# v4.0 Release Notes

!!! warning
    Nautobot Device Onboarding v4.0.0 completely revamps the applications design and framework. The original `OnboardingTask` job is still packaged with the app to provide a backwards compatible way for users that have used its extensions framework in the past to solve complex problems. However, that job is now hidden by default to avoid confusion with the two new SSoT based onboarding jobs that v4.0.0 exposes.

## [v4.0.1 (2024-08-27)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.0.1)

### Fixed

- [#218](https://github.com/nautobot/nautobot-app-device-onboarding/pull/218) - Fixed Emoji shorthand to be unicode instead.

### Dependencies

- [#224](https://github.com/nautobot/nautobot-app-device-onboarding/pull/224) - Removed secrets provider dependency.

### Housekeeping

- [#216](https://github.com/nautobot/nautobot-app-device-onboarding/pull/216) - Rebaked Cookie.

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
