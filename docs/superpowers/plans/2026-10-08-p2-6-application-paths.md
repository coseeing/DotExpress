# Application Paths Injection (P2-6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `BrailleApp.OnInit` becomes the one place that resolves application data: it builds one `ApplicationPaths`, validates that object, cleans its `dual_view/`, builds one `config.ConfigStore(paths.config)` and hands both to `BrailleFrame` (and the store to client init). `config.CONFIG_PATH`, the module-level config functions and the five `app_paths.get_*` helpers are deleted, every dictionary, workspace and dual-view folder parameter is required, the logger keeps resolving its folder through `log._log_directory()`, and `ConversionPresenter` moves from `conversion/presenter.py` to `ui/conversion_presenter.py` behind an import guard. Pure refactor: same files in the same places, same startup order and error dialog, same `config.json` bytes, no msgid change (353), both fixtures untouched.

**Architecture:** Five commits in the spec's order. Task 1 characterizes today's behavior through one helper per test group (frame wiring, startup order, client init, logger folder, demo, `get_lang`); the helpers reach today's seams (`app_paths.get_application_root`, `config.CONFIG_PATH`), and a throwaway mutant runner shows that 26 deliberate breakages are each caught. Task 2 adds `ConfigStore` behind the module functions red-first. Task 3 switches the helpers and the existing tests to stores and paths and adds three wiring tests (red), then injects the paths and the store (green); 22 mutants of the new wiring are caught. Task 4 adds allow-list guards (red), then deletes the implicit defaults (green); 8 guard mutants are caught. Task 5 adds the `conversion` layer guard (red), then moves the presenter.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `inspect`, `ast`, `json`, `contextlib`, `functools`, `dataclasses`). wxPython is not installed: `tests/test_gui_document_flows.py` runs `gui` under `tests/wx_stub.py`'s gui profile; everything else runs without a stub.

