"""Processor used by Nornir command getter tasks to prep data for SSoT framework sync and to catch unknown errors."""

from typing import Dict

from jsonschema import ValidationError, validate
from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from nornir_nautobot.plugins.processors import BaseLoggingProcessor


class CommandGetterProcessor(BaseLoggingProcessor):
    """Processor class for Command Getter Nornir Tasks."""

    def __init__(self, logger):
        """Set logging facility."""
        self.logger = logger

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on task completed.

        Args:
            task (Task): Nornir task individual object
            host (Host): Host object with Nornir
            result (MultiResult): Result from Nornir task

        Returns:
            None
        """
        parsed_command_outputs = {}
        self.logger.info(
            f"Task instance completed. Task Name: {task.name}",
            extra={"object": task.host},
        )
        # If any main task resulted in a failed:True then add that key so ssot side can ignore that entry.
        if result[0].failed:
            self.logger.info(
                f"Netmiko Send Commands failed on {host.name} with result: {result[0].result}",
                extra={"object": host.name},
            )

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on subtask completed."""
        self.logger.info(
            f"Subtask {'failed' if result.failed else 'succeeded'}: {task.name}, {task.host}.",
            extra={"object": task.host},
        )
        if result.failed:
            for res in result:
                if res.exception:
                    self.logger.info(
                        f"{host.name} an exception occured: {res.exception}.",
                        extra={"object": host.name},
                    )

    def subtask_instance_started(self, task: Task, host: Host) -> None:  # show command start
        """Processor for logging and data processing on subtask start."""
        self.logger.info(f"Subtask starting: {task.name}, {task.host}.", extra={"object": task.host})


class TroubleshootingProcessor(BaseLoggingProcessor):
    """Processor class for to troubleshot command getter."""

    def __init__(self, command_outputs):
        """Set logging facility."""
        self.data: Dict = command_outputs

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on task completed.

        Args:
            task (Task): Nornir task individual object
            host (Host): Host object with Nornir
            result (MultiResult): Result from Nornir task

        Returns:
            None
        """
        # [1:] because result 1 is the (network_send_commands ) task which runs all the subtask, it has no result.
        for res in result[1:]:
            self.data[res.name] = res.result
