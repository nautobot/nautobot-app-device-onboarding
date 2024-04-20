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

# This should potentially be removed and used nautobot core directly choices.
INTERFACE_TYPE_MAP_STATIC = {
    "Gigabit Ethernet": "1000base-t",
    "Ten Gigabit Ethernet": "10gbase-t",
    "Ethernet SVI": "virtual",
    "EtherChannel": "lag",
    "1000/10000 Ethernet": "1000base-t",
    "Port-channel": "lag",
    "EtherSVI": "virtual",
    "FastEthernet": "100base-fx",
}
