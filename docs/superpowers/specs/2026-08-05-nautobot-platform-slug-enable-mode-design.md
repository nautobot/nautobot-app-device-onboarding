# Nautobot Platform Slug Enable-Mode Policy

## Purpose

Make `netmiko_enable_mode_platforms` select devices by their Nautobot Platform
slug, rather than by the Netmiko driver. This permits multiple Nautobot
Platforms, such as `cisco_2960` and `cisco_3850`, to share `cisco_ios` for SSH
while having different enable-mode policies.

## Scope

Included:

- `Sync Devices From Network` and `Sync Network Data From Network`.
- The `netmiko_enable_mode_platforms` allow-list, enable-mode log message,
  tests, and documentation.

Excluded:

- Changes to Netmiko driver selection, command-mapper selection, or secrets.
- The original NAPALM onboarding job.
- A configuration UI, Config Context setting, or migration of existing values.

## Configuration

The existing optional setting remains a list of strings:

```python
PLUGINS_CONFIG = {
    "nautobot_device_onboarding": {
        "netmiko_enable_mode_platforms": ["cisco_2960"],
    },
}
```

Each value is a Nautobot Platform `slug`. The list remains opt-in: when it is
missing or empty, `enable=False` for every device. When it contains
`cisco_2960`, only devices assigned that Nautobot Platform use `enable=True`.

## Design

The policy key is intentionally separate from `task.host.platform`.
`task.host.platform` continues to hold the network-driver value used to select
command mappers and establish the Netmiko connection. In the reported case it
is `cisco_ios`; changing it would alter established command-mapper and
transport behavior.

The shared command task resolves a Nautobot Platform slug as follows:

1. For `Sync Devices From Network`, `_set_inventory()` saves the explicitly
   selected Platform slug in the constructed Nornir host data before using its
   `network_driver_mappings["netmiko"]` value as the host platform.
2. For `Sync Network Data From Network`, the Nautobot ORM inventory already
   stores the Device object in `task.host.data["obj"]`; the task reads
   `device.platform.slug` from that object.
3. The allow-list comparison and info-level log use this resolved slug.

If a `Sync Devices From Network` run uses auto-detection and has no explicitly
selected Platform, there is no Nautobot Platform slug to match. Its enable
mode is therefore `False`. This is the safe default and preserves opt-in
behavior.

For a device on Platform `cisco_2960` with Netmiko mapping `cisco_ios`, the
log will state `Nautobot Platform 'cisco_2960' enable mode: enabled` when
`cisco_2960` is listed. It will not report the Netmiko driver as the policy
key.

## Error Handling

Missing platform metadata is not an error. It resolves to disabled enable
mode, does not trigger a database lookup, and does not expose credentials.
Existing validation of command-mapper/network-driver values remains unchanged.

## Tests

Focused tests will verify:

- a selected `cisco_2960` Platform with Netmiko mapping `cisco_ios` sends
  `enable=True` when `cisco_2960` is listed;
- another Platform sharing `cisco_ios` sends `enable=False` when unlisted;
- a Sync Network Data host resolves its slug from `task.host.data["obj"]`;
- an auto-detected Sync Devices host without a Nautobot Platform sends
  `enable=False`;
- the info log identifies the Nautobot Platform slug and resolved state.

## Documentation

Update the existing configuration and enable-secret guidance so it states
unambiguously that allow-list entries are Nautobot Platform slugs. Documentation
will distinguish this policy key from the Platform's Netmiko network-driver
mapping and retain the default-disabled explanation.

## Acceptance Criteria

- `netmiko_enable_mode_platforms=["cisco_2960"]` enables Netmiko mode for a
  device on Nautobot Platform `cisco_2960`, even when its Netmiko mapping is
  `cisco_ios`.
- A second Nautobot Platform sharing the same `cisco_ios` mapping remains
  disabled unless its own slug is listed.
- Both SSoT jobs use Nautobot Platform slugs for the decision.
- Auto-detected Sync Devices hosts without an assigned Platform remain
  disabled.
- Command-mapper selection, Netmiko driver selection, and secrets behavior are
  unchanged.
