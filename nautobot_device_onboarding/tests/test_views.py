"""Unit tests for nautobot_device_onboarding views."""
from nautobot.dcim.models import Location
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
        site = Location.objects.create(name="USWEST")
        OnboardingTask.objects.create(ip_address="10.10.10.10", location=site)
        OnboardingTask.objects.create(ip_address="192.168.1.1", location=site)

        cls.form_data = {
            "site": site.pk,
            "ip_address": "192.0.2.99",
            "port": 22,
            "timeout": 30,
        }

        cls.csv_data = (
            "site,ip_address",
            "uswest,10.10.10.10",
            "uswest,10.10.10.20",
            "uswest,10.10.10.30",
        )

    def test_has_advanced_tab(self):
        """Overwrite the test as OnboardingTask doesn't have advanced tab."""

    def test_list_objects_unknown_filter_no_strict_filtering(self):
        """Overwrite the test as strict filtering."""

    def test_list_objects_unknown_filter_strict_filtering(self):
        """Overwrite the test as strict filtering option yet."""
