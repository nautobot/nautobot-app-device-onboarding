"""Device Onboarding model forms."""

from nautobot.apps.forms import (
    NautobotFilterForm,
    NautobotModelForm,
    NautobotBulkEditForm,
    DynamicModelChoiceField,
    StaticSelect2,
    DynamicModelMultipleChoiceField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot.extras.models import SecretsGroup
from nautobot.dcim.models import Platform
from nautobot.ipam.models import Prefix
from django import forms


class DiscoveredDeviceFilterForm(NautobotFilterForm):
    model = DiscoveredDevice

    prefix = DynamicModelChoiceField(queryset=Prefix.objects.all(), required=False, label="Prefix")
    tcp_response = forms.NullBooleanField(
        required=False,
        label="Has a TCP Response?",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    ssh_response = forms.NullBooleanField(
        required=False,
        label="Has a SSH Response?",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    ssh_credentials = DynamicModelMultipleChoiceField(
        queryset=SecretsGroup.objects.all(), required=False, label="SSH Credentials"
    )
    network_driver = DynamicModelMultipleChoiceField(
        queryset=Platform.objects.all(), required=False, label="Discoverd Platform"
    )

    class Meta:
        fields = [
            "ip_address",
            "hostname",
            "prefix",
            "tcp_response",
            "tcp_response_datetime",
            "ssh_response",
            "ssh_response_datetime",
            "ssh_port",
            "ssh_credentials",
            "network_driver",
            "device",
            "serial",
            "device_type",
            "inventory_status"
        ]


class DiscoveredDeviceForm(NautobotModelForm):
    ssh_credentials = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(), to_field_name="name", required=False, label="SSH Credentials"
    )

    class Meta:
        model = DiscoveredDevice
        fields = [
            "ip_address",
            "hostname",
            "tcp_response",
            "tcp_response_datetime",
            "ssh_response",
            "ssh_response_datetime",
            "ssh_port",
            "ssh_credentials",
            "network_driver",
            "device",
            "serial",
            "device_type",
            "inventory_status"
        ]


class DiscoveredDeviceBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=DiscoveredDevice.objects.all(), widget=forms.MultipleHiddenInput)
    ssh_credentials = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(), to_field_name="name", required=False, label="SSH Credentials"
    )

    class Meta:
        model = DiscoveredDevice
        fields = [
            "ip_address",
            "hostname",
            "notes",
        ]
