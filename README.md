# Nautobot Device Onboarding

<p align="center">
  <img src="https://raw.githubusercontent.com/nautobot/nautobot-app-device-onboarding/develop/docs/images/icon-DeviceOnboarding.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/nautobot/nautobot-app-device-onboarding/actions"><img src="https://github.com/nautobot/nautobot-app-device-onboarding/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://docs.nautobot.com/projects/device-onboarding/en/latest/"><img src="https://readthedocs.org/projects/nautobot-plugin-device-onboarding/badge/"></a>
  <a href="https://pypi.org/project/nautobot-device-onboarding/"><img src="https://img.shields.io/pypi/v/nautobot-device-onboarding"></a>
  <a href="https://pypi.org/project/nautobot-device-onboarding/"><img src="https://img.shields.io/pypi/dm/nautobot-device-onboarding"></a>
  <br>
  An <a href="https://networktocode.com/nautobot-apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

The `nautobot-device-onboarding` plugin is using the [netmiko](https://github.com/ktbyers/netmiko) and [NAPALM](https://napalm.readthedocs.io/en/latest/) libraries to simplify the onboarding process of a new device into Nautobot down to, in many cases, an *IP Address* and a *Location*. In some cases, the user may also have to specify a specific *Device Platform* and *Device Port*.

Regardless, the Onboarding App greatly simplifies the onboarding process by allowing the user to specify a small amount of info and having the app populate a much larger amount of device data in Nautobot.

### Support Matrix (Sync Devices From Network)


|     Data Attribute      | Cisco IOS          | Cisco XE           | Cisco NXOS         | Cisco XR | Cisco WLC          | Juniper Junos      | Arista EOS         | F5  | HP Comware | Palo Alto Panos | Aruba AOSCX |
| ----------------------  | :-: | :-: |  :-:  |  :-:  |  :-:  |  :-:  | :-: | :-: | :-: | :-: | :-: |
| Hostname                | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Platform                | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Manufacturer            | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Serial Number           | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Device Type             | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Mgmt Interface          | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |
| Mgmt IP Address         | ✅ | ✅ | ✅ | 🧪 | ✅ | ✅ | ✅ | 🧪 | 🧪 | 🧪 | 🧪 |


### Support Matrix (Sync Data From Network)

|     Interfaces          | Cisco IOS          | Cisco XE           | Cisco NXOS         | Cisco XR | Cisco WLC          | Juniper Junos      | Arista EOS         | F5  |
| ----------------------- | :----------------: |  :--------------:  |  :--------------:  | :-: | :--------------:  |  :--------------:  |  :--------------:  | :-: |
| Name           | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| IP Address     | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Type           | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| MTU            | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Description    | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Mac Address    | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Link Status    | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| 802.1Q mode    | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Lag Member     | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Vrf Membership | ✅ | ✅ | ✅ | 🧪 | ❌ | ✅ | ✅ | ❌ |
| Software Version | ✅ | ✅ | ✅  | 🧪 | ❌ | ✅ | ✅ | ❌ |

|     VLANS          | Cisco IOS          | Cisco XE           | Cisco XR           | Cisco NXOS         | Cisco WLC          | Juniper Junos      | Arista EOS         | F5  |
| ----------------------- | :----------------: |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  | :-: |
| Untagged VLANs       | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Tagged VLANs        | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |

|     Cabling          | Cisco IOS          | Cisco XE           | Cisco XR           | Cisco NXOS         | Cisco WLC          | Juniper Junos      | Arista EOS         | F5  |
| ----------------------- | :----------------: |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  |  :--------------:  | :-: |
|  Terminations A      | 🧪 | 🧪 | ❌ | 🧪 | ❌ | 🧪 | ❌ | ❌ |
|  Terminations B      | 🧪 | 🧪 | ❌ | 🧪 | ❌ | 🧪 | ❌ | ❌ |

| Legend |
| :---- |
| ✅ - Supported and stable. |
| ❌ - No current support. |
| 🧪 - Supported, but has limited testing. |

### Screenshots

Device Onboarding is a Job that allows you to provide a few required pieces of information and onboard the device.

![job input](https://raw.githubusercontent.com/nautobot/nautobot-app-device-onboarding/develop/docs/images/sync_devices_inputs.png)

## Try it out!

This App is installed in the Nautobot Community Sandbox found over at [demo.nautobot.com](https://demo.nautobot.com/)!

> For a full list of all the available always-on sandbox environments, head over to the main page on [networktocode.com](https://www.networktocode.com/nautobot/sandbox-environments/).

## Documentation

Full web-based HTML documentation for this app can be found over on the [Nautobot Docs](https://docs.nautobot.com/) website:

- [User Guide](https://docs.nautobot.com/projects/device-onboarding/en/latest/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://docs.nautobot.com/projects/device-onboarding/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://docs.nautobot.com/projects/device-onboarding/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://docs.nautobot.com/projects/device-onboarding/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://docs.nautobot.com/projects/device-onboarding/en/latest/user/faq/).

### Contributing to the Docs

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/nautobot/nautobot-app-device-onboarding/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully generated documentation site, you can build it with [mkdocs](https://www.mkdocs.org/). A container hosting the docs will be started using the invoke commands (details in the [Development Environment Guide](https://docs.nautobot.com/projects/device-onboarding/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). As your changes are saved, the live docs will be automatically reloaded.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://docs.nautobot.com/projects/device-onboarding/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
