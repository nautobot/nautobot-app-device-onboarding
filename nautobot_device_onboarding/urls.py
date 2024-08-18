"""Urls."""

from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "nautobot_device_onboarding"

router = NautobotUIViewSetRouter()
router.register("discovered-groups", views.DiscoveredGroupUIViewSet)
router.register("discovered-ipaddresses", views.DiscoveredIPAddressUIViewSet)
router.register("discovered-ports", views.DiscoveredPortUIViewSet)

urlpatterns = [
  path("discovered-groups/<uuid:pk>/", views.DiscoveredGroupView.as_view(), name="discoveredgroup-detail"),
] + router.urls
