"""Model serializers for the nautobot_device_onboarding REST API."""
# pylint: disable=duplicate-code

from rest_framework import serializers

from nautobot.core.api.serializers import ValidatedModelSerializer
from nautobot.dcim.models import Location, Platform
from nautobot.extras.models import Role

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.utils.credentials import Credentials, onboarding_credentials_serializer
from nautobot_device_onboarding.worker import enqueue_onboarding_task



class OnboardingTaskSerializer(ValidatedModelSerializer):
    # """Serializer for the OnboardingTask model."""

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask

        fields = "__all__"

        read_only_fields = ["id", "created_device", "status", "failed_reason", "message"]
