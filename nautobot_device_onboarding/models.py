import json

from dataclasses import dataclass, asdict, field
from typing import Literal, Optional

from nautobot.apps.models import PrimaryModel
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from django.db.models import (
    BooleanField,
    DateTimeField,
    ForeignKey,
    SET_NULL,
    CASCADE,
    PositiveIntegerField,
    GenericIPAddressField,
    CharField,
)

from nautobot.core.choices import ChoiceSet
from nornir.core.inventory import Host
from nornir.core.inventory import ConnectionOptions, Host

from nautobot_device_onboarding.constants import NETMIKO_EXTRAS


class SshStateChoices(ChoiceSet):
    """SSH State Choices."""

    PORT_CLOSED = "port_closed"
    PORT_OPENED = "port_opened"
    SERVICE_UNAUTHENTICATED = "Service unauthenticated"
    SERVICE_AUTHENTICATED = "service_authenticated"
    SERVICE_DATA_COLLECTED = "service_data_collected"
    INVALID_COMMAND = "invalid_command"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"

    CHOICES = (
        (PORT_CLOSED, "Port closed"),
        (PORT_OPENED, "Port opened"),
        (SERVICE_UNAUTHENTICATED, "Service unauthenticated"),
        (SERVICE_AUTHENTICATED, "Service authenticated"),
        (SERVICE_DATA_COLLECTED, "Service data collected"),
        (INVALID_COMMAND, "Invalid command"),
        (PARSE_ERROR, "Parse error"),
        (UNKNOWN, "Unknown"),
    )


class DiscoveredDevice(PrimaryModel):
    ip_address = GenericIPAddressField(unique=True)
    # ignore = BooleanField(default=False, verbose_name="Ignore")  # TODO(mzb): skip/ignore flag

    ssh_response = BooleanField(default=False, verbose_name="SSH login")
    ssh_response_datetime = DateTimeField(blank=True, null=True, verbose_name="SSH last response")
    ssh_issue = CharField(choices=SshStateChoices.CHOICES, blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)  # TODO(mzb): Rename to ssh_status!
    ssh_port = PositiveIntegerField(blank=True, null=True)
    ssh_credentials = ForeignKey(to="extras.SecretsGroup", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    ssh_timeout = PositiveIntegerField(default=30, blank=True, null=True)

    device = ForeignKey(to="dcim.Device", on_delete=SET_NULL, related_name="+", blank=True, null=True)
    network_driver = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    hostname = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    serial = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    device_type = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
    inventory_status = CharField(blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)

    def __str__(self):
        if self.hostname:
            return f"{self.hostname} / {self.ip_address}"
        else:
            return f"{self.ip_address}"



@dataclass(eq=True, frozen=True)
class DeviceService:
    ip: str
    port: int
    name: Literal['ssh', 'snmp', 'api']

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}:{self.name}"

    @classmethod
    def from_args(cls, ip, port, name):
        return cls(ip, int(port), name)

    @classmethod
    def from_string(cls, value: str):
        try:
            ip, port, name = value.strip().split(":")
            return cls.from_args(ip, port, name)
        except ValueError as e:
            raise ValueError(f"Invalid format for DeviceService string: {value!r}") from e


@dataclass
class ProbedDeviceServices:
    service: DeviceService

    port_status: Optional[Literal[
        'open',
        'unreachable',
        'filtered',
    ]] = None
    service_status: Optional[Literal[
        'ok',
        'timeout',
        'invalid_credentials',
        'unexpected_output',
        'parsing_error',
        'authenticated',
        'discovery_issue',
    ]] = None

    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_timeout: Optional[int] = None
    network_driver: Optional[str] = "cisco_ios"
    hostname: Optional[str] = None
    device_model: Optional[str] = None
    serial: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.service.ip}:{self.service.port}:{self.service.name}"

    def to_nornir_host(self, name_eq_ip=False):
        return Host(
            name=str(self.service) if not name_eq_ip else self.service.ip,
            hostname=self.service.ip,
            port=self.service.port,
            username=self.ssh_username,
            password=self.ssh_password,
            platform=self.network_driver,
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname=self.service.ip,
                    port=self.service.port,
                    username=self.ssh_username,
                    password=self.ssh_password,
                    platform=self.network_driver,
                    extras=NETMIKO_EXTRAS,
                )
            },
        )

    def to_dict(self):
        base = {
            **asdict(self.service),
            "port_status": self.port_status,
            "service_status": self.service_status,
            "banner": self.banner,
            "last_seen": self.last_seen,
        }
        discovery_dict = {
            k: v for k, v in asdict(self.discovery_result).items() if v is not None
        }
        return {**base, **discovery_dict}


class ProbedDeviceStore:
    def __init__(self):
        self._entries: dict[DeviceService, ProbedDeviceServices] = {}

    def __contains__(self, item: DeviceService) -> bool:
        return item in self._entries

    def __iter__(self):
        return iter(self._entries.values())

    def __getitem__(self, key: DeviceService) -> ProbedDeviceServices:
        return self._entries[key]

    def __setitem__(self, key: DeviceService, value: ProbedDeviceServices):
        self._entries[key] = value

    def __delitem__(self, key: DeviceService):
        del self._entries[key]

    def __len__(self):
        return len(self._entries)

    def add_or_update(self, probed_device_services: ProbedDeviceServices):
        self._entries[probed_device_services.service] = probed_device_services

    def filter(self, **kwargs) -> list['ProbedDeviceServices']:
        def match(entry) -> bool:
            for key, value in kwargs.items():
                # Support nested fields, e.g., service__ip
                parts = key.split("__")
                negate = False

                # Handle special suffixes like __in and __not
                if parts[-1] == "in":
                    attr_path = parts[:-1]
                    op = "in"
                elif parts[-1] == "not":
                    attr_path = parts[:-1]
                    op = "not"
                else:
                    attr_path = parts
                    op = "eq"

                # Traverse nested attributes
                current = entry
                try:
                    for attr in attr_path:
                        current = getattr(current, attr)
                except AttributeError:
                    return False  # attribute doesn't exist

                # Compare based on operation
                if op == "in":
                    if current not in value:
                        return False
                elif op == "not":
                    if current == value:
                        return False
                else:  # equality check
                    if current != value:
                        return False

            return True

        return [entry for entry in self._entries.values() if match(entry)]

    def to_json(self) -> str:
        return json.dumps(
            [entry.to_dict() for entry in self._entries.values()],
            indent=2
        )
