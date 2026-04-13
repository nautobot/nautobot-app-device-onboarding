"""Test Jobs."""

from unittest.mock import patch

from nautobot.apps.testing import TransactionTestCase, create_job_result_and_run_job
from nautobot.dcim.models import Device, Interface, VirtualChassis
from nautobot.extras.choices import JobResultStatusChoices

from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture


class SyncDevicesDeviceTestCase(TransactionTestCase):
    """Test SyncDevicesDevice class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects()

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__missing_primary_ip__success(self, device_data):
        """Test updating a device that does not have a primary ip with the 'Sync Devices From Network' job"""
        device_data.return_value = sync_devices_fixture.sync_devices_data_update

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.10",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role_backup"].pk,
            "device_status": self.testing_objects["status_planned"].pk,
            "device_tenant": self.testing_objects["device_tenant_1"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group_alternate"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        self.testing_objects["device_1"].primary_ip4 = None  # test existing device with missing primary ip
        self.testing_objects["device_1"].validated_save()
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        device = Device.objects.get(serial="9ABUXU5882222")
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        self.assertEqual(device.primary_ip4.host, "10.1.1.10")
        self.assertEqual(device.name, device_data.return_value["10.1.1.10"]["hostname"])
        self.assertEqual(device.serial, device_data.return_value["10.1.1.10"]["serial"])
        self.assertEqual(device.device_type.model, device_data.return_value["10.1.1.10"]["device_type"])
        self.assertEqual(device.platform.name, device_data.return_value["10.1.1.10"]["platform"])
        self.assertEqual(device.status.name, self.testing_objects["status_planned"].name)
        self.assertEqual(device.role.name, self.testing_objects["device_role_backup"].name)
        self.assertEqual(device.secrets_group.name, self.testing_objects["secrets_group_alternate"].name)

        mgmt_interface = Interface.objects.get(
            device=device, name=device_data.return_value["10.1.1.10"]["mgmt_interface"]
        )
        self.assertIn("10.1.1.10", list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__primary_ip_and_interface__success(self, device_data):
        """Test updating the primary ip and interface name with the 'Sync Devices From Network' job"""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_single_device_valid
        # update returned interface to force this value to be updated
        device_data.return_value["10.1.1.10"]["mgmt_interface"] = "NewInterfaceName"

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.10",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "device_tenant": self.testing_objects["device_tenant_1"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        device = Device.objects.get(serial="test-serial-abc")
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        self.assertEqual(device.name, device_data.return_value["10.1.1.10"]["hostname"])
        self.assertEqual(device.serial, device_data.return_value["10.1.1.10"]["serial"])
        self.assertEqual(device.device_type.model, device_data.return_value["10.1.1.10"]["device_type"])
        self.assertEqual(device.platform.name, device_data.return_value["10.1.1.10"]["platform"])
        self.assertEqual(device.status.name, self.testing_objects["status"].name)
        self.assertEqual(device.role.name, self.testing_objects["device_role"].name)
        self.assertEqual(device.secrets_group.name, self.testing_objects["secrets_group"].name)

        mgmt_interface = Interface.objects.get(
            device=device, name=device_data.return_value["10.1.1.10"]["mgmt_interface"]
        )
        self.assertIn("10.1.1.10", list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__interface_only__success(self, device_data):
        """Test updating only the primary ip of a device with the 'Sync Devices From Network' job"""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_single_device_alternate_valid

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "192.1.1.10",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role_backup"].pk,
            "device_status": self.testing_objects["status_planned"].pk,
            "device_tenant": self.testing_objects["device_tenant_1"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group_alternate"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        device = Device.objects.get(serial="test-serial-abc")
        mgmt_interface = Interface.objects.get(
            device=device, name=device_data.return_value["192.1.1.10"]["mgmt_interface"]
        )
        self.assertIn("192.1.1.10", list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

        old_mgmt_interface = Interface.objects.get(device=device, name="GigabitEthernet1")
        self.assertNotIn("192.1.1.10", list(old_mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_create__virtual_chassis__success(self, device_data):
        """Test creating a virtual chassis / switch stack with the 'Sync Devices From Network' job."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_virtual_chassis

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.20",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": False,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Verify master device was created
        master_device = Device.objects.get(serial="STACK001")
        self.assertEqual("stack-switch-1", master_device.name)
        self.assertEqual("C9300-48P", master_device.device_type.model)
        self.assertEqual("10.1.1.20", master_device.primary_ip4.host)
        self.assertIsNotNone(master_device.virtual_chassis)
        self.assertEqual(1, master_device.vc_position)
        self.assertEqual(15, master_device.vc_priority)

        # Verify virtual chassis was created
        vc = VirtualChassis.objects.get(name="stack-switch-1")
        self.assertEqual(master_device, vc.master)

        # Verify member 2 was created
        member2 = Device.objects.get(serial="STACK002")
        self.assertEqual("stack-switch-1:2", member2.name)
        self.assertEqual("C9300-24P", member2.device_type.model)
        self.assertEqual(vc, member2.virtual_chassis)
        self.assertEqual(2, member2.vc_position)
        self.assertEqual(14, member2.vc_priority)
        self.assertIsNone(member2.secrets_group)  # VC members should not have secrets group

        # Verify member 3 was created
        member3 = Device.objects.get(serial="STACK003")
        self.assertEqual("stack-switch-1:3", member3.name)
        self.assertEqual("C9300-48P", member3.device_type.model)
        self.assertEqual(vc, member3.virtual_chassis)
        self.assertEqual(3, member3.vc_position)
        self.assertEqual(1, member3.vc_priority)
        self.assertIsNone(member3.secrets_group)  # VC members should not have secrets group

        # Verify only master has primary IP
        self.assertIsNone(member2.primary_ip4)
        self.assertIsNone(member3.primary_ip4)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_create__standalone__success(self, device_data):
        """Test creating a standalone device (single member, not a stack) with the 'Sync Devices From Network' job."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_standalone

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.21",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": False,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Verify standalone device was created without virtual chassis
        device = Device.objects.get(serial="STANDALONE001")
        self.assertEqual("standalone-switch-1", device.name)
        self.assertEqual("C9300-48P", device.device_type.model)
        self.assertEqual("10.1.1.21", device.primary_ip4.host)
        self.assertIsNone(device.virtual_chassis)  # Standalone device should not be in a VC
        self.assertIsNone(device.vc_position)
        self.assertIsNone(device.vc_priority)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__virtual_chassis__success(self, device_data):
        """Test updating an existing virtual chassis (e.g. member priority change) with the job."""
        # First, create the VC by running the job
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_virtual_chassis

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.20",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": False,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Verify initial state
        vc = VirtualChassis.objects.get(name="stack-switch-1")
        master_device = Device.objects.get(serial="STACK001")
        self.assertEqual(master_device, vc.master)
        self.assertEqual(15, master_device.vc_priority)
        member2 = Device.objects.get(serial="STACK002")
        self.assertEqual(14, member2.vc_priority)

        # Now run again with updated priorities
        updated_data = {
            "10.1.1.20": {
                "hostname": "stack-switch-1",
                "serial": "STACK001",
                "device_type": "C9300-48P",
                "mgmt_interface": "Vlan1",
                "manufacturer": "Cisco",
                "platform": "cisco_xe",
                "network_driver": "cisco_xe",
                "mask_length": 24,
                "virtual_chassis": [
                    {"switch": "1", "priority": "10"},
                    {"switch": "2", "priority": "5"},
                    {"switch": "3", "priority": "1"},
                ],
                "modules": [
                    {"model": "C9300-48P", "serial": "STACK001"},
                    {"model": "C9300-24P", "serial": "STACK002"},
                    {"model": "C9300-48P", "serial": "STACK003"},
                ],
            },
        }
        device_data.return_value = updated_data

        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Verify priorities were updated
        master_device.refresh_from_db()
        self.assertEqual(10, master_device.vc_priority)
        member2.refresh_from_db()
        self.assertEqual(5, member2.vc_priority)
        member3 = Device.objects.get(serial="STACK003")
        self.assertEqual(1, member3.vc_priority)

        # VC master should still be set correctly
        vc.refresh_from_db()
        self.assertEqual(master_device, vc.master)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_virtual_chassis_create__success(self, device_data):
        """Test that SyncDevicesVirtualChassis.create() creates a VirtualChassis object in Nautobot."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_virtual_chassis

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.20",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": False,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Verify the VirtualChassis object was created in Nautobot
        self.assertTrue(VirtualChassis.objects.filter(name="stack-switch-1").exists())
        vc = VirtualChassis.objects.get(name="stack-switch-1")
        # Master should be set by device creation
        self.assertIsNotNone(vc.master)
        self.assertEqual("stack-switch-1", vc.master.name)
        # All 3 members should be in the VC
        self.assertEqual(3, vc.members.count())

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_create__vc_master_not_first__success(self, device_data):
        """Test that the correct device is set as VC master when the conductor is not at index 0."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_vc_master_not_first

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.40",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": False,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # The conductor (switch 2, serial CONDUCTOR002) should be the master
        conductor = Device.objects.get(serial="CONDUCTOR002")
        self.assertEqual("vsf-stack-1", conductor.name)
        self.assertEqual("C9300-24P", conductor.device_type.model)
        self.assertEqual("10.1.1.40", conductor.primary_ip4.host)
        self.assertEqual(2, conductor.vc_position)
        self.assertEqual(15, conductor.vc_priority)

        # Verify VC master is the conductor, not switch 1
        vc = VirtualChassis.objects.get(name="vsf-stack-1")
        self.assertEqual(conductor, vc.master)

        # Switch 1 (standby) should be a member, not the master
        standby = Device.objects.get(serial="STANDBY001")
        self.assertEqual("vsf-stack-1:1", standby.name)
        self.assertEqual(1, standby.vc_position)
        self.assertIsNone(standby.primary_ip4)  # Only master gets primary IP
        self.assertIsNone(standby.secrets_group)  # Only master gets secrets group

        # Switch 3 should be a member
        member3 = Device.objects.get(serial="MEMBER003")
        self.assertEqual("vsf-stack-1:3", member3.name)
        self.assertEqual(3, member3.vc_position)
        self.assertIsNone(member3.primary_ip4)
        self.assertIsNone(member3.secrets_group)

        # All 3 should be in the VC
        self.assertEqual(3, vc.members.count())
