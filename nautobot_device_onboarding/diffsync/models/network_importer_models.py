"""Diffsync models."""

from dataclasses import dataclass
from typing import List, Optional

from diffsync import DiffSync, DiffSyncModel
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddressToInterface, IPAddress
from nautobot_ssot.contrib import NautobotModel

from nautobot_device_onboarding.utils import diffsync_utils


class FilteredNautobotModel(NautobotModel):
    """
    Allow Nautobot data to be filtered by the Job form inputs.

    Must be used with FilteredNautobotAdapter.
    """

    @classmethod
    def _get_queryset(cls, diffsync: "DiffSync"):
        """Get the queryset used to load the models data from Nautobot."""
        parameter_names = list(cls._identifiers) + list(cls._attributes)
        # Here we identify any foreign keys (i.e. fields with '__' in them) so that we can load them directly in the
        # first query if this function hasn't been overridden.
        prefetch_related_parameters = [parameter.split("__")[0] for parameter in parameter_names if "__" in parameter]
        qs = cls.get_queryset(diffsync=diffsync)
        return qs.prefetch_related(*prefetch_related_parameters)

    @classmethod
    def get_queryset(cls, diffsync: "DiffSync"):
        """Get the queryset used to load the models data from Nautobot."""
        # Replace return with a filtered queryset.
        # Access the job form inputs with diffsync ex: diffsync.job.location.name
        return cls._model.objects.all()


class NetworkImporterDevice(FilteredNautobotModel):
    """Shared data model representing a Device."""

    _modelname = "device"
    _model = Device
    _identifiers = (
        "name",
        "serial",
    )
    _children = {"interface": "interfaces"}

    name: str
    serial: str

    interfaces: List["NetworkImporterInterface"] = []

    @classmethod
    def _get_queryset(cls, diffsync: "DiffSync"):
        """Get the queryset used to load the models data from Nautobot."""
        filter = {}

        if diffsync.job.devices:
            filter["id__in"] = [device.id for device in diffsync.job.devices]
        if diffsync.job.location:
            filter["location"] = diffsync.job.location
        if diffsync.job.device_role:
            filter["role"] = diffsync.job.device_role
        if diffsync.job.tag:
            filter["tags"] = diffsync.job.tag
        filtered_qs = cls._model.objects.filter(**filter)

        if filter:
            return filtered_qs
        else:
            diffsync.job.logger.error("No device filter options were provided, no devices will be synced.")
            return cls._model.objects.none()

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """
        Do not create new devices.

        Network devices need to exist in Nautobot prior to syncing data and
        need to be included in the queryset generated based on job form inputs.
        """
        diffsync.job.logger.error(
            f"{ids} is not included in the devices selected for syncing. "
            "This device either does not exist in Nautobot or was not "
            "included based on filter criteria provided on the job form."
        )
        return None

    def delete(self):
        """Delete the ORM object corresponding to this diffsync object."""
        self.job.logger.error(f"{self} will not be deleted.")
        return super().delete()


class NetworkImporterInterface(FilteredNautobotModel):
    """Shared data model representing an Interface."""

    _modelname = "interface"
    _model = Interface
    _identifiers = (
        "device__name",
        "name",
    )
    _attributes = (
        "status__name",
        "type",
        "mac_address",
        "mtu",
        # "parent_interface__name",
        # "lag__name",
        "mode",
        "mgmt_only",
        # tagged vlan,
        # untagged vlans,
    )

    device__name: str
    name: str

    status__name: Optional[str]
    type: Optional[str]
    mac_address: Optional[str]
    mtu: Optional[str]
    parent_interface__name: Optional[str]
    # lag__name: Optional[str]
    mode: Optional[str]
    mgmt_only: Optional[bool]


class NetworkImporterIPAddress(DiffSyncModel):
    """Shared data model representing an IPAddress."""

    _modelname = "ip_address"
    _identifiers = ("host",)
    _attributes = ("type", "ip_version", "mask_length", "status__name")

    host: str

    mask_length: int
    type: str
    ip_version: int
    status__name: str

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new IPAddressToInterface object."""
        diffsync_utils.get_or_create_ip_address(
            host=ids["host"],
            mask_length=attrs["mask_length"],
            namespace=diffsync.job.namespace,
            default_ip_status=diffsync.job.ip_address_status,
            default_prefix_status=diffsync.job.default_prefix_status,
            job=diffsync.job,
        )
        return super().create(diffsync, ids, attrs)

    def update(self, attrs):
        """Update an existing IPAddressToInterface object."""
        ip_address = IPAddress.objects.get(**self.get_identifiers())

        if self.diffsync.job.debug:
            self.diffsync.job.logger.debug(f"Updating {self} with attrs: {attrs}")
        if attrs.get("mask_length"):
            ip_address.mask_length = attrs["mask_length"]
        if attrs.get("status__name"):
            ip_address.status = Status.objects.get(name=attrs["status__name"])
            try:
                ip_address.validated_save()
            except ValidationError as err:
                self.job.logger.error(f"{self} failed to update, {err}")

        return super().update(attrs)


class NetworkImporterIPAddressToInterface(FilteredNautobotModel):
    """Shared data model representing an IPAddressToInterface."""

    _model = IPAddressToInterface
    _modelname = "ipaddress_to_interface"
    _identifiers = ("interface__device__name", "interface__name", "ip_address__host")
    _attributes = ("ip_address__mask_length",)

    interface__device__name: str
    interface__name: str
    ip_address__host: str
    ip_address__mask_length: str

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """
        Do not attempt to assign IP addresses to interfaces that are not in the queryset of synced devices.
        """
        filter = {}
        if diffsync.job.devices:
            filter["id__in"] = [device.id for device in diffsync.job.devices]
        if diffsync.job.location:
            filter["location"] = diffsync.job.location
        if diffsync.job.device_role:
            filter["role"] = diffsync.job.device_role
        if diffsync.job.tag:
            filter["tags"] = diffsync.job.tag
        devices_in_sync = Device.objects.filter(**filter).values_list("name", flat=True)

        try:
            device = Device.objects.get(name=ids["interface__device__name"])
            if device.name in devices_in_sync:
                return super().create(diffsync, ids, attrs)
            else:
                return None
        except ObjectDoesNotExist:
            return None


# TODO: Vlan Model

# TODO: Cable Model
