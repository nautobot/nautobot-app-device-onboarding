"""Test for single command, extraction, and processing."""

import json
import os
import unittest

import yaml
from nornir.core.inventory import ConnectionOptions, Defaults, Host

from nautobot_device_onboarding.nornir_plays.formatter import extract_and_post_process

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestSingleCommandFormatterExtractAndProcess(unittest.TestCase):
    """Test for single command, extraction, and processing."""

    def setUp(self):
        self.host = Host(
            name="198.51.100.1",
            hostname="198.51.100.1",
            port=22,
            username="username",
            password="password",  # nosec
            platform="not_used_here",
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname="198.51.100.1",
                    port=22,
                    username="username",
                    password="password",  # nosec
                    platform="platform",
                )
            },
            defaults=Defaults(data={"sync_vlans": False, "sync_vrfs": False, "sync_cables": False}),
        )

    def test_extract_and_process_from_directory(self):
        test_dir = f"{MOCK_DIR}/extract_and_process/"
        for subdir in os.listdir(test_dir):
            subdir_path = os.path.join(test_dir, subdir)
            if os.path.isdir(subdir_path):
                with self.subTest(subdir=subdir):
                    with open(
                        os.path.join(subdir_path, "partial_command_mapper.yml"), "r", encoding="utf-8"
                    ) as parsing_info:
                        platform_parsing_info = yaml.safe_load(parsing_info)
                    with open(os.path.join(subdir_path, "command_output"), "r", encoding="utf-8") as command_info:
                        command_outputs = json.loads(command_info.read())
                    with open(os.path.join(subdir_path, "expected_result"), "r", encoding="utf-8") as expected_info:
                        expected_result = json.loads(expected_info.read())

                    _, postpro_result = extract_and_post_process(
                        command_outputs,
                        platform_parsing_info,
                        {"obj": self.host.name, "original_host": self.host.name},
                        None,
                        False,
                    )
                    self.assertEqual(expected_result, postpro_result)
