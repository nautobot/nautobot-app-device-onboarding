"""Unit tests for nautobot_device_onboarding.netdev_keeper module and its classes.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from socket import gaierror
from unittest import mock

from django.test import TestCase
from nautobot.dcim.models import Site, DeviceRole, Platform

from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.netdev_keeper import NetdevKeeper
from nautobot_device_onboarding.models import OnboardingTask


class NetdevKeeperTestCase(TestCase):
    """Test the NetdevKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.site1 = Site.objects.create(name="USWEST", slug="uswest")
        self.device_role1 = DeviceRole.objects.create(name="Firewall", slug="firewall")

        self.platform1 = Platform.objects.create(name="JunOS", slug="junos", napalm_driver="junos")
        # self.platform2 = Platform.objects.create(name="Cisco NX-OS", slug="cisco-nx-os")

        self.onboarding_task4 = OnboardingTask.objects.create(
            ip_address="ntc123.local", site=self.site1, role=self.device_role1, platform=self.platform1
        )

        self.onboarding_task5 = OnboardingTask.objects.create(
            ip_address="bad.local", site=self.site1, role=self.device_role1, platform=self.platform1
        )

        self.onboarding_task7 = OnboardingTask.objects.create(
            ip_address="192.0.2.1/32", site=self.site1, role=self.device_role1, platform=self.platform1
        )

        # Apply patch on connectivity check
        self.reachability_patch = mock.patch("nautobot_device_onboarding.netdev_keeper.NetdevKeeper.check_reachability")
        self.reachability_patch.start()

    def tearDown(self):
        """Disable patches."""
        self.reachability_patch.stop()

    @mock.patch("nautobot_device_onboarding.netdev_keeper.socket.gethostbyname")
    def test_check_ip(self, mock_get_hostbyname):
        """Check DNS to IP address."""
        # Look up response value
        mock_get_hostbyname.return_value = "192.0.2.1"

        # FQDN -> IP
        hostname = self.onboarding_task4.ip_address
        napalm_driver = self.onboarding_task4.platform.napalm_driver
        nk = NetdevKeeper(hostname, napalm_driver=napalm_driver)

        # Run the check to change the IP address
        self.assertEqual(nk.hostname, "192.0.2.1")

    @mock.patch("nautobot_device_onboarding.netdev_keeper.socket.gethostbyname")
    def test_failed_check_ip(self, mock_get_hostbyname):
        """Check DNS to IP address failing."""
        # Look up a failed response
        mock_get_hostbyname.side_effect = gaierror(8)

        # Check for bad.local raising an exception
        with self.assertRaises(OnboardException) as exc_info:
            hostname = self.onboarding_task5.ip_address
            napalm_driver = self.onboarding_task5.platform.napalm_driver
            NetdevKeeper(hostname, napalm_driver=napalm_driver)
        self.assertEqual(exc_info.exception.message, "ERROR failed to complete DNS lookup: bad.local")
        self.assertEqual(exc_info.exception.reason, "fail-dns")

    def test_failed_check_prefix(self):
        """Check for exception with prefix address entered."""
        with self.assertRaises(OnboardException) as exc_info:
            hostname = self.onboarding_task7.ip_address
            napalm_driver = self.onboarding_task7.platform.napalm_driver
            NetdevKeeper(hostname, napalm_driver=napalm_driver)
        self.assertEqual(exc_info.exception.reason, "fail-prefix")
        self.assertEqual(exc_info.exception.message, "ERROR appears a prefix was entered: 192.0.2.1/32")
