"""Django views for device onboarding."""

from django.shortcuts import get_object_or_404, render

from rest_framework.response import Response

from nautobot.core.views import generic

from nautobot_device_onboarding.filters import OnboardingTaskFilterSet
from nautobot_device_onboarding.forms import OnboardingTaskForm, OnboardingTaskFilterForm, OnboardingTaskBulkEditForm
from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.tables import OnboardingTaskTable

from nautobot_device_onboarding.api.serializers import OnboardingTaskSerializer

from nautobot.apps.views import ObjectEditViewMixin, ObjectListViewMixin, ObjectDetailViewMixin, ObjectBulkCreateViewMixin, ObjectBulkDestroyViewMixin, ObjectChangeLogViewMixin, ObjectDestroyViewMixin, ObjectNotesViewMixin

from nautobot.core.forms import (
    BootstrapMixin,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    restrict_form_fields,
)

from nautobot.core.views.utils import (
    get_csv_form_fields_from_serializer_class,
    handle_protectederror,
    prepare_cloned_fields,
)

from django.forms import Form, ModelMultipleChoiceField, MultipleHiddenInput

class OnboardingTaskUIViewSet(ObjectEditViewMixin, ObjectListViewMixin, ObjectDetailViewMixin, ObjectBulkCreateViewMixin, ObjectBulkDestroyViewMixin, ObjectChangeLogViewMixin, ObjectDestroyViewMixin, ObjectNotesViewMixin):

    bulk_update_form_class = OnboardingTaskBulkEditForm
    filterset_class = OnboardingTaskFilterSet
    filterset_form_class = OnboardingTaskFilterForm
    form_class = OnboardingTaskForm
    queryset = OnboardingTask.objects.all()
    serializer_class = OnboardingTaskSerializer
    table_class = OnboardingTaskTable
    action_buttons = ["add", "export", "import"]

    def bulk_create(self, request, *args, **kwargs):
        context = {}
        if request.method == "POST":
            return self.perform_bulk_create(request)
        return Response(context)
    
    def perform_bulk_create(self, request):
        form_class = self.get_form_class()
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
        
    def get_form_class(self, **kwargs):
        """
        Helper function to get form_class for different views.
        """

        if self.action in ["create", "update"]:
            form_class = getattr(self, "form_class", None)
        elif self.action == "bulk_create":
            required_field_names = [
                field["name"]
                for field in get_csv_form_fields_from_serializer_class(self.serializer_class)
                if field["required"]
            ]

            class BulkCreateForm(BootstrapMixin, Form):
                csv_data = CSVDataField(required_field_names=required_field_names)
                csv_file = CSVFileField()

            form_class = BulkCreateForm
        else:
            form_class = getattr(self, f"{self.action}_form_class", None)

        if not form_class:
            if self.action == "bulk_destroy":
                queryset = self.get_queryset()

                class BulkDestroyForm(ConfirmationForm):
                    pk = ModelMultipleChoiceField(queryset=queryset, widget=MultipleHiddenInput)

                return BulkDestroyForm
            else:
                # Check for request first and then kwargs for form_class specified.
                form_class = self.request.data.get("form_class", None)
                if not form_class:
                    form_class = kwargs.get("form_class", None)

        return form_class

    def form_save(self, form, **kwargs):
        """
        Generic method to save the object from form.
        Should be overriden by user if customization is needed.
        """
        return form.save()