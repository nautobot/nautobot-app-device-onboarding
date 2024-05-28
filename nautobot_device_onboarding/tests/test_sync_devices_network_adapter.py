"""Test Cisco Support adapter."""

import json
from unittest.mock import MagicMock, patch

from nautobot.core.testing import TransactionTestCase
from nautobot.extras.models import JobResult

from nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters import SyncDevicesNetworkAdapter
from nautobot_device_onboarding.diffsync.models.sync_devices_models import SyncDevicesDevice

from nautobot_device_onboarding.jobs import SSOTSyncDevices
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.nornir_plays import command_getter
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture


class TestSyncDevicesNetworkTestCase(TransactionTestCase):
    """Test NautobotSsotCiscoSupportAdapter class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Job
        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.sync_devices_adapter = SyncDevicesNetworkAdapter(job=self.job, sync=None)

        # Setup Nautobot Objects
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects()

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load(self, device_data):
        """Test loading device data returned from command getter."""

        # Mock return from command_getter
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_valid

        self.job.debug = True
        self.job.ip_addresses = ""
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]
        self.job.port = 22
        self.job.timeout = 30
        self.job.update_devices_without_primary_ip = True
        self.job.device_role = self.testing_objects["device_role"]
        self.job.device_status = self.testing_objects["status"]
        self.job.interface_status = self.testing_objects["status"]
        self.job.ip_address_status = self.testing_objects["status"]
        self.job.secrets_group = self.testing_objects["secrets_group"]
        self.job.platform = None

        self.sync_devices_adapter.load()

        returned_device_data = self.sync_devices_adapter.device_data

        for device_ip, data in returned_device_data.items():
            unique_id = f"{self.testing_objects['location'].name}__{data['hostname']}__{data['serial']}"
            diffsync_device = self.sync_devices_adapter.get("device", unique_id)
            self.assertEqual(data["device_type"], diffsync_device.device_type__model)
            self.assertEqual(self.testing_objects["location"].name, diffsync_device.location__name)
            self.assertEqual(data["hostname"], diffsync_device.name)
            self.assertEqual(data["platform"], diffsync_device.platform__name)
            self.assertEqual(device_ip, diffsync_device.primary_ip4__host)
            self.assertEqual(self.testing_objects["status"].name, diffsync_device.primary_ip4__status__name)
            self.assertEqual(self.testing_objects["device_role"].name, diffsync_device.role__name)
            self.assertEqual(self.testing_objects["status"].name, diffsync_device.status__name)
            self.assertEqual(self.testing_objects["secrets_group"].name, diffsync_device.secrets_group__name)
            self.assertEqual([data["mgmt_interface"]], diffsync_device.interfaces)
            self.assertEqual(data["mask_length"], diffsync_device.mask_length)
            self.assertEqual(data["serial"], diffsync_device.serial)
