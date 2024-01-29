"""DiffSync adapters."""

import diffsync
from nautobot_ssot.contrib import NautobotAdapter

from nautobot_device_onboarding.diffsync.models import network_importer_models

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
mock_data = {
    "demo-cisco-xe1": {
        "serial": "9ABUXU581111",
        "interfaces": {
            "GigabitEthernet1": {
                "mgmt_only": True,
                "ip_addresses": ["10.1.1.8"],
            },
            "GigabitEthernet2": {
                "mgmt_only": False,
                "ip_addresses": ["10.1.1.9"],
            },
            "GigabitEthernet3": {
                "mgmt_only": False,
                "ip_addresses": ["10.1.1.10, 10.1.1.11"],
            },
            "GigabitEthernet4": {
                "mgmt_only": False,
                "ip_addresses": [],
            },
        },
    },
}
#######################################
######################################


class FilteredNautobotAdapter(NautobotAdapter):
    """
    Allow for filtering of data loaded from Nautobot into DiffSync models.

    Must be used with FilteredNautobotModel.
    """

    def _load_objects(self, diffsync_model):
        """Given a diffsync model class, load a list of models from the database and return them."""
        parameter_names = self._get_parameter_names(diffsync_model)
        for database_object in diffsync_model._get_queryset(diffsync=self):
            self.job.logger.debug(
                f"LOADING: Database Object: {database_object}, "
                f"Model Name: {diffsync_model._modelname}, "
                f"Parameter Names: {parameter_names}"
            )
            self._load_single_object(database_object, diffsync_model, parameter_names)


class NetworkImporterNautobotAdapter(FilteredNautobotAdapter):
    """Adapter for loading Nautobot data."""

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    ip_address = network_importer_models.NetworkImporterIPAddress

    top_level = ["device"]


class NetworkImporterNetworkAdapter(diffsync.DiffSync):
    """Adapter for loading Network data."""

    def __init__(self, *args, job, sync=None, **kwargs):
        """Instantiate this class, but do not load data immediately from the local system."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    ip_address = network_importer_models.NetworkImporterIPAddress

    top_level = ["device"]
    device_data = mock_data

    def load_devices(self):
        """Load device data from network devices."""
        pass

    def load(self):
        """Load network data."""
        self.load_devices()
