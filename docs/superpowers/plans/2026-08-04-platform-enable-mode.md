# Per-Platform Netmiko Enable Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Make Netmiko enable mode opt-in per logical Nautobot platform for both SSoT onboarding jobs.

**Architecture:** Store an allow-list named netmiko_enable_mode_platforms in the Device Onboarding app configuration, with an empty-list default. The shared command getter compares each host's logical platform (task.host.platform) with that list once per host and passes the resulting Boolean to nornir_netmiko.tasks.netmiko_send_command. The platform identity remains independent of the underlying Netmiko device type, allowing cisco_platform_1 and cisco_platform_2 to have different privilege behavior.

**Tech Stack:** Nautobot App configuration, Django settings/schema validation, Nornir, nornir-netmiko, unittest, Invoke.

## Global Constraints

- Before feature code changes, fetch upstream, merge the latest upstream/develop, and run invoke tests successfully.
- Apply the policy only to Sync Devices From Network and Sync Network Data From Network, which share netmiko_send_commands().
- Do not change the original NAPALM onboarding job.
- The default is disabled: an absent or empty netmiko_enable_mode_platforms setting must result in enable=False.
- Use logical platform/network-driver identifiers such as cisco_platform_1, not underlying Netmiko identifiers such as cisco_ios, to select enable mode.
- Do not store secrets in the repository; use ignored development/creds.env only for local integration credentials.

---

## File Structure

- Modify: nautobot_device_onboarding/__init__.py — declare the default empty allow-list in NautobotDeviceOnboardingConfig.default_settings.
- Modify: development/nautobot_config.py — include the empty allow-list so the generated JSON schema has an array-of-strings property.
- Modify: nautobot_device_onboarding/app-config-schema.json — regenerate and review the configuration schema.
- Modify: nautobot_device_onboarding/nornir_plays/command_getter.py — add the platform-policy helper and replace unconditional enable=True.
- Modify: nautobot_device_onboarding/tests/test_command_getter.py — add task-level assertions for the enable value passed to nornir-netmiko.
- Modify: docs/admin/install.md — document the new Device Onboarding setting.
- Modify: docs/user/app_getting_started.md and docs/user/faq.md — distinguish an enable password from enable-mode selection and show the custom-Cisco example.

## Task 1: Synchronize With Upstream and Establish a Passing Baseline

**Files:**
- Modify: Git history only through the merge of upstream/develop.
- Test: full project suite via Invoke.

**Interfaces:**
- Consumes: current feature branch and configured upstream remote.
- Produces: a feature branch containing the latest upstream/develop changes and a passing baseline before feature code is edited.

- [ ] **Step 1: Confirm the branch and worktree are safe to merge**

Run:

~~~
git status --short --branch
git remote -v
git log --oneline --decorate -5
~~~

Expected: the current branch is feature/add-netmiko-enable-secret-support; only intentional committed work is present; an upstream remote exists.

- [ ] **Step 2: Fetch and merge the latest upstream development branch**

Run:

~~~
git fetch upstream
git merge upstream/develop
~~~

Expected: a clean fast-forward or merge commit. If conflicts occur, preserve docs/superpowers/specs/2026-08-04-platform-enable-mode-design.md, preserve unrelated user changes, resolve only the merge conflict, and rerun git status --short before continuing.

- [ ] **Step 3: Run the complete merged-baseline suite before editing feature code**

Run:

~~~
invoke tests
~~~

Expected: Ruff, djlint, yamllint, markdownlint, lock check, migration check, pylint, documentation build, app-config-schema validation, and unit tests all pass.

- [ ] **Step 4: Stop and diagnose any baseline failure before feature work**

If Step 3 fails, record the exact failing command and output, use the systematic-debugging workflow to identify whether it is an upstream or environment issue, and do not edit enable-mode feature code until the baseline passes.

- [ ] **Step 5: Confirm the merge is recorded without creating an empty commit**

Run:

~~~
git status --short --branch
git log --oneline --decorate -3
~~~

Expected: the branch contains the merged upstream commit and has a clean worktree before Task 2 starts. Do not create an empty commit when the merge fast-forwards.

## Task 2: Add the Opt-In Configuration Contract and Schema

**Files:**
- Modify: nautobot_device_onboarding/__init__.py:23-46
- Modify: development/nautobot_config.py:127-150
- Modify: nautobot_device_onboarding/app-config-schema.json
- Test: nautobot_device_onboarding/tests/test_command_getter.py

**Interfaces:**
- Consumes: settings.PLUGINS_CONFIG["nautobot_device_onboarding"].
- Produces: netmiko_enable_mode_platforms: list[str], always defaulting to [].

- [ ] **Step 1: Write the failing default-setting test**

Add this import and test class to nautobot_device_onboarding/tests/test_command_getter.py:

~~~python
from nautobot_device_onboarding import NautobotDeviceOnboardingConfig


