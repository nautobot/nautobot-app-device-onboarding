"""Testing the transform helpers."""

import os
import tempfile
import unittest
from unittest import mock

import yaml
from nautobot.core.jobs import GitRepositorySync
from nautobot.core.testing import TransactionTestCase, run_job_for_testing
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import GitRepository, JobResult

from nautobot_device_onboarding.nornir_plays.transform import add_platform_parsing_info, load_command_mappers_from_dir

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestTransformNoGitRepo(unittest.TestCase):
    """Testing the transform helpers with no git repo overloads."""

    def setUp(self):
        self.yaml_file_dir = f"{MOCK_DIR}/command_mappers/"

    def test_add_platform_parsing_info_sane_defaults(self):
        command_mappers = add_platform_parsing_info()
        default_mappers = ["cisco_ios", "arista_eos", "cisco_wlc", "cisco_xe", "juniper_junos", "cisco_nxos"]
        self.assertEqual(sorted(default_mappers), list(sorted(command_mappers.keys())))

    def test_load_command_mappers_from_dir(self):
        command_mappers = load_command_mappers_from_dir(self.yaml_file_dir)
        self.assertEqual(["mock_cisco_ios"], list(command_mappers.keys()))


@mock.patch("nautobot.extras.datasources.git.GitRepo")
class TestTransformWithGitRepo(TransactionTestCase):
    """Testing the transform helpers with git repo overloads."""

    databases = ("default", "job_logs")
    COMMIT_HEXSHA = "88dd9cd78df89e887ee90a1d209a3e9a04e8c841"

    def setUp(self):
        super().setUp()
        self.yaml_file_dir = f"{MOCK_DIR}/command_mappers/"
        self.repo_slug = "test_git_repo"
        self.repo = GitRepository(
            name="Test Git Repository",
            slug=self.repo_slug,
            remote_url="http://localhost/git.git",
            provided_contents=["nautobot_device_onboarding.onboarding_command_mappers"],
        )
        self.repo.save()
        self.job_result = JobResult.objects.create(name=self.repo.name)
        return mock.DEFAULT

    def populate_repo(self, path, url, *args, **kwargs):
        """Simple helper to populate a mock repo with some data."""
        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "onboarding_command_mappers"), exist_ok=True)
        with open(os.path.join(path, "onboarding_command_mappers", "foo_bar.yml"), "w", encoding="utf-8") as fd:
            yaml.dump(
                {
                    "sync_devices": {
                        "serial": {
                            "commands": [{"command": "show version", "parser": "textfsm", "jpath": "[*].serial"}]
                        }
                    }
                },
                fd,
            )
        return mock.DEFAULT

    def test_git_repo_was_created(self, MockGitRepo):  # pylint:disable=invalid-name
        repo_count = GitRepository.objects.filter(
            provided_contents=["nautobot_device_onboarding.onboarding_command_mappers"]
        ).count()
        self.assertEqual(1, repo_count)

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.load_command_mappers_from_dir")
    def test_pull_git_repository_and_refresh_data_with_valid_data(
        self, mock_load_command_mappers, MockGitRepo
    ):  # pylint:disable=invalid-name
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                MockGitRepo.side_effect = self.populate_repo
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (job_result.traceback, list(job_result.job_log_entries.values_list("message", flat=True))),
                )
                mock_load_command_mappers.side_effect = [
                    {"foo_bar": {"sync_devices": "serial"}},
                    {"cisco_ios": {"sync_devices": "serial-2"}},
                ]
                expected_dict = {
                    "foo_bar": {"sync_devices": "serial"},
                    "cisco_ios": {"sync_devices": "serial-2"},
                }
                merged_mappers = add_platform_parsing_info()
                self.assertEqual(expected_dict, merged_mappers)
