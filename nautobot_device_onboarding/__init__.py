"""Plugin declaration for nautobot_device_onboarding."""

try:
    from importlib import metadata
except ImportError:
    # Python version < 3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)

from nautobot.extras.plugins import PluginConfig


class OnboardingConfig(PluginConfig):
    """Plugin configuration for the nautobot_device_onboarding plugin."""

    name = "nautobot_device_onboarding"
    verbose_name = "Device Onboarding"
    version = __version__
    min_version = "2.0.0-rc.4"
    max_version = "2.9"
    author = "Network to Code, LLC"
    author_email = "opensource@networktocode.com"
    description = "Nautobot App that simplifies device onboarding (and re-onboarding) by collecting and populating common device 'facts' into Nautobot."
    base_url = "device-onboarding"
    required_settings = []
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
        "onboarding_extensions_map": {
            "ios": "nautobot_device_onboarding.onboarding_extensions.ios",
        },
        "object_match_strategy": "loose",
    }
    caching_config = {}


config = OnboardingConfig  # pylint:disable=invalid-name
