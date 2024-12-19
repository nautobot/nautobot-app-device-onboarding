# App Overview

This document provides an overview of the App including critical information and import considerations when applying it to your Nautobot environment.

This [Nautobot](https://github.com/nautobot/nautobot) App allows to easily onboard new devices.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description/Overview

This section describes the new implementation (SSoT Implementation) and the original implementation.

### New SSoT Implementation

The new implementation of device onboarding in this app is utilizing the SSoT framework; the main reasons for providing the new mechanisms were to solve the following challenges:

- Make it easier to extending and add additional vendor/OS support.
- Collapse this app and the external [Network Importer](https://github.com/networktocode/network-importer) into the same Nautobot app for simplified device onboarding with more object support.'
    - Remove the Batfish dependency.
- Re-use backend plugins and libraries such as `nautobot-app-nornir` to provide the a similar feeling to other plugins like `nautobot-app-golden-config`.
- Utilize SSoT framework and the new `contrib` functionality to speed up development of new features.
- By collapsing:

Expose two new SSoT based Nautobot jobs to perform the syncing of data.

1. `Sync Devices From Network` - Takes minimum inputs nearly identical to the original job (IP, Location, SecretGroup), and create a device with bare minium information to be able to manage a device. This job syncs data from the network itself and creates a device with the follow attributes.
    - Hostname
    - Serial Number
    - Device Type
    - Platform
    - Management Interface
    - Management IP address (creates a prefix if one doesn't exist for the IP discovered.)

2. `Sync Network Data From Network` - From a provided list of existing Nautobot device objects, sync in additional metadata from a network device to enhance the available data from the network in Nautobot.
    - All interfaces on the device with plus the attributes below:
        - Interface Name
        - MTU
        - Description
        - Interface type (limited support. Default: 'Other')
        - Mac Address
        - Link Status
        - Interface Mode
    - VLANs
        - Vlans
        - Untagged and Tagged
    - VRFs
        - VRF Names
        - Route Distinguishers (RD)
    - Cabling

!!! info
    For more information look at the provided jsonschema definitions for each of the jobs.

Additional References:

- For more information see [App Use Cases](./app_use_cases.md).
- To understand the lower level details of how the Network-SSoT framework is designed see [Network-SSoT Design](./app_detailed_design.md)
- To learn how to add additional platform/OS support visit [Extending](./external_interactions.md).

### Original Implementation

!!! info
    The original job and extensions pattern will remain a part of this App for the near future, this will allow custom extensions to continue working without causes issues to users that have taken the time and understand the original framework.  The newer SSoT implementation will be discussed in the next section.

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

Existing Nautobot users may want to incorporate the Onboarding App as part of onboarding new devices to the platform.

## Authors and Maintainers

### Authors

@mzb and @dgarros and many other great contributors!

### Maintainers

- @mzb
- @glennmatthews
- @chadell
- @scetron

## Nautobot Features Used/Employed

- Secrets & SecretsGroup
- Jobs
- Datasources
