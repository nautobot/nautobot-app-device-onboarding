"""Django views for device onboarding."""

from django.shortcuts import get_object_or_404, render

from nautobot.core.views import generic

from nautobot_device_onboarding.filters import OnboardingTaskFilterSet
from nautobot_device_onboarding.forms import OnboardingTaskForm, OnboardingTaskFilterForm, OnboardingTaskFeedCSVForm
from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.tables import OnboardingTaskTable, OnboardingTaskFeedBulkTable


class OnboardingTaskView(generic.ObjectView):
    """View for presenting a single OnboardingTask."""

    queryset = OnboardingTask.objects.all()

    def get(self, request, pk):  # pylint: disable=invalid-name, arguments-differ
        """Get request."""
        instance = get_object_or_404(self.queryset, pk=pk)

        return render(
            request, "nautobot_device_onboarding/onboardingtask.html", {"object": instance, "onboardingtask": instance}
        )


class OnboardingTaskListView(generic.ObjectListView):
    """View for listing all extant OnboardingTasks."""

    queryset = OnboardingTask.objects.all().order_by("-label")
    filterset = OnboardingTaskFilterSet
    filterset_form = OnboardingTaskFilterForm
    table = OnboardingTaskTable


class OnboardingTaskCreateView(generic.ObjectEditView):
    """View for creating a new OnboardingTask."""

    model = OnboardingTask
    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskForm
    template_name = "nautobot_device_onboarding/onboarding_task_edit.html"
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"


class OnboardingTaskBulkDeleteView(generic.BulkDeleteView):
    """View for deleting one or more OnboardingTasks."""

    queryset = OnboardingTask.objects.filter().exclude(status="running")
    table = OnboardingTaskTable
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"


class OnboardingTaskFeedBulkImportView(generic.BulkImportView):
    """View for bulk-importing a CSV file to create OnboardingTasks."""

    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskFeedCSVForm
    table = OnboardingTaskFeedBulkTable
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"
