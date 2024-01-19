"""DiffSync adapters."""

import netaddr
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device
from nautobot_device_onboarding.diffsync.models import onboarding_models
from nautobot_ssot.contrib import NautobotAdapter

from diffsync import DiffSync

from nautobot.extras.models.jobs import Job as JobModel

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
mock_data = {
    "10.1.1.8": {
        "hostname": "demo-cisco-xe",
        "serial_number": "9ABUXU580QS",
        "device_type": "CSR1000V2",
        "mgmt_ip_address": "10.1.1.8",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "IOS",
        "network_driver": "cisco_ios",
        "prefix": "10.0.0.0", # this is the network field on the Prefix model
        "prefix_length": 8,
        "mask_length": 24,
    }
}
#######################################
#######################################


class OnboardingNautobotAdapter(NautobotAdapter):
    """Adapter for loading Nautobot data."""

    manufacturer = onboarding_models.OnboardingManufacturer
    platform = onboarding_models.OnboardingPlatform
    device = onboarding_models.OnboardingDevice
    device_type = onboarding_models.OnboardingDeviceType
    interface = onboarding_models.OnboardingInterface
    ip_address = onboarding_models.OnboardingIPAddress

    top_level = ["manufacturer", "platform", "device_type", "device"]

    def _load_objects(self, diffsync_model):
        """Given a diffsync model class, load a list of models from the database and return them."""
        parameter_names = self._get_parameter_names(diffsync_model)
        if diffsync_model._model == Device:
            for database_object in diffsync_model._get_queryset(filter=self.job.ip_addresses):
                self._load_single_object(database_object, diffsync_model, parameter_names)
        else:
            for database_object in diffsync_model._get_queryset():
                self._load_single_object(database_object, diffsync_model, parameter_names)


class OnboardingNetworkAdapter(DiffSync):
    """Adapter for loading device data from a network."""

    manufacturer = onboarding_models.OnboardingManufacturer
    platform = onboarding_models.OnboardingPlatform
    device = onboarding_models.OnboardingDevice
    device_type = onboarding_models.OnboardingDeviceType
    interface = onboarding_models.OnboardingInterface
    ip_address = onboarding_models.OnboardingIPAddress

    top_level = ["manufacturer", "platform", "device_type", "device"]

    def __init__(self, job, sync, *args, **kwargs):
        """Initialize the NautobotDiffSync."""
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

    def load_devices(self):
        """Load device data into a DiffSync model."""

        # PROVIDE TO JOB: ip4address, port, timeout, secrets_group, platform (optional)
        # TODO: CHECK FOR FAILED CONNECTIONS AND DO NOT LOAD DATA, LOG FAILED IPs
        # TODO: Call onboarding job to query devices

        command_getter_job = JobModel.objects.get(name="Command Getter for Device Onboarding").job_task
        result = command_getter_job.s()
        result.apply_async(args=self.job.job_result.task_args, kwargs=self.job.job_result.task_kwargs, **self.job.job_result.celery_kwargs)


        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device data for {ip_address}")
            onboarding_device = self.device(
                diffsync=self,
                device_type__model=mock_data[ip_address]["device_type"],
                location__name=self.job.location.name,
                name=mock_data[ip_address]["hostname"],
                platform__name=mock_data[ip_address]["platform"],
                primary_ip4__host=ip_address,
                role__name=self.job.device_role.name,
                status__name=self.job.device_status.name,
                secrets_group__name=self.job.secrets_group.name,
            )
            self.add(onboarding_device)
            self.load_interface(onboarding_device, mock_data, ip_address)

    def load_device_types(self):
        """Load device type data into a DiffSync model."""
        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device_type data for {ip_address}")
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=mock_data[ip_address]["device_type"],
                manufacturer__name=mock_data[ip_address]["manufacturer"],
            )
            self.add(onboarding_device_type)

    def load_interface(self, onboarding_device, device_data, ip_address):
        """Load interface data into a DiffSync model."""
        if self.job.debug:
            self.job.logger.debug(f"loading interface data for {ip_address}")
        onboarding_interface = self.interface(
            diffsync=self,
            name=device_data[ip_address]["mgmt_interface"],
            device__name=device_data[ip_address]["hostname"],
            status__name=self.job.interface_status.name,
            type=InterfaceTypeChoices.TYPE_OTHER,
            mgmt_only=self.job.management_only_interface,
        )
        self.add(onboarding_interface)
        onboarding_device.add_child(onboarding_interface)
        self.load_ip_address(onboarding_interface, mock_data, ip_address)

    def load_ip_address(self, onboarding_interface, device_data, ip_address):
        """Load ip address data into a DiffSync model."""
        if self.job.debug:
            self.job.logger.debug(f"loading ip address data for {ip_address}")
        onboarding_ip_address = self.ip_address(
            diffsync=self,
            parent__namespace__name=self.job.namespace.name,
            parent__network=device_data[ip_address]["prefix"],
            parent__prefix_length=device_data[ip_address]["prefix_length"],
            host=ip_address,
            mask_length=device_data[ip_address]["mask_length"],
        )
        self.add(onboarding_ip_address)
        onboarding_interface.add_child(onboarding_ip_address)

    def load_manufacturers(self):
        """Load manufacturer data into a DiffSync model."""
        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading manufacturer data for {ip_address}")
            onboarding_manufacturer = self.manufacturer(
                diffsync=self,
                name=mock_data[ip_address]["manufacturer"],
            )
            self.add(onboarding_manufacturer)

    def load_platforms(self):
        """Load platform data into a DiffSync model."""
        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading platform data for {ip_address}")
            onboarding_platform = self.platform(
                diffsync=self,
                name=mock_data[ip_address]["platform"],
                manufacturer__name=mock_data[ip_address]["manufacturer"],
                network_driver=mock_data[ip_address]["network_driver"],
            )
            self.add(onboarding_platform)

    def load(self):
        """Load device data."""
        self._validate_ip_addresses(self.job.ip_addresses)
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()
