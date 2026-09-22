"""Tests for CommandGetterProcessor manufacturer/platform derivation."""

import unittest
from unittest.mock import MagicMock

from nautobot_device_onboarding.nornir_plays.processor import CommandGetterProcessor


class TestManufacturerDerivation(unittest.TestCase):
    """task_instance_started should produce the correct Nautobot Manufacturer display name."""

    def _run(self, platform):
        outputs = {}
        processor = CommandGetterProcessor(logger=MagicMock(), command_outputs=outputs, job=MagicMock(debug=False))
        host = MagicMock(platform=platform)
        host.name = "10.0.0.1"
        processor.task_instance_started(task=MagicMock(), host=host)
        return outputs["10.0.0.1"]

    def test_paloalto_panos_maps_to_palo_alto(self):
        self.assertEqual(self._run("paloalto_panos")["manufacturer"], "Palo Alto")

    def test_juniper_junos_legacy_mapping_preserved(self):
        self.assertEqual(self._run("juniper_junos")["manufacturer"], "Juniper")

    def test_cisco_ios_legacy_mapping_preserved(self):
        self.assertEqual(self._run("cisco_ios")["manufacturer"], "Cisco")

    def test_unknown_token_falls_back_to_split_title(self):
        self.assertEqual(self._run("someNew_vendor")["manufacturer"], "Somenew")

    def test_missing_platform_is_placeholder(self):
        self.assertEqual(self._run(None)["manufacturer"], "PLACEHOLDER")

    def test_platform_string_is_netmiko_token_unchanged(self):
        self.assertEqual(self._run("paloalto_panos")["platform"], "paloalto_panos")
