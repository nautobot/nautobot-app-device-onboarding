"""DiffSync adapters."""

from nautobot_ssot.contrib import NautobotAdapter
from nautobot_device_onboarding.diffsync.models import network_importer_models
import diffsync


class FilteredNautobotAdapter(NautobotAdapter):
    """
    Allow for filtering of data loaded from Nautobot into DiffSync models.

    Must be used with FilteredNautobotModel.
    """
        
    def _load_objects(self, diffsync_model):
        """Given a diffsync model class, load a list of models from the database and return them."""
        parameter_names = self._get_parameter_names(diffsync_model)
        for database_object in diffsync_model._get_queryset(diffsync=self):
            self.job.logger.debug(f"LOADING: Database Object: {database_object}, "
                                  f"Model Name: {diffsync_model._modelname}, "
                                  f"Parameter Names: {parameter_names}")
            self._load_single_object(database_object, diffsync_model, parameter_names)


class NetworkImporterNautobotAdapter(FilteredNautobotAdapter):
    """Adapter for loading Nautobot data."""

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    ip_address = network_importer_models.NetworkImporterIPAddress

    top_level = ["ip_address", "interface", "device"]


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

    top_level = ["ip_address", "interface", "device"]

    def load_devices(self):
        pass

    def load(self):
        self.load_devices()
