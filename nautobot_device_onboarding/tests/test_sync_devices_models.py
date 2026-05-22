"""Test Jobs."""

from unittest.mock import patch

from nautobot.apps.testing import TransactionTestCase, create_job_result_and_run_job
from nautobot.dcim.models import Device, Interface, VirtualChassis
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.tenancy.models import Tenant

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

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__standalone_becomes_vc_master__success(self, device_data):
        """A device first onboarded as standalone, then re-onboarded as the master of a stack.

        Proves the change in PR #567: with `serial` as an attribute ( not an identifier ), the
        next sync matches on ( location, name ) and updates the existing Device row — even when
        the network adapter reports a different serial for the same chassis on the second sync
        ( e.g. modules[0].serial vs the chassis-level serial, which the parser pulls from
        different fields and can differ ).

        Under the previous design ( serial in `_identifiers` ), the second sync would have seen
        a new device and called create() — ending up with a duplicate, with the VC-attachment
        logic in update() never reached.
        """
        # First sync: device appears as a single-module ( standalone ) device.
        initial_data = {
            "10.1.1.50": {
                "hostname": "transition-switch",
                "serial": "CHASSIS-SERIAL-A",
                "device_type": "C9300-48P",
                "mgmt_interface": "Vlan1",
                "manufacturer": "Cisco",
                "platform": "cisco_xe",
                "network_driver": "cisco_xe",
                "mask_length": 24,
                "virtual_chassis": [
                    {"switch": "1", "priority": "15"},
                ],
                "modules": [
                    {"model": "C9300-48P", "serial": "CHASSIS-SERIAL-A"},
                ],
            },
        }
        device_data.return_value = initial_data

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.50",
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

        # Capture the pk of the standalone device. This is the row that must persist across the
        # transition — if diffsync calls create() instead of update() on the second sync, the
        # refresh_from_db() below will raise DoesNotExist.
        standalone_device = Device.objects.get(name="transition-switch")
        original_pk = standalone_device.pk
        self.assertIsNone(standalone_device.virtual_chassis)
        self.assertEqual("CHASSIS-SERIAL-A", standalone_device.serial)
        self.assertEqual(1, Device.objects.filter(name="transition-switch").count())

        # Second sync: same IP, same hostname — but now reports as a 3-member stack, and
        # modules[0].serial differs from the chassis-level serial on the first run. This is the
        # parser-field-divergence scenario that motivated moving serial out of the identifiers.
        stack_data = {
            "10.1.1.50": {
                "hostname": "transition-switch",
                "serial": "MODULE-SERIAL-B",
                "device_type": "C9300-48P",
                "mgmt_interface": "Vlan1",
                "manufacturer": "Cisco",
                "platform": "cisco_xe",
                "network_driver": "cisco_xe",
                "mask_length": 24,
                "virtual_chassis": [
                    {"switch": "1", "priority": "15"},
                    {"switch": "2", "priority": "14"},
                    {"switch": "3", "priority": "1"},
                ],
                "modules": [
                    {"model": "C9300-48P", "serial": "MODULE-SERIAL-B"},
                    {"model": "C9300-24P", "serial": "MODULE-SERIAL-C"},
                    {"model": "C9300-48P", "serial": "MODULE-SERIAL-D"},
                ],
            },
        }
        device_data.return_value = stack_data

        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Master Device row from the first sync must still exist with the same pk — proving
        # diffsync called update() ( not delete+create ).
        standalone_device.refresh_from_db()
        self.assertEqual(original_pk, standalone_device.pk)

        # The same row is now the master of a 3-member VirtualChassis.
        vc = VirtualChassis.objects.get(name="transition-switch")
        self.assertEqual(standalone_device, vc.master)
        self.assertEqual(vc, standalone_device.virtual_chassis)
        self.assertEqual(1, standalone_device.vc_position)

        # No duplicate of the original device — only 1 device with the master's name, and
        # 3 devices total in the stack.
        self.assertEqual(1, Device.objects.filter(name="transition-switch").count())
        self.assertEqual(3, Device.objects.filter(virtual_chassis=vc).count())

        # The master Device's serial attribute was updated to reflect modules[0].serial from
        # the second sync.
        self.assertEqual("MODULE-SERIAL-B", standalone_device.serial)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__serial_changes_on_same_name_location__success(self, device_data):
        """Re-onboarding the same ( location, name ) with a different serial updates the row.

        Covers the device-refresh / RMA scenario: a standalone chassis is swapped out for a
        replacement unit. The new unit reports a different serial but is brought up under the
        same hostname and management IP. With `serial` as an attribute, the second sync matches
        the existing Device row on ( location, name ) and updates the serial — no duplicate,
        no delete+create.
        """
        # First sync: standalone device with original serial.
        initial_data = {
            "10.1.1.60": {
                "hostname": "rma-switch",
                "serial": "OLD-SERIAL-001",
                "device_type": "C9300-48P",
                "mgmt_interface": "Vlan1",
                "manufacturer": "Cisco",
                "platform": "cisco_xe",
                "network_driver": "cisco_xe",
                "mask_length": 24,
                "virtual_chassis": [
                    {"switch": "1", "priority": "15"},
                ],
                "modules": [
                    {"model": "C9300-48P", "serial": "OLD-SERIAL-001"},
                ],
            },
        }
        device_data.return_value = initial_data

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.60",
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

        device = Device.objects.get(name="rma-switch")
        original_pk = device.pk
        self.assertEqual("OLD-SERIAL-001", device.serial)
        self.assertEqual(1, Device.objects.filter(name="rma-switch").count())

        # Second sync: same IP, same hostname — replacement unit reports a different serial.
        replaced_data = {
            "10.1.1.60": {
                "hostname": "rma-switch",
                "serial": "NEW-SERIAL-999",
                "device_type": "C9300-48P",
                "mgmt_interface": "Vlan1",
                "manufacturer": "Cisco",
                "platform": "cisco_xe",
                "network_driver": "cisco_xe",
                "mask_length": 24,
                "virtual_chassis": [
                    {"switch": "1", "priority": "15"},
                ],
                "modules": [
                    {"model": "C9300-48P", "serial": "NEW-SERIAL-999"},
                ],
            },
        }
        device_data.return_value = replaced_data

        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )

        # Same row persists across the swap — pk unchanged, only the serial attribute updated.
        device.refresh_from_db()
        self.assertEqual(original_pk, device.pk)
        self.assertEqual("NEW-SERIAL-999", device.serial)
        self.assertEqual(1, Device.objects.filter(name="rma-switch").count())

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_device_update__multi_tenant_same_name_location__job_fails_loudly(self, device_data):
        """Documents the failure mode when two Devices share (name, location) under different tenants.

        Surfaced by David Cates on Slack 2026-05-21. Nautobot's `Device` model only enforces
        uniqueness on `(rack, position, face)` and `(virtual_chassis, vc_position)` —
        `(name, location)` and `(name, location, tenant)` are NOT unique constraints. A
        service-provider scenario where two customers share a physical site can legitimately
        have e.g. Device(name="border-1", location="DC-East", tenant="Customer-A") AND
        Device(name="border-1", location="DC-East", tenant="Customer-B") both exist.

        `SyncDevicesDevice._get_or_create_device()` and `update()` both call
        `Device.objects.get(name=..., location=...)` without a tenant filter, so when a sync
        re-discovers either of these devices the ORM lookup raises MultipleObjectsReturned.
        `update()` wraps the error with a clear "Multiple devices found with name X and
        location Y" message and the job aborts loudly — no silent data corruption, but no
        sync either.

        This is a pre-existing limitation of the app, not a regression of PR #567: the ORM
        lookup ignored tenant under the old serial-as-identifier scheme as well. Pinned
        here so the failure mode is visible in the test suite.
        """
        # device_1 (from the test helper) is "test device 1" at "Site A" with primary_ip4=192.1.1.10.
        # Tag it with tenant_1 to make the multi-tenant scenario concrete.
        self.testing_objects["device_1"].tenant = self.testing_objects["device_tenant_1"]
        self.testing_objects["device_1"].validated_save()

        # Create a second tenant and a colliding Device sharing (name, location) but under it.
        second_tenant = Tenant.objects.create(name="Device Tenant 2")
        Device.objects.create(
            name=self.testing_objects["device_1"].name,
            location=self.testing_objects["device_1"].location,
            tenant=second_tenant,
            device_type=self.testing_objects["device_1"].device_type,
            role=self.testing_objects["device_1"].role,
            status=self.testing_objects["status"],
            serial="COLLISION-SERIAL",
        )

        # Sanity check: two devices now share (name, location).
        self.assertEqual(
            2,
            Device.objects.filter(
                name="test device 1",
                location=self.testing_objects["location"],
            ).count(),
        )

        # Run the sync against the IP that matches device_1. The Nautobot adapter loads
        # device_1 into diffsync; the network-side record matches its (location, name)
        # identifier, so diffsync calls update(); update()'s ORM lookup finds both rows
        # and raises MultipleObjectsReturned.
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

        # The job aborts.
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)

        # The failure message identifies the multi-match condition.
        log_messages = " ".join(job_result.job_log_entries.values_list("message", flat=True))
        traceback = job_result.traceback or ""
        self.assertTrue(
            "Multiple devices" in log_messages
            or "Multiple devices" in traceback
            or "MultipleObjectsReturned" in traceback,
            f"Expected a MultipleObjectsReturned-style failure; got log={log_messages!r} traceback={traceback!r}",
        )

        # No data was mutated — both rows still exist with their tenants intact.
        self.assertEqual(
            2,
            Device.objects.filter(
                name="test device 1",
                location=self.testing_objects["location"],
            ).count(),
        )
