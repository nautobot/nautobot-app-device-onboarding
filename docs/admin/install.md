# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 2.0.3 and higher.
- Databases supported: PostgreSQL, MySQL

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

#### NAPALM Credentials

The Onboarding App uses NAPALM. You can configure a default NAPALM username and password in `nautobot_config.py`.

When `NAPALM_USERNAME`, `NAPALM_PASSWORD` and `NAPALM_ARGS` are configured in `nautobot_config.py`, the user does not have to use the Credentials/SecretGroup fields in the Device Onboarding job, unless they wish to override the values in `nautobot_config.py`:

```python
# Credentials that Nautobot will use to authenticate to devices when connecting via NAPALM.
NAPALM_USERNAME = "<napalm username>"
NAPALM_PASSWORD = "<napalm pwd>"
NAPALM_ARGS = {"secret": "<enable secret pwd>"}
```

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
PLUGINS = ["nautobot_device_onboarding"]

# PLUGINS_CONFIG = {
#   "nautobot_device_onboarding": {
#     ADD YOUR SETTINGS HERE
#   }
# }
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

## App Configuration

Although the plugin can run without providing any settings, the plugin behavior can be controlled with the following list of settings defined in `nautobot_config.py`:

The app behavior can be controlled with the following list of settings:

| Key     | Example | Default | Description                          |
| ------- | ------ | -------- | ------------------------------------- |
| `enable_backup` | `True` | `True` | A boolean to represent whether or not to run backup configurations within the app. |
| `platform_slug_map` | `{"cisco_wlc": "cisco_aireos"}` | `None` | A dictionary in which the key is the platform slug and the value is what netutils uses in any "network_os" parameter. |
| `per_feature_bar_width` | `0.15` | `0.15` | The width of the table bar within the overview report |
