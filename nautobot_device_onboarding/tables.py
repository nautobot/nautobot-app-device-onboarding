import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ToggleColumn
from nautobot_device_onboarding.models import DiscoveredDevice
from django.utils.timesince import timesince
from django.utils.timezone import now

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

    def render_ssh_response_datetime(self, value):
        if not value:
            return "-"

        delta = now() - value

        if delta.total_seconds() < 60:
            return "Now"
        elif delta.days == 0 and delta.seconds < 3600:
            hours = delta.seconds // 3600
            return f"{delta.seconds // 60} minutes ago"
        elif delta.days == 0:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days < 30:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    class Meta(BaseTable.Meta):
        model = DiscoveredDevice
        fields = (
            "pk",
            "ip_address",
            "hostname",
            # "tcp_response",
            # "tcp_response_datetime",
            "ssh_response",
            "ssh_response_datetime",
            "ssh_port",
            "ssh_credentials",
            "network_driver",
            "device",
            "serial",
            "device_type",
            "ssh_issue",
        )
        default_columns = (
            "pk",
            "ip_address",
            "hostname",
            # "tcp_response",
            "ssh_response",
            "ssh_response_datetime",
            "device_type",
            "serial",
            "network_driver",
            "ssh_issue",
        )
