"""Test Cisco Support adapter."""

import copy
from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from nautobot.apps.testing import TransactionTestCase
from nautobot.dcim.models import Cable, Device, Interface, SoftwareVersion
from nautobot.extras.models import JobResult
from nautobot.ipam.models import VLAN, VRF, IPAddress

from nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters import (
    SyncNetworkDataNautobotAdapter,
    SyncNetworkDataNetworkAdapter,
)
from nautobot_device_onboarding.jobs import SSOTSyncDevices
from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.fixtures import sync_network_data_fixture


class SyncNetworkDataNetworkAdapterTestCase(TransactionTestCase):
    """Test SyncNetworkDataNetworkAdapter class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()

        # Setup Job
        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.command_getter_result = sync_network_data_fixture.sync_network_mock_data_valid

        # Form inputs
        self.job.interface_status = self.testing_objects["status"]
        self.job.ip_address_status = self.testing_objects["status"]
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]
        self.job.sync_vlans = True
        self.job.sync_vrfs = True
        self.job.sync_software_version = True
        self.job.debug = True
        self.job.devices_to_load = None

        self.sync_network_data_adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)

    def test_handle_failed_devices(self):
        """Devices that failed to returned pardsed data should be removed from results."""
        # Add a failed device to the mock returned data
        self.job.command_getter_result.update(sync_network_data_fixture.failed_device)
        self.assertIn("demo-cisco-3", self.job.command_getter_result.keys())

        self.sync_network_data_adapter._handle_failed_devices(  # pylint: disable=protected-access
            device_data=self.job.command_getter_result
        )
        self.assertNotIn("demo-cisco-3", self.job.command_getter_result.keys())

    def test_handle_failed_devices_no_serial(self):
        """Test handling of failed devices when an error is raised due to missing serial."""
        self.job.command_getter_result.update(sync_network_data_fixture.missing_serial)
        self.assertIn("demo-cisco-4", self.job.command_getter_result.keys())
        self.sync_network_data_adapter._handle_failed_devices(  # pylint: disable=protected-access
            device_data=self.job.command_getter_result
        )
        self.assertNotIn("demo-cisco-4", self.job.command_getter_result.keys())

    def test_exclude_filtered_out_devices_no_devices_to_load(self):
        """When devices_to_load is None, the helper returns early without mutating command_getter_result."""
        self.assertIsNone(self.job.devices_to_load)
        original_keys = set(self.job.command_getter_result.keys())

        self.sync_network_data_adapter._exclude_filtered_out_devices()  # pylint: disable=protected-access

        self.assertEqual(set(self.job.command_getter_result.keys()), original_keys)

    def test_exclude_filtered_out_devices_all_valid(self):
        """When every hostname in command_getter_result is in devices_to_load, the helper is a no-op."""
        self.job.devices_to_load = Device.objects.filter(name__in=list(self.job.command_getter_result.keys()))
        original_keys = set(self.job.command_getter_result.keys())
        self.job.logger = MagicMock()

        self.sync_network_data_adapter._exclude_filtered_out_devices()  # pylint: disable=protected-access

        self.assertEqual(set(self.job.command_getter_result.keys()), original_keys)
        self.job.logger.warning.assert_not_called()

    def test_exclude_filtered_out_devices_prunes_excluded(self):
        """Hostnames absent from devices_to_load are removed from command_getter_result and a warning is logged.

        Regression test for the Site 3 leak — without this guard, every load_*() method iterates
        command_getter_result for ALL discovered hostnames, including those excluded by the
        (name, serial) queryset filter, silently writing interfaces / cables / IPs against them.
        """
        # Keep demo-cisco-1, exclude demo-cisco-2 — both are in command_getter_result, only the
        # first is in devices_to_load (simulates demo-cisco-2 failing the (name, serial) filter).
        self.assertIn("demo-cisco-1", self.job.command_getter_result)
        self.assertIn("demo-cisco-2", self.job.command_getter_result)
        self.job.devices_to_load = Device.objects.filter(name="demo-cisco-1")
        self.job.logger = MagicMock()

        self.sync_network_data_adapter._exclude_filtered_out_devices()  # pylint: disable=protected-access

        self.assertIn("demo-cisco-1", self.job.command_getter_result)
        self.assertNotIn("demo-cisco-2", self.job.command_getter_result)
        self.job.logger.warning.assert_called_once()
        # The warning message names the excluded hostname so operators can investigate.
        warning_args = str(self.job.logger.warning.call_args)
        self.assertIn("demo-cisco-2", warning_args)

    @patch("nautobot_device_onboarding.diffsync.adapters.sync_network_data_adapters.sync_network_data_command_getter")
    def test_execute_command_getter(self, command_getter_result):
        """Test execute command getter."""
        command_getter_result.return_value = sync_network_data_fixture.sync_network_mock_data_valid
        command_getter_result.update(sync_network_data_fixture.failed_device)
        self.sync_network_data_adapter.execute_command_getter()
        self.assertIn(
            self.testing_objects["device_1"].name, list(self.job.devices_to_load.values_list("name", flat=True))
        )
        self.assertIn(
            self.testing_objects["device_2"].name, list(self.job.devices_to_load.values_list("name", flat=True))
        )

    def test_load_devices(self):
        """Test loading device data returned from command getter into the diffsync store."""
        self.sync_network_data_adapter.load_devices()

        # test loaded devices — diffsync identity for SyncNetworkDataDevice is (name,) only;
        # serial is an attribute since the trial branch's Delta 2 move.
        for hostname, device_data in self.job.command_getter_result.items():
            diffsync_obj = self.sync_network_data_adapter.get("device", hostname)
            self.assertEqual(hostname, diffsync_obj.name)
            self.assertEqual(device_data["serial"], diffsync_obj.serial)

        # test child interfaces which are loaded along with devices
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                unique_id = f"{hostname}__{interface_name}"
                diffsync_obj = self.sync_network_data_adapter.get("interface", unique_id)
                self.assertEqual(hostname, diffsync_obj.device__name)
                self.assertEqual(interface_name, diffsync_obj.name)
                self.assertEqual(self.testing_objects["status"].name, diffsync_obj.status__name)
                self.assertEqual(
                    self.sync_network_data_adapter._process_mac_address(  # pylint: disable=protected-access
                        mac_address=interface_data["mac_address"]
                    ),
                    diffsync_obj.mac_address,
                )
                self.assertEqual(interface_data["802.1Q_mode"], diffsync_obj.mode)
                self.assertEqual(interface_data["link_status"], diffsync_obj.enabled)
                self.assertEqual(interface_data["description"], diffsync_obj.description)

    def test_load_ip_addresses(self):
        """Test loading ip address data returned from command getter into the diffsync store."""
        self.sync_network_data_adapter.load_ip_addresses()

        for _, device_data in self.job.command_getter_result.items():
            for _, interface_data in device_data["interfaces"].items():
                if interface_data["ip_addresses"]:
                    for ip_address in interface_data["ip_addresses"]:
                        if ip_address["ip_address"]:
                            unique_id = f"{ip_address['ip_address']}__{self.job.namespace.name}"
                            diffsync_obj = self.sync_network_data_adapter.get("ip_address", unique_id)
                            self.assertEqual(ip_address["ip_address"], diffsync_obj.host)
                            self.assertEqual(self.job.namespace.name, diffsync_obj.namespace)
                            self.assertEqual(4, diffsync_obj.ip_version)
                            self.assertEqual(int(ip_address["prefix_length"]), diffsync_obj.mask_length)
                            self.assertEqual(self.job.ip_address_status.name, diffsync_obj.status__name)

    def test_load_vlans(self):
        """Test loading vlan data returned from command getter into the diffsync store."""
        self.job.devices_to_load = Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2"])
        self.sync_network_data_adapter.load_vlans()

        location_natural_keys = {}
        for device in self.job.devices_to_load:
            location_natural_keys[device.name] = device.location.natural_key()

        for hostname, device_data in self.job.command_getter_result.items():
            for _, interface_data in device_data["interfaces"].items():
                for tagged_vlan in interface_data["tagged_vlans"]:
                    unique_id = f"{tagged_vlan['id']}__{tagged_vlan['name']}__{tuple(location_natural_keys[hostname])}"
                    diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
                    self.assertEqual(int(tagged_vlan["id"]), diffsync_obj.vid)
                    self.assertEqual(tagged_vlan["name"], diffsync_obj.name)
                    self.assertEqual(tuple(location_natural_keys[hostname]), diffsync_obj.location_natural_key)
                if interface_data["untagged_vlan"]:
                    unique_id = f"{interface_data['untagged_vlan']['id']}__{interface_data['untagged_vlan']['name']}__{tuple(location_natural_keys[hostname])}"
                    diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
                    self.assertEqual(int(interface_data["untagged_vlan"]["id"]), diffsync_obj.vid)
                    self.assertEqual(interface_data["untagged_vlan"]["name"], diffsync_obj.name)
                    self.assertEqual(tuple(location_natural_keys[hostname]), diffsync_obj.location_natural_key)

    def test_load_vrfs(self):
        """Test loading vrf data returned from command getter into the diffsync store."""
        self.sync_network_data_adapter.load_vrfs()
        for _, device_data in self.job.command_getter_result.items():
            for _, interface_data in device_data["interfaces"].items():
                if interface_data["vrf"]:
                    unique_id = f"{interface_data['vrf']['name']}__{self.job.namespace.name}"
                    diffsync_obj = self.sync_network_data_adapter.get("vrf", unique_id)
                    self.assertEqual(interface_data["vrf"]["name"], diffsync_obj.name)
                    self.assertEqual(self.job.namespace.name, diffsync_obj.namespace__name)

    def test_load_ip_address_to_interfaces(self):
        """Test loading ip address interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_ip_address_to_interfaces()
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                for ip_address in interface_data["ip_addresses"]:
                    if ip_address["ip_address"]:
                        unique_id = (
                            f"{hostname}__{interface_name}__{ip_address['ip_address']}__{self.job.namespace.name}"
                        )
                        diffsync_obj = self.sync_network_data_adapter.get("ipaddress_to_interface", unique_id)
                        self.assertEqual(hostname, diffsync_obj.interface__device__name)
                        self.assertEqual(interface_name, diffsync_obj.interface__name)
                        self.assertEqual(ip_address["ip_address"], diffsync_obj.ip_address__host)
                        self.assertEqual(self.job.namespace.name, diffsync_obj.ip_address__parent__namespace__name)

    def test_load_tagged_vlans_to_interface(self):
        """Test loading tagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_tagged_vlans_to_interface()
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                unique_id = f"{hostname}__{interface_name}"
                diffsync_obj = self.sync_network_data_adapter.get("tagged_vlans_to_interface", unique_id)
                self.assertEqual(hostname, diffsync_obj.device__name)
                self.assertEqual(interface_name, diffsync_obj.name)
                self.assertEqual(interface_data["tagged_vlans"], diffsync_obj.tagged_vlans)

    def test_load_untagged_vlan_to_interface(self):
        """Test loading untagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_untagged_vlan_to_interface()
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                unique_id = f"{hostname}__{interface_name}"
                diffsync_obj = self.sync_network_data_adapter.get("untagged_vlan_to_interface", unique_id)
                self.assertEqual(hostname, diffsync_obj.device__name)
                self.assertEqual(interface_name, diffsync_obj.name)
                if interface_data["untagged_vlan"]:
                    self.assertEqual(interface_data["untagged_vlan"], diffsync_obj.untagged_vlan)
                else:
                    self.assertEqual({}, diffsync_obj.untagged_vlan)

    def test_load_lag_to_interface(self):
        """Test loading lag interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_lag_to_interface()
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                unique_id = f"{hostname}__{interface_name}"
                diffsync_obj = self.sync_network_data_adapter.get("lag_to_interface", unique_id)
                self.assertEqual(hostname, diffsync_obj.device__name)
                self.assertEqual(interface_name, diffsync_obj.name)
                self.assertEqual(interface_data["lag"], diffsync_obj.lag__interface__name)

    def test_load_vrf_to_interface(self):
        """Test loading vrf interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_vrf_to_interface()
        for hostname, device_data in self.job.command_getter_result.items():
            for interface_name, interface_data in device_data["interfaces"].items():
                unique_id = f"{hostname}__{interface_name}"
                diffsync_obj = self.sync_network_data_adapter.get("vrf_to_interface", unique_id)
                self.assertEqual(hostname, diffsync_obj.device__name)
                self.assertEqual(interface_name, diffsync_obj.name)
                self.assertEqual(interface_data["vrf"], diffsync_obj.vrf)

    def test_load_cables(self):
        """Test loading cable data returned from command getter into the diffsync store."""
        self.sync_network_data_adapter.load_cables()
        for hostname, device_data in self.job.command_getter_result.items():
            for cable in device_data["cables"]:
                if hostname < cable["remote_device"]:
                    termination_a_device = hostname
                    termination_a_interface = cable["local_interface"]
                    termination_b_device = cable["remote_device"]
                    termination_b_interface = cable["remote_interface"]
                else:
                    termination_a_device = cable["remote_device"]
                    termination_a_interface = cable["remote_interface"]
                    termination_b_device = hostname
                    termination_b_interface = cable["local_interface"]
                unique_id = f"dcim__interface__{termination_a_device}__{termination_a_interface}__dcim__interface__{termination_b_device}__{termination_b_interface}"
                diffsync_obj = self.sync_network_data_adapter.get("cable", unique_id)
                self.assertEqual(termination_a_device, diffsync_obj.termination_a__device__name)
                self.assertEqual(termination_a_interface, diffsync_obj.termination_a__name)
                self.assertEqual(termination_b_device, diffsync_obj.termination_b__device__name)
                self.assertEqual(termination_b_interface, diffsync_obj.termination_b__name)

    def test_load_software_versions(self):
        """Test loading software version data returned from command getter into the diffsync store."""
        # In production, execute_command_getter() populates devices_to_load via
        # generate_device_queryset_from_command_getter_result(). This test calls
        # load_software_versions() directly, so set the queryset up by hand.
        self.job.devices_to_load = Device.objects.filter(name__in=list(self.job.command_getter_result.keys()))
        self.sync_network_data_adapter.load_software_versions()
        for _, device_data in self.job.command_getter_result.items():
            device_data = self.job.command_getter_result["demo-cisco-1"]
            device = Device.objects.get(serial=device_data["serial"])
            unique_id = f"{device_data['software_version']}__{device.platform}"
            diffsync_obj = self.sync_network_data_adapter.get("software_version", unique_id)
            self.assertEqual("cisco_ios", diffsync_obj.platform__name)
            self.assertEqual(device_data["software_version"], diffsync_obj.version)

    def test_load_software_version_to_device(self):
        self.sync_network_data_adapter.load_software_version_to_device()
        for _, device_data in self.job.command_getter_result.items():
            device = Device.objects.get(serial=device_data["serial"])
            unique_id = device.name
            diffsync_obj = self.sync_network_data_adapter.get("software_version_to_device", unique_id)
            self.assertEqual(device_data["software_version"], diffsync_obj.software_version__version)

    def test_load_config_context(self):
        """Network adapter loads collected config_context blobs into the diffsync store."""
        self.job.command_getter_result["demo-cisco-1"]["config_context"] = {
            "ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]
        }
        self.sync_network_data_adapter.load_config_context()
        diffsync_obj = self.sync_network_data_adapter.get("config_context", "demo-cisco-1")
        self.assertEqual(diffsync_obj.data, {"ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]})


class SyncNetworkDataNautobotAdapterTestCase(TransactionTestCase):
    """Test SyncNetworkDataNautobotAdapter class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        # Setup Nautobot Objects
        self.testing_objects = utils.sync_network_data_ensure_required_nautobot_objects()

        # Setup Job
        self.job = SSOTSyncDevices()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, user=None, task_name="fake task", worker="default"
        )
        self.job.command_getter_result = sync_network_data_fixture.sync_network_mock_data_valid

        # Form inputs
        self.job.interface_status = self.testing_objects["status"]
        self.job.ip_address_status = self.testing_objects["status"]
        self.job.location = self.testing_objects["location"]
        self.job.namespace = self.testing_objects["namespace"]
        self.job.sync_vlans = True
        self.job.sync_vrfs = True
        self.job.debug = True
        self.job.devices_to_load = Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2", "demo-cisco-4"])

        self.sync_network_data_adapter = SyncNetworkDataNautobotAdapter(job=self.job, sync=None)

    def test_cache_primary_ips(self):
        """Test IP Cache."""
        self.sync_network_data_adapter._cache_primary_ips(  # pylint: disable=protected-access
            device_queryset=self.job.devices_to_load
        )
        for device in self.job.devices_to_load.filter(Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)):
            self.assertEqual(
                self.sync_network_data_adapter.primary_ips[device.id],
                device.primary_ip.id,
            )

    def test_load_param_mac_address(self):
        """Test MAC address string converstion."""
        database_obj = MagicMock()
        database_obj.mac_address = "0000.0000.0000"
        mac_address = self.sync_network_data_adapter.load_param_mac_address(
            parameter_name="mac_address", database_object=database_obj
        )
        self.assertEqual(str, type(mac_address))

    def test_load_ip_addresses(self):
        """Test loading Nautobot ip into the diffsync store."""
        ip_address_hosts = self.sync_network_data_adapter.load_ip_addresses()
        for ip_address in IPAddress.objects.filter(
            host__in=ip_address_hosts,
            parent__namespace__name=self.job.namespace.name,
        ):
            unique_id = f"{ip_address.host}__{ip_address.parent.namespace.name}"
            diffsync_obj = self.sync_network_data_adapter.get("ip_address", unique_id)
            self.assertEqual(ip_address.host, diffsync_obj.host)
            self.assertEqual(ip_address.ip_version, diffsync_obj.ip_version)
            self.assertEqual(ip_address.mask_length, diffsync_obj.mask_length)
            self.assertEqual(self.job.ip_address_status.name, diffsync_obj.status__name)
            self.assertEqual(ip_address.parent.namespace.name, diffsync_obj.namespace)

    def test_load_vlans(self):
        """Test loading Nautobot vlan data into the diffsync store."""
        self.sync_network_data_adapter.load_vlans()

        for vlan in VLAN.objects.all():
            unique_id = f"{vlan.vid}__{vlan.name}__{tuple(vlan.location.natural_key())}"
            diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
            self.assertEqual(int(vlan.vid), diffsync_obj.vid)
            self.assertEqual(vlan.name, diffsync_obj.name)
            self.assertEqual(tuple(vlan.location.natural_key()), diffsync_obj.location_natural_key)

    def test_load_tagged_vlans_to_interface(self):
        """Test loading Nautobot tagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_tagged_vlans_to_interface()
        for device in self.job.devices_to_load:
            for interface in device.all_interfaces:
                tagged_vlans = []
                for vlan in interface.tagged_vlans.all():
                    vlan_dict = {}
                    vlan_dict["name"] = vlan.name
                    vlan_dict["id"] = str(vlan.vid)
                    tagged_vlans.append(vlan_dict)

                    unique_id = f"{interface.parent.name}__{interface.name}"
                    diffsync_obj = self.sync_network_data_adapter.get("tagged_vlans_to_interface", unique_id)
                    self.assertEqual(interface.parent.name, diffsync_obj.device__name)
                    self.assertEqual(interface.name, diffsync_obj.name)
                    self.assertEqual(tagged_vlans, diffsync_obj.tagged_vlans)

    def load_untagged_vlan_to_interface(self):
        """Test loading Nautobot untagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_untagged_vlan_to_interface()
        for device in self.job.devices_to_load:
            for interface in device.all_interfaces:
                untagged_vlan = {}
                if interface.untagged_vlan:
                    untagged_vlan["name"] = interface.untagged_vlan.name
                    untagged_vlan["id"] = str(interface.untagged_vlan.vid)

                    unique_id = f"{interface.parent.name}__{interface.name}"
                    diffsync_obj = self.sync_network_data_adapter.get("untagged_vlans_to_interface", unique_id)
                    self.assertEqual(interface.parent.name, diffsync_obj.device__name)
                    self.assertEqual(interface.name, diffsync_obj.name)
                    self.assertEqual(untagged_vlan, diffsync_obj.tagged_vlan)

    def test_load_lag_to_interface(self):
        """Test loading Nautobot lag interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_lag_to_interface()
        for device in self.job.devices_to_load:
            for interface in device.all_interfaces:
                unique_id = f"{interface.parent.name}__{interface.name}"
                diffsync_obj = self.sync_network_data_adapter.get("lag_to_interface", unique_id)
                self.assertEqual(interface.parent.name, diffsync_obj.device__name)
                self.assertEqual(interface.name, diffsync_obj.name)
                self.assertEqual(interface.lag.name if interface.lag else "", diffsync_obj.lag__interface__name)

    def test_load_vrfs(self):
        """Test loading Nautobot vrf data into the diffsync store."""
        self.sync_network_data_adapter.load_vrfs()
        for vrf in VRF.objects.all():
            unique_id = f"{vrf.name}__{self.job.namespace.name}"
            diffsync_obj = self.sync_network_data_adapter.get("vrf", unique_id)
            self.assertEqual(vrf.name, diffsync_obj.name)
            self.assertEqual(self.job.namespace.name, diffsync_obj.namespace__name)

    def test_load_cables(self):
        """Test loading Nautobot cable data into the diffsync store."""
        dcim_interface_content_type = ContentType.objects.get_for_model(Interface)

        with self.assertLogs(self.job.logger, level="WARNING") as logs:
            self.sync_network_data_adapter.load_cables()
            for cable in Cable.objects.all():
                if (
                    cable.termination_a_type != dcim_interface_content_type
                    or cable.termination_b_type != dcim_interface_content_type
                ):
                    self.assertIn(
                        f"WARNING:nautobot_device_onboarding.jobs:Skipping Cable: {cable}. Only cables with interface terminations are supported.",
                        logs.output[0],
                    )
                    continue
                unique_id = f"dcim__interface__{cable.termination_a.device.name}__{cable.termination_a.name}__dcim__interface__{cable.termination_b.device.name}__{cable.termination_b.name}"
                diffsync_obj = self.sync_network_data_adapter.get("cable", unique_id)
                self.assertEqual(cable.termination_a.device.name, diffsync_obj.termination_a__device__name)
                self.assertEqual(cable.termination_a.name, diffsync_obj.termination_a__name)
                self.assertEqual(cable.termination_b.device.name, diffsync_obj.termination_b__device__name)
                self.assertEqual(cable.termination_b.name, diffsync_obj.termination_b__name)
            # self.assertIn(f"WARNING - Skipping Cable: #{cable}. Only cables with interface terminations are supported.", logs.output[0])

    def test_load_vrf_to_interface(self):
        """Test loading Nautobot vrf interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_vrf_to_interface()
        for device in self.job.devices_to_load:
            for interface in device.all_interfaces:
                vrf = {}
                if interface.vrf:
                    vrf["name"] = interface.vrf.name
                unique_id = f"{interface.parent.name}__{interface.name}"
                diffsync_obj = self.sync_network_data_adapter.get("vrf_to_interface", unique_id)
                self.assertEqual(interface.parent.name, diffsync_obj.device__name)
                self.assertEqual(interface.name, diffsync_obj.name)
                self.assertEqual(vrf, diffsync_obj.vrf)

    def test_load_software_versions(self):
        """Test loading Nautobot software version data into the diffsync store."""
        self.sync_network_data_adapter.load_software_versions()
        for software_version in SoftwareVersion.objects.all():
            unique_id = f"{software_version.version}__{software_version.platform.name}"
            diffsync_obj = self.sync_network_data_adapter.get("software_version", unique_id)
            self.assertEqual(software_version.platform.name, diffsync_obj.platform__name)
            self.assertEqual(software_version.version, diffsync_obj.version)

    def test_load_software_version_to_device(self):
        """Test loading Nautobot software version device assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_software_version_to_device()
        for device in Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2"]):
            unique_id = device.name
            diffsync_obj = self.sync_network_data_adapter.get("software_version_to_device", unique_id)
            self.assertEqual(device.software_version.version, diffsync_obj.software_version__version)

    def test_sync_complete(self):
        """Test primary ip re-assignment if deleted during the sync."""
        self.sync_network_data_adapter._cache_primary_ips(  # pylint: disable=protected-access
            device_queryset=self.job.devices_to_load
        )
        for device in self.job.devices_to_load:
            device.primary_ip4 = None
            device.validated_save()
        self.sync_network_data_adapter.sync_complete(source=None, diff=None)
        # Only test for Devices that initially had Primary IP set
        for device in self.job.devices_to_load.filter(Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)):
            self.assertEqual(
                self.sync_network_data_adapter.primary_ips[device.id],
                device.primary_ip.id if device.primary_ip else None,
            )

    def test_load_config_context_reads_only_managed_slice(self):
        """Nautobot adapter loads only the device_onboarding slice, ignoring other top-level keys."""
        device = Device.objects.get(name="demo-cisco-1")
        device.local_config_context_data = {
            "ntp": ["192.0.2.1"],
            "device_onboarding": {"ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]},
        }
        device.validated_save()

        self.sync_network_data_adapter.load_config_context()

        diffsync_obj = self.sync_network_data_adapter.get("config_context", "demo-cisco-1")
        self.assertEqual(diffsync_obj.data, {"ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]})

    def test_config_context_create_preserves_unmanaged_keys(self):
        """Writing the managed slice leaves sibling and other top-level keys intact."""
        device = Device.objects.get(name="demo-cisco-1")
        device.local_config_context_data = {
            "ntp": ["192.0.2.1"],
            "other_tool": {"foo": "bar"},
            "device_onboarding": {"stale": True},
        }
        device.validated_save()

        new_data = {"ip_ospf_neighbors": [{"neighbor_id": "2.2.2.2"}]}
        self.sync_network_data_adapter.config_context.create(
            self.sync_network_data_adapter, {"device__name": "demo-cisco-1"}, {"data": new_data}
        )

        device.refresh_from_db()
        self.assertEqual(device.local_config_context_data["ntp"], ["192.0.2.1"])
        self.assertEqual(device.local_config_context_data["other_tool"], {"foo": "bar"})
        self.assertEqual(device.local_config_context_data["device_onboarding"], new_data)

    def test_config_context_delete_is_noop(self):
        """delete() never strips a device's config context (additive-only contract)."""
        self.job.logger = MagicMock()
        device = Device.objects.get(name="demo-cisco-1")
        device.local_config_context_data = {"device_onboarding": {"x": 1}}
        device.validated_save()

        instance = self.sync_network_data_adapter.config_context(
            adapter=self.sync_network_data_adapter, device__name="demo-cisco-1", data={"x": 1}
        )
        self.assertIsNone(instance.delete())

        device.refresh_from_db()
        self.assertEqual(device.local_config_context_data["device_onboarding"], {"x": 1})

    def test_config_context_diff_is_idempotent(self):
        """A device whose managed slice already equals the collected data produces no diff (no perpetual update)."""
        blob = {
            "ip_ospf_neighbors": [
                {"neighbor_id": "1.1.1.1", "ip_address": "10.0.12.2", "interface": "Ethernet0/1", "state": "FULL/  -"}
            ],
            "snmp_communities": [{"community": "snmp-server community public RO"}],
        }
        device = Device.objects.get(name="demo-cisco-1")
        device.local_config_context_data = {"device_onboarding": blob}
        device.validated_save()

        # Deep-copy the shared fixture before seeding the source side so the mutation doesn't leak.
        self.job.command_getter_result = copy.deepcopy(sync_network_data_fixture.sync_network_mock_data_valid)
        self.job.command_getter_result["demo-cisco-1"]["config_context"] = copy.deepcopy(blob)

        nautobot_adapter = self.sync_network_data_adapter
        nautobot_adapter.load_config_context()
        network_adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)
        network_adapter.load_config_context()

        # Source (network) already equals destination (Nautobot): the config_context model must not diff.
        diff = network_adapter.diff_to(nautobot_adapter)
        self.assertFalse(diff.has_diffs(), diff.summary())

    def test_config_context_update_replaces_managed_slice(self):
        """update() swaps the managed slice for the latest collected data and leaves sibling keys intact."""
        device = Device.objects.get(name="demo-cisco-1")
        device.local_config_context_data = {
            "manual": "keep",
            "device_onboarding": {"ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]},
        }
        device.validated_save()

        new_data = {"ip_ospf_neighbors": [{"neighbor_id": "9.9.9.9"}]}
        instance = self.sync_network_data_adapter.config_context(
            adapter=self.sync_network_data_adapter,
            device__name="demo-cisco-1",
            data={"ip_ospf_neighbors": [{"neighbor_id": "1.1.1.1"}]},
        )
        instance.update({"data": new_data})

        device.refresh_from_db()
        self.assertEqual(device.local_config_context_data["device_onboarding"], new_data)
        self.assertEqual(device.local_config_context_data["manual"], "keep")
