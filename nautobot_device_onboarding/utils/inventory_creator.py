"""Inventory Creator and Helpers."""

from django.conf import settings
from nautobot.dcim.models import Platform
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from netmiko import SSHDetect
from nornir.core.inventory import ConnectionOptions, Host

from nautobot_device_onboarding.exceptions import OnboardException


def _parse_credentials(credentials):
    """Parse and return dictionary of credentials."""
    if credentials:
        try:
            username = credentials.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
            password = credentials.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            )
            try:
                secret = credentials.get_secret_value(
                    access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                    secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
                )
            except Exception:
                secret = None
        except Exception as err:
            raise OnboardException("fail-credentials - Unable to parse selected credentials.") from err
    else:
        username = settings.NAPALM_USERNAME
        password = settings.NAPALM_PASSWORD
        secret = settings.NAPALM_ARGS.get("secret", None)
    return (username, password, secret)

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
    print(f"************************Guessed device type: {guessed_device_type}")
    return guessed_device_type

def _set_inventory(host_ip, platform, port, secrets_group):
    """Construct Nornir Inventory."""
    inv = {}
    username, password, secret = _parse_credentials(secrets_group)
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
    )
    inv.update({host_ip: host})

    return inv
