"""Extension of the base Models for the NautobotORMAdapter."""
import logging
from typing import Optional

from nautobot.dcim import models as dcim_models
from nautobot.ipam import models as ipam_models
from nautobot.extras import models as extras_models
from nautobot_ssot.mixins import DiffSyncModelMixIn

from nautobot_device_onboarding.network_importer.models import (  # pylint: disable=import-error
    Site,
    Device,
    Interface,
    IPAddress,
    Cable,
    Prefix,
    Vlan,
    Status,
)

LOGGER = logging.getLogger(__name__)


class NautobotSite(Site):
    """Extension of the Site model."""

    _attributes = ("pk",)
    _unique_fields = ("pk",)
    _orm_model = dcim_models.Site
    _generic_relation = {}


class NautobotDevice(Device):
    """Extension of the Device model."""

    _attributes = ("pk",)
    _unique_fields = ("pk",)
    _orm_model = dcim_models.Device
    _generic_relation = {}

    # device_tag_id: Optional[str]


class NautobotInterface(DiffSyncModelMixIn, Interface):
    """Extension of the Interface model."""

    _attributes = Interface._attributes + ("pk",)
    _unique_fields = ("pk",)
    _orm_model = dcim_models.Interface
    _foreign_key = {"device": "device", "status": "status", "lag": "interface", "untagged_vlan": "vlan"}
    _many_to_many = {"tagged_vlans": "vlan"}
    _generic_relation = {}

    pk: Optional[str]
    connected_endpoint_type: Optional[str]


class NautobotIPAddress(DiffSyncModelMixIn, IPAddress):
    """Extension of the IPAddress model."""

    _attributes = IPAddress._attributes + ("pk",)
    _unique_fields = ("pk",)
    _orm_model = ipam_models.IPAddress
    _foreign_key = {"status": "status"}
    _many_to_many = {}
    _generic_relation = {
        "interface": {"parent": "interface", "identifiers": ["device", "interface"], "attr": "assigned_object"}
    }

    pk: Optional[str]


class NautobotPrefix(DiffSyncModelMixIn, Prefix):
    """Extension of the Prefix model."""

    _attributes = Prefix._attributes + ("pk",)
    _unique_fields = ("pk",)
    _orm_model = ipam_models.Prefix
    _foreign_key = {"site": "site", "status": "status"}
    _many_to_many = {}
    _generic_relation = {}

    pk: Optional[str]


class NautobotVlan(DiffSyncModelMixIn, Vlan):
    """Extension of the Vlan model."""

    _attributes = Vlan._attributes + ("pk",)
    _unique_fields = ("pk",)
    _orm_model = ipam_models.VLAN
    _foreign_key = {"site": "site", "status": "status"}
    _many_to_many = {}
    _generic_relation = {}

    pk: Optional[str]
    tag_prefix: str = "device="


class NautobotCable(Cable):
    """Extension of the Cable model."""

    _attributes = ("pk",)
    _unique_fields = ("pk",)
    _model = dcim_models.Cable
    _generic_relation = {}

    pk: Optional[str]
    termination_a_id: Optional[str]
    termination_z_id: Optional[str]


class NautobotStatus(Status):
    """Extension of the Status model."""

    _unique_fields = ("pk",)
    _attributes = ("pk", "name")
    _orm_model = extras_models.Status
