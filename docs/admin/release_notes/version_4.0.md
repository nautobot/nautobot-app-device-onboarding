# v4.0 Release Notes

!!! warning
    Nautobot Device Onboarding v4.0.0 completely revamps the applications design and framework. The original `OnboardingTask` job is still packaged with the app to provide a backwards compatible way for users that have used its extensions framework in the past to solve complex problems. However, that job is now hidden by default to avoid confusion with the two new SSoT based onboarding jobs that v4.0.0 exposes.

## v4.0.0 TBD

### Added

- [#TBD](TBD) - Sync Devices from Network job was added which utilizes the SSoT framework to onboard devices.
- [#TBD](TBD) - Sync Data from Network job was added which utilizes the SSoT framework to onboard devices.
- [#TBD](TBD) - Git Datasource object to be able to use a Git Repo to overload new SSoT job YAML file definitions.
- [#TBD](TBD) - Create a Nornir inventory `EmptyInventory` to support ondemand inventory population for `Sync Devices` job.
- [#TBD](TBD) - Add `nautobot-app-nornir` dependency to reuse `NautobotORMInventory` to support inventory creation for `Sync Data` job.

### Changed

- [#TBD](tbd) - The `OnboardingTask` job is changed to `hidden` by default.
