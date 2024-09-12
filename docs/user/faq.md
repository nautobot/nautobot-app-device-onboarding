# Frequently Asked Questions

## Why does my Location or Role not appear on the job form?

Locations are related to the LocationType object and the LocationType has an attribute for ContentTypes that are meant to limit what types of object that can be associated to a location. Validate the desired Location you are attempting to use is using a LocationType that has `dcim.Device` in the list of allowed ContentTypes.

Similarly to Location, Roles are also scoped to ContentTypes however this is controlled via an attribute directly on the Role model and not through an additional model as Location + LocationType is done. The required ContentType is also `dcim.Device`.

## What are the use cases for Onboarding Extensions?

See dedicated FAQ for device [onboarding extensions](../dev/onboarding_extensions.md).

## How do I onboard a device using HTTPS-API?

You need to disable automatic platform detection, specify the device platform type (platform has to be configured with napalm driver) and port. By default, onboarding plugin uses SSH port (22) to discover platform type and loads appropriate NAPALM driver automatically. In case a HTTPS-API is to be used, you have to disable this behaviour and manually choose the platform type with a declared NAPALM driver.

## Is it possible to disable the automatic creation of Device Type, Device Role or Platform?

**Yes** (original)! Using the plugin settings, it's possible to control individually the creation of `device_role`, `device_type`, `manufacturer` & `platform`.

```python
# configuration.py
# If need you can override the default settings
PLUGINS_CONFIG = {
    "nautobot_device_onboarding": {
        "create_platform_if_missing": True,
        "create_manufacturer_if_missing": True,
        "create_device_type_if_missing": True,
        "create_device_role_if_missing": True,
        "default_device_role": "network",
    }
}
```

**Yes** (SSoT)! Using the job for input selections, it's possible to control individually the creation of `device_role`, `device_type`, `manufacturer` & `platform`.

## How can I update the default credentials used to connect to a device?

By default, the plugin uses the credentials defined in the main `nautobot_config.py` for NAPALM (`NAPALM_USERNAME`/`NAPALM_PASSWORD`/`DEVICE_ARGS`). You can update the default credentials in `nautobot_config.py ` or you can provide specific one for each onboarding job via a SecretsGroup. If using SecretsGroup the Access Type for the associated Secrets must be `Generic` and at minimum associated Secrets for `Username` & `Password` are required with `Secret` being optional.

!!! warning
    If an enable secret is required for the remote device it must be set using above patterns.

For the SSoT onboarding based jobs SecretGroups are required.

## How can I update the optional arguments for NAPALM?

Optional arguments are often used to define a `secret` for Cisco devices and other connection parameters. By default, app will use a provided secret for each onboarding task. If such one is not provided, for tasks with a declared platform app will read optional arguments from Nautobot if they are defined at a platform level. Last resort of optional arguments is `settings.NAPALM_ARGS`.

## Does this app support the discovery and the creation of all interfaces and IP Addresses?

**Yes**. The original Deivce Onboarding job/SSot Sync Devices will only discover and create the management interface and the management IP address. Importing all interfaces and IP addresses is available from the SSoT job (Sync Network Data).

## Does this app support the discovery of device based on fqdn?

**Yes**, app will resolve FQDN into an IP address and will use the IP address for its connections.

## Does this app support the discovery of Stack or Virtual Chassis devices?

**Yes**! Multi member devices (Stack, Virtual Chassis, FW Pair) can be imported but by default they will be imported as a single device. As multi member devices modelling is very individual in each case, it is required to create a customized onboarding extensions to control the behaviour of creating multiple devices.

## Is this app able to automatically discover the type of my device?

**Yes**! The app is leveraging [Netmiko](https://github.com/ktbyers/netmiko) & [Napalm](https://napalm.readthedocs.io/en/latest/) to attempt to automatically discover the OS and the model of each device.

## How many devices can I import at the same time?

**Many**, there are no strict limitations regarding the number of devices that can be imported. The speed at which devices will be imported will depend of the number of active Nautobot workers.

## Do I need to setup a dedicated Celery Worker node?

**No**. The app is leveraging the existing Celery Worker infrastructure already in place in Nautobot, the only requirement is to ensure the app itself is installed in the Worker node.

## Why don't I see a webhook generated when a new device is onboarded successfully?

It's expected that any changes done asynchronously in Nautobot currently (within a worker) will not generate a webhook.

## Why should I limit as much as possible the initial job?

- No access to "all" data, such as config context.
- Several assumptions made for Nornir inventory that would be different in all other Nornir inventory jobs.
- An inventory created for each device.
    - Causes additional SQL connections which may benefit from the use of `serial` runner.

## What is the order for Secrets in the `Sync Devices` job?

- Secret Group

The second job currently does:
- Credential_path in nautobot_nornir PLUGIN CONFIG set to in nautobot_config.py

Environment Variables

Settings Vars

Nautobot Secrets Group
- Assigned to Device (via first job)
- 