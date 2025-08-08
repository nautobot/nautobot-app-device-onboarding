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
    SERVICE_UNAUTHENTICATED = "service_unauthenticated"
    SERVICE_AUTHENTICATED = "service_authenticated"
    SERVICE_INVALID_COMMAND = "invalid_command"
    SERVICE_PARSING_ERROR = "parsing_error"
    SERVICE_DATA_COLLECTED = "service_data_collected"
    UNKNOWN = "unknown"

    CHOICES = (
        (PORT_CLOSED, "Port closed"),
        (PORT_OPENED, "Port opened"),
        (SERVICE_UNAUTHENTICATED, "Service unauthenticated"),
        (SERVICE_AUTHENTICATED, "Service authenticated"),
        (SERVICE_INVALID_COMMAND, "Invalid command"),
        (SERVICE_PARSING_ERROR, "Parsing error"),
        (SERVICE_DATA_COLLECTED, "Service data collected"),
        (UNKNOWN, "Unknown"),
    )


class DiscoveredDevice(PrimaryModel):
    ip_address = GenericIPAddressField(unique=True)
    # ignore = BooleanField(default=False, verbose_name="Ignore")  # TODO(mzb): skip/ignore flag

    ssh_response = BooleanField(default=False, verbose_name="SSH login")
    ssh_response_datetime = DateTimeField(blank=True, null=True, verbose_name="SSH last response")
    ssh_issue = CharField(choices=SshStateChoices.CHOICES, blank=True, null=True, max_length=CHARFIELD_MAX_LENGTH, verbose_name="SSH issue")  # TODO(mzb): Rename to ssh_status!
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
    """
    Represents a network device service uniquely identified by an IP address, port number, and service name.

    Attributes:
        ip (str): The IP address of the device.
        port (int): The port number on which the service is running.
        name (Literal['ssh', 'snmp', 'api']): The type of service; must be one of 'ssh', 'snmp', or 'api'.

    Methods:
        __str__():
            Returns a string representation of the DeviceService in the format "ip:port:name".

        from_args(ip: str, port: int | str, name: str) -> DeviceService:
            Creates a DeviceService instance from separate arguments.
            Ensures that 'name' is one of the allowed service types and converts port to an integer.

        from_string(value: str) -> DeviceService:
            Parses a DeviceService from a string formatted as "ip:port:name".
            Raises ValueError if the format is invalid or the service name is not allowed.
    """

    ip: str
    port: int
    name: Literal['ssh', 'snmp', 'api']

    def __str__(self) -> str:
        """
        Return a concise string representation of the device service.

        Returns:
            str: A string in the format "ip:port:name".
        """
        return f"{self.ip}:{self.port}:{self.name}"

    @classmethod
    def from_args(cls, ip: str, port: int | str, name: str) -> "DeviceService":
        """
        Create a DeviceService from individual arguments, ensuring proper types and values.

        Args:
            ip (str): IP address of the device.
            port (int | str): Port number, either as int or string convertible to int.
            name (str): Service name; must be one of 'ssh', 'snmp', or 'api'.

        Raises:
            ValueError: If 'name' is not one of the allowed values.

        Returns:
            DeviceService: A new instance of DeviceService.
        """
        if name not in ('ssh', 'snmp', 'api'):
            raise ValueError(f"Invalid service name: {name!r}. Must be one of 'ssh', 'snmp', 'api'.")
        return cls(ip=ip, port=int(port), name=name)

    @classmethod
    def from_string(cls, value: str) -> "DeviceService":
        """
        Parse a DeviceService from a string formatted as 'ip:port:name'.

        Args:
            value (str): The string to parse.

        Raises:
            ValueError: If the string is not properly formatted or contains invalid service name.

        Returns:
            DeviceService: A new instance of DeviceService parsed from the string.
        """
        try:
            ip, port, name = value.strip().split(":")
        except ValueError as e:
            raise ValueError(
                f"Invalid format for DeviceService string: {value!r}. "
                "Expected format 'ip:port:name'."
            ) from e
        return cls.from_args(ip, port, name)


@dataclass
class ProbedDeviceServices:
    """
    Represents a device service that has been probed for accessibility and metadata.

    Attributes:
        service (DeviceService): The service being probed, including IP, port, and type.
        port_status (str | None): Result of probing the port ('open', 'unreachable', or 'filtered').
        service_status (str | None): Result of attempting to interact with the service.
        ssh_username (str | None): SSH username if service is SSH and credentials are known.
        ssh_password (str | None): SSH password.
        ssh_timeout (int | None): Timeout (in seconds) for SSH attempts.
        network_driver (str | None): Network driver/platform (e.g., 'cisco_ios').
        hostname (str | None): Hostname discovered during probing.
        device_model (str | None): Device model string.
        serial (str | None): Device serial number.
    """

    service: DeviceService

    port_status: Optional[
        Literal[
            SshStateChoices.PORT_CLOSED,
            SshStateChoices.PORT_OPENED,
        ]
    ] = None

    service_status: Optional[
        Literal[
            SshStateChoices.SERVICE_UNAUTHENTICATED,
            SshStateChoices.SERVICE_AUTHENTICATED,
            SshStateChoices.SERVICE_INVALID_COMMAND,
            SshStateChoices.SERVICE_PARSING_ERROR,
            SshStateChoices.SERVICE_DATA_COLLECTED,
            SshStateChoices.UNKNOWN,
        ]
    ] = None

    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_timeout: Optional[int] = None
    network_driver: Optional[str] = None
    hostname: Optional[str] = None
    device_model: Optional[str] = None
    serial: Optional[str] = None

    def __str__(self) -> str:
        """Return a human-readable representation of the probed service."""
        return str(self.service)

    def to_nornir_host(self, name_eq_ip: bool = False):
        """
        Convert this object into a Nornir Host object for inventory purposes.

        Args:
            name_eq_ip (bool): If True, the Nornir host name will be the IP address.
                               Otherwise, uses full 'ip:port:name' string.

        Returns:
            Host: A Nornir-compatible Host object.
        """
        return Host(
            name=self.service.ip if name_eq_ip else str(self.service),
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
        }
        return {**base}