**Spec:** `docs/superpowers/specs/2026-10-08-p2-6-application-paths-design.md` (authoritative, commit `2c2fb1e`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p2-6-application-paths`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (28 code and test files, nothing else): production `client/app_paths.py`, `client/config.py`, `client/log.py`, `client/gui.py`, `client/main.py`, `client/client_init.py`, `client/settings/translation.py`, `client/settings/view.py`, `client/settings/translation_tables.py`, `client/dictionaries/manager.py`, `client/dictionaries/name_prompt.py`, `client/documents/workspace.py`, `client/dual_view/files.py`, `client/documents/export_coordinator.py` (docstring), `client/conversion/presenter.py` -> `client/ui/conversion_presenter.py` (rename, body unchanged); tests `test_gui_document_flows`, `test_config`, `test_client_init`, `test_log`, `test_main_demo`, `test_app_paths`, `test_translation_import_isolation`, `test_view_settings`, `test_translation_tables`, `test_translation_settings`, `test_conversion_language_explicit`, `test_conversion_presenter`, `test_export_coordinator`. Never touch `client/locales/`, `client/tests/fixtures/`, `client/tests/wx_stub.py`, `client/settings/__init__.py`, `client/dictionaries/presenter.py`, `client/documents/workspace_service.py`, `scripts/` or the historical specs and plans.
- Indentation: `client/gui.py` and `client/dictionaries/name_prompt.py` use tabs (`gui.py`'s parenthesized imports mix tabs and spaces; keep each line as it is); every other touched file uses 4 spaces. The patches carry the exact characters (several test modules contain zh_TW text as UTF-8); run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes and no msgid changes: the source msgid set (`source msgids: 353`) is compared with the Task 0 snapshot in Task 6 (`SOURCE == SAVED`). No `.po`/`.mo` change, no `generate_pot.bat` run.
- Fixtures are never touched: `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`), checked in Task 0 and Task 6.
- No test writes real application data. Every new test works in a `TemporaryDirectory`; the frame wiring helper points the real application root at an empty decoy folder from Task 3 on. Task 6 compares a snapshot of `client/` application data taken before and after a full suite run (correction 4).
- Out of scope (spec): the S-5 store shape, batching the three translation-settings writes, removing `set_lang`/`_runtime_lang`, injecting the log folder (D10), the development-mode `dual_view/` package/HTML overlap, splitting `test_gui_document_flows.py`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed` and absolute paths are stripped from errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p26impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.
- Baseline (re-verified at `2c2fb1e`, the spec commit; code identical to `f1ff5b3` = `main`): `$PY -m unittest discover -s tests` gives `Ran 1043 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: AC6's presenter grep cannot print nothing.** In `grep -rn "conversion.presenter\|conversion/presenter"` the `.` matches any character, so it matches `_conversion_presenter` (frame attribute, 4 lines in `gui.py`), `ui.conversion_presenter` (the new import) and `test_conversion_presenter`; on the spec commit it already prints 23 lines, and after Task 5 it prints 24. The check meant is the literal module path, `grep -rn "conversion\.presenter\|conversion/presenter"` (escaped dot): 5 lines today, nothing after Task 5. Task 6 runs the escaped form.
2. **Factual correction: `ConfigModuleShapeTest` cannot ask that no `config` attribute starts with `get_`.** `config.py` imports `get_logger` from `log`, so that attribute exists for good. The guard checks the functions *defined in* `config` (`inspect.isfunction(value) and value.__module__ == config.__name__`): none may start with `get_` or `set_`, and no module name may contain `PATH`.
3. **Factual correction: "two requests read the file twice" (Test Plan A item 1).** With `TEXT2BRAILLE_LANG` unset and no runtime override, one conversion request reads `config.json` twice (`get_lang`, then `get_charset_maps`), so two requests read it four times. The test pins `(2, 4)` and also rewrites the file between the requests (the second request sees the new language), which proves nothing is cached.
4. **Clarification: AC7 and "no test writes real app data".** The baseline suite already appends to `client/log/dual_view.log`, `init.log`, `math.log` and `translation.log` (the loggers are bound to the real log folder at import; D10 keeps that, the log work belongs to P2-7). And `client/dictionary/` is git-ignored user data that may exist in a working checkout (it does in `/workspace/DotExpress`). So Task 6 does not ask for absence: it snapshots `config.json`/`workspace/` existence, the sha256 of every file under `dictionary/`, the non-source entries of `dual_view/` and the names in `log/`, runs the full suite, snapshots again and requires an empty diff (no new or changed app data, no new log file). It also shows that `config.json` and `workspace/` do not exist, as AC7 says.
5. **Refinement: the new-test count is fixed at 28 (1043 -> 1071).** Task 1 adds 14 (`ApplicationPathsWiringCharacterizationTest` 4, `BrailleAppLifecycleTest` 2, `ClientInitConfigCharacterizationTest` 3, `test_log` 1, `test_main_demo` 1, `ConfigLanguageOverrideCharacterizationTest` 3); Task 2 adds 5 (`ConfigStoreTest`); Task 3 adds 3 (`test_app_passes_the_validated_paths_and_one_store`, `test_app_exit_cleans_the_validated_dual_view_folder`, `test_frame_requires_paths_and_config_store`); Task 4 adds 5 (`ApplicationPathsApiTest` 3, `ConfigModuleShapeTest` 1, `test_client_init_does_not_import_config`); Task 5 adds 1 (`test_conversion_package_imports_no_higher_layer`). Per module at the end: `test_gui_document_flows` 151 -> 160, `test_config` 25 -> 34, `test_client_init` 7 -> 10, `test_app_paths` 7 -> 10, `test_translation_import_isolation` 4 -> 6, `test_log` 1 -> 2, `test_main_demo` 2 -> 3. AC1's roadmap command therefore runs 204 tests.
6. **Refinement: Part A additions beyond the spec's list (Review Focus below).** The client-init group also asserts the worker thread is a daemon and that starting client init creates no client id before the worker runs; the selected-dictionary test uses a zh_TW name and compares the exact file text (`ensure_ascii=False`, `indent=2`); the logger test passes `"nested/sample.log"` to pin `Path(filename).name`; the order test also asserts no error dialog; the stop test asserts the dialog names the failing path.
7. **Refinement: the frame wiring helper uses a decoy root from Task 3 on.** After the switch, `make_frame` builds paths and a store for `self.root` and patches `app_paths.get_application_root` (and, until Task 4 deletes it, `config.CONFIG_PATH`) to an empty sibling folder. A regression that still resolves a folder implicitly then lands in the decoy, fails the `self.root` assertions, and never writes into `client/`. Task 4 drops the `CONFIG_PATH` half (the helper is the only part steps 3 and 4 change, as the spec requires). The client-init and demo helpers drop their `CONFIG_PATH` patch in Task 3, so a regression to the module functions fails there instead of being masked.
8. **Refinement: `gui.py` keeps importing `get_dictionary_directory` until Task 4.** Task 3 stops calling it and drops the now unused `get_workspace_directory`, `get_lang`, `get_charset_maps` and `set_selected_dictionary` imports, but the P0-6 guard `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` lists `get_dictionary_directory` as kept, and the spec changes that guard in step 4. Task 4 removes the import and the guard entry together (intentional guard change, called out in the commit message). The guard never gains an absence check for the name, so AC6's grep stays empty.
9. **Refinement: guards that are green on arrival are shown by mutation.** `test_client_init_does_not_import_config` (client init stops importing `config` in Task 3, per D7) and the rewritten `test_consumers_use_the_common_application_root` pass before Task 4's production change; Task 4's `guards` mutant set shows each guard fails when its rule is broken (for example `client-init-imports-config`).
10. **Refinement: `ConfigStoreTest.test_store_writes_the_documented_config_bytes`** compares the store with the module functions only while they exist (Tasks 2-3) and always with the literal expected text; Task 4 removes the module half. The two throttle tests hold both stores in variables, so a per-instance throttle cannot pass by `id()` reuse.
11. **Clarification: two lifecycle tests used `Mock()` paths.** `test_app_cleans_stale_dual_view_html_after_path_validation` and `test_app_reports_startup_cleanup_failure_before_runtime` built `paths = Mock()`; `ConfigStore(Mock().config)` raises `TypeError` in `Path()`, so Task 3 gives them real `ApplicationPaths` (`make_paths(Path("C:/DotExpress"))`) and patches `gui.build_application_paths` to return them. Their assertions are unchanged. Under the wx stub a missing attribute reads as a no-op function, so every `OnExit` test sets `app.paths` (the spec says so; this is why it is required).
12. **Clarification: `config.py` gains `from __future__ import annotations`** for the `Path | str` annotation, as the other modules that use PEP 604 unions do (`app_paths.py`, `dictionaries/manager.py`, `documents/workspace.py`, `dual_view/files.py`). No runtime effect.

Everything else in the spec was re-checked at `2c2fb1e`: the current-state line numbers (`config.py:15`, `gui.py:138, 147, 334, 1056, 1074`, `client_init.py:14, 145-149`, `main.py:5, 23`), the 15 lines of AC6's optional-parameter grep before the change, the callers of every changed function (no production or test caller passes `None` or omits a folder), the tests that patch `CONFIG_PATH` and the gui seams, the baseline counts and the msgid set.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `2c2fb1e` (`$SP/p26plan/dry`, never the repo), one commit per task; after each task the full suite and 20 shuffle seeds gave the counts below with the P2-5 case as the only failure, and after Task 5 the pair orders, the msgid scan, the app-data snapshot and every acceptance criterion passed. The patches in this plan are `git diff`s of the dry clone's commits (each task split into its test step and its production step; Task 5's rename is a `git mv`). Then this file's blocks were run in order on fresh clones (`$SP/p26plan/replay1` onwards, each with a stand-in plan commit and a local `main` at `f1ff5b3`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 5 commits applied, every expected block matched byte for byte on the final replay, and the resulting `client/` tree is identical to the dry clone's. Final production sha256: `client/app_paths.py` `72da44f99b9e5822b2881c336a6bd09854a5b825386bb5a12c32b2b22c98e35e`, `client/config.py` `d84d08ba4ae2cad35f2c0fa087b14682a0f6d9f9e2e332709b23eee61e87283a`, `client/log.py` `57bd8585e64c0c469a8c83d8f818878c8d8e203def3c421e063b7b8c986ea5d0`, `client/gui.py` `abb5392ed437279c34a593f7774ae1489c5fb68d96fa6f7d249045bb8c0eeac3`, `client/main.py` `43003bd971095c05803d7500f91a7595bd259d764f95d30574bb084103d5bede`, `client/client_init.py` `dc5c53a8b47b6ddd80996c544545cbe32be671968d4666d9d9e88258e38d2652`, `client/settings/translation.py` `ce12c6051fbe603e6dcde1f7ced57f6ab081a57abaaebcdae3e1d720a389ac51`, `client/settings/view.py` `deb00071bb6d5c16134e4daf30613a6d0020547afcb92a1056efbde1073e427b`, `client/settings/translation_tables.py` `e15c4a4e94451f46167ae3a46d656f3f79b049b6e6aa011aac84ba21a04f571a`, `client/dictionaries/manager.py` `1ae0d6676ea71ab2fcd97949a62a8d71a76cabf9026bf5fb54f6442d6d1f6b3b`, `client/dictionaries/name_prompt.py` `b35dee200da115ef2fdbe4d07cbdbe71b8f8196d3981389be88db3cadfb49e0a`, `client/documents/workspace.py` `55d0adb693126f373033e27d000fa8c7ffaa06e5eafe20c463e5c6bc7fb8d316`, `client/dual_view/files.py` `88c0afd88972ebc74d5de22e78c8d909ec340bac9f0b6151809b3a6c77c477f6`, `client/documents/export_coordinator.py` `12fe2032909a1580340091fb2081953a0e45cd4aef3de4289101c43d4a751dcb`, `client/ui/conversion_presenter.py` `914a4630fac2be9ec8a42c41fdeba40d1230625e4915ec6955176958f4c0d9cb`; both fixtures unchanged. Windows-only behavior was not run; see the end of Task 6.

## Review Focus

Inputs and conditions the spec implies but does not list as tests, most likely to bite first. Each has a test in Task 1, so it guards Tasks 2-5 as well.

1. **A read-only install folder.** Validation fails: the error dialog must name the failing folder and nothing after it may run (no cleanup, runtime, frame or client init), or a half-built app would start writing elsewhere. `test_app_stops_before_cleanup_when_validation_fails`; mutants `continue-after-validation-error`, `cleanup-before-validation`.
2. **Startup must not touch `config.json` on the UI thread for client init.** The client id is created and saved on the worker; a regression that creates it before starting the thread makes startup wait on disk (and on a slow or locked `config.json`). `test_no_client_id_is_created_before_the_worker_runs`; mutants `client-id-on-caller-thread` (old and new).
3. **zh_TW dictionary names in `config.json`.** Users name dictionaries in Chinese; the file must keep them unescaped with the same indentation, or a byte-compare and hand edits break. `test_selecting_a_dictionary_writes_the_config_file_under_the_root` and `test_store_writes_the_documented_config_bytes` compare exact text with `點字`; mutants `config-ascii-escaped`, `store-ascii-escaped`.
4. **The log folder must be the validated folder.** If the logger resolved its folder any other way, startup would validate one `log/` and write to another. `test_default_log_directory_follows_the_application_root` (also `nested/sample.log` keeps only the name); mutants `logger-folder-from-cwd`, `logger-keeps-subfolder`, `log-directory-from-cwd`.
5. **A regression must not write into `client/`.** The wiring tests run against a temp root with the real root pointed at a decoy (refinement 7), and Task 6's snapshot catches any write into the real application data.

## File Map

- Task 1: modify `client/tests/test_gui_document_flows.py` (imports, `BrailleAppLifecycleTest._startup_recorders` + 2 tests, class `ApplicationPathsWiringCharacterizationTest`), `client/tests/test_client_init.py` (`_InlineThread`, `_NeverRunThread`, class `ClientInitConfigCharacterizationTest`), `client/tests/test_log.py`, `client/tests/test_main_demo.py` (helper `run_demo_at_root` + 1 test), `client/tests/test_config.py` (helper `make_store`, class `ConfigLanguageOverrideCharacterizationTest`). Additions only.
- Task 2: `client/tests/test_config.py` (`make_store` body, class `ConfigStoreTest`), then `client/config.py` (`ConfigStore`; module functions delegate).
- Task 3: the eight test modules that call the config API or the gui seams, then `client/gui.py`, `client/settings/translation.py`, `client/settings/view.py`, `client/settings/translation_tables.py`, `client/client_init.py`, `client/main.py`.
- Task 4: `client/tests/test_app_paths.py`, `test_config.py`, `test_translation_import_isolation.py`, `test_gui_document_flows.py`, `test_log.py`, then `client/app_paths.py`, `client/config.py`, `client/log.py`, `client/dictionaries/manager.py`, `client/dictionaries/name_prompt.py`, `client/documents/workspace.py`, `client/dual_view/files.py`, `client/gui.py`.
- Task 5: `client/tests/test_translation_import_isolation.py`, `test_conversion_presenter.py`, `test_export_coordinator.py`, then `git mv client/conversion/presenter.py client/ui/conversion_presenter.py`, `client/gui.py`, `client/documents/export_coordinator.py`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 1043 |
| 1 characterization | 14 | 1057 |
| 2 config store | 5 | 1062 |
| 3 inject | 3 | 1065 |
| 4 remove defaults | 5 | 1070 |
| 5 move presenter | 1 | 1071 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `paths_mutants.py <client_dir> <scratch_dir> (old|new|guards) [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`) to `<scratch_dir>/client`, then for each mutant of the set edits one file of the copy, runs the set's tests there and restores the file. The repo is never changed. Set `old` (26 mutants, run in Task 1) matches today's code and runs only the part A tests; set `new` (22, Task 3) matches the injected wiring and runs the six touched modules; set `guards` (8, Task 4) matches the code without implicit defaults and runs the modules holding the Task 4 guards.
- Existing: `$SP/p12/tools/msgid_scan.py` (the P0-5 AST stand-in for xgettext; source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`) and `$SP/shuffle_harness.py <seed>` (runs every test module in a seeded random order, one process).

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO diff main --stat -- client
```

Expected (no output from `status` and from the `client` diff; HEAD is the plan commit):

```text
docs: plan application paths injection
refactor/p2-6-application-paths
```

- [ ] **Step 2: Create the mutant runner.**

```bash
mkdir -p $T/tools
cat > $T/tools/paths_mutants.py <<'EOF'
"""Run the P2-6 application paths tests against deliberately broken code (throwaway).

Usage: python paths_mutants.py <client_dir> <scratch_dir> (old|new) [mutant ...]
Copies <client_dir> (without .venv, __pycache__, log) to <scratch_dir>/client
(fresh each run), then for each mutant of the set edits one file in the copy,
runs the set's tests there and restores the file. <client_dir> is never changed.
Prints "<mutant>: failures=F errors=E (summary)" per mutant (all of the set by default).
Set "old" matches the code before Task 3 (module-level resolvers) and runs only the
part A tests; set "new" matches the code after Task 3 (injected paths and store) and
runs the touched test modules; set "guards" matches the code after Task 4 (no implicit
defaults) and runs the modules that hold the Task 4 guards.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

TESTS = {
    "old": [
        "tests.test_gui_document_flows.ApplicationPathsWiringCharacterizationTest",
        "tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_startup_runs_steps_in_contract_order",
        "tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_stops_before_cleanup_when_validation_fails",
        "tests.test_client_init.ClientInitConfigCharacterizationTest",
        "tests.test_log.FileLoggerTest.test_default_log_directory_follows_the_application_root",
        "tests.test_main_demo.MainDemoTest.test_demo_reads_dictionary_and_language_from_the_application_root",
        "tests.test_config.ConfigLanguageOverrideCharacterizationTest",
    ],
    "new": [
        "tests.test_gui_document_flows",
        "tests.test_client_init",
        "tests.test_log",
        "tests.test_main_demo",
        "tests.test_config",
        "tests.test_app_paths",
    ],
    "guards": [
        "tests.test_app_paths",
        "tests.test_config",
        "tests.test_log",
        "tests.test_translation_import_isolation",
        "tests.test_gui_document_flows",
    ],
}

GET_LANG_HEAD = "def get_lang() -> str:\n    if _runtime_lang:\n"
GET_MAPS_HEAD = "def get_charset_maps() -> dict[str, str]:\n    return _get_dict_setting(\n"
STORE_GET_LANG_HEAD = "    def get_lang(self) -> str:\n        if _runtime_lang:\n"
STORE_GET_MAPS_HEAD = "    def get_charset_maps(self) -> dict[str, str]:\n        return self._get_dict_setting(\n"

# set -> name -> (file, old, new); old must occur exactly once in the file.
MUTANTS = {
    "old": {
        "frame-dictionary-from-cwd": (
            "gui.py",
            "\t\tself.dictionary_dir = get_dictionary_directory()\n",
            "\t\tself.dictionary_dir = Path.cwd() / \"dictionary\"\n",
        ),
        "frame-workspace-from-cwd": (
            "gui.py",
            "DocumentWorkspaceService(self._document_controller, get_workspace_directory())",
            "DocumentWorkspaceService(self._document_controller, Path.cwd() / \"workspace\")",
        ),
        "tables-not-loaded": (
            "gui.py",
            "load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()",
            "DEFAULT_TRANSLATION_TABLES.copy()",
        ),
        "selected-dictionary-not-saved": ("gui.py", "\t\tset_selected_dictionary(selected_name)\n", ""),
        "dual-view-into-workspace": (
            "gui.py",
            "write_dual_view_html(self._render_dual_view_for_open_document())",
            "write_dual_view_html(self._render_dual_view_for_open_document(), get_workspace_directory())",
        ),
        "cleanup-before-validation": (
            "gui.py",
            "\t\t\tpaths = prepare_application_directories()\n\t\t\tcleanup_dual_view_html(paths.dual_view)\n",
            "\t\t\tcleanup_dual_view_html()\n\t\t\tpaths = prepare_application_directories()\n",
        ),
        "no-startup-cleanup": ("gui.py", "\t\t\tcleanup_dual_view_html(paths.dual_view)\n", ""),
        "runtime-before-cleanup": (
            "gui.py",
            "\tdef OnInit(self):\n\t\ttry:\n",
            "\tdef OnInit(self):\n\t\tself.translation_runtime = build_default_translation_runtime()\n\t\ttry:\n",
        ),
        "client-init-before-show": (
            "gui.py",
            "\t\tself.frame.Show()\n\t\tstart_client_init_background()\n",
            "\t\tstart_client_init_background()\n\t\tself.frame.Show()\n",
        ),
        "continue-after-validation-error": (
            "gui.py",
            "\t\t\t_show_application_data_error(error)\n\t\t\treturn False\n\t\texcept OSError",
            "\t\t\t_show_application_data_error(error)\n\t\texcept OSError",
        ),
        "client-id-on-caller-thread": (
            "client_init.py",
            "    def worker():\n        try:\n            run_client_init()\n",
            "    client_id = get_or_create_client_id()\n\n"
            "    def worker():\n        try:\n            run_client_init(client_id_provider=lambda: client_id)\n",
        ),
        "client-thread-not-daemon": (
            "client_init.py",
            "thread_factory(target=worker, daemon=True)",
            "thread_factory(target=worker, daemon=False)",
        ),
        "client-locale-fixed": ("client_init.py", "    locale_provider=get_lang,\n", "    locale_provider=lambda: \"zh_TW\",\n"),
        "client-id-not-saved": (
            "config.py",
            "    data[CLIENT_SECTION] = section_data\n    _save_to_file(data)\n",
            "    data[CLIENT_SECTION] = section_data\n",
        ),
        "first-save-defaults-dropped": ("config.py", "        if not os.path.exists(CONFIG_PATH):\n", "        if False:\n"),
        "config-ascii-escaped": (
            "config.py",
            "json.dump(data, f, ensure_ascii=False, indent=2)",
            "json.dump(data, f, indent=2)",
        ),
        "lang-cached": (
            "config.py",
            GET_LANG_HEAD,
            "_cached_lang: list = []\n\n\ndef get_lang() -> str:\n"
            "    if not _cached_lang:\n        _cached_lang.append(_read_lang())\n    return _cached_lang[0]\n\n\n"
            "def _read_lang() -> str:\n    if _runtime_lang:\n",
        ),
        "charset-maps-cached": (
            "config.py",
            GET_MAPS_HEAD,
            "_cached_maps: list = []\n\n\ndef get_charset_maps() -> dict[str, str]:\n"
            "    if not _cached_maps:\n        _cached_maps.append(_read_maps())\n    return dict(_cached_maps[0])\n\n\n"
            "def _read_maps() -> dict[str, str]:\n    return _get_dict_setting(\n",
        ),
        "environment-ignored": ("config.py", "    lang = os.getenv(LANG_ENV)\n", "    lang = None\n"),
        "runtime-override-ignored": ("config.py", "    if _runtime_lang:\n        return _runtime_lang\n", ""),
        "persist-ignored": ("config.py", "    if persist:\n", "    if False:\n"),
        "logger-folder-from-cwd": (
            "log.py",
            "            get_log_directory() / Path(filename).name,\n",
            "            Path.cwd() / \"log\" / Path(filename).name,\n",
        ),
        "logger-keeps-subfolder": (
            "log.py",
            "            get_log_directory() / Path(filename).name,\n",
            "            get_log_directory() / filename,\n",
        ),
        "demo-dictionary-from-cwd": (
            "main.py",
            "dictionary_path=get_dictionary_directory() / \"default.csv\"",
            "dictionary_path=Path(\"dictionary\") / \"default.csv\"",
        ),
        "demo-language-fixed": ("main.py", "lang=get_lang(),", "lang=\"zh_TW\","),
        "demo-charset-maps-default": ("main.py", "charset_maps=get_charset_maps(),", "charset_maps={},"),
    },
    "new": {
        "validates-another-object": (
            "gui.py",
            "\t\t\tprepare_application_directories(paths)\n",
            "\t\t\tprepare_application_directories(build_application_paths())\n",
        ),
        "paths-not-kept-on-app": ("gui.py", "\t\tself.paths = paths\n", ""),
        "store-after-runtime": (
            "gui.py",
            "\t\tconfig_store = ConfigStore(paths.config)\n\t\tself.translation_runtime = build_default_translation_runtime()\n",
            "\t\tself.translation_runtime = build_default_translation_runtime()\n\t\tconfig_store = ConfigStore(paths.config)\n",
        ),
        "second-store-for-client-init": (
            "gui.py",
            "\t\tstart_client_init_background(config_store)\n",
            "\t\tstart_client_init_background(ConfigStore(paths.config))\n",
        ),
        "exit-cleans-implicit-folder": (
            "gui.py",
            "\t\t\t\tcleanup_dual_view_html(paths.dual_view)\n",
            "\t\t\t\tcleanup_dual_view_html(build_application_paths().dual_view)\n",
        ),
        "frame-dictionary-implicit": (
            "gui.py",
            "\t\tself.dictionary_dir = self._paths.dictionary\n",
            "\t\tself.dictionary_dir = build_application_paths().dictionary\n",
        ),
        "frame-workspace-implicit": (
            "gui.py",
            "DocumentWorkspaceService(self._document_controller, self._paths.workspace)",
            "DocumentWorkspaceService(self._document_controller, build_application_paths().workspace)",
        ),
        "dual-view-implicit": (
            "gui.py",
            "self._render_dual_view_for_open_document(), self._paths.dual_view)",
            "self._render_dual_view_for_open_document(), build_application_paths().dual_view)",
        ),
        "selection-saved-to-implicit-store": (
            "gui.py",
            "\t\tself._config_store.set_selected_dictionary(selected_name)\n",
            "\t\tConfigStore(build_application_paths().config).set_selected_dictionary(selected_name)\n",
        ),
        "request-language-from-implicit-store": (
            "gui.py",
            "\t\t\tlang=self._config_store.get_lang(),\n",
            "\t\t\tlang=ConfigStore(build_application_paths().config).get_lang(),\n",
        ),
        "font-size-saved-to-implicit-store": (
            "gui.py",
            "save_view_settings(self._config_store, self.view_settings)",
            "save_view_settings(ConfigStore(build_application_paths().config), self.view_settings)",
        ),
        "client-id-on-caller-thread": (
            "client_init.py",
            "    def worker():\n        try:\n            run_client_init(\n"
            "                client_id_provider=config_store.get_or_create_client_id,\n",
            "    client_id = config_store.get_or_create_client_id()\n\n"
            "    def worker():\n        try:\n            run_client_init(\n"
            "                client_id_provider=lambda: client_id,\n",
        ),
        "client-locale-fixed": (
            "client_init.py",
            "                locale_provider=config_store.get_lang,\n",
            "                locale_provider=lambda: \"zh_TW\",\n",
        ),
        "demo-dictionary-at-root": (
            "main.py",
            "dictionary_path=paths.dictionary / \"default.csv\"",
            "dictionary_path=paths.root / \"default.csv\"",
        ),
        "demo-store-in-working-folder": (
            "main.py",
            "    config_store = ConfigStore(paths.config)\n",
            "    config_store = ConfigStore(\"config.json\")\n",
        ),
        "store-constructor-creates-folder": (
            "config.py",
            "        self._path = Path(path)\n",
            "        self._path = Path(path)\n        self._path.parent.mkdir(parents=True, exist_ok=True)\n",
        ),
        "store-path-is-a-string": (
            "config.py",
            "    def path(self) -> Path:\n        return self._path\n",
            "    def path(self) -> Path:\n        return str(self._path)\n",
        ),
        "store-caches-language": (
            "config.py",
            STORE_GET_LANG_HEAD,
            "    def get_lang(self) -> str:\n        if not hasattr(self, \"_cached_lang\"):\n"
            "            self._cached_lang = self._read_lang()\n        return self._cached_lang\n\n"
            "    def _read_lang(self) -> str:\n        if _runtime_lang:\n",
        ),
        "store-caches-charset-maps": (
            "config.py",
            STORE_GET_MAPS_HEAD,
            "    def get_charset_maps(self) -> dict[str, str]:\n        if not hasattr(self, \"_cached_maps\"):\n"
            "            self._cached_maps = self._read_maps()\n        return dict(self._cached_maps)\n\n"
            "    def _read_maps(self) -> dict[str, str]:\n        return self._get_dict_setting(\n",
        ),
        "store-throttles-per-instance": (
            "config.py",
            "            if _logged_load_failures.get(path) != signature:\n                _logged_load_failures[path] = signature\n",
            "            if _logged_load_failures.get((path, id(self))) != signature:\n"
            "                _logged_load_failures[(path, id(self))] = signature\n",
        ),
        "store-first-save-defaults-dropped": ("config.py", "            if not os.path.exists(path):\n", "            if False:\n"),
        "store-ascii-escaped": (
            "config.py",
            "json.dump(data, f, ensure_ascii=False, indent=2)",
            "json.dump(data, f, indent=2)",
        ),
    },
    "guards": {
        "app-paths-helper-back": (
            "app_paths.py",
            "def prepare_application_directories(\n",
            "def get_dual_view_directory() -> Path:\n    return build_application_paths().dual_view\n\n\n"
            "def prepare_application_directories(\n",
        ),
        "prepare-paths-optional": (
            "app_paths.py",
            "    paths: ApplicationPaths,\n    *,\n",
            "    paths: ApplicationPaths = None,\n    *,\n",
        ),
        "cleanup-folder-optional": (
            "dual_view/files.py",
            "def cleanup_dual_view_html(directory: Path) -> None:\n",
            "def cleanup_dual_view_html(directory: Path = None) -> None:\n",
        ),
        "workspace-resolves-the-root": (
            "documents/workspace.py",
            "def ensure_workspace_directory(workspace_dir: Path) -> Path:\n    directory = Path(workspace_dir)\n",
            "def ensure_workspace_directory(workspace_dir: Path) -> Path:\n"
            "    directory = Path(workspace_dir) if workspace_dir else __import__(\"app_paths\").build_application_paths().workspace\n",
        ),
        "config-module-getter-back": (
            "config.py",
            "class ConfigStore:\n",
            "def get_lang() -> str:\n    return ConfigStore(\"config.json\").get_lang()\n\n\nclass ConfigStore:\n",
        ),
        "config-module-path-back": (
            "config.py",
            "LANG_ENV = \"TEXT2BRAILLE_LANG\"\n",
            "LANG_ENV = \"TEXT2BRAILLE_LANG\"\nDEFAULT_CONFIG_PATH = \"config.json\"\n",
        ),
        "client-init-imports-config": (
            "client_init.py",
            "import about\nfrom log import get_logger\n",
            "import about\nimport config  # noqa: F401\nfrom log import get_logger\n",
        ),
        "log-directory-from-cwd": (
            "log.py",
            "    return build_application_paths().log\n",
            "    return Path.cwd() / \"log\"\n",
        ),
    },
}


def main() -> int:
    client = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    which = sys.argv[3]
    mutants = MUTANTS[which]
    names = sys.argv[4:] or list(mutants)
    copy = scratch / "client"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(client, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", "log"))
    (copy / "log").mkdir()
    for name in names:
        relative, old, new = mutants[name]
        path = copy / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            print(f"{name}: pattern found {original.count(old)} times")
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", *TESTS[which]],
                cwd=copy,
                capture_output=True,
                text=True,
                timeout=600,
            )
        finally:
            path.write_text(original, encoding="utf-8")
        summary = re.search(r"^(OK|FAILED).*$", result.stderr, re.M)
        failures = len(re.findall(r"^FAIL: ", result.stderr, re.M))
        errors = len(re.findall(r"^ERROR: ", result.stderr, re.M))
        state = summary.group(0) if summary else "no summary"
        print(f"{name}: failures={failures} errors={errors} ({state})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
$PY -I -m py_compile $T/tools/paths_mutants.py && echo compiled
```

Expected:

```text
compiled
```

- [ ] **Step 3: Record the baseline suite, the touched modules, the msgids and both fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for m in test_app_paths test_config test_gui_document_flows test_client_init test_log test_main_demo test_view_settings test_translation_tables test_translation_settings test_conversion_language_explicit test_translation_import_isolation test_conversion_presenter test_export_coordinator; do echo "$m: $($PY -m unittest tests.$m 2>&1 | grep -E '^Ran' | sed -E 's/ in [0-9.]+s$//')"; done
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --save $T/base_msgids.json) | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
ls -d config.json workspace 2>&1
```

Expected (1043 tests with the P2-5 failure; the per-module counts; 353 msgids saved; both fixture hashes; no `config.json` or `workspace/` in `client/`):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1043 tests
FAILED (failures=1, skipped=9)
test_app_paths: Ran 7 tests
test_config: Ran 25 tests
test_gui_document_flows: Ran 151 tests
test_client_init: Ran 7 tests
test_log: Ran 1 test
test_main_demo: Ran 2 tests
test_view_settings: Ran 5 tests
test_translation_tables: Ran 2 tests
test_translation_settings: Ran 5 tests
test_conversion_language_explicit: Ran 2 tests
test_translation_import_isolation: Ran 4 tests
test_conversion_presenter: Ran 19 tests
test_export_coordinator: Ran 21 tests
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
ls: cannot access 'config.json': No such file or directory
ls: cannot access 'workspace': No such file or directory
```

---

### Task 1: Characterize the application paths wiring (spec step 1, part A)

Nothing in production changes. Every new test passes on the current code by construction; Step 3 shows that the net fails for each of 26 deliberate breakages.

**Interfaces:**
- Consumes: today's `app_paths.get_application_root()` (patched to a temp root; every `get_*_directory()` resolves it at call time), `config.CONFIG_PATH` (fixed at import, patched), `BrailleFrame._initialize_state()`, `_set_active_dictionary(name)`, `on_open_dual_view(event)`, `_build_conversion_request(raw_text, output_mode, width, dictionary_path)`, `BrailleApp.OnInit()`, `client_init.start_client_init_background(*, run_client_init, thread_factory)`, `client_init.run_client_init(*, ..., opener)`, `log.get_logger(name, filename)`, `main.run_demo(text)`, `config.get_lang()` / `set_lang(lang, persist)`.
- Produces (test side only): `ApplicationPathsWiringCharacterizationTest.make_frame()`, `ClientInitConfigCharacterizationTest.start(thread_factory)`, `MainDemoTest.run_demo_at_root(root)` and `make_store(path)` in `tests/test_config.py`: the only parts later tasks change. `BrailleAppLifecycleTest._startup_recorders(order, prepare_error=None)` returns name -> fake for the five startup seams; its fakes accept any arguments, so it survives the new signatures unchanged.

- [ ] **Step 1: Add the characterization tests.** The frame wiring class goes at the end of `tests/test_gui_document_flows.py` (the module with the gui stub scope); `app_paths` and `config` are imported after the scope block, so the test patches the same module objects `gui` uses.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_client_init.py b/client/tests/test_client_init.py
index 3e31c5e..99a1c82 100644
--- a/client/tests/test_client_init.py
+++ b/client/tests/test_client_init.py
@@ -1,8 +1,15 @@
 import json
+import os
+import tempfile
 import unittest
+from functools import partial
+from pathlib import Path
+from unittest.mock import patch
 from urllib.error import URLError
+from uuid import UUID
 
 import client_init
+import config
 
 
 class _Response:
@@ -190,5 +197,98 @@ class ClientInitRequestTest(unittest.TestCase):
             },
         )
 
+
+class _InlineThread:
+    """Thread stand-in that runs its target on ``start()``, on the calling thread."""
+
+    def __init__(self, *, target, daemon):
+        self.target = target
+        self.daemon = daemon
+        self.started = False
+
+    def start(self) -> None:
+        self.started = True
+        self.target()
+
+
+class _NeverRunThread(_InlineThread):
+    """Thread stand-in whose worker never gets to run."""
+
+    def start(self) -> None:
+        self.started = True
+
+
+class ClientInitConfigCharacterizationTest(unittest.TestCase):
+    """P2-6 characterization: background client init reads and writes one config file.
+
+    Every test starts client init through ``start``, the only part that changes when the
+    config store is injected (P2-6 step 3).
+    """
+
+    RESPONSE = {
+        "version": "1.3",
+        "minimum_supported_version": "1.0",
+        "download_url": "https://dotexpress.coseeing.org/download",
+        "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
+        "message": "DotExpress 1.3 is available.",
+        "severity": "optional",
+    }
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.config_path = Path(temp_dir.name) / "config.json"
+        self.bodies: list[dict] = []
+        for patcher in (patch.dict(os.environ), patch.object(config, "_runtime_lang", None)):
+            patcher.start()
+            self.addCleanup(patcher.stop)
+        os.environ.pop(config.LANG_ENV, None)
+
+    def opener(self, request, timeout):
+        self.bodies.append(json.loads(request.data.decode("utf-8")))
+        return _Response(self.RESPONSE)
+
+    def start(self, thread_factory=_InlineThread):
+        """Start background client init against ``self.config_path`` (today: the module-level config path)."""
+        with patch.object(config, "CONFIG_PATH", str(self.config_path)):
+            return client_init.start_client_init_background(
+                run_client_init=partial(client_init.run_client_init, opener=self.opener),
+                thread_factory=thread_factory,
+            )
+
+    def test_first_start_creates_saves_and_sends_one_client_id(self) -> None:
+        thread = self.start()
+
+        client_id = self.bodies[0]["client_id"]
+        UUID(client_id)
+        self.assertTrue(thread.daemon)
+        self.assertEqual(self.bodies[0]["locale"], "zh_TW")
+        self.assertEqual(
+            json.loads(self.config_path.read_text(encoding="utf-8")),
+            {
+                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
+                "client": {"id": client_id},
+            },
+        )
+
+        self.start()
+
+        self.assertEqual([body["client_id"] for body in self.bodies], [client_id, client_id])
+
+    def test_the_configured_language_is_sent_as_locale(self) -> None:
+        self.config_path.write_text(json.dumps({"language": "ja"}), encoding="utf-8")
+
+        self.start()
+
+        self.assertEqual(self.bodies[0]["locale"], "ja")
+
+    def test_no_client_id_is_created_before_the_worker_runs(self) -> None:
+        thread = self.start(_NeverRunThread)
+
+        self.assertTrue(thread.started)
+        self.assertFalse(self.config_path.exists())
+        self.assertEqual(self.bodies, [])
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_config.py b/client/tests/test_config.py
index 6c34ccc..dcb1609 100644
--- a/client/tests/test_config.py
+++ b/client/tests/test_config.py
@@ -1,5 +1,6 @@
 import json
 import logging
+import os
 import tempfile
 import unittest
 import gettext
@@ -420,5 +421,78 @@ class ConfigLoadFailureLoggingTest(unittest.TestCase):
         self.assertFalse(missing_log.parent.exists())
 
 
+class _ConfigFunctionsAtPath:
+    """The module-level config functions, each run with ``config.CONFIG_PATH`` set to one path."""
+
+    def __init__(self, path: Path) -> None:
+        self.path = Path(path)
+
+    def __getattr__(self, name: str):
+        function = getattr(config, name)
+
+        def call(*args, **kwargs):
+            with patch.object(config, "CONFIG_PATH", str(self.path)):
+                return function(*args, **kwargs)
+
+        return call
+
+
+def make_store(path: Path):
+    """The config API bound to ``path``.
+
+    P2-6: the module-level functions today, ``config.ConfigStore`` from step 2 on.
+    """
+    return _ConfigFunctionsAtPath(path)
+
+
+class ConfigLanguageOverrideCharacterizationTest(unittest.TestCase):
+    """P2-6 characterization: where ``get_lang`` finds the language, and what ``set_lang`` writes."""
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.path = Path(temp_dir.name) / "config.json"
+        self.store = make_store(self.path)
+        self.addCleanup(setattr, config, "_runtime_lang", config._runtime_lang)
+        config._runtime_lang = None
+        environment = patch.dict(os.environ)
+        environment.start()
+        self.addCleanup(environment.stop)
+        os.environ.pop(config.LANG_ENV, None)
+
+    def read(self) -> dict:
+        return json.loads(self.path.read_text(encoding="utf-8"))
+
+    def test_language_comes_from_the_environment_then_the_file_then_the_fallback(self) -> None:
+        self.assertEqual(self.store.get_lang(), "zh_TW")
+        self.path.write_text(json.dumps({"language": "en"}), encoding="utf-8")
+        self.assertEqual(self.store.get_lang(), "en")
+        os.environ[config.LANG_ENV] = "ko"
+        self.assertEqual(self.store.get_lang(), "ko")
+
+    def test_runtime_override_wins_without_writing_the_file(self) -> None:
+        self.path.write_text(json.dumps({"language": "en"}), encoding="utf-8")
+        os.environ[config.LANG_ENV] = "ko"
+
+        self.store.set_lang("ja")
+
+        self.assertEqual(self.store.get_lang(), "ja")
+        self.assertEqual(config._runtime_lang, "ja")
+        self.assertEqual(self.read(), {"language": "en"})
+
+    def test_persisted_override_writes_the_top_level_language_with_first_save_defaults(self) -> None:
+        self.store.set_lang("en", persist=True)
+
+        self.assertEqual(
+            self.read(),
+            {
+                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
+                "language": "en",
+            },
+        )
+        config._runtime_lang = None
+        self.assertEqual(self.store.get_lang(), "en")
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 62ee69d..f2e2199 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -2,9 +2,12 @@ from __future__ import annotations
 
 import importlib
 import inspect
+import json
+import os
 import tempfile
 import unittest
 import zipfile
+from contextlib import ExitStack
 from pathlib import Path
 from types import SimpleNamespace
 from unittest.mock import ANY, DEFAULT, Mock, call, patch
@@ -24,6 +27,8 @@ with _SCOPE.loading():
 setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
 
+import app_paths
+import config
 from documents.controller import DocumentController
 from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
 from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
@@ -630,6 +635,60 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         log_exception.assert_called_once_with("Failed to clean up dual-view HTML")
         runtime.close.assert_called_once_with()
 
+    def _startup_recorders(self, order: list, prepare_error: Exception | None = None) -> dict:
+        """P2-6: recording fakes for every startup step; each accepts any arguments."""
+
+        def prepare(*args, **kwargs):
+            order.append("prepare")
+            if prepare_error is not None:
+                raise prepare_error
+            return args[0] if args else Mock(dual_view=Path("C:/DotExpress/dual_view"))
+
+        def record(step, result=None):
+            def fake(*args, **kwargs):
+                order.append(step)
+                return result
+
+            return fake
+
+        frame = Mock()
+        frame.Show.side_effect = record("show")
+        return {
+            "prepare_application_directories": prepare,
+            "cleanup_dual_view_html": record("cleanup"),
+            "build_default_translation_runtime": record("runtime", Mock()),
+            "BrailleFrame": record("frame", frame),
+            "start_client_init_background": record("client_init"),
+        }
+
+    def test_app_startup_runs_steps_in_contract_order(self) -> None:
+        order: list[str] = []
+
+        with ExitStack() as stack:
+            for name, fake in self._startup_recorders(order).items():
+                stack.enter_context(patch.object(gui, name, side_effect=fake))
+            message_box = stack.enter_context(patch.object(gui.wx, "MessageBox"))
+            result = gui.BrailleApp().OnInit()
+
+        self.assertTrue(result)
+        self.assertEqual(order, ["prepare", "cleanup", "runtime", "frame", "show", "client_init"])
+        message_box.assert_not_called()
+
+    def test_app_stops_before_cleanup_when_validation_fails(self) -> None:
+        order: list[str] = []
+        error = gui.ApplicationDataError(Path("C:/Program Files/DotExpress/dictionary"), PermissionError("denied"))
+
+        with ExitStack() as stack:
+            for name, fake in self._startup_recorders(order, prepare_error=error).items():
+                stack.enter_context(patch.object(gui, name, side_effect=fake))
+            message_box = stack.enter_context(patch.object(gui.wx, "MessageBox"))
+            result = gui.BrailleApp().OnInit()
+
+        self.assertFalse(result)
+        self.assertEqual(order, ["prepare"])
+        message_box.assert_called_once()
+        self.assertIn(str(error.path), message_box.call_args.args[0])
+
     def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
         frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._dual_view_frame = Mock()
@@ -3756,5 +3815,133 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         self.assertEqual(text_dialog.mock_calls, [])
 
 
+class ApplicationPathsWiringCharacterizationTest(unittest.TestCase):
+    """P2-6 characterization: the frame keeps all of its application data under one root.
+
+    Every test gets its frame from ``make_frame``, the only part that changes when the
+    application paths and the config store are injected (P2-6 steps 3 and 4).
+    """
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name) / "application"
+        self.root.mkdir()
+        self.config_path = self.root / "config.json"
+
+    def make_frame(self) -> gui.BrailleFrame:
+        """A bare frame whose application data lives under ``self.root``.
+
+        Today the frame resolves its folders and its config file through module-level
+        defaults, so the application root and the import-time config path are patched.
+        """
+        for patcher in (
+            patch.object(app_paths, "get_application_root", return_value=self.root),
+            patch.object(config, "CONFIG_PATH", str(self.config_path)),
+        ):
+            patcher.start()
+            self.addCleanup(patcher.stop)
+        return object.__new__(gui.BrailleFrame)
+
+    def write_config(self, data: dict) -> None:
+        self.config_path.write_text(json.dumps(data), encoding="utf-8")
+
+    def root_entries(self) -> list[str]:
+        return sorted(path.name for path in self.root.iterdir())
+
+    def test_initialize_state_keeps_dictionaries_workspace_and_settings_under_the_root(self) -> None:
+        self.write_config(
+            {
+                "conversion": {
+                    "output_mode": "ascii",
+                    "width": 52,
+                    "selected_dictionary": "alpha",
+                    "translation_tables": {"default": "en-ueb-g1.ctb"},
+                },
+                "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
+            }
+        )
+        (self.root / "dictionary").mkdir()
+        (self.root / "dictionary" / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
+        frame = self.make_frame()
+        frame._document_controller = DocumentController()
+        frame._register_output_font = Mock(return_value=False)
+
+        view = frame._initialize_state()
+
+        self.assertEqual(frame.dictionary_dir, self.root / "dictionary")
+        self.assertEqual(frame._dictionary_presenter.dictionary_dir, self.root / "dictionary")
+        self.assertTrue((self.root / "dictionary" / "default.csv").is_file())
+        self.assertEqual(frame._workspace_service.workspace_dir, self.root / "workspace")
+        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "alpha"))
+        self.assertEqual(frame.translation_tables, {**gui.DEFAULT_TRANSLATION_TABLES, "default": "en-ueb-g1.ctb"})
+        self.assertEqual(view, ViewSettings(18, "dark", "default"))
+        self.assertIs(frame.view_settings, view)
+        self.assertEqual(self.root_entries(), ["config.json", "dictionary"])
+
+    def test_selecting_a_dictionary_writes_the_config_file_under_the_root(self) -> None:
+        frame = self.make_frame()
+        frame.translation_settings = TranslationSettings("ascii", 52, "alpha")
+
+        frame._set_active_dictionary("點字")
+
+        expected = {
+            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
+            "conversion": {"selected_dictionary": "點字"},
+        }
+        self.assertEqual(
+            self.config_path.read_text(encoding="utf-8"),
+            json.dumps(expected, ensure_ascii=False, indent=2),
+        )
+        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "點字"))
+        self.assertEqual(self.root_entries(), ["config.json"])
+
+    def test_dual_view_html_is_written_under_the_root(self) -> None:
+        frame = self.make_frame()
+        frame.GetSize = Mock(return_value=(800, 600))
+        frame._render_dual_view_for_open_document = Mock(return_value="<html>雙視</html>")
+        frame._show_file_error = Mock()
+
+        with patch.object(gui, "open_html_in_browser") as open_browser:
+            frame.on_open_dual_view(None)
+
+        written = sorted((self.root / "dual_view").glob("dual-view-*.html"))
+        self.assertEqual(len(written), 1)
+        self.assertEqual(written[0].read_text(encoding="utf-8"), "<html>雙視</html>")
+        open_browser.assert_called_once_with(written[0], (800, 600))
+        frame._show_file_error.assert_not_called()
+        self.assertEqual(self.root_entries(), ["dual_view"])
+
+    def test_each_conversion_request_reads_the_language_settings_from_the_root_config(self) -> None:
+        frame = self.make_frame()
+        frame.translation_tables = {"default": "zh-tw.ctb"}
+        reads: list[str] = []
+        real_open = open
+
+        def counting_open(file, mode="r", *args, **kwargs):
+            if str(file) == str(self.config_path) and "r" in mode:
+                reads.append(str(file))
+            return real_open(file, mode, *args, **kwargs)
+
+        self.write_config({"language": "en", "language_detection": {"charset_maps": {"latinCharactersLanguage": "fr"}}})
+        with (
+            patch.dict(os.environ),
+            patch.object(config, "_runtime_lang", None),
+            patch("builtins.open", counting_open),
+        ):
+            os.environ.pop(config.LANG_ENV, None)
+            first = frame._build_conversion_request("x", "unicode", 40, Path("d.csv"))
+            reads_after_first = len(reads)
+            self.write_config({"language": "ja"})
+            second = frame._build_conversion_request("x", "unicode", 40, Path("d.csv"))
+
+        self.assertEqual(first.lang, "en")
+        self.assertEqual(first.charset_maps, {**config.DEFAULT_CHARSET_MAPS, "latinCharactersLanguage": "fr"})
+        self.assertEqual(second.lang, "ja")
+        self.assertEqual(second.charset_maps, config.DEFAULT_CHARSET_MAPS)
+        self.assertEqual((reads_after_first, len(reads)), (2, 4))
+        self.assertEqual(self.root_entries(), ["config.json"])
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_log.py b/client/tests/test_log.py
index 7acf3ee..48c37d0 100644
--- a/client/tests/test_log.py
+++ b/client/tests/test_log.py
@@ -5,6 +5,7 @@ from pathlib import Path
 from uuid import uuid4
 from unittest.mock import patch
 
+import app_paths
 import log
 
 
@@ -28,6 +29,22 @@ class FileLoggerTest(unittest.TestCase):
             handler.close()
             logger.removeHandler(handler)
 
+    def test_default_log_directory_follows_the_application_root(self) -> None:
+        with tempfile.TemporaryDirectory() as directory:
+            root = Path(directory) / "application"
+            logger_name = f"dotexpress.test.{uuid4().hex}"
+            with patch.object(app_paths, "get_application_root", return_value=root):
+                logger = log.get_logger(logger_name, "nested/sample.log")
+                validated_log_directory = app_paths.build_application_paths().log
+
+            handler = next(item for item in logger.handlers if isinstance(item, logging.FileHandler))
+            self.addCleanup(logger.removeHandler, handler)
+            self.addCleanup(handler.close)
+            self.assertEqual(Path(handler.baseFilename), root / "log" / "sample.log")
+            self.assertEqual(Path(handler.baseFilename), validated_log_directory / "sample.log")
+            self.assertIsNone(handler.stream)
+            self.assertFalse(root.exists())
+
 
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_main_demo.py b/client/tests/test_main_demo.py
index 1ecf18c..74d5185 100644
--- a/client/tests/test_main_demo.py
+++ b/client/tests/test_main_demo.py
@@ -1,7 +1,12 @@
+import json
+import os
+import tempfile
 import unittest
 from pathlib import Path
 from unittest.mock import Mock, patch
 
+import app_paths
+import config
 import main
 from conversion.service import ConversionOutput
 
@@ -47,6 +52,39 @@ class MainDemoTest(unittest.TestCase):
         print_mock.assert_called_once_with("braille")
         runtime.close.assert_called_once_with()
 
+    def run_demo_at_root(self, root: Path):
+        """Run the demo with its application data under ``root``; return the request.
+
+        P2-6: today the application root and the import-time config path are patched.
+        """
+        with (
+            patch.object(app_paths, "get_application_root", return_value=root),
+            patch.object(config, "CONFIG_PATH", str(root / "config.json")),
+            patch.dict(os.environ),
+            patch.object(config, "_runtime_lang", None),
+            patch.object(main, "build_default_translation_runtime", return_value=Mock()),
+            patch.object(main, "convert_text_with_alignment", return_value=ConversionOutput("braille", (), ())) as convert,
+            patch("builtins.print"),
+        ):
+            os.environ.pop(config.LANG_ENV, None)
+            main.run_demo("x")
+        return convert.call_args.args[0]
+
+    def test_demo_reads_dictionary_and_language_from_the_application_root(self) -> None:
+        with tempfile.TemporaryDirectory() as directory:
+            root = Path(directory)
+            (root / "config.json").write_text(
+                json.dumps({"language": "en", "language_detection": {"charset_maps": {"CJKCharactersLanguage": "ja"}}}),
+                encoding="utf-8",
+            )
+
+            request = self.run_demo_at_root(root)
+
+            self.assertEqual(request.dictionary_path, root / "dictionary" / "default.csv")
+            self.assertEqual(request.lang, "en")
+            self.assertEqual(request.charset_maps, {**config.DEFAULT_CHARSET_MAPS, "CJKCharactersLanguage": "ja"})
+            self.assertEqual(sorted(path.name for path in root.iterdir()), ["config.json"])
+
 
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_client_init.py        | 100 +++++++++++++++++
 client/tests/test_config.py             |  74 +++++++++++++
 client/tests/test_gui_document_flows.py | 187 ++++++++++++++++++++++++++++++++
 client/tests/test_log.py                |  17 +++
 client/tests/test_main_demo.py          |  38 +++++++
 5 files changed, 416 insertions(+)
```

- [ ] **Step 2: Run part A on the current code, then the five modules in full.**

```bash
$PY -m unittest tests.test_gui_document_flows.ApplicationPathsWiringCharacterizationTest tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_startup_runs_steps_in_contract_order tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_stops_before_cleanup_when_validation_fails tests.test_client_init.ClientInitConfigCharacterizationTest tests.test_log.FileLoggerTest.test_default_log_directory_follows_the_application_root tests.test_main_demo.MainDemoTest.test_demo_reads_dictionary_and_language_from_the_application_root tests.test_config.ConfigLanguageOverrideCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_gui_document_flows tests.test_client_init tests.test_log tests.test_main_demo tests.test_config 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (14 new tests, all passing; the five modules 157 + 10 + 2 + 3 + 28 = 200, with the 2 usual Windows-only skips):

```text
Ran 14 tests
OK
Ran 200 tests
OK (skipped=2)
```

- [ ] **Step 3: Mutation check: every mutant of today's code must fail part A.** The runner works on a copy under `$T/mut`; the repo is not changed.

```bash
$PY -I $T/tools/paths_mutants.py $REPO/client $T/mut old
git -C $REPO status --short -- client ':!client/tests'
```

Expected (every line FAILED; an `errors=` count is an assertion that hit a missing file or a `NameError` in the broken code; no production file changed in the repo):

```text
frame-dictionary-from-cwd: failures=1 errors=0 (FAILED (failures=1))
frame-workspace-from-cwd: failures=1 errors=0 (FAILED (failures=1))
tables-not-loaded: failures=1 errors=0 (FAILED (failures=1))
selected-dictionary-not-saved: failures=0 errors=1 (FAILED (errors=1))
dual-view-into-workspace: failures=1 errors=0 (FAILED (failures=1))
cleanup-before-validation: failures=2 errors=0 (FAILED (failures=2))
no-startup-cleanup: failures=1 errors=0 (FAILED (failures=1))
runtime-before-cleanup: failures=2 errors=0 (FAILED (failures=2))
client-init-before-show: failures=1 errors=0 (FAILED (failures=1))
continue-after-validation-error: failures=1 errors=0 (FAILED (failures=1))
client-id-on-caller-thread: failures=1 errors=0 (FAILED (failures=1))
client-thread-not-daemon: failures=1 errors=0 (FAILED (failures=1))
client-locale-fixed: failures=1 errors=0 (FAILED (failures=1))
client-id-not-saved: failures=0 errors=1 (FAILED (errors=1))
first-save-defaults-dropped: failures=3 errors=0 (FAILED (failures=3))
config-ascii-escaped: failures=1 errors=0 (FAILED (failures=1))
lang-cached: failures=5 errors=0 (FAILED (failures=5))
charset-maps-cached: failures=2 errors=0 (FAILED (failures=2))
environment-ignored: failures=1 errors=0 (FAILED (failures=1))
runtime-override-ignored: failures=1 errors=0 (FAILED (failures=1))
persist-ignored: failures=0 errors=1 (FAILED (errors=1))
logger-folder-from-cwd: failures=1 errors=0 (FAILED (failures=1))
logger-keeps-subfolder: failures=1 errors=0 (FAILED (failures=1))
demo-dictionary-from-cwd: failures=1 errors=0 (FAILED (failures=1))
demo-language-fixed: failures=1 errors=0 (FAILED (failures=1))
demo-charset-maps-default: failures=1 errors=0 (FAILED (failures=1))
```

- [ ] **Step 4: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1043 + 14):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1057 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_gui_document_flows.py client/tests/test_client_init.py client/tests/test_log.py client/tests/test_main_demo.py client/tests/test_config.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize application paths wiring

Pin where application data lands before the paths and the config store
are injected (P2-6 step 1, part A): the frame keeps its dictionaries,
workspace, config file and dual-view HTML under one root and reads the
language settings on every conversion request; startup validates, then
cleans, then builds the runtime, the frame and client init, and stops
at a validation error; client init creates and sends one client id on
its worker; the logger folder and the demo follow the application root;
get_lang's override, environment and file order. Each group reaches the
code through one helper, the only part later steps change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize application paths wiring
```

---

### Task 2: Add the config store behind the config functions (spec step 2, part B)

**Interfaces:**
- Consumes: the bodies of today's `config` functions, `_logged_load_failures`, `_log_current_exception`, `_coerce_int`, `_get_section`, the constants.
- Produces: `config.ConfigStore(path: Path | str)` with `path` (property, a `Path`), private `_load()`, `_save(data)`, `_set_section_value(section, key, value)`, `_get_dict_setting(section, key, default)`, and public `get_lang()`, `get_charset_maps()`, `set_lang(lang, persist=False)` (sets the module's `_runtime_lang`), `get_translation_tables()`, `set_translation_tables(tables)`, `get_output_mode(default=DEFAULT_OUTPUT_MODE)`, `set_output_mode(output_mode)`, `get_conversion_width(default=DEFAULT_CONVERSION_WIDTH)`, `set_conversion_width(width)`, `get_selected_dictionary(default="default")`, `set_selected_dictionary(name)`, `get_view_font_size(default=DEFAULT_VIEW_FONT_SIZE)`, `get_view_scheme(default=DEFAULT_VIEW_SCHEME)`, `get_braille_font(default=DEFAULT_BRAILLE_FONT)`, `set_view_settings(font_size, scheme, braille_font)`, `get_or_create_client_id()`. The constructor does no IO; every getter re-reads the file. Each module function becomes `ConfigStore(CONFIG_PATH).<same method>(...)`, built at call time.

- [ ] **Step 1: Write the failing tests.** `make_store` now returns `config.ConfigStore(path)` (the spec's step-2 switch), and `ConfigStoreTest` adds 5 tests: no IO and no log call in the constructor, `path` is a `Path` for `str` and `Path` input, one warning for two stores on one corrupt file, one warning each for two corrupt files, and the exact bytes of a setter sequence (store and module functions identical and equal to the expected text).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_config.py b/client/tests/test_config.py
index dcb1609..2be0732 100644
--- a/client/tests/test_config.py
+++ b/client/tests/test_config.py
@@ -421,28 +421,12 @@ class ConfigLoadFailureLoggingTest(unittest.TestCase):
         self.assertFalse(missing_log.parent.exists())
 
 
-class _ConfigFunctionsAtPath:
-    """The module-level config functions, each run with ``config.CONFIG_PATH`` set to one path."""
-
-    def __init__(self, path: Path) -> None:
-        self.path = Path(path)
-
-    def __getattr__(self, name: str):
-        function = getattr(config, name)
-
-        def call(*args, **kwargs):
-            with patch.object(config, "CONFIG_PATH", str(self.path)):
-                return function(*args, **kwargs)
-
-        return call
-
-
 def make_store(path: Path):
     """The config API bound to ``path``.
 
-    P2-6: the module-level functions today, ``config.ConfigStore`` from step 2 on.
+    P2-6: the module-level functions in step 1, ``config.ConfigStore`` from step 2 on.
     """
-    return _ConfigFunctionsAtPath(path)
+    return config.ConfigStore(path)
 
 
 class ConfigLanguageOverrideCharacterizationTest(unittest.TestCase):
@@ -494,5 +478,95 @@ class ConfigLanguageOverrideCharacterizationTest(unittest.TestCase):
         self.assertEqual(self.store.get_lang(), "en")
 
 
+class ConfigStoreTest(unittest.TestCase):
+    """P2-6 part B: ``config.ConfigStore`` owns one config file path."""
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.directory = Path(temp_dir.name)
+        config._logged_load_failures.clear()
+        self.addCleanup(config._logged_load_failures.clear)
+
+    def test_constructor_does_no_io_and_logs_nothing(self) -> None:
+        with patch.object(config, "logger") as logger:
+            config.ConfigStore(self.directory / "missing" / "config.json")
+
+        self.assertEqual(logger.mock_calls, [])
+        self.assertEqual(list(self.directory.iterdir()), [])
+
+    def test_path_is_a_path_for_str_and_path_input(self) -> None:
+        for given in (str(self.directory / "config.json"), self.directory / "config.json"):
+            with self.subTest(given=type(given).__name__):
+                store = config.ConfigStore(given)
+
+                self.assertIsInstance(store.path, Path)
+                self.assertEqual(store.path, Path(given))
+
+    def test_two_stores_on_one_corrupt_file_log_one_warning(self) -> None:
+        path = self.directory / "config.json"
+        path.write_bytes(b"{not json")
+
+        first = config.ConfigStore(path)
+        second = config.ConfigStore(str(path))
+
+        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
+            first.get_output_mode()
+            second.get_conversion_width()
+
+        self.assertEqual(len(captured.records), 1)
+        self.assertIn(str(path), captured.records[0].getMessage())
+
+    def test_stores_on_two_corrupt_files_log_one_warning_each(self) -> None:
+        paths = [self.directory / "first.json", self.directory / "second.json"]
+        for path in paths:
+            path.write_bytes(b"{not json")
+
+        stores = [config.ConfigStore(path) for path in paths]
+
+        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
+            for store in stores:
+                store.get_output_mode()
+                store.get_output_mode()
+
+        self.assertEqual(len(captured.records), 2)
+        for record, path in zip(captured.records, paths):
+            self.assertIn(str(path), record.getMessage())
+
+    def _apply_setters(self, target) -> None:
+        target.set_output_mode("ascii")
+        target.set_conversion_width(52)
+        target.set_selected_dictionary("點字")
+        target.set_translation_tables({"default": "en-ueb-g1.ctb"})
+        target.set_view_settings(18, "dark", "default")
+        target.set_lang("en", persist=True)
+
+    def test_store_writes_the_documented_config_bytes(self) -> None:
+        self.addCleanup(setattr, config, "_runtime_lang", config._runtime_lang)
+        store_path = self.directory / "store" / "config.json"
+        module_path = self.directory / "module" / "config.json"
+
+        self._apply_setters(config.ConfigStore(store_path))
+        with patch.object(config, "CONFIG_PATH", str(module_path)):
+            self._apply_setters(config)
+
+        expected = {
+            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
+            "conversion": {
+                "output_mode": "ascii",
+                "width": 52,
+                "selected_dictionary": "點字",
+                "translation_tables": {"default": "en-ueb-g1.ctb"},
+            },
+            "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
+            "language": "en",
+        }
+        self.assertEqual(
+            store_path.read_text(encoding="utf-8"),
+            json.dumps(expected, ensure_ascii=False, indent=2),
+        )
+        self.assertEqual(module_path.read_bytes(), store_path.read_bytes())
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_config.py | 110 ++++++++++++++++++++++++++++++++++++--------
 1 file changed, 92 insertions(+), 18 deletions(-)
```

- [ ] **Step 2: Run them red.**

```bash
$PY -m unittest tests.test_config 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (9 errors, all `AttributeError: module 'config' has no attribute 'ConfigStore'`: the 3 Task 1 language tests through `make_store` and the 5 store tests, the path test once per subtest):

```text
ERROR: test_language_comes_from_the_environment_then_the_file_then_the_fallback (tests.test_config.ConfigLanguageOverrideCharacterizationTest.test_language_comes_from_the_environment_then_the_file_then_the_fallback)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_persisted_override_writes_the_top_level_language_with_first_save_defaults (tests.test_config.ConfigLanguageOverrideCharacterizationTest.test_persisted_override_writes_the_top_level_language_with_first_save_defaults)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_runtime_override_wins_without_writing_the_file (tests.test_config.ConfigLanguageOverrideCharacterizationTest.test_runtime_override_wins_without_writing_the_file)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_constructor_does_no_io_and_logs_nothing (tests.test_config.ConfigStoreTest.test_constructor_does_no_io_and_logs_nothing)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_path_is_a_path_for_str_and_path_input (tests.test_config.ConfigStoreTest.test_path_is_a_path_for_str_and_path_input) (given='str')
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_path_is_a_path_for_str_and_path_input (tests.test_config.ConfigStoreTest.test_path_is_a_path_for_str_and_path_input) (given='PosixPath')
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_store_writes_the_documented_config_bytes (tests.test_config.ConfigStoreTest.test_store_writes_the_documented_config_bytes)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_stores_on_two_corrupt_files_log_one_warning_each (tests.test_config.ConfigStoreTest.test_stores_on_two_corrupt_files_log_one_warning_each)
AttributeError: module 'config' has no attribute 'ConfigStore'
ERROR: test_two_stores_on_one_corrupt_file_log_one_warning (tests.test_config.ConfigStoreTest.test_two_stores_on_one_corrupt_file_log_one_warning)
AttributeError: module 'config' has no attribute 'ConfigStore'
Ran 33 tests
FAILED (errors=9)
```

- [ ] **Step 3: Add `ConfigStore` and make the module functions delegate.** The method bodies are the function bodies with `_load_from_file()`/`_save_to_file()`/`CONFIG_PATH` replaced by `self._load()`/`self._save()`/`str(self._path)`; `_load_from_file`, `_save_to_file`, `_set_section_value` and `_get_dict_setting` move into the class. `CONFIG_PATH` and every module function keep their names, signatures and defaults until Task 4.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/config.py b/client/config.py
index a42d074..62d4dc2 100644
--- a/client/config.py
+++ b/client/config.py
@@ -1,6 +1,9 @@
+from __future__ import annotations
+
 import json
 import logging
 import os
+from pathlib import Path
 from typing import Optional
 from uuid import uuid4
 
@@ -60,44 +63,6 @@ def _log_current_exception(level: int, message: str, *args: object) -> None:
         pass
 
 
-def _load_from_file() -> dict:
-    path = CONFIG_PATH
-    try:
-        with open(path, "r", encoding="utf-8") as f:
-            data = json.load(f)
-    except FileNotFoundError:
-        _logged_load_failures.pop(path, None)
-        return {}
-    except Exception as error:
-        signature = f"{type(error).__name__}: {error}"
-        if _logged_load_failures.get(path) != signature:
-            _logged_load_failures[path] = signature
-            _log_current_exception(
-                logging.WARNING,
-                "Failed to read config file %s; using defaults",
-                path,
-            )
-        return {}
-    _logged_load_failures.pop(path, None)
-    return data
-
-
-def _save_to_file(data: dict) -> None:
-    try:
-        if not os.path.exists(CONFIG_PATH):
-            data = {
-                "language_detection": {
-                    "charset_maps": DEFAULT_CHARSET_MAPS.copy(),
-                },
-                **data,
-            }
-        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
-        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
-            json.dump(data, f, ensure_ascii=False, indent=2)
-    except Exception:
-        _log_current_exception(logging.ERROR, "Failed to save config file %s", CONFIG_PATH)
-
-
 def _coerce_int(value: object) -> Optional[int]:
     if isinstance(value, bool):
         return None
@@ -116,133 +81,231 @@ def _get_section(data: dict, section: str) -> dict:
     return value if isinstance(value, dict) else {}
 
 
-def _set_section_value(section: str, key: str, value: object) -> None:
-    data = _load_from_file()
-    section_data = _get_section(data, section).copy()
-    section_data[key] = value
-    data[section] = section_data
-    _save_to_file(data)
+class ConfigStore:
+    """config.json at one path. Each getter re-reads the file; nothing is cached."""
 
+    def __init__(self, path: Path | str) -> None:
+        self._path = Path(path)
 
-def _get_dict_setting(section: str, key: str, default: dict) -> dict:
-    data = _load_from_file()
-    section_data = _get_section(data, section)
-    value = section_data.get(key)
-    if not isinstance(value, dict):
-        return default.copy()
-    merged = default.copy()
-    for name, table in value.items():
-        if isinstance(name, str) and isinstance(table, str):
-            merged[name] = table
-    return merged
+    @property
+    def path(self) -> Path:
+        return self._path
+
+    def _load(self) -> dict:
+        path = str(self._path)
+        try:
+            with open(path, "r", encoding="utf-8") as f:
+                data = json.load(f)
+        except FileNotFoundError:
+            _logged_load_failures.pop(path, None)
+            return {}
+        except Exception as error:
+            signature = f"{type(error).__name__}: {error}"
+            if _logged_load_failures.get(path) != signature:
+                _logged_load_failures[path] = signature
+                _log_current_exception(
+                    logging.WARNING,
+                    "Failed to read config file %s; using defaults",
+                    path,
+                )
+            return {}
+        _logged_load_failures.pop(path, None)
+        return data
+
+    def _save(self, data: dict) -> None:
+        path = str(self._path)
+        try:
+            if not os.path.exists(path):
+                data = {
+                    "language_detection": {
+                        "charset_maps": DEFAULT_CHARSET_MAPS.copy(),
+                    },
+                    **data,
+                }
+            os.makedirs(os.path.dirname(path), exist_ok=True)
+            with open(path, "w", encoding="utf-8") as f:
+                json.dump(data, f, ensure_ascii=False, indent=2)
+        except Exception:
+            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)
+
+    def _set_section_value(self, section: str, key: str, value: object) -> None:
+        data = self._load()
+        section_data = _get_section(data, section).copy()
+        section_data[key] = value
+        data[section] = section_data
+        self._save(data)
+
+    def _get_dict_setting(self, section: str, key: str, default: dict) -> dict:
+        data = self._load()
+        section_data = _get_section(data, section)
+        value = section_data.get(key)
+        if not isinstance(value, dict):
+            return default.copy()
+        merged = default.copy()
+        for name, table in value.items():
+            if isinstance(name, str) and isinstance(table, str):
+                merged[name] = table
+        return merged
+
+    def get_lang(self) -> str:
+        if _runtime_lang:
+            return _runtime_lang
+        lang = os.getenv(LANG_ENV)
+        if lang:
+            return lang
+        data = self._load()
+        lang = data.get("language")
+        return lang or DEFAULT_FALLBACK
+
+    def get_charset_maps(self) -> dict[str, str]:
+        return self._get_dict_setting(
+            "language_detection",
+            "charset_maps",
+            DEFAULT_CHARSET_MAPS,
+        )
+
+    def set_lang(self, lang: str, persist: bool = False) -> None:
+        global _runtime_lang
+        _runtime_lang = lang
+        if persist:
+            data = self._load()
+            data["language"] = lang
+            self._save(data)
+
+    def get_translation_tables(self) -> dict:
+        return self._get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)
+
+    def set_translation_tables(self, tables: dict[str, str]) -> None:
+        self._set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))
+
+    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str:
+        data = self._load()
+        value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
+        return value if isinstance(value, str) else default
+
+    def set_output_mode(self, output_mode: str) -> None:
+        self._set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)
+
+    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int:
+        data = self._load()
+        width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
+        return width if width is not None else default
+
+    def set_conversion_width(self, width: int) -> None:
+        self._set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)
+
+    def get_selected_dictionary(self, default: str = "default") -> str:
+        data = self._load()
+        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
+        return value if isinstance(value, str) else default
+
+    def set_selected_dictionary(self, dictionary_name: str) -> None:
+        self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)
+
+    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
+        data = self._load()
+        font_size = _coerce_int(_get_section(data, VIEW_SECTION).get(FONT_SIZE_KEY))
+        return font_size if font_size is not None else default
+
+    def get_view_scheme(self, default: str = DEFAULT_VIEW_SCHEME) -> str:
+        data = self._load()
+        value = _get_section(data, VIEW_SECTION).get(SCHEME_KEY)
+        return value if isinstance(value, str) else default
+
+    def get_braille_font(self, default: str = DEFAULT_BRAILLE_FONT) -> str:
+        data = self._load()
+        value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
+        return value if isinstance(value, str) else default
+
+    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> None:
+        data = self._load()
+        section_data = _get_section(data, VIEW_SECTION).copy()
+        section_data.update(
+            {
+                FONT_SIZE_KEY: font_size,
+                SCHEME_KEY: scheme,
+                BRAILLE_FONT_KEY: braille_font,
+            }
+        )
+        data[VIEW_SECTION] = section_data
+        self._save(data)
+
+    def get_or_create_client_id(self) -> str:
+        data = self._load()
+        value = _get_section(data, CLIENT_SECTION).get(CLIENT_ID_KEY)
+        if isinstance(value, str) and value:
+            return value
+        client_id = str(uuid4())
+        section_data = _get_section(data, CLIENT_SECTION).copy()
+        section_data[CLIENT_ID_KEY] = client_id
+        data[CLIENT_SECTION] = section_data
+        self._save(data)
+        return client_id
+
+
+# Module-level API kept until P2-6 step 4: each call reads CONFIG_PATH and
+# delegates to a ConfigStore built for that call.
 
 
 def get_lang() -> str:
-    if _runtime_lang:
-        return _runtime_lang
-    lang = os.getenv(LANG_ENV)
-    if lang:
-        return lang
-    data = _load_from_file()
-    lang = data.get("language")
-    return lang or DEFAULT_FALLBACK
+    return ConfigStore(CONFIG_PATH).get_lang()
 
 
 def get_charset_maps() -> dict[str, str]:
-    return _get_dict_setting(
-        "language_detection",
-        "charset_maps",
-        DEFAULT_CHARSET_MAPS,
-    )
+    return ConfigStore(CONFIG_PATH).get_charset_maps()
 
 
 def set_lang(lang: str, persist: bool = False) -> None:
-    global _runtime_lang
-    _runtime_lang = lang
-    if persist:
-        data = _load_from_file()
-        data["language"] = lang
-        _save_to_file(data)
+    ConfigStore(CONFIG_PATH).set_lang(lang, persist)
 
 
 def get_translation_tables() -> dict:
-    return _get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)
+    return ConfigStore(CONFIG_PATH).get_translation_tables()
 
 
 def set_translation_tables(tables: dict[str, str]) -> None:
-    _set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))
+    ConfigStore(CONFIG_PATH).set_translation_tables(tables)
 
 
 def get_output_mode(default: str = DEFAULT_OUTPUT_MODE) -> str:
-    data = _load_from_file()
-    value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
-    return value if isinstance(value, str) else default
+    return ConfigStore(CONFIG_PATH).get_output_mode(default)
 
 
 def set_output_mode(output_mode: str) -> None:
-    _set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)
+    ConfigStore(CONFIG_PATH).set_output_mode(output_mode)
 
 
 def get_conversion_width(default: int = DEFAULT_CONVERSION_WIDTH) -> int:
-    data = _load_from_file()
-    width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
-    return width if width is not None else default
+    return ConfigStore(CONFIG_PATH).get_conversion_width(default)
 
 
 def set_conversion_width(width: int) -> None:
-    _set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)
+    ConfigStore(CONFIG_PATH).set_conversion_width(width)
 
 
 def get_selected_dictionary(default: str = "default") -> str:
-    data = _load_from_file()
-    value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
-    return value if isinstance(value, str) else default
+    return ConfigStore(CONFIG_PATH).get_selected_dictionary(default)
 
 
 def set_selected_dictionary(dictionary_name: str) -> None:
-    _set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)
+    ConfigStore(CONFIG_PATH).set_selected_dictionary(dictionary_name)
 
 
 def get_view_font_size(default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
-    data = _load_from_file()
-    font_size = _coerce_int(_get_section(data, VIEW_SECTION).get(FONT_SIZE_KEY))
-    return font_size if font_size is not None else default
+    return ConfigStore(CONFIG_PATH).get_view_font_size(default)
 
 
 def get_view_scheme(default: str = DEFAULT_VIEW_SCHEME) -> str:
-    data = _load_from_file()
-    value = _get_section(data, VIEW_SECTION).get(SCHEME_KEY)
-    return value if isinstance(value, str) else default
+    return ConfigStore(CONFIG_PATH).get_view_scheme(default)
 
 
 def get_braille_font(default: str = DEFAULT_BRAILLE_FONT) -> str:
-    data = _load_from_file()
-    value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
-    return value if isinstance(value, str) else default
+    return ConfigStore(CONFIG_PATH).get_braille_font(default)
 
 
 def set_view_settings(font_size: int, scheme: str, braille_font: str) -> None:
-    data = _load_from_file()
-    section_data = _get_section(data, VIEW_SECTION).copy()
-    section_data.update(
-        {
-            FONT_SIZE_KEY: font_size,
-            SCHEME_KEY: scheme,
-            BRAILLE_FONT_KEY: braille_font,
-        }
-    )
-    data[VIEW_SECTION] = section_data
-    _save_to_file(data)
+    ConfigStore(CONFIG_PATH).set_view_settings(font_size, scheme, braille_font)
 
 
 def get_or_create_client_id() -> str:
-    data = _load_from_file()
-    value = _get_section(data, CLIENT_SECTION).get(CLIENT_ID_KEY)
-    if isinstance(value, str) and value:
-        return value
-    client_id = str(uuid4())
-    section_data = _get_section(data, CLIENT_SECTION).copy()
-    section_data[CLIENT_ID_KEY] = client_id
-    data[CLIENT_SECTION] = section_data
-    _save_to_file(data)
-    return client_id
+    return ConfigStore(CONFIG_PATH).get_or_create_client_id()
EOF
git -C $REPO diff --stat -- client/config.py
```

Expected:

```text
 client/config.py | 299 +++++++++++++++++++++++++++++++++----------------------
 1 file changed, 181 insertions(+), 118 deletions(-)
```

- [ ] **Step 4: Run green: `test_config`, the modules that still use `CONFIG_PATH` and the module functions, the full suite.**

```bash
$PY -m unittest tests.test_config 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_app_paths tests.test_client_init tests.test_main_demo 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (33; the unchanged modules green through the delegates, 5 + 2 + 5 + 2 + 7 + 10 + 3 = 34; 1057 + 5):

```text
Ran 33 tests
OK
Ran 34 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1062 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/config.py client/tests/test_config.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add config store behind the config functions

config.ConfigStore owns one config file path: the constructor does no
IO, every getter re-reads the file, and the method bodies are today's
function bodies, so the file format, the first-save language_detection
defaults and the per-path load warning stay the same (P2-6 step 2). The
module functions now delegate to a store built from CONFIG_PATH at call
time; nothing else changes yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add config store behind the config functions
```

---

### Task 3: Inject the application paths and the config store at startup (spec step 3, part C)

**Interfaces:**
- Consumes: `ConfigStore` (Task 2), `app_paths.build_application_paths(root=None)`, `prepare_application_directories(paths=None, *, probe_factory)` (called with the paths from now on), `DocumentWorkspaceService(controller, workspace_dir)`, `write_dual_view_html(content, directory=None, ...)`, `cleanup_dual_view_html(directory=None)`.
- Produces: `BrailleFrame.__init__(self, *args, runtime, paths: ApplicationPaths, config_store: ConfigStore, **kwargs)` (all three keyword-only, required; stored as `translation_runtime`, `_paths`, `_config_store` before `_initialize_frame()`); `BrailleApp.OnInit()` sets `self.paths` and validates, cleans, builds the store, the runtime, the frame, shows it and calls `start_client_init_background(config_store)`; `BrailleApp.OnExit()` cleans `self.paths.dual_view` when `paths` is set; `load_translation_settings(store, dictionary_names)`, `save_translation_settings(store, settings)`, `load_view_settings(store)`, `save_view_settings(store, settings)`, `load_translation_tables(store)`, `save_translation_tables(store, tables)`; `start_client_init_background(config_store, *, run_client_init=..., thread_factory=...)` and `run_client_init(*, client_id_provider, locale_provider, ...)` (both providers required); `main.run_demo` builds its own paths and store. Test helper `make_paths(root=Path("unused-root"), **folders)` in `tests/test_gui_document_flows.py`.

- [ ] **Step 1: Move the tests to stores and paths and add the three wiring tests.** The four config/settings modules create `self.store = config.ConfigStore(tmp / "config.json")` instead of reassigning `CONFIG_PATH`; `test_conversion_language_explicit` patches `config.ConfigStore.get_lang`/`get_charset_maps`; the demo and client-init helpers drop their `CONFIG_PATH` patch; the frame factories set `_paths` and `_config_store` (`Mock(spec=gui.ConfigStore)`), and assertions that named a patched module function name the store instead; `ApplicationPathsWiringCharacterizationTest.make_frame` switches (refinement 7); the two `Mock()` paths become real ones (clarification 11). `test_unused_single_view_setters_are_removed` also checks `ConfigStore`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_client_init.py b/client/tests/test_client_init.py
index 99a1c82..b2b7cf1 100644
--- a/client/tests/test_client_init.py
+++ b/client/tests/test_client_init.py
@@ -249,12 +249,12 @@ class ClientInitConfigCharacterizationTest(unittest.TestCase):
         return _Response(self.RESPONSE)
 
     def start(self, thread_factory=_InlineThread):
-        """Start background client init against ``self.config_path`` (today: the module-level config path)."""
-        with patch.object(config, "CONFIG_PATH", str(self.config_path)):
-            return client_init.start_client_init_background(
-                run_client_init=partial(client_init.run_client_init, opener=self.opener),
-                thread_factory=thread_factory,
-            )
+        """Start background client init with a config store for ``self.config_path``."""
+        return client_init.start_client_init_background(
+            config.ConfigStore(self.config_path),
+            run_client_init=partial(client_init.run_client_init, opener=self.opener),
+            thread_factory=thread_factory,
+        )
 
     def test_first_start_creates_saves_and_sends_one_client_id(self) -> None:
         thread = self.start()
diff --git a/client/tests/test_config.py b/client/tests/test_config.py
index 2be0732..6556932 100644
--- a/client/tests/test_config.py
+++ b/client/tests/test_config.py
@@ -13,18 +13,16 @@ import config
 
 class ConfigTest(unittest.TestCase):
     def setUp(self) -> None:
-        self._original_config_path = config.CONFIG_PATH
         self._tmpdir = tempfile.TemporaryDirectory()
-        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
+        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self._original_config_path
         self._tmpdir.cleanup()
 
     def test_view_settings_are_persisted_under_view_section(self) -> None:
-        config.set_view_settings(18, "dark", "simbraille")
+        self.store.set_view_settings(18, "dark", "simbraille")
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -38,9 +36,9 @@ class ConfigTest(unittest.TestCase):
                 }
             },
         )
-        self.assertEqual(config.get_view_font_size(), 18)
-        self.assertEqual(config.get_view_scheme(), "dark")
-        self.assertEqual(config.get_braille_font("default"), "simbraille")
+        self.assertEqual(self.store.get_view_font_size(), 18)
+        self.assertEqual(self.store.get_view_scheme(), "dark")
+        self.assertEqual(self.store.get_braille_font("default"), "simbraille")
 
     def test_conversion_settings_roundtrip_under_conversion_section(self) -> None:
         tables = {
@@ -51,11 +49,11 @@ class ConfigTest(unittest.TestCase):
             "math": "UEB",
         }
 
-        config.set_translation_tables(tables)
-        config.set_output_mode("ascii")
-        config.set_conversion_width(52)
+        self.store.set_translation_tables(tables)
+        self.store.set_output_mode("ascii")
+        self.store.set_conversion_width(52)
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -69,19 +67,19 @@ class ConfigTest(unittest.TestCase):
                 }
             },
         )
-        self.assertEqual(config.get_translation_tables(), tables)
-        self.assertEqual(config.get_output_mode(), "ascii")
-        self.assertEqual(config.get_conversion_width(), 52)
+        self.assertEqual(self.store.get_translation_tables(), tables)
+        self.assertEqual(self.store.get_output_mode(), "ascii")
+        self.assertEqual(self.store.get_conversion_width(), 52)
 
     def test_translation_tables_default_includes_math_table(self) -> None:
-        tables = config.get_translation_tables()
+        tables = self.store.get_translation_tables()
 
         self.assertEqual(tables["math"], "UEB")
 
     def test_new_config_file_contains_language_detection_defaults(self) -> None:
-        config.set_output_mode("unicode")
+        self.store.set_output_mode("unicode")
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -90,7 +88,7 @@ class ConfigTest(unittest.TestCase):
         )
 
     def test_charset_maps_read_from_config_with_defaults_for_missing_values(self) -> None:
-        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
+        with open(self.store.path, "w", encoding="utf-8") as f:
             json.dump(
                 {
                     "language_detection": {
@@ -100,15 +98,15 @@ class ConfigTest(unittest.TestCase):
                 f,
             )
 
-        charset_maps = config.get_charset_maps()
+        charset_maps = self.store.get_charset_maps()
 
         self.assertEqual(charset_maps["arabicCharactersLanguage"], "fa")
         self.assertEqual(charset_maps["CJKCharactersLanguage"], "zh")
 
     def test_selected_dictionary_roundtrip_under_conversion_section(self) -> None:
-        config.set_selected_dictionary("math")
+        self.store.set_selected_dictionary("math")
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -120,10 +118,10 @@ class ConfigTest(unittest.TestCase):
                 }
             },
         )
-        self.assertEqual(config.get_selected_dictionary("default"), "math")
+        self.assertEqual(self.store.get_selected_dictionary("default"), "math")
 
     def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
-        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
+        with open(self.store.path, "w", encoding="utf-8") as f:
             json.dump(
                 {
                     "conversion": {"width": 52},
@@ -132,9 +130,9 @@ class ConfigTest(unittest.TestCase):
                 f,
             )
 
-        config.set_view_settings(14, "light", "default")
+        self.store.set_view_settings(14, "light", "default")
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -149,21 +147,22 @@ class ConfigTest(unittest.TestCase):
                 },
             },
         )
-        self.assertEqual(config.get_braille_font(), "default")
+        self.assertEqual(self.store.get_braille_font(), "default")
 
     def test_unused_single_view_setters_are_removed(self) -> None:
         for name in ("set_view_font_size", "set_view_scheme", "set_braille_font"):
             with self.subTest(name=name):
                 self.assertFalse(hasattr(config, name))
+                self.assertFalse(hasattr(config.ConfigStore, name))
 
     def test_braille_font_defaults_to_simbraille_when_config_is_missing(self) -> None:
-        self.assertEqual(config.get_braille_font(), "simbraille")
+        self.assertEqual(self.store.get_braille_font(), "simbraille")
 
     def test_client_id_is_generated_and_persisted_under_client_section(self) -> None:
-        client_id = config.get_or_create_client_id()
+        client_id = self.store.get_or_create_client_id()
 
         UUID(client_id)
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(
@@ -173,22 +172,22 @@ class ConfigTest(unittest.TestCase):
                 "client": {"id": client_id},
             },
         )
-        self.assertEqual(config.get_or_create_client_id(), client_id)
+        self.assertEqual(self.store.get_or_create_client_id(), client_id)
 
     def test_existing_client_id_is_reused(self) -> None:
         expected_client_id = "existing-client-id"
-        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
+        with open(self.store.path, "w", encoding="utf-8") as f:
             json.dump({"client": {"id": expected_client_id}}, f)
 
-        self.assertEqual(config.get_or_create_client_id(), expected_client_id)
+        self.assertEqual(self.store.get_or_create_client_id(), expected_client_id)
 
     def test_client_id_generation_preserves_unrelated_config_values(self) -> None:
-        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
+        with open(self.store.path, "w", encoding="utf-8") as f:
             json.dump({"view": {"font_size": 18}}, f)
 
-        client_id = config.get_or_create_client_id()
+        client_id = self.store.get_or_create_client_id()
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
 
         self.assertEqual(data["view"], {"font_size": 18})
@@ -281,38 +280,36 @@ class ConfigTest(unittest.TestCase):
 
 class ConfigSaveFailureLoggingTest(unittest.TestCase):
     def setUp(self) -> None:
-        self._original_config_path = config.CONFIG_PATH
         self._tmpdir = tempfile.TemporaryDirectory()
         self._blocker = Path(self._tmpdir.name) / "blocker"
         self._blocker.write_text("not a directory", encoding="utf-8")
-        config.CONFIG_PATH = str(self._blocker / "nested" / "config.json")
+        self.store = config.ConfigStore(self._blocker / "nested" / "config.json")
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self._original_config_path
         self._tmpdir.cleanup()
 
     def test_save_failure_is_logged_and_not_raised(self) -> None:
         with self.assertLogs("dotexpress.config", level="ERROR") as captured:
-            config.set_output_mode("ascii")
+            self.store.set_output_mode("ascii")
 
         self.assertEqual(len(captured.records), 1)
         record = captured.records[0]
         self.assertEqual(record.levelno, logging.ERROR)
         self.assertIsNotNone(record.exc_info)
-        self.assertIn(config.CONFIG_PATH, record.getMessage())
-        self.assertFalse(Path(config.CONFIG_PATH).exists())
+        self.assertIn(str(self.store.path), record.getMessage())
+        self.assertFalse(self.store.path.exists())
         self.assertTrue(self._blocker.is_file())
 
     def test_every_save_failure_is_logged(self) -> None:
         with self.assertLogs("dotexpress.config", level="ERROR") as captured:
-            config.set_output_mode("ascii")
-            config.set_conversion_width(52)
+            self.store.set_output_mode("ascii")
+            self.store.set_conversion_width(52)
 
         self.assertEqual(len(captured.records), 2)
 
     def test_save_failure_log_does_not_contain_config_data(self) -> None:
         with self.assertLogs("dotexpress.config", level="ERROR") as captured:
-            client_id = config.get_or_create_client_id()
+            client_id = self.store.get_or_create_client_id()
 
         UUID(client_id)
         self.assertNotIn(client_id, "\n".join(captured.output))
@@ -325,28 +322,26 @@ class ConfigSaveFailureLoggingTest(unittest.TestCase):
 
         try:
             with patch.object(config, "logger", unopenable):
-                config.set_output_mode("ascii")
+                self.store.set_output_mode("ascii")
         finally:
             handler.close()
 
         self.assertFalse(missing_log.parent.exists())
-        self.assertFalse(Path(config.CONFIG_PATH).exists())
+        self.assertFalse(self.store.path.exists())
 
 
 class ConfigLoadFailureLoggingTest(unittest.TestCase):
     def setUp(self) -> None:
-        self._original_config_path = config.CONFIG_PATH
         self._tmpdir = tempfile.TemporaryDirectory()
-        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
+        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")
         config._logged_load_failures.clear()
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self._original_config_path
         config._logged_load_failures.clear()
         self._tmpdir.cleanup()
 
     def _write_raw(self, content: bytes) -> None:
-        with open(config.CONFIG_PATH, "wb") as f:
+        with open(self.store.path, "wb") as f:
             f.write(content)
 
     def _warnings(self, captured) -> list[logging.LogRecord]:
@@ -356,34 +351,34 @@ class ConfigLoadFailureLoggingTest(unittest.TestCase):
         self._write_raw(b"{not json")
 
         with self.assertLogs("dotexpress.config", level="WARNING") as captured:
-            output_mode = config.get_output_mode()
-            width = config.get_conversion_width()
+            output_mode = self.store.get_output_mode()
+            width = self.store.get_conversion_width()
 
         self.assertEqual(output_mode, config.DEFAULT_OUTPUT_MODE)
         self.assertEqual(width, config.DEFAULT_CONVERSION_WIDTH)
         warnings = self._warnings(captured)
         self.assertEqual(len(warnings), 1)
-        self.assertIn(config.CONFIG_PATH, warnings[0].getMessage())
+        self.assertIn(str(self.store.path), warnings[0].getMessage())
         self.assertIn("using defaults", warnings[0].getMessage())
         self.assertIsNotNone(warnings[0].exc_info)
 
     def test_warning_is_emitted_again_after_recovery(self) -> None:
         with self.assertLogs("dotexpress.config", level="WARNING") as captured:
             self._write_raw(b"{not json")
-            config.get_output_mode()
+            self.store.get_output_mode()
             self._write_raw(b'{"conversion": {"output_mode": "ascii"}}')
-            self.assertEqual(config.get_output_mode(), "ascii")
+            self.assertEqual(self.store.get_output_mode(), "ascii")
             self._write_raw(b"{not json")
-            config.get_output_mode()
+            self.store.get_output_mode()
 
         self.assertEqual(len(self._warnings(captured)), 2)
 
     def test_different_failure_on_same_path_is_logged_again(self) -> None:
         with self.assertLogs("dotexpress.config", level="WARNING") as captured:
             self._write_raw(b"{not json")
-            config.get_output_mode()
+            self.store.get_output_mode()
             self._write_raw(b"\xff\xfe\x00")
-            config.get_output_mode()
+            self.store.get_output_mode()
 
         self.assertEqual(len(self._warnings(captured)), 2)
 
@@ -391,17 +386,17 @@ class ConfigLoadFailureLoggingTest(unittest.TestCase):
         other_path = str(Path(self._tmpdir.name) / "other.json")
         with self.assertLogs("dotexpress.config", level="WARNING") as captured:
             self._write_raw(b"{not json")
-            config.get_output_mode()
-            config.CONFIG_PATH = other_path
+            self.store.get_output_mode()
+            self.store = config.ConfigStore(other_path)
             self._write_raw(b"{not json")
-            config.get_output_mode()
+            self.store.get_output_mode()
 
         self.assertEqual(len(self._warnings(captured)), 2)
 
     def test_missing_file_is_not_logged(self) -> None:
         with patch.object(config, "logger") as logger:
-            self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
-            self.assertEqual(config.get_charset_maps(), config.DEFAULT_CHARSET_MAPS)
+            self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
+            self.assertEqual(self.store.get_charset_maps(), config.DEFAULT_CHARSET_MAPS)
 
         self.assertEqual(logger.mock_calls, [])
 
@@ -414,7 +409,7 @@ class ConfigLoadFailureLoggingTest(unittest.TestCase):
 
         try:
             with patch.object(config, "logger", unopenable):
-                self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
+                self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
         finally:
             handler.close()
 
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
index a3da26a..9671e84 100644
--- a/client/tests/test_conversion_language_explicit.py
+++ b/client/tests/test_conversion_language_explicit.py
@@ -84,9 +84,9 @@ class ConversionLanguageTest(unittest.TestCase):
         math_translator = RecordingMathTranslator()
         config._runtime_lang = "ko"
         with patch.dict(os.environ, {config.LANG_ENV: env_lang}), patch.object(
-            config, "get_lang", side_effect=AssertionError("config.get_lang must not be read")
+            config.ConfigStore, "get_lang", side_effect=AssertionError("ConfigStore.get_lang must not be read")
         ), patch.object(
-            config, "get_charset_maps", side_effect=AssertionError("config.get_charset_maps must not be read")
+            config.ConfigStore, "get_charset_maps", side_effect=AssertionError("ConfigStore.get_charset_maps must not be read")
         ):
             output = convert_text_with_alignment(
                 request,
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index f2e2199..4163476 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -8,6 +8,7 @@ import tempfile
 import unittest
 import zipfile
 from contextlib import ExitStack
+from dataclasses import replace
 from pathlib import Path
 from types import SimpleNamespace
 from unittest.mock import ANY, DEFAULT, Mock, call, patch
@@ -43,6 +44,11 @@ from dual_view.html import render_dual_view_html
 from dual_view.model import build_dual_view_model
 
 
+def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
+    """Application paths under ``root``, with the given folders replaced (P2-6)."""
+    return replace(app_paths.build_application_paths(root), **folders)
+
+
 def make_snapshot(
     *,
     translation=TranslationSettings("unicode", 40, "default"),
@@ -60,6 +66,8 @@ class GuiDocumentFlowsTest(unittest.TestCase):
     def _make_frame(self, documents=(Document("alpha", "source", None),), open_name="alpha") -> gui.BrailleFrame:
         frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
         frame.translation_runtime = Mock()
+        frame._paths = make_paths()
+        frame._config_store = Mock(spec=gui.ConfigStore)
         frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
         frame._conversion_presenter.is_running.return_value = False
         frame._convert_dialog = Mock()
@@ -137,7 +145,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         ):
             frame.on_open_dual_view(None)
 
-        write_html.assert_called_once_with("<html>dual</html>")
+        write_html.assert_called_once_with("<html>dual</html>", frame._paths.dual_view)
         open_browser.assert_called_once_with(html_path, (1024, 768))
 
     def test_dual_view_menu_reports_write_or_launch_failure(self) -> None:
@@ -177,7 +185,7 @@ class DocumentControllerOwnershipTest(unittest.TestCase):
             patch.object(gui.BrailleFrame, "_initialize_frame", autospec=True, side_effect=initialize_frame),
             patch.multiple(gui.BrailleFrame, **{name: DEFAULT for name in self.STARTUP_STEPS}),
         ):
-            frame = gui.BrailleFrame(None, runtime=Mock())
+            frame = gui.BrailleFrame(None, runtime=Mock(), paths=make_paths(), config_store=Mock())
 
         self.assertEqual(len(seen), 1)
         self.assertIsInstance(seen[0], gui.DocumentController)
@@ -189,11 +197,11 @@ class DocumentControllerOwnershipTest(unittest.TestCase):
         controller = DocumentController(documents=[Document("alpha", "a", "1")], open_name="alpha")
         frame._document_controller = controller
         frame._register_output_font = Mock(return_value=False)
+        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
+        frame._config_store = Mock(spec=gui.ConfigStore)
         with (
-            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
             patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
             patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
-            patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
             patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
             patch.object(gui, "load_translation_tables", return_value={}),
         ):
@@ -203,6 +211,15 @@ class DocumentControllerOwnershipTest(unittest.TestCase):
         self.assertEqual(controller.document_names, ["alpha"])
         self.assertEqual(controller.open_document_name, "alpha")
 
+    def test_frame_requires_paths_and_config_store(self) -> None:
+        parameters = inspect.signature(gui.BrailleFrame.__init__).parameters
+
+        for name in ("runtime", "paths", "config_store"):
+            with self.subTest(name=name):
+                self.assertIn(name, parameters)
+                self.assertIs(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
+                self.assertIs(parameters[name].default, inspect.Parameter.empty)
+
 
 class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
     """The frame hands workspace IO to its service and keeps the dialogs and UI updates."""
@@ -245,11 +262,11 @@ class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
         frame = object.__new__(gui.BrailleFrame)
         frame._document_controller = DocumentController()
         frame._register_output_font = Mock(return_value=False)
+        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=self.workspace)
+        frame._config_store = Mock(spec=gui.ConfigStore)
         with (
-            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
             patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
             patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
-            patch.object(gui, "get_workspace_directory", return_value=self.workspace),
             patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
             patch.object(gui, "load_translation_tables", return_value={}),
         ):
@@ -500,13 +517,11 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
         runtime = Mock()
         frame = Mock()
+        paths = make_paths(Path("C:/DotExpress"))
 
         with (
-            patch.object(
-                gui,
-                "prepare_application_directories",
-                return_value=Mock(dual_view=Path("C:/DotExpress/dual_view")),
-            ),
+            patch.object(gui, "build_application_paths", return_value=paths),
+            patch.object(gui, "prepare_application_directories", return_value=paths),
             patch.object(gui, "cleanup_dual_view_html"),
             patch.object(gui, "build_default_translation_runtime", return_value=runtime),
             patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
@@ -516,7 +531,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
             result = app.OnInit()
 
         self.assertTrue(result)
-        frame_class.assert_called_once_with(None, runtime=runtime)
+        frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=ANY)
         frame.Show.assert_called_once_with()
 
     def test_app_validates_application_data_before_building_runtime(self) -> None:
@@ -525,10 +540,11 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         order: list[str] = []
 
         with (
+            patch.object(gui, "build_application_paths", return_value=make_paths(Path("C:/DotExpress"))),
             patch.object(
                 gui,
                 "prepare_application_directories",
-                side_effect=lambda: (order.append("paths"), Mock(dual_view=Path("C:/DotExpress/dual_view")))[1],
+                side_effect=lambda paths: (order.append("paths"), paths)[1],
             ),
             patch.object(gui, "cleanup_dual_view_html"),
             patch.object(gui, "build_default_translation_runtime", side_effect=lambda: (order.append("runtime"), runtime)[1]),
@@ -567,6 +583,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def test_app_exit_without_initialized_runtime_is_safe(self) -> None:
         app = gui.BrailleApp()
+        app.paths = make_paths(Path("C:/DotExpress"))
         app.translation_runtime = None
 
         with patch.object(gui, "cleanup_dual_view_html"):
@@ -575,6 +592,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_app_exit_closes_runtime(self) -> None:
         runtime = Mock()
         app = gui.BrailleApp()
+        app.paths = make_paths(Path("C:/DotExpress"))
         app.translation_runtime = runtime
 
         with patch.object(gui, "cleanup_dual_view_html"):
@@ -584,12 +602,12 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         runtime.close.assert_called_once_with()
 
     def test_app_cleans_stale_dual_view_html_after_path_validation(self) -> None:
-        paths = Mock()
-        paths.dual_view = Path("C:/DotExpress/dual_view")
+        paths = make_paths(Path("C:/DotExpress"))
         runtime = Mock()
         frame = Mock()
 
         with (
+            patch.object(gui, "build_application_paths", return_value=paths),
             patch.object(gui, "prepare_application_directories", return_value=paths),
             patch.object(gui, "cleanup_dual_view_html") as cleanup,
             patch.object(gui, "build_default_translation_runtime", return_value=runtime),
@@ -602,11 +620,11 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         cleanup.assert_called_once_with(paths.dual_view)
 
     def test_app_reports_startup_cleanup_failure_before_runtime(self) -> None:
-        paths = Mock()
-        paths.dual_view = Path("C:/DotExpress/dual_view")
+        paths = make_paths(Path("C:/DotExpress"))
         cause = PermissionError("locked")
 
         with (
+            patch.object(gui, "build_application_paths", return_value=paths),
             patch.object(gui, "prepare_application_directories", return_value=paths),
             patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
             patch.object(gui, "build_default_translation_runtime") as build_runtime,
@@ -622,6 +640,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
         runtime = Mock()
         app = gui.BrailleApp()
+        app.paths = make_paths(Path("C:/DotExpress"))
         app.translation_runtime = runtime
         error = OSError("locked")
 
@@ -689,6 +708,61 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         message_box.assert_called_once()
         self.assertIn(str(error.path), message_box.call_args.args[0])
 
+    def test_app_passes_the_validated_paths_and_one_store(self) -> None:
+        paths = make_paths(Path("C:/DotExpress"))
+        runtime = Mock()
+        frame = Mock()
+        order: list[str] = []
+        stores: list = []
+        store_class = gui.ConfigStore
+
+        def build_store(path):
+            order.append("store")
+            stores.append(store_class(path))
+            return stores[-1]
+
+        with (
+            patch.object(gui, "build_application_paths", return_value=paths) as build_paths,
+            patch.object(
+                gui,
+                "prepare_application_directories",
+                side_effect=lambda validated: (order.append("prepare"), validated)[1],
+            ) as prepare,
+            patch.object(gui, "cleanup_dual_view_html", side_effect=lambda folder: order.append("cleanup")) as cleanup,
+            patch.object(gui, "ConfigStore", side_effect=build_store),
+            patch.object(
+                gui,
+                "build_default_translation_runtime",
+                side_effect=lambda: (order.append("runtime"), runtime)[1],
+            ),
+            patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
+            patch.object(gui, "start_client_init_background") as start_client_init,
+        ):
+            app = gui.BrailleApp()
+            self.assertTrue(app.OnInit())
+
+        build_paths.assert_called_once_with()
+        self.assertIs(prepare.call_args.args[0], paths)
+        self.assertIs(app.paths, paths)
+        cleanup.assert_called_once_with(paths.dual_view)
+        self.assertEqual(order, ["prepare", "cleanup", "store", "runtime"])
+        self.assertEqual(len(stores), 1)
+        self.assertEqual(stores[0].path, paths.config)
+        frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=stores[0])
+        self.assertIs(frame_class.call_args.kwargs["paths"], paths)
+        start_client_init.assert_called_once_with(stores[0])
+
+    def test_app_exit_cleans_the_validated_dual_view_folder(self) -> None:
+        app = gui.BrailleApp()
+        app.paths = make_paths(Path("C:/DotExpress"))
+        app.translation_runtime = Mock()
+
+        with patch.object(gui, "cleanup_dual_view_html") as cleanup:
+            self.assertEqual(app.OnExit(), 0)
+
+        cleanup.assert_called_once_with(Path("C:/DotExpress/dual_view"))
+        app.translation_runtime.close.assert_called_once_with()
+
     def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
         frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._dual_view_frame = Mock()
@@ -840,15 +914,15 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame = object.__new__(gui.BrailleFrame)
         frame._document_controller = DocumentController()
         frame._register_output_font = Mock(return_value=False)
+        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
+        frame._config_store = Mock(spec=gui.ConfigStore)
         with (
-            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
             patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
             patch.object(
                 gui,
                 "load_translation_settings",
                 return_value=TranslationSettings("unicode", 40, "default"),
             ),
-            patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
             patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
             patch.object(gui, "load_translation_tables", return_value=loaded_tables) as load_tables,
         ):
@@ -861,7 +935,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame, load_tables = self._initialize_state_with_loaded_tables(loaded_tables)
 
         self.assertEqual(frame.translation_tables, loaded_tables)
-        load_tables.assert_called_once_with()
+        load_tables.assert_called_once_with(frame._config_store)
 
     def test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty(self) -> None:
         frame, _load_tables = self._initialize_state_with_loaded_tables({})
@@ -887,10 +961,10 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_conversion_request_copies_frame_translation_tables(self) -> None:
         frame = self._make_frame()
         frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}
+        frame._config_store.get_lang.return_value = "zh_TW"
+        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
 
-        with patch.object(gui, "get_lang", return_value="zh_TW"), \
-             patch.object(gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}):
-            request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
 
         self.assertEqual(
             request.translation_tables,
@@ -908,9 +982,9 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
              patch.object(gui, "save_translation_tables"), \
              patch.object(gui, "save_view_settings"):
             frame.apply_settings_from_dialog(snapshot)
-        with patch.object(gui, "get_lang", return_value="zh_TW"), \
-             patch.object(gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}):
-            request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        frame._config_store.get_lang.return_value = "zh_TW"
+        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
+        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
 
         self.assertEqual(request.translation_tables, snapshot.translation_tables)
 
@@ -920,15 +994,16 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         first_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
         second_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "ja"}
 
-        with patch.object(gui, "get_lang", side_effect=["en", "zh_TW"]) as get_lang, \
-             patch.object(gui, "get_charset_maps", side_effect=[first_maps, second_maps]) as get_charset_maps:
-            first = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
-            second = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        frame._config_store.get_lang.side_effect = ["en", "zh_TW"]
+        frame._config_store.get_charset_maps.side_effect = [first_maps, second_maps]
+
+        first = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        second = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
 
         self.assertEqual((first.lang, first.charset_maps), ("en", first_maps))
         self.assertEqual((second.lang, second.charset_maps), ("zh_TW", second_maps))
-        self.assertEqual(get_lang.call_count, 2)
-        self.assertEqual(get_charset_maps.call_count, 2)
+        self.assertEqual(frame._config_store.get_lang.call_count, 2)
+        self.assertEqual(frame._config_store.get_charset_maps.call_count, 2)
 
     def test_translation_tables_are_not_module_state(self) -> None:
         self.assertFalse(hasattr(gui, "language_map_translate_table"))
@@ -1044,14 +1119,14 @@ class DictionaryManagementFrameTest(unittest.TestCase):
             frame = object.__new__(gui.BrailleFrame)
             frame._document_controller = DocumentController()
             frame._register_output_font = Mock(return_value=False)
+            frame._paths = make_paths(dictionary=dictionary_dir, workspace=Path("workspace"))
+            frame._config_store = Mock(spec=gui.ConfigStore)
             with (
-                patch.object(gui, "get_dictionary_directory", return_value=dictionary_dir),
                 patch.object(
                     gui,
                     "load_translation_settings",
                     return_value=TranslationSettings("unicode", 40, "alpha"),
                 ) as load_settings,
-                patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
                 patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
                 patch.object(gui, "load_translation_tables", return_value={}),
             ):
@@ -1060,17 +1135,16 @@ class DictionaryManagementFrameTest(unittest.TestCase):
             view = Mock()
             view.confirm.return_value = True
 
-            with patch.object(gui, "set_selected_dictionary") as set_selected:
-                selected = presenter.delete(view, "alpha")
+            selected = presenter.delete(view, "alpha")
 
             remaining = sorted(path.name for path in dictionary_dir.iterdir())
 
         self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
         self.assertEqual(presenter.dictionary_dir, dictionary_dir)
-        load_settings.assert_called_once_with(["alpha", "default"])
+        load_settings.assert_called_once_with(frame._config_store, ["alpha", "default"])
         self.assertEqual(selected, "default")
         self.assertEqual(remaining, ["default.csv"])
-        set_selected.assert_called_once_with("default")
+        frame._config_store.set_selected_dictionary.assert_called_once_with("default")
         self.assertEqual(frame.translation_settings, TranslationSettings("unicode", 40, "default"))
 
     def test_frame_dictionary_callbacks_are_removed(self) -> None:
@@ -2466,8 +2540,6 @@ class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
             patch.object(gui.wx, "CallLater", self.timers),
             patch.object(gui.wx, "EVT_CLOSE", "EVT_CLOSE"),
             patch.object(gui, "ConvertingDialog", self._converting_dialog_class()),
-            patch.object(gui, "get_lang", return_value=self.LANG),
-            patch.object(gui, "get_charset_maps", return_value=dict(self.CHARSET_MAPS)),
         ):
             patcher.start()
             self.addCleanup(patcher.stop)
@@ -2601,6 +2673,9 @@ class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
         frame.translation_tables = dict(self.TABLES)
         frame.translation_settings = TranslationSettings("ascii", 32, "default")
         frame.dictionary_dir = self.root / "dictionary"
+        frame._config_store = Mock(spec=gui.ConfigStore)
+        frame._config_store.get_lang.return_value = self.LANG
+        frame._config_store.get_charset_maps.return_value = dict(self.CHARSET_MAPS)
         self._wire_conversion(frame)
         return frame
 
@@ -3279,11 +3354,11 @@ class FrameConversionDelegationTest(unittest.TestCase):
         frame = self._make_frame()
         frame.translation_settings = TranslationSettings("ascii", 32, "math")
         frame.dictionary_dir = Path("dictionaries")
+        frame._config_store = Mock(spec=gui.ConfigStore)
+        frame._config_store.get_lang.return_value = "zh_TW"
+        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
 
-        with patch.object(gui, "get_lang", return_value="zh_TW"), patch.object(
-            gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}
-        ):
-            request = frame._build_conversion_request_for_text("text")
+        request = frame._build_conversion_request_for_text("text")
 
         self.assertEqual(
             request,
@@ -3695,6 +3770,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         frame = object.__new__(gui.BrailleFrame)
         frame.view_settings = view
         frame._apply_editor_view_settings = Mock()
+        frame._config_store = Mock(spec=gui.ConfigStore)
         return frame
 
     def make_dialog(self):
@@ -3730,7 +3806,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
             patch.object(
                 gui,
                 "save_view_settings",
-                side_effect=lambda _view: dialog_size_when_saved.append(dialog.snapshot.view.font_size),
+                side_effect=lambda _store, _view: dialog_size_when_saved.append(dialog.snapshot.view.font_size),
             ) as save,
         ):
             frame.on_editor_mousewheel(event)
@@ -3738,7 +3814,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         expected = ViewSettings(13, "dark", "default")
         self.assertEqual(frame.view_settings, expected)
         frame._apply_editor_view_settings.assert_called_once_with(expected)
-        save.assert_called_once_with(expected)
+        save.assert_called_once_with(frame._config_store, expected)
         self.assertEqual(dialog_size_when_saved, [12])
         self.assertEqual(dialog.snapshot, make_snapshot(view=ViewSettings(13, "light", "simbraille")))
         self.assertEqual(dialog.window_calls.mock_calls, [])  # the editor keeps the focus
@@ -3756,7 +3832,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
                 expected = ViewSettings(start, "dark", "default")
                 self.assertEqual(frame.view_settings, expected)
                 frame._apply_editor_view_settings.assert_called_once_with(expected)
-                save.assert_called_once_with(expected)
+                save.assert_called_once_with(frame._config_store, expected)
                 self.assertEqual(dialog.snapshot.view, ViewSettings(start, "light", "simbraille"))
 
     def test_a_wheel_without_a_step_is_skipped_and_changes_nothing(self) -> None:
@@ -3782,7 +3858,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         expected = ViewSettings(11, "dark", "default")
         self.assertEqual(frame.view_settings, expected)
         frame._apply_editor_view_settings.assert_called_once_with(expected)
-        save.assert_called_once_with(expected)
+        save.assert_called_once_with(frame._config_store, expected)
 
     def test_a_cancelled_dialog_is_no_longer_synced(self) -> None:
         frame = self.make_frame()
@@ -3797,7 +3873,10 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         self.assertEqual(frame.view_settings, ViewSettings(14, "dark", "default"))
         self.assertEqual(
             save.call_args_list,
-            [call(ViewSettings(13, "dark", "default")), call(ViewSettings(14, "dark", "default"))],
+            [
+                call(frame._config_store, ViewSettings(13, "dark", "default")),
+                call(frame._config_store, ViewSettings(14, "dark", "default")),
+            ],
         )
         self.assertEqual(dialog.snapshot.view, ViewSettings(13, "light", "simbraille"))
 
@@ -3811,7 +3890,7 @@ class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
         ):
             frame.on_editor_mousewheel(self.wheel(120))
 
-        save.assert_called_once_with(ViewSettings(13, "dark", "default"))
+        save.assert_called_once_with(frame._config_store, ViewSettings(13, "dark", "default"))
         self.assertEqual(text_dialog.mock_calls, [])
 
 
@@ -3832,16 +3911,21 @@ class ApplicationPathsWiringCharacterizationTest(unittest.TestCase):
     def make_frame(self) -> gui.BrailleFrame:
         """A bare frame whose application data lives under ``self.root``.
 
-        Today the frame resolves its folders and its config file through module-level
-        defaults, so the application root and the import-time config path are patched.
+        The frame gets paths built from the root and one config store for them. The real
+        application root and the module-level config path point at an empty decoy folder,
+        so anything still resolved implicitly misses ``self.root`` and never reaches ``client/``.
         """
+        decoy = self.root.parent / "decoy"
         for patcher in (
-            patch.object(app_paths, "get_application_root", return_value=self.root),
-            patch.object(config, "CONFIG_PATH", str(self.config_path)),
+            patch.object(app_paths, "get_application_root", return_value=decoy),
+            patch.object(config, "CONFIG_PATH", str(decoy / "config.json")),
         ):
             patcher.start()
             self.addCleanup(patcher.stop)
-        return object.__new__(gui.BrailleFrame)
+        frame = object.__new__(gui.BrailleFrame)
+        frame._paths = app_paths.build_application_paths(self.root)
+        frame._config_store = config.ConfigStore(frame._paths.config)
+        return frame
 
     def write_config(self, data: dict) -> None:
         self.config_path.write_text(json.dumps(data), encoding="utf-8")
diff --git a/client/tests/test_main_demo.py b/client/tests/test_main_demo.py
index 74d5185..b0b11ad 100644
--- a/client/tests/test_main_demo.py
+++ b/client/tests/test_main_demo.py
@@ -15,11 +15,12 @@ class MainDemoTest(unittest.TestCase):
     def test_demo_uses_alignment_conversion_output(self) -> None:
         runtime = Mock()
         output = ConversionOutput("braille", (), ())
+        paths = app_paths.build_application_paths(Path("C:/Portable/DotExpress"))
         dictionary_directory = Path("C:/Portable/DotExpress/dictionary")
         with (
             patch.object(main, "build_default_translation_runtime", return_value=runtime),
             patch.object(main, "convert_text_with_alignment", return_value=output) as convert,
-            patch.object(main, "get_dictionary_directory", return_value=dictionary_directory),
+            patch.object(main, "build_application_paths", return_value=paths),
             patch("builtins.print") as print_mock,
         ):
             main.run_demo("source")
@@ -38,8 +39,8 @@ class MainDemoTest(unittest.TestCase):
         with (
             patch.object(main, "build_default_translation_runtime", return_value=runtime),
             patch.object(main, "convert_text_with_alignment", return_value=ConversionOutput("braille", (), ())) as convert,
-            patch.object(main, "get_lang", return_value="en") as get_lang,
-            patch.object(main, "get_charset_maps", return_value=charset_maps) as get_charset_maps,
+            patch.object(main.ConfigStore, "get_lang", return_value="en") as get_lang,
+            patch.object(main.ConfigStore, "get_charset_maps", return_value=charset_maps) as get_charset_maps,
             patch("builtins.print") as print_mock,
         ):
             main.run_demo("x")
@@ -55,11 +56,10 @@ class MainDemoTest(unittest.TestCase):
     def run_demo_at_root(self, root: Path):
         """Run the demo with its application data under ``root``; return the request.
 
-        P2-6: today the application root and the import-time config path are patched.
+        P2-6: the demo builds its paths and config store from the application root.
         """
         with (
             patch.object(app_paths, "get_application_root", return_value=root),
-            patch.object(config, "CONFIG_PATH", str(root / "config.json")),
             patch.dict(os.environ),
             patch.object(config, "_runtime_lang", None),
             patch.object(main, "build_default_translation_runtime", return_value=Mock()),
diff --git a/client/tests/test_translation_settings.py b/client/tests/test_translation_settings.py
index 2fce7d7..93a6ef1 100644
--- a/client/tests/test_translation_settings.py
+++ b/client/tests/test_translation_settings.py
@@ -15,16 +15,14 @@ from settings.translation import (
 
 class TranslationSettingsTest(unittest.TestCase):
     def setUp(self) -> None:
-        self._original_config_path = config.CONFIG_PATH
         self._tmpdir = tempfile.TemporaryDirectory()
-        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
+        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self._original_config_path
         self._tmpdir.cleanup()
 
     def _write_config(self, conversion: dict[str, object]) -> None:
-        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
+        with open(self.store.path, "w", encoding="utf-8") as f:
             json.dump({"conversion": conversion}, f)
 
     def test_load_normalizes_invalid_config(self) -> None:
@@ -36,7 +34,7 @@ class TranslationSettingsTest(unittest.TestCase):
             }
         )
 
-        settings = load_translation_settings(["default", "math"])
+        settings = load_translation_settings(self.store, ["default", "math"])
 
         self.assertEqual(
             settings,
@@ -57,16 +55,16 @@ class TranslationSettingsTest(unittest.TestCase):
         )
 
         self.assertEqual(
-            load_translation_settings(["default", "math"]),
+            load_translation_settings(self.store, ["default", "math"]),
             TranslationSettings("ascii", 52, "math"),
         )
 
     def test_save_persists_one_complete_settings_value(self) -> None:
         settings = TranslationSettings("ascii", 64, "math")
 
-        save_translation_settings(settings)
+        save_translation_settings(self.store, settings)
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             self.assertEqual(
                 json.load(f),
                 {
diff --git a/client/tests/test_translation_tables.py b/client/tests/test_translation_tables.py
index 2c7bba8..646bed1 100644
--- a/client/tests/test_translation_tables.py
+++ b/client/tests/test_translation_tables.py
@@ -9,19 +9,17 @@ from settings.translation_tables import load_translation_tables, save_translatio
 
 class TranslationTablesTest(unittest.TestCase):
     def setUp(self) -> None:
-        self._original_config_path = config.CONFIG_PATH
         self._tmpdir = tempfile.TemporaryDirectory()
-        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
+        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self._original_config_path
         self._tmpdir.cleanup()
 
     def test_load_translation_tables_returns_copy(self) -> None:
         stored_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"}
-        config.set_translation_tables(stored_tables)
+        self.store.set_translation_tables(stored_tables)
 
-        loaded_tables = load_translation_tables()
+        loaded_tables = load_translation_tables(self.store)
 
         self.assertEqual(loaded_tables["default"], "zh-tw.ctb")
         self.assertEqual(loaded_tables["en"], "en-ueb-g1.ctb")
@@ -31,15 +29,15 @@ class TranslationTablesTest(unittest.TestCase):
         loaded_tables["en"] = "changed"
 
         self.assertEqual(stored_tables["en"], "en-ueb-g1.ctb")
-        self.assertEqual(config.get_translation_tables()["en"], "en-ueb-g1.ctb")
+        self.assertEqual(self.store.get_translation_tables()["en"], "en-ueb-g1.ctb")
 
     def test_save_translation_tables_passes_copy(self) -> None:
         tables = {"default": "zh-tw.ctb", "math": "UEB"}
 
-        save_translation_tables(tables)
+        save_translation_tables(self.store, tables)
         tables["math"] = "Nemeth"
 
-        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
+        with open(self.store.path, "r", encoding="utf-8") as f:
             data = json.load(f)
         self.assertEqual(
             data["conversion"]["translation_tables"],
diff --git a/client/tests/test_view_settings.py b/client/tests/test_view_settings.py
index d93bceb..4f82467 100644
--- a/client/tests/test_view_settings.py
+++ b/client/tests/test_view_settings.py
@@ -13,12 +13,10 @@ from settings.view import (
 
 class ViewSettingsTest(unittest.TestCase):
     def setUp(self) -> None:
-        self.original_path = config.CONFIG_PATH
         self.temp_dir = tempfile.TemporaryDirectory()
-        config.CONFIG_PATH = str(Path(self.temp_dir.name) / "config.json")
+        self.store = config.ConfigStore(Path(self.temp_dir.name) / "config.json")
 
     def tearDown(self) -> None:
-        config.CONFIG_PATH = self.original_path
         self.temp_dir.cleanup()
 
     def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
@@ -29,8 +27,8 @@ class ViewSettingsTest(unittest.TestCase):
 
     def test_save_and_load_round_trip_as_one_value(self) -> None:
         expected = ViewSettings(18, "dark", "default")
-        save_view_settings(expected)
-        self.assertEqual(load_view_settings(), expected)
+        save_view_settings(self.store, expected)
+        self.assertEqual(load_view_settings(self.store), expected)
 
 
 class ViewSettingsNormalizeTest(unittest.TestCase):
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_client_init.py                  |  12 +-
 client/tests/test_config.py                       | 125 +++++++-------
 client/tests/test_conversion_language_explicit.py |   4 +-
 client/tests/test_gui_document_flows.py           | 194 ++++++++++++++++------
 client/tests/test_main_demo.py                    |  10 +-
 client/tests/test_translation_settings.py         |  14 +-
 client/tests/test_translation_tables.py           |  14 +-
 client/tests/test_view_settings.py                |   8 +-
 8 files changed, 227 insertions(+), 154 deletions(-)
```

- [ ] **Step 2: Run red.** Failures and errors per module:

```bash
$PY -m unittest tests.test_config tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_main_demo tests.test_client_init tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//' | sed -E 's/^(FAIL|ERROR): .*\((tests\.)?(test_[a-z_]+)\..*/\1 \3/' | LC_ALL=C sort | uniq -c
```

Expected (7 failures and 92 errors in 220 tests: the settings loaders and savers do not take a store yet, the demo and client init still read `CONFIG_PATH`, and every gui test whose frame factory names `gui.ConfigStore` or the new keyword arguments errors; `test_config` and `test_conversion_language_explicit` already pass against Task 2's store):

```text
      3 ERROR test_client_init
     81 ERROR test_gui_document_flows
      2 ERROR test_main_demo
      3 ERROR test_translation_settings
      2 ERROR test_translation_tables
      1 ERROR test_view_settings
      6 FAIL test_gui_document_flows
      1 FAIL test_main_demo
      1 FAILED (failures=7, errors=92, skipped=2)
      1 Ran 220 tests
```

- [ ] **Step 3: Inject the paths and the store.** In `gui.py` (tabs): imports, `BrailleFrame.__init__`, `_initialize_state`, `_open_dual_view_in_browser`, `apply_settings_from_dialog`, `_set_active_dictionary`, `_build_conversion_request`, `_set_view_font_size`, `OnInit`, `OnExit` (refinement 8 for the kept import). In the three `settings` modules, `client_init.py` and `main.py` (4 spaces): per D6, D7, D12.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/client_init.py b/client/client_init.py
index 7d9c5ae..df9519c 100644
--- a/client/client_init.py
+++ b/client/client_init.py
@@ -11,7 +11,6 @@ import urllib.request
 from urllib.error import URLError
 
 import about
-from config import get_lang, get_or_create_client_id
 from log import get_logger
 
 logger = get_logger("dotexpress.client_init", "init.log")
@@ -142,11 +141,11 @@ def post_client_init(
 def run_client_init(
     *,
     version: str = about.version,
-    client_id_provider=get_or_create_client_id,
+    client_id_provider,
     os_name_provider=platform.system,
     os_version_provider=platform.version,
     arch_provider=platform.machine,
-    locale_provider=get_lang,
+    locale_provider,
     opener=urllib.request.urlopen,
     timeout: float = DEFAULT_TIMEOUT,
 ) -> ClientInitResult:
@@ -162,13 +161,17 @@ def run_client_init(
 
 
 def start_client_init_background(
+    config_store,
     *,
     run_client_init=run_client_init,
     thread_factory=threading.Thread,
 ):
     def worker():
         try:
-            run_client_init()
+            run_client_init(
+                client_id_provider=config_store.get_or_create_client_id,
+                locale_provider=config_store.get_lang,
+            )
         except Exception:
             pass
 
diff --git a/client/gui.py b/client/gui.py
index cb3bfe7..94744d8 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -7,7 +7,7 @@ import wx
 
 import about
 from i18n import _, resource_path
-from app_paths import ApplicationDataError, prepare_application_directories
+from app_paths import ApplicationDataError, ApplicationPaths, build_application_paths, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
 from conversion.math_service import latex_to_mathml
@@ -27,19 +27,13 @@ from documents.workspace import (
     DEFAULT_DOCUMENT_NAME,
     Document,
     create_default_document,
-	get_workspace_directory,
     normalize_document_name,
 )
 from documents.workspace_service import DocumentWorkspaceService
 from ui.action_menu import get_document_menu_enabled_state
 from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
 from ui.menu_builder import apply_document_menu_state, build_document_menu
-from config import (
-	DEFAULT_TRANSLATION_TABLES,
-	get_charset_maps,
-	get_lang,
-	set_selected_dictionary,
-)
+from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
 from settings.translation import (
 	TranslationSettings,
 	load_translation_settings,
@@ -117,9 +111,18 @@ class NamedControlAccessible(wx.Accessible):
 
 
 class BrailleFrame(wx.Frame):
-	def __init__(self, *args, runtime: TranslationRuntime, **kwargs):
+	def __init__(
+		self,
+		*args,
+		runtime: TranslationRuntime,
+		paths: ApplicationPaths,
+		config_store: ConfigStore,
+		**kwargs,
+	):
 		super().__init__(*args, **kwargs)
 		self.translation_runtime = runtime
+		self._paths = paths
+		self._config_store = config_store
 		self._document_controller = DocumentController()
 
 		self._initialize_frame()
@@ -135,20 +138,23 @@ class BrailleFrame(wx.Frame):
 		self.SetMenuBar(self._create_menu_bar())
 
 	def _initialize_state(self) -> ViewSettings:
-		self.dictionary_dir = get_dictionary_directory()
+		self.dictionary_dir = self._paths.dictionary
 		self._dictionary_presenter = DictionaryManagementPresenter(
 			self.dictionary_dir,
 			get_active_name=lambda: self.translation_settings.selected_dictionary,
 			set_active_name=self._set_active_dictionary,
 		)
 		self._dictionary_presenter.refresh()
-		self.translation_settings = load_translation_settings(self._dictionary_presenter.dictionary_names)
-		self.translation_tables = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
-		self._workspace_service = DocumentWorkspaceService(self._document_controller, get_workspace_directory())
+		self.translation_settings = load_translation_settings(
+			self._config_store,
+			self._dictionary_presenter.dictionary_names,
+		)
+		self.translation_tables = load_translation_tables(self._config_store) or DEFAULT_TRANSLATION_TABLES.copy()
+		self._workspace_service = DocumentWorkspaceService(self._document_controller, self._paths.workspace)
 		self._simbraille_font_available = self._register_output_font()
 		self._dual_view_frame: DualViewFrame | None = None
 
-		self.view_settings = load_view_settings()
+		self.view_settings = load_view_settings(self._config_store)
 		return self.view_settings
 
 	def _create_main_layout(self, initial_settings: ViewSettings) -> None:
@@ -331,7 +337,7 @@ class BrailleFrame(wx.Frame):
 
 	def _open_dual_view_in_browser(self) -> None:
 		try:
-			html_path = write_dual_view_html(self._render_dual_view_for_open_document())
+			html_path = write_dual_view_html(self._render_dual_view_for_open_document(), self._paths.dual_view)
 			width, height = self.GetSize()
 			open_html_in_browser(html_path, (width, height))
 		except Exception as error:
@@ -419,9 +425,9 @@ class BrailleFrame(wx.Frame):
 		self.translation_tables = tables
 		self._apply_editor_view_settings(view)
 
-		save_translation_settings(translation)
-		save_translation_tables(tables)
-		save_view_settings(view)
+		save_translation_settings(self._config_store, translation)
+		save_translation_tables(self._config_store, tables)
+		save_view_settings(self._config_store, view)
 		return DotExpressSettingsSnapshot.create(translation, tables, view)
 
 	def _set_active_dictionary(self, selected_name: str) -> None:
@@ -430,7 +436,7 @@ class BrailleFrame(wx.Frame):
 			width=self.translation_settings.width,
 			selected_dictionary=selected_name,
 		)
-		set_selected_dictionary(selected_name)
+		self._config_store.set_selected_dictionary(selected_name)
 
 	def _get_selected_dictionary_path(self) -> Path:
 		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)
@@ -527,8 +533,8 @@ class BrailleFrame(wx.Frame):
 			dictionary_path=dictionary_path,
 			data_dir=resource_path("data"),
 			translation_tables=self.translation_tables.copy(),
-			lang=get_lang(),
-			charset_maps=get_charset_maps(),
+			lang=self._config_store.get_lang(),
+			charset_maps=self._config_store.get_charset_maps(),
 		)
 
 	def _build_conversion_request_for_text(self, raw_text: str) -> ConversionRequest:
@@ -554,7 +560,7 @@ class BrailleFrame(wx.Frame):
 			replace(self.view_settings, font_size=font_size)
 		)
 		self._apply_editor_view_settings(self.view_settings)
-		save_view_settings(self.view_settings)
+		save_view_settings(self._config_store, self.view_settings)
 		settings_dialog = DotExpressSettingsDialog.open_instance()
 		if settings_dialog is not None:
 			settings_dialog.sync_font_size(self.view_settings.font_size)
@@ -1052,8 +1058,10 @@ def _show_application_data_error(error: ApplicationDataError) -> None:
 
 class BrailleApp(wx.App):
 	def OnInit(self):
+		paths = build_application_paths()
+		self.paths = paths
 		try:
-			paths = prepare_application_directories()
+			prepare_application_directories(paths)
 			cleanup_dual_view_html(paths.dual_view)
 		except ApplicationDataError as error:
 			_show_application_data_error(error)
@@ -1063,17 +1071,25 @@ class BrailleApp(wx.App):
 			_show_application_data_error(error)
 			return False
 
+		config_store = ConfigStore(paths.config)
 		self.translation_runtime = build_default_translation_runtime()
-		self.frame = BrailleFrame(None, runtime=self.translation_runtime)
+		self.frame = BrailleFrame(
+			None,
+			runtime=self.translation_runtime,
+			paths=paths,
+			config_store=config_store,
+		)
 		self.frame.Show()
-		start_client_init_background()
+		start_client_init_background(config_store)
 		return True
 
 	def OnExit(self):
-		try:
-			cleanup_dual_view_html()
-		except OSError:
-			logger.exception("Failed to clean up dual-view HTML")
+		paths = getattr(self, "paths", None)
+		if paths is not None:
+			try:
+				cleanup_dual_view_html(paths.dual_view)
+			except OSError:
+				logger.exception("Failed to clean up dual-view HTML")
 		runtime = getattr(self, "translation_runtime", None)
 		if runtime is not None:
 			runtime.close()
diff --git a/client/main.py b/client/main.py
index 97eb1a4..8cbe664 100644
--- a/client/main.py
+++ b/client/main.py
@@ -1,8 +1,8 @@
 from pathlib import Path
 
 from adapters.translation.provider import build_default_translation_runtime
-from app_paths import get_dictionary_directory
-from config import DEFAULT_TRANSLATION_TABLES, get_charset_maps, get_lang
+from app_paths import build_application_paths
+from config import DEFAULT_TRANSLATION_TABLES, ConfigStore
 from conversion.service import ConversionRequest, convert_text_with_alignment
 
 
@@ -13,6 +13,8 @@ SAMPLE_TEXT = """
 
 
 def run_demo(text: str = SAMPLE_TEXT) -> None:
+    paths = build_application_paths()
+    config_store = ConfigStore(paths.config)
     runtime = build_default_translation_runtime()
     try:
         output = convert_text_with_alignment(
@@ -20,15 +22,15 @@ def run_demo(text: str = SAMPLE_TEXT) -> None:
                 raw_text=text,
                 output_mode="unicode",
                 width=40,
-                dictionary_path=get_dictionary_directory() / "default.csv",
+                dictionary_path=paths.dictionary / "default.csv",
                 data_dir=BASE_DIR / "data",
                 translation_tables={
                     **DEFAULT_TRANSLATION_TABLES,
                     "default": "en-ueb-g2.ctb",
                     "en": "en-ueb-g2.ctb",
                 },
-                lang=get_lang(),
-                charset_maps=get_charset_maps(),
+                lang=config_store.get_lang(),
+                charset_maps=config_store.get_charset_maps(),
             ),
             runtime=runtime,
         )
