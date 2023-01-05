"""Onboarding Extension for IOS."""

from nautobot_device_onboarding.onboarding.onboarding import StandaloneOnboarding


class OnboardingDriverExtensions:
    """Onboarding Driver's Extensions."""

    def __init__(self, napalm_device):
        """Initialize class."""
        self.napalm_device = napalm_device

    @property
    def onboarding_class(self):
        """Return onboarding class for IOS driver.

        Currently supported is Standalone Onboarding Process.

        Result of this method is used by the OnboardingManager to
        initiate the instance of the onboarding class.
        """
        return StandaloneOnboarding

    @property
    def ext_result(self):
        """This method is used to store any object as a return value.

        Result of this method is passed to the onboarding class as
        driver_addon_result argument.

        :return: Any()
        """
        return None
