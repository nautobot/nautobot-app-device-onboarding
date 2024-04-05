"""Formatter."""

import json
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json
from jinja2.sandbox import SandboxedEnvironment
from netutils.interface import canonical_interface_name
from nautobot.dcim.models import Device

from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC


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
    # https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jinja2-filters/
    #
    # if PLUGIN_CFG.get("custom_post_processing_filters"):
    #     for filter_name, filter_function in PLUGIN_CFG["custom_post_processing_filters"].items():
    #         try:
    #             func = import_string(filter_function)
    #         except Exception as error:  # pylint: disable=broad-except
    #             msg = (
    #                 "There was an issue attempting to import the custom post_processing filters of"
    #                 f" {filter_name} this is expected with a local configuration issue "
    #                 "and not related to the Device Onboarding App, please contact your system admin for further details"
    #             )
    #             raise Exception(msg).with_traceback(error.__traceback__)
    #         jinja_env.filters[filter_name] = func
    # jinja_env.filters["fix_interfaces"] = fix_interfaces
    return jinja_env


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
    # Think about whether this should become a constant, the env shouldn't change per job execution, but
    # perhaps it shouldn't be reused to avoid any memory leak?
    jinja_env = get_django_env()

    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]
    final_result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if command_info.get("commands"):
            # Means their isn't any "nested" structures. Therefore not expected to see "validator_pattern key"
            if isinstance(command_info["commands"], dict):
                command_info["commands"] = [command_info["commands"]]
            result = perform_data_extraction(host, default_dict_field, command_info, jinja_env, multi_result[0])
            final_result_dict.update(result)
        else:
            # Means their is a "nested" structures. Priority
            for dict_field, nested_command_info in command_info.items():
                if isinstance(nested_command_info["commands"], dict):
                    nested_command_info["commands"] = [nested_command_info["commands"]]
                result = perform_data_extraction(host, dict_field, nested_command_info, jinja_env, multi_result[0])
                final_result_dict.update(result)
    return final_result_dict


def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    # Can maybe this be used?
    # from nautobot.dcim.choices import InterfaceTypeChoices
    # InterfaceTypeChoices.CHOICES
    # In [15]: dict(InterfaceTypeChoices.CHOICES).get('Other')
    # Out[15]: (('other', 'Other'),)
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


def ensure_list(data):
    """Ensure data is a list."""
    if not isinstance(data, list):
        return [data]
    return data


def format_ios_results(device):
    """Format the results of the show commands for IOS devices."""
    try:
        serial = device.get("serial")
        mtus = device.get("mtu", [])
        types = device.get("type", [])
        ips = device.get("ip_addresses", [])
        prefixes = device.get("prefix_length", [])
        macs = device.get("mac_address", [])
        descriptions = device.get("description", [])
        link_statuses = device.get("link_status", [])
        vrfs = device.get("vrfs", [])

        # Some data may come across as a dict, needs to be list. Probably should do this elsewhere.
        mtu_list = ensure_list(mtus)
        type_list = ensure_list(types)
        ip_list = ensure_list(ips)
        prefix_list = ensure_list(prefixes)
        mac_list = ensure_list(macs)
        description_list = ensure_list(descriptions)
        link_status_list = ensure_list(link_statuses)
        vrf_list = ensure_list(vrfs)

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
            interface_dict.setdefault(item["interface"], {})["link_status"] = (
                True if item["link_status"] == "up" else False
            )
        for vrf in vrf_list:
            for interface in vrf["interfaces"]:
                canonical_name = canonical_interface_name(interface)
                interface_dict.setdefault(canonical_name, {})
                interface_dict[canonical_name]["vrf"] = {"name": vrf["name"], "rd": vrf["default_rd"]}
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
            del device["vrfs"]

        except KeyError:
            device = {"failed": True, "failed_reason": f"Formatting error 2 for device {device}"}
    except Exception as e:
        device = {"failed": True, "failed_reason": f"Formatting error 1 {e} for device {device}"}
        print(f"susan {device}")
    return device


def format_nxos_vrf_results(device):
    """Format the show commands to get interface and rd."""
    try:
        vrf_interface_list = device.get("vrf_interfaces", [])
        vrf_rd_list = device.get("vrf_rds", [])

        # dict2 = {item["id"]: item for item in list2}  # jeff commented out since it wasn't used at all.

        for id in vrf_interface_list:
            id.update(vrf_rd_list.get(id["id"], {}))
        print(f"vrf_interface_list {vrf_interface_list}")
    except Exception:
        device = {"failed": True, "failed_reason": f"Formatting error for device {device}"}
    return vrf_interface_list


def format_nxos_results(device):
    """Format the results of the show commands for NX-OS devices."""
    try:
        serial = device.get("serial")
        mtus = device.get("mtu", [])
        types = device.get("type", [])
        ips = device.get("ip_addresses", [])
        prefixes = device.get("prefix_length", [])
        macs = device.get("mac_address", [])
        descriptions = device.get("description", [])
        link_statuses = device.get("link_status", [])
        modes = device.get("mode", [])

        mtu_list = ensure_list(mtus)
        type_list = ensure_list(types)
        ip_list = ensure_list(ips)
        prefix_list = ensure_list(prefixes)
        mac_list = ensure_list(macs)
        description_list = ensure_list(descriptions)
        link_status_list = ensure_list(link_statuses)
        mode_list = ensure_list(modes)

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
            interface_dict.setdefault(item["interface"], {})["link_status"] = (
                True if item["link_status"] == "up" else False
            )
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
            device = {"failed": True, "failed_reason": f"Formatting error for device {device}"}
    except Exception:
        device = {"failed": True, "failed_reason": f"Formatting error for device {device}"}
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
        try:
            if "platform" in data:
                platform = data.get("platform")
            if platform not in ["cisco_ios", "cisco_xe", "cisco_nxos"]:
                data.update({"failed": True, "failed_reason": f"Unsupported platform {platform}"})
            if "type" in data:

                serial = Device.objects.get(name=device).serial
                if serial == "":
                    data.update({"failed": True, "failed_reason": "Serial not found for device in Nautobot."})
                else:
                    data["serial"] = serial
                if platform in ["cisco_ios", "cisco_xe"]:
                    format_ios_results(data)
                elif platform == "cisco_nxos":
                    format_nxos_results(data)
            else:
                data.update({"failed": True, "failed_reason": "Cannot connect to device."})
        except Exception as e:
            data.update({"failed": True, "failed_reason": f"Error formatting device: {e}"})
    return compiled_results
