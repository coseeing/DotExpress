# Config Alignment (P0-1) Design

## Goal

Bring `client/config.py` and its tests back into agreement and stop it from silently swallowing I/O errors. This is roadmap task P0-1 in `storage/refactor.md` (section 6.1), covering finding S-5 (section 3.1), the `config.py` entry under 5.3 (error handling) and the `config.py` entry under 5.4 (dead setters).

Three changes:

1. `_save_to_file` stops adding a `language_detection` section when it creates a new config file.
2. `_load_from_file` and `_save_to_file` log failures through the project logger instead of hiding them.
3. Remove the unused setters `set_view_font_size`, `set_view_scheme` and `set_braille_font`.

This is a small step to restore a safety net. It does not include the `ConfigStore` redesign that S-5 recommends.

## Current State (verified 2026-10-08 on `refactor/p0-1-config-alignment`, HEAD `6e5819f`)

- `config.py` uses 4-space indentation, not tabs. Keep 4 spaces.
- `_load_from_file` (lines 47-54) returns `{}` for `FileNotFoundError`, and also for every other `Exception` (corrupt JSON, `UnicodeDecodeError`, `PermissionError`, ...). Nothing is reported.
- `_save_to_file` (lines 57-70) adds `{"language_detection": {"charset_maps": DEFAULT_CHARSET_MAPS}}` at the start of the data when `CONFIG_PATH` does not exist yet (lines 59-65). It wraps the whole write in `except Exception: pass` (lines 69-70).
- Commit `6e5819f` ("align language detection with configured language") added that injection. In the same commit it updated `tests/test_config.py` to expect it, including `test_new_config_file_contains_language_detection_defaults`. It did not update `tests/test_translation_settings.py`. As a result, `test_save_persists_one_complete_settings_value` fails today. It is one of the 2 known baseline failures (full suite: 428 tests, failures=2, skipped=7).
- `get_charset_maps()` (lines 123-128) reads through `_get_dict_setting`, which already merges `DEFAULT_CHARSET_MAPS` with any stored values. Writing the defaults into the file therefore does not change what callers see.
- `languageDetection/__init__.py:365` calls `config.get_charset_maps()` and `pipeline.py:79` / `languageDetection` call `config.get_lang()` during conversion. Both re-read the config file on every call (`set_lang` has no caller in the app, so `_runtime_lang` is always unset). With a corrupt config file, a log call inside `_load_from_file` would run many times per conversion.
- Dead setters, checked with `grep -rn` over the whole repository (`*.py`):
  - `set_view_font_size` (line 184): no caller outside `config.py` except `tests/test_config.py:22`. `gui.py:849` defines an unrelated method, `BrailleFrame._set_view_font_size`, that routes through `settings.view.save_view_settings`.
  - `set_view_scheme` (line 194): only `tests/test_config.py:23`.
  - `set_braille_font` (line 204): only `tests/test_config.py:122`.
  - The app persists view settings only through `set_view_settings` (from `settings/view.py`).
- Logging convention: modules get a logger with `log.get_logger(name, filename, level)`, for example `dotexpress.translation` and `translation.log` at `WARNING`. That `FileHandler` uses `delay=True`, so importing a module neither opens a file nor creates `log/`. `tests/test_log.py` covers this. The 2026-07-20 app-data-paths spec requires it.

## Behavior Changes

### 1. No `language_detection` injection on first save

Delete the `if not os.path.exists(CONFIG_PATH): data = {...}` block from `_save_to_file`. A newly created config file then holds only the sections that the calling setter wrote.

- Values read through `get_charset_maps()` stay the same in every case. The read side already supplies the defaults.
- Existing `config.json` files that already contain a `language_detection` section (written by builds that included `6e5819f`) are left alone. The setters do read-modify-write and keep sections they do not own.
- Side effect: someone who wants to change `charset_maps` by editing the file by hand no longer finds a template section in a new file. No UI edits this setting, and the roadmap row records this trade-off ("設定檔首次建立時少一個區段"). This is a deliberate decision, not an oversight.
- `DEFAULT_CHARSET_MAPS` and `get_charset_maps()` stay. `languageDetection` uses them.
- The `os` import is still needed for `os.makedirs`, `os.path.dirname` and `os.getenv`.

