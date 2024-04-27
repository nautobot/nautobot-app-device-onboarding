"""Processor used by Nornir command getter tasks to prep data for SSoT framework sync and to catch unknown errors."""

from typing import Dict

from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from nornir_nautobot.plugins.processors import BaseLoggingProcessor

from nautobot_device_onboarding.nornir_plays.formatter import extract_show_data


class CommandGetterProcessor(BaseLoggingProcessor):
    """Processor class for Command Getter Nornir Tasks."""

    def __init__(self, logger, command_outputs, kwargs):
        """Set logging facility."""
        self.logger = logger
        self.data: Dict = command_outputs
        self.parsed_command_outputs = {}
        self.kwargs = kwargs

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Processor for logging and data processing on task start."""
        if not self.data.get(host.name):
            self.data[host.name] = {
                "platform": host.platform,
                "manufacturer": host.platform.split("_")[0].title() if host.platform else "PLACEHOLDER",
                "network_driver": host.platform,
            }

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on task completed.

        Args:
            task (Task): Nornir task individual object
            host (Host): Host object with Nornir
            result (MultiResult): Result from Nornir task

        Returns:
            None
        """
        self.logger.info(
            f"task_instance_completed Task Name: {task.name} Task Result: {result.result}",
            extra={"object": task.host},
        )
        # [1:] because result 1 is the (network_send_commands ) task which runs all the subtask, it has no result.
        for res in result[1:]:
            self.parsed_command_outputs[res.name] = res.result

        ready_for_ssot_data = extract_show_data(host, self.parsed_command_outputs, task.params["command_getter_job"])
        self.data[host.name].update(ready_for_ssot_data)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on subtask completed."""
        self.logger.info(f"subtask_instance_completed Subtask completed {task.name}.", extra={"object": task.host})
        if self.kwargs["debug"]:
            self.logger.debug(
                f"subtask_instance_completed Subtask result {result.result}.", extra={"object": task.host}
            )

    def subtask_instance_started(self, task: Task, host: Host) -> None:  # show command start
        """Processor for logging and data processing on subtask start."""
        self.logger.info(
            f"subtask_instance_started Subtask starting {task.name}, {task.host}.", extra={"object": task.host}
        )
