"""Filtering logic for OnboardingTask instances."""
# pylint: disable=unsupported-binary-operation

import django_filters
from django.db.models import Q

from nautobot.dcim.models import Location, Platform
from nautobot.extras.models import Role
from nautobot.core.filters import BaseFilterSet

from nautobot_device_onboarding.models import OnboardingTask


class OnboardingTaskFilterSet(BaseFilterSet):
    """Filter capabilities for OnboardingTask instances."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    location = django_filters.ModelMultipleChoiceFilter(
        field_name="name",
        queryset=Location.objects.all(),
        label="Location (name)",
    )

    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platform__name",
        queryset=Platform.objects.all(),
        to_field_name="name",
        label="Platform (name)",
    )

    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__name",
        queryset=Role.objects.all(),
        to_field_name="name",
        label="Device Role (name)",
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["id", "location", "platform", "role", "status", "failed_reason"]

    def search(self, queryset, name, value):  # pylint: disable=unused-argument
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        qs_filter = (
            Q(id__icontains=value)
            | Q(ip_address__icontains=value)
            | Q(location__name__icontains=value)
            | Q(platform__name__icontains=value)
            | Q(created_device__name__icontains=value)
            | Q(status__icontains=value)
            | Q(failed_reason__icontains=value)
            | Q(message__icontains=value)
        )
        return queryset.filter(qs_filter)
