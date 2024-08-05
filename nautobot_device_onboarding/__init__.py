"""App declaration for nautobot_device_onboarding."""

# Metadata is inherited from Nautobot
# If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotDeviceOnboardingConfig(NautobotAppConfig):
    """App configuration for the nautobot_device_onboarding app."""

    name = "nautobot_device_onboarding"
    verbose_name = "Device Onboarding"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot App that simplifies device onboarding (and re-onboarding) by \
                   collecting and populating common device 'facts' into Nautobot."
    base_url = "nautobot-device-onboarding"
    required_settings = []
    min_version = "2.1.1"
    max_version = "2.9999"
    default_settings = {
        "create_platform_if_missing": True,
        "create_manufacturer_if_missing": True,
        "create_device_type_if_missing": True,
        "create_device_role_if_missing": True,
        "default_device_role": "network",
        "default_device_role_color": "ff0000",
        "default_management_interface": "PLACEHOLDER",
        "default_management_prefix_length": 0,
        "default_device_status": "Active",
        "default_ip_status": "Active",
        "create_management_interface_if_missing": True,
        "skip_device_type_on_update": False,
        "skip_manufacturer_on_update": False,
        "platform_map": {},
        "assign_secrets_group": False,
        "set_management_only_interface": False,
        "onboarding_extensions_map": {
            "ios": "nautobot_device_onboarding.onboarding_extensions.ios",
        },
        "object_match_strategy": "loose",
    }
    caching_config = {}


config = NautobotDeviceOnboardingConfig  # pylint:disable=invalid-name
