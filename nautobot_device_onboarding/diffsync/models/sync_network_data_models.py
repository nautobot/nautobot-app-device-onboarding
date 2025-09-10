"""Diffsync models."""

from typing import List, Optional
from uuid import UUID

try:
    from typing import Annotated  # Python>=3.9
except ImportError:
    from typing_extensions import Annotated  # Python<3.9

from diffsync import Adapter, DiffSyncModel
from diffsync import exceptions as diffsync_exceptions
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Cable, Device, Interface, Location, Platform, SoftwareVersion
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, VRF, IPAddress, IPAddressToInterface
from nautobot_ssot.contrib import CustomFieldAnnotation, NautobotModel

from nautobot_device_onboarding.utils import diffsync_utils


class FilteredNautobotModel(NautobotModel):
    """
    Allow Nautobot data to be filtered by the Job form inputs.

    Must be used with FilteredNautobotAdapter.
    """

    @classmethod
    def _get_queryset(cls, adapter: "Adapter"):
        """Get the queryset used to load the models data from Nautobot."""
        parameter_names = list(cls._identifiers) + list(cls._attributes)
        # Here we identify any foreign keys (i.e. fields with '__' in them) so that we can load them directly in the
        # first query if this function hasn't been overridden.
        prefetch_related_parameters = [parameter.split("__")[0] for parameter in parameter_names if "__" in parameter]
        qs = cls.get_queryset(adapter=adapter)
        return qs.prefetch_related(*prefetch_related_parameters)

    @classmethod
    def get_queryset(cls, adapter: "Adapter"):
        """Get the queryset used to load the models data from Nautobot."""
        # Replace return with a filtered queryset.
        # Access the job form inputs with adapter ex: adapter.job.location.name
        return cls._model.objects.all()


class SyncNetworkDataDevice(FilteredNautobotModel):
    """Shared data model representing a Device."""

    _modelname = "device"
    _model = Device
    _identifiers = (
        "name",
        "serial",
    )
    _attributes = ("last_network_data_sync",)
    _children = {"interface": "interfaces"}

    name: str
    serial: str

    last_network_data_sync: Annotated[
        Optional[str], CustomFieldAnnotation(key="last_network_data_sync", name="last_network_data_sync")
    ] = None

    interfaces: List["SyncNetworkDataInterface"] = []

    @classmethod
    def _get_queryset(cls, adapter: "Adapter"):
        """Get the queryset used to load the models data from Nautobot.

        job.command_getter_result contains the result from the CommandGetter job.
        Only devices that actually responded with data should be considered for the sync.
        """
        return adapter.job.devices_to_load

    @classmethod
    def create(cls, adapter, ids, attrs):
        """
        Do not create new devices.

        Network devices need to exist in Nautobot prior to syncing data and
        need to be included in the queryset generated based on job form inputs.
        """
        adapter.job.logger.error(
            f"Network device {ids} is not included in the Nautobot devices "
            "selected for syncing. This device either does not exist in Nautobot "
            "or was not included based on filter criteria provided on the job form."
        )
        return None

    def delete(self):
        """Prevent device deletion."""
        self.adapter.job.logger.error(f"{self} will not be deleted.")
        return None


class SyncNetworkDataInterface(FilteredNautobotModel):
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
        "enabled",
        "description",
    )

    device__name: str
    name: str

    status__name: Optional[str] = None
    type: Optional[str] = None
    mac_address: Optional[str] = None
    mtu: Optional[str] = None
    parent_interface__name: Optional[str] = None
    lag__name: Optional[str] = None
    mode: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class SyncNetworkDataIPAddress(DiffSyncModel):
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
    def create(cls, adapter, ids, attrs):
        """Create a new IPAddress object."""
        diffsync_utils.get_or_create_ip_address(
            host=ids["host"],
            mask_length=attrs["mask_length"],
            namespace=adapter.job.namespace,
            default_ip_status=adapter.job.ip_address_status,
            default_prefix_status=adapter.job.default_prefix_status,
            job=adapter.job,
        )
        return super().create(adapter, ids, attrs)

    def update(self, attrs):
        """Update an existing IPAddress object."""
        try:
            ip_address = IPAddress.objects.get(host=self.host, parent__namespace=self.adapter.job.namespace)
        except ObjectDoesNotExist as err:
            self.adapter.job.logger.error(f"{self} failed to update, {err}")
        if attrs.get("mask_length"):
            ip_address.mask_length = attrs["mask_length"]
        if attrs.get("status__name"):
            ip_address.status = Status.objects.get(name=attrs["status__name"])
        if attrs.get("ip_version"):
            ip_address.ip_version = attrs["ip_version"]
        try:
            ip_address.validated_save()
        except ValidationError as err:
            self.adapter.job.logger.error(f"{self} failed to update, {err}")

        return super().update(attrs)


