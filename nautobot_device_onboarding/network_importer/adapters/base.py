"""BaseAdapter for the network importer."""

from django.conf import settings as django_settings

from diffsync import DiffSync
from diffsync.exceptions import ObjectNotFound

from nornir import InitNornir
from netutils.ip import is_ip

from nautobot.dcim import models
from nautobot.extras import models as extras_models

from nautobot_device_onboarding.network_importer.models import (
    Site,
    Device,
    Interface,
    IPAddress,
    # Cable,
    Vlan,
    Prefix,
    Status,
)


PLUGIN_SETTINGS = django_settings.PLUGINS_CONFIG.get("nautobot_device_onboarding", {})


class BaseAdapter(DiffSync):
    """Base Adapter for the network importer."""

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    # cable = Cable
    vlan = Vlan
    status = Status
    prefix = Prefix
    _unique_data = {}

    # settings_class = None
    # settings = None

    # def __init__(self, nornir, settings):
    #     """Initialize the base adapter and store the Nornir object locally."""
    #     super().__init__()
    #     self.nornir = nornir
    #     self.settings = self._validate_settings(settings)

    # def _validate_settings(self, settings):
    #     """Load and validate the configuration based on the settings_class."""
    #     if self.settings_class:
    #         if settings and isinstance(settings, dict):
    #             return self.settings_class(**settings)  # pylint: disable=not-callable

    #         return self.settings_class()  # pylint: disable=not-callable

    #     return settings

    def add(self, obj, *args, **kwargs):
        """Override add method to stuff data into dictionary based on the `_unique_fields`."""
        super().add(obj, *args, **kwargs)
        modelname = obj._modelname

        for attr in getattr(obj, "_unique_fields", []):
            if hasattr(obj, attr):
                if not self._unique_data.get(modelname):
                    self._unique_data[modelname] = {}
                if not self._unique_data[modelname].get(attr):
                    self._unique_data[modelname][attr] = {}
                self._unique_data[modelname][attr][getattr(obj, attr)] = obj

    def load(self):
        """Load the local cache with data from the remove system."""
        raise NotImplementedError

    def load_inventory(self):
        """Initialize and load all data from nautobot in the local cache."""
        with InitNornir(
            runner={
                "plugin": "threaded",
            },
            logging={"enabled": False},
            inventory={
                "plugin": "nautobot-inventory",
                "options": {
                    "credentials_class": "nautobot_plugin_nornir.plugins.credentials.env_vars.CredentialsEnvVars",
                    "params": {},
                    "queryset": models.Device.objects.filter(site__slug="ams01"),
                },
            },
        ) as nornir_obj:

            for device_obj in nornir_obj.inventory.hosts:
                result = nornir_obj.inventory.hosts[device_obj]
                site_slug = result.data.get("site")

                try:
                    site = self.get(self.site, site_slug)
                except ObjectNotFound:
                    site_id = models.Site.objects.get(slug=site_slug)
                    site = self.site(slug=site_slug, pk=str(site_id.pk))
                    self.add(site)

                device = self.device(slug=device_obj, site=site_slug, pk=str(result.data.get("id")))

                if is_ip(result.hostname):
                    device.primary_ip = result.hostname

                self.add(device)
            for status in extras_models.Status.objects.all():
                _st = self.status(slug=status.slug, name=status.name, pk=str(status.pk))
                self.add(_st)
