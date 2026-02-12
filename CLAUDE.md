# Nautobot Device Onboarding Plugin

## Current Goal

Add module/line card support to device onboarding via DiffSync integration.

## Module Support Implementation Plan

### 1. DiffSync Model

- File: `diffsync/models/sync_network_data_models.py`
- Create: `SyncNetworkDataModule` class
- Model: `nautobot.dcim.models.Module`
- Identifiers: `device__name`, `name`, `module_bay`
- Attributes: `type`, `description`, `status__name`, `serial`, `asset_tag`

### 2. Adapters

- File: `diffsync/adapters/sync_network_data_adapters.py`
- Add `module = SyncNetworkDataModule` to both adapters
- Include `"module"` in `top_level` lists
- Implement `load_modules()` in both adapters

### 3. Command Mapper

- File: `nornir_plays/parsers/command_mappers/cisco_ios.yml`
- Add module discovery commands (e.g., `show module`, `show inventory`)
- Define TextFSM/TTP templates for parsing
- Add to `sync_network_data` section

### 4. Schema Extension

- File: `nornir_plays/schemas.py`
- Extend `NETWORK_DATA_SCHEMA` with modules section
- Validate module data structure

### 5. Command Getter

- File: `nornir_plays/command_getter.py`
- Extend `_get_commands_to_run` to include module commands
- Update `netmiko_send_commands` to handle module data

### 6. Job Flag (Optional)

- File: `jobs.py` (SSOTSyncNetworkData)
- Add `sync_modules = BooleanVar()` if needed
- Guard command mapper and adapter loading

### 7. Tests

- Files: `tests/test_jobs.py`, `tests/test_sync_network_data_adapters.py`
- Mock module command output
- Test DiffSync create/update for Module objects

## Key Files

``` text
diffsync/
├── models/sync_network_data_models.py    # Add SyncNetworkDataModule
└── adapters/sync_network_data_adapters.py # Add module loading

nornir_plays/
├── command_getter.py                      # Extend command execution
├── schemas.py                             # Add module schema
└── parsers/command_mappers/
    └── cisco_ios.yml                      # Add module commands

jobs.py                                    # Optional: sync_modules flag
tests/                                     # Add module tests
```

## DiffSync Pattern

```python
# Model structure
class SyncNetworkDataModule(DiffSyncModel):
    _model = Module
    _identifiers = ("device__name", "name")
    _attributes = ("type", "description", "status__name", "serial")

    @classmethod
    def create(cls, diffsync, ids, attrs):
        # Module.objects.get_or_create(...)

    def update(self, attrs):
        # Update existing module
```

## Network Commands

- Cisco IOS: `show module`, `show inventory`
- Cisco NXOS: `show module`, `show inventory`
- Parse with TextFSM or TTP templates

## Testing Strategy

- Mock Netmiko command output with module data
- Verify DiffSync creates Module objects in Nautobot
- Test adapter loading with/without modules present
