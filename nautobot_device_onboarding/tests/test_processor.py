"""Tests for the Nornir processors used by the command getter."""

import unittest
from unittest.mock import MagicMock, patch

from nornir.core.task import MultiResult

from nautobot_device_onboarding.nornir_plays.processor import (
    CommandGetterProcessor,
    TroubleshootingProcessor,
)


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


def _result(failed=False, message="", names=()):
    """Build a MultiResult shaped like the one the command getter task produces.

    Index 0 is the parent `netmiko_send_commands` result, which carries no data of its own;
    the remaining entries are one per command.
    """
    multi_result = MultiResult("netmiko_send_commands")
    parent = MagicMock(failed=failed)
    parent.result = message
    multi_result.append(parent)
    for name in names:
        sub = MagicMock()
        sub.name = name
        sub.result = f"{name} output"
        multi_result.append(sub)
    return multi_result


def _host(name="10.0.0.1"):
    host = MagicMock(platform="cisco_ios")
    host.name = name
    return host


@patch("nornir_nautobot.plugins.processors.BaseLoggingProcessor.task_instance_completed")
class TestCommandGetterProcessorCleanup(unittest.TestCase):
    """The base processor must run for every completed task instance.

    It releases the exception frames a failed task pins and reclaims the file descriptors held
    by driver reference cycles. Overriding `task_instance_completed` without calling `super()`
    silently opts out of both, leaking descriptors for the lifetime of the play.
    """

    def _processor(self, data):
        return CommandGetterProcessor(logger=MagicMock(), command_outputs=data, job=MagicMock(debug=False))

    def test_cleanup_runs_on_a_failed_task(self, mock_base):
        host = _host()
        data = {host.name: {"platform": "cisco_ios"}}
        result = _result(failed=True, message="connection refused")

        self._processor(data).task_instance_completed(MagicMock(), host, result)

        mock_base.assert_called_once()
        self.assertTrue(data[host.name]["failed"])

    def test_cleanup_runs_on_the_early_return_path(self, mock_base):
        """A host with no platform returns early, which is still a failed connection."""
        host = _host()
        data = {host.name: {"platform": None}}
        result = _result(failed=True, message="10.0.0.1 has no platform set")

        self._processor(data).task_instance_completed(MagicMock(), host, result)

        mock_base.assert_called_once()
        self.assertNotIn(host.name, data)

    def test_cleanup_runs_even_when_the_body_raises(self, mock_base):
        """Cleanup is in a finally block, so an unexpected error cannot skip it."""
        host = _host()
        result = _result(failed=True, message="connection refused")

        with self.assertRaises(KeyError):
            self._processor({}).task_instance_completed(MagicMock(), host, result)

        mock_base.assert_called_once()


@patch("nornir_nautobot.plugins.processors.BaseLoggingProcessor.task_instance_completed")
class TestTroubleshootingProcessorCleanup(unittest.TestCase):
    """The troubleshooting processor must run the same base cleanup."""

    def test_cleanup_runs_and_command_output_is_collected(self, mock_base):
        data = {}
        result = _result(names=("show version", "show interfaces"))

        TroubleshootingProcessor(command_outputs=data).task_instance_completed(MagicMock(), _host(), result)

        mock_base.assert_called_once()
        self.assertEqual(data, {"show version": "show version output", "show interfaces": "show interfaces output"})
