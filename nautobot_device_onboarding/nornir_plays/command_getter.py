"""CommandGetter."""

import json
import os
import pprint
import traceback
from functools import lru_cache
from typing import Dict, Tuple, Union

from django.conf import settings
from nautobot.dcim.utils import get_all_network_driver_mappings
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import SecretsGroup, SecretsGroupAssociation
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from netutils.ping import tcp_ping
from nornir import InitNornir
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from ntc_templates.parse import parse_output
from ttp import ttp

from nautobot_device_onboarding.constants import SUPPORTED_COMMAND_PARSERS
from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory
from nautobot_device_onboarding.nornir_plays.inventory_creator import _set_inventory
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
from nautobot_device_onboarding.nornir_plays.processor import CommandGetterProcessor
from nautobot_device_onboarding.nornir_plays.transform import (
    add_platform_parsing_info,
    get_git_repo_parser_path,
    load_files_with_precedence,
)
from nautobot_device_onboarding.utils.helper import check_for_required_file, format_log_message
from nautobot_device_onboarding.nornir_plays.formatter import perform_data_extraction
from jsonschema import ValidationError, validate
from nautobot_device_onboarding.nornir_plays.schemas import NETWORK_DEVICES_SCHEMA, NETWORK_DATA_SCHEMA

PARSER_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "parsers"))

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)
InventoryPluginRegister.register("empty-inventory", EmptyInventory)


def deduplicate_command_list(data):
    """Deduplicates a list of dictionaries based on 'command' and 'parser' keys.

    Args:
        data: A list of dictionaries.

    Returns:
        A new list containing only unique elements based on 'command' and 'parser'.
    """
    seen = set()
    unique_list = []
    for item in data:
        # Create a tuple containing only 'command' and 'parser' for comparison
        key = (item["command"], item["parser"])
        if key not in seen:
            seen.add(key)
            unique_list.append(item)
    return unique_list


def _get_commands_to_run(yaml_parsed_info, skip_list=None):
    """Return a deduplicated list of commands to run based on YAML info and sync flags."""
    all_commands = []

    for key, value in yaml_parsed_info.items():
        # Handle pre_processor section separately
        if key == "pre_processor":
            for pre_processor_name, pre_processor_value in value.items():
                # Skip if this key shouldn't be synced
                if skip_list and (pre_processor_name in skip_list):
                    continue
                commands = pre_processor_value.get("commands", [])
                if isinstance(commands, dict):
                    all_commands.append(commands)
                elif isinstance(commands, list):
                    all_commands.extend(commands)
            continue  # move to next key

        # Skip if this key shouldn't be synced
        if skip_list and (key in skip_list):
            continue

        commands = value.get("commands", [])
        if isinstance(commands, dict):
            all_commands.append(commands)
        elif isinstance(commands, list):
            all_commands.extend(commands)

    return deduplicate_command_list(all_commands)


def get_device_facts(  # legacy `netmiko_send_commands`
    task: Task,
    command_getter_yaml_data: Dict,
    command_getter_schema,
    command_getter_section_name: str,  # legacy `job name`: sync_device, sync_network etc.
    logger,
    **kwargs,
):
    """Run platform-specific commands with optional parsing and logging."""

    command_exclusions = kwargs.get("command_exclusions")
    connectivity_test = kwargs.get("connectivity_test", False)

    # ---- 1. Validation -------------------------------------------------------
    validation_result = _validate_task(task, command_getter_yaml_data, command_getter_section_name)
    if validation_result:
        return validation_result

    if connectivity_test and not _check_connectivity(task):
        return Result(
            host=task.host,
            result=f"{task.host.name} failed connectivity check via tcp_ping.",
            failed=True,
        )

    task.host.data["platform_parsing_info"] = command_getter_yaml_data[task.host.platform]

    # ---- 2. Command Preparation ---------------------------------------------
    commands = _get_commands_to_run(
        yaml_parsed_info=command_getter_yaml_data[task.host.platform][command_getter_section_name],
        skip_list=command_exclusions,
    )
    logger.debug(f"Commands to run: {[cmd['command'] for cmd in commands]}")

    # ---- 3. Command Execution & Parsing -------------------------------------
    host_facts = {}

    for idx, command in enumerate(commands):
        command_name = command["command"]
        try:
            command_result = task.run(
                task=netmiko_send_command,
                name=command_name,
                command_string=command_name,
                read_timeout=60,
            )
        except NornirSubTaskError as exc:  # proceed if `netmiko_send_command` exception
            return _handle_netmiko_error(task=task, exception=exc)

        parsed_result = parse_command_result(
            network_driver=task.host.platform,
            command=command_name,
            raw_output=command_result.result,
            parser_type=command.get("parser"),
            logger=logger,
        )

        formatted_result = perform_data_extraction(
            task.host,
            command_getter_yaml_data[task.host.platform][command_getter_section_name],
            parsed_result,
            logger,
            skip_list=command_exclusions,
        )

        host_facts[command_name] = formatted_result

    # ---- 4. Schema Validation  -----------------------------------------------
    try:
        validate(host_facts, command_getter_schema)
    except ValidationError as err:
        logger.debug(f"Schema validation failed for {task.host.name}. Error: {err}.")
        return Result(host=task.host, result="Schema validation failed.", failed=True)

    logger.debug(f"Facts getter collected, parsed and formatted successfully: {task.host.name} {host_facts}")

    return Result(host=task.host, result=host_facts, failed=False)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def _validate_task(task, yaml_data, job):
    """Check platform and YAML definition validity."""
    platform = task.host.platform
    if not platform:
        return Result(host=task.host, result=f"{task.host.name} has no platform set.", failed=True)

    supported_platforms = get_all_network_driver_mappings().keys()
    if platform not in supported_platforms and platform != "cisco_wlc_ssh":
        return Result(host=task.host, result=f"{task.host.name} has an unsupported platform.", failed=True)

    if not yaml_data.get(platform, {}).get(job):
        return Result(
            host=task.host,
            result=f"{task.host.name} missing definitions in command_mapper YAML.",
            failed=True,
        )

    return None