diff --git a/client/settings/translation.py b/client/settings/translation.py
index 17d08e4..2effda6 100644
--- a/client/settings/translation.py
+++ b/client/settings/translation.py
@@ -3,14 +3,9 @@ from __future__ import annotations
 from dataclasses import dataclass
 
 from config import (
+    ConfigStore,
     DEFAULT_CONVERSION_WIDTH,
     DEFAULT_OUTPUT_MODE,
-    get_conversion_width,
-    get_output_mode,
-    get_selected_dictionary,
-    set_conversion_width,
-    set_output_mode,
-    set_selected_dictionary,
 )
 from dictionaries.actions import resolve_dictionary_selection
 from .options import CONVERSION_WIDTH_RANGE, OUTPUT_MODE_OPTIONS, normalize_option_value
@@ -56,17 +51,17 @@ def normalize_translation_settings(
     )
 
 
-def load_translation_settings(dictionary_names: list[str]) -> TranslationSettings:
+def load_translation_settings(store: ConfigStore, dictionary_names: list[str]) -> TranslationSettings:
     settings = TranslationSettings(
-        output_mode=get_output_mode(DEFAULT_OUTPUT_MODE),
-        width=get_conversion_width(DEFAULT_CONVERSION_WIDTH),
-        selected_dictionary=get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
+        output_mode=store.get_output_mode(DEFAULT_OUTPUT_MODE),
+        width=store.get_conversion_width(DEFAULT_CONVERSION_WIDTH),
+        selected_dictionary=store.get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
     )
     return normalize_translation_settings(settings, dictionary_names)
 
 
