"""Plugin additions to the Nautobot navigation menu."""

from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:nautobot_device_onboarding:onboardingtask_list",
        link_text="Onboarding Tasks",
        permissions=["nautobot_device_onboarding.view_onboardingtask"],
        buttons=(
            PluginMenuButton(
                link="plugins:nautobot_device_onboarding:onboardingtask_add",
                title="Onboard",
                icon_class="mdi mdi-plus-thick",
                color=ButtonColorChoices.GREEN,
                permissions=["nautobot_device_onboarding.add_onboardingtask"],
            ),
            PluginMenuButton(
                link="plugins:nautobot_device_onboarding:onboardingtask_import",
                title="Bulk Onboard",
                icon_class="mdi mdi-database-import-outline",
                color=ButtonColorChoices.BLUE,
                permissions=["nautobot_device_onboarding.add_onboardingtask"],
            ),
        ),
    ),
)
