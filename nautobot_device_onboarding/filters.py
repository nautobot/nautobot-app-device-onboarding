"""Filterset classes."""

from nautobot.extras.filters import NautobotFilterSet

from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class DiscoveredGroupFilterSet(NautobotFilterSet):
    """Filterset for DiscoveredGroup."""

    class Meta:
        """Filterset Meta."""

        model = DiscoveredGroup
        fields = [
            "name",
        ]


class DiscoveredIPAddressFilterSet(NautobotFilterSet):
    """Filterset for IPAddress."""

    class Meta:
        """Filterset Meta."""

        model = DiscoveredIPAddress
        fields = ["discovered_group", "ip_address"]


class DiscoveredPortFilterSet(NautobotFilterSet):
    """Filterset for Port."""

    class Meta:
        """Filterset Meta."""

        model = DiscoveredPort
        fields = ["discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl"]
