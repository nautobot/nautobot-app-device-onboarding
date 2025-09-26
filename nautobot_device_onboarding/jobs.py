# pylint: disable=attribute-defined-outside-init
"""Device Onboarding Jobs."""

import csv
import json
import logging
import socket

import netaddr
from diffsync.enum import DiffSyncFlags
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.apps.jobs import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    Job,
    MultiObjectVar,
    ObjectVar,
    StringVar,
)
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Device, DeviceType, Location, Platform
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.models import (
    CustomField,
    Role,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
)
from nautobot.ipam.models import Namespace
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_ssot.jobs.base import DataSource
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister

from nautobot_device_onboarding.choices import SSOT_JOB_TO_COMMAND_CHOICE
from nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters import (
    SyncDevicesNautobotAdapter,
    SyncDevicesNetworkAdapter,
)
from nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters import (
    SyncNetworkDataNautobotAdapter,
    SyncNetworkDataNetworkAdapter,
)
from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.netdev_keeper import NetdevKeeper
from nautobot_device_onboarding.nornir_plays.command_getter import (
    _parse_credentials,
    netmiko_send_commands,
)
from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory
from nautobot_device_onboarding.nornir_plays.inventory_creator import _set_inventory
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
from nautobot_device_onboarding.nornir_plays.processor import TroubleshootingProcessor
from nautobot_device_onboarding.utils.helper import onboarding_task_fqdn_to_ip

InventoryPluginRegister.register("empty-inventory", EmptyInventory)

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]

LOGGER = logging.getLogger(__name__)
name = "Device Onboarding"  # pylint: disable=invalid-name


