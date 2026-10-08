# Config Alignment (P0-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `client/config.py` and its tests back into agreement, log config load/save failures instead of swallowing them, and remove three dead view setters.

**Architecture:** All production changes stay inside `client/config.py`. A module-level `dotexpress.config` logger (built with the existing `log.get_logger`) records save failures at ERROR and load failures at WARNING. Load warnings are throttled per config path by failure signature. The `language_detection.charset_maps` injection in `_save_to_file` is kept unchanged; the stale test in `tests/test_translation_settings.py` is aligned with it instead.

**Tech Stack:** Python 3 (3.9+ syntax already required by `config.py`), `json`, `logging`, `unittest`, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-10-08-p0-1-config-alignment-design.md` (authoritative; its Decisions section overrides the roadmap row in `storage/refactor.md` section 6.1).

## Global Constraints

- Branch: `refactor/p0-1-config-alignment`. Never switch to or merge into `main`, never push, never rewrite history.
- `client/config.py` and `client/tests/test_config.py` use 4-space indentation. Keep 4 spaces. Do not reformat unrelated code.
- Keep the `if not os.path.exists(CONFIG_PATH): data = {"language_detection": {...}, **data}` block in `_save_to_file` exactly as it is.
- `_load_from_file` and `_save_to_file` never raise. Catch breadth stays `except Exception`.
- Logger: `get_logger("dotexpress.config", "config.log", level=logging.WARNING)`. Importing `config` must not create `log/` or `config.log` (guaranteed by `delay=True` in `log.get_logger`).
- Save failure: `"Failed to save config file %s"` with `CONFIG_PATH`, ERROR level, with traceback, on every failure. Never log the config data.
- Load failure (anything except `FileNotFoundError`): `"Failed to read config file %s; using defaults"` with the path, WARNING level, with traceback, throttled by `f"{type(error).__name__}: {error}"` per path. `FileNotFoundError` and successful reads clear the path's entry. No lock.
- Do not validate the parsed JSON shape (a top-level `[]` is still returned as is).
- Remove `set_view_font_size`, `set_view_scheme`, `set_braille_font`. Keep `set_view_settings` and the three view getters.
- Log messages are English developer diagnostics, not gettext strings. No `.po`/`.mo` changes.
- Tests: `unittest` only, run from `client/`. Do not use `assertNoLogs` (3.10+) or parenthesized multi-item `with (...)` (3.10+); the Windows build interpreter's minimum version is unverified.
- Every test that drives a config failure path must capture logs with `assertLogs` or patch `config.logger`, so the suite never writes `client/log/config.log`.
- Test command prefix used below: `PY=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad/venv/bin/python` (on another machine, use any Python 3.9+ with client deps, e.g. `python3`).
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Spec Correction (decided in this plan)

The spec's Risks section says that if a config failure is logged before `log/` exists, "the standard library's `Handler.handleError` ... continues. It never crashes." That is wrong. `logging.FileHandler.emit` with `delay=True` calls `self._open()` **outside** the `try`/`handleError` block, so a missing or unwritable log directory raises `FileNotFoundError`/`PermissionError` out of the logging call. Verified on this host (Python 3.14.4, `/usr/lib/python3.14/logging/__init__.py`, `FileHandler.emit`); the same structure exists in earlier CPython 3 releases.

Without a guard, a logging call inside the `except` handlers would break the spec's own invariant "`_load_from_file` and `_save_to_file` never raise". Exposure is real outside the normal GUI startup order: `main.py` and other non-GUI entry points, a fresh clone running tests without `client/log/`, or an unwritable `log/`.

Resolution: route both log calls through one small helper, `_log_current_exception(level, message, *args)`, that calls `logger.log(level, message, *args, exc_info=True)` and drops the record if the handler raises `OSError`. The records produced are identical to `logger.exception(...)` / `logger.warning(..., exc_info=True)`. `_load_from_file` and `_save_to_file` themselves still contain no bare `pass` (Acceptance Criterion 2). Two tests pin this (Task 3 and Task 4).

## Review Focus

1. The log file cannot be opened (`log/` missing or unwritable) when a config read or save fails: the app must still fall back to defaults / drop the write without raising. Tests: `test_save_failure_does_not_raise_when_log_file_cannot_be_opened` (Task 3), `test_load_failure_does_not_raise_when_log_file_cannot_be_opened` (Task 4).
2. The same config file fails in a new way (invalid JSON, then invalid UTF-8 or a permission error): the new failure must be logged even though the path was already throttled. Test: `test_different_failure_on_same_path_is_logged_again` (Task 4).
3. A save fails while the data contains the client id: the log must name the path and include the traceback but never the data. Test: `test_save_failure_log_does_not_contain_config_data` (Task 3).
4. The user retries a failing save (settings dialog OK pressed twice): each failure must be logged, with no deduplication. Test: `test_every_save_failure_is_logged` (Task 3).
5. Two different config paths are corrupt (the throttle is keyed by path; tests and app-root changes switch `CONFIG_PATH`): each path must get its own warning. Test: `test_corrupt_files_at_different_paths_are_each_logged` (Task 4).

## File Map

- Modify `client/tests/test_translation_settings.py` (Task 1): expected dict only.
- Modify `client/config.py` (Tasks 2-4): delete three setters; add logger, helper, throttle dict; replace the two silent `except` bodies.
- Modify `client/tests/test_config.py` (Tasks 2-4): migrate two tests to `set_view_settings`; add a setter-removal guard; add `ConfigSaveFailureLoggingTest` and `ConfigLoadFailureLoggingTest`.

---

### Task 1: Align the stale translation-settings save test with the charset-maps injection

**Files:**
- Modify: `client/tests/test_translation_settings.py:63-78`

**Interfaces:**
- Consumes: `config.DEFAULT_CHARSET_MAPS` (existing).
- Produces: nothing new.

- [ ] **Step 1: Confirm the test fails today (it is the failing test for this task)**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_translation_settings -v`
Expected: `FAILED (failures=1)` in `test_save_persists_one_complete_settings_value`; the diff shows the actual file has an extra `'language_detection': {'charset_maps': {...}}` key.

