"""Filters for Jinja2 PostProcessing."""


def fix_interfaces(interfaces):
    """Prep interface formatting for SSoT."""
    for interface in interfaces:
        for _, int_values in interface.items():
            int_values["type"] = "other"
            int_values["802.1Q_mode"] = ""
            int_values["untagged_vlan"] = ""
            int_values["tagged_vlans"] = []
            int_values["lag"] = ""
            int_values["ip_addresses"] = []
            int_values["ip_addresses"].append(
                {"ip_address": int_values.get("ip_address", ""), "prefix_length": int_values.get("prefix_length", "")}
            )
            if "up" in int_values["link_status"]:
                int_values["link_status"] = True
            else:
                int_values["link_status"] = False
    return interfaces
