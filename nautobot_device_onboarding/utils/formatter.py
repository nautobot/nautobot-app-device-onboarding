"""Formatter."""

import json
import os

import yaml
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json
from jinja2.sandbox import SandboxedEnvironment
from netutils.interface import canonical_interface_name

from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC
from nautobot_device_onboarding.utils.jinja_filters import fix_interfaces

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


def get_django_env():
    """Load Django Jinja filters from the Django jinja template engine, and add them to the jinja_env.

    Returns:
        SandboxedEnvironment
    """
    # Use a custom Jinja2 environment instead of Django's to avoid HTML escaping
    j2_env = {
        "undefined": "jinja2.StrictUndefined",
        "trim_blocks": True,
        "lstrip_blocks": False,
    }
    if isinstance(j2_env["undefined"], str):
        j2_env["undefined"] = import_string(j2_env["undefined"])
    jinja_env = SandboxedEnvironment(**j2_env)
    jinja_env.filters = engines["jinja"].env.filters
    jinja_env.filters["fix_interfaces"] = fix_interfaces
    return jinja_env


def load_yaml_datafile(filename):
    """Get the contents of the given YAML data file.

    Args:
        filename (str): Filename within the 'data' directory.
    """
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as yaml_file:
            data = yaml.safe_load(yaml_file)
        return data


def perform_data_extraction(host, dict_field, command_info_dict, j2_env, task_result):
    """Extract, process data."""
    result_dict = {}
    for show_command in command_info_dict["commands"]:
        if show_command["command"] == task_result.name:
            jpath_template = j2_env.from_string(show_command["jpath"])
            j2_rendered_jpath = jpath_template.render({"obj": host.name, "original_host": host.name})
            print(j2_rendered_jpath)
            if not task_result.failed:
                if isinstance(task_result.result, str):
                    try:
                        result_to_json = json.loads(task_result.result)
                        extracted_value = extract_data_from_json(result_to_json, j2_rendered_jpath)
                        print(f"extraced value: {extracted_value}")
                    except json.decoder.JSONDecodeError:
                        extracted_value = None
                else:
                    extracted_value = extract_data_from_json(task_result.result, j2_rendered_jpath)
                    print(f"extracted value 2: {extracted_value}")
                if show_command.get("post_processor"):
                    template = j2_env.from_string(show_command["post_processor"])
                    extracted_processed = template.render({"obj": extracted_value, "original_host": host.name})
                    print(f"extracted 1: {extracted_processed}")
                else:
                    extracted_processed = extracted_value
                    print(f"extracted 2: {extracted_processed}")
                    if isinstance(extracted_value, list) and len(extracted_value) == 1:
                        extracted_processed = extracted_value[0]
                        print(f"extracted 3: {extracted_processed}")
                if command_info_dict.get("validator_pattern"):
                    # temp validator
                    if command_info_dict["validator_pattern"] == "not None":
                        if not extracted_processed:
                            print("validator pattern not detected, checking next command.")
                            continue
                        else:
                            print("About to break the sequence due to valid pattern found")
                            result_dict[dict_field] = extracted_processed
                            break
                result_dict[dict_field] = extracted_processed
    return result_dict


def extract_show_data(host, multi_result, command_getter_type):
    """Take a result of show command and extra specific needed data.

    Args:
        host (host): host from task
        multi_result (multiResult): multiresult object from nornir
        command_getter_type (str): to know what dict to pull, device_onboarding or network_importer.
    """
    jinja_env = get_django_env()

    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]
    final_result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if command_info.get("commands"):
            # Means their isn't any "nested" structures. Therefore not expected to see "validator_pattern key"
            result = perform_data_extraction(host, default_dict_field, command_info, jinja_env, multi_result[0])
            final_result_dict.update(result)
        else:
            # Means their is a "nested" structures. Priority
            for dict_field, nested_command_info in command_info.items():
                result = perform_data_extraction(host, dict_field, nested_command_info, jinja_env, multi_result[0])
                final_result_dict.update(result)
    return final_result_dict


def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


