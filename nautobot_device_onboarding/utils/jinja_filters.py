"""Filters for Jinja2 PostProcessing."""

from netutils.interface import canonical_interface_name

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
    print(f"Interfaces: {interfaces}")
    return interfaces

def fix_interfaces_switchport(interfaces):
    """Add data from interfaces swtichport command."""
    normalized_interfaces = {}
    for interface_dict in interfaces:
        for interface_name, interface_info in interface_dict.items():
            normalized_name = canonical_interface_name(interface_name)
            normalized_interfaces[normalized_name] = interface_info
        # for _, int_values in interface.items():
        #     int_values["mode"] = int_values.get("admin_mode", "")
    print(f"NORMALIZED INTERFACES: {normalized_interfaces}")
    return normalized_interfaces
            