### 2. Log load and save failures instead of swallowing them

Add a module-level logger to `config.py`:

```python
import logging
from log import get_logger

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)
```

- This follows the existing per-module convention. The `delay=True` file handler means importing `config` creates no file and no directory. The first record opens `<application-root>/log/config.log`. `gui.BrailleApp.OnInit` validates and creates `log/` before any normal config read.
- `log` imports only `logging`, `pathlib` and `app_paths`, and `config` already imports `app_paths`. No import cycle is added.
- Log messages are developer diagnostics in English and are not passed through gettext. No `.po` or `.mo` changes are needed.

`_save_to_file(data)`:

- Keep `except Exception` (same breadth as today). Inside the handler, call `logger.exception("Failed to save config file %s", CONFIG_PATH)`. This logs at ERROR level with the traceback. The function still returns `None` and does not raise.
- Log every failure; do not deduplicate. Saves come from the user (settings dialogs, dictionary selection) or happen once at startup (`get_or_create_client_id`), so volume stays low. Each lost write is worth recording.
- Never log the config data itself. It can contain the client id.

`_load_from_file()`:

- `FileNotFoundError` still returns `{}` and logs nothing. A missing file is normal on first run.
- Any other `Exception` still returns `{}`. It also logs a WARNING (the app falls back to defaults) with `exc_info=True`, using the message `"Failed to read config file %s; using defaults"` with `CONFIG_PATH`.
- Throttle the warning so the per-call reads described under "Current State" cannot flood the log. Keep a module-level `dict[str, str]` that maps the config path to the signature of the last failure that was logged (`f"{type(error).__name__}: {error}"`):
  - On failure, log only when the path has no entry or the signature is different, then store the signature.
  - On a successful read or a `FileNotFoundError`, remove the entry for that path. If the file breaks again later, it gets logged again.
  - Do not add a lock. Single dict operations are atomic under the GIL. The worst case under a thread race (`client_init` runs in a background thread) is one duplicate warning.
- Leave validation of what was parsed unchanged. A top-level JSON value that is not an object (for example `[]`) is still returned as it is. That is a separate existing defect, out of scope here and recorded under Out of Scope.

### 3. Remove dead setters

Delete `set_view_font_size`, `set_view_scheme` and `set_braille_font` from `config.py`. Keep `set_view_settings` and all three view getters (`get_view_font_size`, `get_view_scheme`, `get_braille_font`), because `settings/view.py` uses them.

Roadmap task P0-3 also lists these three setters (section 5.4). After P0-1 lands they are gone, and P0-3 only needs to confirm that.

## What Stays Identical

- Signatures, defaults and return values of every remaining public function and constant in `config.py`.
- `_load_from_file` and `_save_to_file` never raise. Callers (GUI event handlers, the `client_init` background thread) still see the same non-raising behavior.
- Read-modify-write semantics, including preservation of unknown or other sections.
- Write mechanics: non-atomic `open(..., "w")` plus `json.dump(..., ensure_ascii=False, indent=2)`, and `os.makedirs(..., exist_ok=True)` of the parent directory.
- `config.CONFIG_PATH` stays a module attribute read at call time. Tests keep monkeypatching it.
- The getters' existing results when the file is missing or corrupt (they fall back to defaults).
- No user-visible strings change. Nothing is shown in the GUI because of these log records.

## Out of Scope

- The `ConfigStore` repository, batching `save_translation_settings` into one write, and removing `_runtime_lang`/`set_lang` (S-5 later phases).
- Atomic writes, and protecting a corrupt file from being overwritten by the next setter. Today a corrupt file reads as `{}`, so the next save replaces it with a single section. This stays the same, and the new warning makes it visible.
- Rejecting top-level JSON values that are not objects.
- Narrowing the `except Exception` clauses.
- Other 5.3 or 5.4 items outside `config.py`.

## Test Strategy

All tests use `unittest`, run from `client/`, and keep the existing `setUp` that points `config.CONFIG_PATH` at a temporary directory.

`tests/test_translation_settings.py`

- No edits. `test_save_persists_one_complete_settings_value` must pass as written.

`tests/test_config.py`

