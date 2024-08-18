"""Filterset classes."""

from nautobot.core.filters import SearchFilter
from nautobot.extras.filters import NautobotFilterSet

from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class DiscoveredGroupFilterSet(NautobotFilterSet):
    """Filterset for DiscoveredGroup."""
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        },
    )

    class Meta:
        """Filterset Meta."""

        model = DiscoveredGroup
        fields = [
            "name",
        ]


class DiscoveredIPAddressFilterSet(NautobotFilterSet):
    """Filterset for IPAddress."""
    q = SearchFilter(
        filter_predicates={
            "discovered_group__name": "icontains",
        },
    )
    class Meta:
        """Filterset Meta."""

        model = DiscoveredIPAddress
        fields = ["discovered_group", "ip_address"]


class DiscoveredPortFilterSet(NautobotFilterSet):
    """Filterset for Port."""
    q = SearchFilter(
        filter_predicates={
            "discovered_ip_address__discovered_group__name": "icontains",
        },
    )

    class Meta:
        """Filterset Meta."""

        model = DiscoveredPort
        fields = ["discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl"]
