"""DiffSync adapters."""

import json

import diffsync
from diffsync.enum import DiffSyncModelFlags
from django.core.exceptions import ValidationError
from nautobot.dcim.models import Interface
from nautobot.ipam.models import VLAN, IPAddress
from nautobot_ssot.contrib import NautobotAdapter
from netaddr import EUI, mac_unix_expanded

from nautobot_device_onboarding.diffsync.models import network_importer_models
from nautobot_device_onboarding.nornir_plays.command_getter import command_getter_ni
from nautobot_device_onboarding.utils import diffsync_utils


class FilteredNautobotAdapter(NautobotAdapter):
    """
    Allow Nautobot data to be filtered by the Job form inputs.

    Must be used with FilteredNautobotModel.
    """

    def _load_objects(self, diffsync_model):  # pylint: disable=protected-access
        """Given a diffsync model class, load a list of models from the database and return them."""
        parameter_names = self._get_parameter_names(diffsync_model)
        for database_object in diffsync_model._get_queryset(diffsync=self):  # pylint: disable=protected-access
            self._load_single_object(database_object, diffsync_model, parameter_names)


class NetworkImporterNautobotAdapter(FilteredNautobotAdapter):
    """Adapter for loading Nautobot data."""

    device = network_importer_models.NetworkImporterDevice
    interface = network_importer_models.NetworkImporterInterface
    ip_address = network_importer_models.NetworkImporterIPAddress
    ipaddress_to_interface = network_importer_models.NetworkImporterIPAddressToInterface
    vlan = network_importer_models.NetworkImporterVLAN
    tagged_vlans_to_interface = network_importer_models.NetworkImporterTaggedVlansToInterface
    lag_to_interface = network_importer_models.NetworkImporterLagToInterface

    top_level = [
        "ip_address",
        "vlan",
        "device",
        "ipaddress_to_interface",
        "tagged_vlans_to_interface",
        "lag_to_interface",
    ]

    def load_param_mac_address(self, parameter_name, database_object):
        """Convert interface mac_address to string."""
        if self.job.debug:
            self.job.logger.debug(f"Converting {parameter_name}: {database_object.mac_address}")
        return str(database_object.mac_address)

    def load_ip_addresses(self):
        """Load IP addresses into the DiffSync store.

        Only IP Addresses that were returned by the CommandGetter job should be loaded.
        """
        ip_address_hosts = set()
        for _, device_data in self.job.command_getter_result.items():
            for interface in device_data["interfaces"]:
                for _, interface_data in interface.items():
                    for ip_address in interface_data["ip_addresses"]:
                        if ip_address:
                            ip_address_hosts.add(ip_address["ip_address"])
        ip_address_hosts.remove("")  # do not attempt to filter ip addresses with empty strings
        for ip_address in IPAddress.objects.filter(
            host__in=ip_address_hosts,
            parent__namespace__name=self.job.namespace.name,
        ):
            network_ip_address = self.ip_address(
                diffsync=self,
                host=ip_address.host,
                mask_length=ip_address.mask_length,
                type=ip_address.type,
                ip_version=ip_address.ip_version,
                status__name=ip_address.status.name,
            )
            try:
                network_ip_address.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
                self.add(network_ip_address)
                if self.job.debug:
                    self.job.logger.debug(f"{network_ip_address} loaded.")
            except diffsync.exceptions.ObjectAlreadyExists:
                self.job.logger.warning(
                    f"{network_ip_address} is already loaded to the DiffSync store. This is a duplicate IP Address."
                )

    def load_vlans(self):
        """
        Load Vlans into the Diffsync store.

        Only Vlans that were returned by the CommandGetter job should be loaded.
        """
        for vlan in VLAN.objects.all():
            network_vlan = self.vlan(
                diffsync=self,
                name=vlan.name,
                vid=vlan.vid,
                location__name=vlan.location.name if vlan.location else "",
            )
            try:
                network_vlan.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
                self.add(network_vlan)
                if self.job.debug:
                    self.job.logger.debug(f"Vlan {network_vlan} loaded.")
            except diffsync.exceptions.ObjectAlreadyExists:
                pass

    def load_tagged_vlans_to_interface(self):
        """Load a model representing tagged vlan assignments to the Diffsync store.

        Only Vlan assignments that were returned by the CommandGetter job should be loaded.
        """
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            tagged_vlans = []
            for vlan in interface.tagged_vlans.all():
                vlan_dict = {}
                vlan_dict["name"] = vlan.name
                vlan_dict["id"] = str(vlan.vid)
                tagged_vlans.append(vlan_dict)

            network_tagged_vlans_to_interface = self.tagged_vlans_to_interface(
                diffsync=self,
                device__name=interface.device.name,
                name=interface.name,
                tagged_vlans=tagged_vlans,
            )
            network_tagged_vlans_to_interface.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
            self.add(network_tagged_vlans_to_interface)
            if self.job.debug:
                self.job.logger.debug(f"Vlan to interface: {network_tagged_vlans_to_interface} loaded.")

    def load_lag_to_interface(self):
        """
        Load a model representing lag assignments to the Diffsync store.

        Only Lag assignments that were returned by the CommandGetter job should be loaded.
        """
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            network_lag_to_interface = self.lag_to_interface(
                diffsync=self,
                device__name=interface.device.name,
                name=interface.name,
                lag__interface__name=interface.lag.name if interface.lag else "",
            )
            network_lag_to_interface.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
            self.add(network_lag_to_interface)
            if self.job.debug:
                self.job.logger.debug(f"Lag to interface {network_lag_to_interface} loaded.")

    def load(self):
        """Generic implementation of the load function."""
        if not hasattr(self, "top_level") or not self.top_level:
            raise ValueError("'top_level' needs to be set on the class.")

        for model_name in self.top_level:
            if model_name == "ip_address":
                self.load_ip_addresses()
            elif model_name == "vlan":
                if self.job.sync_vlans:
                    self.load_vlans()
            elif model_name == "tagged_vlans_to_interface":
                if self.job.sync_vlans:
                    self.load_tagged_vlans_to_interface()
            elif model_name == "lag_to_interface":
                self.load_lag_to_interface()
            else:
                diffsync_model = self._get_diffsync_class(model_name)
                self._load_objects(diffsync_model)


