
# v4.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Fixed VLANs creation on cisco_nxos devices.
- Fixed nxos lag member assigment.

## [v4.4.0 (2025-10-24)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.4.0)

### Fixed

- [#392](https://github.com/nautobot/nautobot-app-device-onboarding/issues/392) - Fixed a bug when creating VLANs for trunks on cisco_nxos devices.
- [#433](https://github.com/nautobot/nautobot-app-device-onboarding/issues/433) - In the sync network data job, fix nxos lag member assignment.
