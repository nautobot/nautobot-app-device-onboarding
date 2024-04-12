# Extending the App

Extending the application is welcome, however it is best to open an issue first, to ensure that a PR would be accepted and makes sense in terms of features and design.

## Customizing Onboarding Behavior With Extensions

This plugin provides methods to customize onboarding behavior. By creating onboarding extensions, it is possible to onboard switch stacks, HA pairs and perform other customizations.

Please see the dedicated FAQ for [device onboarding extensions](onboarding_extensions.md).

!!! warn
    This is the legacy onboarding extensions.  The next section covers how to extend the new framework.

## Extending SSoT jobs (Sync Devices, and Sync Network Data)

Extending the platform support for the SSoT specific jobs should be accomplished with adding a yaml file that defines commands, jdiff jmespaths, and post_processors. A PR into this library is welcomed, but this app exposes the Nautobot core datasource capabilities to be able to load in overrides from a Git repository.

### Adding Platform/OS Support

New platform support should be simplified in this framework, by providing a YAML file.

TODO:
