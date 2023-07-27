"""NautobotORMAdapter class."""
import logging
from diffsync.enum import DiffSyncFlags, DiffSyncModelFlags


from django.conf import settings
from graphene_django.settings import graphene_settings
from graphql import get_default_backend
from nornir.core.plugins.inventory import InventoryPluginRegister


from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from nautobot.dcim.choices import InterfaceTypeChoices, InterfaceModeChoices

from nautobot_device_onboarding.network_importer.adapters.nautobot.models import (  # pylint: disable=import-error
    NautobotSite,
    NautobotDevice,
    NautobotInterface,
    NautobotIPAddress,
    NautobotCable,
    NautobotPrefix,
    NautobotVlan,
    NautobotStatus,
)

from nautobot_device_onboarding.network_importer.adapters.base import BaseAdapter  # pylint: disable=import-error


InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("nautobot_device_onboarding", {})
LOGGER = logging.getLogger("network-importer")

IMPORT_VLANS = PLUGIN_SETTINGS["import_vlans"]
if not isinstance(IMPORT_VLANS, bool):
    raise ValueError(
        f"The value of `import_vlans` must be a bool, received: {IMPORT_VLANS} of type {type(IMPORT_VLANS)}"
    )

backend = get_default_backend()
schema = graphene_settings.SCHEMA

SITE_QUERY = """query ($site_id: ID!) {
  site(id: $site_id) {
    name
    devices {
      name
      status {
        slug
        id
      }
    }
    tags {
      name
      id
    }
    vlans {
      id
      vid
      name
      status {
        slug
        id
      }
      tags {
        name
      }
    }
    prefixes {
      id
      network
      prefix
      status {
        slug
        id
      }
      tags {
        name
      }
    }
  }
}"""

DEVICE_QUERY = """query ($device_id: ID!) {
  device(id: $device_id) {
    name
    site {
      id
      name
    }
    interfaces {
      id
      name
      description
      mtu
      mode
      type
      tags {
        name
      }
      status {
        slug
        id
      }
      connected_endpoint {
        __typename
      }
      ip_addresses {
        id
        address
        tags {
          name
        }
        status {
          slug
          id
        }
      }
      cable {
        termination_a_type
        tags {
          name
        }
        status {
          name
        }
        color
      }
      lag {
        id
        enabled
        name
        status {
          slug
        }
        type
        member_interfaces {
          name
          enabled
        }
      }
      tagged_vlans {
        id
        vid
      }
      untagged_vlan {
        id
        vid
      }
    }
  }
}"""

CABLE_QUERY = """query ($site_id: String) {
  cables(site_id: [$site_id]) {
    id
    termination_a_id
    termination_b_id
    termination_a_type
    termination_b_type
  }
}"""

INTERFACE_ENUM_QUERY = """{
  __schema {
    types{
      name
      kind
      enumValues {
        name
        description
      }
    }
  }
}
"""


def get_schema_data(request):
    """Function run GraphQL Query to get schema mapping information."""
    document = backend.document_from_string(schema, INTERFACE_ENUM_QUERY)
    gql_result = document.execute(context_value=request)
    return gql_result.data


# TODO: See if there is a better way to get this data. GraphQl query is inefficient and relies
# on the first query to populate the data.
def populate_interface_types(data):
    """Function to convert what GraphQL shows vs what data is stored for interface types."""
    interface_types = list(filter(lambda x: x["name"] == "DcimInterfaceTypeChoices", data["__schema"]["types"]))[0][
        "enumValues"
    ]
    return {item["name"]: item["description"] for item in interface_types}


def get_interface_type_value(val, interface_types):
    """Function to create dictionary of Interface Types."""
    for _, value in InterfaceTypeChoices.CHOICES:
        for item in value:
            if interface_types[val] == item[1]:
                return item[0]
    raise ValueError(f"Value: {val} not found")


