"""Test for nornir plays in command_getter."""

import os
import json
import unittest
import yaml
from nornir.core.inventory import ConnectionOptions, Host, Defaults
from nautobot_device_onboarding.nornir_plays.formatter import perform_data_extraction, extract_and_post_process
from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


def find_files_by_prefix(directory, prefix):
    """Finds all files within a directory whose names start with the given prefix.

    Args:
        directory: The directory path to search.
        prefix: The prefix string to match in filenames.

    Returns:
        A list of filenames that start with the prefix.
    """
    matching_files = []
    for filename in os.listdir(directory):
        if filename.startswith(prefix):
            matching_files.append(filename)
    return matching_files


class TestFormatterDeviceSync(unittest.TestCase):
    """Tests to ensure formatter is working for sync devices 'ssot job'."""

    def setUp(self):
        # Load the application command_mapper files
        self.platform_parsing_info = add_platform_parsing_info()
        self.host = Host(
            name="198.51.100.1",
            hostname="198.51.100.1",
            port=22,
            username="username",
            password="password",  # nosec
            platform="",  # Purposedly setting as None since we will loop through a single host instance for other tests.
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname="198.51.100.1",
                    port=22,
                    username="username",
                    password="password",  # nosec
                    platform="platform",
                )
            },
            defaults=Defaults(data={"sync_vlans": False, "sync_vrfs": False}),
        )

    def test_add_platform_parsing_info_sane_defaults(self):
        # Note: This is also officially tested in test_transform, but secondary check here as well.
        default_mappers = ["cisco_ios", "arista_eos", "cisco_wlc", "cisco_xe", "juniper_junos", "cisco_nxos"]
        self.assertEqual(sorted(default_mappers), list(sorted(self.platform_parsing_info.keys())))

    def test_create_inventory_host_per_platform(self):
        for platform in list(self.platform_parsing_info.keys()):
            self.host.platform = platform
            with self.subTest(msg=f"Testing host with platform {platform}"):
                self.assertEqual(platform, self.host.platform)

    def test_perform_data_extraction_simple_host_values(self):
        for platform in list(self.platform_parsing_info.keys()):
            self.host.platform = platform
            with self.subTest(msg=f"Testing host with platform {platform}"):
                self.assertEqual("198.51.100.1", self.host.name)
                self.assertFalse(self.host.data.get("sync_vlans"))
                self.assertFalse(self.host.data.get("sync_vrfs"))

    def test_perform_data_extraction_sync_devices(self):
        for platform in list(self.platform_parsing_info.keys()):
            self.host.platform = platform
            current_test_dir = f"{MOCK_DIR}/{platform}/"
            getters = find_files_by_prefix(current_test_dir, "command_getter")
            # NOTE: Cleanup later, should always require tests to be present
            if len(getters) > 0:
                with self.subTest(msg=f"test_perform_data_extraction_sync_devices with platform {platform}"):
                    for command_getter_file in getters:
                        with open(
                            f"{MOCK_DIR}/{platform}/sync_devices_expected_result_{command_getter_file.split('_')[-1]}",
                            "r",
                            encoding="utf-8",
                        ) as expected_parsed:
                            expected_parsed_result = json.loads(expected_parsed.read())
                        with open(
                            f"{MOCK_DIR}/{platform}/{command_getter_file}", "r", encoding="utf-8"
                        ) as command_info:
                            command_outputs = json.loads(command_info.read())
                            actual_result = perform_data_extraction(
                                self.host,
                                self.platform_parsing_info[platform]["sync_devices"],
                                command_outputs,
                                job_debug=False,
                            )
                            self.assertEqual(expected_parsed_result, actual_result)

    @unittest.skip(reason="Todo test sync network data, similar to test_perform_data_extraction_sync_devices.")
    def test_perform_data_extraction_sync_network_data(self):
        for platform in list(self.platform_parsing_info.keys()):
            self.host.platform = platform
            current_test_dir = f"{MOCK_DIR}/{platform}/"
            getters = find_files_by_prefix(current_test_dir, "command_getter")
            # NOTE: Cleanup later, should always require tests to be present
            if len(getters) > 0:
                with self.subTest(msg=f"test_perform_data_extraction_sync_devices with platform {platform}"):
                    for command_getter_file in getters:
                        with open(
                            f"{MOCK_DIR}/{platform}/sync_network_data_expected_result_{command_getter_file.split('_')[-1]}",
                            "r",
                            encoding="utf-8",
                        ) as expected_parsed:
                            expected_parsed_result = json.loads(expected_parsed.read())
                        with open(
                            f"{MOCK_DIR}/{platform}/{command_getter_file}", "r", encoding="utf-8"
                        ) as command_info:
                            command_outputs = json.loads(command_info.read())
                            actual_result = perform_data_extraction(
                                self.host,
                                self.platform_parsing_info[platform]["sync_network_data"],
                                command_outputs,
                                job_debug=False,
                            )
                            self.assertEqual(expected_parsed_result, actual_result)