- [ ] **Step 2: Update the expected dict**

Replace the body of `test_save_persists_one_complete_settings_value` with:

```python
    def test_save_persists_one_complete_settings_value(self) -> None:
        settings = TranslationSettings("ascii", 64, "math")

        save_translation_settings(settings)

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            self.assertEqual(
                json.load(f),
                {
                    "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                    "conversion": {
                        config.OUTPUT_MODE_KEY: "ascii",
                        config.WIDTH_KEY: 64,
                        config.SELECTED_DICTIONARY_KEY: "math",
                    },
                },
            )
```

No change to `config.py` in this task.

- [ ] **Step 3: Run to verify it passes**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_translation_settings tests.test_config -v`
Expected: `OK` (3 + 14 tests).

- [ ] **Step 4: Commit**

```bash
git add client/tests/test_translation_settings.py
git commit -m "test: expect language detection defaults in translation settings save

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Remove the unused single-value view setters

**Files:**
- Modify: `client/config.py:184-185` (`set_view_font_size`), `:194-195` (`set_view_scheme`), `:204-205` (`set_braille_font`)
- Modify: `client/tests/test_config.py:21-39` and `:121-136`

**Interfaces:**
- Consumes: `config.set_view_settings(font_size: int, scheme: str, braille_font: str) -> None` (existing, unchanged).
- Produces: `config` no longer has `set_view_font_size`, `set_view_scheme`, `set_braille_font`. P0-3 relies on this.

- [ ] **Step 1: Migrate the two tests and add the removal guard**

In `client/tests/test_config.py`, replace `test_view_settings_are_persisted_under_view_section` (lines 21-39) with:

```python
    def test_view_settings_are_persisted_under_view_section(self) -> None:
        config.set_view_settings(18, "dark", "simbraille")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "view": {
                    "font_size": 18,
                    "scheme": "dark",
                    "braille_font": "simbraille",
                }
            },
        )
        self.assertEqual(config.get_view_font_size(), 18)
        self.assertEqual(config.get_view_scheme(), "dark")
        self.assertEqual(config.get_braille_font("default"), "simbraille")
```

Replace `test_braille_font_setting_is_persisted_under_view_section` (lines 121-136) with these two tests:

```python
    def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "conversion": {"width": 52},
                    "view": {"font_size": 20, "custom": "kept"},
                },
                f,
            )

        config.set_view_settings(14, "light", "default")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "conversion": {"width": 52},
                "view": {
                    "font_size": 14,
                    "custom": "kept",
                    "scheme": "light",
                    "braille_font": "default",
                },
            },
        )
        self.assertEqual(config.get_braille_font(), "default")

    def test_unused_single_view_setters_are_removed(self) -> None:
        for name in ("set_view_font_size", "set_view_scheme", "set_braille_font"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(config, name))
```

