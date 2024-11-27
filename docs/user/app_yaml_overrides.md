# Extending and Overriding Platform YAML Files

One element of the new SSoT based jobs this app exposes is the attempt to create a framework that allows the definition of each platforms dependencies in a YAML format. 

This App provides sane defaults that have been tested, the command mapper files are located in the source code under `command_mappers`. There is potential for these sane defaults to not work in a given environment; alternatively you may want to add additional platform support in your deployment. These are the two main use cases to utilize the datasource feature this app exposes.

!!! info
    To avoid overly complicating the merge logic, the App will always prefer the platform specific YAML file loaded in from the git repository.

!!! warn
    Partial YAML file merging is not supported. Meaning you can't only overload `sync_devices` definition and inherit `sync_network_data` definition.


## File Name
The YAML file names must be named `<network_driver>.yml`.  Where network_driver must exist in the netutils mapping exposed from Nautobot core.

## File Placement
The override files can either be placed directly into the python plugin command mappers directory (by default: `/opt/nautobot/lib64/python<python version>/site-packages/nautobot_device_onboarding/command_mappers/`) or by using a Git Datasources.

### Git Datasources

File structure:
```bash
.
├── README.md
└── onboarding_command_mappers
    └── <network_driver>.yml
```

When loading from a Git Repository this App is expecting a root directory called `onboarding_command_mappers`. Each of the platform YAML files are then located in this directory. The YAML file names must be named `<network_driver>.yml`.  Where network_driver must exist in the netutils mapping exposed from Nautobot core. If your platform does not appear in the netutils mapping, you can override or add your platform via the admin > config panel. 

To quickly get a list of network driver mappings in core, run:

```python
from nautobot.dcim.utils import get_all_network_driver_mappings

sorted(list(get_all_network_driver_mappings().keys()))
```

### Setting up the Git Repository

1. Extensibility -> Git Repositories
2. Create a new repository, most importantly selecting the `Provides` of `Network Sync Job Command Mappers`

## File Format
There are only a few components to the file and they're described below:

- `ssot job name` - Name of the job to define the commands and metadata needed for that job. (choices: `sync_devices` or `sync_network_data`)
- `root key data name` - Is fully defined in the schema definition.
- `commands` - List of commands to execute in order to get the required data.
- `command` - Actual `show` command to execute.
- `parser` - Whether to use a parser (textfsm, pyats, ttp, etc) alternatives are `none` which can be used if the platform supports some other method to return structured data. E.g. (`| display json`) or an equivalent, or `raw` which allows a command to be run and **NO** jmespath extraction to take place, this is useful when simple text extractions via the `post_processor` are good enough.
- `jpath` - The jmespath (specifically jdiffs implementation) to extract the data from the parsed json returned from parser. If `raw` is used as the `parser` then `jpath` should also be set to `raw` which will be the dictionary key to extract the raw command data.
- `post_processor` - Jinja2 capable code to further transform the returned data post jpath extraction.
- `iterable_type` - A optional value to force a parsed result to a specific data type.

As an example:

```yaml
---
sync_devices:
  hostname:
    commands:
      - command: "show version"
        parser: "textfsm"
        jpath: "[*].hostname"
        post_processor: "{{ obj[0] | upper }}"
..omitted..
```

If there is only one command that needs to be run, the code base also accepts that in a dictionary format.

```yaml
---
sync_devices:
  hostname:
    commands:
      command: "show version"
      parser: "textfsm"
      jpath: "[*].hostname"
      post_processor: "{{ obj[0] | upper }}"
..omitted..
```
