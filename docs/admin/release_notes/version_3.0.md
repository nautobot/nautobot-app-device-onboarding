# v3.0 Release Notes

!!! warning
    Nautobot Device Onboarding v2.0.0-2.0.2 contains a vulnerability where the credentials used to log into a device may be visible in clear text on the Job Results page under the Additional Data tab. It is recommended to review all OnbaordingTasks from the affected releases, delete any affeccted JobResults, and upgrade to v3.0.0. For more information please see the full write up on the issue which is available as [a security advisory](https://github.com/nautobot/nautobot-plugin-device-onboarding/security/advisories/GHSA-qf3c-rw9f-jh7v) on the repo. Nautobot Device Onboarding app versions v2.0.0-2.0.2 have been removed for PyPI to ensure all gaps are closed. v2.0.3 is published with disabled functionality and banner message encouraging to upgrade to v3.0.0. [CVE-2023-48700](https://www.cve.org/CVERecord?id=CVE-2023-48700) has been issued for this vulnerability.

## Release Overview

## v3.0.1 2023-11-24

### Fixed

- [#128](https://github.com/nautobot/nautobot-plugin-device-onboarding/issues/128) - Failures when onboarding via IP Address

## v3.0.0 2023-11-21

### Changed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Device onboarding is now provided via a Nautobot Job.
- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - CSV import has changed to a comma separated list of IPs/FQDNs as a job input

### Fixed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Leaking of device credentials if username & password were provided on creation of an instance of the `OnboardingTask` object.

### Removed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Removed all models, UI Views, and API Views from app
- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - All data for instances of `OnboardingTask` & `OnboardingDevice` will be removed on upgrade, affected `JobResults` from tasks created while on affected versions should be reviewed & deleted.
