from nautobot.apps.forms import NautobotFilterForm, NautobotModelForm, DateTimePicker, NautobotBulkEditForm, DynamicModelChoiceField
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot.extras.models import SecretsGroup, Status, Role
from nautobot.dcim.models import Location
from nautobot.ipam.models import Namespace
from django import forms

class DiscoveredDeviceFilterForm(NautobotFilterForm):
    model = DiscoveredDevice
    class Meta:
        fields = [
            "id",
        ]

class DiscoveredDeviceForm(NautobotModelForm):

    last_successful_tcp_response = forms.DateTimeField(widget=DateTimePicker())
    last_successful_ssh_response = forms.DateTimeField(widget=DateTimePicker())

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
            "device_role",
            "device_status",
            "interface_status"
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