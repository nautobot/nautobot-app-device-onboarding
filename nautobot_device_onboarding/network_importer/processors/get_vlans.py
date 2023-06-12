"""GetVlans processor for the nautobot_device_onboarding.network_importer."""
import logging
from typing import List

from pydantic import BaseModel  # pylint: disable=no-name-in-module

from nautobot_device_onboarding.network_importer.processors import BaseProcessor

LOGGER = logging.getLogger("network-importer")


# ------------------------------------------------------------
# Standard model to return for get_vlans
# ------------------------------------------------------------
class Vlan(BaseModel):
    """Dataclass model to store one vlan returned by get_vlans."""

    name: str
    vid: int


class Vlans(BaseModel):
    """Dataclass model to store Vlans returned by get_vlans."""

    vlans: List[Vlan] = []


# ------------------------------------------------------------
# Processor
# ------------------------------------------------------------
class GetVlans(BaseProcessor):
    """Placeholder for GetVlans processor, currently using the BaseProcessor."""
