"""Device Onboarding Jobs."""
from diffsync.enum import DiffSyncFlags
from django.conf import settings
from django.templatetags.static import static
from nautobot.apps.jobs import BooleanVar, IntegerVar, Job, ObjectVar, StringVar
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import DeviceType, Location, Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Role, SecretsGroup, SecretsGroupAssociation, Status
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
from nautobot_device_onboarding.utils.inventory_creator import _set_inventory
from nautobot_ssot.jobs.base import DataSource
from nornir import InitNornir
from nornir.core.inventory import ConnectionOptions, Defaults, Groups, Host, Hosts, Inventory
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

InventoryPluginRegister.register("empty-inventory", EmptyInventory)

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


name = "Device Onboarding/Network Importer"


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

    class Meta:  # pylint: disable=too-few-public-methods
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
            optional_args=self.platform.napalm_args
            if self.platform and self.platform.napalm_args
            else settings.NAPALM_ARGS,
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


class SSOTDeviceOnboarding(DataSource):
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
        description="Assigned Location for the onboarded device(s)",
    )
    namespace = ObjectVar(model=Namespace, description="Namespace ip addresses belong to.")
    ip_addresses = StringVar(
        description="IP Address of the device to onboard, specify in a comma separated list for multiple devices.",
        label="IPv4 Addresses",
    )
    management_only_interface = BooleanVar(
        default=False,
        label="Set Management Only",
        description="If True, interfaces that are created or updated will be set to management only. If False, the interface will be set to not be management only.",
    )
    device_role = ObjectVar(
        model=Role,
        query_params={"content_types": "dcim.device"},
        required=True,
        description="Role to be applied to all onboarded devices",
    )
    device_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.device"},
        required=True,
        description="Status to be applied to all onboarded devices",
    )
    interface_status = ObjectVar(
        model=Status,
        query_params={"content_types": "dcim.interface"},
        required=True,
        description="Status to be applied to all onboarded device interfaces",
    )
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)
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

    def run(self, dryrun, memory_profiling, *args, **kwargs):  # pylint:disable=arguments-differ
        """Run sync."""

        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.debug = kwargs["debug"]
        self.location = kwargs["location"]
        self.namespace = kwargs["namespace"]
        self.ip_addresses = kwargs["ip_addresses"].replace(" ", "").split(",")
        self.management_only_interface = kwargs["management_only_interface"]
        self.device_role = kwargs["device_role"]
        self.device_status = kwargs["device_status"]
        self.interface_status = kwargs["interface_status"]
        self.port = kwargs["port"]
        self.timeout = kwargs["timeout"]
        self.secrets_group = kwargs["secrets_group"]
        self.platform = kwargs["platform"]
        super().run(dryrun, memory_profiling, *args, **kwargs)


class SSOTNetworkImporter(DataSource):
    """Job syncing extended device attributes into Nautobot."""

    debug = BooleanVar(description="Enable for more verbose logging.")

    class Meta:
        """Metadata about this Job."""

        name = "Sync Network Data"
        description = (
            "Synchronize extended device attribute information into Nautobot; "
            "including Interfaces, IPAddresses, Prefixes, Vlans and Cables."
        )


class CommandGetterDO(Job):
    """Simple Job to Execute Show Command."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta object boilerplate for onboarding."""

        name = "Command Getter for Device Onboarding"
        description = "Login to a device(s) and run commands."
        has_sensitive_variables = False
        hidden = False

    def __init__(self, *args, **kwargs):
        """Initialize Command Getter Job."""
        self.username = None
        self.password = None
        self.secret = None
        self.secrets_group = None
        self.ip4address = None
        self.platform = None
        self.port = None
        self.timeout = None
        super().__init__(*args, **kwargs)

    def run(self):
        mock_job_data = {
            "ip4address": "174.51.52.76,10.1.1.1",
            "platform": "cisco_ios",
            "secrets_group": SecretsGroup.objects.get(name="Cisco Devices"),
            "port": 8922,
            "timeout": 30,
        }

        """Process onboarding task from ssot-ni job."""
        self.ip4address = mock_job_data["ip4address"]
        self.secrets_group = mock_job_data["secrets_group"]
        self.platform = mock_job_data["platform"]
        self.port = mock_job_data["port"]
        self.timeout = mock_job_data["timeout"]

        # Initiate Nornir instance with empty inventory
        try:
            with InitNornir(inventory={"plugin": "empty-inventory"}) as nr:
                ip_address = mock_job_data["ip4address"].split(",")
                self.platform = mock_job_data.get("platform", None)
                inventory_constructed = _set_inventory(ip_address, self.platform, self.port, self.secrets_group)
                nr.inventory.hosts.update(inventory_constructed)
                self.logger.info(nr.inventory.hosts)

                self.logger.info("Inventory built for %s devices", len(ip_address))

                results = nr.run(task=netmiko_send_commands)

                for agg_result in results:
                    for r in results[agg_result]:
                        self.logger.info("host: %s", r.host)
                        self.logger.info("result: %s", r.result)

        except Exception as err:
            self.logger.info("Error: %s", err)
            return err
        # return {
        #         "10.1.1.8": {
        #             "command_output_results": True,
        #             "hostname": "demo-cisco-xe",
        #             "serial_number": "9ABUXU580QS",
        #             "device_type": "CSR1000V2",
        #             "mgmt_ip_address": "10.1.1.8",
        #             "mgmt_interface": "GigabitEthernet1",
        #             "manufacturer": "Cisco",
        #             "platform": "IOS",
        #             "network_driver": "cisco_ios",
        #             "prefix": "10.0.0.0", # this is the network field on the Prefix model
        #             "prefix_length": 8,
        #             "mask_length": 24,
        #         },
        #         "10.1.1.9": {
        #             "command_output_results": False,
        #         }
        #     }
        return {"additonal_data": "This worked"}


jobs = [OnboardingTask, SSOTDeviceOnboarding, CommandGetterDO]
register_jobs(*jobs)
