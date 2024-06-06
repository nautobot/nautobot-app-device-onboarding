"""Test Cisco Support adapter."""

from unittest.mock import MagicMock, patch

from nautobot.core.testing import TransactionTestCase
from nautobot.dcim.models import Device, Interface
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
        self.job.debug = True
        self.job.devices_to_load = None

        self.sync_network_data_adapter = SyncNetworkDataNetworkAdapter(job=self.job, sync=None)

    def test_handle_failed_devices(self):
        """Devices that failed to returned pardsed data should be removed from results."""
        # Add a failed device to the mock returned data
        self.job.command_getter_result.update(sync_network_data_fixture.failed_device)

        self.sync_network_data_adapter._handle_failed_devices(  # pylint: disable=protected-access
            device_data=self.job.command_getter_result
        )
        self.assertNotIn("demo-cisco-xe3", self.job.command_getter_result.keys())

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

        # test loaded devices
        for hostname, device_data in self.job.command_getter_result.items():
            unique_id = f"{hostname}__{device_data['serial']}"
            diffsync_obj = self.sync_network_data_adapter.get("device", unique_id)
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
                            unique_id = ip_address["ip_address"]
                            diffsync_obj = self.sync_network_data_adapter.get("ip_address", unique_id)
                            self.assertEqual(ip_address["ip_address"], diffsync_obj.host)
                            self.assertEqual(4, diffsync_obj.ip_version)
                            self.assertEqual(int(ip_address["prefix_length"]), diffsync_obj.mask_length)
                            self.assertEqual(self.job.ip_address_status.name, diffsync_obj.status__name)

    def test_load_vlans(self):
        """Test loading vlan data returned from command getter into the diffsync store."""
        self.job.devices_to_load = Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2"])
        self.sync_network_data_adapter.load_vlans()

        for _, device_data in self.job.command_getter_result.items():
            for _, interface_data in device_data["interfaces"].items():
                for tagged_vlan in interface_data["tagged_vlans"]:
                    unique_id = f"{tagged_vlan['id']}__{tagged_vlan['name']}__{self.job.location.name}"
                    diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
                    self.assertEqual(int(tagged_vlan["id"]), diffsync_obj.vid)
                    self.assertEqual(tagged_vlan["name"], diffsync_obj.name)
                    self.assertEqual(self.job.location.name, diffsync_obj.location__name)
                if interface_data["untagged_vlan"]:
                    unique_id = f"{interface_data['untagged_vlan']['id']}__{interface_data['untagged_vlan']['name']}__{self.job.location.name}"
                    diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
                    self.assertEqual(int(interface_data["untagged_vlan"]["id"]), diffsync_obj.vid)
                    self.assertEqual(interface_data["untagged_vlan"]["name"], diffsync_obj.name)
                    self.assertEqual(self.job.location.name, diffsync_obj.location__name)

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
                        unique_id = f"{hostname}__{interface_name}__{ip_address['ip_address']}"
                        diffsync_obj = self.sync_network_data_adapter.get("ipaddress_to_interface", unique_id)
                        self.assertEqual(hostname, diffsync_obj.interface__device__name)
                        self.assertEqual(interface_name, diffsync_obj.interface__name)
                        self.assertEqual(ip_address["ip_address"], diffsync_obj.ip_address__host)

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
        self.job.devices_to_load = Device.objects.filter(name__in=["demo-cisco-1", "demo-cisco-2"])

        self.sync_network_data_adapter = SyncNetworkDataNautobotAdapter(job=self.job, sync=None)

    def test_cache_primary_ips(self):
        """Test IP Cache."""
        self.sync_network_data_adapter._cache_primary_ips(  # pylint: disable=protected-access
            device_queryset=self.job.devices_to_load
        )
        for device in self.job.devices_to_load:
            self.assertEqual(self.sync_network_data_adapter.primary_ips[device.id], device.primary_ip.id)

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
            unique_id = f"{ip_address.host}"
            diffsync_obj = self.sync_network_data_adapter.get("ip_address", unique_id)
            self.assertEqual(ip_address.host, diffsync_obj.host)
            self.assertEqual(ip_address.ip_version, diffsync_obj.ip_version)
            self.assertEqual(ip_address.mask_length, diffsync_obj.mask_length)
            self.assertEqual(self.job.ip_address_status.name, diffsync_obj.status__name)

    def test_load_vlans(self):
        """Test loading Nautobot vlan data into the diffsync store."""
        self.sync_network_data_adapter.load_vlans()

        for vlan in VLAN.objects.all():
            unique_id = f"{vlan.vid}__{vlan.name}__{self.job.location.name}"
            diffsync_obj = self.sync_network_data_adapter.get("vlan", unique_id)
            self.assertEqual(int(vlan.vid), diffsync_obj.vid)
            self.assertEqual(vlan.name, diffsync_obj.name)
            self.assertEqual(self.job.location.name, diffsync_obj.location__name)

    def test_load_tagged_vlans_to_interface(self):
        """Test loading Nautobot tagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_tagged_vlans_to_interface()
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            tagged_vlans = []
            for vlan in interface.tagged_vlans.all():
                vlan_dict = {}
                vlan_dict["name"] = vlan.name
                vlan_dict["id"] = str(vlan.vid)
                tagged_vlans.append(vlan_dict)

                unique_id = f"{interface.device.name}__{interface.name}"
                diffsync_obj = self.sync_network_data_adapter.get("tagged_vlans_to_interface", unique_id)
                self.assertEqual(interface.device.name, diffsync_obj.device__name)
                self.assertEqual(interface.name, diffsync_obj.name)
                self.assertEqual(tagged_vlans, diffsync_obj.tagged_vlans)

    def load_untagged_vlan_to_interface(self):
        """Test loading Nautobot untagged vlan interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_untagged_vlan_to_interface()
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            untagged_vlan = {}
            if interface.untagged_vlan:
                untagged_vlan["name"] = interface.untagged_vlan.name
                untagged_vlan["id"] = str(interface.untagged_vlan.vid)

                unique_id = f"{interface.device.name}__{interface.name}"
                diffsync_obj = self.sync_network_data_adapter.get("untagged_vlans_to_interface", unique_id)
                self.assertEqual(interface.device.name, diffsync_obj.device__name)
                self.assertEqual(interface.name, diffsync_obj.name)
                self.assertEqual(untagged_vlan, diffsync_obj.tagged_vlan)

    def test_load_lag_to_interface(self):
        """Test loading Nautobot lag interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_lag_to_interface()
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            unique_id = f"{interface.device.name}__{interface.name}"
            diffsync_obj = self.sync_network_data_adapter.get("lag_to_interface", unique_id)
            self.assertEqual(interface.device.name, diffsync_obj.device__name)
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

    def test_load_vrf_to_interface(self):
        """Test loading Nautobot vrf interface assignments into the Diffsync store."""
        self.sync_network_data_adapter.load_vrf_to_interface()
        for interface in Interface.objects.filter(device__in=self.job.devices_to_load):
            vrf = {}
            if interface.vrf:
                vrf["name"] = interface.vrf.name
            unique_id = f"{interface.device.name}__{interface.name}"
            diffsync_obj = self.sync_network_data_adapter.get("vrf_to_interface", unique_id)
            self.assertEqual(interface.device.name, diffsync_obj.device__name)
            self.assertEqual(interface.name, diffsync_obj.name)
            self.assertEqual(vrf, diffsync_obj.vrf)

    def test_sync_complete(self):
        """Test primary ip re-assignment if deleted during the sync."""
        self.sync_network_data_adapter._cache_primary_ips(  # pylint: disable=protected-access
            device_queryset=self.job.devices_to_load
        )
        for device in self.job.devices_to_load:
            device.primary_ip4 = None
            device.validated_save()
        self.sync_network_data_adapter.sync_complete(source=None, diff=None)
        for device in self.job.devices_to_load.all():
            self.assertEqual(self.sync_network_data_adapter.primary_ips[device.id], device.primary_ip.id)
