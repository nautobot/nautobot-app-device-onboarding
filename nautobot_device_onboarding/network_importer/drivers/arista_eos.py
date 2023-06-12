"""network_importer driver for arista_eos."""
import logging

from nornir.core.task import Result, Task

from nautobot_device_onboarding.network_importer.drivers.default import (
    NetworkImporterDriver as DefaultNetworkImporterDriver,
)
from nautobot_device_onboarding.network_importer.processors.get_vlans import Vlan, Vlans

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Arista EOS devices."""

    @staticmethod
    def get_vlans(task: Task) -> Result:
        """Get a list of vlans from the device.

        Args:
            task (Task): Nornir Task

        Returns:
            Result: Nornir Result object with a dict as a result containing the vlans
            The format of the result but must be similar to Vlans defined in nautobot_device_onboarding.network_importer.processors.get_vlans
        """
        results = Vlans()

        nr_device = task.host.get_connection("napalm", task.nornir.config)
        eos_device = nr_device.device
        results = eos_device.run_commands(["show vlan"])

        if not isinstance(results[0], dict) or "vlans" not in results[0]:
            LOGGER.warning("%s | No vlans information returned", task.host.name)
            return Result(host=task.host, result=False)

        for vid, data in results[0]["vlans"].items():
            results.vlans.append(Vlan(name=data["name"], id=vid))

        return Result(host=task.host, result=results)
