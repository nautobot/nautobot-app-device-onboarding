# nautobot_device_onboarding/onboarding_extensions/aoscx.py
"""
Aruba AOS-CX Virtual Chassis (VSF/VSX) Onboarding Extension.

Handles:
- VSF (Virtual Switching Fabric) stacks for 6100 series
- VSX (Virtual Switching Extension) pairs for 8300+ series

Uses ntc-templates for robust CLI output parsing.
"""

import logging
from typing import Any, Dict, Optional

from napalm.base.exceptions import CommandErrorException
from nautobot.dcim.models import Device, Status
from nautobot.extras.models import Tag

logger = logging.getLogger("rq.worker")


class OnboardingDriverExtensions:
    """
    Aruba AOS-CX NAPALM device extension.

    Collects virtual chassis information (VSF/VSX) with live NAPALM connection.
    Parses outputs using ntc-templates.
    """

    onboarding_class = "ArubaAoscxOnboarding"
    ext_result: Dict[str, Any] = {}

    def __init__(self, napalm_device):
        """
        Initialize with NAPALM device connection.

        Args:
            napalm_device: NAPALM device instance (connection open).
        """
        self.device = napalm_device

    def main(self) -> None:
        """
        Collect VSF and VSX data from device.

        Executes with active NAPALM connection.
        Results stored in self.ext_result for OnboardingClass to consume.
        """
        try:
            vsf_data = self._collect_vsf_data()
            vsx_data = self._collect_vsx_data()

            self.ext_result = {
                "vsf": vsf_data,
                "vsx": vsx_data,
            }

            logger.info(
                f"Virtual chassis data collected: VSF={bool(vsf_data)}, VSX={bool(vsx_data)}"
            )

        except Exception as e:
            logger.warning(f"Failed to collect virtual chassis data: {e}")
            self.ext_result = {"vsf": {}, "vsx": {}}

    def _collect_vsf_data(self) -> Dict[str, Any]:
        """
        Collect VSF (Virtual Switching Fabric) stack information.

        For 6100 series: parses 'show vsf detail' output using ntc-templates.

        Returns:
            Dictionary with keys:
            - topology: 'standalone', 'ring', 'stack' (or None if error)
            - stack_name: Name of VSF stack (or None)
            - conductor_member_id: Member ID of conductor (typically 1)
            - members: List of member dicts
                - member_id: int
                - status: 'Conductor', 'Member', 'Standby', 'Disabled'
                - serial_number: Device serial
                - mac_address: MAC of member
                - vsf_link_status: Dict of link statuses
        """
        try:
            # Execute CLI command
            raw_output = self.device.cli(["show vsf detail"])

            # Parse using ntc-templates
            vsf_data = self._parse_vsf_textfsm(raw_output)

            logger.debug(f"VSF data parsed: topology={vsf_data.get('topology')}")
            return vsf_data

        except CommandErrorException as e:
            # Device might not have VSF capability or no stack configured
            logger.debug(f"VSF command failed (may be standalone): {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to collect VSF data: {e}")
            return {}

    def _parse_vsf_textfsm(self, raw_output: str) -> Dict[str, Any]:
        """
        Parse 'show vsf detail' output using ntc-templates TextFSM.

        Args:
            raw_output: Raw CLI output string

        Returns:
            Structured dictionary with VSF topology and members
        """
        try:
            from ntc_templates.parse import parse_raw_text
        except ImportError:
            logger.error("ntc-templates not installed; VSF parsing unavailable")
            return {}

        try:
            # Parse using ntc-templates
            # Template: aruba_aoscx_show_vsf_detail.textfsm (exists since v2.3.0)
            parsed_list = parse_raw_text(
                raw_output, platform="aruba_aoscx", command="show vsf detail"
            )

            if not parsed_list:
                logger.debug("VSF output parsed empty (likely standalone)")
                return {}

            # ntc-templates returns a list of dicts (one per VSF)
            # For a single VSF stack, take the first entry
            vsf_entry = parsed_list[0] if parsed_list else {}

            # Normalize structure
            result = {
                "topology": vsf_entry.get("topology"),
                "stack_name": vsf_entry.get("stack_name"),
                "conductor_member_id": vsf_entry.get("conductor_member_id", 1),
                "members": vsf_entry.get("members", []),
            }

            logger.debug(f"VSF textfsm parsed: {len(result.get('members', []))} members")
            return result

        except Exception as e:
            logger.error(f"VSF TextFSM parsing failed: {e}")
            return {}

    def _collect_vsx_data(self) -> Dict[str, Any]:
        """
        Collect VSX (Virtual Switching Extension) pair information.

        For 8300+ series: parses 'show vsx detail' output using ntc-templates.

        Returns:
            Dictionary with keys:
            - system_role: 'Primary' or 'Secondary' (or None if not VSX)
            - peer_ip: IP address of VSX peer
            - isl_status: 'Up' or 'Down'
            - isl_port: Physical port used for ISL
            - local_mac: MAC address of this device
            - peer_mac: MAC address of peer
            - sync_status: Synchronization status string
        """
        try:
            # Execute CLI command
            raw_output = self.device.cli(["show vsx detail"])

            # Parse using ntc-templates
            vsx_data = self._parse_vsx_textfsm(raw_output)

            logger.debug(f"VSX data parsed: role={vsx_data.get('system_role')}")
            return vsx_data

        except CommandErrorException as e:
            # Device might not support VSX (older models)
            logger.debug(f"VSX command failed (likely not 8300+ series): {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to collect VSX data: {e}")
            return {}

    def _parse_vsx_textfsm(self, raw_output: str) -> Dict[str, Any]:
        """
        Parse 'show vsx detail' output using ntc-templates TextFSM.

        Args:
            raw_output: Raw CLI output string

        Returns:
            Structured dictionary with VSX peer information
        """
        try:
            from ntc_templates.parse import parse_raw_text
        except ImportError:
            logger.error("ntc-templates not installed; VSX parsing unavailable")
            return {}

        try:
            # Parse using ntc-templates
            # Template: aruba_aoscx_show_vsx_detail.textfsm
            # NOTE: Template does NOT exist yet in ntc-templates v2.x
            # Requires PR to upstream ntc-templates repo first
            parsed_list = parse_raw_text(
                raw_output, platform="aruba_aoscx", command="show vsx detail"
            )

            if not parsed_list:
                logger.debug("VSX output parsed empty (not a VSX device)")
                return {}

            vsx_entry = parsed_list[0] if parsed_list else {}

            # Normalize structure
            result = {
                "system_role": vsx_entry.get("system_role"),
                "peer_ip": vsx_entry.get("peer_ip"),
                "isl_status": vsx_entry.get("isl_status"),
                "isl_port": vsx_entry.get("isl_port"),
                "local_mac": vsx_entry.get("local_mac"),
                "peer_mac": vsx_entry.get("peer_mac"),
                "sync_status": vsx_entry.get("sync_status"),
            }

            logger.debug(f"VSX textfsm parsed: system_role={result.get('system_role')}")
            return result

        except Exception as e:
            # Expected until VSX template is added to ntc-templates
            logger.debug(
                f"VSX TextFSM parsing failed (template may not exist yet): {e}"
            )
            return {}


