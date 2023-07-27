"""DiffSync Models for the network importer."""
from typing import List, Optional


from diffsync import DiffSyncModel


class Site(DiffSyncModel):
    """Site Model based on DiffSyncModel.

    A site must have a unique name and can be composed of Vlans and Prefixes.
    """

    _modelname = "site"
    _identifiers = ("slug",)
    _children = {"vlan": "vlans", "prefix": "prefixes"}

    slug: str
    prefixes: List = []
    vlans: List[str] = []
    pk: Optional[str]


class Device(DiffSyncModel):
    """Device Model based on DiffSyncModel.

    A device must have a unique name and can be part of a site.
    """

    _modelname = "device"
    _identifiers = ("slug",)
    _attributes = ("site", "primary_ip")
    _children = {"interface": "interfaces"}

    slug: str
    site: Optional[str]
    interfaces: List = []
    primary_ip: Optional[str]
    pk: Optional[str]


class Interface(DiffSyncModel):  # pylint: disable=too-many-instance-attributes
    """Interface Model based on DiffSyncModel.

    An interface must be attached to a device and the name must be unique per device.
    """

    _modelname = "interface"
    _identifiers = ("device", "name")
    _shortname = ("name",)
    _attributes = (
        "description",
        "mtu",
        "lag",
        "mode",
        "tagged_vlans",
        "untagged_vlan",
        "status",
        "type",
    )
    _children = {"ip_address": "ip_addresses"}

    name: str
    device: str
    status: str
    type: str

    ip_addresses: List[str] = []
    tagged_vlans: List[str] = []

    lag: Optional[str]
    description: Optional[str]
    mode: Optional[str]
    untagged_vlan: Optional[str]
    mtu: Optional[int]

    parent: Optional[str]  # Not the same


class IPAddress(DiffSyncModel):
    """IPAddress Model based on DiffSyncModel.

    An IP address must be unique and can be associated with an interface.
    """

    _modelname = "ip_address"
    _identifiers = ("device", "interface", "address")
    _attributes = ("status",)

    device: str  # interface.all()[0].device
    interface: str
    address: str
    status: str


class Prefix(DiffSyncModel):
    """Prefix Model based on DiffSyncModel.

    An Prefix must be associated with a Site and must be unique within a site.
    """

    _modelname = "prefix"
    _identifiers = ("site", "prefix")
    _attributes = ("vlan", "status")


    prefix: str
    site: Optional[str]
    vlan: Optional[str]
    status: str


class Vlan(DiffSyncModel):
    """Vlan Model based on DiffSyncModel.

    An Vlan must be associated with a Site and the vlan_id msut be unique within a site.
    """

    _modelname = "vlan"
    _identifiers = ("site", "vid")
    _attributes = ("name", "status")


    vid: int
    site: str
    status: str
    name: Optional[str]

    associations: List[str] = []

    def add_device(self, device):
        """Add a device to the list of associated devices.

        Args:
            device (str): name of a device to associate with this VLAN
        """
        if device not in self.associations:
            self.associations.append(device)
            self.associations = sorted(self.associations)


class Cable(DiffSyncModel):
    """Cable Model based on DiffSyncModel."""

    _modelname = "cable"
    _identifiers = (
        "termination_a_device",
        "termination_a",
        "termination_b_device",
        "termination_b",
    )


    termination_a_device: str  # mapped to _termination_a_device
    termination_a: str
    termination_b_device: str  # mapped to _termination_b_device
    termination_b: str

    source: Optional[str]  # Not in Nautobot
    is_valid: bool = True  # Not in Nautobot
    error: Optional[str]  # Not in Nautobot

    # TODO: This should be moved to the adapter if needed.
    # def __init__(self, *args, **kwargs):
    #     """Ensure the cable is unique by ordering the devices alphabetically."""
    #     if "termination_a_device" not in kwargs or "termination_b_device" not in kwargs:
    #         raise ValueError("termination_a_device and termination_b_device are mandatory")
    #     if not kwargs["termination_a_device"] or not kwargs["termination_b_device"]:
    #         raise ValueError("termination_a_device and termination_b_device are mandatory and must not be None")

    #     keys_to_copy = ["termination_a_device", "termination_a", "termination_b_device", "termination_b"]
    #     ids = {key: kwargs[key] for key in keys_to_copy}

    #     devices = [kwargs["termination_a_device"], kwargs["termination_b_device"]]
    #     if sorted(devices) != devices:
    #         ids["termination_a_device"] = kwargs["termination_b_device"]
    #         ids["termination_a"] = kwargs["termination_b"]
    #         ids["termination_b_device"] = kwargs["termination_a_device"]
    #         ids["termination_b"] = kwargs["termination_a"]

    #     for key in keys_to_copy:
    #         del kwargs[key]

    #     super().__init__(*args, **ids, **kwargs)

    # def get_device_intf(self, side):
    #     """Get the device name and the interface name for a given side.

    #     Args:
    #         side (str): site to query, must be either a or z

    #     Raises:
    #         ValueError: when the side is not either a or z

    #     Returns:
    #         (device (str), interface (str))
    #     """
    #     if side.lower() == "a":
    #         return self.termination_a_device, self.termination_a

    #     if side.lower() == "z":
    #         return self.termination_b_device, self.termination_b

    #     raise ValueError("side must be either 'a' or 'z'")


class Status(DiffSyncModel):
    """Status Model based on DiffSyncModel.

    A status must have a unique name and can be composed of Vlans and Prefixes.
    """

    _modelname = "status"
    _identifiers = ("slug",)
    _attributes = ("name",)
    _generic_relation = {}

    slug: str
    name: str
    pk: Optional[str]
