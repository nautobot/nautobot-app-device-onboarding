# v5.3 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v5.3.0 (2026-04-13)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.3.0)

### Added

- [#329](https://github.com/nautobot/nautobot-app-device-onboarding/issues/329) - Updated Sync Devices from Network job to automatically update location type content types if required

### Fixed

- [#425](https://github.com/nautobot/nautobot-app-device-onboarding/issues/425) - Fixed check connectivity failing on Sync Network Data job.
- [#523](https://github.com/nautobot/nautobot-app-device-onboarding/issues/523) - Fixed invalid IP Address returned for Arista EOS virtual interface addresses.

### Dependencies

- [#546](https://github.com/nautobot/nautobot-app-device-onboarding/issues/546) - Bumped minimum version of ntc-templates to 9.0.0.
- [#549](https://github.com/nautobot/nautobot-app-device-onboarding/issues/549) - Bumped minimum version of nautobot-plugin-nornir to 3.2.0.

### Housekeeping

- [#527](https://github.com/nautobot/nautobot-app-device-onboarding/issues/527) - Added @cdtomkins to CODEOWNERS.
- Rebaked from the cookie `nautobot-app-v3.1.3`.
