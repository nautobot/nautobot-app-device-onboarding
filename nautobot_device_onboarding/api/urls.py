"""REST API URLs for device onboarding."""

# from rest_framework import routers
# from nautobot_device_onboarding.api.views import OnboardingTaskView

# router = routers.DefaultRouter()

# router.register(r"onboarding", OnboardingTaskView)

# urlpatterns = router.urls

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_device_onboarding.api import views

router = OrderedDefaultRouter()
router.register("onboarding", views.OnboardingTaskView)


app_name = "nautobot_device_onboarding-api"
urlpatterns = router.urls