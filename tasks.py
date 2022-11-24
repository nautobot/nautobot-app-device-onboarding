"""Tasks for use with Invoke."""

from distutils.util import strtobool
from invoke import Collection, task as invoke_task
import os


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_{{cookiecutter.plugin_name.upper()}}_xxx
namespace = Collection("nautobot_device_onboarding")
namespace.configure(
    {
        "nautobot_device_onboarding": {
            "nautobot_ver": "1.1.0",
            "project_name": "nautobot_device_onboarding",
            "python_ver": "3.7",
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "development"),
            "compose_files": [
                "docker-compose.yml",
            ],
        }
    }
)


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    build_env = {
        "NAUTOBOT_VER": context.nautobot_device_onboarding.nautobot_ver,
        "PYTHON_VER": context.nautobot_device_onboarding.python_ver,
    }
    compose_command = f'docker-compose --project-name {context.nautobot_device_onboarding.project_name} --project-directory "{context.nautobot_device_onboarding.compose_dir}"'
    for compose_file in context.nautobot_device_onboarding.compose_files:
        compose_file_path = os.path.join(context.nautobot_device_onboarding.compose_dir, compose_file)
        compose_command += f' -f "{compose_file_path}"'
    compose_command += f" {command}"
    print(f'Running docker-compose command "{command}"')
    return context.run(compose_command, env=build_env, **kwargs)


def run_command(context, command, **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    if is_truthy(context.nautobot_device_onboarding.local):
        context.run(command, **kwargs)
    else:
        # Check if nautobot is running, no need to start another nautobot container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")
        if "nautobot" in results.stdout:
            compose_command = f"exec nautobot {command}"
        else:
            compose_command = f"run --entrypoint '{command}' nautobot"

        docker_compose(context, compose_command, pty=True)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
    }
)
def build(context, force_rm=False, cache=True):
    """Build Nautobot docker image."""
    command = "build"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {context.nautobot_device_onboarding.python_ver}...")
    docker_compose(context, command)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot .. ")
    docker_compose(context, "up")


@task
def start(context):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode.. ")
    docker_compose(context, "up --detach")


@task
def stop(context):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot .. ")
    docker_compose(context, "down")


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, "down --volumes")


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"
    run_command(context, command)


@task
def cli(context):
    """Launch a bash shell inside the running Nautobot container."""
    run_command(context, "bash")


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task(
    help={
        "name": "name of the migration to be created; if unspecified, will autogenerate a name",
    }
)
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations nautobot_device_onboarding"

    if name:
        command += f" --name {name}"

    run_command(context, command)


# ------------------------------------------------------------------------------
# TESTS / LINTING
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
    }
)
def black(context, autoformat=False):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"

    command = f"{black_command} ."

    run_command(context, command)


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 . --config .flake8"
    run_command(context, command)


@task
def pylint(context):
    """Run pylint code analysis."""
    command = (
        'pylint --init-hook "import nautobot; nautobot.setup()" --rcfile pyproject.toml nautobot_device_onboarding'
    )
    run_command(context, command)


@task
def pydocstyle(context):
    """Run pydocstyle to validate docstring formatting adheres to NTC defined standards."""
    # We exclude the /migrations/ directory since it is autogenerated code
    command = "pydocstyle --config=.pydocstyle.ini ."
    run_command(context, command)


@task
def bandit(context):
    """Run bandit to validate basic static code security analysis."""
    command = "bandit --recursive . --configfile .bandit.yml"
    run_command(context, command)


@task
def yamllint(context):
    """Run yamllint to validate formating adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
    """
    command = "yamllint . --format standard"
    run_command(context, command)


@task
def unittest(context):
    """Run Nautobot unit tests."""
    command = "nautobot-server test nautobot_device_onboarding"
    run_command(context, command)


@task
def tests(context):
    """Run all tests for this plugin.

    Args:
         context (obj): Used to run specific commands
        nautobot_ver (str): Nautobot version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    # Sorted loosely from fastest to slowest
    print("Running black...")
    black(context)
    print("Running yamllint...")
    yamllint(context)
    print("Running bandit...")
    bandit(context)
    print("Running pydocstyle...")
    pydocstyle(context)
    print("Running flake8...")
    flake8(context)
    # print("Running pylint...")
    # pylint(context)
    print("Running unit tests...")
    unittest(context)
    print("All tests have passed!")
