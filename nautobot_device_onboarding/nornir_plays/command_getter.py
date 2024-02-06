"""Command Getter."""

from nornir.core.task import Task
from nornir_netmiko.tasks import netmiko_send_command

from nautobot_device_onboarding.constants import PLATFORM_COMMAND_MAP


def netmiko_send_commands(task: Task):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    for command in PLATFORM_COMMAND_MAP.get(task.host.platform):
        task.run(task=netmiko_send_command, name=command, command_string=command, use_textfsm=True)
