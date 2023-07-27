"""Custom Exceptions for the NetworkImporterAdapter."""
import ipaddress
import logging
from ipaddress import ip_interface
from dataclasses import dataclass

from django.conf import settings


from diffsync.exceptions import ObjectNotFound

# pylint: disable=import-error

from nautobot_device_onboarding.network_importer.adapters.base import BaseAdapter

from nautobot_device_onboarding.network_importer.inventory import reachable_devs, valid_and_reachable_devs
from nautobot_device_onboarding.network_importer.tasks import check_if_reachable, warning_not_reachable
from nautobot_device_onboarding.network_importer.drivers import dispatcher
from nautobot_device_onboarding.network_importer.processors.get_neighbors import GetNeighbors, hosts_for_cabling
from nautobot_device_onboarding.network_importer.processors.get_vlans import GetVlans
from nautobot_device_onboarding.network_importer.processors.get_ips import GetIPs

# from nautobot_device_onboarding.network_importer.utils import (
#     is_interface_lag,
#     is_interface_physical,
#     expand_vlans_list,
# )

LOGGER = logging.getLogger("network-importer")
PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("nautobot_device_onboarding", {})


@dataclass
class IPData:
    """Data class to hold IPData about the IP addresses on a device."""

    host: ip_interface
    prefix: str
    prefix_length: int
    interface: str
    address_family: str


