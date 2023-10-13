"""Plugin additions to the Nautobot navigation menu."""

# from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab, NavMenuAddButton, NavMenuImportButton


menu_items = (
    NavMenuTab(
        name="Plugins",
        groups=(
            NavMenuGroup(
                name="Device Onboarding",
                weight=1000,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_device_onboarding:onboardingtask_list",
                        name="Onboarding Tasks",
                        permissions=["nautobot_device_onboarding.view_onboardingtask"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_device_onboarding:onboardingtask_add",
                                permissions=["nautobot_device_onboarding.add_onboardingtask"],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobot_device_onboarding:onboardingtask_import",
                                permissions=["nautobot_device_onboarding.add_onboardingtask"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
