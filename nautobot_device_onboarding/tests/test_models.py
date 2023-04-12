"""Unit tests for nautobot_device_onboarding OnboardingDevice model."""
from django.test import TestCase

from nautobot.dcim.models import Site, DeviceRole, DeviceType, Manufacturer, Device, Interface
from nautobot.ipam.models import IPAddress

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.models import OnboardingDevice
from nautobot_device_onboarding.choices import OnboardingStatusChoices, OnboardingFailChoices

from django.db.utils import DataError


class OnboardingDeviceModelTestCase(TestCase):
    """Test the Onboarding models."""

    def setUp(self):
        """Setup objects for Onboarding Model tests."""
        self.site = Site.objects.create(name="USWEST", slug="uswest")
        manufacturer = Manufacturer.objects.create(name="Juniper", slug="juniper")
        device_role = DeviceRole.objects.create(name="Firewall", slug="firewall")
        self.device_type = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=manufacturer)

        self.device = Device.objects.create(
            device_type=self.device_type,
            name="device1",
            device_role=device_role,
            site=self.site,
        )

        intf = Interface.objects.create(name="test_intf", device=self.device)

        primary_ip = IPAddress.objects.create(address="10.10.10.10/32")
        intf.ip_addresses.add(primary_ip)

        self.device.primary_ip4 = primary_ip
        self.device.save()

        self.succeeded_task1 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            site=self.site,
            status=OnboardingStatusChoices.STATUS_SUCCEEDED,
            created_device=self.device,
        )

        self.succeeded_task2 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            site=self.site,
            status=OnboardingStatusChoices.STATUS_SUCCEEDED,
            created_device=self.device,
        )

        self.failed_task1 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            site=self.site,
            status=OnboardingStatusChoices.STATUS_FAILED,
            created_device=self.device,
        )

        self.failed_task2 = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            site=self.site,
            status=OnboardingStatusChoices.STATUS_FAILED,
            created_device=self.device,
        )

    def create_onboarding_task(self, port):
        """Helper to create device onboarding task with specific port."""
        task = OnboardingTask.objects.create(
            ip_address="10.10.10.10",
            site=self.site,
            created_device=self.device,
            device_type=self.device_type,
            status=OnboardingStatusChoices.STATUS_FAILED,
            failed_reason=OnboardingFailChoices.FAIL_GENERAL,
            port=port,
        )
        task.validated_save()



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
        for index, task_object in enumerate(OnboardingTask.objects.order_by("created"), start=1):
            self.assertEqual(index, task_object.label)

    def test_port_min(self):
        """Verify task fails when port is under 1."""
        self.assertRaises(DataError, self.create_onboarding_task, -1)

    def test_port_max(self):
        """Verify task fails when port is over 65535."""
        self.assertRaises(DataError, self.create_onboarding_task, 65536)

    def test_port_valid(self):
        """Verify task succeeds when port is between 1 and 65535."""
        self.create_onboarding_task(443)
