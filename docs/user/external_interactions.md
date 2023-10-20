# External Interactions

This document describes external dependencies and prerequisites for this App to operate, including system requirements, API endpoints, interconnection or integrations to other applications or services, and similar topics.

## External System Integrations

### From the App to Other Systems

The App uses [netmiko](https://github.com/ktbyers/netmiko) and [NAPALM](https://napalm.readthedocs.io/en/latest/) libraries to connect to network devices. 

## Nautobot REST API endpoints

The plugin includes 4 API endpoints to manage the onboarding tasks:

```shell
GET        /api/plugins​/device-onboarding​/onboarding​/       Check status of all onboarding tasks.
POST    ​   /api/plugins​/device-onboarding​/onboarding​/       Onboard a new device
GET     ​   /api/plugins​/device-onboarding​/onboarding​/{id}​/  Check the status of a specific onboarding task
DELETE    ​ /api/plugins​/device-onboarding​/onboarding​/{id}​/  Delete a specific onboarding task
```
