"""Diffsync models."""

from nautobot_ssot.contrib import NautobotModel
from nautobot.dcim.models import Device, DeviceType, Interface
from typing import List, Optional

class OnboardingDevice(NautobotModel):

    _modelname = "device"
    _model = Device
    _identifiers = ("primary_ip4__host",)
    _attributes = (
        "location__name",  
        "device_type__model", 
        "role__name", 
        "platform__name", 
    )
    _children = {
        "interface": "interfaces",
    }

    primary_ip4__host: str

    location__name: Optional[str]
    device_type__model: Optional[str]
    role__name: Optional[str]
    platform__name: Optional[str]

    interfaces: List["Interface"] = []

class OnboardingInterface(NautobotModel):

    _modelname = "interface"
    _model = Interface
    _identifiers = ("name",)

    name: str

class OnboardingDeviceType(NautobotModel):

    _modelname = "device_type"
    _model = DeviceType
    _identifiers = ("model",)
    
    model: str