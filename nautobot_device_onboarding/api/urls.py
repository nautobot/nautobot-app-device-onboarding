"""REST API URLs for device onboarding."""

from rest_framework import routers
from nautobot_device_onboarding.api.views import OnboardingTaskView

router = routers.DefaultRouter()

router.register(r"onboarding", OnboardingTaskView)

urlpatterns = router.urls
