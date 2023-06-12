"""BaseProcessor for the nornir."""
import logging

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

logger = logging.getLogger("network-importer")  # TODO: Fix Logger

# pylint: disable=missing-function-docstring


class BaseProcessor:
    """Base Processor for nornir."""

    task_name = "'no task defined'"

    def task_started(self, task: Task) -> None:
        pass

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass
