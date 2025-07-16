import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ToggleColumn
from nautobot_device_onboarding.models import DiscoveredDevice


class DiscoveredDeviceTable(BaseTable):
    pk = ToggleColumn()
    ip_address = tables.Column(
        linkify=lambda record: record.get_absolute_url(),
        verbose_name="IP Address",
    )
    device = tables.Column(
        linkify=lambda record: record.device.get_absolute_url() if record.device else None,
        verbose_name="Device",
    )

    class Meta(BaseTable.Meta):
        model = DiscoveredDevice
        fields = (
            "pk",
            "ip_address",
            "hostname",
            "tcp_response",
            "tcp_response_datetime",
            "ssh_response",
            "ssh_response_datetime",
            "ssh_port",
            "ssh_credentials",
            "network_driver",
            "device",
            "serial",
            "device_type",
        )
        default_columns = (
            "pk",
            "ip_address",
            "hostname",
            "tcp_response",
            "ssh_response",
            "network_driver",
        )
