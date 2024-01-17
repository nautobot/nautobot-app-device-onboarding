"""Diffsync models."""

from nautobot_ssot.contrib import NautobotModel
from nautobot.dcim.models import Device, DeviceType

class OnboardingDevice(NautobotModel):

    _modelname = "device"
    _model = Device
    _identifiers = ("name",)

    name: str

class OnboardingDeviceType(NautobotModel):

    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model",)

    model: str