"""DiffSync adapters."""

import ipaddress

import diffsync
from nautobot_ssot.contrib import NautobotAdapter
from netaddr import EUI, mac_unix_expanded

from nautobot_device_onboarding.diffsync.models import network_importer_models
from nautobot.ipam.models import IPAddressToInterface
from nautobot.dcim.models import Device

#######################################
# FOR TESTING ONLY - TO BE REMOVED    #
#######################################
mock_data = {
    "demo-cisco-xe1": {
        "serial": "9ABUXU581111",
        "interfaces": {
            "GigabitEthernet1": {
                "mgmt_only": True,
                "status": "Active",
                "type": "100base-tx",
                "ip_addresses": [
                    {"host": "10.1.1.8", "mask_length": 32},
                ],
                "mac_address": "d8b1.905c.5130",
                "mtu": "1500",
                "description": "",
                "enabled": True,
                "802.1Q_mode": "",
                "lag": "",
            },
            "GigabitEthernet2": {
                "mgmt_only": False,
                "status": "Active",
                "type": "100base-tx",
                "ip_addresses": [
                    {"host": "10.1.1.9", "mask_length": 32},
                ],
                "mac_address": "d8b1.905c.6130",
                "mtu": "1500",
                "description": "uplink Po1",
                "enabled": True,
                "802.1Q_mode": "tagged-all",
                "lag": "Po1",
            },
            "GigabitEthernet3": {
                "mgmt_only": False,
                "status": "Active",
                "type": "100base-tx",
                "ip_addresses": [
                    {"host": "10.1.1.10", "mask_length": 32},
                    {"host": "10.1.1.11", "mask_length": 30},
                ],
                "mac_address": "d8b1.905c.6130",
                "mtu": "1500",
                "description": "",
                "enabled": True,
                "802.1Q_mode": "",
                "lag": "",
            },
            "GigabitEthernet4": {
                "mgmt_only": False,
                "status": "Active",
                "type": "100base-tx",
                "ip_addresses": [
                    {"host": "10.1.1.12", "mask_length": 32},
                ],
                "mac_address": "d8b1.905c.7130",
                "mtu": "1500",
                "description": "",
                "enabled": True,
                "802.1Q_mode": "",
                "lag": "",
            },
            "Po1": {
                "mgmt_only": False,
                "status": "Active",
                "type": "lag",
                "ip_addresses": [],
                "mac_address": "d8b1.905c.8130",
                "mtu": "1500",
                "description": "",
                "enabled": True,
                "802.1Q_mode": "",
                "lag": "",
            },
        },
    },
}
#######################################
######################################


class FilteredNautobotAdapter(NautobotAdapter):
    """
    Allow Nautobot data to be filtered by the Job form inputs.

    Must be used with FilteredNautobotModel.
    """

    def _load_objects(self, diffsync_model):  # pylint: disable=protected-access
        """Given a diffsync model class, load a list of models from the database and return them."""
        parameter_names = self._get_parameter_names(diffsync_model)
        for database_object in diffsync_model._get_queryset(diffsync=self):  # pylint: disable=protected-access
            self.job.logger.debug(
                f"LOADING: Database Object: {database_object}, "
                f"Model Name: {diffsync_model._modelname}, "  # pylint: disable=protected-access
                f"Parameter Names: {parameter_names}"
            )
            self._load_single_object(database_object, diffsync_model, parameter_names)


# TODO: remove this if unused
class mac_unix_expanded_uppercase(mac_unix_expanded):
    word_fmt = "%.2X"


class NetworkImporterNautobotAdapter(FilteredNautobotAdapter):
    """Adapter for loading Nautobot data."""

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    # ip_address = network_importer_models.NetworkImporterIPAddress
    ipaddress_to_interface = network_importer_models.NetworkImporterIPAddressToInterface
    prefix = network_importer_models.NetworkImporterPrefix

    top_level = ["prefix", "device", "ipaddress_to_interface"]

    def load_ip_address_to_interfaces(self):
        """
        Load the IP address to interface model into the DiffSync store.

        Only interfaces which belong to devices included in the sync should be considered.
        """
        filter = {}
        if self.job.devices:
            filter["id__in"] = [device.id for device in self.job.devices]
        if self.job.location:
            filter["location"] = self.job.location
        if self.job.device_role:
            filter["role"] = self.job.device_role
        if self.job.tag:
            filter["tags"] = self.job.tag
        devices_in_sync = Device.objects.filter(**filter)

        for obj in IPAddressToInterface.objects.filter(interface__device__in=devices_in_sync):
            network_ip_address_to_interface = self.ipaddress_to_interface(
                diffsync=self,
                interface__device__name=obj.interface.device.name,
                interface__name=obj.interface.name,
                ip_address__host=obj.ip_address.host,
                ip_address__mask_length=obj.ip_address.mask_length,
            )
            self.add(network_ip_address_to_interface)

    def load(self):
        """Generic implementation of the load function."""
        if not hasattr(self, "top_level") or not self.top_level:
            raise ValueError("'top_level' needs to be set on the class.")

        for model_name in self.top_level:
            if model_name is "ipaddress_to_interface":
                self.load_ip_address_to_interfaces()
            else:
                diffsync_model = self._get_diffsync_class(model_name)

                # This function directly mutates the diffsync store, i.e. it will create and load the objects
                # for this specific model class as well as its children without returning anything.
                self._load_objects(diffsync_model)


