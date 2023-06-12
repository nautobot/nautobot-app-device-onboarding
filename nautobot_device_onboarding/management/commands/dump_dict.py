"""Add the dump_dict command to nautobot-server."""

import uuid
import json
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand
from nautobot.users.models import User

from nautobot_device_onboarding.network_importer.adapters.nautobot.adapter import NautobotOrmAdapter


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
        print(json.dumps(nautobot_adapter.dict(), indent=4))
