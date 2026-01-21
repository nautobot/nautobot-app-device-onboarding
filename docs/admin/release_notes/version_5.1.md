# v5.1 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Support for additional device platforms has been added, including Brocade/Ruckus FastIron, HP Procurve, ArubaCX, ArubaOS, and F5 TMSH.
- Fixed several bugs related to database connections, device synchronization, and interface management.

<!-- towncrier release notes start -->

## [v5.1.0 (2026-01-21)](https://github.com/nautobot/nautobot-app-device-onboarding/releases/tag/v5.1.0)

### Added

- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for Brocade/Ruckus fastiron. Tested in SW versions: 08.0.30hT211,08.0.30hT213,08.0.30saT211,08.0.61aT211,08.0.61cT211,08.0.61T203,08.0.61T211,08.0.70dbT211,08.0.80bT211,08.0.80cT211,08.0.80cT213,08.0.80dT213,08.0.90dT211,08.0.90dT213,08.0.90jT211,08.0.90T211,08.0.92bT211,08.0.92bT213,08.0.92T211,08.0.92T213,08.0.92T233,08.0.95bbT211,08.0.95bbT213,08.0.95dT211,08.0.95fT211,08.0.95gT211,08.0.95gT241,08.0.95hT211,08.0.95jT211,08.0.95kT211,08.0.95kT213,08.0.95mT213,08.0.95nT211,08.0.95rT211,10.0.00T253,10.0.10bT253,10.0.10c_cd4T253,10.0.10d_cd2T253,10.0.10d_cd3T253,10.0.10f_cd1T213,10.0.10f_cd1T243,10.0.10f_cd1T253,10.0.10f_cd2T253,10.0.10f_cd3T253,10.0.10f_cd4T213,10.0.10fT253
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for HP Procurve. Tested in SW versions: A.15.09.0012,A.15.15.0012,A.15.16.0021,C.09.22,C.09.30,E.11.43,F.05.80,G.07.117,H.10.119,I.10.107,J.15.09.0028,K.15.02.0005,K.15.18.0015,K.15.18.0021,K.16.02.0030,K.16.02.0033,KA.16.04.0023,KB.15.15.0008,KB.15.18.0010,KB.16.02.0013,KB.16.05.0007,KB.16.07.0003,KB.16.10.0016,KB.16.10.0022,KB.16.11.0001,KB.16.11.0013,KB.16.11.0015,KB.16.11.0019,KB.16.11.0020,KB.16.11.0021,L.11.48,M.10.104,N.11.52,N.11.78,Q.11.17,Q.11.57,Q.11.78,R.11.122,R.11.25,R.11.30,R.11.70,RA.16.04.0023,S.15.09.0029,U.11.10,U.11.11,U.11.66,W.15.14.0018,WB.16.10.0016,Y.11.52,YA.15.17.0009,YA.16.01.0004,YA.16.02.0012,YA.16.10.0009,YA.16.10.0016,YA.16.11.0001,YA.16.11.0003,YA.16.11.0015,YA.16.11.0018,YA.16.11.0021,YB.16.03.0003,YB.16.10.0016,YB.16.11.0001,YB.16.11.0023
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds network data sync support for ArubaCX. Tested in SW versions: FL.10.10.1030,FL.10.13.1000,FL.10.13.1031,FL.10.13.1040,FL.10.13.1060,FL.10.13.1101,FL.10.13.1110,FL.10.14.1000,FL.10.15.0005,ML.10.10.1030,ML.10.13.0001,ML.10.13.1031,ML.10.13.1040,ML.10.13.1060,ML.10.13.1080,ML.10.13.1090,ML.10.14.0001,ML.10.14.1010,ML.10.15.0005,PL.10.08.1010,PL.10.10.1090,PL.10.11.1001,PL.10.11.1011,PL.10.13.1031,PL.10.13.1040,PL.10.13.1050,PL.10.13.1060,PL.10.13.1070,PL.10.13.1080,PL.10.13.1090,PL.10.14.1000,PL.10.14.1010,PL.10.14.1020,PL.10.14.1050,PL.10.15.0005,PL.10.15.1020,RL.10.13.1040
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds support for ArubaOS. Tested in SW versions: FL.10.06.0101,FL.10.06.0170,KA.16.02.0028,KA.16.04.0023,KB.16.10.0009,ML.10.06.0101,PB.03.10,RA.16.04.0016,RA.16.04.0023,WB.16.10.0009,WB.16.10.0016,YA.16.10.0016,YB.16.10.0016,YC.16.10.0009
- [#424](https://github.com/nautobot/nautobot-app-device-onboarding/issues/424) - Adds network data sync for F5 tmsh. Tested in SW versions: 17.1.13, 15.1.10.2

### Fixed

- [#366](https://github.com/nautobot/nautobot-app-device-onboarding/issues/366) - Fixed Sync Devices and Sync Network Data jobs not releasing DB connections.
- [#428](https://github.com/nautobot/nautobot-app-device-onboarding/issues/428) - In the sync network data job, added handling of Devices who's Primary IP is not set.
- [#455](https://github.com/nautobot/nautobot-app-device-onboarding/issues/455) - Fixed migration bug where OnboardingTask was not filtered correctly.
- [#476](https://github.com/nautobot/nautobot-app-device-onboarding/issues/476) - Fixed interfaces attached to modules being recreated when running the Sync Network Data job.

### Documentation

- [#437](https://github.com/nautobot/nautobot-app-device-onboarding/issues/437) - Updated documentation on the readme for capitalization.

### Housekeeping

- Rebaked from the cookie `nautobot-app-v3.0.0`.
