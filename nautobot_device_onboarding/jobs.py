"""Device Onboarding Jobs."""
from django.conf import settings
from nautobot.apps.jobs import Job, ObjectVar, IntegerVar, StringVar
from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Location, DeviceType, Platform
from nautobot.extras.models import Role, SecretsGroup
from nautobot.extras.choices import SecretsGroupSecretTypeChoices

from nautobot_device_onboarding.helpers import onboarding_task_fqdn_to_ip
from nautobot_device_onboarding.netdev_keeper import NetdevKeeper


PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


class OnboardingTask(Job):
    """Nautobot Job for onboarding a new device."""

    location = ObjectVar(
        model=Location,
        query_params={"content_type": "dcim.device"},
        description="Assigned Location for the onboarded device.",
    )
    ip_address = StringVar(
        description="IP Address/DNS Name of the device to onboard, specify in a comma separate list for multiple devices.",
        label="IP Address/FQDN",
    )
    port = IntegerVar(default=22)
    timeout = IntegerVar(default=30)
    credentials = ObjectVar(
        model=SecretsGroup, required=False, description="SecretGroup for Device connection credentials."
    )
    platform = ObjectVar(
        model=Platform,
        required=False,
        description="Device platform. Define ONLY to override auto-recognition of platform.",
    )
    role = ObjectVar(
        model=Role,
        query_params={"content_type": "dcim.device"},
        required=False,
        description="Device role. Define ONLY to override auto-recognition of role.",
    )
    device_type = ObjectVar(
        model=DeviceType, required=False, description="Device type. Define ONLY to override auto-recognition of type."
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta object boilerplate for onboarding."""

        name = "Perform Device Onboarding"
        description = "Login to a device and populate Nautobot device object."
        has_sensitive_variables = False

    def __init__(self, *args, **kwargs):
        """Overload init to instantiate class attributes per W0201."""
        self.username = None
        self.password = None
        self.secret = None
        super().__init__(*args, **kwargs)

    def run(self, *args, **data):
        """Process a single Onboarding Task instance."""
        self.logger.info("START: onboard device")
        self._parse_credentials(data["credentials"])
        platform = data["platform"]

        # allows for itteration without having to spawn multiple jobs
        # Later refactor to use nautobot-plugin-nornir
        for address in data["ip_address"].split(","):
            netdev = NetdevKeeper(
                hostname=address,
                port=data["port"],
                timeout=data["timeout"],
                username=self.username,
                password=self.password,
                secret=self.secret,
                napalm_driver=platform.napalm_driver if platform and platform.napalm_driver else None,
                optional_args=platform.napalm_args if platform and platform.napalm_args else settings.NAPALM_ARGS,
            )
            netdev.get_onboarding_facts()
            netdev_dict = netdev.get_netdev_dict()

            onboarding_kwargs = {
                # Kwargs extracted from OnboardingTask:
                "netdev_mgmt_ip_address": onboarding_task_fqdn_to_ip(address),
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
            self.username = credentials.secrets.get(secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME)
            self.password = credentials.secrets.get(secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD)
            secret = credentials.secrets.filter(secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET)
            if secret.exists():
                self.secret = secret.first()
        else:
            self.username = settings.NAPALM_USERNAME
            self.password = settings.NAPALM_PASSWORD
            self.secret = settings.NAPALM_ARGS.get("secret", None)


register_jobs(OnboardingTask)
