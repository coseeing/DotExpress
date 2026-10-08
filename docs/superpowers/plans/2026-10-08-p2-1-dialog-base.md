# Dialog Base and Typed Name Errors (P2-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the copied dialog boilerplate and the string matching on name errors without changing anything a user sees. `shared/name_validation.normalize_base_name` raises `NameValidationError(ValueError)` with a `code` (`empty`, `invalid`, `too_long`, `reserved`) and the same English message. A new wx-free `client/ui/dialog_base.py` holds `ContextManagedDialog`, `NameDialogBase` with `NameDialogMessages`, and `SingletonDialogMixin`. `dialog.py` loses its seven `__enter__/__exit__` pairs and `_normalize_dialog_name`; the two name dialogs only declare a normalizer and their messages. `settings/dialogs.py` loses both copies of `_destroy`, `_is_destroyed_window_error` and the `show_singleton` body. `ConvertingDialog` moves unchanged from `gui.py` to `dialog.py`. Same text, order, focus and result in every dialog; the msgid set stays at 353; `client/locales` does not change.

**Architecture:** Six commits in the spec's order. Task 1 is the safety net on unchanged production code (name validation, both name dialogs against a frozen copy of `_normalize_dialog_name` on 3,431 generated names, `_on_ok` call order, the `with` contract of seven dialogs, both singletons, `ConvertingDialog`); it cannot be red, so a throwaway mutant runner shows it catches 13 deliberate breakages. Tasks 2 and 3 start with failing tests (red: `NameValidationError` and `ui.dialog_base` do not exist). Tasks 4 and 5 are pure migrations: no new tests, the Task 1 net must stay green; Task 4 shows the acceptance grep before and after, Task 5 runs a throwaway probe of decision D1 before and after. Task 6 switches the `ConvertingDialog` tests to `dialog.ConvertingDialog` first (red: 3 errors), then moves the class.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `dataclasses`, `ast`, `itertools`). wxPython is not installed: the dialog tests run against the stubs in `tests/wx_stub.py` (`dialog_validation_stubs`, `settings_dialog_stubs`, `gui_frame_stubs`), and `ui/dialog_base.py` is tested without any stub scope.

