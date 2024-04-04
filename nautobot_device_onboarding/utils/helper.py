"""helper.py."""
import os
import socket
import netaddr
import yaml
from netaddr.core import AddrFormatError
from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import Device
from nautobot.extras.models import GitRepository
from nornir_nautobot.exceptions import NornirNautobotException

from nautobot_device_onboarding.exceptions import OnboardException

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))

FIELDS_PK = {
    "location",
    "role",
}

FIELDS_NAME = {"tags"}


def get_job_filter(data=None):
    """Helper function to return a the filterable list of OS's based on platform.name and a specific custom value."""
    if not data:
        data = {}
    query = {}

    # Translate instances from FIELDS set to list of primary keys
    for field in FIELDS_PK:
        if data.get(field):
            query[field] = [str(data[field].id)]

    # Translate instances from FIELDS set to list of names
    for field in FIELDS_NAME:
        if data.get(field):
            query[field] = [str(data[field].id)]
    # Handle case where object is from single device run all.
    if data.get("devices") and isinstance(data["devices"], Device):
        query.update({"id": [str(data["devices"].pk)]})
    elif data.get("devices"):
        query.update({"id": data["devices"].values_list("pk", flat=True)})
    base_qs = Device.objects.all()
    # {'debug': False, 'namespace': <Namespace: Global>, 'devices': <ConfigContextModelQuerySet [<Device: demo-cisco-xe>]>, 'location': None, 'device_role': None, 'tag': None, 'port': 22, 'timeout': 30}
    devices_filtered = DeviceFilterSet(data=query, queryset=base_qs)

    if not devices_filtered.qs.exists():
        raise NornirNautobotException(
            "`E3016:` The provided job parameters didn't match any devices detected. Please select the correct job parameters to correctly match devices."
        )
    devices_no_platform = devices_filtered.qs.filter(platform__isnull=True)
    if devices_no_platform.exists():
        raise NornirNautobotException(
            f"`E3017:` The following device(s) {', '.join([device.name for device in devices_no_platform])} have no platform defined. Platform is required."
        )

    return devices_filtered.qs


def onboarding_task_fqdn_to_ip(address):
    """Method to assure OT has FQDN resolved to IP address and rewritten into OT.

    If it is a DNS name, attempt to resolve the DNS address and assign the IP address to the
    name.

    Returns:
        None

    Raises:
        OnboardException("fail-general"):
            When a prefix was entered for an IP address
        OnboardException("fail-dns"):
            When a Name lookup via DNS fails to resolve an IP address
    """
    try:
        # If successful, this is an IP address and can pass
        netaddr.IPAddress(address)
        return address
    # Raise an Exception for Prefix values
    except ValueError as err:
        raise OnboardException(f"fail-general - ERROR appears a prefix was entered: {address}") from err
    # An AddrFormatError exception means that there is not an IP address in the field, and should continue on
    except AddrFormatError:
        try:
            # Perform DNS Lookup
            return socket.gethostbyname(address)
        except socket.gaierror as err:
            # DNS Lookup has failed, Raise an exception for unable to complete DNS lookup
            raise OnboardException(f"fail-dns - ERROR failed to complete DNS lookup: {address}") from err


def add_platform_parsing_info(host):
    """This nornir transform function adds platform parsing info."""
    repository_record = GitRepository.objects.filter(provided_contents=['nautobot_device_onboarding.onboarding_command_mappers']).first()
    repo_data_dir = os.path.join(repository_record.filesystem_path, 'onboarding_command_mappers')
    command_mapper_defaults = load_command_mappers_from_dir(DATA_DIR)
    command_mappers_repo_path = load_command_mappers_from_dir(repo_data_dir)
    # parsing_info = _get_default_platform_parsing_info(host.platform)
    merged_command_mappers = {**command_mapper_defaults, **command_mappers_repo_path}
    # This is so we can reuse this for a non-nornir host object since we don't have it in an empty inventory at this point.
    if not isinstance(host, str):
        host.data.update({"platform_parsing_info": merged_command_mappers})
    return merged_command_mappers


def load_command_mappers_from_dir(command_mappers_path):
    """Helper to load all yaml files in directory and return merged dictionary."""
    command_mappers_result = {}
    for filename in os.listdir(command_mappers_path):
        with open(os.path.join(command_mappers_path, filename), encoding="utf-8") as fd:
            network_driver = filename.split('.')[0]
            command_mappers_data = yaml.safe_load(fd)
            command_mappers_result[network_driver] = command_mappers_data
        return command_mappers_result