class OnboardingTask(Job):  # pylint: disable=too-many-instance-attributes
    """Nautobot Job for onboarding a new device (original)."""

    location = ObjectVar(
        model=Location,
        query_params={"content_type": "dcim.device"},
        description="Assigned Location for the onboarded device.",
    )
    ip_address = StringVar(
        description="IP Address/DNS Name of the device to onboard, specify in a comma separated list for multiple devices.",
        label="IP Address/FQDN",
    )
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)
    credentials = ObjectVar(
        model=SecretsGroup,
        required=False,
        description="SecretsGroup for Device connection credentials.",
    )
    platform = ObjectVar(
        model=Platform,
        required=False,
        description="Device platform. Define ONLY to override auto-recognition of platform.",
    )
    role = ObjectVar(
        model=Role,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Device role. Define ONLY to override auto-recognition of role.",
    )
    device_type = ObjectVar(
        model=DeviceType,
        label="Device Type",
        required=False,
        description="Device type. Define ONLY to override auto-recognition of type.",
    )
    continue_on_failure = BooleanVar(
        label="Continue On Failure",
        default=True,
        description="If an exception occurs, log the exception and continue to next device.",
    )

    class Meta:
        """Meta object boilerplate for onboarding."""

        name = "Perform Device Onboarding (Original)"
        description = "Login to a device(s) and populate Nautobot Device object(s). This is the original Job as part of Device Onboarding initially created in 2021."
        has_sensitive_variables = False
        hidden = True

    def __init__(self, *args, **kwargs):
        """Overload init to instantiate class attributes per W0201."""
        self.username = None
        self.password = None
        self.secret = None
        self.platform = None
        self.port = None
        self.timeout = None
        self.location = None
        self.device_type = None
        self.role = None
        self.credentials = None
        super().__init__(*args, **kwargs)

    def run(self, *args, **data):
        """Process a single Onboarding Task instance."""
        self._parse_credentials(data["credentials"])
        self.platform = data["platform"]
        self.port = data["port"]
        self.timeout = data["timeout"]
        self.location = data["location"]
        self.device_type = data["device_type"]
        self.role = data["role"]
        self.credentials = data["credentials"]

        self.logger.info("START: onboarding devices")
        # allows for iteration without having to spawn multiple jobs
        # Later refactor to use nautobot-plugin-nornir
        for address in data["ip_address"].replace(" ", "").split(","):
            try:
                self._onboard(address=address)
            except OnboardException as err:
                self.logger.exception(
                    "The following exception occurred when attempting to onboard %s: %s",
                    address,
                    str(err),
                )
                if not data["continue_on_failure"]:
                    raise OnboardException(
                        "fail-general - An exception occurred and continue on failure was disabled."
                    ) from err

    def _onboard(self, address):
        """Onboard single device."""
        self.logger.info("Attempting to onboard %s.", address)
        address = onboarding_task_fqdn_to_ip(address)
        netdev = NetdevKeeper(
            hostname=address,
            port=self.port,
            timeout=self.timeout,
            username=self.username,
            password=self.password,
            secret=self.secret,
            napalm_driver=(self.platform.napalm_driver if self.platform and self.platform.napalm_driver else None),
            optional_args=(
                self.platform.napalm_args if self.platform and self.platform.napalm_args else settings.NAPALM_ARGS
            ),
        )
        netdev.get_onboarding_facts()
        netdev_dict = netdev.get_netdev_dict()

        onboarding_kwargs = {
            # Kwargs extracted from OnboardingTask:
            "netdev_mgmt_ip_address": address,
            "netdev_nb_location_name": self.location.name,
            "netdev_nb_device_type_name": self.device_type,
            "netdev_nb_role_name": (self.role.name if self.role else PLUGIN_SETTINGS["default_device_role"]),
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_nb_platform_name": self.platform.name if self.platform else None,
            "netdev_nb_credentials": (self.credentials if PLUGIN_SETTINGS["assign_secrets_group"] else None),
            # Kwargs discovered on the Onboarded Device:
            "netdev_hostname": netdev_dict["netdev_hostname"],
            "netdev_vendor": netdev_dict["netdev_vendor"],
            "netdev_model": netdev_dict["netdev_model"],
            "netdev_serial_number": netdev_dict["netdev_serial_number"],
            "netdev_mgmt_ifname": netdev_dict["netdev_mgmt_ifname"],
            "netdev_mgmt_pflen": netdev_dict["netdev_mgmt_pflen"],
            "netdev_netmiko_device_type": netdev_dict["netdev_netmiko_device_type"],
            "onboarding_class": netdev_dict["onboarding_class"],
            "driver_addon_result": netdev_dict["driver_addon_result"],
        }
        onboarding_cls = netdev_dict["onboarding_class"]()
        onboarding_cls.credentials = {
            "username": self.username,
            "password": self.password,
            "secret": self.secret,
        }
        onboarding_cls.run(onboarding_kwargs=onboarding_kwargs)
        self.logger.info(
            "Successfully onboarded %s with a management IP of %s",
            netdev_dict["netdev_hostname"],
            address,
        )

    def _parse_credentials(self, credentials):
        """Parse and return dictionary of credentials."""
        if credentials:
            self.logger.info("Attempting to parse credentials from selected SecretGroup")
            try:
                self.username = credentials.get_secret_value(
                    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                )
                self.password = credentials.get_secret_value(
                    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
                )
                try:
                    self.secret = credentials.get_secret_value(
                        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                        secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
                    )
                except SecretsGroupAssociation.DoesNotExist:
                    self.secret = None
            except SecretsGroupAssociation.DoesNotExist as err:
                self.logger.exception(
                    "Unable to use SecretsGroup selected, ensure Access Type is set to Generic & at minimum Username & Password types are set."
                )
                raise OnboardException("fail-credentials - Unable to parse selected credentials.") from err

        else:
            self.logger.info("Using napalm credentials configured in nautobot_config.py")
            self.username = settings.NAPALM_USERNAME
            self.password = settings.NAPALM_PASSWORD
            self.secret = settings.NAPALM_ARGS.get("secret", None)


