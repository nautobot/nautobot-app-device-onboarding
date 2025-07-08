import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ToggleColumn
from nautobot_device_onboarding.models import DiscoveredDevice

class DiscoveredDeviceTable(BaseTable):

    pk = ToggleColumn()
    ip_address = tables.Column(
        linkify=lambda record: record.get_absolute_url(), 
        verbose_name="Discovered IP Address",
    )

    class Meta(BaseTable.Meta):
        model = DiscoveredDevice
        fields = (
            "pk",
            "ip_address",
            "hostname",
            "tcp_response",
            "last_successful_tcp_response",
            "ssh_response",
            "last_successful_ssh_response",
            "ssh_port",
            "ssh_credentials",
            "discovered_platform",
        )
        default_columns = (
            "pk",
            "ip_address",
            "hostname",
            "tcp_response",
            "ssh_response",
            "discovered_platform",
        )