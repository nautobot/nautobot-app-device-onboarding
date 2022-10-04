# App Overview

A plugin for [Nautobot](https://github.com/nautobot/nautobot) to easily onboard new devices.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description/Overview

The `nautobot-device-onboarding` plugin is using the [netmiko](https://github.com/ktbyers/netmiko) and [NAPALM](https://napalm.readthedocs.io/en/latest/) libraries to simplify the onboarding process of a new device into Nautobot down to, in many cases, an *IP Address* and a *Site*. In some cases, the user may also have to specify a specific *Device Platform* and *Device Port*.

Regardless, the Onboarding Plugin greatly simplifies the onboarding process by allowing the user to specify a small amount of info and having the plugin populate a much larger amount of device data in Nautobot.

In most cases, the user would specify:

- Device Name
- Site
- Platform [^1]
- Transport Port [^1]

[^1]: Necessary for onboarding NXOS API, Arista EOS, or any other platform not using SSH as a transport

And the Onboarding Plugin would populate the following:

- Device Type (Model) - Creates if it does not exist
- Device Role - defaults to `network`
- Platform - Creates Cisco IOS, Cisco NXOS (ssh), and Junos Platforms if they do not exist
- Manufacturer - Creates Cisco/Juniper/Arista if it does not exist
- Management Interface
- Management Interface IP
- Serial Number (when available)

The goal of this plugin is not to import everything about a device into Nautobot. Rather, the goal is to quickly build an inventory of basic device data in Nautobot that provides basic info on how to access the devices.
For example, getting the Management IP and Platform data into Nautobot allows a follow-on tool that uses the basic info to access each device, retrieve data, and then populate Nautobot with that data.

One example of a solution that can retrieve that additional device data and import it into Nautobot is the [Network Importer](https://github.com/networktocode/network-importer). Other options would include an Ansible playbook or a Python script.

## Audience (User Personas) - Who should use this App?

!!! warning "Developer Note - Remove Me!"
    Who is this meant for/ who is the common user of this app?

## Authors and Maintainers

## Features Used/Employed

!!! warning "Developer Note - Remove Me!"
    What is shown today in the Installed Plugins page in Nautobot.

### Extras

!!! warning "Developer Note - Remove Me!"
    Custom Fields - things like which CFs are created by this app?
    Jobs - are jobs, if so, which ones, installed by this app?
