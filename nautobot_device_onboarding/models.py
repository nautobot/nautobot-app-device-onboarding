"""Models for Natobot Device Onboarding."""

from django.db import models

# Nautobot imports
from nautobot.apps.models import PrimaryModel

from nautobot_device_onboarding.choices import VLANLocationSyncTypeChoices


class OnboardingConfigSyncDevices(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Settings used by the Nautobot Device Onboarding app when running Sync Devices From Network."""

    name = models.CharField(max_length=100, unique=True)
    preferred_config = models.BooleanField(default=False)
    connectivity_test = models.BooleanField(default=False)
    namespace = models.ForeignKey(
        to="ipam.Namespace",
        on_delete=models.PROTECT,
        related_name="sync_devices_onboarding_configs",
        blank=True,
        null=True,
    )
    device_role = models.ForeignKey(
        to="extras.Role",
        on_delete=models.PROTECT,
        related_name="sync_devices_onboarding_configs",
        blank=True,
        null=True,
    )
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.PROTECT,
        related_name="sync_devices_onboarding_configs",
        blank=True,
        null=True,
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    device_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    interface_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    ip_address_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    port = models.IntegerField(
        blank=True,
        null=True,
    )
    timeout = models.IntegerField(
        blank=True,
        null=True,
    )

    class Meta:
        """Meta class."""

        verbose_name = "Onboarding Config - Sync Devices"
        verbose_name_plural = "Onboarding Configs - Sync Devices"

    def __str__(self):
        """Stringify instance."""
        return self.name

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure only config is "preferred".

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.preferred_config:
            OnboardingConfigSyncDevices.objects.exclude(pk=self.pk).update(preferred_config=False)
        super().save(*args, **kwargs)


class OnboardingConfigSyncNetworkDataFromNetwork(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Settings used by the Nautobot Device Onboarding app when running Sync Network Data From Network."""

    name = models.CharField(max_length=100, unique=True)
    preferred_config = models.BooleanField(default=False)
    connectivity_test = models.BooleanField(default=False)
    sync_vlans = models.BooleanField(default=False)
    sync_vrfs = models.BooleanField(default=False)
    sync_cables = models.BooleanField(default=False)
    namespace = models.ForeignKey(
        to="ipam.Namespace",
        on_delete=models.PROTECT,
        related_name="sync_network_data_onboarding_configs",
        blank=True,
        null=True,
    )
    interface_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    ip_address_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    default_prefix_status = models.ForeignKey(
        to="extras.Status",
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    sync_vlans_location_type = models.CharField(
        choices=VLANLocationSyncTypeChoices, max_length=50, default=VLANLocationSyncTypeChoices.SINGLE_LOCATION
    )

    class Meta:
        """Meta class."""

        verbose_name = "Onboarding Config - Sync Network Data"
        verbose_name_plural = "Onboarding Configs - Sync Network Data"

    def __str__(self):
        """Stringify instance."""
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure only config is "preferred".

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        if self.preferred_config:
            OnboardingConfigSyncNetworkDataFromNetwork.objects.exclude(pk=self.pk).update(preferred_config=False)
        super().save(*args, **kwargs)
