"""Inventory Creator and Helpers."""

from typing import Dict, Tuple, Union

from netmiko import SSHDetect
from nornir.core.inventory import ConnectionOptions, Host

from nautobot_device_onboarding.constants import NETMIKO_EXTRAS


def guess_netmiko_device_type(
    hostname: str, username: str, password: str, port: str
) -> Tuple[str, Union[Exception, None]]:
    """Guess the device type of host, based on Netmiko."""
    netmiko_optional_args = {"port": port, **NETMIKO_EXTRAS}
    guessed_device_type = None

    remote_device = {
        "device_type": "autodetect",
        "host": hostname,
        "username": username,
        "password": password,
        **netmiko_optional_args,
    }
    guessed_exc = None
    try:
        guesser = SSHDetect(**remote_device)
        guessed_device_type = guesser.autodetect()

    except Exception as err:  # pylint: disable=broad-exception-caught
        guessed_device_type = None
        guessed_exc = err
        # Additional checking is done later in the process. We shouldn't reraise an error as it causes the job to fail.
    return guessed_device_type, guessed_exc


def _set_inventory(
    host_ip: str, platform: str, port: str, username: str, password: str
) -> Tuple[Dict, Union[Exception, None]]:
    """Construct Nornir Inventory."""
    inv = {}
    if platform:
        platform_guess_exc = None
        platform = platform.network_driver_mappings.get("netmiko")
    else:
        platform, platform_guess_exc = guess_netmiko_device_type(host_ip, username, password, port)
    host = Host(
        name=host_ip,
        hostname=host_ip,
        port=int(port),
        username=username,
        password=password,
        platform=platform,
        connection_options={
            "netmiko": ConnectionOptions(
                hostname=host_ip,
                port=int(port),
                username=username,
                password=password,
                platform=platform,
                extras=NETMIKO_EXTRAS,
            )
        },
    )
    if not platform_guess_exc:
        inv.update({host_ip: host})

    return inv, platform_guess_exc
