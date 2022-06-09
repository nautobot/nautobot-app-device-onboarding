# External Interactions

```{admonition} Developer Note - Remove Me!
What (if any) interactions exist between this Nautobot App and the outside world (i.e. systems that are not part of Nautobot).
```

## External System Integrations

### From the App to Other Systems

### From Other Systems to the App

## Nautobot REST API endpoints

```{admonition} Developer Note - Remove Me!
TBD: This is 50-50 user/developer - so TBD on location. Maybe just a pointer to a page under the dev guide.

API documentation in this doc - including python request examples, curl examples, postman collections referred etc.
```

The plugin includes 4 API endpoints to manage the onboarding tasks:

```shell
GET        /api/plugins​/device-onboarding​/onboarding​/       Check status of all onboarding tasks.
POST    ​   /api/plugins​/device-onboarding​/onboarding​/       Onboard a new device
GET     ​   /api/plugins​/device-onboarding​/onboarding​/{id}​/  Check the status of a specific onboarding task
DELETE    ​ /api/plugins​/device-onboarding​/onboarding​/{id}​/  Delete a specific onboarding task
```
