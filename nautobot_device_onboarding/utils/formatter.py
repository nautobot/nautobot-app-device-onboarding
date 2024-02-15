"""Formatter."""
import os

import yaml
from django.template import engines
from jdiff import extract_data_from_json
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


def load_yaml_datafile(filename, config=None):
    """Get the contents of the given YAML data file.

    Args:
        filename (str): Filename within the 'data' directory.
        config (dict): Data for Jinja2 templating.
    """
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(file_path):
        raise RuntimeError(f"No data file found at {file_path}")
    if not config:
        config = {}
    jinja_env = SandboxedEnvironment(
        loader=FileSystemLoader(DATA_DIR), autoescape=True, trim_blocks=True, lstrip_blocks=False
    )
    jinja_env.filters = engines["jinja"].env.filters
    template = jinja_env.get_template(filename)
    populated = template.render(config)
    return yaml.safe_load(populated)


def extract_show_data(host, multi_result):
    """_summary_

    Args:
        host (_type_): _description_
        result (_type_): _description_
    
    result is a MultiResult Nornir Object for a single host.
    """
    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]

    result_dict = {}
    for default_dict_field, command_info in command_jpaths['device_onboarding'].items():
        if command_info["command"] == multi_result[0].name:
            extracted_value = extract_data_from_json(multi_result[0].result, command_info['jpath'])
            if isinstance(extracted_value, list) and len(extracted_value) == 1:
                extracted_value = extracted_value[0]
            result_dict[default_dict_field] = extracted_value
    return result_dict

# from nautobot_device_onboarding.constants import (
#     CISCO_INTERFACE_ABBREVIATIONS,
#     CISCO_TO_NAUTOBOT_INTERFACE_TYPE,
#     TAGGED_INTERFACE_TYPES,
# )


# def format_ob_data_ios(host, result):
#     """Format the data for onboarding IOS devices."""
#     primary_ip4 = host.name
#     formatted_data = {}

#     for r in result:
#         if r.name == "show inventory":
#             device_type = r.result[0].get("pid")
#             formatted_data["device_type"] = device_type
#         elif r.name == "show version":
#             hostname = r.result[0].get("hostname")
#             serial = r.result[0].get("serial")
#             formatted_data["hostname"] = hostname
#             formatted_data["serial"] = serial[0]
#         elif r.name == "show interfaces":
#             show_interfaces = r.result
#             for interface in show_interfaces:
#                 if interface.get("ip_address") == primary_ip4:
#                     mask_length = interface.get("prefix_length")
#                     interface_name = interface.get("interface")
#                     formatted_data["mask_length"] = mask_length
#                     formatted_data["mgmt_interface"] = interface_name

#     return formatted_data


# def format_ob_data_nxos(host, result):
#     """Format the data for onboarding NXOS devices."""
#     primary_ip4 = host.name
#     formatted_data = {}

#     for r in result:
#         if r.name == "show inventory":
#             # TODO: Add check for PID when textfsm template is fixed
#             pass
#         elif r.name == "show version":
#             device_type = r.result[0].get("platform")
#             formatted_data["device_type"] = device_type
#             hostname = r.result[0].get("hostname")
#             serial = r.result[0].get("serial")
#             formatted_data["hostname"] = hostname
#             if serial:
#                 formatted_data["serial"] = serial
#             else:
#                 formatted_data["serial"] = ""
#         elif r.name == "show interface":
#             show_interfaces = r.result
#             print(f"show interfaces {show_interfaces}")
#             for interface in show_interfaces:
#                 if interface.get("ip_address") == primary_ip4:
#                     mask_length = interface.get("prefix_length")
#                     interface_name = interface.get("interface")
#                     formatted_data["mask_length"] = mask_length
#                     formatted_data["mgmt_interface"] = interface_name
#                     break
#     return formatted_data

#     return formatted_data

# def format_ob_data_junos(host, result):
#     """Format the data for onboarding Juniper JUNOS devices."""
#     primary_ip4 = host.name
#     formatted_data = {}

