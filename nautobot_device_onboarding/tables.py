"""Tables."""

import json

import django_tables2 as tables
from django.utils.html import format_html

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


class JSONExpandColumn(tables.Column):
    def render(self, value):
        # Convert JSON to a formatted string
        formatted_json = json.dumps(value, indent=2)
        # Return HTML with a hidden JSON blob and a button to toggle its visibility
        return format_html(
            '<div class="json-blob" style="display: none;">{}</div>'
            '<button type="button" class="json-toggle" onclick="toggleJson(this)">Show Extra Info</button>',
            formatted_json
        )


class DiscoveredGroupTable(BaseTable):
    """DiscoverdGroup Table."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(DiscoveredGroup)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = DiscoveredGroup
        fields = ("pk", "name", "actions")
        default_columns = ("pk", "name", "actions")


class DiscoveredIPAddressTable(BaseTable):
    """DiscoveredIPAddress Table."""

    pk = ToggleColumn()
    discovered_group = tables.Column(linkify=True, verbose_name="Discovered Group")
    ip_address = tables.Column(linkify=True)
    marked_for_onboarding = tables.BooleanColumn()
    extra_info = JSONExpandColumn()

    class Meta(BaseTable.Meta):
        """Meta options."""

        model = DiscoveredIPAddress
        fields = ("pk",  "ip_address", "discovered_group", "marked_for_onboarding", "extra_info")
        default_columns = ("pk", "ip_address", "discovered_group", "marked_for_onboarding", "extra_info")
        template = "nautobot_device_onboarding/"


class DiscoveredPortTable(BaseTable):
    discovered_ip_address = tables.Column(linkify=True, verbose_name="Discovered IP Address", accessor="discovered_ip_address.ip_address")
    protocol = tables.Column()
    port_id = tables.Column()
    state = tables.Column()
    reason = tables.Column()
    reason_ttl = tables.Column()

    class Meta(BaseTable.Meta):
        model = DiscoveredPort
        fields = ("discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl")
        default_columns = ("discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl")

