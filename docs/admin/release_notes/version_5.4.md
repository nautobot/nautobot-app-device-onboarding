# v5.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v5.4.0 (2026-07-01)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.4.0)

### Added

- [#244](https://github.com/nautobot/nautobot-app-device-onboarding/issues/244) - Added support for onboarding switch stacks as Virtual Chassis objects in the Sync Devices From Network job for Cisco IOS and Cisco IOS-XE platforms.
- [#244](https://github.com/nautobot/nautobot-app-device-onboarding/issues/244) - Added Virtual Chassis master identification via serial number matching, correctly handling stacks where the conductor is not switch 1.
- [#244](https://github.com/nautobot/nautobot-app-device-onboarding/issues/244) - Added handling of provisioned-but-absent stack slots so single-member stacks with empty provisioned slots are onboarded as standalone devices.
- [#568](https://github.com/nautobot/nautobot-app-device-onboarding/issues/568) - Added optional `Sync VRF to Prefix` toggle on the Sync Network Data From Network job that additively associates each interface's VRF with the parent prefix of the interface's IP addresses.

### Changed

- [#244](https://github.com/nautobot/nautobot-app-device-onboarding/issues/244) - Changed the Sync Devices From Network and Sync Network Data From Network jobs to require both hostname and serial to match an existing Nautobot Device by default; devices with a drifted serial are now skipped with a warning rather than having their serial silently rewritten. The new `Update Devices With Changed Serial` toggle (default OFF) restores hostname-only matching within the job's filter scope, required for Virtual Chassis where the chassis-level serial changes when the stack master role moves between members.

### Fixed

- [#555](https://github.com/nautobot/nautobot-app-device-onboarding/issues/555) - Fixed erroneous Manufacturer (Paloalto) created, and Duplicate DeviceType exception when the same model exists under multiple manufacturers.
- [#557](https://github.com/nautobot/nautobot-app-device-onboarding/issues/557) - Fixed `get_vlan_data` Jinja filter raising an error when trunking VLANs were reported as `NONE` by the device, so trunk interfaces with no tagged VLANs are now handled correctly.
- [#561](https://github.com/nautobot/nautobot-app-device-onboarding/issues/561) - Fix silently dropped per-host failure messages in sync jobs.
- [#563](https://github.com/nautobot/nautobot-app-device-onboarding/issues/563) - Fixed Sync Network Data From Network failing with `Found multiple instances for ip_address` when the same IP host existed in multiple Nautobot namespaces.
- [#565](https://github.com/nautobot/nautobot-app-device-onboarding/issues/565) - Fixed VRF assignment lookup for VLAN SVI interfaces on Cisco IOS-XE devices in the Sync Network Data From Network job.
- [#572](https://github.com/nautobot/nautobot-app-device-onboarding/issues/572) - Fix Junos IPv6 Loopback network mask discovery.
- [#572](https://github.com/nautobot/nautobot-app-device-onboarding/issues/572) - Fix Junos management Interface and IP address discovery when additional sub-string IP exists on device.
- [#581](https://github.com/nautobot/nautobot-app-device-onboarding/issues/581) - Fix Sync Device Job to raise if platform auto-discovery fails and fail_job_on_task_failure is set to True.

### Documentation

- [#559](https://github.com/nautobot/nautobot-app-device-onboarding/issues/559) - Add Palo Alto to support matrix for sync network data jobs.
