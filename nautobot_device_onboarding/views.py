from nautobot.apps.views import NautobotUIViewSet
from nautobot_device_onboarding import models, tables, filters, forms

class DiscoveredDeviceViewSet(NautobotUIViewSet):
    queryset = models.DiscoveredDevice.objects.all()
    table_class = tables.DiscoveredDeviceTable
    filterset_class = filters.DiscoveredDeviceFilterSet
    filterset_form_class = forms.DiscoveredDeviceFilterForm
    form_class = forms.DiscoveredDeviceForm
    bulk_update_form_class = forms.DiscoveredDeviceBulkEditForm