# v5.6 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

<!-- towncrier release notes start -->

## [v5.6.0 (2026-09-22)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.6.0)

### Added

- [#584](https://github.com/nautobot/nautobot-app-device-onboarding/issues/584) - Added Sync Network Data support for Palo Alto PAN-OS in the `paloalto_panos.yml` command mapper, covering interfaces (name, type, IP addresses, MAC, MTU, description, link status, 802.1Q mode, LAG membership, tagged/untagged VLANs, VRF membership), software version, and serial number.
