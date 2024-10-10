# Architecture Decision Records

The intention is to document deviations from a standard Model View Controller (MVC) design. And other general Application decisions.

## Handling the Nornir Inventory

In order for Nornir to function an inventory is created. There are multiple supported inventory sources that fit many needs; however there is a unique requirement that this plugin is trying to solve. The problem is specifically around the first SSoT job (Sync Devices from Network); how can we create an inventory when there is no source "yet"? Our solution to this problem is to generate a empty inventory, and then process the ip addresses from the job form to create a inventory in an on demand fashion and inject the credentials into the inventory based on the secrets group selected.

For the general application constraint for this ADR see the [Credentials Section](../user/app_getting_started.md#device-credentials-functionality).
