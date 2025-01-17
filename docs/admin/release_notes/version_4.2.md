
# v4.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v4.2.0 (2025-01-17)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.2.0)

### Added

- [#200](https://github.com/nautobot/nautobot-app-device-onboarding/issues/200) - - Added basic connectivity checker using Netutils tcp_ping method.
- [#241](https://github.com/nautobot/nautobot-app-device-onboarding/issues/241) - Added FQDN support to the sync network device job.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added TTP Parser support.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added ability to load TTP templates from Git Repository.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added TTP template precedence loading from Git Repository.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added Sync Device from Network support for Palo Alto Panos.
- [#274](https://github.com/nautobot/nautobot-app-device-onboarding/issues/274) - Added a ability to use nautobot-app-nornir connection option extras in Sync Devices job.
- [#282](https://github.com/nautobot/nautobot-app-device-onboarding/issues/282) - - Added support for trying a textfsm directory from the git repo for initial template parsing.
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - - Added additional error handling/logging to the git repository sync method

### Changed

- [#243](https://github.com/nautobot/nautobot-app-device-onboarding/issues/243) - Sync Devices From Network job form now highlights required fields.

### Fixed

- [#255](https://github.com/nautobot/nautobot-app-device-onboarding/issues/255) - - Fixed Timeout and Authenticaiton failure detection to base netmiko_send_commands task.
- [#257](https://github.com/nautobot/nautobot-app-device-onboarding/issues/257) - Fixed Docs typo in nautobot-server command.
- [#272](https://github.com/nautobot/nautobot-app-device-onboarding/issues/272) - - Fixed incorrect default on SSoT based jobs for has_sensitive_data Meta field. Now defaults to false.
- [#277](https://github.com/nautobot/nautobot-app-device-onboarding/issues/277) - - Fixed multiple git repo provides not working, change filter logic to contains from exact.
- [#279](https://github.com/nautobot/nautobot-app-device-onboarding/issues/279) - - Fix incorrect "no platform set" error which was catching all errors.
- [#279](https://github.com/nautobot/nautobot-app-device-onboarding/issues/279) - - Properly skip command extraction when command_getter fails.
- [#283](https://github.com/nautobot/nautobot-app-device-onboarding/issues/283) - - Fixed adding invalid VLAN 0 to Diffsync Store causing Sync Data job to fail.
- [#287](https://github.com/nautobot/nautobot-app-device-onboarding/issues/287) - - Fix conditional logic to only show job log entries when git repo is used.
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - - Fixed typos in the 3.0 changelog
- [#289](https://github.com/nautobot/nautobot-app-device-onboarding/issues/289) - - Fixed a logging typo in an adapter
- [#293](https://github.com/nautobot/nautobot-app-device-onboarding/issues/293) - Makes fixes to platform detection so that netmiko ssh pubkey auth settings are applied.
- [#301](https://github.com/nautobot/nautobot-app-device-onboarding/issues/301) - Fixed missing job argument for the troubleshooting job.

### Housekeeping

- [#1](https://github.com/nautobot/nautobot-app-device-onboarding/issues/1) - Rebaked from the cookie `nautobot-app-v2.4.1`.
- [#189](https://github.com/nautobot/nautobot-app-device-onboarding/issues/189) - - Added documentation on using ssh public key authentication.
- [#189](https://github.com/nautobot/nautobot-app-device-onboarding/issues/189) - - Added documentation on using ssh proxy via jumphost.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Fixed typos in function names, comments, and errors.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Updated documentation to include an example CSV for bulk onboarding.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Updated documentation to make yaml override placement and git repository more clear.
- [#266](https://github.com/nautobot/nautobot-app-device-onboarding/issues/266) - Added a homepage to the app config.
- [#286](https://github.com/nautobot/nautobot-app-device-onboarding/issues/286) - Fixed typos on app overview file
