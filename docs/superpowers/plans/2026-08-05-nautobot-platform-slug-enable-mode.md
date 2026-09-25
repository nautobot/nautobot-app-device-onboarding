# Nautobot Platform Slug Enable-Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `netmiko_enable_mode_platforms` enable Netmiko privilege mode by Nautobot Platform slug, independently of the Netmiko driver mapping.

**Architecture:** Preserve `Host.platform` as the existing network-driver key for command mapper and Netmiko behavior. Add a separate `nautobot_platform_slug` host-data value for explicitly selected Sync Devices platforms, and resolve the Platform slug from the existing Device object for Sync Network Data hosts. The shared command task will use only the resolved slug for its allow-list comparison and log message.

**Tech Stack:** Python 3.12, Django/Nautobot, Nornir, Netmiko, unittest, MkDocs.

## Global Constraints

- Allow-list values are Nautobot Platform `natural_slug` strings (the Nautobot UI slug), not `network_driver` or Netmiko device-type values.
- Missing or empty `netmiko_enable_mode_platforms` must resolve to `enable=False`.
- An auto-detected Sync Devices host without an explicitly selected Platform must resolve to `enable=False`.
- Do not alter command-mapper lookup, Netmiko connection-driver selection, enable-secret handling, or the original NAPALM onboarding job.
- Preserve one info-level, credential-free enable-mode decision log per host.

---

### Task 1: Preserve and resolve the Nautobot Platform slug

**Files:**
- Modify: `nautobot_device_onboarding/nornir_plays/inventory_creator.py:37-73`
- Modify: `nautobot_device_onboarding/nornir_plays/command_getter.py:121-145`
- Test: `nautobot_device_onboarding/tests/test_inventory_creator.py:36-47`
- Test: `nautobot_device_onboarding/tests/test_command_getter.py:29-81`

**Interfaces:**
- Produces: `Host.data["nautobot_platform_slug"]: str` for an explicitly selected Sync Devices Platform.
- Produces: `_get_nautobot_platform_slug(task: Task) -> str | None`, which reads `task.host.data["nautobot_platform_slug"]` first, then `task.host.data["obj"].platform.natural_slug` for Nautobot ORM inventory hosts.
- Consumes: `task.host.platform` unchanged as the network-driver key for command mapper lookup and Netmiko transport.

- [ ] **Step 1: Write the failing inventory-metadata tests**

  In `TestInventoryCreator`, use a Platform whose name produces `cisco_2960` as its `natural_slug`. Extend `test_set_inventory_specified_platform()` to assert both the existing Netmiko platform result and the preserved natural slug:

  ```python
  self.assertEqual(inv["198.51.100.1"].platform, self.platform.name)
  self.assertEqual(inv["198.51.100.1"].data["nautobot_platform_slug"], self.platform.natural_slug)
  ```

  Extend `test_set_inventory_no_platform()` to assert that auto-detection creates no `nautobot_platform_slug` value:

  ```python
  self.assertNotIn("nautobot_platform_slug", inv["198.51.100.1"].data)
  ```

- [ ] **Step 2: Run the inventory tests to verify the new assertion fails**

  Run:

  ```bash
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_inventory_creator
  ```

  Expected: the selected-platform test fails with `KeyError: 'nautobot_platform_slug'`.

- [ ] **Step 3: Write failing command-task tests for slug policy resolution**

  Change `_run_single_raw_command()` to accept a transport driver and optional host data. Use `cisco_ios` as the driver/YAML key and include `{"nautobot_platform_slug": "cisco_2960"}` as host data. Replace the existing listed/unlisted assertions with these cases:

  ```python
  enable, logger = self._run_single_raw_command(
      "cisco_ios", ["cisco_2960"], {"nautobot_platform_slug": "cisco_2960"}
  )
  self.assertTrue(enable)
  logger.info.assert_called_once_with("Nautobot Platform 'cisco_2960' enable mode: enabled")
  ```

  ```python
  enable, logger = self._run_single_raw_command(
      "cisco_ios", ["cisco_2960"], {"nautobot_platform_slug": "cisco_3850"}
  )
  self.assertFalse(enable)
  logger.info.assert_called_once_with("Nautobot Platform 'cisco_3850' enable mode: disabled")
  ```

  Add a Sync Network Data-style host-data case:

  ```python
  device = SimpleNamespace(platform=SimpleNamespace(slug="cisco_2960"))
  enable, _ = self._run_single_raw_command("cisco_ios", ["cisco_2960"], {"obj": device})
  self.assertTrue(enable)
  ```

  Add an auto-detected/no-platform case with empty host data and a non-empty allow-list; assert `enable` is false and the log identifies the Platform as unavailable.

