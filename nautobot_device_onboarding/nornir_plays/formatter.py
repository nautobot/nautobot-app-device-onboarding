"""Command Extraction and Formatting or SSoT Based Jobs."""

import json
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json
from jinja2.sandbox import SandboxedEnvironment
from nautobot.dcim.models import Device
from netutils.interface import canonical_interface_name
from netutils.vlan import vlanconfig_to_list
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
    return jinja_env


def extract_and_post_process(parsed_command_output, yaml_command_element, j2_data_context, iter_type):
    """Helper to extract and apply post_processing on a single element."""
    j2_env = get_django_env()
    jpath_template = j2_env.from_string(yaml_command_element["jpath"])
    j2_rendered_jpath = jpath_template.render(**j2_data_context)
    if isinstance(parsed_command_output, str):
            parsed_command_output = json.loads(parsed_command_output)
    extracted_value = extract_data_from_json(parsed_command_output, j2_rendered_jpath)
    pre_processed_extracted = extracted_value
    if yaml_command_element.get("post_processor"):
        # j2 context data changes obj(hostname) -> extracted_value for post_processor
        j2_data_context["obj"] = extracted_value
        template = j2_env.from_string(yaml_command_element["post_processor"])
        extracted_processed = template.render(**j2_data_context)
    else:
        extracted_processed = extracted_value
    try:
        post_processed_data = json.loads(extracted_processed)
    except Exception:
        post_processed_data = extracted_processed
    if isinstance(post_processed_data, list) and len(post_processed_data) == 0:
        # means result was empty, change empty result to iterater_type if applicable.
        if iter_type:
            print(f"in iter_type {iter_type}")
            if iter_type == "dict":
                print(f"post_iter: {post_processed_data}")
                post_processed_data = {}
    if isinstance(post_processed_data, list) and len(post_processed_data) == 1:
        if isinstance(post_processed_data[0], str):
            post_processed_data = post_processed_data[0]
        else:
            if isinstance(post_processed_data[0], dict):
                if iter_type:
                    if iter_type == "dict":
                        post_processed_data = post_processed_data[0]
    return pre_processed_extracted, post_processed_data

def perform_data_extractionv2(host, command_info_dict, command_outputs_dict):
    """Extract, process data."""
    result_dict = {}
    for ssot_field, field_data in command_info_dict.items():
        if isinstance(field_data['commands'], dict):
            # only one command is specified as a dict force it to a list.
            loop_commands = [field_data['commands']]
        else:
            loop_commands = field_data['commands']
        for show_command_dict in loop_commands:
            final_iterable_type = show_command_dict.get("iterable_type")
            if field_data.get('root_key'):
                root_key_pre, root_key_post = extract_and_post_process(
                    command_outputs_dict[show_command_dict["command"]],
                    show_command_dict,
                    {"obj": host.name, "original_host": host.name},
                    final_iterable_type
                )
                # root_key_extracted = a1.copy()
                result_dict[ssot_field] = root_key_post
            else:
                field_nesting = ssot_field.split('__')
                # for current_nesting in field_nesting:
                if len(field_nesting) > 1:
                    # Means there is "anticipated" data nesting `interfaces__mtu` means final data would be
                    # {"Ethernet1/1": {"mtu": <value>}}
                    for current_key in root_key_pre:
                        # current_key is a single iteration from the root_key extracted value. Typically we want this to be
                        # a list of data that we want to become our nested key. E.g. current_key "Ethernet1/1"
                        # These get passed into the render context for the template render to allow nested jpaths to use
                        # the current_key context for more flexible jpath queries.
                        _, current_key_post = extract_and_post_process(
                            command_outputs_dict[show_command_dict["command"]],
                            show_command_dict,
                            {"current_key": current_key, "obj": host.name, "original_host": host.name},
                            final_iterable_type
                        )
                        result_dict[field_nesting[0]][current_key][field_nesting[1]] = current_key_post
                else:
                    _, current_field_post = extract_and_post_process(
                        command_outputs_dict[show_command_dict["command"]],
                        show_command_dict,
                        {"obj": host.name, "original_host": host.name},
                        final_iterable_type
                    )
                    result_dict[ssot_field] = current_field_post
        # if command_info_dict.get("validator_pattern"):
        #     # temp validator
        #     if command_info_dict["validator_pattern"] == "not None":
        #         if not extracted_processed:
        #             print("validator pattern not detected, checking next command.")
        #             continue
        #         else:
        #             print("About to break the sequence due to valid pattern found")
        #             result_dict[dict_field] = extracted_processed
        #             break
    return result_dict


