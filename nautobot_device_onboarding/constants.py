"""Constants for nautobot_device_onboarding app."""

NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
}

INTERFACE_TYPE_MAP_STATIC = {
    "Gigabit Ethernet": "1000base-t",
    "Ten Gigabit Ethernet": "10gbase-t",
    "Forty Gigabit Ethernet": "40gbase-t",
    "Ethernet SVI": "virtual",
    "EthernetChannel": "lag",
}
