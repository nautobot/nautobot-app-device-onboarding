from nautobot.apps.api import OrderedDefaultRouter
from nautobot_device_onboarding.api import views


router = OrderedDefaultRouter()
router.register("discovereddevices", views.DiscoveredDeviceViewSet)


# app_name = "nautobot_device_onboarding-api"
urlpatterns = router.urls
