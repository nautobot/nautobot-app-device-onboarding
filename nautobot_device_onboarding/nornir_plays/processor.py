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
        self.kwargs = kwargs

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Processor for logging and data processing on task start."""
        if not self.data.get(host.name):
            self.data[host.name] = {}

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

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on subtask completed."""
        self.logger.info(f"subtask_instance_completed Subtask completed {task.name}.", extra={"object": task.host})
        if self.kwargs["debug"]:
            self.logger.debug(
                f"subtask_instance_completed Subtask result {result.result}.", extra={"object": task.host}
            )
        formatted_data = extract_show_data(host, result, task.parent_task.params["command_getter_job"])
        for k, v in formatted_data.items():
            self.data[host.name][k] = v

    def subtask_instance_started(self, task: Task, host: Host) -> None:  # show command start
        """Processor for logging and data processing on subtask start."""
        self.logger.info(
            f"subtask_instance_started Subtask starting {task.name}, {task.host}.", extra={"object": task.host}
        )
        if not self.data.get(host.name):
            self.data[host.name] = {
                "platform": host.platform,
                "manufacturer": host.platform.split("_")[0].title() if host.platform else "PLACEHOLDER",
                "network_driver": host.platform,
            }
