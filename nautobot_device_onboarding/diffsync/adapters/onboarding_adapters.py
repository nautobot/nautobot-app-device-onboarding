"""DiffSync adapters."""

from diffsync import DiffSync
from nautobot_ssot.contrib import NautobotAdapter
from nautobot_device_onboarding.diffsync.models import onboarding_models
import netaddr 

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
mock_data = {
    "10.1.1.8": {
        "hostname": "demo-cisco-xe",
        "serial_number": "9ABUXU580QS",
        "device_type": "CSR1000V",
        "mgmt_ip_address": "10.1.1.8",
    }
}
#######################################
#######################################

class OnboardingNautobotAdapter(NautobotAdapter):
    """Adapter for loading Nautobot data."""

    device_type = onboarding_models.OnboardingDeviceType
    device = onboarding_models.OnboardingDevice
    interface = onboarding_models.OnboardingInterface

    top_level = ["device_type", "device"]

class OnboardingNetworkAdapter(DiffSync):
    """Adapter for loading device data from a network."""

    device_type = onboarding_models.OnboardingDeviceType
    device = onboarding_models.OnboardingDevice
    interface = onboarding_models.OnboardingInterface

    top_level = ["device_type", "device"]

    def __init__(
            self, 
            job: object, 
            sync: object,
            *args, 
            **kwargs
        ):
        """Initialize the NautobotDiffSync."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    def _validate_ip_addresses(self, ip_addresses: list):
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
        """Query devices and load device data into a DiffSync model."""

        # PROVIDE TO JOB: ip4address, port, timeout, secrets_group, platform (optional)
        #TODO: Call onboarding job to query devices

        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device data for {ip_address}")
            onboarding_device = self.device(
                diffsync=self,
                primary_ip4__host=ip_address,
                location__name=self.job.location.name,
                role__name=self.job.role.name,
                device_type__model=mock_data[ip_address]["device_type"],
            )
            self.add(onboarding_device)

    def load_device_types(self):
        """Query devices and load device type data into a DiffSync model."""
        for ip_address in mock_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device_type data for {ip_address}")
            onboarding_device_type = self.device_type(
                diffsync=self,
                model = mock_data[ip_address]["device_type"]
            )
            self.add(onboarding_device_type)
            
    def load(self):
        """Load device data."""
        self._validate_ip_addresses(self.job.ip_addresses)
        self.load_devices()
        self.load_device_types()
