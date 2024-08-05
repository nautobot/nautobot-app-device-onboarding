"""Test Cisco Support adapter."""

from unittest.mock import patch

from diffsync.exceptions import ObjectNotFound
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Platform
from nautobot.extras.models import JobResult

from nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters import (
    SyncDevicesNautobotAdapter,
    SyncDevicesNetworkAdapter,
)
from nautobot_device_onboarding.jobs import SSOTSyncDevices
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture


class SyncDevicesNetworkAdapaterTestCase(TransactionTestCase):
    """Test SyncDevicesNetworkAdapter class."""

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
        """Test loading data returned from command getter into the diffsync store."""

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


class SyncDevicesNautobotAdapterTestCase(TransactionTestCase):
    """Test SyncDevicesNautobotAdapter class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Job
        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.sync_devices_adapter = SyncDevicesNautobotAdapter(job=self.job, sync=None)

        # Setup Nautobot Objects
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects()

    def test_load(self):
        """Test loading Nautobot data into the diffsync store."""

        self.job.debug = True
        self.job.ip_addresses = ["10.1.1.10", "10.1.1.11", "192.1.1.10"]
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

        for manufacturer in Manufacturer.objects.all():
            unique_id = manufacturer.name
            diffsync_obj = self.sync_devices_adapter.get("manufacturer", unique_id)
            self.assertEqual(manufacturer.name, diffsync_obj.name)

        for platform in Platform.objects.all():
            unique_id = platform.name
            diffsync_obj = self.sync_devices_adapter.get("platform", unique_id)
            self.assertEqual(platform.name, diffsync_obj.name)
            self.assertEqual(platform.network_driver, diffsync_obj.network_driver)
            self.assertEqual(platform.manufacturer.name, diffsync_obj.manufacturer__name)

        for device_type in DeviceType.objects.all():
            unique_id = f"{device_type.model}__{device_type.manufacturer.name}"
            diffsync_obj = self.sync_devices_adapter.get("device_type", unique_id)
            self.assertEqual(device_type.model, diffsync_obj.model)
            self.assertEqual(device_type.manufacturer.name, diffsync_obj.manufacturer__name)
            self.assertEqual(device_type.part_number, diffsync_obj.part_number)

        for device in Device.objects.filter(primary_ip4__host__in=self.job.ip_addresses):
            unique_id = f"{device.location.name}__{device.name}__{device.serial}"
            diffsync_obj = self.sync_devices_adapter.get("device", unique_id)
            self.assertEqual(device.location.name, diffsync_obj.location__name)
            self.assertEqual(device.name, diffsync_obj.name)
            self.assertEqual(device.serial, diffsync_obj.serial)
            self.assertEqual(device.primary_ip.host, diffsync_obj.primary_ip4__host)
            self.assertEqual(device.primary_ip.status.name, diffsync_obj.primary_ip4__status__name)
            self.assertEqual(device.platform.name, diffsync_obj.platform__name)
            self.assertEqual(device.role.name, diffsync_obj.role__name)
            self.assertEqual(device.secrets_group.name, diffsync_obj.secrets_group__name)
            self.assertEqual(device.status.name, diffsync_obj.status__name)
            self.assertEqual([device.interfaces.all().first().name], diffsync_obj.interfaces)

        with self.assertRaises(ObjectNotFound):
            # Devices with a primary IP that was not entered into the job form
            # should not be included in the sync
            device = self.testing_objects["device_2"]
            unique_id = f"{device.location.name}__{device.name}__{device.serial}"
            diffsync_obj = self.sync_devices_adapter.get("device", unique_id)
