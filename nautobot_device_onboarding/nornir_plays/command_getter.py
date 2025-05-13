"""CommandGetter."""

import json
import os
from typing import Dict, Tuple, Union

from django.conf import settings
from nautobot.dcim.models import Platform
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
from nautobot_device_onboarding.utils.helper import check_for_required_file

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


def _get_commands_to_run(yaml_parsed_info, sync_vlans, sync_vrfs, sync_cables, sync_software_version):
    """Using merged command mapper info and look up all commands that need to be run."""
    all_commands = []
    for key, value in yaml_parsed_info.items():
        if key == "pre_processor":
            for pre_processor, v in value.items():
                if not sync_vlans and pre_processor == "vlan_map":
                    continue
                current_root_key = v.get("commands")
                if isinstance(current_root_key, list):
                    # Means their is any "nested" structures. e.g multiple commands
                    for command in v["commands"]:
                        all_commands.append(command)
                else:
                    if isinstance(current_root_key, dict):
                        all_commands.append(current_root_key)
        else:
            # Deduplicate commands + parser key
            current_root_key = value.get("commands")
            if isinstance(current_root_key, list):
                # Means there is a "nested" structures. e.g. multiple commands
                for command in value["commands"]:
                    # If syncing vlans isn't in scope don't run the unneeded commands.
                    if not sync_vlans and key in ["interfaces__tagged_vlans", "interfaces__untagged_vlan"]:
                        continue
                    # If syncing vrfs isn't in scope remove the unneeded commands.
                    if not sync_vrfs and key == "interfaces__vrf":
                        continue
                    # If syncing cables isn't in scope remove the unneeded commands.
                    if not sync_cables and key == "cables":
                        continue
                    # If syncing software_versions isn't in scope remove the unneeded commands.
                    if not sync_software_version and key == "software_version":
                        continue
                    all_commands.append(command)
            else:
                if isinstance(current_root_key, dict):
                    # Means there isn't a "nested" structures. e.g. 1 command
                    # If syncing vlans isn't in scope don't run the unneeded commands.
                    if not sync_vlans and key in ["interfaces__tagged_vlans", "interfaces__untagged_vlan"]:
                        continue
                    # If syncing vrfs isn't in scope remove the unneeded commands.
                    if not sync_vrfs and key == "interfaces__vrf":
                        continue
                    # If syncing cables isn't in scope remove the unneeded commands.
                    if not sync_cables and key == "cables":
                        continue
                    # If syncing software_versions isn't in scope remove the unneeded commands.
                    if not sync_software_version and key == "software_version":
                        continue
                    all_commands.append(current_root_key)
    return deduplicate_command_list(all_commands)