def perform_data_extraction(host, dict_field, command_info_dict, j2_env, task_result):
    """Extract, process data."""
    result_dict = {}
    for show_command in command_info_dict["commands"]:
        if show_command["command"] == task_result.name:
            jpath_template = j2_env.from_string(show_command["jpath"])
            j2_rendered_jpath = jpath_template.render({"obj": host.name, "original_host": host.name})

            if not task_result.failed:
                if isinstance(task_result.result, str):
                    try:
                        result_to_json = json.loads(task_result.result)
                        extracted_value = extract_data_from_json(result_to_json, j2_rendered_jpath)

                    except json.decoder.JSONDecodeError:
                        extracted_value = None
                else:
                    extracted_value = extract_data_from_json(task_result.result, j2_rendered_jpath)

                if show_command.get("post_processor"):
                    template = j2_env.from_string(show_command["post_processor"])
                    extracted_processed = template.render({"obj": extracted_value, "original_host": host.name})

                else:
                    extracted_processed = extracted_value

                    if isinstance(extracted_value, list) and len(extracted_value) == 1:
                        extracted_processed = extracted_value[0]

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


def extract_show_datav2(host, command_outputs, command_getter_type):
    """Take a result of show command and extra specific needed data.

    Args:
        host (host): host from task
        multi_result (multiResult): multiresult object from nornir
        command_getter_type (str): to know what dict to pull, sync_devices or sync_network_data.
    """
    command_getter_iterable = host.data["platform_parsing_info"][command_getter_type]
    all_results_extracted = perform_data_extractionv2(host, command_getter_iterable, command_outputs)
    return all_results_extracted


def extract_show_data(host, multi_result, command_getter_type):
    """Take a result of show command and extra specific needed data.

    Args:
        host (host): host from task
        multi_result (multiResult): multiresult object from nornir
        command_getter_type (str): to know what dict to pull, sync_devices or sync_network_data.
    """
    jinja_env = get_django_env()

    host_platform = host.platform
    # if host_platform == "cisco_xe":
    #     host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]
    root_keys = extract_root_keys(command_jpaths[command_getter_type])
    final_result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if not default_dict_field.startswith('_metadata'):
            if command_info.get("commands"):
                # Means there isn't any "nested" structures. Therefore not expected to see "validator_pattern key"
                if isinstance(command_info["commands"], dict):
                    command_info["commands"] = [command_info["commands"]]
                result = perform_data_extraction(host, default_dict_field, command_info, jinja_env, multi_result[0])
                root_keys[default_dict_field] = result
                final_result_dict.update(result)
            else:
                # Means there is a "nested" structures. Priority
                for dict_field, nested_command_info in command_info.items():
                    if isinstance(nested_command_info["commands"], dict):
                        nested_command_info["commands"] = [nested_command_info["commands"]]
                    result = perform_data_extraction(host, dict_field, nested_command_info, jinja_env, multi_result[0])
                    root_keys[default_dict_field] = result
                    final_result_dict.update(result)
    return final_result_dict


def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


def ensure_list(data):
    """Ensure data is a list."""
    if not isinstance(data, list):
        return [data]
    return data


def extract_prefix_from_subnet(prefix_list):
    """Extract the prefix length from the IP/Prefix."""
    for item in prefix_list:
        if "prefix_length" in item and item["prefix_length"]:
            item["prefix_length"] = item["prefix_length"].split("/")[-1]
        else:
            item["prefix_length"] = None
    return prefix_list


