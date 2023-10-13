"""Django views for device onboarding."""
from nautobot.apps.views import (
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectDetailViewMixin,
    ObjectBulkCreateViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectNotesViewMixin,
)

from nautobot_device_onboarding.filters import OnboardingTaskFilterSet
from nautobot_device_onboarding.forms import OnboardingTaskForm, OnboardingTaskFilterForm
from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.tables import OnboardingTaskTable

from nautobot_device_onboarding.api.serializers import OnboardingTaskSerializer


class OnboardingTaskUIViewSet(
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectDetailViewMixin,
    ObjectBulkCreateViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectNotesViewMixin,
):  # pylint: disable=abstract-method
    """UI Viewset for Onboarding."""

    filterset_class = OnboardingTaskFilterSet
    filterset_form_class = OnboardingTaskFilterForm
    form_class = OnboardingTaskForm
    queryset = OnboardingTask.objects.all()
    serializer_class = OnboardingTaskSerializer
    table_class = OnboardingTaskTable
    action_buttons = ["add", "export", "import"]
    # pylint disable=abstract-method
