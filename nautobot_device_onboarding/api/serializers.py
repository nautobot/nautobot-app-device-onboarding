from nautobot.apps.api import NautobotModelSerializer
from nautobot_device_onboarding.models import DiscoveredDevice


class DiscoveredDeviceSerializer(NautobotModelSerializer):
    class Meta:
        model = DiscoveredDevice
        fields = [
            "ip_address",
            "tcp_response",
        ]
