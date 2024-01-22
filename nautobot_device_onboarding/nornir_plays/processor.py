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
            "failed": result.failed,
        }

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Processor for Logging on SubTask Completed."""
        self.logger.info(f"Subtask completed {task.name}.", extra={"object": task.host})
        
        formatted_data = self.format_onboarding_ios(host, result)
        host_ip = host.name

        if host.name not in self.data:
            self.data[host.name] = formatted_data
        else:
            for key, value in formatted_data.items():
                self.data[host_ip][key] = value
            

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Processor for Logging on SubTask Start."""
        self.logger.info(f"Subtask starting {task.name}.", extra={"object": task.host})
        
    def format_onboarding_ios(self, host: Host, result: MultiResult):
        primary_ip4 = host.name
        formatted_data = {}
       
        for r in result:
            if r.name == "show inventory":
                device_type = r.result[0].get("pid")
                formatted_data["device_type"] = device_type
            elif r.name == "show version":
                hostname = r.result[0].get("hostname")
                serial = r.result[0].get("serial")
                formatted_data["hostname"] = hostname 
                formatted_data["serial"] = serial[0]
            elif r.name == "show interfaces":
                show_interfaces = r.result
                for interface in show_interfaces:
                    if interface.get("ip_address") == primary_ip4:
                        mask_length = interface.get("prefix_length")
                        interface_name = interface.get("interface")
                        formatted_data["mask_length"] = mask_length
                        formatted_data["interface_name"] = interface_name
                        
        return formatted_data