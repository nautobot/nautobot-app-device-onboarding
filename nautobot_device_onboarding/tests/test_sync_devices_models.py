"""Test Jobs."""

from unittest.mock import patch

from nautobot.apps.testing import create_job_result_and_run_job
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, Interface
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.15",
            "port": 22,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": True,
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
        device = Device.objects.get(serial="test-serial-abc")
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group_alternate"].pk,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        device = Device.objects.get(serial="test-serial-abc")
        mgmt_interface = Interface.objects.get(
            device=device, name=device_data.return_value["192.1.1.10"]["mgmt_interface"]
        )
        self.assertIn("192.1.1.10", list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

        old_mgmt_interface = Interface.objects.get(device=device, name="GigabitEthernet1")
        self.assertNotIn("192.1.1.10", list(old_mgmt_interface.ip_addresses.all().values_list("host", flat=True)))
