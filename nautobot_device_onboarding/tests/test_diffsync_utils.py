"""Test Cisco Support adapter."""

from unittest.mock import MagicMock

from nautobot.apps.testing import TestCase
from nautobot.ipam.models import IPAddress, Prefix

from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_network_data_fixture
from nautobot_device_onboarding.utils.diffsync_utils import (
    check_data_type,
    generate_device_queryset_from_command_getter_result,
    get_or_create_ip_address,
    get_or_create_prefix,
)


class TestDiffSyncUtils(TestCase):
    """Test Diffsync Utils functions."""

    @classmethod
    def setUpTestData(cls):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects.
        cls.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        cls.command_getter_result = sync_network_data_fixture.sync_network_mock_data_valid
        cls.ip_address_inventory = {
            "10.1.1.10": {
                "location": cls.testing_objects["location"],
                "namespace": cls.testing_objects["namespace"],
                "port": 22,
                "timeout": 30,
                "set_mgmt_only": True,
                "update_devices_without_primary_ip": True,
                "device_role": cls.testing_objects["device_role"],
                "device_status": cls.testing_objects["status"],
                "interface_status": cls.testing_objects["status"],
                "ip_address_status": cls.testing_objects["status"],
                "secrets_group": cls.testing_objects["secrets_group"],
                "platform": cls.testing_objects["platform_1"],
            },
            "10.1.1.11": {
                "location": cls.testing_objects["location"],
                "namespace": cls.testing_objects["namespace"],
                "port": 22,
                "timeout": 30,
                "set_mgmt_only": True,
                "update_devices_without_primary_ip": True,
                "device_role": cls.testing_objects["device_role"],
                "device_status": cls.testing_objects["status"],
                "interface_status": cls.testing_objects["status"],
                "ip_address_status": cls.testing_objects["status"],
                "secrets_group": cls.testing_objects["secrets_group"],
                "platform": cls.testing_objects["platform_2"],
            },
        }
        cls.mock_job = MagicMock()
        cls.mock_job.ip_address_inventory = cls.ip_address_inventory
        cls.testing_objects["location"].name = "Site B"
        cls.mock_job.logger.error.return_value = None
        cls.mock_job.logger.warning.return_value = None

    def test_generate_device_queryset_from_command_getter_result(self):
        """Test generating a queryset from data returned from command getter."""
        queryset, devices_with_errors = generate_device_queryset_from_command_getter_result(
            job=self.mock_job, command_getter_result=self.command_getter_result
        )
        hostnames_list = list(queryset.values_list("name", flat=True))
        self.assertEqual(2, queryset.count())
        self.assertEqual(devices_with_errors, [])
        self.assertIn("demo-cisco-1", hostnames_list)
        self.assertIn("demo-cisco-2", hostnames_list)

    def test_check_data_type(self):
        """Test argument data type is a dict"""
        # test existing prefix
        data_type_check_result = check_data_type(self.command_getter_result)
        self.assertEqual(True, data_type_check_result)

        data_type_check_result = check_data_type("Bad Input")
        self.assertEqual(False, data_type_check_result)

    def test_get_or_create_prefix(self):
        """Test getting a prefix and creating one if necessary."""
        # test existing prefix
        prefix = get_or_create_prefix(
            host="1.1.1.10",
            mask_length="24",
            default_status=self.testing_objects["status"],
            namespace=self.testing_objects["namespace"],
            job=None,
        )
        queryset = Prefix.objects.filter(prefix=f"{prefix.network}/{prefix.prefix_length}")
        self.assertEqual(1, queryset.count())
        with self.assertRaises(Exception):
            # test prefix failure
            get_or_create_prefix(
                host="192.1.1.10",
                mask_length="24",
                default_status="bad_status",
                namespace=self.testing_objects["namespace"],
                job=None,
            )

    def test_get_or_create_ip_address(self):
        """Test getting an ip address and creating one if necessary."""
        ip_address = get_or_create_ip_address(
            host="192.1.1.1",
            mask_length=24,
            namespace=self.testing_objects["namespace"],
            default_ip_status=self.testing_objects["status"],
            default_prefix_status=self.testing_objects["status"],
            job=None,
        )
        prefix_queryset = Prefix.objects.filter(prefix="192.1.1.0/24")
        ip_address_queryset = IPAddress.objects.filter(address=ip_address.address)
        self.assertEqual(1, prefix_queryset.count())
        self.assertEqual(1, ip_address_queryset.count())

        with self.assertRaises(Exception):
            # test ip_address failure
            get_or_create_ip_address(
                host="200.1.1.1",
                mask_length=24,
                namespace=self.testing_objects["namespace"],
                default_ip_status="bad status",
                default_prefix_status=self.testing_objects["status"],
                job=None,
            )
