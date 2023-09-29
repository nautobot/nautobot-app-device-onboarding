"""Onboard."""

from django.conf import settings

from nautobot_device_onboarding.netdev_keeper import NetdevKeeper

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


class OnboardingTaskManager:
    """Onboarding Task Manager."""

    def __init__(self, onboarding_task):
        """Inits class."""
        self.onboarding_task = onboarding_task

    @property
    def napalm_driver(self):
        """Return napalm driver name."""
        if self.onboarding_task.platform and self.onboarding_task.platform.napalm_driver:
            return self.onboarding_task.platform.napalm_driver

        return None

    @property
    def optional_args(self):
        """Return platform optional args."""
        if self.onboarding_task.platform and self.onboarding_task.platform.napalm_args:
            return self.onboarding_task.platform.napalm_args

        return {}

    @property
    def ip_address(self):
        """Return ot's ip address."""
        return self.onboarding_task.ip_address

    @property
    def port(self):
        """Return ot's port."""
        return self.onboarding_task.port

    @property
    def timeout(self):
        """Return ot's timeout."""
        return self.onboarding_task.timeout

    @property
    def location(self):
        """Return ot's location."""
        return self.onboarding_task.location

    @property
    def device_type(self):
        """Return ot's device type."""
        return self.onboarding_task.device_type

    @property
    def role(self):
        """Return it's device role."""
        return self.onboarding_task.role

    @property
    def platform(self):
        """Return ot's device platform."""
        return self.onboarding_task.platform


class OnboardingManager:  # pylint: disable=too-few-public-methods
    """Onboarding Manager."""

    def __init__(self, onboarding_task, username, password, secret):
        """Inits class."""
        # Create instance of Onboarding Task Manager class:
        otm = OnboardingTaskManager(onboarding_task)

        self.username = username or settings.NAPALM_USERNAME
        self.password = password or settings.NAPALM_PASSWORD
        self.secret = secret or otm.optional_args.get("secret", None) or settings.NAPALM_ARGS.get("secret", None)

        netdev = NetdevKeeper(
            hostname=otm.ip_address,
            port=otm.port,
            timeout=otm.timeout,
            username=self.username,
            password=self.password,
            secret=self.secret,
            napalm_driver=otm.napalm_driver,
            optional_args=otm.optional_args or settings.NAPALM_ARGS,
        )

        netdev.get_onboarding_facts()
        netdev_dict = netdev.get_netdev_dict()

        onboarding_kwargs = {
            # Kwargs extracted from OnboardingTask:
            "netdev_mgmt_ip_address": otm.ip_address,
            "netdev_nb_location_name": otm.location.name if otm.location else None,
            "netdev_nb_device_type_name": otm.device_type,
            "netdev_nb_role_name": otm.role.name if otm.role else PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_nb_platform_name": otm.platform.name if otm.platform else None,
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

        self.created_device = onboarding_cls.created_device
