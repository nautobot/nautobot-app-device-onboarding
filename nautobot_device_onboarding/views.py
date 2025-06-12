from nautobot.apps.views import NautobotUIViewSet
from rest_framework.decorators import action
from nautobot_device_onboarding import models, tables, filters, forms, jobs
from django.shortcuts import redirect
from nautobot.extras.models import Job, JobResult
from django.contrib import messages

class DiscoveredDeviceViewSet(NautobotUIViewSet):
    queryset = models.DiscoveredDevice.objects.all()
    table_class = tables.DiscoveredDeviceTable
    filterset_class = filters.DiscoveredDeviceFilterSet
    filterset_form_class = forms.DiscoveredDeviceFilterForm
    form_class = forms.DiscoveredDeviceForm
    bulk_update_form_class = forms.DiscoveredDeviceBulkEditForm

    @action(detail=False, methods=["post"])
    def syncdevices(self, request, *args, **kwargs):
        job_model = Job.objects.get_for_class_path(jobs.SSOTSyncDevices.class_path)
        if not Job.objects.check_perms(request.user, instance=job_model, action="run"):
            messages.error(request, "User does not have permission to run the SSoTSyncDevice job.")
            return redirect("plugins:nautobot_device_onboarding:discovereddevice_list")
        pk_list = list(request.POST.getlist("pk"))
        # grab discovered devices to sync based on toggle
        if request.POST.get("_all"):
            queryset = self.filterset_class(request.GET, models.DiscoveredDevice.objects.all()).qs
        else:
            queryset = self.queryset.filter(pk__in=pk_list)
        result = JobResult.enqueue_job(
            job_model,
            request.user,
            dryrun=False,
            discovered_devices=queryset.values_list("pk", flat=True),
            memory_profiling=False,
            debug=False,
            connectivity_test=False,
            csv_file=None,
            location=None,
            namespace=None,
            ip_addresses=None,
            set_mgmt_only=None,
            update_devices_without_primary_ip=None,
            device_role=None,
            device_status=None,
            interface_status=None,
            ip_address_status=None,
            port=None,
            timeout=None,
            secrets_group=None,
            platform=None,
        )
        return redirect(result)