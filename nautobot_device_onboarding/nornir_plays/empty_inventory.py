"""Empty Nornir Inventory Plugin."""

from nornir.core.inventory import Defaults, Groups, Hosts, Inventory


class EmptyInventory:
    """Creates an empty Nornir inventory."""

    def load(self):
        """Create a default empty inventory."""
        hosts = Hosts()
        defaults = Defaults(data={})
        groups = Groups()
        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