class SSOTSyncDevices(DataSource):  # pylint: disable=too-many-instance-attributes
    """Job for syncing basic device info from a network into Nautobot."""

    def __init__(self, *args, **kwargs):
        """Initialize SSoTSyncDevices."""
        super().__init__(*args, **kwargs)
        self.ip_address_inventory = {}
        self.found_invalid_ip_address = False

        self.diffsync_flags = DiffSyncFlags.SKIP_UNMATCHED_DST

    class Meta:
        """Metadata about this Job."""

        name = "Sync Devices From Network"
        description = "Synchronize basic device information into Nautobot from one or more network devices. Information includes Device Name, Serial Number, Management IP/Interface."
        has_sensitive_variables = False

    debug = BooleanVar(
        default=False,
        description="Enable for more verbose logging.",
    )
    connectivity_test = BooleanVar(
        default=False,
        description="Enable to test connectivity to the device(s) prior to attempting onboarding.",
    )
    csv_file = FileVar(
        label="CSV File",
        required=False,
        description="If a file is provided, all the options in the manual input tab will be disabled.",
    )
    location = ObjectVar(
        model=Location,
        required=False,
        query_params={"content_type": "dcim.device"},
        description="Assigned Location for all synced device(s)",
    )
    namespace = ObjectVar(model=Namespace, required=False, description="Namespace ip addresses belong to.")
    ip_addresses = StringVar(
        required=False,
        description="IP address or FQDN of the device to sync, specify in a comma separated list for multiple devices.",
        label="IPv4 addresses",
    )
    port = IntegerVar(required=False, default=22)
    timeout = IntegerVar(required=False, default=30)
    set_mgmt_only = BooleanVar(
        default=True,
        label="Set Management Only",
        description="If True, new interfaces that are created will be set to management only. If False, new interfaces will be set to not be management only.",
    )
    update_devices_without_primary_ip = BooleanVar(
        default=False,
        description="If a device at the specified location already exists in Nautobot but the primary ip address "
        "does not match an ip address entered, update this device with the sync.",
    )
    device_role = ObjectVar(
        model=Role,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Role to be applied to all synced devices.",
    )
    device_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Status to be applied to all synced devices.",
    )
    interface_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.interface"},
        required=False,
        description="Status to be applied to all new synced device interfaces. This value does not update with additional syncs.",
    )
    ip_address_status = ObjectVar(
        label="IP address status",
        model=Status,
        query_params={"content_types": "ipam.ipaddress"},
        required=False,
        description="Status to be applied to all new synced IP addresses. This value does not update with additional syncs.",
    )
    secrets_group = ObjectVar(
        model=SecretsGroup,
        required=False,
        description="SecretsGroup for device connection credentials.",
    )
    platform = ObjectVar(
        model=Platform,
        required=False,
        description="Device platform. Define ONLY to override auto-recognition of platform.",
    )

    template_name = "nautobot_device_onboarding/ssot_sync_devices.html"

    def load_source_adapter(self):
        """Load onboarding network adapter."""
        self.source_adapter = SyncDevicesNetworkAdapter(job=self, sync=self.sync)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load onboarding Nautobot adapter."""
        self.target_adapter = SyncDevicesNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def _convert_string_to_bool(self, string, header):
        """Given a string of 'true' or 'false' convert to bool."""
        if string.lower() == "true":
            return True
        if string.lower() == "false":
            return False
        raise ValidationError(
            f"'{string}' in column '{header}' failed to convert to a boolean value. "
            "Please use either 'True' or 'False'."
        )

    def _process_csv_data(self, csv_file):
        """Convert CSV data into a list of dictionaries containing Nautobot objects."""
        self.logger.info("Decoding CSV file...")
        decoded_csv_file = csv_file.read().decode("utf-8")
        csv_reader = csv.DictReader(decoded_csv_file.split("\n"))

        if len(decoded_csv_file.split("\n")) <= 1:
            self.logger.error("The CSV file contains no data!")
            return None

        self.logger.info("Processing CSV data...")
        processing_failed = False
        processed_csv_data = {}
        for row_num, row in enumerate(csv_reader, start=2):
            query = None
            try:
                query = f"location_name: {row.get('location_name')}, location_parent_name: {row.get('location_parent_name')}"
                if row.get("location_parent_name"):
                    location = Location.objects.get(
                        name=row["location_name"].strip(),
                        parent__name=row["location_parent_name"].strip(),
                    )
                else:
                    query = query = f"location_name: {row.get('location_name')}"
                    location = Location.objects.get(name=row["location_name"].strip(), parent=None)
                query = f"device_role: {row.get('device_role_name')}"
                device_role = Role.objects.get(
                    name=row["device_role_name"].strip(),
                )
                query = f"namespace: {row.get('namespace')}"
                namespace = Namespace.objects.get(
                    name=row["namespace"].strip(),
                )
                query = f"device_status: {row.get('device_status_name')}"
                device_status = Status.objects.get(
                    name=row["device_status_name"].strip(),
                )
                query = f"interface_status: {row.get('interface_status_name')}"
                interface_status = Status.objects.get(
                    name=row["interface_status_name"].strip(),
                )
                query = f"ip_address_status: {row.get('ip_address_status_name')}"
                ip_address_status = Status.objects.get(
                    name=row["ip_address_status_name"].strip(),
                )
                query = f"secrets_group: {row.get('secrets_group_name')}"
                secrets_group = SecretsGroup.objects.get(
                    name=row["secrets_group_name"].strip(),
                )
                query = f"platform: {row.get('platform_name')}"
                platform = None
                if row.get("platform_name"):
                    platform = Platform.objects.get(
                        name=row["platform_name"].strip(),
                    )
                    self._validate_platform_network_driver(platform)

                set_mgmt_only = self._convert_string_to_bool(
                    string=row["set_mgmt_only"].lower().strip(), header="set_mgmt_only"
                )
                update_devices_without_primary_ip = self._convert_string_to_bool(
                    string=row["update_devices_without_primary_ip"].lower().strip(),
                    header="update_devices_without_primary_ip",
                )

                resolved_ip = self._validate_ip_address(row["ip_address_host"])
                processed_row = {
                    "original_ip_address": row["ip_address_host"],
                    "location": location,
                    "namespace": namespace,
                    "port": int(row["port"].strip()),
                    "timeout": int(row["timeout"].strip()),
                    "set_mgmt_only": set_mgmt_only,
                    "update_devices_without_primary_ip": update_devices_without_primary_ip,
                    "device_role": device_role,
                    "device_status": device_status,
                    "interface_status": interface_status,
                    "ip_address_status": ip_address_status,
                    "secrets_group": secrets_group,
                    "platform": platform,
                }

                processed_csv_data[resolved_ip] = processed_row

            except ObjectDoesNotExist as err:
                self.logger.error(f"(row {row_num}), {err} {query}")
                processing_failed = True
            except ValidationError as err:
                self.logger.error(f"(row {row_num}), {err}")
                processing_failed = True
        if processing_failed:
            processed_csv_data = None

        return processed_csv_data

    def _validate_ip_address(self, ip_address):
        """Validate the IP Address, resolving FQDNs and replacing with an IP as necessary."""
        try:
            netaddr.IPAddress(ip_address)
            return ip_address
        except netaddr.AddrFormatError:
            try:
                resolved_ip = socket.gethostbyname(ip_address)
                self.logger.info("[{%s}] resolved to [{%s}]", ip_address, resolved_ip)
                return resolved_ip
            except socket.gaierror:
                self.logger.error("[{%s}] is not a valid IP Address or FQDN.", ip_address)
                self.found_invalid_ip_address = True
                return ip_address

    def _validate_platform_network_driver(self, platform):
        if not platform.network_driver:
            self.logger.error(
                "The selected platform, '%s' does not have a network driver, please update the Platform.", platform
            )
            return False
        return True

    def run(  # pylint: disable=too-many-positional-arguments
        self,
        dryrun=True,
        memory_profiling=False,
        debug=False,
        port=22,
        timeout=30,
        connectivity_test=False,
        update_devices_without_primary_ip=False,
        set_mgmt_only=True,
        csv_file=None,
        location=None,
        namespace=None,
        ip_addresses=None,
        device_role=None,
        device_status=None,
        interface_status=None,
        ip_address_status=None,
        secrets_group=None,
        platform=None,
    ):
        """Run sync."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = debug

        if csv_file:
            self.ip_address_inventory = self._process_csv_data(csv_file=csv_file)
            if not self.ip_address_inventory:
                raise ValidationError(message="CSV check failed. No devices will be synced.")

        else:
            # Verify that all required form inputs have been provided, this is here in case the form is not used
            required_inputs = {
                "location": location,
                "namespace": namespace,
                "ip_addresses": ip_addresses,
                "device_role": device_role,
                "device_status": device_status,
                "interface_status": interface_status,
                "ip_address_status": ip_address_status,
                "port": port,
                "timeout": timeout,
                "secrets_group": secrets_group,
            }

            missing_required_inputs = [
                form_field for form_field, input_value in required_inputs.items() if not input_value
            ]
            if missing_required_inputs:
                self.logger.error(f"Missing requried inputs from job form: {missing_required_inputs}")
                raise ValidationError(message=f"Missing required inputs {missing_required_inputs}")

            default_values = {
                "port": int(port),
                "timeout": int(timeout),
                "secrets_group": secrets_group,
                "platform": platform,
                "location": location,
                "namespace": namespace,
                "device_role": device_role,
                "device_status": device_status,
                "interface_status": interface_status,
                "ip_address_status": ip_address_status,
                "set_mgmt_only": set_mgmt_only,
                "update_devices_without_primary_ip": update_devices_without_primary_ip,
            }

            if platform:
                if not self._validate_platform_network_driver(platform):
                    # TODO: We're only raising an exception if a csv file is not provided. Is that correct?
                    raise ValueError("Platform.network_driver missing")

            for ip_address in ip_addresses.replace(" ", "").split(","):
                resolved = self._validate_ip_address(ip_address)
                self.ip_address_inventory[resolved] = {"original_ip_address": ip_address, **default_values}

        self.connectivity_test = connectivity_test
        self.csv_file = csv_file

        if self.found_invalid_ip_address:
            raise RuntimeError("An invalid IP Address or FQDN was provided")

        super().run(dryrun, memory_profiling)


