"""Device Onboarding Jobs."""
from django.conf import settings
from nautobot.apps.jobs import Job, ObjectVar, IntegerVar, IPAddressVar
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Location, DeviceType, Platform
from nautobot.extras.models import Role, SecretsGroup
from nautobot.extras.choices import SecretsGroupSecretTypeChoices

from nautobot_device_onboarding.netdev_keeper import NetdevKeeper


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


class OnboardingTask(Job):
    location = ObjectVar(model=Location, query_params={"": ""}, required=False, description="")
    ip_address = IPAddressVar(description="", label="")
    port = IntegerVar(description="")
    timeout = IntegerVar(description="")
    credentials = ObjectVar(model=SecretsGroup, query_params={"": ""}, required=False, description="")
    platform = ObjectVar(model=Platform, required=False, description="")
    role = ObjectVar(model=Role, query_params={"": ""}, required=False, description="")
    device_type = ObjectVar(model=DeviceType, required=False, description="")

    def run(self, *args, **data):
        """Process a single Onboarding Task instance."""
        self.logger.info("START: onboard device")
        credentials = self._parse_credentials(data["credentials"])
        platform = data["platform"]
        netdev = NetdevKeeper(
            hostname=data["ip_address"],
            port=data["port"],
            timeout=data["timeout"],
            username=credentials["username"],
            password=credentials["password"],
            secret=credentials["secret"],
            napalm_driver=platform.napalm_driver if platform and platform.napalm_driver else None,
            optional_args=platform.napalm_args if platform and platform.napalm_args else settings.NAPALM_ARGS,
        )
        netdev.get_onboarding_facts()
        netdev_dict = netdev.get_netdev_dict()

        onboarding_kwargs = {
            # Kwargs extracted from OnboardingTask:
            "netdev_mgmt_ip_address": data["ip_address"],
            "netdev_nb_location_name": data["location"].name,
            "netdev_nb_device_type_name": data["device_type"],
            "netdev_nb_role_name": data["role"].name if data["role"] else PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_nb_platform_name": data["platform"].name if data["platform"] else None,
            # Kwargs discovered on the Onboarded Device:
            "netdev_hostname": netdev_dict["netdev_hostname"],
            "netdev_vendor": netdev_dict["netdev_vendor"],
            "netdev_model": netdev_dict["netdev_model"],
            "netdev_serial_number": netdev_dict["netdev_serial_number"],
            "netdev_mgmt_ifname": netdev_dict["netdev_mgmt_ifname"],
            "netdev_mgmt_pflen": netdev_dict["netdev_mgmt_pflen"],
            "netdev_netmiko_device_type": netdev_dict["netdev_netmiko_device_type"],
            "onboarding_class": netdev_dict["onboarding_class"],
            "driver_addon_result": netdev_dict["driver_addon_result"],
        }
        onboarding_cls = netdev_dict["onboarding_class"]()
        onboarding_cls.credentials = {"username": self.username, "password": self.password, "secret": self.secret}
        onboarding_cls.run(onboarding_kwargs=onboarding_kwargs)

    def _parse_credentials(self, credentials):
        """Parse and return dictionary of credentials."""

        if credentials:
            self.username = (credentials.secrets.get(secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME),)
            self.password = (credentials.secrets.get(secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD),)
            self.secret = (None,)
            secret = credentials.secrets.filter(secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET)
            if secret.exists():
                self.secret = secret.first()
        else:
            self.username = (settings.NAPALM_USERNAME,)
            self.password = (settings.NAPALM_PASSWORD,)
            self.secret = (settings.NAPALM_ARGS.get("secret", None),)


register_jobs(OnboardingTask)
