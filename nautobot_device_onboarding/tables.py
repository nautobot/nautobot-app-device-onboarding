"""Tables for Nautobot Device Onboarding."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ColoredLabelColumn, ToggleColumn

from nautobot_device_onboarding import models


class OnboardingConfigSyncDevicesTable(BaseTable):
    # pylint: disable=R0903
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    namespace = tables.Column(linkify=True, verbose_name="Namespace")
    device_role = tables.Column(linkify=True, verbose_name="Device Role")
    secrets_group = tables.Column(linkify=True, verbose_name="Secrets Group")
    defice_status = ColoredLabelColumn(linkify=True, verbose_name="Device Status")
    interface_status = ColoredLabelColumn(linkify=True, verbose_name="Interface Status")
    ip_address_status = ColoredLabelColumn(linkify=True, verbose_name="IP Address Status")
    port = tables.Column(verbose_name="Port")
    timeout = tables.Column(verbose_name="Timeout")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.OnboardingConfigSyncDevices
        fields = (
            "name",
            "preferred_config",
            "namespace",
            "device_role",
            "secrets_group",
            "device_status",
            "interface_status",
            "ip_address_status",
            "port",
            "timeout",
        )

        # Option for modifying the columns that show up in the list view by default:
        default_columns = (
            "name",
            "preferred_config",
        )


class OnboardingConfigSyncNetworkDataFromNetworkTable(BaseTable):
    # pylint: disable=R0903
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    connectivity_test = tables.Column(linkify=True, verbose_name="Connectivity Test")
    sync_vlans = tables.Column(linkify=True, verbose_name="Sync VLANs")
    sync_vrfs = tables.Column(linkify=True, verbose_name="Sync VRFs")
    sync_cables = tables.Column(linkify=True, verbose_name="Sync Cables")
    sync_software = tables.Column(linkify=True, verbose_name="Sync Cables")
    namespace = tables.Column(linkify=True, verbose_name="Namespace")
    interface_status = ColoredLabelColumn(linkify=True, verbose_name="Interface Status")
    ip_address_status = ColoredLabelColumn(linkify=True, verbose_name="IP Address Status")
    default_prefix_status = ColoredLabelColumn(linkify=True, verbose_name="Prefix Status")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.OnboardingConfigSyncNetworkDataFromNetwork
        fields = (
            "name",
            "preferred_config",
            "connectivity_test",
            "sync_vlans",
            "sync_vrfs",
            "sync_cables",
            "sync_software",
            "namespace",
            "interface_status",
            "ip_address_status",
            "default_prefix_status",
            "sync_vlans_location_type",
        )

        # Option for modifying the columns that show up in the list view by default:
        default_columns = (
            "name",
            "preferred_config",
        )
