"""Forms for network device onboarding."""

from django import forms
from django.db import transaction

from nautobot.apps.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.core.forms import BootstrapMixin, StaticSelect2Multiple
from nautobot.dcim.models import DeviceType, Location, Platform
from nautobot.extras.models import Role

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.choices import OnboardingStatusChoices, OnboardingFailChoices
from nautobot_device_onboarding.utils.credentials import Credentials
from nautobot_device_onboarding.worker import enqueue_onboarding_task

BLANK_CHOICE = (("", "---------"),)


class OnboardingTaskForm(BootstrapMixin, forms.ModelForm):
    """Form for creating a new OnboardingTask instance."""

    ip_address = forms.CharField(
        required=True, label="IP address", help_text="IP Address/DNS Name of the device to onboard"
    )

    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        query_params={"content_type": "dcim.device"},
        required=True,
        help_text="Name of parent Location for the onboarded device",
        error_messages={
            "invalid_choice": "Location not found",
        },
    )

    username = forms.CharField(required=False, help_text="Device username (will not be stored in database)")
    password = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device password (will not be stored in database)"
    )
    secret = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device secret (will not be stored in database)"
    )

    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="pk",
        help_text="Device platform. Define ONLY to override auto-recognition of platform.",
    )
    role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        query_params={"content_types": "dcim.device"},
        required=False,
        help_text="Slug of device role. Define ONLY to override auto-recognition of role.",
        error_messages={
            "invalid_choice": "Role not found",
        },
    )
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        to_field_name="model",
        help_text="Device type. Define ONLY to override auto-recognition of type.",
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "location",
            "ip_address",
            "port",
            "timeout",
            "username",
            "password",
            "secret",
            "platform",
            "role",
            "device_type",
        ]

    def clean(self):
        """Update clean to make Null a blank string."""
        super().clean()
        if not self.cleaned_data.get("device_type"):
            self.cleaned_data["device_type"] = ""

    def save(self, commit=True, **kwargs):
        """Save the model, and add it and the associated credentials to the onboarding worker queue."""
        model = super().save(commit=commit, **kwargs)
        if commit:
            credentials = Credentials(self.data.get("username"), self.data.get("password"), self.data.get("secret"))
            transaction.on_commit(lambda: enqueue_onboarding_task(model.pk, credentials))
        return model


class OnboardingTaskFilterForm(BootstrapMixin, forms.ModelForm):
    """Form for filtering OnboardingTask instances."""

    location = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(), query_params={"content_type": "dcim.device"}, required=False
    )

    platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False)

    status = forms.MultipleChoiceField(
        choices=BLANK_CHOICE + OnboardingStatusChoices.CHOICES, required=False, widget=StaticSelect2Multiple()
    )

    failed_reason = forms.MultipleChoiceField(
        choices=BLANK_CHOICE + OnboardingFailChoices.CHOICES,
        required=False,
        label="Failed Reason",
        widget=StaticSelect2Multiple(),
    )

    q = forms.CharField(required=False, label="Search")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["q", "location", "platform", "status", "failed_reason"]
