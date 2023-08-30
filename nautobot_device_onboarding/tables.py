"""Tables for device onboarding tasks."""
# pylint: disable=duplicate-code

import django_tables2 as tables
from nautobot.core.tables import BaseTable, ToggleColumn
from nautobot_device_onboarding.models import OnboardingTask


class OnboardingTaskTable(BaseTable):
    """Table for displaying OnboardingTask instances."""

    pk = ToggleColumn()
    label = tables.LinkColumn()
    location = tables.LinkColumn()
    platform = tables.LinkColumn()
    created_device = tables.LinkColumn()

    class Meta(BaseTable.Meta):  # noqa: D106 pylint: disable=too-few-public-methods
        model = OnboardingTask
        fields = (
            "pk",
            "label",
            "created",
            "ip_address",
            "location",
            "platform",
            "created_device",
            "status",
            "failed_reason",
            "message",
        )


class OnboardingTaskFeedBulkTable(BaseTable):
    """TODO document me."""

    location = tables.LinkColumn()

    class Meta(BaseTable.Meta):  # noqa: D106 pylint: disable=too-few-public-methods
        model = OnboardingTask
        fields = (
            "label",
            "created",
            "location",
            "platform",
            "ip_address",
            "port",
            "timeout",
        )
