"""DiffSync adapters."""

import datetime

import diffsync
from diffsync.enum import DiffSyncModelFlags
from django.conf import settings
from django.core.exceptions import ValidationError
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import VLAN, VRF, IPAddress
from nautobot_ssot.contrib import NautobotAdapter
from netaddr import EUI, mac_unix_expanded

from nautobot_device_onboarding.diffsync.models import sync_network_data_models
from nautobot_device_onboarding.nornir_plays.command_getter import sync_network_data_command_getter
from nautobot_device_onboarding.utils import diffsync_utils

app_settings = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


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


class SyncNetworkDataNautobotAdapter(FilteredNautobotAdapter):
    """Adapter for loading Nautobot data."""

    device = sync_network_data_models.SyncNetworkDataDevice
    interface = sync_network_data_models.SyncNetworkDataInterface
    ip_address = sync_network_data_models.SyncNetworkDataIPAddress
    ipaddress_to_interface = sync_network_data_models.SyncNetworkDataIPAddressToInterface
    vlan = sync_network_data_models.SyncNetworkDataVLAN
    vrf = sync_network_data_models.SyncNetworkDataVRF
    tagged_vlans_to_interface = sync_network_data_models.SyncNetworkDataTaggedVlansToInterface
    untagged_vlan_to_interface = sync_network_data_models.SyncNetworkDataUnTaggedVlanToInterface
    lag_to_interface = sync_network_data_models.SyncNetworkDataLagToInterface
    vrf_to_interface = sync_network_data_models.SyncNetworkDataVrfToInterface

    primary_ips = None

    top_level = [
        "ip_address",
        "vlan",
        "vrf",
        "device",
        "ipaddress_to_interface",
        "untagged_vlan_to_interface",
        "tagged_vlans_to_interface",
        "lag_to_interface",
        "vrf_to_interface",
    ]

    def _cache_primary_ips(self, device_queryset):
        """
        Create a cache of primary ip address for devices.

        If the primary ip address of a device is unset due to the deletion
        of an interface, this cache is used to reset it in sync_complete().
        """
        self.primary_ips = {}
        for device in device_queryset:
            self.primary_ips[device.id] = device.primary_ip.id

    def load_param_last_network_data_sync(self, parameter_name, database_object):
        """Return None or the current date depending on the config setting for sync dates."""
        print("call 1")
        if type(database_object) is Device:
            print("call 2")
            if app_settings.get("track_network_data_sync_dates"):  # optionally sync dates
                print("call 3")
                return database_object.cf.get("last_network_data_sync")
            else:
                print("call 4")
                return None

    def load_param_mac_address(self, parameter_name, database_object):
        """Convert interface mac_address to string."""
        if database_object.mac_address:
            return str(database_object.mac_address)
        return ""

    def load_ip_addresses(self):
        """Load IP addresses into the DiffSync store.

        Only IP Addresses that were returned by the CommandGetter job should be loaded.
        """
        ip_address_hosts = set()
        for _, device_data in self.job.command_getter_result.items():
            # for interface in device_data["interfaces"]:
            for _, interface_data in device_data["interfaces"].items():
                for ip_address in interface_data["ip_addresses"]:
                    if ip_address:
                        ip_address_hosts.add(ip_address["ip_address"])
        if "" in ip_address_hosts:
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

        Only Vlans that were returned by the CommandGetter job should be synced.
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
        """
        Load Tagged VLAN interface assignments into the Diffsync store.

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
                self.job.logger.debug(f"Tagged Vlan to interface: {network_tagged_vlans_to_interface} loaded.")

    def load_untagged_vlan_to_interface(self):
        """
        Load UnTagged VLAN interface assignments into the Diffsync store.

        Only UnTagged Vlan assignments that were returned by the CommandGetter job should be synced.
        """
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            untagged_vlan = {}
            if interface.untagged_vlan:
                untagged_vlan["name"] = interface.untagged_vlan.name
                untagged_vlan["id"] = str(interface.untagged_vlan.vid)

            network_untagged_vlan_to_interface = self.untagged_vlan_to_interface(
                diffsync=self,
                device__name=interface.device.name,
                name=interface.name,
                untagged_vlan=untagged_vlan,
            )
            network_untagged_vlan_to_interface.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
            self.add(network_untagged_vlan_to_interface)
            if self.job.debug:
                self.job.logger.debug(f"Unagged Vlan to interface: {network_untagged_vlan_to_interface} loaded.")

    def load_lag_to_interface(self):
        """
        Load Lag interface assignments into the Diffsync store.

        Only Lag assignments that were returned by the CommandGetter job should be synced.
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

    def load_vrfs(self):
        """
        Load Vrfs into the Diffsync store.

        Only Vrfs that were returned by the CommandGetter job should be synced.
        """
        for vrf in VRF.objects.all():
            network_vrf = self.vrf(
                diffsync=self,
                name=vrf.name,
                namespace__name=vrf.namespace.name,
            )
            try:
                network_vrf.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
                self.add(network_vrf)
                if self.job.debug:
                    self.job.logger.debug(f"Vrf {network_vrf} loaded.")
            except diffsync.exceptions.ObjectAlreadyExists:
                pass

    def load_vrf_to_interface(self):
        """
        Load Vrf to  interface assignments into the Diffsync store.

        Only Vrf assignments that were returned by the CommandGetter job should be synced.
        """
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            vrf = {}
            if interface.vrf:
                vrf["name"] = interface.vrf.name

            network_vrf_to_interface = self.vrf_to_interface(
                diffsync=self,
                device__name=interface.device.name,
                name=interface.name,
                vrf=vrf,
            )
            network_vrf_to_interface.model_flags = DiffSyncModelFlags.SKIP_UNMATCHED_DST
            self.add(network_vrf_to_interface)
            if self.job.debug:
                self.job.logger.debug(f"Vrf to interface: {network_vrf_to_interface} loaded.")

    def load(self):
        """Generic implementation of the load function."""
        if not hasattr(self, "top_level") or not self.top_level:
            raise ValueError("'top_level' needs to be set on the class.")

        self._cache_primary_ips(device_queryset=self.job.devices_to_load)
        for model_name in self.top_level:
            if model_name == "ip_address":
                self.load_ip_addresses()
            elif model_name == "vlan":
                if self.job.sync_vlans:
                    self.load_vlans()
            elif model_name == "vrf":
                if self.job.sync_vrfs:
                    self.load_vrfs()
            elif model_name == "tagged_vlans_to_interface":
                if self.job.sync_vlans:
                    self.load_tagged_vlans_to_interface()
            elif model_name == "untagged_vlan_to_interface":
                if self.job.sync_vlans:
                    self.load_untagged_vlan_to_interface()
            elif model_name == "lag_to_interface":
                self.load_lag_to_interface()
            elif model_name == "vrf_to_interface":
                if self.job.sync_vrfs:
                    self.load_vrf_to_interface()
            else:
                diffsync_model = self._get_diffsync_class(model_name)
                self._load_objects(diffsync_model)

    def sync_complete(self, source, diff, *args, **kwargs):
        """
        Assign the primary ip address to a device and update the management interface setting.

        Syncing interfaces may result in the deletion of the original management interface. If
        this happens, the primary IP Address for the device should be set and the management only
        option on the appropriate interface should be set to True.

        This method only runs if data was changed.
        """
        if self.job.debug:
            self.job.logger.debug("Sync Complete method called, checking for missing primary ip addresses...")
        for device in self.job.devices_to_load.all():  # refresh queryset after sync is complete
            if not device.primary_ip:
                ip_address = ""
                try:
                    ip_address = IPAddress.objects.get(id=self.primary_ips[device.id])
                    device.primary_ip4 = ip_address
                    device.validated_save()
                    self.job.logger.info(f"Assigning {ip_address} as primary IP Address for Device: {device.name}")
                except Exception as err:  # pylint: disable=broad-exception-caught
                    self.job.logger.error(
                        f"Unable to set Primary IP for {device.name}, {err.args}. "
                        "Please check the primary IP Address assignment for this device."
                    )
                if ip_address:
                    try:
                        interface = Interface.objects.get(device=device, ip_addresses__in=[ip_address])
                        interface.mgmt_only = True
                        interface.validated_save()
                        self.job.logger.info(
                            f"Management only set for interface: {interface.name} on device: {device.name}"
                        )
                    except Exception as err:  # pylint: disable=broad-exception-caught
                        self.job.logger.error(
                            "Failed to set management only on the "
                            f"management interface for {device.name}, {err}, {err.args}"
                        )
                else:
                    self.job.logger.error(
                        f"Failed to set management only on the managmeent interface for {device.name}"
                    )
        return super().sync_complete(source, diff, *args, **kwargs)


