"""Test Jobs."""

import os
from unittest.mock import ANY, patch

from django.core.files.base import ContentFile
from django.test import override_settings
from fakenos import FakeNOS
from fakenos.core.host import Host
from nautobot.apps.jobs import Job as JobClass
from nautobot.apps.testing import create_job_result_and_run_job
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, Interface, Manufacturer, Platform
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import FileProxy

from nautobot_device_onboarding import jobs
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_devices_fixture, sync_network_data_fixture


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
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location_1"].pk,
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

        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        self.assertEqual(2, Device.objects.all().count())
        for returned_device_ip, data in device_data.return_value.items():
            device = Device.objects.get(serial=data["serial"])
            self.assertEqual(device.name, data["hostname"])
            self.assertEqual(device.serial, data["serial"])
            self.assertEqual(device.device_type.model, data["device_type"])
            self.assertEqual(device.device_type.manufacturer.name, data["manufacturer"])
            self.assertEqual(device.platform.name, data["platform"])
            self.assertEqual(device.platform.network_driver, data["network_driver"])
            self.assertEqual(device.primary_ip.host, returned_device_ip)
            self.assertEqual(device.primary_ip.mask_length, data["mask_length"])

            mgmt_interface = Interface.objects.get(device=device, name=data["mgmt_interface"])
            self.assertEqual(mgmt_interface.mgmt_only, True)
            self.assertIn(returned_device_ip, list(mgmt_interface.ip_addresses.all().values_list("host", flat=True)))

    def test_process_csv_data(self):
        """Test processing of CSV file used for onboarding jobs."""

        manufacturer, _ = Manufacturer.objects.get_or_create(name="Cisco")
        platform, _ = Platform.objects.get_or_create(
            name="cisco_ios", network_driver="cisco_ios", manufacturer=manufacturer
        )
        onboarding_job = jobs.SSOTSyncDevices()
        with open("nautobot_device_onboarding/tests/fixtures/onboarding_csv_fixture.csv", "rb") as csv_file:
            processed_csv_data = onboarding_job._process_csv_data(csv_file=csv_file)  # pylint: disable=protected-access
        self.assertEqual(processed_csv_data["10.1.1.10"]["location"], self.testing_objects["location_1"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["namespace"], self.testing_objects["namespace"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["port"], 22)
        self.assertEqual(processed_csv_data["10.1.1.10"]["timeout"], 30)
        self.assertEqual(processed_csv_data["10.1.1.10"]["set_mgmt_only"], True)
        self.assertEqual(processed_csv_data["10.1.1.10"]["update_devices_without_primary_ip"], True)
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_role"], self.testing_objects["device_role"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["interface_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["ip_address_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["secrets_group"], self.testing_objects["secrets_group"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["platform"], platform)

        self.assertEqual(processed_csv_data["10.1.1.11"]["location"], self.testing_objects["location_2"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["namespace"], self.testing_objects["namespace"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["port"], 22)
        self.assertEqual(processed_csv_data["10.1.1.11"]["timeout"], 30)
        self.assertEqual(processed_csv_data["10.1.1.11"]["set_mgmt_only"], False)
        self.assertEqual(processed_csv_data["10.1.1.11"]["update_devices_without_primary_ip"], False)
        self.assertEqual(processed_csv_data["10.1.1.11"]["device_role"], self.testing_objects["device_role"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["device_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["interface_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["ip_address_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["secrets_group"], self.testing_objects["secrets_group"])
        self.assertEqual(processed_csv_data["10.1.1.11"]["platform"], platform)

    def test_process_csv_data__bad_file(self):
        """Test error checking of a bad CSV file used for onboarding jobs."""
        manufacturer, _ = Manufacturer.objects.get_or_create(name="Cisco")
        Platform.objects.get_or_create(name="cisco_ios", network_driver="cisco_ios", manufacturer=manufacturer)
        onboarding_job = jobs.SSOTSyncDevices()
        with open("nautobot_device_onboarding/tests/fixtures/onboarding_csv_fixture_bad_data.csv", "rb") as csv_file:
            processed_csv_data = onboarding_job._process_csv_data(csv_file=csv_file)  # pylint: disable=protected-access
        self.assertEqual(processed_csv_data, None)

    def test_process_csv_data__empty_file(self):
        """Test error checking of a bad CSV file used for onboarding jobs."""
        onboarding_job = jobs.SSOTSyncDevices()
        with open("nautobot_device_onboarding/tests/fixtures/onboarding_csv_fixture_empty.csv", "rb") as csv_file:
            processed_csv_data = onboarding_job._process_csv_data(csv_file=csv_file)  # pylint: disable=protected-access
        self.assertEqual(processed_csv_data, None)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    @patch.dict("os.environ", {"DEVICE_USER": "test_user", "DEVICE_PASS": "test_password"})
    def test_csv_process_pass_connectivity_test_flag(self, mock_sync_devices_command_getter):
        """Ensure the 'connectivity_test' option is passed to the command_getter when a CSV is in-play."""
        with open("nautobot_device_onboarding/tests/fixtures/all_required_fields.csv", "rb") as csv_file:
            csv_contents = csv_file.read()

        job_form_inputs = {
            "debug": True,
            "connectivity_test": "AnyWackyValueHere",
            "dryrun": False,
            "csv_file": FileProxy.objects.create(
                name="onboarding.csv", file=ContentFile(csv_contents, name="onboarding.csv")
            ).id,
            "location": None,
            "namespace": None,
            "ip_addresses": None,
            "port": None,
            "timeout": None,
            "set_mgmt_only": None,
            "update_devices_without_primary_ip": None,
            "device_role": None,
            "device_status": None,
            "interface_status": None,
            "ip_address_status": None,
            "secrets_group": None,
            "platform": None,
            "memory_profiling": False,
        }

        create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
        )
        job = mock_sync_devices_command_getter.mock_calls[0].args[0]
        log_level = mock_sync_devices_command_getter.mock_calls[0].args[1]
        self.assertIsInstance(job, JobClass)
        self.assertEqual(job.connectivity_test, "AnyWackyValueHere")
        self.assertEqual(job.debug, True)
        self.assertSequenceEqual(list(job.ip_address_inventory.keys()), ["172.23.0.8"])
        self.assertEqual(job.ip_address_inventory["172.23.0.8"]["port"], 22)
        self.assertEqual(job.ip_address_inventory["172.23.0.8"]["timeout"], 30)
        self.assertEqual(job.ip_address_inventory["172.23.0.8"]["secrets_group"], ANY)
        self.assertEqual(job.ip_address_inventory["172.23.0.8"]["platform"], None)
        self.assertEqual(log_level, 10)


class SSOTSyncNetworkDataTestCase(TransactionTestCase):
    """Test SSOTSyncNetworkData class."""

    databases = ("default", "job_logs")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters.sync_network_data_command_getter")
    def test_sync_network_data__success(self, device_data):
        """Test a successful run of the 'Sync Network Data From Network' job"""
        device_data.return_value = sync_network_data_fixture.sync_network_mock_data_valid
        devices = ["demo-cisco-1", "demo-cisco-2"]
        device_ids_to_sync = list(Device.objects.filter(name__in=devices).values_list("id", flat=True))

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "sync_vlans": True,
            "sync_vrfs": True,
            "sync_cables": True,
            "sync_software_version": True,
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

        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        for returned_device_hostname, data in device_data.return_value.items():
            device = Device.objects.get(serial=data["serial"])
            self.assertEqual(device.name, returned_device_hostname)
            for interface in device.interfaces.all():
                interface_data = data["interfaces"][interface.name]
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

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch.dict("os.environ", {"DEVICE_USER": "admin", "DEVICE_PASS": "admin"})
    def test_sync_network_devices_with_full_ssh(self):
        """Use the fakeNOS library to expand test coverage to cover SSH connectivity."""
        job_form_inputs = {
            "debug": False,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location"].pk,
            "namespace": self.testing_objects["namespace"].pk,
            "ip_addresses": "localhost",
            "port": 6222,
            "timeout": 30,
            "set_mgmt_only": True,
            "update_devices_without_primary_ip": True,
            "device_role": self.testing_objects["device_role"].pk,
            "device_status": self.testing_objects["status"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": self.testing_objects["platform_1"].pk,
            "memory_profiling": False,
        }
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        fake_ios_inventory = {
            "hosts": {
                "dev1": {
                    "username": "admin",
                    "password": "admin",
                    "platform": "tweaked_cisco_ios",
                    "port": 6222,
                }
            }
        }
        # This is hacky, theres clearly a bug in the fakenos library
        # https://github.com/fakenos/fakenos/issues/19
        with patch.object(Host, "_check_if_platform_is_supported"):
            with FakeNOS(
                inventory=fake_ios_inventory, plugins=[os.path.join(current_file_path, "fakenos/custom_ios.yaml")]
            ):
                job_result = create_job_result_and_run_job(
                    module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
                )

        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
        )
        self.assertTrue(job_result.job_log_entries.filter(message=r"[{localhost}] resolved to [{127.0.0.1}]").exists())
        newly_imported_device = Device.objects.get(name="fake-ios-01")
        self.assertEqual(str(newly_imported_device.primary_ip4), "127.0.0.1/32")
        self.assertEqual(newly_imported_device.serial, "991UCMIHG4UAJ1J010CQG")
