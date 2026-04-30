"""Tests for the diffsync Prefix-to-VRF association model and adapter loaders."""

from unittest import mock

from diffsync import Adapter
from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Interface
from nautobot.extras.models import JobResult
from nautobot.ipam.models import VRF, Prefix

from nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters import (
    SyncNetworkDataNautobotAdapter,
    SyncNetworkDataNetworkAdapter,
)
from nautobot_device_onboarding.diffsync.models.sync_network_data_models import SyncNetworkDataPrefixToVrf
from nautobot_device_onboarding.jobs import SSOTSyncNetworkData
from nautobot_device_onboarding.tests import utils


class _StubAdapter(Adapter):
    """Bare diffsync adapter; the model only reads `adapter.job.logger` from this."""

    prefix_to_vrf = SyncNetworkDataPrefixToVrf
    top_level = ["prefix_to_vrf"]
    type = "stub"

    def __init__(self, *args, job, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job


class _StubJob:
    """Minimal stand-in for the SSOT job, exposing only what create() reads."""

    def __init__(self):
        self.logger = mock.MagicMock()


class PrefixToVrfModelCreateTestCase(TransactionTestCase):
    """Verify SyncNetworkDataPrefixToVrf.create() side effects on the database."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        self.namespace = self.testing_objects["namespace"]
        self.prefix = Prefix.objects.get(prefix="10.1.1.0/24", namespace=self.namespace)
        self.vrf = VRF.objects.get(name="mgmt", namespace=self.namespace)
        self.other_vrf = VRF.objects.get(name="vrf2", namespace=self.namespace)
        self.adapter = _StubAdapter(job=_StubJob())

    def _ids(self, prefix="10.1.1.0/24", vrf_name="mgmt"):
        return {
            "namespace__name": self.namespace.name,
            "prefix": prefix,
            "vrf__name": vrf_name,
        }

    def test_create_adds_prefix_vrf_link(self):
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_create_is_idempotent(self):
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertEqual(self.prefix.vrfs.filter(pk=self.vrf.pk).count(), 1)

    def test_create_preserves_other_vrf_associations(self):
        """Additive contract: pre-existing VRF links must not be dropped when adding a new one."""
        self.prefix.vrfs.add(self.other_vrf)
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertTrue(self.prefix.vrfs.filter(pk=self.other_vrf.pk).exists())
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())


class PrefixToVrfNetworkAdapterTestCase(TransactionTestCase):
    """Verify the network adapter loads (prefix, vrf) records from CommandGetter results."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        self.namespace = self.testing_objects["namespace"]

        self.job = SSOTSyncNetworkData()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.namespace = self.namespace
        self.job.debug = False
        self.job.sync_vrfs = True
        self.job.sync_vrf_to_prefix = True
        self.job.command_getter_result = {
            "demo-cisco-2": {
                "interfaces": {
                    "GigabitEthernet1": {
                        "vrf": {"name": "mgmt"},
                        "ip_addresses": [{"ip_address": "10.1.1.11", "prefix_length": 24}],
                    },
                    "GigabitEthernet2": {
                        "vrf": {},
                        "ip_addresses": [{"ip_address": "10.1.1.12", "prefix_length": 24}],
                    },
                },
            },
        }

        self.adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)

    def test_load_emits_record_for_interface_with_vrf_and_ip(self):
        self.adapter.load_prefix_to_vrf()
        record = self.adapter.get(SyncNetworkDataPrefixToVrf, "Global__10.1.1.0/24__mgmt")
        self.assertEqual(record.namespace__name, "Global")
        self.assertEqual(record.prefix, "10.1.1.0/24")
        self.assertEqual(record.vrf__name, "mgmt")

    def test_load_skips_interfaces_without_vrf(self):
        self.adapter.load_prefix_to_vrf()
        records = list(self.adapter.get_all(SyncNetworkDataPrefixToVrf))
        # Only GigabitEthernet1 has a VRF; GigabitEthernet2's vrf is empty.
        self.assertEqual(len(records), 1)


class PrefixToVrfNautobotAdapterTestCase(TransactionTestCase):
    """Verify the Nautobot adapter loads existing (prefix, vrf) associations in scope."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        self.namespace = self.testing_objects["namespace"]
        self.prefix = Prefix.objects.get(prefix="10.1.1.0/24", namespace=self.namespace)
        self.vrf = VRF.objects.get(name="mgmt", namespace=self.namespace)

        # Wire an interface IP so the destination's scope (synced devices' interface IPs) reaches the prefix.
        device_2 = self.testing_objects["device_2"]
        interface = Interface.objects.get(device=device_2, name="GigabitEthernet1")
        interface.ip_addresses.add(self.testing_objects["ip_address_2"])  # 10.1.1.11

        self.job = SSOTSyncNetworkData()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.namespace = self.namespace
        self.job.debug = False
        self.job.sync_vrfs = True
        self.job.sync_vrf_to_prefix = True
        self.job.devices_to_load = type(device_2).objects.filter(pk=device_2.pk)

        self.adapter = SyncNetworkDataNautobotAdapter(job=self.job, sync=None)

    def test_load_emits_existing_association(self):
        self.prefix.vrfs.add(self.vrf)
        self.adapter.load_prefix_to_vrf()
        record = self.adapter.get(SyncNetworkDataPrefixToVrf, "Global__10.1.1.0/24__mgmt")
        self.assertEqual(record.vrf__name, "mgmt")

    def test_load_emits_nothing_when_no_associations_exist(self):
        # No prefix.vrfs.add() done — destination should be empty so source-side creates re-establish.
        self.adapter.load_prefix_to_vrf()
        self.assertEqual(list(self.adapter.get_all(SyncNetworkDataPrefixToVrf)), [])
