"""Diffsync models."""

from typing import List, Optional

import netaddr
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Platform
from nautobot.ipam.models import IPAddress, Prefix
from nautobot_ssot.contrib import NautobotModel


class OnboardingDevice(NautobotModel):
    _modelname = "device"
    _model = Device
    _identifiers = ("primary_ip4__host",)
    _attributes = (
        "device_type__model",
        "location__name",
        "name",
        "platform__name",
        "role__name",
        "secrets_group__name",
        "status__name",
    )
    _children = {
        "interface": "interfaces",
    }

    primary_ip4__host: str

    device_type__model: Optional[str]
    location__name: Optional[str]
    name: Optional[str]
    platform__name: Optional[str]
    role__name: Optional[str]
    secrets_group__name: Optional[str]
    status__name: Optional[str]

    interfaces: List["OnboardingInterface"] = []
    device_type: List["OnboardingDeviceType"] = []

    @classmethod
    def _get_queryset(cls, filter: list = None):
        """Get the queryset used to load the models data from Nautobot."""
        parameter_names = list(cls._identifiers) + list(cls._attributes)
        # Here we identify any foreign keys (i.e. fields with '__' in them) so that we can load them directly in the
        # first query if this function hasn't been overridden.
        prefetch_related_parameters = [parameter.split("__")[0] for parameter in parameter_names if "__" in parameter]
        qs = cls.get_queryset(filter=filter)
        return qs.prefetch_related(*prefetch_related_parameters)

    @classmethod
    def get_queryset(cls, filter: list = None):
        """Get the queryset used to load the models data from Nautobot."""
        if filter:
            # Only devices with a primary_ip that is being onboarded should be considered for the sync
            return cls._model.objects.filter(primary_ip4__host__in=filter)
        else:
            return cls._model.objects.all()


class OnboardingDeviceType(NautobotModel):
    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model", "manufacturer__name")

    model: str
    manufacturer__name: str


class OnboardingInterface(NautobotModel):
    _modelname = "interface"
    _model = Interface
    _identifiers = ("name", "device__name")
    _attributes = (
        "mgmt_only",
        "status__name",
        "type",
    )
    _children = {"ip_address": "ip_addresses"}

    name: str
    device__name: str

    mgmt_only: Optional[bool]
    status__name: Optional[str]
    type: Optional[str]

    ip_addresses: List["OnboardingIPAddress"] = []


class OnboardingIPAddress(NautobotModel):
    _modelname = "ip_address"
    _model = IPAddress
    _identifiers = (
        "parent__namespace__name",
        "parent__network",
        "parent__prefix_length",
        "host",
        "mask_length",
    )

    parent__namespace__name: str
    parent__network: str
    parent__prefix_length: int
    host: str
    mask_length: int


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
