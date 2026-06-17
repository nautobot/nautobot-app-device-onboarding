"""Test Cisco Support adapter."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from diffsync.exceptions import ObjectNotFound
from nautobot.apps.choices import InterfaceTypeChoices
from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer, Platform, VirtualChassis
from nautobot.extras.models import JobResult
from nautobot.ipam.choices import PrefixTypeChoices
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Prefix

from nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters import (
    SyncDevicesNautobotAdapter,
    SyncDevicesNetworkAdapter,
)
from nautobot_device_onboarding.jobs import SSOTSyncDevices
from nautobot_device_onboarding.nornir_plays.command_getter import sync_devices_command_getter
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture


class SyncDevicesNetworkAdapterTestCase(TransactionTestCase):
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

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "device_tenant": self.testing_objects["device_tenant_1"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.10": processed_ip_address_attrs,
            "10.1.1.11": processed_ip_address_attrs,
        }

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

    @patch("nautobot_device_onboarding.nornir_plays.command_getter.InitNornir")
    def test_command_getter_raises_when_fail_job_on_task_failure_true(self, init_nornir):
        self.job.fail_job_on_task_failure = True

        nornir_obj = MagicMock()
        nr_with_processors = MagicMock()
        nornir_obj.with_processors.return_value = nr_with_processors

        nr_with_processors.run.return_value = SimpleNamespace(
            failed=True,
            failed_hosts={"1.1.1.1": "DEVICE01"},
        )

        init_nornir.return_value.__enter__.return_value = nornir_obj

        with self.assertRaises(RuntimeError):
            sync_devices_command_getter(job=self.job, log_level="INFO")

    @patch("nautobot_device_onboarding.nornir_plays.command_getter.InitNornir")
    def test_command_getter_does_not_raise_when_fail_job_on_task_failure_false(self, init_nornir):
        self.job.fail_job_on_task_failure = False

        nornir_obj = MagicMock()
        nr_with_processors = MagicMock()
        nornir_obj.with_processors.return_value = nr_with_processors

        nr_with_processors.run.return_value = SimpleNamespace(
            failed=True,
            failed_hosts={"1.1.1.1": "DEVICE01"},
        )

        init_nornir.return_value.__enter__.return_value = nornir_obj

        result = sync_devices_command_getter(job=self.job, log_level="INFO")
        self.assertEqual(result, {})

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_respects_form_supplied_platform_manufacturer(self, device_data):
        """When the job form supplies a Platform, its Manufacturer.name wins over the processor-derived value."""
        palo_mfr, _ = Manufacturer.objects.get_or_create(name="Palo Alto")
        palo_platform, _ = Platform.objects.get_or_create(
            name="Palo Alto PanOS",
            defaults={"manufacturer": palo_mfr, "network_driver": "paloalto_panos"},
        )
        device_data.return_value = {
            "10.1.1.50": {
                "hostname": "palo-fw-1",
                "serial": "SN-PALO-001",
                "device_type": "PA-220",
                "mgmt_interface": "management",
                "manufacturer": "Paloalto",
                "platform": "paloalto_panos",
                "network_driver": "paloalto_panos",
                "mask_length": 24,
            },
        }

        self.job.debug = True
        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "device_tenant": self.testing_objects["device_tenant_1"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "set_mgmt_only": False,
            "platform": palo_platform,
        }
        self.job.ip_address_inventory = {"10.1.1.50": processed_ip_address_attrs}

        self.sync_devices_adapter.load()

        self.assertTrue(self.sync_devices_adapter.get("manufacturer", "Palo Alto"))
        with self.assertRaises(ObjectNotFound):
            self.sync_devices_adapter.get("manufacturer", "Paloalto")

        diff_platform = self.sync_devices_adapter.get("platform", "Palo Alto PanOS")
        self.assertEqual(diff_platform.manufacturer__name, "Palo Alto")

        diff_device_type = self.sync_devices_adapter.get("device_type", "PA-220__Palo Alto")
        self.assertEqual(diff_device_type.manufacturer__name, "Palo Alto")


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
        self.job.ip_address_inventory = {"10.1.1.10": {}, "10.1.1.11": {}, "192.1.1.10": {}}
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]
        self.job.port = 22
        self.job.timeout = 30
        self.job.update_devices_without_primary_ip = True
        self.job.device_role = self.testing_objects["device_role"]
        self.job.device_status = self.testing_objects["status"]
        self.job.device_tenant = self.testing_objects["device_tenant_1"]
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

        for device in Device.objects.filter(primary_ip4__host__in=list(self.job.ip_address_inventory)):
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
            unique_id = f"{device.location.name}__{device.name}"
            diffsync_obj = self.sync_devices_adapter.get("device", unique_id)


class SyncDevicesNetworkAdapterVirtualChassisTestCase(TransactionTestCase):
    """Test SyncDevicesNetworkAdapter class with Virtual Chassis / Switch Stack data."""

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
    def test_load_virtual_chassis(self, device_data):
        """Test loading virtual chassis / switch stack data into the diffsync store."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_virtual_chassis

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.20": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        # Verify the master device was loaded
        master_unique_id = f"{self.testing_objects['location'].name}__stack-switch-1__STACK001"
        diffsync_master = self.sync_devices_adapter.get("device", master_unique_id)
        self.assertEqual("stack-switch-1", diffsync_master.name)
        self.assertEqual("C9300-48P", diffsync_master.device_type__model)
        self.assertEqual("STACK001", diffsync_master.serial)
        self.assertEqual("10.1.1.20", diffsync_master.primary_ip4__host)
        self.assertEqual("stack-switch-1", diffsync_master.virtual_chassis__name)
        self.assertEqual(1, diffsync_master.vc_position)
        self.assertEqual(15, diffsync_master.vc_priority)

        # Verify member 2 was loaded
        member2_unique_id = f"{self.testing_objects['location'].name}__stack-switch-1:2__STACK002"
        diffsync_member2 = self.sync_devices_adapter.get("device", member2_unique_id)
        self.assertEqual("stack-switch-1:2", diffsync_member2.name)
        self.assertEqual("C9300-24P", diffsync_member2.device_type__model)
        self.assertEqual("STACK002", diffsync_member2.serial)
        self.assertEqual("stack-switch-1", diffsync_member2.virtual_chassis__name)
        self.assertEqual(2, diffsync_member2.vc_position)
        self.assertEqual(14, diffsync_member2.vc_priority)

        # Verify member 3 was loaded
        member3_unique_id = f"{self.testing_objects['location'].name}__stack-switch-1:3__STACK003"
        diffsync_member3 = self.sync_devices_adapter.get("device", member3_unique_id)
        self.assertEqual("stack-switch-1:3", diffsync_member3.name)
        self.assertEqual("C9300-48P", diffsync_member3.device_type__model)
        self.assertEqual("STACK003", diffsync_member3.serial)
        self.assertEqual("stack-switch-1", diffsync_member3.virtual_chassis__name)
        self.assertEqual(3, diffsync_member3.vc_position)
        self.assertEqual(1, diffsync_member3.vc_priority)

        # Verify the virtual chassis object was loaded
        vc_unique_id = "stack-switch-1"
        diffsync_vc = self.sync_devices_adapter.get("virtual_chassis", vc_unique_id)
        self.assertEqual("stack-switch-1", diffsync_vc.name)
        self.assertEqual("stack-switch-1", diffsync_vc.master__name)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_standalone_device(self, device_data):
        """Test loading a standalone device (single member stack) into the diffsync store."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_standalone

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.21": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        # Verify the standalone device was loaded as a regular device (not as virtual chassis)
        device_unique_id = f"{self.testing_objects['location'].name}__standalone-switch-1__STANDALONE001"
        diffsync_device = self.sync_devices_adapter.get("device", device_unique_id)
        self.assertEqual("standalone-switch-1", diffsync_device.name)
        self.assertEqual("C9300-48P", diffsync_device.device_type__model)
        self.assertEqual("STANDALONE001", diffsync_device.serial)
        self.assertEqual("10.1.1.21", diffsync_device.primary_ip4__host)
        # Standalone device should not have virtual_chassis set
        self.assertIsNone(diffsync_device.virtual_chassis__name)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_vc_master_not_first_in_list(self, device_data):
        """Test that the master is identified by serial match, not list position."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_master_not_first

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.40": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        # The master (conductor) is switch 2 (serial CONDUCTOR002), NOT switch 1
        # It should get the hostname and primary IP
        master_uid = f"{self.testing_objects['location'].name}__vsf-stack-1__CONDUCTOR002"
        diffsync_master = self.sync_devices_adapter.get("device", master_uid)
        self.assertEqual("vsf-stack-1", diffsync_master.name)
        self.assertEqual("C9300-24P", diffsync_master.device_type__model)
        self.assertEqual("CONDUCTOR002", diffsync_master.serial)
        self.assertEqual("10.1.1.40", diffsync_master.primary_ip4__host)
        self.assertEqual("vsf-stack-1", diffsync_master.virtual_chassis__name)
        self.assertEqual(2, diffsync_master.vc_position)
        self.assertEqual(15, diffsync_master.vc_priority)

        # Switch 1 (standby) should be a member, named by its switch number
        member1_uid = f"{self.testing_objects['location'].name}__vsf-stack-1:1__STANDBY001"
        diffsync_member1 = self.sync_devices_adapter.get("device", member1_uid)
        self.assertEqual("vsf-stack-1:1", diffsync_member1.name)
        self.assertEqual("C9300-48P", diffsync_member1.device_type__model)
        self.assertEqual("STANDBY001", diffsync_member1.serial)
        self.assertEqual(1, diffsync_member1.vc_position)

        # Switch 3 should be a member
        member3_uid = f"{self.testing_objects['location'].name}__vsf-stack-1:3__MEMBER003"
        diffsync_member3 = self.sync_devices_adapter.get("device", member3_uid)
        self.assertEqual("vsf-stack-1:3", diffsync_member3.name)
        self.assertEqual("MEMBER003", diffsync_member3.serial)
        self.assertEqual(3, diffsync_member3.vc_position)

        # VC master__name should point to the hostname (the conductor)
        diffsync_vc = self.sync_devices_adapter.get("virtual_chassis", "vsf-stack-1")
        self.assertEqual("vsf-stack-1", diffsync_vc.master__name)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_vc_missing_modules_data(self, device_data):
        """Test that a VC with non-list modules data is added to the failed list."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_missing_modules

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.30": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        self.assertIn("10.1.1.30", self.sync_devices_adapter.failed_ip_addresses)
        with self.assertRaises(ObjectNotFound):
            self.sync_devices_adapter.get("device", f"{self.testing_objects['location'].name}__bad-stack-1")

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_vc_single_module_treated_as_standalone(self, device_data):
        """Test that a VC with many provisioned slots but only 1 physical module is treated as standalone."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_mismatched_modules

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.31": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        # Should be loaded as a standalone device, not failed
        self.assertNotIn("10.1.1.31", self.sync_devices_adapter.failed_ip_addresses)
        device_uid = f"{self.testing_objects['location'].name}__bad-stack-2__BADSTACK002"
        diffsync_device = self.sync_devices_adapter.get("device", device_uid)
        self.assertEqual("bad-stack-2", diffsync_device.name)
        self.assertEqual("BADSTACK002", diffsync_device.serial)
        self.assertIsNone(diffsync_device.virtual_chassis__name)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_vc_invalid_member_keys(self, device_data):
        """Test that a VC with missing keys in member data is added to the failed list."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_invalid_member_keys

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.32": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        self.assertIn("10.1.1.32", self.sync_devices_adapter.failed_ip_addresses)
        with self.assertRaises(ObjectNotFound):
            self.sync_devices_adapter.get("device", f"{self.testing_objects['location'].name}__bad-stack-3")

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_load_vc_invalid_module_data(self, device_data):
        """Test that a VC with a non-dict module entry is added to the failed list."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_invalid_module_data

        self.job.debug = True

        processed_ip_address_attrs = {
            "location": self.testing_objects["location"],
            "namespace": self.testing_objects["namespace"],
            "port": 22,
            "timeout": 30,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"],
            "device_status": self.testing_objects["status"],
            "interface_status": self.testing_objects["status"],
            "ip_address_status": self.testing_objects["status"],
            "secrets_group": self.testing_objects["secrets_group"],
            "device_tenant": None,
            "platform": None,
        }
        self.job.ip_address_inventory = {
            "10.1.1.33": processed_ip_address_attrs,
        }

        self.sync_devices_adapter.load()

        self.assertIn("10.1.1.33", self.sync_devices_adapter.failed_ip_addresses)
        with self.assertRaises(ObjectNotFound):
            self.sync_devices_adapter.get("device", f"{self.testing_objects['location'].name}__bad-stack-4")


