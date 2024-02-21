"""Formatter."""

import os

import yaml
from django.template import engines
from jdiff import extract_data_from_json
from jinja2 import Environment

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


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


def extract_show_data(host, multi_result, command_getter_type):
    """Take a result of show command and extra specific needed data.

    Args:
        host (host): host from task
        multi_result (multiResult): multiresult object from nornir
        command_getter_type (str): to know what dict to pull, device_onboarding or network_importer.
    """
    jinja_env = Environment(autoescape=True, trim_blocks=True, lstrip_blocks=False)
    jinja_env.filters = engines["jinja"].env.filters

    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]

    result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if not default_dict_field == "use_textfsm":
            if command_info["command"] == multi_result[0].name:
                j2_rendered_jpath_template = jinja_env.from_string(command_info["jpath"])
                j2_rendered_jpath = j2_rendered_jpath_template.render(host_info=host.name)
                extracted_value = extract_data_from_json(multi_result[0].result, j2_rendered_jpath)
                if command_info.get("post_processor"):
                    transform_template = jinja_env.from_string(command_info["post_processor"])
                    extracted_processed = transform_template.render(obj=extracted_value)
                else:
                    if isinstance(extracted_value, list) and len(extracted_value) == 1:
                        extracted_processed = extracted_value[0]
                result_dict[default_dict_field] = extracted_processed
    return result_dict
