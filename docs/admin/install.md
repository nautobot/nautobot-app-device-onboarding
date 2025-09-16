# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

<<<<<<< HEAD
- The app is compatible with Nautobot 2.3.1 and higher.
=======
- The app is compatible with Nautobot 2.4.2 and higher.
>>>>>>> 7e2e637 (Cookie updated by NetworkToCode Cookie Drift Manager Tool)
- Databases supported: PostgreSQL, MySQL

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Application Dependencies

Device onboarding 4.0 added two additional application dependencies.

- [nautobot_ssot](https://docs.nautobot.com/projects/ssot/en/latest/)
- [nautobot_plugin_nornir](https://docs.nautobot.com/projects/plugin-nornir/en/latest/)

### Access Requirements

- The original OnboardingTask Job used NAPALM Credentials.
- The new SSoT based jobs use Nautobot Secrets in a similar method to other apps. This is a more flexible and supportable way for the future.

## Install Guide

!!! note
    Apps can be installed manually or using Python's `pip`. See the [nautobot documentation](https://nautobot.readthedocs.io/en/latest/plugins/#install-the-package) for more details. The pip package name for this app is [`nautobot-device-onboarding`](https://pypi.org/project/nautobot-device-onboarding/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-device-onboarding
```

To ensure Device Onboarding is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-device-onboarding` package:

```shell
echo nautobot-device-onboarding >> local_requirements.txt
```

Once installed, the app needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_device_onboarding"` to the `PLUGINS` list.
- Append the `"nautobot_device_onboarding"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_plugin_nornir", "nautobot_ssot", "nautobot_device_onboarding"]

# PLUGINS_CONFIG = {
#   "nautobot_device_onboarding": {
#     ADD YOUR SETTINGS HERE
#   }
# }
```

For the `Sync Data from Network` job to work the below must be added to the `PLUGINS_CONFIG`.

```python
    "nautobot_plugin_nornir": {
        "nornir_settings": {
            "credentials": "nautobot_plugin_nornir.plugins.credentials.nautobot_secrets.CredentialsNautobotSecrets",
            "runner": {
                "plugin": "threaded",
                "options": {
                    "num_workers": 20,
                },
            },
        },
    },
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration (Original)

Although the app can run without providing any settings, the app behavior can be controlled with the following list of settings defined in `nautobot_config.py`:

- `create_platform_if_missing` boolean (default True). If True, a new platform object will be created if the platform discovered by netmiko do not already exist and is in the list of supported platforms (`cisco_ios`, `cisco_nxos`, `arista_eos`, `juniper_junos`, `cisco_xr`)
- `create_device_type_if_missing` boolean (default True), If True, a new device type object will be created if the model discovered by Napalm do not match an existing device type.
- `create_manufacturer_if_missing` boolean (default True), If True, a new manufacturer object will be created if the manufacturer discovered by Napalm is do not match an existing manufacturer, this option is only valid if `create_device_type_if_missing` is True as well.
- `create_device_role_if_missing` boolean (default True), If True, a new device role object will be created if the device role provided was not provided as part of the onboarding and if the `default_device_role` does not already exist.
- `create_management_interface_if_missing` boolean (default True), If True, add management interface and IP address to the device. If False no management interfaces will be created, nor will the IP address be added to Nautobot, while the device will still get added.
- `default_device_status` string (default "Active"), status assigned to a new device by default.
- `default_ip_status` string (default "Active"), status assigned to a new device management IP.
- `default_device_role` string (default "network")
- `default_device_role_color` string (default FF0000), color assigned to the device role if it needs to be created.
- `default_management_interface` string (default "PLACEHOLDER"), name of the management interface that will be created, if one can't be identified on the device.
- `default_management_prefix_length` integer ( default 0), length of the prefix that will be used for the management IP address, if the IP can't be found.
- `skip_device_type_on_update` boolean (default False), If True, an existing Nautobot device will not get its device type updated. If False, device type will be updated with one discovered on a device.
- `skip_manufacturer_on_update` boolean (default False), If True, an existing Nautobot device will not get its manufacturer updated. If False, manufacturer will be updated with one discovered on a device.
- `assign_secrets_group` boolean (default False), If True, the credentials used to connect to the device will be assigned as the secrets group for the device upon creation. If False, no secrets group will be assigned.
- `set_management_only_interface` boolean (default False), If True, the interface that is created or updated will be set to management only. If False, the interface will be set to not be management only.
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
- `object_match_strategy` (string), defines the method for searching models. There are currently two strategies, strict and loose. Strict has to be a direct match, normally using a slug. Loose allows a range of search criteria to match a single object. If multiple objects are returned an error is raised.

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
