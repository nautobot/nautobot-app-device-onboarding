"""Filters for Jinja2 PostProcessing."""

from django_jinja import library
from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC

# https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jinja2-filters/


@library.filter
def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


@library.filter
def fix_interfaces(interfaces):
    """Prep interface formatting for SSoT."""
    for interface in interfaces:
        for _, int_values in interface.items():
            int_values["type"] = map_interface_type(int_values.get("hardware_type", ""))
            int_values["802.1Q_mode"] = ""
            int_values["untagged_vlan"] = ""
            int_values["tagged_vlans"] = []
            int_values["lag"] = ""
            int_values["ip_addresses"] = []
            int_values["mtu"] = ""
            int_values["ip_addresses"].append(
                {"ip_address": int_values.get("ip_address", ""), "prefix_length": int_values.get("prefix_length", "")}
            )
            if "up" in int_values["link_status"]:
                int_values["link_status"] = True
            else:
                int_values["link_status"] = False

    return interfaces
