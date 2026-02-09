# v5.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Added support for assigning tenants to devices.

<!-- towncrier release notes start -->


## [v5.2.1 (2026-01-29)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.1)

### Fixed

- [#500](https://github.com/nautobot/nautobot-app-device-onboarding/issues/500) - Fixed dryrun variable being set to True incorrectly.

## [v5.2.0 (2026-01-27)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.2.0)

### Added

- [#484](https://github.com/nautobot/nautobot-app-device-onboarding/issues/484) - Added support for assigning a tenant to devices created by the SSOTSyncDevices job.

### Fixed

- [#477](https://github.com/nautobot/nautobot-app-device-onboarding/issues/477) - Fixed VRFs not syncing on Cisco XE interfaces that are down.
- [#493](https://github.com/nautobot/nautobot-app-device-onboarding/issues/493) - Fixed unexpected keyword argument 'parallel_loading' with `nautobot-ssot` 4.1.x.
