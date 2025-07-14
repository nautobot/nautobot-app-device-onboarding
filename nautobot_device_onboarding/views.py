from nautobot.apps.views import NautobotUIViewSet
from rest_framework.decorators import action
from nautobot_device_onboarding import models, tables, filters, forms, jobs
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.template.loader import get_template, TemplateDoesNotExist
from nautobot.core.utils.requests import normalize_querydict
from nautobot.extras import forms as job_forms
from nautobot.extras.jobs import get_job, JobResult
from nautobot.extras.models import JobQueue
from nautobot.extras.choices import JobQueueTypeChoices
from nautobot.extras.views import JobRunView
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
        # job_model = Job.objects.get_for_class_path(jobs.SSOTSyncDevices.class_path)
        if "_sync" in request.POST:
            pk_list = list(request.POST.getlist("pk"))
            # grab discovered devices to sync based on toggle
            if request.POST.get("_all"):
                queryset = self.filterset_class(request.GET, models.DiscoveredDevice.objects.all()).qs
            else:
                queryset = self.queryset.filter(pk__in=pk_list)
            pks = queryset.all().values_list("pk", flat=True)
            return DiscoveryJobRunView().get(request, class_path=jobs.SSOTSyncDevices.class_path, discovered_pks=pks)
        else:
            return DiscoveryJobRunView().post(request, class_path=jobs.SSOTSyncDevices.class_path, *args, **kwargs)


class DiscoveryJobRunView(JobRunView):
    def get(self, request, class_path=None, pk=None, discovered_pks=None):
        job_model = self._get_job_model_or_404(class_path, pk)
        print(request)
        print(discovered_pks)
        try:
            job_class = get_job(job_model.class_path, reload=True)
            if job_class is None:
                raise RuntimeError("Job code for this job is not currently installed or loadable")
            initial = normalize_querydict(request.GET, form_class=job_class.as_form_class())
            if "kwargs_from_job_result" in initial:
                job_result_pk = initial.pop("kwargs_from_job_result")
                try:
                    job_result = job_model.job_results.get(pk=job_result_pk)
                    # Allow explicitly specified arg values in request.GET to take precedence over the saved task_kwargs,
                    # for example "?kwargs_from_job_result=<UUID>&integervar=22"
                    explicit_initial = initial
                    initial = job_result.task_kwargs.copy()
                    task_queue = job_result.celery_kwargs.get("queue", None)
                    job_queue = None
                    if task_queue is not None:
                        try:
                            job_queue = JobQueue.objects.get(
                                name=task_queue, queue_type=JobQueueTypeChoices.TYPE_CELERY
                            )
                        except JobQueue.DoesNotExist:
                            pass
                    initial["_job_queue"] = job_queue
                    initial["_profile"] = job_result.celery_kwargs.get("nautobot_job_profile", False)
                    initial["_ignore_singleton_lock"] = job_result.celery_kwargs.get(
                        "nautobot_job_ignore_singleton_lock", False
                    )
                    initial.update(explicit_initial)
                except JobResult.DoesNotExist:
                    messages.warning(
                        request,
                        f"JobResult {job_result_pk} not found, cannot use it to pre-populate inputs.",
                    )
            if discovered_pks:
                initial.update({"discovered_devices": discovered_pks})
                print("yurp")

            template_name = "extras/job.html"
            job_form = job_class.as_form(initial=initial)
            if hasattr(job_class, "template_name"):
                try:
                    get_template(job_class.template_name)
                    template_name = job_class.template_name
                except TemplateDoesNotExist as err:
                    messages.error(
                        request, f'Unable to render requested custom job template "{job_class.template_name}": {err}'
                    )
        except RuntimeError as err:
            messages.error(request, f"Unable to run or schedule '{job_model}': {err}")
            return redirect("extras:job_list")

        schedule_form = job_forms.JobScheduleForm(initial=initial)

        response = render(
            request,
            template_name,
            {
                "job_model": job_model,
                "job_form": job_form,
                "schedule_form": schedule_form,
            },
        )
        print(dir(response))
        return response
