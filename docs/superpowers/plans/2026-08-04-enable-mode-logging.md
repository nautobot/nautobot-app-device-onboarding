# Netmiko Enable-Mode Decision Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit one info-level job log per host showing its logical platform and the resolved Netmiko enable-mode state.

**Architecture:** Reuse the existing `NornirLogger.info()` path in the shared `netmiko_send_commands()` task. Compute the state with the existing `_platform_requires_enable_mode()` helper, log it once before command execution, and leave credential handling and Netmiko command arguments unchanged.

**Tech Stack:** Python, Django settings, Nornir task execution, unittest/mocks, Nautobot `NornirLogger`.

## Global Constraints

- Log exactly once per host task, not once per command.
- Use info level through the existing `logger.info()` interface.
- Include the logical platform identifier and the resolved enabled/disabled state.
- Do not log usernames, passwords, enable secrets, or other credential values.
- Preserve the existing per-platform behavior: absent/empty configuration resolves to `enable=False`, and only listed logical platforms resolve to `enable=True`.
- Do not change the original NAPALM onboarding job or secret-provider behavior.

---

### Task 1: Log the resolved platform enable-mode decision

**Files:**
- Modify: `nautobot_device_onboarding/nornir_plays/command_getter.py:128-170`
- Test: `nautobot_device_onboarding/tests/test_command_getter.py:27-75`

**Interfaces:**
- Consumes: `_platform_requires_enable_mode(platform: str) -> bool` and the existing `logger` argument passed to `netmiko_send_commands()`.
- Produces: one info log before the first `netmiko_send_command()` call, using the exact message format shown by `Platform 'cisco_platform_1' enable mode: enabled` and substituting the current platform and state.

- [ ] **Step 1: Extend the focused test helper to capture the logger.**

In `TestNetmikoEnableModeConfiguration._run_single_raw_command()`, create a named `MagicMock` logger, pass it to `netmiko_send_commands()`, and return both the captured `enable` value and logger. Update the three existing tests to unpack the returned tuple without changing their current enable assertions.

- [ ] **Step 2: Add the failing logging assertions.**

Add assertions to the listed and unlisted platform tests:

```python
enable, logger = self._run_single_raw_command("cisco_platform_1", ["cisco_platform_1"])
self.assertTrue(enable)
logger.info.assert_called_once_with("Platform 'cisco_platform_1' enable mode: enabled")

enable, logger = self._run_single_raw_command("cisco_platform_2", ["cisco_platform_1"])
self.assertFalse(enable)
logger.info.assert_called_once_with("Platform 'cisco_platform_2' enable mode: disabled")
```

Run the focused tests and verify they fail because the decision log is not yet emitted:

```bash
source .venv/bin/activate
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
```

Expected: the existing enable assertions pass, but the new `logger.info` assertions fail.

- [ ] **Step 3: Add the minimal info-level log.**

Immediately after calculating `enable_mode` in `netmiko_send_commands()`, add:

```python
logger.info(
    f"Platform '{task.host.platform}' enable mode: {'enabled' if enable_mode else 'disabled'}"
)
```

Do not add logging inside the command loop and do not include credential values.

- [ ] **Step 4: Run focused tests and formatting checks.**

Run:

```bash
source .venv/bin/activate
invoke unittest --label nautobot_device_onboarding.tests.test_command_getter --keepdb
invoke ruff
git diff --check
```

Expected: the focused command-getter tests pass, Ruff reports no violations, and `git diff --check` is clean. If host port 8080 is occupied, use the repository’s established temporary test-only host-port remap and revert it before committing.

- [ ] **Step 5: Commit the implementation.**

```bash
git add nautobot_device_onboarding/nornir_plays/command_getter.py nautobot_device_onboarding/tests/test_command_getter.py
git commit -m "feat: log netmiko enable mode per platform"
```

After the commit, run `git status --short --branch` and confirm the worktree is clean.
