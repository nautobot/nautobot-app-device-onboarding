"""Plugin additions to the Nautobot navigation menu."""

# from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab, NavMenuAddButton


menu_items = (
    NavMenuTab(
        name="Plugins",
        groups=(NavMenuGroup(name="Device Onboarding", weight=1000, items=(
            NavMenuItem(
                link="plugins:nautobot_device_onboarding:onboardingtask_list",
                name="Onboarding Tasks",
                permissions=["nautobot_device_onboarding.view_onboardingtask"],
                buttons=(
                    NavMenuAddButton(
                        link="plugins:nautobot_device_onboarding:onboardingtask_add",
                        # name="Onboard",
                        # icon_class="mdi mdi-plus-thick",
                        # color=ButtonColorChoices.GREEN,
                        permissions=["nautobot_device_onboarding.add_onboardingtask"],
                    ),
                    NavMenuAddButton(
                        link="plugins:nautobot_device_onboarding:onboardingtask_import",
                        # name="Bulk Onboard",
                        # icon_class="mdi mdi-database-import-outline",
                        # color=ButtonColorChoices.BLUE,
                        permissions=["nautobot_device_onboarding.add_onboardingtask"],
                    ),
                ),
            ),
        ),),),
    ),
)
