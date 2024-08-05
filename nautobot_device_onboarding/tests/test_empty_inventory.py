"""Test empty inventory creation."""

import unittest

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
