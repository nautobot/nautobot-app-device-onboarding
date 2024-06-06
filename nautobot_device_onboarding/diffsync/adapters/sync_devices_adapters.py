"""DiffSync adapters."""

from collections import defaultdict
from typing import DefaultDict, Dict, FrozenSet, Hashable, Tuple, Type

import diffsync
import netaddr
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Model
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform

from nautobot_device_onboarding.diffsync.models import sync_devices_models
from nautobot_device_onboarding.nornir_plays.command_getter import sync_devices_command_getter
from nautobot_device_onboarding.utils import diffsync_utils

ParameterSet = FrozenSet[Tuple[str, Hashable]]


class SyncDevicesNautobotAdapter(diffsync.DiffSync):
    """Adapter for loading Nautobot data."""

    manufacturer = sync_devices_models.SyncDevicesManufacturer
    platform = sync_devices_models.SyncDevicesPlatform
    device = sync_devices_models.SyncDevicesDevice
    device_type = sync_devices_models.SyncDevicesDeviceType

    top_level = ["manufacturer", "platform", "device_type", "device"]

    # This dictionary acts as an ORM cache.
    _cache: DefaultDict[str, Dict[ParameterSet, Model]]
    _cache_hits: DefaultDict[str, int] = defaultdict(int)

    def __init__(self, job, sync, *args, **kwargs):
        """Initialize the SyncDevicesNautobotAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.invalidate_cache()

    def invalidate_cache(self, zero_out_hits=True):
        """Invalidates all the objects in the ORM cache."""
        self._cache = defaultdict(dict)
        if zero_out_hits:
            self._cache_hits = defaultdict(int)

    def get_from_orm_cache(self, parameters: Dict, model_class: Type[Model]):
        """Retrieve an object from the ORM or the cache."""
        parameter_set = frozenset(parameters.items())
        content_type = ContentType.objects.get_for_model(model_class)
        model_cache_key = f"{content_type.app_label}.{content_type.model}"
        if cached_object := self._cache[model_cache_key].get(parameter_set):
            self._cache_hits[model_cache_key] += 1
            return cached_object
        # As we are using `get` here, this will error if there is not exactly one object that corresponds to the
        # parameter set. We intentionally pass these errors through.
        self._cache[model_cache_key][parameter_set] = model_class.objects.get(**dict(parameter_set))
        return self._cache[model_cache_key][parameter_set]

    def load_manufacturers(self):
        """Load manufacturer data from Nautobot."""
        for manufacturer in Manufacturer.objects.all():
            if self.job.debug:
                self.job.logger.debug("Loading Manufacturer data from Nautobot...")
            onboarding_manufacturer = self.manufacturer(diffsync=self, name=manufacturer.name)
            self.add(onboarding_manufacturer)
            if self.job.debug:
                self.job.logger.debug(f"Manufacturer: {manufacturer.name} loaded.")

    def load_platforms(self):
        """Load platform data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading Platform data from Nautobot...")
        for platform in Platform.objects.all():
            onboarding_platform = self.platform(
                diffsync=self,
                name=platform.name,
                network_driver=platform.network_driver if platform.network_driver else "",
                manufacturer__name=platform.manufacturer.name if platform.manufacturer else None,
            )
            self.add(onboarding_platform)
            if self.job.debug:
                self.job.logger.debug(f"Platform: {platform.name} loaded.")

    def load_device_types(self):
        """Load device type data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading DeviceType data from Nautobot...")
        for device_type in DeviceType.objects.all():
            onboarding_device_type = self.device_type(
                diffsync=self,
                model=device_type.model,
                part_number=device_type.model,
                manufacturer__name=device_type.manufacturer.name,
            )
            self.add(onboarding_device_type)
            if self.job.debug:
                self.job.logger.debug(f"DeviceType: {device_type.model} loaded.")

    def load_devices(self):
        """Load device data from Nautobot."""
        if self.job.debug:
            self.job.logger.debug("Loading Device data from Nautobot...")

        for device in Device.objects.filter(primary_ip4__host__in=self.job.ip_addresses):
            interface_list = []
            # Only interfaces with the device's primary ip should be considered for diff calculations
            # Ultimately, only the first matching interface is used but this list could support multiple
            # interface syncs in the future.
            for interface in device.interfaces.all():
                if device.primary_ip4 in interface.ip_addresses.all():
                    interface_list.append(interface.name)
            if interface_list:
                interface_list.sort()
                interfaces = [interface_list[0]]
            else:
                interfaces = []
            onboarding_device = self.device(
                diffsync=self,
                device_type__model=device.device_type.model,
                location__name=device.location.name,
                name=device.name,
                platform__name=device.platform.name if device.platform else "",
                primary_ip4__host=device.primary_ip4.host if device.primary_ip4 else "",
                primary_ip4__status__name=device.primary_ip4.status.name if device.primary_ip4 else "",
                role__name=device.role.name,
                status__name=device.status.name,
                secrets_group__name=device.secrets_group.name if device.secrets_group else "",
                interfaces=interfaces,
                mask_length=device.primary_ip4.mask_length if device.primary_ip4 else None,
                serial=device.serial,
            )
            self.add(onboarding_device)
            if self.job.debug:
                self.job.logger.debug(f"Device: {device.name} loaded.")

    def load(self):
        """Load nautobot data."""
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()


class SyncDevicesNetworkAdapter(diffsync.DiffSync):
    """Adapter for loading device data from a network."""

    manufacturer = sync_devices_models.SyncDevicesManufacturer
    platform = sync_devices_models.SyncDevicesPlatform
    device = sync_devices_models.SyncDevicesDevice
    device_type = sync_devices_models.SyncDevicesDeviceType

    top_level = ["manufacturer", "platform", "device_type", "device"]

    def __init__(self, job, sync, *args, **kwargs):
        """Initialize the SyncDevicesNetworkAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.device_data = None
        self.failed_ip_addresses = []

    def _validate_ip_addresses(self, ip_addresses):
        """Validate the format of each IP Address in a list of IP Addresses."""
        # Validate IP Addresses
        validation_successful = True
        for ip_address in ip_addresses:
            try:
                netaddr.IPAddress(ip_address)
            except netaddr.AddrFormatError:
                self.job.logger.error(f"[{ip_address}] is not a valid IP Address ")
                validation_successful = False
        if validation_successful:
            return True
        raise netaddr.AddrConversionError

    def _handle_failed_devices(self, device_data):
        """
        Handle result data from failed devices.

        If a device fails to return expected data, log the result
        and remove it from the data to be loaded into the diffsync store.
        """
        self.device_data = None
        self.failed_ip_addresses = []
        for ip_address in device_data:
            if not device_data[ip_address]:
                self.job.logger.error(f"{ip_address}: Connection or data error, this device will not be synced.")
                self.failed_ip_addresses.append(ip_address)
        for ip_address in self.failed_ip_addresses:
            del device_data[ip_address]
        self.device_data = device_data

    def execute_command_getter(self):
        """Start the CommandGetterDO job to query devices for data."""
        if not self.job.processed_csv_data:
            if self.job.platform:
                if not self.job.platform.network_driver:
                    self.job.logger.error(
                        f"The selected platform, {self.job.platform} "
                        "does not have a network driver, please update the Platform."
                    )
                    raise Exception("Platform.network_driver missing")  # pylint: disable=broad-exception-raised

        result = sync_devices_command_getter(
            self.job.job_result, self.job.logger.getEffectiveLevel(), self.job.job_result.task_kwargs
        )
        if self.job.debug:
            self.job.logger.debug(f"Command Getter Result: {result}")
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

    def _add_ip_address_to_failed_list(self, ip_address):
        """If an a model fails to load, add the ip address to the failed list for logging."""
        if ip_address not in self.failed_ip_addresses:
            self.failed_ip_addresses.append(ip_address)

    def load_manufacturers(self):
        """Load manufacturers into the DiffSync store."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading manufacturer data for {ip_address}")
            onboarding_manufacturer = None
            try:
                onboarding_manufacturer = self.manufacturer(
                    diffsync=self,
                    name=self.device_data[ip_address]["manufacturer"],
                )
            except KeyError as err:
                self.job.logger.error(
                    f"{ip_address}: Unable to load Manufacturer due to a missing key in returned data, {err.args}"
                )
            if onboarding_manufacturer:
                try:
                    self.add(onboarding_manufacturer)
                except diffsync.ObjectAlreadyExists:
                    pass

    def load_platforms(self):
        """Load platforms into the DiffSync store."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading platform data for {ip_address}")
            onboarding_platform = None
            try:
                onboarding_platform = self.platform(
                    diffsync=self,
                    name=self.device_data[ip_address]["platform"],
                    manufacturer__name=self.device_data[ip_address]["manufacturer"],
                    network_driver=self.device_data[ip_address]["network_driver"],
                )
            except KeyError as err:
                self.job.logger.error(
                    f"{ip_address}: Unable to load Platform due to a missing key in returned data, {err.args}"
                )
            if onboarding_platform:
                try:
                    self.add(onboarding_platform)
                except diffsync.ObjectAlreadyExists:
                    pass

    def load_device_types(self):
        """Load device types into the DiffSync store."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device_type data for {ip_address}")
            onboarding_device_type = None
            try:
                onboarding_device_type = self.device_type(
                    diffsync=self,
                    model=self.device_data[ip_address]["device_type"],
                    part_number=self.device_data[ip_address]["device_type"],
                    manufacturer__name=self.device_data[ip_address]["manufacturer"],
                )
            except KeyError as err:
                self.job.logger.error(
                    f"{ip_address}: Unable to load DeviceType due to a missing key in returned data, {err.args}"
                )
            if onboarding_device_type:
                try:
                    self.add(onboarding_device_type)
                except diffsync.ObjectAlreadyExists:
                    pass

    def _fields_missing_data(self, device_data, ip_address, platform):
        """Verify that all of the fields returned from a device actually contain data."""
        fields_missing_data = []
        required_fields_from_device = ["device_type", "hostname", "mgmt_interface", "mask_length", "serial"]
        if platform:  # platform is only retruned with device data if not provided on the job form/csv
            required_fields_from_device.append("platform")
        for field in required_fields_from_device:
            data = device_data[ip_address]
            if not data.get(field):
                fields_missing_data.append(field)
        return fields_missing_data

    def load_devices(self):
        """Load devices into the DiffSync store."""
        for ip_address in self.device_data:
            if self.job.debug:
                self.job.logger.debug(f"loading device data for {ip_address}")
            platform = None  # If an excption is caught below, the platform must still be set.
            onboarding_device = None
            try:
                location = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="location"
                )
                platform = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="platform"
                )
                primary_ip4__status = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="ip_address_status"
                )
                device_role = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="device_role"
                )
                device_status = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="device_status"
                )
                secrets_group = diffsync_utils.retrieve_submitted_value(
                    job=self.job, ip_address=ip_address, query_string="secrets_group"
                )

                onboarding_device = self.device(
                    diffsync=self,
                    device_type__model=self.device_data[ip_address]["device_type"],
                    location__name=location.name,
                    name=self.device_data[ip_address]["hostname"],
                    platform__name=platform.name if platform else self.device_data[ip_address]["platform"],
                    primary_ip4__host=ip_address,
                    primary_ip4__status__name=primary_ip4__status.name,
                    role__name=device_role.name,
                    status__name=device_status.name,
                    secrets_group__name=secrets_group.name,
                    interfaces=[self.device_data[ip_address]["mgmt_interface"]],
                    mask_length=int(self.device_data[ip_address]["mask_length"]),
                    serial=self.device_data[ip_address]["serial"],
                )
            except KeyError as err:
                self.job.logger.error(
                    f"{ip_address}: Unable to load Device due to a missing key in returned data, {err.args}, {err}"
                )
                if ip_address not in self.failed_ip_addresses:
                    self.failed_ip_addresses.append(ip_address)
            except ValueError as err:
                self.job.logger.error(
                    f"{ip_address}: Unable to load Device due to invalid data type in data return, {err}"
                )

            fields_missing_data = self._fields_missing_data(
                device_data=self.device_data, ip_address=ip_address, platform=platform
            )
            if fields_missing_data:
                onboarding_device = None
                self.job.logger.error(
                    f"Unable to onbaord {ip_address}, returned data missing for {fields_missing_data}"
                )
            else:
                if onboarding_device:
                    try:
                        self.add(onboarding_device)
                        if self.job.debug:
                            self.job.logger.debug(f"Device: {self.device_data[ip_address]['hostname']} loaded.")
                    except diffsync.ObjectAlreadyExists:
                        self.job.logger.error(
                            f"Device: {self.device_data[ip_address]['hostname']} has already been loaded! "
                            f"Duplicate devices will not be synced. "
                            f"[Serial Number: {self.device_data[ip_address]['serial']}, "
                            f"IP Address: {ip_address}]"
                        )
                else:
                    self._add_ip_address_to_failed_list(ip_address=ip_address)
                    if self.job.debug:
                        self.job.logger.debug(f"{ip_address} was added to the failed ip_address list")

    def load(self):
        """Load network data."""
        self._validate_ip_addresses(self.job.ip_addresses)
        self.execute_command_getter()
        self.load_manufacturers()
        self.load_platforms()
        self.load_device_types()
        self.load_devices()

        if self.failed_ip_addresses:
            self.job.logger.warning(f"Failed IP Addresses: {self.failed_ip_addresses}")
