"""Urls."""

from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "nautobot_device_onboarding"

router = NautobotUIViewSetRouter()
router.register("discovered-groups", views.DiscoveredGroupUIViewSet)
router.register("discovered-ipaddresses", views.DiscoveredIPAddressUIViewSet)
router.register("discovered-ports", views.DiscoveredPortUIViewSet)

urlpatterns = router.urls