class TestNetmikoEnableModeConfiguration(unittest.TestCase):
    def test_enable_mode_platforms_default_to_empty_list(self):
        self.assertEqual(NautobotDeviceOnboardingConfig.default_settings["netmiko_enable_mode_platforms"], [])
~~~

- [ ] **Step 2: Run the new test and verify it fails**

Run:

~~~
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
~~~

Expected: FAIL with KeyError: "netmiko_enable_mode_platforms".

- [ ] **Step 3: Add the configuration default and schema-generation input**

Add this entry to NautobotDeviceOnboardingConfig.default_settings in nautobot_device_onboarding/__init__.py:

~~~python
"netmiko_enable_mode_platforms": [],
~~~

Update development/nautobot_config.py so the Device Onboarding section is:

~~~python
"nautobot_device_onboarding": {
    "netmiko_enable_mode_platforms": [],
},
~~~

Do not add this policy to development/creds.env; it is not a credential.

- [ ] **Step 4: Regenerate and inspect the schema**

Run:

~~~
invoke generate-app-config-schema
git diff -- nautobot_device_onboarding/app-config-schema.json
~~~

Expected: app-config-schema.json is a JSON object that accepts netmiko_enable_mode_platforms as an array whose items are strings, with a default of [].

- [ ] **Step 5: Run the focused default and schema checks**

Run:

~~~
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
invoke validate-app-config
~~~

Expected: PASS.

- [ ] **Step 6: Commit the configuration contract**

~~~
git add nautobot_device_onboarding/__init__.py development/nautobot_config.py nautobot_device_onboarding/app-config-schema.json nautobot_device_onboarding/tests/test_command_getter.py
git commit -m "feat: add netmiko enable mode platform setting"
~~~

## Task 3: Make Command Execution Respect the Logical Platform Allow-List

**Files:**
- Modify: nautobot_device_onboarding/nornir_plays/command_getter.py:121-165
- Modify: nautobot_device_onboarding/tests/test_command_getter.py

**Interfaces:**
- Consumes: task.host.platform: str and settings.PLUGINS_CONFIG["nautobot_device_onboarding"]["netmiko_enable_mode_platforms"]: list[str].
- Produces: _platform_requires_enable_mode(platform: str) -> bool; netmiko_send_commands() passes this Boolean to netmiko_send_command(enable=...).

- [ ] **Step 1: Write failing task-level enable-mode tests**

Import settings from django.conf, override_settings from django.test, and SimpleNamespace from types. Add this test helper:

~~~python
def _run_single_raw_command(self, platform, enabled_platforms):
    task = MagicMock()
    task.host.name = "test-host"
    task.host.hostname = "198.51.100.1"
    task.host.port = 22
    task.host.platform = platform
    task.host.data = {}
    task.host.data["platform_parsing_info"] = {}
    task.results = [MagicMock()]
    task.run.return_value.result = "show version output"
    job = SimpleNamespace(connectivity_test=False, debug=False, fail_job_on_task_failure=False)
    yaml_data = {platform: {"sync_devices": {"hostname": {"commands": {"command": "show version", "parser": "raw"}}}}}

    with override_settings(
        PLUGINS_CONFIG={
            **settings.PLUGINS_CONFIG,
            "nautobot_device_onboarding": {"netmiko_enable_mode_platforms": enabled_platforms},
        }
    ):
        with patch(
            "nautobot_device_onboarding.nornir_plays.command_getter.get_all_network_driver_mappings",
            return_value={platform: {}},
        ):
            with patch(
                "nautobot_device_onboarding.nornir_plays.command_getter._get_commands_to_run",
                return_value=[{"command": "show version", "parser": "raw"}],
            ):
                netmiko_send_commands(task, yaml_data, "sync_devices", MagicMock(), job)
    return task.run.call_args.kwargs["enable"]
~~~

Add these assertions:

~~~python
def test_empty_allow_list_disables_enable_mode(self):
    self.assertFalse(self._run_single_raw_command("juniper_junos", []))

def test_listed_logical_platform_enables_enable_mode(self):
    self.assertTrue(self._run_single_raw_command("cisco_platform_1", ["cisco_platform_1"]))

def test_unlisted_logical_platform_disables_enable_mode(self):
    self.assertFalse(self._run_single_raw_command("cisco_platform_2", ["cisco_platform_1"]))
~~~

- [ ] **Step 2: Run the tests and verify the disabled-platform assertions fail**

Run:

~~~
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
~~~

Expected: FAIL because production code still passes enable=True for every platform.

- [ ] **Step 3: Implement the smallest shared policy helper**

Add this helper before netmiko_send_commands() in command_getter.py:

~~~python
def _platform_requires_enable_mode(platform: str) -> bool:
    """Return whether Netmiko enable mode is configured for a logical platform."""
    enabled_platforms = settings.PLUGINS_CONFIG["nautobot_device_onboarding"].get(
        "netmiko_enable_mode_platforms", []
    )
    return platform in enabled_platforms