class NetworkImporterNetworkAdapter(diffsync.DiffSync):
    """Adapter for loading Network data."""

    def __init__(self, *args, job, sync=None, **kwargs):
        """Instantiate this class, but do not load data immediately from the local system."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    device_data = mock_data

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    # ip_address = network_importer_models.NetworkImporterIPAddress
    ipaddress_to_interface = network_importer_models.NetworkImporterIPAddressToInterface
    prefix = network_importer_models.NetworkImporterPrefix

    top_level = ["prefix", "device", "ipaddress_to_interface"]

    device_data = mock_data

    def load_devices(self):
        """Load device data from network devices."""
        for hostname, device_data in self.device_data.items():
            network_device = self.device(diffsync=self, name=hostname, serial=device_data["serial"])
            self.add(network_device)
            if self.job.debug:
                self.job.logger.debug(f"Device {network_device} loaded.")
            for interface_name, interface_data in device_data["interfaces"].items():
                network_interface = self.load_interface(hostname, interface_name, interface_data)
                network_device.add_child(network_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Interface {network_interface} loaded.")

    def load_interface(self, hostname, interface_name, interface_data):
        """Load data for a single interface into the DiffSync store."""
        network_interface = self.interface(
            diffsync=self,
            name=interface_name,
            device__name=hostname,
            status__name=interface_data["status"],
            type=interface_data["type"],
            # mac_address=interface_data["mac_address"],
            # mac_address=EUI(interface_data["mac_address"], version=48, dialect=mac_unix_expanded_uppercase),
            mtu=interface_data["mtu"],
            description=interface_data["description"],
            enabled=interface_data["enabled"],
            mode=interface_data["802.1Q_mode"],
            mgmt_only=interface_data["mgmt_only"],
            lag=interface_data["lag"],
        )
        self.add(network_interface)
        return network_interface

    def _determine_network(self, ip_address, mask_length):
        ip_interface = ipaddress.ip_interface(f"{ip_address}/{mask_length}")
        return str(ip_interface.network).split("/")[0]

    def load_prefixes(self):
        """Load IP addresses used by interfaces into the DiffSync store."""
        for hostname, device_data in self.device_data.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                for ip_address in interface_data["ip_addresses"]:
                    network_prefix = self.prefix(
                        diffsync=self,
                        namespace__name=self.job.namespace.name,
                        network=self._determine_network(ip_address=ip_address["host"], mask_length=24),
                        # TODO: prefix length is hard coded here, can it be determined from the device?
                        prefix_length=24,
                        status__name="Active",
                    )
                    try:
                        self.add(network_prefix)
                        if self.job.debug:
                            self.job.logger.debug(f"{network_prefix} loaded.")
                    except diffsync.exceptions.ObjectAlreadyExists:
                        pass

    def load_ip_addresses(self):
        """Load IP addresses used by interfaces into the DiffSync store."""
        for hostname, device_data in self.device_data.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                for ip_address in interface_data["ip_addresses"]:
                    network_ip_address = self.ip_address(
                        diffsync=self,
                        host=ip_address["host"],
                        mask_length=ip_address["mask_length"],
                        type="host",
                        ip_version=4,
                        status__name="Active",
                    )
                    try:
                        self.add(network_ip_address)
                        if self.job.debug:
                            self.job.logger.debug(f"{network_ip_address} loaded.")
                    except diffsync.exceptions.ObjectAlreadyExists:
                        self.job.warning(
                            f"{network_ip_address} is already loaded to the "
                            "DiffSync store. This is a duplicate IP Address."
                        )

    def load_ip_address_to_interfaces(self):
        """Load the IP address to interface model into the DiffSync store."""
        for hostname, device_data in self.device_data.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                for ip_address in interface_data["ip_addresses"]:
                    network_ip_address_to_interface = self.ipaddress_to_interface(
                        diffsync=self,
                        interface__device__name=hostname,
                        interface__name=interface_name,
                        ip_address__host=ip_address["host"],
                        ip_address__mask_length=ip_address["mask_length"],
                    )
                    self.add(network_ip_address_to_interface)
                    if self.job.debug:
                        self.job.logger.debug(f"{network_ip_address_to_interface} loaded.")

    def load(self):
        """Load network data."""
        self.load_prefixes()
        # self.load_ip_addresses()
        self.load_devices()
        self.load_ip_address_to_interfaces()
