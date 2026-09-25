# v5.6 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v5.6.0 (2026-09-25)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.6.0)

### Added

- [#584](https://github.com/nautobot/nautobot-app-device-onboarding/issues/584) - Added Sync Network Data support for Palo Alto PAN-OS in the `paloalto_panos.yml` command mapper, covering interfaces (name, type, IP addresses, MAC, MTU, description, link status, 802.1Q mode, LAG membership, tagged/untagged VLANs, VRF membership), software version, and serial number.
- Added Virtual Chassis support for Aruba AOS-CX devices in the Sync Devices From Network job, via `show vsf detail` (VSF stacks).
- Added module-based device_type detection for Aruba AOS-CX devices in the Sync Devices From Network job, via `show module`.

### Fixed

- [#579](https://github.com/nautobot/nautobot-app-device-onboarding/issues/579) - Fixed Sync Network Data wiping the OOBM management interface IP attachment and clearing `primary_ip4` on Aruba AOS-CX devices whose primary IP lives on the dedicated `mgmt` port. The mapper now reads `show interface mgmt` and reconciles the OOBM port as a virtual interface with its IP attachment preserved across syncs.
- [#625](https://github.com/nautobot/nautobot-app-device-onboarding/issues/625) - Fixed Aruba AOS-CX VLAN SVI interfaces being classified as "1000base-t" instead of "virtual" during Sync Network Data From Network.
- [#639](https://github.com/nautobot/nautobot-app-device-onboarding/issues/639) - Fixed a file descriptor leak during large jobs by calling the base Nornir processor from `CommandGetterProcessor.task_instance_completed` and `TroubleshootingProcessor.task_instance_completed`, so that exception frames are released and descriptors held by driver reference cycles are reclaimed while the job is still running.

### Dependencies

- [#639](https://github.com/nautobot/nautobot-app-device-onboarding/issues/639) - Changed the minimum version of nautobot-plugin-nornir to 3.2.5.