-def save_translation_settings(settings: TranslationSettings) -> None:
-    set_output_mode(settings.output_mode)
-    set_conversion_width(settings.width)
-    set_selected_dictionary(settings.selected_dictionary)
+def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> None:
+    store.set_output_mode(settings.output_mode)
+    store.set_conversion_width(settings.width)
+    store.set_selected_dictionary(settings.selected_dictionary)
 
diff --git a/client/settings/translation_tables.py b/client/settings/translation_tables.py
index afee805..4622adc 100644
--- a/client/settings/translation_tables.py
+++ b/client/settings/translation_tables.py
@@ -1,9 +1,9 @@
 import config
 
 
-def load_translation_tables() -> dict[str, str]:
-    return dict(config.get_translation_tables())
+def load_translation_tables(store: config.ConfigStore) -> dict[str, str]:
+    return dict(store.get_translation_tables())
 
 
-def save_translation_tables(tables: dict[str, str]) -> None:
-    config.set_translation_tables(dict(tables))
+def save_translation_tables(store: config.ConfigStore, tables: dict[str, str]) -> None:
+    store.set_translation_tables(dict(tables))
diff --git a/client/settings/view.py b/client/settings/view.py
index 182cea1..15c2573 100644
--- a/client/settings/view.py
+++ b/client/settings/view.py
@@ -1,13 +1,10 @@
 from dataclasses import dataclass
 
 from config import (
+    ConfigStore,
     DEFAULT_BRAILLE_FONT,
     DEFAULT_VIEW_FONT_SIZE,
     DEFAULT_VIEW_SCHEME,
-    get_braille_font,
-    get_view_font_size,
-    get_view_scheme,
-    set_view_settings,
 )
 from .options import (
     BRAILLE_FONT_OPTIONS,
@@ -36,19 +33,19 @@ def normalize_view_settings(settings: ViewSettings) -> ViewSettings:
     )
 
 
