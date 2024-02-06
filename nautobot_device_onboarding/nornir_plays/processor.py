"""Processor used by Device Onboarding to catch unknown errors."""

from typing import Dict

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.processors import BaseLoggingProcessor

from nautobot_device_onboarding.utils.formatter import format_ob_data_ios, format_ob_data_nxos, format_ob_data_junos


class ProcessorDO(BaseLoggingProcessor):
    """Processor class for Device Onboarding jobs."""

    def __init__(self, logger, command_outputs):
        """Set logging facility."""
        self.logger = logger
        self.data: Dict = command_outputs

    def task_started(self, task: Task) -> None:
        """Boilerplate Nornir processor for task_started."""
        self.data[task.name] = {}
        # self.data[task.name]["started"] = True
        self.logger.info(f"Task Name: {task.name} started")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Boilerplate Nornir processor for task_instance_completed."""
        # self.data[task.name]["completed"] = True
        self.logger.info(f"Task Name: {task.name} completed")

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Processor for Logging on Task Start."""
        self.logger.info(f"Starting {task.name}.", extra={"object": task.host})
        self.data[task.name][host.name] = {}

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Nornir processor task completion for OS upgrades.

        Args:
            task (Task): Nornir task individual object
            host (Host): Host object with Nornir
            result (MultiResult): Result from Nornir task

        Returns:
            None
        """
        # Complex logic to see if the task exception is expected, which is depicted by
        # a sub task raising a NornirNautobotException.
        if result.failed:
            for level_1_result in result:
                if hasattr(level_1_result, "exception") and hasattr(level_1_result.exception, "result"):
                    for level_2_result in level_1_result.exception.result:  # type: ignore
                        if isinstance(level_2_result.exception, NornirNautobotException):
                            return
            self.logger.critical(f"{task.name} failed: {result.exception}", extra={"object": task.host})
        else:
            self.logger.info(f"Task Name: {task.name} Task Result: {result.result}", extra={"object": task.host})

        # self.data[task.name][host.name] = {
        #     "completed": True,
        #     "failed": result.failed,
        # }

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for Logging on SubTask Completed."""
        self.logger.info(f"Subtask completed {task.name}.", extra={"object": task.host})
        self.logger.info(f"Subtask result {result.result}.", extra={"object": task.host})

        self.data[task.name][host.name] = {
            "failed": result.failed,
            "subtask_result": result.result,
        }

        if self.data[task.name][host.name].get("failed"):
            self.data[host.name] = {
                "failed": True,
                "subtask_result": result.result,
            }
        elif host.name not in self.data:
            self.data[host.name] = {
                "platform": host.platform,
                "manufacturer": host.platform.split("_")[0].title() if host.platform else "PLACEHOLDER",
                "network_driver": host.platform,
            }

        if host.platform in ["cisco_ios", "cisco_xe"]:
            formatted_data = format_ob_data_ios(host, result)
        elif host.platform == "cisco_nxos":
            formatted_data = format_ob_data_nxos(host, result)
        elif host.platform == "juniper_junos":
            formatted_data = format_ob_data_junos(host, result)
        else:
            formatted_data = {}
            self.logger.info(f"No formatter for platform: {host.platform}.", extra={"object": task.host})

        self.data[host.name].update(formatted_data)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Processor for Logging on SubTask Start."""
        self.logger.info(f"Subtask starting {task.name}.", extra={"object": task.host})
        self.data[task.name] = {}
        # self.data[task.name][host.name] = {"started": True}
