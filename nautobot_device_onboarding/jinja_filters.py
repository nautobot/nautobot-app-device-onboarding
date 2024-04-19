"""Filters for Jinja2 PostProcessing."""

from django_jinja import library
from nautobot_device_onboarding.constants import INTERFACE_TYPE_MAP_STATIC
# https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jinja2-filters/


@library.filter
def map_interface_type(interface_type):
    """Map interface type to a Nautobot type."""
    return INTERFACE_TYPE_MAP_STATIC.get(interface_type, "other")


@library.filter
def collapse_list_to_dict(original_data):
    """Takes a list of dictionaries and creates a dictionary based on outtermost key.

    Args:
        original_data (list): list of dictionaries
        root_key (str): dictionary key to use as the root key

    Example:
    >>> example_data = [
            {'GigabitEthernet1': {'link_status': 'up'}},
            {'GigabitEthernet2': {'link_status': 'administratively down'}},
            {'GigabitEthernet3': {'link_status': 'administratively down'}},
            {'GigabitEthernet4': {'link_status': 'administratively down'}},
            {'Loopback0': {'link_status': 'administratively down'}},
            {'Loopback2': {'link_status': 'administratively down'}},
            {'Port-channel1': {'link_status': 'down'}}
        ]
    >>> collapse_list_to_dict(example_data)
    {'GigabitEthernet1': {'link_status': 'up'},
    'GigabitEthernet2': {'link_status': 'administratively down'},
    'GigabitEthernet3': {'link_status': 'administratively down'},
    'GigabitEthernet4': {'link_status': 'administratively down'},
    'Loopback0': {'link_status': 'administratively down'},
    'Loopback2': {'link_status': 'administratively down'},
    'Port-channel1': {'link_status': 'down'}}
    """
    return {root_key: data for data in original_data for root_key, data in data.items()}


def merge_dicts(*dicts):
    """Merges any number of dictionaries recursively, handling nested dictionaries.

    Args:
        *dicts: A variable number of dictionaries to merge.

    Returns:
        A new dictionary containing the merged data from all dictionaries.
    """
    if not dicts:
        return {}  # Empty input returns an empty dictionary
    merged = dicts[0].copy()
    for other_dict in dicts[1:]:
        if other_dict:
            for key, value in other_dict.items():
                if key in merged:
                    if isinstance(value, dict) and isinstance(merged[key], dict):
                        # Recursively merge nested dictionaries
                        merged[key] = merge_dicts(merged[key], value)
                else:
                    # Overwrite existing values with values from subsequent dictionaries (giving priority to later ones)
                    merged[key] = value
            # Add new key-value pairs from subsequent dictionaries
            # merged[key] = value
    return merged
