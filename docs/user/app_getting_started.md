# Getting Started with the App

A step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## Prequisites

You will need:
- a device reachable from the Nautobot instance
    - this can an IP or DNS name
- the device's credentials
- to create a site in Nautobot

The device must be reachable from the Nautobot and Nautobot worker instances (usually if one can reach it, the other can as well). You can test reachability directly with ssh. Since the plugin uses Napalm and Netmiko, they could also be used for a more accurate test.

Sites are the only other Nautobot prerequisite for the plugin to onboard a device. 

## Onboarding a Device

Navigate to the Device Onboarding plugin: Plugins > Onboarding Tasks. Clicking the plus button takes you directly to the Onboarding form. 

[!Device Onboarding Navigation Menu](../images/menu.png)

From the Onboarding Tasks view, click the **add** button in the top right.

[!In the Onboarding Tasks view, click the add button](../images/onboarding_tasks_full_view.png)

This will bring you to the *Add a new onboarding task* form. 

[!Onboarding task form](../images/single_device_form.png)

Fill in the form with your device's data, then click the create button to start onboarding the device.

[!Onboarding form filled in](../images/onboarding_form_filled.png)

The Nautobot worker will initiate an onboarding task and will reach out to the device and attempt to onboard it.



