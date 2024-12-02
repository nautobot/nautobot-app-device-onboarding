# Extending the App

Extending the application is welcome, however it is best to open an issue first, to ensure that a PR would be accepted and makes sense in terms of features and design.

## Customizing Onboarding Behavior With Extensions (Original)

This plugin provides methods to customize onboarding behavior. By creating onboarding extensions, it is possible to onboard switch stacks, HA pairs and perform other customizations.

Please see the dedicated FAQ for [device onboarding extensions](onboarding_extensions.md).

!!! warn
    This is the original onboarding extensions.  The next section covers how to extend the new framework.

## Extending SSoT jobs (Sync Devices From Network, and Sync Network Data From Network)

Extending the platform support for the SSoT specific jobs should be accomplished with adding a yaml file that defines commands, jdiff, jmespaths, and post_processors. A PR into this library is welcomed, but this app exposes the Nautobot core datasource capabilities to be able to load in overrides from a Git repository.

### Adding Platform/OS Support

New platform support should be simplified in this framework, by providing a YAML file.

The format of these YAML files are and how to extend this application is covered in [App YAML Overrides](../user/app_yaml_overrides.md).

### Passing Custom Nornir Connection Options

Device Onboarding 4.0 uses Netmiko as the automation engine that queries the devices for information; more specifically, nornir-netmiko. To extend the device onboarding app to pass `extras` to the connection options the following can be added to `nautobot_plugin_nornir` `PLUGIN_CONFIG`.

```python
PLUGINS_CONFIG = {
    "nautobot_device_onboarding": {},
    "nautobot_plugin_nornir": {
        "nornir_settings": {
            "... omitted ..."},
        "connection_options": {
            "netmiko": {
                "extras": {  # <==== passed into the connection setup.
                    "fast_cli": False,
                    "read_timeout_override": 30,
                },
            },
        },
    },
}
```

When the on-demand inventory is created for the `Sync Device from Network` job, the extras in the `netmiko` connection dictionary are added to the connection setup.
