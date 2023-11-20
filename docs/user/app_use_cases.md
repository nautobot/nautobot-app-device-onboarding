# Using the App

## General Usage

### Preparation

To properly onboard a device, a user needs to provide, at a minimum:

1. The Device's Location
2. The Device's primary IP address or DNS Name

!!! note
    For DNS Name Resolution to work, the instance of Nautobot must be able to resolve the name of the device to IP address.

If other attributes (`Platform`, `Device Type`, `Role`) are provided in the onboarding job, the app will use provided value for the onboarded device.

If `Platform`, `Device Type` and/or `Role` are not provided, the plugin will try to identify this information automatically and, based on the settings, it can create them in Nautobot as needed.

!!! note
    If the Platform is provided, it must point to an existing Nautobot Platform. NAPALM driver of this platform will be used only if it is defined for the platform in Nautobot.
    To use a preferred NAPALM driver, either define it in Nautobot per platform or in the plugins settings under `platform_map`.

#### SSH Autodetect

The `nautobot-device-onboarding` app recognizes platform types with a Netmiko SSH Autodetect mechanism. The user may need to specify additional information for platforms where Netmiko's `ssh_autodetect` feature does not work.

[Here is the list](https://github.com/ktbyers/netmiko/blob/v3.4.0/netmiko/ssh_autodetect.py#L50) of platforms supported by `ssh_autodetect`.

The `nautobot-device-onboarding` app can be used with any devices that are supported by NAPALM. Even custom NAPALM driver plugins can be used with a bit of effort.

Devices that are supported by NAPALM but are not running SSH or don't have support for `ssh_autodetect` will still work with this app, but will require some additional information in the onboarding job.

The table below shows which common platforms will be SSH auto-detected by default.

|Platform     |Platform Autodetect|
--------------|--------------------
Juniper/Junos | Yes (when running Netconf over SSH)|
Cisco IOS-XE  |Yes|
Cisco NXOS (ssh) | Yes|
Cisco NXOS (nxapi)| No|
Arista EOS | No|

For the platforms where SSH auto-detection does not work, the user will need to:

1. Manually define a Platform in Nautobot (this will be a one-time task in order to support any number of devices using this Platform)
2. During onboarding, a Port and Platform must explicitly be specified (in addition to the IP and Location)

### IOS and Junos Auto-Created Platforms

The Onboarding App will automatically create Platforms for vendor operating systems where platform auto-detection works. The picture below shows the details of auto-created Platforms for `cisco_ios` and `juniper_junos`.

![cisco_ios_platform](../images/platform_cisco_ios.png)
![juniper_junos_platform](../images/platform_juniper_junos.png)


## Use-cases and common workflows

### Create a New Platform

This section demonstrates how to create a new Platform in the Nautobot UI. Specifically, it offers examples for creating platforms for Cisco `nxapi` and Arista `eos` devices, but the concepts are applicable to any Platform that is manually created.

- In the Nautobot dropdown menu, go to `Devices--> Platforms--> Add/+`.
- Define the attributes for the Platform on this screen and click on the 'Create' button.
- 'Manufacturer' and 'NAPALM arguments' are optional.

!!! note
    Slugs have been deprecated in Nautobot 2. The Platform `Network driver` will now be used to determine the driver to use.

#### Cisco NXOS Platform

A Platform that will work with NXOS devices running the `nxapi` feature must have specific values for these attributes:

- `Network driver` **SHOULD** be `cisco_nxos`.
- `NAPALM driver` **MUST** be `nxos`.

#### Arista EOS Platform

A Platform that will work with Arista EOS devices must have specific values for these attributes:

- `Network driver` **SHOULD** be `arista_eos`.
- `NAPALM driver` **MUST** be `eos`.


### Onboard a New Device

A new device can be onboarded via :

- A job execution. 
- An API, via a `POST` to `/api/extras/jobs/{id}/run`

During a successful onboarding process, a new device will be created in Nautobot with its management interface and its primary IP assigned. The management interface will be discovered on the device based on the IP address provided.

!!! note
    By default, the app is using the credentials defined in the main `nautobot_config.py` for Napalm (`NAPALM_USERNAME`/`NAPALM_PASSWORD`/`NAPALM_ARGS`). It's possible to define specific credentials for each onboarding job execution.

### Onboard a Cisco NXOS Device Running the `nxapi` Feature

When onboarding an NXOS device with the `nxapi` feature, there are a few requirements:

- The `Port` must be the same value configured for `nxapi https port` on the Cisco Nexus device
- The `Platform` must be explicitly set to be one with the specific parameters in the [Cisco NXOS Platform](#cisco-nxos-platform) section

### Onboarding an Arista EOS Device

When onboarding an Arista EOS device, there are a few requirements:

- The `Port` must be the same value configured for HTTPS on the Arista device
- The `Platform` must be explicitly set to be the one with the specific parameters in the [Arista EOS Platform](#arista-eos-platform) section


### Consult the Status of Onboarding Tasks

The status of the onboarding process for each device is maintained is a dedicated table in Nautobot and can be retrieved:
- Via the UI via Job-Results
- Via the API via Job-Results