Notes: the file already exists in the second test, so no `language_detection` section is injected (injection only happens when the file is new). The removal guard is a small addition beyond the spec's test list; it gives this deletion a failing test and lets P0-3 confirm the removal mechanically.

- [ ] **Step 2: Run to verify the guard fails**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config -v`
Expected: `FAILED (failures=3)`, all from `test_unused_single_view_setters_are_removed` subtests (`AssertionError: True is not false` for `set_view_font_size`, `set_view_scheme`, `set_braille_font`). The two migrated tests already pass.

- [ ] **Step 3: Delete the three setters**

In `client/config.py`, delete these three functions and the two blank lines after each (leave the getters and `set_view_settings` intact):

```python
def set_view_font_size(font_size: int) -> None:
    _set_section_value(VIEW_SECTION, FONT_SIZE_KEY, font_size)
```

```python
def set_view_scheme(scheme: str) -> None:
    _set_section_value(VIEW_SECTION, SCHEME_KEY, scheme)
```

```python
def set_braille_font(braille_font: str) -> None:
    _set_section_value(VIEW_SECTION, BRAILLE_FONT_KEY, braille_font)
```

- [ ] **Step 4: Run to verify it passes and nothing else referenced the setters**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config tests.test_view_settings tests.test_settings_state -v`
Expected: `OK`.

Run: `cd /workspace/DotExpress && grep -rn "set_view_font_size\|set_view_scheme\|set_braille_font" client --include=*.py`
Expected: exactly `client/gui.py:849` (`def _set_view_font_size`) and `client/gui.py:1228` (its call site), plus the three name strings inside `test_unused_single_view_setters_are_removed` in `client/tests/test_config.py`.

- [ ] **Step 5: Commit**

