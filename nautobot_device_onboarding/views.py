"""Django views for Onboarding."""

from django.shortcuts import render
from nautobot.apps.views import GenericView, NautobotUIViewSet

from nautobot_device_onboarding import forms, models, tables


class OnboardingConfigSyncDevicesUIViewSet(NautobotUIViewSet):
    """Onboarding view for Sync Devices configs."""

    bulk_update_form_class = None
    filterset_class = None
    filterset_form_class = None
    form_class = forms.OnboardingConfigSyncDevicesForm
    lookup_field = "pk"
    queryset = models.OnboardingConfigSyncDevices.objects.all()
    serializer_class = None
    table_class = tables.OnboardingConfigSyncDevicesTable


class OnboardingConfigSyncNetworkDataFromNetworkUIViewSet(NautobotUIViewSet):
    """Onboarding view for Sync Devices configs."""

    bulk_update_form_class = None
    filterset_class = None
    filterset_form_class = None
    form_class = forms.OnboardingConfigSyncNetworkDataFromNetworkForm
    lookup_field = "pk"
    queryset = models.OnboardingConfigSyncNetworkDataFromNetwork.objects.all()
    serializer_class = None
    table_class = tables.OnboardingConfigSyncNetworkDataFromNetworkTable


class OnboardingConfigView(GenericView):
    """Onboarding config view."""

    sync_devices_class = models.OnboardingConfigSyncDevices
    sync_network_data_class = models.OnboardingConfigSyncNetworkDataFromNetwork
    sync_devices_table_class = tables.OnboardingConfigSyncDevicesTable
    sync_network_data_table_class = tables.OnboardingConfigSyncNetworkDataFromNetworkTable

    def get(self, request):
        """Return a list of Onboarding Configurations."""
        sync_devices_queryset = self.sync_devices_class.objects.all()
        sync_network_data_queryset = self.sync_network_data_class.objects.all()
        sync_devices_table = self.sync_devices_table_class(sync_devices_queryset, orderable=False)
        sync_network_data_table = self.sync_network_data_table_class(sync_network_data_queryset, orderable=False)
        sync_devices_preferred_config = sync_devices_queryset.filter(preferred_config=True).first()
        sync_network_data_preferred_config = sync_network_data_queryset.filter(preferred_config=True).first()
        return render(
            request,
            "onboarding_config.html",
            {
                "sync_devices_preferred_config": sync_devices_preferred_config,
                "sync_network_data_preferred_config": sync_network_data_preferred_config,
                "tables": {
                    "Sync Devices from Network Configurations": {
                        "add_url": "plugins:nautobot_device_onboarding:onboardingconfigsyncdevices_add",
                        "table": sync_devices_table,
                    },
                    "Sync Network Data from Network Configurations": {
                        "add_url": "plugins:nautobot_device_onboarding:onboardingconfigsyncnetworkdatafromnetwork_add",
                        "table": sync_network_data_table,
                    },
                },
            },
        )