class SyncDevicesNautobotAdapterVirtualChassisTestCase(TransactionTestCase):
    """Test SyncDevicesNautobotAdapter loading of existing Virtual Chassis data from Nautobot."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.sync_devices_adapter = SyncDevicesNautobotAdapter(job=self.job, sync=None)
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects()

    def test_load_existing_virtual_chassis(self):
        """Test that the Nautobot adapter loads existing VC devices and VC object from the DB."""
        self.job.debug = True

        # Create a Virtual Chassis with a master and one member in Nautobot
        vc = VirtualChassis.objects.create(name="existing-vc")
        master_device = Device.objects.create(
            name="vc-master",
            serial="VCMASTER001",
            device_type=self.testing_objects["device_type"],
            status=self.testing_objects["status"],
            location=self.testing_objects["location"],
            role=self.testing_objects["device_role"],
            platform=self.testing_objects["platform"],
            secrets_group=self.testing_objects["secrets_group"],
            virtual_chassis=vc,
            vc_position=1,
            vc_priority=15,
        )
        vc.master = master_device
        vc.validated_save()

        Device.objects.create(
            name="vc-member-2",
            serial="VCMEMBER002",
            device_type=self.testing_objects["device_type"],
            status=self.testing_objects["status"],
            location=self.testing_objects["location"],
            role=self.testing_objects["device_role"],
            platform=self.testing_objects["platform"],
            virtual_chassis=vc,
            vc_position=2,
            vc_priority=14,
        )

        # Assign a primary IP to the master so it's picked up by load_devices

        Prefix.objects.get_or_create(
            prefix="10.99.99.0/24",
            namespace=self.testing_objects["namespace"],
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=self.testing_objects["status"],
        )
        ip_address, _ = IPAddress.objects.get_or_create(
            host="10.99.99.1", mask_length=24, type="host", status=self.testing_objects["status"]
        )
        interface, _ = Interface.objects.get_or_create(
            device=master_device,
            name="Vlan1",
            status=self.testing_objects["status"],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )
        IPAddressToInterface.objects.get_or_create(interface=interface, ip_address=ip_address)
        master_device.primary_ip4 = ip_address
        master_device.validated_save()

        self.job.ip_address_inventory = {"10.99.99.1": {}}
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]

        self.sync_devices_adapter.load()

        # Verify the VC object was loaded
        diffsync_vc = self.sync_devices_adapter.get("virtual_chassis", "existing-vc")
        self.assertEqual("existing-vc", diffsync_vc.name)
        self.assertEqual("vc-master", diffsync_vc.master__name)

        # Verify the master device was loaded with VC attrs
        master_uid = f"{self.testing_objects['location'].name}__vc-master__VCMASTER001"
        diffsync_master = self.sync_devices_adapter.get("device", master_uid)
        self.assertEqual("vc-master", diffsync_master.name)
        self.assertEqual("existing-vc", diffsync_master.virtual_chassis__name)
        self.assertEqual(1, diffsync_master.vc_position)
        self.assertEqual(15, diffsync_master.vc_priority)
        self.assertEqual("10.99.99.1", diffsync_master.primary_ip4__host)

        # Verify the member device was loaded with VC attrs
        member_uid = f"{self.testing_objects['location'].name}__vc-member-2__VCMEMBER002"
        diffsync_member = self.sync_devices_adapter.get("device", member_uid)
        self.assertEqual("vc-member-2", diffsync_member.name)
        self.assertEqual("existing-vc", diffsync_member.virtual_chassis__name)
        self.assertEqual(2, diffsync_member.vc_position)
        self.assertEqual(14, diffsync_member.vc_priority)
        self.assertEqual("VCMEMBER002", diffsync_member.serial)