~~~

After the existing platform and mapper validation in netmiko_send_commands(), calculate the decision once:

~~~python
enable_mode = _platform_requires_enable_mode(task.host.platform)
~~~

Replace the unconditional task argument with:

~~~python
enable=enable_mode,
~~~

Keep existing secret parsing, connection options, command list, parser behavior, and error handling unchanged.

- [ ] **Step 4: Run focused policy and related inventory/job tests**

Run:

~~~
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
invoke unittest --label nautobot_device_onboarding.tests.test_inventory_creator --keepdb
invoke unittest --label nautobot_device_onboarding.tests.test_jobs --keepdb
~~~

Expected: PASS. The task-call assertions are False for Juniper and cisco_platform_2, and True for cisco_platform_1. Inventory and job setup still preserve the enable secret.

- [ ] **Step 5: Commit the shared execution change**

~~~
git add nautobot_device_onboarding/nornir_plays/command_getter.py nautobot_device_onboarding/tests/test_command_getter.py
git commit -m "feat: configure netmiko enable mode per platform"
~~~

## Task 4: Document Platform Selection and Secret Behavior

**Files:**
- Modify: docs/admin/install.md:96-153
- Modify: docs/user/app_getting_started.md:65-81
- Modify: docs/user/faq.md:38-51

**Interfaces:**
- Consumes: netmiko_enable_mode_platforms from Task 2 and _platform_requires_enable_mode() behavior from Task 3.
- Produces: accurate operator instructions for enabling privileged mode only on selected logical platforms.

- [ ] **Step 1: Add the administrator setting reference and example**

Add this bullet after set_management_only_interface in docs/admin/install.md:

~~~markdown
- netmiko_enable_mode_platforms list of strings (default []), logical platform/network-driver identifiers for which the SSoT jobs call Netmiko enable mode. All unlisted platforms run commands with enable mode disabled.
~~~

Add this example to the Device Onboarding configuration example:

~~~python
"netmiko_enable_mode_platforms": ["cisco_platform_1"],
~~~

- [ ] **Step 2: Correct the enable-secret guidance**

In docs/user/app_getting_started.md and docs/user/faq.md, retain the Secret type table but replace the claim that supplying Secret automatically enters privileged mode with:

~~~markdown
The Secret value is supplied to Netmiko as the enable password. Netmiko enters enable mode only when the device's logical platform is listed in netmiko_enable_mode_platforms; an unlisted platform, such as juniper_junos, does not attempt a Cisco-style enable command.
~~~

- [ ] **Step 3: Document separate Cisco logical platforms**

Add an example containing:

~~~python
"netmiko_enable_mode_platforms": ["cisco_platform_1"],
~~~

Explain that cisco_platform_1 and cisco_platform_2 must be distinct Nautobot Platform network_driver values, must have matching command mapper files, and must map through Netmiko aliases as documented in docs/dev/custom_command_mapper_per_platform.md. State that only cisco_platform_1 enters enable mode.

- [ ] **Step 4: Run documentation and schema checks**

Run:

~~~
invoke markdownlint
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
invoke validate-app-config
~~~

Expected: PASS.

- [ ] **Step 5: Commit the documentation**

~~~
git add docs/admin/install.md docs/user/app_getting_started.md docs/user/faq.md
git commit -m "docs: explain per-platform netmiko enable mode"
~~~

## Task 5: Full Verification and Handoff

**Files:**
- Verify: all files modified by Tasks 2–4.

**Interfaces:**
- Consumes: merged upstream baseline and the completed configuration, command, test, and documentation changes.
- Produces: verified feature branch ready for review.

- [ ] **Step 1: Run the complete project suite**

Run:

~~~
invoke tests
~~~

Expected: all lint, documentation, schema, migration, unit, and coverage checks pass.

- [ ] **Step 2: Inspect the final diff and history**

Run:

~~~
git status --short
git diff upstream/develop...HEAD --stat
git log --oneline upstream/develop..HEAD
~~~

Expected: no uncommitted changes; the diff contains only the design/plan documents, intended upstream merge, configuration contract, shared task policy, tests, and documentation.

- [ ] **Step 3: Perform an optional local integration check**

Set only this non-secret policy in development/nautobot_config.py while retaining credentials in ignored development/creds.env:

~~~python
"nautobot_device_onboarding": {
    "netmiko_enable_mode_platforms": ["cisco_platform_1"],
},
~~~

Run the hidden troubleshooting job against one device from each logical platform. Confirm cisco_platform_1 succeeds using its enable secret and cisco_platform_2/juniper_junos succeed without a Cisco-style enable attempt. Remove any local-only policy change before committing.

- [ ] **Step 4: Request code review**

Provide reviewers with the configuration example, the distinction between logical platform and Netmiko driver, and evidence from invoke tests.