-def load_view_settings() -> ViewSettings:
+def load_view_settings(store: ConfigStore) -> ViewSettings:
     return normalize_view_settings(
         ViewSettings(
-            get_view_font_size(DEFAULT_VIEW_FONT_SIZE),
-            get_view_scheme(DEFAULT_VIEW_SCHEME),
-            get_braille_font(DEFAULT_BRAILLE_FONT),
+            store.get_view_font_size(DEFAULT_VIEW_FONT_SIZE),
+            store.get_view_scheme(DEFAULT_VIEW_SCHEME),
+            store.get_braille_font(DEFAULT_BRAILLE_FONT),
         )
     )
 
 
-def save_view_settings(settings: ViewSettings) -> None:
+def save_view_settings(store: ConfigStore, settings: ViewSettings) -> None:
     normalized = normalize_view_settings(settings)
-    set_view_settings(
+    store.set_view_settings(
         normalized.font_size,
         normalized.scheme,
         normalized.braille_font,
EOF
git -C $REPO diff --stat -- client ':!client/tests'
```

Expected:

```text
 client/client_init.py                 | 11 ++++--
 client/gui.py                         | 74 +++++++++++++++++++++--------------
 client/main.py                        | 12 +++---
 client/settings/translation.py        | 23 +++++------
 client/settings/translation_tables.py |  8 ++--
 client/settings/view.py               | 17 ++++----
 6 files changed, 79 insertions(+), 66 deletions(-)
```

- [ ] **Step 4: Run green: the touched modules, then the full suite.**

```bash
$PY -m unittest tests.test_config tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_main_demo tests.test_client_init tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (33 + 5 + 2 + 5 + 2 + 3 + 10 + 160 = 220; 1062 + 3):

```text
Ran 220 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1065 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Mutation check of the new wiring.** Every mutant must fail the six touched modules.

```bash
$PY -I $T/tools/paths_mutants.py $REPO/client $T/mut new
git -C $REPO status --short -- client ':!client/tests'
```

Expected (every line FAILED; `skipped=2` is the usual Windows-only skips of these modules; the `status` lines are this task's six production files, not committed yet):

```text
validates-another-object: failures=1 errors=0 (FAILED (failures=1, skipped=2))
paths-not-kept-on-app: failures=1 errors=0 (FAILED (failures=1, skipped=2))
store-after-runtime: failures=1 errors=0 (FAILED (failures=1, skipped=2))
second-store-for-client-init: failures=1 errors=0 (FAILED (failures=1, skipped=2))
exit-cleans-implicit-folder: failures=1 errors=0 (FAILED (failures=1, skipped=2))
frame-dictionary-implicit: failures=2 errors=0 (FAILED (failures=2, skipped=2))
frame-workspace-implicit: failures=2 errors=0 (FAILED (failures=2, skipped=2))
dual-view-implicit: failures=3 errors=0 (FAILED (failures=3, skipped=2))
selection-saved-to-implicit-store: failures=1 errors=1 (FAILED (failures=1, errors=1, skipped=2))
request-language-from-implicit-store: failures=2 errors=0 (FAILED (failures=2, skipped=2))
font-size-saved-to-implicit-store: failures=6 errors=0 (FAILED (failures=6, skipped=2))
client-id-on-caller-thread: failures=1 errors=0 (FAILED (failures=1, skipped=2))
client-locale-fixed: failures=1 errors=0 (FAILED (failures=1, skipped=2))
demo-dictionary-at-root: failures=2 errors=0 (FAILED (failures=2, skipped=2))
demo-store-in-working-folder: failures=1 errors=0 (FAILED (failures=1, skipped=2))
store-constructor-creates-folder: failures=1 errors=4 (FAILED (failures=1, errors=4, skipped=2))
store-path-is-a-string: failures=3 errors=2 (FAILED (failures=3, errors=2, skipped=2))
store-caches-language: failures=2 errors=0 (FAILED (failures=2, skipped=2))
store-caches-charset-maps: failures=1 errors=0 (FAILED (failures=1, skipped=2))
store-throttles-per-instance: failures=2 errors=0 (FAILED (failures=2, skipped=2))
store-first-save-defaults-dropped: failures=8 errors=1 (FAILED (failures=8, errors=1, skipped=2))
store-ascii-escaped: failures=2 errors=0 (FAILED (failures=2, skipped=2))
 M client/client_init.py
 M client/gui.py
 M client/main.py
 M client/settings/translation.py
 M client/settings/translation_tables.py
 M client/settings/view.py
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/gui.py client/settings/translation.py client/settings/view.py client/settings/translation_tables.py client/client_init.py client/main.py client/tests/test_config.py client/tests/test_view_settings.py client/tests/test_translation_tables.py client/tests/test_translation_settings.py client/tests/test_conversion_language_explicit.py client/tests/test_main_demo.py client/tests/test_client_init.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
refactor: inject application paths and config store at startup

BrailleApp.OnInit builds one ApplicationPaths, validates that object,
cleans its dual_view folder, builds one ConfigStore for its config file
and passes both to BrailleFrame and the store to client init; OnExit
cleans the validated folder (P2-6 step 3). The frame reads its folders
from the paths and its settings through the store; the settings
loaders and savers take the store first; client init asks the store
for the client id and locale on its worker; the demo builds its own
paths and store. Files, startup order and config bytes are unchanged.
Tests use stores and paths instead of CONFIG_PATH and patched module
functions.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: inject application paths and config store at startup
```

---

### Task 4: Remove the implicit application path defaults (spec step 4)

**Interfaces:**
- Consumes: Task 3's injected wiring (nothing in production calls a removed name any more).
- Produces: `app_paths` exposes exactly `get_application_root()`, `build_application_paths(root=None)` and `prepare_application_directories(paths, *, probe_factory=tempfile.TemporaryFile)` (plus `ApplicationPaths`, `ApplicationDataError`); `config` has no `CONFIG_PATH` and no module-level IO function; `log._log_directory() -> Path` returns `build_application_paths().log`; every `dictionary_dir`/`workspace_dir`/`directory` parameter of `dictionaries/manager.py`, `dictionaries/name_prompt.py`, `documents/workspace.py` and `dual_view/files.py` is a required `Path` (bodies use `Path(x)`, so `str` still works).

- [ ] **Step 1: Write the guards.** `ApplicationPathsApiTest` (3 tests: the public functions and the required `paths`; the 14 folder parameters without a default and annotated `Path`; the AST scan for no-argument `build_application_paths()` calls outside `tests/`, `.venv/`, `__pycache__` and `braille/liblouis/`, which must be exactly `gui.py`, `log.py`, `main.py`); `test_consumers_use_the_common_application_root` rewritten on `build_application_paths(root)`; `ConfigModuleShapeTest` (correction 2); `test_client_init_does_not_import_config`; `test_log` patches `log._log_directory`; the frame wiring helper drops its `CONFIG_PATH` patch; the P0-6 gui guard no longer lists `get_dictionary_directory` as kept (refinement 8); the store bytes test drops its module half (refinement 10).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_app_paths.py b/client/tests/test_app_paths.py
index de68a2b..a86ac4e 100644
--- a/client/tests/test_app_paths.py
+++ b/client/tests/test_app_paths.py
@@ -1,3 +1,5 @@
+import ast
+import inspect
 import unittest
 from pathlib import Path
 from unittest.mock import patch
@@ -108,11 +110,82 @@ class ApplicationPathsTest(unittest.TestCase):
         import dictionaries.manager as dictionary_manager
         import documents.workspace as document_workspace
 
-        paths = app_paths.build_application_paths()
+        root = Path("C:/DotExpress")
+        paths = app_paths.build_application_paths(root)
 
-        self.assertEqual(Path(config.CONFIG_PATH), paths.config)
-        self.assertEqual(dictionary_manager.get_dictionary_directory(), paths.dictionary)
-        self.assertEqual(document_workspace.get_workspace_directory(), paths.workspace)
+        self.assertEqual(config.ConfigStore(paths.config).path, root / "config.json")
+        self.assertEqual(
+            dictionary_manager.dictionary_path_for_name("default", paths.dictionary),
+            root / "dictionary" / "default.csv",
+        )
+        self.assertEqual(
+            document_workspace.document_package_path_for_name("alpha", paths.workspace),
+            root / "workspace" / "alpha.dep",
+        )
+
+
+class ApplicationPathsApiTest(unittest.TestCase):
+    """P2-6: the application root is resolved implicitly only by the composition roots and the logger."""
+
+    CLIENT_DIR = Path(app_paths.__file__).resolve().parent
+
+    def test_app_paths_offers_only_the_root_the_layout_and_the_startup_check(self) -> None:
+        public = {
+            name
+            for name, value in vars(app_paths).items()
+            if inspect.isfunction(value) and value.__module__ == app_paths.__name__ and not name.startswith("_")
+        }
+
+        self.assertEqual(
+            public,
+            {"get_application_root", "build_application_paths", "prepare_application_directories"},
+        )
+        paths = inspect.signature(app_paths.prepare_application_directories).parameters["paths"]
+        self.assertIs(paths.default, inspect.Parameter.empty)
+
+    def test_folder_parameters_have_no_default(self) -> None:
+        import dictionaries.manager as manager
+        import dictionaries.name_prompt as name_prompt
+        import documents.workspace as workspace
+        import dual_view.files as dual_view_files
+
+        cases = (
+            (manager.dictionary_path_for_name, "dictionary_dir"),
+            (manager.ensure_default_dictionary, "dictionary_dir"),
+            (manager.list_dictionary_names, "dictionary_dir"),
+            (manager.create_dictionary, "dictionary_dir"),
+            (manager.import_dictionary, "dictionary_dir"),
+            (manager.rename_dictionary, "dictionary_dir"),
+            (manager.export_dictionary, "dictionary_dir"),
+            (manager.delete_dictionary, "dictionary_dir"),
+            (name_prompt.rename_dictionary_after_name_prompt, "dictionary_dir"),
+            (workspace.ensure_workspace_directory, "workspace_dir"),
+            (workspace.document_package_path_for_name, "workspace_dir"),
+            (workspace.load_workspace_documents, "workspace_dir"),
+            (dual_view_files.write_dual_view_html, "directory"),
+            (dual_view_files.cleanup_dual_view_html, "directory"),
+        )
+        for function, name in cases:
+            with self.subTest(function=f"{function.__module__}.{function.__name__}"):
+                parameter = inspect.signature(function).parameters[name]
+                self.assertIs(parameter.default, inspect.Parameter.empty)
+                self.assertEqual(parameter.annotation, "Path")
+
+    def test_only_the_composition_roots_and_the_logger_resolve_the_real_root(self) -> None:
+        callers = set()
+        for path in sorted(self.CLIENT_DIR.rglob("*.py")):
+            relative = path.relative_to(self.CLIENT_DIR)
+            if {"tests", ".venv", "__pycache__"} & set(relative.parts) or relative.parts[:2] == ("braille", "liblouis"):
+                continue
+            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+                if not isinstance(node, ast.Call) or node.args or node.keywords:
+                    continue
+                function = node.func
+                name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)
+                if name == "build_application_paths":
+                    callers.add(relative.as_posix())
+
+        self.assertEqual(callers, {"gui.py", "log.py", "main.py"})
 
 
 if __name__ == "__main__":
diff --git a/client/tests/test_config.py b/client/tests/test_config.py
index 6556932..51babce 100644
--- a/client/tests/test_config.py
+++ b/client/tests/test_config.py
@@ -4,6 +4,7 @@ import os
 import tempfile
 import unittest
 import gettext
+import inspect
 from pathlib import Path
 from unittest.mock import patch
 from uuid import UUID
@@ -539,11 +540,8 @@ class ConfigStoreTest(unittest.TestCase):
     def test_store_writes_the_documented_config_bytes(self) -> None:
         self.addCleanup(setattr, config, "_runtime_lang", config._runtime_lang)
         store_path = self.directory / "store" / "config.json"
-        module_path = self.directory / "module" / "config.json"
 
         self._apply_setters(config.ConfigStore(store_path))
-        with patch.object(config, "CONFIG_PATH", str(module_path)):
-            self._apply_setters(config)
 
         expected = {
             "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
@@ -560,7 +558,20 @@ class ConfigStoreTest(unittest.TestCase):
             store_path.read_text(encoding="utf-8"),
             json.dumps(expected, ensure_ascii=False, indent=2),
         )
-        self.assertEqual(module_path.read_bytes(), store_path.read_bytes())
+
+
+class ConfigModuleShapeTest(unittest.TestCase):
+    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""
+
+    def test_config_io_lives_only_on_the_store(self) -> None:
+        own_functions = [
+            name
+            for name, value in vars(config).items()
+            if inspect.isfunction(value) and value.__module__ == config.__name__
+        ]
+
+        self.assertEqual([name for name in own_functions if name.startswith(("get_", "set_"))], [])
+        self.assertEqual([name for name in vars(config) if "PATH" in name], [])
 
 
 if __name__ == "__main__":
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 4163476..f4272c4 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1184,7 +1184,7 @@ class DictionaryManagementFrameTest(unittest.TestCase):
             with self.subTest(module_attribute=name):
                 self.assertFalse(hasattr(gui, name))
         self.assertFalse(hasattr(gui.BrailleFrame, "_get_csv_wildcard"))
-        for name in ("dictionary_path_for_name", "get_dictionary_directory", "DictionaryManagementDialog", "DictionaryEntriesDialog"):
+        for name in ("dictionary_path_for_name", "DictionaryManagementDialog", "DictionaryEntriesDialog"):
             with self.subTest(kept=name):
                 self.assertTrue(hasattr(gui, name))
         for name in ("_get_selected_dictionary_path", "_show_file_error"):
@@ -3912,16 +3912,13 @@ class ApplicationPathsWiringCharacterizationTest(unittest.TestCase):
         """A bare frame whose application data lives under ``self.root``.
 
         The frame gets paths built from the root and one config store for them. The real
-        application root and the module-level config path point at an empty decoy folder,
-        so anything still resolved implicitly misses ``self.root`` and never reaches ``client/``.
+        application root points at an empty decoy folder, so anything still resolved
+        implicitly misses ``self.root`` and never reaches ``client/``.
         """
         decoy = self.root.parent / "decoy"
-        for patcher in (
-            patch.object(app_paths, "get_application_root", return_value=decoy),
-            patch.object(config, "CONFIG_PATH", str(decoy / "config.json")),
-        ):
-            patcher.start()
-            self.addCleanup(patcher.stop)
+        patcher = patch.object(app_paths, "get_application_root", return_value=decoy)
+        patcher.start()
+        self.addCleanup(patcher.stop)
         frame = object.__new__(gui.BrailleFrame)
         frame._paths = app_paths.build_application_paths(self.root)
         frame._config_store = config.ConfigStore(frame._paths.config)
diff --git a/client/tests/test_log.py b/client/tests/test_log.py
index 48c37d0..0a30c20 100644
--- a/client/tests/test_log.py
+++ b/client/tests/test_log.py
@@ -14,7 +14,7 @@ class FileLoggerTest(unittest.TestCase):
         with tempfile.TemporaryDirectory() as directory:
             log_dir = Path(directory) / "log"
             logger_name = f"dotexpress.test.{uuid4().hex}"
-            with patch.object(log, "get_log_directory", return_value=log_dir):
+            with patch.object(log, "_log_directory", return_value=log_dir):
                 logger = log.get_logger(logger_name, "sample.log")
 
             handler = next(item for item in logger.handlers if isinstance(item, logging.FileHandler))
diff --git a/client/tests/test_translation_import_isolation.py b/client/tests/test_translation_import_isolation.py
index 159f724..8dce504 100644
--- a/client/tests/test_translation_import_isolation.py
+++ b/client/tests/test_translation_import_isolation.py
@@ -40,6 +40,21 @@ assert "config" not in sys.modules, "config was imported"
 
         self.assertEqual(completed.returncode, 0, completed.stderr)
 
+    def test_client_init_does_not_import_config(self) -> None:
+        script = """
+import sys
+import client_init
+assert "config" not in sys.modules, "config was imported"
+"""
+        completed = subprocess.run(
+            [sys.executable, "-c", script],
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+
+        self.assertEqual(completed.returncode, 0, completed.stderr)
+
     def test_conversion_does_not_import_dual_view(self) -> None:
         script = """
 import sys
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_app_paths.py                    | 81 +++++++++++++++++++++--
 client/tests/test_config.py                       | 19 ++++--
 client/tests/test_gui_document_flows.py           | 15 ++---
 client/tests/test_log.py                          |  2 +-
 client/tests/test_translation_import_isolation.py | 15 +++++
 5 files changed, 114 insertions(+), 18 deletions(-)
```

- [ ] **Step 2: Run red.**

```bash
$PY -m unittest tests.test_app_paths tests.test_config tests.test_log tests.test_translation_import_isolation 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (17 failures and 1 error in 51 tests: the API test sees the five helpers; the 14 folder subtests fail, 8 on a `None` default and 6 on a `Path | None` annotation; the scan finds `app_paths.py` instead of `log.py`; the shape test lists the delegating module functions; `test_log` has no `_log_directory` to patch; the import guard and the rewritten consumers test are already green, refinement 9):

```text
ERROR: test_logger_defers_file_creation_and_uses_application_log_directory (tests.test_log.FileLoggerTest.test_logger_defers_file_creation_and_uses_application_log_directory)
AttributeError: <module 'log' from 'client/log.py'> does not have the attribute '_log_directory'
FAIL: test_app_paths_offers_only_the_root_the_layout_and_the_startup_check (tests.test_app_paths.ApplicationPathsApiTest.test_app_paths_offers_only_the_root_the_layout_and_the_startup_check)
AssertionError: Items in the first set but not the second:
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.dictionary_path_for_name')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.ensure_default_dictionary')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.list_dictionary_names')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.create_dictionary')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.import_dictionary')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.rename_dictionary')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.export_dictionary')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.manager.delete_dictionary')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dictionaries.name_prompt.rename_dictionary_after_name_prompt')
AssertionError: 'Path | None' != 'Path'
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='documents.workspace.ensure_workspace_directory')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='documents.workspace.document_package_path_for_name')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='documents.workspace.load_workspace_documents')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dual_view.files.write_dual_view_html')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default) (function='dual_view.files.cleanup_dual_view_html')
AssertionError: None is not <class 'inspect._empty'>
FAIL: test_only_the_composition_roots_and_the_logger_resolve_the_real_root (tests.test_app_paths.ApplicationPathsApiTest.test_only_the_composition_roots_and_the_logger_resolve_the_real_root)
AssertionError: Items in the first set but not the second:
FAIL: test_config_io_lives_only_on_the_store (tests.test_config.ConfigModuleShapeTest.test_config_io_lives_only_on_the_store)
AssertionError: Lists differ: ['get_lang', 'get_charset_maps', 'set_lang[298 chars]_id'] != []
Ran 51 tests
FAILED (failures=17, errors=1)
```

- [ ] **Step 3: Delete the defaults.** `app_paths.py` loses the five helpers and `prepare_application_directories` uses `paths` directly; `config.py` loses the `get_config_path` import, `CONFIG_PATH` and the delegating functions; `log.py` gets `_log_directory()`; the four folder modules drop their `app_paths` import and take required folders; `gui.py` drops `get_dictionary_directory` from its `dictionaries.manager` import.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/app_paths.py b/client/app_paths.py
index f51f088..ae3e0a6 100644
--- a/client/app_paths.py
+++ b/client/app_paths.py
@@ -47,43 +47,22 @@ def build_application_paths(root: Path | None = None) -> ApplicationPaths:
     )
 
 
-def get_config_path(path: Path | None = None) -> Path:
-    return Path(path) if path is not None else build_application_paths().config
-
-
-def get_dictionary_directory(path: Path | None = None) -> Path:
-    return Path(path) if path is not None else build_application_paths().dictionary
-
-
-def get_workspace_directory(path: Path | None = None) -> Path:
-    return Path(path) if path is not None else build_application_paths().workspace
-
-
-def get_log_directory(path: Path | None = None) -> Path:
-    return Path(path) if path is not None else build_application_paths().log
-
-
-def get_dual_view_directory(path: Path | None = None) -> Path:
-    return Path(path) if path is not None else build_application_paths().dual_view
-
-
 def prepare_application_directories(
-    paths: ApplicationPaths | None = None,
+    paths: ApplicationPaths,
     *,
     probe_factory: Callable[..., BinaryIO] = tempfile.TemporaryFile,
 ) -> ApplicationPaths:
-    managed_paths = paths or build_application_paths()
-    for directory in managed_paths.writable_directories:
+    for directory in paths.writable_directories:
         try:
             directory.mkdir(parents=True, exist_ok=True)
             with probe_factory(dir=directory):
                 pass
         except OSError as error:
             raise ApplicationDataError(directory, error) from error
-    if managed_paths.config.exists():
+    if paths.config.exists():
         try:
-            with managed_paths.config.open("a", encoding="utf-8"):
+            with paths.config.open("a", encoding="utf-8"):
                 pass
         except OSError as error:
-            raise ApplicationDataError(managed_paths.config, error) from error
-    return managed_paths
+            raise ApplicationDataError(paths.config, error) from error
+    return paths
diff --git a/client/config.py b/client/config.py
index 62d4dc2..969abdc 100644
--- a/client/config.py
+++ b/client/config.py
@@ -7,7 +7,6 @@ from pathlib import Path
 from typing import Optional
 from uuid import uuid4
 
-from app_paths import get_config_path
 from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
 from log import get_logger
 
@@ -15,7 +14,6 @@ logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)
 
 DEFAULT_FALLBACK = "zh_TW"
 LANG_ENV = "TEXT2BRAILLE_LANG"
-CONFIG_PATH = str(get_config_path())
 
 CONVERSION_SECTION = "conversion"
 VIEW_SECTION = "view"
@@ -242,70 +240,3 @@ class ConfigStore:
         self._save(data)
         return client_id
 
-
-# Module-level API kept until P2-6 step 4: each call reads CONFIG_PATH and
-# delegates to a ConfigStore built for that call.
-
-
-def get_lang() -> str:
-    return ConfigStore(CONFIG_PATH).get_lang()
-
-
-def get_charset_maps() -> dict[str, str]:
-    return ConfigStore(CONFIG_PATH).get_charset_maps()
-
-
-def set_lang(lang: str, persist: bool = False) -> None:
-    ConfigStore(CONFIG_PATH).set_lang(lang, persist)
-
-
-def get_translation_tables() -> dict:
-    return ConfigStore(CONFIG_PATH).get_translation_tables()
-
-
-def set_translation_tables(tables: dict[str, str]) -> None:
-    ConfigStore(CONFIG_PATH).set_translation_tables(tables)
-
-
-def get_output_mode(default: str = DEFAULT_OUTPUT_MODE) -> str:
-    return ConfigStore(CONFIG_PATH).get_output_mode(default)
-
-
-def set_output_mode(output_mode: str) -> None:
-    ConfigStore(CONFIG_PATH).set_output_mode(output_mode)
-
-
-def get_conversion_width(default: int = DEFAULT_CONVERSION_WIDTH) -> int:
-    return ConfigStore(CONFIG_PATH).get_conversion_width(default)
-
-
-def set_conversion_width(width: int) -> None:
-    ConfigStore(CONFIG_PATH).set_conversion_width(width)
-
-
-def get_selected_dictionary(default: str = "default") -> str:
-    return ConfigStore(CONFIG_PATH).get_selected_dictionary(default)
-
-
-def set_selected_dictionary(dictionary_name: str) -> None:
-    ConfigStore(CONFIG_PATH).set_selected_dictionary(dictionary_name)
-
-
-def get_view_font_size(default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
-    return ConfigStore(CONFIG_PATH).get_view_font_size(default)
-
-
-def get_view_scheme(default: str = DEFAULT_VIEW_SCHEME) -> str:
-    return ConfigStore(CONFIG_PATH).get_view_scheme(default)
-
-
-def get_braille_font(default: str = DEFAULT_BRAILLE_FONT) -> str:
-    return ConfigStore(CONFIG_PATH).get_braille_font(default)
-
-
-def set_view_settings(font_size: int, scheme: str, braille_font: str) -> None:
-    ConfigStore(CONFIG_PATH).set_view_settings(font_size, scheme, braille_font)
-
-
-def get_or_create_client_id() -> str:
-    return ConfigStore(CONFIG_PATH).get_or_create_client_id()
diff --git a/client/dictionaries/manager.py b/client/dictionaries/manager.py
index e483898..12e2dba 100644
--- a/client/dictionaries/manager.py
+++ b/client/dictionaries/manager.py
@@ -4,7 +4,6 @@ import csv
 from pathlib import Path
 import shutil
 
-from app_paths import get_dictionary_directory
 from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name
 
 DEFAULT_DICTIONARY_NAME = "default"
@@ -12,12 +11,12 @@ DEFAULT_HEADER = ["text", "braille", "type"]
 MAX_DICTIONARY_NAME_LENGTH = MAX_NAME_LENGTH
 
 
-def dictionary_path_for_name(name: str, dictionary_dir: Path | None = None) -> Path:
-    return get_dictionary_directory(dictionary_dir) / f"{name}.csv"
+def dictionary_path_for_name(name: str, dictionary_dir: Path) -> Path:
+    return Path(dictionary_dir) / f"{name}.csv"
 
 
-def ensure_default_dictionary(dictionary_dir: Path | None = None) -> Path:
-    directory = get_dictionary_directory(dictionary_dir)
+def ensure_default_dictionary(dictionary_dir: Path) -> Path:
+    directory = Path(dictionary_dir)
     directory.mkdir(parents=True, exist_ok=True)
     default_path = directory / f"{DEFAULT_DICTIONARY_NAME}.csv"
     if not default_path.exists():
@@ -27,8 +26,8 @@ def ensure_default_dictionary(dictionary_dir: Path | None = None) -> Path:
     return default_path
 
 
-def list_dictionary_names(dictionary_dir: Path | None = None) -> list[str]:
-    directory = get_dictionary_directory(dictionary_dir)
+def list_dictionary_names(dictionary_dir: Path) -> list[str]:
+    directory = Path(dictionary_dir)
     if not directory.exists():
         return []
     names = [path.stem for path in directory.glob("*.csv") if path.is_file()]
@@ -48,8 +47,8 @@ def validate_dictionary_csv(path: Path | str) -> None:
         raise ValueError("Dictionary CSV must contain text, braille, and type headers.")
 
 
-def create_dictionary(dictionary_dir: Path | None, name: str) -> Path:
-    directory = get_dictionary_directory(dictionary_dir)
+def create_dictionary(dictionary_dir: Path, name: str) -> Path:
+    directory = Path(dictionary_dir)
     directory.mkdir(parents=True, exist_ok=True)
     normalized = normalize_dictionary_name(name)
     path = directory / f"{normalized}.csv"
@@ -61,8 +60,8 @@ def create_dictionary(dictionary_dir: Path | None, name: str) -> Path:
     return path
 
 
-def import_dictionary(dictionary_dir: Path | None, source_path: Path | str, name: str) -> Path:
-    directory = get_dictionary_directory(dictionary_dir)
+def import_dictionary(dictionary_dir: Path, source_path: Path | str, name: str) -> Path:
+    directory = Path(dictionary_dir)
     directory.mkdir(parents=True, exist_ok=True)
     normalized = normalize_dictionary_name(name)
     destination_path = directory / f"{normalized}.csv"
@@ -74,7 +73,7 @@ def import_dictionary(dictionary_dir: Path | None, source_path: Path | str, name
     return destination_path
 
 
-def rename_dictionary(dictionary_dir: Path | None, source_name: str, new_name: str) -> Path:
+def rename_dictionary(dictionary_dir: Path, source_name: str, new_name: str) -> Path:
     source_normalized = source_name.strip()
     if source_normalized.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
         raise ValueError("Default dictionary cannot be renamed.")
@@ -87,14 +86,14 @@ def rename_dictionary(dictionary_dir: Path | None, source_name: str, new_name: s
     return destination_path
 
 
-def export_dictionary(dictionary_dir: Path | None, name: str, destination_path: Path | str) -> Path:
+def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
     source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
     destination = Path(destination_path)
     shutil.copyfile(source_path, destination)
     return destination
 
 
-def delete_dictionary(dictionary_dir: Path | None, name: str) -> None:
+def delete_dictionary(dictionary_dir: Path, name: str) -> None:
     normalized = name.strip()
     if normalized.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
         raise ValueError("Default dictionary cannot be deleted.")
diff --git a/client/dictionaries/name_prompt.py b/client/dictionaries/name_prompt.py
index cc6b704..735d365 100644
--- a/client/dictionaries/name_prompt.py
+++ b/client/dictionaries/name_prompt.py
@@ -31,7 +31,7 @@ def prompt_dictionary_name_until_success(
 
 
 def rename_dictionary_after_name_prompt(
-	dictionary_dir: Path | None,
+	dictionary_dir: Path,
 	source_name: str,
 	new_name: str,
 ) -> Path:
diff --git a/client/documents/workspace.py b/client/documents/workspace.py
index c52737e..dce9b22 100644
--- a/client/documents/workspace.py
+++ b/client/documents/workspace.py
@@ -6,7 +6,6 @@ from pathlib import Path
 import zipfile
 from collections.abc import Callable
 
-from app_paths import get_workspace_directory
 from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
 from shared.name_validation import normalize_base_name
 
@@ -34,8 +33,8 @@ def create_default_document() -> Document:
     return Document(name=DEFAULT_DOCUMENT_NAME, text="", braille=None)
 
 
-def ensure_workspace_directory(workspace_dir: Path | None = None) -> Path:
-    directory = get_workspace_directory(workspace_dir)
+def ensure_workspace_directory(workspace_dir: Path) -> Path:
+    directory = Path(workspace_dir)
     directory.mkdir(parents=True, exist_ok=True)
     return directory
 
@@ -44,8 +43,8 @@ def normalize_document_name(name: str) -> str:
     return normalize_base_name(name)
 
 
-def document_package_path_for_name(name: str, workspace_dir: Path | None = None) -> Path:
-    return get_workspace_directory(workspace_dir) / f"{name}{DEP_EXTENSION}"
+def document_package_path_for_name(name: str, workspace_dir: Path) -> Path:
+    return Path(workspace_dir) / f"{name}{DEP_EXTENSION}"
 
 
 def save_document_package(
@@ -129,7 +128,7 @@ def prepare_document_for_save(
     return Document(name=document.name, text=text, braille=saved_braille)
 
 
-def load_workspace_documents(workspace_dir: Path | None = None) -> tuple[list[Document], list[Path]]:
+def load_workspace_documents(workspace_dir: Path) -> tuple[list[Document], list[Path]]:
     directory = ensure_workspace_directory(workspace_dir)
     documents: list[Document] = []
     invalid_paths: list[Path] = []
diff --git a/client/dual_view/files.py b/client/dual_view/files.py
index dd46c11..274b1f8 100644
--- a/client/dual_view/files.py
+++ b/client/dual_view/files.py
@@ -4,8 +4,6 @@ from pathlib import Path
 from uuid import uuid4
 from collections.abc import Callable
 
-from app_paths import get_dual_view_directory
-
 
 OWNED_HTML_PATTERN = "dual-view-*.html"
 
@@ -16,19 +14,19 @@ def _new_token() -> str:
 
 def write_dual_view_html(
     content: str,
-    directory: Path | None = None,
+    directory: Path,
     *,
     token_factory: Callable[[], str] = _new_token,
 ) -> Path:
-    target_directory = get_dual_view_directory(directory)
+    target_directory = Path(directory)
     target_directory.mkdir(parents=True, exist_ok=True)
     target = target_directory / f"dual-view-{token_factory()}.html"
     target.write_text(content, encoding="utf-8")
     return target
 
 
-def cleanup_dual_view_html(directory: Path | None = None) -> None:
-    target_directory = get_dual_view_directory(directory)
+def cleanup_dual_view_html(directory: Path) -> None:
+    target_directory = Path(directory)
     if not target_directory.exists():
         return
     for path in target_directory.glob(OWNED_HTML_PATTERN):
diff --git a/client/gui.py b/client/gui.py
index 94744d8..e645edd 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -14,7 +14,7 @@ from conversion.math_service import latex_to_mathml
 from conversion.presenter import ConversionPresenter
 from conversion.service import ConversionRequest
 from conversion.preprocessing.user_script import preprocessing_script_path
-from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
+from dictionaries.manager import dictionary_path_for_name
 from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
 from documents.export_coordinator import ExportCoordinator
diff --git a/client/log.py b/client/log.py
index 614044d..2b6f0ca 100644
--- a/client/log.py
+++ b/client/log.py
@@ -1,7 +1,11 @@
 import logging
 from pathlib import Path
 
-from app_paths import get_log_directory
+from app_paths import build_application_paths
+
+
+def _log_directory() -> Path:
+    return build_application_paths().log
 
 
 def get_logger(
@@ -14,7 +18,7 @@ def get_logger(
 
     if not logger.handlers:
         file_handler = logging.FileHandler(
-            get_log_directory() / Path(filename).name,
+            _log_directory() / Path(filename).name,
             encoding="utf-8",
             delay=True,
         )
EOF
git -C $REPO diff --stat -- client ':!client/tests'
```

