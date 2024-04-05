"""Nornir tranform function to add command mapper, platform parsing info."""

import os
import yaml
from nautobot.extras.models import GitRepository

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "command_mappers"))


def add_platform_parsing_info(host):
    """This nornir transform function adds platform parsing info."""
    if (
        GitRepository.objects.filter(
            provided_contents=["nautobot_device_onboarding.onboarding_command_mappers"]
        ).count()
        == 1
    ):
        repository_record = GitRepository.objects.filter(
            provided_contents=["nautobot_device_onboarding.onboarding_command_mappers"]
        ).first()
        repo_data_dir = os.path.join(repository_record.filesystem_path, "onboarding_command_mappers")
        command_mappers_repo_path = load_command_mappers_from_dir(repo_data_dir)
    else:
        command_mappers_repo_path = {}
    command_mapper_defaults = load_command_mappers_from_dir(DATA_DIR)
    # parsing_info = _get_default_platform_parsing_info(host.platform)
    merged_command_mappers = {**command_mapper_defaults, **command_mappers_repo_path}
    # This is so we can reuse this for a non-nornir host object since we don't have it in an empty inventory at this point.
    if not isinstance(host, str):
        host.data.update({"platform_parsing_info": merged_command_mappers[host.platform]})
    return merged_command_mappers


def load_command_mappers_from_dir(command_mappers_path):
    """Helper to load all yaml files in directory and return merged dictionary."""
    command_mappers_result = {}
    for filename in os.listdir(command_mappers_path):
        with open(os.path.join(command_mappers_path, filename), encoding="utf-8") as fd:
            network_driver = filename.split(".")[0]
            command_mappers_data = yaml.safe_load(fd)
            command_mappers_result[network_driver] = command_mappers_data
    return command_mappers_result
