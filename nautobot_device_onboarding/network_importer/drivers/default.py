"""default driver for the nautobot_device_onboarding.network_importer."""
import logging

from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_command

from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

from django.conf import settings

from nautobot_device_onboarding.network_importer.drivers.converters import convert_cisco_genie_cdp_neighbors_details

LOGGER = logging.getLogger("network-importer")
PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("nautobot_device_onboarding", {})


class NetworkImporterDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        LOGGER.debug("Executing get_config for %s (%s)", task.host.name, task.host.platform)

        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except:  # noqa: E722 # pylint: disable=bare-except
            LOGGER.debug("An exception occured while pulling the configuration", exc_info=True)
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def get_neighbors(task: Task) -> Result:  # pylint: disable=too-many-return-statements
        """Get a list of neighbors from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the neighbors
            The format of the result but must be similar to Neighbors defined in nautobot_device_onboarding.network_importer.processors.get_neighbors
        """
        LOGGER.debug("Executing get_neighbor for %s (%s)", task.host.name, task.host.platform)

        if PLUGIN_SETTINGS.get("main", {}).get("import_cabling", "").lower() == "lldp":
            try:
                result = task.run(task=napalm_get, getters=["lldp_neighbors"])
            except:  # noqa: E722 # pylint: disable=bare-except
                LOGGER.debug("An exception occurred while pulling lldp_data", exc_info=True)
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            neighbors = result[0].result.get("lldp_neighbors", {})
            return Result(host=task.host, result={"neighbors": neighbors})

        if PLUGIN_SETTINGS.get("main", {}).get("import_cabling", "").lower() == "cdp":
            try:
                result = task.run(
                    task=netmiko_send_command, command_string="show cdp neighbors detail", use_genie=True
                )  # TODO convert to NTC Templates
            except NornirSubTaskError:
                LOGGER.debug("An exception occurred while pulling CDP data")
                return Result(host=task.host, failed=True)

            if result[0].failed:
                return result

            results = convert_cisco_genie_cdp_neighbors_details(device_name=task.host.name, data=result[0].result)
            return Result(host=task.host, result=results.dict())

        LOGGER.warning("%s | Unexpected value for `import_cabling`, should be either LLDP or CDP", task.host.name)
        return Result(host=task.host, failed=True)

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Placeholder for get_vlans Get a list of vlans from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in nautobot_device_onboarding.network_importer.processors.get_vlans
        """
        LOGGER.warning("%s | Get Vlans not implemented in the default driver.", task.host.name)

    @staticmethod
    def get_ips(task: Task) -> Result:
        """Placeholder for get_ips Get a list of IP addresses from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the IP addresses
        """
        LOGGER.debug("Executing get_config for %s (%s)", task.host.name, task.host.platform)
        try:
            result = task.run(task=napalm_get, getters=["get_interfaces_ip"])
        except:  # noqa: E722 # pylint: disable=bare-except
            LOGGER.debug("An exception occured while executing NAPALM Getters for Interface IP", exc_info=True)
            return Result(host=task.host, failed=True)

        if result[0].failed:
            return result

        return Result(host=task.host, result=result)
