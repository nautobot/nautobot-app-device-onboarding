"""Plugin declaration for nautobot_device_onboarding.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__version__ = "1.0.1"

from nautobot.extras.plugins import PluginConfig


class OnboardingConfig(PluginConfig):
    """Plugin configuration for the nautobot_device_onboarding plugin."""

    name = "nautobot_device_onboarding"
    verbose_name = "Device Onboarding"
    version = __version__
    min_version = "1.0.0b4"
    author = "Network to Code"
    author_email = "opensource@networktocode.com"
    description = "A plugin for Nautobot to easily onboard new devices."
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
