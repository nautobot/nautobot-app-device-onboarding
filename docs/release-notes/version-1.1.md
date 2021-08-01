# nautobot-device-onboarding plugin v1.1

This document describes all new features and changes in nautobot-device-onboarding plugin 1.1


## Release Overview

### Added

#### Documentation updates ([#??](https://github.com/...))

nautobot-device-onboarding now covers onboarding of Cisco Nexus and Arista EOS devices. Documentation was reviewed and updated.

#### Assign default custom fields values to new objects ([#13](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/13))

While new objects are created during onboarding a device, they will inherit model's default custom fields.

### Changed

#### Support for Nautobot 1.1.0 (Celery) ([#18](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/18))

Celery has been introduced to eventually replace RQ for executing background tasks within Nautobot. Plugin's usage of RQ has been migrated to use Celery. 

## v1.1.0 (2021-08-??)

### Added

- [#??](https://github.com/...) - Documentation updates 
- [#13](https://github.com/nautobot/nautobot-plugin-device-onboarding/pull/13) - Assign default custom fields values to new objects

### Changed

### Fixed

- [#14](https://github.com/nautobot/nautobot-plugin-device-onboarding/issues/14) - Error 'ipv4' when onboarding Juniper device
