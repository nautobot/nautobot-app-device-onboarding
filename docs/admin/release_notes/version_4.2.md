
# v4.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- [#200](https://github.com/nautobot/nautobot-app-device-onboarding/issues/200) - Added basic connectivity checker using Netutils tcp_ping method.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added TTP Parser support.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added Sync Device from Network support for Palo Alto Panos.
- [#340](https://github.com/nautobot/nautobot-app-device-onboarding/issues/340) - Add Aruba AOSCX support for Sync Devices from Network Job.
- [#278](https://github.com/nautobot/nautobot-app-device-onboarding/issues/278) - Optimized VLAN loading into diffsync from Nautbot
- [#278](https://github.com/nautobot/nautobot-app-device-onboarding/issues/278) - Improved error handling when creating VLANs
- [#233](https://github.com/nautobot/nautobot-app-device-onboarding/issues/233) - Added support syncing in software versions from devices to nautobot core models.
- [#334](https://github.com/nautobot/nautobot-app-device-onboarding/issues/334) - Add initial F5 Support for Network Device Sync
- [#357](https://github.com/nautobot/nautobot-app-device-onboarding/issues/357) - Added improved error messaging for device object `get()` call in the `update()` method of `SyncDevicesDevice`
- [#372](https://github.com/nautobot/nautobot-app-device-onboarding/issues/372) - Fixed bug when loading Nautobot Vlans with multiple locations assigned. Only Vlans with 1 location will be considered for the sync.

## [v4.2.6 (2025-07-25)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.6a0)

### Fixed

- [#385](https://github.com/nautobot/nautobot-app-device-onboarding/issues/385) - Fixed bug causing exessive logging noise
- [#386](https://github.com/nautobot/nautobot-app-device-onboarding/issues/386) - Add 10GEChannel to INTERFACE_TYPE_MAP_STATIC so that port-channel interfaces with this hardware type are recognized as type LAG.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v2.5.0`.

## [v4.2.5 (2025-05-13)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.5)

### Added

- [#233](https://github.com/nautobot/nautobot-app-device-onboarding/issues/233) - Added support syncing in software versions from devices to nautobot core models.
- [#334](https://github.com/nautobot/nautobot-app-device-onboarding/issues/334) - Add initial F5 Support for Network Device Sync
- [#357](https://github.com/nautobot/nautobot-app-device-onboarding/issues/357) - Added improved error messaging for device object `get()` call in the `update()` method of `SyncDevicesDevice`

### Fixed

- [#372](https://github.com/nautobot/nautobot-app-device-onboarding/issues/372) - Fixed bug when loading Nautobot Vlans with multiple locations assigned. Only Vlans with 1 location will be considered for the sync.

### Dependencies

- [#367](https://github.com/nautobot/nautobot-app-device-onboarding/issues/367) - Updated jdiff dependency pin.

### Documentation

- [#358](https://github.com/nautobot/nautobot-app-device-onboarding/issues/358) - Updated documentation on the README for VRF.


## [v4.2.4 (2025-04-08)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.4)

### Added

- [#326](https://github.com/nautobot/nautobot-app-device-onboarding/issues/326) - Added testing for cable termination type when adding cables to diffsync store.
- [#340](https://github.com/nautobot/nautobot-app-device-onboarding/issues/340) - Add Aruba AOSCX support for Sync Devices from Network Job.

### Changed

- [#278](https://github.com/nautobot/nautobot-app-device-onboarding/issues/278) - Optimized VLAN loading into diffsync from Nautbot
- [#278](https://github.com/nautobot/nautobot-app-device-onboarding/issues/278) - Improved error handling when creating VLANs

### Fixed

- [#326](https://github.com/nautobot/nautobot-app-device-onboarding/issues/326) - Fixed incorrect call to cable termination type.
- [#337](https://github.com/nautobot/nautobot-app-device-onboarding/issues/337) - Fixed logging call from an invalid path to the correct one.
- [#346](https://github.com/nautobot/nautobot-app-device-onboarding/issues/346) - Fixed Juniper IP addresses not syncing secondary IP addresses.

### Housekeeping

- [#341](https://github.com/nautobot/nautobot-app-device-onboarding/issues/341) - Add MySQL testing back to the CI configuration.

## [v4.2.3 (2025-03-11)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.3)

### Fixed

- [#326](https://github.com/nautobot/nautobot-app-device-onboarding/issues/326) - Fixed error from ingesting existing cable attached to a circuit.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v2.4.2`.


## [v4.2.2 (2025-02-19)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.2)

### Fixed

- [#320](https://github.com/nautobot/nautobot-app-device-onboarding/issues/320) - Fixed app startup crashing Nautobot during startup in some cases.

## [v4.2.1 (2025-02-11)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.1)

### Fixed

- [#306](https://github.com/nautobot/nautobot-app-device-onboarding/issues/306) - Fixed error with logging message in SyncNetworkDataIPAddress.update()
- [#311](https://github.com/nautobot/nautobot-app-device-onboarding/issues/311) - Fixed issue with Lags, VRFs and Untagged Vlans not being removed from interfaces
- [#313](https://github.com/nautobot/nautobot-app-device-onboarding/issues/313) - Fixed issue running a sync job via CSV would raise an exception.

### Dependencies

- [#307](https://github.com/nautobot/nautobot-app-device-onboarding/issues/307) - Updated ntc-templates to 7.x

### Housekeeping

- [#315](https://github.com/nautobot/nautobot-app-device-onboarding/issues/315) - Added fake SSH devices to tests to increase coverage.


## [v4.2.0 (2025-01-17)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.0)

### Added

- [#200](https://github.com/nautobot/nautobot-app-device-onboarding/issues/200) - Added basic connectivity checker using Netutils tcp_ping method.
- [#241](https://github.com/nautobot/nautobot-app-device-onboarding/issues/241) - Added FQDN support to the sync network device job.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added TTP Parser support.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added ability to load TTP templates from Git Repository.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added TTP template precedence loading from Git Repository.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added Sync Device from Network support for Palo Alto Panos.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added a ability to use nautobot-app-nornir connection option extras in Sync Devices job.
- [#282](https://github.com/nautobot/nautobot-app-device-onboarding/issues/282) - Added support for trying a textfsm directory from the git repo for initial template parsing.
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - Added additional error handling/logging to the git repository sync method

### Changed

- [#243](https://github.com/nautobot/nautobot-app-device-onboarding/issues/243) - Sync Devices From Network job form now highlights required fields.

### Fixed

- [#255](https://github.com/nautobot/nautobot-app-device-onboarding/issues/255) - Fixed Timeout and Authenticaiton failure detection to base netmiko_send_commands task.
- [#257](https://github.com/nautobot/nautobot-app-device-onboarding/issues/257) - Fixed Docs typo in nautobot-server command.
- [#272](https://github.com/nautobot/nautobot-app-device-onboarding/issues/272) - Fixed incorrect default on SSoT based jobs for has_sensitive_data Meta field. Now defaults to false.
- [#277](https://github.com/nautobot/nautobot-app-device-onboarding/issues/277) - Fixed multiple git repo provides not working, change filter logic to contains from exact.
- [#279](https://github.com/nautobot/nautobot-app-device-onboarding/issues/279) - Fix incorrect "no platform set" error which was catching all errors.
- [#279](https://github.com/nautobot/nautobot-app-device-onboarding/issues/279) - Properly skip command extraction when command_getter fails.
- [#283](https://github.com/nautobot/nautobot-app-device-onboarding/issues/283) - Fixed adding invalid VLAN 0 to Diffsync Store causing Sync Data job to fail.
- [#287](https://github.com/nautobot/nautobot-app-device-onboarding/issues/287) - Fix conditional logic to only show job log entries when git repo is used.
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - Fixed typos in the 3.0 changelog
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - Fixed a logging typo in an adapter
- [#293](https://github.com/nautobot/nautobot-app-device-onboarding/issues/293) - Makes fixes to platform detection so that netmiko ssh pubkey auth settings are applied.
- [#301](https://github.com/nautobot/nautobot-app-device-onboarding/issues/301) - Fixed missing job argument for the troubleshooting job.

### Housekeeping

- [#1](https://github.com/nautobot/nautobot-app-device-onboarding/issues/1) - Rebaked from the cookie `nautobot-app-v2.4.1`.
- [#189](https://github.com/nautobot/nautobot-app-device-onboarding/issues/189) - Added documentation on using ssh public key authentication.
- [#189](https://github.com/nautobot/nautobot-app-device-onboarding/issues/189) - Added documentation on using ssh proxy via jumphost.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Fixed typos in function names, comments, and errors.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Updated documentation to include an example CSV for bulk onboarding.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Updated documentation to make yaml override placement and git repository more clear.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Added a homepage to the app config.
- [#286](https://github.com/nautobot/nautobot-app-device-onboarding/issues/286) - Fixed typos on app overview file
