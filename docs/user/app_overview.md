# App Overview

This document provides an overview of the App including critical information and import considerations when applying it to your Nautobot environment.

This [Nautobot](https://github.com/nautobot/nautobot) App allows to easily onboard new devices.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description/Overview

The `nautobot-device-onboarding` app uses the [netmiko](https://github.com/ktbyers/netmiko) and [NAPALM](https://napalm.readthedocs.io/en/latest/) libraries to simplify the onboarding process of a new device into Nautobot down to, in many cases, an *IP Address* and a *Location*. In some cases, the user may also have to specify a specific *Device Platform* and *Device Port*.

Regardless, the Onboarding App greatly simplifies the onboarding process by allowing the user to specify a small amount of info and having the app populate a much larger amount of device data in Nautobot.

In most cases, the user would specify:

- Device Name
- Location
- Platform *
- Transport Port *

!!! note
    * `Platform` and `Transport Port` are necessary for onboarding NXOS API, Arista EOS, or any other platform not using SSH as a transport.

And the Onboarding App would populate the following:

- Device Type (Model) - Creates it if it does not exist.
- Role - via a Role of content-type "dcim:device". Defaults to `network`.
- Platform - Creates Cisco IOS, Cisco NXOS (ssh), and Junos Platforms if they do not exist.
- Manufacturer - Creates Cisco/Juniper/Arista if it does not exist.
- Management Interface.
- Management Interface IP.
- Serial Number (when available).

The goal of this app is not to import everything about a device into Nautobot. Rather, the goal is to quickly build an inventory of basic device data in Nautobot that provides basic info on how to access the devices.
For example, getting the Management IP and Platform data into Nautobot allows a follow-on tool that uses the basic info to access each device, retrieve data, and then populate Nautobot with that data.

One example of a solution that can retrieve that additional device data and import it into Nautobot is the [Network Importer](https://github.com/networktocode/network-importer). Other options would include an Ansible playbook or a Python script.

## Audience (User Personas) - Who should use this App?

The Onboarding App is meant for new Nautobot users who want to start importing their devices directly rather than from another, existing, source. Even with other sources for device information, they may not include everything that is necessary.

Existing Nautobot users may want to incorporate the Onboarding Plugin as part of onboarding new devices to the platform.

## Authors and Maintainers

### Authors

@mzb and @dgarros

### Maintainers

- @mzb
- @glennmatthews
- @chadell
- @scetron

## Nautobot Features Used/Employed

- Secrets & SecretsGroup
- Jobs
