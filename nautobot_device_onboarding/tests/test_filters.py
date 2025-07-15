from unittest import TestCase
from nautobot.ipam.models import Prefix, get_default_namespace
from nautobot.extras.models import Status
from nautobot_device_onboarding.models import DiscoveredDevice
from nautobot_device_onboarding.filters import DiscoveredDeviceFilterSet


class DiscoveredDeviceFilterTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.prefix = Prefix.objects.create(namespace=get_default_namespace(), network="10.0.0.0", prefix_length=30, ip_version=4, status=Status.objects.create(name="Active"))
        cls.discovered_1 = DiscoveredDevice.objects.create(ip_address="10.0.0.1")
        cls.discovered_2 = DiscoveredDevice.objects.create(ip_address="192.168.1.1")
    
    def test_prefix_filter(self):
        filterset = DiscoveredDeviceFilterSet()
        self.assertTrue(len(filterset.get_ips_by_prefix(DiscoveredDevice.objects.all(), "", self.prefix)) == 1)
