from nautobot.apps.models import PrimaryModel
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from django.db.models import BooleanField, DateTimeField, ForeignKey, SET_NULL, CASCADE, PositiveIntegerField

class DiscoveredDevice(PrimaryModel):
    ip_address = ForeignKey(to="ipam.IPAddress", on_delete=CASCADE, related_name="+", blank=True, null=True, unique=True)

    tcp_response = BooleanField(default=False)
    last_successful_tcp_response = DateTimeField(blank=True, null=True)

    ssh_response = BooleanField(default=False)
    last_successful_ssh_response = DateTimeField(blank=True, null=True)
    ssh_port = PositiveIntegerField(blank=True, null=True)
    ssh_credentials = ForeignKey(to="extras.SecretsGroup", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    discovered_platform = ForeignKey(to="dcim.platform", on_delete=SET_NULL, related_name="+", blank=True, null=True)

    location = ForeignKey(to="dcim.Location", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    device_role = ForeignKey(to="extras.Role", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    device_status = ForeignKey(to="extras.Status", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    interface_status = ForeignKey(to="extras.Status", on_delete=SET_NULL, related_name="+", blank=True, null=True)

# TODO: soft mapping to device