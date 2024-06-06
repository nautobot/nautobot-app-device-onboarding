"""Test for nornir plays in command_getter."""

import os
import unittest

import yaml

from nautobot_device_onboarding.nornir_plays.command_getter import _get_commands_to_run

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestGetCommandsToRun(unittest.TestCase):
    """Test the ability to get the proper commands to run."""

    def setUp(self):
        with open(f"{MOCK_DIR}/command_mappers/mock_cisco_ios.yml", "r", encoding="utf-8") as mock_file_data:
            self.expected_data = yaml.safe_load(mock_file_data)

    def test_deduplicate_command_list_sync_devices(self):
        """Test dedup on sync_devices ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_devices"], sync_vlans=False, sync_vrfs=False
        )
        expected_commands_to_run = [
            {"command": "show version", "jpath": "[*].hostname", "parser": "textfsm"},
            {
                "command": "show interfaces",
                "jpath": "[?ip_address=='{{ obj }}'].{name: interface, enabled: link_status}",
                "parser": "textfsm",
                "post_processor": "{{ (obj | selectattr('enabled', 'eq', 'up') | list | first ).name }}",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_no_vrfs_no_vlans(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"], sync_vlans=False, sync_vrfs=False
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_with_vrfs_no_vlans(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"], sync_vlans=False, sync_vrfs=True
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
            {
                "command": "show ip interface",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key }}'].{name:vrf}",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | key_exist_or_default('name') | tojson }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "dict",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_no_vrfs_with_vlans(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"], sync_vlans=True, sync_vrfs=False
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_with_vrfs_and_vlans(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"], sync_vlans=True, sync_vrfs=True
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
            {
                "command": "show ip interface",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key }}'].{name:vrf}",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | key_exist_or_default('name') | tojson }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "dict",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)
