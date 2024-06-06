"""Nautobot Keeper."""

import ipaddress
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from nautobot.apps.choices import PrefixTypeChoices
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, Manufacturer, Platform
from nautobot.extras.models import Role, Status
from nautobot.extras.models.customfields import CustomField
from nautobot.ipam.models import IPAddress, Namespace, Prefix

from nautobot_device_onboarding.constants import NETMIKO_TO_NAPALM_STATIC
from nautobot_device_onboarding.exceptions import OnboardException

logger = logging.getLogger("rq.worker")

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


def ensure_default_cf(obj, model):
    """Update objects's default custom fields."""
    for field in CustomField.objects.get_for_model(model):
        if (field.default is not None) and (field.label not in obj.cf):
            obj.cf[field.label] = field.default

    try:
        obj.validated_save()
    except ValidationError as err:
        raise OnboardException(
            f"fail-general - ERROR: {obj} validation error: {err.messages}",
        ) from err


def object_match(obj, search_array):
    """Used to search models for multiple criteria.

    Inputs:
        obj:            The model used for searching.
        search_array:   Nested dictionaries used to search models. First criteria will be used
                        for strict searching. Loose searching will loop through the search_array
                        until it finds a match. Example below.
                        [
                            {"slug__iexact": 'switch1'},
                            {"model__iexact": 'Cisco'}
                        ]
    """
    try:
        result = obj.objects.get(**search_array[0])
        return result
    except obj.DoesNotExist:
        if PLUGIN_SETTINGS["object_match_strategy"] == "loose":
            for search_array_element in search_array[1:]:
                try:
                    result = obj.objects.get(**search_array_element)
                    return result
                except obj.DoesNotExist:
                    pass
                except obj.MultipleObjectsReturned as err:
                    raise OnboardException(
                        f"fail-general - ERROR multiple objects found in {str(obj)} searching on {str(search_array_element)})",
                    ) from err
        raise
    except obj.MultipleObjectsReturned as err:
        raise OnboardException(
            f"fail-general - ERROR multiple objects found in {str(obj)} searching on {str(search_array_element)})",
        ) from err


