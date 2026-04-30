"""Tests for the opt-in sync_vrf_to_prefix post-sync association on SSOTSyncNetworkData."""

from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Interface
from nautobot.extras.models import JobResult
from nautobot.ipam.models import VRF, IPAddress, Prefix

from nautobot_device_onboarding.jobs import SSOTSyncNetworkData
from nautobot_device_onboarding.tests import utils


class SyncVrfToPrefixTestCase(TransactionTestCase):
    """Verify that the post-sync VRF-to-Prefix association behaves as expected."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        namespace = self.testing_objects["namespace"]

        self.prefix = Prefix.objects.get(prefix="10.1.1.0/24", namespace=namespace)
        self.ip_address = IPAddress.objects.get(host="10.1.1.11")
        self.interface = Interface.objects.get(device__name="demo-cisco-2", name="GigabitEthernet1")

        self.vrf = VRF.objects.get(name="mgmt", namespace=namespace)
        self.other_vrf = VRF.objects.get(name="vrf2", namespace=namespace)

        self.job = SSOTSyncNetworkData()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.namespace = namespace
        self.job.debug = False
        self.job.sync_vrfs = True
        self.job.command_getter_result = {
            "demo-cisco-2": {
                "interfaces": {
                    "GigabitEthernet1": {"vrf": {"name": self.vrf.name}},
                },
            },
        }

    def _run_post_sync(self, sync_vrf_to_prefix):
        self.job.sync_vrf_to_prefix = sync_vrf_to_prefix
        if sync_vrf_to_prefix:
            self.job._associate_vrfs_to_prefixes_post_sync()  # pylint: disable=protected-access

    def test_prefix_gets_vrf_when_flag_enabled(self):
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        self._run_post_sync(sync_vrf_to_prefix=True)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_prefix_unchanged_when_flag_disabled(self):
        self._run_post_sync(sync_vrf_to_prefix=False)
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_add_is_idempotent(self):
        self._run_post_sync(sync_vrf_to_prefix=True)
        self._run_post_sync(sync_vrf_to_prefix=True)
        self.assertEqual(self.prefix.vrfs.filter(pk=self.vrf.pk).count(), 1)

    def test_existing_vrf_association_preserved(self):
        """Additive-only: assigning a new VRF must not drop a pre-existing VRF link."""
        self.prefix.vrfs.add(self.other_vrf)
        self._run_post_sync(sync_vrf_to_prefix=True)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.other_vrf.pk).exists())
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_reasserts_link_when_vrf_to_interface_unchanged(self):
        """Regression: link is re-added on every sync even when diffsync sees no Interface↔VRF change.

        This covers the scenario reported in production: a user manually removed the Prefix↔VRF
        association in the UI; the next sync had no Interface↔VRF diff but still needed to
        re-establish the prefix tag.
        """
        self.prefix.vrfs.add(self.vrf)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        self.prefix.vrfs.remove(self.vrf)
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        self._run_post_sync(sync_vrf_to_prefix=True)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
