"""Inventory Creator and Helpers."""

from netmiko import SSHDetect
from nornir.core.inventory import ConnectionOptions, Host


def guess_netmiko_device_type(hostname, username, password, port):
    """Guess the device type of host, based on Netmiko."""
    netmiko_optional_args = {"port": port}

    remote_device = {
        "device_type": "autodetect",
        "host": hostname,
        "username": username,
        "password": password,
        **netmiko_optional_args,
    }

    try:
        guesser = SSHDetect(**remote_device)
        guessed_device_type = guesser.autodetect()

    except Exception:  # pylint: disable=broad-exception-caught
        guessed_device_type = None
        # Additional checking is done later in the process. We shouldn't reraise an error as it causes the job to fail.
    return guessed_device_type


def _set_inventory(host_ip, platform, port, username, password):
    """Construct Nornir Inventory."""
    inv = {}
    if platform:
        platform = platform.network_driver_mappings.get("netmiko")
    else:
        platform = guess_netmiko_device_type(host_ip, username, password, port)
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
            )
        },
    )
    inv.update({host_ip: host})

    return inv