- Remove the `"language_detection": {...}` entry from the expected dicts in the four exact-equality tests (view, conversion roundtrip, selected dictionary, client id).
- Replace `test_new_config_file_contains_language_detection_defaults` with a test that does two things:
  - after `set_output_mode("unicode")` on a fresh path, the file contains no `language_detection` key;
  - `config.get_charset_maps()` still equals `config.DEFAULT_CHARSET_MAPS`.
- Add a test that a pre-existing `language_detection` section survives a setter call.
- Move tests that used the deleted setters over to `set_view_settings`:
  - `test_view_settings_are_persisted_under_view_section` calls `set_view_settings(18, "dark", "simbraille")` and expects all three view keys.
  - The braille-font persistence test asserts that `set_view_settings` writes `braille_font` under `view`, and that `set_view_settings` keeps unrelated keys in other sections.
- New error-handling tests:
  - **Save failure is logged, not raised.** Point `CONFIG_PATH` below a path component that is a regular file. `os.makedirs` then raises an `OSError` on every platform. Call a setter under `self.assertLogs("dotexpress.config", level="ERROR")`. Assert that:
    - there is no exception;
    - one record contains the config path;
    - no config file was created.
  - **Corrupt file is logged once and defaults are returned.** Write invalid JSON. Call two different getters under `assertLogs(..., level="WARNING")`. Assert that:
    - both return their defaults;
    - exactly one warning was emitted.
  - **The warning is emitted again after recovery.** Use a corrupt file, then a valid file, then a corrupt file again, and expect two warnings in total.
  - **A missing file is silent.** Patch `config.logger` (for example with `unittest.mock.patch.object`) and assert that nothing was logged. Do not use `assertNoLogs`: it needs Python 3.10+, and the Windows build interpreter's minimum version was not verified here.
- `assertLogs` swaps the logger's handlers for the duration of the block, so these tests never write `config.log` into the real application log directory.

Unchanged safety nets that must stay green: `tests/test_view_settings.py`, `tests/test_translation_tables.py`, `tests/test_log.py`, `tests/test_app_paths.py`, `tests/test_settings_state.py`, `tests/test_language_detection_char_langinfo.py`.

## Acceptance Criteria

1. `config.py` contains no `language_detection` injection, and `grep -rn "set_view_font_size\|set_view_scheme\|set_braille_font" client --include=*.py` returns only `gui.py`'s `_set_view_font_size` method and its call site.
2. `_load_from_file` and `_save_to_file` contain no bare `pass`. Every non-`FileNotFoundError` failure goes through `config.logger` (`dotexpress.config`) as described above.
3. Importing `config` creates neither `log/` nor `config.log`. This is guaranteed by `log.get_logger` and covered by `tests/test_log.py`.
4. Focused verification passes with 0 failures and 0 errors:
   `cd client && python3 -m unittest tests.test_config tests.test_translation_settings tests.test_view_settings tests.test_translation_tables tests.test_log tests.test_app_paths -v`
5. Full suite: `cd client && python3 -m unittest discover -s tests -p "test_*.py"` reports `failures=1` (only the known P2-5 `test_conversion_service` failure), `errors=0` and `skipped=7`. The test count is 428 plus the new tests.
6. Not verifiable on this Linux host: packaged Windows behavior. Logging goes through the same `log.get_logger` path that `gui`, `client_init` and the translation provider already use on Windows, and no Windows-specific code changes.

## Risks

- **Less discoverable `charset_maps`** (low): newly created config files no longer contain the template section. The read-side defaults are unchanged. The roadmap accepts this trade-off.
- **Log flood with a corrupt config** (mitigated): handled by the throttle keyed on path and signature.
- **Logging before `log/` exists** (low): if a config read fails before `prepare_application_directories` runs, the `FileHandler` cannot open its file. The standard library's `Handler.handleError` then prints a "Logging error" notice to stderr (when one exists) and continues. It never crashes. In the normal startup order, `log/` is validated before the main frame reads settings.
- **Tests writing to the real log directory** (low): only possible if a future test triggers a failure path without `assertLogs` or a patched logger. The test strategy requires one or the other.
- **Overlap with P0-3** (none functionally): P0-3 must skip the three setters that P0-1 already removed.
