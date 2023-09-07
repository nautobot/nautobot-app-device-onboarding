"""Base Job classes for sync workers."""
from collections import namedtuple
from datetime import datetime
import traceback
import tracemalloc
from typing import Iterable

from django.db.utils import OperationalError
from django.forms import HiddenInput
from django.templatetags.static import static
from django.utils import timezone
from django.utils.functional import classproperty

# pylint-django doesn't understand classproperty, and complains unnecessarily. We disable this specific warning:
# pylint: disable=no-self-argument

from diffsync.enum import DiffSyncFlags
from diffsync import DiffSync
import structlog

from nautobot.extras.jobs import Job, BaseJob, BooleanVar

from nautobot_ssot.choices import SyncLogEntryActionChoices
from nautobot_ssot.models import Sync, SyncLogEntry


from nautobot.dcim.models import Manufacturer, Platform

from nautobot_ssot.jobs import DataSource
from nautobot_ssot.contrib import NautobotModel

from nautobot_ssot.contrib import BaseAdapter

class ManufacturerModel(NautobotModel):
    """An example model of a tenant."""
    _model = Manufacturer
    _modelname = "manufacturer"
    _identifiers = ("name",)
    _attributes = ("description",)
    _children = {"platform": "platforms"}

    name: str
    description: str
    platforms: list = []

class PlatformModel(NautobotModel):
    _model = Platform
    _modelname = "platform"
    _identifiers = ("name",)
    _attributes = ("manufacturer__name",)

    name: str
    manufacturer__name: str

class DeviceOnboarding(DiffSync):
    manufacturer = ManufacturerModel
    
    # site
    platform = PlatformModel
    # device_type
    # device_role
    # interface
    # ip_address
    
    top_level = ("manufacturer",)

    # def __init__(self, ip):
        # need to super DiffSync init
    #     pass

    def load(self):
        
        manufacturer = "Cisco"
        platform1 = "ios"
        platfomr2 = "nxos"
        description = "Work Work Work"

        manufacturer_diffsync = self.manufacturer(name=manufacturer, description=description)

        self.add(manufacturer_diffsync)

        platform1_diffsync = self.platform(name=platform1, manufacturer__name=manufacturer)
        platform2_diffsync = self.platform(name=platfomr2, manufacturer__name=manufacturer)

        self.add(platform1_diffsync)
        self.add(platform2_diffsync)

        manufacturer_diffsync.add_child(platform1_diffsync)
        manufacturer_diffsync.add_child(platform2_diffsync)


        

class NautobotAdapter(BaseAdapter):
    manufacturer = ManufacturerModel
    platform = PlatformModel
    top_level = ("manufacturer",)

class DeviceOnboardingJob(DataSource, Job):
    def load_source_adapter(self):
        """Method to instantiate and load the SOURCE adapter into `self.source_adapter`."""
        self.source_adapter = DeviceOnboarding("dummy")
        self.source_adapter.load()

    def load_target_adapter(self):
        """Method to instantiate and load the TARGET adapter into `self.target_adapter`."""
        self.target_adapter = NautobotAdapter()
        self.target_adapter.load()

jobs = [DeviceOnboardingJob]