"""Test empty inventory creation."""

import unittest
from unittest import mock

from nautobot_device_onboarding.nornir_plays.empty_inventory import EmptyInventory


class TestEmptyInventory(unittest.TestCase):
    """Test Empty Inventory Nornir Class."""

    def setUp(self):
        self.inv = EmptyInventory().load()

    def test_initialize_empty_inventory_hosts(self):
        self.assertEqual(self.inv.hosts, {})

    def test_initialize_empty_inventory_groups(self):
        self.assertEqual(self.inv.groups, {})

    def test_initialize_empty_inventory_defaults(self):
        self.assertEqual(list(self.inv.defaults.data.keys()), ["platform_parsing_info", "network_driver_mappings"])

    @mock.patch("nautobot_device_onboarding.nornir_plays.empty_inventory.add_platform_parsing_info")
    def test_load_passes_logger_through(self, mock_add_platform_parsing_info):
        logger = mock.MagicMock()
        EmptyInventory(logger=logger, raise_on_repo_error=True).load()
        mock_add_platform_parsing_info.assert_called_once_with(logger=logger, raise_on_repo_error=True)
