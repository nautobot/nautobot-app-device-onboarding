# v4.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Fixed VLANs creation on cisco_nxos devices.
- Fixed nxos lag member assigment.

<!-- towncrier release notes start -->

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
