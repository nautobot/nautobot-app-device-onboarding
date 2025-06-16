from nautobot.apps.forms import NautobotFilterForm, NautobotModelForm, NautobotBulkEditForm, DynamicModelChoiceField, StaticSelect2, DynamicModelMultipleChoiceField
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot.extras.models import SecretsGroup, Status, Role
from nautobot.dcim.models import Location, Platform
from nautobot.ipam.models import Namespace, Prefix
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
    ssh_credentials = DynamicModelMultipleChoiceField(queryset=SecretsGroup.objects.all(), required=False, label="SSH Credentials")
    discovered_platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False, label="Discoverd Platform")
    
    class Meta:
        fields = [
            "ip_address",
            "prefix",
            "tcp_response",
            "last_successful_tcp_response",
            "ssh_response",
            "last_successful_ssh_response",
            "ssh_port",
            "ssh_credentials",
            "discovered_platform",
            "location",
            "namespace",
            "device_role",
            "device_status",
            "interface_status",
            "ip_address_status"
        ]

class DiscoveredDeviceForm(NautobotModelForm):

    ssh_credentials = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), to_field_name="name", required=False, label="SSH Credentials")
    location = DynamicModelChoiceField(queryset=Location.objects.all(), to_field_name="name", required=False, label="Location")
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), to_field_name="name", required=False, label="Namespace for IP Address")
    device_role = DynamicModelChoiceField(queryset=Role.objects.all(), to_field_name="name", required=False, label="Device Role")
    device_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="Device Status")
    interface_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="Interface Status") # TODO: filter this properly
    ip_address_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="IP Address Status") 

    class Meta:
        model = DiscoveredDevice
        fields = [
            "ip_address",
            "tcp_response",
            "last_successful_tcp_response",
            "ssh_response",
            "last_successful_ssh_response",
            "ssh_port",
            "ssh_credentials",
            "discovered_platform",
            "location",
            "namespace",
            "device_role",
            "device_status",
            "interface_status",
            "ip_address_status"
        ]

class DiscoveredDeviceBulkEditForm(NautobotBulkEditForm):

    pk = forms.ModelMultipleChoiceField(queryset=DiscoveredDevice.objects.all(), widget=forms.MultipleHiddenInput)
    ssh_credentials = DynamicModelChoiceField(queryset=SecretsGroup.objects.all(), to_field_name="name", required=False, label="SSH Credentials")
    location = DynamicModelChoiceField(queryset=Location.objects.all(), to_field_name="name", required=False, label="Location")
    namespace = DynamicModelChoiceField(queryset=Namespace.objects.all(), to_field_name="name", required=False, label="Namespace for IP Address")
    device_role = DynamicModelChoiceField(queryset=Role.objects.all(), to_field_name="name", required=False, label="Device Role")
    device_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="Device Status")
    interface_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="Interface Status") # TODO: filter this properly
    ip_address_status = DynamicModelChoiceField(queryset=Status.objects.all(), to_field_name="name", required=False, label="IP Address Status") 

    class Meta:
        model = DiscoveredDevice
        fields = [
            "ip_address",
            "tcp_response",
            "last_successful_tcp_response",
            "ssh_response",
            "last_successful_ssh_response",
            "ssh_port",
            "ssh_credentials",
            "discovered_platform",
            "location",
            "namespace",
            "device_role",
            "device_status",
            "interface_status",
            "ip_address_status"
        ]