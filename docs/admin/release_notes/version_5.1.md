# v5.1 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Support for additional device platforms has been added, including Brocade/Ruckus FastIron, HP Procurve, ArubaCX, ArubaOS, and F5 TMSH.
- Fixed several bugs related to database connections, device synchronization, and interface management.

<!-- towncrier release notes start -->

## [v5.1.0 (2026-01-21)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.1.0)

### Added

- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for Brocade/Ruckus fastiron.
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for HP Procurve.
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds network data sync support for ArubaCX.
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for ArubaOS.
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds network data sync for F5 tmsh.

### Fixed

- [#366](https://github.com/nautobot/nautobot-app-device-onboarding/issues/366) - Fixed Sync Devices and Sync Network Data jobs not releasing DB connections.
- [#428](https://github.com/nautobot/nautobot-app-device-onboarding/issues/428) - In the sync network data job, added handling of Devices who's Primary IP is not set.
- [#455](https://github.com/nautobot/nautobot-app-device-onboarding/issues/455) - Fixed migration bug where OnboardingTask was not filtered correctly.
- [#476](https://github.com/nautobot/nautobot-app-device-onboarding/issues/476) - Fixed interfaces attached to modules being recreated when running the Sync Network Data job.

### Documentation

- [#437](https://github.com/nautobot/nautobot-app-device-onboarding/issues/437) - Updated documentation on the readme for capitalization.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v3.0.0`.
