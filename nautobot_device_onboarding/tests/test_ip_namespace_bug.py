"""Regression test for IPAddressToInterface namespace lookup bug.

Demonstrates that SyncNetworkDataIPAddressToInterface fails during sync when
the same IP host exists in multiple Nautobot namespaces. The nautobot-ssot contrib
NautobotModel.create() resolves the ip_address FK using only the fields present
in _identifiers. Without ip_address__parent__namespace__name in _identifiers, it
queries IPAddress.objects.get(host=...) which returns MultipleObjectsReturned.

Error observed in production:
    Found multiple instances for ip_address with: {'host': '192.168.220.230'}
    No object resulted from sync, will not process child objects.

To run:
    invoke unittest --label nautobot_device_onboarding.tests.test_ip_namespace_bug
"""

from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Device
from nautobot.extras.models import JobResult
from nautobot.ipam.choices import IPAddressTypeChoices, PrefixTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix

from nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters import (
    SyncNetworkDataNautobotAdapter,
)
from nautobot_device_onboarding.jobs import SSOTSyncNetworkData
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_network_data_fixture


class IPAddressToInterfaceNamespaceBugTestCase(TransactionTestCase):
    """Prove that duplicate IPs across namespaces break IPAddressToInterface sync.

    When two IPAddress records share the same host value in different Nautobot
    namespaces, the nautobot-ssot contrib FK resolution fails because it queries
    IPAddress using only {'host': ...} — which is not unique.

    The fix adds ip_address__parent__namespace__name to the model _identifiers
    so the FK resolution query becomes:
        IPAddress.objects.get(host=..., parent__namespace__name=...)
    """

    databases = ("default", "job_logs")

    def setUp(self):
        """Set up test data: standard objects plus a second namespace with duplicate IPs."""
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()

        # Create a second namespace with the same IP hosts as the Global namespace.
        # This is the condition that triggers the bug.
        self.second_namespace, _ = Namespace.objects.get_or_create(name="Secondary")
        second_prefix, _ = Prefix.objects.get_or_create(
            prefix="10.1.1.0/24",
            namespace=self.second_namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=self.testing_objects["status"],
        )
        # Create duplicate IPs in the second namespace — same hosts as in Global
        self.dup_ip_1, _ = IPAddress.objects.get_or_create(
            host="10.1.1.10",
            mask_length=24,
            type=IPAddressTypeChoices.TYPE_HOST,
            status=self.testing_objects["status"],
            parent=second_prefix,
        )
        self.dup_ip_2, _ = IPAddress.objects.get_or_create(
            host="10.1.1.11",
            mask_length=24,
            type=IPAddressTypeChoices.TYPE_HOST,
            status=self.testing_objects["status"],
            parent=second_prefix,
        )

        # Verify duplicate IPs exist
        self.assertGreater(
            IPAddress.objects.filter(host="10.1.1.10").count(),
            1,
            "Test setup error: expected duplicate IP 10.1.1.10 across namespaces",
        )

        # Set up the job and adapters
        self.job = SSOTSyncNetworkData()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.command_getter_result = sync_network_data_fixture.sync_network_mock_data_valid
        self.job.interface_status = self.testing_objects["status"]
        self.job.ip_address_status = self.testing_objects["status"]
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]  # Global
        self.job.sync_vlans = True
        self.job.sync_vrfs = True
        self.job.sync_vrf_to_prefix = False
        self.job.sync_cables = False
        self.job.sync_software_version = True
        self.job.default_prefix_status = self.testing_objects["status"]
        self.job.debug = True
        self.job.devices_to_load = Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2", "demo-cisco-4"])

    def test_nautobot_adapter_loads_ipaddress_to_interface_with_duplicate_ips(self):
        """Loading IPAddressToInterface from Nautobot should succeed with duplicate IPs across namespaces.

        On unpatched code (without ip_address__parent__namespace__name in _identifiers),
        the NautobotAdapter._load_objects call for ipaddress_to_interface fails because
        nautobot-ssot's contrib code resolves FK fields using the identifier field names.

        With only ip_address__host in _identifiers, the FK resolution dict is
        {'host': '10.1.1.10'} and IPAddress.objects.get(**dict) raises
        MultipleObjectsReturned, producing the error:
            "Found multiple instances for ip_address with: {'host': '10.1.1.10'}"

        With the fix (ip_address__parent__namespace__name added to _identifiers),
        the resolution dict becomes {'host': '10.1.1.10', 'parent__namespace__name': 'Global'}
        which uniquely identifies the correct IPAddress.
        """
        adapter = SyncNetworkDataNautobotAdapter(job=self.job, sync=None)

        # This calls NautobotAdapter._load_objects for each top_level model,
        # including ipaddress_to_interface. Without the namespace fix, the
        # ipaddress_to_interface load will fail.
        adapter.load()

        # Verify ipaddress_to_interface objects were loaded successfully
        loaded = adapter.get_all("ipaddress_to_interface")
        self.assertGreater(len(loaded), 0, "Expected at least one IPAddressToInterface loaded")

        # Verify the loaded objects include the namespace field
        for obj in loaded:
            self.assertEqual(
                obj.ip_address__parent__namespace__name,
                "Global",
                "IPAddressToInterface should reference the Global namespace",
            )
