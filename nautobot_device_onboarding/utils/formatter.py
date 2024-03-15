"""Formatter."""

import json
import os

import yaml
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json
from jinja2.sandbox import SandboxedEnvironment
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
            j2_rendered_jpath = jpath_template.render({"obj": host.name})
            if not task_result.failed:
                if isinstance(task_result.result, str):
                    try:
                        result_to_json = json.loads(task_result.result)
                        print("result_to_json_1: ", result_to_json)
                        extracted_value = extract_data_from_json(result_to_json, j2_rendered_jpath)
                    except json.decoder.JSONDecodeError:
                        extracted_value = None
                else:
                    print(f"result_to_json_2:  {task_result.result}")
                    extracted_value = extract_data_from_json(task_result.result, j2_rendered_jpath)
                if show_command.get("post_processor"):
                    template = j2_env.from_string(show_command["post_processor"])
                    print(f"extracted_value_2: {extracted_value}")
                    extracted_processed = template.render({"obj": extracted_value, "original_host": host.name})
                else:
                    print(f"extracted_value_3: {extracted_value}")
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
            print(f"default dict field: {default_dict_field}")
            result = perform_data_extraction(host, default_dict_field, command_info, jinja_env, multi_result[0])
            final_result_dict.update(result)
        else:
            # Means their is a "nested" structures. Priority
            for dict_field, nested_command_info in command_info.items():
                print(f"default dict field: {default_dict_field}")
                result = perform_data_extraction(host, dict_field, nested_command_info, jinja_env, multi_result[0])
                final_result_dict.update(result)
    return final_result_dict


def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")
