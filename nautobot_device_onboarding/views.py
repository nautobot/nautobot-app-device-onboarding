"""Model UI Viewset."""

from nautobot.core.views.viewsets import NautobotUIViewSet

from . import filters, tables
from .api import serializers
from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class DiscoveredGroupUIViewSet(NautobotUIViewSet):
    """DiscoveredGroup UI ViewSet."""

    filterset_class = filters.DiscoveredGroupFilterSet
    queryset = DiscoveredGroup.objects.all()
    serializer_class = serializers.DiscoveredGroupSerializer
    table_class = tables.DiscoveredGroupTable


class DiscoveredIPAddressUIViewSet(NautobotUIViewSet):
    """DiscoveredIPAddress UI ViewSet."""

    filterset_class = filters.DiscoveredIPAddressFilterSet
    queryset = DiscoveredIPAddress.objects.all()
    serializer_class = serializers.DiscoveredIPAddressSerializer
    table_class = tables.DiscoveredIPAddressGroupTable


class DiscoveredPortUIViewSet(NautobotUIViewSet):
    """DiscoveredPort UI ViewSet."""

    filterset_class = filters.DiscoveredPortFilterSet
    queryset = DiscoveredPort.objects.all()
    serializer_class = serializers.DiscoveredPortSerializer
    table_class = tables.DiscoveredPortTable
