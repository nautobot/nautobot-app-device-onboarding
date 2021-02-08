"""Tasks for use with Invoke.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from invoke import task

PYTHON_VER = os.getenv("PYTHON_VER", "3.7")
NAUTOBOT_VER = os.getenv("NAUTOBOT_VER", "main")

# Name of the docker image/container
NAME = os.getenv("IMAGE_NAME", "nautobot-device-onboarding")
PWD = os.getcwd()

COMPOSE_FILE = "development/docker-compose.yml"
BUILD_NAME = "nautobot_device_onboarding"


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task
def build(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER, nocache=False, forcerm=False):
    """Build all docker images.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
        nocache (bool): Do not use cache when building the image
        forcerm (bool): Always remove intermediate containers
    """
    command = "build"

    if nocache:
        command += " --no-cache"
    if forcerm:
        command += " --force-rm"

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} {command}",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Start Nautobot and its dependencies in debug mode.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Starting Nautobot .. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


@task
def start(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Start Nautobot and its dependencies in detached mode.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Starting Nautobot in detached mode.. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up -d",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


@task
def stop(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Stop Nautobot and its dependencies.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Stopping Nautobot .. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


@task
def destroy(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Destroy all containers and volumes.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )
    context.run(
        f"docker volume rm -f {BUILD_NAME}_pgdata_nautobot_device_onboarding",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Launch a nbshell session.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot nautobot-server nbshell",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def cli(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Launch a bash shell inside the running Nautobot container.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot bash",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def create_user(context, user="admin", nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Create a new user in django (default: admin), will prompt for password.

    Args:
        context (obj): Used to run specific commands
        user (str): name of the superuser to create
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot nautobot-server createsuperuser --username {user}",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def makemigrations(context, name="", nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run Make Migration in Django.

    Args:
        context (obj): Used to run specific commands
        name (str): Name of the migration to be created
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up -d postgres",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )

    if name:
        context.run(
            f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot nautobot-server makemigrations --name {name}",
            env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        )
    else:
        context.run(
            f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot nautobot-server makemigrations",
            env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        )

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# TESTS / LINTING
# ------------------------------------------------------------------------------
@task
def unittest(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run Django unit tests for the plugin.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f'{docker} sh -c "nautobot-server test nautobot_device_onboarding"',
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def pylint(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run pylint code analysis.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    # We exclude the /migrations/ directory since it is autogenerated code
    context.run(
        f"{docker} sh -c \"cd /source && find . -name '*.py' -not -path '*/migrations/*' | xargs pylint\"",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def black(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run black to check that Python files adhere to its style standards.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f'{docker} sh -c "cd /source && black --check --diff ."',
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def blacken(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run black to format Python files to adhere to its style standards.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f'{docker} sh -c "cd /source && black ."',
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def pydocstyle(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run pydocstyle to validate docstring formatting adheres to NTC defined standards.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    # We exclude the /migrations/ directory since it is autogenerated code
    context.run(
        f"{docker} sh -c \"cd /source && find . -name '*.py' -not -path '*/migrations/*' | xargs pydocstyle\"",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def flake8(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """This will run flake8 for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f"{docker} sh -c \"cd /source && find . -name '*.py' | xargs flake8\"",
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def yamllint(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f'{docker} sh -c "cd /source && yamllint ."',
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def bandit(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run bandit to validate basic static code security analysis.

    Args:
        context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run nautobot"
    context.run(
        f'{docker} sh -c "cd /source && bandit --configfile .bandit.yml --recursive ./"',
        env={"NAUTOBOT_VER": nautobot_ver, "PYTHON_VER": python_ver},
        pty=True,
    )


@task
def tests(context, nautobot_ver=NAUTOBOT_VER, python_ver=PYTHON_VER):
    """Run all tests for this plugin.

    Args:
         context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    # Sorted loosely from fastest to slowest
    print("Running black...")
    black(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    print("Running yamllint...")
    yamllint(context, NAME, python_ver)
    print("Running bandit...")
    bandit(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    # print("Running pydocstyle...")
    # pydocstyle(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    print("Running flake8...")
    flake8(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    # print("Running pylint...")
    # pylint(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    print("Running unit tests...")
    unittest(context, nautobot_ver=nautobot_ver, python_ver=python_ver)
    print("All tests have passed!")