Expected:

```text
 client/app_paths.py                | 33 ++++--------------
 client/config.py                   | 69 --------------------------------------
 client/dictionaries/manager.py     | 27 +++++++--------
 client/dictionaries/name_prompt.py |  2 +-
 client/documents/workspace.py      | 11 +++---
 client/dual_view/files.py          | 10 +++---
 client/gui.py                      |  2 +-
 client/log.py                      |  8 +++--
 8 files changed, 36 insertions(+), 126 deletions(-)
```

- [ ] **Step 4: Run green: the guard modules, the folder modules' own tests, the full suite.**

```bash
$PY -m unittest tests.test_app_paths tests.test_config tests.test_log tests.test_translation_import_isolation tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_dictionary_manager tests.test_dictionary_name_prompt tests.test_dictionary_presenter tests.test_document_workspace tests.test_workspace_service tests.test_dual_view_files 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (10 + 34 + 2 + 5 + 160 = 211; the folder modules unchanged and green; 1065 + 5):

```text
Ran 211 tests
OK (skipped=2)
Ran 109 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1070 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Mutation check of the guards.** Every mutant must fail the guard modules.

```bash
$PY -I $T/tools/paths_mutants.py $REPO/client $T/mut guards
git -C $REPO status --short -- client ':!client/tests'
```

