"""Django urlpatterns declaration for nautobot_device_onboarding plugin."""
from django.urls import path
from nautobot.extras.views import ObjectChangeLogView

from .models import OnboardingTask
from .views import (
    OnboardingTaskView,
    OnboardingTaskListView,
    OnboardingTaskCreateView,
    OnboardingTaskBulkDeleteView,
    OnboardingTaskFeedBulkImportView,
)

urlpatterns = [
    path("", OnboardingTaskListView.as_view(), name="onboardingtask_list"),
    path("<uuid:pk>/", OnboardingTaskView.as_view(), name="onboardingtask"),
    path("add/", OnboardingTaskCreateView.as_view(), name="onboardingtask_add"),
    path("delete/", OnboardingTaskBulkDeleteView.as_view(), name="onboardingtask_bulk_delete"),
    path("import/", OnboardingTaskFeedBulkImportView.as_view(), name="onboardingtask_import"),
    path(
        "<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="onboardingtask_changelog",
        kwargs={"model": OnboardingTask},
    ),
]
