"""Django urlpatterns declaration for nautobot_device_onboarding app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

# Uncomment the following line if you have views to import
# from nautobot_device_onboarding import views


app_name = "nautobot_device_onboarding"
router = NautobotUIViewSetRouter()

# Here is an example of how to register a viewset, you will want to replace views.NautobotDeviceOnboardingUIViewSet with your viewset
# router.register("nautobot_device_onboarding", views.NautobotDeviceOnboardingUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_device_onboarding/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