class TestFormatter(unittest.TestCase):
    """Original test formatter test, to be replaced by newer format."""

    def setUp(self):
        with open(f"{MOCK_DIR}/command_mappers/mock_cisco_ios.yml", "r", encoding="utf-8") as parsing_info:
            self.platform_parsing_info = yaml.safe_load(parsing_info)
        with open(f"{MOCK_DIR}/cisco_ios/command_getter_result_1.json", "r", encoding="utf-8") as command_info:
            self.command_outputs = json.loads(command_info.read())
        self.host = Host(
            name="198.51.100.1",
            hostname="198.51.100.1",
            port=22,
            username="username",
            password="password",  # nosec
            platform="cisco_ios",
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname="198.51.100.1",
                    port=22,
                    username="username",
                    password="password",  # nosec
                    platform="platform",
                )
            },
            defaults=Defaults(data={"sync_vlans": False, "sync_vrfs": False}),
        )

    def test_perform_data_extraction_simple_host_values(self):
        self.assertEqual("198.51.100.1", self.host.name)
        self.assertFalse(self.host.data.get("sync_vlans"))
        self.assertFalse(self.host.data.get("sync_vrfs"))

    def test_perform_data_extraction_sync_devices(self):
        actual_result = perform_data_extraction(
            self.host, self.platform_parsing_info["sync_devices"], self.command_outputs, job_debug=False
        )
        expected_parsed_result = {
            "device_type": "WS-C4948E",
            "hostname": "dummy_rtr",
            "mask_length": 16,
            "mgmt_interface": "Vlan1",
            "serial": "CAT1451S15C",
        }
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_str(self):
        parsed_command_output = ""
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ("", [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_list(self):
        parsed_command_output = []
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ([], [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_dict(self):
        parsed_command_output = {}
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ({}, [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_str_with_iterable(self):
        parsed_command_output = ""
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            False,
        )
        expected_parsed_result = ("", "")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_list_with_iterable(self):
        parsed_command_output = []
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            False,
        )
        expected_parsed_result = ([], {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_dict_with_iterable(self):
        parsed_command_output = {}
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            False,
        )
        expected_parsed_result = ({}, {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_dict_with_iterable(self):
        parsed_command_output = self.command_outputs["show version"]
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"]["commands"][0],
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = (["CAT1451S15C"], "CAT1451S15C")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_json_string(self):
        parsed_command_output = '{"foo": "bar"}'
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ("bar", "bar")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_python_dict(self):
        parsed_command_output = {"foo": "bar"}
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ("bar", "bar")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_non_json_string(self):
        parsed_command_output = "jeff"
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ([], [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_non_json_string_with_iterable(self):
        parsed_command_output = "jeff"
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            False,
        )
        expected_parsed_result = ([], {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_dict(self):
        parsed_command_output = [{"foo": {"bar": "moo"}}]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            False,
        )
        expected_parsed_result = ([{"bar": "moo"}], {"bar": "moo"})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_string(self):
        parsed_command_output = ["foo"]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*]",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            False,
        )
        expected_parsed_result = (["foo"], "foo")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_default_iterable(self):
        parsed_command_output = [{"foo": {"bar": "moo"}}]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].foo",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            False,
        )
        expected_parsed_result = ([{"bar": "moo"}], [{"bar": "moo"}])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_sync_network_no_vlans_no_vrfs(self):
        actual_result = perform_data_extraction(
            self.host, self.platform_parsing_info["sync_network_data"], self.command_outputs, job_debug=False
        )
        expected_parsed_result = {
            "serial": "CAT1451S15C",
            "interfaces": {
                "GigabitEthernet0/0": {
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "mac_address": "fa16.3e57.336f",
                    "mtu": "1500",
                    "description": "",
                    "link_status": "False",
                    "802.1Q_mode": "",
                    "lag": [],
                    "type": "other",
                },
                "GigabitEthernet0/1": {
                    "802.1Q_mode": "tagged-all",
                    "description": "to iosvl2-2",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel1",
                    "link_status": "True",
                    "mac_address": "fa16.3e4f.41cc",
                    "mtu": "1500",
                    "type": "other",
                },
                "GigabitEthernet0/2": {
                    "802.1Q_mode": "access",
                    "description": ["to iosvl2-4", "Port"],
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}, {"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel1",
                    "link_status": "True",
                    "mac_address": ["fa16.3ea3.3e49", "78da.6eaf.3b82"],
                    "mtu": ["1500", "1500"],
                    "type": "other",
                },
                "GigabitEthernet0/3": {
                    "802.1Q_mode": "",
                    "description": "to iosvl2-3",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "fa16.3e31.2c47",
                    "mtu": "1500",
                    "type": "other",
                },
                "GigabitEthernet1/0": {
                    "802.1Q_mode": "",
                    "description": "to iosvl2-3",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel3",
                    "link_status": "True",
                    "mac_address": "fa16.3ec8.50ab",
                    "mtu": "1500",
                    "type": "other",
                },
                "Loopback0": {
                    "802.1Q_mode": "",
                    "description": "Loopback",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "",
                    "mtu": "1514",
                    "type": "other",
                },
                "Port-channel1": {
                    "802.1Q_mode": "",
                    "description": "",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "False",
                    "mac_address": "fa16.3e4f.41cc",
                    "mtu": "1500",
                    "type": "lag",
                },
                "Port-channel3": {
                    "802.1Q_mode": "",
                    "description": "",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "False",
                    "mac_address": "fa16.3e4f.41c2",
                    "mtu": "1500",
                    "type": "lag",
                },
                "Vlan1": {
                    "802.1Q_mode": "",
                    "description": "OOB Management",
                    "ip_addresses": [{"ip_address": "198.51.100.1", "prefix_length": "16"}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "fa16.3e57.8001",
                    "mtu": "1500",
                    "type": "virtual",
                },
            },
        }
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_string_vios(self):
        parsed_command_output = [
            {
                "software_image": "VIOS-ADVENTERPRISEK9-M",
                "version": "15.8(3)M2",
                "release": "fc2",
                "rommon": "Bootstrap",
                "hostname": "rtr-01",
                "uptime": "1 week, 3 days, 16 hours, 11 minutes",
                "uptime_years": "",
                "uptime_weeks": "1",
                "uptime_days": "3",
                "uptime_hours": "16",
                "uptime_minutes": "11",
                "reload_reason": "Unknown reason",
                "running_image": "/vios-adventerprisek9-m",
                "hardware": ["IOSv"],
                "serial": ["991UCMIHG4UAJ1J010CQG"],
                "config_register": "0x0",
                "mac_address": [],
                "restarted": "",
            }
        ]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].serial[]",
            },
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            False,
        )
        expected_parsed_result = (["991UCMIHG4UAJ1J010CQG"], "991UCMIHG4UAJ1J010CQG")
        self.assertEqual(expected_parsed_result, actual_result)


class TestFormatterSyncNetworkData(unittest.TestCase):
    """Tests to ensure formatter is working for sync network data 'ssot job'."""

    def setUp(self):
        with open(f"{MOCK_DIR}/command_mappers/mock_cisco_ios.yml", "r", encoding="utf-8") as parsing_info:
            self.platform_parsing_info = yaml.safe_load(parsing_info)
        with open(f"{MOCK_DIR}/cisco_ios/command_getter_result_1.json", "r", encoding="utf-8") as command_info:
            self.command_outputs = json.loads(command_info.read())
        self.host = Host(
            name="198.51.100.1",
            hostname="198.51.100.1",
            port=22,
            username="username",
            password="password",  # nosec
            platform="cisco_ios",
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname="198.51.100.1",
                    port=22,
                    username="username",
                    password="password",  # nosec
                    platform="platform",
                )
            },
            defaults=Defaults(data={"sync_vlans": True, "sync_vrfs": False}),
        )

    def test_perform_data_extraction_sync_network_data(self):
        actual_result = perform_data_extraction(
            self.host, self.platform_parsing_info["sync_network_data"], self.command_outputs, job_debug=False
        )
        expected_parsed_result = {
            "interfaces": {
                "GigabitEthernet0/0": {
                    "802.1Q_mode": "",
                    "description": "",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "False",
                    "mac_address": "fa16.3e57.336f",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "other",
                    "untagged_vlan": [],
                },
                "GigabitEthernet0/1": {
                    "802.1Q_mode": "tagged-all",
                    "description": "to iosvl2-2",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel1",
                    "link_status": "True",
                    "mac_address": "fa16.3e4f.41cc",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "other",
                    "untagged_vlan": {"id": "1", "name": "default"},
                },
                "GigabitEthernet0/2": {
                    "802.1Q_mode": "access",
                    "description": ["to iosvl2-4", "Port"],
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}, {"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel1",
                    "link_status": "True",
                    "mac_address": ["fa16.3ea3.3e49", "78da.6eaf.3b82"],
                    "mtu": ["1500", "1500"],
                    "tagged_vlans": [{"id": "100", "name": ""}],
                    "type": "other",
                    "untagged_vlan": {"id": "1", "name": "default"},
                },
                "GigabitEthernet0/3": {
                    "802.1Q_mode": "",
                    "description": "to iosvl2-3",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "fa16.3e31.2c47",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "other",
                    "untagged_vlan": [],
                },
                "GigabitEthernet1/0": {
                    "802.1Q_mode": "",
                    "description": "to iosvl2-3",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": "Port-channel3",
                    "link_status": "True",
                    "mac_address": "fa16.3ec8.50ab",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "other",
                    "untagged_vlan": [],
                },
                "Loopback0": {
                    "802.1Q_mode": "",
                    "description": "Loopback",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "",
                    "mtu": "1514",
                    "tagged_vlans": [],
                    "type": "other",
                    "untagged_vlan": [],
                },
                "Port-channel1": {
                    "802.1Q_mode": "",
                    "description": "",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "False",
                    "mac_address": "fa16.3e4f.41cc",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "lag",
                    "untagged_vlan": [],
                },
                "Port-channel3": {
                    "802.1Q_mode": "",
                    "description": "",
                    "ip_addresses": [{"ip_address": "", "prefix_length": ""}],
                    "lag": [],
                    "link_status": "False",
                    "mac_address": "fa16.3e4f.41c2",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "lag",
                    "untagged_vlan": [],
                },
                "Vlan1": {
                    "802.1Q_mode": "",
                    "description": "OOB Management",
                    "ip_addresses": [{"ip_address": "198.51.100.1", "prefix_length": "16"}],
                    "lag": [],
                    "link_status": "True",
                    "mac_address": "fa16.3e57.8001",
                    "mtu": "1500",
                    "tagged_vlans": [],
                    "type": "virtual",
                    "untagged_vlan": [],
                },
            },
            "serial": "CAT1451S15C",
        }
        self.assertEqual(expected_parsed_result, actual_result)
