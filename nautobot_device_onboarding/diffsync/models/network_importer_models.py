"""Diffsync models."""

from typing import List, Optional

from diffsync import DiffSync, DiffSyncModel
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, Interface, Location
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, IPAddress, IPAddressToInterface
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
        """Get the queryset used to load the models data from Nautobot.

        job.command_getter_result contains the result from the CommandGetter job.
        Only devices that actually responded with data should be considered for the sync.
        """
        return diffsync.job.devices_to_load

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """
        Do not create new devices.

        Network devices need to exist in Nautobot prior to syncing data and
        need to be included in the queryset generated based on job form inputs.
        """
        diffsync.job.logger.error(
            f"Network device {ids} is not included in the Nautobot devices "
            "selected for syncing. This device either does not exist in Nautobot "
            "or was not included based on filter criteria provided on the job form."
        )
        return None

    def delete(self):
        """Prevent device deletion."""
        self.diffsync.job.logger.error(f"{self} will not be deleted.")
        return None


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
        "mode",
        "untagged_vlan__name",
    )

    device__name: str
    name: str

    status__name: Optional[str]
    type: Optional[str]
    mac_address: Optional[str]
    mtu: Optional[str]
    parent_interface__name: Optional[str]
    lag__name: Optional[str]
    mode: Optional[str]
    untagged_vlan__name: Optional[str]


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
        try:
            ip_address = IPAddress.objects.get(host=self.host, parent__namespace=self.diffsync.job.namespace)
        except ObjectDoesNotExist as err:
            self.job.logger.error(f"{self} failed to update, {err}")
        if self.diffsync.job.debug:
            self.diffsync.job.logger.debug(f"Updating {self} with attrs: {attrs}")
        if attrs.get("mask_length"):
            ip_address.mask_length = attrs["mask_length"]
        if attrs.get("status__name"):
            ip_address.status = Status.objects.get(name=attrs["status__name"])
        if attrs.get("ip_version"):
            ip_address.status = attrs["ip_version"]
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

    interface__device__name: str
    interface__name: str
    ip_address__host: str

    @classmethod
    def _get_queryset(cls, diffsync: "DiffSync"):
        """Get the queryset used to load the models data from Nautobot."""
        return IPAddressToInterface.objects.filter(interface__device__in=diffsync.job.devices_to_load)


