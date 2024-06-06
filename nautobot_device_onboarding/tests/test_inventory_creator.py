"""Test ability to create an inventory."""

import unittest
from unittest.mock import patch

from nautobot.dcim.models import Platform

from nautobot_device_onboarding.nornir_plays.inventory_creator import _set_inventory, guess_netmiko_device_type


class TestInventoryCreator(unittest.TestCase):
    """Test ability to create an inventory."""

    def setUp(self) -> None:
        self.host_ip = "198.51.100.1"
        self.hostname = "router1.example.com"
        self.username = "admin"
        self.password = "password"  # nosec
        self.port = 22
        self.platform = Platform(name="cisco_xe", network_driver="cisco_xe")

    @patch("nautobot_device_onboarding.nornir_plays.inventory_creator.SSHDetect")
    def test_guess_device_type_success(self, mock_sshdetect):
        mock_sshdetect.return_value.autodetect.return_value = "cisco_ios"
        device_type, exception = guess_netmiko_device_type(self.hostname, self.username, self.password, self.port)
        self.assertEqual(device_type, "cisco_ios")
        self.assertIsNone(exception)

    @patch("nautobot_device_onboarding.nornir_plays.inventory_creator.SSHDetect")
    def test_guess_device_type_exception(self, mock_sshdetect):
        mock_sshdetect.return_value.autodetect.side_effect = Exception("SSH Connection Failed")
        device_type, exception = guess_netmiko_device_type(self.hostname, self.username, self.password, self.port)
        self.assertIsNone(device_type)
        self.assertIsInstance(exception, Exception)

    @patch("nautobot_device_onboarding.nornir_plays.inventory_creator.SSHDetect")
    def test_set_inventory_no_platform(self, mock_sshdetect):
        mock_sshdetect.return_value.autodetect.return_value = "cisco_ios"
        inv, exception = _set_inventory(self.host_ip, None, self.port, self.username, self.password)

        self.assertEqual(inv["198.51.100.1"].platform, "cisco_ios")
        self.assertIsNone(exception)

    def test_set_inventory_specified_platform(self):
        inv, exception = _set_inventory(self.host_ip, self.platform, self.port, self.username, self.password)
        self.assertEqual(inv["198.51.100.1"].platform, self.platform.name)
        self.assertIsNone(exception)
