"""Constants for nautobot_device_onboarding app."""

from django.conf import settings

PLUGIN_CFG = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]

# DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))

# This should be removed and network_driver mapping should be used instead.
NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
    "cisco_wlc": "cisco_wlc",
}

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
