"""Onboarding module."""

from nautobot_device_onboarding.nautobot_keeper import NautobotKeeper


class Onboarding:
    """Generic onboarding class."""

    def __init__(self):
        """Init the class."""
        self.created_device = None
        self.credentials = None

    def run(self, onboarding_kwargs):
        """Implement run method."""
        raise NotImplementedError


class StandaloneOnboarding(Onboarding):
    """Standalone onboarding class."""

    def run(self, onboarding_kwargs):
        """Ensure device is created with Nautobot Keeper."""
        nb_k = NautobotKeeper(**onboarding_kwargs)
        nb_k.ensure_device()

        self.created_device = nb_k.device
