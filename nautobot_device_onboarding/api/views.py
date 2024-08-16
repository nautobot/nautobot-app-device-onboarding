"""API Viewsets."""

from nautobot.extras.api.views import NautobotModelViewSet

from nautobot_device_onboarding import filters
from nautobot_device_onboarding.models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort

from . import serializers


class DiscoveredGroupViewSet(NautobotModelViewSet):
    """API ViewSet for DiscoveredGroup."""

    queryset = DiscoveredGroup.objects.all()
    serializer_class = serializers.DiscoveredGroupSerializer
    filterset_class = filters.DiscoveredGroupFilterSet


class DiscoveredIPAddressViewSet(NautobotModelViewSet):
    """API ViewSet for DiscoveredIPAddress."""

    queryset = DiscoveredIPAddress.objects.all()
    serializer_class = serializers.DiscoveredIPAddressSerializer
    filterset_class = filters.DiscoveredIPAddressFilterSet


class DiscoveredPortViewSet(NautobotModelViewSet):
    """API ViewSet for DiscoveredPort."""

    queryset = DiscoveredPort.objects.all()
    serializer_class = serializers.DiscoveredPortSerializer
    filterset_class = filters.DiscoveredPortFilterSet
