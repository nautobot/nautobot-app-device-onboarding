"""Models to represent discovered ip address instances by NetworkScanNMAP Job."""

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import JSONArrayField, OrganizationalModel, PrimaryModel
from nautobot.core.choices import ChoiceSet


class ProtocolTypeChoices(ChoiceSet):
    """Protocol Type Choices."""

    TCP = "tcp"
    UDP = "udp"

    CHOICES = (
        (TCP, "TCP"),
        (UDP, "UDP"),
    )


class PortStateChoices(ChoiceSet):
    """Port State Choices."""

    STATE_OPEN = "open"
    STATE_CLOSED = "closed"

    CHOICES = (
        (STATE_OPEN, "Open"),
        (STATE_CLOSED, "Closed"),
    )


class DiscoveredGroup(OrganizationalModel):
    """Group of discovered ip addresses by the NetworkScanNMAP Job."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The name of the discovered group.", unique=True)


class DiscoveredIPAddress(PrimaryModel):
    """IP Addresses discovered in the given subnet by the NetworkScanNMAP Job."""

    discovered_group = models.ForeignKey(to=DiscoveredGroup, on_delete=models.PROTECT)
    ip_address = models.ForeignKey("ipam.IPAddress", on_delete=models.CASCADE, null=True)
    marked_for_onboarding = models.BooleanField(
        default=False,
        verbose_name="Marked for onboarding",
        help_text="IP Addresses that are ready for onboarding",
    )
    extra_info = models.JSONField(encoder=DjangoJSONEncoder, blank=True, default=dict)


class DiscoveredPort(OrganizationalModel):
    """Port discovered on the discovered_ip_address."""

    discovered_ip_address = models.ForeignKey(to=DiscoveredIPAddress, on_delete=models.PROTECT)
    protocol = models.CharField(choices=ProtocolTypeChoices, max_length=CHARFIELD_MAX_LENGTH, help_text="TCP/UDP")
    port_id = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="Port ID")
    state = models.CharField(choices=PortStateChoices, max_length=CHARFIELD_MAX_LENGTH, help_text="open/closed")
    reason = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="The reason why the port is open or closed")
    reason_ttl = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    service = models.JSONField(encoder=DjangoJSONEncoder, blank=True, default=dict)
    cpe = JSONArrayField(base_field=models.CharField(max_length=CHARFIELD_MAX_LENGTH))
    scripts = JSONArrayField(base_field=models.CharField(max_length=CHARFIELD_MAX_LENGTH))
