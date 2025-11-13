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


def netmiko_send_commands(
    task: Task,
    command_getter_yaml_data: Dict,
    command_getter_job: str,
    logger,
    nautobot_job,
    **kwargs,
):
    """Run platform-specific commands with optional parsing and logging."""

    command_exclusions = kwargs.get("command_exclusions", [])
    connectivity_test = kwargs.get("connectivity_test", False)
    # sync_cables = kwargs.get("sync_cables", False)

    # ---- 1. Validation -------------------------------------------------------
    validation_result = _validate_task(task, command_getter_yaml_data, command_getter_job)
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
        yaml_parsed_info=command_getter_yaml_data[task.host.platform][command_getter_job],
        skip_list=command_exclusions,
    )
    logger.debug(f"Commands to run: {[cmd['command'] for cmd in commands]}")

    # ---- 3. Command Execution & Parsing -------------------------------------
    for idx, command in enumerate(commands):
        try:
            current_result = _run_command(task, command)
            _handle_command_result(task, idx, command, current_result, nautobot_job, logger)
        except NornirSubTaskError as e:
            return _handle_subtask_error(task, idx, e)

    return Result(host=task.host, result="Commands executed successfully.", failed=False)


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


def _run_command(task, command):
    """Execute a single Netmiko command."""
    return task.run(
        task=netmiko_send_command,
        name=command["command"],
        command_string=command["command"],
        read_timeout=60,
    )


def _handle_command_result(task, idx, command, current_result, nautobot_job, logger):
    """Parse and store results based on parser type."""
    raw_output = current_result.result
    parser_type = command.get("parser")

    # Debug output
    if nautobot_job.debug:
        log_message = format_log_message(pprint.pformat(raw_output))
        logger.debug(f"Result of '{command['command']}' command:<br><br>{log_message}")

    # Handle invalid input gracefully
    if isinstance(raw_output, str) and "Invalid input detected" in raw_output:
        task.results[idx].result = []
        task.results[idx].failed = False
        return

    if parser_type in SUPPORTED_COMMAND_PARSERS:
        parsed = _parse_command_output(task, command, raw_output, parser_type, nautobot_job, logger)
        task.results[idx].result = parsed
        task.results[idx].failed = False
    else:
        task.results[idx].result = _handle_raw_or_none(raw_output, parser_type)
        task.results[idx].failed = False


def _parse_command_output(task, command, raw_output, parser_type, nautobot_job, logger):
    """Dispatch to the appropriate parser."""
    try:
        if parser_type == "textfsm":
            return _parse_textfsm(task, command, raw_output, nautobot_job, logger)
        elif parser_type == "ttp":
            return _parse_ttp(task, command, raw_output)
    except Exception as e:
        logger.warning(f"Parsing failed for {command['command']}: {e}")
        return []
    return []


def _parse_textfsm(task, command, data, nautobot_job, logger):
    git_template_dir = get_git_repo_parser_path("textfsm")
    if git_template_dir and not check_for_required_file(git_template_dir, "index"):
        logger.debug(f"Missing index file in {git_template_dir}, falling back to defaults.")
        git_template_dir = None

    parsed_output = parse_output(
        platform=get_all_network_driver_mappings()[task.host.platform]["ntc_templates"],
        template_dir=git_template_dir,
        command=command["command"],
        data=data,
        try_fallback=bool(git_template_dir),
    )

    if nautobot_job.debug:
        logger.debug(format_log_message(pprint.pformat(parsed_output)))

    return parsed_output


def _parse_ttp(task, command, data):
    ttp_template_files = load_files_with_precedence(f"{PARSER_DIR}/ttp", "ttp")
    template_name = f"{task.host.platform}_{command['command'].replace(' ', '_')}.ttp"
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


def _handle_subtask_error(task, idx, exception):
    """Handle connection/authentication errors gracefully."""
    exc_type = type(task.results[idx].exception).__name__

    if exc_type == "NetmikoAuthenticationException":
        return Result(host=task.host, result=f"{task.host.name} failed authentication.", failed=True)
    if exc_type == "NetmikoTimeoutException":
        return Result(host=task.host, result=f"{task.host.name} SSH timeout occurred.", failed=True)

    task.results[idx].result = []
    task.results[idx].failed = False

    return None


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
            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger, compiled_results, job)])
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
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_devices",
                logger=logger,
                nautobot_job=job,
                # command_getter_yaml_exclusions=command_exclusions,
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
                        # "sync_vlans": job.sync_vlans,
                        # "sync_vrfs": job.sync_vrfs,
                        # "sync_cables": job.sync_cables,
                        # "sync_software_version": job.sync_software_version,
                    },
                },
            },
        ) as nornir_obj:

            command_exclusions = {
                "interfaces__tagged_vlans": not job.sync_vlans,
                "vlan_map": not job.sync_vlans,
                "interfaces__untagged_vlan": not job.sync_vlans,
                "interfaces__vrf": not job.sync_vrfs,
                "cables": not job.sync_cables,
                "software_version": not job.sync_software_version,
            }
            exclusions = [k for k, v in command_exclusions.items() if v]

            # commands = _get_commands_to_run(
            #     command_getter_yaml_data[task.host.platform][command_getter_job],
            #     # getattr(nautobot_job, "sync_vlans", False),
            #     # getattr(nautobot_job, "sync_vrfs", False),
            #     # getattr(nautobot_job, "sync_cables", False),
            #     # getattr(nautobot_job, "sync_software_version", False),
            # )


            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger, compiled_results, job)])
            nr_with_processors.run(
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_network_data",
                logger=logger,
                command_exclusions=exclusions,
                connectivity_test=job.connectivity_test,
                sync_cables=job.sync_cables,
                # nautobot_job=job,
            )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Network Data Command Getter: {traceback.format_exc()}")
    return compiled_results
