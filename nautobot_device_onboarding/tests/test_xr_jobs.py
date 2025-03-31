"""Test Jobs."""

from unittest.mock import patch

from django.test import override_settings
from nautobot.apps.testing import create_job_result_and_run_job
from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device
from nautobot.ipam.models import IPAddress

from nautobot_device_onboarding.tests import utils

# The following test case is a functional test of the IOS-XR Device Onboarding App. This Test Case syncs the Initial Device Data.
# This TEST DATA represents 3 variants of the IOS-XRv Virtual Devices, versions 6.5.1, 7.11.1, and 24.3.1
TEST_DATA = [
    {
        "host_address": "192.168.254.130",
        "hostname": "XRv24",
        "serial_number": "D84508AE944",
        "ipv4": "192.168.254.130/24",
    },
    {
        "host_address": "192.168.254.131",
        "hostname": "XRv6.5.1",
        "serial_number": "C42C8A16B8A",
        "ipv4": "192.168.254.131/24",
    },
    {
        "host_address": "192.168.254.133",
        "hostname": "XRv7.11.1",
        "serial_number": "B5ABC78C64B",
        "ipv4": "192.168.254.133/24",
    },
]


class SSOTSyncDevicesXRTestCase(TransactionTestCase):
    """Functional Test of the IOS-XR Device Onboarding App. This Test Case syncs the Initial Device Data"""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_devices_ensure_required_nautobot_objects__jobs_testing()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch.dict("os.environ", {"DEVICE_USER": "admin", "DEVICE_PASS": "cisco@123"})
    def test_sync_network_devices_with_full_ssh(self):
        """Use the TEST DATA to cover SSH connectivity and verify that devices onboard correctly."""
        for device in TEST_DATA:
            job_form_inputs = {
                "debug": True,
                "connectivity_test": False,
                "dryrun": False,
                "csv_file": None,
                "location": self.testing_objects["location_1"].pk,
                "namespace": self.testing_objects["namespace"].pk,
                "ip_addresses": device["host_address"],
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
            create_job_result_and_run_job(
                module="nautobot_device_onboarding.jobs", name="SSOTSyncDevices", **job_form_inputs
            )
            newly_imported_device = Device.objects.get(name=device["hostname"])
            self.assertEqual(str(IPAddress.objects.get(id=newly_imported_device.primary_ip4_id)), device["ipv4"])
            self.assertEqual(newly_imported_device.serial, device["serial_number"])
