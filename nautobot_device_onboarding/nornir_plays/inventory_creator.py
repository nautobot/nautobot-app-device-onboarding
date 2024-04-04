"""Inventory Creator and Helpers."""

from netmiko import SSHDetect
from nornir.core.inventory import ConnectionOptions, Host

from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info


def guess_netmiko_device_type(hostname, username, password, port):
    """Guess the device type of host, based on Netmiko."""
    guessed_device_type = None

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

    except Exception as err:
        print(err)
    print(f"{hostname} - guessed platform: {guessed_device_type}")
    return guessed_device_type


def _set_inventory(host_ip, platform, port, username, password):
    """Construct Nornir Inventory."""
    parsing_info = add_platform_parsing_info(host_ip)
    inv = {}
    if platform:
        platform = platform.network_driver
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
        data={"platform_parsing_info": parsing_info[platform]},
    )
    inv.update({host_ip: host})

    return inv
