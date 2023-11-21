# v3.0 Release Notes

!!! warning
    Nautobot Device Onboarding v2.0.0-2.0.3 introduced a vulnerability where the credentials used to log into a device will be visible in clear text on the Job Results page under the Additional Data tab. This only affect v2 releases of the app and only if the credentials were passed in on creation of an OnboardingTask object. A full write up on the issue is available as a security advisory located [here](https://github.com/nautobot/nautobot-plugin-device-onboarding/security/advisories/GHSA-qf3c-rw9f-jh7v) on the repo. On publish of v3.0.0 of the Nautobot Device Onboarding app all v2 releases will be removed for PyPI to ensure all gaps are closed.

## Release Overview

## v3.0.0 2023-11

### Changed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Device onboarding is now provided via a Nautobot Job.
- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - CSV import has changed to a comma separated list of IPs/FQDNs as a job input

### Fixed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Leaking of device credentials if username & password were provided on creation of an instance of the `OnboardingTask` object.

### Removed

- [#124](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/124) - Removed all models, UI Views, and API Views from app
