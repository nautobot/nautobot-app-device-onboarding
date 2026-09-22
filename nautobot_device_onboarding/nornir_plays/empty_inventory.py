"""Empty Nornir Inventory Plugin."""

from nautobot.dcim.utils import get_all_network_driver_mappings
from nornir.core.inventory import Defaults, Groups, Hosts, Inventory

from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info


class EmptyInventory:  # pylint: disable=too-few-public-methods
    """Creates an empty Nornir inventory."""

    def __init__(self, logger=None, raise_on_repo_error=False):
        """Initialize the inventory plugin.

        Args:
            logger (NornirLogger): Optional logger to write results to the job result log.
            raise_on_repo_error (bool): Fail instead of falling back to the app provided defaults
                when the command mappers Git repository cannot be refreshed or read.
        """
        self.logger = logger
        self.raise_on_repo_error = raise_on_repo_error

    def load(self) -> Inventory:
        """Create a default empty inventory."""
        hosts = Hosts()
        defaults = Defaults(
            data={
                "platform_parsing_info": add_platform_parsing_info(
                    logger=self.logger, raise_on_repo_error=self.raise_on_repo_error
                ),
                "network_driver_mappings": list(get_all_network_driver_mappings().keys()),
            }
        )
        groups = Groups()
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
