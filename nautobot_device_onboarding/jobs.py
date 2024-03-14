# pylint: disable=attribute-defined-outside-init
"""Device Onboarding Jobs."""

import csv
import logging
from io import StringIO

from diffsync.enum import DiffSyncFlags
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.apps.jobs import BooleanVar, FileVar, IntegerVar, Job, MultiObjectVar, ObjectVar, StringVar
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Device, DeviceType, Location, Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Role, SecretsGroup, SecretsGroupAssociation, Status
from nautobot.ipam.models import Namespace
from nautobot_ssot.jobs.base import DataSource

from nautobot_device_onboarding.diffsync.adapters.network_importer_adapters import (
    NetworkImporterNautobotAdapter,
    NetworkImporterNetworkAdapter,
)
from nautobot_device_onboarding.diffsync.adapters.onboarding_adapters import (
    OnboardingNautobotAdapter,
    OnboardingNetworkAdapter,
)


from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.helpers import onboarding_task_fqdn_to_ip
from nautobot_device_onboarding.netdev_keeper import NetdevKeeper
from nautobot_device_onboarding.utils.formatter import map_interface_type
from nautobot_device_onboarding.nornir_plays.command_getter import command_getter_do, command_getter_ni
from netutils.interface import canonical_interface_name

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]

LOGGER = logging.getLogger(__name__)
name = "Device Onboarding/Network Importer"  # pylint: disable=invalid-name


