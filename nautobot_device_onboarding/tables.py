"""Tables."""

import django_tables2 as tables
from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from .models import DiscoveredGroup, DiscoveredIPAddress, DiscoveredPort


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


class DiscoveredIPAddressGroupTable(BaseTable):
    """DiscoverdIPAddress Table."""

    pk = ToggleColumn()
    discovered_group = tables.Column(linkify=True)
    ip_address = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = DiscoveredIPAddress
        fields = ("pk", "discovered_group", "ip_address")
        default_columns = ("pk", "name", "ip_address")


class DiscoveredPortTable(BaseTable):
    """DiscoverdPort Table."""

    pk = ToggleColumn()
    discovered_ip_address = tables.Column(linkify=True)
    protocol = tables.Column()
    port_id = tables.Column()
    state = tables.Column()
    reason = tables.Column()
    reason_ttl = tables.Column()

    class Meta(BaseTable.Meta):
        """Meta."""

        model = DiscoveredPort
        fields = ("pk", "discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl")
        default_columns = ("pk", "discovered_ip_address", "protocol", "port_id", "state", "reason", "reason_ttl")
