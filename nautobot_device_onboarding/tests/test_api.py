"""Unit tests for nautobot_device_onboarding REST API."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from nautobot.users.models import Token
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status

from nautobot_device_onboarding.models import OnboardingTask

User = get_user_model()


class OnboardingTaskTestCase(TestCase):
    """Test the OnboardingTask API."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.user = User.objects.create(username="testuser", is_superuser=True)
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.base_url_lookup = "plugins-api:nautobot_device_onboarding-api:onboardingtask"

        active = Status.objects.get(name="Active")
        location_type = LocationType.objects.create(name="site")

        self.site1 = Location.objects.create(name="USWEST", location_type=location_type, status=active)

        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", location=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", location=self.site1)

    def test_list_onboarding_tasks(self):
        """Verify that OnboardingTasks can be listed."""
        url = reverse(f"{self.base_url_lookup}-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_get_onboarding_task(self):
        """Verify that an Onboardingtask can be retrieved."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk}) + "?depth=1"

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ip_address"], self.onboarding_task1.ip_address)
        self.assertEqual(response.data["location"], self.onboarding_task1.location.name)

    def test_create_task_missing_mandatory_parameters(self):
        """Verify that the only mandatory POST parameters are ip_address and site."""
        url = reverse(f"{self.base_url_lookup}-list")

        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response tells us which fields are missing from the request
        self.assertIn("ip_address", response.data)
        self.assertIn("location", response.data)
        self.assertEqual(len(response.data), 2, "Only two parameters should be mandatory")

    def test_create_task(self):
        """Verify that an OnboardingTask can be created."""
        url = reverse(f"{self.base_url_lookup}-list")
        data = {"ip_address": "10.10.10.20", "location": self.site1.name}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["port"], 22)  # default value
        self.assertEqual(response.data["timeout"], 30)  # default value

        onboarding_task = OnboardingTask.objects.get(pk=response.data["id"])
        self.assertEqual(onboarding_task.ip_address, data["ip_address"])
        self.assertEqual(onboarding_task.location.id, self.site1.id)

    def test_update_task_forbidden(self):
        """Verify that an OnboardingTask cannot be updated via this API."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk})

        response = self.client.patch(url, {"ip_address": "10.10.10.20"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.onboarding_task1.ip_address, "10.10.10.10")

        response = self.client.put(url, {"ip_address": "10.10.10.20"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.onboarding_task1.ip_address, "10.10.10.10")

    def test_delete_task(self):
        """Verify that an OnboardingTask can be deleted."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(OnboardingTask.DoesNotExist):
            OnboardingTask.objects.get(pk=self.onboarding_task1.pk)