```bash
git add client/config.py client/tests/test_config.py
git commit -m "refactor: remove unused config view setters

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Log config save failures instead of swallowing them

**Files:**
- Modify: `client/config.py` (imports, new `logger`, new `_log_current_exception`, `_save_to_file` except body at lines 69-70)
- Modify: `client/tests/test_config.py` (imports; new class `ConfigSaveFailureLoggingTest`)

**Interfaces:**
- Consumes: `log.get_logger(name: str, filename: str = "init.log", level: int = logging.ERROR) -> logging.Logger` (existing).
- Produces: `config.logger: logging.Logger` named `"dotexpress.config"`; `config._log_current_exception(level: int, message: str, *args: object) -> None` (must be called from inside an `except` block; logs with `exc_info=True`; swallows only `OSError` raised by the logging call). Task 4 uses both.

- [ ] **Step 1: Write the failing tests**

In `client/tests/test_config.py`, change the import block at the top to:

```python
import json
import logging
import tempfile
import unittest
import gettext
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import config
```

Add this class after `ConfigTest` (before `if __name__ == "__main__":`):

```python
class ConfigSaveFailureLoggingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self._blocker = Path(self._tmpdir.name) / "blocker"
        self._blocker.write_text("not a directory", encoding="utf-8")
        config.CONFIG_PATH = str(self._blocker / "nested" / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def test_save_failure_is_logged_and_not_raised(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            config.set_output_mode("ascii")

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIsNotNone(record.exc_info)
        self.assertIn(config.CONFIG_PATH, record.getMessage())
        self.assertFalse(Path(config.CONFIG_PATH).exists())
        self.assertTrue(self._blocker.is_file())

    def test_every_save_failure_is_logged(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            config.set_output_mode("ascii")
            config.set_conversion_width(52)

        self.assertEqual(len(captured.records), 2)

    def test_save_failure_log_does_not_contain_config_data(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            client_id = config.get_or_create_client_id()

        UUID(client_id)
        self.assertNotIn(client_id, "\n".join(captured.output))

    def test_save_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                config.set_output_mode("ascii")
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())
        self.assertFalse(Path(config.CONFIG_PATH).exists())
```

Why the blocker file: `CONFIG_PATH` sits below a regular file, so `os.makedirs` raises an `OSError` on every platform. On Linux the preceding `_load_from_file` read also fails with `NotADirectoryError` (Windows reports `FileNotFoundError`); after Task 4 that may add a WARNING, which `assertLogs(level="ERROR")` filters out, so the ERROR counts above hold on both platforms.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config.ConfigSaveFailureLoggingTest -v`
Expected: `FAILED (failures=3, errors=1)`:
- the three `assertLogs` tests fail with `AssertionError: no logs of level ERROR or higher triggered on dotexpress.config`;
- `test_save_failure_does_not_raise_when_log_file_cannot_be_opened` errors with `AttributeError: <module 'config' ...> does not have the attribute 'logger'`.

- [ ] **Step 3: Implement the logger, helper and save logging**

In `client/config.py`, change the imports and add the logger right after them:

```python
import json
import logging
import os
from typing import Optional
from uuid import uuid4

from app_paths import get_config_path
from log import get_logger

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)
```

Add this helper directly above `_load_from_file`:

```python
def _log_current_exception(level: int, message: str, *args: object) -> None:
    try:
        logger.log(level, message, *args, exc_info=True)
    except OSError:
        # A delay=True FileHandler opens its file inside emit() and raises if
        # log/ is missing or unwritable. Config I/O must never raise, so a
        # diagnostic that cannot be written is dropped.
        pass
```

Replace the end of `_save_to_file`:

```python
    except Exception:
        pass
```

with:

```python
    except Exception:
        _log_current_exception(logging.ERROR, "Failed to save config file %s", CONFIG_PATH)
```

Leave the rest of `_save_to_file` (including the `language_detection` injection) and `_load_from_file` unchanged in this task.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config tests.test_log tests.test_app_paths -v`
Expected: `OK`.

Run: `cd /workspace/DotExpress/client && test ! -e log/config.log && echo "no config.log"`
Expected: `no config.log`.

- [ ] **Step 5: Commit**

```bash
git add client/config.py client/tests/test_config.py
git commit -m "fix: log config save failures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Log config load failures once per path and signature

**Files:**
- Modify: `client/config.py` (new `_logged_load_failures`; rewrite `_load_from_file`)
- Modify: `client/tests/test_config.py` (new class `ConfigLoadFailureLoggingTest`)

**Interfaces:**
- Consumes: `config.logger`, `config._log_current_exception(level, message, *args)` from Task 3.
- Produces: `config._logged_load_failures: dict[str, str]` (config path -> last logged failure signature). Tests clear it; nothing else reads it.

- [ ] **Step 1: Write the failing tests**

Add this class to `client/tests/test_config.py` after `ConfigSaveFailureLoggingTest`:

```python
class ConfigLoadFailureLoggingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
        config._logged_load_failures.clear()

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        config._logged_load_failures.clear()
        self._tmpdir.cleanup()

    def _write_raw(self, content: bytes) -> None:
        with open(config.CONFIG_PATH, "wb") as f:
            f.write(content)

    def _warnings(self, captured) -> list[logging.LogRecord]:
        return [r for r in captured.records if r.levelno == logging.WARNING]

    def test_corrupt_file_is_logged_once_and_defaults_are_returned(self) -> None:
        self._write_raw(b"{not json")

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            output_mode = config.get_output_mode()
            width = config.get_conversion_width()

        self.assertEqual(output_mode, config.DEFAULT_OUTPUT_MODE)
        self.assertEqual(width, config.DEFAULT_CONVERSION_WIDTH)
        warnings = self._warnings(captured)
        self.assertEqual(len(warnings), 1)
        self.assertIn(config.CONFIG_PATH, warnings[0].getMessage())
        self.assertIn("using defaults", warnings[0].getMessage())
        self.assertIsNotNone(warnings[0].exc_info)

    def test_warning_is_emitted_again_after_recovery(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            self._write_raw(b'{"conversion": {"output_mode": "ascii"}}')
            self.assertEqual(config.get_output_mode(), "ascii")
            self._write_raw(b"{not json")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_different_failure_on_same_path_is_logged_again(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            self._write_raw(b"\xff\xfe\x00")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_corrupt_files_at_different_paths_are_each_logged(self) -> None:
        other_path = str(Path(self._tmpdir.name) / "other.json")
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            config.CONFIG_PATH = other_path
            self._write_raw(b"{not json")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_missing_file_is_not_logged(self) -> None:
        with patch.object(config, "logger") as logger:
            self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
            self.assertEqual(config.get_charset_maps(), config.DEFAULT_CHARSET_MAPS)

        self.assertEqual(logger.mock_calls, [])

    def test_load_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        self._write_raw(b"{not json")
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())
```

Notes:
- `b"\xff\xfe\x00"` is invalid UTF-8, so it raises `UnicodeDecodeError` instead of `JSONDecodeError`: a different signature on the same path.
- `test_missing_file_is_not_logged` patches `config.logger` instead of using `assertNoLogs` (3.10+ only). It is a regression guard: it would already pass once `_logged_load_failures` exists, and must keep passing.
- `tearDown` restores `CONFIG_PATH`, so reassigning it inside `test_corrupt_files_at_different_paths_are_each_logged` is safe.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config.ConfigLoadFailureLoggingTest -v`
Expected: `FAILED (errors=6)`, each from `setUp` with `AttributeError: module 'config' has no attribute '_logged_load_failures'`. (If the attribute alone were added, the four `assertLogs` tests would still fail with `AssertionError: no logs of level WARNING or higher triggered on dotexpress.config`.)

- [ ] **Step 3: Implement throttled load logging**

In `client/config.py`, add below `_runtime_lang: Optional[str] = None`:

```python

# Config path -> signature of the last load failure that was logged for it.
_logged_load_failures: dict[str, str] = {}
```

Replace `_load_from_file` with:

```python
def _load_from_file() -> dict:
    path = CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        _logged_load_failures.pop(path, None)
        return {}
    except Exception as error:
        signature = f"{type(error).__name__}: {error}"
        if _logged_load_failures.get(path) != signature:
            _logged_load_failures[path] = signature
            _log_current_exception(
                logging.WARNING,
                "Failed to read config file %s; using defaults",
                path,
            )
        return {}
    _logged_load_failures.pop(path, None)
    return data
```

Details that matter:
- `path = CONFIG_PATH` is read once per call so the throttle key and the logged path match the file that was opened. `CONFIG_PATH` stays a module attribute read at call time.
- The parsed value is returned as is (no shape validation; out of scope).
- No lock: single dict operations are atomic under the GIL; a thread race costs at most one duplicate warning.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config -v`
Expected: `OK` (25 tests).

- [ ] **Step 5: Commit**

```bash
git add client/config.py client/tests/test_config.py
git commit -m "fix: log config read failures once per path

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Final verification (no commit unless something had to be fixed)

- [ ] **Step 1: Focused verification (Acceptance Criterion 4)**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_config tests.test_translation_settings tests.test_view_settings tests.test_translation_tables tests.test_log tests.test_app_paths -v`
Expected: `OK`, 0 failures, 0 errors.

- [ ] **Step 2: Other safety nets named by the spec**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_settings_state tests.test_language_detection_char_langinfo -v`
Expected: `OK`.

- [ ] **Step 3: Full suite (Acceptance Criterion 5)**

Run: `cd /workspace/DotExpress/client && $PY -m unittest discover -s tests -p "test_*.py"`
Expected: `Ran 439 tests` (428 baseline + 11 new: 1 in Task 2, 4 in Task 3, 6 in Task 4; the migrated braille-font test replaces the old one), `FAILED (failures=1, skipped=7)`, 0 errors. The single failure must be `tests.test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` (P2-5). Any other failure or error is a regression to fix before handoff.

- [ ] **Step 4: Static acceptance checks (Criteria 1-3)**

Run: `cd /workspace/DotExpress && grep -rn "set_view_font_size\|set_view_scheme\|set_braille_font" client --include=*.py | grep -v "client/tests/test_config.py"`
Expected: only `client/gui.py:849` and `client/gui.py:1228`.

Run: `cd /workspace/DotExpress/client && sed -n '/^def _load_from_file/,/^def _coerce_int/p' config.py | grep -n "pass"`
Expected: no output (no bare `pass` in `_load_from_file` or `_save_to_file`).

Run: `cd /workspace/DotExpress/client && grep -n '"language_detection"' config.py`
Expected: the injection line inside `_save_to_file` is still present.

Run: `cd /workspace/DotExpress/client && test ! -e log/config.log && echo "no config.log"`
Expected: `no config.log` (tests never wrote to the real log directory; importing `config` created nothing).

- [ ] **Step 5: Record what cannot be verified here**

State in the handoff: packaged Windows behavior was not run (Linux host). Logging uses the same `log.get_logger` path as `gui`, `client_init` and the translation provider; no Windows-specific code changed. No user-facing strings changed, so no `.po`/`.mo` regeneration.
