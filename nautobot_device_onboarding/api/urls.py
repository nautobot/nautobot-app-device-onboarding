"""API urls."""

from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="DeviceOnboarding")

router.register("discovered-groups", views.DiscoveredGroupViewSet)
router.register("discovered-ipaddresses", views.DiscoveredIPAddressViewSet)
router.register("discovered-ports", views.DiscoveredPortViewSet)

app_name = "device-onboarding-api"
urlpatterns = router.urls
