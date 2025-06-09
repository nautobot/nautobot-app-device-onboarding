from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuImportButton, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Device Onboarding",
        weight=150,
        groups=(
            NavMenuGroup(
                weight=100,
                name="Discovery",
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_device_onboarding:discovereddevice_list",
                        name="Discovered Devices",
                        permissions=["nautobot_device_onboarding.view_discovereddevice"],
                    ),
                )
            ),
        )
    ),
)