def populate_interface_modes(data):
    """Function to convert what GraphQL shows vs what data is stored for interface modes."""
    interface_types = list(filter(lambda x: x["name"] == "DcimInterfaceModeChoices", data["__schema"]["types"]))[0][
        "enumValues"
    ]
    return {item["name"]: item["description"] for item in interface_types}


def get_interface_mode_value(val, interface_modes):
    """Function to create dictionary of Interface Modes."""
    for item in InterfaceModeChoices.CHOICES:
        if interface_modes[val] == item[1]:
            return item[0]
    raise ValueError(f"Value: {val} not found")


class NautobotOrmAdapter(BaseAdapter):
    """Adapter to import Data from a Nautobot Server from the ORM."""

    site = NautobotSite
    device = NautobotDevice
    interface = NautobotInterface
    ip_address = NautobotIPAddress
    cable = NautobotCable
    vlan = NautobotVlan
    prefix = NautobotPrefix
    status = NautobotStatus

    schema_data = None
    interface_types = None
    interface_modes = None

    top_level = ["status", "site", "device", "cable"]

    global_flags = DiffSyncFlags.NONE

    diffsync_flags = PLUGIN_SETTINGS.get("diffsync_flags")
    diffsync_model_flags = PLUGIN_SETTINGS.get("model_flags")

    type = "Nautobot"

    def __init__(self, *args, request, job=None, **kwargs):
        """Initialize Infoblox.

        Args:
            request: The context of the request.
        """
        super().__init__(*args, **kwargs)
        self.job = job
        self.request = request
        # self.apply_diffsync_flags()

    # This should be handled generically in ssot, not here. This was a start but not finished.
    # def apply_model_flags(self, obj, tags): 
    #     """Helper function for DiffSync Flag assignment."""
    #     if not self.diffsync_model_flags:
    #         return
    #     for item in tags:
    #         if not hasattr(DiffSyncModelFlags, item):
    #             continue
    #         obj.model_flags |= getattr(DiffSyncModelFlags, item)
    #     if not self.diffsync_model_flags.get(obj._modelname):
    #         return
    #     for item in self.diffsync_model_flags[obj._modelname]:
    #         if not hasattr(DiffSyncModelFlags, item):
    #             raise ValueError(f"There was an attempt to add a non-existing flag of `{item}`")
    #         obj.model_flags |= getattr(DiffSyncModelFlags, item)
    #     print(obj.model_flags)

    # def apply_diffsync_flags(self):
    #     """Helper function for DiffSync Flag assignment."""
    #     if not self.diffsync_flags:
    #         return
    #     for item in self.diffsync_flags:
    #         if not hasattr(DiffSyncFlags, item):
    #             raise ValueError(f"There was an attempt to add a non-existing flag of `{item}`")
    #         self.global_flags |= getattr(DiffSyncFlags, item)


    def load(self):
        """Initialize and load all data from nautobot in the local cache."""
        self.load_inventory()
        if not self.schema_data:
            self.schema_data = get_schema_data(self.request)
            self.interface_types = populate_interface_types(self.schema_data)
            self.interface_modes = populate_interface_modes(self.schema_data)

        # Load Prefix and Vlan per site
        for site in self.get_all(self.site):
            site_variables = {"site_id": site.pk}
            document = backend.document_from_string(schema, SITE_QUERY)
            gql_result = document.execute(context_value=self.request, variable_values=site_variables)
            data = gql_result.data
            self.load_nautobot_prefix(site, data)
            self.load_nautobot_vlan(site, data)

        # Load interfaces and IP addresses for each devices
        for device in self.get_all(self.device):
            device_variables = {"device_id": device.pk}
            document = backend.document_from_string(schema, DEVICE_QUERY)
            gql_result = document.execute(context_value=self.request, variable_values=device_variables)
            data = gql_result.data
            site = self.get(self.site, device.site)
            self.load_nautobot_device(site, device, data)

        # Load Cabling
        if PLUGIN_SETTINGS.get("import_cabling") in ["lldp", "cdp"]:
            for site in self.get_all(self.site):
                site_variables = {"site_id": site.pk}
                document = backend.document_from_string(schema, CABLE_QUERY)
                gql_result = document.execute(context_value=self.request, variable_values=site_variables)
                data = gql_result.data
                self.load_nautobot_cable(site, data)

    def load_nautobot_device(self, site, device, data):
        """Import all interfaces and IP address from Nautobot for a given device.

        Args:
            site (NautobotSite): Site the device is part of
            device (DiffSyncModel): Device to import
            data (dict): Scoped GraphQL returned dictionary
        """
        intfs = data["device"]["interfaces"]
        for intf in intfs:
            self.convert_interface_from_nautobot(device, intf, site)

        LOGGER.debug("%s | Found %s interfaces for %s", self.name, len(intfs), device.slug)

    def load_nautobot_prefix(self, site, data):
        """Import all prefixes from Nautobot for a given site.

        Args:
            site (NautobotSite): Site to import prefix for
            data (dict): Scoped GraphQL returned dictionary
        """
        # Adapter Model methods not accounted for
        # vlan: Optional[str]

        if PLUGIN_SETTINGS.get("import_prefixes") is False:
            return

        prefixes = data["site"]["prefixes"]

        for nb_prefix in prefixes:

            prefix = self.prefix(
                prefix=nb_prefix["prefix"],
                site=data["site"]["name"],
                pk=nb_prefix["id"],
                status="active",
            )
            # if nb_prefix.vlan:
            #     prefix.vlan = self.vlan.create_unique_id(vid=nb_prefix.vlan.vid, site=site.slug)
            # self.apply_model_flags(prefix, [val["name"] for val in nb_prefix["tags"]])
            self.add(prefix)
            site.add_child(prefix)

    def load_nautobot_vlan(self, site, data):
        """Import all vlans from Nautobot for a given site.

        Args:
            site (NautobotSite): Site to import vlan for
            data (dict): Scoped GraphQL returned dictionary
        """
        if IMPORT_VLANS is not True:
            return

        vlans = data["site"]["vlans"]

        for nb_vlan in vlans:
            vlan = self.vlan(
                vid=nb_vlan["vid"],
                site=data["site"]["name"],
                name=nb_vlan["name"],
                pk=nb_vlan["id"],
                status="active",
            )
            # print(vlan)
            # self.apply_model_flags(vlan, [val["name"] for val in nb_vlan["tags"]])
            self.add(vlan)
            site.add_child(vlan)

    def convert_interface_from_nautobot(
        self, device, data, site=None
    ):  # pylint: disable=too-many-branches,too-many-statements
        """Convert PyNautobot interface object to NautobotInterface model.

        Args:
            site (NautobotSite): [description]
            device (NautobotDevice): [description]
            data (dict): Scoped GraphQL returned dictionary
            intf (pynautobot interface object): [description]
        """
        # Adapter Model methods not accounted for
        # speed: Optional[int]
        # lag_members: List[str] = list()
        # tagged_vlans: List[str] = list()
        # untagged_vlan: Optional[str]
        interface = self.interface(
            name=data["name"],
            device=device.slug,
            pk=data["id"],
            description=data["description"] or "",
            mtu=data["mtu"],
            tagged_vlans=[],
            status="active",
            type=get_interface_type_value(data["type"], self.interface_types),
        )
        if data["mode"]:
            interface.mode = get_interface_mode_value(data["mode"], self.interface_modes)

        if data["lag"]:
            # This presumes that the interface will be created (if not already), which seems like a reasonable assumption
            interface.lag = f"{device.slug}__{data['lag']['name']}"

        if data["tagged_vlans"] and IMPORT_VLANS:
            for vlan in data["tagged_vlans"]:
                interface.tagged_vlans.append(f"{site}__{vlan['vid']}")

        if data["untagged_vlan"] and data["untagged_vlan"].get("vid") and IMPORT_VLANS:
            # This presumes that the vlan will be created (if not already), which seems like a reasonable assumption
            interface.untagged_vlan = f"{site}__{data['untagged_vlan']['vid']}"

        if data["connected_endpoint"]:
            interface.connected_endpoint_type = data["connected_endpoint"]["__typename"]

        new_intf, created = self.get_or_add_model_instance(interface)
        # self.apply_model_flags(new_intf, [val["name"] for val in data["tags"]])
        if created:
            device.add_child(new_intf)

        # GraphQL returns [] when empty, so can just loop through nothing with no effect
        for ip_addr in data["ip_addresses"]:
            ip_address = self.ip_address(
                interface=data["name"],
                device=device.slug,
                pk=ip_addr["id"],
                address=ip_addr["address"],
                status="active",
            )

            # self.apply_model_flags(ip_address, [val["name"] for val in ip_addr["tags"]])
            self.add(ip_address)
            new_intf.add_child(ip_address)

        return new_intf

    def load_nautobot_cable(self, site, data):
        """Import all Cables from Nautobot for a given site.

        If both devices at each end of the cables are not in the list of device_id_map, the cable will be ignored.

        Args:
            site (Site): Site object to import cables for
            device_id_map (dict): Dict of device IDs and names that are part of the inventory
            data (dict): Scoped GraphQL returned dictionary
        """
        # Adapter Model methods not accounted for
        # source: Optional[str]
        # is_valid: bool = True
        # error: Optional[str]
        cables = data["cables"]
        devices = [device.slug for device in self.get_all(self.device)]

        nbr_cables = 0
        for nb_cable in cables:
            if nb_cable["termination_a_type"] != "dcim.interface" or nb_cable["termination_b_type"] != "dcim.interface":
                continue
            term_a_device = self._unique_data["interface"]["pk"][nb_cable["termination_a_id"]].device
            term_b_device = self._unique_data["interface"]["pk"][nb_cable["termination_b_id"]].device
            term_a_interface_name = self._unique_data["interface"]["pk"][nb_cable["termination_a_id"]].name
            term_b_interface_name = self._unique_data["interface"]["pk"][nb_cable["termination_b_id"]].name

            if (term_a_device not in devices) and (term_b_device not in devices):
                LOGGER.debug(
                    "%s | Skipping cable %s because neither devices (%s, %s) is in the list of devices",
                    self.name,
                    nb_cable.id,
                    term_a_device,
                    term_b_device,
                )
                continue

            # TODO: Legacy comment, Review the below
            # Disabling this check for now until we are able to allow user to control how cabling should be imported
            # if term_a_device not in devices:
            #     LOGGER.debug(
            #         "%s | Skipping cable %s because %s is not in the list of devices",
            #         self.name,
            #         nb_cable.id,
            #         term_a_device,
            #     )
            #     continue

            # if term_b_device not in devices:
            #     LOGGER.debug(
            #         "%s | Skipping cable %s because %s is not in the list of devices",
            #         self.name,
            #         nb_cable.id,
            #         term_b_device,
            #     )
            #     continue

            cable = self.cable(
                termination_a_device=term_a_device,
                termination_a=term_a_interface_name,
                termination_b_device=term_b_device,
                termination_b=term_b_interface_name,
                pk=nb_cable["id"],
                status="connected",
            )
            # TODO: confirm can remove
            # try:
            #     self.add(cable)
            # except ObjectAlreadyExists:
            #     pass
            obj, _ = self.get_or_add_model_instance(cable)
            # self.apply_model_flags(obj, [val["name"] for val in nb_cable["tags"]])
            nbr_cables += 1

        LOGGER.debug("%s | Found %s cables in nautobot for %s", self.name, nbr_cables, site.slug)
