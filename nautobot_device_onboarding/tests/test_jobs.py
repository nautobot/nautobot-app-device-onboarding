"""Test Jobs."""

from unittest.mock import MagicMock, patch

from nautobot.apps.testing import create_job_result_and_run_job
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, Interface
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import JobLogEntry
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture, sync_network_data_fixture

from nautobot_device_onboarding.tests import utils


class SSOTSyncDevicesTestCase(TransactionTestCase):
    """Test SSOTSyncDevices class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects__jobs_testing()

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_sync_devices__success(self, device_data):
        """Test a successful run of the 'Sync Devices From Network' job"""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_valid

        job_form_inputs = {
            "debug": True,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "10.1.1.10,10.1.1.11",
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
        job_logs = [log.message for log in JobLogEntry.objects.filter(job_result=job_result)]
        print(job_logs)
        print(job_result.result)

        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(2, Device.objects.all().count())
        for returned_device_ip, device_data in device_data.return_value.items():
            device = Device.objects.get(serial=device_data["serial"])
            self.assertEqual(device.name, device_data["hostname"])
            self.assertEqual(device.serial, device_data["serial"])
            self.assertEqual(device.device_type.model, device_data["device_type"])
            self.assertEqual(device.device_type.manufacturer.name, device_data["manufacturer"])
            self.assertEqual(device.platform.name, device_data["platform"])
            self.assertEqual(device.platform.network_driver, device_data["network_driver"])
            self.assertEqual(device.primary_ip.host, returned_device_ip)
            self.assertEqual(device.primary_ip.mask_length, device_data["mask_length"])

            mgmt_interface = Interface.objects.get(device=device, name=device_data["mgmt_interface"])
            self.assertEqual(mgmt_interface.mgmt_only, True)
            self.assertIn(returned_device_ip, list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))


class SSOTSyncNetworkDataTestCase(TransactionTestCase):
    """Test SSOTSyncNetworkData class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters.sync_network_data_command_getter")
    def test_sync_network_data__success(self, device_data):
        """Test a successful run of the 'Sync Network Data From Network' job"""
        device_data.return_value = sync_network_data_fixture.sync_network_mock_data_valid
        devices = ["demo-cisco-xe1", "demo-cisco-xe2"]
        device_ids_to_sync = list(Device.objects.filter(name__in=devices).values_list("id", flat=True))

        job_form_inputs = {
            "debug": True,
            "dryrun": False,
            "sync_vlans": True,
            "sync_vrfs": True,
            "namespace": self.testing_objects["namespace"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "devices": device_ids_to_sync,
            "location": None,
            "device_role": None,
            "platform": None,
            "memory_profiling": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncNetworkData", **job_form_inputs
        )
        job_logs = [log.message for log in JobLogEntry.objects.filter(job_result=job_result)]
        print(job_logs)
        print(job_result.result)

        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        for returned_device_hostname, device_data in device_data.return_value.items():
            device = Device.objects.get(serial=device_data["serial"])
            self.assertEqual(device.name, returned_device_hostname)
            for interface in device.interfaces.all():
                interface_data = device_data["interfaces"][interface.name]
                self.assertEqual(interface.status, self.testing_objects["status"])
                self.assertEqual(interface.type, interface_data["type"])
                self.assertEqual(interface.mac_address, interface_data["mac_address"])
                self.assertEqual(interface.mtu, int(interface_data["mtu"]))
                self.assertEqual(interface.description, interface_data["description"])
                self.assertEqual(interface.enabled, interface_data["link_status"])
                self.assertEqual(interface.mode, interface_data["802.1Q_mode"])

                for ip_address in interface_data["ip_addresses"]:
                    self.assertIn(
                        ip_address["ip_address"], list(interface.ip_addresses.all().values_list("host", flat=True))
                    )

                for tagged_vlan in interface_data["tagged_vlans"]:
                    self.assertIn(
                        int(tagged_vlan["id"]), list(interface.tagged_vlans.all().values_list("vid", flat=True))
                    )

                if interface_data["untagged_vlan"]:
                    self.assertEqual(interface.untagged_vlan.vid, int(interface_data["untagged_vlan"]["id"]))

                if interface_data["vrf"]:
                    self.assertEqual(interface.vrf.name, interface_data["vrf"]["name"])