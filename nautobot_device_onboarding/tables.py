"""Tables."""

import json

import django_tables2 as tables
from django.utils.html import format_html
from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
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
            formatted_json,
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
    """DiscoverdIPAddress Table."""

    pk = ToggleColumn()
    name = tables.TemplateColumn(
        template_code="""<a href="{% url 'plugins:nautobot_device_onboarding:discoveredipaddress' pk=record.pk %}">{{record}}</a>"""
    )
    discovered_group = tables.Column(linkify=True)
    ip_address = tables.Column(linkify=True)
    marked_for_onboarding = BooleanColumn()
    extra_info = JSONExpandColumn()

    class Meta(BaseTable.Meta):
        """Meta."""

        model = DiscoveredIPAddress
        fields = ("pk", "name", "discovered_group", "ip_address", "marked_for_onboarding", "extra_info")
        default_columns = ("pk", "name", "discovered_group", "ip_address", "marked_for_onboarding", "extra_info")


class DiscoveredPortTable(BaseTable):
    """DiscoverdPort Table."""

    pk = ToggleColumn()
    port_id = tables.TemplateColumn(
        template_code="""<a href="{% url 'plugins:nautobot_device_onboarding:discoveredport' pk=record.pk %}">{{record.port_id}}</a>"""
    )
    discovered_ip_address = tables.Column(linkify=True)
    protocol = tables.Column()
    state = tables.Column()

    class Meta(BaseTable.Meta):
        """Meta."""

        model = DiscoveredPort
        fields = ("pk", "port_id", "discovered_ip_address", "protocol", "state", "service", "reason", "reason_ttl")
        default_columns = (
            "pk",
            "port_id",
            "discovered_ip_address",
            "protocol",
            "state",
            "service",
            "reason",
            "reason_ttl",
        )
