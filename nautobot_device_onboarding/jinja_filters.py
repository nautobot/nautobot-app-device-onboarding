"""Filters for Jinja2 PostProcessing."""

from django_jinja import library
from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC

# https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jinja2-filters/


@library.filter
def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")
