
# v4.1 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Added Python 3.12 Support
- Updated SSoT support to 3.0
- Added support for HP Comware for sync_devices job
- Added ability to use the FQDN of the device instead of the IP
- Fixed some other small issues

## [v4.1.0 (2024-10-18)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.1.0)

### Added

- [#231](https://github.com/nautobot/nautobot-app-device-onboarding/issues/231) - Added Python 3.12 support.
- [#249](https://github.com/nautobot/nautobot-app-device-onboarding/issues/249) - Added raw parser choice to skip jpath extraction.
- [#249](https://github.com/nautobot/nautobot-app-device-onboarding/issues/249) - Added initial hp_comware support for sync_devices job.

### Fixed

- [#192](https://github.com/nautobot/nautobot-app-device-onboarding/issues/192) - Fixes lack of logging of certain termination based failures.
- [#217](https://github.com/nautobot/nautobot-app-device-onboarding/issues/217) - Removed secrets-provider app dependency.
- [#217](https://github.com/nautobot/nautobot-app-device-onboarding/issues/217) - Removed python-tss-sdk dependency.
- [#218](https://github.com/nautobot/nautobot-app-device-onboarding/issues/218) - Replaced all instances of emoji shortcodes with the unicode characters so they render correctly in docs.
- [#238](https://github.com/nautobot/nautobot-app-device-onboarding/issues/238) - Added a fix for mtu as an integer rather than a string.
- [#241](https://github.com/nautobot/nautobot-app-device-onboarding/issues/241) - Fixed Multiple RE support to Juniper parsing logic.
- [#261](https://github.com/nautobot/nautobot-app-device-onboarding/issues/261) - Add general exception handling when loading interfaces into a DiffSync model. 

### Dependencies

- [#235](https://github.com/nautobot/nautobot-app-device-onboarding/issues/235) - Updated Nautobot App SSoT to v3.0.0.
- [#235](https://github.com/nautobot/nautobot-app-device-onboarding/issues/235) - Pinned griffe to v1.1.1.

### Housekeeping

- [#0](https://github.com/nautobot/nautobot-app-device-onboarding/issues/0) - Rebaked from the cookie `nautobot-app-v2.4.0`.
- [#216](https://github.com/nautobot/nautobot-app-device-onboarding/issues/216) - Rebake using 2.3 Nautobot-App-Cookiecutter.
- [#231](https://github.com/nautobot/nautobot-app-device-onboarding/issues/231) - Rebaked from the cookie `nautobot-app-v2.3.2`.
