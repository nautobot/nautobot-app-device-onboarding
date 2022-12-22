"""Filtering logic for OnboardingTask instances."""

import django_filters
from django.db.models import Q

from nautobot.dcim.models import Site, DeviceRole, Platform
from nautobot.utilities.filters import NameSlugSearchFilterSet

from nautobot_device_onboarding.models import OnboardingTask


class OnboardingTaskFilterSet(NameSlugSearchFilterSet):
    """Filter capabilities for OnboardingTask instances."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    site = django_filters.ModelMultipleChoiceFilter(
        field_name="site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )

    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (ID)",
    )

    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platform__slug",
        queryset=Platform.objects.all(),
        to_field_name="slug",
        label="Platform (slug)",
    )

    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug",
        queryset=DeviceRole.objects.all(),
        to_field_name="slug",
        label="Device Role (slug)",
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["id", "site", "site_id", "platform", "role", "status", "failed_reason"]

    def search(self, queryset, name, value):  # pylint: disable=unused-argument, no-self-use
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        qs_filter = (
            Q(id__icontains=value)
            | Q(ip_address__icontains=value)
            | Q(site__name__icontains=value)
            | Q(platform__name__icontains=value)
            | Q(created_device__name__icontains=value)
            | Q(status__icontains=value)
            | Q(failed_reason__icontains=value)
            | Q(message__icontains=value)
        )
        return queryset.filter(qs_filter)