- [ ] **Step 4: Run the command-task tests to verify they fail**

  Run:

  ```bash
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_command_getter --pattern=TestNetmikoEnableModeConfiguration
  ```

  Expected: listed-slug and expected-log assertions fail because the current code compares/logs `cisco_ios`.

- [ ] **Step 5: Implement the smallest policy-key separation**

  In `_set_inventory()`, save the input Platform's `natural_slug` before replacing the local `platform` variable with its Netmiko mapping. Supply that value as Host data only when a Platform was explicitly selected:

  ```python
  platform_slug = platform.natural_slug if platform else None
  # retain existing platform = platform.network_driver_mappings.get("netmiko") flow
  host_data = {"nautobot_platform_slug": platform_slug} if platform_slug else {}
  # pass data=host_data to Host(...)
  ```

  In `command_getter.py`, add `_get_nautobot_platform_slug()` before `_platform_requires_enable_mode()`. It must prefer the explicit `nautobot_platform_slug`, then safely read `obj.platform.natural_slug`, and return `None` without querying the database when neither exists. Update `_platform_requires_enable_mode()` to accept `str | None` and return false for `None`.

  In `netmiko_send_commands()`, resolve the slug once, pass it to `_platform_requires_enable_mode()`, and log either:

  ```python
  logger.info(f"Nautobot Platform '{platform_slug}' enable mode: {'enabled' if enable_mode else 'disabled'}")
  ```

  or, when the slug is unavailable:

  ```python
  logger.info(f"Nautobot Platform unavailable; enable mode: {'enabled' if enable_mode else 'disabled'}")
  ```

  Leave every use of `task.host.platform` below this block unchanged.

- [ ] **Step 6: Run focused tests to verify the implementation passes**

  Run:

  ```bash
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_inventory_creator
  source .venv/bin/activate && invoke unittest --keepdb --skip-docs-build --label=nautobot_device_onboarding.tests.test_command_getter --pattern=TestNetmikoEnableModeConfiguration
  ```

  Expected: all selected tests pass, including the shared-driver, distinct-slug scenarios.

- [ ] **Step 7: Commit the tested policy change**

  ```bash
  git add nautobot_device_onboarding/nornir_plays/inventory_creator.py nautobot_device_onboarding/nornir_plays/command_getter.py nautobot_device_onboarding/tests/test_inventory_creator.py nautobot_device_onboarding/tests/test_command_getter.py
  git commit -m "fix: select netmiko enable mode by platform slug"
  ```

### Task 2: Correct operator documentation

**Files:**
- Modify: `docs/admin/install.md:124-138`
- Modify: `docs/user/app_getting_started.md:65-89`
- Modify: `docs/user/faq.md:37-50`

**Interfaces:**
- Consumes: the policy semantics from Task 1.
- Produces: user-facing configuration guidance that uses Nautobot Platform slugs and distinguishes them from the Netmiko mapping.

- [ ] **Step 1: Update all enable-mode configuration examples to use a Platform slug**

  Replace `cisco_platform_1` examples with `cisco_2960`. State that the list contains Nautobot Platform `slug` values. Include the concrete mapping distinction: a Platform with slug `cisco_2960` and Netmiko mapping `cisco_ios` is enabled by `['cisco_2960']`, not `['cisco_ios']`.

  State that two Platform slugs can share `cisco_ios` and still receive independent policies. Explain that Sync Devices auto-detection has no selected Platform slug and remains disabled.

- [ ] **Step 2: Build the documentation strictly**

  Run:

  ```bash
  source .venv/bin/activate && invoke build-and-check-docs
  ```

  Expected: MkDocs completes successfully with no broken links or warnings.

- [ ] **Step 3: Commit the documentation**

  ```bash
  git add docs/admin/install.md docs/user/app_getting_started.md docs/user/faq.md
  git commit -m "docs: clarify enable mode platform slug setting"
  ```

### Task 3: Run regression verification

**Files:**
- Verify only: no source changes expected.

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: evidence that the full app suite, documentation build, lint, schema validation, migration check, Pylint, coverage, and LCOV checks still pass.

- [ ] **Step 1: Run the repository verification command**

  Run:

  ```bash
  source .venv/bin/activate && invoke tests --keepdb
  ```

  Expected: the full project suite passes. If the development Docker host port `8080` is already occupied, temporarily map the development service to `18080:8080` only for this verification command, then restore `development/docker-compose.dev.yml` before any commit.

- [ ] **Step 2: Inspect the final worktree**

  Run:

  ```bash
  git status --short
  git log --oneline -3
  ```

  Expected: only the two intentional feature commits and this plan/spec documentation are present; no credentials file, generated documentation, or temporary port change is staged.
