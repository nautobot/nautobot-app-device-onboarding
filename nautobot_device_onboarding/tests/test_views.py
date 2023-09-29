"""Unit tests for nautobot_device_onboarding views."""
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.models import Status
from nautobot.core.testing import ViewTestCases

from nautobot_device_onboarding.models import OnboardingTask


class OnboardingTestCase(  # pylint: disable=no-member,too-many-ancestors
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
):
    """Test the OnboardingTask views."""

    def _get_base_url(self):
        return f"plugins:{self.model._meta.app_label}:{self.model._meta.model_name}_" + "{}"

    model = OnboardingTask

    @classmethod
    def setUpTestData(cls):  # pylint: disable=invalid-name
        """Setup test data."""
        status = Status.objects.get(name="Active")
        location_type = LocationType.objects.create(name="site")
        location_type.content_types.set([ContentType.objects.get_for_model(Device)])
        site = Location.objects.create(name="USWEST", location_type=location_type, status=status)
        OnboardingTask.objects.create(ip_address="10.10.10.10", location=site)
        OnboardingTask.objects.create(ip_address="192.168.1.1", location=site)
        OnboardingTask.objects.create(ip_address="172.16.128.1", location=site)

        cls.form_data = {
            "location": site.pk,
            "ip_address": "192.0.2.99",
            "port": 22,
            "timeout": 30,
        }

        cls.csv_data = (
            "ip_address,location",
            "10.10.10.10,USWEST",
            "10.10.10.20,USWEST",
            "10.10.10.30,USWEST",
        )

    def test_has_advanced_tab(self):
        """Overwrite the test as OnboardingTask doesn't have advanced tab."""

    def test_list_objects_unknown_filter_no_strict_filtering(self):
        """Overwrite the test as strict filtering."""

    def test_list_objects_unknown_filter_strict_filtering(self):
        """Overwrite the test as strict filtering option yet."""
