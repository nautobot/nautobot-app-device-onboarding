"""Django urlpatterns declaration for nautobot_device_onboarding plugin."""
from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.views import OnboardingTaskUIViewSet
# from nautobot_device_onboarding.views import (
#     OnboardingTaskView,
#     OnboardingTaskListView,
#     OnboardingTaskCreateView,
#     OnboardingTaskBulkDeleteView,
# )

router = NautobotUIViewSetRouter()

router.register("onboardingtask", OnboardingTaskUIViewSet)

urlpatterns = []

urlpatterns += router.urls

# urlpatterns = [
#     path("", OnboardingTaskListView.as_view(), name="onboardingtask_list"),
#     path("<uuid:pk>/", OnboardingTaskView.as_view(), name="onboardingtask"),
#     path("add/", OnboardingTaskCreateView.as_view(), name="onboardingtask_add"),
#     path("delete/", OnboardingTaskBulkDeleteView.as_view(), name="onboardingtask_bulk_delete"),
#     # path("import/", OnboardingTaskFeedBulkImportView.as_view(), name="onboardingtask_import"),
#     path(
#         "<uuid:pk>/changelog/",
#         ObjectChangeLogView.as_view(),
#         name="onboardingtask_changelog",
#         kwargs={"model": OnboardingTask},
#     ),
# ]
