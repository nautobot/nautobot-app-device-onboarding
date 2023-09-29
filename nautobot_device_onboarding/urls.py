"""Django urlpatterns declaration for nautobot_device_onboarding plugin."""
from nautobot.core.views.routers import NautobotUIViewSetRouter

from nautobot_device_onboarding.views import OnboardingTaskUIViewSet


router = NautobotUIViewSetRouter()

router.register("onboardingtask", OnboardingTaskUIViewSet)

urlpatterns = []

urlpatterns += router.urls