def netmiko_send_commands(
    task: Task, command_getter_yaml_data: Dict, command_getter_job: str, logger, **orig_job_kwargs
):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    if not task.host.platform:
        return Result(host=task.host, result=f"{task.host.name} has no platform set.", failed=True)
    if task.host.platform not in get_all_network_driver_mappings().keys() or not "cisco_wlc_ssh":
        return Result(host=task.host, result=f"{task.host.name} has a unsupported platform set.", failed=True)
    if not command_getter_yaml_data[task.host.platform].get(command_getter_job):
        return Result(
            host=task.host, result=f"{task.host.name} has missing definitions in command_mapper YAML file.", failed=True
        )
    if orig_job_kwargs.get("connectivity_test", False):
        if not tcp_ping(task.host.hostname, task.host.port):
            return Result(
                host=task.host, result=f"{task.host.name} failed connectivity check via tcp_ping.", failed=True
            )
    task.host.data["platform_parsing_info"] = command_getter_yaml_data[task.host.platform]
    commands = _get_commands_to_run(
        command_getter_yaml_data[task.host.platform][command_getter_job],
        orig_job_kwargs.get("sync_vlans", False),
        orig_job_kwargs.get("sync_vrfs", False),
        orig_job_kwargs.get("sync_cables", False),
        orig_job_kwargs.get("sync_software_version", False),
    )
    if (
        orig_job_kwargs.get("sync_cables", False)
        and "cables" not in command_getter_yaml_data[task.host.platform][command_getter_job].keys()
    ):
        logger.error(
            f"{task.host.platform} has missing definitions for cables in command_mapper YAML file. Cables will not be loaded."
        )

    logger.debug(f"Commands to run: {[cmd['command'] for cmd in commands]}")
    # All commands in this for loop are running within 1 device connection.
    for result_idx, command in enumerate(commands):
        send_command_kwargs = {}
        try:
            current_result = task.run(
                task=netmiko_send_command,
                name=command["command"],
                command_string=command["command"],
                read_timeout=60,
                **send_command_kwargs,
            )
            if command.get("parser") in SUPPORTED_COMMAND_PARSERS:
                if isinstance(current_result.result, str):
                    if "Invalid input detected at" in current_result.result:
                        task.results[result_idx].result = []
                        task.results[result_idx].failed = False
                    else:
                        if command["parser"] == "textfsm":
                            try:
                                # Look for custom textfsm templates in the git repo
                                git_template_dir = get_git_repo_parser_path(parser_type="textfsm")
                                if git_template_dir:
                                    if not check_for_required_file(git_template_dir, "index"):
                                        logger.debug(
                                            f"Unable to find required index file in {git_template_dir} for textfsm parsing. Falling back to default templates."
                                        )
                                        git_template_dir = None
                                # Parsing textfsm ourselves instead of using netmikos use_<parser> function to be able to handle exceptions
                                # ourselves. Default for netmiko is if it can't parse to return raw text which is tougher to handle.
                                parsed_output = parse_output(
                                    platform=get_all_network_driver_mappings()[task.host.platform]["ntc_templates"],
                                    template_dir=git_template_dir if git_template_dir else None,
                                    command=command["command"],
                                    data=current_result.result,
                                    try_fallback=bool(git_template_dir),
                                )
                                task.results[result_idx].result = parsed_output
                                task.results[result_idx].failed = False
                            except Exception:  # https://github.com/networktocode/ntc-templates/issues/369
                                task.results[result_idx].result = []
                                task.results[result_idx].failed = False
                        if command["parser"] == "ttp":
                            try:
                                # Parsing ttp ourselves instead of using netmikos use_<parser> function to be able to handle exceptions
                                # ourselves.
                                ttp_template_files = load_files_with_precedence(
                                    filesystem_dir=f"{PARSER_DIR}/ttp", parser_type="ttp"
                                )
                                template_name = f"{task.host.platform}_{command['command'].replace(' ', '_')}.ttp"
                                parser = ttp(
                                    data=current_result.result,
                                    template=ttp_template_files[template_name],
                                )
                                parser.parse()
                                parsed_result = parser.result(format="json")[0]
                                # task.results[result_idx].result = json.loads(json.dumps(parsed_result))
                                task.results[result_idx].result = json.loads(parsed_result)
                                task.results[result_idx].failed = False
                            except Exception:
                                task.results[result_idx].result = []
                                task.results[result_idx].failed = False
            else:
                if command["parser"] == "raw":
                    raw = {"raw": current_result.result}
                    task.results[result_idx].result = json.loads(json.dumps(raw))
                    task.results[result_idx].failed = False
                if command["parser"] == "none":
                    try:
                        jsonified = json.loads(current_result.result)
                        task.results[result_idx].result = jsonified
                        task.results[result_idx].failed = False
                    except Exception:
                        task.result.failed = False
        except NornirSubTaskError:
            # These exceptions indicate that the device is unreachable or the credentials are incorrect.
            # We should fail the task early to avoid trying all commands on a device that is unreachable.
            if type(task.results[result_idx].exception).__name__ == "NetmikoAuthenticationException":
                return Result(host=task.host, result=f"{task.host.name} failed authentication.", failed=True)
            if type(task.results[result_idx].exception).__name__ == "NetmikoTimeoutException":
                return Result(host=task.host, result=f"{task.host.name} SSH Timeout Occured.", failed=True)
            # We don't want to fail the entire subtask if SubTaskError is hit, set result to empty list and failed to False
            # Handle this type or result latter in the ETL process.
            task.results[result_idx].result = []
            task.results[result_idx].failed = False


