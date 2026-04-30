"""Tests for the SyncNetworkDataPrefixToVrf diffsync model and its source loader."""

from diffsync.enum import DiffSyncModelFlags
from nautobot.apps.testing import TransactionTestCase
from nautobot.extras.models import JobResult
from nautobot.ipam.models import VRF, Prefix

from nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters import (
    SyncNetworkDataNetworkAdapter,
)
from nautobot_device_onboarding.diffsync.models.sync_network_data_models import (
    SyncNetworkDataPrefixToVrf,
)
from nautobot_device_onboarding.jobs import SSOTSyncNetworkData
from nautobot_device_onboarding.tests import utils


class PrefixToVrfModelCreateTestCase(TransactionTestCase):
    """Verify that SyncNetworkDataPrefixToVrf.create() additively tags a Prefix with a VRF."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        self.namespace = self.testing_objects["namespace"]

        self.prefix = Prefix.objects.get(prefix="10.1.1.0/24", namespace=self.namespace)
        self.vrf = VRF.objects.get(name="mgmt", namespace=self.namespace)
        self.other_vrf = VRF.objects.get(name="vrf2", namespace=self.namespace)

        self.job = SSOTSyncNetworkData()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.namespace = self.namespace
        self.job.debug = False

        self.adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)

    def _ids(self, vrf_name="mgmt", prefix="10.1.1.0/24"):
        return {"prefix": prefix, "namespace__name": self.namespace.name, "vrf__name": vrf_name}

    def test_create_adds_vrf_to_prefix(self):
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_create_is_idempotent(self):
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertEqual(self.prefix.vrfs.filter(pk=self.vrf.pk).count(), 1)

    def test_create_preserves_existing_vrf_associations(self):
        self.prefix.vrfs.add(self.other_vrf)
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertTrue(self.prefix.vrfs.filter(pk=self.other_vrf.pk).exists())
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_create_skips_unknown_vrf(self):
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(vrf_name="does-not-exist"), {})
        self.assertEqual(self.prefix.vrfs.count(), 0)

    def test_create_skips_unknown_prefix(self):
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(prefix="203.0.113.0/24"), {})
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_reassociates_after_manual_removal(self):
        """Regression: model.create() re-establishes a Prefix-to-VRF link removed via the UI.

        This is the production scenario: a sync ran in the past and tagged 10.1.1.0/24 with mgmt.
        A user then removed that VRF from the prefix manually. On the next sync, the source
        adapter emits the same (prefix, vrf) entry and the target adapter does NOT — so diffsync
        flags it as create, our model.create() runs, and the link is restored.
        """
        self.prefix.vrfs.add(self.vrf)
        self.prefix.vrfs.remove(self.vrf)
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        SyncNetworkDataPrefixToVrf.create(self.adapter, self._ids(), {})
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())


class PrefixToVrfSourceLoaderTestCase(TransactionTestCase):
    """Verify SyncNetworkDataNetworkAdapter.load_prefix_to_vrf() emits the right diffsync entries."""

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
        self.job.command_getter_result = {
            "demo-cisco-2": {
                "interfaces": {
                    "GigabitEthernet1": {
                        "vrf": {"name": "mgmt"},
                        "ip_addresses": [{"ip_address": "10.1.1.11", "prefix_length": 24}],
                    },
                    "GigabitEthernet2": {
                        "vrf": {"name": "mgmt"},
                        "ip_addresses": [{"ip_address": "10.1.1.20", "prefix_length": 24}],
                    },
                    "GigabitEthernet3": {
                        # no VRF — must be skipped
                        "vrf": {},
                        "ip_addresses": [{"ip_address": "10.1.1.30", "prefix_length": 24}],
                    },
                    "GigabitEthernet4": {
                        # VRF but no IPs — must be skipped
                        "vrf": {"name": "vrf2"},
                        "ip_addresses": [],
                    },
                    "GigabitEthernet5": {
                        "vrf": {"name": "vrf2"},
                        "ip_addresses": [{"ip_address": "192.168.50.1", "prefix_length": 30}],
                    },
                },
            },
        }
        self.adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)

    def _identifiers_in_store(self):
        return {
            (entry.prefix, entry.namespace__name, entry.vrf__name) for entry in self.adapter.get_all("prefix_to_vrf")
        }

    def test_loader_emits_one_entry_per_unique_prefix_vrf_pair(self):
        self.adapter.load_prefix_to_vrf()
        identifiers = self._identifiers_in_store()
        self.assertIn(("10.1.1.0/24", self.namespace.name, "mgmt"), identifiers)
        self.assertIn(("192.168.50.0/30", self.namespace.name, "vrf2"), identifiers)
        # GigabitEthernet1 and GigabitEthernet2 share the same (prefix, vrf) — must be deduped.
        self.assertEqual(
            len([i for i in identifiers if i == ("10.1.1.0/24", self.namespace.name, "mgmt")]),
            1,
        )

    def test_loader_skips_interfaces_without_vrf(self):
        self.adapter.load_prefix_to_vrf()
        identifiers = self._identifiers_in_store()
        self.assertFalse(any(i[0] == "10.1.1.0/24" and "mgmt" not in i for i in identifiers))
        # 10.1.1.30 was on an interface with no VRF; no entry for that prefix should be emitted.
        for ident in identifiers:
            self.assertNotEqual(ident, ("10.1.1.0/24", self.namespace.name, ""))

    def test_loader_skips_interfaces_without_ips(self):
        self.adapter.load_prefix_to_vrf()
        identifiers = self._identifiers_in_store()
        # GigabitEthernet4 had vrf2 but no IPs. Only the (192.168.50.0/30, vrf2) entry should
        # come from GigabitEthernet5, not from GigabitEthernet4.
        vrf2_entries = [i for i in identifiers if i[2] == "vrf2"]
        self.assertEqual(len(vrf2_entries), 1)

    def test_loader_sets_skip_unmatched_dst_flag(self):
        self.adapter.load_prefix_to_vrf()
        for entry in self.adapter.get_all("prefix_to_vrf"):
            self.assertTrue(
                entry.model_flags & DiffSyncModelFlags.SKIP_UNMATCHED_DST,
                f"SKIP_UNMATCHED_DST not set on {entry}",
            )