**Spec:** `docs/superpowers/specs/2026-10-08-p2-1-dialog-base-design.md` (authoritative, commit `1066c5c`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p2-1-dialog-base`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (13, nothing else): production `client/shared/name_validation.py`, `client/ui/dialog_base.py` (new), `client/dialog.py`, `client/settings/dialogs.py`, `client/gui.py`; tests `client/tests/test_name_validation.py` (new), `client/tests/test_dialog_validation.py`, `client/tests/test_settings_dialogs.py`, `client/tests/test_converting_dialog.py` (new), `client/tests/test_dictionary_manager.py`, `client/tests/test_document_workspace.py`, `client/tests/test_dialog_base.py` (new), `client/tests/wx_stub.py`. Never touch `client/locales/`, `scripts/`, `client/dictionaries/`, `client/documents/`, `client/conversion/`, `client/about.py`, any other `client/ui/` module or `client/tests/fixtures/`.
- Indentation: `client/dialog.py` and `client/gui.py` use tabs; every other touched file uses 4 spaces. The patches and file blocks carry the exact characters; run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes: the seven name-dialog msgids move from `_()` to `N_()` (same literals), so the source msgid set is compared with the Task 0 snapshot after Task 4 and at the end (`SOURCE == SAVED`, 353). No `.po`/`.mo` change, no `generate_pot.bat` run.
- The golden fixture is never touched; its sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd` is checked in Task 0 and Task 7.
- Test text is ASCII except the zh_TW messages the dialogs show and Unicode whitespace written as escapes (`\u3000`, `\xa0`, `\x85`).
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, and absolute paths are stripped from import errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p21impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.4.
- Baseline (re-verified at `1066c5c`, the spec commit; code identical to `000239b`): `$PY -m unittest discover -s tests` gives `Ran 818 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: three of the test modules the spec names use tabs.** Current State says "the test modules named below use 4 spaces". `tests/test_dialog_display.py`, `tests/test_dictionary_management_dialog.py` and `tests/test_dictionary_presenter.py` are indented with tabs. None of them is edited by this plan (they must only stay green), so nothing else changes; every test file this plan edits does use 4 spaces.
2. **Refinement: test count fixed at 71 new tests (818 -> 889).** Task 1: 43 (`tests/test_name_validation.py` 9, `tests/test_dialog_validation.py` 11, `tests/test_settings_dialogs.py` 20, `tests/test_converting_dialog.py` 3); Task 2: 5 (2 in `test_name_validation`, 1 in `test_dictionary_manager`, 2 in `test_document_workspace`); Task 3: 23 (`tests/test_dialog_base.py`); Tasks 4-6: 0. The roadmap command (spec AC1) goes from 40 to 71 tests.
3. **Refinement: the `ConvertingDialog` tests live in a new module, `tests/test_converting_dialog.py`.** Each test builds the dialog with `object.__new__`, gives it a recording `Bind`, patches `wx.Dialog.__init__` of the stub base (the "recording `wx.Dialog.__init__`" of the spec), replaces the defining module's `wx` global with a namespace of distinct flag values and patches its `finalize_dialog_layout`, then runs the real `__init__`. That works under both the gui stubs (Task 1: `gui.ConvertingDialog`, loaded with the same scope as `test_gui_document_flows`) and the dialog-validation stubs (Task 6: `dialog.ConvertingDialog`, loaded like `test_dialog_validation`). The move commit changes only the module-level loading block (the module the tests call `defining_module`); the three test bodies are not edited. This is the switch the spec allows.
4. **Refinement: the frozen oracle checks the whole corpus through `_on_ok` too.** The spec asks for `_validate_name` on the corpus and the normalized name "on a sample". `NameDialogOracleTest` runs every one of the 3,431 names through both `_validate_name` and the real `_on_ok` (with a recording text box, event and message box) for both dialogs and compares message or normalized name with the oracle; it asserts the corpus size first. The corpus is the spec's (all strings of up to 3 pieces from 15 pieces, plus 19 words with one piece added at either end). Fake controls are plain classes, not `Mock`s, so the two tests take about 0.07 s.
5. **Refinement: part B placement.** The "importer base name" of the spec is `documents.importers.base.source_name` (used by the docx, epub and pdf importers); its test sits in `tests/test_document_workspace.py` next to the `normalize_document_name` test, and checks the English message too (it is the reachable `FileIssuesDialog` reason, known quirk 3). New tests reach `NameValidationError` through `shared.name_validation` (module attribute), so the red run shows the 5 new tests failing while every Task 1 test in the same modules still runs.
6. **Refinement: the characterization net is shown to fail.** Task 1 cannot be red, so `$T/tools/dialog_mutants.py` applies 13 small breakages (one edit each) to a copy of `client/` (reserved message lost, too-long reported as invalid, `_on_ok` keeps the raw text, focus before message box, `__exit__` swallowing, normalizer accepting a trailing period, a dead-window phrase dropped, `Show` before the slot is set, category selected after `Raise`, the category check dropped, `_destroy` clearing any slot, `ConvertingDialog` always vetoing or keeping its close box). Each one makes the Task 1 modules fail.
7. **Refinement: a throwaway probe for decision D1.** `$T/tools/d1_check.py` loads `settings.dialogs` against the settings stubs with `PyDeadObjectError` removed and makes the open dialog raise from `Iconize`. Before Task 5 both a dead-window error and an unrelated `RuntimeError` become `AttributeError: module 'wx' has no attribute 'PyDeadObjectError'`; after Task 5 the dead one rebuilds the dialog and the unrelated one is re-raised. The stub module's `__getattr__` turns any missing name into a fresh plain class, so the probe also makes it raise `AttributeError` for `PyDeadObjectError`; without that, `getattr(wx, "PyDeadObjectError", None)` would return a class that is not an exception. Every committed stub defines `PyDeadObjectError`, so the tests are not affected.
8. **Refinement: small code choices the spec leaves open.** `DotExpressSettingsDialog.show_singleton` passes `None if initial_category is None else lambda instance: instance.select_category(initial_category)` to `_raise_existing` (no lambda assigned to a name). `ui/dialog_base.py` gets a module docstring and `_raise_existing` a one-line docstring; `NameDialogMessages.message_for` a one-line docstring; `_NameDialog` a docstring. `ConvertingDialog` goes after `FileIssuesDialog` in `dialog.py`. Otherwise the code is the spec's, character for character.
9. **Refinement: AC3's order check also covers `tests/test_converting_dialog.py`**, the new stub-scope module (alone and in both orders with `tests/test_dialog_base.py`).

Everything else in the spec was re-checked at `1066c5c`: the dialog inventory and line numbers, the identical `__enter__/__exit__` pairs, both `show_singleton` copies (including the `ValueError` for an unregistered category before the slot is read), `_normalize_dialog_name` and its two string guesses (`dialog.py:82`, `dialog.py:84`), the consumers of `str(exc)` (presenter lines 105 and 149), the stub table, the baseline (818, 40 for the roadmap command) and the msgid scan (353 plus the 4 known only-in-pot wildcards). The spec's equivalence claim was re-run as part of the oracle test: no difference on the 3,431 names for either dialog.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `1066c5c` (`$SP/p21plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 6 the 20 shuffle seeds, the pair orders, the msgid scan and every acceptance criterion passed. The patches in this file are `git diff`s of those commits (Tasks 2 and 6 split into the red test step and the implementation step); new modules are given as whole files. Then this file's blocks were run in order on fresh clones (`$SP/p21plan/replay1` to `replay5`, each with a stand-in plan commit and a local `main` at `000239b`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 6 commits applied, every expected block (28) matched byte for byte on the final replay, and the resulting `client/` tree is identical to the dry clone. Final sha256: `client/shared/name_validation.py` `2295a7bed96750d302ae8a35e0db07c2753a0f6666e85637a00e8e81da7d7001`, `client/ui/dialog_base.py` `284d8c3dd7f2b82bcd414c5b70532c143fe24db043e8f9fb1873b3db37b77944`, `client/dialog.py` `3beea02e1f29d96604ffcaf3310a59d63902d35f81947778793789ec5dd39a43`, `client/settings/dialogs.py` `257e4508682fe7c42b2621b0ce5337080e91701170894a26df98c89aaf057239`, `client/gui.py` `c2381ee13d9ef022c23863b18b97cbffb438d198cc38b64ffddf972236ff3892`, `client/tests/test_name_validation.py` `2c56b45345707dfa4e185518c0b6aa4e8cf5feb9f889fff6363c4f7e025bd3e6`, `client/tests/test_dialog_validation.py` `8600fa2851a4e2b63a0799a3593cf7bf5f268f682010e9731182716f1c701ce7`, `client/tests/test_settings_dialogs.py` `e7d015ea5aeaf87ab36ace6118004ba92a621bfc1ee1559c420b0fd3f4b96396`, `client/tests/test_converting_dialog.py` `7616778e212e526f984265042628f986063974e3830c3ffcaefcade367b42a68`, `client/tests/test_dictionary_manager.py` `ad6db0dac1d424d9b56829b6061f08b0471464a5c4ea5ffb9f41f8428cc1e822`, `client/tests/test_document_workspace.py` `687c207ea08618d18c715d7cbf702543a8bffe308561c925635567a0b14f2386`, `client/tests/test_dialog_base.py` `91416e1280e447fe5e29f2c31bfbcd5f5fe33988c57d868d7276921f26cd010d`, `client/tests/wx_stub.py` `22d0e04213df93d299693750b8d833760b5134813b845f35b2be8870d309bd15`; `client/tests/fixtures/translation_golden.json` unchanged at `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`.

## Review Focus

1. **Same messages for every name.** The dialogs call the normalizer on the raw text and map `error.code`; the old pre-checks are gone because `normalize_base_name` runs the same checks in the same order on the same raw text. Guards: the frozen oracle over 3,431 names through `_validate_name` and `_on_ok` for both dialogs, the explicit zh_TW table (20 inputs), the reserved message always naming `default`. The `except ValueError` fallback keeps the old breadth (any other `ValueError` from a normalizer is "invalid"); other exceptions still propagate.
2. **Same typed-error compatibility.** `NameValidationError` subclasses `ValueError` with the English message as its only argument, so `str(error)`, `args` and every `except ValueError`/`except Exception` consumer are unchanged; `dictionaries/`, `documents/` and the presenter have no diff. `copy.copy` or pickling an instance would fail (`args` lacks the code); nothing in the client copies or pickles exceptions (no `pickle`, `copy` or `multiprocessing` import).
3. **Same singleton behavior.** Call order `Iconize(False)`, [`select_category`], `Raise`, `SetFocus`; slot set before `Show`; unregistered category rejected before the slot is read; non-dead errors re-raised with the slot kept; constructor failure leaves the slot empty. Guards: the 20 Task 1 singleton tests for both classes and the mixin tests. Intended differences: D1 (no `AttributeError` on a wx without `PyDeadObjectError`, shown by the probe) and D2 (`_destroy` clears `type(self)`'s slot; same class for both production dialogs).
4. **Stub-scope safety.** `ui/dialog_base.py` imports only `__future__`, `dataclasses`, `typing`, `i18n` and `shared.name_validation` (AST guard), defines no `__init__`/`__new__`/`__slots__`/metaclass and goes first in every base list, so it binds to no stub. Guards: 20 shuffled full-suite seeds, each dialog test module alone and in both orders with `test_dialog_base`, and the oracle (which would show the invalid message everywhere if `NameValidationError` were loaded twice).
5. **Untouched seams.** `show_singleton` signatures, `sync_open_font_size` (P2-4), the name-dialog constructors and `get_*_name`, `finalize_dialog_layout`, `show_converting_dialog`/`close_converting_dialog`, the presenter and importer error handling, `MAX_DICTIONARY_NAME_LENGTH` (now without a consumer; out of scope).

## File Map

- Task 1: create `client/tests/test_name_validation.py`, `client/tests/test_converting_dialog.py`; modify `client/tests/test_dialog_validation.py`, `client/tests/test_settings_dialogs.py`.
- Task 2: modify `client/shared/name_validation.py`, `client/tests/test_name_validation.py`, `client/tests/test_dictionary_manager.py`, `client/tests/test_document_workspace.py`.
- Task 3: create `client/ui/dialog_base.py`, `client/tests/test_dialog_base.py`.
- Task 4: modify `client/dialog.py`.
- Task 5: modify `client/settings/dialogs.py`.
- Task 6: modify `client/dialog.py`, `client/gui.py`, `client/tests/wx_stub.py`, `client/tests/test_converting_dialog.py`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 818 |
| 1 characterization | 43 (9 name validation, 11 name dialogs and `with`, 20 singletons, 3 `ConvertingDialog`) | 861 |
| 2 typed error | 5 | 866 |
| 3 dialog base | 23 | 889 |
| 4 `dialog.py` | 0 | 889 |
| 5 settings dialogs | 0 | 889 |
| 6 `ConvertingDialog` move | 0 | 889 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `dialog_mutants.py <client_dir> <scratch_dir> [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`) to `<scratch_dir>/client` once, then for each mutant edits one file in the copy, runs the four Task 1 modules there and restores the file. The repo is never changed. Only meaningful in Task 1 (the patterns match the pre-refactor code).
- `d1_check.py`: the decision D1 probe (refinement 7). Run from `client/`.
- Existing: `$SP/p12/tools/msgid_scan.py` (the P0-5 AST stand-in for xgettext; source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`) and `$SP/shuffle_harness.py <seed>` (runs every test module in a seeded random order, one process).

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
```

Expected (no output from `status`; HEAD is the plan commit):

```text
docs: plan dialog base and typed name errors
refactor/p2-1-dialog-base
```

- [ ] **Step 2: Create the tools.**

```bash
mkdir -p $T/tools
cat > $T/tools/dialog_mutants.py <<'EOF'
"""Run the P2-1 characterization tests against deliberately broken code (throwaway).

Usage: python dialog_mutants.py <client_dir> <scratch_dir> [mutant ...]
Copies <client_dir> (without .venv, __pycache__, log) to <scratch_dir>/client once,
then for each mutant writes one edited file into the copy, runs the Task 1 test
modules there and restores the file. <client_dir> is never changed.
Prints "<mutant>: failures=F errors=E" per mutant. With no mutant names, runs all.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = [
    "tests.test_name_validation",
    "tests.test_dialog_validation",
    "tests.test_settings_dialogs",
    "tests.test_converting_dialog",
]

# name -> (file, old, new); old must occur exactly once.
MUTANTS = {
    "dictionary-reserved-message-lost": (
        "dialog.py",
        "\t\tif reserved_message and normalized_candidate",
        "\t\tif False and normalized_candidate",
    ),
    "too-long-reported-as-invalid": (
        "dialog.py",
        "\tif len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:\n\t\treturn None, length_message",
        "\tif len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:\n\t\treturn None, invalid_message",
    ),
    "document-on-ok-keeps-raw-text": (
        "dialog.py",
        "\t\t\t_(\"Document name is not a valid Windows file name.\"),\n\t\t)\n\t\tif message:\n"
        "\t\t\twx.MessageBox(message, _(\"Info\"), wx.OK | wx.ICON_INFORMATION, parent=self)\n"
        "\t\t\tself.name_ctrl.SetFocus()\n\t\t\treturn\n\t\tself.name_ctrl.SetValue(normalized_candidate)",
        "\t\t\t_(\"Document name is not a valid Windows file name.\"),\n\t\t)\n\t\tif message:\n"
        "\t\t\twx.MessageBox(message, _(\"Info\"), wx.OK | wx.ICON_INFORMATION, parent=self)\n"
        "\t\t\tself.name_ctrl.SetFocus()\n\t\t\treturn\n\t\tself.name_ctrl.SetValue(candidate)",
    ),
    "dictionary-on-ok-focus-before-message": (
        "dialog.py",
        "\t\tif message:\n\t\t\twx.MessageBox(message, _(\"Info\"), wx.OK | wx.ICON_INFORMATION, parent=self)\n"
        "\t\t\tself.name_ctrl.SetFocus()\n\t\t\treturn\n\t\tself.name_ctrl.SetValue(normalized_candidate)\n"
        "\t\tevent.Skip()\n\n\tdef _validate_name(self, candidate: str) -> str | None:\n"
        "\t\t_normalized, message = _normalize_dialog_name(\n\t\t\tcandidate,\n\t\t\tnormalize_dictionary_name,",
        "\t\tif message:\n\t\t\tself.name_ctrl.SetFocus()\n"
        "\t\t\twx.MessageBox(message, _(\"Info\"), wx.OK | wx.ICON_INFORMATION, parent=self)\n"
        "\t\t\treturn\n\t\tself.name_ctrl.SetValue(normalized_candidate)\n"
        "\t\tevent.Skip()\n\n\tdef _validate_name(self, candidate: str) -> str | None:\n"
        "\t\t_normalized, message = _normalize_dialog_name(\n\t\t\tcandidate,\n\t\t\tnormalize_dictionary_name,",
    ),
    "exit-swallows-exceptions": (
        "dialog.py",
        "\tdef __exit__(self, exc_type, exc, _tb) -> None:\n\t\tself.Destroy()\n\n\nclass DictionaryNameDialog",
        "\tdef __exit__(self, exc_type, exc, _tb) -> None:\n\t\tself.Destroy()\n\t\treturn True\n\n\nclass DictionaryNameDialog",
    ),
    "trailing-period-accepted-by-normalizer": (
        "shared/name_validation.py",
        "    if name.endswith((\" \", \".\")):\n        raise ValueError(\"Name cannot end with a period or space.\")\n",
        "",
    ),
    "destroyed-phrase-not-dead": (
        "settings/dialogs.py",
        "            or \"already deleted\" in message\n            or \"destroyed\" in message\n        )\n\n    @classmethod\n    def show_singleton(\n        cls,\n        *,\n        parent,\n        script_path",
        "            or \"already deleted\" in message\n        )\n\n    @classmethod\n    def show_singleton(\n        cls,\n        *,\n        parent,\n        script_path",
    ),
    "text-processing-shows-before-slot": (
        "settings/dialogs.py",
        "        instance = cls(parent, script_path=script_path)\n        cls._instance = instance\n        instance.Show()\n",
        "        instance = cls(parent, script_path=script_path)\n        instance.Show()\n        cls._instance = instance\n",
    ),
    "settings-category-selected-after-raise": (
        "settings/dialogs.py",
        "                if initial_category is not None:\n                    instance.select_category(initial_category)\n                instance.Raise()\n",
        "                instance.Raise()\n                if initial_category is not None:\n                    instance.select_category(initial_category)\n",
    ),
    "settings-category-check-dropped": (
        "settings/dialogs.py",
        "        if initial_category is not None and initial_category not in cls.category_classes:\n            raise ValueError(\"initial_category is not registered\")\n",
        "",
    ),
    "text-processing-destroy-clears-any-slot": (
        "settings/dialogs.py",
        "        if TextProcessingDialog._instance is self:\n",
        "        if True:\n",
    ),
    "converting-dialog-always-vetoes": (
        "gui.py",
        "\t\tif evt.CanVeto():\n\t\t\tevt.Veto()",
        "\t\tevt.CanVeto()\n\t\tevt.Veto()",
    ),
    "converting-dialog-keeps-close-box": (
        "gui.py",
        "style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP",
        "style = wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP",
    ),
}


def main() -> int:
    client_dir = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    names = sys.argv[3:] or list(MUTANTS)
    copy = scratch / "client"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(client_dir, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", "log", ".pytest_cache"))
    (copy / "log").mkdir()
    for name in names:
        relative, old, new = MUTANTS[name]
        path = copy / relative
        original = path.read_text(encoding="utf-8")
        count = original.count(old)
        if count != 1:
            print(f"{name}: pattern found {count} times")
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", *MODULES],
                cwd=copy,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            path.write_text(original, encoding="utf-8")
        summary = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
        failures = re.search(r"failures=(\d+)", summary)
        errors = re.search(r"errors=(\d+)", summary)
        print(
            f"{name}: failures={failures.group(1) if failures else 0} errors={errors.group(1) if errors else 0}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
cat > $T/tools/d1_check.py <<'EOF'
"""Decision D1 probe (throwaway; run from a client/ directory).

Loads settings.dialogs against the settings stubs with wx.PyDeadObjectError
removed (as believed for wxPython 4.2.5) and calls
TextProcessingDialog.show_singleton while the open dialog raises from Iconize.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path.cwd()))

from tests import wx_stub

stubs = wx_stub.settings_dialog_stubs()
wx = stubs["wx"]
del wx.PyDeadObjectError
auto_class = wx.__getattr__


def no_dead_object_error(name):
    if name == "PyDeadObjectError":
        raise AttributeError(f"module 'wx' has no attribute {name!r}")
    return auto_class(name)


wx.__getattr__ = no_dead_object_error
scope = wx_stub.StubScope(stubs, isolate=("settings.dialogs",))
with scope.loading():
    from settings.dialogs import TextProcessingDialog
scope.activate()
try:
    print("hasattr(wx, 'PyDeadObjectError'):", hasattr(wx, "PyDeadObjectError"))
    for error in (RuntimeError("window has been deleted"), RuntimeError("unexpected")):
        existing = Mock()
        existing.Iconize.side_effect = error
        with (
            patch.object(TextProcessingDialog, "_instance", existing),
            patch.multiple(TextProcessingDialog, __init__=lambda self, *a, **k: None, Show=lambda self: None),
        ):
            try:
                result = TextProcessingDialog.show_singleton(parent=None, script_path="x.py")
            except Exception as exc:
                print(f"{error!r}: raised {type(exc).__name__}: {exc}")
            else:
                print(f"{error!r}: rebuilt={result is not existing} slot_holds_new={TextProcessingDialog._instance is result}")
finally:
    scope.deactivate()
EOF
ls $T/tools
```

Expected:

```text
d1_check.py
dialog_mutants.py
```

- [ ] **Step 3: Record the baseline suite, the roadmap command, the msgids and the fixture.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json
```

Expected (818 tests with the P2-5 failure; the roadmap command runs 40 tests):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 818 tests
FAILED (failures=1, skipped=9)
Ran 40 tests
OK
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

---

### Task 1: Characterize dialog lifecycle, name validation and singletons (spec part A)

Nothing in production changes. Every new test passes on the current code by construction; Step 6 shows the net can fail.

- [ ] **Step 1: Pin `normalize_base_name` (A.2).** New module: every check with its exact English message, the order of the checks, the stripped result (Python `str.strip`, so U+3000, U+00A0 and U+0085 are trimmed and U+007F is kept), reserved names casefolded and reported with the stripped name as typed, and `args == (message,)`.

```bash
cat > tests/test_name_validation.py <<'EOF'
import unittest

from shared.name_validation import normalize_base_name

EMPTY = "Name cannot be empty."
INVALID = "Name contains invalid characters."
TRAILING = "Name cannot end with a period or space."
TOO_LONG = "Name cannot exceed 32 characters."


class NormalizeBaseNameTest(unittest.TestCase):
    def assert_rejected(self, name: str, message: str, **kwargs) -> ValueError:
        with self.assertRaises(ValueError) as caught:
            normalize_base_name(name, **kwargs)
        self.assertEqual(str(caught.exception), message)
        return caught.exception

    def test_returns_the_stripped_name(self) -> None:
        cases = (
            ("name", "name"),
            (" name", "name"),
            ("name　", "name"),
            ("　name", "name"),
            ("\xa0x", "x"),
            ("\x85a", "a"),
            ("1.1", "1.1"),
            ("x\x7f", "x\x7f"),
            ("a" * 32, "a" * 32),
            (" " + "a" * 32, "a" * 32),
            ("default", "default"),
        )
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(normalize_base_name(name), expected)

    def test_rejects_empty_names(self) -> None:
        for name in ("", " ", "　", "\t", " \t "):
            with self.subTest(name=name):
                self.assert_rejected(name, EMPTY)

    def test_rejects_control_characters(self) -> None:
        for name in ("a\tb", "\x00", "a\x1f", "a\t."):
            with self.subTest(name=name):
                self.assert_rejected(name, INVALID)

    def test_rejects_a_trailing_period_or_space_on_the_raw_name(self) -> None:
        for name in ("name.", "name ", " name ", ".", "..", "a" * 40 + ".", "a" * 33 + " "):
            with self.subTest(name=name):
                self.assert_rejected(name, TRAILING)

    def test_rejects_names_longer_than_32_characters_after_stripping(self) -> None:
        for name in ("a" * 33, "　" + "a" * 33, "?" * 33):
            with self.subTest(name=name):
                self.assert_rejected(name, TOO_LONG)

    def test_rejects_names_that_are_not_legal_windows_file_names(self) -> None:
        for name in ("a?b", "a<b", "CON", "con.txt", "COM1", "LPT9.a", "nul.tar.gz", "　..　", "name.　"):
            with self.subTest(name=name):
                self.assert_rejected(name, INVALID)

    def test_rejects_reserved_names_case_insensitively_with_the_stripped_name(self) -> None:
        cases = (
            ("default", {"default"}, "Name 'default' is reserved."),
            ("Default", {"default"}, "Name 'Default' is reserved."),
            (" DEFAULT", {"Default"}, "Name 'DEFAULT' is reserved."),
            ("default　", {"default"}, "Name 'default' is reserved."),
        )
        for name, reserved, message in cases:
            with self.subTest(name=name):
                self.assert_rejected(name, message, reserved_names=reserved)

    def test_windows_check_runs_before_the_reserved_check(self) -> None:
        self.assert_rejected("CON", INVALID, reserved_names={"con"})

    def test_errors_are_value_errors_with_the_message_as_only_argument(self) -> None:
        cases = (
            ("", EMPTY),
            ("a\tb", INVALID),
            ("name.", TRAILING),
            ("a" * 33, TOO_LONG),
            ("CON", INVALID),
        )
        for name, message in cases:
            with self.subTest(name=name):
                error = self.assert_rejected(name, message)
                self.assertIsInstance(error, ValueError)
                self.assertEqual(error.args, (message,))


if __name__ == "__main__":
    unittest.main()
EOF
```

- [ ] **Step 2: Pin the name dialogs and the `with` contract (A.1).** `_pre_p2_1_normalize_dialog_name` is a verbatim copy of today's `dialog._normalize_dialog_name` (renamed) and is the oracle. `NameDialogOracleTest` compares both dialogs with it on the 3,431-name corpus through `_validate_name` and `_on_ok`; `NameDialogMessageTableTest` is the explicit zh_TW table; `NameDialogOkTest` pins the exact `_on_ok` call sequence (`MessageBox(message, "資訊", OK | ICON_INFORMATION, parent=dialog)` then `SetFocus`, no `SetValue`, no `Skip`; or `SetValue(normalized)` then `Skip`), with `wx.MessageBox`, `wx.OK` (4) and `wx.ICON_INFORMATION` (128) patched onto the stub with `create=True`; `DialogContextManagerTest` covers the seven classes (instances from `object.__new__`, `Destroy` a `Mock`).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_dialog_validation.py b/client/tests/test_dialog_validation.py
index 406dd6b..681e220 100644
--- a/client/tests/test_dialog_validation.py
+++ b/client/tests/test_dialog_validation.py
@@ -1,14 +1,139 @@
+from __future__ import annotations
+
+import itertools
 import unittest
+from collections.abc import Callable
+from contextlib import contextmanager
+from unittest.mock import Mock, patch
 
 from tests import wx_stub
 
 _SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog",))
 with _SCOPE.loading():
-    from dialog import DictionaryNameDialog, DocumentNameDialog
+    import dialog as dialog_module
+    from dialog import (
+        AddSymbolDialog,
+        DictionaryManagementDialog,
+        DictionaryNameDialog,
+        DocumentNameDialog,
+        FileIssuesDialog,
+        InvalidWorkspaceFilesDialog,
+        SpeechSymbolsDialog,
+    )
 
 setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
 
+from dictionaries.manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name
+from documents.workspace import normalize_document_name
+from i18n import _
+
+DICTIONARY_EMPTY = "請輸入字典名稱。"
+DICTIONARY_TOO_LONG = "字典名稱長度需為 1 到 32 個字元。"
+DICTIONARY_INVALID = "字典名稱不是有效的 Windows 檔名。"
+DICTIONARY_RESERVED = "字典名稱「default」為保留名稱。"
+DOCUMENT_EMPTY = "請輸入文件名稱。"
+DOCUMENT_TOO_LONG = "文件名稱長度需為 1 到 32 個字元。"
+DOCUMENT_INVALID = "文件名稱不是有效的 Windows 檔名。"
+INFO_TITLE = "資訊"
+CONTEXT_MANAGED_DIALOGS = (
+    AddSymbolDialog,
+    DictionaryNameDialog,
+    DocumentNameDialog,
+    InvalidWorkspaceFilesDialog,
+    FileIssuesDialog,
+    SpeechSymbolsDialog,
+    DictionaryManagementDialog,
+)
+
+
+# Pre-P2-1 reference: a verbatim copy of dialog._normalize_dialog_name as it was
+# before P2-1 removed it (renamed). Do not edit; it is the oracle for the name dialogs.
+def _pre_p2_1_normalize_dialog_name(
+    candidate: str,
+    normalizer: Callable[[str], str],
+    empty_message: str,
+    length_message: str,
+    invalid_message: str,
+    reserved_message: str | None = None,
+) -> tuple[str | None, str | None]:
+    if not candidate or not candidate.strip():
+        return None, empty_message
+    if any(ord(char) < 32 for char in candidate):
+        return None, invalid_message
+    if candidate.endswith((" ", ".")):
+        return None, invalid_message
+    normalized_candidate = candidate.strip()
+    if len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:
+        return None, length_message
+    try:
+        return normalizer(normalized_candidate), None
+    except ValueError as exc:
+        if reserved_message and normalized_candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
+            return None, reserved_message
+        if "exceed" in str(exc):
+            return None, length_message
+        return None, invalid_message
+
+
+def _pre_p2_1_dictionary_result(candidate: str) -> tuple[str | None, str | None]:
+    return _pre_p2_1_normalize_dialog_name(
+        candidate,
+        normalize_dictionary_name,
+        _("Please enter the dictionary name."),
+        _("Dictionary name must be 1 to 32 characters."),
+        _("Dictionary name is not a valid Windows file name."),
+        _('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
+    )
+
+
+def _pre_p2_1_document_result(candidate: str) -> tuple[str | None, str | None]:
+    return _pre_p2_1_normalize_dialog_name(
+        candidate,
+        normalize_document_name,
+        _("Please enter the document name."),
+        _("Document name must be 1 to 32 characters."),
+        _("Document name is not a valid Windows file name."),
+    )
+
+
+def _name_corpus() -> list[str]:
+    """Every string of up to 3 pieces from ALPHABET, plus WORDS with one piece added at either end."""
+    alphabet = ["", " ", ".", "\t", "\u3000", "\xa0", "\x85", "a", "?", "C", "O", "N", "d", "\x7f", "x."]
+    words = [
+        "default",
+        "Default",
+        "DEFAULT",
+        "default.",
+        " default",
+        "default\u3000",
+        "CON",
+        "con.txt",
+        "COM1",
+        "LPT9.a",
+        "..",
+        ".",
+        "a" * 32,
+        "a" * 33,
+        " " + "a" * 32,
+        "a" * 32 + "\u3000",
+        "a" * 31 + ".",
+        "\u3000" * 40,
+        "a" * 33 + " ",
+    ]
+    corpus = set(words)
+    for length in range(4):
+        for pieces in itertools.product(alphabet, repeat=length):
+            corpus.add("".join(pieces))
+    for word in words:
+        for piece in alphabet:
+            corpus.add(piece + word)
+            corpus.add(word + piece)
+    return sorted(corpus)
+
+
+NAME_CORPUS = _name_corpus()
+
 
 class _TextCtrl:
     def __init__(self) -> None:
@@ -97,5 +222,199 @@ class DialogValidationTextTest(unittest.TestCase):
                 )
 
 
+class _RecordingNameCtrl:
+    def __init__(self, value: str, events: list[tuple]) -> None:
+        self.value = value
+        self.events = events
+
+    def GetValue(self) -> str:
+        return self.value
+
+    def SetValue(self, value: str) -> None:
+        self.events.append(("SetValue", value))
+
+    def SetFocus(self) -> None:
+        self.events.append(("SetFocus",))
+
+
+class _RecordingEvent:
+    def __init__(self, events: list[tuple]) -> None:
+        self.events = events
+
+    def Skip(self) -> None:
+        self.events.append(("Skip",))
+
+
+class _NameDialogHarness:
+    """Runs a name dialog's real ``_on_ok`` with a recording text box, event and message box."""
+
+    @contextmanager
+    def recording_message_box(self):
+        events: list[tuple] = []
+
+        def message_box(*args, **kwargs):
+            events.append(("MessageBox", args, kwargs))
+
+        with (
+            patch.object(dialog_module.wx, "MessageBox", message_box, create=True),
+            patch.object(dialog_module.wx, "OK", 4, create=True),
+            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
+        ):
+            yield events
+
+    def run_on_ok(self, dialog_class, text: str, events: list[tuple]) -> object:
+        events.clear()
+        dialog = object.__new__(dialog_class)
+        dialog.name_ctrl = _RecordingNameCtrl(text, events)
+        dialog_class._on_ok(dialog, _RecordingEvent(events))
+        return dialog
+
+    def on_ok_outcome(self, dialog_class, text: str, events: list[tuple]) -> tuple[str, str]:
+        """("message", text) for box-then-focus, ("accepted", name) for set-then-skip, else ("unexpected", events)."""
+        dialog = self.run_on_ok(dialog_class, text, events)
+        if (
+            len(events) == 2
+            and events[0][0] == "MessageBox"
+            and events[0][1][1:] == (INFO_TITLE, 132)
+            and events[0][2] == {"parent": dialog}
+            and events[1] == ("SetFocus",)
+        ):
+            return "message", events[0][1][0]
+        if len(events) == 2 and events[0][0] == "SetValue" and events[1] == ("Skip",):
+            return "accepted", events[0][1]
+        return "unexpected", repr(events)
+
+
+class NameDialogOracleTest(_NameDialogHarness, unittest.TestCase):
+    def assert_matches_oracle(self, dialog_class, oracle) -> None:
+        self.assertEqual(len(NAME_CORPUS), 3431)
+        mismatches = []
+        with self.recording_message_box() as events:
+            for name in NAME_CORPUS:
+                normalized, message = oracle(name)
+                expected = ("message", message) if message else ("accepted", normalized)
+                validated = dialog_class._validate_name(object.__new__(dialog_class), name)
+                outcome = self.on_ok_outcome(dialog_class, name, events)
+                if validated != message or outcome != expected:
+                    mismatches.append((name, expected, validated, outcome))
+        self.assertEqual(mismatches, [])
+
+    def test_dictionary_name_dialog_matches_the_pre_p2_1_validation(self) -> None:
+        self.assert_matches_oracle(DictionaryNameDialog, _pre_p2_1_dictionary_result)
+
+    def test_document_name_dialog_matches_the_pre_p2_1_validation(self) -> None:
+        self.assert_matches_oracle(DocumentNameDialog, _pre_p2_1_document_result)
+
+
+NAME_MESSAGE_TABLE = (
+    ("", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
+    ("   ", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
+    ("\u3000", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
+    ("\t", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
+    ("a\x01b", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("name ", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("name.", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("name\u3000", None, None),
+    (" name", None, None),
+    ("a" * 32, None, None),
+    ("a" * 33, DICTIONARY_TOO_LONG, DOCUMENT_TOO_LONG),
+    (" " + "a" * 32, None, None),
+    (" " + "a" * 33, DICTIONARY_TOO_LONG, DOCUMENT_TOO_LONG),
+    ("a?b", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("CON", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("con.txt", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("..", DICTIONARY_INVALID, DOCUMENT_INVALID),
+    ("default", DICTIONARY_RESERVED, None),
+    ("Default", DICTIONARY_RESERVED, None),
+    ("DEFAULT", DICTIONARY_RESERVED, None),
+)
+
+
+class NameDialogMessageTableTest(unittest.TestCase):
+    def test_dictionary_name_dialog_messages(self) -> None:
+        dialog = object.__new__(DictionaryNameDialog)
+        for name, expected, _document_expected in NAME_MESSAGE_TABLE:
+            with self.subTest(name=name):
+                self.assertEqual(DictionaryNameDialog._validate_name(dialog, name), expected)
+
+    def test_document_name_dialog_messages(self) -> None:
+        dialog = object.__new__(DocumentNameDialog)
+        for name, _dictionary_expected, expected in NAME_MESSAGE_TABLE:
+            with self.subTest(name=name):
+                self.assertEqual(DocumentNameDialog._validate_name(dialog, name), expected)
+
+
+class NameDialogOkTest(_NameDialogHarness, unittest.TestCase):
+    def assert_rejects(self, dialog_class, cases) -> None:
+        with self.recording_message_box() as events:
+            for name, message in cases:
+                with self.subTest(name=name):
+                    dialog = self.run_on_ok(dialog_class, name, events)
+                    self.assertEqual(
+                        events,
+                        [("MessageBox", (message, INFO_TITLE, 132), {"parent": dialog}), ("SetFocus",)],
+                    )
+
+    def assert_accepts(self, dialog_class, cases) -> None:
+        with self.recording_message_box() as events:
+            for name, normalized in cases:
+                with self.subTest(name=name):
+                    self.run_on_ok(dialog_class, name, events)
+                    self.assertEqual(events, [("SetValue", normalized), ("Skip",)])
+
+    def test_dictionary_on_ok_shows_the_message_then_focuses_and_stays_open(self) -> None:
+        self.assert_rejects(
+            DictionaryNameDialog,
+            (("", DICTIONARY_EMPTY), ("a" * 33, DICTIONARY_TOO_LONG), ("CON", DICTIONARY_INVALID), ("Default", DICTIONARY_RESERVED)),
+        )
+
+    def test_dictionary_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
+        self.assert_accepts(DictionaryNameDialog, ((" name", "name"), ("name\u3000", "name"), ("1.1", "1.1")))
+
+    def test_document_on_ok_shows_the_message_then_focuses_and_stays_open(self) -> None:
+        self.assert_rejects(
+            DocumentNameDialog,
+            (("", DOCUMENT_EMPTY), ("a" * 33, DOCUMENT_TOO_LONG), ("CON", DOCUMENT_INVALID)),
+        )
+
+    def test_document_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
+        self.assert_accepts(DocumentNameDialog, ((" name", "name"), ("name\u3000", "name"), ("Default", "Default")))
+
+
+class DialogContextManagerTest(unittest.TestCase):
+    def make_dialog(self, dialog_class):
+        dialog = object.__new__(dialog_class)
+        dialog.Destroy = Mock()
+        return dialog
+
+    def test_with_returns_the_dialog_and_destroys_it_once(self) -> None:
+        for dialog_class in CONTEXT_MANAGED_DIALOGS:
+            with self.subTest(dialog=dialog_class.__name__):
+                dialog = self.make_dialog(dialog_class)
+                with dialog as entered:
+                    self.assertIs(entered, dialog)
+                    dialog.Destroy.assert_not_called()
+                dialog.Destroy.assert_called_once_with()
+
+    def test_with_destroys_the_dialog_and_propagates_an_exception(self) -> None:
+        for dialog_class in CONTEXT_MANAGED_DIALOGS:
+            with self.subTest(dialog=dialog_class.__name__):
+                dialog = self.make_dialog(dialog_class)
+                error = RuntimeError("boom")
+                with self.assertRaises(RuntimeError) as caught:
+                    with dialog:
+                        raise error
+                self.assertIs(caught.exception, error)
+                dialog.Destroy.assert_called_once_with()
+
+    def test_exit_returns_none(self) -> None:
+        for dialog_class in CONTEXT_MANAGED_DIALOGS:
+            with self.subTest(dialog=dialog_class.__name__):
+                dialog = self.make_dialog(dialog_class)
+                self.assertIsNone(dialog.__exit__(None, None, None))
+                self.assertIsNone(dialog.__exit__(ValueError, ValueError("x"), None))
+                self.assertEqual(dialog.Destroy.call_count, 2)
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
```

- [ ] **Step 3: Pin both singletons (A.3).** `_SingletonCharacterization` runs the same eight tests for `TextProcessingDialog` and `DotExpressSettingsDialog` (constructor and `Show` patched on the production class with `patch.multiple`, the slot with `patch.object`, so every test restores the class); the settings dialog adds three category tests; one test checks that the two slots are independent.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index 8cf4215..ce7d196 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -3,7 +3,7 @@ from __future__ import annotations
 import sys
 import unittest
 from pathlib import Path
-from unittest.mock import Mock, patch
+from unittest.mock import Mock, call, patch
 
 from tests import wx_stub
 
@@ -543,5 +543,236 @@ class DotExpressSettingsDialogFlowTest(unittest.TestCase):
         self.assertEqual(dialog._format_title("轉譯"), "DotExpress 設定：轉譯")
 
 
+def dead_window_errors():
+    return (
+        wx.PyDeadObjectError("dead"),
+        RuntimeError("Wrapped C/C++ object of type Dialog"),
+        RuntimeError("the window has been deleted"),
+        RuntimeError("window already deleted"),
+        RuntimeError("Window Destroyed"),
+        ReferenceError("weakly-referenced object has been deleted"),
+    )
+
+
+class _SingletonCharacterization:
+    """``show_singleton`` and ``_destroy`` of one singleton settings dialog (P2-1 characterization)."""
+
+    def dialog_class(self):
+        raise NotImplementedError
+
+    def show_kwargs(self) -> dict:
+        raise NotImplementedError
+
+    def expected_init_kwargs(self, kwargs: dict) -> dict:
+        """The keyword arguments ``show_singleton`` passes to the constructor for ``kwargs``."""
+        return kwargs
+
+    def show(self, **overrides):
+        return self.dialog_class().show_singleton(**{**self.show_kwargs(), **overrides})
+
+    def slot(self, value):
+        return patch.object(self.dialog_class(), "_instance", value)
+
+    def recording_constructor(self, events, error=None):
+        dialog_class = self.dialog_class()
+
+        def fake_init(dialog, *args, **kwargs):
+            events.append(("init", args, kwargs))
+            if error is not None:
+                raise error
+
+        def fake_show(dialog):
+            events.append(("Show", dialog_class._instance is dialog))
+
+        return patch.multiple(dialog_class, __init__=fake_init, Show=fake_show)
+
+    def test_show_singleton_builds_forwards_and_shows_a_new_dialog(self) -> None:
+        dialog_class = self.dialog_class()
+        events = []
+        with self.slot(None), self.recording_constructor(events):
+            result = self.show()
+            self.assertIs(dialog_class._instance, result)
+
+        self.assertIs(type(result), dialog_class)
+        kwargs = self.show_kwargs()
+        parent = kwargs.pop("parent")
+        self.assertEqual(events, [("init", (parent,), self.expected_init_kwargs(kwargs)), ("Show", True)])
+
+    def test_show_singleton_raises_the_live_dialog_in_order(self) -> None:
+        existing = Mock()
+        events = []
+        with self.slot(existing), self.recording_constructor(events):
+            result = self.show()
+            self.assertIs(self.dialog_class()._instance, existing)
+
+        self.assertIs(result, existing)
+        self.assertEqual(existing.mock_calls, [call.Iconize(False), call.Raise(), call.SetFocus()])
+        self.assertEqual(events, [])
+
+    def test_show_singleton_rebuilds_after_a_dead_window_error(self) -> None:
+        dialog_class = self.dialog_class()
+        for error in dead_window_errors():
+            with self.subTest(error=repr(error)):
+                existing = Mock()
+                existing.Iconize.side_effect = error
+                events = []
+                with self.slot(existing), self.recording_constructor(events):
+                    result = self.show()
+                    self.assertIs(dialog_class._instance, result)
+
+                self.assertIsNot(result, existing)
+                self.assertEqual(existing.mock_calls, [call.Iconize(False)])
+                self.assertEqual([event[0] for event in events], ["init", "Show"])
+
+    def test_show_singleton_reraises_a_live_window_error_and_keeps_the_slot(self) -> None:
+        dialog_class = self.dialog_class()
+        for error in (ReferenceError("weakly-referenced object no longer exists"), RuntimeError("unexpected")):
+            with self.subTest(error=repr(error)):
+                existing = Mock()
+                existing.Iconize.side_effect = error
+                events = []
+                with self.slot(existing), self.recording_constructor(events):
+                    with self.assertRaises(type(error)) as caught:
+                        self.show()
+                    self.assertIs(dialog_class._instance, existing)
+
+                self.assertIs(caught.exception, error)
+                self.assertEqual(events, [])
+
+    def test_show_singleton_propagates_other_exceptions_and_keeps_the_slot(self) -> None:
+        dialog_class = self.dialog_class()
+        existing = Mock()
+        existing.Raise.side_effect = KeyError("boom")
+        events = []
+        with self.slot(existing), self.recording_constructor(events):
+            with self.assertRaises(KeyError):
+                self.show()
+            self.assertIs(dialog_class._instance, existing)
+
+        self.assertEqual(existing.mock_calls, [call.Iconize(False), call.Raise()])
+        self.assertEqual(events, [])
+
+    def test_constructor_failure_leaves_the_slot_empty(self) -> None:
+        dialog_class = self.dialog_class()
+        events = []
+        with self.slot(None), self.recording_constructor(events, error=OSError("unreadable")):
+            with self.assertRaises(OSError):
+                self.show()
+            self.assertIsNone(dialog_class._instance)
+
+        self.assertEqual([event[0] for event in events], ["init"])
+
+    def test_destroy_clears_its_own_slot_and_destroys(self) -> None:
+        dialog_class = self.dialog_class()
+        dialog = object.__new__(dialog_class)
+        dialog.Destroy = Mock()
+        with self.slot(dialog):
+            dialog._destroy()
+            self.assertIsNone(dialog_class._instance)
+
+        dialog.Destroy.assert_called_once_with()
+
+    def test_destroy_keeps_another_dialog_in_the_slot(self) -> None:
+        dialog_class = self.dialog_class()
+        dialog = object.__new__(dialog_class)
+        dialog.Destroy = Mock()
+        other = Mock()
+        with self.slot(other):
+            dialog._destroy()
+            self.assertIs(dialog_class._instance, other)
+
+        dialog.Destroy.assert_called_once_with()
+        self.assertEqual(other.mock_calls, [])
+
+
+class TextProcessingSingletonTest(_SingletonCharacterization, unittest.TestCase):
+    def dialog_class(self):
+        from settings.dialogs import TextProcessingDialog
+
+        return TextProcessingDialog
+
+    def show_kwargs(self) -> dict:
+        return {"parent": "parent-window", "script_path": "dictionary/preprocessing.py"}
+
+
+class DotExpressSettingsSingletonTest(_SingletonCharacterization, unittest.TestCase):
+    def setUp(self) -> None:
+        self.snapshot = make_snapshot()
+        self.commit = Mock()
+
+    def dialog_class(self):
+        from settings.dialogs import DotExpressSettingsDialog
+
+        return DotExpressSettingsDialog
+
+    def show_kwargs(self) -> dict:
+        return {
+            "parent": "parent-window",
+            "snapshot": self.snapshot,
+            "dictionary_names": ["default", "math"],
+            "commit": self.commit,
+        }
+
+    def expected_init_kwargs(self, kwargs: dict) -> dict:
+        return {**kwargs, "initial_category": None}
+
+    def test_show_singleton_forwards_the_initial_category_to_a_new_dialog(self) -> None:
+        dialog_class = self.dialog_class()
+        category = dialog_class.category_classes[1]
+        events = []
+        with self.slot(None), self.recording_constructor(events):
+            self.show(initial_category=category)
+
+        kwargs = self.show_kwargs()
+        parent = kwargs.pop("parent")
+        self.assertEqual(events, [("init", (parent,), {**kwargs, "initial_category": category}), ("Show", True)])
+
+    def test_show_singleton_selects_the_initial_category_before_raising(self) -> None:
+        category = self.dialog_class().category_classes[2]
+        existing = Mock()
+        with self.slot(existing):
+            result = self.show(initial_category=category)
+
+        self.assertIs(result, existing)
+        self.assertEqual(
+            existing.mock_calls,
+            [call.Iconize(False), call.select_category(category), call.Raise(), call.SetFocus()],
+        )
+
+    def test_show_singleton_rejects_an_unregistered_category_before_reading_the_slot(self) -> None:
+        dialog_class = self.dialog_class()
+        existing = Mock()
+        events = []
+        with self.slot(existing), self.recording_constructor(events):
+            with self.assertRaisesRegex(ValueError, "^initial_category is not registered$"):
+                self.show(initial_category=object())
+            self.assertIs(dialog_class._instance, existing)
+
+        self.assertEqual(existing.mock_calls, [])
+        self.assertEqual(events, [])
+
+
+class SingletonSlotIndependenceTest(unittest.TestCase):
+    def test_the_two_singleton_dialogs_keep_separate_slots(self) -> None:
+        from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog
+
+        text_dialog = Mock()
+        settings_dialog = object.__new__(DotExpressSettingsDialog)
+        settings_dialog.Destroy = Mock()
+        with (
+            patch.object(TextProcessingDialog, "_instance", text_dialog),
+            patch.object(DotExpressSettingsDialog, "_instance", settings_dialog),
+        ):
+            self.assertIs(
+                TextProcessingDialog.show_singleton(parent=None, script_path="dictionary/preprocessing.py"),
+                text_dialog,
+            )
+            settings_dialog._destroy()
+            self.assertIsNone(DotExpressSettingsDialog._instance)
+            self.assertIs(TextProcessingDialog._instance, text_dialog)
+
+        settings_dialog.Destroy.assert_called_once_with()
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
```

- [ ] **Step 4: Pin `ConvertingDialog` (A.4).** Loaded from `gui` with the gui-frame stubs, the same scope as `test_gui_document_flows` (refinement 3). The fake flag values make the style expression observable: `(0b0111 & ~0b0010) | 0b1000 == 0b1101`.

```bash
cat > tests/test_converting_dialog.py <<'EOF'
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch, sentinel

from tests import wx_stub

# The module that defines ConvertingDialog, loaded against stub wx.
_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view"),
)
with _SCOPE.loading():
    defining_module = importlib.import_module("gui")

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

FAKE_WX = SimpleNamespace(
    DEFAULT_DIALOG_STYLE=0b0111,
    CLOSE_BOX=0b0010,
    STAY_ON_TOP=0b1000,
    VERTICAL=0b0100,
    ALL=0b0001_0000,
    ALIGN_CENTER_HORIZONTAL=0b0010_0000,
    EVT_CLOSE=sentinel.EVT_CLOSE,
)


class ConvertingDialogTest(unittest.TestCase):
    def build(self, parent):
        """Run the real ``ConvertingDialog.__init__`` with recording wx calls; return the records."""
        dialog_class = defining_module.ConvertingDialog
        wx_namespace = SimpleNamespace(
            **vars(FAKE_WX),
            StaticText=Mock(return_value=sentinel.message),
            BoxSizer=Mock(return_value=Mock(name="sizer")),
        )
        dialog_init = Mock(return_value=None)
        dialog = object.__new__(dialog_class)
        dialog.Bind = Mock()
        with (
            patch.object(defining_module.wx.Dialog, "__init__", dialog_init),
            patch.object(defining_module, "wx", wx_namespace),
            patch.object(defining_module, "finalize_dialog_layout") as finalize,
        ):
            dialog_class.__init__(dialog, parent)
        return dialog, dialog_init, wx_namespace, finalize

    def test_builds_a_closeless_stay_on_top_info_dialog_with_the_converting_label(self) -> None:
        dialog, dialog_init, wx_namespace, finalize = self.build(sentinel.parent)

        dialog_init.assert_called_once_with(sentinel.parent, title="資訊", style=0b1101)
        wx_namespace.StaticText.assert_called_once_with(dialog, label="轉換中")
        wx_namespace.BoxSizer.assert_called_once_with(0b0100)
        sizer = wx_namespace.BoxSizer.return_value
        sizer.Add.assert_called_once_with(sentinel.message, 0, 0b0011_0000, 20)
        finalize.assert_called_once_with(dialog, sizer)
        dialog.Bind.assert_called_once_with(sentinel.EVT_CLOSE, dialog._on_close)

    def test_close_is_vetoed_when_it_can_be(self) -> None:
        dialog = object.__new__(defining_module.ConvertingDialog)
        event = Mock()
        event.CanVeto.return_value = True

        dialog._on_close(event)

        event.Veto.assert_called_once_with()

    def test_close_is_not_vetoed_when_it_cannot_be(self) -> None:
        dialog = object.__new__(defining_module.ConvertingDialog)
        event = Mock()
        event.CanVeto.return_value = False

        dialog._on_close(event)

        event.Veto.assert_not_called()
        self.assertEqual(event.mock_calls, [call.CanVeto()])


if __name__ == "__main__":
    unittest.main()
EOF
```

- [ ] **Step 5: Run the new tests on the unchanged code.** Characterization passes by construction.

```bash
$PY -m unittest tests.test_name_validation tests.test_dialog_validation tests.test_settings_dialogs tests.test_converting_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (9 + 19 + 47 + 3):

```text
Ran 78 tests
OK
```

- [ ] **Step 6: Show that the net can fail.** Each mutant edits one file of a copy of `client/`; the repo stays unchanged.

```bash
$PY -B $T/tools/dialog_mutants.py $REPO/client $T/mutants
git -C $REPO status --short
```

Expected (every mutant fails or errors at least one test; `status` lists only the four new or changed test files):

```text
dictionary-reserved-message-lost: failures=6 errors=0
too-long-reported-as-invalid: failures=10 errors=0
document-on-ok-keeps-raw-text: failures=3 errors=0
dictionary-on-ok-focus-before-message: failures=5 errors=0
exit-swallows-exceptions: failures=2 errors=0
trailing-period-accepted-by-normalizer: failures=8 errors=0
destroyed-phrase-not-dead: failures=0 errors=1
text-processing-shows-before-slot: failures=1 errors=0
settings-category-selected-after-raise: failures=1 errors=0
settings-category-check-dropped: failures=1 errors=0
text-processing-destroy-clears-any-slot: failures=1 errors=0
converting-dialog-always-vetoes: failures=1 errors=0
converting-dialog-keeps-close-box: failures=1 errors=0
 M client/tests/test_dialog_validation.py
 M client/tests/test_settings_dialogs.py
?? client/tests/test_converting_dialog.py
?? client/tests/test_name_validation.py
```

- [ ] **Step 7: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (818 + 43):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 861 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 8: Commit.**

```bash
git -C $REPO add client/tests/test_name_validation.py client/tests/test_dialog_validation.py client/tests/test_settings_dialogs.py client/tests/test_converting_dialog.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize dialog lifecycle, name validation and singletons

Pin the behavior that P2-1 refactors before touching production code:
normalize_base_name messages and order, both name dialogs against a
frozen copy of _normalize_dialog_name on 3,431 generated names, the
exact _on_ok call sequence, the with-statement contract of the seven
context-managed dialogs, show_singleton/_destroy of both settings
dialogs, and the ConvertingDialog construction and close veto.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize dialog lifecycle, name validation and singletons
```

---

### Task 2: Raise a typed `NameValidationError` (spec part B)

- [ ] **Step 1: Write the failing tests.** `NameValidationErrorTest` (each check's code, type, message and `args`; the class is a `ValueError` that keeps its message), `test_normalize_dictionary_name_raises_typed_errors`, `test_normalize_document_name_raises_typed_errors` and `test_importer_source_name_raises_typed_errors_with_the_english_message`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_dictionary_manager.py b/client/tests/test_dictionary_manager.py
index 79b7ccf..3694bac 100644
--- a/client/tests/test_dictionary_manager.py
+++ b/client/tests/test_dictionary_manager.py
@@ -3,6 +3,7 @@ import tempfile
 import unittest
 from pathlib import Path
 
+from shared import name_validation
 from dictionaries.manager import (
     DEFAULT_DICTIONARY_NAME,
     DEFAULT_HEADER,
@@ -87,6 +88,14 @@ class DictionaryManagerTest(unittest.TestCase):
     def test_normalize_dictionary_name_accepts_32_characters(self) -> None:
         self.assertEqual(normalize_dictionary_name("a" * 32), "a" * 32)
 
+    def test_normalize_dictionary_name_raises_typed_errors(self) -> None:
+        cases = (("", "empty"), ("CON", "invalid"), ("name.", "invalid"), ("a" * 33, "too_long"), (" Default", "reserved"))
+        for value, code in cases:
+            with self.subTest(value=value):
+                with self.assertRaises(name_validation.NameValidationError) as caught:
+                    normalize_dictionary_name(value)
+                self.assertEqual(caught.exception.code, code)
+
     def test_export_dictionary_copies_selected_dictionary_to_destination(self) -> None:
         source_path = create_dictionary(self.dictionary_dir, "math")
         with source_path.open("a", newline="", encoding="utf-8") as f:
diff --git a/client/tests/test_document_workspace.py b/client/tests/test_document_workspace.py
index 91b43ad..5dde7b5 100644
--- a/client/tests/test_document_workspace.py
+++ b/client/tests/test_document_workspace.py
@@ -3,6 +3,7 @@ import unittest
 from pathlib import Path
 
 import documents.workspace as workspace
+from documents.importers.base import source_name
 from documents.workspace import (
     BatchIssue,
     Document,
@@ -15,6 +16,7 @@ from documents.workspace import (
     prepare_document_for_save,
     save_document_package,
 )
+from shared import name_validation
 
 
 class DocumentWorkspaceTest(unittest.TestCase):
@@ -71,6 +73,27 @@ class DocumentWorkspaceTest(unittest.TestCase):
     def test_normalize_document_name_accepts_32_characters(self) -> None:
         self.assertEqual(normalize_document_name("a" * 32), "a" * 32)
 
+    def test_normalize_document_name_raises_typed_errors(self) -> None:
+        cases = (("", "empty"), ("a?b", "invalid"), ("name ", "invalid"), ("a" * 33, "too_long"))
+        for value, code in cases:
+            with self.subTest(value=value):
+                with self.assertRaises(name_validation.NameValidationError) as caught:
+                    normalize_document_name(value)
+                self.assertEqual(caught.exception.code, code)
+
+    def test_importer_source_name_raises_typed_errors_with_the_english_message(self) -> None:
+        cases = (
+            ("CON.docx", "invalid", "Name contains invalid characters."),
+            ("name..docx", "invalid", "Name cannot end with a period or space."),
+            ("a" * 33 + ".docx", "too_long", "Name cannot exceed 32 characters."),
+        )
+        for file_name, code, message in cases:
+            with self.subTest(file_name=file_name):
+                with self.assertRaises(name_validation.NameValidationError) as caught:
+                    source_name(Path(file_name))
+                self.assertEqual(caught.exception.code, code)
+                self.assertEqual(str(caught.exception), message)
+
     def test_save_and_load_document_package_roundtrip(self) -> None:
         document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
         package_path = self.workspace_dir / "lesson1.dep"
diff --git a/client/tests/test_name_validation.py b/client/tests/test_name_validation.py
index d59e7d5..9a71aa4 100644
--- a/client/tests/test_name_validation.py
+++ b/client/tests/test_name_validation.py
@@ -1,5 +1,6 @@
 import unittest
 
+from shared import name_validation
 from shared.name_validation import normalize_base_name
 
 EMPTY = "Name cannot be empty."
@@ -87,5 +88,37 @@ class NormalizeBaseNameTest(unittest.TestCase):
                 self.assertEqual(error.args, (message,))
 
 
+class NameValidationErrorTest(unittest.TestCase):
+    def test_each_check_raises_a_name_validation_error_with_its_code(self) -> None:
+        cases = (
+            ("", "empty", EMPTY),
+            (" \t ", "empty", EMPTY),
+            ("a\tb", "invalid", INVALID),
+            ("name.", "invalid", TRAILING),
+            ("name ", "invalid", TRAILING),
+            ("a" * 33, "too_long", TOO_LONG),
+            ("a?b", "invalid", INVALID),
+            ("CON", "invalid", INVALID),
+            ("\u3000..\u3000", "invalid", INVALID),
+            (" Default", "reserved", "Name 'Default' is reserved."),
+        )
+        for name, code, message in cases:
+            with self.subTest(name=name):
+                with self.assertRaises(name_validation.NameValidationError) as caught:
+                    normalize_base_name(name, reserved_names={"default"})
+                self.assertIs(type(caught.exception), name_validation.NameValidationError)
+                self.assertEqual(caught.exception.code, code)
+                self.assertEqual(str(caught.exception), message)
+                self.assertEqual(caught.exception.args, (message,))
+
+    def test_name_validation_error_is_a_value_error_that_keeps_its_message(self) -> None:
+        error = name_validation.NameValidationError("too_long", "Name cannot exceed 32 characters.")
+
+        self.assertIsInstance(error, ValueError)
+        self.assertEqual(error.code, "too_long")
+        self.assertEqual(error.args, ("Name cannot exceed 32 characters.",))
+        self.assertEqual(str(error), "Name cannot exceed 32 characters.")
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_name_validation tests.test_dictionary_manager tests.test_document_workspace > $T/task2_red.txt 2>&1
grep -E '^(FAIL|ERROR):' $T/task2_red.txt | sed -E 's/ \(.*//' | sort | uniq -c
grep -E 'Error:' $T/task2_red.txt | sort | uniq -c
grep -E '^Ran|^OK|^FAILED' $T/task2_red.txt | sed -E 's/ in [0-9.]+s$//'
```

Expected (the 5 new tests error, counted per failing subtest, all for the missing class; the other 40 tests in the three modules pass):

```text
     10 ERROR: test_each_check_raises_a_name_validation_error_with_its_code
      3 ERROR: test_importer_source_name_raises_typed_errors_with_the_english_message
      1 ERROR: test_name_validation_error_is_a_value_error_that_keeps_its_message
      5 ERROR: test_normalize_dictionary_name_raises_typed_errors
      4 ERROR: test_normalize_document_name_raises_typed_errors
     23 AttributeError: module 'shared.name_validation' has no attribute 'NameValidationError'
Ran 45 tests
FAILED (errors=23)
```

- [ ] **Step 3: Add the error class and raise it.** Same checks, same order, same messages; only the exception type and the code are new.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/shared/name_validation.py b/client/shared/name_validation.py
index 4bd29d6..da2e842 100644
--- a/client/shared/name_validation.py
+++ b/client/shared/name_validation.py
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from typing import Literal
+
 MAX_NAME_LENGTH = 32
 WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')
 WINDOWS_RESERVED_DEVICE_NAMES = {
@@ -28,6 +30,16 @@ WINDOWS_RESERVED_DEVICE_NAMES = {
 }
 WINDOWS_RESERVED_DEVICE_NAMES_CASEFOLDED = {name.casefold() for name in WINDOWS_RESERVED_DEVICE_NAMES}
 
+NameValidationCode = Literal["empty", "invalid", "too_long", "reserved"]
+
+
+class NameValidationError(ValueError):
+    """``normalize_base_name`` rejected a name: ``code`` says why, ``str(error)`` is the English message."""
+
+    def __init__(self, code: NameValidationCode, message: str) -> None:
+        super().__init__(message)
+        self.code = code
+
 
 def _is_windows_reserved_device_name(name: str) -> bool:
     root_name = name.split(".", 1)[0]
@@ -50,16 +62,16 @@ def _is_windows_legal_name(name: str) -> bool:
 
 def normalize_base_name(name: str, *, reserved_names: set[str] | None = None) -> str:
     if not name or not name.strip():
-        raise ValueError("Name cannot be empty.")
+        raise NameValidationError("empty", "Name cannot be empty.")
     if any(ord(char) < 32 for char in name):
-        raise ValueError("Name contains invalid characters.")
+        raise NameValidationError("invalid", "Name contains invalid characters.")
     if name.endswith((" ", ".")):
-        raise ValueError("Name cannot end with a period or space.")
+        raise NameValidationError("invalid", "Name cannot end with a period or space.")
     normalized = name.strip()
     if len(normalized) > MAX_NAME_LENGTH:
-        raise ValueError(f"Name cannot exceed {MAX_NAME_LENGTH} characters.")
+        raise NameValidationError("too_long", f"Name cannot exceed {MAX_NAME_LENGTH} characters.")
     if not _is_windows_legal_name(normalized):
-        raise ValueError("Name contains invalid characters.")
+        raise NameValidationError("invalid", "Name contains invalid characters.")
     if reserved_names and normalized.casefold() in {reserved.casefold() for reserved in reserved_names}:
-        raise ValueError(f"Name '{normalized}' is reserved.")
+        raise NameValidationError("reserved", f"Name '{normalized}' is reserved.")
     return normalized
EOF
```

- [ ] **Step 4: Focused tests (presenter and dialogs unchanged and green) and full suite.**

```bash
$PY -m unittest tests.test_name_validation tests.test_dictionary_manager tests.test_document_workspace tests.test_dictionary_presenter tests.test_workspace_service tests.test_dialog_validation 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (861 + 5):

```text
Ran 132 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 866 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/shared/name_validation.py client/tests/test_name_validation.py client/tests/test_dictionary_manager.py client/tests/test_document_workspace.py
git -C $REPO commit -q -F - <<'EOF'
refactor: raise typed NameValidationError for invalid names

normalize_base_name now raises NameValidationError, a ValueError with a
code ("empty", "invalid", "too_long" or "reserved") so callers can tell
the reasons apart without matching on the message. The English message
stays the only argument, so str(error), args and every existing
"except ValueError" handler behave exactly as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: raise typed NameValidationError for invalid names
```

---

### Task 3: Add the wx-free dialog base mixins (spec part C)

- [ ] **Step 1: Write the failing tests.** No wx, no stub scope. Every behavior runs with two bases: `PlainDialog` (like the dialog-validation, speech and display stubs) and `MaskingDialog`, a `wx_stub.RecordingWidget` subclass (like the settings stubs, whose `__getattr__` turns missing attributes into no-ops). `ContextManagedDialogTest` (2), `MixinShapeTest` (1: no `__init__`/`__new__`/`__slots__`, plain `type` metaclass, mixin first in the MRO), `NameDialogMessagesTest` (4: real zh_TW messages per code, the missing-reserved and unknown-code fallback, translate-then-format at show time, frozen), `NameDialogBaseTest` (7: typed codes, plain `ValueError` -> invalid, other exceptions propagate, the normalizer sees the raw text, both `_on_ok` orders, abstract hooks), `SingletonDialogMixinTest` (8: empty slot, raise order with and without `prepare`, dead-window rebuild for a custom dead type and the four phrases, re-raise with the slot kept, the phrase table, slot set before `Show`, a subclass without its own slot does not see the parent's dialog, `_destroy` clears only its own class's slot) and the AST import guard (1).

```bash
cat > tests/test_dialog_base.py <<'EOF'
import ast
import dataclasses
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from shared.name_validation import NameValidationError
from tests import wx_stub
from ui import dialog_base
from ui.dialog_base import (
    ContextManagedDialog,
    NameDialogBase,
    NameDialogMessages,
    SingletonDialogMixin,
)

DIALOG_BASE_PATH = Path(__file__).resolve().parents[1] / "ui" / "dialog_base.py"


class PlainDialog:
    """Like the ``wx.Dialog`` of the dialog-validation, speech and display stubs."""


class MaskingDialog(wx_stub.RecordingWidget):
    """Like the ``wx.Dialog`` of the settings stubs: missing attributes become no-ops."""


DIALOG_BASES = (PlainDialog, MaskingDialog)

TEST_MESSAGES = NameDialogMessages(
    empty="P2-1 test: empty",
    too_long="P2-1 test: too long",
    invalid="P2-1 test: invalid",
    reserved="P2-1 test: {name} is reserved",
    reserved_name="default",
)


def name_dialog_class(base, normalizer):
    class FakeNameDialog(NameDialogBase, base):
        normalize_name = staticmethod(normalizer)
        name_messages = TEST_MESSAGES

        def _show_name_error(self, message: str) -> None:
            self.events.append(("error", message))

    return FakeNameDialog


def make_name_dialog(base, normalizer, text: str):
    dialog = name_dialog_class(base, normalizer)()
    dialog.events = []
    dialog.name_ctrl = Mock()
    dialog.name_ctrl.GetValue.return_value = text
    dialog.name_ctrl.SetValue.side_effect = lambda value: dialog.events.append(("SetValue", value))
    dialog.name_ctrl.SetFocus.side_effect = lambda: dialog.events.append(("SetFocus",))
    return dialog


def raising(error):
    def normalizer(name: str) -> str:
        raise error

    return normalizer


def singleton_class(base, dead_types=()):
    class FakeSingleton(SingletonDialogMixin, base):
        _instance = None
        dead_window_error_types = dead_types

    return FakeSingleton


class DeadWindowError(Exception):
    pass


class ContextManagedDialogTest(unittest.TestCase):
    def test_with_returns_the_dialog_and_destroys_it_once(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = type("Combined", (ContextManagedDialog, base), {})()
                dialog.Destroy = Mock()
                with dialog as entered:
                    self.assertIs(entered, dialog)
                    dialog.Destroy.assert_not_called()
                dialog.Destroy.assert_called_once_with()
                self.assertIsNone(dialog.__exit__(None, None, None))

    def test_with_destroys_the_dialog_and_propagates_an_exception(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = type("Combined", (ContextManagedDialog, base), {})()
                dialog.Destroy = Mock()
                error = RuntimeError("boom")
                with self.assertRaises(RuntimeError) as caught:
                    with dialog:
                        raise error
                self.assertIs(caught.exception, error)
                dialog.Destroy.assert_called_once_with()


class MixinShapeTest(unittest.TestCase):
    def test_mixins_have_no_constructor_slots_or_metaclass_and_go_first(self) -> None:
        for mixin in (ContextManagedDialog, NameDialogBase, SingletonDialogMixin):
            with self.subTest(mixin=mixin.__name__):
                self.assertIs(type(mixin), type)
                for name in ("__init__", "__new__", "__slots__"):
                    self.assertNotIn(name, vars(mixin))
                for base in DIALOG_BASES:
                    combined = type("Combined", (mixin, base), {})
                    self.assertEqual(combined.__mro__[1], mixin)
                    self.assertLess(combined.__mro__.index(mixin), combined.__mro__.index(base))


class NameDialogMessagesTest(unittest.TestCase):
    def test_message_for_each_code_is_translated(self) -> None:
        messages = NameDialogMessages(
            empty="Please enter the dictionary name.",
            too_long="Dictionary name must be 1 to 32 characters.",
            invalid="Dictionary name is not a valid Windows file name.",
            reserved='Dictionary name "{name}" is reserved.',
            reserved_name="default",
        )

        self.assertEqual(messages.message_for("empty"), "請輸入字典名稱。")
        self.assertEqual(messages.message_for("too_long"), "字典名稱長度需為 1 到 32 個字元。")
        self.assertEqual(messages.message_for("invalid"), "字典名稱不是有效的 Windows 檔名。")
        self.assertEqual(messages.message_for("reserved"), "字典名稱「default」為保留名稱。")

    def test_reserved_without_a_reserved_message_and_unknown_codes_are_invalid(self) -> None:
        messages = NameDialogMessages(empty="e", too_long="t", invalid="i")

        self.assertIsNone(messages.reserved)
        self.assertEqual(messages.reserved_name, "")
        self.assertEqual(messages.message_for("reserved"), "i")
        self.assertEqual(messages.message_for("something_else"), "i")

    def test_messages_are_translated_when_shown_then_formatted(self) -> None:
        translations = {"P2-1 test: {name} is reserved": "{name} reserved (translated)"}
        with patch.object(dialog_base, "_", side_effect=lambda text: translations.get(text, text.upper())) as translate:
            self.assertEqual(TEST_MESSAGES.message_for("reserved"), "default reserved (translated)")
            self.assertEqual(TEST_MESSAGES.message_for("empty"), "P2-1 TEST: EMPTY")

        self.assertEqual(translate.call_args_list, [call("P2-1 test: {name} is reserved"), call("P2-1 test: empty")])

    def test_messages_are_frozen(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
            TEST_MESSAGES.empty = "changed"


class NameDialogBaseTest(unittest.TestCase):
    def test_validate_name_maps_each_typed_code_to_its_message(self) -> None:
        cases = (
            ("empty", "P2-1 test: empty"),
            ("too_long", "P2-1 test: too long"),
            ("invalid", "P2-1 test: invalid"),
            ("reserved", "P2-1 test: default is reserved"),
        )
        for base in DIALOG_BASES:
            for code, message in cases:
                with self.subTest(base=base.__name__, code=code):
                    dialog = make_name_dialog(base, raising(NameValidationError(code, "English")), "x")
                    self.assertEqual(dialog._validate_name("x"), message)

    def test_a_plain_value_error_is_reported_as_invalid(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(ValueError("Name cannot exceed 32 characters.")), "x")
                self.assertEqual(dialog._validate_name("x"), "P2-1 test: invalid")

    def test_other_exceptions_propagate(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(TypeError("bug")), "x")
                with self.assertRaisesRegex(TypeError, "^bug$"):
                    dialog._validate_name("x")

    def test_a_valid_name_has_no_message_and_the_normalizer_sees_the_raw_text(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                seen = []

                def normalizer(name: str) -> str:
                    seen.append(name)
                    return name.strip()

                dialog = make_name_dialog(base, normalizer, " name　")
                self.assertIsNone(dialog._validate_name(" name　"))
                self.assertEqual(seen, [" name　"])

    def test_on_ok_shows_the_error_then_focuses_and_does_not_skip(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(NameValidationError("empty", "English")), "")
                event = Mock()
                dialog._on_ok(event)
                self.assertEqual(dialog.events, [("error", "P2-1 test: empty"), ("SetFocus",)])
                event.Skip.assert_not_called()

    def test_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, str.strip, " name ")
                event = Mock()
                event.Skip.side_effect = lambda: dialog.events.append(("Skip",))
                dialog._on_ok(event)
                self.assertEqual(dialog.events, [("SetValue", "name"), ("Skip",)])

    def test_hooks_must_be_provided_by_the_subclass(self) -> None:
        with self.assertRaises(NotImplementedError):
            NameDialogBase.normalize_name("name")
        with self.assertRaises(NotImplementedError):
            NameDialogBase._show_name_error(object(), "message")


class SingletonDialogMixinTest(unittest.TestCase):
    def test_raise_existing_returns_none_for_an_empty_slot(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                self.assertIsNone(singleton_class(base)._raise_existing())

    def test_raise_existing_raises_the_open_dialog_in_order(self) -> None:
        for base in DIALOG_BASES:
            for prepare, expected in (
                (None, [call.Iconize(False), call.Raise(), call.SetFocus()]),
                (lambda dialog: dialog.prepare(), [call.Iconize(False), call.prepare(), call.Raise(), call.SetFocus()]),
            ):
                with self.subTest(base=base.__name__, prepare=prepare is not None):
                    dialog_class = singleton_class(base)
                    existing = Mock()
                    dialog_class._instance = existing
                    self.assertIs(dialog_class._raise_existing(prepare), existing)
                    self.assertIs(dialog_class._instance, existing)
                    self.assertEqual(existing.mock_calls, expected)

    def test_raise_existing_clears_the_slot_after_a_dead_window_error(self) -> None:
        errors = (
            DeadWindowError("no phrase needed"),
            RuntimeError("WRAPPED C/C++ OBJECT of type Dialog"),
            RuntimeError("window has been deleted"),
            ReferenceError("already deleted"),
            RuntimeError("destroyed"),
        )
        for base in DIALOG_BASES:
            for error in errors:
                with self.subTest(base=base.__name__, error=repr(error)):
                    dialog_class = singleton_class(base, (DeadWindowError,))
                    existing = Mock()
                    existing.Raise.side_effect = error
                    dialog_class._instance = existing
                    self.assertIsNone(dialog_class._raise_existing())
                    self.assertIsNone(dialog_class._instance)

    def test_raise_existing_reraises_other_errors_and_keeps_the_slot(self) -> None:
        errors = (
            RuntimeError("unexpected"),
            ReferenceError("weakly-referenced object no longer exists"),
            DeadWindowError("not registered as dead"),
            KeyError("other"),
        )
        for base in DIALOG_BASES:
            for error in errors:
                with self.subTest(base=base.__name__, error=repr(error)):
                    dialog_class = singleton_class(base)
                    existing = Mock()
                    existing.Iconize.side_effect = error
                    dialog_class._instance = existing
                    with self.assertRaises(type(error)) as caught:
                        dialog_class._raise_existing()
                    self.assertIs(caught.exception, error)
                    self.assertIs(dialog_class._instance, existing)

    def test_is_destroyed_window_error(self) -> None:
        dialog_class = singleton_class(PlainDialog, (DeadWindowError,))
        cases = (
            (DeadWindowError(), True),
            (RuntimeError("Has Been Deleted"), True),
            (ReferenceError("wrapped C/C++ object"), True),
            (RuntimeError("other"), False),
            (ReferenceError(""), False),
            (ValueError("destroyed"), False),
        )
        for error, expected in cases:
            with self.subTest(error=repr(error)):
                self.assertIs(dialog_class._is_destroyed_window_error(error), expected)

    def test_show_new_sets_the_slot_before_showing(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog_class = singleton_class(base)
                dialog = dialog_class()
                shown = []
                dialog.Show = lambda: shown.append(dialog_class.__dict__["_instance"] is dialog)
                self.assertIs(dialog_class._show_new(dialog), dialog)
                self.assertIs(dialog_class._instance, dialog)
                self.assertEqual(shown, [True])

    def test_a_subclass_without_its_own_slot_does_not_see_the_parent_dialog(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                parent_class = singleton_class(base)
                existing = Mock()
                parent_class._instance = existing
                child_class = type("Child", (parent_class,), {})

                self.assertIsNone(child_class._raise_existing())
                self.assertEqual(existing.mock_calls, [])
                child = child_class()
                child.Show = Mock()
                child_class._show_new(child)
                self.assertIs(child_class.__dict__["_instance"], child)
                self.assertIs(parent_class._instance, existing)

    def test_destroy_clears_only_its_own_class_slot(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                parent_class = singleton_class(base)
                child_class = type("Child", (parent_class,), {"_instance": None})
                parent_dialog = parent_class()
                parent_dialog.Destroy = Mock()
                child = child_class()
                child.Destroy = Mock()
                parent_class._instance = parent_dialog
                child_class._instance = child

                child._destroy()
                self.assertIsNone(child_class._instance)
                self.assertIs(parent_class._instance, parent_dialog)
                child.Destroy.assert_called_once_with()

                other = child_class()
                other.Destroy = Mock()
                child_class._instance = child
                other._destroy()
                self.assertIs(child_class._instance, child)
                other.Destroy.assert_called_once_with()
                parent_dialog.Destroy.assert_not_called()


class DialogBaseImportTest(unittest.TestCase):
    def test_module_imports_only_the_standard_library_i18n_and_name_validation(self) -> None:
        tree = ast.parse(DIALOG_BASE_PATH.read_text(encoding="utf-8"), filename=str(DIALOG_BASE_PATH))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add("." * node.level + (node.module or ""))

        self.assertEqual(imported, {"__future__", "dataclasses", "typing", "i18n", "shared.name_validation"})
        self.assertEqual({name.split(".")[0] for name in imported} & {"wx", "gui", "dialog", "settings"}, set())


if __name__ == "__main__":
    unittest.main()
EOF
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_dialog_base 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the module does not exist yet):

```text
ERROR: test_dialog_base (unittest.loader._FailedTest.test_dialog_base)
ImportError: Failed to import test module: test_dialog_base
ImportError: cannot import name 'dialog_base' from 'ui' (client/ui/__init__.py)
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Add `client/ui/dialog_base.py`.** The spec's code with the docstrings of refinement 8. Not used by production code yet.

```bash
cat > ui/dialog_base.py <<'EOF'
"""wx-free mixins shared by the wx dialogs in ``dialog.py`` and ``settings/dialogs.py``.

The mixins define no ``__init__``, ``__new__``, ``__slots__`` or metaclass and go
first in the base list (``class X(Mixin, wx.Dialog)``), so they combine with the
sip classes of real wxPython and with every test stub. Nothing here imports wx:
the one wx call (the name-error message box) is the ``_show_name_error`` hook and
the one wx value (the dead-window exception type) is ``dead_window_error_types``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from i18n import _
from shared.name_validation import NameValidationError

_DialogT = TypeVar("_DialogT")


class ContextManagedDialog:
    """``with Dialog(...) as dialog:`` destroys the dialog on exit and never swallows an exception."""

    def __enter__(self: _DialogT) -> _DialogT:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.Destroy()


@dataclass(frozen=True)
class NameDialogMessages:
    """Untranslated msgids (marked with ``N_`` where defined); translated when shown."""

    empty: str
    too_long: str
    invalid: str
    reserved: str | None = None
    reserved_name: str = ""

    def message_for(self, code: str) -> str:
        """The translated message for a ``NameValidationError`` code; ``reserved`` may use ``{name}``."""
        if code == "empty":
            return _(self.empty)
        if code == "too_long":
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=self.reserved_name)
        return _(self.invalid)


class NameDialogBase(ContextManagedDialog):
    """``_on_ok``/``_validate_name`` of a dialog with a ``name_ctrl`` text box.

    Subclasses set ``normalize_name`` (a staticmethod) and ``name_messages`` and implement
    ``_show_name_error``.
    """

    name_messages: ClassVar[NameDialogMessages]

    @staticmethod
    def normalize_name(name: str) -> str:
        raise NotImplementedError

    def _check_name(self, candidate: str) -> tuple[str | None, str | None]:
        try:
            return self.normalize_name(candidate), None
        except NameValidationError as error:
            code = error.code
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code)

    def _validate_name(self, candidate: str) -> str | None:
        return self._check_name(candidate)[1]

    def _on_ok(self, event) -> None:
        normalized, message = self._check_name(self.name_ctrl.GetValue())
        if message:
            self._show_name_error(message)
            self.name_ctrl.SetFocus()
            return
        self.name_ctrl.SetValue(normalized)
        event.Skip()

    def _show_name_error(self, message: str) -> None:
        raise NotImplementedError


class SingletonDialogMixin:
    """At most one open dialog per class; ``show_singleton`` raises it or builds a new one.

    The open dialog lives in the class's own ``_instance`` (read through ``cls.__dict__``,
    so a subclass never sees its parent's dialog).
    """

    dead_window_error_types: ClassVar[tuple[type[BaseException], ...]] = ()

    @classmethod
    def _raise_existing(cls, prepare=None):
        """Raise and return the open dialog; ``None`` when there is none or it was destroyed."""
        instance = cls.__dict__.get("_instance")
        if instance is None:
            return None
        try:
            instance.Iconize(False)
            if prepare is not None:
                prepare(instance)
            instance.Raise()
            instance.SetFocus()
            return instance
        except (ReferenceError, RuntimeError, *cls.dead_window_error_types) as error:
            if not cls._is_destroyed_window_error(error):
                raise
            cls._instance = None
            return None

    @classmethod
    def _show_new(cls, instance):
        cls._instance = instance
        instance.Show()
        return instance

    def _destroy(self) -> None:
        owner = type(self)
        if owner.__dict__.get("_instance") is self:
            owner._instance = None
        self.Destroy()

    @classmethod
    def _is_destroyed_window_error(cls, error: BaseException) -> bool:
        if isinstance(error, cls.dead_window_error_types):
            return True
        if not isinstance(error, (ReferenceError, RuntimeError)):
            return False
        message = str(error).lower()
        return (
            "wrapped c/c++ object" in message
            or "has been deleted" in message
            or "already deleted" in message
            or "destroyed" in message
        )
EOF
```

- [ ] **Step 4: Run the new tests and the full suite.**

```bash
$PY -m unittest tests.test_dialog_base 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (866 + 23):

```text
Ran 23 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/ui/dialog_base.py client/tests/test_dialog_base.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add wx-free dialog base mixins

Add ui/dialog_base.py with ContextManagedDialog (with-statement that
destroys the dialog), NameDialogBase plus NameDialogMessages (the shared
_on_ok/_validate_name of the name dialogs, mapping NameValidationError
codes to messages) and SingletonDialogMixin (one open dialog per class).
The mixins import no wx and define no constructor, so they combine with
real wx classes and with every test stub. Not used yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add wx-free dialog base mixins
```

---

### Task 4: Use the mixins in `dialog.py` (spec step 4)

No new tests: the Task 1 and Task 2 tests must stay green unchanged.

- [ ] **Step 1: Show what goes.** The acceptance grep (AC4, `dialog.py` part) on the current code.

```bash
grep -n "def __enter__\|def __exit__\|_normalize_dialog_name\|\"exceed\"" dialog.py
```

Expected (seven pairs, the helper, its four calls and the string guess):

```text
62:def _normalize_dialog_name(
84:		if "exceed" in str(exc):
185:	def __enter__(self) -> "AddSymbolDialog":
188:	def __exit__(self, exc_type, exc, _tb) -> None:
227:		normalized_candidate, message = _normalize_dialog_name(
243:		_normalized, message = _normalize_dialog_name(
253:	def __enter__(self) -> "DictionaryNameDialog":
256:	def __exit__(self, exc_type, exc, _tb) -> None:
292:		normalized_candidate, message = _normalize_dialog_name(
307:		_normalized, message = _normalize_dialog_name(
316:	def __enter__(self) -> "DocumentNameDialog":
319:	def __exit__(self, exc_type, exc, _tb) -> None:
356:	def __enter__(self) -> "InvalidWorkspaceFilesDialog":
359:	def __exit__(self, exc_type, exc, _tb) -> None:
378:	def __enter__(self) -> "FileIssuesDialog":
381:	def __exit__(self, exc_type, exc, _tb) -> None:
417:	def __enter__(self) -> "SpeechSymbolsDialog":
420:	def __exit__(self, exc_type, exc, _tb) -> None:
870:	def __enter__(self) -> "DictionaryManagementDialog":
873:	def __exit__(self, exc_type, exc, _tb) -> None:
```

- [ ] **Step 2: Migrate.** The five plain dialogs become `class X(ContextManagedDialog, wx.Dialog)` and lose their pairs. The private `_NameDialog(NameDialogBase, wx.Dialog)` implements `_show_name_error` with the same `wx.MessageBox` call. `DictionaryNameDialog` and `DocumentNameDialog` derive from it, declare `normalize_name` and `name_messages` (the seven msgids now marked with `N_` and translated when shown) and lose `_on_ok`, `_validate_name`, `__enter__` and `__exit__`. `_normalize_dialog_name` and the `MAX_DICTIONARY_NAME_LENGTH` import go. Tabs.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/dialog.py b/client/dialog.py
index ae59b0c..d2ebd26 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -18,12 +18,12 @@ from dictionaries.entries import (
 )
 from dictionaries.manager import (
 	DEFAULT_DICTIONARY_NAME,
-	MAX_DICTIONARY_NAME_LENGTH,
 	normalize_dictionary_name,
 )
 from dictionaries.presenter import DictionaryManagementActions
 from documents.workspace import normalize_document_name
 from i18n import N_, _
+from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
 
 CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")
 
@@ -59,34 +59,7 @@ def localize_standard_buttons(
 				button.SetLabel(label)
 
 
-def _normalize_dialog_name(
-	candidate: str,
-	normalizer: Callable[[str], str],
-	empty_message: str,
-	length_message: str,
-	invalid_message: str,
-	reserved_message: str | None = None,
-) -> tuple[str | None, str | None]:
-	if not candidate or not candidate.strip():
-		return None, empty_message
-	if any(ord(char) < 32 for char in candidate):
-		return None, invalid_message
-	if candidate.endswith((" ", ".")):
-		return None, invalid_message
-	normalized_candidate = candidate.strip()
-	if len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:
-		return None, length_message
-	try:
-		return normalizer(normalized_candidate), None
-	except ValueError as exc:
-		if reserved_message and normalized_candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
-			return None, reserved_message
-		if "exceed" in str(exc):
-			return None, length_message
-		return None, invalid_message
-
-
-class AddSymbolDialog(wx.Dialog):
+class AddSymbolDialog(ContextManagedDialog, wx.Dialog):
 	"""Dialog to create or edit a dictionary entry."""
 
 	def __init__(self, parent: wx.Window | None, entry: DictionaryEntry | None = None):
@@ -182,16 +155,26 @@ class AddSymbolDialog(wx.Dialog):
 
 		event.Skip()
 
-	def __enter__(self) -> "AddSymbolDialog":
-		return self
 
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
+class _NameDialog(NameDialogBase, wx.Dialog):
+	"""Name dialog base: shows a name error in an information message box."""
+
+	def _show_name_error(self, message: str) -> None:
+		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
 
 
-class DictionaryNameDialog(wx.Dialog):
+class DictionaryNameDialog(_NameDialog):
 	"""Dialog for creating a new dictionary file name."""
 
+	normalize_name = staticmethod(normalize_dictionary_name)
+	name_messages = NameDialogMessages(
+		empty=N_("Please enter the dictionary name."),
+		too_long=N_("Dictionary name must be 1 to 32 characters."),
+		invalid=N_("Dictionary name is not a valid Windows file name."),
+		reserved=N_('Dictionary name "{name}" is reserved.'),
+		reserved_name=DEFAULT_DICTIONARY_NAME,
+	)
+
 	def __init__(self, parent: wx.Window | None, initial_name: str = ""):
 		super().__init__(parent, title=_("Add Dictionary"))
 
@@ -222,44 +205,17 @@ class DictionaryNameDialog(wx.Dialog):
 		self.name_ctrl.SetFocus()
 		self.name_ctrl.SelectAll()
 
-	def _on_ok(self, event: wx.CommandEvent) -> None:
-		candidate = self.name_ctrl.GetValue()
-		normalized_candidate, message = _normalize_dialog_name(
-			candidate,
-			normalize_dictionary_name,
-			_("Please enter the dictionary name."),
-			_("Dictionary name must be 1 to 32 characters."),
-			_("Dictionary name is not a valid Windows file name."),
-			_('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
-		)
-		if message:
-			wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
-			self.name_ctrl.SetFocus()
-			return
-		self.name_ctrl.SetValue(normalized_candidate)
-		event.Skip()
-
-	def _validate_name(self, candidate: str) -> str | None:
-		_normalized, message = _normalize_dialog_name(
-			candidate,
-			normalize_dictionary_name,
-			_("Please enter the dictionary name."),
-			_("Dictionary name must be 1 to 32 characters."),
-			_("Dictionary name is not a valid Windows file name."),
-			_('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
-		)
-		return message
-
-	def __enter__(self) -> "DictionaryNameDialog":
-		return self
-
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
 
-
-class DocumentNameDialog(wx.Dialog):
+class DocumentNameDialog(_NameDialog):
 	"""Dialog for creating or renaming a document."""
 
+	normalize_name = staticmethod(normalize_document_name)
+	name_messages = NameDialogMessages(
+		empty=N_("Please enter the document name."),
+		too_long=N_("Document name must be 1 to 32 characters."),
+		invalid=N_("Document name is not a valid Windows file name."),
+	)
+
 	def __init__(self, parent: wx.Window | None, title: str, initial_name: str = ""):
 		super().__init__(parent, title=title)
 
@@ -287,40 +243,8 @@ class DocumentNameDialog(wx.Dialog):
 	def get_document_name(self) -> str:
 		return self.name_ctrl.GetValue().strip()
 
-	def _on_ok(self, event: wx.CommandEvent) -> None:
-		candidate = self.name_ctrl.GetValue()
-		normalized_candidate, message = _normalize_dialog_name(
-			candidate,
-			normalize_document_name,
-			_("Please enter the document name."),
-			_("Document name must be 1 to 32 characters."),
-			_("Document name is not a valid Windows file name."),
-		)
-		if message:
-			wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
-			self.name_ctrl.SetFocus()
-			return
-		self.name_ctrl.SetValue(normalized_candidate)
-		event.Skip()
-
-	def _validate_name(self, candidate: str) -> str | None:
-		_normalized, message = _normalize_dialog_name(
-			candidate,
-			normalize_document_name,
-			_("Please enter the document name."),
-			_("Document name must be 1 to 32 characters."),
-			_("Document name is not a valid Windows file name."),
-		)
-		return message
-
-	def __enter__(self) -> "DocumentNameDialog":
-		return self
-
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
-
 
-class InvalidWorkspaceFilesDialog(wx.Dialog):
+class InvalidWorkspaceFilesDialog(ContextManagedDialog, wx.Dialog):
 	"""Dialog shown when startup finds invalid DEP files in the workspace."""
 
 	def __init__(self, parent: wx.Window | None, invalid_paths: list[Path]):
@@ -353,14 +277,8 @@ class InvalidWorkspaceFilesDialog(wx.Dialog):
 		self._delete_invalid_files = False
 		self.EndModal(wx.ID_CANCEL)
 
-	def __enter__(self) -> "InvalidWorkspaceFilesDialog":
-		return self
 
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
-
-
-class FileIssuesDialog(wx.Dialog):
+class FileIssuesDialog(ContextManagedDialog, wx.Dialog):
 	"""Dialog shown when a batch operation skips one or more files."""
 
 	def __init__(self, parent: wx.Window | None, title: str, message: str, issues: list[str]):
@@ -375,12 +293,6 @@ class FileIssuesDialog(wx.Dialog):
 		finalize_dialog_layout(self, main_sizer)
 		self.SetMinSize((520, 320))
 
-	def __enter__(self) -> "FileIssuesDialog":
-		return self
-
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
-
 
 class CallbackVirtualListCtrl(wx.ListCtrl):
 	"""Virtual list that asks its owner for visible dictionary cell text."""
@@ -401,7 +313,7 @@ class CallbackVirtualListCtrl(wx.ListCtrl):
 DictionaryEntryListCtrl = CallbackVirtualListCtrl
 
 
-class SpeechSymbolsDialog(wx.Dialog):
+class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 	"""Dialog for editing custom dictionary mappings stored on disk."""
 
 	def __init__(self, parent: wx.Window | None, dictionary_path: Path | None = None):
@@ -414,12 +326,6 @@ class SpeechSymbolsDialog(wx.Dialog):
 		self.filter_entries()
 		self._update_button_states()
 
-	def __enter__(self) -> "SpeechSymbolsDialog":
-		return self
-
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
-
 	def _build_ui(self) -> None:
 		main_sizer = wx.BoxSizer(wx.VERTICAL)
 
@@ -648,7 +554,7 @@ class SpeechSymbolsDialog(wx.Dialog):
 		save_dictionary_entries(self.dictionary_path, self.entries)
 
 
-class DictionaryManagementDialog(wx.Dialog):
+class DictionaryManagementDialog(ContextManagedDialog, wx.Dialog):
 	"""Passive view of dictionary management: runs ``actions`` and implements ``DictionaryManagementView``."""
 
 	def __init__(
@@ -866,9 +772,3 @@ class DictionaryManagementDialog(wx.Dialog):
 			if file_dialog.ShowModal() != wx.ID_OK:
 				return None
 			return Path(file_dialog.GetPath())
-
-	def __enter__(self) -> "DictionaryManagementDialog":
-		return self
-
-	def __exit__(self, exc_type, exc, _tb) -> None:
-		self.Destroy()
EOF
```

- [ ] **Step 3: Grep, focused tests, full suite and msgids.**

```bash
grep -n "def __enter__\|def __exit__\|_normalize_dialog_name\|\"exceed\"" dialog.py
$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog tests.test_gui_document_flows tests.test_i18n tests.test_dialog_base 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
```

Expected (the grep prints nothing; the msgid set is unchanged):

```text
Ran 253 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dialog.py
git -C $REPO commit -q -F - <<'EOF'
refactor: use dialog base mixins in dialog.py

The seven context-managed dialogs take __enter__/__exit__ from
ContextManagedDialog. DictionaryNameDialog and DocumentNameDialog share
_on_ok/_validate_name through NameDialogBase and only declare their
normalizer and messages; the message box stays in a private _NameDialog
base. _normalize_dialog_name, which repeated half of the name checks and
guessed the reason from the error text, is removed: the dialogs map
NameValidationError.code instead. Same messages, order, focus and result.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: use dialog base mixins in dialog.py
```

---

### Task 5: Use `SingletonDialogMixin` in the settings dialogs (spec step 5)

- [ ] **Step 1: Probe decision D1 on the current code.**

```bash
$PY -B $T/tools/d1_check.py
```

Expected (on a wx without `PyDeadObjectError`, both errors turn into `AttributeError`):

```text
hasattr(wx, 'PyDeadObjectError'): False
RuntimeError('window has been deleted'): raised AttributeError: module 'wx' has no attribute 'PyDeadObjectError'
RuntimeError('unexpected'): raised AttributeError: module 'wx' has no attribute 'PyDeadObjectError'
```

- [ ] **Step 2: Migrate.** `_DEAD_WINDOW_ERROR_TYPES` resolves `PyDeadObjectError` once with `getattr`; both dialogs put `SingletonDialogMixin` first, set `dead_window_error_types`, lose `_destroy` and `_is_destroyed_window_error`, and keep a `show_singleton` that forwards its arguments (the settings dialog keeps its category check first). `on_ok`/`on_cancel` and `sync_open_font_size` are not touched.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/settings/dialogs.py b/client/settings/dialogs.py
index 26c4306..f806735 100644
--- a/client/settings/dialogs.py
+++ b/client/settings/dialogs.py
@@ -13,6 +13,7 @@ from conversion.preprocessing.user_script import (
     save_preprocessing_script,
 )
 from i18n import _
+from ui.dialog_base import SingletonDialogMixin
 from .state import DotExpressSettingsSnapshot
 from .translation import (
     MAX_CONVERSION_WIDTH,
@@ -104,8 +105,14 @@ class SettingsDialog(wx.Dialog):
         pass
 
 
-class TextProcessingDialog(SettingsDialog):
+_DEAD_WINDOW_ERROR_TYPES = tuple(
+    error_type for error_type in (getattr(wx, "PyDeadObjectError", None),) if error_type is not None
+)
+
+
+class TextProcessingDialog(SingletonDialogMixin, SettingsDialog):
     _instance: "TextProcessingDialog | None" = None
+    dead_window_error_types = _DEAD_WINDOW_ERROR_TYPES
 
     def __init__(self, parent, *, script_path: Path | str) -> None:
         self.script_path = Path(script_path)
@@ -165,25 +172,6 @@ class TextProcessingDialog(SettingsDialog):
     def on_cancel(self, event=None) -> None:
         self._destroy()
 
-    def _destroy(self) -> None:
-        if TextProcessingDialog._instance is self:
-            TextProcessingDialog._instance = None
-        self.Destroy()
-
-    @staticmethod
-    def _is_destroyed_window_error(error: Exception) -> bool:
-        if isinstance(error, getattr(wx, "PyDeadObjectError", ())):
-            return True
-        if not isinstance(error, (ReferenceError, RuntimeError)):
-            return False
-        message = str(error).lower()
-        return (
-            "wrapped c/c++ object" in message
-            or "has been deleted" in message
-            or "already deleted" in message
-            or "destroyed" in message
-        )
-
     @classmethod
     def show_singleton(
         cls,
@@ -191,21 +179,10 @@ class TextProcessingDialog(SettingsDialog):
         parent,
         script_path: Path | str,
     ) -> "TextProcessingDialog":
-        instance = cls._instance
-        if instance is not None:
-            try:
-                instance.Iconize(False)
-                instance.Raise()
-                instance.SetFocus()
-                return instance
-            except (ReferenceError, RuntimeError, wx.PyDeadObjectError) as error:
-                if not cls._is_destroyed_window_error(error):
-                    raise
-                cls._instance = None
-        instance = cls(parent, script_path=script_path)
-        cls._instance = instance
-        instance.Show()
-        return instance
+        existing = cls._raise_existing()
+        if existing is not None:
+            return existing
+        return cls._show_new(cls(parent, script_path=script_path))
 
 
 class MultiCategorySettingsDialog(SettingsDialog):
@@ -715,7 +692,7 @@ CommitSettings = Callable[
 ]
 
 
-class DotExpressSettingsDialog(MultiCategorySettingsDialog):
+class DotExpressSettingsDialog(SingletonDialogMixin, MultiCategorySettingsDialog):
     base_title = _("DotExpress Settings")
     title_template = _("DotExpress Settings: {category}")
     category_classes = [
@@ -724,6 +701,7 @@ class DotExpressSettingsDialog(MultiCategorySettingsDialog):
         ViewSettingsPanel,
     ]
     _instance: "DotExpressSettingsDialog | None" = None
+    dead_window_error_types = _DEAD_WINDOW_ERROR_TYPES
 
     def __init__(
         self,
@@ -790,31 +768,12 @@ class DotExpressSettingsDialog(MultiCategorySettingsDialog):
             panel.on_discard()
         self._destroy()
 
-    def _destroy(self) -> None:
-        if DotExpressSettingsDialog._instance is self:
-            DotExpressSettingsDialog._instance = None
-        self.Destroy()
-
     def select_category(self, category_class) -> None:
         index = self.category_classes.index(category_class)
         self.category_list.Select(index)
         self.category_list.Focus(index)
         self._change_category(index)
 
-    @staticmethod
-    def _is_destroyed_window_error(error: Exception) -> bool:
-        if isinstance(error, getattr(wx, "PyDeadObjectError", ())):
-            return True
-        if not isinstance(error, (ReferenceError, RuntimeError)):
-            return False
-        message = str(error).lower()
-        return (
-            "wrapped c/c++ object" in message
-            or "has been deleted" in message
-            or "already deleted" in message
-            or "destroyed" in message
-        )
-
     @classmethod
     def show_singleton(
         cls,
@@ -827,29 +786,22 @@ class DotExpressSettingsDialog(MultiCategorySettingsDialog):
     ) -> "DotExpressSettingsDialog":
         if initial_category is not None and initial_category not in cls.category_classes:
             raise ValueError("initial_category is not registered")
-        instance = cls._instance
-        if instance is not None:
-            try:
-                instance.Iconize(False)
-                if initial_category is not None:
-                    instance.select_category(initial_category)
-                instance.Raise()
-                instance.SetFocus()
-                return instance
-            except (ReferenceError, RuntimeError, wx.PyDeadObjectError) as error:
-                if not cls._is_destroyed_window_error(error):
-                    raise
-                cls._instance = None
-        instance = cls(
-            parent,
-            snapshot=snapshot,
-            dictionary_names=dictionary_names,
-            commit=commit,
-            initial_category=initial_category,
+        existing = cls._raise_existing(
+            None
+            if initial_category is None
+            else lambda instance: instance.select_category(initial_category)
+        )
+        if existing is not None:
+            return existing
+        return cls._show_new(
+            cls(
+                parent,
+                snapshot=snapshot,
+                dictionary_names=dictionary_names,
+                commit=commit,
+                initial_category=initial_category,
+            )
         )
-        cls._instance = instance
-        instance.Show()
-        return instance
 
     @classmethod
     def sync_open_font_size(cls, font_size: int) -> None:
EOF
```

- [ ] **Step 3: Probe again, grep, focused tests and full suite.**

```bash
$PY -B $T/tools/d1_check.py
grep -n "_is_destroyed_window_error\|def _destroy" settings/dialogs.py
$PY -m unittest tests.test_settings_dialogs tests.test_gui_document_flows tests.test_dialog_base 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (D1: the dead window is rebuilt, the unrelated error re-raised; the grep prints nothing):

```text
hasattr(wx, 'PyDeadObjectError'): False
RuntimeError('window has been deleted'): rebuilt=True slot_holds_new=True
RuntimeError('unexpected'): raised RuntimeError: unexpected
Ran 213 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/settings/dialogs.py
git -C $REPO commit -q -F - <<'EOF'
refactor: use SingletonDialogMixin in settings dialogs

TextProcessingDialog and DotExpressSettingsDialog drop their copies of
_destroy, _is_destroyed_window_error and the show_singleton body; each
show_singleton now only forwards its arguments to the mixin. Same call
order, slot handling and errors. The dead-window exception type is
looked up with getattr once, so on a wx without PyDeadObjectError an
error while raising the open dialog is handled as intended instead of
turning into AttributeError (decision D1; not reachable in the app).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: use SingletonDialogMixin in settings dialogs
```

---

### Task 6: Move `ConvertingDialog` into `dialog.py` (spec step 6)

- [ ] **Step 1: Point the `ConvertingDialog` tests at `dialog` and watch them fail.** Only the module-level loading block changes (refinement 3).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_converting_dialog.py b/client/tests/test_converting_dialog.py
index 7700463..ec924b4 100644
--- a/client/tests/test_converting_dialog.py
+++ b/client/tests/test_converting_dialog.py
@@ -1,4 +1,3 @@
-import importlib
 import unittest
 from types import SimpleNamespace
 from unittest.mock import Mock, call, patch, sentinel
@@ -6,12 +5,9 @@ from unittest.mock import Mock, call, patch, sentinel
 from tests import wx_stub
 
 # The module that defines ConvertingDialog, loaded against stub wx.
-_SCOPE = wx_stub.StubScope(
-    wx_stub.gui_frame_stubs(),
-    isolate=("gui", "settings.dialogs", "ui.dual_view"),
-)
+_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog",))
 with _SCOPE.loading():
-    defining_module = importlib.import_module("gui")
+    import dialog as defining_module
 
 setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
EOF
$PY -m unittest tests.test_converting_dialog 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
ERROR: test_builds_a_closeless_stay_on_top_info_dialog_with_the_converting_label (tests.test_converting_dialog.ConvertingDialogTest.test_builds_a_closeless_stay_on_top_info_dialog_with_the_converting_label)
AttributeError: module 'dialog' has no attribute 'ConvertingDialog'
ERROR: test_close_is_not_vetoed_when_it_cannot_be (tests.test_converting_dialog.ConvertingDialogTest.test_close_is_not_vetoed_when_it_cannot_be)
AttributeError: module 'dialog' has no attribute 'ConvertingDialog'
ERROR: test_close_is_vetoed_when_it_can_be (tests.test_converting_dialog.ConvertingDialogTest.test_close_is_vetoed_when_it_can_be)
AttributeError: module 'dialog' has no attribute 'ConvertingDialog'
Ran 3 tests
FAILED (errors=3)
```

- [ ] **Step 2: Move the class.** The class body is copied unchanged into `dialog.py` after `FileIssuesDialog`; `gui.py` imports it from `dialog` and drops `finalize_dialog_layout` from that import; `_GUI_DIALOG_NAMES` gains `ConvertingDialog`, so the stubbed `dialog` module of the gui scope provides it (the guard is updated in the same commit as the change it guards).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/dialog.py b/client/dialog.py
index d2ebd26..06a4712 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -294,6 +294,22 @@ class FileIssuesDialog(ContextManagedDialog, wx.Dialog):
 		self.SetMinSize((520, 320))
 
 
+class ConvertingDialog(wx.Dialog):
+	def __init__(self, parent: wx.Window):
+		style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP
+		super().__init__(parent, title=_("Info"), style=style)
+
+		message = wx.StaticText(self, label=_("converting"))
+		sizer = wx.BoxSizer(wx.VERTICAL)
+		sizer.Add(message, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 20)
+		finalize_dialog_layout(self, sizer)
+		self.Bind(wx.EVT_CLOSE, self._on_close)
+
+	def _on_close(self, evt: wx.CloseEvent):
+		if evt.CanVeto():
+			evt.Veto()
+
+
 class CallbackVirtualListCtrl(wx.ListCtrl):
 	"""Virtual list that asks its owner for visible dictionary cell text."""
 
diff --git a/client/gui.py b/client/gui.py
index 76ddd35..3a94e46 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -74,12 +74,12 @@ from ui.translation_menu import get_translation_menu_items
 from client_init import start_client_init_background
 
 from dialog import (
+	ConvertingDialog,
 	DictionaryManagementDialog,
 	DocumentNameDialog,
 	FileIssuesDialog,
 	InvalidWorkspaceFilesDialog,
 	SpeechSymbolsDialog,
-	finalize_dialog_layout,
 )
 from settings.view import (
 	ViewSettings,
@@ -105,22 +105,6 @@ VIEW_SCHEMES = {
 logger = get_logger("dotexpress.gui", "gui.log")
 
 
-class ConvertingDialog(wx.Dialog):
-	def __init__(self, parent: wx.Window):
-		style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP
-		super().__init__(parent, title=_("Info"), style=style)
-
-		message = wx.StaticText(self, label=_("converting"))
-		sizer = wx.BoxSizer(wx.VERTICAL)
-		sizer.Add(message, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 20)
-		finalize_dialog_layout(self, sizer)
-		self.Bind(wx.EVT_CLOSE, self._on_close)
-
-	def _on_close(self, evt: wx.CloseEvent):
-		if evt.CanVeto():
-			evt.Veto()
-
-
 class NamedControlAccessible(wx.Accessible):
 	def __init__(self, window: wx.Window, name: str, description: str = ""):
 		super().__init__(window)
diff --git a/client/tests/wx_stub.py b/client/tests/wx_stub.py
index 6f9fdf1..068062c 100644
--- a/client/tests/wx_stub.py
+++ b/client/tests/wx_stub.py
@@ -374,6 +374,7 @@ def dual_view_stubs():
 
 
 _GUI_DIALOG_NAMES = (
+    "ConvertingDialog",
     "DictionaryManagementDialog",
     "DictionaryNameDialog",
     "DocumentNameDialog",
EOF
```

- [ ] **Step 3: Grep, focused tests and full suite.**

```bash
grep -n "class ConvertingDialog\|finalize_dialog_layout" gui.py
$PY -m unittest tests.test_converting_dialog tests.test_gui_document_flows tests.test_wx_stub tests.test_dialog_validation tests.test_dialog_display 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (the grep prints nothing):

```text
Ran 190 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dialog.py client/gui.py client/tests/wx_stub.py client/tests/test_converting_dialog.py
git -C $REPO commit -q -F - <<'EOF'
refactor: move ConvertingDialog into dialog.py

ConvertingDialog joins the other wx dialogs in dialog.py, unchanged, and
gui.py imports it from there; gui.py no longer needs
finalize_dialog_layout. The gui test stubs provide a ConvertingDialog
fake in the stubbed dialog module, and the ConvertingDialog tests now
load dialog.py instead of gui.py.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: move ConvertingDialog into dialog.py
```

---

### Task 7: Final verification (spec acceptance criteria; no commit)

- [ ] **Step 1: AC1 (roadmap command, verbose) and AC2.**

```bash
$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_name_validation tests.test_dialog_base tests.test_dictionary_manager tests.test_document_workspace tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_speech_symbols_dialog tests.test_gui_document_flows tests.test_workspace_service tests.test_i18n tests.test_removed_dead_code tests.test_wx_stub tests.test_converting_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (AC1: 71 tests, all passing; AC2 all green; the 2 skips in `test_gui_document_flows` need a case-insensitive file system):

```text
71
Ran 71 tests
OK
Ran 370 tests
OK (skipped=2)
```

- [ ] **Step 2: AC3, full suite and fixture.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
git -C $REPO diff main --stat -- client/tests/fixtures
sha256sum tests/fixtures/translation_golden.json
```

Expected (818 + 71; no fixture diff):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

- [ ] **Step 3: AC3, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 889 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=889 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC3, each dialog test module alone and in both orders with `test_dialog_base`.**

```bash
for m in test_dialog_validation test_dialog_display test_speech_symbols_dialog test_dictionary_management_dialog test_settings_dialogs test_gui_document_flows test_converting_dialog; do
  for order in "tests.$m" "tests.$m tests.test_dialog_base" "tests.test_dialog_base tests.$m"; do
    echo "$order: $($PY -B -m unittest $order 2>&1 | grep -E '^(OK|FAILED)')"
  done
done
```

Expected:

```text
tests.test_dialog_validation: OK
tests.test_dialog_validation tests.test_dialog_base: OK
tests.test_dialog_base tests.test_dialog_validation: OK
tests.test_dialog_display: OK
tests.test_dialog_display tests.test_dialog_base: OK
tests.test_dialog_base tests.test_dialog_display: OK
tests.test_speech_symbols_dialog: OK
tests.test_speech_symbols_dialog tests.test_dialog_base: OK
tests.test_dialog_base tests.test_speech_symbols_dialog: OK
tests.test_dictionary_management_dialog: OK
tests.test_dictionary_management_dialog tests.test_dialog_base: OK
tests.test_dialog_base tests.test_dictionary_management_dialog: OK
tests.test_settings_dialogs: OK
tests.test_settings_dialogs tests.test_dialog_base: OK
tests.test_dialog_base tests.test_settings_dialogs: OK
tests.test_gui_document_flows: OK (skipped=2)
tests.test_gui_document_flows tests.test_dialog_base: OK (skipped=2)
tests.test_dialog_base tests.test_gui_document_flows: OK (skipped=2)
tests.test_converting_dialog: OK
tests.test_converting_dialog tests.test_dialog_base: OK
tests.test_dialog_base tests.test_converting_dialog: OK
```

- [ ] **Step 5: AC4-AC7 and the msgid scan.**

```bash
echo AC4
grep -n "def __enter__\|def __exit__\|_normalize_dialog_name\|\"exceed\"" $REPO/client/dialog.py
grep -n "_is_destroyed_window_error\|def _destroy" $REPO/client/settings/dialogs.py
grep -n "raise ValueError" $REPO/client/shared/name_validation.py
grep -n "class ConvertingDialog\|finalize_dialog_layout" $REPO/client/gui.py
grep -rn "in str(exc)" $REPO/client --include=*.py --exclude-dir=tests
echo AC5
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json
git -C $REPO diff main --stat -- client/locales scripts
echo AC6
git -C $REPO diff main --stat -- client/dictionaries client/documents client/conversion client/about.py client/ui
echo AC7
$PY -m unittest tests.test_dialog_base.DialogBaseImportTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo end
```

Expected (nothing after AC4; 353 source msgids, the same 4 only-in-pot wildcards and nothing only in source; AC6 lists only the new module):

```text
AC4
AC5
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
SOURCE == SAVED
AC6
 client/ui/dialog_base.py | 142 +++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 142 insertions(+)
AC7
Ran 1 test
OK
end
```

- [ ] **Step 6: The branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -7
git -C $REPO diff --stat HEAD~6 HEAD
```

Expected:

```text
refactor: move ConvertingDialog into dialog.py
refactor: use SingletonDialogMixin in settings dialogs
refactor: use dialog base mixins in dialog.py
refactor: add wx-free dialog base mixins
refactor: raise typed NameValidationError for invalid names
test: characterize dialog lifecycle, name validation and singletons
docs: plan dialog base and typed name errors
 client/dialog.py                        | 170 ++++-----------
 client/gui.py                           |  18 +-
 client/settings/dialogs.py              | 106 +++-------
 client/shared/name_validation.py        |  24 ++-
 client/tests/test_converting_dialog.py  |  78 +++++++
 client/tests/test_dialog_base.py        | 357 ++++++++++++++++++++++++++++++++
 client/tests/test_dialog_validation.py  | 321 +++++++++++++++++++++++++++-
 client/tests/test_dictionary_manager.py |   9 +
 client/tests/test_document_workspace.py |  23 ++
 client/tests/test_name_validation.py    | 124 +++++++++++
 client/tests/test_settings_dialogs.py   | 233 ++++++++++++++++++++-
 client/tests/wx_stub.py                 |   1 +
 client/ui/dialog_base.py                | 142 +++++++++++++
 13 files changed, 1377 insertions(+), 229 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): run `python -c "import wx; print(wx.version(), hasattr(wx, 'PyDeadObjectError'))"` on the build machine (expected `4.2.5 ... False`, D1's premise). On a packaged build, open and close every dialog in the spec's inventory; in Add Dictionary, Rename Dictionary, Add Document and Rename Document enter an empty name, a 33-character name, `CON` and (dictionaries) `Default`: the same zh_TW messages appear and the dialog stays open. Open Settings and Text Processing twice (the open window is raised), close and reopen them. Start a long conversion: the converting dialog appears and Alt+F4 does not close it. PyInstaller must pick up `ui/dialog_base.py` through the static imports in `dialog.py` and `settings/dialogs.py` (read, not run). No visual or string change, so no screenshots and no `generate_pot.bat` run.
