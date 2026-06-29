# v4.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Fixed VLANs creation on cisco_nxos devices.
- Fixed nxos lag member assigment.

<!-- towncrier release notes start -->


## [v4.4.6 (2026-06-29)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.6)

### Fixed

- [#572](https://github.com/nautobot/nautobot-app-device-onboarding/issues/572) - Fix Junos IPv6 Loopback network mask discovery.
- [#572](https://github.com/nautobot/nautobot-app-device-onboarding/issues/572) - Fix Junos management Interface and IP address discovery when additional sub-string IP exists on device.
- [#581](https://github.com/nautobot/nautobot-app-device-onboarding/issues/581) - Fix Sync Device Job to raise if platform auto-discovery fails and fail_job_on_task_failure is set to True.

### Dependencies

- [#590](https://github.com/nautobot/nautobot-app-device-onboarding/issues/590) - Bumped minimum version of ntc-templates to 9.0.0.

## [v4.4.5 (2026-05-06)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.5)

### Fixed

- [#425](https://github.com/nautobot/nautobot-app-device-onboarding/issues/425) - Fixed check connectivity failing on Sync Network Data job.
- [#557](https://github.com/nautobot/nautobot-app-device-onboarding/issues/557) - Fixed `get_vlan_data` Jinja filter raising an error when trunking VLANs were reported as `NONE` by the device, so trunk interfaces with no tagged VLANs are now handled correctly.

## [v4.4.4 (2026-03-23)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.4)

### Fixed

- [#409](https://github.com/nautobot/nautobot-app-device-onboarding/issues/409) - Fixed debug logging not adhering to the debug job input boolean.
- [#517](https://github.com/nautobot/nautobot-app-device-onboarding/issues/517) - Added "fail job on task failure" so the job fails when one or more tasks fail.

## [v4.4.3 (2026-01-27)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.3)

### Fixed

- [#477](https://github.com/nautobot/nautobot-app-device-onboarding/issues/477) - Fixed VRFs not syncing on Cisco XE interfaces that are down.

### Added

- [#484](https://github.com/nautobot/nautobot-app-device-onboarding/issues/484) - Added support for assigning a tenant to devices created by the SSOTSyncDevices job.

## [v4.4.2 (2026-01-21)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.2)

### Fixed

- [#366](https://github.com/nautobot/nautobot-app-device-onboarding/issues/366) - Fixed Sync Devices and Sync Network Data jobs not releasing DB connections.
- [#483](https://github.com/nautobot/nautobot-app-device-onboarding/issues/483) - Fixed interfaces attached to modules being recreated when running the Sync Network Data job.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v2.7.2`.

## [v4.4.1 (2025-12-09)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.1)

### Fixed

- [#458](https://github.com/nautobot/nautobot-app-device-onboarding/issues/458) - Fixed migration bug where OnboardingTask was not filtered correctly.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v2.7.0`.
- Rebaked from the cookie `nautobot-app-v2.7.1`.

## [v4.4.0 (2025-10-27)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.0)

### Fixed

- [#392](https://github.com/nautobot/nautobot-app-device-onboarding/issues/392) - Fixed a bug when creating VLANs for trunks on cisco_nxos devices.
- [#433](https://github.com/nautobot/nautobot-app-device-onboarding/issues/433) - In the sync network data job, fix nxos lag member assignment.
