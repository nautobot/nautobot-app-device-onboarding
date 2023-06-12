"""Add the run_ssot command to nautobot-server."""

import uuid
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand
from nautobot.users.models import User

from nautobot_device_onboarding.network_importer.adapters.nautobot.adapter import NautobotOrmAdapter
from nautobot_device_onboarding.network_importer.adapters.network_device.adapter import NetworkImporterAdapter
from nautobot_device_onboarding.tests.mock.network_device.basic import data as network_data
from nautobot_device_onboarding.network_importer.diff import NetworkImporterDiff


class Command(BaseCommand):
    """Boilerplate Command to Sync from Network Device data dictionary."""

    help = "Sync from Network Device data dictionary."

    def add_arguments(self, parser):
        """Add arguments for dev_destroy_and_build."""
        parser.add_argument("-u", "--user", type=str, default="admin", help="Username to create.")

    def handle(self, *args, **kwargs):
        """Add handler for `run_ssot`."""
        user = kwargs["user"]
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = User.objects.get(username=user)

        nautobot_adapter = NautobotOrmAdapter(request=request)
        nautobot_adapter.load()

        network_adapter = NetworkImporterAdapter()
        network_adapter.load_from_dict(network_data)

        _diff = nautobot_adapter.diff_from(network_adapter, diff_class=NetworkImporterDiff)
        nautobot_adapter.sync_from(network_adapter, diff=_diff, diff_class=NetworkImporterDiff)
