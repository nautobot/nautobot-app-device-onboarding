"""Tables for Nautobot Device Onboarding."""

import django_tables2 as tables
from nautobot.apps.tables import (BaseTable, ButtonsColumn, StatusTableMixin,
                                  ToggleColumn, ColoredLabelColumn,)

from nautobot_device_onboarding import models


class OnboardingConfigSyncDevicesTable(BaseTable):
    # pylint: disable=R0903
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    default_namespace = tables.Column(linkify=True, verbose_name="Namespace")
    default_device_role = tables.Column(linkify=True, verbose_name="Device Role")
    default_secrets_group = tables.Column(linkify=True, verbose_name="Secrets Group")
    default_device_status = ColoredLabelColumn(linkify=True, verbose_name="Device Status")
    default_interface_status = ColoredLabelColumn(linkify=True, verbose_name="Interface Status")
    default_ip_address_status = ColoredLabelColumn(linkify=True, verbose_name="IP Address Status")
    default_port = tables.Column(verbose_name="Port")
    default_timeout = tables.Column(verbose_name="Timeout")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.OnboardingConfigSyncDevices
        fields = (
            "name",
            "preferred_config",
            "default_namespace",
            "default_device_role",
            "default_secrets_group",
            "default_device_status",
            "default_interface_status",
            "default_ip_address_status",
            "default_port",
            "default_timeout",
        )

        # Option for modifying the columns that show up in the list view by default:
        default_columns = (
            "name",
            "preferred_config",
            "default_namespace",
            "default_device_role",
            "default_secrets_group",
            "default_device_status",
            "default_interface_status",
            "default_ip_address_status",
            "default_port",
            "default_timeout",
        )


class OnboardingConfigSyncNetworkDataFromNetworkTable(BaseTable):
    # pylint: disable=R0903
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    default_connectivity_test = tables.Column(linkify=True, verbose_name="Connectivity Test")
    default_sync_vlans = tables.Column(linkify=True, verbose_name="Sync VLANs")
    default_sync_vrfs = tables.Column(linkify=True, verbose_name="Sync VRFs")
    default_sync_cables = tables.Column(linkify=True, verbose_name="Sync Cables")
    default_namespace = tables.Column(linkify=True, verbose_name="Namespace")
    default_interface_status = ColoredLabelColumn(linkify=True, verbose_name="Interface Status")
    default_ip_address_status = ColoredLabelColumn(linkify=True, verbose_name="IP Address Status")
    default_prefix_status = ColoredLabelColumn(linkify=True, verbose_name="Prefix Status")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.OnboardingConfigSyncNetworkDataFromNetwork
        fields = (
            "name",
            "preferred_config",
            "default_connectivity_test",
            "default_sync_vlans",
            "default_sync_vrfs",
            "default_sync_cables",
            "default_namespace",
            "default_interface_status",
            "default_ip_address_status",
            "default_prefix_status",
            "sync_vlans_location_type",
        )

        # Option for modifying the columns that show up in the list view by default:
        default_columns = (
            "name",
            "preferred_config",
            "default_connectivity_test",
            "default_sync_vlans",
            "default_sync_vrfs",
            "default_sync_cables",
            "default_namespace",
            "default_interface_status",
            "default_ip_address_status",
            "default_prefix_status",
            "sync_vlans_location_type",
        )