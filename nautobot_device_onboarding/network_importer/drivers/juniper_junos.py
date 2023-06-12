"""default nautobot_device_onboarding.network_importer driver for cisco."""

import logging

from nautobot_device_onboarding.network_importer.drivers.default import (
    NetworkImporterDriver as DefaultNetworkImporterDriver,
)

LOGGER = logging.getLogger("network-importer")


class NetworkImporterDriver(DefaultNetworkImporterDriver):
    """Collection of Nornir Tasks specific to Juniper Junos devices."""
