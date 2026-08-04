# Per-Platform Netmiko Enable Mode

## Purpose

Allow the SSoT onboarding jobs to enter Netmiko enable mode only for explicitly selected logical platforms. This lets two groups of Cisco devices use different privilege behavior while retaining the same underlying Cisco IOS Netmiko implementation.

## Scope

Included:

- `Sync Devices From Network`.
- `Sync Network Data From Network`.
- Configuration validation, unit tests, and user documentation.

Excluded:

- The original NAPALM onboarding job.
- Changes to secret storage or secret-provider behavior.
- A Nautobot UI field, Config Context setting, or command-mapper YAML metadata.

## Configuration

Add this default to `NautobotDeviceOnboardingConfig.default_settings`:

```python
"netmiko_enable_mode_platforms": [],
```

Operators configure logical platform/network-driver identifiers in `nautobot_config.py`:

```python
PLUGINS_CONFIG = {
    "nautobot_device_onboarding": {
        "netmiko_enable_mode_platforms": [
            "cisco_platform_1",
        ],
    },
}
```

The generated app configuration schema must describe this setting as a list of strings.

## Behavior

The shared `netmiko_send_commands()` task resolves enable mode from `task.host.platform`, the logical platform identifier used to select the command mapper.

- If `netmiko_enable_mode_platforms` is omitted or empty, `enable=False` for every platform.
- If it is populated, `enable=True` only when `task.host.platform` is in the list.
- Every other platform uses `enable=False`.
- The resolved Boolean is passed as the `enable` argument to every `netmiko_send_command()` call for that host.

This replaces the existing unconditional `enable=True` behavior.

Example result:

| Logical platform | Configured list | Netmiko `enable` |
| --- | --- | --- |
| `cisco_platform_1` | contains `cisco_platform_1` | `True` |
| `cisco_platform_2` | contains only `cisco_platform_1` | `False` |
| `juniper_junos` | contains only `cisco_platform_1` | `False` |

## Custom Cisco Platforms

To separate Cisco groups, create separate Nautobot Platform records whose `network_driver` values are `cisco_platform_1` and `cisco_platform_2`. Each needs a matching command mapper. Configure the custom Netmiko aliases as documented in `docs/dev/custom_command_mapper_per_platform.md` so both SSoT inventory paths use the same logical platform identifier while Netmiko dispatches to the Cisco IOS implementation.

The enable-mode allow-list is deliberately based on this logical platform identifier, not on the underlying Netmiko driver. If it used the Netmiko driver, both groups would resolve to `cisco_ios` and could not have distinct behavior.

## Secrets and Error Handling

The existing `Username`, `Password`, and optional `Secret` credential flow remains unchanged. The `Secret` remains available as Netmiko's enable password, but it is used only when a listed platform invokes enable mode.

An empty list is valid. A listed identifier that does not match any selected device platform is harmless: no device enables mode for that entry. Invalid configuration types are rejected by the app configuration schema before jobs run.

## Pre-Implementation Synchronization and Baseline Verification

Before changing application code for this feature:

1. Fetch the latest `upstream` repository state.
2. Merge the latest `upstream/develop` into the feature branch.
3. Resolve merge conflicts without discarding the approved design document or unrelated user changes.
4. Run the full project test suite with `invoke tests` against the merged branch.
5. Begin implementation only after the merge completes and the baseline test suite succeeds.

If the merge or baseline test suite fails, stop feature implementation and report the failure. Diagnose any failure before proposing a repair; do not attribute a failure to this feature before code for the feature exists.

## Tests

Add focused tests around the shared command task to assert the `enable` argument passed to `netmiko_send_command`:

- Empty/default configuration sends `enable=False` for Cisco and Juniper hosts.
- `cisco_platform_1` in the allow-list sends `enable=True`.
- Unlisted `cisco_platform_2` sends `enable=False`.
- Existing enable-secret parsing and inventory tests remain unchanged and pass.

When an integration environment needs device credentials, use the ignored `development/creds.env` file. Do not add actual credentials to the repository or use that file to store the platform-policy configuration.

## Documentation

Update the installation/configuration documentation and enable-secret guidance to explain:

- The new `netmiko_enable_mode_platforms` setting.
- Default-disabled behavior.
- A Cisco/Juniper example.
- How separate logical Cisco platforms allow different enable-mode policies.

## Acceptance Criteria

- Both SSoT jobs use the same per-platform enable-mode decision.
- An unconfigured app never calls Netmiko enable mode.
- A listed logical platform calls Netmiko enable mode for its commands.
- Two custom Cisco logical platforms can have opposite enable-mode behavior.
- Enable-password handling is unchanged.
- The original NAPALM job behavior is unchanged.
