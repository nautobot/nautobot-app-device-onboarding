"""Unit tests for nautobot_device_onboarding.onboard module and its classes."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Manufacturer, Platform
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField, Role, Status
from nautobot.extras.models.secrets import SecretsGroup
from nautobot.ipam.models import IPAddress

from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.nautobot_keeper import NautobotKeeper

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


class NautobotKeeperTestCase(TestCase):
    """Test the NautobotKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        role_content_type = ContentType.objects.get_for_model(Device)

        device_role = Role.objects.create(name="Switch")
        device_role.content_types.set([role_content_type])

        status = Status.objects.get(name="Active")
        location_type = LocationType.objects.create(name="site")
        location_type.content_types.set([ContentType.objects.get_for_model(Device)])
        self.site1 = Location.objects.create(name="USWEST", location_type=location_type, status=status)
        data = (
            {
                "field_type": CustomFieldTypeChoices.TYPE_TEXT,
                "field_name": "cf_manufacturer",
                "default_value": "Foobar!",
                "model": Manufacturer,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_name": "cf_devicetype",
                "default_value": 5,
                "model": DeviceType,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_name": "cf_devicerole",
                "default_value": 10,
                "model": Role,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_name": "cf_platform",
                "default_value": True,
                "model": Platform,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_name": "cf_device",
                "default_value": False,
                "model": Device,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_name": "cf_device_null",
                "default_value": None,
                "model": Device,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_DATE,
                "field_name": "cf_interface",
                "default_value": "2016-06-23",
                "model": Interface,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_URL,
                "field_name": "cf_ipaddress",
                "default_value": "http://example.com/",
                "model": IPAddress,
            },
        )

        for item in data:
            # Create a custom field
            field = CustomField.objects.create(
                type=item["field_type"], label=item["field_name"], default=item["default_value"], required=False
            )
            field.content_types.set([ContentType.objects.get_for_model(item["model"])])

    def test_ensure_device_manufacturer_strict_missing(self):
        """Verify ensure_device_manufacturer function when Manufacturer object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_manufacturer(create_manufacturer=False)
            self.assertEqual(str(exc_info), "fail-config - ERROR manufacturer not found: Cisco")

        nbk.ensure_device_manufacturer(create_manufacturer=True)
        self.assertIsInstance(nbk.nb_manufacturer, Manufacturer)
        self.assertEqual(nbk.nb_manufacturer.name, onboarding_kwargs["netdev_vendor"])

    def test_ensure_device_manufacturer_loose_missing(self):
        """Verify ensure_device_manufacturer function when Manufacturer object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_manufacturer(create_manufacturer=False)
            self.assertEqual(str(exc_info), "fail-config - ERROR manufacturer not found: Cisco")

        nbk.ensure_device_manufacturer(create_manufacturer=True)
        self.assertIsInstance(nbk.nb_manufacturer, Manufacturer)
        self.assertEqual(nbk.nb_manufacturer.name, onboarding_kwargs["netdev_vendor"])

    def test_ensure_device_type_strict_missing(self):
        """Verify ensure_device_type function when DeviceType object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = Manufacturer.objects.create(name="Cisco")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_device_type=False)
            self.assertEqual(str(exc_info), "fail-config - ERROR device type not found: CSR1000v")

        nbk.ensure_device_type(create_device_type=True)
        self.assertIsInstance(nbk.nb_device_type, DeviceType)
        self.assertEqual(nbk.nb_device_type.model, onboarding_kwargs["netdev_model"])

    def test_ensure_device_type_loose_missing(self):
        """Verify ensure_device_type function when DeviceType object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = Manufacturer.objects.create(name="Cisco")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_device_type=False)
            self.assertEqual(str(exc_info), "fail-config - ERROR device type not found: CSR1000v")

        nbk.ensure_device_type(create_device_type=True)
        self.assertIsInstance(nbk.nb_device_type, DeviceType)
        self.assertEqual(nbk.nb_device_type.model, onboarding_kwargs["netdev_model"])

    def test_ensure_device_type_strict_present(self):
        """Verify ensure_device_type function when DeviceType object is already present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        manufacturer = Manufacturer.objects.create(name="Juniper")

        device_type = DeviceType.objects.create(model="SRX3600", manufacturer=manufacturer)

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_name": device_type.model,
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = manufacturer

        nbk.ensure_device_type(create_device_type=False)
        self.assertEqual(nbk.nb_device_type, device_type)

    def test_ensure_device_type_loose_present(self):
        """Verify ensure_device_type function when DeviceType object is already present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        manufacturer = Manufacturer.objects.create(name="Juniper")

        device_type = DeviceType.objects.create(model="SRX3600", manufacturer=manufacturer)

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_name": device_type.model,
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = manufacturer

        nbk.ensure_device_type(create_device_type=False)
        self.assertEqual(nbk.nb_device_type, device_type)

    def test_ensure_device_role_not_exist(self):
        """Verify ensure_device_role function when Role does not already exist."""
        test_role_name = "mytestrole"

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": test_role_name,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_role(create_device_role=False)
            self.assertEqual(str(exc_info), f"fail-config - ERROR device role not found: {test_role_name}")

        nbk.ensure_device_role(create_device_role=True)
        self.assertIsInstance(nbk.nb_device_role, Role)
        self.assertEqual(nbk.nb_device_role.name, test_role_name)

    def test_ensure_device_role_exist(self):
        """Verify ensure_device_role function when Role exist but is not assigned to the OT."""
        device_role = Role.objects.create(name="Firewall")

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": device_role.name,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.ensure_device_role(create_device_role=False)

        self.assertEqual(nbk.nb_device_role, device_role)

    #
    def test_ensure_device_role_assigned(self):
        """Verify ensure_device_role function when Role exist and is already assigned."""
        device_role = Role.objects.create(name="Firewall")
        device_role.content_types.set([ContentType.objects.get_for_model(Device)])

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": device_role.name,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_location_name": self.site1,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.ensure_device_role(create_device_role=True)

        self.assertEqual(nbk.nb_device_role, device_role)

    def test_ensure_device_instance_not_exist(self):
        """Verify ensure_device_instance function."""
        serial_number = "123456"
        platform_name = "cisco_ios"
        hostname = "device1"

        onboarding_kwargs = {
            "netdev_hostname": hostname,
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": platform_name,
            "netdev_serial_number": serial_number,
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "GigaEthernet0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.name, hostname)

        device_status = Status.objects.get(
            content_types__in=[ContentType.objects.get_for_model(Device)], name=PLUGIN_SETTINGS["default_device_status"]
        )

        self.assertEqual(nbk.device.status, device_status)
        # self.assertEqual(nbk.device.platform.name, platform_slug) # TODO: What is this test doing?
        self.assertEqual(nbk.device.serial, serial_number)

    def test_ensure_device_instance_exist(self):
        """Verify ensure_device_instance function when the device already exists in Nautobot."""
        manufacturer = Manufacturer.objects.create(name="Cisco")

        role_content_type = ContentType.objects.get_for_model(Device)
        device_role, _ = Role.objects.get_or_create(name="Switch")
        device_role.content_types.set([role_content_type])

        device_type = DeviceType.objects.create(model="c2960", manufacturer=manufacturer)

        device_name = "test_name"

        planned_status = Status.objects.get(
            content_types__in=[ContentType.objects.get_for_model(Device)], name="Planned"
        )

        device = Device.objects.create(
            name=device_name,
            location=self.site1,
            device_type=device_type,
            role=device_role,
            status=planned_status,
            serial="987654",
        )

        onboarding_kwargs = {
            "netdev_hostname": device_name,
            "netdev_nb_role_name": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "GigaEthernet0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.pk, device.pk)

        self.assertEqual(nbk.device.name, device_name)
        self.assertEqual(nbk.device.platform.name, "cisco_ios")
        self.assertEqual(nbk.device.serial, "123456")

    def test_ensure_interface_not_exist(self):
        """Verify ensure_interface function when the interface does not exist."""
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "ge-0/0/0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.ensure_device()

        self.assertIsInstance(nbk.nb_mgmt_ifname, Interface)
        self.assertEqual(nbk.nb_mgmt_ifname.name, "ge-0/0/0")

    def test_ensure_interface_exist(self):
        """Verify ensure_interface function when the interface already exist."""
        manufacturer = Manufacturer.objects.create(name="Cisco")

        device_role, _ = Role.objects.get_or_create(name="Switch")
        device_role.content_types.set([ContentType.objects.get_for_model(Device)])

        device_type = DeviceType.objects.create(model="c2960", manufacturer=manufacturer)

        device_name = "test_name"
        netdev_mgmt_ifname = "GigaEthernet0"

        planned_status = Status.objects.get(
            content_types__in=[ContentType.objects.get_for_model(Device)], name="Planned"
        )

        device = Device.objects.create(
            name=device_name,
            location=self.site1,
            device_type=device_type,
            role=device_role,
            status=planned_status,
            serial="987654",
        )

        active_status = Status.objects.get(
            content_types__in=[ContentType.objects.get_for_model(Interface)], name="Active"
        )

        # TODO: Update to take from plugin default interface status setting
        intf = Interface.objects.create(
            name=netdev_mgmt_ifname,
            device=device,
            type=InterfaceTypeChoices.TYPE_OTHER,
            status=active_status,
        )

        onboarding_kwargs = {
            "netdev_hostname": device_name,
            "netdev_nb_role_name": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": netdev_mgmt_ifname,
            "netdev_mgmt_pflen": 24,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertEqual(nbk.nb_mgmt_ifname, intf)

    def test_ensure_primary_ip_not_exist(self):
        """Verify ensure_primary_ip function when the IP address do not already exist."""
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "ge-0/0/0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.ensure_device()

        self.assertIsInstance(nbk.nb_primary_ip, IPAddress)
        self.assertIn(nbk.nb_primary_ip, Interface.objects.get(device=nbk.device, name="ge-0/0/0").ip_addresses.all())
        self.assertEqual(nbk.device.primary_ip, nbk.nb_primary_ip)

    def test_ensure_device_platform_missing(self):
        """Verify ensure_device_platform function when Platform object is not present."""
        platform_name = "cisco_ios"

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
            "netdev_nb_platform_name": platform_name,
            "netdev_netmiko_device_type": platform_name,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_platform(create_platform_if_missing=False)
            self.assertEqual(str(exc_info), f"fail-config - ERROR device platform not found: {platform_name}")

        nbk.ensure_device_platform(create_platform_if_missing=True)
        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform.name, platform_name)

    def test_ensure_platform_present(self):
        """Verify ensure_device_platform function when Platform object is present."""
        platform_name = "juniper_junos"

        manufacturer = Manufacturer.objects.create(name="Juniper")

        device_type = DeviceType.objects.create(model="SRX3600", manufacturer=manufacturer)

        platform = Platform.objects.create(
            name=platform_name,
        )

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_name": device_type.model,
            "netdev_nb_location_name": self.site1,
            "netdev_nb_platform_name": platform_name,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device_platform(create_platform_if_missing=False)

        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform, platform)
        self.assertEqual(nbk.nb_platform.name, platform_name)

    def test_platform_map(self):
        """Verify platform mapping of netmiko to name functionality."""
        # Create static mapping
        PLUGIN_SETTINGS["platform_map"] = {"cisco_ios": "ios", "arista_eos": "eos", "cisco_nxos": "cisco-nxos"}

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device_platform(create_platform_if_missing=True)
        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform.name, PLUGIN_SETTINGS["platform_map"]["cisco_ios"])
        self.assertEqual(
            Platform.objects.get(name=PLUGIN_SETTINGS["platform_map"]["cisco_ios"]).name,
            PLUGIN_SETTINGS["platform_map"]["cisco_ios"],
        )

    def test_ensure_custom_fields(self):
        """Verify objects inherit default custom fields."""
        onboarding_kwargs = {
            "netdev_hostname": "sw1",
            "netdev_nb_role_name": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_location_name": self.site1.name,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.15",
            "netdev_mgmt_ifname": "Management0",
            "netdev_mgmt_pflen": 24,
            "netdev_nb_role_color": "ff0000",
        }

        nbk = NautobotKeeper(**onboarding_kwargs)
        nbk.ensure_device()

        device = Device.objects.get(name="sw1")

        self.assertEqual(device.cf["cf_device"], False)
        self.assertEqual("cf_device_null" in device.cf, False)
        self.assertEqual(device.platform.cf["cf_platform"], True)
        self.assertEqual(device.device_type.cf["cf_devicetype"], 5)
        self.assertEqual(device.role.cf["cf_devicerole"], 10)
        self.assertEqual(device.device_type.manufacturer.cf["cf_manufacturer"], "Foobar!")
        self.assertEqual(device.interfaces.get(name="Management0").cf["cf_interface"], "2016-06-23")
        self.assertEqual(device.primary_ip.cf["cf_ipaddress"], "http://example.com/")

    def test_ensure_secret_group_exist(self):
        "Verify secret group assignment to device when specified in plugin config."

        PLUGIN_SETTINGS["assign_secrets_group"] = True
        test_secret_group = SecretsGroup.objects.create(name="test_secret_group")

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_name": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_location_name": self.site1,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "GigaEthernet0",
            "netdev_nb_credentials": test_secret_group,
        }

        nbk = NautobotKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        nbk.ensure_secret_group()
        self.assertEqual(nbk.netdev_nb_credentials.name, test_secret_group.name)
