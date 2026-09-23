"""Test Jobs."""

import os
from pathlib import Path
from unittest.mock import ANY, patch

from django.core.files.base import ContentFile
from django.test import override_settings
from fakenos import FakeNOS
from fakenos.core.host import Host
from nautobot.apps.choices import InterfaceModeChoices
from nautobot.apps.jobs import Job as JobClass
from nautobot.apps.testing import create_job_result_and_run_job
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, Interface, Manufacturer, Platform
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import FileProxy
from nautobot.ipam.models import VLAN, VRF

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
            "device_tenant": self.testing_objects["device_tenant_1"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
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
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_tenant"], self.testing_objects["device_tenant_1"])
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

    def test_additional_parent_fields(self):
        """Test processing of CSV file used for onboarding jobs with additional parent columns."""

        manufacturer, _ = Manufacturer.objects.get_or_create(name="Cisco")
        platform, _ = Platform.objects.get_or_create(
            name="cisco_ios", network_driver="cisco_ios", manufacturer=manufacturer
        )
        onboarding_job = jobs.SSOTSyncDevices()
        with open("nautobot_device_onboarding/tests/fixtures/additional_parent_fields.csv", "rb") as csv_file:
            processed_csv_data = onboarding_job._process_csv_data(csv_file=csv_file)  # pylint: disable=protected-access
        self.assertEqual(processed_csv_data["10.1.1.10"]["location"], self.testing_objects["location_3"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["namespace"], self.testing_objects["namespace"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["port"], 22)
        self.assertEqual(processed_csv_data["10.1.1.10"]["timeout"], 30)
        self.assertEqual(processed_csv_data["10.1.1.10"]["set_mgmt_only"], True)
        self.assertEqual(processed_csv_data["10.1.1.10"]["update_devices_without_primary_ip"], True)
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_role"], self.testing_objects["device_role"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["device_tenant"], self.testing_objects["device_tenant_1"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["interface_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["ip_address_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["secrets_group"], self.testing_objects["secrets_group"])
        self.assertEqual(processed_csv_data["10.1.1.10"]["platform"], platform)

        self.assertEqual(processed_csv_data["10.1.1.11"]["location"], self.testing_objects["location_4"])
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

        self.assertEqual(processed_csv_data["10.1.1.12"]["location"], self.testing_objects["location_1"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["namespace"], self.testing_objects["namespace"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["port"], 22)
        self.assertEqual(processed_csv_data["10.1.1.12"]["timeout"], 30)
        self.assertEqual(processed_csv_data["10.1.1.12"]["set_mgmt_only"], False)
        self.assertEqual(processed_csv_data["10.1.1.12"]["update_devices_without_primary_ip"], False)
        self.assertEqual(processed_csv_data["10.1.1.12"]["device_role"], self.testing_objects["device_role"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["device_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["interface_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["ip_address_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["secrets_group"], self.testing_objects["secrets_group"])
        self.assertEqual(processed_csv_data["10.1.1.12"]["platform"], platform)

        self.assertEqual(processed_csv_data["10.1.1.13"]["location"], self.testing_objects["location_1"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["namespace"], self.testing_objects["namespace"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["port"], 22)
        self.assertEqual(processed_csv_data["10.1.1.13"]["timeout"], 30)
        self.assertEqual(processed_csv_data["10.1.1.13"]["set_mgmt_only"], False)
        self.assertEqual(processed_csv_data["10.1.1.13"]["update_devices_without_primary_ip"], False)
        self.assertEqual(processed_csv_data["10.1.1.13"]["device_role"], self.testing_objects["device_role"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["device_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["interface_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["ip_address_status"], self.testing_objects["status"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["secrets_group"], self.testing_objects["secrets_group"])
        self.assertEqual(processed_csv_data["10.1.1.13"]["platform"], platform)

    def _make_job_with_mock_logger(self, debug):
        """Build an SSOTSyncDevices instance with a patched logger for cache-helper tests."""
        from unittest.mock import MagicMock  # pylint: disable=import-outside-toplevel

        onboarding_job = jobs.SSOTSyncDevices()
        onboarding_job.debug = debug
        onboarding_job.logger = MagicMock()
        return onboarding_job

    def test_cached_get__logs_miss_then_hit_with_safe_kwargs(self):
        """_cached_get emits a miss log, then a hit log with the cached object's pk and str-formatted kwargs."""
        location = self.testing_objects["location_1"]
        parent = location.parent
        onboarding_job = self._make_job_with_mock_logger(debug=True)

        first = onboarding_job._cached_get(jobs.Location, name=location.name, parent=parent)  # pylint: disable=protected-access
        self.assertEqual(first, location)
        self.assertEqual(onboarding_job.logger.debug.call_count, 1)
        miss_msg = onboarding_job.logger.debug.call_args_list[0].args[0]
        self.assertIn("Cache miss for Location.objects.get(", miss_msg)
        self.assertIn(f"name={location.name}", miss_msg)
        self.assertIn(f"parent={parent}", miss_msg)
        self.assertNotIn("<Location:", miss_msg)

        onboarding_job.logger.debug.reset_mock()
        second = onboarding_job._cached_get(jobs.Location, name=location.name, parent=parent)  # pylint: disable=protected-access
        self.assertIs(second, first)
        hit_msg = onboarding_job.logger.debug.call_args_list[0].args[0]
        self.assertIn("Cache hit for Location.objects.get(", hit_msg)
        self.assertIn(f"parent={parent}", hit_msg)
        self.assertIn(str(location.pk), hit_msg)
        self.assertNotIn("<Location:", hit_msg)

    def test_cached_filter_count_and_first__logs_miss_then_hit_with_uuids(self):
        """_cached_filter_count_and_first hit log shows match count and all matched UUIDs."""
        duplicate_name = "Site C (intentional duplicate)"
        onboarding_job = self._make_job_with_mock_logger(debug=True)

        count, first = onboarding_job._cached_filter_count_and_first(jobs.Location, name=duplicate_name)  # pylint: disable=protected-access
        self.assertEqual(count, 2)
        self.assertIsNotNone(first)
        miss_msg = onboarding_job.logger.debug.call_args_list[0].args[0]
        self.assertIn("Cache miss for Location.objects.filter(", miss_msg)
        self.assertIn(f"name={duplicate_name}", miss_msg)

        onboarding_job.logger.debug.reset_mock()
        count, _ = onboarding_job._cached_filter_count_and_first(jobs.Location, name=duplicate_name)  # pylint: disable=protected-access
        self.assertEqual(count, 2)
        hit_msg = onboarding_job.logger.debug.call_args_list[0].args[0]
        self.assertIn("2 match(es)", hit_msg)
        self.assertIn(str(self.testing_objects["location_3"].pk), hit_msg)
        self.assertIn(str(self.testing_objects["location_4"].pk), hit_msg)

    def test_cached_filter_count_and_first__zero_matches_render_as_none_not_empty_list(self):
        """Zero-match filter results render as `[none]`, not `[]`, so the hit log reads clearly."""
        onboarding_job = self._make_job_with_mock_logger(debug=True)

        onboarding_job._cached_filter_count_and_first(jobs.Location, name="does-not-exist")  # pylint: disable=protected-access
        onboarding_job.logger.debug.reset_mock()

        count, first = onboarding_job._cached_filter_count_and_first(jobs.Location, name="does-not-exist")  # pylint: disable=protected-access
        self.assertEqual(count, 0)
        self.assertIsNone(first)
        hit_msg = onboarding_job.logger.debug.call_args_list[0].args[0]
        self.assertIn("0 match(es)", hit_msg)
        self.assertIn("[none]", hit_msg)

    def test_cached_helpers__debug_false_emits_no_log_output(self):
        """When debug=False, neither helper should emit cache-miss or cache-hit debug output."""
        location = self.testing_objects["location_1"]
        onboarding_job = self._make_job_with_mock_logger(debug=False)

        onboarding_job._cached_get(jobs.Location, name=location.name, parent=location.parent)  # pylint: disable=protected-access
        onboarding_job._cached_get(jobs.Location, name=location.name, parent=location.parent)  # pylint: disable=protected-access
        onboarding_job._cached_filter_count_and_first(jobs.Location, name=location.name)  # pylint: disable=protected-access
        onboarding_job._cached_filter_count_and_first(jobs.Location, name=location.name)  # pylint: disable=protected-access
        onboarding_job.logger.debug.assert_not_called()

    def test_cached_helpers__non_location_models_bypass_cache_and_log(self):
        """Non-Location lookups never populate the cache and never emit cache-related debug logs."""
        role = self.testing_objects["device_role"]
        onboarding_job = self._make_job_with_mock_logger(debug=True)

        for _ in range(2):
            onboarding_job._cached_get(jobs.Role, name=role.name)  # pylint: disable=protected-access

        self.assertEqual(onboarding_job._db_cache, {})
        onboarding_job.logger.debug.assert_not_called()

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
            "device_tenant": None,
            "interface_status": None,
            "ip_address_status": None,
            "secrets_group": None,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
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

    def test_add_content_type_during_csv_sync(self):
        """Test successful addition of content type to location type during CSV sync."""
        # Create a location type without Device content type
        location_type_without_device = self.testing_objects["location_2"].location_type
        location_type_without_device.content_types.clear()
        location_type_without_device.validated_save()

        self.assertFalse(location_type_without_device.content_types.filter(app_label="dcim", model="device").exists())

        # Run CSV processing which should add the content type
        onboarding_job = jobs.SSOTSyncDevices()
        with open("nautobot_device_onboarding/tests/fixtures/onboarding_csv_fixture.csv", "rb") as csv_file:
            onboarding_job._process_csv_data(csv_file=csv_file)  # pylint: disable=protected-access

        # Verify content type was added
        location_type_without_device.refresh_from_db()
        self.assertTrue(location_type_without_device.content_types.filter(app_label="dcim", model="device").exists())

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_devices_adapters.sync_devices_command_getter")
    def test_add_content_type_during_manual_sync(self, device_data):
        """Test that content type is added when running manual sync with location."""
        device_data.return_value = sync_devices_fixture.sync_devices_mock_data_valid

        # Create a location type without Device content type
        location_type_without_device = self.testing_objects["location_2"].location_type
        location_type_without_device.content_types.clear()
        location_type_without_device.validated_save()

        self.assertFalse(location_type_without_device.content_types.filter(app_label="dcim", model="device").exists())

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "csv_file": None,
            "location": self.testing_objects["location_2"].pk,
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
        # Verify content type was added
        location_type_without_device.refresh_from_db()
        self.assertTrue(location_type_without_device.content_types.filter(app_label="dcim", model="device").exists())


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
        devices = ["demo-cisco-1", "demo-cisco-2", "demo-cisco-4"]
        device_ids_to_sync = list(Device.objects.filter(name__in=devices).values_list("id", flat=True))

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "sync_vlans": True,
            "sync_vrfs": True,
            "sync_vrf_to_prefix": False,
            "sync_cables": True,
            "sync_software_version": True,
            "update_devices_with_changed_serial": False,
            "namespace": self.testing_objects["namespace"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "devices": device_ids_to_sync,
            "location": None,
            "device_role": None,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
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

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters.sync_network_data_command_getter")
    def test_update_devices_with_changed_serial_toggle__absorbs_serial_drift(self, device_data):
        """With update_devices_with_changed_serial=True, a serial-drifted device's row gets
        its serial updated and its interfaces enriched in a single SND run.

        Counterpart to test_master_role_flip_excludes_device_from_devices_to_load in
        test_sync_network_data_adapters.py (which pins the toggle=False failure mode at the
        adapter level). This test pins the toggle=True success path end-to-end.

        Mechanism (after the trial-branch Delta 2):
          - utils/diffsync_utils.py loosens the queryset filter when the toggle is on, so
            the serial-drifted device makes it into devices_to_load.
          - SyncNetworkDataDevice identity is now (name,) only, so source (name, NEW_SERIAL)
            and target (name, OLD_SERIAL) match on diffsync identity.
          - Diffsync calls update() — `serial` is in _attributes, so the new serial is
            written to the Device row. Interface children process normally.
        """
        drifted_data = {
            "demo-cisco-1": {
                "serial": "MASTER-FLIPPED-SERIAL",
                "interfaces": {
                    "GigabitEthernet99": {
                        "type": "100base-tx",
                        "ip_addresses": [],
                        "mac_address": "aa:bb:cc:dd:ee:ff",
                        "mtu": "1500",
                        "description": "empirical-test-interface",
                        "link_status": True,
                        "802.1Q_mode": "access",
                        "lag": "",
                        "untagged_vlan": None,
                        "tagged_vlans": [],
                        "vrf": None,
                    },
                },
            },
        }
        device_data.return_value = drifted_data

        device_1 = self.testing_objects["device_1"]
        self.assertEqual("9ABUXU581111", device_1.serial)

        job_form_inputs = {
            "debug": True,
            "connectivity_test": False,
            "dryrun": False,
            "sync_vlans": False,
            "sync_vrfs": False,
            "sync_vrf_to_prefix": False,
            "sync_cables": False,
            "sync_software_version": False,
            "update_devices_with_changed_serial": True,
            "namespace": self.testing_objects["namespace"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "devices": [device_1.id],
            "location": None,
            "device_role": None,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
        }
        job_result = create_job_result_and_run_job(
            module="nautobot_device_onboarding.jobs", name="SSOTSyncNetworkData", **job_form_inputs
        )

        log_messages = list(job_result.job_log_entries.values_list("message", flat=True))
        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            (job_result.traceback, log_messages),
        )

        device_1.refresh_from_db()

        # Serial was absorbed by the sync — the drifted value is now stored in Nautobot.
        self.assertEqual("MASTER-FLIPPED-SERIAL", device_1.serial)

        # Interface enrichment proceeded — the new interface was created on the existing row.
        self.assertTrue(
            device_1.interfaces.filter(name="GigabitEthernet99").exists(),
            "GigabitEthernet99 should have been created on demo-cisco-1",
        )

        # No "not included in Nautobot devices selected for syncing" error — diffsync identity
        # matched on hostname alone, so SyncNetworkDataDevice.create() (the no-op error path)
        # was never reached.
        not_included_logs = [m for m in log_messages if "not included" in m]
        self.assertEqual(0, len(not_included_logs), not_included_logs)

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
            "device_tenant": None,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": self.testing_objects["platform_1"].pk,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
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

    # TODO: This should be using override_settings but nautobot-app-nornir isn't accessing the django settings directly
    @patch.dict(
        "nautobot_plugin_nornir.plugins.inventory.nautobot_orm.PLUGIN_CFG",
        connection_options={"netmiko": {"extras": {"fast_cli": False, "read_timeout_override": 30}, "port": 6222}},
    )
    @patch.dict("os.environ", {"DEVICE_USER": "admin", "DEVICE_PASS": "admin"})
    def test_sync_network_data_with_full_ssh_nxos_trunked_vlans(self):
        """Test full nxos device sync and network data sync with VLANs."""
        sync_devices_job_form_inputs = {
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
            "device_tenant": None,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": self.testing_objects["platform_3"].pk,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
        }
        sync_network_data_job_form_inputs = {
            "debug": False,
            "connectivity_test": False,
            "dryrun": False,
            "sync_vlans": True,
            "sync_vrfs": True,
            "sync_vrf_to_prefix": False,
            "sync_cables": True,
            "sync_software_version": True,
            "update_devices_with_changed_serial": False,
            "namespace": self.testing_objects["namespace"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "location": None,
            "device_role": None,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
        }

        initial_vlans = set(VLAN.objects.values_list("vid", flat=True))

        fakenos_inventory = {
            "hosts": {
                "fake-nxos-01": {
                    "username": "admin",
                    "password": "admin",
                    "platform": "nexustest",
                    "port": 6222,
                }
            }
        }

        # This is hacky, theres clearly a bug in the fakenos library
        # https://github.com/fakenos/fakenos/issues/19
        with patch.object(Host, "_check_if_platform_is_supported"):
            with FakeNOS(
                inventory=fakenos_inventory,
                plugins=[str(Path(__file__).parent.joinpath("fakenos/nxos.yaml").resolve())],
            ):
                create_job_result_and_run_job(
                    module="nautobot_device_onboarding.jobs",
                    name="SSOTSyncDevices",
                    **sync_devices_job_form_inputs,
                )
                sync_network_data_job_form_inputs["devices"] = Device.objects.filter(name="fake-nxos-01")
                create_job_result_and_run_job(
                    module="nautobot_device_onboarding.jobs",
                    name="SSOTSyncNetworkData",
                    **sync_network_data_job_form_inputs,
                )

        device_obj = Device.objects.filter(name="fake-nxos-01").first()

        # Ethernet1/60 mode should be tagged with no tagged_vlans -- switchport trunk allowed vlan none
        eth1_60 = device_obj.interfaces.filter(name="Ethernet1/60").first()
        self.assertIsNotNone(eth1_60)
        self.assertEqual(eth1_60.mode, InterfaceModeChoices.MODE_TAGGED)
        self.assertFalse(eth1_60.tagged_vlans.exists())
        self.assertEqual(eth1_60.untagged_vlan.vid, 1)

        # Ethernet1/61 mode should be tagged-all  -- switchport trunk allowed vlan all
        eth1_61 = device_obj.interfaces.filter(name="Ethernet1/61").first()
        self.assertIsNotNone(eth1_61)
        self.assertEqual(eth1_61.mode, InterfaceModeChoices.MODE_TAGGED_ALL)
        self.assertFalse(eth1_61.tagged_vlans.exists())
        self.assertEqual(eth1_61.untagged_vlan.vid, 1)

        # VLANS 10 and 20 should be created for Ethernet1/62 -- switchport trunk allowed vlan 10,20
        eth1_62 = device_obj.interfaces.filter(name="Ethernet1/62").first()
        self.assertIsNotNone(eth1_62)
        self.assertEqual(eth1_62.mode, InterfaceModeChoices.MODE_TAGGED)
        self.assertSequenceEqual(eth1_62.tagged_vlans.values_list("vid", flat=True), [10, 20])
        self.assertEqual(eth1_62.untagged_vlan.vid, 1)

        # VLANS 100-120 should be created for Ethernet1/63 -- switchport trunk allowed vlan 100-120
        eth1_63 = device_obj.interfaces.filter(name="Ethernet1/63").first()
        self.assertIsNotNone(eth1_63)
        self.assertEqual(eth1_63.mode, InterfaceModeChoices.MODE_TAGGED)
        self.assertSequenceEqual(eth1_63.tagged_vlans.values_list("vid", flat=True), range(100, 121))
        self.assertEqual(eth1_63.untagged_vlan.vid, 1)

        self.assertEqual(
            initial_vlans.union({1, 10, 20, *range(100, 121)}),
            set(VLAN.objects.values_list("vid", flat=True)),
        )

    # TODO: This should be using override_settings but nautobot-app-nornir isn't accessing the django settings directly
    @patch.dict(
        "nautobot_plugin_nornir.plugins.inventory.nautobot_orm.PLUGIN_CFG",
        connection_options={"netmiko": {"extras": {"fast_cli": False, "read_timeout_override": 30}, "port": 6222}},
    )
    @patch.dict("os.environ", {"DEVICE_USER": "admin", "DEVICE_PASS": "admin"})
    def test_sync_network_data_with_full_ssh_cisco_xe_vrfs(self):
        """Test full cisco xe device sync and network data sync with VRFs."""
        sync_devices_job_form_inputs = {
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
            "device_tenant": None,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "secrets_group": self.testing_objects["secrets_group"].pk,
            "platform": self.testing_objects["platform_2"].pk,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
        }
        sync_network_data_job_form_inputs = {
            "debug": False,
            "connectivity_test": False,
            "dryrun": False,
            "sync_vlans": True,
            "sync_vrfs": True,
            "sync_vrf_to_prefix": False,
            "sync_cables": False,
            "sync_software_version": True,
            "update_devices_with_changed_serial": False,
            "namespace": self.testing_objects["namespace"].pk,
            "interface_status": self.testing_objects["status"].pk,
            "ip_address_status": self.testing_objects["status"].pk,
            "default_prefix_status": self.testing_objects["status"].pk,
            "location": None,
            "device_role": None,
            "platform": None,
            "memory_profiling": False,
            "fail_job_on_task_failure": False,
        }

        initial_vrfs = set(VRF.objects.values_list("name", flat=True))

        fakenos_inventory = {
            "hosts": {
                "fake-xe-01": {
                    "username": "admin",
                    "password": "admin",
                    "platform": "xetest",
                    "port": 6222,
                }
            }
        }

        # This is hacky, theres clearly a bug in the fakenos library
        # https://github.com/fakenos/fakenos/issues/19
        with patch.object(Host, "_check_if_platform_is_supported"):
            with FakeNOS(
                inventory=fakenos_inventory,
                plugins=[str(Path(__file__).parent.joinpath("fakenos/xe_vrfs.yaml").resolve())],
            ):
                create_job_result_and_run_job(
                    module="nautobot_device_onboarding.jobs",
                    name="SSOTSyncDevices",
                    **sync_devices_job_form_inputs,
                )
                sync_network_data_job_form_inputs["devices"] = Device.objects.filter(name="fake-xe-01")
                create_job_result_and_run_job(
                    module="nautobot_device_onboarding.jobs",
                    name="SSOTSyncNetworkData",
                    **sync_network_data_job_form_inputs,
                )
        device_obj = Device.objects.filter(name="fake-xe-01").first()

        # GigabitEthernet0/0/0 should have no VRF
        gi0_0_0 = device_obj.interfaces.filter(name="GigabitEthernet0/0/0").first()
        self.assertIsNotNone(gi0_0_0)
        self.assertIsNone(gi0_0_0.vrf)

        # GigabitEthernet0/0/1 should be in VRF "Mgmt-vrf"
        gi0_0_1 = device_obj.interfaces.filter(name="GigabitEthernet0/0/1").first()
        self.assertIsNotNone(gi0_0_1)
        self.assertIsNotNone(gi0_0_1.vrf)
        self.assertEqual(gi0_0_1.vrf.name, "Mgmt-vrf")

        # VirtualPortGroup4 should be in VRF "10" This also validates that the addl_reverse_map for VirtualPortGroup to Vi is working.
        vi4 = device_obj.interfaces.filter(name="VirtualPortGroup4").first()
        self.assertIsNotNone(vi4)
        self.assertIsNotNone(vi4.vrf)
        self.assertEqual(vi4.vrf.name, "10")

        po1 = device_obj.interfaces.filter(name="Port-channel1").first()
        self.assertIsNotNone(po1)

        po1_91 = device_obj.interfaces.filter(name="Port-channel1.91").first()
        self.assertIsNotNone(po1_91)
        self.assertIsNotNone(po1_91.vrf)
        self.assertEqual(po1_91.vrf.name, "91")

        self.assertEqual(initial_vrfs.union({"Mgmt-vrf", "10", "91"}), set(VRF.objects.values_list("name", flat=True)))
