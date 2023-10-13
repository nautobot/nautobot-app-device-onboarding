"""Django REST Framework API views for device onboarding."""

from rest_framework import status
from rest_framework.response import Response

from nautobot.apps.api import NautobotModelViewSet

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.filters import OnboardingTaskFilterSet

from nautobot_device_onboarding.api.serializers import OnboardingTaskSerializer


class OnboardingTaskViewSet(NautobotModelViewSet):
    """API Viewset."""

    queryset = OnboardingTask.objects.all()
    filterset_class = OnboardingTaskFilterSet
    serializer_class = OnboardingTaskSerializer

    def update(self, request, *args, **kwargs):
        """Override the update method to disallow put/patch."""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
