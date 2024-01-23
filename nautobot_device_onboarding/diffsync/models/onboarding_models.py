"""Diffsync models."""

import ipaddress
from typing import List, Optional

import netaddr
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.apps.choices import InterfaceTypeChoices, PrefixTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Platform
from nautobot.extras.models import Role, SecretsGroup, Status
from nautobot.ipam.models import IPAddress, Prefix
from nautobot_ssot.contrib import  NautobotModel

from diffsync import DiffSyncModel


class OnboardingDevice(DiffSyncModel):
    _modelname = "device"
    # _model = Device
    _identifiers = ("location__name", "name")
    _attributes = (
        "device_type__model",
        "primary_ip4__host",
        "primary_ip4__status__name",
        "prefix_length",
        "mask_length",
        "platform__name",
        "role__name",
        "secrets_group__name",
        "status__name",
        "interfaces",
    )

    name: str
    location__name: str

    primary_ip4__host: Optional[str]
    primary_ip4__status__name: Optional[str]
    prefix_length: Optional[int]
    mask_length: Optional[int]
    device_type__model: Optional[str]
    platform__name: Optional[str]
    role__name: Optional[str]
    secrets_group__name: Optional[str]
    status__name: Optional[str]

    interfaces: Optional[list]
    device_type: List["OnboardingDeviceType"] = []

    @classmethod
    def _get_or_create_ip_address(cls, diffsync, attrs):
        """Attempt to get a Nautobot IP Address, create a new one if necessary."""
        ip_address = None
        try:
            ip_address = IPAddress.objects.get(
                address=f"{attrs['primary_ip4__host']}/{attrs['mask_length']}",
                parent__namespace=diffsync.job.namespace,
            )
        except ObjectDoesNotExist:
            try:
                ip_address = IPAddress.objects.create(
                    address=f"{attrs['primary_ip4__host']}/{attrs['mask_length']}",
                    namespace=diffsync.job.namespace,
                    status=diffsync.job.ip_address_status,
                )
            except ValidationError as err:
                diffsync.job.logger.warning(
                    f"No suitable parent Prefix exists for IP {attrs['primary_ip4__host']} in "
                    f"Namespace {diffsync.job.namespace.name}, a new Prefix will be created."
                )
                new_prefix = ipaddress.ip_interface(f"{attrs['primary_ip4__host']}/{attrs['mask_length']}")
                try:
                    prefix = Prefix.objects.get(
                        prefix=f"{new_prefix.network}",
                        namespace=diffsync.job.namespace,
                    )
                except ObjectDoesNotExist:
                    prefix = Prefix.objects.create(
                        prefix=f"{new_prefix.network}",
                        namespace=diffsync.job.namespace,
                        type=PrefixTypeChoices.TYPE_NETWORK,
                        status=diffsync.job.ip_address_status,
                    )
                ip_address, _ = IPAddress.objects.get_or_create(
                    address=f"{attrs['primary_ip4__host']}/{attrs['mask_length']}",
                    status=diffsync.job.ip_address_status,
                    parent=prefix,
                )
        return ip_address

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
    def create(cls, diffsync, ids, attrs):
        """Create a new nautobot device using data scraped from a device."""
        # Determine device platform
        platform = None
        if diffsync.job.platform:
            platform = diffsync.job.platform
        else:
            platform = Platform.objects.get(name=attrs["platform__name"])

        try:
            device = Device.objects.get(**ids)

        except ObjectDoesNotExist:
            # Create Device
            device = Device.objects.create(
                location=diffsync.job.location,
                status=diffsync.job.device_status,
                role=diffsync.job.device_role,
                device_type=DeviceType.objects.get(model=attrs["device_type__model"]),
                name=ids["name"],
                platform=platform,
                secrets_group=diffsync.job.secrets_group,
            )

        ip_address = cls._get_or_create_ip_address(diffsync=diffsync, attrs=attrs)
        interface = cls._get_or_create_interface(diffsync=diffsync, device=device, attrs=attrs)
        interface.ip_addresses.add(ip_address)
        interface.validated_save()

        # Assign primary IP Address to device
        try:
            device.primary_ip4 = ip_address
            device.validated_save()
        except ValidationError as err:
            diffsync.job.logger.error(
                f"Failed to save changes to {attrs['primary_ip4__host']} Device: {ids['name']}, {err}"
            )

        return DiffSyncModel.create(diffsync=diffsync, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update an existing nautobot device using data scraped from a device."""

        device = Device.objects.get(name=self.name, location__name=self.location__name)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.debug(f"Updating device with attrs: {attrs}")
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
        if attrs.get("primary_ip4__status__name"):
            device.primary_ip.status.name = Status.objects.get(name=attrs.get("primary_ip4__status__name"))

        if attrs.get("interfaces"):
            interface = self._get_or_create_interface(diffsync=self.diffsync, device=device, attrs=attrs)
            # If the primary ip address is being updated, the mask length must be included
            if attrs.get("primary_ip4__host"):
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length
                ip_address = self._get_or_create_ip_address(diffsync=self.diffsync, attrs=attrs)
                interface.ip_addresses.add(ip_address)
                interface.validated_save()
                # set the new ip address as the device primary ip address
                device.primary_ip4 = ip_address
                interface.validated_save()
            else:
                # Check for a device with a matching IP Address and remove it before assigning 
                # the IP Address to the new interface
                try:
                    old_interface = Interface.objects.get(
                        device=device,
                        ip_addresses__in=[device.primary_ip4]
                    )
                    old_interface.ip_addresses.remove(device.primary_ip4)
                    old_interface.validated_save()
                    interface.ip_addresses.add(device.primary_ip4)
                    interface.validated_save()
                except ObjectDoesNotExist:
                    interface.ip_addresses.add(device.primary_ip4)
                    interface.validated_save()
        else:
            # update the primary ip address when the interface has not changed
            if attrs.get("primary_ip4__host"):
                if not attrs.get("mask_length"):
                    attrs["mask_length"] = device.primary_ip4.mask_length
                ip_address = self._get_or_create_ip_address(diffsync=self.diffsync, attrs=attrs)
                interface = Interface.objects.get(
                        device=device,
                        ip_addresses__in=[device.primary_ip4]
                    )
                interface.ip_addresses.remove(device.primary_ip4) #TODO: This is not removing the IP from the interface as expected
                interface.ip_addresses.add(ip_address)
                interface.validated_save()
                device.primary_ip4 = ip_address
        try:
            device.validated_save()
        except ValidationError as err:
            self.diffsync.job.logger.error(f"Device {self.name} failed to update, {err}")
        return super().update(attrs)


class OnboardingDeviceType(NautobotModel):
    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model", "manufacturer__name")

    model: str
    manufacturer__name: str


class OnboardingManufacturer(NautobotModel):
    _modelname = "manufacturer"
    _model = Manufacturer
    _identifiers = ("name",)

    name: str


class OnboardingPlatform(NautobotModel):
    _modelname = "platform"
    _model = Platform
    _identifiers = ("name",)
    _attributes = ("network_driver", "manufacturer__name")

    name: str

    network_driver: Optional[str]
    manufacturer__name: Optional[str]
