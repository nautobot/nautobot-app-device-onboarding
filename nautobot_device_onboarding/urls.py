"""URLS for nautobot_device_onboarding."""

from django.urls import path
from django.templatetags.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_device_onboarding/docs/index.html")), name="docs"),
]