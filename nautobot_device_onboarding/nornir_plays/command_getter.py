"""CommandGetter."""

# pylint: disable=relative-beyond-top-level
from django.conf import settings
from nautobot.dcim.models import Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import SecretsGroup
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from nornir import InitNornir
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.plugins.inventory import InventoryPluginRegister, TransformFunctionRegister
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

from nautobot_device_onboarding.constants import NETMIKO_TO_NAPALM_STATIC
from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
from nautobot_device_onboarding.nornir_plays.processor import ProcessorDO
from nautobot_device_onboarding.nornir_plays.inventory_creator import _set_inventory
from nautobot_device_onboarding.utils.formatter import format_results
from nautobot_device_onboarding.utils.helper import add_platform_parsing_info

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)
InventoryPluginRegister.register("empty-inventory", EmptyInventory)
TransformFunctionRegister.register("transform_to_add_command_parser_info", add_platform_parsing_info)


def deduplicate_command_list(data):
    """Deduplicates a list of dictionaries based on 'command' and 'use_textfsm' keys.

    Args:
        data: A list of dictionaries.

    Returns:
        A new list containing only unique elements based on 'command' and 'use_textfsm'.
    """
    seen = set()
    unique_list = []
    for item in data:
        # Create a tuple containing only 'command' and 'use_textfsm' for comparison
        key = (item["command"], item["use_textfsm"])
        if key not in seen:
            seen.add(key)
            unique_list.append(item)
    return unique_list


def _get_commands_to_run(yaml_parsed_info, command_getter_job):
    """Load yaml file and look up all commands that need to be run."""
    all_commands = []
    for _, value in yaml_parsed_info[command_getter_job].items():
        # Deduplicate commands + parser key
        if value.get("commands"):
            # Means their isn't any "nested" structures.
            for command in value["commands"]:
                all_commands.append(command)
        else:
            # Means their is a "nested" structures.
            for _, nested_command_info in value.items():
                if isinstance(nested_command_info, dict):
                    for command in nested_command_info["commands"]:
                        all_commands.append(command)
    return deduplicate_command_list(all_commands)


def netmiko_send_commands(task: Task, command_getter_job: str):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    if not task.host.platform:
        return Result(host=task.host, result=f"{task.host.name} has no platform set.", failed=True)
    if task.host.platform not in list(NETMIKO_TO_NAPALM_STATIC.keys()):
        return Result(host=task.host, result=f"{task.host.name} has a unsupported platform set.", failed=True)
    commands = _get_commands_to_run(task.host.data["platform_parsing_info"], command_getter_job)
    for command in commands:
        try:
            task.run(
                task=netmiko_send_command,
                name=command["command"],
                command_string=command["command"],
                use_textfsm=command["use_textfsm"],
                read_timeout=60,
            )
        except NornirSubTaskError:
            Result(
                host=task.host,
                changed=False,
                result=f"{command['command']}: E0001 - Textfsm template issue.",
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
            except Exception:
                secret = None
        except Exception:
            return (None, None, None)
    else:
        username = settings.NAPALM_USERNAME
        password = settings.NAPALM_PASSWORD
        secret = settings.NAPALM_ARGS.get("secret", None)
    return (username, password, secret)


def command_getter_do(job_result, log_level, kwargs):
    """Nornir play to run show commands."""
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
        logger = NornirLogger(job_result, log_level=0)
        compiled_results = {}
        with InitNornir(
            runner=NORNIR_SETTINGS.get("runner"),
            logging={"enabled": False},
            inventory={
                "plugin": "empty-inventory",
                # Can't use this since we're dynamically generating inventory on demand.
                # "transform_function": "transform_to_add_command_parser_info",
            },
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([ProcessorDO(logger, compiled_results, kwargs)])
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
            logger.info(nr_with_processors.inventory.hosts)
            nr_with_processors.run(task=netmiko_send_commands, command_getter_job="device_onboarding")
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.error(err)
    return compiled_results


def command_getter_ni(job_result, log_level, kwargs):
    """Process onboarding task from ssot-ni job."""
    logger = NornirLogger(job_result, log_level)
    try:
        compiled_results = {}
        # qs = get_job_filter(kwargs)
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
                },
                "transform_function": "transform_to_add_command_parser_info",
            },
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([ProcessorDO(logger, compiled_results, kwargs)])
            nr_with_processors.run(task=netmiko_send_commands, command_getter_job="network_importer")
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.info("Error: %s", err)
        return err

    compiled_results = format_results(compiled_results)

    return compiled_results
