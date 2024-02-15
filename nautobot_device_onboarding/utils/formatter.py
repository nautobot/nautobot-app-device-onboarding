"""Formatter."""

from nautobot_device_onboarding.constants import (
    CISCO_INTERFACE_ABBREVIATIONS,
    CISCO_TO_NAUTOBOT_INTERFACE_TYPE,
    TAGGED_INTERFACE_TYPES,
)


def format_ob_data_ios(host, result):
    """Format the data for onboarding IOS devices."""
    primary_ip4 = host.name
    formatted_data = {}

    for r in result:
        if r.name == "show inventory":
            device_type = r.result[0].get("pid")
            formatted_data["device_type"] = device_type
        elif r.name == "show version":
            hostname = r.result[0].get("hostname")
            serial = r.result[0].get("serial")
            formatted_data["hostname"] = hostname
            formatted_data["serial"] = serial[0]
        elif r.name == "show interfaces":
            show_interfaces = r.result
            for interface in show_interfaces:
                if interface.get("ip_address") == primary_ip4:
                    mask_length = interface.get("prefix_length")
                    interface_name = interface.get("interface")
                    formatted_data["mask_length"] = mask_length
                    formatted_data["mgmt_interface"] = interface_name

    return formatted_data


def format_ob_data_nxos(host, result):
    """Format the data for onboarding NXOS devices."""
    primary_ip4 = host.name
    formatted_data = {}

    for r in result:
        if r.name == "show inventory":
            # TODO: Add check for PID when textfsm template is fixed
            pass
        elif r.name == "show version":
            device_type = r.result[0].get("platform")
            formatted_data["device_type"] = device_type
            hostname = r.result[0].get("hostname")
            serial = r.result[0].get("serial")
            formatted_data["hostname"] = hostname
            if serial:
                formatted_data["serial"] = serial
            else:
                formatted_data["serial"] = ""
        elif r.name == "show interface":
            show_interfaces = r.result
            print(f"show interfaces {show_interfaces}")
            for interface in show_interfaces:
                if interface.get("ip_address") == primary_ip4:
                    mask_length = interface.get("prefix_length")
                    interface_name = interface.get("interface")
                    formatted_data["mask_length"] = mask_length
                    formatted_data["mgmt_interface"] = interface_name
                    break
    return formatted_data


def format_ob_data_junos(host, result):
    """Format the data for onboarding Juniper JUNOS devices."""
    primary_ip4 = host.name
    formatted_data = {}

    for r in result:
        if r.name == "show version":
            device_type = r.result[0].get("model")
            formatted_data["device_type"] = device_type
            hostname = r.result[0].get("hostname")
            serial = "USASR24490"
            # serial = r.result[0].get("serial")
            formatted_data["hostname"] = hostname
            if serial:
                formatted_data["serial"] = serial
            else:
                formatted_data["serial"] = ""
        elif r.name == "show interfaces":
            show_interfaces = r.result
            print(f"show interfaces {show_interfaces}")
            for interface in show_interfaces:
                if interface.get("local") == primary_ip4:
                    print(interface.get("destination"))
                    mask_length = interface.get("destination").split("/")[1]
                    print(f"interface mask {mask_length}")
                    interface_name = interface.get("interface")
                    formatted_data["mask_length"] = mask_length
                    formatted_data["mgmt_interface"] = interface_name
                    break

    return formatted_data


def normalize_interface_name(interface_name):
    """Normalize interface names."""
    for interface_abbreviation, interface_full in CISCO_INTERFACE_ABBREVIATIONS.items():
        if interface_name.startswith(interface_abbreviation):
            interface_name = interface_name.replace(interface_abbreviation, interface_full, 1)
            break
    return interface_name


def normalize_interface_type(interface_type):
    """Normalize interface types."""
    if interface_type in CISCO_TO_NAUTOBOT_INTERFACE_TYPE:
        return CISCO_TO_NAUTOBOT_INTERFACE_TYPE[interface_type]
    return "other"


def normalize_tagged_interface(tagged_interface):
    """Normalize tagged interface types."""
    if tagged_interface in TAGGED_INTERFACE_TYPES:
        return TAGGED_INTERFACE_TYPES[tagged_interface]
    return ""
