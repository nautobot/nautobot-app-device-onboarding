"""Django REST Framework API views for device onboarding."""

# from drf_yasg.openapi import Parameter, TYPE_STRING
# from drf_yasg.utils import swagger_auto_schema

from rest_framework import mixins, viewsets

# from rest_framework.decorators import action
# from rest_framework.response import Response

# from nautobot.utilities.api import IsAuthenticatedOrLoginNotRequired

# from nautobot.dcim.models import Device, Site, Platform, DeviceRole

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.filters import OnboardingTaskFilter

# from nautobot_device_onboarding.choices import OnboardingStatusChoices
from .serializers import OnboardingTaskSerializer


class OnboardingTaskView(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Create, check status of, and delete onboarding tasks.

    In-place updates (PUT, PATCH) of tasks are not permitted.
    """

    queryset = OnboardingTask.objects.all()
    filterset_class = OnboardingTaskFilter
    serializer_class = OnboardingTaskSerializer
