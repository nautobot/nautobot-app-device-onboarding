# pylint: disable=attribute-defined-outside-init
"""Device Onboarding Jobs."""

import logging

from diffsync.enum import DiffSyncFlags
from django.conf import settings
from nautobot.apps.jobs import BooleanVar, IntegerVar, Job, MultiObjectVar, ObjectVar, StringVar
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Device, DeviceType, Location, Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Role, SecretsGroup, SecretsGroupAssociation, Status, Tag
from nautobot.ipam.models import Namespace
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
from nautobot_device_onboarding.nornir_plays.command_getter import netmiko_send_commands
from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
from nautobot_device_onboarding.nornir_plays.processor import ProcessorDO
from nautobot_device_onboarding.utils.helper import get_job_filter
from nautobot_device_onboarding.utils.inventory_creator import _set_inventory
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from nautobot_ssot.jobs.base import DataSource
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)
InventoryPluginRegister.register("empty-inventory", EmptyInventory)

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

    def __init__(self):
        """Initialize SSOTDeviceOnboarding."""
        super().__init__()
        self.diffsync_flags = DiffSyncFlags.SKIP_UNMATCHED_DST

    class Meta:
        """Metadata about this Job."""

        name = "Sync Devices"
        description = "Synchronize basic device information into Nautobot"

    debug = BooleanVar(
        default=False,
        description="Enable for more verbose logging.",
    )
    location = ObjectVar(
        model=Location,
        query_params={"content_type": "dcim.device"},
        description="Assigned Location for all synced device(s)",
    )
    namespace = ObjectVar(model=Namespace, description="Namespace ip addresses belong to.")
    ip_addresses = StringVar(
        description="IP address of the device to sync, specify in a comma separated list for multiple devices.",
        label="IPv4 addresses",
    )
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)
    management_only_interface = BooleanVar(
        default=False,
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
        required=True,
        description="Role to be applied to all synced devices.",
    )
    device_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.device"},
        required=True,
        description="Status to be applied to all synced devices.",
    )
    interface_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.interface"},
        required=True,
        description="Status to be applied to all new synced device interfaces. This value does not update with additional syncs.",
    )
    ip_address_status = ObjectVar(
        label="IP address status",
        model=Status,
        query_params={"content_types": "ipam.ipaddress"},
        required=True,
        description="Status to be applied to all new synced IP addresses. This value does not update with additional syncs.",
    )
    secrets_group = ObjectVar(
        model=SecretsGroup, required=True, description="SecretsGroup for device connection credentials."
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

    def run(
        self,
        dryrun,
        memory_profiling,
        debug,
        location,
        namespace,
        ip_addresses,
        management_only_interface,
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
        self.location = location
        self.namespace = namespace
        self.ip_addresses = ip_addresses.replace(" ", "").split(",")
        self.management_only_interface = management_only_interface
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
            "management_only_interface": management_only_interface,
            "update_devices_without_primary_ip": update_devices_without_primary_ip,
            "device_role": device_role,
            "device_status": device_status,
            "interface_status": interface_status,
            "ip_address_status": ip_address_status,
            "port": port,
            "timeout": timeout,
            "secrets_group": secrets_group,
            "platform": platform,
        }
        super().run(dryrun, memory_profiling, *args, **kwargs)


class SSOTNetworkImporter(DataSource):  # pylint: disable=too-many-instance-attributes
    """Job syncing extended device attributes into Nautobot."""

    def __init__(self):
        """Initialize SSOTNetworkImporter."""
        super().__init__()
        self.filtered_devices = None

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
    tag = ObjectVar(
        model=Tag,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Only update devices with the selected tag.",
    )

    def load_source_adapter(self):
        """Load onboarding network adapter."""
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
        ip_address_status,
        default_prefix_status,
        location,
        devices,
        device_role,
        sync_vlans,
        tag,
        *args,
        **kwargs,
    ):
        """Run sync."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = debug
        self.namespace = namespace
        self.ip_address_status = ip_address_status
        self.default_prefix_status = default_prefix_status
        self.location = location
        self.devices = devices
        self.device_role = device_role
        self.tag = tag
        self.sync_vlans = sync_vlans

        # Filter devices based on form input
        device_filter = {}
        if self.devices:
            device_filter["id__in"] = [device.id for device in devices]
        if self.location:
            device_filter["location"] = location
        if self.device_role:
            device_filter["role"] = device_role
        if self.tag:
            device_filter["tags"] = tag
        self.filtered_devices = Device.objects.filter(**device_filter)

        self.job_result.task_kwargs = {
            "debug": debug,
            "ip_address_status": ip_address_status,
            "default_prefix_status": default_prefix_status,
            "location": location,
            "devices": devices,
            "device_role": device_role,
            "tag": tag,
            "sync_vlans": sync_vlans,
        }

        super().run(dryrun, memory_profiling, *args, **kwargs)


class CommandGetterDO(Job):
    """Simple Job to Execute Show Command."""

    class Meta:
        """Meta object boilerplate for onboarding."""

        name = "Command Getter for Device Onboarding"
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = False

    debug = BooleanVar()
    ip_addresses = StringVar()
    port = IntegerVar()
    timeout = IntegerVar()
    secrets_group = ObjectVar(model=SecretsGroup)
    platform = ObjectVar(model=Platform, required=False)

    def run(self, *args, **kwargs):
        """Process onboarding task from ssot-ni job."""
        self.ip_addresses = kwargs["ip_addresses"].replace(" ", "").split(",")
        self.port = kwargs["port"]
        self.timeout = kwargs["timeout"]
        self.secrets_group = kwargs["secrets_group"]
        self.platform = kwargs["platform"]

        # Initiate Nornir instance with empty inventory
        try:
            logger = NornirLogger(self.job_result, log_level=0)
            compiled_results = {}
            with InitNornir(
                runner=NORNIR_SETTINGS.get("runner"),
                logging={"enabled": False},
                inventory={
                    "plugin": "empty-inventory",
                },
            ) as nornir_obj:
                nr_with_processors = nornir_obj.with_processors([ProcessorDO(logger, compiled_results)])
                for entered_ip in self.ip_addresses:
                    single_host_inventory_constructed = _set_inventory(
                        entered_ip, self.platform, self.port, self.secrets_group
                    )
                    nr_with_processors.inventory.hosts.update(single_host_inventory_constructed)
                nr_with_processors.run(task=netmiko_send_commands)
        except Exception as err:  # pylint: disable=broad-exception-caught
            self.logger.error("Error: %s", err)
            return err
        return compiled_results


class CommandGetterNetworkImporter(Job):
    """Simple Job to Execute Show Command."""

    debug = BooleanVar(description="Enable for more verbose logging.")
    namespace = ObjectVar(
        model=Namespace, required=True, description="The namespace for all IP addresses created or updated in the sync."
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
    tag = ObjectVar(
        model=Tag,
        query_params={"content_types": "dcim.device"},
        required=False,
        description="Only update devices with the selected tag.",
    )
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)

    class Meta:
        """Meta object boilerplate for onboarding."""

        name = "Command Getter for Network Importer"
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = False

    def run(self, *args, **kwargs):
        """Process onboarding task from ssot-ni job."""
        try:
            logger = NornirLogger(self.job_result, log_level=0)
            compiled_results = {}
            qs = get_job_filter(kwargs)
            with InitNornir(
                runner=NORNIR_SETTINGS.get("runner"),
                logging={"enabled": False},
                inventory={
                    "plugin": "nautobot-inventory",
                    "options": {
                        "credentials_class": NORNIR_SETTINGS.get("credentials"),
                        "queryset": qs,
                    },
                    # need to figure out how to inject the platform_yaml_data here into data
                },
            ) as nornir_obj:
                # commands = ["show version", "show interfaces", "show vlan", "show interfaces switchport"]
                nr_with_processors = nornir_obj.with_processors([ProcessorDO(logger, compiled_results)])
                nr_with_processors.run(task=netmiko_send_commands)
        except Exception as err:  # pylint: disable=broad-exception-caught
            self.logger.info("Error: %s", err)
            return err
        return compiled_results


jobs = [OnboardingTask, SSOTDeviceOnboarding, SSOTNetworkImporter, CommandGetterDO, CommandGetterNetworkImporter]
register_jobs(*jobs)
