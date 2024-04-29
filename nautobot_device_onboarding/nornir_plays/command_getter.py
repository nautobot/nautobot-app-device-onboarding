"""CommandGetter."""

from typing import Dict
from django.conf import settings
from nautobot.dcim.models import Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import SecretsGroup
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from nornir import InitNornir
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory
from nautobot_device_onboarding.nornir_plays.inventory_creator import _set_inventory
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
from nautobot_device_onboarding.nornir_plays.processor import CommandGetterProcessor
from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info
from nautobot_device_onboarding.constants import SUPPORTED_NETWORK_DRIVERS, SUPPORTED_COMMAND_PARSERS

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


def _get_commands_to_run(yaml_parsed_info, sync_vlans, sync_vrfs):
    """Using merged command mapper info and look up all commands that need to be run."""
    all_commands = []
    for key, value in yaml_parsed_info.items():
        if not key.startswith('_metadata'):
            # Deduplicate commands + parser key
            current_root_key = value.get("commands")
            if isinstance(current_root_key, list):
                # Means their is any "nested" structures. e.g multiple commands
                for command in value["commands"]:
                    # If syncing vlans isn't inscope don't run the unneeded commands.
                    if not sync_vlans and key in ["interfaces__tagged_vlans", "interfaces__untagged_vlan"]:
                        continue
                    # If syncing vrfs isn't inscope remove the unneeded commands.
                    if not sync_vrfs and key == "interfaces__vrf":
                        continue
                    all_commands.append(command)
            else:
                if isinstance(current_root_key, dict):
                    # If syncing vlans isn't inscope don't run the unneeded commands.
                    if not sync_vlans and key in ["interfaces__tagged_vlans", "interfaces__untagged_vlan"]:
                        continue
                    # If syncing vrfs isn't inscope remove the unneeded commands.
                    if not sync_vrfs and key == "interfaces__vrf":
                        continue
                    # Means their isn't a "nested" structures. e.g 1 command
                    all_commands.append(current_root_key)
    return deduplicate_command_list(all_commands)


def netmiko_send_commands(task: Task, command_getter_yaml_data: Dict, command_getter_job: str, **orig_job_kwargs):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    if not task.host.platform:
        return Result(host=task.host, result=f"{task.host.name} has no platform set.", failed=True)
    if task.host.platform not in SUPPORTED_NETWORK_DRIVERS:
        return Result(host=task.host, result=f"{task.host.name} has a unsupported platform set.", failed=True)
    if not command_getter_yaml_data[task.host.platform].get(command_getter_job):
        return Result(host=task.host, result=f"{task.host.name} has missing definitions in command_mapper YAML file.", failed=True)
    task.host.data["platform_parsing_info"] = command_getter_yaml_data[task.host.platform]
    commands = _get_commands_to_run(
        command_getter_yaml_data[task.host.platform][command_getter_job],
        orig_job_kwargs.get('sync_vlans', False),
        orig_job_kwargs.get('sync_vrfs', False)
    )
    # All commands in this for loop are running within 1 device connection.
    for command in commands:
        send_command_kwargs = {}
        if command.get("parser") in SUPPORTED_COMMAND_PARSERS:
            send_command_kwargs = {f"use_{command['parser']}": True}
        try:
            task.run(
                task=netmiko_send_command,
                name=command["command"],
                command_string=command["command"],
                read_timeout=60,
                **send_command_kwargs
            )
        except NornirSubTaskError as err:
            return Result(
                host=task.host,
                changed=False,
                result=f"{command['command']}: E0001 - Textfsm template issue. The error was {err}",
                failed=True,
            )


def _parse_credentials(credentials):
    """Parse and return dictionary of credentials."""
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
            try:
                secret = credentials.get_secret_value(
                    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                secret = None
        except Exception:  # pylint: disable=broad-exception-caught
            return (None, None, None)
    else:
        username = settings.NAPALM_USERNAME
        password = settings.NAPALM_PASSWORD
        secret = settings.NAPALM_ARGS.get("secret", None)
    return (username, password, secret)


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
        username, password, secret = _parse_credentials(kwargs["secrets_group"])

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
            nr_with_processors = nornir_obj.with_processors(
                [CommandGetterProcessor(logger, compiled_results, kwargs)]
            )
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
                            username, password, secret = _parse_credentials(loaded_secrets_group)
                            if not (username and password):
                                logger.error(f"Unable to onboard {entered_ip}, failed to parse credentials")
                        single_host_inventory_constructed = _set_inventory(
                            host_ip=entered_ip,
                            platform=platform,
                            port=kwargs["csv_file"][entered_ip]["port"],
                            username=username,
                            password=password,
                        )
                else:
                    single_host_inventory_constructed = _set_inventory(entered_ip, platform, port, username, password)
                nr_with_processors.inventory.hosts.update(single_host_inventory_constructed)
            nr_with_processors.run(
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_devices",
                **kwargs,
            )
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Devices Command Getter: {err}")
    print(f"compiled_results: {compiled_results}")
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
                        "network_driver_mappings": SUPPORTED_NETWORK_DRIVERS,
                        "sync_vlans": kwargs["sync_vlans"],
                        "sync_vrfs": kwargs["sync_vrfs"],
                    },
                },
            },
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors(
                [CommandGetterProcessor(logger, compiled_results, kwargs)]
            )
            nr_with_processors.run(
                task=netmiko_send_commands,
                command_getter_yaml_data=nr_with_processors.inventory.defaults.data["platform_parsing_info"],
                command_getter_job="sync_network_data",
                **kwargs
            )
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.info(f"Error During Sync Network Data Command Getter: {err}")
        return err
    print(f"compiled_results: {compiled_results}")

    return compiled_results