def format_ios_results(device):
    """Format the results of the show commands for IOS devices."""
    try:
        serial = device.get("serial")
        mtu_list = device.get("mtu", [])
        type_list = device.get("type", [])
        ip_list = device.get("ip_addresses", [])
        prefix_list = device.get("prefix_length", [])
        mac_list = device.get("mac_address", [])
        description_list = device.get("description", [])
        link_status_list = device.get("link_status", [])
        #vrf_list = device.get("vrf", [])
        #print(f"vrf_list: {vrf_list}")

        interface_dict = {}
        for item in mtu_list:
            interface_dict.setdefault(item["interface"], {})["mtu"] = item["mtu"]
        for item in type_list:
            interface_type = map_interface_type(item["type"])
            interface_dict.setdefault(item["interface"], {})["type"] = interface_type
        for item in ip_list:
            interface_dict.setdefault(item["interface"], {})["ip_addresses"] = {"ip_address": item["ip_address"]}
        for item in prefix_list:
            interface_dict.setdefault(item["interface"], {}).setdefault("ip_addresses", {})["prefix_length"] = item[
                "prefix_length"
            ]
        for item in mac_list:
            interface_dict.setdefault(item["interface"], {})["mac_address"] = item["mac_address"]
        for item in description_list:
            interface_dict.setdefault(item["interface"], {})["description"] = item["description"]
        for item in link_status_list:
            interface_dict.setdefault(item["interface"], {})["link_status"] = True if item["link_status"] == "up" else False
        for interface in interface_dict.values():
            interface.setdefault("802.1Q_mode", "")
            interface.setdefault("lag", "")
            interface.setdefault("untagged_vlan", {})
            interface.setdefault("tagged_vlans", [])

        for interface, data in interface_dict.items():
            ip_addresses = data.get("ip_addresses", {})
            if ip_addresses:
                data["ip_addresses"] = [ip_addresses]

        # Convert interface names to canonical form
        interface_list = []
        for interface_name, interface_info in interface_dict.items():
            interface_list.append({canonical_interface_name(interface_name): interface_info})

        device["interfaces"] = interface_list
        device["serial"] = serial
        try:
            del device["mtu"]
            del device["type"]
            del device["ip_addresses"]
            del device["prefix_length"]
            del device["mac_address"]
            del device["description"]
            del device["link_status"]

        except KeyError:
            pass
    except Error as e:
        device = { "failed": True, "failed_reason": f"Formatting error for device {device}"}  
    return device


def format_nxos_results(device):
    """Format the results of the show commands for NX-OS devices."""
    try:
        serial = device.get("serial")
        mtu_list = device.get("mtu", [])
        type_list = device.get("type", [])
        ip_list = device.get("ip_addresses", [])
        prefix_list = device.get("prefix_length", [])
        mac_list = device.get("mac_address", [])
        description_list = device.get("description", [])
        link_status_list = device.get("link_status", [])
        mode_list = device.get("mode", [])

        interface_dict = {}
        for item in mtu_list:
            interface_dict.setdefault(item["interface"], {})["mtu"] = item["mtu"]
        for item in type_list:
            interface_type = map_interface_type(item["type"])
            interface_dict.setdefault(item["interface"], {})["type"] = interface_type
        for item in ip_list:
            interface_dict.setdefault(item["interface"], {})["ip_addresses"] = {"ip_address": item["ip_address"]}
        for item in prefix_list:
            interface_dict.setdefault(item["interface"], {}).setdefault("ip_addresses", {})["prefix_length"] = item[
                "prefix_length"
            ]
        for item in mac_list:
            interface_dict.setdefault(item["interface"], {})["mac_address"] = item["mac_address"]
        for item in description_list:
            interface_dict.setdefault(item["interface"], {})["description"] = item["description"]
        for item in link_status_list:
            interface_dict.setdefault(item["interface"], {})["link_status"] = True if item["link_status"] == "up" else False
        for item in mode_list:
            interface_dict.setdefault(item["interface"], {})["802.1Q_mode"] = (
                "access" if item["mode"] == "access" else "tagged" if item["mode"] == "trunk" else ""
            )

        for interface in interface_dict.values():
            # interface.setdefault("802.1Q_mode", "")
            interface.setdefault("lag", "")
            interface.setdefault("untagged_vlan", {})
            interface.setdefault("tagged_vlans", [])

        for interface, data in interface_dict.items():
            ip_addresses = data.get("ip_addresses", {})
            if ip_addresses:
                data["ip_addresses"] = [ip_addresses]

        # Convert interface names to canonical form
        interface_list = []
        for interface_name, interface_info in interface_dict.items():
            interface_list.append({canonical_interface_name(interface_name): interface_info})

        device["interfaces"] = interface_list
        device["serial"] = serial
        try:
            del device["mtu"]
            del device["type"]
            del device["ip_addresses"]
            del device["prefix_length"]
            del device["mac_address"]
            del device["description"]
            del device["link_status"]
            del device["mode"]
        except KeyError:
            pass
    except Error as e:
        device = { "failed": True, "failed_reason": f"Formatting error for device {device}"}
        return device
       
    return device


def format_junos_results(compiled_results):
    """For mat the results of the show commands for Junos devices."""
    return compiled_results


def format_results(compiled_results):
    """Format the results of the show commands for IOS devices.

    Args:
        compiled_results (dict): The compiled results from the Nornir task.

    Returns:
        compiled_results (dict): The formatted results.
    """
    for device, data in compiled_results.items():
        if "platform" in data:
            platform = data.get("platform")
        if platform not in ["cisco_ios", "cisco_xe", "cisco_nxos"]:
            print(f"Unsupported platform {platform}")
            data.update({"failed": True, "failed_reason": f"Unsupported platform {platform}"})
        if "type" in data:
            if platform in ["cisco_ios", "cisco_xe"]:
                format_ios_results(data)
            elif platform == "cisco_nxos":
                format_nxos_results(data)                   
        else:
            data.update({"failed": True, "failed_reason": "Cannot connect to device."})
            
    return compiled_results
