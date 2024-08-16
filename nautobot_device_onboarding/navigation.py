"""Append discovered models to Navigation Menu."""

from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab

items = [
    NavMenuItem(
        link="plugins:nautobot_device_onboarding:discoveredgroup_list",
        name="Discovered Group",
        permissions=["nautobot_device_onboarding.view_discoveredgroup"],
    ),
    NavMenuItem(
        link="plugins:nautobot_device_onboarding:discoveredipaddress_list",
        name="Discovered IP Address",
        permissions=["nautobot_device_onboarding.view_discoveredipaddress"],
    ),
    NavMenuItem(
        link="plugins:nautobot_device_onboarding:discoveredport_list",
        name="Discovered Port",
        permissions=["nautobot_device_onboarding.view_discoveredport"],
    ),
]

menu_items = (
    NavMenuTab(
        name="Discovered Network",
        weight=1000,
        groups=(NavMenuGroup(name="Discovered Models", weight=100, items=items),),
    ),
)
