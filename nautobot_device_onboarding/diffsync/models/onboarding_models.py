"""Diffsync models."""

from typing import Optional

from diffsync import DiffSyncModel
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from nautobot.apps.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Platform
from nautobot.extras.models import Role, SecretsGroup, Status
from nautobot_ssot.contrib import NautobotModel

from nautobot_device_onboarding.utils import diffsync_utils


class OnboardingDevice(DiffSyncModel):
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
        "prefix_length",
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
    prefix_length: Optional[int]
    platform__name: Optional[str]
    role__name: Optional[str]
    secrets_group__name: Optional[str]
    status__name: Optional[str]

    interfaces: Optional[list]

    @classmethod
    def _get_or_create_device(cls, platform, diffsync, ids, attrs):
        """Attempt to get a Device, create a new one if necessary."""
        device = None
        try:
            # Only Devices with a primary ip address are loaded from Nautobot when syncing.
            # If a device is found in Nautobot with a matching name and location as the
            # device being created, but the primary ip address doesn't match an ip address entered,
            # the matching device will be updated or skipped based on user preference.

            device = Device.objects.get(
                name=ids["name"],
                location=diffsync.job.location,
            )
            if diffsync.job.update_devices_without_primary_ip:
                diffsync.job.logger.warning(
                    f"Device {ids['name']} at location {diffsync.job.location} already exists in Nautobot "
                    "but the primary ip address either does not exist, or doesn't match an entered ip address. "
                    "This device will be updated."
                )
                device = cls._update_device_with_attrs(device, platform, ids, attrs, diffsync)
            else:
                diffsync.job.logger.warning(
                    f"Device {ids['name']} at location {diffsync.job.location} already exists in Nautobot "
                    "but the primary ip address either does not exist, or doesn't match an entered ip address. "
                    "IP Address, this device will be skipped."
                )
                return None

        except ObjectDoesNotExist:
            # Create Device
            device = Device(
                location=diffsync.job.location,
                status=diffsync.job.device_status,
                role=diffsync.job.device_role,
                device_type=DeviceType.objects.get(model=attrs["device_type__model"]),
                name=ids["name"],
                platform=platform,
                secrets_group=diffsync.job.secrets_group,
                serial=ids["serial"],
            )
            device.validated_save()
        return device

    @classmethod
    def _get_or_create_interface(cls, diffsync, device, attrs):
        """Attempt to get a Device Interface, create a new one if necessary."""
        device_interface = None
        try:
            device_interface = Interface.objects.get(
                name=attrs["interfaces"][0],
                device=device,
            )
        except ObjectDoesNotExist:
            try:
                device_interface = Interface.objects.create(
                    name=attrs["interfaces"][0],
                    mgmt_only=diffsync.job.management_only_interface,
                    status=diffsync.job.interface_status,
                    type=InterfaceTypeChoices.TYPE_OTHER,
                    device=device,
                )
            except ValidationError as err:
                diffsync.job.logger.error(f"Device Interface could not be created, {err}")
        return device_interface

    @classmethod
    def _update_device_with_attrs(cls, device, platform, ids, attrs, diffsync):
        """Update a Nautobot device instance."""
        device.location = diffsync.job.location
        device.status = diffsync.job.device_status
        device.role = diffsync.job.device_role
        device.device_type = DeviceType.objects.get(model=attrs["device_type__model"])
        device.platform = platform
        device.secrets_group = diffsync.job.secrets_group
        device.serial = ids["serial"]

        return device

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new nautobot device using data scraped from a device."""
        # Determine device platform
        platform = None
        if diffsync.job.platform:
            platform = diffsync.job.platform
        else:
            platform = Platform.objects.get(name=attrs["platform__name"])

        # Get or create Device, Interface and IP Address
        device = cls._get_or_create_device(platform, diffsync, ids, attrs)
        if device:
            ip_address = diffsync_utils.get_or_create_ip_address(
                host=attrs["primary_ip4__host"],
                mask_length=attrs["mask_length"],
                namespace=diffsync.job.namespace,
                default_ip_status=diffsync.job.ip_address_status,
                default_prefix_status=diffsync.job.ip_address_status,
                job=diffsync.job,
            )
            interface = cls._get_or_create_interface(diffsync=diffsync, device=device, attrs=attrs)
            interface.ip_addresses.add(ip_address)
            interface.validated_save()

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
        if attrs.get("serial"):
            device.primary_ip.serial = attrs.get("serial")

        if attrs.get("interfaces"):
            interface = self._get_or_create_interface(diffsync=self.diffsync, device=device, attrs=attrs)
            # Update both the interface and primary ip address
            if attrs.get("primary_ip4__host"):
                # If the primary ip address is being updated, the mask length must be included
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length

                ip_address = diffsync_utils.get_or_create_ip_address(
                    host=attrs["primary_ip4__host"],
                    mask_length=attrs["mask_length"],
                    namespace=self.diffsync.job.namespace,
                    default_ip_status=self.diffsync.job.ip_address_status,
                    default_prefix_status=self.diffsync.job.ip_address_status,
                    job=self.diffsync.job,
                )
                interface.ip_addresses.add(ip_address)
                interface.validated_save()
                # set the new ip address as the device primary ip address
                device.primary_ip4 = ip_address
                interface.validated_save()
            # Update the interface only
            else:
                # Check for an interface with a matching IP Address and remove it before
                # assigning the IP Address to the new interface
                try:
                    old_interface = Interface.objects.get(
                        device=device,
                        ip_addresses__in=[device.primary_ip4],
                    )
                    old_interface.ip_addresses.remove(device.primary_ip4)
                    interface.ip_addresses.add(device.primary_ip4)
                    interface.validated_save()
                except MultipleObjectsReturned:
                    self.diffsync.job.logger.warning(
                        f"{device.primary_ip4} is assigned to multiple interfaces. A new "
                        "interface will be created and assigned this IP Address, but the "
                        "duplicate assignments will remain."
                    )
                except ObjectDoesNotExist:
                    interface.ip_addresses.add(device.primary_ip4)
                    interface.validated_save()
        else:
            # Update the primary ip address only

            # The OnboardingNautobotAdapter only loads devices with primary ips matching those
            # entered for onboarding. This will not be called unless the adapter is changed to
            # include all devices
            if attrs.get("primary_ip4__host"):
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length

                ip_address = diffsync_utils.get_or_create_ip_address(
                    host=attrs["primary_ip4__host"],
                    mask_length=attrs["mask_length"],
                    namespace=self.diffsync.job.namespace,
                    default_ip_status=self.diffsync.job.ip_address_status,
                    default_prefix_status=self.diffsync.job.ip_address_status,
                    job=self.diffsync.job,
                )
                interface = Interface.objects.get(
                    device=device, ip_addresses__in=[device.primary_ip4], name=self.get_attrs()["interfaces"][0]
                )
                interface.ip_addresses.add(ip_address)
                interface.validated_save()
                device.primary_ip4 = ip_address
        try:
            device.validated_save()
        except ValidationError as err:
            self.diffsync.job.logger.error(f"Device {device.name} failed to update, {err}")
        return super().update(attrs)


class OnboardingDeviceType(NautobotModel):
    """Diffsync model for device type data."""

    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model", "manufacturer__name")
    _attributes = ("part_number",)

    model: str
    manufacturer__name: str

    part_number: str


class OnboardingManufacturer(NautobotModel):
    """Diffsync model for manufacturer data."""

    _modelname = "manufacturer"
    _model = Manufacturer
    _identifiers = ("name",)

    name: str


class OnboardingPlatform(NautobotModel):
    """Diffsync model for platform data."""

    _modelname = "platform"
    _model = Platform
    _identifiers = ("name",)
    _attributes = ("network_driver", "manufacturer__name")

    name: str

    network_driver: Optional[str]
    manufacturer__name: Optional[str]
