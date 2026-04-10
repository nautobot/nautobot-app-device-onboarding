# v5.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Added support for assigning tenants to devices.

<!-- towncrier release notes start -->

## [v5.2.3 (2026-04-10)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.3)

### Fixed

- [#425](https://github.com/nautobot/nautobot-app-device-onboarding/issues/425) - Fixed check connectivity failing on Sync Network Data job.
- [#523](https://github.com/nautobot/nautobot-app-device-onboarding/issues/523) - Fixed invalid IP Address returned for Arista EOS virtual interface addresses.

### Housekeeping

- [#527](https://github.com/nautobot/nautobot-app-device-onboarding/issues/527) - Added @cdtomkins to CODEOWNERS.
- Rebaked from the cookie `nautobot-app-v3.1.3`.

## [v5.2.2 (2026-03-18)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.2)

### Fixed

- [#509](https://github.com/nautobot/nautobot-app-device-onboarding/issues/509) - Fixed VLAN sync failing with duplicate child location name.
- [#513](https://github.com/nautobot/nautobot-app-device-onboarding/issues/513) - Fixed HP ProCurve not onboarding if using OOBM interface.
- [#515](https://github.com/nautobot/nautobot-app-device-onboarding/issues/515) - Updated ntc-templates dependency.
- [#517](https://github.com/nautobot/nautobot-app-device-onboarding/issues/517) - Added “fail job on task failure” so the job fails when one or more tasks fail.
- [#519](https://github.com/nautobot/nautobot-app-device-onboarding/issues/519) - Fixed AOS-CX not onboarding if using OOBM interface.

### Documentation

- [#472](https://github.com/nautobot/nautobot-app-device-onboarding/issues/472) - Updated Device onboarding documentation to include 3.0 screenshots.

## [v5.2.1 (2026-01-29)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.1)

### Fixed

- [#500](https://github.com/nautobot/nautobot-app-device-onboarding/issues/500) - Fixed dryrun variable being set to True incorrectly.

## [v5.2.0 (2026-01-27)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.0)

### Added

- [#484](https://github.com/nautobot/nautobot-app-device-onboarding/issues/484) - Added support for assigning a tenant to devices created by the SSOTSyncDevices job.

### Fixed

- [#477](https://github.com/nautobot/nautobot-app-device-onboarding/issues/477) - Fixed VRFs not syncing on Cisco XE interfaces that are down.
- [#493](https://github.com/nautobot/nautobot-app-device-onboarding/issues/493) - Fixed unexpected keyword argument 'parallel_loading' with `nautobot-ssot` 4.1.x.
