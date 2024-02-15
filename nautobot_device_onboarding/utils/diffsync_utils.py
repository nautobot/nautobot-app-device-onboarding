"""Utility functions for use with diffsync."""

import ipaddress

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from nautobot.apps.choices import PrefixTypeChoices
from nautobot.ipam.models import IPAddress, Prefix


def get_or_create_prefix(host, mask_length, default_status, namespace, job=None):
    """Attempt to get a Nautobot Prefix, create a new one if necessary."""
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
    """Attempt to get a Nautobot IPAddress, create a new one if necessary."""
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
