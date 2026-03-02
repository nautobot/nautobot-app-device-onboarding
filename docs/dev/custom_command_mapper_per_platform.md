# Custom Command Mapper Per Device Platform

This document explains how the Device Onboarding app selects command mapper YAML files and how to configure **per-platform custom command mappers** (e.g., different YAML files for Juniper MX204 vs MX205).

## Background

The app uses command mapper YAML files to define what CLI commands to run on a device and how to parse the output. By default, all Juniper Junos devices share a single `juniper_junos.yml` mapper. However, some device models have different command syntax and require separate mapper files.

## How Command Mapper Selection Works

### File Loading

`load_command_mappers_from_dir()` in `nautobot_device_onboarding/nornir_plays/transform.py` loads all `.yml` files from a directory and uses the **filename (without extension)** as the dictionary key:

```python
network_driver = filename.split(".")[0]  # "juniper_junos_mx204.yml" → "juniper_junos_mx204"
command_mappers_result[network_driver] = command_mappers_data
```

### Merging (Defaults + Git Repo)

`add_platform_parsing_info()` merges built-in mappers with Git repo mappers. Git repo files **take precedence**:

```python
merged_command_mappers = {**command_mapper_defaults, **command_mappers_repo_path}
```

### Lookup Key: `task.host.platform`

The command mapper is looked up by `task.host.platform` in `netmiko_send_commands()` (`command_getter.py`):

```python
command_getter_yaml_data[task.host.platform]
```

### How `task.host.platform` Is Set (Two Job Paths)

| Job | Inventory Plugin | `task.host.platform` set to | Source |
|---|---|---|---|
| `sync_network_data` | `NautobotORMInventory` | `device.platform.network_driver` | `nautobot_plugin_nornir/.../nautobot_orm.py` line 248 |
| `sync_devices` | `EmptyInventory` + `_set_inventory()` | `platform.network_driver_mappings.get("netmiko")` | `inventory_creator.py` line 44 |

**Key difference**: `sync_network_data` uses the Platform's `network_driver` field directly, while `sync_devices` uses the netmiko-specific mapping from `network_driver_mappings`.

### Connection Options Are Decoupled

In `NautobotORMInventory`, the SSH connection uses the library-specific driver from `network_driver_mappings`, not `host.platform`:

```python
# host.platform = device.platform.network_driver  → for command mapper lookup
# connection_options[driver].platform = network_driver_mappings[driver]  → for SSH
```

## Solution: Per-Platform Custom Mappers (No Code Changes)

To support different command mappers for different device models (e.g., MX204 vs MX205), use the Netmiko `CLASS_MAPPER` trick combined with the `NETWORK_DRIVERS` Nautobot setting.

### Step 1: `nautobot_config.py`

Register custom Netmiko device types and define network driver mappings:

```python
# Register custom Netmiko device types that alias to juniper_junos
from netmiko.ssh_dispatcher import CLASS_MAPPER
CLASS_MAPPER['juniper_junos_mx204'] = CLASS_MAPPER['juniper_junos']
CLASS_MAPPER['juniper_junos_mx205'] = CLASS_MAPPER['juniper_junos']

# Map the custom network_driver names to their netmiko driver names
# This makes platform.network_driver_mappings.get("netmiko") return the custom name
NETWORK_DRIVERS = {
    "netmiko": {
        "juniper_junos_mx204": "juniper_junos_mx204",
        "juniper_junos_mx205": "juniper_junos_mx205",
    },
}
```

**Why this works:**
- `CLASS_MAPPER` makes Netmiko accept `juniper_junos_mx204` as a valid device type (aliased to the `juniper_junos` SSH class).
- `NETWORK_DRIVERS` makes `platform.network_driver_mappings.get("netmiko")` return `"juniper_junos_mx204"` instead of `None`.

### Step 2: Nautobot Platform Configuration

Create separate Platforms for each device model:

| Field | Platform 1 | Platform 2 |
|---|---|---|
| **Platform Name** | `juniper_junos_mx204` | `juniper_junos_mx205` |
| **Network Driver** | `juniper_junos_mx204` | `juniper_junos_mx205` |
| **NAPALM Driver** | `junos` | `junos` |
| **Manufacturer** | Juniper | Juniper |

The netmiko mapping will automatically show `juniper_junos_mx204` / `juniper_junos_mx205` thanks to the `NETWORK_DRIVERS` setting.

### Step 3: Git Repo Command Mapper Files

Place your custom YAML files in the Git repo's `onboarding_command_mappers/` folder:

```
onboarding_command_mappers/
├── juniper_junos_mx204.yml   # MX204-specific commands
└── juniper_junos_mx205.yml   # MX205-specific commands
```

### Step 4: Device Assignment

Assign each device to the appropriate Platform based on its model.

## End-to-End Flow

### `sync_devices` Job (MX204 example)

1. `_set_inventory()`: `platform.network_driver_mappings.get("netmiko")` → `"juniper_junos_mx204"` (via `NETWORK_DRIVERS`)
2. `Host.platform` = `"juniper_junos_mx204"` → command mapper lookup matches `juniper_junos_mx204.yml` ✅
3. Netmiko SSH: receives `"juniper_junos_mx204"` → `CLASS_MAPPER` maps to `juniper_junos` SSH class ✅

### `sync_network_data` Job (MX204 example)

1. `NautobotORMInventory`: `device.platform.network_driver` → `"juniper_junos_mx204"`
2. `Host.platform` = `"juniper_junos_mx204"` → command mapper lookup matches `juniper_junos_mx204.yml` ✅
3. `connection_options["netmiko"].platform` = `network_driver_mappings["netmiko"]` → `"juniper_junos_mx204"` → `CLASS_MAPPER` maps to `juniper_junos` SSH class ✅

## Applying to Other Vendors

This pattern works for any vendor. For example, to add a custom `h3c_comware` driver:

```python
# nautobot_config.py
from netmiko.ssh_dispatcher import CLASS_MAPPER
CLASS_MAPPER['h3c_comware'] = CLASS_MAPPER['hp_comware']

NETWORK_DRIVERS = {
    "netmiko": {
        "h3c_comware": "h3c_comware",
    },
}
```

Then create a Platform with `network_driver = "h3c_comware"` and a command mapper file `h3c_comware.yml`.
