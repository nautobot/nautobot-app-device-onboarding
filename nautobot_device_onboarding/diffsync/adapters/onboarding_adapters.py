"""DiffSync adapters."""

import netaddr
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform
from nautobot.extras.models.jobs import Job as JobModel
from nautobot_device_onboarding.diffsync.models import onboarding_models

from diffsync import DiffSync

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
# mock_data = {
#     "10.1.1.8": {
#         "hostname": "demo-cisco-xe",
#         "serial_number": "9ABUXU580QS",
#         "device_type": "CSR1000V2",
#         "mgmt_interface": "GigabitEthernet3",
#         "manufacturer": "Cisco",
#         "platform": "IOS",
#         "network_driver": "cisco_ios",
#         "mask_length": 24,
#     }
# }
#######################################
#######################################


class OnboardingNautobotAdapter(DiffSync):
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
        for manufacturer in Manufacturer.objects.all():
            if self.job.debug:
                self.job.logger.debug(f"Loading Manufacturer data from Nautobot...")
            onboarding_manufacturer = self.manufacturer(diffsync=self, name=manufacturer.name)
            self.add(onboarding_manufacturer)
            if self.job.debug:
                self.job.logger.debug(f"Manufacturer: {manufacturer.name} loaded.")

    def load_platforms(self):
        if self.job.debug:
            self.job.logger.debug(f"Loading Platform data from Nautobot...")
        for platform in Platform.objects.all():
            onboarding_platform = self.platform(
                diffsync=self,
                name=platform.name,
                network_driver=platform.network_driver,
                manufacturer__name=platform.manufacturer.name,
            )
            self.add(onboarding_platform)
            if self.job.debug:
                self.job.logger.debug(f"Platform: {platform.name} loaded.")

    def load_device_types(self):
        if self.job.debug:
            self.job.logger.debug(f"Loading DeviceType data from Nautobot...")
        for device_type in DeviceType.objects.all():
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=device_type.model,
                manufacturer__name=device_type.manufacturer.name,
            )
            self.add(onboarding_device_type)
            if self.job.debug:
                self.job.logger.debug(f"DeviceType: {device_type.model} loaded.")

    def load_devices(self):
        if self.job.debug:
            self.job.logger.debug(f"Loading Device data from Nautobot...")

        for device in Device.objects.filter(primary_ip4__host__in=self.job.ip_addresses):
            interface_list = list()
            for interface in device.interfaces.all():
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
                mask_length=device.primary_ip4.mask_length if device.primary_ip4 else "",
            )
            self.add(onboarding_device)
            if self.job.debug:
                self.job.logger.debug(f"Platform: {device.name} loaded.")

    def load(self):
        """Load nautobot data."""
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()


class OnboardingNetworkAdapter(DiffSync):
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

    def execute_command_getter(self):
        command_getter_job = JobModel.objects.get(name="Command Getter for Device Onboarding").job_task
        result = command_getter_job.s()
        result.apply_async(
            args=self.job.job_result.task_args,
            kwargs=self.job.job_result.task_kwargs,
            **self.job.job_result.celery_kwargs,
        )
        self.device_data = result

    def load_devices(self):
        """Load device data into a DiffSync model."""

        # PROVIDE TO JOB: ip4address, port, timeout, secrets_group, platform (optional)
        # TODO: CHECK FOR FAILED CONNECTIONS AND DO NOT LOAD DATA, LOG FAILED IPs

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
            )
            self.add(onboarding_device)

    def load_device_types(self):
        """Load device type data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device_type data for {ip_address}")
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=self.device_data[ip_address]["device_type"],
                manufacturer__name=self.device_data[ip_address]["manufacturer"],
            )
            self.add(onboarding_device_type)

    def load_manufacturers(self):
        """Load manufacturer data into a DiffSync model."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading manufacturer data for {ip_address}")
            onboarding_manufacturer = self.manufacturer(
                diffsync=self,
                name=self.device_data[ip_address]["manufacturer"],
            )
            self.add(onboarding_manufacturer)

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
            )
            self.add(onboarding_platform)


    def load(self):
        """Load network data."""
        self._validate_ip_addresses(self.job.ip_addresses)
        self.execute_command_getter()
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()
