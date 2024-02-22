"""Formatter."""

import os

import yaml
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json

# from jinja2 import exceptions as jinja_errors
from jinja2.sandbox import SandboxedEnvironment
from nautobot.core.utils.data import render_jinja2

# from nautobot_device_onboarding.exceptions import OnboardException
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


# def render_jinja_template(obj, template):
#     """
#     Helper function to render Jinja templates.

#     Args:
#         obj (Device): The Device object from Nautobot.
#         template (str): A Jinja2 template to be rendered.

#     Returns:
#         str: The ``template`` rendered.

#     Raises:
#         NornirNautobotException: When there is an error rendering the ``template``.
#     """
#     try:
#         return render_jinja2(template_code=template, context={"obj": obj})
#     except jinja_errors.UndefinedError as error:
#         error_msg = (
#             "`E3019:` Jinja encountered and UndefinedError`, check the template for missing variable definitions.\n"
#             f"Template:\n{template}\n"
#             f"Original Error: {error}"
#         )
#         raise OnboardException(error_msg) from error

#     except jinja_errors.TemplateSyntaxError as error:  # Also catches subclass of TemplateAssertionError
#         error_msg = (
#             f"`E3020:` Jinja encountered a SyntaxError at line number {error.lineno},"
#             f"check the template for invalid Jinja syntax.\nTemplate:\n{template}\n"
#             f"Original Error: {error}"
#         )
#         raise OnboardException(error_msg) from error
#     # Intentionally not catching TemplateNotFound errors since template is passes as a string and not a filename
#     except jinja_errors.TemplateError as error:  # Catches all remaining Jinja errors
#         error_msg = (
#             "`E3021:` Jinja encountered an unexpected TemplateError; check the template for correctness\n"
#             f"Template:\n{template}\n"
#             f"Original Error: {error}"
#         )
#         raise OnboardException(error_msg) from error


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
    jinja_env = get_django_env()

    host_platform = host.platform
    if host_platform == "cisco_xe":
        host_platform = "cisco_ios"
    command_jpaths = host.data["platform_parsing_info"]

    result_dict = {}
    for default_dict_field, command_info in command_jpaths[command_getter_type].items():
        if not default_dict_field == "use_textfsm":
            if command_info["command"] == multi_result[0].name:
                jpath_template = jinja_env.from_string(command_info["jpath"])
                j2_rendered_jpath = jpath_template.render({"obj": host.name})
                # j2_rendered_jpath = render_jinja_template(obj=host.name, template=command_info["jpath"])
                extracted_value = extract_data_from_json(multi_result[0].result, j2_rendered_jpath)
                # print(extracted_value)
                if command_info.get("post_processor"):
                    template = jinja_env.from_string(command_info["post_processor"])
                    extracted_processed = template.render({"obj": extracted_value})
                    # extracted_processed = render_jinja_template(
                    #     obj=extracted_value, template=command_info["post_processor"]
                    # )
                    # print(extracted_processed)
                else:
                    extracted_processed = extracted_value
                    if isinstance(extracted_value, list) and len(extracted_value) == 1:
                        extracted_processed = extracted_value[0]
                result_dict[default_dict_field] = extracted_processed
    return result_dict
