
# v4.3 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Deprecated Python 3.8
- Added Cisco IOS-XR experimental support to Nautobot Device Onboarding.

## [v4.3.0 (2025-09-10)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v4.3.0)

### Added

- [#348](https://github.com/nautobot/nautobot-app-device-onboarding/issues/348) - Added Cisco IOS-XR experimental support to Nautobot Device Onboarding.

### Changed

- [#407](https://github.com/nautobot/nautobot-app-device-onboarding/issues/407) - Changed napalm dependency to match Nautobot Core.

### Deprecated

- [#414](https://github.com/nautobot/nautobot-app-device-onboarding/issues/414) - Deprecated Python 3.8 support as its EOL.

### Fixed

- [#342](https://github.com/nautobot/nautobot-app-device-onboarding/issues/342) - Fixed a bug that prevented onboarding devices using their FQDN.
- [#376](https://github.com/nautobot/nautobot-app-device-onboarding/issues/376) - Fixed the default coming back for admin status to default to False instead of an empty list.
- [#384](https://github.com/nautobot/nautobot-app-device-onboarding/issues/384) - Fixed a typo in the F5 command mapper yaml.
- [#385](https://github.com/nautobot/nautobot-app-device-onboarding/issues/385) - Fixed bug causing exessive logging noise
- [#386](https://github.com/nautobot/nautobot-app-device-onboarding/issues/386) - Add 10GEChannel to INTERFACE_TYPE_MAP_STATIC so that port-channel interfaces with this hardware type are recognized as type LAG.
- [#387](https://github.com/nautobot/nautobot-app-device-onboarding/issues/387) - fixes capitalization of the keys in the command_mapper for cisco_nxos for `show interface switchport`
- [#388](https://github.com/nautobot/nautobot-app-device-onboarding/issues/388) - Fixed dictionary being modified during execution by working off of a copy of the dictionary.

### Dependencies

- [#348](https://github.com/nautobot/nautobot-app-device-onboarding/issues/348) - Update ntc-templates pinning to support Cisco XR parsing.
- [#414](https://github.com/nautobot/nautobot-app-device-onboarding/issues/414) - Updating the jdiff dependency to major version.

### Documentation

- [#402](https://github.com/nautobot/nautobot-app-device-onboarding/issues/402) - Added Analytics GTM template override only to the public ReadTheDocs build.
- Fixed some section headings in the documentation for proper TOC parsing.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v2.5.0`.
- Rebaked from the cookie `nautobot-app-v2.5.1`.