class OnboardingTask(Job):  # pylint: disable=too-many-instance-attributes
    """Nautobot Job for onboarding a new device."""

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
        model=SecretsGroup, required=False, description="SecretsGroup for Device connection credentials."
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

        name = "Perform Device Onboarding"
        description = "Login to a device(s) and populate Nautobot Device object(s)."
        has_sensitive_variables = False

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
        # allows for itteration without having to spawn multiple jobs
        # Later refactor to use nautobot-plugin-nornir
        for address in data["ip_address"].replace(" ", "").split(","):
            try:
                self._onboard(address=address)
            except OnboardException as err:
                self.logger.exception(
                    "The following exception occurred when attempting to onboard %s: %s", address, str(err)
                )
                if not data["continue_on_failure"]:
                    raise OnboardException(
                        "fail-general - An exception occured and continue on failure was disabled."
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
            napalm_driver=self.platform.napalm_driver if self.platform and self.platform.napalm_driver else None,
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
            "netdev_nb_role_name": self.role.name if self.role else PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_nb_platform_name": self.platform.name if self.platform else None,
            "netdev_nb_credentials": self.credentials if PLUGIN_SETTINGS["assign_secrets_group"] else None,
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
        onboarding_cls.credentials = {"username": self.username, "password": self.password, "secret": self.secret}
        onboarding_cls.run(onboarding_kwargs=onboarding_kwargs)
        self.logger.info(
            "Successfully onboarded %s with a management IP of %s", netdev_dict["netdev_hostname"], address
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


class SSOTDeviceOnboarding(DataSource):  # pylint: disable=too-many-instance-attributes
    """Job for syncing basic device info from a network into Nautobot."""

    def __init__(self, *args, **kwargs):
        """Initialize SSOTDeviceOnboarding."""
        super().__init__(*args, **kwargs)
        self.processed_csv_data = {}
        self.task_kwargs_csv_data = {}

        self.diffsync_flags = DiffSyncFlags.SKIP_UNMATCHED_DST

    class Meta:
        """Metadata about this Job."""

        name = "Sync Devices"
        description = "Synchronize basic device information into Nautobot"

    debug = BooleanVar(
        default=False,
        description="Enable for more verbose logging.",
    )
    csv_file = FileVar(
        label="CSV File", required=False, description="If a file is provided all the options below will be ignored."
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
        description="IP address of the device to sync, specify in a comma separated list for multiple devices.",
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
        model=SecretsGroup, required=False, description="SecretsGroup for device connection credentials."
    )
    platform = ObjectVar(
        model=Platform,
        required=False,
        description="Device platform. Define ONLY to override auto-recognition of platform.",
    )

    def load_source_adapter(self):
        """Load onboarding network adapter."""
        self.source_adapter = OnboardingNetworkAdapter(job=self, sync=self.sync)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load onboarding Nautobot adapter."""
        self.target_adapter = OnboardingNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def _convert_sring_to_bool(self, string, header):
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
        """Convert CSV data into a dictionary containing Nautobot objects."""
        self.logger.info("Decoding CSV file...")
        decoded_csv_file = csv_file.read().decode("utf-8")
        csv_reader = csv.DictReader(StringIO(decoded_csv_file))
        self.logger.info("Processing CSV data...")
        processing_failed = False
        processed_csv_data = {}
        self.task_kwargs_csv_data = {}
        row_count = 1
        for row in csv_reader:
            query = None
            try:
                query = f"location_name: {row.get('location_name')}, location_parent_name: {row.get('location_parent_name')}"
                if row.get("location_parent_name"):
                    location = Location.objects.get(
                        name=row["location_name"].strip(), parent__name=row["location_parent_name"].strip()
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

                set_mgmgt_only = self._convert_sring_to_bool(
                    string=row["set_mgmt_only"].lower().strip(), header="set_mgmt_only"
                )
                update_devices_without_primary_ip = self._convert_sring_to_bool(
                    string=row["update_devices_without_primary_ip"].lower().strip(),
                    header="update_devices_without_primary_ip",
                )

                processed_csv_data[row["ip_address_host"]] = {}
                processed_csv_data[row["ip_address_host"]]["location"] = location
                processed_csv_data[row["ip_address_host"]]["namespace"] = namespace
                processed_csv_data[row["ip_address_host"]]["port"] = int(row["port"].strip())
                processed_csv_data[row["ip_address_host"]]["timeout"] = int(row["timeout"].strip())
                processed_csv_data[row["ip_address_host"]]["set_mgmt_only"] = set_mgmgt_only
                processed_csv_data[row["ip_address_host"]][
                    "update_devices_without_primary_ip"
                ] = update_devices_without_primary_ip
                processed_csv_data[row["ip_address_host"]]["device_role"] = device_role
                processed_csv_data[row["ip_address_host"]]["device_status"] = device_status
                processed_csv_data[row["ip_address_host"]]["interface_status"] = interface_status
                processed_csv_data[row["ip_address_host"]]["ip_address_status"] = ip_address_status
                processed_csv_data[row["ip_address_host"]]["secrets_group"] = secrets_group
                processed_csv_data[row["ip_address_host"]]["platform"] = platform

                # Prepare ids to send to the job in celery
                self.task_kwargs_csv_data[row["ip_address_host"]] = {}
                self.task_kwargs_csv_data[row["ip_address_host"]]["port"] = int(row["port"].strip())
                self.task_kwargs_csv_data[row["ip_address_host"]]["timeout"] = int(row["timeout"].strip())
                self.task_kwargs_csv_data[row["ip_address_host"]]["secrets_group"] = (
                    secrets_group.id if secrets_group else ""
                )
                self.task_kwargs_csv_data[row["ip_address_host"]]["platform"] = platform.id if platform else ""
                row_count += 1
            except ObjectDoesNotExist as err:
                self.logger.error(f"(row {sum([row_count, 1])}), {err} {query}")
                processing_failed = True
                row_count += 1
            except ValidationError as err:
                self.logger.error(f"(row {sum([row_count, 1])}), {err}")
                row_count += 1
        if processing_failed:
            processed_csv_data = None
        if row_count <= 1:
            self.logger.error("The CSV file is empty!")
            processed_csv_data = None

        return processed_csv_data

    def run(
        self,
        dryrun,
        memory_profiling,
        debug,
        csv_file,
        location,
        namespace,
        ip_addresses,
        set_mgmt_only,
        update_devices_without_primary_ip,
        device_role,
        device_status,
        interface_status,
        ip_address_status,
        port,
        timeout,
        secrets_group,
        platform,
        *args,
        **kwargs,
    ):
        """Run sync."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = debug

        if csv_file:
            self.processed_csv_data = self._process_csv_data(csv_file=csv_file)
            if self.processed_csv_data:
                # create a list of ip addresses for processing in the adapter
                self.ip_addresses = []
                for ip_address in self.processed_csv_data:
                    self.ip_addresses.append(ip_address)
                # prepare the task_kwargs needed by the CommandGetterDO job
                self.job_result.task_kwargs = {"debug": debug, "csv_file": self.task_kwargs_csv_data}
            else:
                raise ValidationError(message="CSV check failed. No devices will be onboarded.")

        else:
            # Verify that all requried form inputs have been provided
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
            if not missing_required_inputs:
                pass
            else:
                self.logger.error(f"Missing requried inputs from job form: {missing_required_inputs}")
                raise ValidationError(message=f"Missing required inputs {missing_required_inputs}")

            self.location = location
            self.namespace = namespace
            self.ip_addresses = ip_addresses.replace(" ", "").split(",")
            self.set_mgmt_only = set_mgmt_only
            self.update_devices_without_primary_ip = update_devices_without_primary_ip
            self.device_role = device_role
            self.device_status = device_status
            self.interface_status = interface_status
            self.ip_address_status = ip_address_status
            self.port = port
            self.timeout = timeout
            self.secrets_group = secrets_group
            self.platform = platform

            self.job_result.task_kwargs = {
                "debug": debug,
                "location": location,
                "namespace": namespace,
                "ip_addresses": ip_addresses,
                "set_mgmt_only": set_mgmt_only,
                "update_devices_without_primary_ip": update_devices_without_primary_ip,
                "device_role": device_role,
                "device_status": device_status,
                "interface_status": interface_status,
                "ip_address_status": ip_address_status,
                "port": port,
                "timeout": timeout,
                "secrets_group": secrets_group,
                "platform": platform,
                "csv_file": "",
            }
        super().run(dryrun, memory_profiling, *args, **kwargs)


class SSOTNetworkImporter(DataSource):  # pylint: disable=too-many-instance-attributes
    """Job syncing extended device attributes into Nautobot."""

    def __init__(self, *args, **kwargs):
        """Initialize SSOTNetworkImporter."""
        super().__init__(*args, **kwargs)

        self.filtered_devices = None  # Queryset of devices based on form inputs

        # FOR TESTING ONLY, REMOVE WHEN NOT TESTING
        # from nautobot_device_onboarding.diffsync import mock_data
        # from nautobot_device_onboarding.utils import diffsync_utils
        # self.command_getter_result = mock_data.network_importer_mock_data
        # self.devices_to_load = diffsync_utils.generate_device_queryset_from_command_getter_result(mock_data.network_importer_mock_data)
        # FOR TESTING ONLY, REMOVE WHEN NOT TESTING

        # RESTORE THESE LINES WHEN NOT TESTING! #
        self.command_getter_result = None  # Dict result from CommandGetter job
        self.devices_to_load = None  # Queryset consisting of devices that responded
        # RESTORE THESE LINES WHEN NOT TESTING! #

    class Meta:
        """Metadata about this Job."""

        name = "Sync Network Data"
        description = (
            "Synchronize extended device attribute information into Nautobot; "
            "including Interfaces, IPAddresses, Prefixes, Vlans and Cables."
        )

    debug = BooleanVar(description="Enable for more verbose logging.")
    sync_vlans = BooleanVar(default=True, description="Sync VLANs and interface VLAN assignments.")
    namespace = ObjectVar(
        model=Namespace, required=True, description="The namespace for all IP addresses created or updated in the sync."
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

    def load_source_adapter(self):
        """Load onboarding network adapter."""
        # do not load source data if the job form does not filter which devices to sync
        if self.filtered_devices:
            self.source_adapter = NetworkImporterNetworkAdapter(job=self, sync=self.sync)
            self.source_adapter.load()

    def load_target_adapter(self):
        """Load onboarding Nautobot adapter."""
        self.target_adapter = NetworkImporterNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def run(
        self,
        dryrun,
        memory_profiling,
        debug,
        namespace,
        interface_status,
        ip_address_status,
        default_prefix_status,
        location,
        devices,
        device_role,
        sync_vlans,
        *args,
        **kwargs,
    ):
        """Run sync."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = debug
        self.namespace = namespace
        self.ip_address_status = ip_address_status
        self.interface_status = interface_status
        self.default_prefix_status = default_prefix_status
        self.location = location
        self.devices = devices
        self.device_role = device_role
        self.sync_vlans = sync_vlans

        # Filter devices based on form input
        device_filter = {}
        if self.devices:
            device_filter["id__in"] = [device.id for device in devices]
        if self.location:
            device_filter["location"] = location
        if self.device_role:
            device_filter["role"] = device_role
        if device_filter:  # prevent all devices from being returned by an empty filter
            self.filtered_devices = Device.objects.filter(**device_filter)
        else:
            self.logger.error("No device filter options were provided, no devices will be synced.")

        self.job_result.task_kwargs = {
            "debug": debug,
            "ip_address_status": ip_address_status,
            "default_prefix_status": default_prefix_status,
            "location": location,
            "devices": self.filtered_devices,
            "device_role": device_role,
            "sync_vlans": sync_vlans,
        }

        super().run(dryrun, memory_profiling, *args, **kwargs)


class CommandGetterDO(Job):
    """Simple Job to Execute Show Command."""

    class Meta:
        """Job Meta."""

        name = "Command Getter for Device Onboarding"
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = False

    csv_file = StringVar(required=False)
    debug = BooleanVar(required=False)
    ip_addresses = StringVar(required=False)
    port = IntegerVar(required=False)
    timeout = IntegerVar(required=False)
    secrets_group = ObjectVar(model=SecretsGroup)
    platform = ObjectVar(model=Platform, required=False)

    def run(self, *args, **kwargs):
        """Run command getter."""
        compiled_results = command_getter_do(self.job_result, self.logger.getEffectiveLevel(), kwargs)
        return compiled_results


class CommandGetterNetworkImporter(Job):
    """Simple Job to Execute Show Command."""

    class Meta:
        """Job Meta."""

        name = "Command Getter for Network Importer"
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = False

    debug = BooleanVar()
    namespace = ObjectVar(model=Namespace, required=True)
    devices = MultiObjectVar(model=Device, required=False)
    location = ObjectVar(model=Location, required=False)
    device_role = ObjectVar(model=Role, required=False)
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)

    def run(self, *args, **kwargs):
        """Run command getter."""
        compiled_results = command_getter_ni(self.job_result, self.logger.getEffectiveLevel(), kwargs)
        for device, device_data in compiled_results.items():
            self.logger.info(f"Device Data: {device_data}")
            serial = Device.objects.get(name=device).serial
            self.logger.info(f"Serial: {serial}")
            mtu_list = device_data.get("mtu", [])
            type_list = device_data.get("type", [])
            ip_list = device_data.get("ip_addresses", [])
            prefix_list = device_data.get("prefix_length", [])
            mac_list = device_data.get("mac_address", [])
            description_list = device_data.get("description", [])
            link_status_list = device_data.get("link_status", [])
            self.logger.info(f"IP List {ip_list}")
            self.logger.info(f"Prefix List {prefix_list}")
            interface_dict = {}
            for item in mtu_list:
                interface_dict.setdefault(item["interface"], {})["mtu"] = item["mtu"]
            for item in type_list:
                interface_type = map_interface_type(item["type"])
                interface_dict.setdefault(item["interface"], {})["type"] = interface_type
            for item in ip_list:
                interface_dict.setdefault(item["interface"], {})["ip_addresses"] = {"host": item["ip_address"]}
            self.logger.info(f"Interface Dict {interface_dict}")
            for item in prefix_list:
                interface_dict.setdefault(item["interface"], {}).setdefault("ip_addresses", {})["prefix_length"] = item[
                    "prefix_length"
                ]
            for item in mac_list:
                interface_dict.setdefault(item["interface"], {})["mac_address"] = item["mac_address"]
            for item in description_list:
                interface_dict.setdefault(item["interface"], {})["description"] = item["description"]
            for item in link_status_list:
                interface_dict.setdefault(item["interface"], {})["enabled"] = (
                    True if item["link_status"] == "up" else False
                )

            device_data["interfaces"] = interface_dict
            device_data["serial"] = serial

            del device_data["mtu"]
            del device_data["type"]
            del device_data["ip_addresses"]
            del device_data["prefix_length"]
            del device_data["mac_address"]
            del device_data["description"]
            del device_data["link_status"]

        return compiled_results


jobs = [OnboardingTask, SSOTDeviceOnboarding, SSOTNetworkImporter, CommandGetterDO, CommandGetterNetworkImporter]
register_jobs(*jobs)