class NetworkImporterAdapter(BaseAdapter):
    """Adapter to import data from a network based on Batfish."""

    top_level = ["status", "site", "device"]  # , "cable"]

    type = "Network"

    def load(self):
        """Load all data from the network in the local cache."""
        # Josh, I changed this, the way I understand the flow, the site and devices will
        # always come from Nautobot. We should use exactly the same code then. I changed the logic to
        # accomodate.
        # sites = {}

        # # Create all devices and site object from Nornir Inventory
        # for hostname, host in self.nornir.inventory.hosts.items():

        #     self.nornir.inventory.hosts[hostname].has_config = True

        #     # Check that the host site is in the sites dictionary.
        #     if host.site not in sites:
        #         site = self.site(name=host.site)
        #         sites[host.site] = site
        #         self.add(site)
        #     else:
        #         site = sites[host.site]

        #     device = self.device(name=hostname, site=host.site)
        #     self.add(device)
        self.load_inventory()

        if PLUGIN_SETTINGS.get("import_cabling") in ["lldp", "cdp"] or PLUGIN_SETTINGS.get("import_vlans") in [
            True,
            "cli",
        ]:
            self.nornir.filter(filter_func=reachable_devs).run(task=check_if_reachable, on_failed=True)
            self.nornir.filter(filter_func=reachable_devs).run(task=warning_not_reachable, on_failed=True)

        self.load_vlans()
        self.load_cabling()
        # TODO: Not actually used, remove the F841 when updated
        ip_addresses = self.get_ipaddresses_from_napalm()  # noqa: F841
        # Loop over each of the ip addresses (which should be in a dictionary)
        # TODO: Build out interfaces that need to be made
        # TODO: Build out Prefixes
        # TODO: Build out IP addresses

        self.check_data_consistency()

    def get_ipaddesses_from_napalm(self):
        """Gets IP addresses via NAPALM from the device and returns them in a list of IPData."""

        def parse_nornir_get_ip_data(ip_data):
            return_list = []

            # Parse through the IPv4 Addresses found
            for interface, interface_data in ip_data.items():
                for address_family, address_data in interface_data.items():
                    for ip_address, prefix_data in address_data.items():
                        interface_data = ip_interface(f"{ip_address}/{prefix_data['prefix_length']}")
                        return_list.append(
                            IPData(
                                host=interface_data,
                                prefix=interface_data.network,
                                prefix_length=prefix_data["prefix_length"],
                                interface=interface,
                                address_family=address_family,
                            )
                        )

            return return_list

        LOGGER.debug("Getting IP Addresses from devices.")
        results = (
            self.nornir.filter(filter_func=valid_and_reachable_devs)
            .with_processors([GetIPs()])
            .run(task=dispatcher, method="get_ips")
        )

        # Anticipating that self.device.slug is the hostname that corresponds to the Nornir inventory
        return parse_nornir_get_ip_data(results[self.device.slug].result[0].result["get_interfaces_ip"])

    def add_prefix_from_ip(self, ip_address, site, vlan=None):
        """Try to extract a prefix from an IP address and save it locally.

        Args:
            ip_address (IPAddress): DiffSync IPAddress object
            site (Site): Site object the prefix is part of.
            vlan (str): Identifier of the vlan

        Returns:
            Prefix, bool: False if a prefix can't be extracted from this IP address
        """
        prefix = ipaddress.ip_network(ip_address.address, strict=False)

        if prefix.num_addresses == 1:
            return False

        try:
            prefix_obj = self.get(self.prefix, identifier=dict(site=site.slug, prefix=prefix))
        except ObjectNotFound:
            prefix_obj = None

        if not prefix_obj:
            prefix_obj = self.prefix(prefix=str(prefix), site=site.slug, vlan=vlan)
            self.add(prefix_obj)
            site.add_child(prefix_obj)
            LOGGER.debug("Added Prefix %s", prefix)

        if prefix_obj and vlan and not prefix_obj.vlan:
            prefix_obj.vlan = vlan
            LOGGER.debug("Updated Prefix %s with vlan %s", prefix, vlan)

        return prefix_obj

    def load_cabling(self):
        """Load cabling from either batfish, cdl or lldp based on the configuration."""
        if PLUGIN_SETTINGS.get("import_cabling") in ["no", False]:
            return False

        if PLUGIN_SETTINGS.get("import_cabling") in ["lldp", "cdp", True]:
            self.load_cabling_from_cmds()

        self.validate_cabling()

        return True

    def load_vlans(self):
        """Load vlans information from the devices using CLI."""
        if PLUGIN_SETTINGS.get("import_cabling") not in ["cli", True]:
            return

        LOGGER.info("Collecting vlans information from devices .. ")

        results = (
            self.nornir.filter(filter_func=valid_and_reachable_devs)
            .with_processors([GetVlans()])
            .run(task=dispatcher, method="get_vlans")
        )

        for dev_name, items in results.items():
            if items[0].failed:
                continue

            if not isinstance(items[1].result, dict) or "vlans" not in items[1].result:
                LOGGER.debug("%s | No vlan information returned SKIPPING", dev_name)
                continue

            device = self.get(self.device, identifier=dev_name)
            site = self.get(self.site, identifier=device.site)

            for vlan in items[1].result["vlans"]:
                new_vlan, created = self.get_or_add_model_instance(
                    self.vlan(vid=vlan["vid"], name=vlan["name"], site=site.slug)
                )

                if created:
                    site.add_child(new_vlan)

                new_vlan.add_device(device.get_unique_id())

    def load_cabling_from_cmds(self):
        """Import cabling information from the CLI, either using LLDP or CDP based on the configuration.

        If the FQDN is defined, and the hostname of a neighbor include the FQDN, remove it.
        """
        LOGGER.info("Collecting cabling information from devices .. ")

        results = (
            self.nornir.filter(filter_func=valid_and_reachable_devs)
            .filter(filter_func=hosts_for_cabling)
            .with_processors([GetNeighbors()])
            .run(
                task=dispatcher,
                method="get_neighbors",
                on_failed=True,
            )
        )

        nbr_cables = 0
        for dev_name, items in results.items():
            if items[0].failed:
                continue

            if not isinstance(items[1][0].result, dict) or "neighbors" not in items[1][0].result:
                LOGGER.debug("%s | No neighbors information returned SKIPPING", dev_name)
                continue

            for interface, neighbors in items[1][0].result["neighbors"].items():
                cable = self.cable(
                    termination_a_device=dev_name,
                    termination_a=interface,
                    termination_b_device=neighbors[0]["hostname"],
                    termination_b=neighbors[0]["port"],
                    source="cli",
                )
                nbr_cables += 1
                LOGGER.debug("%s | Added cable %s", dev_name, cable.get_unique_id())
                self.get_or_add_model_instance(cable)

        LOGGER.debug("Found %s cables from Cli", nbr_cables)

    def check_data_consistency(self):
        """Check the validaty and consistency of the data in the local store.

        Ensure the vlans configured for each interface exist in the system.
        On some vendors, it's possible to have a list larger than what is really available

        In the process, ensure that all devices are associated with the right vlans
        """
        # Get a dictionnary with all vlans organized by uid
        vlans = {vlan.get_unique_id(): vlan for vlan in self.get_all(self.vlan)}
        interfaces = self.get_all(self.interface)

        for intf in interfaces:
            if intf.tagged_vlans:
                clean_tagged_vlans = []
                for vlan in intf.tagged_vlans:
                    if vlan in vlans.keys():
                        clean_tagged_vlans.append(vlan)
                        vlans[vlan].add_device(intf.device)

                intf.tagged_vlans = clean_tagged_vlans

    def validate_cabling(self):
        """Check if all cables are valid.

        Check if all cables are valid
        Check if both devices are present in the device list
            For now only process cables with both devices present
        Check if both interfaces are present as well and are not virtual
        Check that both interfaces are not already connected to a different device/interface

        When a cable is not valid, update the flag valid on the object itself
        Non valid cables will be ignored later on for update/creation
        """

        def is_cable_side_valid(cable, side):
            """Check if the given side of a cable (a or z) is valid or not.

            Check if both the device and the interface are present in the internal store
            """
            dev_name, intf_name = cable.get_device_intf(side)

            try:
                self.get(self.device, identifier=dev_name)
            except ObjectNotFound:
                return True

            try:
                # TODO: Not actually used right now, update F841 when complete
                self.get(self.interface, identifier=dict(name=intf_name, device=dev_name))  # noqa: F841
            except ObjectNotFound:
                return True

            # if not dev:
            #     LOGGER.debug("CABLE: %s not present in devices list (%s side)", dev_name, side)
            #     self.delete(cable)
            #     return False

            # intf = self.get(self.interface, keys=[dev_name, intf_name])

            # if not intf:
            #     LOGGER.warning("CABLE: %s:%s not present in interfaces list", dev_name, intf_name)
            #     self.delete(cable)
            #     return False

            # if intf.is_virtual:
            #     LOGGER.debug(
            #         "CABLE: %s:%s is a virtual interface, can't be used for cabling SKIPPING (%s side)",
            #         dev_name,
            #         intf_name,
            #         side,
            #     )
            #     self.remove(cable)
            #     return False

            return True

        cables = self.get_all(self.cable)
        for cable in list(cables):

            for side in ["a", "z"]:

                if not is_cable_side_valid(cable, side):
                    break
