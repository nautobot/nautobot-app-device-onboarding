"""Command Extraction and Formatting or SSoT Based Jobs."""

import json
import logging
from json.decoder import JSONDecodeError

import jinja2
from django.template import engines
from django.utils.module_loading import import_string
from jdiff import extract_data_from_json
from jinja2.sandbox import SandboxedEnvironment


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


def process_empty_result(iterable_type):
    """Helper to map iterable_type on an empty result."""
    iterable_mapping = {
        "dict": {},
        "str": "",
    }
    return iterable_mapping.get(iterable_type, [])


def normalize_processed_data(processed_data, iterable_type):
    """Helper to normalize the processed data returned from jdiff/jmespath."""
    # If processed_data is an empty data structure, return default based on iterable_type
    if not processed_data:
        return process_empty_result(iterable_type)
    if isinstance(processed_data, str) and not processed_data.isdigit():
        try:
            # If processed_data is a json string try to load it into a python datatype.
            post_processed_data = json.loads(processed_data)
        except (JSONDecodeError, TypeError):
            post_processed_data = processed_data
    else:
        post_processed_data = processed_data
    if isinstance(post_processed_data, list) and len(post_processed_data) == 1:
        if isinstance(post_processed_data[0], str):
            post_processed_data = post_processed_data[0]
        else:
            if isinstance(post_processed_data[0], dict):
                if iterable_type:
                    if iterable_type == "dict":
                        post_processed_data = post_processed_data[0]
            else:
                post_processed_data = post_processed_data[0]
    if not post_processed_data and iterable_type in ["str", "dict"]:
        return process_empty_result(iterable_type)
    if iterable_type == "int":
        return int(post_processed_data)
    if iterable_type == "str":
        return str(post_processed_data)
    return post_processed_data


def extract_and_post_process(parsed_command_output, yaml_command_element, j2_data_context, iter_type, logger):
    """Helper to extract and apply post_processing on a single element."""
    # if parsed_command_output is an empty data structure, no need to go through all the processing.
    if not parsed_command_output:
        return parsed_command_output, normalize_processed_data(parsed_command_output, iter_type)
    j2_env = get_django_env()
    # This just renders the jpath itself if any interpolation is needed.
    jpath_template = j2_env.from_string(yaml_command_element["jpath"])
    j2_rendered_jpath = jpath_template.render(**j2_data_context)
    logger.debug("Post Rendered Jpath: %s", j2_rendered_jpath)
    try:
        if isinstance(parsed_command_output, str):
            try:
                parsed_command_output = json.loads(parsed_command_output)
            except (JSONDecodeError, TypeError):
                logger.debug("Parsed Command Output is a string but not jsonable: %s", parsed_command_output)
        extracted_value = extract_data_from_json(parsed_command_output, j2_rendered_jpath)
    except TypeError as err:
        logger.debug("Error occurred during extraction: %s setting default extracted value to []", err)
        extracted_value = []
    pre_processed_extracted = extracted_value
    if yaml_command_element.get("post_processor"):
        # j2 context data changes obj(hostname) -> extracted_value for post_processor
        j2_data_context["obj"] = extracted_value
        template = j2_env.from_string(yaml_command_element["post_processor"])
        try:
            extracted_processed = template.render(**j2_data_context)
        except jinja2.exceptions.UndefinedError:
            raise ValueError(
                f"Failure Jinja parsing, context: {j2_data_context}. processor: {yaml_command_element['post_processor']}"
            )
    else:
        extracted_processed = extracted_value
    post_processed_data = normalize_processed_data(extracted_processed, iter_type)
    logger.debug("Pre Processed Extracted: %s", pre_processed_extracted)
    logger.debug("Post Processed Data: %s", post_processed_data)
    return pre_processed_extracted, post_processed_data


def perform_data_extraction(host, command_info_dict, command_outputs_dict, logger, skip_list=None):
    """Extract, process data."""
    result_dict = {}

    get_context_from_pre_processor = {}

    for pre_processor_name, field_data in command_info_dict.get("pre_processor", {}).items():
        if skip_list and (pre_processor_name in skip_list):
            continue

        if isinstance(field_data["commands"], dict):
            # only one command is specified as a dict force it to a list.
            loop_commands = [field_data["commands"]]
        else:
            loop_commands = field_data["commands"]
        for show_command_dict in loop_commands:
            final_iterable_type = show_command_dict.get("iterable_type")
            _, current_field_post = extract_and_post_process(
                command_outputs_dict[show_command_dict["command"]],
                show_command_dict,
                {"obj": host.name, "original_host": host.name},
                final_iterable_type,
                logger,
            )
            get_context_from_pre_processor[pre_processor_name] = current_field_post

    for ssot_field, field_data in command_info_dict.items():
        # Do not process a pre_processor
        if ssot_field == "pre_processor":  # Skip fast
            continue
        # Skip if this key shouldn't be synced
        if skip_list and (ssot_field in skip_list):
            continue

        if isinstance(field_data["commands"], dict):
            # only one command is specified as a dict force it to a list.
            loop_commands = [field_data["commands"]]
        else:
            loop_commands = field_data["commands"]
        for show_command_dict in loop_commands:
            final_iterable_type = show_command_dict.get("iterable_type")
            if field_data.get("root_key"):
                original_context = {"obj": host.name, "original_host": host.name}
                merged_context = {**original_context, **get_context_from_pre_processor}
                root_key_pre, root_key_post = extract_and_post_process(
                    command_outputs_dict[show_command_dict["command"]],
                    show_command_dict,
                    merged_context,
                    final_iterable_type,
                    logger,
                )
                result_dict[ssot_field] = root_key_post
            else:
                field_nesting = ssot_field.split("__")
                # for current_nesting in field_nesting:
                if len(field_nesting) > 1:
                    # Means there is "anticipated" data nesting `interfaces__mtu` means final data would be
                    # {"Ethernet1/1": {"mtu": <value>}}
                    for current_key in root_key_post:
                        # current_key is a single iteration from the root_key extracted value. Typically we want this to be
                        # a list of data that we want to become our nested key. E.g. current_key "Ethernet1/1"
                        # These get passed into the render context for the template render to allow nested jpaths to use
                        # the current_key context for more flexible jpath queries.
                        original_context = {"current_key": current_key, "obj": host.name, "original_host": host.name}
                        merged_context = {**original_context, **get_context_from_pre_processor}
                        _, current_key_post = extract_and_post_process(
                            command_outputs_dict[show_command_dict["command"]],
                            show_command_dict,
                            merged_context,
                            final_iterable_type,
                            logger,
                        )
                        result_dict[field_nesting[0]][current_key][field_nesting[1]] = current_key_post
                else:
                    original_context = {"obj": host.name, "original_host": host.name}
                    merged_context = {**original_context, **get_context_from_pre_processor}
                    _, current_field_post = extract_and_post_process(
                        command_outputs_dict[show_command_dict["command"]],
                        show_command_dict,
                        merged_context,
                        final_iterable_type,
                        logger,
                    )
                    result_dict[ssot_field] = current_field_post
        # if command_info_dict.get("validator_pattern"):
        #     # temp validator
        #     if command_info_dict["validator_pattern"] == "not None":
        #         if not extracted_processed:
        #             logger.debug("validator pattern not detected, checking next command.")
        #             continue
        #         else:
        #             logger.debug("About to break the sequence due to valid pattern found")
        #             result_dict[dict_field] = extracted_processed
        #             break
    return result_dict