class NetworkImporterVLAN(DiffSyncModel):
    """Shared data model representing a VLAN."""

    _model = VLAN
    _modelname = "vlan"
    _identifiers = ("vid", "name", "location__name")

    vid: int
    name: str
    location__name: str

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create a new VLAN."""
        location = None
        try:
            location = Location.objects.get(name=ids["location__name"])
        except ObjectDoesNotExist:
            diffsync.job.logger.warning(
                f"While creating VLAN {ids['vid']} - {ids['name']}, "
                f"unable to find a Location with name: {ids['location__name']}. "
                "This VLAN will be created without a Location"
            )
        except MultipleObjectsReturned:
            diffsync.job.logger.warning(
                f"While creating VLAN {ids['vid']} - {ids['name']}, "
                f"Multiple Locations were found with name: {ids['location__name']}. "
                "This VLAN will be created without a Location"
            )
        try:
            vlan = VLAN(
                name=ids["name"],
                vid=ids["vid"],
                location=location,
                status=Status.objects.get(name="Active"),  # TODO: this can't be hardcoded, add a form input
            )
            vlan.validated_save()
        except ValidationError as err:
            diffsync.job.logger.error(f"VLAN {vlan} failed to create, {err}")

        return super().create(diffsync, ids, attrs)


class NetworkImporterTaggedVlansToInterface(DiffSyncModel):
    """Shared data model representing a TaggedVlanToInterface."""

    _modelname = "tagged_vlans_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("tagged_vlans",)

    device__name: str
    name: str

    tagged_vlans: Optional[list]

    # TODO: move the create and update method logic to a single utility function
    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Assign tagged vlans to an interface."""
        interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])

        for network_vlan in attrs["tagged_vlans"]:
            try:
                nautobot_vlan = VLAN.objects.get(
                    name=network_vlan["name"], vid=network_vlan["id"], location=interface.device.location
                )
                interface.tagged_vlans.add(nautobot_vlan)
            except ObjectDoesNotExist:
                diffsync.job.logger.error(
                    f"Failed to assign tagged vlan to {interface}, unable to locate a vlan "
                    f"with attributes [name: {network_vlan['name']}, vid: {network_vlan['id']} "
                    f"location: {interface.device.location}]"
                )
        try:
            interface.validated_save()
        except ValidationError as err:
            diffsync.job.logger.error(
                f"Failed to assign tagged vlans {attrs['tagged_vlans']} to {interface} on {interface.device}, {err}"
            )
        return super().create(diffsync, ids, attrs)

    def update(self, attrs):
        """Update tagged vlans."""
        interface = Interface.objects.get(**self.get_identifiers())
        interface.tagged_vlans.clear()

        for network_vlan in attrs["tagged_vlans"]:
            try:
                nautobot_vlan = VLAN.objects.get(
                    name=network_vlan["name"], vid=network_vlan["id"], location=interface.device.location
                )
                interface.tagged_vlans.add(nautobot_vlan)
            except ObjectDoesNotExist:
                self.diffsync.job.logger.error(
                    f"Failed to assign tagged vlan to {interface}, unable to locate a vlan "
                    f"with attributes [name: {network_vlan['name']}, vid: {network_vlan['id']} "
                    f"location: {interface.device.location}]"
                )
        try:
            interface.validated_save()
        except ValidationError as err:
            self.diffsync.job.logger.error(
                f"Failed to assign tagged vlans {attrs['tagged_vlans']} to {interface} on {interface.device}, {err}"
            )

        return super().update(attrs)


class NetworkImporterLagToInterface(DiffSyncModel):
    """Shared data model representing a LagToInterface."""

    _modelname = "lag_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("lag__interface__name",)

    device__name: str
    name: str

    lag__interface__name: Optional[str]

    # TODO: move the create and update method locgic to a single utility function
    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Assign a lag to an interface."""
        if attrs["lag__interface__name"]:  # Prevent the sync from attempting to assign lag interface names of 'None'
            interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])
            try:
                lag_interface = Interface.objects.get(
                    name=attrs["lag__interface__name"], device=interface.device, type=InterfaceTypeChoices.TYPE_LAG
                )
                interface.lag = lag_interface
                interface.validated_save()
            except ObjectDoesNotExist:
                diffsync.job.logger.error(
                    f"Failed to assign lag to {interface}, unable to locate a lag interface "
                    f"with attributes [name: {attrs['lag__interface__name']}, device: {interface.device.name} "
                    f"type: {InterfaceTypeChoices.TYPE_LAG}]"
                )
            except ValidationError as err:
                diffsync.job.logger.error(
                    f"Failed to assign lag {lag_interface} to {interface} on {interface.device}, {err}"
                )
        return super().create(diffsync, ids, attrs)

    def update(self, attrs):
        """Update and interface lag."""
        interface = Interface.objects.get(**self.get_identifiers())
        try:
            lag_interface = Interface.objects.get(
                name=attrs["lag__interface__name"], device=interface.device, type=InterfaceTypeChoices.TYPE_LAG
            )
            interface.lag = lag_interface
            interface.validated_save()
        except ObjectDoesNotExist:
            self.diffsync.job.logger.error(
                f"Failed to assign lag to {interface}, unable to locate a lag interface "
                f"with attributes [name: {attrs['lag__interface__name']}, device: {interface.device.name} "
                f"type: {InterfaceTypeChoices.TYPE_LAG}]"
            )
        except ValidationError as err:
            self.diffsync.job.logger.error(
                f"Failed to assign lag {lag_interface} to {interface} on {interface.device}, {err}"
            )

        return super().update(attrs)


# TODO: Cable Model