class MacUnixExpandedUppercase(mac_unix_expanded):
    """Mac Unix Expanded Uppercase."""

    word_fmt = "%.2X"


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
    ipaddress_to_interface = network_importer_models.NetworkImporterIPAddressToInterface
    vlan = network_importer_models.NetworkImporterVLAN
    tagged_vlans_to_interface = network_importer_models.NetworkImporterTaggedVlansToInterface
    lag_to_interface = network_importer_models.NetworkImporterLagToInterface

    top_level = [
        "ip_address",
        "vlan",
        "device",
        "ipaddress_to_interface",
        "tagged_vlans_to_interface",
        "lag_to_interface",
    ]

    def _handle_failed_devices(self, device_data):
        """
        Handle result data from failed devices.

        If a device fails to return expected data, log the result
        and remove it from the data to be loaded into the diffsync store.
        """
        failed_devices = []

        for hostname in device_data:
            if device_data[hostname].get("failed"):
                self.job.logger.error(
                    f"{hostname}: Connection or data error, this device will not be synced. "
                    f"{device_data[hostname].get('failed_reason')}"
                )
                failed_devices.append(hostname)
        for hostname in failed_devices:
            del device_data[hostname]
        if failed_devices:
            self.job.logger.warning(f"Failed devices: {failed_devices}")
        self.job.command_getter_result = device_data
        self.job.devices_to_load = diffsync_utils.generate_device_queryset_from_command_getter_result(device_data)

    def execute_command_getter(self):
        """Start the CommandGetterDO job to query devices for data."""
        result = command_getter_ni(
            self.job.job_result, self.job.logger.getEffectiveLevel(), self.job.job_result.task_kwargs
        )
        if self.job.debug:
            self.job.logger.debug(f"Command Getter Job Result: {result}")
        # verify data returned is a dict
        data_type_check = diffsync_utils.check_data_type(result)
        if self.job.debug:
            self.job.logger.debug(f"CommandGetter data type check resut: {data_type_check}")
        if data_type_check:
            self._handle_failed_devices(device_data=result)
        else:
            self.job.logger.error(
                "Data returned from CommandGetter is not the correct type. "
                "No devices will be onboarded, check the CommandGetter job logs."
            )
            raise ValidationError("Unexpected data returend from CommandGetter.")

    def _process_mac_address(self, mac_address):
        """Convert a mac address to match the value stored by Nautobot."""
        if mac_address:
            return str(EUI(mac_address, version=48, dialect=MacUnixExpandedUppercase))
        return ""

    def load_devices(self):
        """Load devices into the DiffSync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            network_device = self.device(diffsync=self, name=hostname, serial=device_data["serial"])
            self.add(network_device)
            if self.job.debug:
                self.job.logger.debug(f"Device {network_device} loaded.")
            for interface in device_data["interfaces"]:
                for interface_name, interface_data in interface.items():
                    network_interface = self.load_interface(hostname, interface_name, interface_data)
                    network_device.add_child(network_interface)
                    if self.job.debug:
                        self.job.logger.debug(f"Interface {network_interface} loaded.")

    def load_interface(self, hostname, interface_name, interface_data):
        """Load an interface into the DiffSync store."""
        network_interface = self.interface(
            diffsync=self,
            name=interface_name,
            device__name=hostname,
            status__name=self.job.interface_status.name,
            type=interface_data["type"],
            mac_address=self._process_mac_address(interface_data["mac_address"]),
            mtu=interface_data["mtu"] if interface_data["mtu"] else 1500,
            description=interface_data["description"],
            enabled=interface_data["link_status"],
            mode=interface_data["802.1Q_mode"],
            untagged_vlan__name=interface_data["untagged_vlan"]["name"] if interface_data["untagged_vlan"] else None,
        )
        self.add(network_interface)
        if self.job.debug:
            self.job.logger.debug(f"Interface {network_interface} loaded.")
        return network_interface

    def load_ip_addresses(self):
        """Load IP addresses into the DiffSync store."""
        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            for interface in device_data["interfaces"]:
                for interface_name, interface_data in interface.items():
                    for ip_address in interface_data["ip_addresses"]:
                        if ip_address["ip_address"]:  # the ip_address and mask_length may be empty, skip these
                            if self.job.debug:
                                self.job.logger.debug(f"Loading {ip_address} from {interface_name} on {hostname}")
                            network_ip_address = self.ip_address(
                                diffsync=self,
                                host=ip_address["ip_address"],
                                mask_length=int(ip_address["prefix_length"]),
                                type="host",
                                ip_version=4,
                                status__name=self.job.ip_address_status.name,
                            )
                            try:
                                self.add(network_ip_address)
                                if self.job.debug:
                                    self.job.logger.debug(f"{network_ip_address} loaded.")
                            except diffsync.exceptions.ObjectAlreadyExists:
                                self.job.logger.warning(
                                    f"{network_ip_address} is already loaded to the "
                                    "DiffSync store. This is a duplicate IP Address."
                                )

    def load_vlans(self):
        """Load vlans into the Diffsync store."""
        location_names = {}
        for device in self.job.devices_to_load:
            location_names[device.name] = device.location.name

        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            for interface in device_data["interfaces"]:
                for _, interface_data in interface.items():
                    # add tagged vlans
                    for tagged_vlan in interface_data["tagged_vlans"]:
                        network_vlan = self.vlan(
                            diffsync=self,
                            name=tagged_vlan["name"],
                            vid=tagged_vlan["id"],
                            location__name=location_names.get(hostname, ""),
                        )
                        try:
                            self.add(network_vlan)
                            if self.job.debug:
                                self.job.logger.debug(f"Tagged Vlan {network_vlan} loaded.")
                        except diffsync.exceptions.ObjectAlreadyExists:
                            pass
                    # check for untagged vlan and add if necessary
                    if interface_data["untagged_vlan"]:
                        network_vlan = self.vlan(
                            diffsync=self,
                            name=interface_data["untagged_vlan"]["name"],
                            vid=interface_data["untagged_vlan"]["id"],
                            location__name=location_names.get(hostname, ""),
                        )
                        try:
                            self.add(network_vlan)
                            if self.job.debug:
                                self.job.logger.debug(f"Untagged Vlan {network_vlan} loaded.")
                        except diffsync.exceptions.ObjectAlreadyExists:
                            pass

    def load_ip_address_to_interfaces(self):
        """Load ip address interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            for interface in device_data["interfaces"]:
                for interface_name, interface_data in interface.items():
                    for ip_address in interface_data["ip_addresses"]:
                        if ip_address["ip_address"]:  # the ip_address and mask_length may be empty, skip these
                            network_ip_address_to_interface = self.ipaddress_to_interface(
                                diffsync=self,
                                interface__device__name=hostname,
                                interface__name=interface_name,
                                ip_address__host=ip_address["ip_address"],
                                ip_address__mask_length=(
                                    int(ip_address["prefix_length"]) if ip_address["prefix_length"] else None
                                ),
                            )
                            self.add(network_ip_address_to_interface)
                            if self.job.debug:
                                self.job.logger.debug(
                                    f"IP Address to interface {network_ip_address_to_interface} loaded."
                                )

    def load_tagged_vlans_to_interface(self):
        """Load tagged vlan to interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            for interface in device_data["interfaces"]:
                for interface_name, interface_data in interface.items():
                    network_tagged_vlans_to_interface = self.tagged_vlans_to_interface(
                        diffsync=self,
                        device__name=hostname,
                        name=interface_name,
                        tagged_vlans=interface_data["tagged_vlans"],
                    )
                    self.add(network_tagged_vlans_to_interface)
                    if self.job.debug:
                        self.job.logger.debug(f"Tagged Vlan to interface {network_tagged_vlans_to_interface} loaded.")

    def load_lag_to_interface(self):
        """Load lag interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            for interface in device_data["interfaces"]:
                for interface_name, interface_data in interface.items():
                    network_lag_to_interface = self.lag_to_interface(
                        diffsync=self,
                        device__name=hostname,
                        name=interface_name,
                        lag__interface__name=interface_data["lag"] if interface_data["lag"] else "",
                    )
                    self.add(network_lag_to_interface)
                    if self.job.debug:
                        self.job.logger.debug(f"Lag to interface {network_lag_to_interface} loaded.")

    def load(self):
        """Load network data."""
        self.execute_command_getter()
        self.load_ip_addresses()
        if self.job.sync_vlans:
            self.load_vlans()
        self.load_devices()
        self.load_ip_address_to_interfaces()
        if self.job.sync_vlans:
            self.load_tagged_vlans_to_interface()
        self.load_lag_to_interface()
