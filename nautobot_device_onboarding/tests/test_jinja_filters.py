"""Test Filters for Jinja2 PostProcessing."""

import unittest
import unittest.mock
from nautobot_device_onboarding.jinja_filters import (
    extract_prefix,
    flatten_dict_from_value,
    flatten_list_of_dict_from_value,
    get_entry_from_dict,
    get_vlan_data,
    interface_mode_logic,
    interface_status_to_bool,
    key_exist_or_default,
    map_interface_type,
    parse_junos_ip_address,
    port_mode_to_nautobot,
)


class TestJinjaFilters(unittest.TestCase):
    """Test all the jinja filters defined."""

    def test_map_interface_type_default(self):
        """Map interface type to a Nautobot type."""
        self.assertEqual(map_interface_type("foo"), "other")

    def test_map_interface_type_valid_key(self):
        """Map interface type to a Nautobot type."""
        self.assertEqual(map_interface_type("ethernet"), "1000base-t")

    def test_extract_prefix_valid_without_slash(self):
        """Extract the prefix length from the IP/Prefix. E.g 192.168.1.1/24."""
        self.assertEqual(extract_prefix("198.51.100.1"), "198.51.100.1")

    def test_extract_prefix_valid_with_slash(self):
        """Extract the prefix length from the IP/Prefix. E.g 192.168.1.1/24."""
        self.assertEqual(extract_prefix("198.51.100.1/24"), "24")

    def test_interface_status_to_bool_down(self):
        """Take links or admin status and change to boolean."""
        self.assertFalse(interface_status_to_bool("down"))

    def test_interface_status_to_bool_admindown(self):
        """Take links or admin status and change to boolean."""
        self.assertFalse(interface_status_to_bool("Administratively Down"))

    def test_interface_status_to_bool_linkdown(self):
        """Take links or admin status and change to boolean."""
        self.assertFalse(interface_status_to_bool("link status down"))

    def test_interface_status_to_bool_up(self):
        """Take links or admin status and change to boolean."""
        self.assertTrue(interface_status_to_bool("up"))

    def test_interface_status_to_bool_up_upper(self):
        """Take links or admin status and change to boolean."""
        self.assertTrue(interface_status_to_bool("UP"))

    def test_port_mode_to_nautobot_default(self):
        """Take links or admin status and change to boolean."""
        self.assertEqual(port_mode_to_nautobot("foo"), "")

    def test_port_mode_to_nautobot_valid_key(self):
        """Take links or admin status and change to boolean."""
        self.assertEqual(port_mode_to_nautobot("bridged"), "tagged")

    def test_key_exist_or_default_key_valid(self):
        """Take a dict with a key and if its not truthy return a default."""
        self.assertEqual(key_exist_or_default({"foo": "bar"}, "foo"), {"foo": "bar"})

    def test_key_exist_or_default_key_invalid(self):
        """Take a dict with a key and if its not truthy return a default."""
        self.assertEqual(key_exist_or_default({"foo": "bar"}, "baz"), {})

    def test_flatten_list_of_dict_from_value_valid(self):
        """Takes a list of dictionaries with a value and flattens it."""
        sent_data = [{"1": {"name": "name1"}}, {"2": {"name": "name2"}}]
        expected_data = {"1": "name1", "2": "name2"}
        self.assertEqual(flatten_list_of_dict_from_value(sent_data, "name"), expected_data)

    def test_flatten_dict_from_value_valid(self):
        """Takes a dictionary of dictionaries with a value and flattens it."""
        sent_data = {"1": {"name": "name1"}, "2": {"name": "name2"}}
        expected_data = {"1": "name1", "2": "name2"}
        self.assertEqual(flatten_dict_from_value(sent_data, "name"), expected_data)

    def test_get_entry_from_dict_valid(self):
        """Take a dict with a key and return its object."""
        self.assertEqual(get_entry_from_dict({"foo": "bar"}, "foo"), "bar")

    def test_get_entry_from_dict_default(self):
        """Take a dict with a key and return its object."""
        self.assertEqual(get_entry_from_dict({"foo": "bar"}, "baz"), "")

    def test_interface_mode_logic_access(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "access"
        actual_value = interface_mode_logic(
            [{"admin_mode": "access", "mode": "access", "access_vlan": "1", "trunking_vlans": "10"}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_trunk_tagged_all_str(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged-all"
        actual_value = interface_mode_logic(
            [{"admin_mode": "trunk", "mode": "trunk", "access_vlan": "1", "trunking_vlans": "ALL"}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_trunk_tagged_range_str(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged-all"
        actual_value = interface_mode_logic(
            [{"admin_mode": "trunk", "mode": "trunk", "access_vlan": "1", "trunking_vlans": "1-4094"}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_trunk_tagged_all_list(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged-all"
        actual_value = interface_mode_logic(
            [{"admin_mode": "trunk", "mode": "trunk", "access_vlan": "1", "trunking_vlans": ["ALL"]}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_trunk_tagged_range_list(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged-all"
        actual_value = interface_mode_logic(
            [{"admin_mode": "trunk", "mode": "trunk", "access_vlan": "1", "trunking_vlans": ["1-4094"]}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_trunk_single_tagged(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged"
        actual_value = interface_mode_logic(
            [{"admin_mode": "trunk", "mode": "trunk", "access_vlan": "1", "trunking_vlans": ["10"]}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_dynamic_access(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "access"
        actual_value = interface_mode_logic(
            [{"admin_mode": "dynamic", "mode": "access", "access_vlan": "1", "trunking_vlans": ["10"]}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_dynamic_trunk_all(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged-all"
        actual_value = interface_mode_logic(
            [{"admin_mode": "dynamic", "mode": "trunk", "access_vlan": "1", "trunking_vlans": ["ALL"]}]
        )
        self.assertEqual(expected_value, actual_value)

    def test_interface_mode_logic_dynamic_trunk_single(self):
        """Logic to translate network modes to nautobot mode."""
        expected_value = "tagged"
        actual_value = interface_mode_logic(
            [{"admin_mode": "dynamic", "mode": "trunk", "access_vlan": "1", "trunking_vlans": "10"}]
        )
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_empty_item_data(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "access"
        expected_value = []
        actual_value = get_vlan_data([], [], "tagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_tagged_all_tagged_all(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged-all"
        expected_value = []
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": ["ALL"]}], [{"10": "VLAN0010"}], "tagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_tagged_all_tagged_range(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged-all"
        expected_value = []
        actual_value = get_vlan_data(
            [{"access_vlan": "10", "trunking_vlans": ["1-4094"]}], {"10": "VLAN0010"}, "tagged"
        )
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_access_create_defined_name(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "access"
        expected_value = [{"id": "10", "name": "DATA"}]
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": ["1-4094"]}], {"10": "DATA"}, "untagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_access_tagged_vlans_defined_trunking_as_list(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged"
        expected_value = [{"id": "10", "name": "DATA"}]
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": ["10"]}], {"10": "DATA"}, "tagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_access_tagged_vlans_defined_trunking_as_str(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged"
        expected_value = [{"id": "10", "name": "DATA"}]
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": "10"}], {"10": "DATA"}, "tagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_access_tagged_vlans_no_name_trunking_as_list(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged"
        expected_value = [{"id": "12", "name": "VLAN0012"}]
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": ["12"]}], {"10": "DATA"}, "tagged")
        self.assertEqual(expected_value, actual_value)

    @unittest.mock.patch("nautobot_device_onboarding.jinja_filters.interface_mode_logic")
    def test_get_vlan_data_access_tagged_vlans_no_name_trunking_as_str(self, mock_mode):
        """Get vlan information from an item."""
        mock_mode.return_value = "tagged"
        expected_value = [{"id": "12", "name": "VLAN0012"}]
        actual_value = get_vlan_data([{"access_vlan": "10", "trunking_vlans": "12"}], {"10": "DATA"}, "tagged")
        self.assertEqual(expected_value, actual_value)

    def test_parse_junos_ip_address_values_as_list_single(self):
        """Parse Junos IP and destination prefix."""
        data = [{"prefix_length": ["10.65.229.106/31"], "ip_address": ["10.65.229.106"]}]
        expected = [{"prefix_length": "31", "ip_address": "10.65.229.106"}]
        self.assertEqual(parse_junos_ip_address(data), expected)

    @unittest.skip("Need to correct assert used for list of dictionaries.")
    def test_parse_junos_ip_address_values_as_list_multiple(self):
        """Parse Junos IP and destination prefix."""
        data = [{"prefix_length": ["10.65.133.0/29", "10.65.133.0/29"], "ip_address": ["10.65.133.1", "10.65.133.3"]}]
        expected = [
            {"prefix_length": "29", "ip_address": "10.65.133.1"},
            {"ip_address": "10.65.133.3", "prefix_length": "29"},
        ]
        self.assertEqual(parse_junos_ip_address(data), expected)

    def test_parse_junos_ip_address_values_as_empty_list(self):
        """Parse Junos IP and destination prefix."""
        data = [{"prefix_length": [], "ip_address": []}]
        self.assertEqual(parse_junos_ip_address(data), [])

    def test_parse_junos_ip_address_values_as_none(self):
        """Parse Junos IP and destination prefix."""
        data = [{"prefix_length": None, "ip_address": None}]
        self.assertEqual(parse_junos_ip_address(data), [])
