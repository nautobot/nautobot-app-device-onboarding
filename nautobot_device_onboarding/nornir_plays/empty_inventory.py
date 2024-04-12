"""Empty Nornir Inventory Plugin."""

from nornir.core.inventory import Defaults, Groups, Hosts, Inventory
from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info


class EmptyInventory:  # pylint: disable=too-few-public-methods
    """Creates an empty Nornir inventory."""

    def load(self) -> Inventory:
        """Create a default empty inventory."""
        hosts = Hosts()
        defaults = Defaults(data={"platform_parsing_info": add_platform_parsing_info()})
        groups = Groups()
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
