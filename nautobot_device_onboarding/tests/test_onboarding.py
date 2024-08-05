"""Unit tests for nautobot_device_onboarding.netdev_keeper module and its classes."""

# from unittest import mock

from django.conf import settings

# from django.test import TestCase
# from django.contrib.contenttypes.models import ContentType


# from nautobot.dcim.models import Device, Location, LocationType, Platform
# from nautobot.extras.models import Status


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


class NapalmMock:
    """Base napalm mock class for tests."""

    def __init__(self, *args, **kwargs):
        pass

    def open(self):
        """Mock test open ssh connection."""


class NapalmMockNxos(NapalmMock):
    """Mock napalm for nxos tests."""

    def get_facts(self):
        """Mock test get napalm facts."""
        return {
            "uptime": 4066631,
            "vendor": "Cisco",
            "hostname": "nxos-spine1",
            "fqdn": "nxos-spine1.domain.net",
            "os_version": "7.3(1)D1(1) [build 7.3(1)D1(0.10)]",
            "serial_number": "TM6017D760B",
            "model": "NX-OSv Chassis",
            "interface_list": ["mgmt0"],
        }

    def get_interfaces_ip(self):
        """Mock test get interface ip facts."""
        return {"mgmnt0": {"ipv4": {"1.1.1.1": {"prefix_length": 32}}}}


class NapalmMockEos(NapalmMock):
    """Mock napalm for eos tests."""

    def get_facts(self):
        """Mock test get napalm facts on eos."""
        return {
            "fqdn": "arista-device.domain.net",
            "hostname": "arista-device",
            "interface_list": ["Vlan100"],
            "model": "vEOS",
            "os_version": "4.15.5M-3054042.4155M",
            "serial_number": "",
            "uptime": "...",
            "vendor": "Arista",
        }

    def get_interfaces_ip(self):
        """Mock test get napalm interfaces on eos."""
        return {"Vlan100": {"ipv4": {"2.2.2.2": {"prefix_length": 32}}}}


class SSHDetectMock:
    """SSHDetect mock class for tests."""

    def __init__(self, *args, **kwargs):
        self.driver = args[0]

    def autodetect(self):
        """Mock test SSH."""
        return self.driver


# class OnboardingTestCase(TestCase):
#     """Test the OnboardingManager Class."""

#     def setUp(self):
#         """Prepare test objects."""
#         PLUGIN_SETTINGS["platform_map"] = {}  # Reset platform map to default
#         status = Status.objects.get(name="Active")
#         location_type = LocationType.objects.create(name="site")
#         location_type.content_types.set([ContentType.objects.get_for_model(Device)])
#         self.site = Location.objects.create(name="TEST_SITE", location_type=location_type, status=status)
#         self.eos_platform = Platform.objects.create(name="arista_eos", napalm_driver="eos")

#         self.onboarding_task1 = OnboardingTask.objects.create(ip_address="1.1.1.1", location=self.site)
#         self.onboarding_task2 = OnboardingTask.objects.create(
#             ip_address="2.2.2.2", location=self.site, platform=self.eos_platform, port=443
#         )

#         # Patch socket as it would be able to verify connectivity
#         self.patcher = mock.patch("nautobot_device_onboarding.netdev_keeper.socket")
#         self.patcher.start()

#     def tearDown(self):
#         """Disable patch on socket."""
#         self.patcher.stop()

#     @mock.patch("nautobot_device_onboarding.netdev_keeper.SSHDetect")
#     @mock.patch("nautobot_device_onboarding.netdev_keeper.get_network_driver")
#     def test_onboarding_nxos(self, mock_napalm, mock_ssh_detect):
#         """Test device onboarding nxos."""

#         mock_napalm.return_value = NapalmMockNxos
#         mock_ssh_detect.return_value = SSHDetectMock("cisco_nxos")

#         # Run onboarding
#         on_manager = OnboardingManager(self.onboarding_task1, "user", "pass", "secret")

#         self.assertEqual(on_manager.created_device.name, "nxos-spine1")
#         self.assertEqual(on_manager.created_device.platform.name, "cisco_nxos")
#         self.assertEqual(on_manager.created_device.platform.napalm_driver, "nxos_ssh")
#         self.assertEqual(str(on_manager.created_device.primary_ip4), "1.1.1.1/32")

#     @mock.patch("nautobot_device_onboarding.netdev_keeper.SSHDetect")
#     @mock.patch("nautobot_device_onboarding.netdev_keeper.get_network_driver")
#     def test_onboarding_eos(self, mock_napalm, mock_ssh_detect):
#         """Test device onboarding eos."""

#         mock_napalm.return_value = NapalmMockEos
#         mock_ssh_detect.return_value = SSHDetectMock("arista_eos")

#         # Run onboarding
#         on_manager = OnboardingManager(self.onboarding_task2, "user", "pass", "secret")

#         self.assertEqual(on_manager.created_device.name, "arista-device")
#         self.assertEqual(on_manager.created_device.platform.name, "arista_eos")
#         self.assertEqual(on_manager.created_device.platform.napalm_driver, "eos")
#         self.assertEqual(str(on_manager.created_device.primary_ip4), "2.2.2.2/32")
