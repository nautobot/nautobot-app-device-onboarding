"""Model serializers for the nautobot_device_onboarding REST API."""

from rest_framework import serializers

from nautobot.dcim.models import Site, DeviceRole, Platform

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.utils.credentials import Credentials
from nautobot_device_onboarding.worker import enqueue_onboarding_task


class OnboardingTaskSerializer(serializers.ModelSerializer):
    """Serializer for the OnboardingTask model."""

    site = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Site.objects.all(),
        slug_field="slug",
        required=True,
        help_text="Nautobot site 'slug' value",
    )

    ip_address = serializers.CharField(
        required=True,
        help_text="IP Address to reach device",
    )

    username = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Device username",
    )

    password = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Device password",
    )

    secret = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Device secret password",
    )

    port = serializers.IntegerField(required=False, help_text="Device PORT to check for online")

    timeout = serializers.IntegerField(required=False, help_text="Timeout (sec) for device connect")

    role = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=DeviceRole.objects.all(),
        slug_field="slug",
        required=False,
        help_text="Nautobot device role 'slug' value",
    )

    device_type = serializers.CharField(
        required=False,
        help_text="Nautobot device type 'slug' value",
    )

    platform = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Platform.objects.all(),
        slug_field="slug",
        required=False,
        help_text="Nautobot Platform 'slug' value",
    )

    created_device = serializers.CharField(
        required=False,
        read_only=True,
        help_text="Created device name",
    )

    status = serializers.CharField(required=False, read_only=True, help_text="Onboarding Status")

    failed_reason = serializers.CharField(required=False, read_only=True, help_text="Failure reason")

    message = serializers.CharField(required=False, read_only=True, help_text="Status message")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "id",
            "site",
            "ip_address",
            "username",
            "password",
            "secret",
            "port",
            "timeout",
            "role",
            "device_type",
            "platform",
            "created_device",
            "status",
            "failed_reason",
            "message",
        ]

    def create(self, validated_data):
        """Create an OnboardingTask and enqueue it for processing."""
        # Fields are string-type so default to empty (instead of None)
        username = validated_data.pop("username", "")
        password = validated_data.pop("password", "")
        secret = validated_data.pop("secret", "")

        credentials = Credentials(
            username=username,
            password=password,
            secret=secret,
        )

        ot = OnboardingTask.objects.create(**validated_data)

        enqueue_onboarding_task(ot.id, credentials)

        return ot
