"""Command Getter."""

from nornir.core.task import Task
from nornir_netmiko.tasks import netmiko_send_command


def _get_commands_to_run(yaml_parsed_info):
    """Load yaml file and look up all commands that need to be run."""
    commands = []
    for _, value in yaml_parsed_info['device_onboarding'].items():
        commands.append(value['command'])
    return list(set(commands))


def netmiko_send_commands(task: Task):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    commands = _get_commands_to_run(task.host.data["platform_parsing_info"])
    for command in commands:
        task.run(task=netmiko_send_command, name=command, command_string=command, use_textfsm=True)
