from nautobot.apps.filters import NautobotFilterSet
from nautobot_device_onboarding.models import DiscoveredDevice

class DiscoveredDeviceFilterSet(NautobotFilterSet):
    
    class Meta:
        model = DiscoveredDevice
        fields = [
            "id",
        ]