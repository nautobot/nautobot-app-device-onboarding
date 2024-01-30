"""DiffSync adapters."""

import time

import diffsync
import netaddr
from nautobot.apps.choices import JobResultStatusChoices
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform
from nautobot.extras.models import Job, JobResult

from nautobot_device_onboarding.diffsync.models import onboarding_models

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
mock_data = {
    "10.1.1.8": {
        "hostname": "demo-cisco-xe1",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet20",
        "manufacturer": "Cisco",
        "platform": "IOS-test",
        "network_driver": "cisco_ios",
        "mask_length": 16,
    },
    "10.1.1.9": {
        "hostname": "demo-cisco-xe2",
        "serial": "9ABUXU5882222",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet16",
        "manufacturer": "Cisco",
        "platform": "IOS",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
}
#######################################
#######################################


class OnboardingNautobotAdapter(diffsync.DiffSync):
    """Adapter for loading Nautobot data."""

    manufacturer = onboarding_models.OnboardingManufacturer
    platform = onboarding_models.OnboardingPlatform
    device = onboarding_models.OnboardingDevice
    device_type = onboarding_models.OnboardingDeviceType

    top_level = ["manufacturer", "platform", "device_type", "device"]

    def __init__(self, job, sync, *args, **kwargs):
        """Initialize the OnboardingNautobotAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    def load_manufacturers(self):
        """Load manufacturer data from Nautobot."""
        for manufacturer in Manufacturer.objects.all():
            if self.job.debug:
                self.job.logger.debug("Loading Manufacturer data from Nautobot...")
            onboarding_manufacturer = self.manufacturer(diffsync=self, name=manufacturer.name)
            self.add(onboarding_manufacturer)
            if self.job.debug:
                self.job.logger.debug(f"Manufacturer: {manufacturer.name} loaded.")

    def load_platforms(self):
        """Load platform data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading Platform data from Nautobot...")
        for platform in Platform.objects.all():
            onboarding_platform = self.platform(
                diffsync=self,
                name=platform.name,
                network_driver=platform.network_driver if platform.network_driver else "",
                manufacturer__name=platform.manufacturer.name if platform.manufacturer else None,
            )  # type: ignore
            self.add(onboarding_platform)
            if self.job.debug:
                self.job.logger.debug(f"Platform: {platform.name} loaded.")

    def load_device_types(self):
        """Load device type data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading DeviceType data from Nautobot...")
        for device_type in DeviceType.objects.all():
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=device_type.model,
                part_number=device_type.model,
                manufacturer__name=device_type.manufacturer.name,
            )  # type: ignore
            self.add(onboarding_device_type)
            if self.job.debug:
                self.job.logger.debug(f"DeviceType: {device_type.model} loaded.")

    def load_devices(self):
        """Load device data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading Device data from Nautobot...")

        # for device in Device.objects.filter(primary_ip4__host__in=self.job.ip_addresses):
        for device in Device.objects.all():
            interface_list = list()
            # Only interfaces with the device's primeary ip should be considered for diff calculations
            for interface in device.interfaces.all():
                if device.primary_ip4 in interface.ip_addresses.all():
                    interface_list.append(interface.name)

            onboarding_device = self.device(
                diffsync=self,
                device_type__model=device.device_type.model,
                location__name=device.location.name,
                name=device.name,
                platform__name=device.platform.name if device.platform else "",
                primary_ip4__host=device.primary_ip4.host if device.primary_ip4 else "",
                primary_ip4__status__name=device.primary_ip4.status.name if device.primary_ip4 else "",
                role__name=device.role.name,
                status__name=device.status.name,
                secrets_group__name=device.secrets_group.name if device.secrets_group else "",
                interfaces=interface_list,
                mask_length=device.primary_ip4.mask_length if device.primary_ip4 else None,
                serial=device.serial,
            )  # type: ignore
            self.add(onboarding_device)
            if self.job.debug:
                self.job.logger.debug(f"Device: {device.name} loaded.")

    def load(self):
        """Load nautobot data."""
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()


class OnboardingNetworkAdapter(diffsync.DiffSync):
    """Adapter for loading device data from a network."""

    device_data = None

    manufacturer = onboarding_models.OnboardingManufacturer
    platform = onboarding_models.OnboardingPlatform
    device = onboarding_models.OnboardingDevice
    device_type = onboarding_models.OnboardingDeviceType

    top_level = ["manufacturer", "platform", "device_type", "device"]

    def __init__(self, job, sync, *args, **kwargs):
        """Initialize the OnboardingNetworkAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    def _validate_ip_addresses(self, ip_addresses):
        """Validate the format of each IP Address in a list of IP Addresses."""
        # Validate IP Addresses
        validation_successful = True
        for ip_address in ip_addresses:
            try:
                netaddr.IPAddress(ip_address)
            except netaddr.AddrFormatError:
                self.job.logger.error(f"[{ip_address}] is not a valid IP Address ")
                validation_successful = False
        if validation_successful:
            return True
        else:
            raise netaddr.AddrConversionError

    def _handle_failed_connections(self, device_data):
        """
        Handle result data from failed device connections.

        If a device fails to return expected data, log the result
        and remove it from the data to be loaded into the diffsync store.
        """
        failed_ip_addresses = []

        for ip_address in device_data:
            if device_data[ip_address].get("failed"):
                self.job.logger.error(f"Failed to connect to {ip_address}. This device will not be onboarded.")
                if self.job.debug:
                    self.job.logger.debug(device_data[ip_address].get("subtask_result"))
                failed_ip_addresses.append(ip_address)
        for ip_address in failed_ip_addresses:
            del device_data[ip_address]
        self.device_data = device_data

    def execute_command_getter(self):
        """Start the CommandGetterDO job to query devices for data."""
        if self.job.platform:
            if not self.job.platform.network_driver:
                self.job.logger.error(
                    f"The selected platform, {self.job.platform} "
                    "does not have a network driver, please update the Platform."
                )
                raise Exception("Platform.network_driver missing")

        command_getter_job = Job.objects.get(name="Command Getter for Device Onboarding")
        job_kwargs = self.job.prepare_job_kwargs(self.job.job_result.task_kwargs)
        kwargs = self.job.serialize_data(job_kwargs)
        result = JobResult.enqueue_job(
            job_model=command_getter_job, user=self.job.user, celery_kwargs=self.job.job_result.celery_kwargs, **kwargs
        )
        while True:
            if result.status not in JobResultStatusChoices.READY_STATES:
                time.sleep(5)
                result.refresh_from_db()
            else:
                break
        if self.job.debug:
            self.job.logger.debug(f"Command Getter Job Result: {result.result}")
        self._handle_failed_connections(device_data=result.result)

    def load_manufacturers(self):
        """Load manufacturer data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading manufacturer data for {ip_address}")
            onboarding_manufacturer = self.manufacturer(
                diffsync=self,
                name=self.device_data[ip_address]["manufacturer"],
            )  # type: ignore
            try:
                self.add(onboarding_manufacturer)
            except diffsync.ObjectAlreadyExists:
                pass

    def load_platforms(self):
        """Load platform data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading platform data for {ip_address}")
            onboarding_platform = self.platform(
                diffsync=self,
                name=self.device_data[ip_address]["platform"],
                manufacturer__name=self.device_data[ip_address]["manufacturer"],
                network_driver=self.device_data[ip_address]["network_driver"],
            )  # type: ignore
            try:
                self.add(onboarding_platform)
            except diffsync.ObjectAlreadyExists:
                pass

    def load_device_types(self):
        """Load device type data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device_type data for {ip_address}")
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=self.device_data[ip_address]["device_type"],
                part_number=self.device_data[ip_address]["device_type"],
                manufacturer__name=self.device_data[ip_address]["manufacturer"],
            )  # type: ignore
            try:
                self.add(onboarding_device_type)
            except diffsync.ObjectAlreadyExists:
                pass

    def load_devices(self):
        """Load device data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device data for {ip_address}")
            onboarding_device = self.device(
                diffsync=self,
                device_type__model=self.device_data[ip_address]["device_type"],
                location__name=self.job.location.name,
                name=self.device_data[ip_address]["hostname"],
                platform__name=self.device_data[ip_address]["platform"],
                primary_ip4__host=ip_address,
                primary_ip4__status__name=self.job.ip_address_status.name,
                role__name=self.job.device_role.name,
                status__name=self.job.device_status.name,
                secrets_group__name=self.job.secrets_group.name,
                interfaces=[self.device_data[ip_address]["mgmt_interface"]],
                mask_length=self.device_data[ip_address]["mask_length"],
                serial=self.device_data[ip_address]["serial"],
            )  # type: ignore
            try:
                self.add(onboarding_device)
                if self.job.debug:
                    self.job.logger.debug(f"Device: {self.device_data[ip_address]['hostname']} loaded.")
            except diffsync.ObjectAlreadyExists:
                self.job.logger.error(
                    f"Device: {self.device_data[ip_address]['hostname']} has already been loaded! "
                    f"Duplicate devices will not be synced. "
                    f"[Serial Number: {self.device_data[ip_address]['serial']}, "
                    f"IP Address: {ip_address}]"
                )

    def load(self):
        """Load network data."""
        self._validate_ip_addresses(self.job.ip_addresses)
        self.execute_command_getter()
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()
