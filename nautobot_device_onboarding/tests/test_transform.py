"""Testing the transform helpers."""

import os
import tempfile
from unittest import mock

import yaml
from django.core.exceptions import ObjectDoesNotExist
from nautobot.apps.testing import TestCase, TransactionTestCase
from nautobot.core.jobs import GitRepositorySync
from nautobot.core.testing import run_job_for_testing
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import GitRepository, JobResult

from nautobot_device_onboarding.constants import (
    ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER,
    ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER,
)
from nautobot_device_onboarding.nornir_plays.transform import (
    DATA_DIR,
    add_platform_parsing_info,
    get_git_repo,
    load_command_mappers_from_dir,
)

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestTransformNoGitRepo(TestCase):
    """Testing the transform helpers with no git repo overloads."""

    def setUp(self):
        self.yaml_file_dir = f"{MOCK_DIR}/command_mappers/"

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.GitRepository.objects.get")
    def test_add_platform_parsing_info_no_git_repo_skips_ensure(self, mock_repo_get, mock_ensure):
        """With no command mapper repo, the git repo must never be touched."""
        mock_repo_get.side_effect = ObjectDoesNotExist
        add_platform_parsing_info()
        mock_ensure.assert_not_called()

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.GitRepository.objects.get")
    def test_add_platform_parsing_info_sane_defaults(self, mock_repo_get):
        mock_repo_get.side_effect = ObjectDoesNotExist
        command_mappers = add_platform_parsing_info()
        default_mappers = [
            "cisco_ios",
            "arista_eos",
            "cisco_wlc",
            "cisco_xe",
            "cisco_xr",
            "juniper_junos",
            "cisco_nxos",
            "hp_comware",
            "paloalto_panos",
            "f5_tmsh",
            "aruba_aoscx",
            "aruba_os",
            "brocade_fastiron",
            "hp_procurve",
            "nokia_sros",
        ]
        self.assertEqual(sorted(default_mappers), sorted(command_mappers.keys()))

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
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER],
        )
        self.repo.save()
        self.job_result = JobResult.objects.create(name=self.repo.name)
        return mock.DEFAULT

    def populate_repo(self, path, url, *args, **kwargs):
        """Simple helper to populate a mock repo with some data."""
        os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(path, "onboarding_command_mappers"), exist_ok=True)
        with open(
            os.path.join(path, "onboarding_command_mappers", "foo_bar.yml"),
            "w",
            encoding="utf-8",
        ) as fd:  # pylint:disable=invalid-name
            yaml.dump(
                {
                    "sync_devices": {
                        "serial": {
                            "commands": [
                                {
                                    "command": "show version",
                                    "parser": "textfsm",
                                    "jpath": "[*].serial",
                                }
                            ]
                        }
                    }
                },
                fd,
            )
        return mock.DEFAULT

    def test_git_repo_was_created(self, MockGitRepo):  # pylint:disable=invalid-name
        repo_count = GitRepository.objects.filter(
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER]
        ).count()
        self.assertEqual(1, repo_count)

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.load_command_mappers_from_dir")
    def test_pull_git_repository_and_refresh_data_with_valid_data(self, mock_load_command_mappers, MockGitRepo):  # pylint:disable=invalid-name
        """
        The test_pull_git_repository_and_refresh_data job should succeed if valid data is present in the repo.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                MockGitRepo.side_effect = self.populate_repo
                # Nautobot >= 3.1.7 uses `with GitRepo(...) as repo_helper`; older versions
                # assign the instance directly. Stub both so the test works on either.
                MockGitRepo.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)
                MockGitRepo.return_value.__enter__.return_value.checkout.return_value = (self.COMMIT_HEXSHA, True)

                # Run the Git operation and refresh the object from the DB
                job_model = GitRepositorySync().job_model
                job_result = run_job_for_testing(job=job_model, repository=self.repo.pk)
                job_result.refresh_from_db()
                self.assertEqual(
                    job_result.status,
                    JobResultStatusChoices.STATUS_SUCCESS,
                    (
                        job_result.traceback,
                        list(job_result.job_log_entries.values_list("message", flat=True)),
                    ),
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


@mock.patch("nautobot.extras.datasources.git.GitRepo")
class TestEnsureCommandMappersRepo(TestCase):
    """Testing that the command mapper repo is cloned on the worker running the job."""

    def setUp(self):
        super().setUp()
        GitRepository.objects.filter(provided_contents__contains=ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER).delete()
        self.repo = GitRepository(
            name="Test Git Repo",
            remote_url="http://localhost/git.git",
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER],
        )
        self.repo.save()
        self.default_mappers = load_command_mappers_from_dir(DATA_DIR)
        self.logger = mock.MagicMock()
        return mock.DEFAULT

    @staticmethod
    def populate_repo(repository_record, *args, **kwargs):
        """Simulate ensure_git_repository cloning the repo onto this worker."""
        mappers_dir = os.path.join(repository_record.filesystem_path, ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER)
        os.makedirs(mappers_dir, exist_ok=True)
        with open(os.path.join(mappers_dir, "foo_bar.yml"), "w", encoding="utf-8") as file_handle:
            yaml.dump({"sync_devices": {"serial": {"commands": []}}}, file_handle)
        return True

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    def test_add_platform_parsing_info_ensures_repo_on_worker(self, mock_ensure, *args):
        """The repo must be refreshed on whichever worker is executing the job."""
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                mock_ensure.side_effect = self.populate_repo
                add_platform_parsing_info(logger=self.logger)
        mock_ensure.assert_called_once_with(self.repo, head=self.repo.current_head or None)

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    def test_add_platform_parsing_info_clones_when_filesystem_path_missing(self, mock_ensure, *args):
        """Regression test for #609: a worker with no local clone must not raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                # The repo directory does not exist until ensure_git_repository creates it.
                self.assertFalse(os.path.isdir(self.repo.filesystem_path))
                mock_ensure.side_effect = self.populate_repo
                command_mappers = add_platform_parsing_info(logger=self.logger)
        self.assertIn("foo_bar", command_mappers)
        self.assertEqual(sorted([*self.default_mappers, "foo_bar"]), sorted(command_mappers))
        self.logger.error.assert_not_called()

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    def test_add_platform_parsing_info_missing_dir_after_ensure_falls_back(self, mock_ensure, *args):
        """A repo without an onboarding_command_mappers directory logs an error instead of raising."""
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                mock_ensure.return_value = False
                command_mappers = add_platform_parsing_info(logger=self.logger)
        self.assertEqual(sorted(self.default_mappers), sorted(command_mappers))
        self.logger.error.assert_called_once()
        self.assertIn(ONBOARDING_COMMAND_MAPPERS_REPOSITORY_FOLDER, self.logger.error.call_args[0][0])

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    def test_add_platform_parsing_info_ensure_failure_logs_error_and_falls_back(self, mock_ensure, *args):
        """A git failure must be surfaced as an error, not silently swallowed."""
        mock_ensure.side_effect = Exception("authentication failed")
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                command_mappers = add_platform_parsing_info(logger=self.logger)
        self.assertEqual(sorted(self.default_mappers), sorted(command_mappers))
        self.logger.error.assert_called_once()
        self.assertIn("authentication failed", self.logger.error.call_args[0][0])
        self.logger.warning.assert_called_once()

    @mock.patch("nautobot_device_onboarding.nornir_plays.transform.ensure_git_repository")
    def test_add_platform_parsing_info_ensure_failure_raises_when_fail_job_on_task_failure(self, mock_ensure, *args):
        """With the job's fail fast option set, a git failure must fail the job."""
        mock_ensure.side_effect = Exception("authentication failed")
        with tempfile.TemporaryDirectory() as tempdir:
            with self.settings(GIT_ROOT=tempdir):
                with self.assertRaises(Exception):
                    add_platform_parsing_info(logger=self.logger, raise_on_repo_error=True)
        self.logger.error.assert_called_once()


