"""Command Getter."""

from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command


def _get_commands_to_run(yaml_parsed_info, command_getter_job):
    """Load yaml file and look up all commands that need to be run."""
    commands = []
    for key, value in yaml_parsed_info[command_getter_job].items():
        if not key == "use_textfsm":
            commands.append(value["command"])
    print(f"COMMANDS: {commands}")
    return list(set(commands))


def netmiko_send_commands(task: Task, command_getter_job: str):
    """Run commands specified in PLATFORM_COMMAND_MAP."""
    if not task.host.platform:
        return Result(
            host=task.host,
            result=f"{task.host.name} has no platform set.",
            failed=True
        )
    commands = _get_commands_to_run(task.host.data["platform_parsing_info"], command_getter_job)
    for command in commands:
        command_use_textfsm = task.host.data["platform_parsing_info"][command_getter_job]["use_textfsm"]
        task.run(task=netmiko_send_command, name=command, command_string=command, use_textfsm=command_use_textfsm)
