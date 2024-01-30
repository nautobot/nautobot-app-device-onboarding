"""NetDev Keeper."""

import importlib
import logging
import socket

from django.conf import settings
from napalm import get_network_driver
from napalm.base.exceptions import CommandErrorException, ConnectionException
from napalm.base.netmiko_helpers import netmiko_args
from nautobot.dcim.models import Platform
from netmiko import NetMikoAuthenticationException, NetMikoTimeoutException, SSHDetect
from paramiko.ssh_exception import SSHException

from nautobot_device_onboarding.constants import NETMIKO_TO_NAPALM_STATIC
from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.onboarding.onboarding import StandaloneOnboarding

logger = logging.getLogger("rq.worker")

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_device_onboarding"]


def get_mgmt_info(
    hostname,
    ip_ifs,
    default_mgmt_if=PLUGIN_SETTINGS["default_management_interface"],
    default_mgmt_pfxlen=PLUGIN_SETTINGS["default_management_prefix_length"],
):
    """Get the interface name and prefix length for the management interface.

    Locate the interface assigned with the hostname value and retain
    the interface name and IP prefix-length so that we can use it
    when creating the IPAM IP-Address instance.

    Note that in some cases (e.g., NAT) the hostname may differ than
    the interface addresses present on the device. We need to handle this.
    """
    for if_name, if_data in ip_ifs.items():
        if "ipv4" in if_data:
            for if_addr, if_addr_data in if_data["ipv4"].items():
                if if_addr == hostname:
                    return if_name, if_addr_data["prefix_length"]

    return default_mgmt_if, default_mgmt_pfxlen


