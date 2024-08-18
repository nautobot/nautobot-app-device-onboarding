"""Model UI Viewset."""

from nautobot.core.views import generic
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.core.views.generic import ObjectView

from . import filters, tables
from .api import serializers
from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class DiscoveredGroupUIViewSet(NautobotUIViewSet):
    """DiscoveredGroup UI ViewSet."""

    filterset_class = filters.DiscoveredGroupFilterSet
    queryset = DiscoveredGroup.objects.all()
    serializer_class = serializers.DiscoveredGroupSerializer
    table_class = tables.DiscoveredGroupTable


class DiscoveredGroupView(ObjectView):
    """Detail view for a DiscoveredGroup."""

    queryset = DiscoveredGroup.objects.all()
    model = DiscoveredGroup
    template_name = "nautobot_device_onboarding/discoveredgroup_detail.html"


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