def format_ios_results(device):
    """Format the results of the show commands for IOS devices."""
    serial = device.get("serial")
    mtus = device.get("mtu", [])
    types = device.get("type", [])
    ips = device.get("ip_addresses", [])
    prefixes = device.get("prefix_length", [])
    macs = device.get("mac_address", [])
    descriptions = device.get("description", [])
    link_statuses = device.get("link_status", [])
    vrfs = device.get("vrfs", [])
    vlans = device.get("vlans", [])
    interface_vlans = device.get("interface_vlans", [])

    # Some data may come across as a dict, needs to be list. Probably should do this elsewhere.
    mtu_list = ensure_list(mtus)
    type_list = ensure_list(types)
    ip_list = ensure_list(ips)
    prefix_list = ensure_list(prefixes)
    mac_list = ensure_list(macs)
    description_list = ensure_list(descriptions)
    link_status_list = ensure_list(link_statuses)
    vlan_list = ensure_list(vlans)
    interface_vlan_list = ensure_list(interface_vlans)

    if vrfs is None:
        vrf_list = []
    else:
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
        interface_dict.setdefault(item["interface"], {})["mac_address"] = (
            item["mac_address"] if item["mac_address"] else ""
        )
    for item in description_list:
        interface_dict.setdefault(item["interface"], {})["description"] = (
            item["description"] if item["description"] else ""
        )
    for item in link_status_list:
        interface_dict.setdefault(item["interface"], {})["link_status"] = True if item["link_status"] == "up" else False

    # Add default values to interfaces
    default_values = {
        "lag": "",
        "untagged_vlan": {},
        "tagged_vlans": [],
        "vrf": {},
        "802.1Q_mode": "",
    }

    vlan_map = {vlan["vlan_id"]: vlan["vlan_name"] for vlan in vlan_list}
    for item in interface_vlan_list:
        try:
            if not item["interface"]:
                continue
            canonical_name = canonical_interface_name(item["interface"])
            interface_dict.setdefault(canonical_name, {})
            mode = item["admin_mode"]
            trunking_vlans = item["trunking_vlans"]
            if mode == "trunk" and trunking_vlans == ["ALL"]:
                interface_dict[canonical_name]["802.1Q_mode"] = "tagged-all"
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": vlan_map[item["native_vlan"]],
                    "id": item["native_vlan"],
                }
            elif mode == "static access":
                interface_dict[canonical_name]["802.1Q_mode"] = "access"
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": vlan_map[item["access_vlan"]],
                    "id": item["access_vlan"],
                }
            elif mode == "trunk" and trunking_vlans != ["ALL"]:
                interface_dict[canonical_name]["802.1Q_mode"] = "tagged"
                tagged_vlans = []
                for vlan_id in trunking_vlans[0].split(","):

                    if "-" in vlan_id:
                        start, end = map(int, vlan_id.split("-"))
                        for id in range(start, end + 1):
                            if str(id) not in vlan_map:
                                print(f"Error: VLAN {id} found on interface, but not found in vlan db.")
                            else:
                                tagged_vlans.append({"name": vlan_map[str(id)], "id": str(id)})
                    else:
                        if vlan_id not in vlan_map:
                            print(f"Error: VLAN {vlan_id} found on interface, but not found in vlan db.")
                        else:
                            tagged_vlans.append({"name": vlan_map[vlan_id], "id": vlan_id})

                interface_dict[canonical_name]["tagged_vlans"] = tagged_vlans
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": vlan_map[item["native_vlan"]],
                    "id": item["native_vlan"],
                }
            else:
                interface_dict[canonical_name]["802.1Q_mode"] = ""
        except KeyError as e:
            print(f"Error: VLAN not found on interface for interface {canonical_name} {e}")
            continue

    for interface in interface_dict.values():
        for key, default in default_values.items():
            interface.setdefault(key, default)

    for interface, data in interface_dict.items():
        ip_addresses = data.get("ip_addresses", {})
        if ip_addresses:
            data["ip_addresses"] = [ip_addresses]

    # Convert interface names to canonical form
    interface_list = []
    for interface_name, interface_info in interface_dict.items():
        interface_list.append({canonical_interface_name(interface_name): interface_info})

    # Change VRF interface names to canonical and create dict of interfaces
    for vrf in vrf_list:
        try:
            for interface in vrf["interfaces"]:
                canonical_name = canonical_interface_name(interface)
                if canonical_name.startswith("VLAN"):
                    canonical_name = canonical_name.replace("VLAN", "Vlan", 1)
                interface_dict.setdefault(canonical_name, {})
                interface_dict[canonical_name]["vrf"] = {
                    "name": vrf["name"],
                }
        except KeyError:
            print(f"Error: VRF configuration on interface {interface} not as expected.")
            continue

    device["interfaces"] = interface_list
    device["serial"] = serial

    del device["mtu"]
    del device["type"]
    del device["ip_addresses"]
    del device["prefix_length"]
    del device["mac_address"]
    del device["description"]
    del device["link_status"]
    del device["vrfs"]
    del device["vlans"]
    del device["interface_vlans"]

    return device