class MacUnixExpandedUppercase(mac_unix_expanded):
    """Mac Unix Expanded Uppercase."""

    word_fmt = "%.2X"


class SyncNetworkDataNetworkAdapter(diffsync.DiffSync):
    """Adapter for loading Network data."""

    def __init__(self, *args, job, sync=None, **kwargs):
        """Instantiate this class, but do not load data immediately from the local system."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync

    device = sync_network_data_models.SyncNetworkDataDevice
    interface = sync_network_data_models.SyncNetworkDataInterface
    ip_address = sync_network_data_models.SyncNetworkDataIPAddress
    ipaddress_to_interface = sync_network_data_models.SyncNetworkDataIPAddressToInterface
    vlan = sync_network_data_models.SyncNetworkDataVLAN
    vrf = sync_network_data_models.SyncNetworkDataVRF
    tagged_vlans_to_interface = sync_network_data_models.SyncNetworkDataTaggedVlansToInterface
    untagged_vlan_to_interface = sync_network_data_models.SyncNetworkDataUnTaggedVlanToInterface
    lag_to_interface = sync_network_data_models.SyncNetworkDataLagToInterface
    vrf_to_interface = sync_network_data_models.SyncNetworkDataVrfToInterface

    top_level = [
        "ip_address",
        "vlan",
        "vrf",
        "device",
        "ipaddress_to_interface",
        "untagged_vlan_to_interface",
        "tagged_vlans_to_interface",
        "lag_to_interface",
        "vrf_to_interface",
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
        result = sync_network_data_command_getter(
            self.job.job_result, self.job.logger.getEffectiveLevel(), self.job.job_result.task_kwargs
        )
        if self.job.debug:
            self.job.logger.debug(f"Command Getter Result: {result}")
        # verify data returned is a dict
        data_type_check = diffsync_utils.check_data_type(result)
        if self.job.debug:
            self.job.logger.debug(f"CommandGetter data type check resut: {data_type_check}")
        if data_type_check:
            self._handle_failed_devices(device_data=result)
        else:
            self.job.logger.error(
                "Data returned from CommandGetter is not the correct type. No devices will be onboarded"
            )
            raise ValidationError("Unexpected data returend from CommandGetter.")

    def _process_mac_address(self, mac_address):
        """Convert a mac address to match the value stored by Nautobot."""
        if mac_address:
            return str(EUI(mac_address, version=48, dialect=MacUnixExpandedUppercase))
        return ""

    def _get_sync_date(self):
        """Return None or the current date depending on the config setting for sync dates."""
        if app_settings.get("track_network_data_sync_dates"):  # optionally sync dates
            return datetime.datetime.now().date().isoformat()
        else:
            return "0001-01-01"

    def load_devices(self):
        """Load devices into the DiffSync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            network_device = self.device(
                diffsync=self,
                name=hostname,
                serial=device_data["serial"],
                last_network_data_sync=self._get_sync_date(),
            )
            self.add(network_device)
            if self.job.debug:
                self.job.logger.debug(f"Device {network_device} loaded.")
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                network_interface = self.load_interface(hostname, interface_name, interface_data)
                network_device.add_child(network_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Interface {network_interface} loaded.")

    def _get_vlan_name(self, interface_data):
        """Given interface data returned from a device, process and return the vlan name."""
        vlan_name = ""
        if self.job.sync_vlans:
            vlan_name = interface_data["untagged_vlan"]["name"] if interface_data["untagged_vlan"] else ""
        return vlan_name

    def load_interface(self, hostname, interface_name, interface_data):
        """Load an interface into the DiffSync store."""
        network_interface = self.interface(
            diffsync=self,
            name=interface_name,
            device__name=hostname,
            status__name=self.job.interface_status.name,
            type=interface_data["type"],
            mac_address=self._process_mac_address(mac_address=interface_data["mac_address"]),
            mtu=interface_data["mtu"] if interface_data["mtu"] else 1500,
            description=interface_data["description"],
            enabled=interface_data["link_status"],
            mode=interface_data["802.1Q_mode"],
            untagged_vlan__name=self._get_vlan_name(interface_data=interface_data),
        )
        self.add(network_interface)
        if self.job.debug:
            self.job.logger.debug(f"Interface {network_interface} loaded.")
        return network_interface

    def load_ip_addresses(self):
        """Load IP addresses into the DiffSync store."""
        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            if self.job.debug:
                self.job.logger.debug(f"Loading IP Addresses from {hostname}")
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                if interface_data["ip_addresses"]:
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
            if self.job.debug:
                self.job.logger.debug(f"Loading Vlans from {hostname}")
            # for interface in device_data["interfaces"]:
            for _, interface_data in device_data["interfaces"].items():
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

    def load_vrfs(self):
        """Load vrfs into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            if self.job.debug:
                self.job.logger.debug(f"Loading Vrfs from {hostname}")
            # for interface in device_data["interfaces"]:
            for _, interface_data in device_data["interfaces"].items():
                if interface_data["vrf"]:
                    network_vrf = self.vrf(
                        diffsync=self,
                        name=interface_data["vrf"]["name"],
                        namespace__name=self.job.namespace.name,
                    )
                    try:
                        self.add(network_vrf)
                        if self.job.debug:
                            self.job.logger.debug(f"Vrf {network_vrf} loaded.")
                    except diffsync.exceptions.ObjectAlreadyExists:
                        pass

    def load_ip_address_to_interfaces(self):
        """Load ip address interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():  # pylint: disable=too-many-nested-blocks
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
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
                            self.job.logger.debug(f"IP Address to interface {network_ip_address_to_interface} loaded.")

    def load_tagged_vlans_to_interface(self):
        """Load tagged vlan to interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                network_tagged_vlans_to_interface = self.tagged_vlans_to_interface(
                    diffsync=self,
                    device__name=hostname,
                    name=interface_name,
                    tagged_vlans=interface_data["tagged_vlans"],
                )
                self.add(network_tagged_vlans_to_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Tagged Vlan to interface {network_tagged_vlans_to_interface} loaded.")

    def load_untagged_vlan_to_interface(self):
        """Load untagged vlan to interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                network_untagged_vlan_to_interface = self.untagged_vlan_to_interface(
                    diffsync=self,
                    device__name=hostname,
                    name=interface_name,
                    untagged_vlan=interface_data["untagged_vlan"],
                )
                self.add(network_untagged_vlan_to_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Untagged Vlan to interface {network_untagged_vlan_to_interface} loaded.")

    def load_lag_to_interface(self):
        """Load lag interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                network_lag_to_interface = self.lag_to_interface(
                    diffsync=self,
                    device__name=hostname,
                    name=interface_name,
                    lag__interface__name=interface_data["lag"] if interface_data["lag"] else "",
                )
                self.add(network_lag_to_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Lag to interface {network_lag_to_interface} loaded.")

    def load_vrf_to_interface(self):
        """Load Vrf to interface assignments into the Diffsync store."""
        for hostname, device_data in self.job.command_getter_result.items():
            # for interface in device_data["interfaces"]:
            for interface_name, interface_data in device_data["interfaces"].items():
                network_vrf_to_interface = self.vrf_to_interface(
                    diffsync=self,
                    device__name=hostname,
                    name=interface_name,
                    vrf=interface_data["vrf"],
                )
                self.add(network_vrf_to_interface)
                if self.job.debug:
                    self.job.logger.debug(f"Untagged Vlan to interface {network_vrf_to_interface} loaded.")

    def load(self):
        """Load network data."""
        self.execute_command_getter()
        self.load_ip_addresses()
        if self.job.sync_vlans:
            self.load_vlans()
        if self.job.sync_vrfs:
            self.load_vrfs()
        self.load_devices()
        self.load_ip_address_to_interfaces()
        if self.job.sync_vlans:
            self.load_tagged_vlans_to_interface()
            self.load_untagged_vlan_to_interface()
        self.load_lag_to_interface()
        if self.job.sync_vrfs:
            self.load_vrf_to_interface()
