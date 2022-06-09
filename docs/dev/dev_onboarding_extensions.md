# Onboarding Extensions

## What are onboarding extensions?

Onboarding Extensions are Python modules that are dynamically loaded and executed as a part of device onboarding.

## What are common use cases for onboarding extensions?

Onboarding extensions could be used (but not limited to) to perform the following operations:

- Stack onboarding
- HA Pairs, VSS pairs onboarding
- Populating device-bays and child devices, ie. Cisco UCS-Es
- Populating device inventories during onboarding
- Setting device roles during onboarding, ie. `Role = Access Switch`
- Setting device tags during onboarding, ie: `onboarded_with=networktocode`

## How do I enable onboarding extensions?

You have to modify Nautobot configuration in `nautobot_config.py` to include your extension's configuration. In the example below, we map a NAPALM driver name (this one could be a custom NAPALM driver too!), into a loadable python module containing your onboarding extension. Onboarding plugin will dynamically load and execute your module as specified below:

```python
        "onboarding_extensions_map": {
            "cisco_ios": "onboarding_extensions.ios",
            "cisco_nxos": "onboarding_extensions.nxos",
            "cisco_asa": "onboarding_extensions.asa",
        },
```

## How do I create an onboarding extension?

You have to create two elements as a part of your extension:

- an `OnboardingDriverExtensions` class inside your python module
- an `OnboardingClass`

At first, plugin will initiate an instance of your `OnboardingDriverExtensions` (you have to use this name of the class). Onboarding plugin passes the NAPALM device with an opened connection to this class, allowing you to to execute any custom commands with NAPALM (ie. collect device stack information).

`OnboardingDriverExtensions` must contain two important class attributes:

- `onboarding_class` (mandatory)
- `ext_result` (optional).

In `onboarding_class` attribute, you have to return a custom class that defines your onboarding methods. This is useful, as you might want to onboard devices in multiple different ways and `onboarding_class` acts as an distinguisher here.

The `ext_result` attribute allows to collect and store any data while the device connection is active. Your custom `OnboardingClass` will be initiated with `driver_addon_result` attribute containing the value of `ext_result`.

## Where do I find an example of onboarding extension ?

Please check our example: [example_ios_set_device_role.py](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/examples/example_ios_set_device_role.py).
