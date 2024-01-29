"""Diffsync models."""

from nautobot_ssot.contrib import NautobotModel
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from typing import List, Optional
from diffsync import DiffSync


class FilteredNautobotModel(NautobotModel):
    """
    Allow for filtering of data loaded from Nautobot into DiffSync models.

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
    _modelname = "device"
    _model = Device
    _identifiers = (
    "location__name",
    "name",
    "serial",
    )
    _children = {"interface": "interfaces"}

    name: str
    location__name: str
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


class NetworkImporterInterface(FilteredNautobotModel):
    _modelname = "interface"
    _model = Interface
    _identifiers = (
    "device__name",
    "name",
    )
    _children = {"ip_address": "ip_addresses"}
    device__name: str
    name: str

    ip_addresses: List["NetworkImporterIPAddress"] = []


class NetworkImporterIPAddress(FilteredNautobotModel):
    _modelname = "ip_address"
    _model = IPAddress
    _identifiers = (
        "parent__namespace__name",
        "host",
    )

    parent__namespace__name: str
    host: str