def format_nxos_results(device):
    """Format the results of the show commands for NX-OS devices."""
    interfaces = device.get("interface")
    serial = device.get("serial")
    mtus = device.get("mtu", [])
    types = device.get("type", [])
    ips = device.get("ip_addresses", [])
    prefixes = device.get("prefix_length", [])
    macs = device.get("mac_address", [])
    descriptions = device.get("description", [])
    link_statuses = device.get("link_status", [])
    vrfs_interfaces = device.get("vrf_interfaces", [])
    vlans = device.get("vlans", [])
    interface_vlans = device.get("interface_vlans", [])

    interface_list = ensure_list(interfaces)
    mtu_list = ensure_list(mtus)
    type_list = ensure_list(types)
    ip_list = ensure_list(ips)
    prefix_list = ensure_list(prefixes)
    prefix_list = extract_prefix_from_subnet(prefix_list)
    mac_list = ensure_list(macs)
    description_list = ensure_list(descriptions)
    link_status_list = ensure_list(link_statuses)
    vlan_list = ensure_list(vlans)
    interface_vlan_list = ensure_list(interface_vlans)

    if vrfs_interfaces is None:
        vrfs_interfaces = []
    else:
        vrfs_interfaces = ensure_list(vrfs_interfaces)

    interface_dict = {}
    default_values = {
        "mtu": "",
        "type": "",
        "ip_addresses": [],
        "mac_address": "",
        "description": "",
        "link_status": False,
        "lag": "",
        "vrf": {},
        "802.1Q_mode": "",
        "tagged_vlans": [],
        "untagged_vlan": "",
    }
    for item in interface_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict[canonical_name] = {**default_values}
    for item in mtu_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {})["mtu"] = item["mtu"]
    for item in type_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_type = map_interface_type(item["type"])
        interface_dict.setdefault(canonical_name, {})["type"] = interface_type
    for item in ip_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {})["ip_addresses"] = {"ip_address": item["ip_address"]}
    for item in prefix_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {}).setdefault("ip_addresses", {})["prefix_length"] = item[
            "prefix_length"
        ]
    for item in mac_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {})["mac_address"] = item["mac_address"]
    for item in description_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {})["description"] = item["description"]
    for item in link_status_list:
        canonical_name = canonical_interface_name(item["interface"])
        interface_dict.setdefault(canonical_name, {})["link_status"] = True if item["link_status"] == "up" else False

    vlan_map = {vlan["vlan_id"]: vlan["vlan_name"] for vlan in vlan_list}
    for item in interface_vlan_list:
        try:
            if not item["interface"]:
                continue
            canonical_name = canonical_interface_name(item["interface"])
            interface_dict.setdefault(canonical_name, {})
            mode = item["mode"]
            trunking_vlans = item["trunking_vlans"]

            if mode == "trunk" and trunking_vlans == "1-4094":
                interface_dict[canonical_name]["802.1Q_mode"] = "tagged-all"
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": vlan_map[item["native_vlan"]],
                    "id": item["native_vlan"],
                }
                interface_dict[canonical_name]["tagged_vlans"] = []

            elif mode == "access":
                interface_dict[canonical_name]["802.1Q_mode"] = "access"
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": item["access_vlan_name"],
                    "id": item["access_vlan"],
                }
                interface_dict[canonical_name]["tagged_vlans"] = []

            elif mode == "trunk" and trunking_vlans != "1-4094":

                tagged_vlans = []
                trunking_vlans = vlanconfig_to_list(trunking_vlans)

                for vlan_id in trunking_vlans:

                    if vlan_id not in vlan_map:
                        continue

                    else:
                        tagged_vlans.append({"name": vlan_map[vlan_id], "id": vlan_id})
                interface_dict[canonical_name]["802.1Q_mode"] = "tagged"
                interface_dict[canonical_name]["tagged_vlans"] = tagged_vlans
                interface_dict[canonical_name]["untagged_vlan"] = {
                    "name": vlan_map[item["native_vlan"]],
                    "id": item["native_vlan"],
                }

            else:

                interface_dict[canonical_name]["802.1Q_mode"] = ""
                interface_dict[canonical_name]["untagged_vlan"] = {}
                interface_dict[canonical_name]["tagged_vlans"] = []
        except KeyError as e:
            print(f"Error: VLAN not found on interface for interface {canonical_name} {e}")
            continue

    for interface, data in interface_dict.items():
        ip_addresses = data.get("ip_addresses", {})
        if ip_addresses:
            data["ip_addresses"] = [ip_addresses]
        else:
            data["ip_addresses"] = []

    # Convert interface names to canonical form
    interface_list = []
    for interface_name, interface_info in interface_dict.items():
        interface_list.append({canonical_interface_name(interface_name): interface_info})

    for vrf in vrfs_interfaces:
        try:
            canonical_name = canonical_interface_name(vrf["interface"])
            interface_dict.setdefault(canonical_name, {})
            interface_dict[canonical_name]["vrf"] = {"name": vrf["name"]}
        except KeyError:
            continue

    device["interfaces"] = interface_list
    device["serial"] = serial

    del device["mtu"]
    del device["type"]
    del device["ip_addresses"]
    del device["prefix_length"]
    del device["mac_address"]
    del device["description"]
    del device["link_status"]
    del device["mode"]
    del device["vrf_interfaces"]
    del device["vlans"]
    del device["interface_vlans"]
    del device["interface"]

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
        except Exception as err:  # pylint: disable=broad-exception-caught
            data.update({"failed": True, "failed_reason": f"Error formatting device: {err}"})
    return compiled_results