#     for r in result:
#         if r.name == "show version":
#             device_type = r.result[0].get("model")
#             formatted_data["device_type"] = device_type
#             hostname = r.result[0].get("hostname")
#             serial = "USASR24490"
#             # serial = r.result[0].get("serial")
#             formatted_data["hostname"] = hostname
#             if serial:
#                 formatted_data["serial"] = serial
#             else:
#                 formatted_data["serial"] = ""
#         elif r.name == "show interfaces":
#             show_interfaces = r.result
#             print(f"show interfaces {show_interfaces}")
#             for interface in show_interfaces:
#                 if interface.get("local") == primary_ip4:
#                     print(interface.get("destination"))
#                     mask_length = interface.get("destination").split("/")[1]
#                     print(f"interface mask {mask_length}")
#                     interface_name = interface.get("interface")
#                     formatted_data["mask_length"] = mask_length
#                     formatted_data["mgmt_interface"] = interface_name
#                     break

#     return formatted_data


# def normalize_interface_name(interface_name):
#     """Normalize interface names."""
#     for interface_abbreviation, interface_full in CISCO_INTERFACE_ABBREVIATIONS.items():
#         if interface_name.startswith(interface_abbreviation):
#             interface_name = interface_name.replace(interface_abbreviation, interface_full, 1)
#             break
#     return interface_name


# def normalize_interface_type(interface_type):
#     """Normalize interface types."""
#     if interface_type in CISCO_TO_NAUTOBOT_INTERFACE_TYPE:
#         return CISCO_TO_NAUTOBOT_INTERFACE_TYPE[interface_type]
#     return "other"


# def normalize_tagged_interface(tagged_interface):
#     """Normalize tagged interface types."""
#     if tagged_interface in TAGGED_INTERFACE_TYPES:
#         return TAGGED_INTERFACE_TYPES[tagged_interface]
#     return ""


# def format_ni_data_cisco_ios(command, command_result):
#     """Format cisco_ios data."""
#     all_results = {}
#     # command = ["show version", "show interfaces", "show vlan", "show interfaces switchport"]
#     for host_name, result in command_result.items():
#         if host_name not in all_results:
#             all_results[host_name] = {"interfaces": {}, "serial": ""}

#         if command == "show version":
#             serial_info = result.result[0]
#             serial_number = serial_info.get("serial")
#             all_results[host_name]["serial"] = serial_number[0]
#         elif command == "show interfaces":
#             print(f"Interfaces: {result.result}")
#             for interface_info in result.result:
#                 interface_name = interface_info.get("interface")
#                 media_type = interface_info.get("media_type")
#                 hardware_type = interface_info.get("hardware_type")
#                 mtu = interface_info.get("mtu")
#                 description = interface_info.get("description")
#                 mac_address = interface_info.get("mac_address")
#                 link_status = interface_info.get("link_status")

#                 if link_status == "up":
#                     link_status = True
#                 else:
#                     link_status = False

#                 type = "other"
#                 if hardware_type == "EtherChannel":
#                     type = "lag"
#                 elif hardware_type == "Ethernet SVI":
#                     type = "virtual"
#                 elif media_type == "10/100/1000BaseTX":
#                     type = "100base-tx"
#                 else:
#                     type = "other"

#                 all_results[host_name]["interfaces"][interface_name] = {
#                     "mtu": mtu,
#                     "type": type,
#                     "media_type": media_type,
#                     "hardware_type": hardware_type,
#                     "description": description,
#                     "mac_address": mac_address,
#                     "enabled": link_status,
#                 }
#         elif command == "show vlan":
#             print(f"Vlan: {result.result}")
#         elif command == "show interfaces switchport":
#             for interface_info in result.result:
#                 print(f"Interfaces switchport: {result.result}")
#                 interface_mode = interface_info.get("admin_mode")
#                 access_vlan = interface_info.get("access_vlan")
#     return all_results
