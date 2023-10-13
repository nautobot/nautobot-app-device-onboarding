"""Administrative capabilities for nautobot_device_onboarding plugin."""
from django.contrib import admin
from nautobot_device_onboarding.models import OnboardingTask


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    """Administrative view for managing OnboardingTask instances."""

    list_display = (
        "pk",
        "created_device",
        "ip_address",
        "location",
        "role",
        "device_type",
        "platform",
        "status",
        "message",
        "failed_reason",
        "port",
        "timeout",
        "created",
    )
