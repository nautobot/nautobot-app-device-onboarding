"""Adds command mapper, platform parsing info."""

import os

import yaml
from nautobot.extras.models import GitRepository

from nautobot_device_onboarding.constants import (
    ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER,
    ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER,
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


def get_git_repo():
    """Get the git repo object."""
    if (
        GitRepository.objects.filter(
            provided_contents__contains="nautobot_device_onboarding.onboarding_command_mappers"
        ).count()
        == 1
    ):
        repository_record = GitRepository.objects.filter(
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER]
        ).first()
        return repository_record
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


def add_platform_parsing_info():
    """Merges platform command mapper from repo or defaults."""
    repository_record = get_git_repo()
    if repository_record:
        repo_data_dir = os.path.join(repository_record.filesystem_path, ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER)
        command_mappers_repo_path = load_command_mappers_from_dir(repo_data_dir)
    else:
        command_mappers_repo_path = {}
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
