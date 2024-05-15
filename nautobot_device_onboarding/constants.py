"""Constants for nautobot_device_onboarding app."""

from django.conf import settings
from nautobot.dcim.utils import get_all_network_driver_mappings

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


# This is used in the new SSoT based jobs.
SUPPORTED_NETWORK_DRIVERS = list(get_all_network_driver_mappings().keys())

# This is used in the new SSoT based jobs. Soon TPP, PYATS should be supported.
# SUPPORTED_COMMAND_PARSERS = ["textfsm", "ttp", "pyats"]
SUPPORTED_COMMAND_PARSERS = ["textfsm"]

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
    "EtherSVI": "virtual",
    "FastEthernet": "100base-fx",
    "ethernet": "1000base-t",
}