@mock.patch("nautobot.extras.datasources.git.GitRepo")
class GetGitRepoTestCase(TestCase):
    """Testing the get_git_repo helper function."""

    def setUp(self):
        # Create a clean state before each test
        super().setUp()
        # Clean up any existing repos to ensure a fresh state (safe option)
        GitRepository.objects.filter(provided_contents__contains=ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER).delete()
        self.repo = GitRepository(
            name="Test Git Repo",
            remote_url="http://localhost/git.git",
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER],
        )
        self.repo.save()
        return mock.DEFAULT

    def test_get_git_repo_success(self, *args, **kwargs):
        """
        Scenario: A single repository exists with the correct content identifier.
        Expected: The function returns that specific repository object.
        """

        result = get_git_repo()

        self.assertIsNotNone(result)
        self.assertEqual(result, self.repo)
        self.assertEqual(result.name, self.repo.name)

    def test_get_git_repo_success_with_multiple_contents(self, *args, **kwargs):
        """
        Scenario: A repository provides the mappers AND other content (e.g., jobs).
        Expected: The function still finds it because we use `__contains`.
        """
        result = get_git_repo()
        result.provided_contents.append("some_other_content")
        result.save()
        self.assertIsNotNone(result)
        self.assertEqual(result, self.repo)

    def test_get_git_repo_multiple_exist(self, *args, **kwargs):
        """
        Scenario: Two repositories claim to provide the command mappers.
        Expected: Returns None (catches MultipleObjectsReturned) to avoid ambiguity.
        """
        # Create Repo 1
        new_repo = GitRepository(
            name="repo-1",
            slug="repo-1",
            remote_url="http://github.com/test/repo1.git",
            provided_contents=[ONBOARDING_COMMAND_MAPPERS_CONTENT_IDENTIFIER],
        )
        new_repo.save()

        result = get_git_repo()

        self.assertIsNone(result)
        # clean up
        new_repo.delete()

    def test_get_git_repo_none_exists(self, *args, **kwargs):
        """
        Scenario: No repository exists with that specific content identifier.
        Expected: Returns None (catches ObjectDoesNotExist).
        """
        # delete existing test repo
        self.repo.delete()
        # Create a repo that does NOT have the right content
        irr_repo = GitRepository(
            name="irrelevant-repo",
            remote_url="http://github.com/test/irr_repo.git",
            provided_contents=["some_other_content"],
        )
        irr_repo.save()
        result = get_git_repo()
        self.assertIsNone(result)
        # clean up
        irr_repo.delete()
