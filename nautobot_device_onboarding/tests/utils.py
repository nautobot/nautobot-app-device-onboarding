"""Utilities for easier testing."""

from django.contrib.contenttypes.models import ContentType
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
)
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Role, Secret, SecretsGroup, SecretsGroupAssociation, Status
from nautobot.ipam.choices import IPAddressTypeChoices, PrefixTypeChoices
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Namespace, Prefix


#TODO Update this for testing Network Importer
# def sync_network_data_ensure_required_nautobot_objects():
#     """Ensure the requied Nautobot objects needed for testing exist."""
#     status, _ = Status.objects.get_or_create(name="Active")
#     status.content_types.add(ContentType.objects.get_for_model(Device))
#     status.content_types.add(ContentType.objects.get_for_model(Prefix))
#     status.content_types.add(ContentType.objects.get_for_model(IPAddress))
#     status.content_types.add(ContentType.objects.get_for_model(Location))
#     status.content_types.add(ContentType.objects.get_for_model(Interface))
#     status.content_types.add(ContentType.objects.get_for_model(Interface))
#     status.validated_save()

#     username_secret, _ = Secret.objects.get_or_create(
#         name="username", provider="environment-variable", parameters={"variable": "DEVICE_USER"}
#     )
#     password_secret, _ = Secret.objects.get_or_create(
#         name="password", provider="environment-variable", parameters={"variable": "DEVICE_PASS"}
#     )
#     secrets_group, _ = SecretsGroup.objects.get_or_create(name="test secrets group")
#     SecretsGroupAssociation.objects.get_or_create(
#         secrets_group=secrets_group,
#         secret=username_secret,
#         access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
#         secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
#     )
#     SecretsGroupAssociation.objects.get_or_create(
#         secrets_group=secrets_group,
#         secret=password_secret,
#         access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
#         secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
#     )

#     namespace, _ = Namespace.objects.get_or_create(name="Global")

#     prefix, _ = Prefix.objects.get_or_create(
#         prefix="1.1.1.0/24",
#         namespace=namespace,
#         type=PrefixTypeChoices.TYPE_NETWORK,
#         status=status,
#     )
#     ip_address, _ = IPAddress.objects.get_or_create(
#         host="1.1.1.1", mask_length=24, type=IPAddressTypeChoices.TYPE_HOST, status=status
#     )

#     location_type, _ = LocationType.objects.get_or_create(name="Site")
#     location_type.content_types.add(ContentType.objects.get_for_model(Device))
#     location_type.validated_save()
#     location, _ = Location.objects.get_or_create(name="Site A", location_type=location_type, status=status)

#     device_role, _ = Role.objects.get_or_create(name="Network")
#     device_role.content_types.add(ContentType.objects.get_for_model(Device))
#     device_role.validated_save()

#     manufacturer, _ = Manufacturer.objects.get_or_create(name="Cisco")

#     platform, _ = Platform.objects.get_or_create(
#         name="cisco_ios", network_driver="cisco_ios", manufacturer=manufacturer
#     )

#     device_type, _ = DeviceType.objects.get_or_create(model="test_model_123", manufacturer=manufacturer)
#     device, _ = Device.objects.get_or_create(
#         name="test_device",
#         serial="ABC123456EF",
#         device_type=device_type,
#         status=status,
#         location=location,
#         role=device_role,
#         platform=platform,
#         secrets_group=secrets_group,
#     )
#     interface, _ = Interface.objects.get_or_create(
#         device=device, name="int0", status=status, type=InterfaceTypeChoices.TYPE_VIRTUAL
#     )
#     ip_address_to_interface, _ = IPAddressToInterface.objects.get_or_create(interface=interface, ip_address=ip_address)
#     device.primary_ip4 = ip_address
#     device.validated_save()
#     return True

def sync_devices_ensure_required_nautobot_objects():
    """Ensure the requied Nautobot objects needed for testing exist."""
    testing_objects = {}

    status, _ = Status.objects.get_or_create(name="Active")
    status.content_types.add(ContentType.objects.get_for_model(Device))
    status.content_types.add(ContentType.objects.get_for_model(Prefix))
    status.content_types.add(ContentType.objects.get_for_model(IPAddress))
    status.content_types.add(ContentType.objects.get_for_model(Location))
    status.content_types.add(ContentType.objects.get_for_model(Interface))
    status.content_types.add(ContentType.objects.get_for_model(Interface))
    status.validated_save()

    username_secret, _ = Secret.objects.get_or_create(
        name="username", provider="environment-variable", parameters={"variable": "DEVICE_USER"}
    )
    password_secret, _ = Secret.objects.get_or_create(
        name="password", provider="environment-variable", parameters={"variable": "DEVICE_PASS"}
    )
    secrets_group, _ = SecretsGroup.objects.get_or_create(name="test secrets group")
    SecretsGroupAssociation.objects.get_or_create(
        secrets_group=secrets_group,
        secret=username_secret,
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
    )
    SecretsGroupAssociation.objects.get_or_create(
        secrets_group=secrets_group,
        secret=password_secret,
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
    )

    namespace, _ = Namespace.objects.get_or_create(name="Global")

    location_type, _ = LocationType.objects.get_or_create(name="Site")
    location_type.content_types.add(ContentType.objects.get_for_model(Device))
    location_type.validated_save()
    location, _ = Location.objects.get_or_create(name="Site A", location_type=location_type, status=status)

    device_role, _ = Role.objects.get_or_create(name="Network")
    device_role.content_types.add(ContentType.objects.get_for_model(Device))
    device_role.validated_save()

    testing_objects["status"] = status
    testing_objects["secrets_group"] = secrets_group
    testing_objects["namespace"] = namespace
    testing_objects["location"] = location
    testing_objects["device_role"] = device_role

    return testing_objects