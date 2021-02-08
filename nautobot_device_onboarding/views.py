"""Django views for device onboarding.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging

from django.shortcuts import get_object_or_404, render

from nautobot.core.views import generic

from .filters import OnboardingTaskFilter
from .forms import OnboardingTaskForm, OnboardingTaskFilterForm, OnboardingTaskFeedCSVForm
from .models import OnboardingTask
from .tables import OnboardingTaskTable, OnboardingTaskFeedBulkTable


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

    queryset = OnboardingTask.objects.all().order_by("-id")
    filterset = OnboardingTaskFilter
    filterset_form = OnboardingTaskFilterForm
    table = OnboardingTaskTable
    template_name = "nautobot_device_onboarding/onboarding_tasks_list.html"


class OnboardingTaskCreateView(generic.ObjectEditView):
    """View for creating a new OnboardingTask."""

    model = OnboardingTask
    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskForm
    template_name = "nautobot_device_onboarding/onboarding_task_edit.html"
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"


class OnboardingTaskBulkDeleteView(generic.BulkDeleteView):
    """View for deleting one or more OnboardingTasks."""

    queryset = OnboardingTask.objects.filter()  # TODO: can we exclude currently-running tasks?
    table = OnboardingTaskTable
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"


class OnboardingTaskFeedBulkImportView(generic.BulkImportView):
    """View for bulk-importing a CSV file to create OnboardingTasks."""

    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskFeedCSVForm
    table = OnboardingTaskFeedBulkTable
    default_return_url = "plugins:nautobot_device_onboarding:onboardingtask_list"