class NetdevKeeper:  # pylint: disable=too-many-instance-attributes
    """Used to maintain information about the network device during the onboarding process."""

    def __init__(  # pylint: disable=R0913
        self,
        hostname,
        port=None,
        timeout=None,
        username=None,
        password=None,
        secret=None,
        napalm_driver=None,
        optional_args=None,
    ):
        """Initialize the network device keeper instance and ensure the required configuration parameters are provided.

        Args:
          hostname (str): IP Address or FQDN of an onboarded device
          port (int): Port used to connect to an onboarded device
          timeout (int): Connection timeout of an onboarded device
          username (str): Device username (if unspecified, NAPALM_USERNAME settings variable will be used)
          password (str): Device password (if unspecified, NAPALM_PASSWORD settings variable will be used)
          secret (str): Device secret password (if unspecified, NAPALM_ARGS["secret"] settings variable will be used)
          napalm_driver (str): Napalm driver name to use to onboard network device
          optional_args (dict): Optional arguments passed to NAPALM and Netmiko

        Raises:
          OnboardException('fail-config'):
            When any required config options are missing.
        """
        # Attributes
        self.hostname = hostname
        self.port = port
        self.timeout = timeout
        self.username = username
        self.password = password
        self.secret = secret
        self.napalm_driver = napalm_driver

        # Netmiko and NAPALM expects optional_args to be a dictionary.
        if isinstance(optional_args, dict):
            self.optional_args = optional_args
        elif optional_args is None:
            self.optional_args = {}
        else:
            raise OnboardException("fail-general - Optional arguments should be None or a dict")

        self.facts = None
        self.ip_ifs = None
        self.netmiko_device_type = None
        self.onboarding_class = StandaloneOnboarding
        self.driver_addon_result = None

        # Enable loading driver extensions
        self.load_driver_extension = True

    def check_reachability(self):
        """Ensure that the device at the mgmt-ipaddr provided is reachable.

        We do this check before attempting other "show" commands so that we know we've got a
        device that can be reached.

        Raises:
          OnboardException('fail-connect'):
            When device unreachable
        """
        logger.info("CHECK: IP %s:%s", self.hostname, self.port)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.hostname, self.port))

        except (socket.error, socket.timeout, ConnectionError) as err:
            raise OnboardException(f"fail-connect - ERROR device unreachable: {self.hostname}:{self.port}") from err

    def guess_netmiko_device_type(self):
        """Guess the device type of host, based on Netmiko."""
        guessed_device_type = None

        netmiko_optional_args = netmiko_args(self.optional_args)

        remote_device = {
            "device_type": "autodetect",
            "host": self.hostname,
            "username": self.username,
            "password": self.password,
            **netmiko_optional_args,
        }

        if self.secret:
            remote_device["secret"] = self.secret

        if self.port:
            remote_device["port"] = self.port

        if self.timeout:
            remote_device["timeout"] = self.timeout

        try:
            logger.info("INFO guessing device type: %s", self.hostname)
            guesser = SSHDetect(**remote_device)
            guessed_device_type = guesser.autodetect()
            logger.info("INFO guessed device type: %s", guessed_device_type)

        except NetMikoAuthenticationException as err:
            logger.error("ERROR %s", err)
            raise OnboardException(f"fail-login - ERROR: {str(err)}") from err

        except (NetMikoTimeoutException, SSHException) as err:
            logger.error("ERROR: %s", str(err))
            raise OnboardException(f"fail-connect - ERROR: {str(err)}") from err

        except Exception as err:
            logger.error("ERROR: %s", str(err))
            raise OnboardException(f"fail-general - ERROR: {str(err)}") from err

        if guessed_device_type is None:
            logger.error("ERROR: Could not detect device type with SSHDetect")
            raise OnboardException("fail-general - ERROR: Could not detect device type with SSHDetect")

        return guessed_device_type

    def set_napalm_driver_name(self):
        """Sets napalm driver name."""
        if not self.napalm_driver:
            netmiko_device_type = self.guess_netmiko_device_type()
            logger.info("Guessed Netmiko Device Type: %s", netmiko_device_type)

            self.netmiko_device_type = netmiko_device_type

            platform_to_napalm_nautobot = {
                platform: platform.napalm_driver for platform in Platform.objects.all() if platform.napalm_driver
            }

            # Update Constants if Napalm driver is defined for Nautobot Platform
            netmiko_to_napalm = {**NETMIKO_TO_NAPALM_STATIC, **platform_to_napalm_nautobot}

            self.napalm_driver = netmiko_to_napalm.get(netmiko_device_type)

    def check_napalm_driver_name(self):
        """Checks for napalm driver name."""
        if not self.napalm_driver:
            raise OnboardException(
                f"fail-general - Onboarding for Platform {self.netmiko_device_type} not "
                f"supported, as it has no specified NAPALM driver",
            )

    def get_onboarding_facts(self):
        """Gather information from the network device that is needed to onboard the device into the Nautobot system.

        Raises:
          OnboardException('fail-login'):
            When unable to login to device

          OnboardException('fail-execute'):
            When unable to run commands to collect device information

          OnboardException('fail-general'):
            Any other unexpected device comms failure.
        """
        self.check_reachability()

        logger.info("COLLECT: device information %s", self.hostname)

        try:
            # Get Napalm Driver with Netmiko if needed
            self.set_napalm_driver_name()

            # Raise if no Napalm Driver not selected
            self.check_napalm_driver_name()

            driver = get_network_driver(self.napalm_driver)

            # Create NAPALM optional arguments
            napalm_optional_args = self.optional_args.copy()

            if self.port:
                napalm_optional_args["port"] = self.port

            if self.secret:
                napalm_optional_args["secret"] = self.secret

            napalm_device = driver(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                optional_args=napalm_optional_args,
            )

            napalm_device.open()

            logger.info("COLLECT: device facts")
            self.facts = napalm_device.get_facts()

            logger.info("COLLECT: device interface IPs")
            self.ip_ifs = napalm_device.get_interfaces_ip()

            module_name = PLUGIN_SETTINGS["onboarding_extensions_map"].get(self.napalm_driver)

            if module_name and self.load_driver_extension:
                try:
                    module = importlib.import_module(module_name)
                    driver_addon_class = module.OnboardingDriverExtensions(napalm_device=napalm_device)
                    self.onboarding_class = driver_addon_class.onboarding_class
                    self.driver_addon_result = driver_addon_class.ext_result
                except ModuleNotFoundError as err:
                    raise OnboardException(
                        f"fail-general - ERROR: ModuleNotFoundError: Onboarding extension for napalm driver {self.napalm_driver} configured but can not be imported per configuration",
                    ) from err
                except ImportError as err:
                    raise OnboardException(f"fail-general - ERROR: ImportError: {err.args[0]}") from err
            elif module_name and not self.load_driver_extension:
                logger.info("INFO: Skipping execution of driver extension")
            else:
                logger.info(
                    "INFO: No onboarding extension defined for napalm driver %s, using default napalm driver",
                    self.napalm_driver,
                )
            napalm_device.close()

        except ConnectionException as err:
            raise OnboardException(f"fail-login - {err.args[0]}") from err

        except CommandErrorException as err:
            raise OnboardException(f"fail-execute - {err.args[0]}") from err

        except Exception as err:
            raise OnboardException(f"fail-general - {str(err)}") from err

    def get_netdev_dict(self):
        """Construct network device dict."""
        netdev_dict = {
            "netdev_hostname": self.facts["hostname"],
            "netdev_vendor": self.facts["vendor"].title(),
            "netdev_model": self.facts["model"].lower(),
            "netdev_serial_number": self.facts["serial_number"],
            "netdev_mgmt_ifname": get_mgmt_info(hostname=self.hostname, ip_ifs=self.ip_ifs)[0],
            "netdev_mgmt_pflen": get_mgmt_info(hostname=self.hostname, ip_ifs=self.ip_ifs)[1],
            "netdev_netmiko_device_type": self.netmiko_device_type,
            "onboarding_class": self.onboarding_class,
            "driver_addon_result": self.driver_addon_result,
        }

        return netdev_dict