class ProbedDeviceStore:
    """
    A container for storing and managing `ProbedDeviceServices` instances keyed by their associated `DeviceService`.

    This class provides dictionary-like access to probed device services, along with convenience methods
    for adding, updating, filtering, and serializing entries.

    Attributes:
        _entries (dict[DeviceService, ProbedDeviceServices]):
            Internal dictionary mapping each unique DeviceService to its probed service data.

    Methods:
        __contains__(item: DeviceService) -> bool:
            Check if a DeviceService is present in the store.

        __iter__():
            Iterate over all stored ProbedDeviceServices instances.

        __getitem__(key: DeviceService) -> ProbedDeviceServices:
            Retrieve a ProbedDeviceServices instance by its DeviceService key.

        __setitem__(key: DeviceService, value: ProbedDeviceServices):
            Add or update a ProbedDeviceServices entry by its DeviceService key.

        __delitem__(key: DeviceService):
            Remove a ProbedDeviceServices entry by its DeviceService key.

        __len__() -> int:
            Return the number of entries stored.

        add_or_update(probed_device_services: ProbedDeviceServices):
            Add a new or update an existing entry using the DeviceService as key.

        filter(**kwargs) -> list[ProbedDeviceServices]:
            Filter stored entries by arbitrary attributes using Django-style lookup expressions.

            Supports nested attribute lookups (e.g., `service__ip='192.168.1.1'`) and special operators:
            - `__in`: inclusion check (value should be iterable)
            - `__not`: negation check

            Returns:
                A list of ProbedDeviceServices matching the filter criteria.

        to_json() -> str:
            Serialize all stored entries to a JSON-formatted string.
    """

    def __init__(self):
        self._entries: dict[DeviceService, ProbedDeviceServices] = {}

    def __contains__(self, item: DeviceService) -> bool:
        """
        Check whether a DeviceService key exists in the store.

        Args:
            item (DeviceService): The device service key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return item in self._entries

    def __iter__(self):
        """
        Iterate over all stored ProbedDeviceServices instances.

        Returns:
            Iterator[ProbedDeviceServices]: An iterator over all stored values.
        """
        return iter(self._entries.values())

    def __getitem__(self, key: DeviceService) -> ProbedDeviceServices:
        """
        Retrieve a ProbedDeviceServices entry by DeviceService key.

        Args:
            key (DeviceService): The device service key to look up.

        Returns:
            ProbedDeviceServices: The corresponding probed service data.

        Raises:
            KeyError: If the key is not found.
        """
        return self._entries[key]

    def __setitem__(self, key: DeviceService, value: ProbedDeviceServices):
        """
        Add or update a ProbedDeviceServices entry.

        Args:
            key (DeviceService): The device service key.
            value (ProbedDeviceServices): The probed service data to store.
        """
        self._entries[key] = value

    def __delitem__(self, key: DeviceService):
        """
        Remove a ProbedDeviceServices entry by its DeviceService key.

        Args:
            key (DeviceService): The key of the entry to remove.

        Raises:
            KeyError: If the key is not found.
        """
        del self._entries[key]

    def __len__(self):
        """
        Return the number of stored entries.

        Returns:
            int: Count of stored ProbedDeviceServices.
        """
        return len(self._entries)

    def add_or_update(self, probed_device_services: ProbedDeviceServices):
        """
        Add a new or update an existing ProbedDeviceServices entry, keyed by its DeviceService.

        Args:
            probed_device_services (ProbedDeviceServices): The probed device service data to add or update.
        """
        self._entries[probed_device_services.service] = probed_device_services

    def filter(self, **kwargs) -> list['ProbedDeviceServices']:
        """
        Filter stored entries based on attribute conditions.

        Supports nested attribute lookups using double underscores (e.g., `service__ip='192.168.1.1'`).

        Special lookup suffixes:
          - `__in`: checks if the attribute's value is in the given iterable.
          - `__not`: checks if the attribute's value is not equal to the given value.

        Args:
            **kwargs: Arbitrary attribute filters.

        Returns:
            list[ProbedDeviceServices]: List of entries matching all filter conditions.
        """
        def match(entry) -> bool:
            for key, value in kwargs.items():
                parts = key.split("__")
                # Determine operation type
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
                    return False  # Attribute path doesn't exist

                # Perform comparison based on operation
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
        """
        Serialize all stored entries to a pretty-printed JSON string.

        Assumes each ProbedDeviceServices instance has a `to_dict()` method returning serializable data.

        Returns:
            str: JSON-formatted string representing all stored entries.
        """
        return json.dumps(
            [entry.to_dict() for entry in self._entries.values()],
            indent=2
        )
