"""Utility functions for use with diffsync."""

import ipaddress

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.apps.choices import PrefixTypeChoices
from nautobot.dcim.models import Device
from nautobot.ipam.models import IPAddress, Prefix


def generate_device_queryset_from_command_getter_result(job, command_getter_result):
    """Generate a Nautobot device queryset based on data returned from Command Getter Nornir Task."""
    devices_to_sync_hostnames = []
    devices_to_sync_serial_numbers = []
    devices_with_errors = []
    for hostname, device_data in command_getter_result.items():
        try:
            devices_to_sync_hostnames.append(hostname)
            devices_to_sync_serial_numbers.append(device_data["serial"])
        except Exception as err:
            devices_with_errors.append(hostname)
            job.logger.error(f"Error while creating device queryset, hostname: {hostname}, {type(err).__name__} {err}")
            if job.debug:
                job.logger.debug(f"{hostname}: {device_data}")
            continue
    device_queryset = Device.objects.filter(name__in=devices_to_sync_hostnames).filter(
        serial__in=devices_to_sync_serial_numbers
    )
    return device_queryset, devices_with_errors


def check_data_type(data):
    """Verify data is of type dict."""
    data_type_check_result = True
    if not isinstance(data, dict):
        data_type_check_result = False
    return data_type_check_result


def get_or_create_prefix(host, mask_length, default_status, namespace, job=None):
    """Attempt to get a Nautobot Prefix, and create a new one if necessary."""
    prefix = None
    new_network = ipaddress.ip_interface(f"{host}/{mask_length}")
    try:
        prefix = Prefix.objects.get(
            prefix=f"{new_network.network}",
            namespace=namespace,
        )
    except ObjectDoesNotExist:
        prefix = Prefix(
            prefix=f"{new_network.network}",
            namespace=namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=default_status,
        )
        try:
            prefix.validated_save()
        except ValidationError as err:
            if job:
                job.logger.error(f"Prefix {host} failed to create, {err}")
    return prefix


def get_or_create_ip_address(host, mask_length, namespace, default_ip_status, default_prefix_status, job=None):
    """Attempt to get a Nautobot IPAddress, and create a new one if necessary."""
    ip_address = None

    try:
        ip_address = IPAddress.objects.get(
            host=host,
            parent__namespace=namespace,
        )
    except ObjectDoesNotExist:
        try:
            ip_address = IPAddress(
                address=f"{host}/{mask_length}",
                namespace=namespace,
                status=default_ip_status,
            )
            ip_address.validated_save()
        except ValidationError:
            if job:
                job.logger.warning(
                    f"No suitable parent Prefix exists for IP {host} in "
                    f"Namespace {namespace.name}, a new Prefix will be created."
                )
            prefix = get_or_create_prefix(host, mask_length, default_prefix_status, namespace, job)
            ip_address = IPAddress.objects.create(
                address=f"{host}/{mask_length}",
                status=default_ip_status,
                parent=prefix,
            )
        try:
            ip_address.validated_save()
        except ValidationError as err:
            if job:
                job.logger.error(f"IP Address {host} failed to create, {err}")
    return ip_address
