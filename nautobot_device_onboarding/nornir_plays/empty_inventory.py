"""Empty Nornir Inventory Plugin."""

from nautobot.dcim.utils import get_all_network_driver_mappings
from nornir.core.inventory import Defaults, Groups, Hosts, Inventory
from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info
from nautobot_device_onboarding.constants import SUPPORTED_NETWORK_DRIVERS

class EmptyInventory:  # pylint: disable=too-few-public-methods
    """Creates an empty Nornir inventory."""

    def load(self) -> Inventory:
        """Create a default empty inventory."""
        hosts = Hosts()
        defaults = Defaults(
            data={
                "platform_parsing_info": add_platform_parsing_info(),
                "network_driver_mappings": SUPPORTED_NETWORK_DRIVERS,
            }
        )
        groups = Groups()
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
