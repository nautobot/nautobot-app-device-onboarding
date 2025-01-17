"""Datasources to override command_mapper yaml files."""

from pathlib import Path

from nautobot.apps.datasources import DatasourceContent
from nautobot.extras.choices import LogLevelChoices

from nautobot_device_onboarding.constants import (
    ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER,
    ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER,
)


def refresh_git_command_mappers(repository_record, job_result, delete=False):  # pylint: disable=unused-argument
    """Callback for gitrepository updates on Command Mapper Repo."""
    # Since we don't create any DB records we can just ignore deletions.
    if delete:
        return
    if ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER not in repository_record.provided_contents:
        return
    job_result.log(
        "Refreshing network sync job command mappers...",
        level_choice=LogLevelChoices.LOG_INFO,
    )
    repo_data_dir = Path(repository_record.filesystem_path) / ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER
    if not repo_data_dir.exists():
        job_result.log(
            "Command mapper repo folder does not exist. "  # pylint: disable=consider-using-f-string
            "Create a sub folder in the repository at %s" % repo_data_dir,
            repository_record,
            level_choice=LogLevelChoices.LOG_WARNING,
        )
        return
    try:
        next(repo_data_dir.glob("*.yml"))
    except StopIteration:
        job_result.log(
            "Command mapper repo folder found, but it doesn't contain any command mapper files. "
            "They need to have the '.yml' extension.",
            level_choice=LogLevelChoices.LOG_WARNING,
        )


datasource_contents = [
    (
        "extras.gitrepository",
        DatasourceContent(
            name="Network Sync Job Command Mappers",
            content_identifier=ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER,
            icon="mdi-paw",
            callback=refresh_git_command_mappers,
        ),
    )
]
