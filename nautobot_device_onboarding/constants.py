"""Constants for nautobot_device_onboarding app."""

NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
}

PLATFORM_COMMAND_MAP = {
    "cisco_ios": ["show version", "show inventory", "show interfaces"],
    "cisco_nxos": ["show version", "show inventory", "show interface"],
    "cisco_xe": ["show version", "show inventory", "show interfaces"],
    "juniper_junos": ["show version", "show interfaces", "show chassis hardware"],
