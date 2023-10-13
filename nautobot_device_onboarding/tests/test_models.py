"""Unit tests for nautobot_device_onboarding OnboardingDevice model."""
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Location, LocationType, DeviceType, Manufacturer, Device, Interface
from nautobot.extras.models import Role
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.extras.models import Status

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.models import OnboardingDevice
from nautobot_device_onboarding.choices import OnboardingStatusChoices


class OnboardingDeviceModelTestCase(TestCase):
    """Test the Onboarding models."""

    def setUp(self):
        """Setup objects for Onboarding Model tests."""
        status = Status.objects.get(name="Active")
        location_type = LocationType.objects.create(name="site")

        self.site = Location.objects.create(name="USWEST", location_type=location_type, status=status)
        manufacturer = Manufacturer.objects.create(name="Juniper")
        device_content_type = ContentType.objects.get_for_model(model=Device)
        device_role = Role.objects.create(name="Firewall")
        device_role.content_types.set([device_content_type])
        device_type = DeviceType.objects.create(model="SRX3600", manufacturer=manufacturer)

        self.device = Device.objects.create(
            device_type=device_type,
            name="device1",
            role=device_role,
            location=self.site,
            status=status,
        )

        intf = Interface.objects.create(name="test_intf", device=self.device, status=status)

        namespace = Namespace.objects.get(name="Global")

        Prefix.objects.create(prefix="10.10.10.0/24", namespace=namespace, status=status)

        primary_ip = IPAddress.objects.create(address="10.10.10.10/32", status=status, type="Host", namespace=namespace)
        intf.ip_addresses.add(primary_ip)

        self.device.primary_ip4 = primary_ip
        self.device.save()

        self.succeeded_task1 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            location=self.site,
            status=OnboardingStatusChoices.STATUS_SUCCEEDED,
            created_device=self.device,
        )

        self.succeeded_task2 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            location=self.site,
            status=OnboardingStatusChoices.STATUS_SUCCEEDED,
            created_device=self.device,
        )

        self.failed_task1 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            location=self.site,
            status=OnboardingStatusChoices.STATUS_FAILED,
            created_device=self.device,
        )

        self.failed_task2 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            location=self.site,
            status=OnboardingStatusChoices.STATUS_FAILED,
            created_device=self.device,
        )

    def test_onboardingdevice_autocreated(self):
        """Verify that OnboardingDevice is auto-created."""
        onboarding_device = OnboardingDevice.objects.get(device=self.device)
        self.assertEqual(self.device, onboarding_device.device)

    def test_last_check_attempt_date(self):
        """Verify OnboardingDevice last attempt."""
        onboarding_device = OnboardingDevice.objects.get(device=self.device)
        self.assertEqual(onboarding_device.last_check_attempt_date, self.failed_task2.created)

    def test_last_check_successful_date(self):
        """Verify OnboardingDevice last success."""
        onboarding_device = OnboardingDevice.objects.get(device=self.device)
        self.assertEqual(onboarding_device.last_check_successful_date, self.succeeded_task2.created)

    def test_status(self):
        """Verify OnboardingDevice status."""
        onboarding_device = OnboardingDevice.objects.get(device=self.device)
        self.assertEqual(onboarding_device.status, self.failed_task2.status)

    def test_last_ot(self):
        """Verify OnboardingDevice last ot."""
        onboarding_device = OnboardingDevice.objects.get(device=self.device)
        self.assertEqual(onboarding_device.last_ot, self.failed_task2)

    def test_tasks_labels(self):
        """Verify created tasks are with labels following creation order."""
        for index, task_object in enumerate(OnboardingTask.objects.order_by("last_updated"), start=1):
            self.assertEqual(index, task_object.label)
