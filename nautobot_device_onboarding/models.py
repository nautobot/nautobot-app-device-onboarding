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

class SshIssuesChoices(ChoiceSet):
    """Styling choices for custom banners."""

    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_COMMAND = "invalid_command"
    PORT_CLOSED = "port_closed"
    PARSE_ERROR = "parse_error"

    CHOICES = (
        (INVALID_CREDENTIALS, "Invalid credentials"),
        (PORT_CLOSED, "Port closed"),
        (PARSE_ERROR, "Parse error"),
        (INVALID_COMMAND, "Invalid command"),
    )


class DiscoveredDevice(PrimaryModel):
    ip_address = GenericIPAddressField(unique=True)

    ssh_response = BooleanField(default=False)
    ssh_response_datetime = DateTimeField(blank=True, null=True)
    ssh_issue = CharField(choices=SshIssuesChoices.CHOICES, blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH)
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
    service: Literal['ssh', 'snmp', 'api']

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}:{self.service}"

    @classmethod
    def from_args(cls, ip, port, service):
        return cls(ip, port, service)

    @classmethod
    def from_string(cls, value: str):
        try:
            ip, port, service = value.strip().split(":")
            return cls.from_args(ip, port, service)
        except ValueError as e:
            raise ValueError(f"Invalid format for DeviceService string: {value!r}") from e


@dataclass
class DiscoveryResult:
    hostname: Optional[str] = None
    device_model: Optional[str] = None
    serial: Optional[str] = None
    network_driver: Optional[str] = None


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
    ]] = None

    banner: str = ""
    last_seen: str = ""
    discovery_result: DiscoveryResult = field(default_factory=DiscoveryResult)

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

from collections import defaultdict
from typing import Iterator

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

    # def get(self, ip: str, port: int, service: Literal['ssh', 'snmp', 'api']) -> Optional[ProbedDeviceServices]:
    #     key = DeviceService(ip, port, service)
    #     return self._entries.get(key)

    def filter(self, **kwargs) -> list['ProbedDeviceServices']:
        def match(entry) -> bool:
            for key, value in kwargs.items():
                if key.endswith("__in"):
                    attr = key[:-4]
                    if getattr(entry, attr, None) not in value:
                        return False
                elif key.endswith("__not"):
                    attr = key[:-5]
                    if getattr(entry, attr, None) == value:
                        return False
                else:
                    if getattr(entry, key, None) != value:
                        return False
            return True

        return [entry for entry in self._entries.values() if match(entry)]

    # def group_by_ip_and_service(self) -> dict[tuple[str, str], list[ProbedDeviceServices]]:
    #     grouped = defaultdict(list)
    #
    #     for entry in self._entries.values():
    #         key = (entry.service.ip, entry.service.service)
    #         grouped[key].append(entry)
    #
    #     return grouped

    # from collections import defaultdict
    #
    # def reachable_and_unreachable_ips(self, service: Optional[str] = None) -> tuple[set[str], set[str]]:
    #     status_by_ip = defaultdict(list)
    #
    #     for entry in self._entries.values():
    #         if service is None or entry.service.service == service:
    #             status_by_ip[entry.service.ip].append(entry.port_status)
    #
    #     reachable = {ip for ip, statuses in status_by_ip.items() if "open" in statuses}
    #     unreachable = set(status_by_ip.keys()) - reachable
    #     return reachable, unreachable
    #
    # def reachable_ips(self, service: Optional[str] = None) -> set[str]:
    #     reachable, _ = self.reachable_and_unreachable_ips(service)
    #     return reachable
    #
    # def unreachable_ips(self, service: Optional[str] = None) -> set[str]:
    #     _, unreachable = self.reachable_and_unreachable_ips(service)
    #     return unreachable

    def to_json(self) -> str:
        return json.dumps(
            [entry.to_dict() for entry in self._entries.values()],
            indent=2
        )

    def from_json(self, json_str: str):
        data = json.loads(json_str)
        for entry in data:
            service = DeviceService(
                ip=entry["ip"],
                port=entry["port"],
                service=entry["service"]
            )
            discovery_result = DiscoveryResult(
                hostname=entry.get("hostname"),
                device_model=entry.get("device_model"),
                serial_number=entry.get("serial_number")
            )
            probed = ProbedDeviceServices(
                service=service,
                port_status=entry.get("port_status"),
                service_status=entry.get("service_status"),
                banner=entry.get("banner", ""),
                last_seen=entry.get("last_seen", ""),
                discovery_result=discovery_result
            )
            self.add_or_update(probed)