class SyncNetworkDataIPAddressToInterface(FilteredNautobotModel):
    """Shared data model representing an IPAddressToInterface."""

    _modelname = "ipaddress_to_interface"
    _model = IPAddressToInterface
    _identifiers = ("interface__device__name", "interface__name", "ip_address__host")

    interface__device__name: str
    interface__name: str
    ip_address__host: str

    @classmethod
    def _get_queryset(cls, adapter: "Adapter"):
        """Get the queryset used to load the models data from Nautobot."""
        return IPAddressToInterface.objects.filter(interface__device__in=adapter.job.devices_to_load)


class SyncNetworkDataVLAN(DiffSyncModel):
    """Shared data model representing a VLAN."""

    _model = VLAN
    _modelname = "vlan"
    _identifiers = ("vid", "name", "location__name")

    vid: int
    name: str
    location__name: str

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Create a new VLAN."""
        location = None
        try:
            location = Location.objects.get(name=ids["location__name"])
        except ObjectDoesNotExist as err:
            adapter.job.logger.error(
                f"While creating VLAN {ids['vid']} - {ids['name']}, "
                f"unable to find a Location with name: {ids['location__name']}."
            )
            raise diffsync_exceptions.ObjectNotCreated(err)
        except MultipleObjectsReturned as err:
            adapter.job.logger.error(
                f"While creating VLAN {ids['vid']} - {ids['name']}, "
                f"Multiple Locations were found with name: {ids['location__name']}."
            )
            raise diffsync_exceptions.ObjectNotCreated(err)
        try:
            vlan = VLAN(
                name=ids["name"],
                vid=ids["vid"],
                location=location,
                status=Status.objects.get(name="Active"),  # TODO: this can't be hardcoded, add a form input
            )
            vlan.validated_save()
        except ValidationError as err:
            adapter.job.logger.error(f"VLAN {vlan} failed to create, {err}")
            raise diffsync_exceptions.ObjectNotCreated(err)

        return super().create(adapter, ids, attrs)


class SyncNetworkDataTaggedVlansToInterface(DiffSyncModel):
    """Shared data model representing a TaggedVlanToInterface."""

    _modelname = "tagged_vlans_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("tagged_vlans",)

    device__name: str
    name: str

    tagged_vlans: Optional[list] = None

    @classmethod
    def _get_and_assign_tagged_vlan(cls, adapter, network_vlan, interface, diff_method_type):
        """Assign a tagged vlan to an interface."""
        try:
            nautobot_vlan = VLAN.objects.get(
                name=network_vlan["name"], vid=network_vlan["id"], location=interface.device.location
            )
            interface.tagged_vlans.add(nautobot_vlan)
        except ObjectDoesNotExist as err:
            adapter.job.logger.error(
                f"Failed to assign tagged vlan to interface: [{interface}] on device: [{interface.device}]. "
                f"Unable to locate a vlan with attributes [{network_vlan}] at location: [{interface.device.location}]"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)
        except Exception as err:
            adapter.job.logger.error(
                f"Failed to assign tagged vlan: [{network_vlan}] "
                f"to interface: [{interface}]on device: [{interface.device}], {err}"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Assign tagged vlans to an interface."""
        if attrs.get("tagged_vlans"):
            try:
                interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])
            except ObjectDoesNotExist as err:
                adapter.job.logger.error(
                    f"Failed to assign tagged vlans {attrs['tagged_vlans']}. "
                    f"An interface with identifiers: [{ids}] was not found."
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
            for network_vlan in attrs["tagged_vlans"]:
                cls._get_and_assign_tagged_vlan(adapter, network_vlan, interface, diff_method_type="create")
            try:
                interface.validated_save()
            except ValidationError as err:
                adapter.job.logger.error(
                    f"Failed to assign tagged vlans {attrs['tagged_vlans']} to {interface} on {interface.device}, {err}"
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
        return super().create(adapter, ids, attrs)

    def update(self, attrs):
        """Update tagged vlans."""
        # An interface must exist before vlan assignments can be updated
        try:
            interface = Interface.objects.get(**self.get_identifiers())
        except ObjectDoesNotExist:
            self.adapter.job.logger.error(
                f"Failed to update tagged vlans, an interface with identifiers: [{self.get_identifiers()}] was not found."
            )
            raise diffsync_exceptions.ObjectNotUpdated
        # Clear all tagged vlans from an interface and assign them based on what was loaded into the diffsync store
        if attrs.get("tagged_vlans"):
            interface.tagged_vlans.clear()
            for network_vlan in attrs["tagged_vlans"]:
                self._get_and_assign_tagged_vlan(self.adapter, network_vlan, interface, diff_method_type="update")
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to assign tagged vlans {attrs['tagged_vlans']} "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated
        # Clear all tagged vlans from an interface
        if not attrs.get("tagged_vlans"):
            interface.tagged_vlans.clear()
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to remove tagged vlans from interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated(err)
        return super().update(attrs)


class SyncNetworkDataUnTaggedVlanToInterface(DiffSyncModel):
    """Shared data model representing a UnTaggedVlanToInterface."""

    _modelname = "untagged_vlan_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("untagged_vlan",)

    device__name: str
    name: str

    untagged_vlan: Optional[dict] = None

    @classmethod
    def _get_and_assign_untagged_vlan(cls, adapter, attrs, interface, diff_method_type):
        """Assign an untagged vlan to an interface."""
        try:
            vlan = VLAN.objects.get(
                name=attrs["untagged_vlan"]["name"],
                vid=attrs["untagged_vlan"]["id"],
                location=interface.device.location,
            )
            interface.untagged_vlan = vlan
        except ObjectDoesNotExist as err:
            adapter.job.logger.error(
                f"Failed to assign untagged vlan to interface: [{interface}] on device: [{interface.device}]. "
                f"Unable to locate a vlan with attributes: [{attrs['untagged_vlan']}] "
                f" at location: {interface.device.location}]"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)
        except Exception as err:
            adapter.job.logger.error(
                f"Failed to assign untagged vlan: [{attrs['untagged_vlan']}] "
                f"to interface: [{interface}] on device: [{interface.device}], {err}"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Assign an untagged vlan to an interface."""
        if attrs.get("untagged_vlan"):
            try:
                interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])
            except ObjectDoesNotExist:
                adapter.job.logger.error(
                    f"Failed to assign untagged vlan {attrs['untagged_vlan']}. "
                    f"An interface with identifiers: [{ids}] was not found."
                )
                raise diffsync_exceptions.ObjectNotCreated
            cls._get_and_assign_untagged_vlan(adapter, attrs, interface, diff_method_type="create")
            try:
                interface.validated_save()
            except ValidationError as err:
                adapter.job.logger.error(
                    f"Failed to assign untagged vlan {attrs['untagged_vlan']} "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
        return super().create(adapter, ids, attrs)

    def update(self, attrs):
        """Update the untagged vlan on an interface."""
        # An interface must exist before vlan assignments can be updated
        try:
            interface = Interface.objects.get(**self.get_identifiers())
        except ObjectDoesNotExist:
            self.adapter.job.logger.error(
                f"Failed to update untagged vlan, an interface with identifiers: [{self.get_identifiers()}] was not found."
            )
            raise diffsync_exceptions.ObjectNotUpdated
        # Assign an untagged vlan to an interface
        if attrs.get("untagged_vlan"):
            self._get_and_assign_untagged_vlan(self.adapter, attrs, interface, diff_method_type="update")
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to assign untagged vlan {attrs['untagged_vlan']} "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated
        # Removed an untagged vlan from an interface
        if not attrs.get("untagged_vlan"):
            interface.untagged_vlan = None
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to remove untagged vlan from {interface} on {interface.device}, {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated
        return super().update(attrs)


class SyncNetworkDataLagToInterface(DiffSyncModel):
    """Shared data model representing a LagToInterface."""

    _modelname = "lag_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("lag__interface__name",)

    device__name: str
    name: str

    lag__interface__name: Optional[str] = None

    @classmethod
    def _get_and_assign_lag(cls, adapter, attrs, interface, diff_method_type):
        """Assign a lag interface to an interface."""
        try:
            lag_interface = Interface.objects.get(
                name=attrs["lag__interface__name"], device=interface.device, type=InterfaceTypeChoices.TYPE_LAG
            )
            interface.lag = lag_interface
        except ObjectDoesNotExist as err:
            adapter.job.logger.error(
                f"Failed to assign lag to interface: [{interface}] on device: [{interface.device}]. "
                f"Unable to locate a lag interface with name: [{attrs['lag__interface__name']}] "
                f"on device: [{interface.device}]"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Assign a lag to an interface."""
        if attrs["lag__interface__name"]:
            try:
                interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])
            except ObjectDoesNotExist as err:
                adapter.job.logger.error(
                    f"Failed to assign lag: [{attrs['lag__interface__name']}]. "
                    f"An interface with identifiers: [{ids}] was not found."
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
            cls._get_and_assign_lag(adapter, attrs, interface, diff_method_type="create")
            try:
                interface.validated_save()
            except ValidationError as err:
                adapter.job.logger.error(
                    f"Failed to assign lag: [{attrs['lag__interface__name']}] "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
        return super().create(adapter, ids, attrs)

    def update(self, attrs):
        """Update and interface lag."""
        # An interface must exist before lag can be updated
        try:
            interface = Interface.objects.get(**self.get_identifiers())
        except ObjectDoesNotExist as err:
            self.adapter.job.logger.error(
                f"Failed to update lag, an interface with identifiers: [{self.get_identifiers()}] was not found."
            )
            raise diffsync_exceptions.ObjectNotUpdated(err)
        # Assign lag to an interface
        if attrs.get("lag__interface__name"):
            self._get_and_assign_lag(self.adapter, attrs, interface, diff_method_type="update")
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to assign lag: [{attrs['lag__interface__name']}] "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated(err)
        # Remove lag from an interface
        if not attrs.get("lag__interface__name"):
            interface.lag = None
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to remove lag from interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated(err)
        return super().update(attrs)


class SyncNetworkDataVRF(FilteredNautobotModel):
    """Shared data model representing a VRF."""

    _modelname = "vrf"
    _model = VRF
    _identifiers = ("name", "namespace__name")

    name: str
    namespace__name: str


class SyncNetworkDataVrfToInterface(DiffSyncModel):
    """Shared data model representing a VrfToInterface."""

    _modelname = "vrf_to_interface"
    _identifiers = ("device__name", "name")
    _attributes = ("vrf",)

    device__name: str
    name: str

    vrf: Optional[dict] = None

    @classmethod
    def _get_and_assign_vrf(cls, adapter, attrs, interface, diff_method_type):
        """Assign a vrf to an interface."""
        try:
            vrf = VRF.objects.get(
                name=attrs["vrf"]["name"],
                namespace=adapter.job.namespace,
            )
        except ObjectDoesNotExist as err:
            adapter.job.logger.error(
                f"Failed to assign vrf to interface: [{interface}] on device: [{interface.device}]. "
                f"Unable to locate a vrf with name: [{attrs['vrf']['name']}] in namespace: [{adapter.job.namespace}]"
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)
        except MultipleObjectsReturned as err:
            adapter.job.logger.error(
                f"Failed to assign vrf to interface: [{interface}] on device: [{interface.device}]. "
                f"There are multipple vrfs with name: [{attrs['vrf']['name']}] in namespace: [{adapter.job.namespace}]. "
                "Unsure which to assign."
            )
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)
        try:
            vrf.devices.add(interface.device)
            vrf.validated_save()
            interface.vrf = vrf
        except Exception as err:
            adapter.job.logger.error(f"Failed to assign device: [{interface.device}] to vrf: [{vrf}], {err}")
            if diff_method_type == "create":
                raise diffsync_exceptions.ObjectNotCreated(err)
            if diff_method_type == "update":
                raise diffsync_exceptions.ObjectNotUpdated(err)

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Assign a vrf to an interface."""
        if attrs.get("vrf"):
            try:
                interface = Interface.objects.get(device__name=ids["device__name"], name=ids["name"])
            except ObjectDoesNotExist as err:
                adapter.job.logger.error(
                    f"Failed to assign vrf: [{attrs['vrf']['name']}]. "
                    f"An interface with identifiers: [{ids}] was not found."
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
            cls._get_and_assign_vrf(adapter, attrs, interface, diff_method_type="create")
            try:
                interface.validated_save()
            except ValidationError as err:
                adapter.job.logger.error(
                    f"Failed to assign vrf: [{attrs['vrf']}] "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotCreated(err)
        return super().create(adapter, ids, attrs)

    def update(self, attrs):
        """Update the vrf on an interface."""
        # An interface must exist before vrf can be updated
        try:
            interface = Interface.objects.get(**self.get_identifiers())
        except ObjectDoesNotExist as err:
            self.adapter.job.logger.error(
                f"Failed to update vrf, an interface with identifiers: [{self.get_identifiers()}] was not found."
            )
            raise diffsync_exceptions.ObjectNotUpdated(err)
        if attrs.get("vrf"):
            # Assign a vrf to an interface
            self._get_and_assign_vrf(self.adapter, attrs, interface, diff_method_type="update")
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to assign vrf: [{attrs['vrf']}] "
                    f"to interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated(err)
        if not attrs.get("vrf"):
            interface.vrf = None
            try:
                interface.validated_save()
            except ValidationError as err:
                self.adapter.job.logger.error(
                    f"Failed to remove vrf from interface: [{interface}] on device: [{interface.device}], {err}"
                )
                raise diffsync_exceptions.ObjectNotUpdated(err)
        return super().update(attrs)


class SyncNetworkDataCable(FilteredNautobotModel):
    """Shared data model representing a cable between two interfaces."""

    _modelname = "cable"
    _model = Cable
    _identifiers = (
        "termination_a__app_label",
        "termination_a__model",
        "termination_a__device__name",
        "termination_a__name",
        "termination_b__app_label",
        "termination_b__model",
        "termination_b__device__name",
        "termination_b__name",
    )

    _attributes = ("status__name",)

    termination_a__app_label: str
    termination_a__model: str
    termination_a__device__name: str
    termination_a__name: str
    termination_b__app_label: str
    termination_b__model: str
    termination_b__device__name: str
    termination_b__name: str

    status__name: str


class SyncNetworkSoftwareVersion(DiffSyncModel):
    """Shared data model representing a software version."""

    _modelname = "software_version"
    _model = SoftwareVersion
    _identifiers = (
        "version",
        "platform__name",
    )
    _attributes = ()
    _children = {}

    version: str
    platform__name: str

    pk: Optional[UUID] = None

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Create a new software version."""
        try:
            platform = Platform.objects.get(name=ids["platform__name"])
        except ObjectDoesNotExist:
            adapter.job.logger.error(
                f"Failed to create software version {ids['version']}. An platform with name: "
                f"{ids['platform__name']} was not found."
            )
            raise diffsync_exceptions.ObjectNotCreated
        try:
            software_version = SoftwareVersion(
                version=ids["version"],
                platform=platform,
                status=Status.objects.get(name="Active"),
            )
            software_version.validated_save()
        except ValidationError as err:
            adapter.job.logger.error(f"Software version {software_version} failed to create, {err}")
            raise diffsync_exceptions.ObjectNotCreated

        return super().create(adapter, ids, attrs)

    def delete(self):
        """Prevent software version deletion."""
        self.adapter.job.logger.error(f"{self} will not be deleted.")
        return None


class SyncNetworkSoftwareVersionToDevice(DiffSyncModel):
    """Shared data model representing a software version to device."""

    _model = Device
    _modelname = "software_version_to_device"
    _identifiers = (
        "name",
        "serial",
    )
    _attributes = ("software_version__version",)

    name: str
    serial: str
    software_version__version: str

    def _get_and_assign_sofware_version(self, adapter, attrs):
        """Assign a software version to a device."""
        try:
            device = Device.objects.get(**self.get_identifiers())
        except ObjectDoesNotExist:
            adapter.job.logger.error(
                f"Failed to assign software version to {self.name}. An device with name: " f"{self.name} was not found."
            )
            raise diffsync_exceptions.ObjectNotCreated
        try:
            software_version = SoftwareVersion.objects.get(
                version=attrs["software_version__version"], platform=device.platform
            )
            device.software_version = software_version
        except ObjectDoesNotExist:
            adapter.job.logger.error(
                f"Failed to assign software version to {self.name}. An software version with name: "
                f"{self.name} was not found."
            )
            raise diffsync_exceptions.ObjectNotUpdated
        try:
            device.validated_save()
        except ValidationError as err:
            adapter.job.logger.error(f"Software version {software_version} failed to assign, {err}")
            raise diffsync_exceptions.ObjectNotUpdated

    def update(self, attrs):
        """Update an existing SoftwareVersionToDevice object."""
        if attrs.get("software_version__version"):
            try:
                self._get_and_assign_sofware_version(self.adapter, attrs)
            except ObjectDoesNotExist as err:
                self.adapter.job.logger.error(f"{self} failed to update, {err}")
                raise diffsync_exceptions.ObjectNotUpdated

        return super().update(attrs)

    @classmethod
    def create(cls, adapter, ids, attrs):
        """
        Do not create new devices.

        Network devices need to exist in Nautobot prior to syncing data and
        need to be included in the queryset generated based on job form inputs.
        """
        return None

    def delete(self):
        """Prevent device deletion."""
        return None