class SSOTSyncNetworkData(DataSource):  # pylint: disable=too-many-instance-attributes
    """Job syncing extended device attributes into Nautobot."""

    def __init__(self, *args, **kwargs):
        """Initialize SSOTSyncNetworkData."""
        super().__init__(*args, **kwargs)

        self.filtered_devices = None  # Queryset of devices based on job form inputs
        self.command_getter_result = None  # Dict result from CommandGetter nornir task
        self.devices_to_load = None  # Queryset consisting of devices that responded

    class Meta:
        """Metadata about this Job."""

        name = "Sync Network Data From Network"
        description = "Synchronize extended device attribute information into Nautobot from one or more network devices. Information includes Interfaces, IP Addresses, Prefixes, VLANs and VRFs."
        has_sensitive_variables = False

    debug = BooleanVar(description="Enable for more verbose logging.")
    connectivity_test = BooleanVar(
        default=False,
        description="Enable to test connectivity to the device(s) prior to attempting onboarding.",
    )
    sync_vlans = BooleanVar(default=False, description="Sync VLANs and interface VLAN assignments.")
    sync_vrfs = BooleanVar(default=False, description="Sync VRFs and interface VRF assignments.")
    sync_cables = BooleanVar(default=False, description="Sync cables between interfaces via a LLDP or CDP.")
    sync_software_version = BooleanVar(default=False, description="Sync software version from device.")
    namespace = ObjectVar(
        model=Namespace,
        required=True,
        description="The namespace for all IP addresses created or updated in the sync.",
    )
    interface_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.interface"},
        required=True,
        description="Status to be applied to all synced device interfaces. This will update existing interface statuses.",
    )
    ip_address_status = ObjectVar(
        label="IP address status",
        model=Status,
        query_params={"content_types": "ipam.ipaddress"},
        required=True,
        description="Status to be applied to all synced IP addresses. This will update existing IP address statuses",
    )

    default_prefix_status = ObjectVar(
        model=Status,
        query_params={"content_types": "ipam.prefix"},
        required=True,
        description="Status to be applied to all new created prefixes. Prefix status does not update with additional syncs.",
    )
    devices = MultiObjectVar(
        model=Device,
        required=False,
        description="Device(s) to update.",
    )
    location = ObjectVar(
        model=Location,
        query_params={"content_type": "dcim.device"},
        required=False,
        description="Only update devices at a specific location.",
    )
    device_role = ObjectVar(
        model=Role,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Only update devices with the selected role.",
    )
    platform = ObjectVar(
        model=Platform,
        required=False,
        description="Only update devices with the selected platform.",
    )

    def load_source_adapter(self):
        """Load network data adapter."""
        # do not load source data if the job form does not filter which devices to sync
        if self.filtered_devices:
            self.source_adapter = SyncNetworkDataNetworkAdapter(job=self, sync=self.sync)
            self.source_adapter.load()

    def load_target_adapter(self):
        """Load network data Nautobot adapter."""
        self.target_adapter = SyncNetworkDataNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def run(  # pylint: disable=too-many-positional-arguments
        self,
        dryrun,
        memory_profiling,
        debug,
        connectivity_test,
        sync_vlans,
        sync_vrfs,
        sync_cables,
        sync_software_version,
        namespace,
        interface_status,
        ip_address_status,
        default_prefix_status,
        devices=None,
        location=None,
        device_role=None,
        platform=None,
    ):
        """Run sync."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = debug
        self.connectivity_test = connectivity_test
        self.sync_vlans = sync_vlans
        self.sync_vrfs = sync_vrfs
        self.sync_cables = sync_cables
        self.sync_software_version = sync_software_version
        self.namespace = namespace
        self.interface_status = interface_status
        self.ip_address_status = ip_address_status
        self.default_prefix_status = default_prefix_status
        self.devices = devices
        self.location = location
        self.device_role = device_role
        self.platform = platform

        # Check for last_network_data_sync CustomField
        if self.debug:
            self.logger.debug("Checking for last_network_data_sync custom field")
        try:
            cf = CustomField.objects.get(  # pylint:disable=invalid-name
                key="last_network_data_sync"
            )
        except ObjectDoesNotExist:
            cf, _ = CustomField.objects.get_or_create(  # pylint:disable=invalid-name
                label="Last Network Data Sync",
                key="last_network_data_sync",
                type=CustomFieldTypeChoices.TYPE_DATE,
                required=False,
            )

            cf.content_types.add(ContentType.objects.get_for_model(Device))

            if self.debug:
                self.logger.debug("Custom field found or created")
        except Exception as err:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to get or create last_network_data_sync custom field, {err}")
            return

        # Filter devices based on form input
        device_filter = {}
        if self.devices:
            device_filter["id__in"] = [device.id for device in devices]
        if self.location:
            device_filter["location"] = location
        if self.device_role:
            device_filter["role"] = device_role
        if self.platform:
            device_filter["platform"] = platform
        if device_filter:  # prevent all devices from being returned by an empty filter
            self.filtered_devices = Device.objects.filter(**device_filter)
        else:
            self.logger.error("No device filter options were provided, no devices will be synced.")

        # Stop the job if no devices are returned after filtering
        if not self.filtered_devices:
            self.logger.info("No devices returned based on filter selections.")
            return

        # Log the devices that will be synced
        filtered_devices_names = list(self.filtered_devices.values_list("name", flat=True))
        self.logger.info(f"{len(filtered_devices_names)} devices will be synced")
        if len(filtered_devices_names) <= 300:
            self.logger.info(f"Devices: {filtered_devices_names}")
        else:
            self.logger.warning("Over 300 devices were selected to sync")

        super().run(dryrun, memory_profiling)


class DeviceOnboardingTroubleshootingJob(Job):
    """Simple Job to Execute Show Command."""

    debug = BooleanVar()
    ip_addresses = StringVar()
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)
    secrets_group = ObjectVar(model=SecretsGroup)
    platform = ObjectVar(model=Platform, required=True)
    ssot_job_type = ChoiceVar(choices=SSOT_JOB_TO_COMMAND_CHOICE)

    class Meta:
        """Meta object boilerplate for onboarding."""

        name = "Runs Commands on a Device to simulate SSoT Command Getter."
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = True

    def run(self, *args, **kwargs):  # pragma: no cover
        """Process onboarding task from ssot-ni job."""
        logger = NornirLogger(self.job_result, self.logger.getEffectiveLevel())
        ip_addresses = kwargs["ip_addresses"].replace(" ", "").split(",")
        port = kwargs["port"]
        platform = kwargs["platform"]
        username, password = (  # pylint:disable=unused-variable
            _parse_credentials(kwargs["secrets_group"], logger=logger)
        )
        kwargs["connectivity_test"] = False
        # Initiate Nornir instance with empty inventory
        compiled_results = {}
        try:
            with InitNornir(
                runner=NORNIR_SETTINGS.get("runner"),
                logging={"enabled": False},
                inventory={
                    "plugin": "empty-inventory",
                },
            ) as nornir_obj:
                for entered_ip in ip_addresses:
                    single_host_inventory_constructed, _ = _set_inventory(
                        entered_ip, platform, port, username, password
                    )
                    nornir_obj.inventory.hosts.update(single_host_inventory_constructed)
                nr_with_processors = nornir_obj.with_processors([TroubleshootingProcessor(compiled_results)])
                if kwargs["ssot_job_type"] == "both":
                    kwargs.update({"sync_vrfs": True})
                    kwargs.update({"sync_vlans": True})
                    kwargs.update({"sync_cables": True})
                    kwargs.update({"sync_software_version": True})
                    nr_with_processors.run(
                        task=netmiko_send_commands,
                        command_getter_yaml_data=nornir_obj.inventory.defaults.data["platform_parsing_info"],
                        command_getter_job="sync_devices",
                        logger=logger,
                        **kwargs,
                    )
                    nr_with_processors.run(
                        task=netmiko_send_commands,
                        command_getter_yaml_data=nornir_obj.inventory.defaults.data["platform_parsing_info"],
                        command_getter_job="sync_network_data",
                        logger=logger,
                        **kwargs,
                    )
                else:
                    if kwargs["ssot_job_type"] == "sync_network_data":
                        kwargs.update({"sync_vrfs": True})
                        kwargs.update({"sync_vlans": True})
                        kwargs.update({"sync_cables": True})
                        kwargs.update({"sync_software_version": True})
                    nr_with_processors.run(
                        task=netmiko_send_commands,
                        command_getter_yaml_data=nornir_obj.inventory.defaults.data["platform_parsing_info"],
                        command_getter_job=kwargs["ssot_job_type"],
                        logger=logger,
                        **kwargs,
                    )
        except Exception as err:  # pylint: disable=broad-exception-caught
            self.logger.info("Error During Sync Devices Command Getter: %s", err)
        self.create_file("command_outputs.json", json.dumps(compiled_results))
        return f"Successfully ran the following commands: {', '.join(list(compiled_results.keys()))}"


jobs = [
    OnboardingTask,
    SSOTSyncDevices,
    SSOTSyncNetworkData,
    DeviceOnboardingTroubleshootingJob,
]
register_jobs(*jobs)
