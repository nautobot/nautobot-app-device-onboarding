# v5.5 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Increased the minimum version of Nautobot to 3.1.0.
- Added support for Cable sync in Nautobot 3.2.0 and higher.

<!-- towncrier release notes start -->

## [v5.5.1 (2026-08-31)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.5.1)

### Fixed

- [#609](https://github.com/nautobot/nautobot-app-device-onboarding/issues/609) - Fixed the Sync Devices and Sync Network Data jobs to ensure Git-provided command mappers are synced before running.

### Housekeeping

- Updated CODEOWNERS file.

## [v5.5.0 (2026-08-17)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.5.0)

### Fixed

- [#277](https://github.com/nautobot/nautobot-app-device-onboarding/issues/277) - Refactors get_git_repo to use .get() for better error handling.
- [#604](https://github.com/nautobot/nautobot-app-device-onboarding/issues/604) - Fixed cable sync failing in Nautobot v3.2.0 and higher.

### Dependencies

- [#605](https://github.com/nautobot/nautobot-app-device-onboarding/issues/605) - Bumped ttp minimum to 0.10.0 for compatibility with nornir-nautobot 4.4.0 and Python 3.14.

### Housekeeping

- [#604](https://github.com/nautobot/nautobot-app-device-onboarding/issues/604) - Fixed unit test failing in Nautobot v3.1.7 and higher.
- Rebaked from the cookie `nautobot-app-v3.1.4`.
