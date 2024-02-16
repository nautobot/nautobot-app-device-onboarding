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


def extract_show_data(host, multi_result, command_getter_type):
    """Take a result of show command and extra specific needed data.

    Args:
        host (host): host from task
        multi_result (multiResult): multiresult object from nornir
    """
    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]

    result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if not default_dict_field == "use_textfsm":
            if command_info["command"] == multi_result[0].name:
                extracted_value = extract_data_from_json(multi_result[0].result, command_info["jpath"])
                if isinstance(extracted_value, list) and len(extracted_value) == 1:
                    extracted_value = extracted_value[0]
                if "/" in extracted_value and default_dict_field == "mask_length":
                    extracted_value = extracted_value.split("/")[1]
                result_dict[default_dict_field] = extracted_value
    return result_dict
