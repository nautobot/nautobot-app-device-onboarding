from nautobot.apps.api import NautobotModelViewSet
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot_device_onboarding.api import serializers


class DiscoveredDeviceViewSet(NautobotModelViewSet):
    queryset = DiscoveredDevice.objects.all()
    serializer_class = serializers.DiscoveredDeviceSerializer
    # filterset_class = filters.RackReservationFilterSet