def _check_connectivity(task):
    """Perform TCP ping check."""
    return tcp_ping(task.host.hostname, task.host.port)


def parse_command_result(network_driver, command, raw_output, parser_type, logger):
    """Parse and store results based on parser type."""

    # # Debug output
    # if nautobot_job.debug:
    #     log_message = format_log_message(pprint.pformat(raw_output))
    #     logger.debug(f"Result of '{command['command']}' command:<br><br>{log_message}")

    # TODO(mzb): Implement conditional formatter
    logger.debug(f"Result of '{command}' command:<br><br>{raw_output}")

    # Handle invalid input gracefully
    # TODO(mzb): This probably should fail tasks execution or not ? Or just fail via schema check?
    if isinstance(raw_output, str) and "Invalid input detected" in raw_output:
        return []

    if parser_type in SUPPORTED_COMMAND_PARSERS:
        parsed = _parse_command_output(network_driver, command, raw_output, parser_type, logger)
    else:
        parsed = _handle_raw_or_none(raw_output, parser_type)

    return parsed


def _parse_command_output(network_driver, command, raw_output, parser_type, logger):
    """Dispatch to the appropriate parser."""
    try:
        if parser_type == "textfsm":
            return _parse_textfsm(network_driver, command, raw_output, logger)
        elif parser_type == "ttp":
            return _parse_ttp(network_driver, command, raw_output)
    except Exception as e:
        logger.warning(f"Parsing failed for {command}: {e}")
        return []
    return []


def _parse_textfsm(network_driver, command, data, logger):
    git_template_dir = get_git_repo_parser_path("textfsm")
    if git_template_dir and not check_for_required_file(git_template_dir, "index"):
        logger.debug(f"Missing index file in {git_template_dir}, falling back to defaults.")
        git_template_dir = None

    parsed_output = parse_output(
        platform=get_all_network_driver_mappings()[network_driver]["ntc_templates"],
        template_dir=git_template_dir,
        command=command,
        data=data,
        try_fallback=bool(git_template_dir),
    )

    # if nautobot_job.debug:
    #     logger.debug(format_log_message(pprint.pformat(parsed_output)))

    # TODO(mzb): Implement conditional log formatter
    logger.debug(parsed_output)

    return parsed_output


def _parse_ttp(network_driver, command, data):
    ttp_template_files = load_files_with_precedence(f"{PARSER_DIR}/ttp", "ttp")
    template_name = f"{network_driver}_{command.replace(' ', '_')}.ttp"
    parser = ttp(data=data, template=ttp_template_files[template_name])
    parser.parse()
    return json.loads(parser.result(format="json")[0])


def _handle_raw_or_none(raw_output, parser_type):
    if parser_type == "raw":
        return {"raw": raw_output}
    if parser_type == "none":
        try:
            return json.loads(raw_output)
        except Exception:
            return []
    return []


def _handle_netmiko_error(task, exception):
    """Handle connection/authentication errors gracefully."""
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

    if isinstance(exception, NetmikoAuthenticationException):
        fail_message = f"Authentication failed for {task.host.name}"
    elif isinstance(exception, NetmikoTimeoutException):
        fail_message = f"Timeout failure for {task.host.name}"
    else:
        fail_message = f"Task failed due to {exception}"

    return Result(host=task.host, result=fail_message, failed=True)


