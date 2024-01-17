"""DiffSync adapters."""

from nautobot_ssot.contrib import NautobotAdapter
from diffsync import DiffSync


class NetworkImporterNautobotAdapter(NautobotAdapter):
    pass


class NetworkImporterNetworkAdapter(DiffSync):
    pass