class NautobotKeeper:  # pylint: disable=too-many-instance-attributes
    """Used to manage the information relating to the network device within the Nautobot server."""

    def __init__(  # pylint: disable=R0913,R0914
        self,
        netdev_hostname,
        netdev_nb_role_name,
        netdev_vendor,
        netdev_nb_location_name,
        netdev_nb_device_type_name=None,
        netdev_model=None,
        netdev_nb_role_color="9e9e9e",
        netdev_mgmt_ip_address=None,
        netdev_nb_platform_name=None,
        netdev_serial_number=None,
        netdev_mgmt_ifname=None,
        netdev_mgmt_pflen=None,
        netdev_netmiko_device_type=None,
        onboarding_class=None,
        driver_addon_result=None,
        netdev_nb_credentials=None,
    ):
        """Create an instance and initialize the managed attributes that are used throughout the onboard processing.

        Args:
            netdev_hostname (str): Nautobot's device name
            netdev_nb_role_name (str): Nautobot's device role name
            netdev_vendor (str): Device's vendor name
            netdev_nb_location_name (str): Device site's slug
            netdev_nb_device_type_name (str): Device type's name
            netdev_model (str): Device's model
            netdev_nb_role_color (str): Nautobot device's role color
            netdev_mgmt_ip_address (str): IPv4 Address of a device
            netdev_nb_platform_name (str): Nautobot device's platform name
            netdev_serial_number (str): Device's serial number
            netdev_mgmt_ifname (str): Device's management interface name
            netdev_mgmt_pflen (str): Device's management IP prefix-len
            netdev_netmiko_device_type (str): Device's Netmiko device type
            onboarding_class (Object): Onboarding Class (future use)
            driver_addon_result (Any): Attached extended result (future use)
            netdev_nb_credentials (Object): Device's secrets group object
        """
        self.netdev_mgmt_ip_address = netdev_mgmt_ip_address
        self.netdev_nb_location_name = netdev_nb_location_name
        self.netdev_nb_device_type_name = netdev_nb_device_type_name
        self.netdev_nb_role_name = netdev_nb_role_name
        self.netdev_nb_role_color = netdev_nb_role_color
        self.netdev_nb_platform_name = netdev_nb_platform_name
        self.netdev_nb_credentials = netdev_nb_credentials

        self.netdev_hostname = netdev_hostname
        self.netdev_vendor = netdev_vendor
        self.netdev_model = netdev_model
        self.netdev_serial_number = netdev_serial_number
        self.netdev_mgmt_ifname = netdev_mgmt_ifname
        self.netdev_mgmt_pflen = netdev_mgmt_pflen
        self.netdev_netmiko_device_type = netdev_netmiko_device_type

        self.onboarding_class = onboarding_class
        self.driver_addon_result = driver_addon_result

        # these attributes are nautobot model instances as discovered/created
        # through the course of processing.
        self.nb_location = None
        self.nb_manufacturer = None
        self.nb_device_type = None
        self.nb_device_role = None
        self.nb_platform = None

        self.device = None
        self.onboarded_device = None
        self.nb_mgmt_ifname = None
        self.nb_primary_ip = None

    def ensure_onboarded_device(self):
        """Lookup if the device already exists in the Nautobot.

        Lookup is performed by querying for the IP address of the onboarded device.
        If the device with a given IP is already in Nautobot, its attributes including name could be updated
        """
        try:
            if self.netdev_mgmt_ip_address:
                self.onboarded_device = Device.objects.get(primary_ip4__host=self.netdev_mgmt_ip_address)
        except Device.DoesNotExist:
            logger.info(
                "Could not find existing Nautobot device for requested primary IP address (%s)",
                self.netdev_mgmt_ip_address,
            )
        except Device.MultipleObjectsReturned as err:
            raise OnboardException(
                f"fail-general - ERROR multiple devices using same IP in Nautobot: {self.netdev_mgmt_ip_address}",
            ) from err

    def ensure_device_site(self):
        """Ensure device's site."""
        try:
            self.nb_location = Location.objects.get(name=self.netdev_nb_location_name)
        except Location.DoesNotExist as err:
            raise OnboardException(f"fail-config - Site not found: {self.netdev_nb_location_name}") from err

    def ensure_device_manufacturer(
        self,
        create_manufacturer=PLUGIN_SETTINGS["create_manufacturer_if_missing"],
        skip_manufacturer_on_update=PLUGIN_SETTINGS["skip_manufacturer_on_update"],
    ):
        """Ensure device's manufacturer."""
        # Support to skip manufacturer updates for existing devices
        if self.onboarded_device and skip_manufacturer_on_update:
            self.nb_manufacturer = self.onboarded_device.device_type.manufacturer

            return

        # First ensure that the vendor, as extracted from the network device exists
        # in Nautobot.  We need the ID for this vendor when ensuring the DeviceType
        # instance.

        nb_manufacturer = self.netdev_vendor

        try:
            search_array = [{"name__iexact": nb_manufacturer}]
            self.nb_manufacturer = object_match(Manufacturer, search_array)
        except Manufacturer.DoesNotExist as err:
            if create_manufacturer:
                self.nb_manufacturer = Manufacturer.objects.create(name=self.netdev_vendor)
                ensure_default_cf(obj=self.nb_manufacturer, model=Manufacturer)
            else:
                raise OnboardException(f"fail-config - ERROR manufacturer not found: {self.netdev_vendor}") from err

    def ensure_device_type(
        self,
        create_device_type=PLUGIN_SETTINGS["create_device_type_if_missing"],
        skip_device_type_on_update=PLUGIN_SETTINGS["skip_device_type_on_update"],
    ):
        """Ensure the Device Type (slug) exists in Nautobot associated to the netdev "model" and "vendor" (manufacturer).

        Args:
          create_device_type (bool): Flag to indicate if we need to create the device_type, if not already present
          skip_device_type_on_update (bool): Flag to indicate if we skip device type updates for existing devices
        Raises:
          OnboardException('fail-config'):
            When the device vendor value does not exist as a Manufacturer in
            Nautobot.

          OnboardException('fail-config'):
            When the device-type exists by slug, but is assigned to a different
            manufacturer.  This should *not* happen, but guard-rail checking
            regardless in case two vendors have the same model name.
        """
        # Support to skip device type updates for existing devices
        if self.onboarded_device and skip_device_type_on_update:
            self.nb_device_type = self.onboarded_device.device_type

            return

        # Now see if the device type (slug) already exists,
        #  if so check to make sure that it is not assigned as a different manufacturer
        # if it doesn't exist, create it if the flag 'create_device_type_if_missing' is defined

        # Use declared device type or auto-discovered model
        nb_device_type_text = self.netdev_nb_device_type_name or self.netdev_model

        if not nb_device_type_text:
            raise OnboardException("fail-config - ERROR device type not found")

        nb_device_type_name = nb_device_type_text

        try:
            search_array = [
                {"model__iexact": nb_device_type_name},
                {"part_number__iexact": self.netdev_model},
            ]

            self.nb_device_type = object_match(DeviceType, search_array)

            if self.nb_device_type.manufacturer.id != self.nb_manufacturer.id:
                raise OnboardException(
                    f"fail-config - ERROR device type {self.netdev_model} "
                    f"already exists for vendor {self.netdev_vendor}",
                )

        except DeviceType.DoesNotExist as err:
            if create_device_type:
                logger.info("CREATE: device-type: %s", self.netdev_model)
                self.nb_device_type = DeviceType.objects.create(
                    model=nb_device_type_name,
                    manufacturer=self.nb_manufacturer,
                )
                ensure_default_cf(obj=self.nb_device_type, model=DeviceType)
            else:
                raise OnboardException(f"fail-config - ERROR device type not found: {self.netdev_model}") from err

    def ensure_device_role(
        self,
        create_device_role=PLUGIN_SETTINGS["create_device_role_if_missing"],
    ):
        """Ensure that the device role is defined / exist in Nautobot or create it if it doesn't exist.

        Args:
          create_device_role (bool) :Flag to indicate if we need to create the device_role, if not already present
        Raises:
          OnboardException('fail-config'):
            When the device role value does not exist
            Nautobot.
        """
        try:
            self.nb_device_role = Role.objects.get(name=self.netdev_nb_role_name)
        except Role.DoesNotExist as err:
            if create_device_role:
                self.nb_device_role = Role.objects.create(
                    name=self.netdev_nb_role_name,
                    color=self.netdev_nb_role_color,
                )
                self.nb_device_role.validated_save()
                self.nb_device_role.content_types.set([ContentType.objects.get_for_model(Device)])
                ensure_default_cf(obj=self.nb_device_role, model=Role)
            else:
                raise OnboardException(
                    f"fail-config - ERROR device role not found: {self.netdev_nb_role_name}"
                ) from err

    def ensure_device_platform(self, create_platform_if_missing=PLUGIN_SETTINGS["create_platform_if_missing"]):
        """Get platform object from Nautobot filtered by platform_slug.

        Args:
            create_platform_if_missing (bool): Flag to indicate if we need to create the platform, if not already present

        Return:
            nautobot.dcim.models.Platform object

        Raises:
            OnboardException

        Lookup is performed based on the object's slug field (not the name field)
        """
        try:
            self.netdev_nb_platform_name = (
                self.netdev_nb_platform_name
                or PLUGIN_SETTINGS["platform_map"].get(self.netdev_netmiko_device_type)
                or self.netdev_netmiko_device_type
            )

            if not self.netdev_nb_platform_name:
                raise OnboardException(f"fail-config - ERROR device platform not found: {self.netdev_hostname}")

            self.nb_platform = Platform.objects.get(name=self.netdev_nb_platform_name)

            if not self.nb_platform:
                Platform.objects.get(network_driver=self.netdev_nb_platform_name)

            logger.info("PLATFORM: found in Nautobot %s", self.netdev_nb_platform_name)

        except Platform.DoesNotExist as err:
            if create_platform_if_missing:
                platform_to_napalm_nautobot = {
                    platform: platform.napalm_driver for platform in Platform.objects.all() if platform.napalm_driver
                }

                # Update Constants if Napalm driver is defined for Nautobot Platform
                netmiko_to_napalm = {**NETMIKO_TO_NAPALM_STATIC, **platform_to_napalm_nautobot}

                self.nb_platform = Platform.objects.create(
                    name=self.netdev_nb_platform_name,
                    napalm_driver=netmiko_to_napalm[self.netdev_netmiko_device_type],
                    network_driver=self.netdev_netmiko_device_type,
                )
                ensure_default_cf(obj=self.nb_platform, model=Platform)
            else:
                raise OnboardException(
                    f"fail-general - ERROR platform not found in Nautobot: {self.netdev_nb_platform_name}",
                ) from err

    def ensure_device_instance(self, default_status=PLUGIN_SETTINGS["default_device_status"]):
        """Ensure that the device instance exists in Nautobot and is assigned the provided device role or DEFAULT_ROLE.

        Args:
          default_status (str) : status assigned to a new device by default.
        """
        if self.onboarded_device:
            # Construct lookup arguments if onboarded device already exists in Nautobot

            logger.info(
                "Found existing Nautobot device (%s) for requested primary IP address (%s)",
                self.onboarded_device.name,
                self.netdev_mgmt_ip_address,
            )
            lookup_args = {
                "pk": self.onboarded_device.pk,
                "defaults": {
                    "name": self.netdev_hostname,
                    "device_type": self.nb_device_type,
                    "device_role": self.nb_device_role,
                    "platform": self.nb_platform,
                    "site": self.nb_location,
                    "serial": self.netdev_serial_number,
                    # "status":  field is not updated in case of already existing devices to prevent changes
                },
            }
        else:
            # Construct lookup arguments if onboarded device does not exist in Nautobot
            ct = ContentType.objects.get_for_model(Device)  # pylint: disable=invalid-name
            try:
                device_status = Status.objects.get(content_types__in=[ct], name=default_status)
            except Status.DoesNotExist as err:
                raise OnboardException(
                    f"fail-general - ERROR could not find existing device status: {default_status}",
                ) from err
            except Status.MultipleObjectsReturned as err:
                raise OnboardException(
                    f"fail-general - ERROR multiple device status using same name: {default_status}",
                ) from err

            lookup_args = {
                "name": self.netdev_hostname,
                "defaults": {
                    "device_type": self.nb_device_type,
                    "role": self.nb_device_role,
                    "platform": self.nb_platform,
                    "location": self.nb_location,
                    "serial": self.netdev_serial_number,
                    # `status` field is defined only for new devices, no update for existing should occur
                    "status": device_status,
                },
            }

        try:
            self.device, created = Device.objects.update_or_create(**lookup_args)
            ensure_default_cf(obj=self.device, model=Device)

            if created:
                logger.info("CREATED device: %s", self.netdev_hostname)
            else:
                logger.info("GOT/UPDATED device: %s", self.netdev_hostname)

        except Device.MultipleObjectsReturned as err:
            raise OnboardException(
                f"fail-general - ERROR multiple devices using same name in Nautobot: {self.netdev_hostname}",
            ) from err

    def ensure_interface(self):
        """Ensures that the interface associated with the mgmt_ipaddr exists and is assigned to the device."""
        if self.netdev_mgmt_ifname:
            mgmt_only_setting = PLUGIN_SETTINGS["set_management_only_interface"]

            # TODO: Add option for default interface status
            self.nb_mgmt_ifname, _ = Interface.objects.get_or_create(
                name=self.netdev_mgmt_ifname,
                device=self.device,
                defaults={
                    "type": InterfaceTypeChoices.TYPE_OTHER,
                    "status": Status.objects.get(name="Active"),
                    "mgmt_only": mgmt_only_setting,
                },
            )
            if mgmt_only_setting:
                self.nb_mgmt_ifname.mgmt_only = mgmt_only_setting
                self.nb_mgmt_ifname.validated_save()

            ensure_default_cf(obj=self.nb_mgmt_ifname, model=Interface)

    def ensure_primary_ip(self):
        """Ensure mgmt_ipaddr exists in IPAM, has the device interface, and is assigned as the primary IP address."""
        # see if the primary IP address exists in IPAM
        if self.netdev_mgmt_ip_address and self.netdev_mgmt_pflen:
            ct = ContentType.objects.get_for_model(IPAddress)  # pylint: disable=invalid-name
            default_status_name = PLUGIN_SETTINGS["default_ip_status"]
            try:
                ip_status = Status.objects.get(content_types__in=[ct], name=default_status_name)
            except Status.DoesNotExist as err:
                raise OnboardException(
                    f"fail-general - ERROR could not find existing IP Address status: {default_status_name}",
                ) from err
            except Status.MultipleObjectsReturned as err:
                raise OnboardException(
                    f"fail-general - ERROR multiple IP Address status using same name: {default_status_name}",
                ) from err

            # Default to Global Namespace -> TODO: add option to specify default namespace
            namespace = Namespace.objects.get(name="Global")

            prefix = ipaddress.ip_interface(f"{self.netdev_mgmt_ip_address}/{self.netdev_mgmt_pflen}")

            nautobot_prefix, _ = Prefix.objects.get_or_create(
                prefix=f"{prefix.network}",
                namespace=namespace,
                type=PrefixTypeChoices.TYPE_NETWORK,
                defaults={"status": ip_status},
            )
            self.nb_primary_ip, created = IPAddress.objects.get_or_create(
                address=f"{self.netdev_mgmt_ip_address}/{self.netdev_mgmt_pflen}",
                parent=nautobot_prefix,
                defaults={"status": ip_status, "type": "host"},
            )

            ensure_default_cf(obj=self.nb_primary_ip, model=IPAddress)

            if created or self.nb_primary_ip not in self.nb_mgmt_ifname.ip_addresses.all():
                logger.info("ASSIGN: IP address %s to %s", self.nb_primary_ip.address, self.nb_mgmt_ifname.name)
                self.nb_mgmt_ifname.ip_addresses.add(self.nb_primary_ip)
                self.nb_mgmt_ifname.full_clean()
                self.nb_mgmt_ifname.save()

            # Ensure the primary IP is assigned to the device
            self.device.primary_ip4 = self.nb_primary_ip
            self.device.full_clean()
            self.device.save()

    def ensure_secret_group(self):
        """Optionally assign secret group from onboarding to created/updated device."""
        if PLUGIN_SETTINGS["assign_secrets_group"]:
            self.device.secrets_group = self.netdev_nb_credentials
            self.device.validated_save()

    def ensure_device(self):
        """Ensure that the device represented by the DevNetKeeper exists in the Nautobot system."""
        self.ensure_onboarded_device()
        self.ensure_device_site()
        self.ensure_device_manufacturer()
        self.ensure_device_type()
        self.ensure_device_role()
        self.ensure_device_platform()
        self.ensure_device_instance()

        if PLUGIN_SETTINGS["create_management_interface_if_missing"]:
            self.ensure_interface()
            self.ensure_primary_ip()

        if PLUGIN_SETTINGS["assign_secrets_group"]:
            self.ensure_secret_group()
