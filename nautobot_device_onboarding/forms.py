"""Nautobot Device Onboarding forms."""

from django import forms
from nautobot.apps.forms import DynamicModelChoiceField, NautobotModelForm, StaticSelect2
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.dcim.models import Platform
from nautobot.extras.models import Role, SecretsGroup, Status
from nautobot.ipam.models import Namespace

from nautobot_device_onboarding import models


class OnboardingConfigSyncDevicesForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """OnboardingConfigSyncDevices creation/edit form."""

    preferred_config = forms.BooleanField(
        required=False,
        label="Preferred Config",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    connectivity_test = forms.BooleanField(
        required=False,
        label="Connectivity Test",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    namespace = DynamicModelChoiceField(
        queryset=Namespace.objects.all(),
        required=False,
    )
    device_role = DynamicModelChoiceField(
        queryset=Role.objects.all(),
        query_params={"content_types": "dcim.device"},
        required=False,
    )
    secrets_group = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        required=False,
    )
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
    )
    device_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "dcim.device"},
        required=False,
    )
    interface_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "dcim.interface"},
        required=False,
    )
    ip_address_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "ipam.ipaddress"},
        required=False,
    )

    class Meta:
        """Meta attributes."""

        model = models.OnboardingConfigSyncDevices
        fields = [
            "name",
            "preferred_config",
            "connectivity_test",
            "namespace",
            "device_role",
            "secrets_group",
            "device_status",
            "interface_status",
            "ip_address_status",
            "port",
            "timeout",
        ]


class OnboardingConfigSyncNetworkDataFromNetworkForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """OnboardingConfigSyncNetworkDataFromNetwork creation/edit form."""

    namespace = DynamicModelChoiceField(
        queryset=Namespace.objects.all(),
        required=False,
    )
    interface_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "dcim.interface"},
        required=False,
    )
    ip_address_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "ipam.ipaddress"},
        required=False,
    )
    default_prefix_status = DynamicModelChoiceField(
        queryset=Status.objects.all(),
        query_params={"content_types": "ipam.prefix"},
        required=False,
    )
    preferred_config = forms.BooleanField(
        required=False,
        label="Preferred Config",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    connectivity_test = forms.BooleanField(
        required=False,
        label="Connectivity Test",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    sync_vlans = forms.BooleanField(
        required=False,
        label="Sync VLANs",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    sync_vrfs = forms.BooleanField(
        required=False,
        label="Sync VRFs",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    sync_cables = forms.BooleanField(
        required=False,
        label="Sync Cables",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    sync_software = forms.BooleanField(
        required=False,
        label="Sync Software",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )

    class Meta:
        """Meta attributes."""

        model = models.OnboardingConfigSyncNetworkDataFromNetwork
        fields = [
            "name",
            "preferred_config",
            "connectivity_test",
            "sync_vlans",
            "sync_vrfs",
            "sync_cables",
            "sync_software",
            "namespace",
            "interface_status",
            "ip_address_status",
            "default_prefix_status",
            "sync_vlans_location_type",
        ]
