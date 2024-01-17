"""DiffSync adapters."""

from diffsync import DiffSync
from nautobot_ssot.contrib import NautobotAdapter
from nautobot_device_onboarding.diffsync.models import onboarding_models


class OnboardingNautobotAdapter(NautobotAdapter):
    """Adapter for loading Nautobot data."""

    device_type = onboarding_models.OnboardingDeviceType
    device = onboarding_models.OnboardingDevice

    top_level = ["device_type", "device"]

class OnboardingNetworkAdapter(DiffSync):
    """Adapter for loading device data from a network."""

    def __init__(self, *args, job, sync, site_filter=None, **kwargs):
        """Initialize the NautobotDiffSync."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.site_filter = site_filter

    def load_devices(self):
        """Query devices and load data into a Diffsync model."""
        
        for ip_address in self.job.ip_addresses:
            #TODO: Call onboarding job to query devices
            self.job.logger.info(f"Attempting to load data from {ip_address}")
            
    def load(self):
        """Load device data."""
        self.load_devices()
        
