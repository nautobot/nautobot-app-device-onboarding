# Frequently Asked Questions

## What are the use cases for Onboarding Extensions?

See dedicated FAQ for device [onboarding extensions](../dev/dev_onboarding_extensions.md).

## How do I onboard a device using HTTPS-API?

You need to disable automatic platform detection, specify the device platform type (platform has to be configured with napalm driver) and port. By default, onboarding plugin uses SSH port (22) to discover platform type and loads appropriate NAPALM driver automatically. In case a HTTPS-API is to be used, you have to disable this behaviour and manually choose the platform type with a declared NAPALM driver.

## Is it possible to disable the automatic creation of Device Type, Device Role or Platform?

**Yes**! Using the plugin settings, it's possible to control individually the creation of `device_role`, `device_type`, `manufacturer` & `platform`.

```
# configuration.py
# If need you can override the default settings
# PLUGINS_CONFIG = {
#   "nautobot_device_onboarding": {
#         "create_platform_if_missing": True,
#         "create_manufacturer_if_missing": True,
#         "create_device_type_if_missing": True,
#         "create_device_role_if_missing": True,
#         "default_device_role": "network",
#   }
# }
```

## How can I update the default credentials used to connect to a device?

By default, the plugin uses the credentials defined in the main `nautobot_config.py` for NAPALM (`NAPALM_USERNAME`/`NAPALM_PASSWORD`). You can update the default credentials in `nautobot_config.py ` or you can provide specific one for each onboarding task.

## How can I update the optional arguments for NAPALM?

Optional arguments are often used to define a `secret` for Cisco devices and other connection parameters. By default, plugin will use a provided secret for each onboarding task. If such one is not provided, for tasks with a declared platform plugin will read optional arguments from Nautobot if they are defined at a platform level. Last resort of optional arguments is `settings.NAPALM_ARGS`.

## Does this plugin support the discovery and the creation of all interfaces and IP Addresses?

**No**. The plugin will only discover and create the management interface and the management IP address. Importing all interfaces and IP addresses is a much larger problem that requires more preparation. This is out of scope of this project.

> We recommend Network Importer tool from Network to Code for a post-onboarding network state synchronization. See [its GitHub repository](https://github.com/networktocode/network-importer) for more details.

## Does this plugin support the discovery of device based on fqdn?

**Yes**, plugin will resolve FQDN into an IP address and will use the IP address for its connections.

## Does this plugin support the discovery of Stack or Virtual Chassis devices?

**Yes**! Multi member devices (Stack, Virtual Chassis, FW Pair) can be imported but by default they will be imported as a single device. As multi member devices modelling is very individual in each case, it is required to create a customized onboarding extensions to control the behaviour of creating multiple devices.

## Is this plugin able to automatically discover the type of my device?

**Yes**! The plugin is leveraging [Netmiko](https://github.com/ktbyers/netmiko) & [Napalm](https://napalm.readthedocs.io/en/latest/) to attempt to automatically discover the OS and the model of each device.

## How many devices can I import at the same time?

**Many**, there are no strict limitations regarding the number of devices that can be imported. The speed at which devices will be imported will depend of the number of active Nautobot workers.

## Do I need to setup a dedicated RQ or Celery Worker node?

**No**. The plugin is leveraging the existing RQ or Celery Worker infrastructure already in place in Nautobot, the only requirement is to ensure the plugin itself is installed in the Worker node.

## Why don't I see a webhook generated when a new device is onboarded successfully?

It's expected that any changes done asynchronously in Nautobot currently (within a worker) will not generate a webhook.
