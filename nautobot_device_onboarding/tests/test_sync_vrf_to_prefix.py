"""Tests for the opt-in sync_vrf_to_prefix behavior on SyncNetworkDataVrfToInterface."""

from unittest.mock import MagicMock

from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Interface
from nautobot.extras.models import JobResult
from nautobot.ipam.models import VRF, IPAddress, Prefix

from nautobot_device_onboarding.diffsync.models.sync_network_data_models import (
    SyncNetworkDataVrfToInterface,
)
from nautobot_device_onboarding.jobs import SSOTSyncDevices
from nautobot_device_onboarding.tests import utils


class SyncVrfToPrefixTestCase(TransactionTestCase):
    """Verify that the sync_vrf_to_prefix flag controls VRF-to-Prefix association."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()
        namespace = self.testing_objects["namespace"]

        self.prefix = Prefix.objects.get(prefix="10.1.1.0/24", namespace=namespace)
        self.ip_address = IPAddress.objects.get(host="10.1.1.11")
        self.interface = Interface.objects.get(device__name="demo-cisco-2", name="GigabitEthernet1")

        self.vrf = VRF.objects.get(name="mgmt", namespace=namespace)
        self.other_vrf = VRF.objects.get(name="vrf2", namespace=namespace)

        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.namespace = namespace
        self.job.debug = False

        self.adapter = MagicMock()
        self.adapter.job = self.job

    def _assign_vrf(self, sync_vrf_to_prefix):
        self.job.sync_vrf_to_prefix = sync_vrf_to_prefix
        SyncNetworkDataVrfToInterface._get_and_assign_vrf(  # pylint: disable=protected-access
            self.adapter,
            {"vrf": {"name": self.vrf.name}},
            self.interface,
            diff_method_type="create",
        )

    def test_prefix_gets_vrf_when_flag_enabled(self):
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
        self._assign_vrf(sync_vrf_to_prefix=True)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_prefix_unchanged_when_flag_disabled(self):
        self._assign_vrf(sync_vrf_to_prefix=False)
        self.assertFalse(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())

    def test_add_is_idempotent(self):
        self._assign_vrf(sync_vrf_to_prefix=True)
        self._assign_vrf(sync_vrf_to_prefix=True)
        self.assertEqual(self.prefix.vrfs.filter(pk=self.vrf.pk).count(), 1)

    def test_existing_vrf_association_preserved(self):
        """Additive-only: assigning a new VRF must not drop a pre-existing VRF link."""
        self.prefix.vrfs.add(self.other_vrf)
        self._assign_vrf(sync_vrf_to_prefix=True)
        self.assertTrue(self.prefix.vrfs.filter(pk=self.other_vrf.pk).exists())
        self.assertTrue(self.prefix.vrfs.filter(pk=self.vrf.pk).exists())
