from nautobot_device_onboarding.constants import PLATFORM_COMMAND_MAP
from nornir.core.task import Task
from nornir_netmiko.tasks import netmiko_send_command


def netmiko_send_commands(task: Task):
    for command in PLATFORM_COMMAND_MAP.get(task.host.platform, "default"):
        task.run(task=netmiko_send_command, command_string=command, use_textfsm=True)
