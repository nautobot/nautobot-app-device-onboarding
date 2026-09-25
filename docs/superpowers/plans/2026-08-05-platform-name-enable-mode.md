# Nautobot Platform Name Enable-Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `netmiko_enable_mode_platforms` match Nautobot Platform names such as `cisco_c2960`, avoiding generated natural-slug suffixes.

**Architecture:** Keep `Host.platform` unchanged as the Netmiko/network-driver key used by command mappers and SSH. Store a separate `nautobot_platform_name` host-data value for explicitly selected Sync Devices Platforms and resolve `device.platform.name` for Sync Network Data. The shared command task compares that name with the allow-list and logs the same name.

**Tech Stack:** Python 3.12, Django/Nautobot 3.0, Nornir, Netmiko, unittest, MkDocs.

## Global Constraints

- Allow-list values are unique Nautobot Platform `name` strings, not `natural_slug`, `network_driver`, or Netmiko device-type values.
- Missing or empty `netmiko_enable_mode_platforms` must resolve to `enable=False`.
- No fallback to `natural_slug` is supported.
- An auto-detected Sync Devices host without an explicitly selected Platform must resolve to `enable=False`.
- Do not alter command-mapper lookup, Netmiko connection-driver selection, enable-secret handling, or the original NAPALM onboarding job.
- Preserve one info-level, credential-free decision log per host.

---

### Task 1: Use Platform.name for the policy decision

**Files:**
- Modify: `nautobot_device_onboarding/nornir_plays/inventory_creator.py:37-75`
- Modify: `nautobot_device_onboarding/nornir_plays/command_getter.py:121-150`
- Test: `nautobot_device_onboarding/tests/test_inventory_creator.py:15-52`
- Test: `nautobot_device_onboarding/tests/test_command_getter.py:29-100`

**Interfaces:**
- Produces: `Host.data["nautobot_platform_name"]: str` for an explicitly selected Sync Devices Platform.
- Produces: `_get_nautobot_platform_name(task: Task) -> str | None`, preferring host metadata and then reading `task.host.data["obj"].platform.name` for Nautobot ORM inventory hosts.
- Consumes: `task.host.platform` unchanged as the network-driver key for command mapper and Netmiko behavior.

- [ ] **Step 1: Write failing tests for name-based metadata and ORM resolution**

  Update the inventory fixture to use `Platform(name="cisco_c2960", network_driver="cisco_xe")`. Change the selected-platform test to assert `Host.data["nautobot_platform_name"] == "cisco_c2960"` and that no `nautobot_platform_slug` key exists.

  Update the command-task helper and cases to use `{"nautobot_platform_name": "cisco_c2960"}` with transport driver `cisco_ios`. Add an ORM-style case:

  ```python
  device = SimpleNamespace(platform=SimpleNamespace(name="cisco_c2960"))
  enable, logger = self._run_single_raw_command("cisco_ios", ["cisco_c2960"], {"obj": device})
  self.assertTrue(enable)
  logger.info.assert_called_once_with("Nautobot Platform 'cisco_c2960' enable mode: enabled")
  ```

  Keep cases for empty configuration, an unlisted second name sharing `cisco_ios`, and an auto-detected host with no Platform metadata. Assert the auto-detected host logs `Nautobot Platform unavailable; enable mode: disabled`.

- [ ] **Step 2: Run the focused tests to verify the old natural-slug implementation fails**

  ```bash
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_inventory_creator
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_command_getter --pattern=TestNetmikoEnableModeConfiguration
  ```

  Expected: failures because the current implementation writes/reads `natural_slug` and `nautobot_platform_slug` rather than the requested Platform name.

- [ ] **Step 3: Implement the minimal name-key change**

  In `_set_inventory()`, capture `platform.name` and pass it to `Host(data={"nautobot_platform_name": platform_name})` before replacing the local Platform object with `network_driver_mappings["netmiko"]`. Do not change the `Host.platform` or Netmiko `ConnectionOptions.platform` values.

  In `command_getter.py`, rename the resolver to `_get_nautobot_platform_name()`, read `nautobot_platform_name` first, then `obj.platform.name`, and return `None` when neither is available. Rename `_platform_requires_enable_mode()`'s argument to `platform_name` and document that it tests a Nautobot Platform name. Use `platform_name` in the info log while retaining all later `task.host.platform` command-mapper logic.

  Do not accept or compare `natural_slug` as a compatibility fallback.

- [ ] **Step 4: Run focused tests to verify the implementation passes**

  ```bash
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_inventory_creator
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_command_getter --pattern=TestNetmikoEnableModeConfiguration
  ```

  Expected: all focused tests pass, including the shared `cisco_ios` transport with distinct Platform names.

- [ ] **Step 5: Commit the implementation and tests**

  ```bash
  git add nautobot_device_onboarding/nornir_plays/inventory_creator.py nautobot_device_onboarding/nornir_plays/command_getter.py nautobot_device_onboarding/tests/test_inventory_creator.py nautobot_device_onboarding/tests/test_command_getter.py
  git commit -m "fix: use platform name for enable mode policy"
  ```

### Task 2: Update operator documentation

**Files:**
- Modify: `docs/admin/install.md:109-138`
- Modify: `docs/user/app_getting_started.md:65-89`
- Modify: `docs/user/faq.md:37-50`

**Interfaces:**
- Consumes: the name-based policy semantics from Task 1.
- Produces: documentation that tells operators to configure Platform names and explains why generated natural slugs are not used.

- [ ] **Step 1: Replace slug terminology and examples**

  Update each configuration example and explanation to say that the list contains Nautobot Platform `name` values. Use:

  ```python
  "netmiko_enable_mode_platforms": ["cisco_c2960"]
  ```

  Explain that the Platform name `cisco_c2960` is matched independently from its Netmiko mapping `cisco_ios`, and that values such as `cisco-c2960_4784` are generated natural slugs and should not be configured.

  Preserve default-disabled behavior, auto-detection behavior, and existing Secrets Group instructions.

- [ ] **Step 2: Build the documentation strictly**

  ```bash
  source .venv/bin/activate && invoke build-and-check-docs
  ```

  Expected: MkDocs completes with exit code 0 and no broken-link or strict-build errors.

- [ ] **Step 3: Commit the documentation**

  ```bash
  git add docs/admin/install.md docs/user/app_getting_started.md docs/user/faq.md
  git commit -m "docs: document platform name enable mode setting"
  ```

### Task 3: Run complete regression verification

**Files:**
- Verify only: no source changes expected.

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: full-suite evidence for tests, lint, docs, schema, migrations, Pylint, coverage, and LCOV.

- [ ] **Step 1: Run the full repository suite**

  ```bash
  source .venv/bin/activate && invoke tests --keepdb
  ```

  Expected: all checks pass, including the full SSH-style job tests that previously caught the incorrect `Platform.slug` assumption. If Docker access is blocked, rerun with approved Docker access. If host port `8080` is occupied, temporarily map only the development service to `18080:8080`, restore `development/docker-compose.dev.yml` with `apply_patch`, and verify it is not modified before handoff.

- [ ] **Step 2: Inspect the final worktree**

  ```bash
  git status --short
  git diff --check
  ```

  Expected: clean worktree with no generated docs, credentials, or temporary port changes.
