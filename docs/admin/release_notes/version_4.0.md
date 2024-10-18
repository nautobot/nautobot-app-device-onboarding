# v4.0 Release Notes

!!! warning
    Nautobot Device Onboarding v4.0.0 completely revamps the applications design and framework. The original `OnboardingTask` job is still packaged with the app to provide a backwards compatible way for users that have used its extensions framework in the past to solve complex problems. However, that job is now hidden by default to avoid confusion with the two new SSoT based onboarding jobs that v4.0.0 exposes.

## Release Overview

- Added Python 3.12 Support
- Updated SSoT support to 3.0
- Added support for HP Comware for sync_devices job
- Added ability to use the FQDN of the device instead of the IP
- Fixed some other small issues

## [v4.0.2 (2024-10-18)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.0.2)

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

### Dependencies

- [#235](https://github.com/nautobot/nautobot-app-device-onboarding/issues/235) - Updated Nautobot App SSoT to v3.0.0.
- [#235](https://github.com/nautobot/nautobot-app-device-onboarding/issues/235) - Pinned griffe to v1.1.1.

### Housekeeping

- [#0](https://github.com/nautobot/nautobot-app-device-onboarding/issues/0) - Rebaked from the cookie `nautobot-app-v2.4.0`.
- [#216](https://github.com/nautobot/nautobot-app-device-onboarding/issues/216) - Rebake using 2.3 Nautobot-App-Cookiecutter.
- [#231](https://github.com/nautobot/nautobot-app-device-onboarding/issues/231) - Rebaked from the cookie `nautobot-app-v2.3.2`.

## [v4.0.0 (2024-08-05)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.0.0)

### Added

- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - Sync Devices from Network job was added which utilizes the SSoT framework to onboard devices.
- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - Sync Data from Network job was added which utilizes the SSoT framework to onboard devices.
- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - Git Datasource object to be able to use a Git Repo to overload new SSoT job YAML file definitions.
- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - Create a Nornir inventory `EmptyInventory` to support ondemand inventory population for `Sync Devices` job.
- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - Add `nautobot-app-nornir` dependency to reuse `NautobotORMInventory` to support inventory creation for `Sync Data` job.
- [#201](https://github.com/nautobot/nautobot-app-device-onboarding/issues/201) - - Add ability to sync in cables for cisco ios,nxos and Juniper via neighbor discovery protocol commands.

### Changed

- [#151](https://github.com/nautobot/nautobot-app-device-onboarding/issues/151) - Replaced pydocstyle with ruff.
- [#181](https://github.com/nautobot/nautobot-app-device-onboarding/issues/181) - The `OnboardingTask` job is changed to `hidden` by default.

### Housekeeping

- [#167](https://github.com/nautobot/nautobot-app-device-onboarding/issues/167) - Re-baked from the template `nautobot-app-v2.2.1`.
- [#194](https://github.com/nautobot/nautobot-app-device-onboarding/issues/194) - - Add @housebpass to Codeowners
- [#194](https://github.com/nautobot/nautobot-app-device-onboarding/issues/194) - - Add ntc-templates to new issue template
- [#203](https://github.com/nautobot/nautobot-app-device-onboarding/issues/203) - - Add compatibility matrix for what platforms support which data fields to sync.