class ArubaAoscxOnboarding:
    """
    Aruba AOS-CX onboarding logic.

    Creates virtual chassis objects and child devices for VSF/VSX stacks/pairs.
    Executes without active NAPALM connection.
    """

    def __init__(
        self, device: Device, driver_addon_result: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize onboarding handler.

        Args:
            device: Device object created by nautobot-device-onboarding
            driver_addon_result: Result from OnboardingDriverExtensions.ext_result
        """
        self.device = device
        self.driver_addon_result = driver_addon_result or {}
        self.vsf_data = self.driver_addon_result.get("vsf", {})
        self.vsx_data = self.driver_addon_result.get("vsx", {})
        self.logger = logging.getLogger("rq.worker")

    def onboarding(self) -> None:
        """Execute virtual chassis onboarding logic."""
        # Check if device is part of a virtual chassis
        if self._is_vsf_stack():
            self._onboard_vsf_stack()
        elif self._is_vsx_pair():
            self._onboard_vsx_pair()
        else:
            self.logger.debug(f"Device {self.device.name}: No virtual chassis detected")

    def _is_vsf_stack(self) -> bool:
        """
        Check if device is part of a VSF stack.

        VSF stack if topology is not 'standalone' and has members.
        """
        topology = self.vsf_data.get("topology")
        members = self.vsf_data.get("members", [])

        # VSF stack if topology != standalone and we have multiple members
        return (
            topology is not None
            and topology.lower() not in ["none", "standalone", ""]
            and len(members) > 1
        )

    def _is_vsx_pair(self) -> bool:
        """
        Check if device is part of a VSX pair.

        VSX pair if ISL is Up and system_role is set.
        """
        isl_status = self.vsx_data.get("isl_status", "").lower()
        system_role = self.vsx_data.get("system_role")

        return isl_status == "up" and system_role is not None

    def _onboard_vsf_stack(self) -> None:
        """
        Onboard VSF stack: create child devices for non-conductor members.

        The primary device (conductor) is already created by device-onboarding.
        This creates Device objects for additional stack members.
        """
        try:
            members = self.vsf_data.get("members", [])
            conductor_member_id = self.vsf_data.get("conductor_member_id", 1)
            stack_name = self.vsf_data.get("stack_name", self.device.name)

            self.logger.info(
                f"Onboarding VSF stack '{stack_name}': "
                f"{len(members)} members, conductor={conductor_member_id}"
            )

            # Create child device for each non-conductor member
            for member in members:
                member_id = member.get("member_id")

                # Skip conductor (it's the main device)
                if member_id == conductor_member_id:
                    continue

                # Create child device for this member
                self._create_vsf_member_device(member)

        except Exception as e:
            self.logger.error(f"VSF stack onboarding failed: {e}")

    def _create_vsf_member_device(
        self, member_info: Dict[str, Any]
    ) -> Optional[Device]:
        """
        Create Device object for a VSF stack member.

        Args:
            member_info: Member data dict from VSF parser
                - member_id: Stack member number
                - serial_number: Device serial
                - status: Member status (Conductor/Member/Standby/Disabled)
                - mac_address: Member MAC address

        Returns:
            Created Device or None if failed
        """
        try:
            member_id = member_info.get("member_id")
            serial = member_info.get("serial_number")
            status_str = member_info.get("status", "Member").lower()

            if not member_id or not serial:
                self.logger.warning(f"Incomplete member data: id={member_id}, sn={serial}")
                return None

            # Generate member device name: "6100-1" → "6100-2", "6100-3", etc.
            base_name = self.device.name.rsplit("-", 1)[0]
            member_device_name = f"{base_name}-{member_id}"

            # Check if device already exists
            existing = Device.objects.filter(name=member_device_name).exists()
            if existing:
                self.logger.debug(f"VSF member {member_device_name} already exists")
                return Device.objects.get(name=member_device_name)

            # Map VSF status to nautobot status
            if status_str in ["disabled"]:
                nautobot_status_slug = "offline"
            else:
                nautobot_status_slug = "active"

            device_status = Status.objects.get(slug=nautobot_status_slug)

            # Create member device
            child_device = Device.objects.create(
                name=member_device_name,
                device_type=self.device.device_type,
                site=self.device.site,
                device_role=self.device.device_role,
                status=device_status,
                serial=serial,
            )

            # Tag as VSF member
            vsf_tag, _ = Tag.objects.get_or_create(
                name="vsf-member", defaults={"slug": "vsf-member"}
            )
            child_device.tags.add(vsf_tag)

            self.logger.info(
                f"✅ Created VSF member device: {member_device_name} (SN: {serial})"
            )
            return child_device

        except Exception as e:
            self.logger.error(f"Failed to create VSF member device: {e}")
            return None

    def _onboard_vsx_pair(self) -> None:
        """
        Onboard VSX pair: handle 8300+ series pairing.

        VSX pairs typically have both devices already onboarded separately.
        This logic could:
        1. Create peer device if missing
        2. Create DeviceRedundancyGroup
        3. Tag devices as VSX pair

        Current implementation: tagging only (minimal approach)
        """
        try:
            system_role = self.vsx_data.get("system_role")
            peer_ip = self.vsx_data.get("peer_ip")
            isl_status = self.vsx_data.get("isl_status")

            self.logger.info(
                f"Onboarding VSX pair: role={system_role}, peer_ip={peer_ip}, isl={isl_status}"
            )

            # Tag device as VSX member
            vsx_tag, _ = Tag.objects.get_or_create(
                name="vsx-member", defaults={"slug": "vsx-member"}
            )
            self.device.tags.add(vsx_tag)

            # Add role-specific tag
            role_tag, _ = Tag.objects.get_or_create(
                name=f"vsx-{system_role.lower()}",
                defaults={"slug": f"vsx-{system_role.lower()}"},
            )
            self.device.tags.add(role_tag)

            self.logger.info(f"✅ Tagged device for VSX pair: {system_role}")

            # TODO: Future enhancement
            # - Look up peer device by peer_ip or peer_mac
            # - Create DeviceRedundancyGroup if not exists
            # - Associate both devices in redundancy group

        except Exception as e:
            self.logger.error(f"VSX pair onboarding failed: {e}")