Expected (every line FAILED; the `status` lines are this task's eight production files, not committed yet):

```text
app-paths-helper-back: failures=2 errors=0 (FAILED (failures=2, skipped=2))
prepare-paths-optional: failures=1 errors=0 (FAILED (failures=1, skipped=2))
cleanup-folder-optional: failures=1 errors=0 (FAILED (failures=1, skipped=2))
workspace-resolves-the-root: failures=1 errors=0 (FAILED (failures=1, skipped=2))
config-module-getter-back: failures=1 errors=0 (FAILED (failures=1, skipped=2))
config-module-path-back: failures=1 errors=0 (FAILED (failures=1, skipped=2))
client-init-imports-config: failures=1 errors=0 (FAILED (failures=1, skipped=2))
log-directory-from-cwd: failures=2 errors=0 (FAILED (failures=2, skipped=2))
 M client/app_paths.py
 M client/config.py
 M client/dictionaries/manager.py
 M client/dictionaries/name_prompt.py
 M client/documents/workspace.py
 M client/dual_view/files.py
 M client/gui.py
 M client/log.py
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/app_paths.py client/config.py client/log.py client/dictionaries/manager.py client/dictionaries/name_prompt.py client/documents/workspace.py client/dual_view/files.py client/gui.py client/tests/test_app_paths.py client/tests/test_config.py client/tests/test_translation_import_isolation.py client/tests/test_gui_document_flows.py client/tests/test_log.py
git -C $REPO commit -q -F - <<'EOF'
refactor: remove implicit application path defaults

Delete the five app_paths get_*_directory/get_config_path helpers,
config.CONFIG_PATH and the module-level config functions (P2-6 step 4).
prepare_application_directories and every dictionary, workspace and
dual-view folder parameter are now required; the logger resolves its
folder through log._log_directory(), the same build_application_paths()
that startup validates. Guards pin the app_paths API, the required
folder parameters, the only no-argument build_application_paths()
callers (gui, main, log), a config module without IO functions or a
path, and client_init without config. The P0-6 gui import guard no
longer lists the deleted get_dictionary_directory as kept (intentional
guard change).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: remove implicit application path defaults
```

---

### Task 5: Move the conversion presenter to `ui` (spec step 5, M-1)

**Interfaces:**
- Consumes: `conversion/presenter.py` as it is (`ConversionPresenter`, `ConversionView`, `CONVERTING_DIALOG_DELAY_MS`, `format_conversion_error`, `missing_default_table_message`).
- Produces: the same module at `ui/conversion_presenter.py`, byte for byte; no `conversion/presenter.py` and no re-export. `test_conversion_package_imports_no_higher_layer` forbids any absolute import (any nesting) of `documents`, `ui`, `gui`, `dialog`, `settings`, `dictionaries`, `dual_view` from `client/conversion/**/*.py`.

- [ ] **Step 1: Write the guard and point the presenter tests at the new module.** `test_conversion_presenter` imports from `ui.conversion_presenter` and its `PRESENTER_PATH` (the wx/gui/dialog AST guard) points at `client/ui/conversion_presenter.py`; `test_export_coordinator` imports from there too.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_conversion_presenter.py b/client/tests/test_conversion_presenter.py
index a7a4869..181ba9a 100644
--- a/client/tests/test_conversion_presenter.py
+++ b/client/tests/test_conversion_presenter.py
@@ -4,7 +4,7 @@ import ast
 import unittest
 from pathlib import Path
 
-from conversion.presenter import (
+from ui.conversion_presenter import (
     CONVERTING_DIALOG_DELAY_MS,
     ConversionPresenter,
     format_conversion_error,
@@ -16,7 +16,7 @@ from documents.workspace import Document
 from i18n import _
 from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
 
-PRESENTER_PATH = Path(__file__).resolve().parents[1] / "conversion" / "presenter.py"
+PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"
 
 
 class RecordingConversionView:
diff --git a/client/tests/test_export_coordinator.py b/client/tests/test_export_coordinator.py
index 4e9b59d..9bbfd40 100644
--- a/client/tests/test_export_coordinator.py
+++ b/client/tests/test_export_coordinator.py
@@ -8,7 +8,7 @@ from pathlib import Path
 from unittest.mock import Mock, call, patch
 
 import documents.export_coordinator as coordinator_module
-from conversion.presenter import ConversionPresenter
+from ui.conversion_presenter import ConversionPresenter
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 from documents.controller import DocumentController
 from documents.export_coordinator import ExportCoordinator
diff --git a/client/tests/test_translation_import_isolation.py b/client/tests/test_translation_import_isolation.py
index 8dce504..eafefde 100644
--- a/client/tests/test_translation_import_isolation.py
+++ b/client/tests/test_translation_import_isolation.py
@@ -1,6 +1,11 @@
+import ast
 import subprocess
 import sys
 import unittest
+from pathlib import Path
+
+CLIENT_DIR = Path(__file__).resolve().parents[1]
+HIGHER_LAYERS = {"documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}
 
 
 class TranslationImportIsolationTest(unittest.TestCase):
@@ -73,6 +78,22 @@ assert not loaded, f"dual_view modules were imported: {loaded}"
 
         self.assertEqual(completed.returncode, 0, completed.stderr)
 
+    def test_conversion_package_imports_no_higher_layer(self) -> None:
+        found = []
+        for path in sorted((CLIENT_DIR / "conversion").rglob("*.py")):
+            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+                if isinstance(node, ast.Import):
+                    names = [alias.name for alias in node.names]
+                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
+                    names = [node.module]
+                else:
+                    continue
+                for name in names:
+                    if name.split(".")[0] in HIGHER_LAYERS:
+                        found.append(f"{path.relative_to(CLIENT_DIR).as_posix()}:{node.lineno} {name}")
+
+        self.assertEqual(found, [])
+
     def test_dual_view_does_not_import_conversion_or_config(self) -> None:
         script = """
 import sys
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_conversion_presenter.py         |  4 ++--
 client/tests/test_export_coordinator.py           |  2 +-
 client/tests/test_translation_import_isolation.py | 21 +++++++++++++++++++++
 3 files changed, 24 insertions(+), 3 deletions(-)
```

- [ ] **Step 2: Run red.**

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_conversion_presenter tests.test_export_coordinator 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the guard names the two `documents` imports of `conversion/presenter.py`; the two presenter test modules cannot import `ui.conversion_presenter` yet):

```text
ERROR: test_conversion_presenter (unittest.loader._FailedTest.test_conversion_presenter)
ImportError: Failed to import test module: test_conversion_presenter
ModuleNotFoundError: No module named 'ui.conversion_presenter'
ERROR: test_export_coordinator (unittest.loader._FailedTest.test_export_coordinator)
ImportError: Failed to import test module: test_export_coordinator
ModuleNotFoundError: No module named 'ui.conversion_presenter'
FAIL: test_conversion_package_imports_no_higher_layer (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_conversion_package_imports_no_higher_layer)
AssertionError: Lists differ: ['conversion/presenter.py:31 documents.con[54 chars]ace'] != []
Ran 8 tests
FAILED (failures=1, errors=2)
```

- [ ] **Step 3: Move the module and update its two importers' references.** `git mv` keeps the body; `gui.py` imports from `ui.conversion_presenter` (next to the other `ui` imports) and its `ConversionView` section comment names the new file; the `ExportConversions` docstring in `documents/export_coordinator.py` names the new module.

```bash
git -C $REPO mv client/conversion/presenter.py client/ui/conversion_presenter.py
git -C $REPO apply <<'EOF'
diff --git a/client/documents/export_coordinator.py b/client/documents/export_coordinator.py
index 9e9d4bd..5de30fe 100644
--- a/client/documents/export_coordinator.py
+++ b/client/documents/export_coordinator.py
@@ -37,7 +37,7 @@ class ExportView(Protocol):
 
 
 class ExportConversions(Protocol):
-    """Satisfied by ``conversion.presenter.ConversionPresenter``."""
+    """Satisfied by ``ui.conversion_presenter.ConversionPresenter``."""
 
     def missing_table_message(self) -> str | None: ...
 
diff --git a/client/gui.py b/client/gui.py
index e645edd..39eeee9 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -11,7 +11,6 @@ from app_paths import ApplicationDataError, ApplicationPaths, build_application_
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
 from conversion.math_service import latex_to_mathml
-from conversion.presenter import ConversionPresenter
 from conversion.service import ConversionRequest
 from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name
@@ -31,6 +30,7 @@ from documents.workspace import (
 )
 from documents.workspace_service import DocumentWorkspaceService
 from ui.action_menu import get_document_menu_enabled_state
+from ui.conversion_presenter import ConversionPresenter
 from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
 from ui.menu_builder import apply_document_menu_state, build_document_menu
 from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
@@ -968,7 +968,7 @@ class BrailleFrame(wx.Frame):
 			viewer.Destroy()
 		evt.Skip()
 
-	# --- ConversionView (conversion/presenter.py) ---------------------------
+	# --- ConversionView (ui/conversion_presenter.py) ------------------------
 
 	def get_source_text(self) -> str:
 		return self.input_txt.GetValue()
EOF
git -C $REPO diff --stat HEAD -M -- client ':!client/tests'
```

Expected:

```text
 client/documents/export_coordinator.py                         | 2 +-
 client/gui.py                                                  | 4 ++--
 client/{conversion/presenter.py => ui/conversion_presenter.py} | 0
 3 files changed, 3 insertions(+), 3 deletions(-)
```

- [ ] **Step 4: Run green: the three modules, the gui module, the full suite.**

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (6 + 19 + 21 + 160 = 206; 1070 + 1):

```text
Ran 206 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1071 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.** The rename is already staged by `git mv`.

```bash
git -C $REPO add client/gui.py client/documents/export_coordinator.py client/tests/test_translation_import_isolation.py client/tests/test_conversion_presenter.py client/tests/test_export_coordinator.py
git -C $REPO commit -q -F - <<'EOF'
refactor: move conversion presenter to ui

ConversionPresenter is the main window's conversion coordinator, so it
moves unchanged from conversion/presenter.py to ui/conversion_presenter.py
(P2-6 step 5, P1 review M-1). The conversion package no longer imports
documents; a guard scans every conversion module for imports of
documents, ui, gui, dialog, settings, dictionaries and dual_view. No
re-export is left behind.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: move conversion presenter to ui
```

---

### Task 6: Final verification against the spec's acceptance criteria (no commit)

- [ ] **Step 1: AC1, the roadmap command and the neighbours.**

```bash
$PY -m unittest tests.test_app_paths tests.test_config tests.test_gui_document_flows -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_app_paths tests.test_config tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_log tests.test_main_demo tests.test_client_init tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_conversion_presenter tests.test_export_coordinator tests.test_translation_import_isolation tests.test_dictionary_manager tests.test_dictionary_name_prompt tests.test_document_workspace tests.test_workspace_service tests.test_dual_view_files tests.test_removed_dead_code tests.test_i18n tests.test_wx_stub 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (AC1: 204 tests pass, 202 `ok` lines plus the 2 usual Windows-only skips of `test_gui_document_flows`; the 18 neighbour modules green):

```text
202
Ran 204 tests
OK (skipped=2)
Ran 183 tests
OK
```

- [ ] **Step 2: AC2, the full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1043 + 28; only the P2-5 failure; no errors):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1071 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 3: AC3, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 1071 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=1071 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC3, the three roadmap modules alone and in both orders of each pair.**

```bash
for order in tests.test_config tests.test_gui_document_flows tests.test_app_paths \
  "tests.test_config tests.test_gui_document_flows" "tests.test_gui_document_flows tests.test_config" \
  "tests.test_config tests.test_app_paths" "tests.test_app_paths tests.test_config" \
  "tests.test_gui_document_flows tests.test_app_paths" "tests.test_app_paths tests.test_gui_document_flows"; do
  echo "$order: $($PY -B -m unittest $order 2>&1 | grep -E '^(OK|FAILED)')"
done
```

Expected:

```text
tests.test_config: OK
tests.test_gui_document_flows: OK (skipped=2)
tests.test_app_paths: OK
tests.test_config tests.test_gui_document_flows: OK (skipped=2)
tests.test_gui_document_flows tests.test_config: OK (skipped=2)
tests.test_config tests.test_app_paths: OK
tests.test_app_paths tests.test_config: OK
tests.test_gui_document_flows tests.test_app_paths: OK (skipped=2)
tests.test_app_paths tests.test_gui_document_flows: OK (skipped=2)
```

- [ ] **Step 5: AC4 msgids (from the repo root) and AC5 fixtures.**

```bash
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --compare $T/base_msgids.json)
git -C $REPO diff main --stat -- client/locales client/tests/fixtures
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
```

Expected (353 source msgids, the same 4 only-in-pot wildcards as before, the same set as the Task 0 snapshot of `main`'s code; no `locales` or fixture diff; both sha256 unchanged):

```text
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
SOURCE == SAVED
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
```

- [ ] **Step 6: AC6 greps (correction 1 for the presenter one).**

```bash
cd $REPO
echo 1; grep -rn "CONFIG_PATH" client --include=*.py --exclude-dir=.venv
echo 2; grep -rn "get_config_path\|get_dictionary_directory\|get_workspace_directory\|get_log_directory\|get_dual_view_directory" client --include=*.py --exclude-dir=.venv
echo 3; grep -rnE "(_dir|directory|paths): (Path|ApplicationPaths) \| None" client/app_paths.py client/dictionaries client/documents/workspace.py client/dual_view/files.py
echo 4; grep -rn "conversion\.presenter\|conversion/presenter" client --include=*.py --exclude-dir=.venv
echo 5; grep -rn "documents" client/conversion --include=*.py
echo 6; ls client/conversion/presenter.py 2>&1
echo 7; grep -rn "build_application_paths()" client --include=*.py --exclude-dir=.venv --exclude-dir=tests
cd $REPO/client
```

Expected (1-5: nothing; 6: no such file; 7: the three implicit-root call sites, `gui.py` `OnInit`, `log.py` `_log_directory`, `main.py` `run_demo`):

```text
1
2
3
4
5
6
ls: cannot access 'client/conversion/presenter.py': No such file or directory
7
client/main.py:16:    paths = build_application_paths()
client/log.py:8:    return build_application_paths().log
client/gui.py:1061:		paths = build_application_paths()
```

- [ ] **Step 7: AC7, no test writes real application data (correction 4).**

```bash
snapshot() {
  for path in config.json workspace; do test -e "$path" && echo "exists: $path"; done
  test -d dictionary && find dictionary -type f -exec sha256sum {} + | LC_ALL=C sort
  ls dual_view | grep -v -e '\.py$' -e '^__pycache__$'
  ls log
}
snapshot > $T/app_data_before.txt
$PY -m unittest discover -s tests > /dev/null 2>&1
snapshot > $T/app_data_after.txt
diff $T/app_data_before.txt $T/app_data_after.txt && echo "application data unchanged by the suite"
ls -d config.json workspace 2>&1
ls log
```

Expected (an empty diff; `config.json` and `workspace/` absent; `log/` holds only the four files the baseline suite already writes to):

```text
application data unchanged by the suite
ls: cannot access 'config.json': No such file or directory
ls: cannot access 'workspace': No such file or directory
dual_view.log
init.log
math.log
translation.log
```

- [ ] **Step 8: AC8, the branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -6
git -C $REPO diff main --name-only -- . ':!client'
git -C $REPO diff main --stat -M -- client | tail -1
git -C $REPO diff main --name-status -M -- client | LC_ALL=C sort -k2
```

Expected (the five commits on top of the plan; outside `client/` only the two spec files and this plan differ from `main`; inside it 15 production and 13 test files, the presenter as a pure rename):

```text
refactor: move conversion presenter to ui
refactor: remove implicit application path defaults
refactor: inject application paths and config store at startup
refactor: add config store behind the config functions
test: characterize application paths wiring
docs: plan application paths injection
docs/superpowers/plans/2026-10-08-p2-6-application-paths.md
docs/superpowers/specs/2026-10-08-p2-6-application-paths-design.md
docs/superpowers/specs/2026-10-08-p2-6-application-paths-design_zh-TW.md
 28 files changed, 1107 insertions(+), 441 deletions(-)
M	client/app_paths.py
M	client/client_init.py
M	client/config.py
R100	client/conversion/presenter.py	client/ui/conversion_presenter.py
M	client/dictionaries/manager.py
M	client/dictionaries/name_prompt.py
M	client/documents/export_coordinator.py
M	client/documents/workspace.py
M	client/dual_view/files.py
M	client/gui.py
M	client/log.py
M	client/main.py
M	client/settings/translation.py
M	client/settings/translation_tables.py
M	client/settings/view.py
M	client/tests/test_app_paths.py
M	client/tests/test_client_init.py
M	client/tests/test_config.py
M	client/tests/test_conversion_language_explicit.py
M	client/tests/test_conversion_presenter.py
M	client/tests/test_export_coordinator.py
M	client/tests/test_gui_document_flows.py
M	client/tests/test_log.py
M	client/tests/test_main_demo.py
M	client/tests/test_translation_import_isolation.py
M	client/tests/test_translation_settings.py
M	client/tests/test_translation_tables.py
M	client/tests/test_view_settings.py
```

Not verifiable on Linux (Windows verification debt, from the spec): build with `scripts\build-dotexpress.bat` and run the exe from a writable folder: `config.json`, `dictionary\`, `workspace\`, `log\` and `dual_view\` appear next to `DotExpress.exe` as before; settings, the selected dictionary and documents survive a restart; Dual View opens and its HTML is removed on exit; client init still reports (server log, or `log\init.log` on failure). Run it from a read-only folder (for example under `Program Files` without elevation): the same localized startup error with the failing path, and no runtime starts. Run `python gui.py` from `client\` and from another working folder: the same `client\` root is used. PyInstaller `--onefile` must pick up `ui/conversion_presenter.py` through `gui.py`'s static import. No visible or spoken change is intended, so no screenshot is needed.
