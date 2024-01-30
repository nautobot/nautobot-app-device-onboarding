"""Empty Nornir Inventory Plugin."""

from nornir.core.inventory import Defaults, Groups, Hosts, Inventory


class EmptyInventory:
    """Creates an empty Nornir Inventory to be populated later."""

    def load(self) -> Inventory:
        """Create a default empty inventory."""
        hosts = Hosts()
        defaults = Defaults(data={})
        groups = Groups()
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
