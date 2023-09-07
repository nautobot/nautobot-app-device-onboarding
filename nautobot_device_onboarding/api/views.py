"""Django REST Framework API views for device onboarding."""

# from drf_yasg.openapi import Parameter, TYPE_STRING
# from drf_yasg.utils import swagger_auto_schema

from rest_framework import mixins, viewsets

# from rest_framework.decorators import action
# from rest_framework.response import Response

# from nautobot.core.api.utils import IsAuthenticatedOrLoginNotRequired

# from nautobot.dcim.models import Device, Site, Platform, Role

from nautobot.apps.api import ModelViewSet, NautobotModelViewSet

from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.filters import OnboardingTaskFilterSet

# from nautobot_device_onboarding.choices import OnboardingStatusChoices
from nautobot_device_onboarding.api.serializers import OnboardingTaskSerializer


# class OnboardingTaskView(  # pylint: disable=too-many-ancestors
#     mixins.CreateModelMixin,
#     mixins.ListModelMixin,
#     mixins.RetrieveModelMixin,
#     mixins.DestroyModelMixin,
#     viewsets.GenericViewSet,
# ):
#     """Create, check status of, and delete onboarding tasks.

#     In-place updates (PUT, PATCH) of tasks are not permitted.
#     """

#     queryset = OnboardingTask.objects.all()
#     filterset_class = OnboardingTaskFilterSet
#     serializer_class = OnboardingTaskSerializer


class OnboardingTaskView(NautobotModelViewSet):
    
    queryset = OnboardingTask.objects.all()
    filterset_class = OnboardingTaskFilterSet
    serializer_class = OnboardingTaskSerializer