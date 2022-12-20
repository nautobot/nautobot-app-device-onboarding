"""Onboarding template content."""

from nautobot.extras.plugins import PluginTemplateExtension
from nautobot_device_onboarding.models import OnboardingDevice


class DeviceContent(PluginTemplateExtension):  # pylint: disable=abstract-method
    """Table to show onboarding details on Device objects."""

    model = "dcim.device"

    def right_page(self):
        """Show table on right side of view."""
        onboarding = OnboardingDevice.objects.filter(device=self.context["object"]).first()

        if not onboarding or not onboarding.enabled:
            return ""

        status = onboarding.status
        last_check_attempt_date = onboarding.last_check_attempt_date
        last_check_successful_date = onboarding.last_check_successful_date
        last_ot = onboarding.last_ot

        return self.render(
            "nautobot_device_onboarding/device_onboarding_table.html",
            extra_context={
                "status": status,
                "last_check_attempt_date": last_check_attempt_date,
                "last_check_successful_date": last_check_successful_date,
                "last_ot": last_ot,
            },
        )


template_extensions = [DeviceContent]
