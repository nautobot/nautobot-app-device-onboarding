"""Django urlpatterns declaration for nautobot_device_onboarding app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_device_onboarding/docs/index.html")), name="docs"),
]
