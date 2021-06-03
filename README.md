# Nautobot Device Onboarding plugin

<!-- Build status with linky to the builds for ease of access. -->
[![Build Status](https://travis-ci.com/nautobot/nautobot-device-onboarding.svg?token=29s5AiDXdkDPwzSmDpxg&branch=master)](https://travis-ci.com/nautobot/nautobot-device-onboarding)

A plugin for [Nautobot](https://github.com/nautobot/nautobot) to easily onboard new devices.

`nautobot-device-onboarding` is using [Netmiko](https://github.com/ktbyers/netmiko) and 
[NAPALM](https://napalm.readthedocs.io/en/latest/) to simplify the onboarding 
process of a new device into Nautobot down to, in many cases, an IP Address and a site. In some cases, the user may also
have to specify a specific Device Platform and Device Port. Regardless, the Onboarding Plugin greatly simplifies the onboarding process
by allowing the user to specify a small amount of info and having the plugin populate a much larger amount of device data in Nautobot.

In most cases, the user would specify:
* Device Name 
* Site
* Platform **
* Transport Port **

> ** Necessary for onboarding NXOS API, Arista EOS, or any other platform not using SSH as a transport

And the Onboarding Plugin would populate the following:
* Device Type (Model) - Creates if it does not exist
* Device Role - defaults to `network` 
* Platform - Creates Cisco IOS, Cisco NXOS (ssh), and Junos Platforms if they do not exist
* Manufacturer - Creates Cisco/Juniper/Arista if it does not exist
* Management Interface
* Management Interface IP
* Serial Number (when available)

The goal of this plugin is not to import everything about a device into Nautobot. Rather, the goal is to quickly build an 
inventory of basic device data in Nautobot that provides basic info on how to access the devices. 
For example, getting the Management IP and Platform data into Nautobot allows a follow-on tool that uses the 
basic info to access each device, retrieve data, and then populate Nautobot with that data.

One example of a solution that can retrieve that additional device data and import it into Nautobot is the [Network Importer](https://github.com/networktocode/network-importer).
Other options would include an Ansible playbook or a Python script.


## Installation

If using the installation pattern from the Nautobot Documentation, you will need sudo to the `nautobot` user before installing so that you install the package into the Nautobot virtual environment.

```no-highlight
$ sudo -iu nautobot
```

The plugin is available as a Python package in PyPI and can be installed with `pip3`.

```no-highlight
$ pip3 install nautobot-device-onboarding
```

### Compatibility Matrix

|                              | Nautobot 1.0 |
| ---------------------------- | ------------ |
| Device Onboarding plugin 1.0 | X            |

To ensure Device Onboarding plugin is automatically re-installed during future upgrades, create a file named
`local_requirements.txt` (or append if it already exists) in the
[`NAUTOBOT_ROOT`](https://nautobot.readthedocs.io/en/latest/configuration/optional-settings/#nautobot_root) directory and list the `nautobot-device-onboarding` package:

```no-highlight
$ echo nautobot-device-onboarding >> $NAUTOBOT_ROOT/local_requirements.txt
```

### Nautobot Configuration

#### Enabling Plugin

Once installed, the plugin needs to be enabled in your `nautobot_config.py`
```python
# In your nautobot_config.py
PLUGINS = ["nautobot_device_onboarding"]
```

#### Plugin Configuration Options

Although plugin can run without providing any settings, the plugin behavior can be controlled with the following list of settings defined in `nautobot_config.py`

- `create_platform_if_missing` boolean (default True), If True, a new platform object will be created if the platform discovered by netmiko do not already exist and is in the list of supported platforms (`cisco_ios`, `cisco_nxos`, `arista_eos`, `juniper_junos`, `cisco_xr`)
- `create_device_type_if_missing` boolean (default True), If True, a new device type object will be created if the model discovered by Napalm do not match an existing device type.
- `create_manufacturer_if_missing` boolean (default True), If True, a new manufacturer object will be created if the manufacturer discovered by Napalm is do not match an existing manufacturer, this option is only valid if `create_device_type_if_missing` is True as well.
- `create_device_role_if_missing` boolean (default True), If True, a new device role object will be created if the device role provided was not provided as part of the onboarding and if the `default_device_role` do not already exist.
- `create_management_interface_if_missing` boolean (default True), If True, add management interface and IP address to the device. If False no management interfaces will be created, nor will the IP address be added to Nautobot, while the device will still get added.
- `default_device_status` string (default "Active"), status assigned to a new device by default.
- `default_ip_status` string (default "Active"), status assigned to a new device management IP.
- `default_device_role` string (default "network")
- `default_device_role_color` string (default FF0000), color assigned to the device role if it needs to be created.
- `default_management_interface` string (default "PLACEHOLDER"), name of the management interface that will be created, if one can't be identified on the device.
- `default_management_prefix_length` integer ( default 0), length of the prefix that will be used for the management IP address, if the IP can't be found.
- `skip_device_type_on_update` boolean (default False), If True, an existing Nautobot device will not get its device type updated. If False, device type will be updated with one discovered on a device.
- `skip_manufacturer_on_update` boolean (default False), If True, an existing Nautobot device will not get its manufacturer updated. If False, manufacturer will be updated with one discovered on a device.
- `platform_map` (dictionary), mapping of an **auto-detected** Netmiko platform to the **Nautobot slug** name of your Platform. The dictionary should be in the format:
    ```python
    {
      <Netmiko Platform>: <Nautobot Slug>
    }
    ```
- `onboarding_extensions_map` (dictionary), mapping of a NAPALM driver name to the loadable Python module used as an onboarding extension. The dictionary should be in the format:
    ```python
    {
      <Napalm Driver Name>: <Loadable Python Module>
    }
    ```
- `object_match_strategy` (string), defines the method for searching models. There are
currently two strategies, strict and loose. Strict has to be a direct match, normally 
using a slug. Loose allows a range of search criteria to match a single object. If multiple
objects are returned an error is raised. 

Modify `nautobot_config.py` with settings of your choice. Example settings are shown below:

```python
# Example settings In your nautobot_config.py
PLUGINS_CONFIG = {
  "nautobot_device_onboarding": {
    "default_ip_status": "Active",
    "default_device_role": "leaf",
    "skip_device_type_on_update": True,
  }
}
```


#### NAPALM Credentials

The Onboarding Plugin uses NAPALM. You can configure a default NAPALM username and password in `nautobot_config.py`.

When `NAPALM_USERNAME` and `NAPALM_PASSWORD` are configured in `nautobot_config.py`, the user does not have to 
specify the `Username` and `Password` fields in the Device Onboarding Task, unless they wish to override the values in 
`nautobot_config.py`:

```python
# Credentials that Nautobot will uses to authenticate to devices when connecting via NAPALM.
NAPALM_USERNAME = "<napalm username>"
NAPALM_PASSWORD = "<napalm pwd>"
```

### Final Configuration Steps

After installing the plugin and modifying `nautobot_config.py`, as the `nautobot` user, run the server migration:

```no-highlight
$ nautobot-server migrate
```

Finally, as root, restart Nautobot and the Nautobot worker.

```no-highlight
$ sudo systemctl restart nautobot nautobot-worker
```

## Upgrades

When a new release comes out it may be necessary to run a migration of the database to account for any changes in the data models used by this plugin. Execute the command `nautobot-server migrate` from the Nautobot install `nautobot/` directory after updating the package.

## Usage

### Preparation

To properly onboard a device, user needs to provide, at a minimum:
1. The Device's Site 
2. The Device's primary IP address or DNS Name

> For DNS Name Resolution to work, the instance of Nautobot must be able to resolve the name of the
> device to IP address.

If other attributes (`Platform`, `Device Type`, `Device Role`) are provided in the onboarding task, the plugin will use provided value for the onboarded device.
If `Platform`, `Device Type` and/or `Device Role` are not provided, the plugin will try to identify these information automatically and, based on the settings, it can create them in Nautobot as needed.
> If the Platform is provided, it must point to an existing Nautobot Platform. NAPALM driver of this platform will be used only if it is defined for the platform in Nautobot.
> To use a preferred NAPALM driver, either define it in Nautobot per platform or in the plugins settings under `platform_map`

#### SSH Autodetect

Plugin recognizes platform types with a Netmiko SSH Autodetect mechanism. The user will need to specify additional information for platforms where Netmiko's `ssh_autodetect` feature does not work. 
[Here is the list](https://github.com/ktbyers/netmiko/blob/v3.4.0/netmiko/ssh_autodetect.py#L50) of platforms supported by `ssh_autodetect`.

The `nautobot-device-onboarding` plugin can be used with any devices that are supported by NAPALM. Even custom NAPALM driver plugins can be used with a bit of effort.

Devices that are supported by NAPALM but are not running SSH or don't have support for `ssh_autodetect` will still work with this plugin, but will require some additional information in the onboarding task.

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
2. During onboarding, a Port and Platform must explicitly be specified (in addition to the IP and Site)

## IOS and Junos Auto-Created Platforms

The Onboarding Plugin will automatically create Platforms for vendor operating systems where platform auto-detection works.
The picture below shows the details of auto-created Platforms for `cisco_ios` and `juniper_junos`.

![cisco_ios_platform](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/platform_cisco_ios.png)
![juniper_junos_platform](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/platform_juniper_junos.png)

## Creating a Platform

This section will demonstrate how to create a new Platform in the Nautobot UI. Specifically, it will offer examples for
creating Cisco `nxapi` and Arista `eos` Platforms, but the concepts are applicable to any Platform that is manually created.

In the Nautobot dropdown menu, go to Devices--> Platforms--> Add/+.

Define the attributes for the Platform on this screen and click on the 'Create' button. 

The Slug value will be auto-populated based on the Platform Name, but you can overwrite that auto-populated value. For the platform to work correctly with this plugin, in many cases you will need to set a specific Slug value for it to work properly.

'Manufacturer' and 'NAPALM arguments' are optional.

### Cisco NXOS Platform

A Platform that will work with NXOS devices running the `nxapi` feature must have specific values for these attributes:
* `Slug` **SHOULD** be `cisco_nxos` (you may have to overwrite the auto-populated Slug value)
* `NAPALM driver` **MUST** be `nxos`


### Arista EOS Platform

A Platform that will work with Arista EOS devices must have specific values for these attributes:
* `Slug` **SHOULD** be `arista_eos` (you may have to overwrite the auto-populated Slug value)
* `NAPALM driver` **MUST** be `eos`


## Device Onboarding

### Onboard a new device

A new device can be onboarded via :
- A web form  `/plugins/device-onboarding/add/`
- A CSV form to import multiple devices in bulk. `/plugins/device-onboarding/import/`
- An API, `POST /api/plugins​/device-onboarding​/onboarding​/`

During a successful onboarding process, a new device will be created in Nautobot with its management interface and its primary IP assigned. The management interface will be discovered on the device based on the IP address provided.

> By default, the plugin is using the credentials defined in the main `configuration.py` for Napalm (`NAPALM_USERNAME`/`NAPALM_PASSWORD`). It's possible to define specific credentials for each onboarding task.


### Onboarding a Cisco NXOS Device Running the `nxapi` Feature

When onboarding an NXOS device with the `nxapi` feature, there are a few requirements:
* The `Port` must be the same value configured for `nxapi https port` on the Cisco Nexus device
* The `Platform` must be explicitly set to be one with the specific parameters in the [Cisco NXOS Platform](#cisco-nxos-platform) section

### Onboarding an Arista EOS Device 

When onboarding an Arista EOS device, there are a few requirements:
* The `Port` must be the same value configured for HTTPS on the Arista device
* The `Platform` must be explicitly set to be the one with the specific parameters in the [Arista EOS Platform](#arista-eos-platform) section


## Consult the Status of Onboarding Tasks

The status of the onboarding process for each device is maintained is a dedicated table in Nautobot and can be retrived :
- Via the UI `/plugins/device-onboarding/`
- Via the API `GET /api/plugins​/device-onboarding​/onboarding​/`

## API

The plugin includes 4 API endpoints to manage the onboarding tasks:

```shell
GET        /api/plugins​/device-onboarding​/onboarding​/       Check status of all onboarding tasks.
POST    ​   /api/plugins​/device-onboarding​/onboarding​/       Onboard a new device
GET     ​   /api/plugins​/device-onboarding​/onboarding​/{id}​/  Check the status of a specific onboarding task
DELETE    ​ /api/plugins​/device-onboarding​/onboarding​/{id}​/  Delete a specific onboarding task
```

## Customizing Onboarding Behaviour With Onboarding Extensions

This plugin provides methods to customize onboarding behaviour. By creating onboarding extensions, it is possible to onboard switch stacks, HA pairs and perform other customizations. Please see the dedicated FAQ for [device onboarding](https://github.com/nautobot/nautobot-plugin-device-onboarding/blob/develop/docs/onboarding-extensions/onboarding_extensions.md).


## Contributing

Pull requests are welcomed and automatically built and tested against multiple version of Python and multiple version of Nautobot through TravisCI.

The project is packaged with a light development environment based on `docker-compose` to help with the local development of the project and to run the tests within TravisCI.

The project is following Network to Code software development guideline and is leveraging:
- Black, Pylint, Bandit and pydocstyle for Python linting and formatting.
- Django unit test to ensure the plugin is working properly.

### CLI Helper Commands

The project is coming with a CLI helper based on [invoke](http://www.pyinvoke.org/) to help setup the development environment. The commands are listed below in 3 categories `dev environment`, `utility` and `testing`. 

Each command can be executed with `invoke <command>`. All commands support the arguments `--nautobot-ver` and `--python-ver` if you want to manually define the version of Python and Nautobot to use. Each command also has its own help `invoke <command> --help`

#### Local dev Environment
```
  build            Build all docker images.
  debug            Start Nautobot and its dependencies in debug mode.
  destroy          Destroy all containers and volumes.
  start            Start Nautobot and its dependencies in detached mode.
  stop             Stop Nautobot and its dependencies.
```

#### Utility 
```
  cli              Launch a bash shell inside the running Nautobot container.
  create-user      Create a new user in django (default: admin), will prompt for password.
  makemigrations   Run Make Migration in Django.
  nbshell          Launch a nbshell session.
```
#### Testing 

```
  tests            Run all tests for this plugin.
  pylint           Run pylint code analysis.
  pydocstyle       Run pydocstyle to validate docstring formatting adheres to NTC defined standards.
  bandit           Run bandit to validate basic static code security analysis.
  black            Run black to check that Python files adhere to its style standards.
  unittest         Run Django unit tests for the plugin.
```

## Questions

For any questions or comments, please check the [FAQ](FAQ.md) first and feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode).
Sign up [here](http://slack.networktocode.com/)

## Screenshots

List of Onboarding Tasks
![Onboarding Tasks](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/onboarding_tasks_view.png)

CSV form to import multiple devices
![CSV Form](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/csv_import_view.png)

Onboard a single device
![Single Device Form](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/single_device_form.png)

Menu 
![Menu](https://github.com/nautobot/nautobot-plugin-device-onboarding/raw/main/docs/images/menu.png)
