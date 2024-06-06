"""Processor used by Nornir command getter tasks to prep data for SSoT framework sync and to catch unknown errors."""

from typing import Dict

from jsonschema import ValidationError, validate
from nornir.core.inventory import Host
from nornir.core.task import MultiResult, Task
from nornir_nautobot.plugins.processors import BaseLoggingProcessor

from nautobot_device_onboarding.nornir_plays.formatter import extract_show_data
from nautobot_device_onboarding.nornir_plays.schemas import NETWORK_DATA_SCHEMA, NETWORK_DEVICES_SCHEMA


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
        parsed_command_outputs = {}
        self.logger.info(
            f"Task instance completed. Task Name: {task.name}",
            extra={"object": task.host},
        )
        # If any main task resulted in a failed:True then add that key so ssot side can ignore that entry.
        if result[0].failed:
            if task.params["command_getter_job"] == "sync_devices":
                self.logger.info(
                    f"{host.name} has no platform set. Removing it from the sync process.",
                    extra={"object": host.name},
                )
                del self.data[host.name]
            else:
                self.data[host.name].update({"failed": True})
        # [1:] because result 1 is the (network_send_commands ) task which runs all the subtask, it has no result.
        for res in result[1:]:
            parsed_command_outputs[res.name] = res.result

        ready_for_ssot_data = extract_show_data(
            host, parsed_command_outputs, task.params["command_getter_job"], self.kwargs["debug"]
        )
        if task.params["command_getter_job"] == "sync_devices":
            try:
                validate(ready_for_ssot_data, NETWORK_DEVICES_SCHEMA)
            except ValidationError as e:
                if self.kwargs["debug"]:
                    self.logger.debug(f"Schema validation failed for {host.name}. Error: {e}.")
                self.data[host.name] = {"failed": True, "failed_reason": "Schema validation failed."}
            else:
                if self.kwargs["debug"]:
                    self.logger.debug(f"Ready for ssot data: {host.name} {ready_for_ssot_data}")
                self.data[host.name].update(ready_for_ssot_data)
        elif task.params["command_getter_job"] == "sync_network_data":
            try:
                validate(ready_for_ssot_data, NETWORK_DATA_SCHEMA)
            except ValidationError as err:
                if self.kwargs["debug"]:
                    self.logger.debug(f"Schema validation failed for {host.name} Error: {err}")
                self.data[host.name] = {"failed": True, "failed_reason": "Schema validation failed."}
            else:
                if self.kwargs["debug"]:
                    self.logger.debug(f"Ready for ssot data: {host.name} {ready_for_ssot_data}")
                self.data[host.name].update(ready_for_ssot_data)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for logging and data processing on subtask completed."""
        self.logger.info(f"Subtask completed: {task.name}, {task.host}.", extra={"object": task.host})

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
