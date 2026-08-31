"""Adds command mapper, platform parsing info."""

import logging
import os

import yaml
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from nautobot.extras.datasources import ensure_git_repository
from nautobot.extras.models import GitRepository

from nautobot_device_onboarding.constants import (
    ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER,
    ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER,
)

LOGGER = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


def get_git_repo():
    """
    Retrieve the Git repository object that contains onboarding command mappers.

    Returns:
        GitRepository or None: The GitRepository object if found, None if no repository
                              is found or if multiple repositories match the criteria.
    """
    try:
        return GitRepository.objects.get(provided_contents__contains=ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER)
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None


def get_git_repo_parser_path(parser_type):
    """Get the git repo object."""
    repository_record = get_git_repo()
    if repository_record:
        repo_data_dir = os.path.join(
            repository_record.filesystem_path, "onboarding_command_mappers", "parsers", parser_type
        )
        if os.path.isdir(repo_data_dir):
            return repo_data_dir
        return None
    return None


def ensure_command_mappers_repo(repository_record, logger=None, raise_on_error=False):
    """Ensure the command mappers Git repository is cloned on the worker running this job.

    Args:
        repository_record (GitRepository): Repository to ensure the state of.
        logger (NornirLogger): Optional logger to write results to the job result log.
        raise_on_error (bool): Re-raise instead of falling back to the app provided defaults.

    Returns:
        bool: True if the local clone is usable, False otherwise.
    """
    logger = logger or LOGGER
    try:
        ensure_git_repository(repository_record, head=repository_record.current_head or None)
    except Exception as err:  # pylint: disable=broad-exception-caught
        logger.error(
            f"Failed to refresh command mapper Git repository '{repository_record.name}' on this worker: {err}"
        )
        if raise_on_error:
            raise
        logger.warning(
            "Falling back to the app provided default command mappers. Command mappers and parsers "
            f"from '{repository_record.name}' will NOT be applied."
        )
        return False
    logger.debug(
        f"Command mapper Git repository '{repository_record.name}' is present at "
        f"{repository_record.filesystem_path}."
    )
    return True


def add_platform_parsing_info(logger=None, raise_on_repo_error=False):
    """Merges platform command mapper from repo or defaults.

    Args:
        logger (NornirLogger): Optional logger to write results to the job result log.
        raise_on_repo_error (bool): Fail instead of falling back to the app provided defaults when
            the Git repository cannot be refreshed or read.

    Returns:
        dict: Command mappers keyed by network driver.
    """
    logger = logger or LOGGER
    command_mappers_repo_path = {}
    repository_record = get_git_repo()
    if repository_record:
        if ensure_command_mappers_repo(repository_record, logger=logger, raise_on_error=raise_on_repo_error):
            repo_data_dir = os.path.join(
                repository_record.filesystem_path, ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER
            )
            if os.path.isdir(repo_data_dir):
                command_mappers_repo_path = load_command_mappers_from_dir(repo_data_dir)
            else:
                message = (
                    f"Git repository '{repository_record.name}' does not contain the expected directory "
                    f"'{ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER}' at {repo_data_dir}. Using the app "
                    "provided default command mappers only."
                )
                logger.error(message)
                if raise_on_repo_error:
                    raise FileNotFoundError(message)
    command_mapper_defaults = load_command_mappers_from_dir(DATA_DIR)
    merged_command_mappers = {**command_mapper_defaults, **command_mappers_repo_path}
    return merged_command_mappers


def load_command_mappers_from_dir(command_mappers_path):
    """Helper to load all yaml files in directory and return merged dictionary."""
    command_mappers_result = {}
    files = [f for f in os.listdir(command_mappers_path) if os.path.isfile(os.path.join(command_mappers_path, f))]
    for filename in files:
        with open(os.path.join(command_mappers_path, filename), encoding="utf-8") as fd:
            network_driver = filename.split(".")[0]
            command_mappers_data = yaml.safe_load(fd)
            command_mappers_result[network_driver] = command_mappers_data
    return command_mappers_result


def load_files_with_precedence(filesystem_dir, parser_type):
    """Utility to load files from filesystem and git repo with precedence."""
    file_paths = {}
    git_repo_dir = get_git_repo_parser_path(parser_type)
    # List files in the first directory and add to the dictionary
    if git_repo_dir:
        for file_name in os.listdir(git_repo_dir):
            file_path = os.path.join(git_repo_dir, file_name)
            if os.path.isfile(file_path):
                file_paths[file_name] = file_path

    # List files in the second directory and add to the dictionary if not already present
    for file_name in os.listdir(filesystem_dir):
        file_path = os.path.join(filesystem_dir, file_name)
        if os.path.isfile(file_path) and file_name not in file_paths:
            file_paths[file_name] = file_path
    return file_paths
