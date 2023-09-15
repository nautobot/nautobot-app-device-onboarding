"""REST API URLs for device onboarding."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_device_onboarding.api import views

router = OrderedDefaultRouter()
router.register("onboarding", views.OnboardingTaskViewSet)


app_name = "nautobot_device_onboarding-api"
urlpatterns = router.urls
