"""Forms."""

from nautobot_device_onboarding.models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort
from nautobot.core.forms import DynamicModelChoiceField
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm
from nautobot.ipam.models import IPAddress
class DiscoveredGroupForm(NautobotModelForm):
    class Meta:
        """Boilerplate form Meta data for discovered group."""

        model = DiscoveredGroup
        fields = ("name",)

class DiscoveredIPAddressForm(NautobotModelForm):

    discovered_group = DynamicModelChoiceField(queryset=DiscoveredGroup.objects.all())
    ip_address = DynamicModelChoiceField(queryset=IPAddress.objects.all())
    class Meta:
        """Boilerplate form Meta data for discovered ipaddress."""
        model = DiscoveredIPAddress
        fields = ("discovered_group", "ip_address", "marked_for_onboarding", "extra_info")

class DiscoveredPortForm(NautobotModelForm):
    discovered_ip_address = DynamicModelChoiceField(queryset=DiscoveredIPAddress.objects.all())

    class Meta:
        """Boilerplate form Meta data for discovered ipaddress."""
        model = DiscoveredPort
        fields = ("discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl", "service", "cpe", "scripts")