@lru_cache(maxsize=None)
def _parse_credentials(secrets_group: Union[SecretsGroup, None], logger: NornirLogger = None) -> Tuple[str, str]:
    """Parse creds from either secretsgroup or settings, return tuple of username/password."""
    username, password = None, None
    if secrets_group:
        logger.info(f"Parsing credentials from Secrets Group: {secrets_group.name}")
        try:
            username = secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
            password = secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            )
        except SecretsGroupAssociation.DoesNotExist:
            pass
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug(f"Error processing credentials from secrets group {secrets_group.name}: {e}")
    else:
        username = settings.NAPALM_USERNAME
        password = settings.NAPALM_PASSWORD

    missing_creds = []
    for cred_var in ["username", "password"]:
        if not locals().get(cred_var, None):
            missing_creds.append(cred_var)
    if missing_creds:
        logger.debug(f"Missing credentials for {missing_creds}")
    return (username, password)


def sync_devices_command_getter(job, log_level):
    """Nornir play to run show commands for sync_devices ssot job."""
    logger = NornirLogger(job.job_result, log_level)

    # Initiate Nornir instance with empty inventory
    try:
        compiled_results = {}
        with InitNornir(
            runner=NORNIR_SETTINGS.get("runner"),
            logging={"enabled": False},
            inventory={
                "plugin": "empty-inventory",
            },
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger)])
            for ip_address, values in job.ip_address_inventory.items():
                # parse secrets from secrets groups provided via csv
                secrets_group = values["secrets_group"]
                if secrets_group:
                    # The _parse_credentials function is cached. This prevents unnecessary repeat calls to secrets providers.
                    username, password = _parse_credentials(secrets_group, logger=logger)
                    if not username or not password:
                        logger.error(f"Unable to onboard {values['original_ip_address']}, failed to parse credentials")
                    single_host_inventory_constructed, exc_info = _set_inventory(
                        host_ip=ip_address,
                        platform=values["platform"],
                        port=values["port"],
                        username=username,
                        password=password,
                    )
                    if exc_info:
                        logger.error(
                            f"Unable to onboard {values['original_ip_address']}, failed with exception {exc_info}"
                        )
                        continue
                nr_with_processors.inventory.hosts.update(single_host_inventory_constructed)

            nr_with_processors.run(
                task=get_device_facts,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_section_name="sync_devices",
                command_getter_schema=NETWORK_DEVICES_SCHEMA,
                logger=logger,
                command_exclusions=None,
            )


    except Exception as err:  # pylint: disable=broad-exception-caught
        try:
            if job.debug:
                traceback_str = format_log_message(traceback.format_exc())
                logger.warning(f"Error During Sync Devices Command Getter:<br><br>{err}<br>{traceback_str}")
            else:
                logger.warning(f"Error During Sync Devices Command Getter: {err}")
        except:  # noqa: E722, S110
            logger.warning(f"Error During Sync Devices Command Getter: {err}")
    return compiled_results


def sync_network_data_command_getter(job, log_level):
    """Nornir play to run show commands for sync_network_data ssot job."""
    logger = NornirLogger(job.job_result, log_level)

    try:
        compiled_results = {}
        qs = job.filtered_devices
        if not qs:
            return None
        with InitNornir(
            runner=NORNIR_SETTINGS.get("runner"),
            logging={"enabled": False},
            inventory={
                "plugin": "nautobot-inventory",
                "options": {
                    "credentials_class": NORNIR_SETTINGS.get("credentials"),
                    "queryset": qs,
                    "defaults": {
                        "platform_parsing_info": add_platform_parsing_info(),
                        "network_driver_mappings": list(get_all_network_driver_mappings().keys()),
                    },
                },
            },
        ) as nornir_obj:

            command_exclusions = {
                "cables": not job.sync_cables,
                "interfaces__tagged_vlans": not job.sync_vlans,
                "interfaces__untagged_vlan": not job.sync_vlans,
                "interfaces__vrf": not job.sync_vrfs,
                "software_version": not job.sync_software_version,
                "vlan_map": not job.sync_vlans,
            }
            exclusions = [k for k, v in command_exclusions.items() if v]

            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger)])
            nr_with_processors.run(
                task=get_device_facts,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_section_name="sync_network_data",
                command_getter_schema=NETWORK_DATA_SCHEMA,
                logger=logger,
                command_exclusions=exclusions,
                connectivity_test=job.connectivity_test,
            )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Network Data Command Getter: {traceback.format_exc()}")
    return compiled_results
