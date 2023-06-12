"""Nautobot Network Importer SSOT Sync.

This job synchronizes data using the Nautobot SSOT sync pattern
"""
# Core Python Imports
import logging

from diffsync import DiffSyncFlags
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Rack, RackGroup, Region, Site

# Nautobot Imports
from nautobot.extras.jobs import BooleanVar, ChoiceVar, Job, MultiObjectVar
from nautobot.extras.models import Tag
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory

# Nautobot Apps Imports
from nautobot_ssot.jobs.base import DataSource
from nornir import InitNornir

# Nornir Imports
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.task import MultiResult, Result, Task
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.processors import BaseLoggingProcessor
from nornir_nautobot.utils.logger import NornirLogger
from nornir_netmiko.tasks import netmiko_send_command

LOGGER = logging.getLogger(__name__)

name = "SSoT - Network Importer"  # pylint: disable=invalid-name

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)


def run_commands(task, logger, job_id, command_list: list = []):
    """Run Commands docstring."""

    logger.log_info(task, message=f"Starting running checks for {task.host}.")

    check_command_map = {}
    getter_commands = []
    # A device can have check commands that use Textfsm and napalm getters so need to separate them.
    # for check_command in check_commands:
    #     if check_command.parser == "NAPALM":
    #         getter_commands.append(check_command.command)
    #     elif check_command.parser == "TEXTFSM":
    #         cli_commands.append(check_command.command)

    #     check_command_map[check_command.command] = check_command
    print(command_list)

    if command_list:
        logger.log_info(command_list, message=f"CLI commands to run in {task.host}.")
        for command in command_list:
            results = task.run(task=netmiko_send_command, command_string=command, use_textfsm=True)

    return Result(
        host=task.host,
        result="Commands task finished!",
    )


class NetworkDeviceDataSource(DataSource, Job):  # pylint: diable=invalid-name
    """Network device data source."""

    def __init__(self):
        """Initialization of Nautobot Plugin Network Importer SSOT."""
        super().__init__()
        self.diffsync_flags = DiffSyncFlags.CONTINUE_ON_FAILURE | DiffSyncFlags.SKIP_UNMATCHED_DST


class FormEntry:  # pylint disable=too-few-public-method
    """Class definition to use as Mixin for form definitions."""

    tenant_group = MultiObjectVar(model=TenantGroup, required=False)
    tenant = MultiObjectVar(model=Tenant, required=False)
    region = MultiObjectVar(model=Region, required=False)
    site = MultiObjectVar(model=Site, required=False)
    rack_group = MultiObjectVar(model=RackGroup, required=False)
    rack = MultiObjectVar(model=Rack, required=False)
    role = MultiObjectVar(model=DeviceRole, required=False)
    manufacturer = MultiObjectVar(model=Manufacturer, required=False)
    platform = MultiObjectVar(model=Platform, required=False)
    device_type = MultiObjectVar(model=DeviceType, required=False, display_field="display_name")
    device = MultiObjectVar(model=Device, required=False)
    tag = MultiObjectVar(model=Tag, required=False)
    debug = BooleanVar(description="Enable for more verbose debug logging")
    # TODO: Add status


class RunCommandsProcessor(BaseLoggingProcessor):
    """Nautobot Network Importer processor."""

    def __init__(self):
        """Run Commands Nornir Processor definition."""
        pass

    def task_started(self, *args, **kwargs):
        print("Hello all!")


class NetworkImporterJob(Job, FormEntry):
    """Network Importer Job."""

    debug = BooleanVar(description="Enable for verbose debug logging.")
    dry_run = BooleanVar(description="Execute Dry Run")
    import_vlans = BooleanVar(description="Import VLANs")
    import_layer3_addresses = BooleanVar(description="Gather IP addresses (no prefixes)")
    import_prefixes = BooleanVar(description="Import Prefixes")
    import_cabling = BooleanVar(description="Import Cabling")
    import_interface_status = BooleanVar(description="Import Interface Status")

    class Meta:
        """Meta data attributes."""

        name = "Network Importer v2"
        description = "Network Importer for Nautobot, version 2"

    def __init__(self):
        super().__init__()
        self.data = None
        self.commit = None

    def run(self, data, commit):
        """Run the job."""
        self.data = data
        self.commit = commit
        self.log_success(obj=None, message="Hello World again!")
        device_queryset = self.data["device"]
        self.log_info(obj=None, message=self.data)
        print(self.data)
        command_list = []

        if self.data["import_vlans"]:
            command_list.append("show vlan")

        if self.data["import_layer3_addresses"]:
            command_list.append("show ip interface brief")

        logger = NornirLogger(__name__, self, data.get("debug"))
        try:
            nornir_obj = InitNornir(
                runner=NORNIR_SETTINGS.get("runner"),
                logging={"enabled": False},
                inventory={
                    "plugin": "nautobot-inventory",
                    "options": {
                        "credentials_class": NORNIR_SETTINGS.get("credentials"),
                        "params": NORNIR_SETTINGS.get("inventory_params"),
                        "queryset": device_queryset,
                    },
                },
            )
        except NornirNautobotException as exception_info:
            self.log_failure(obj=None, message="Error in initializing the inventory. Was a device or filter set?")
            self.log_info(obj=None, message=f"Error: {exception_info}")
            return

        for host in nornir_obj.inventory.hosts:
            if nornir_obj.inventory.hosts[host]["connection_options"]["napalm"].get("platform"):
                nornir_obj.inventory.hosts[host].platform = nornir_obj.inventory.hosts[host]["connection_options"][
                    "napalm"
                ].get("platform")
        nr_with_processors = nornir_obj.with_processors([RunCommandsProcessor()])
        nr_with_processors.run(
            task=run_commands,
            name="Run CheckCommands per device.",
            logger=logger,
            job_id=self.job_result,
            command_list=command_list,
        )

        self.log_info(message="Collect check data job finished.")
