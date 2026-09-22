"""Constants for nautobot_device_onboarding app."""

from django.conf import settings

NETMIKO_EXTRAS = (
    settings.PLUGINS_CONFIG.get("nautobot_plugin_nornir", {})
    .get("connection_options", {})
    .get("netmiko", {})
    .get("extras", {})
)

PLUGIN_CFG = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]

# This mapping is only used for the original onboarding job.
NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
}


# This is used in the new SSoT based jobs. Soon PYATS should be supported.
SUPPORTED_COMMAND_PARSERS = ["textfsm", "ttp"]

# This should potentially be removed and used nautobot core directly choices.
# from nautobot.dcim.choices import InterfaceTypeChoices
# InterfaceTypeChoices.as_dict() doesn't directly fit yet.  Seems like maybe netutils needs the "human readible" nb choices.
INTERFACE_TYPE_MAP_STATIC = {
    "Gigabit Ethernet": "1000base-t",
    "Ten Gigabit Ethernet": "10gbase-t",
    "Ethernet SVI": "virtual",
    "EtherChannel": "lag",
    "1000/10000 Ethernet": "1000base-t",
    "100/1000/10000 Ethernet": "1000base-t",
    "Port-channel": "lag",
    "portChannel": "lag",
    "port-channel": "lag",
    "Port-Channel": "lag",
    "GEChannel": "lag",
    "10GEChannel": "lag",
    "EtherSVI": "virtual",
    "FastEthernet": "100base-fx",
    "ethernet": "1000base-t",
    "1000/10000/25000 Ethernet": "25gbase-x-sfp28",
    "100/1000/10000/25000 Ethernet": "25gbase-x-sfp28",
    "1000/10000/25000/40000/50000/100000 Ethernet": "100gbase-x-qsfp28",
}

# Maps a raw transceiver/port indicator to a Nautobot `PortTypeChoices` value
# (dcim.Interface.port_type - the physical connector, e.g. RJ-45 or LC - which is
# distinct from `type`/INTERFACE_TYPE_MAP_STATIC above, the transceiver/interface class).
#
# This is specific to Aruba AOS-CX's "Type" strings from its transceiver/DOM CLI output
# (lower-cased), e.g. "sfp+sr", "1000sx", "qsfp+sr4" - not just the bare form factor, since
# that's what actually distinguishes the connector in practice. Other platforms report
# transceiver types differently and would need their own map rather than reusing this one.
# Direct-attach copper (DAC/twinax, e.g. "sfp+da3") is handled separately in map_port_type()
# below rather than listed here, since the cable is permanently attached to the module and
# there's no separate connector to report.
#
# Known limitation: an LR4/CWDM4/ER4 QSFP+/QSFP28 optic that internally breaks out to a
# duplex LC pair isn't distinguishable, from this string alone, from a parallel-optics one
# (SR4/PSM4) that uses its native MPO connector. Only the confirmed-MPO variants are listed;
# anything else unmapped returns "" rather than guessing.
ARUBA_AOSCX_INTERFACE_PORT_TYPE_MAP_STATIC = {
    "sfp+sr": "lc",
    "sfp+lr": "lc",
    "sfp+er": "lc",
    "sfp+zr": "lc",
    "sfp28-sr": "lc",
    "sfp28-lr": "lc",
    "sfp28-er": "lc",
    "1000sx": "lc",
    "1000lx": "lc",
    "1000zx": "lc",
    "1000bx": "lc",
    "qsfp+sr4": "mpo",
    "qsfp28-sr4": "mpo",
    "qsfp28-psm4": "mpo",
    "qsfp28-csr4": "mpo",
    # Fallback: fixed copper Ethernet port with no transceiver present / no DOM data
    # available, derived from the interface's hw_type instead of a transceiver type.
    "ethernet": "8p8c",
}

# The git repository data source content identifier for custom command mappers.
ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER = "nautobot_device_onboarding.onboarding_command_mappers"

# The git repository data source folder name for custom command mappers.
ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER = "onboarding_command_mappers"

# Support 4 modules deep (device -> modulebay -> module -> modulebay -> module -> modulebay -> module -> modulebay -> module -> interface)
ONBOARDING_DEVICE_MODULE_RECURSION_LIMIT = 4

# Network driver -> Nautobot Manufacturer display name. Override only where
# `token.split("_")[0].title()` would produce the wrong canonical name.
NETWORK_DRIVER_TO_MANUFACTURER = {
    "paloalto_panos": "Palo Alto",
}
