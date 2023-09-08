"""Django REST Framework API views for device onboarding."""
from rest_framework import mixins, viewsets

from nautobot.apps.api import ModelViewSet, NautobotModelViewSet

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.filters import OnboardingTaskFilterSet

from nautobot_device_onboarding.api.serializers import OnboardingTaskSerializer


class OnboardingTaskViewSet(NautobotModelViewSet):
    
    queryset = OnboardingTask.objects.all()
    filterset_class = OnboardingTaskFilterSet
    serializer_class = OnboardingTaskSerializer
