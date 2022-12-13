# Contributing to the App

Pull requests are welcome and automatically built and tested against multiple version of Python and multiple version of Nautobot through GitHub Actions.

The project is packaged with a light [development environment](dev_environment.md) based on `docker-compose` to help with the local development of the project and to run tests.

The project is following Network to Code software development guidelines and is leveraging the following:

- Black, Pylint, Bandit, flake8, and pydocstyle for Python linting and formatting.
- Django unit test to ensure the plugin is working properly.

Documentation is built using [mkdocs](https://www.mkdocs.org/). The [Docker based development environment](dev_environment.md#docker-development-environment) automatically starts a container hosting a live version of the documentation website on [http://localhost:8001](http://localhost:8001) that auto-refreshes when you make any changes to your local files.

## Branching Policy

Please fork the release and add a new branch to your fork. Make changes to your branch in your fork and submit PRs from there.

## Release Policy

New versions are released as bug fixes and features are introduced. We will make sure to release new versions to support the latest Nautobot versions as necessary.
