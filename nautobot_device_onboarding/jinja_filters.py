"""Filters for Jinja2 PostProcessing."""

from django_jinja import library
from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC

# https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jinja2-filters/


@library.filter
def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


@library.filter
def extract_prefix(network):
    """Extract the prefix length from the IP/Prefix. E.g 192.168.1.1/24."""
    return network.split("/")[-1]

@library.filter
def interface_status_to_bool(status):
    """Take links or admin status and change to boolean."""
    return True if "up" in status.lower() else False


@library.filter
def port_mode_to_nautobot(current_mode):
    """Take links or admin status and change to boolean."""
    mode_mapping = {
        "access": "access",
        "trunk": "tagged",
        # "trunk+x": "tagged-all"
    }
    return mode_mapping.get(current_mode, "")

@library.filter
def key_exist_or_default(dict_obj, key):
    """Take a dict with a key and if its not truthy return a default"""
    if not dict_obj[key]:
        return {}
    return dict_obj
