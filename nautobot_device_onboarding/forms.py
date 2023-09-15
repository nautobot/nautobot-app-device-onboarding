"""Forms for network device onboarding."""

from django import forms
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import BootstrapMixin
from nautobot.dcim.models import Device, DeviceType, Location, Platform
from nautobot.extras.models import Role
from nautobot.extras.forms import NautobotBulkEditForm, TagsBulkEditFormMixin

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.choices import OnboardingStatusChoices, OnboardingFailChoices, DeviceTypeChoiceGenerator
from nautobot_device_onboarding.utils.credentials import Credentials
from nautobot_device_onboarding.worker import enqueue_onboarding_task

BLANK_CHOICE = (("", "---------"),)


class OnboardingTaskForm(BootstrapMixin, forms.ModelForm):
    """Form for creating a new OnboardingTask instance."""

    ip_address = forms.CharField(
        required=True, label="IP address", help_text="IP Address/DNS Name of the device to onboard"
    )

    location = forms.ModelChoiceField(required=True, queryset=Location.objects.all())

    username = forms.CharField(required=False, help_text="Device username (will not be stored in database)")
    password = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device password (will not be stored in database)"
    )
    secret = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device secret (will not be stored in database)"
    )

    platform = forms.ModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="pk",
        help_text="Device platform. Define ONLY to override auto-recognition of platform.",
    )
    # role = forms.ModelChoiceField(
    #     # queryset=Role.objects.get(content_types__in=[ContentType.objects.get_for_model(Device)]),
    #     queryset=Role.objects.all(),
    #     required=False,
    #     to_field_name="pk",
    #     help_text="Device role. Define ONLY to override auto-recognition of role.",
    # )
    device_type = forms.ChoiceField(
        choices=DeviceTypeChoiceGenerator,
        required=False,
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

    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)

    platform = forms.ModelChoiceField(queryset=Platform.objects.all(), required=False)

    status = forms.ChoiceField(choices=BLANK_CHOICE + OnboardingStatusChoices.CHOICES, required=False)

    failed_reason = forms.ChoiceField(
        choices=BLANK_CHOICE + OnboardingFailChoices.CHOICES, required=False, label="Failed Reason"
    )

    q = forms.CharField(required=False, label="Search")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["q", "location", "platform", "status", "failed_reason"]


class OnboardingTaskBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Form for entering CSV to bulk-import OnboardingTask entries."""
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=True,
        to_field_name="name",
        help_text="Name of parent site",
        error_messages={
            "invalid_choice": "Site not found",
        },
    )
    ip_address = forms.CharField(required=True, help_text="IP Address of the onboarded device")
    username = forms.CharField(required=False, help_text="Username, will not be stored in database")
    password = forms.CharField(required=False, help_text="Password, will not be stored in database")
    secret = forms.CharField(required=False, help_text="Secret password, will not be stored in database")
    platform = forms.ModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        help_text="Slug of device platform. Define ONLY to override auto-recognition of platform.",
        error_messages={
            "invalid_choice": "Platform not found.",
        },
    )
    port = forms.IntegerField(
        required=False,
        help_text="Device PORT (def: 22)",
    )

    timeout = forms.IntegerField(
        required=False,
        help_text="Device Timeout (sec) (def: 30)",
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        help_text="Slug of device role. Define ONLY to override auto-recognition of role.",
        error_messages={
            "invalid_choice": "Role not found",
        },
    )

    device_type = forms.ModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        help_text="Slug of device type. Define ONLY to override auto-recognition of type.",
        error_messages={
            "invalid_choice": "DeviceType not found",
        },
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "site",
            "ip_address",
            "port",
            "timeout",
            "platform",
            "role",
        ]

    def save(self, commit=True, **kwargs):
        """Save the model, and add it and the associated credentials to the onboarding worker queue."""
        model = super().save(commit=commit, **kwargs)
        if commit:
            credentials = Credentials(self.data.get("username"), self.data.get("password"), self.data.get("secret"))
            transaction.on_commit(lambda: enqueue_onboarding_task(model.pk, credentials))
        return model
