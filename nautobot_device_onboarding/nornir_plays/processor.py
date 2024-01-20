"""Processor used by Device Onboarding to catch unknown errors."""

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.processors import BaseLoggingProcessor


class ProcessorDO(BaseLoggingProcessor):
    """Processor class for Device Onboarding jobs."""

    def __init__(self, logger, command_outputs):
        """Set logging facility."""
        self.logger = logger
        self.data = command_outputs

    def task_started(self, task: Task) -> None:
        self.data[task.name] = {}
        self.data[task.name]["started"] = True

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.data[task.name]["completed"] = True

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Processor for Logging on Task Start."""
        self.logger.info(f"Starting {task.name}.", extra={"object": task.host})
        self.data[task.name][host.name] = {"started": True}

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
                    for level_2_result in level_1_result.exception.result:
                        if isinstance(level_2_result.exception, NornirNautobotException):
                            return
            self.logger.critical(f"{task.name} failed: {result.exception}", extra={"object": task.host})
        else:
            self.logger.info(
                f"Task Name: {task.name} Task Result: {result.result}", extra={"object": task.host}
            )
        self.data[task.name][host.name] = {
            "completed": True,
            "result": result.result,
        }

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for Logging on SubTask Completed."""
        self.logger.info(f"Subtask completed {task.name}.", extra={"object": task.host})
        self.data[task.name][host.name] = {
            "failed": result.failed,
            "result": result.result,
        }
    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Processor for Logging on SubTask Start."""
        self.logger.info(f"Subtask starting {task.name}.", extra={"object": task.host})
        self.data[task.name] = {}
        self.data[task.name][host.name] = {"started": True}