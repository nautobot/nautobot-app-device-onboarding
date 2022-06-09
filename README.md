# Nautobot Device Onboarding

<p align="center">
  <img src="docs/images/icon-DeviceOnboarding.png" height="200px">
  <br>
  <a href="https://github.com/nautobot/nautobot-plugin-device-onboarding/actions"><img src="https://github.com/nautobot/nautobot-plugin-device-onboarding/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://pypi.org/project/nautobot-device-onboarding/"><img src="https://img.shields.io/pypi/v/nautobot-device-onboarding"></a>
  <a href="https://pypi.org/project/nautobot-device-onboarding/"><img src="https://img.shields.io/pypi/dm/nautobot-device-onboarding"></a>
  <br>
  A plugin for Nautobot to easily onboard new devices.
</p>

## Overview

`nautobot-device-onboarding` is using [Netmiko](https://github.com/ktbyers/netmiko) and [NAPALM](https://napalm.readthedocs.io/en/latest/) to simplify the onboarding process of a new device into Nautobot down to, in many cases, an IP Address and a site. In some cases, the user may also have to specify a specific Device Platform and Device Port.

Regardless, the Onboarding Plugin greatly simplifies the onboarding process
by allowing the user to specify a small amount of info and having the plugin populate a much larger amount of device data in Nautobot.

### Screenshots

![](docs/images/ss_onboarding_tasks_view.png)

## Try it out!

This App is installed in the Nautobot Community Sandbox found over at [demo.nautobot.com](https://demo.nautobot.com/)!

> For a full list of all the available always-on sandbox environments, head over to the main page on [networktocode.com](https://www.networktocode.com/nautobot/sandbox-environments/).

## Documentation

Full web-based HTML documentation for this app can be found over on the [Nautobot Docs](https://nbdocs.pages.dev/) website:

- [User Guide](https://nbdocs.pages.dev/apps/nautobot-plugin-device-onboarding/user/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://nbdocs.pages.dev/apps/nautobot-plugin-device-onboarding/admin/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://nbdocs.pages.dev/apps/nautobot-plugin-device-onboarding/dev/) - Extending the App, API Reference, Contribution Guide.
- [Release Notes / Changelog](https://nbdocs.pages.dev/apps/nautobot-plugin-device-onboarding/admin/admin_release_notes.html)
- [Frequently Asked Questions](https://nbdocs.pages.dev/apps/nautobot-plugin-device-onboarding/user/app_faq.html)

### Contributing to the Docs

You can find all the sources for the App documentation under the [docs](docs/) folder in this repository. Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](docs/user/app_faq.md) first. Feel free to also swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode), sign up [here](http://slack.networktocode.com/).