def _parse_credentials(credentials: Union[SecretsGroup, None], logger: NornirLogger = None) -> Tuple[str, str]:
    """Parse creds from either secretsgroup or settings, return tuple of username/password."""
    username, password = None, None

    if credentials:
        try:
            username = credentials.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
            password = credentials.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            )
        except SecretsGroupAssociation.DoesNotExist:
            pass
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug(f"Error processing credentials from secrets group {credentials.name}: {e}")
            pass
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


def sync_devices_command_getter(job_result, log_level, kwargs):
    """Nornir play to run show commands for sync_devices ssot job."""
    logger = NornirLogger(job_result, log_level)

    if kwargs["csv_file"]:  # ip_addreses will be keys in a dict
        ip_addresses = []
        for ip_address in kwargs["csv_file"]:
            ip_addresses.append(ip_address)
    else:
        ip_addresses = kwargs["ip_addresses"].replace(" ", "").split(",")
        port = kwargs["port"]
        # timeout = kwargs["timeout"]
        platform = kwargs["platform"]
        username, password = _parse_credentials(kwargs["secrets_group"], logger=logger)

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
            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger, compiled_results, kwargs)])
            loaded_secrets_group = None
            for entered_ip in ip_addresses:
                if kwargs["csv_file"]:
                    # get platform if one was provided via csv
                    platform = None
                    platform_id = kwargs["csv_file"][entered_ip]["platform"]
                    if platform_id:
                        platform = Platform.objects.get(id=platform_id)

                    # parse secrets from secrets groups provided via csv
                    secrets_group_id = kwargs["csv_file"][entered_ip]["secrets_group"]
                    if secrets_group_id:
                        new_secrets_group = SecretsGroup.objects.get(id=secrets_group_id)
                        # only update the credentials if the secrets_group specified on a csv row
                        # is different than the secrets group on the previous csv row. This prevents
                        # unnecessary repeat calls to secrets providers.
                        if new_secrets_group != loaded_secrets_group:
                            logger.info(f"Parsing credentials from Secrets Group: {new_secrets_group.name}")
                            loaded_secrets_group = new_secrets_group
                            username, password = _parse_credentials(loaded_secrets_group, logger=logger)
                            if not (username and password):
                                logger.error(f"Unable to onboard {entered_ip}, failed to parse credentials")
                        single_host_inventory_constructed, exc_info = _set_inventory(
                            host_ip=entered_ip,
                            platform=platform,
                            port=kwargs["csv_file"][entered_ip]["port"],
                            username=username,
                            password=password,
                        )
                        if exc_info:
                            logger.error(f"Unable to onboard {entered_ip}, failed with exception {exc_info}")
                            continue
                else:
                    single_host_inventory_constructed, exc_info = _set_inventory(
                        entered_ip, platform, port, username, password
                    )
                    if exc_info:
                        logger.error(f"Unable to onboard {entered_ip}, failed with exception {exc_info}")
                        continue
                nr_with_processors.inventory.hosts.update(single_host_inventory_constructed)
            nr_with_processors.run(
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_devices",
                logger=logger,
                **kwargs,
            )
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Devices Command Getter: {err}")
    return compiled_results


def sync_network_data_command_getter(job_result, log_level, kwargs):
    """Nornir play to run show commands for sync_network_data ssot job."""
    logger = NornirLogger(job_result, log_level)

    try:
        compiled_results = {}
        qs = kwargs["devices"]
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
                        "sync_vlans": kwargs["sync_vlans"],
                        "sync_vrfs": kwargs["sync_vrfs"],
                        "sync_cables": kwargs["sync_cables"],
                        "sync_software_version": kwargs["sync_software_version"],
                    },
                },
            },
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([CommandGetterProcessor(logger, compiled_results, kwargs)])
            nr_with_processors.run(
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_network_data",
                logger=logger,
                **kwargs,
            )
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Network Data Command Getter: {err}")
    return compiled_results
