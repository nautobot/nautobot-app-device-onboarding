"""Diffsync models."""

from dataclasses import dataclass
from typing import List, Optional

from diffsync import DiffSync, DiffSyncModel
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Prefix
from nautobot_ssot.contrib import NautobotModel
from nautobot.extras.models import Status
from nautobot.apps.choices import PrefixTypeChoices
from netaddr import EUI
import ipaddress


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

        Devices need to exist in Nautobot prior to syncing data.
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
        # "mac_address",
        "mtu",
        # "parent_interface__name",
        # "lag__name",
        "mode",
        "mgmt_only",
        # tagged vlan,
        # untagged vlans,
    )

    # _children = {"ip_address": "ip_addresses"}

    device__name: str
    name: str

    status__name: Optional[str]
    type: Optional[str]
    mac_address: Optional[EUI]
    mtu: Optional[str]
    parent_interface__name: Optional[str]
    # lag__name: Optional[str]
    mode: Optional[str]
    mgmt_only: Optional[bool]

    # ip_addresses: List["NetworkImporterIPAddress"] = []


class NetworkImporterPrefix(FilteredNautobotModel):
    """Shared data model representing a Prefix."""

    _model = Prefix
    _modelname = "prefix"
    _identifiers = ("network", "namespace__name")
    _attributes = (
        "prefix_length",
        "status__name",
    )

    network: str
    namespace__name: str

    prefix_length: int
    status__name: str

    @classmethod
    def _get_queryset(cls, diffsync: "DiffSync"):
        """Get the queryset used to load the models data from Nautobot."""
        prefixes = Prefix.objects.filter(namespace__name=diffsync.job.namespace.name)
        return prefixes


# class NetworkImporterIPAddress(FilteredNautobotModel):
#     """Shared data model representing an IPAddress."""

#     _modelname = "ip_address"
#     _model = IPAddress
#     _identifiers = ("host",)
#     _attributes = ("type", "ip_version", "mask_length", "status__name")

#     host: str

#     mask_length: int
#     type: str
#     ip_version: int
#     status__name: str

#     @classmethod
#     def _get_queryset(cls, diffsync: "DiffSync"):
#         """Get the queryset used to load the models data from Nautobot."""
#         ip_addresses = IPAddress.objects.filter(parent__namespace__name=diffsync.job.namespace.name)
#         return ip_addresses


class NetworkImporterIPAddressToInterface(DiffSyncModel):
    """Shared data model representing an IPAddressToInterface."""

    # _model = IPAddressToInterface
    _modelname = "ipaddress_to_interface"
    _identifiers = ("interface__device__name", "interface__name", "ip_address__host")
    _attributes = ("ip_address__mask_length",)

    interface__device__name: str
    interface__name: str
    ip_address__host: str
    ip_address__mask_length: str

    # @classmethod
    # def create(cls, diffsync, ids, attrs):
    #     """
    #     Do not attempt to assign interfaces that are not in the queryset of synced devices.
    #     """
    #     filter = {}
    #     if diffsync.job.devices:
    #         filter["id__in"] = [device.id for device in diffsync.job.devices]
    #     if diffsync.job.location:
    #         filter["location"] = diffsync.job.location
    #     if diffsync.job.device_role:
    #         filter["role"] = diffsync.job.device_role
    #     if diffsync.job.tag:
    #         filter["tags"] = diffsync.job.tag
    #     devices_in_sync = Device.objects.filter(**filter).values_list("name", flat=True)

    #     try:
    #         device = Device.objects.get(name=ids["interface__device__name"])
    #         if device.name in devices_in_sync:
    #             return super().create(diffsync, ids, attrs)
    #         else:
    #             return None
    #     except ObjectDoesNotExist:
    #         return None

    @classmethod
    def _get_or_create_ip_address(cls, ids, attrs, diffsync):
        """Attempt to get a Nautobot IP Address, create a new one if necessary."""
        ip_address = None
        default_status = Status.objects.get(name="Active")
        try:
            ip_address = IPAddress.objects.get(
                host=ids["ip_address__host"],
                mask_length=attrs["ip_address__mask_length"],
                parent__namespace=diffsync.job.namespace,
            )
        except ObjectDoesNotExist:
            try:
                ip_address = IPAddress.objects.create(
                    address=f"{ids['ip_address__host']}/{attrs['ip_address__mask_length']}",
                    namespace=diffsync.job.namespace,
                    status=default_status,
                )
            except ValidationError:
                diffsync.job.logger.warning(
                    f"No suitable parent Prefix exists for IP {ids['hostt']} in "
                    f"Namespace {diffsync.job.namespace.name}, a new Prefix will be created."
                )
                new_prefix = ipaddress.ip_interface(f"{attrs['ip_address__host']}/{attrs['ip_address__mask_length']}").network
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
                        status=default_status,
                    )
                ip_address = IPAddress.objects.create(
                    address=f"{ids['ip_address__host']}/{attrs['ip_address__mask_length']}",
                    status=default_status,
                    parent=prefix,
                )
        return ip_address

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new IPAddressToInterface object."""
        try:
            interface = Interface.objects.get(
                device__name=ids["interface__device__name"],
                name=ids["interface__name"],
                )
            ip_address_to_interface_obj = IPAddressToInterface(
                interface=interface,
                ip_address=cls._get_or_create_ip_address(ids, attrs, diffsync)
            )
            ip_address_to_interface_obj.validated_save()
        except ValidationError as err:
            diffsync.job.logger.error(f"{ids} failed to create, {err}")
        return super().create(diffsync, ids, attrs)

    def update(self, attrs):
        """Update an existing IPAddressToInterface object."""
        ip_address_to_interface = IPAddressToInterface.objects.get(**self.get_identifiers())

        if self.diffsync.job.debug:
            self.diffsync.job.logger.debug(f"Updating {ip_address_to_interface} with attrs: {attrs}")
        if attrs.get("ip_address__mask_length"):
            ip_address = ip_address_to_interface.ip_address
            ip_address.mask_length = attrs["ip_address__mask_length"]
            try:
                ip_address.validated_save()
            except ValidationError as err:
                self.job.logger.error(f"{ip_address} failed to create, {err}")

        return super().update(attrs)
    
    def delete(self):
        """Delete an IPAddressToInterface object."""
        obj = self._model.objects.get(**self.get_identifiers())
        obj.delete()
        return super().delete()
    
# TODO: Vlan Model

# TODO: Cable Model
