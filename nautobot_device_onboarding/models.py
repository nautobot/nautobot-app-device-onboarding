from nautobot.apps.models import PrimaryModel
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from django.db.models import (
    BooleanField,
    DateTimeField,
    ForeignKey,
    SET_NULL,
    CASCADE,
    PositiveIntegerField,
    GenericIPAddressField,
    CharField,
)


class DiscoveredDevice(PrimaryModel):
    ip_address = GenericIPAddressField(unique=True)

    tcp_response = BooleanField(default=False)
    tcp_response_datetime = DateTimeField(blank=True, null=True)

    ssh_response = BooleanField(default=False)
    ssh_response_datetime = DateTimeField(blank=True, null=True)
    ssh_port = PositiveIntegerField(blank=True, null=True)
    ssh_credentials = ForeignKey(to="extras.SecretsGroup", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    ssh_timeout = PositiveIntegerField(default=30, blank=True, null=True)

    device = ForeignKey(to="dcim.Device", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    network_driver = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    hostname = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    serial = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    device_type = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    inventory_status = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)

    def __str__(self):
        if self.hostname:
            return f"{self.hostname} / {self.ip_address}"
        else:
            return f"{self.ip_address}"

