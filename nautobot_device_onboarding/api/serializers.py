"""Serializers."""

from nautobot.core.api import NautobotModelSerializer

from nautobot_device_onboarding.models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class DiscoveredGroupSerializer(NautobotModelSerializer):
    """Serializer for DiscoveredGroup."""

    class Meta:
        """Model Meta."""

        model = DiscoveredGroup
        fields = "__all__"


class DiscoveredIPAddressSerializer(NautobotModelSerializer):
    """Serializer for DiscoveredIPAddress."""

    class Meta:
        """Model Meta."""

        model = DiscoveredIPAddress
        fields = "__all__"


class DiscoveredPortSerializer(NautobotModelSerializer):
    """Serializer for DiscoveredPort."""

    class Meta:
        """Model Meta."""

        model = DiscoveredPort
        fields = "__all__"
