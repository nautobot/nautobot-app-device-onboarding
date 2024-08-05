"""Diffsync models."""

from typing import Optional

from diffsync import DiffSyncModel
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from nautobot.apps.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Platform
from nautobot.extras.models import Role, SecretsGroup, Status
from nautobot.ipam.models import IPAddressToInterface
from nautobot_ssot.contrib import NautobotModel

from nautobot_device_onboarding.utils import diffsync_utils


class SyncDevicesDevice(DiffSyncModel):
    """Diffsync model for device data."""

    _modelname = "device"
    _identifiers = (
        "location__name",
        "name",
        "serial",
    )
    _attributes = (
        "device_type__model",
        "mask_length",
        "primary_ip4__host",
        "primary_ip4__status__name",
        "platform__name",
        "role__name",
        "secrets_group__name",
        "status__name",
        "interfaces",
    )

    name: str
    location__name: str
    serial: str

    device_type__model: Optional[str]
    mask_length: Optional[int]
    primary_ip4__host: Optional[str]
    primary_ip4__status__name: Optional[str]
    platform__name: Optional[str]
    role__name: Optional[str]
    secrets_group__name: Optional[str]
    status__name: Optional[str]

    interfaces: Optional[list]

    @classmethod
    def _get_or_create_device(cls, diffsync, ids, attrs):
        """Attempt to get a Device, create a new one if necessary."""
        device = None
        try:
            # Only Devices with a primary ip address are loaded from Nautobot when syncing.
            # If a device is found in Nautobot with a matching name and location as the
            # device being created, but the primary ip address doesn't match an ip address entered,
            # (or doesn't exist) the matching device will be updated or skipped based on user preference.

            location = diffsync_utils.retrieve_submitted_value(
                job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="location"
            )
            platform = Platform.objects.get(name=attrs["platform__name"])
            device = Device.objects.get(name=ids["name"], location=location)
            update_devices_without_primary_ip = diffsync_utils.retrieve_submitted_value(
                job=diffsync.job,
                ip_address=attrs["primary_ip4__host"],
                query_string="update_devices_without_primary_ip",
            )
            if update_devices_without_primary_ip:
                diffsync.job.logger.warning(
                    f"Device {device.name} at location {location.name} already exists in Nautobot "
                    "but the primary ip address either does not exist, or doesn't match an entered ip address. "
                    "This device will be updated. This update may result in multiple IP Address assignments "
                    "to an interface on the device."
                )
                device = cls._update_device_with_attrs(device, platform, ids, attrs, diffsync)
            else:
                diffsync.job.logger.warning(
                    f"Device {device.name} at location {location.name} already exists in Nautobot "
                    "but the primary ip address either does not exist, or doesn't match an entered ip address. "
                    "IP Address, this device will be skipped."
                )
                return None

        except ObjectDoesNotExist:
            # Create Device
            device = Device(
                location=location,
                status=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="device_status"
                ),
                role=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="device_role"
                ),
                device_type=DeviceType.objects.get(model=attrs["device_type__model"]),
                name=ids["name"],
                platform=platform,
                secrets_group=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="secrets_group"
                ),
                serial=ids["serial"],
            )
            device.validated_save()
        return device

    @classmethod
    def _get_or_create_interface(cls, diffsync, device, ip_address, interface_name):
        """Attempt to get a Device Interface, create a new one if necessary."""
        device_interface = None
        try:
            device_interface = Interface.objects.get(
                name=interface_name,
                device=device,
            )
        except ObjectDoesNotExist:
            try:
                device_interface = Interface(
                    name=interface_name,
                    mgmt_only=diffsync_utils.retrieve_submitted_value(
                        job=diffsync.job, ip_address=ip_address, query_string="set_mgmt_only"
                    ),
                    status=diffsync_utils.retrieve_submitted_value(
                        job=diffsync.job, ip_address=ip_address, query_string="interface_status"
                    ),
                    type=InterfaceTypeChoices.TYPE_OTHER,
                    device=device,
                )
                device_interface.validated_save()
            except Exception as err:
                diffsync.job.logger.error(f"Device Interface could not be created, {err}")
        return device_interface

    @classmethod
    def _get_or_create_ip_address_to_interface(cls, diffsync, interface, ip_address):
        """Attempt to get a Device Interface, create a new one if necessary."""
        interface_assignment = None
        try:
            interface_assignment = IPAddressToInterface.objects.get(
                ip_address=ip_address,
                interface=interface,
            )
        except ObjectDoesNotExist:
            try:
                interface_assignment = IPAddressToInterface(
                    ip_address=ip_address,
                    interface=interface,
                )
                interface_assignment.validated_save()
            except Exception as err:
                diffsync.job.logger.error(f"{ip_address} failed to assign to assign to interface {err}")
        return interface_assignment

    @classmethod
    def _update_device_with_attrs(cls, device, platform, ids, attrs, diffsync):
        """Update a Nautobot device instance with attrs."""
        device.location = diffsync_utils.retrieve_submitted_value(
            job=diffsync.job,
            ip_address=attrs["primary_ip4__host"],
            query_string="location",
        )
        device.status = diffsync_utils.retrieve_submitted_value(
            job=diffsync.job,
            ip_address=attrs["primary_ip4__host"],
            query_string="device_status",
        )
        device.role = diffsync_utils.retrieve_submitted_value(
            job=diffsync.job,
            ip_address=attrs["primary_ip4__host"],
            query_string="device_role",
        )
        device.device_type = DeviceType.objects.get(model=attrs["device_type__model"])
        device.platform = platform
        device.secrets_group = diffsync_utils.retrieve_submitted_value(
            job=diffsync.job,
            ip_address=attrs["primary_ip4__host"],
            query_string="secrets_group",
        )
        device.serial = ids["serial"]

        return device

    def _remove_old_interface_assignment(self, device, ip_address):
        """Remove a device's primary IP address from an interface."""
        try:
            old_interface = Interface.objects.get(
                device=device,
                ip_addresses__in=[ip_address],
            )
            old_interface_assignment = IPAddressToInterface.objects.get(
                interface=old_interface,
                ip_address=ip_address,
            )
            old_interface_assignment.delete()
            if self.diffsync.job.debug:
                self.diffsync.job.logger.debug(f"Interface assignment deleted: {old_interface_assignment}")
        except MultipleObjectsReturned:
            self.diffsync.job.logger.warning(
                f"{ip_address} is assigned to multiple interfaces. The primary IP Address for this "
                "device will be assigned to an interface but duplicate assignments will remain."
            )
        except ObjectDoesNotExist:
            pass

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new nautobot device using data scraped from a device."""
        if diffsync.job.debug:
            diffsync.job.logger.debug(f"Creating device {ids} with {attrs}")

        # Get or create Device, Interface and IP Address
        device = cls._get_or_create_device(diffsync, ids, attrs)
        if device:
            ip_address = diffsync_utils.get_or_create_ip_address(
                host=attrs["primary_ip4__host"],
                mask_length=attrs["mask_length"],
                namespace=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="namespace"
                ),
                default_ip_status=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                ),
                default_prefix_status=diffsync_utils.retrieve_submitted_value(
                    job=diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                ),
                job=diffsync.job,
            )
            interface = cls._get_or_create_interface(
                diffsync=diffsync,
                device=device,
                ip_address=attrs["primary_ip4__host"],
                interface_name=attrs["interfaces"][0],
            )
            cls._get_or_create_ip_address_to_interface(diffsync=diffsync, ip_address=ip_address, interface=interface)
            # Assign primary IP Address to Device
            device.primary_ip4 = ip_address

            try:
                device.validated_save()
            except ValidationError as err:
                diffsync.job.logger.error(f"Failed to create or update Device: {ids['name']}, {err}")
                raise ValidationError(err)
        else:
            diffsync.job.logger.error(f"Failed create or update Device: {ids['name']}")

        return super().create(diffsync=diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update an existing nautobot device using data scraped from a device."""
        device = Device.objects.get(name=self.name, location__name=self.location__name)

        if self.diffsync.job.debug:
            self.diffsync.job.logger.debug(f"Updating {device.name} with attrs: {attrs}")
        if attrs.get("device_type__model"):
            device.device_type = DeviceType.objects.get(model=attrs.get("device_type__model"))
        if attrs.get("platform__name"):
            device.platform = Platform.objects.get(name=attrs.get("platform__name"))
        if attrs.get("role__name"):
            device.role = Role.objects.get(name=attrs.get("role__name"))
        if attrs.get("status__name"):
            device.status = Status.objects.get(name=attrs.get("status__name"))
        if attrs.get("secrets_group__name"):
            device.secrets_group = SecretsGroup.objects.get(name=attrs.get("secrets_group__name"))

        if attrs.get("interfaces"):
            # Update both the interface and primary ip address
            if attrs.get("primary_ip4__host"):
                # If the primary ip address is being updated, the mask length must be included
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length

                ip_address = diffsync_utils.get_or_create_ip_address(
                    host=attrs["primary_ip4__host"],
                    mask_length=attrs["mask_length"],
                    namespace=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="namespace"
                    ),
                    default_ip_status=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                    ),
                    default_prefix_status=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                    ),
                    job=self.diffsync.job,
                )
                new_interface = self._get_or_create_interface(
                    diffsync=self.diffsync,
                    device=device,
                    ip_address=attrs["primary_ip4__host"],
                    interface_name=attrs["interfaces"][0],
                )
                self._get_or_create_ip_address_to_interface(
                    diffsync=self.diffsync, ip_address=ip_address, interface=new_interface
                )
                device.primary_ip4 = ip_address
            # Update the interface only
            else:
                # Remove the primary IP Address from the old managment interface
                self._remove_old_interface_assignment(device=device, ip_address=device.primary_ip4)

                new_interface = self._get_or_create_interface(
                    diffsync=self.diffsync,
                    device=device,
                    ip_address=self.primary_ip4__host,
                    interface_name=attrs["interfaces"][0],
                )
                self._get_or_create_ip_address_to_interface(
                    diffsync=self.diffsync, ip_address=device.primary_ip4, interface=new_interface
                )
        else:
            # Update the primary ip address only
            # This edge case is unlikely to occur. A device with primary_ip that doesn't mach what was entered
            # on the job form should be filtered out of the sync and later caught by _get_or_create_device()
            if attrs.get("primary_ip4__host"):
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length

                new_ip_address = diffsync_utils.get_or_create_ip_address(
                    host=attrs["primary_ip4__host"],
                    mask_length=attrs["mask_length"],
                    namespace=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="namespace"
                    ),
                    default_ip_status=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                    ),
                    default_prefix_status=diffsync_utils.retrieve_submitted_value(
                        job=self.diffsync.job, ip_address=attrs["primary_ip4__host"], query_string="ip_address_status"
                    ),
                    job=self.diffsync.job,
                )
                self._remove_old_interface_assignment(device=device, ip_address=device.primary_ip4)
                existing_interface = self._get_or_create_interface(
                    diffsync=self.diffsync,
                    device=device,
                    ip_address=new_ip_address,
                    interface_name=self.get_attrs()["interfaces"][0],
                )
                self._get_or_create_ip_address_to_interface(
                    diffsync=self.diffsync, ip_address=new_ip_address, interface=existing_interface
                )
                device.primary_ip4 = new_ip_address
        try:
            device.validated_save()
        except ValidationError as err:
            self.diffsync.job.logger.error(f"Device {device.name} failed to update, {err}")
        return super().update(attrs)


class SyncDevicesDeviceType(NautobotModel):
    """Diffsync model for device type data."""

    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model", "manufacturer__name")
    _attributes = ("part_number",)

    model: str
    manufacturer__name: str

    part_number: str


class SyncDevicesManufacturer(NautobotModel):
    """Diffsync model for manufacturer data."""

    _modelname = "manufacturer"
    _model = Manufacturer
    _identifiers = ("name",)

    name: str


class SyncDevicesPlatform(NautobotModel):
    """Diffsync model for platform data."""

    _modelname = "platform"
    _model = Platform
    _identifiers = ("name",)
    _attributes = ("network_driver", "manufacturer__name")

    name: str

    network_driver: Optional[str]
    manufacturer__name: Optional[str]
