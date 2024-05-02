# Extending and Overriding Platform YAML Files

One element of the new SSoT based jobs this app exposes; is the attempt to create a framework that allows the definition of each platforms dependencies in a YAML format. 

## File Format
There are only a few components to the file and they're described below:

- `ssot job name` - Name of the job to define the commands and metadata needed for that job. (choices: `sync_devices` or `sync_network_data`)
- `root key data name` - Is fully defined in the schema definition.
- `commands` - List of commands to execute in order to get the required data.
- `command` - Actual `show` command to execute.
- `parser` - Whether to use a parser (textfsm, pyats, ttp, etc) alternatively `no` can be used if the platform supports some other method to return structured data. E.g. (`| display json`) or an equivalent.
- `jpath` - The jmespath (specifically jdiffs implementation) to extract the data from the parsed json returned from parser.
- `post_processor` - Jinja2 capable code to further transform the returned data post jpath extraction.

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

## Using Datasource to Override

This App provides sane defaults that have been tested, the files are located in the source code under `command_mappers`. There is potential for these sane defaults to not work in a given environment; alternatively you may want to add additional platform support in your deployment. These are the two main use cases to utilize the datasource feature this app exposes.

!!! info
    To avoid overly complicating the merge logic, the App will always prefer the platform specific YAML file loaded in from the git repository.

!!! warn
    Partial YAML file merging is not supported. Meaning you can't only overload `sync_devices` definition and inherit `sync_network_data` definition.

### Properly Formatting Git Repository

When loading from a Git Repository this App is expecting a root directory called `onboarding_command_mappers`. Each of the platform YAML files are then located in this directory. The YAML file names must be named `<network_driver>.yml`.  Where network_driver must exist in the netutils mapping exposed from Nautobot core.

To quickly get a list run:

```python
from nautobot.dcim.utils import get_all_network_driver_mappings

sorted(list(get_all_network_driver_mappings().keys()))
```

### Setting up the Git Repository

1. Extensibility -> Git Repositories
2. Create a new repository, most importantly selecting the `Provides` of `Network Sync Job Command Mappers`
