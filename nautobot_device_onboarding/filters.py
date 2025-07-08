from nautobot.apps.filters import NautobotFilterSet
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot.ipam.models import Prefix
from django_filters import ModelChoiceFilter
import ipaddress

class DiscoveredDeviceFilterSet(NautobotFilterSet):

    prefix = ModelChoiceFilter(queryset=Prefix.objects.all(), method="get_ips_by_prefix")

    # TODO: this runs really inefficiently for large prefixes
    def get_ips_by_prefix(self, queryset, name, value):
        network = ipaddress.ip_network(value.prefix)
        return queryset.filter(ip_address__in=[str(ip) for ip in network.hosts()])
    
    class Meta:
        model = DiscoveredDevice
        fields = [
            "id",
            "ip_address",
            "hostname",
            "prefix",
            "tcp_response",
            "last_successful_tcp_response",
            "ssh_response",
            "last_successful_ssh_response",
            "ssh_port",
            "ssh_credentials",
            "discovered_platform",
        ]