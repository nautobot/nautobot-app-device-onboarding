# Upgrading the App

Here you will find any steps necessary to upgrade the App in your Nautobot environment.

## Upgrade Guide

When a new release comes out it may be necessary to run a migration of the database to account for any changes in the data models used by this app. Execute the command `nautobot-server post_upgrade` within the runtime environment of your Nautobot installation after updating the `nautobot-device-onboarding` package via `pip`.
