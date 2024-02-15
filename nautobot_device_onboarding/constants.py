"""Constants for nautobot_device_onboarding app."""

NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
}

# PLATFORM_COMMAND_MAP = {
#     "cisco_ios": ["show version", "show inventory", "show interfaces"],
#     "cisco_nxos": ["show version", "show inventory", "show interface"],
#     "cisco_xe": ["show version", "show inventory", "show interfaces"],
#     "juniper_junos": ["show version", "show interfaces", "show chassis hardware"],
# }

# CISCO_INTERFACE_ABBREVIATIONS = {
#     "Fa": "FastEthernet",
#     "Gi": "GigabitEthernet",
#     "Te": "TenGigabitEthernet",
#     "Twe": "TwentyFiveGigE",
#     "Fo": "FortyGigabitEthernet",
#     "Ap": "AppGigabitEthernet",
#     "Lo": "Loopback",
#     "Po": "Port-channel",
#     "BE": "Bundle-Ether",
#     "Vl": "Vlan",
#     "Tu": "Tunnel",
# }

# CISCO_TO_NAUTOBOT_INTERFACE_TYPE = {
#     "Fast Ethernet": "100base-tx",
#     "EtherChannel": "lag",
#     "Gigabit Ethernet": "1000base-tx",
#     "Ten Gigabit Ethernet": "10gbase-t",
#     "Twenty Five Gigabit Ethernet": "25gbase-t",
#     "Forty Gigabit Ethernet": "40gbase-t",
#     "AppGigabitEthernet": "40gbase-t",
#     "Port-channel": "lag",
#     "Ethernet SVI": "virtual",
# }

# TAGGED_INTERFACE_TYPES = {
#     "static access": "access",
#     "dynamic auto": "trunk-all",
#     "trunk": "trunk",
# }
