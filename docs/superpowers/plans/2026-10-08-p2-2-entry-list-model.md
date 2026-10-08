# Dictionary Entry List Model (P2-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the data logic of the dictionary entries editor (`dialog.SpeechSymbolsDialog`, "Custom Dictionary Manager") into a new wx-free `client/dictionaries/entry_list_model.py` (`DictionaryEntryListModel`, `EntryListUpdate`, `DuplicateEntryError`), make the dialog a Supervising Controller that renders what the model returns, make `dictionary_path` required, and finally rename the dialog to `DictionaryEntriesDialog`. Nothing a user sees changes: same strings, message boxes and their order, list-control call order, selection, focus, button states and saved CSV bytes. The msgid set stays at 353; `client/locales` does not change; the eight pre-existing quirks Q1-Q8 of the spec are pinned by tests marked `# KNOWN BUG (P2-2 spec, Qn)`, not fixed.

**Architecture:** Four commits in the spec's order. Task 1 replaces the internals-poking dialog tests with a black-box harness that drives the real dialog only through its wx surface (fake widgets, one ordered call log, the virtual-list cell callback, a real CSV file) and records a golden trace fixture from the unmodified editor; the trace tests are red until the fixture is generated, and a throwaway mutant runner shows the net catches all 15 breakages the spec lists. Task 2 writes the model's tests first (red: module missing), then the model. Task 3 adds the two part-C tests (red), then switches the dialog to the model with the Task 1 harness and the trace unchanged and green. Task 4 is the droppable, purely mechanical rename (`git mv` of the test module included).

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `dataclasses`, `ast`, `inspect`, `json`, `random`, `csv`). wxPython is not installed: the dialog tests run against `tests/wx_stub.py`'s speech profile (`load_speech_dialog`) with the module's `wx` replaced by the harness namespace; the model is tested without any stub scope.

**Spec:** `docs/superpowers/specs/2026-10-08-p2-2-entry-list-model-design.md` (authoritative, commit `efb6de3`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p2-2-entry-list-model`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (11, nothing else): production `client/dictionaries/entry_list_model.py` (new), `client/dialog.py`, `client/gui.py`; tests `client/tests/test_speech_symbols_dialog.py` (renamed in Task 4 to `client/tests/test_dictionary_entries_dialog.py`), `client/tests/fixtures/dictionary_entries_trace.json` (new, generated), `client/tests/test_dictionary_entry_list_model.py` (new), `client/tests/test_dialog_validation.py`, `client/tests/test_gui_document_flows.py`, `client/tests/wx_stub.py`. Never touch `client/dictionaries/entries.py`, `client/locales/`, `scripts/`, `client/conversion/`, `client/translation/`, `client/tests/fixtures/translation_golden.json` or any other module.
- Indentation: `client/dialog.py`, `client/gui.py`, `client/dictionaries/*.py` and the new `tests/test_dictionary_entry_list_model.py` use tabs; the dialog test module, `tests/test_dialog_validation.py`, `tests/test_gui_document_flows.py` and `tests/wx_stub.py` use 4 spaces. The patches and file blocks carry the exact characters; run every block as it is, do not retype (the test files write non-ASCII text as `\uXXXX` escapes, and a retyped escape can turn into the character). If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes and no msgid changes: the source msgid set is compared with the Task 0 snapshot after Task 3 and at the end (`SOURCE == SAVED`, 353). No `.po`/`.mo` change, no `generate_pot.bat` run.
- The P1-5 golden fixture is never touched (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, checked in Task 0 and Task 5). The new trace fixture is generated once in Task 1 (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, 300,540 bytes) and never regenerated in the repo; Task 5 regenerates it into `$T` from the refactored editor and compares the bytes.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, and absolute paths are stripped from errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p22impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.4.
- Baseline (re-verified at `efb6de3`, the spec commit; code identical to `33dc34d` = `main`): `$PY -m unittest discover -s tests` gives `Ran 889 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: `load_dictionary_entries` stays imported in `dialog.py`.** The spec lists it among the "now-unused imports" removed in step 3, but `DictionaryManagementDialog._load_dictionary_counts` (`dialog.py:653`) still calls it to show each dictionary's entry count. Task 3 removes only `List`, `normalize_entry_type` and `save_dictionary_entries`, and adds the `dictionaries.entry_list_model` import.
2. **Factual clarification (Q3): the truncated file keeps the rows before the failing one.** "A lone surrogate leaves only the header" holds when the failing row is the first one (the writer has already written the header and every earlier row when it fails). The Q3/Q7 test edits the first row to `"\ud800"`, so the file is left with the header only and the second row is lost on disk.
3. **Refinement: harness surface.** `_EditorHarness` builds the real dialog with `object.__new__`, patches the stub base's `__init__` (captured once as `_NATIVE_DIALOG_BASE`, so two harnesses never look up `Dialog` on a patched `wx`), and replaces the module's `wx`, `CallbackVirtualListCtrl` and `AddSymbolDialog`; the dialog instance gets `CreateButtonSizer`, `FindWindowById`, `SetSizerAndFit`, `GetParent`, `CentreOnParent`, `Centre` and `Destroy`. The log records, in call order: the base `__init__` (title, style), `StaticText` labels, `TextCtrl`, `ListCtrl` (style), `InsertColumn`, every `Bind`, `Button` labels, `CreateButtonSizer`, `SetLabel` of OK/Cancel, `SetSizerAndFit`, `CentreOnParent`, `SetItemCount`, `Refresh`, `Select(index, on)`, `Focus`, `Enable(label, state)`, `ChangeValue`, `SetValue` (which, as in wx, also fires `EVT_TEXT`), `MessageBox(message, caption, flags)`, `AddSymbolDialog(entry)` and every event `Skip`. Message-box and entry-dialog parents are kept separately. The fake list drops the selection when the item count shrinks below it (as the pre-P2-2 fake did) and programmatic `Select` sends no event. "Base `__init__` before the file is read" is shown by writing the CSV from inside the patched base `__init__`: the rows appear, so the file was read afterwards.
4. **Refinement: the 17 rewritten tests.** Same names and the same assertions, expressed on observations: `filtered_entries` becomes the visible rows read through the cell callback, `entries` becomes the rows after clearing the filter (or the saved CSV), `list_ctrl.selected` the fake list's selection. Two setups change: `SpeechSymbolsDialogFilterTest` adds Beta (`Needle`, Bopomofo) through the entry dialog, because the real loader drops a Bopomofo row whose braille is not zhuyin (the old test bypassed the loader); the delete test adds Alpine through the entry dialog instead of appending to `entries`. The four kept tests (`CallbackVirtualListCtrlTest`, the two loading tests, the isolation test) are byte-identical.
5. **Refinement: the golden trace.** Actions are chosen by `random.Random(seed)` for seeds 0-39 (kinds weighted filter 2, select 2, deselect 1, add 2, edit 1, activate 1, delete 1; 20% of add/edit/activate cancel; 30% of entries get a fresh `n<i>` text, the rest collide). A select picks a row of the current visible list (or becomes a deselect when it is empty), so the generator needs the live editor; the replay therefore drives the actions recorded in the fixture, and the generator is only used to write it. Each step stores the action, the call log since the previous step and the state (`rows`, `selected`, `focused`, `edit`, `delete`, `filter`); `rows` is left out when unchanged since the previous step, and the final OK step adds the saved CSV. The initial CSV has identical rows (`a`), padded fields (` Ab `, ` SS `), a skipped empty text, a skipped invalid Bopomofo row, `Straße`/`STRASSE`, empty braille and an unknown type. One compact JSON step per line, UTF-8: 300,540 bytes (under the spec's 300 KB target counted as 300 KiB). Two generations in fresh processes gave the same bytes. Over the 1,000 actions the trace opens the entry dialog 331 times (87 scripted cancels), shows 76 duplicate message boxes and clears the filter from Add 38 times.
6. **Refinement: Part A edit in Task 3.** Part A is not edited after Task 1, except that Task 3 adds two imports to the module header (`inspect`, and `DictionaryEntryListModel` imported before `wx_stub.load_speech_dialog()` as the spec requires; the model module does not exist in Task 1) and appends the part-C class `SpeechSymbolsDialogModelTest`. `git diff` of Task 3 on the test module shows only additions.
7. **Refinement: small code choices the spec leaves open.** Both duplicate message boxes go through one private helper, `_show_duplicate_error(identifier)` (same msgid, text, title, flags and parent; one source location instead of two, in the same file; the set of msgids is unchanged). `_edit_selected` keeps its two-part guard (`visible_index is None or current_entry is None`). The model has a private `_visible_at(index)` that raises `IndexError("visible index out of range: N")` for `replace`/`remove`, and docstrings stating the D4 comparison rules; its module docstring names the dialog by its title, so the rename does not touch the model. `_render` and the handlers are the spec's, line for line.
8. **Refinement: the rename keeps sorted lists sorted.** In `gui.py`'s `from dialog import (...)`, `test_dialog_validation`'s import block and `_GUI_DIALOG_NAMES`, `DictionaryEntriesDialog` moves before `DictionaryManagementDialog`; `CONTEXT_MANAGED_DIALOGS` keeps its order. The wx_stub comment naming the test module is updated (so `wx_stub.py` has 2 changed lines, not 1). Kept as the spec says: `AddSymbolDialog`, the `speech_*`/`SPEECH_*` profile names (including the private module name `_speech_symbols_dialog_under_test`), `DictionaryEntryListCtrl`, and the test method `test_edit_result_opens_speech_symbols_for_presenter_path` in `test_gui_document_flows` (lower case; the spec counts 2 changed lines in that file; AC6's grep is case-sensitive).
9. **Refinement: test counts fixed at 84 new tests (889 -> 973).** Task 1: 43 (`tests/test_speech_symbols_dialog.py` goes from 21 to 64: 4 kept, 17 rewritten, 43 new: construction 7, cell text 2, filter 8, add 6, edit 8, delete 5, OK 5, trace 2); Task 2: 39 (`tests/test_dictionary_entry_list_model.py`); Task 3: 2 (part C); Task 4: 0. The roadmap command (spec AC1) runs 105 tests.
10. **Refinement: the KNOWN BUG markers.** Q1 `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header`; Q2 `test_unchanged_dictionary_is_rewritten_in_normalized_form`; Q3 and Q7 `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file`; Q4 `test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text` and `test_identical_rows_delete_removes_the_first_equal_row`; Q5 `test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index` and `test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized` (Cancel has no handler); Q6 the two duplicate tests of Add and Edit; Q8 `test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog`. A reviewer should reject any "fix" in this task.
11. **Refinement: the empty-result branch.** With the fake list, `SetItemCount(0)` has already dropped the selection, so the empty-result log is `SetItemCount(0)`, `Refresh`, `Enable(Edit, False)`, `Enable(Delete, False)` with no `Select(i, False)`; the test is named for what it shows. Real wx behavior of `SetItemCount` on a selected virtual row is Windows verification debt (unchanged code path either way).
12. **Refinement: the trace is also regenerated from the refactored editor.** Besides `git diff` of the fixture between Task 1 and Task 4 (AC4), Task 5 calls `write_trace_fixture($T/trace_after.json)` on the final code and compares it byte for byte with the committed fixture: the refactored editor reproduces the same random sequences and observations.

Everything else in the spec was re-checked at `efb6de3`: the class and method line numbers, the construction order, the layout and column table, every handler's behavior and wx call order, the comparison rules of D4, the loader and writer behavior (BOM, skipped rows, truncation, `IsADirectoryError` text on Linux), the callers (`gui.py:82`, `gui.py:944`, the two test modules, `_GUI_DIALOG_NAMES`), the stub-scope notes, the baseline (889; 21 tests in the dialog module; 353 msgids plus the 4 known only-in-pot wildcards).

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `efb6de3` (`$SP/p22plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 4 the 20 shuffle seeds, the pair orders, the msgid scan, the trace regeneration and every acceptance criterion passed. The file blocks in this plan are the dry clone's committed files and the patches are `git diff`s of its commits (Task 3 split into the red test step and the implementation step; Task 4 with rename detection). Then this file's blocks were run in order on fresh clones (`$SP/p22plan/replay1` to `replay3`, each with a stand-in plan commit and a local `main` at `33dc34d`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 4 commits applied, every expected block (25) matched byte for byte on the final replay, and the resulting `client/` tree is identical to the dry clone's. Final sha256: `client/dictionaries/entry_list_model.py` `1ba25240294566f1930533c29ebf9e626cfb4130aa504eefdb6f35d3ef520470`, `client/dialog.py` `3a6bbbb6ca3fa000beab6754ac4e7ef9b3a1f03ed17c52b93f1fcd154e70b08f`, `client/gui.py` `78f29ad445b95f783c33db9201c375841e6ec5b54bbce7ed93b0463381ec8aa4`, `client/tests/test_dictionary_entries_dialog.py` `bc9859732d03391d6e1d229a388f1d9354bc161c6c248cef24129fa77273db2d`, `client/tests/test_dictionary_entry_list_model.py` `0f4c8edfed1185aa281308ec88ad10009ef2a456dd3f3968eaeaa4fd8b25fd83`, `client/tests/test_dialog_validation.py` `c98d95b21d112f28efdc7c4c2f1e0613577d47d87bb1fe9c717d99e3c9bb068d`, `client/tests/test_gui_document_flows.py` `704280175e5a3dff8cc188ed0e60192a391b8f335a565b50b3575d8850326c42`, `client/tests/wx_stub.py` `1a0cae258f66c3438b4eb5649c07914002d1635db9a035b0d758cdad7ba4ae45`, `client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`; `client/tests/fixtures/translation_golden.json` unchanged at `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`. Windows-only behavior (real wx, NVDA, PyInstaller, `generate_pot.bat`) was not run; see the end of Task 5.

## Review Focus

1. **Same behavior, shown three ways.** The Task 1 harness tests (exact call logs for construction, filter, add, edit, delete and OK), the 40-sequence golden trace (every step's call log and state, the final CSV), and the trace regenerated from the refactored editor in Task 5. The harness never reads the dialog's data attributes, so the Task 3 switch runs against unchanged tests. The 15 mutants (casefold, type matching, selection read time, equality/identity in restore, replace and remove, duplicate check case, scope and self-exclusion, filter clearing in Add and Edit, `ChangeValue` vs `SetValue`, fallback clamping, saving the visible list, `Skip` after a failed save) each make Task 1 fail.
2. **Comparison rules (D4).** `_selection_after` uses `list.index` (equality, first equal); `replace` finds the full-list item with `is`; `remove` calls `list.remove` (first equal); `source_text_exists` compares `text` with `==` over the full list and excludes by `is`. Each has an identical-row test in both the dialog module and the model module.
3. **Filter-text ownership (D3).** The model keeps the filter text; the dialog passes `filter_ctrl.GetValue()` only to `apply_filter` (construction and `EVT_TEXT`), and mirrors `add`'s `filter_cleared` with `ChangeValue("")` before rendering. `replace`/`remove` use the model's copy where the old code re-read the box. Equal as long as every user edit of the box fires `EVT_TEXT` (Windows verification debt, spec Risks).
4. **Stub-scope safety.** The dialog test module imports `dictionaries.entry_list_model` before `load_speech_dialog()`, so the scope does not evict it and the part-C `isinstance` check sees one class. `test_dialog_validation` (evicts nothing) and `test_dialog_display` (evicts everything) import the model through `dialog`; the model holds no stub reference. Guards: 20 shuffled full-suite seeds and each stub-scope module alone and in both orders with the model test module.
5. **Untouched seams.** `AddSymbolDialog`, `CallbackVirtualListCtrl`, `DictionaryManagementDialog` (still uses `load_dictionary_entries`), `dictionaries/entries.py`, `gui.on_open_dictionary_management` (only the class name changes), the speech stub profile.

## File Map

- Task 1: rewrite `client/tests/test_speech_symbols_dialog.py`; generate `client/tests/fixtures/dictionary_entries_trace.json`.
- Task 2: create `client/tests/test_dictionary_entry_list_model.py`, `client/dictionaries/entry_list_model.py`.
- Task 3: modify `client/tests/test_speech_symbols_dialog.py` (additions only), `client/dialog.py`.
- Task 4: modify `client/dialog.py`, `client/gui.py`, `client/tests/test_dialog_validation.py`, `client/tests/test_gui_document_flows.py`, `client/tests/wx_stub.py`; rename `client/tests/test_speech_symbols_dialog.py` -> `client/tests/test_dictionary_entries_dialog.py`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 889 |
| 1 characterization | 43 (dialog module 21 -> 64) | 932 |
| 2 model | 39 | 971 |
| 3 dialog uses the model | 2 | 973 |
| 4 rename | 0 | 973 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `entry_mutants.py <client_dir> <scratch_dir> [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`; with the untracked trace fixture) to `<scratch_dir>/client` once, then for each of the 15 mutants writes one edited `dialog.py` into the copy, runs `tests.test_speech_symbols_dialog` there and restores the file. The repo is never changed. Only meaningful in Task 1 (the patterns match the pre-refactor editor).
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
docs: plan dictionary entry list model
refactor/p2-2-entry-list-model
```

- [ ] **Step 2: Create the mutant runner.**

```bash
mkdir -p $T/tools
cat > $T/tools/entry_mutants.py <<'EOF'
"""Run the P2-2 characterization tests against deliberately broken editors (throwaway).

Usage: python entry_mutants.py <client_dir> <scratch_dir> [mutant ...]
Copies <client_dir> (without .venv, __pycache__, log) to <scratch_dir>/client once,
then for each mutant writes one edited dialog.py into the copy, runs
tests.test_speech_symbols_dialog there and restores the file. <client_dir> is
never changed. Prints "<mutant>: failures=F errors=E" per mutant (all by default).
Only meaningful before Task 3: the patterns match the pre-P2-2 editor.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = ["tests.test_speech_symbols_dialog"]

# name -> (old, new); old must occur exactly once in dialog.py.
MUTANTS = {
    "lower-instead-of-casefold": (
        "\t\tnormalized_filter = filter_text.casefold()\n"
        "\t\treturn normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()",
        "\t\tnormalized_filter = filter_text.lower()\n"
        "\t\treturn normalized_filter in entry.text.lower() or normalized_filter in entry.braille.lower()",
    ),
    "filter-matches-type": (
        "or normalized_filter in entry.braille.casefold()",
        "or normalized_filter in entry.braille.casefold() or normalized_filter in entry.entry_type.casefold()",
    ),
    "selection-read-after-refilter": (
        "\t\tprevious_entry = preferred_entry or self._get_selected_entry()\n"
        "\t\tif filter_text is None:\n"
        "\t\t\tfilter_text = self.filter_ctrl.GetValue()\n\n"
        "\t\tif filter_text:\n"
        "\t\t\tself.filtered_entries = [\n"
        "\t\t\t\tentry for entry in self.entries if self._entry_matches_filter(entry, filter_text)\n"
        "\t\t\t]\n"
        "\t\telse:\n"
        "\t\t\tself.filtered_entries = list(self.entries)\n",
        "\t\tif filter_text is None:\n"
        "\t\t\tfilter_text = self.filter_ctrl.GetValue()\n\n"
        "\t\tif filter_text:\n"
        "\t\t\tself.filtered_entries = [\n"
        "\t\t\t\tentry for entry in self.entries if self._entry_matches_filter(entry, filter_text)\n"
        "\t\t\t]\n"
        "\t\telse:\n"
        "\t\t\tself.filtered_entries = list(self.entries)\n"
        "\t\tprevious_entry = preferred_entry or self._get_selected_entry()\n",
    ),
    "selection-restored-by-identity": (
        "\t\t\t\tnew_index = self.filtered_entries.index(previous_entry)",
        "\t\t\t\tnew_index = [id(entry) for entry in self.filtered_entries].index(id(previous_entry))",
    ),
    "edit-replaces-first-equal": (
        "index for index, entry in enumerate(self.entries) if entry is current_entry",
        "index for index, entry in enumerate(self.entries) if entry == current_entry",
    ),
    "delete-by-identity": (
        "\t\tself.entries.remove(current_entry)",
        "\t\tdel self.entries[next(index for index, entry in enumerate(self.entries) if entry is current_entry)]",
    ),
    "duplicate-check-ignores-case": (
        "\t\t\tentry.text == identifier and entry is not exclude_entry",
        "\t\t\tentry.text.casefold() == identifier.casefold() and entry is not exclude_entry",
    ),
    "duplicate-check-visible-only": (
        "\t\t\tentry.text == identifier and entry is not exclude_entry\n\t\t\tfor entry in self.entries",
        "\t\t\tentry.text == identifier and entry is not exclude_entry\n\t\t\tfor entry in self.filtered_entries",
    ),
    "duplicate-check-without-self-exclusion": (
        "\t\t\tentry.text == identifier and entry is not exclude_entry",
        "\t\t\tentry.text == identifier",
    ),
    "add-clears-matching-filter": (
        "\t\tif filter_text and not self._entry_matches_filter(new_entry, filter_text):",
        "\t\tif filter_text:",
    ),
    "edit-clears-filter": (
        "\t\tself.entries[full_index] = updated_entry\n"
        "\t\tself.filter_entries(\n"
        "\t\t\tself.filter_ctrl.GetValue(),",
        "\t\tself.entries[full_index] = updated_entry\n"
        "\t\tself.filter_ctrl.ChangeValue(\"\")\n"
        "\t\tself.filter_entries(\n"
        "\t\t\t\"\",",
    ),
    "add-uses-set-value": (
        "\t\t\tself.filter_ctrl.ChangeValue(\"\")",
        "\t\t\tself.filter_ctrl.SetValue(\"\")",
    ),
    "fallback-index-not-clamped": (
        "\t\tnew_index = min(fallback_index, len(self.filtered_entries) - 1)",
        "\t\tnew_index = fallback_index",
    ),
    "save-visible-list-only": (
        "\t\tsave_dictionary_entries(self.dictionary_path, self.entries)",
        "\t\tsave_dictionary_entries(self.dictionary_path, self.filtered_entries)",
    ),
    "skip-after-failed-save": (
        "parent=self)\n\t\t\treturn\n\t\tevent.Skip()\n\n\tdef _save_entries",
        "parent=self)\n\t\t\tevent.Skip()\n\t\t\treturn\n\t\tevent.Skip()\n\n\tdef _save_entries",
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
    path = copy / "dialog.py"
    original = path.read_text(encoding="utf-8")
    for name in names:
        old, new = MUTANTS[name]
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
ls $T/tools
```

Expected:

```text
entry_mutants.py
```

- [ ] **Step 3: Record the baseline suite, the dialog module, the msgids and the golden fixture.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_speech_symbols_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json
```

Expected (889 tests with the P2-5 failure; the dialog module has 21 tests):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 889 tests
FAILED (failures=1, skipped=9)
Ran 21 tests
OK
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

---

### Task 1: Characterize the entries editor and record the golden trace (spec step 1, part A)

Nothing in production changes. The trace tests are red until Step 3 generates the fixture; every other test passes on the current code by construction, and Step 5 shows the net can fail.

- [ ] **Step 1: Replace the dialog test module.** The harness (`_EditorHarness`, refinement 3), the four kept tests unchanged, the 17 tests rewritten onto the harness (refinement 4), the new characterization classes `SpeechSymbolsDialogConstructionTest`, `...CellTextTest`, `...FilterBehaviorTest`, `...AddTest`, `...EditTest`, `...DeleteTest`, `...OkTest` (Q1-Q8 marked, refinement 10), and the trace generator, writer and replay (`write_trace_fixture`, `DictionaryEntriesTraceTest`, refinement 5). 4 spaces; non-ASCII as escapes.

```bash
cat > tests/test_speech_symbols_dialog.py <<'EOF'
"""Tests of the dictionary entries editor (``dialog.SpeechSymbolsDialog``).

The editor is driven only through its wx surface by ``_EditorHarness``: the
module's ``wx`` is a namespace of fake widgets and distinct power-of-two flags,
every widget call goes to one ordered log, the cell text comes from the callback
the dialog hands to its virtual list, and the dictionary is a real CSV file. The
harness never reads or sets the dialog's data attributes, so the same tests pin
the editor before and after its data logic moves into a model (P2-2).

``tests/fixtures/dictionary_entries_trace.json`` is a golden trace recorded from
the pre-P2-2 editor by ``write_trace_fixture()``: 40 seeded sequences of 25
random actions over rows that collide (identical rows, case variants, ``Stra\u00dfe``
and ``STRASSE``). ``DictionaryEntriesTraceTest`` replays it step by step. Never
regenerate it to make a refactor pass.
"""

import csv
import json
import random
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from dictionaries.entries import DictionaryEntry, load_dictionary_entries
from i18n import _
from tests import wx_stub


_MODULE_UNDER_TEST_NAME = wx_stub.SPEECH_DIALOG_MODULE_NAME
_SCOPED_STUB_MODULES = (
    'wx',
    'mammoth',
    'pymupdf',
    'bs4',
    'pypdf',
    'markdown',
    'markdownify',
    'PIL',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'ebooklib',
    'ebooklib.epub',
)


def _restore_module_binding(name: str, existed: bool, module: types.ModuleType | None) -> None:
    if existed:
        sys.modules[name] = module
    else:
        sys.modules.pop(name, None)


def _load_dialog_module() -> types.ModuleType:
    module, _scope = wx_stub.load_speech_dialog()
    return module


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate
CallbackVirtualListCtrl = dialog.CallbackVirtualListCtrl
SpeechSymbolsDialog = dialog.SpeechSymbolsDialog
_NATIVE_DIALOG_BASE = dialog.wx.Dialog


# --- black-box harness ------------------------------------------------------

_FLAG_NAMES = (
    "DEFAULT_DIALOG_STYLE",
    "RESIZE_BORDER",
    "VERTICAL",
    "HORIZONTAL",
    "LEFT",
    "RIGHT",
    "TOP",
    "BOTTOM",
    "EXPAND",
    "ALL",
    "LC_REPORT",
    "BORDER_SUNKEN",
    "LC_SINGLE_SEL",
    "LC_VIRTUAL",
    "OK",
    "CANCEL",
    "APPLY",
    "CLOSE",
    "ICON_ERROR",
)
FLAGS = types.SimpleNamespace(**{name: 1 << bit for bit, name in enumerate(_FLAG_NAMES)})
_EVENT_NAMES = (
    "EVT_TEXT",
    "EVT_BUTTON",
    "EVT_LIST_ITEM_SELECTED",
    "EVT_LIST_ITEM_DESELECTED",
    "EVT_LIST_ITEM_ACTIVATED",
)
ID_OK = 5100
ID_CANCEL = 5101

# zh_TW texts the editor shows (i18n always loads the bundled zh_TW catalog).
TITLE = "\u81ea\u8a02\u5b57\u5178\u7ba1\u7406\u5668"  # Custom Dictionary Manager
DIALOG_STYLE = FLAGS.DEFAULT_DIALOG_STYLE | FLAGS.RESIZE_BORDER
LIST_STYLE = FLAGS.LC_REPORT | FLAGS.BORDER_SUNKEN | FLAGS.LC_SINGLE_SEL | FLAGS.LC_VIRTUAL
ERROR_FLAGS = FLAGS.OK | FLAGS.ICON_ERROR
ERROR_TITLE = "\u932f\u8aa4"  # Error
ADD = "\u65b0\u589e"  # Add
EDIT = "\u7de8\u8f2f"  # Edit
DELETE = "\u522a\u9664"  # Delete
GENERAL = "\u4e00\u822c"  # General
BOPOMOFO = "\u6ce8\u97f3"  # Bopomofo
UNICODE_BRAILLE = "Unicode \u9ede\u5b57"  # Unicode Braille
HEADER = "text,braille,type\r\n"


def _duplicate_message(identifier: str) -> str:
    """zh_TW of 'Source text "{identifier}" already exists.'"""
    return "\u4f86\u6e90\u6587\u5b57\u300c" + identifier + "\u300d\u5df2\u5b58\u5728\u3002"


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
    if entry is None:
        return None
    return [entry.text, entry.braille, entry.entry_type]


class _Event:
    def __init__(self, harness: '_EditorHarness') -> None:
        self._harness = harness
        self.skipped = False

    def Skip(self) -> None:
        self.skipped = True
        self._harness.record("Skip")


class _FakeControl:
    """Fake widget: records ``Bind`` and can fire the bound handlers."""

    def __init__(self, harness: '_EditorHarness', name: str) -> None:
        self._harness = harness
        self.name = name
        self.bindings: list[tuple[str, object]] = []

    def Bind(self, event: str, handler) -> None:
        self._harness.record("Bind", self.name, event)
        self.bindings.append((event, handler))

    def fire(self, event_type: str) -> bool:
        """Call every handler bound to ``event_type``; return whether one called ``Skip``."""
        event = _Event(self._harness)
        for bound_event, handler in list(self.bindings):
            if bound_event == event_type:
                handler(event)
        return event.skipped


class _FakeTextCtrl(_FakeControl):
    def __init__(self, harness: '_EditorHarness') -> None:
        super().__init__(harness, "TextCtrl")
        self.value = ""

    def GetValue(self) -> str:
        return self.value

    def ChangeValue(self, value: str) -> None:
        self._harness.record("ChangeValue", value)
        self.value = value

    def SetValue(self, value: str) -> None:
        """Like wx, ``SetValue`` also sends ``EVT_TEXT`` (``ChangeValue`` does not)."""
        self._harness.record("SetValue", value)
        self.value = value
        self.fire("EVT_TEXT")


class _FakeButton(_FakeControl):
    def __init__(self, harness: '_EditorHarness', name: str, label: str) -> None:
        super().__init__(harness, name)
        self.label = label
        self.enabled = True

    def Enable(self, enable: bool = True) -> None:
        self._harness.record("Enable", self.label, bool(enable))
        self.enabled = bool(enable)

    def SetLabel(self, label: str) -> None:
        self._harness.record("SetLabel", self.name, label)
        self.label = label


class _FakeListCtrl(_FakeControl):
    """Virtual list: keeps the item count, the selected and the focused row.

    Like the pre-P2-2 fake, shrinking the item count below the selected row
    drops the selection; programmatic ``Select`` sends no event.
    """

    def __init__(self, harness: '_EditorHarness', get_item_text) -> None:
        super().__init__(harness, "ListCtrl")
        self.get_item_text = get_item_text
        self.item_count = 0
        self.selected = -1
        self.focused = -1

    def InsertColumn(self, index: int, label: str, width: int = -1) -> None:
        self._harness.record("InsertColumn", index, label, width)

    def SetItemCount(self, count: int) -> None:
        self._harness.record("SetItemCount", count)
        self.item_count = count
        if self.selected >= count:
            self.selected = -1

    def Refresh(self) -> None:
        self._harness.record("Refresh")

    def GetFirstSelected(self) -> int:
        return self.selected

    def Select(self, index: int, on: bool = True) -> None:
        self._harness.record("Select", index, bool(on))
        if on:
            self.selected = index
        elif self.selected == index:
            self.selected = -1

    def Focus(self, index: int) -> None:
        self._harness.record("Focus", index)
        self.focused = index


class _FakeSizer:
    def Add(self, *_args, **_kwargs) -> None:
        pass


class _ScriptedEntryDialog:
    def __init__(self, result: int, entry: DictionaryEntry | None) -> None:
        self._result = result
        self._entry = entry

    def __enter__(self) -> '_ScriptedEntryDialog':
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def ShowModal(self) -> int:
        return self._result

    def get_entry(self) -> DictionaryEntry | None:
        return self._entry


class _EditorHarness:
    """Build the real editor against fake widgets and drive it like a user."""

    def __init__(self, path: Path, on_base_init=None) -> None:
        self.path = path
        self.parent = object()
        self.on_base_init = on_base_init
        self.base_parent = None
        self.log: list[list] = []
        self.buttons: dict[str, _FakeButton] = {}
        self.filter: _FakeTextCtrl | None = None
        self.list: _FakeListCtrl | None = None
        self.ok_button = _FakeButton(self, "ok", "OK")
        self.cancel_button = _FakeButton(self, "cancel", "Cancel")
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
        self.wx = types.SimpleNamespace(
            **vars(FLAGS),
            **{name: name for name in _EVENT_NAMES},
            ID_OK=ID_OK,
            ID_CANCEL=ID_CANCEL,
            ID_APPLY=5102,
            ID_CLOSE=5103,
            NOT_FOUND=-1,
            BoxSizer=lambda _orientation: _FakeSizer(),
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
            Button=self._button,
            MessageBox=self._message_box,
        )

    # construction

    def __enter__(self) -> '_EditorHarness':
        return self.open()

    def __exit__(self, *_exc) -> None:
        self.close()

    def open(self) -> '_EditorHarness':
        stack = self._stack
        try:
            stack.enter_context(patch.object(_NATIVE_DIALOG_BASE, "__init__", self._base_init_function()))
            stack.enter_context(patch.object(dialog, "wx", self.wx))
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            editor = object.__new__(SpeechSymbolsDialog)
            editor.CreateButtonSizer = self._create_button_sizer
            editor.FindWindowById = self._find_window_by_id
            editor.SetSizerAndFit = lambda _sizer: self.record("SetSizerAndFit")
            editor.GetParent = lambda: self.parent
            editor.CentreOnParent = lambda: self.record("CentreOnParent")
            editor.Centre = lambda: self.record("Centre")
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            editor.__init__(self.parent, dictionary_path=self.path)
        except BaseException:
            stack.close()
            raise
        return self

    def close(self) -> None:
        self._stack.close()

    def _base_init_function(self):
        harness = self

        def base_init(_dialog, parent, title=None, style=None):
            harness.record("Dialog.__init__", title, style)
            harness.base_parent = parent
            if harness.on_base_init is not None:
                harness.on_base_init()

        return base_init

    def _static_text(self, _parent, label: str = "") -> object:
        self.record("StaticText", label)
        return object()

    def _text_ctrl(self, _parent) -> _FakeTextCtrl:
        self.record("TextCtrl")
        self.filter = _FakeTextCtrl(self)
        return self.filter

    def _button(self, _parent, label: str = "") -> _FakeButton:
        self.record("Button", label)
        button = _FakeButton(self, label, label)
        self.buttons[label] = button
        return button

    def _list_ctrl(self, _parent, get_item_text, style=None) -> _FakeListCtrl:
        self.record("ListCtrl", style)
        self.list = _FakeListCtrl(self, get_item_text)
        return self.list

    def _create_button_sizer(self, flags: int) -> _FakeSizer:
        self.record("CreateButtonSizer", flags)
        return _FakeSizer()

    def _find_window_by_id(self, window_id: int) -> _FakeButton | None:
        return {ID_OK: self.ok_button, ID_CANCEL: self.cancel_button}.get(window_id)

    def _message_box(self, message: str, caption: str, style: int, parent=None) -> int:
        self.record("MessageBox", message, caption, style)
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
        if not self.script:
            raise AssertionError("the entry dialog opened without a scripted result")
        result, scripted = self.script.pop(0)
        return _ScriptedEntryDialog(result, scripted)

    # recording

    def record(self, *event) -> None:
        self.log.append(list(event))

    def take_log(self) -> list[list]:
        log, self.log = self.log, []
        return log

    # user actions

    def script_entry(self, text: str, braille: str, entry_type: str = "General") -> None:
        """The next entry dialog returns ``ID_OK`` with this entry."""
        self.script.append((ID_OK, DictionaryEntry(text, braille, entry_type)))

    def script_cancel(self) -> None:
        self.script.append((ID_CANCEL, None))

    def type_filter(self, text: str) -> bool:
        self.filter.value = text
        return self.filter.fire("EVT_TEXT")

    def select(self, index: int) -> bool:
        self.list.selected = index
        return self.list.fire("EVT_LIST_ITEM_SELECTED")

    def deselect(self) -> bool:
        self.list.selected = -1
        return self.list.fire("EVT_LIST_ITEM_DESELECTED")

    def click(self, label: str) -> bool:
        """Press the button whose (translated) label is ``_(label)``."""
        return self.buttons[_(label)].fire("EVT_BUTTON")

    def activate(self) -> bool:
        return self.list.fire("EVT_LIST_ITEM_ACTIVATED")

    def press_ok(self) -> bool:
        return self.ok_button.fire("EVT_BUTTON")

    # observations

    def cell(self, row: int, column: int) -> str:
        return self.list.get_item_text(row, column)

    def rows(self) -> list[list[str]]:
        return [[self.cell(row, column) for column in range(3)] for row in range(self.list.item_count)]

    def selected_row(self) -> list[str] | None:
        if self.list.selected < 0:
            return None
        return [self.cell(self.list.selected, column) for column in range(3)]

    def state(self) -> dict:
        return {
            "rows": self.rows(),
            "selected": self.list.selected,
            "focused": self.list.focused,
            "edit": self.buttons[EDIT].enabled,
            "delete": self.buttons[DELETE].enabled,
            "filter": self.filter.value,
        }

    def saved_csv(self) -> str | None:
        if not self.path.is_file():
            return None
        return self.path.read_bytes().decode("utf-8")


def _write_rows(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["text", "braille", "type"])
        writer.writerows(rows)


class _EditorTestCase(unittest.TestCase):
    def make_path(self, name: str = "dictionary.csv") -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name) / name

    def open_editor(self, rows=(), *, path=None, data=None, on_base_init=None, keep_log=False) -> _EditorHarness:
        """Write ``rows`` (or the raw ``data``) to a new CSV and open the editor on it.

        ``rows=None`` leaves the file missing. The construction log is dropped
        unless ``keep_log`` is set.
        """
        if path is None:
            path = self.make_path()
            if data is not None:
                path.write_bytes(data)
            elif rows is not None:
                _write_rows(path, rows)
        harness = _EditorHarness(path, on_base_init=on_base_init)
        harness.open()
        self.addCleanup(harness.close)
        if not keep_log:
            harness.take_log()
        return harness


ALPHA = ["Alpha", "\u2801", "General"]
BETA = ["Beta", "\u2803", "General"]
ALPHA_CELLS = ["Alpha", "\u2801", GENERAL]
BETA_CELLS = ["Beta", "\u2803", GENERAL]


# --- kept tests (unchanged) -------------------------------------------------


class CallbackVirtualListCtrlTest(unittest.TestCase):
    def test_get_item_text_delegates_to_callback(self) -> None:
        control = object.__new__(CallbackVirtualListCtrl)
        control._get_item_text = lambda item, column: f"{item}:{column}"

        self.assertEqual(control.OnGetItemText(4, 2), "4:2")


class DictionaryEntryLoadingTest(unittest.TestCase):
    def test_loads_only_rows_accepted_by_the_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["text", "braille", "type"])
                writer.writerow(["Alpha", "\u2801", "General"])
                writer.writerow(["", "\u2803", "General"])
                writer.writerow(["Zhuyin", "invalid", "Bopomofo"])

            with patch("dictionaries.entries.normalize_zhuyin_sequence", side_effect=ValueError):
                entries = load_dictionary_entries(path)

        self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])

    def test_missing_dictionary_returns_empty_list(self) -> None:
        self.assertEqual(load_dictionary_entries(Path("missing.csv")), [])


class DialogModuleIsolationTest(unittest.TestCase):
    def test_loader_uses_real_dialog_module_without_leaking_stubs(self) -> None:
        had_dialog = 'dialog' in sys.modules
        previous_dialog = sys.modules.get('dialog')
        had_wx = 'wx' in sys.modules
        previous_wx = sys.modules.get('wx')
        stub_dialog = types.ModuleType('dialog')
        sentinel_wx = types.ModuleType('wx')
        sentinel_wx.sentinel = 'preexisting-wx'
        sys.modules['dialog'] = stub_dialog
        sys.modules['wx'] = sentinel_wx
        self.addCleanup(_restore_module_binding, 'dialog', had_dialog, previous_dialog)
        self.addCleanup(_restore_module_binding, 'wx', had_wx, previous_wx)
        before = {name: sys.modules.get(name) for name in _SCOPED_STUB_MODULES}

        loaded_dialog = _load_dialog_module()

        self.assertIs(sys.modules['dialog'], stub_dialog)
        self.assertIs(sys.modules['wx'], sentinel_wx)
        self.assertIsNot(loaded_dialog.wx, sentinel_wx)
        self.assertTrue(hasattr(loaded_dialog.wx, 'Dialog'))
        self.assertEqual(loaded_dialog.wx.NOT_FOUND, -1)
        self.assertNotIn(_MODULE_UNDER_TEST_NAME, sys.modules)
        for name in _SCOPED_STUB_MODULES:
            self.assertIs(sys.modules.get(name), before[name])

        self.doCleanups()

        self.assertIs(sys.modules.get('dialog'), previous_dialog)
        self.assertIs(sys.modules.get('wx'), previous_wx)


# --- pre-P2-2 tests, rewritten onto the harness (same assertions) -----------


class SpeechSymbolsDialogFilterTest(_EditorTestCase):
    def setUp(self) -> None:
        # Beta is added through the entry dialog: the loader drops a Bopomofo row
        # whose braille is not a zhuyin sequence. Row 0 is selected, as before.
        self.harness = self.open_editor([ALPHA])
        self.harness.script_entry("Beta", "Needle", "Bopomofo")
        self.harness.click("Add")
        self.harness.select(0)
        self.alpha = ALPHA_CELLS
        self.beta = ["Beta", "Needle", BOPOMOFO]

    def test_empty_filter_shows_all_entries(self) -> None:
        self.harness.type_filter('')

        self.assertEqual(self.harness.rows(), [self.alpha, self.beta])
        self.assertEqual(self.harness.list.item_count, 2)

    def test_filter_matches_source_text_case_insensitively(self) -> None:
        self.harness.type_filter('ALP')

        self.assertEqual(self.harness.rows(), [self.alpha])

    def test_filter_matches_braille_case_insensitively(self) -> None:
        self.harness.type_filter('NEED')

        self.assertEqual(self.harness.rows(), [self.beta])

    def test_filter_does_not_match_entry_type(self) -> None:
        self.harness.type_filter('bopomofo')

        self.assertEqual(self.harness.rows(), [])

    def test_item_text_uses_visible_entry_and_localized_type_label(self) -> None:
        self.harness.type_filter('bet')

        self.assertEqual(self.harness.cell(0, 0), 'Beta')
        self.assertEqual(self.harness.cell(0, 1), 'Needle')
        self.assertEqual(self.harness.cell(0, 2), '\u6ce8\u97f3')

    def test_filter_preserves_selected_entry_when_it_remains_visible(self) -> None:
        self.harness.select(1)

        self.harness.type_filter("e")

        self.assertEqual(self.harness.selected_row(), self.beta)
        self.assertTrue(self.harness.buttons[EDIT].enabled)
        self.assertTrue(self.harness.buttons[DELETE].enabled)

    def test_filter_falls_back_to_first_entry_when_selection_is_hidden(self) -> None:
        self.harness.select(1)

        self.harness.type_filter("alp")

        self.assertEqual(self.harness.list.selected, 0)
        self.assertEqual(self.harness.rows()[0], self.alpha)

    def test_empty_result_clears_selection_and_disables_edit_and_delete(self) -> None:
        self.harness.type_filter("missing")

        self.assertEqual(self.harness.list.selected, -1)
        self.assertFalse(self.harness.buttons[EDIT].enabled)
        self.assertFalse(self.harness.buttons[DELETE].enabled)

    def test_filter_event_applies_current_text_and_is_skipped(self) -> None:
        skipped = self.harness.type_filter("alp")

        self.assertEqual(self.harness.rows(), [self.alpha])
        self.assertTrue(skipped)


class SpeechSymbolsDialogBuildUiTest(_EditorTestCase):
    def test_build_ui_binds_item_activation_to_edit_handler(self) -> None:
        harness = self.open_editor([ALPHA])
        editor = harness.dialog

        self.assertEqual(
            harness.list.bindings,
            [
                ("EVT_LIST_ITEM_SELECTED", editor._on_selection_changed),
                ("EVT_LIST_ITEM_DESELECTED", editor._on_selection_changed),
                ("EVT_LIST_ITEM_ACTIVATED", editor._on_item_activated),
            ],
        )


class SpeechSymbolsDialogMutationTest(_EditorTestCase):
    def setUp(self) -> None:
        self.harness = self.open_editor([ALPHA, BETA])

    def test_add_matching_entry_keeps_filter_and_selects_new_entry(self) -> None:
        self.harness.type_filter("alp")
        self.harness.script_entry("Alphabet", "\u2801\u2803")

        self.harness.click("Add")

        added = ["Alphabet", "\u2801\u2803", GENERAL]
        self.assertEqual(self.harness.filter.GetValue(), "alp")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, added])
        self.assertEqual(self.harness.selected_row(), added)

    def test_add_nonmatching_entry_clears_filter_and_selects_new_entry(self) -> None:
        self.harness.type_filter("alp")
        self.harness.script_entry("Gamma", "\u281b")

        self.harness.click("Add")

        added = ["Gamma", "\u281b", GENERAL]
        self.assertEqual(self.harness.filter.GetValue(), "")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, BETA_CELLS, added])
        self.assertEqual(self.harness.selected_row(), added)

    def test_edit_visible_entry_updates_full_list_and_preserves_selection(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Better", "\u2803\u2801")

        self.harness.click("Edit")

        updated = ["Better", "\u2803\u2801", GENERAL]
        self.assertEqual(self.harness.rows(), [updated])
        self.assertEqual(self.harness.selected_row(), updated)
        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, updated])

    def test_edit_entry_that_stops_matching_removes_it_from_visible_list(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Gamma", "\u281b")

        self.harness.click("Edit")

        self.assertEqual(self.harness.rows(), [])
        self.assertEqual(self.harness.list.selected, -1)
        self.assertFalse(self.harness.buttons[EDIT].enabled)
        self.assertFalse(self.harness.buttons[DELETE].enabled)
        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, ["Gamma", "\u281b", GENERAL]])

    def test_delete_filtered_entry_selects_nearest_remaining_entry(self) -> None:
        harness = self.harness
        harness.script_entry("Alpine", "\u2801\u2807")
        harness.click("Add")
        alpine = ["Alpine", "\u2801\u2807", GENERAL]
        harness.type_filter("a")
        harness.select(1)

        harness.click("Delete")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, alpine])
        self.assertEqual(harness.list.selected, 1)
        self.assertEqual(harness.rows()[1], alpine)
        harness.type_filter("")
        self.assertEqual(harness.rows(), [ALPHA_CELLS, alpine])

    def test_save_writes_all_entries_not_only_filtered_entries(self) -> None:
        self.harness.type_filter("alp")

        self.assertTrue(self.harness.press_ok())

        with self.harness.path.open("r", newline="", encoding="utf-8") as fp:
            rows = list(csv.DictReader(fp))
        self.assertEqual(
            rows,
            [
                {"text": "Alpha", "braille": "\u2801", "type": "General"},
                {"text": "Beta", "braille": "\u2803", "type": "General"},
            ],
        )

    def test_edit_rejects_duplicate_source_text_outside_filter(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Alpha", "\u2803")
        self.harness.take_log()

        self.harness.click("Edit")

        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        message_boxes = [event for event in self.harness.take_log() if event[0] == "MessageBox"]
        self.assertEqual(len(message_boxes), 1)


# --- new characterization (P2-2 part A) -------------------------------------


class SpeechSymbolsDialogConstructionTest(_EditorTestCase):
    def test_construction_log_is_exact(self) -> None:
        harness = self.open_editor([ALPHA, BETA], keep_log=True)

        self.assertEqual(
            harness.take_log(),
            [
                ["Dialog.__init__", TITLE, DIALOG_STYLE],
                ["StaticText", "\u7be9\u9078\u689d\u4ef6\uff1a"],
                ["TextCtrl"],
                ["Bind", "TextCtrl", "EVT_TEXT"],
                ["StaticText", "\u5b57\u5178\u9805\u76ee"],
                ["ListCtrl", LIST_STYLE],
                ["InsertColumn", 0, "\u4f86\u6e90\u6587\u5b57", 200],
                ["InsertColumn", 1, "\u9ede\u5b57", 230],
                ["InsertColumn", 2, "\u985e\u578b", 120],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_SELECTED"],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_DESELECTED"],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_ACTIVATED"],
                ["Button", ADD],
                ["Button", EDIT],
                ["Button", DELETE],
                ["Bind", ADD, "EVT_BUTTON"],
                ["Bind", EDIT, "EVT_BUTTON"],
                ["Bind", DELETE, "EVT_BUTTON"],
                ["CreateButtonSizer", FLAGS.OK | FLAGS.CANCEL],
                ["SetLabel", "ok", "\u78ba\u5b9a"],
                ["SetLabel", "cancel", "\u53d6\u6d88"],
                ["Bind", "ok", "EVT_BUTTON"],
                ["SetSizerAndFit"],
                ["CentreOnParent"],
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertIs(harness.base_parent, harness.parent)

    def test_native_dialog_exists_before_the_dictionary_is_read(self) -> None:
        path = self.make_path()

        harness = self.open_editor(path=path, on_base_init=lambda: _write_rows(path, [ALPHA]))

        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_empty_dictionary_shows_no_rows_and_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([], keep_log=True)

        self.assertEqual(
            harness.take_log()[-6:],
            [
                ["SetItemCount", 0],
                ["Refresh"],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
            ],
        )
        self.assertEqual(harness.state(), {
            "rows": [], "selected": -1, "focused": -1, "edit": False, "delete": False, "filter": "",
        })

    def test_missing_dictionary_opens_empty_without_creating_the_file(self) -> None:
        harness = self.open_editor(None)

        self.assertEqual(harness.rows(), [])
        self.assertFalse(harness.path.exists())

    def test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog(self) -> None:
        # KNOWN BUG (P2-2 spec, Q8), pinned as it is today, NOT desired: the load error
        # escapes the constructor after the native dialog was created; nothing destroys it.
        path = self.make_path()
        path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")
        harness = _EditorHarness(path)

        with self.assertRaises(UnicodeDecodeError):
            harness.open()

        self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])

    def test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header(self) -> None:
        # KNOWN BUG (P2-2 spec, Q1; data loss), pinned as it is today, NOT desired: the
        # BOM makes the header "\ufefftext", every row is skipped, OK writes the header only.
        harness = self.open_editor(data=b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")

        self.assertEqual(harness.rows(), [])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER)

    def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
        harness = self.open_editor([ALPHA])

        self.assertEqual([event for event, _handler in harness.ok_button.bindings], ["EVT_BUTTON"])
        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: Cancel has no
        # handler of its own, so it discards every edit without asking.
        self.assertEqual(harness.cancel_button.bindings, [])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")


class SpeechSymbolsDialogCellTextTest(_EditorTestCase):
    def test_cells_show_text_braille_and_the_translated_type_label(self) -> None:
        harness = self.open_editor([
            ["Alpha", "\u2801", "General"],
            ["\u3109\u311a\u02cb", "\u3109\u311a\u02cb", "Bopomofo"],
            ["Gamma", "\u281b", "Braille"],
        ])

        self.assertEqual(
            harness.rows(),
            [
                ["Alpha", "\u2801", GENERAL],
                ["\u3109\u311a\u02cb", "\u3109\u311a\u02cb", BOPOMOFO],
                ["Gamma", "\u281b", UNICODE_BRAILLE],
            ],
        )

    def test_unknown_column_raises_value_error(self) -> None:
        harness = self.open_editor([ALPHA])

        with self.assertRaises(ValueError) as caught:
            harness.cell(0, 3)

        self.assertEqual(str(caught.exception), "Unknown column: 3")


class SpeechSymbolsDialogFilterBehaviorTest(_EditorTestCase):
    def test_filter_uses_casefold_not_lower(self) -> None:
        harness = self.open_editor([["Stra\u00dfe", "\u280e", "General"], ["STRASSE", "", "General"]])

        harness.type_filter("STRASSE")
        self.assertEqual([row[0] for row in harness.rows()], ["Stra\u00dfe", "STRASSE"])
        harness.type_filter("\u00df")
        self.assertEqual([row[0] for row in harness.rows()], ["Stra\u00dfe", "STRASSE"])

    def test_whitespace_filter_is_literal(self) -> None:
        harness = self.open_editor([["New York", "\u281d", "General"], ALPHA])

        harness.type_filter(" ")

        self.assertEqual([row[0] for row in harness.rows()], ["New York"])

    def test_filter_does_not_match_the_type_label(self) -> None:
        harness = self.open_editor([ALPHA, BETA])

        harness.type_filter(GENERAL)

        self.assertEqual(harness.rows(), [])

    def test_selection_is_kept_by_equality_so_identical_rows_select_the_first(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], ["b", "\u2803", "General"], ["a", "\u2801", "General"]])
        harness.select(2)

        harness.type_filter("a")

        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], ["a", "\u2801", GENERAL]])
        self.assertEqual(harness.list.selected, 0)

    def test_previous_selection_is_read_from_the_old_visible_list(self) -> None:
        harness = self.open_editor([["b1", "\u2803", "General"], ["a1", "\u2801", "General"], ["a2", "\u2801", "General"]])
        harness.select(2)

        harness.type_filter("a")

        self.assertEqual(harness.selected_row(), ["a2", "\u2801", GENERAL])
        self.assertEqual(harness.list.selected, 1)

    def test_filter_log_with_a_kept_selection_is_exact(self) -> None:
        harness = self.open_editor([ALPHA, BETA, ["Alpine", "\u2801\u2807", "General"]])
        harness.select(2)
        harness.take_log()

        harness.type_filter("alp")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Skip"],
            ],
        )
        self.assertEqual(harness.state()["focused"], 1)

    def test_empty_result_log_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.take_log()

        harness.type_filter("zzz")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 0],
                ["Refresh"],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
                ["Skip"],
            ],
        )

    def test_filter_that_keeps_the_selected_row_index_deselects_it_first(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.take_log()

        harness.type_filter("a")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Skip"],
            ],
        )


class SpeechSymbolsDialogAddTest(_EditorTestCase):
    def test_cancel_changes_nothing(self) -> None:
        harness = self.open_editor([ALPHA])
        before = harness.state()
        harness.script_cancel()

        harness.click("Add")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", None]])
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_duplicate_of_a_hidden_entry_is_rejected_with_the_exact_message(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("bet")
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u281b", "Braille")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry
        # is discarded; the entry dialog is not opened again.
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.script, [])

    def test_case_different_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.script_entry("alpha", "\u2801")

        harness.click("Add")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["alpha", "\u2801", GENERAL]])

    def test_new_entry_is_appended_at_the_end_selected_and_focused(self) -> None:
        harness = self.open_editor([BETA, ALPHA])
        harness.script_entry("Aardvark", "\u2801\u2801")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["SetItemCount", 3],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 2, True],
                ["Focus", 2],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [BETA_CELLS, ALPHA_CELLS, ["Aardvark", "\u2801\u2801", GENERAL]])
        self.assertEqual((harness.list.selected, harness.list.focused), (2, 2))

    def test_nonmatching_filter_is_cleared_with_change_value_before_the_list_update(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("alp")
        harness.take_log()
        harness.script_entry("Gamma", "\u281b")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["ChangeValue", ""],
                ["SetItemCount", 3],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 2, True],
                ["Focus", 2],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )

    def test_matching_filter_is_kept_without_touching_the_filter_box(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("alp")
        harness.take_log()
        harness.script_entry("Alpine", "\u2801\u2807")

        harness.click("Add")

        log = harness.take_log()
        self.assertNotIn("ChangeValue", [event[0] for event in log])
        self.assertNotIn("SetValue", [event[0] for event in log])
        self.assertEqual(harness.filter.value, "alp")
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Alpine", "\u2801\u2807", GENERAL]])


class SpeechSymbolsDialogEditTest(_EditorTestCase):
    def test_edit_button_opens_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.take_log()
        harness.script_cancel()

        harness.click("Edit")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", BETA]])
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_activation_edits_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.take_log()
        harness.script_entry("Bravo", "\u2803\u2817")

        harness.activate()

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", BETA],
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, False],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Bravo", "\u2803\u2817", GENERAL]])

    def test_no_selection_opens_nothing(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.deselect()
        harness.take_log()

        harness.click("Edit")
        harness.activate()

        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.entry_dialog_parents, [])

    def test_cancel_changes_nothing(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        before = harness.state()
        harness.script_cancel()

        harness.click("Edit")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", ALPHA]])
        self.assertEqual(harness.state(), before)

    def test_same_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.script_entry("Alpha", "\u2801\u2801", "Braille")

        harness.click("Edit")

        self.assertEqual(harness.rows(), [["Alpha", "\u2801\u2801", UNICODE_BRAILLE], BETA_CELLS])
        self.assertEqual(harness.list.selected, 0)

    def test_duplicate_is_rejected_with_the_exact_message_and_nothing_changes(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u2803")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", BETA],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
        self.assertEqual(harness.state(), before)

    def test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "General"]])
        harness.select(2)
        harness.script_entry("a", "\u2803")

        harness.click("Edit")

        # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the other
        # identical row makes its own text a duplicate.
        self.assertEqual(harness.take_log()[-1], ["MessageBox", _duplicate_message("a"), ERROR_TITLE, ERROR_FLAGS])
        harness.script_entry("c", "\u2809")

        harness.click("Edit")

        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], BETA_CELLS, ["c", "\u2809", GENERAL]])
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "a,\u2801,General\r\nBeta,\u2803,General\r\nc,\u2809,General\r\n",
        )

    def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
        harness = self.open_editor([ALPHA, ["Alpine", "\u2801\u2807", "General"], BETA])
        harness.type_filter("alp")
        harness.select(1)
        harness.take_log()
        harness.script_entry("Gamma", "\u281b")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", ["Alpine", "\u2801\u2807", "General"]],
                ["SetItemCount", 1],
                ["Refresh"],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.filter.value, "alp")
        self.assertEqual(harness.rows(), [ALPHA_CELLS])


class SpeechSymbolsDialogDeleteTest(_EditorTestCase):
    def test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index(self) -> None:
        harness = self.open_editor([ALPHA, BETA, ["Gamma", "\u281b", "General"]])
        harness.select(1)
        harness.take_log()

        harness.click("Delete")

        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: no confirmation.
        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, False],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Gamma", "\u281b", GENERAL]])

    def test_deleting_the_last_row_selects_the_new_last_row(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)

        harness.click("Delete")

        self.assertEqual(harness.rows(), [ALPHA_CELLS])
        self.assertEqual((harness.list.selected, harness.list.focused), (0, 0))

    def test_deleting_the_only_row_clears_the_selection(self) -> None:
        harness = self.open_editor([ALPHA])

        harness.click("Delete")

        self.assertEqual(harness.state(), {
            "rows": [], "selected": -1, "focused": 0, "edit": False, "delete": False, "filter": "",
        })

    def test_no_selection_deletes_nothing(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.deselect()
        harness.take_log()

        harness.click("Delete")

        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_identical_rows_delete_removes_the_first_equal_row(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "Braille"], ["a", "\u2801", "General"]])
        harness.select(3)

        harness.click("Delete")

        # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the first equal
        # row goes, not the selected one; the remaining equal row gets the selection.
        self.assertEqual(
            harness.rows(),
            [BETA_CELLS, ["a", "\u2801", UNICODE_BRAILLE], ["a", "\u2801", GENERAL]],
        )
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Beta,\u2803,General\r\na,\u2801,Braille\r\na,\u2801,General\r\n",
        )


class SpeechSymbolsDialogOkTest(_EditorTestCase):
    def test_ok_saves_the_full_list_in_order_and_closes(self) -> None:
        harness = self.open_editor([BETA, ALPHA])
        harness.script_entry("Gamma", "\u281b", "Braille")
        harness.click("Add")
        harness.type_filter("gam")
        harness.take_log()

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [["Skip"]])
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Beta,\u2803,General\r\nAlpha,\u2801,General\r\nGamma,\u281b,Braille\r\n",
        )

    def test_unchanged_dictionary_is_rewritten_in_normalized_form(self) -> None:
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file and drops what the loader skipped or stripped.
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
            ",\u2803,General\n"
            "Zhuyin,invalid,Bopomofo\n"
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_missing_parent_directory_is_created(self) -> None:
        path = self.make_path("nested") / "deeper" / "dictionary.csv"
        harness = self.open_editor(path=path)
        harness.script_entry("Alpha", "\u2801")
        harness.click("Add")

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\n")

    def test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.script_entry("Beta", "\u2803")
        harness.click("Add")
        harness.path.unlink()
        harness.path.mkdir()
        try:
            harness.path.open("w", encoding="utf-8")
        except OSError as error:
            expected_error = error  # its text differs between Linux and Windows
        else:
            self.fail("opening a directory for writing did not fail")
        harness.take_log()

        skipped = harness.press_ok()

        self.assertFalse(skipped)
        self.assertEqual(
            harness.take_log(),
            [["MessageBox", "\u5132\u5b58\u5931\u6557\uff1a" + str(expected_error), ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        harness.path.rmdir()
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.script_entry("\ud800", "\u2801")
        harness.click("Edit")
        harness.take_log()

        # KNOWN BUG (P2-2 spec, Q7), pinned as it is today, NOT desired: a non-OSError
        # escapes the OK handler without a message.
        with self.assertRaises(UnicodeEncodeError):
            harness.press_ok()

        self.assertEqual(harness.take_log(), [])
        # KNOWN BUG (P2-2 spec, Q3; data loss), pinned as it is today, NOT desired: the
        # file was truncated before the failing row, so Beta is gone from disk.
        self.assertEqual(harness.saved_csv(), HEADER)


# --- golden trace -----------------------------------------------------------

TRACE_PATH = Path(__file__).resolve().parent / "fixtures" / "dictionary_entries_trace.json"
TRACE_SEQUENCES = 40
TRACE_ACTIONS = 25
TRACE_CSV = (
    "text,braille,type\r\n"
    "a,\u2801,General\r\n"
    " Ab , SS ,General\r\n"
    "a,\u2801,General\r\n"
    ",\u2803,General\r\n"
    "Stra\u00dfe,\u280e,Braille\r\n"
    "STRASSE,,Unknown\r\n"
    "zz,ab,Bopomofo\r\n"
)
_TRACE_TEXTS = ("a", "A", "ab", "Ab", "Stra\u00dfe", "STRASSE", "b", "ss")
_TRACE_BRAILLE = ("\u2801", "ab", "", "SS", "\u2803")
_TRACE_TYPES = ("General", "Bopomofo", "Braille")
_TRACE_FILTERS = ("", "", "a", "A", "b", "ab", "ss", "STRASSE", "\u00df", " ", "\u2801", "x", "General")
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")


def _random_trace_action(rng: random.Random, harness: _EditorHarness, index: int) -> list:
    kind = rng.choice(_TRACE_KINDS)
    if kind == "filter":
        return ["filter", rng.choice(_TRACE_FILTERS)]
    if kind == "select":
        count = harness.list.item_count
        return ["select", rng.randrange(count)] if count else ["deselect"]
    if kind in ("deselect", "delete"):
        return [kind]
    if rng.random() < 0.2:
        return [kind, None]
    text = f"n{index}" if rng.random() < 0.3 else rng.choice(_TRACE_TEXTS)
    return [kind, [text, rng.choice(_TRACE_BRAILLE), rng.choice(_TRACE_TYPES)]]


def _perform_trace_action(harness: _EditorHarness, action: list) -> None:
    kind = action[0]
    if kind == "filter":
        harness.type_filter(action[1])
    elif kind == "select":
        harness.select(action[1])
    elif kind == "deselect":
        harness.deselect()
    elif kind == "delete":
        harness.click("Delete")
    else:
        if action[1] is None:
            harness.script_cancel()
        else:
            harness.script_entry(*action[1])
        if kind == "add":
            harness.click("Add")
        elif kind == "edit":
            harness.click("Edit")
        else:
            harness.activate()
        harness.script.clear()


def _run_trace_sequence(path: Path, next_action) -> list[dict]:
    """Open the editor on ``TRACE_CSV``, run 25 actions and OK; return every step's observations.

    A step's ``state`` has no ``rows`` when the visible rows did not change
    since the previous step (keeps the fixture small).
    """
    path.write_bytes(TRACE_CSV.encode("utf-8"))
    with _EditorHarness(path) as harness:
        steps = [{"action": ["open"], "log": harness.take_log(), "state": harness.state()}]
        for index in range(TRACE_ACTIONS):
            action = next_action(harness, index)
            _perform_trace_action(harness, action)
            steps.append({"action": action, "log": harness.take_log(), "state": harness.state()})
        harness.press_ok()
        steps.append({
            "action": ["ok"],
            "log": harness.take_log(),
            "state": harness.state(),
            "csv": harness.saved_csv(),
        })
    previous_rows = None
    for step in steps:
        rows = step["state"]["rows"]
        if rows == previous_rows:
            del step["state"]["rows"]
        previous_rows = rows
    return steps


def write_trace_fixture(path: Path = TRACE_PATH) -> None:
    """Record the golden trace. Run once, on the pre-P2-2 editor; never to make a test pass."""
    sequences = []
    _DIALOG_SCOPE.activate()
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for seed in range(TRACE_SEQUENCES):
                rng = random.Random(seed)
                sequences.append(_run_trace_sequence(
                    Path(temp_dir) / f"trace{seed}.csv",
                    lambda harness, index, rng=rng: _random_trace_action(rng, harness, index),
                ))
    finally:
        _DIALOG_SCOPE.deactivate()
    lines = ["["]
    for seed, steps in enumerate(sequences):
        lines.append("[")
        lines.append(",\n".join(json.dumps(step, ensure_ascii=False, separators=(",", ":")) for step in steps))
        lines.append("]," if seed < len(sequences) - 1 else "]")
    lines.append("]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


class DictionaryEntriesTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sequences = json.loads(TRACE_PATH.read_text(encoding="utf-8"))

    def test_fixture_has_40_sequences_of_27_steps(self) -> None:
        self.assertEqual(len(self.sequences), TRACE_SEQUENCES)
        for steps in self.sequences:
            self.assertEqual([step["action"][0] for step in steps[::26]], ["open", "ok"])
            self.assertEqual(len(steps), TRACE_ACTIONS + 2)

    def test_replay_matches_every_recorded_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for seed, expected in enumerate(self.sequences):
                with self.subTest(seed=seed):
                    actual = _run_trace_sequence(
                        Path(temp_dir) / f"trace{seed}.csv",
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                    )
                    for index, (got, want) in enumerate(zip(actual, expected)):
                        self.assertEqual(got, want, f"seed {seed}, step {index}: {want['action']}")


if __name__ == '__main__':
    unittest.main()
EOF
```

- [ ] **Step 2: Run it: only the trace tests fail.**

```bash
$PY -m unittest tests.test_speech_symbols_dialog 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the fixture does not exist yet; the other 62 tests pass):

```text
ERROR: test_fixture_has_40_sequences_of_27_steps (tests.test_speech_symbols_dialog.DictionaryEntriesTraceTest.test_fixture_has_40_sequences_of_27_steps)
FileNotFoundError: [Errno 2] No such file or directory: 'client/tests/fixtures/dictionary_entries_trace.json'
ERROR: test_replay_matches_every_recorded_step (tests.test_speech_symbols_dialog.DictionaryEntriesTraceTest.test_replay_matches_every_recorded_step)
FileNotFoundError: [Errno 2] No such file or directory: 'client/tests/fixtures/dictionary_entries_trace.json'
Ran 64 tests
FAILED (errors=2)
```

- [ ] **Step 3: Record the golden trace from the unmodified editor.** Run once. If the sha256 differs from `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, stop: the editor or the harness differs from the dry run; do not commit a different fixture.

```bash
$PY -c "from tests import test_speech_symbols_dialog as module; module.write_trace_fixture()"
sha256sum tests/fixtures/dictionary_entries_trace.json
wc -c < tests/fixtures/dictionary_entries_trace.json
git -C $REPO diff --stat -- client/dialog.py client/dictionaries
```

Expected (the production code is untouched):

```text
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
300540
```

- [ ] **Step 4: Run the module again.**

```bash
$PY -m unittest tests.test_speech_symbols_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (4 kept + 17 rewritten + 43 new):

```text
Ran 64 tests
OK
```

- [ ] **Step 5: Show that the net can fail.** Each mutant edits `dialog.py` in a copy of `client/`; the repo stays unchanged.

```bash
$PY -B $T/tools/entry_mutants.py $REPO/client $T/mutants
git -C $REPO status --short
```

Expected (every mutant fails at least one test, counted per failing subtest; `status` lists only the rewritten module and the new fixture):

```text
lower-instead-of-casefold: failures=31 errors=0
filter-matches-type: failures=31 errors=0
selection-read-after-refilter: failures=25 errors=0
selection-restored-by-identity: failures=12 errors=0
edit-replaces-first-equal: failures=2 errors=0
delete-by-identity: failures=1 errors=0
duplicate-check-ignores-case: failures=30 errors=0
duplicate-check-visible-only: failures=22 errors=0
duplicate-check-without-self-exclusion: failures=8 errors=0
add-clears-matching-filter: failures=11 errors=0
edit-clears-filter: failures=41 errors=0
add-uses-set-value: failures=27 errors=0
fallback-index-not-clamped: failures=21 errors=0
save-visible-list-only: failures=25 errors=0
skip-after-failed-save: failures=1 errors=0
 M client/tests/test_speech_symbols_dialog.py
?? client/tests/fixtures/dictionary_entries_trace.json
```

- [ ] **Step 6: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (889 + 43):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 932 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_speech_symbols_dialog.py client/tests/fixtures/dictionary_entries_trace.json
git -C $REPO commit -q -F - <<'EOF'
test: characterize dictionary entries editor

Drive SpeechSymbolsDialog only through its wx surface (fake widgets, one
ordered call log, the virtual-list cell callback, a real CSV) so the same
tests pin it before and after P2-2. Rewrite the 17 existing dialog tests
onto the harness and add 43 characterization tests, including the known
quirks Q1-Q8 of the P2-2 spec (pinned, not fixed).

Add the golden trace tests/fixtures/dictionary_entries_trace.json
(40 seeded sequences of 25 actions, recorded from the unmodified editor;
sha256 f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize dictionary entries editor
```

---

### Task 2: Add the wx-free model (spec step 2, part B)

- [ ] **Step 1: Write the failing tests.** Plain `unittest`, tabs, no wx, no stub scope: `DuplicateEntryErrorTest` (1), `EntryListUpdateTest` (1), `ConstructionTest` (3: empty default, copied input with all rows visible, tuple snapshots), `VisibleEntryTest` (1: `None`, -1 and count give `None`), `MatchesTest` (1: casefold text or braille, literal space, type and label never matched), `CellTextTest` (4: columns and zh_TW labels, visible rows, unknown-type fallback, unknown column), `SourceTextExistsTest` (1: exact, hidden rows, identity exclusion), `ApplyFilterTest` (6), `AddTest` (5), `ReplaceTest` (7), `RemoveTest` (5), `LoadSaveTest` (3) and the AST import guard (1). Every D4 rule has an identical-row case; `replace`/`remove` reject -1 and the count with `IndexError` and change nothing.

```bash
cat > tests/test_dictionary_entry_list_model.py <<'EOF'
import ast
import tempfile
import unittest
from pathlib import Path

from dictionaries.entries import DictionaryEntry
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate

MODULE_PATH = Path(__file__).resolve().parents[1] / "dictionaries" / "entry_list_model.py"
GENERAL = "\u4e00\u822c"
BOPOMOFO = "\u6ce8\u97f3"


def _entry(text: str, braille: str = "\u2801", entry_type: str = "General") -> DictionaryEntry:
	return DictionaryEntry(text, braille, entry_type)


class _ModelTestCase(unittest.TestCase):
	def assertUnchanged(self, model: DictionaryEntryListModel, entries, visible, filter_text: str) -> None:
		self.assertEqual(model.entries, tuple(entries))
		self.assertEqual(model.visible_entries, tuple(visible))
		self.assertEqual(model.filter_text, filter_text)

	def assertSameObjects(self, actual, expected) -> None:
		self.assertEqual([id(entry) for entry in actual], [id(entry) for entry in expected])


class DuplicateEntryErrorTest(unittest.TestCase):
	def test_is_a_value_error_that_keeps_the_identifier(self) -> None:
		error = DuplicateEntryError("Alpha")

		self.assertIsInstance(error, ValueError)
		self.assertEqual(error.identifier, "Alpha")
		self.assertEqual(error.args, ("Alpha",))


class EntryListUpdateTest(unittest.TestCase):
	def test_is_frozen_and_does_not_clear_the_filter_by_default(self) -> None:
		update = EntryListUpdate(2)

		self.assertEqual(update, EntryListUpdate(selection=2, filter_cleared=False))
		with self.assertRaises(AttributeError):
			update.selection = 0


class ConstructionTest(_ModelTestCase):
	def test_default_model_is_empty(self) -> None:
		model = DictionaryEntryListModel()

		self.assertUnchanged(model, [], [], "")
		self.assertEqual(model.visible_count, 0)

	def test_entries_are_copied_and_all_visible(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta")
		source = [alpha, beta]

		model = DictionaryEntryListModel(source)
		source.append(_entry("Gamma"))

		self.assertUnchanged(model, [alpha, beta], [alpha, beta], "")
		self.assertSameObjects(model.visible_entries, [alpha, beta])
		self.assertEqual(model.visible_count, 2)

	def test_returned_tuples_are_snapshots(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha")])
		entries, visible = model.entries, model.visible_entries

		model.add(_entry("Beta"))

		self.assertIsInstance(entries, tuple)
		self.assertEqual(len(entries), 1)
		self.assertEqual(len(visible), 1)


class VisibleEntryTest(unittest.TestCase):
	def test_returns_the_visible_object_or_none_out_of_range(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta")
		model = DictionaryEntryListModel([alpha, beta])
		model.apply_filter("bet")

		self.assertIs(model.visible_entry(0), beta)
		for index in (None, -1, 1):
			with self.subTest(index=index):
				self.assertIsNone(model.visible_entry(index))


class MatchesTest(unittest.TestCase):
	def test_casefolded_substring_of_text_or_braille(self) -> None:
		cases = [
			(_entry("Stra\u00dfe", "\u280e"), "STRASSE", True),
			(_entry("STRASSE", ""), "\u00df", True),
			(_entry("Alpha", "Needle"), "need", True),
			(_entry("Alpha", "\u2801"), "PH", True),
			(_entry("New York"), " ", True),
			(_entry("Alpha"), " ", False),
			(_entry("Alpha", "\u2801", "Bopomofo"), "bopomofo", False),
			(_entry("Alpha", "\u2801", "General"), GENERAL, False),
			(_entry("Alpha"), "", True),
		]
		for entry, filter_text, expected in cases:
			with self.subTest(entry=entry, filter_text=filter_text):
				self.assertIs(DictionaryEntryListModel.matches(entry, filter_text), expected)


class CellTextTest(unittest.TestCase):
	def test_columns_show_text_braille_and_the_translated_type_label(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha", "\u2801", "General"), _entry("Beta", "\u3105\u311a\u02c7", "Bopomofo")])

		self.assertEqual([model.cell_text(0, column) for column in range(3)], ["Alpha", "\u2801", GENERAL])
		self.assertEqual([model.cell_text(1, column) for column in range(3)], ["Beta", "\u3105\u311a\u02c7", BOPOMOFO])

	def test_rows_are_visible_rows(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha"), _entry("Beta")])
		model.apply_filter("bet")

		self.assertEqual(model.cell_text(0, 0), "Beta")
		with self.assertRaises(IndexError):
			model.cell_text(1, 0)

	def test_unknown_type_is_shown_as_is(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha", "\u2801", "Custom")])

		self.assertEqual(model.cell_text(0, 2), "Custom")

	def test_unknown_column_raises_value_error(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha")])

		with self.assertRaises(ValueError) as caught:
			model.cell_text(0, 3)

		self.assertEqual(str(caught.exception), "Unknown column: 3")


class SourceTextExistsTest(unittest.TestCase):
	def test_exact_text_over_the_full_list_with_identity_exclusion(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta", "\u2803")
		twin = _entry("Alpha")
		model = DictionaryEntryListModel([alpha, beta])
		model.apply_filter("bet")

		self.assertTrue(model.source_text_exists("Alpha"))
		self.assertFalse(model.source_text_exists("alpha"))
		self.assertFalse(model.source_text_exists("Alpha", exclude_entry=alpha))
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))


class ApplyFilterTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.alpine = _entry("Alpine", "\u2801\u2807")
		self.model = DictionaryEntryListModel([self.alpha, self.beta, self.alpine])

	def test_filter_keeps_matching_entries_in_full_list_order(self) -> None:
		update = self.model.apply_filter("alp")

		self.assertEqual(update, EntryListUpdate(0))
		self.assertUnchanged(self.model, [self.alpha, self.beta, self.alpine], [self.alpha, self.alpine], "alp")
		self.assertEqual(self.model.visible_count, 2)

	def test_empty_filter_shows_everything(self) -> None:
		self.model.apply_filter("alp")

		self.model.apply_filter("")

		self.assertSameObjects(self.model.visible_entries, [self.alpha, self.beta, self.alpine])

	def test_selection_is_read_from_the_visible_list_before_the_change(self) -> None:
		self.model.apply_filter("")

		update = self.model.apply_filter("alp", selected_index=2)

		self.assertEqual(update, EntryListUpdate(1))

	def test_hidden_or_missing_selection_falls_back_to_the_first_row(self) -> None:
		for selected_index in (1, None, -1, 3):
			with self.subTest(selected_index=selected_index):
				self.model.apply_filter("")

				self.assertEqual(self.model.apply_filter("alp", selected_index=selected_index), EntryListUpdate(0))

	def test_selection_is_restored_by_equality_so_identical_rows_select_the_first(self) -> None:
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])

		update = model.apply_filter("a", selected_index=2)

		self.assertEqual(update, EntryListUpdate(0))

	def test_empty_result_has_no_selection(self) -> None:
		self.assertEqual(self.model.apply_filter("zzz", selected_index=0), EntryListUpdate(None))
		self.assertEqual(self.model.visible_count, 0)


class AddTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.model = DictionaryEntryListModel([self.alpha, self.beta])

	def test_appends_at_the_end_and_selects_the_new_entry(self) -> None:
		gamma = _entry("Gamma", "\u281b")

		update = self.model.add(gamma)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.beta, gamma])

	def test_matching_filter_is_kept(self) -> None:
		self.model.apply_filter("alp")
		alpine = _entry("Alpine", "\u2801\u2807")

		update = self.model.add(alpine)

		self.assertEqual(update, EntryListUpdate(1, filter_cleared=False))
		self.assertUnchanged(self.model, [self.alpha, self.beta, alpine], [self.alpha, alpine], "alp")

	def test_nonmatching_filter_is_cleared(self) -> None:
		self.model.apply_filter("alp")
		gamma = _entry("Gamma", "\u281b")

		update = self.model.add(gamma)

		self.assertEqual(update, EntryListUpdate(2, filter_cleared=True))
		self.assertUnchanged(self.model, [self.alpha, self.beta, gamma], [self.alpha, self.beta, gamma], "")

	def test_duplicate_of_a_hidden_entry_raises_and_changes_nothing(self) -> None:
		self.model.apply_filter("bet")

		with self.assertRaises(DuplicateEntryError) as caught:
			self.model.add(_entry("Alpha", "\u281b", "Braille"))

		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.beta], "bet")

	def test_case_different_text_is_not_a_duplicate(self) -> None:
		self.model.add(_entry("alpha"))

		self.assertEqual([entry.text for entry in self.model.entries], ["Alpha", "Beta", "alpha"])


class ReplaceTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.alpine = _entry("Alpine", "\u2801\u2807")
		self.beta = _entry("Beta", "\u2803")
		self.model = DictionaryEntryListModel([self.alpha, self.alpine, self.beta])

	def test_replaces_in_place_and_selects_the_new_entry(self) -> None:
		bravo = _entry("Bravo", "\u2803\u2817")

		update = self.model.replace(2, bravo)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.alpine, bravo])

	def test_same_text_is_accepted(self) -> None:
		changed = _entry("Alpha", "\u2801\u2801", "Braille")

		self.model.replace(0, changed)

		self.assertSameObjects(self.model.entries, [changed, self.alpine, self.beta])

	def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
		self.model.apply_filter("alp")
		gamma = _entry("Gamma", "\u281b")

		update = self.model.replace(1, gamma)

		self.assertEqual(update, EntryListUpdate(0))
		self.assertUnchanged(self.model, [self.alpha, gamma, self.beta], [self.alpha], "alp")

	def test_hidden_result_with_nothing_left_has_no_selection(self) -> None:
		self.model.apply_filter("bet")

		update = self.model.replace(0, _entry("Gamma", "\u281b"))

		self.assertEqual(update, EntryListUpdate(None))
		self.assertEqual(self.model.visible_count, 0)

	def test_duplicate_raises_and_changes_nothing(self) -> None:
		self.model.apply_filter("bet")

		with self.assertRaises(DuplicateEntryError) as caught:
			self.model.replace(0, _entry("Alpha", "\u2803"))

		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.beta], "bet")

	def test_identical_rows_replace_the_visible_object_but_cannot_keep_their_text(self) -> None:
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])

		with self.assertRaises(DuplicateEntryError):
			model.replace(2, _entry("a", "\u2803"))
		c = _entry("c")
		update = model.replace(2, c)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[0], first)
		self.assertIs(model.entries[2], c)

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		self.model.apply_filter("alp")
		for index in (-1, 2):
			with self.subTest(index=index):
				with self.assertRaises(IndexError):
					self.model.replace(index, _entry("Gamma"))

				self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.alpha, self.alpine], "alp")


class RemoveTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.gamma = _entry("Gamma", "\u281b")
		self.model = DictionaryEntryListModel([self.alpha, self.beta, self.gamma])

	def test_selects_the_row_now_at_the_same_index(self) -> None:
		update = self.model.remove(1)

		self.assertEqual(update, EntryListUpdate(1))
		self.assertSameObjects(self.model.entries, [self.alpha, self.gamma])

	def test_removing_the_last_row_selects_the_new_last_row(self) -> None:
		self.assertEqual(self.model.remove(2), EntryListUpdate(1))

	def test_removing_the_only_visible_row_has_no_selection(self) -> None:
		self.model.apply_filter("gam")

		self.assertEqual(self.model.remove(0), EntryListUpdate(None))
		self.assertUnchanged(self.model, [self.alpha, self.beta], [], "gam")

	def test_identical_rows_remove_the_first_equal_and_select_the_remaining_twin(self) -> None:
		first, braille, second = _entry("a"), _entry("a", "\u2801", "Braille"), _entry("a")
		beta = _entry("Beta", "\u2803")
		model = DictionaryEntryListModel([first, beta, braille, second])

		update = model.remove(3)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(model.entries, [beta, braille, second])

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		for index in (-1, 3):
			with self.subTest(index=index):
				with self.assertRaises(IndexError):
					self.model.remove(index)

				self.assertUnchanged(
					self.model, [self.alpha, self.beta, self.gamma], [self.alpha, self.beta, self.gamma], ""
				)


class LoadSaveTest(unittest.TestCase):
	def setUp(self) -> None:
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.directory = Path(temp_dir.name)

	def test_load_of_a_missing_file_gives_an_empty_model(self) -> None:
		model = DictionaryEntryListModel.load(self.directory / "missing.csv")

		self.assertEqual(model.entries, ())
		self.assertEqual(model.filter_text, "")

	def test_save_writes_the_full_list_while_filtered_and_load_reads_it_back(self) -> None:
		path = self.directory / "nested" / "dictionary.csv"
		model = DictionaryEntryListModel([_entry("Beta", "\u2803"), _entry("Alpha", "\u2801", "Braille")])
		model.apply_filter("alp")

		model.save(path)

		self.assertEqual(
			path.read_bytes().decode("utf-8"),
			"text,braille,type\r\nBeta,\u2803,General\r\nAlpha,\u2801,Braille\r\n",
		)
		self.assertEqual(DictionaryEntryListModel.load(path).entries, model.entries)

	def test_load_errors_propagate(self) -> None:
		path = self.directory / "broken.csv"
		path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")

		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)


class ImportGuardTest(unittest.TestCase):
	def test_model_imports_no_ui_or_translation_module(self) -> None:
		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name for alias in node.names)
			elif isinstance(node, ast.ImportFrom):
				imported.add(node.module or "")

		self.assertEqual(imported, {"__future__", "collections.abc", "dataclasses", "pathlib", "dictionaries.entries"})
		forbidden = ("wx", "gui", "dialog", "ui", "settings", "i18n")
		for name in imported:
			with self.subTest(name=name):
				self.assertNotIn(name.split(".")[0], forbidden)


if __name__ == "__main__":
	unittest.main()
EOF
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_dictionary_entry_list_model 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the module does not exist yet):

```text
ERROR: test_dictionary_entry_list_model (unittest.loader._FailedTest.test_dictionary_entry_list_model)
ImportError: Failed to import test module: test_dictionary_entry_list_model
ModuleNotFoundError: No module named 'dictionaries.entry_list_model'
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Add `client/dictionaries/entry_list_model.py`.** The spec's API and semantics, each method a transcription of today's dialog code (refinement 7). Tabs. Not used by production code yet.

```bash
cat > dictionaries/entry_list_model.py <<'EOF'
"""wx-free model of the dictionary entries editor (the "Custom Dictionary Manager" in ``dialog.py``).

The model owns the full entry list in file order, the filter text and the
visible (filtered) list. The dialog owns the widgets and the selected row: it
passes the selected visible index into each call and renders the returned
``EntryListUpdate``. Nothing here imports wx or i18n; the dialog shows the
messages.

Comparison rules, kept from the pre-P2-2 dialog (a file may hold identical rows):

* the selection is restored by equality: the first visible entry equal to the
  previous one wins;
* ``replace`` swaps the full-list item that *is* the visible entry (identity);
* ``remove`` removes the first full-list entry *equal* to the visible one;
* the duplicate check compares ``text`` exactly (case-sensitive) over the full
  list, hidden rows included, and excludes the edited entry by identity.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from dictionaries.entries import (
	ENTRY_TYPE_LABELS,
	DictionaryEntry,
	load_dictionary_entries,
	save_dictionary_entries,
)


class DuplicateEntryError(ValueError):
	"""Another entry already has this source text; nothing was changed."""

	def __init__(self, identifier: str) -> None:
		super().__init__(identifier)
		self.identifier = identifier


@dataclass(frozen=True)
class EntryListUpdate:
	"""What the view renders after a change."""

	selection: int | None  # visible row to select and focus; None: clear the selection
	filter_cleared: bool = False  # add only: the filter was reset to "" because the new entry did not match


class DictionaryEntryListModel:
	"""Full list, filter and visible list of one dictionary CSV."""

	def __init__(self, entries: Iterable[DictionaryEntry] = ()) -> None:
		self._entries: list[DictionaryEntry] = list(entries)
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read ``path`` with ``load_dictionary_entries``; errors propagate."""
		return cls(load_dictionary_entries(path))

	def save(self, path: Path) -> None:
		"""Write the full list (not only the visible rows); errors propagate."""
		save_dictionary_entries(path, self._entries)

	@property
	def entries(self) -> tuple[DictionaryEntry, ...]:
		return tuple(self._entries)

	@property
	def visible_entries(self) -> tuple[DictionaryEntry, ...]:
		return tuple(self._visible)

	@property
	def filter_text(self) -> str:
		return self._filter_text

	@property
	def visible_count(self) -> int:
		return len(self._visible)

	def visible_entry(self, index: int | None) -> DictionaryEntry | None:
		if index is None or index < 0 or index >= len(self._visible):
			return None
		return self._visible[index]

	def cell_text(self, row: int, column: int) -> str:
		entry = self._visible[row]
		if column == 0:
			return entry.text
		if column == 1:
			return entry.braille
		if column == 2:
			return ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)
		raise ValueError(f"Unknown column: {column}")

	@staticmethod
	def matches(entry: DictionaryEntry, filter_text: str) -> bool:
		normalized_filter = filter_text.casefold()
		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool:
		return any(entry.text == text and entry is not exclude_entry for entry in self._entries)

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate:
		preferred_entry = self.visible_entry(selected_index)
		self._filter_text = filter_text
		self._refilter()
		return EntryListUpdate(self._selection_after(preferred_entry, 0))

	def add(self, entry: DictionaryEntry) -> EntryListUpdate:
		if self.source_text_exists(entry.text):
			raise DuplicateEntryError(entry.text)
		self._entries.append(entry)
		filter_cleared = bool(self._filter_text) and not self.matches(entry, self._filter_text)
		if filter_cleared:
			self._filter_text = ""
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, 0), filter_cleared=filter_cleared)

	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		if self.source_text_exists(entry.text, exclude_entry=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = next(index for index, candidate in enumerate(self._entries) if candidate is current_entry)
		self._entries[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index))

	def remove(self, visible_index: int) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		self._entries.remove(current_entry)
		self._refilter()
		return EntryListUpdate(self._selection_after(current_entry, visible_index))

	def _visible_at(self, index: int) -> DictionaryEntry:
		if index < 0 or index >= len(self._visible):
			raise IndexError(f"visible index out of range: {index}")
		return self._visible[index]

	def _refilter(self) -> None:
		if self._filter_text:
			self._visible = [entry for entry in self._entries if self.matches(entry, self._filter_text)]
		else:
			self._visible = list(self._entries)

	def _selection_after(self, preferred_entry: DictionaryEntry | None, fallback_index: int) -> int | None:
		if not self._visible:
			return None
		index = min(fallback_index, len(self._visible) - 1)
		if preferred_entry is not None:
			try:
				index = self._visible.index(preferred_entry)
			except ValueError:
				pass
		return index
EOF
```

- [ ] **Step 4: Run the new tests and the full suite.**

```bash
$PY -m unittest tests.test_dictionary_entry_list_model 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (932 + 39):

```text
Ran 39 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 971 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/dictionaries/entry_list_model.py client/tests/test_dictionary_entry_list_model.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add wx-free dictionary entry list model

DictionaryEntryListModel holds the full entry list, the filter text and
the visible list of the entries editor, with duplicate detection,
add/replace/remove, the selection to show after each change, the cell
text and load/save through dictionaries.entries. It keeps the editor's
comparison rules (selection by equality, replace by identity, remove the
first equal entry, exact-text duplicate check excluding the edited entry
by identity). Not used yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add wx-free dictionary entry list model
```

---

### Task 3: Use the model in the entries editor (spec step 3, part C)

Part A is not changed (refinement 6); the harness tests and the trace replay must stay green.

- [ ] **Step 1: Show what goes.** The acceptance grep (AC6, `dialog.py` part) on the current code.

```bash
grep -n "filtered_entries\|_identifier_exists\|_normalize_type\|Path(\"data\")" dialog.py
```

Expected:

```text
338:		self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
340:		self.filtered_entries: List[DictionaryEntry] = list(self.entries)
397:		entry = self.filtered_entries[item]
421:			self.filtered_entries = [
425:			self.filtered_entries = list(self.entries)
427:		self.list_ctrl.SetItemCount(len(self.filtered_entries))
429:		if not self.filtered_entries:
434:		new_index = min(fallback_index, len(self.filtered_entries) - 1)
437:				new_index = self.filtered_entries.index(previous_entry)
453:		if index == wx.NOT_FOUND or index < 0 or index >= len(self.filtered_entries):
459:		return self.filtered_entries[index] if index is not None else None
467:		if index < 0 or index >= len(self.filtered_entries):
487:		if self._identifier_exists(new_entry.text):
513:		if self._identifier_exists(updated_entry.text, exclude_entry=current_entry):
548:	def _identifier_exists(
558:	def _normalize_type(self, entry_type: str | None) -> str:
```

- [ ] **Step 2: Write the two part-C tests and watch them fail.** `test_dictionary_path_is_required` (`inspect.signature`: no default) and `test_model_is_loaded_from_the_dictionary_path` (`_model` is a `DictionaryEntryListModel` holding the CSV rows; `dictionary_path` is the path). The model is imported before the stub scope.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_speech_symbols_dialog.py b/client/tests/test_speech_symbols_dialog.py
index fdde820..c7c08ac 100644
--- a/client/tests/test_speech_symbols_dialog.py
+++ b/client/tests/test_speech_symbols_dialog.py
@@ -15,6 +15,7 @@ regenerate it to make a refactor pass.
 """
 
 import csv
+import inspect
 import json
 import random
 import sys
@@ -26,6 +27,7 @@ from pathlib import Path
 from unittest.mock import patch
 
 from dictionaries.entries import DictionaryEntry, load_dictionary_entries
+from dictionaries.entry_list_model import DictionaryEntryListModel
 from i18n import _
 from tests import wx_stub
 
@@ -1355,6 +1357,23 @@ class SpeechSymbolsDialogOkTest(_EditorTestCase):
         self.assertEqual(harness.saved_csv(), HEADER)
 
 
+# --- the dialog delegates to the model (P2-2 part C) -------------------------
+
+
+class SpeechSymbolsDialogModelTest(_EditorTestCase):
+    def test_dictionary_path_is_required(self) -> None:
+        parameter = inspect.signature(SpeechSymbolsDialog.__init__).parameters["dictionary_path"]
+
+        self.assertIs(parameter.default, inspect.Parameter.empty)
+
+    def test_model_is_loaded_from_the_dictionary_path(self) -> None:
+        harness = self.open_editor([ALPHA, BETA])
+
+        self.assertIsInstance(harness.dialog._model, DictionaryEntryListModel)
+        self.assertEqual(harness.dialog._model.entries, (DictionaryEntry(*ALPHA), DictionaryEntry(*BETA)))
+        self.assertEqual(harness.dialog.dictionary_path, harness.path)
+
+
 # --- golden trace -----------------------------------------------------------
 
 TRACE_PATH = Path(__file__).resolve().parent / "fixtures" / "dictionary_entries_trace.json"
EOF
$PY -m unittest tests.test_speech_symbols_dialog 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the other 64 tests pass):

```text
ERROR: test_model_is_loaded_from_the_dictionary_path (tests.test_speech_symbols_dialog.SpeechSymbolsDialogModelTest.test_model_is_loaded_from_the_dictionary_path)
AttributeError: 'SpeechSymbolsDialog' object has no attribute '_model'
FAIL: test_dictionary_path_is_required (tests.test_speech_symbols_dialog.SpeechSymbolsDialogModelTest.test_dictionary_path_is_required)
AssertionError: None is not <class 'inspect._empty'>
Ran 66 tests
FAILED (failures=1, errors=1)
```

- [ ] **Step 3: Switch the dialog to the model.** `__init__(parent, dictionary_path)` stores `Path(dictionary_path)`, loads `DictionaryEntryListModel`, builds the UI with `self._model.cell_text` as the list callback and renders `apply_filter(filter box, selected index)`; `_render` replaces the tail of `filter_entries`; Add, Edit and Delete call `add`, `replace` and `remove` and catch `DuplicateEntryError`; OK calls `save`. `entries`, `filtered_entries`, `_load_entries`, `_get_item_text`, `_entry_matches_filter`, `filter_entries`, `_get_selected_entry`, `_identifier_exists`, `_normalize_type`, `_save_entries` and the imports `List`, `normalize_entry_type`, `save_dictionary_entries` go (refinement 1). Tabs.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/dialog.py b/client/dialog.py
index 06a4712..a27ebbb 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -2,7 +2,6 @@ from __future__ import annotations
 
 from collections.abc import Callable
 from pathlib import Path
-from typing import List
 
 import wx
 from dictionaries.actions import get_action_availability, resolve_dictionary_selection
@@ -12,10 +11,9 @@ from dictionaries.entries import (
 	ENTRY_TYPE_OPTIONS,
 	DictionaryEntry,
 	load_dictionary_entries,
-	normalize_entry_type,
-	save_dictionary_entries,
 	validate_dictionary_entry,
 )
+from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
 from dictionaries.manager import (
 	DEFAULT_DICTIONARY_NAME,
 	normalize_dictionary_name,
@@ -330,16 +328,19 @@ DictionaryEntryListCtrl = CallbackVirtualListCtrl
 
 
 class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
-	"""Dialog for editing custom dictionary mappings stored on disk."""
+	"""Dialog for editing custom dictionary mappings stored on disk.
 
-	def __init__(self, parent: wx.Window | None, dictionary_path: Path | None = None):
+	Supervising controller: the widgets and the selected row live here, the
+	entries and the filter in ``DictionaryEntryListModel``.
+	"""
+
+	def __init__(self, parent: wx.Window | None, dictionary_path: Path):
 		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
 
-		self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
-		self.entries: List[DictionaryEntry] = self._load_entries()
-		self.filtered_entries: List[DictionaryEntry] = list(self.entries)
+		self.dictionary_path = Path(dictionary_path)
+		self._model = DictionaryEntryListModel.load(self.dictionary_path)
 		self._build_ui()
-		self.filter_entries()
+		self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
 		self._update_button_states()
 
 	def _build_ui(self) -> None:
@@ -356,7 +357,7 @@ class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 
 		self.list_ctrl = CallbackVirtualListCtrl(
 			self,
-			self._get_item_text,
+			self._model.cell_text,
 			style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
 		)
 		self.list_ctrl.InsertColumn(0, _("Source Text"), width=200)
@@ -390,57 +391,17 @@ class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 
 		finalize_dialog_layout(self, main_sizer)
 
-	def _load_entries(self) -> List[DictionaryEntry]:
-		return load_dictionary_entries(self.dictionary_path)
-
-	def _get_item_text(self, item: int, column: int) -> str:
-		entry = self.filtered_entries[item]
-		if column == 0:
-			return entry.text
-		if column == 1:
-			return entry.braille
-		if column == 2:
-			return ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)
-		raise ValueError(f"Unknown column: {column}")
-
-	def _entry_matches_filter(self, entry: DictionaryEntry, filter_text: str) -> bool:
-		normalized_filter = filter_text.casefold()
-		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()
-
-	def filter_entries(
-		self,
-		filter_text: str | None = None,
-		preferred_entry: DictionaryEntry | None = None,
-		fallback_index: int = 0,
-	) -> None:
-		previous_entry = preferred_entry or self._get_selected_entry()
-		if filter_text is None:
-			filter_text = self.filter_ctrl.GetValue()
-
-		if filter_text:
-			self.filtered_entries = [
-				entry for entry in self.entries if self._entry_matches_filter(entry, filter_text)
-			]
-		else:
-			self.filtered_entries = list(self.entries)
-
-		self.list_ctrl.SetItemCount(len(self.filtered_entries))
+	def _render(self, update: EntryListUpdate) -> None:
+		self.list_ctrl.SetItemCount(self._model.visible_count)
 		self.list_ctrl.Refresh()
-		if not self.filtered_entries:
+		if update.selection is None:
 			self._clear_selection()
 			self._update_button_states()
 			return
-
-		new_index = min(fallback_index, len(self.filtered_entries) - 1)
-		if previous_entry is not None:
-			try:
-				new_index = self.filtered_entries.index(previous_entry)
-			except ValueError:
-				pass
-		self._select_index(new_index)
+		self._select_index(update.selection)
 
 	def _on_filter_changed(self, event: wx.CommandEvent) -> None:
-		self.filter_entries(self.filter_ctrl.GetValue())
+		self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
 		event.Skip()
 
 	def _update_button_states(self) -> None:
@@ -450,21 +411,17 @@ class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 
 	def _get_selected_index(self) -> int | None:
 		index = self.list_ctrl.GetFirstSelected()
-		if index == wx.NOT_FOUND or index < 0 or index >= len(self.filtered_entries):
+		if index == wx.NOT_FOUND or index < 0 or index >= self._model.visible_count:
 			return None
 		return index
 
-	def _get_selected_entry(self) -> DictionaryEntry | None:
-		index = self._get_selected_index()
-		return self.filtered_entries[index] if index is not None else None
-
 	def _clear_selection(self) -> None:
 		index = self.list_ctrl.GetFirstSelected()
 		if index != wx.NOT_FOUND:
 			self.list_ctrl.Select(index, False)
 
 	def _select_index(self, index: int) -> None:
-		if index < 0 or index >= len(self.filtered_entries):
+		if index < 0 or index >= self._model.visible_count:
 			self._clear_selection()
 			self._update_button_states()
 			return
@@ -484,60 +441,38 @@ class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 		new_entry = self._open_entry_dialog()
 		if new_entry is None:
 			return
-		if self._identifier_exists(new_entry.text):
-			wx.MessageBox(
-				_('Source text "{identifier}" already exists.').format(identifier=new_entry.text),
-				_("Error"),
-				wx.OK | wx.ICON_ERROR,
-				parent=self,
-			)
+		try:
+			update = self._model.add(new_entry)
+		except DuplicateEntryError as error:
+			self._show_duplicate_error(error.identifier)
 			return
-		self.entries.append(new_entry)
-		filter_text = self.filter_ctrl.GetValue()
-		if filter_text and not self._entry_matches_filter(new_entry, filter_text):
+		if update.filter_cleared:
 			self.filter_ctrl.ChangeValue("")
-			filter_text = ""
-		self.filter_entries(filter_text, preferred_entry=new_entry)
+		self._render(update)
 
 	def _on_edit_clicked(self, _event: wx.CommandEvent) -> None:
 		self._edit_selected()
 
 	def _edit_selected(self) -> None:
 		visible_index = self._get_selected_index()
-		current_entry = self._get_selected_entry()
+		current_entry = self._model.visible_entry(visible_index)
 		if visible_index is None or current_entry is None:
 			return
 		updated_entry = self._open_entry_dialog(current_entry)
 		if updated_entry is None:
 			return
-		if self._identifier_exists(updated_entry.text, exclude_entry=current_entry):
-			wx.MessageBox(
-				_('Source text "{identifier}" already exists.').format(identifier=updated_entry.text),
-				_("Error"),
-				wx.OK | wx.ICON_ERROR,
-				parent=self,
-			)
+		try:
+			update = self._model.replace(visible_index, updated_entry)
+		except DuplicateEntryError as error:
+			self._show_duplicate_error(error.identifier)
 			return
-		full_index = next(
-			index for index, entry in enumerate(self.entries) if entry is current_entry
-		)
-		self.entries[full_index] = updated_entry
-		self.filter_entries(
-			self.filter_ctrl.GetValue(),
-			preferred_entry=updated_entry,
-			fallback_index=visible_index,
-		)
+		self._render(update)
 
 	def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
 		visible_index = self._get_selected_index()
-		current_entry = self._get_selected_entry()
-		if visible_index is None or current_entry is None:
+		if visible_index is None:
 			return
-		self.entries.remove(current_entry)
-		self.filter_entries(
-			self.filter_ctrl.GetValue(),
-			fallback_index=visible_index,
-		)
+		self._render(self._model.remove(visible_index))
 
 	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
 		with AddSymbolDialog(self, entry) as dialog:
@@ -545,30 +480,22 @@ class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
 				return None
 			return dialog.get_entry()
 
-	def _identifier_exists(
-		self,
-		identifier: str,
-		exclude_entry: DictionaryEntry | None = None,
-	) -> bool:
-		return any(
-			entry.text == identifier and entry is not exclude_entry
-			for entry in self.entries
+	def _show_duplicate_error(self, identifier: str) -> None:
+		wx.MessageBox(
+			_('Source text "{identifier}" already exists.').format(identifier=identifier),
+			_("Error"),
+			wx.OK | wx.ICON_ERROR,
+			parent=self,
 		)
 
-	def _normalize_type(self, entry_type: str | None) -> str:
-		return normalize_entry_type(entry_type)
-
 	def _on_ok(self, event: wx.CommandEvent) -> None:
 		try:
-			self._save_entries()
+			self._model.save(self.dictionary_path)
 		except IOError as exc:
 			wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
 			return
 		event.Skip()
 
-	def _save_entries(self) -> None:
-		save_dictionary_entries(self.dictionary_path, self.entries)
-
 
 class DictionaryManagementDialog(ContextManagedDialog, wx.Dialog):
 	"""Passive view of dictionary management: runs ``actions`` and implements ``DictionaryManagementView``."""
EOF
```

- [ ] **Step 4: Grep, focused tests, full suite and msgids.**

```bash
grep -n "filtered_entries\|_identifier_exists\|_normalize_type\|Path(\"data\")" dialog.py
$PY -m unittest tests.test_speech_symbols_dialog tests.test_dictionary_entry_list_model tests.test_dialog_validation tests.test_dialog_display tests.test_dictionary_management_dialog tests.test_gui_document_flows tests.test_wx_stub tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
```

Expected (the grep prints nothing; 971 + 2; the msgid set is unchanged):

```text
Ran 334 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 973 tests
FAILED (failures=1, skipped=9)
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/dialog.py client/tests/test_speech_symbols_dialog.py
git -C $REPO commit -q -F - <<'EOF'
refactor: use DictionaryEntryListModel in the entries editor

SpeechSymbolsDialog becomes a supervising controller: it keeps the
widgets, the selected row and every message, and renders the
EntryListUpdate the model returns. dictionary_path is now required (the
CWD-relative data/dictionary.csv default is gone; the only caller always
passes a path). The dead _normalize_type, the entries/filtered_entries
state and the unused imports go; both duplicate messages share one
helper. The characterization tests and the golden trace are unchanged
and green.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: use DictionaryEntryListModel in the entries editor
```

---

### Task 4: Rename `SpeechSymbolsDialog` to `DictionaryEntriesDialog` (spec step 4, part D)

Mechanical only, in its own commit so it can be dropped without touching Tasks 1-3. The patch carries the module rename (`git apply --index` stages it, as `git mv` would), the class name in `dialog.py`, `gui.py` (import and constructor), `test_dialog_validation` (import and tuple), `test_gui_document_flows` (patch target and kept-names guard), `_GUI_DIALOG_NAMES` and the wx_stub comment, and the test module's class names and docstring (refinement 8). No new tests; the fixture is not touched.

- [ ] **Step 1: Apply the rename.**

```bash
git -C $REPO apply --index <<'EOF'
diff --git a/client/dialog.py b/client/dialog.py
index a27ebbb..e0a2f46 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -327,7 +327,7 @@ class CallbackVirtualListCtrl(wx.ListCtrl):
 DictionaryEntryListCtrl = CallbackVirtualListCtrl
 
 
-class SpeechSymbolsDialog(ContextManagedDialog, wx.Dialog):
+class DictionaryEntriesDialog(ContextManagedDialog, wx.Dialog):
 	"""Dialog for editing custom dictionary mappings stored on disk.
 
 	Supervising controller: the widgets and the selected row live here, the
diff --git a/client/gui.py b/client/gui.py
index 3a94e46..522f006 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -75,11 +75,11 @@ from client_init import start_client_init_background
 
 from dialog import (
 	ConvertingDialog,
+	DictionaryEntriesDialog,
 	DictionaryManagementDialog,
 	DocumentNameDialog,
 	FileIssuesDialog,
 	InvalidWorkspaceFilesDialog,
-	SpeechSymbolsDialog,
 )
 from settings.view import (
 	ViewSettings,
@@ -941,7 +941,7 @@ class BrailleFrame(wx.Frame):
 		if result != wx.ID_EDIT or edit_name is None:
 			return
 		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
-		with SpeechSymbolsDialog(self, dictionary_path=dictionary_path) as editor:
+		with DictionaryEntriesDialog(self, dictionary_path=dictionary_path) as editor:
 			editor.ShowModal()
 
 	def on_convert(self, _evt):
diff --git a/client/tests/test_dialog_validation.py b/client/tests/test_dialog_validation.py
index 681e220..efca257 100644
--- a/client/tests/test_dialog_validation.py
+++ b/client/tests/test_dialog_validation.py
@@ -13,12 +13,12 @@ with _SCOPE.loading():
     import dialog as dialog_module
     from dialog import (
         AddSymbolDialog,
+        DictionaryEntriesDialog,
         DictionaryManagementDialog,
         DictionaryNameDialog,
         DocumentNameDialog,
         FileIssuesDialog,
         InvalidWorkspaceFilesDialog,
-        SpeechSymbolsDialog,
     )
 
 setUpModule = _SCOPE.activate
@@ -42,7 +42,7 @@ CONTEXT_MANAGED_DIALOGS = (
     DocumentNameDialog,
     InvalidWorkspaceFilesDialog,
     FileIssuesDialog,
-    SpeechSymbolsDialog,
+    DictionaryEntriesDialog,
     DictionaryManagementDialog,
 )
 
diff --git a/client/tests/test_speech_symbols_dialog.py b/client/tests/test_dictionary_entries_dialog.py
similarity index 98%
rename from client/tests/test_speech_symbols_dialog.py
rename to client/tests/test_dictionary_entries_dialog.py
index c7c08ac..fcb383e 100644
--- a/client/tests/test_speech_symbols_dialog.py
+++ b/client/tests/test_dictionary_entries_dialog.py
@@ -1,4 +1,4 @@
-"""Tests of the dictionary entries editor (``dialog.SpeechSymbolsDialog``).
+"""Tests of the dictionary entries editor (``dialog.DictionaryEntriesDialog``).
 
 The editor is driven only through its wx surface by ``_EditorHarness``: the
 module's ``wx`` is a namespace of fake widgets and distinct power-of-two flags,
@@ -66,7 +66,7 @@ dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
 setUpModule = _DIALOG_SCOPE.activate
 tearDownModule = _DIALOG_SCOPE.deactivate
 CallbackVirtualListCtrl = dialog.CallbackVirtualListCtrl
-SpeechSymbolsDialog = dialog.SpeechSymbolsDialog
+DictionaryEntriesDialog = dialog.DictionaryEntriesDialog
 _NATIVE_DIALOG_BASE = dialog.wx.Dialog
 
 
@@ -308,7 +308,7 @@ class _EditorHarness:
             stack.enter_context(patch.object(dialog, "wx", self.wx))
             stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
             stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
-            editor = object.__new__(SpeechSymbolsDialog)
+            editor = object.__new__(DictionaryEntriesDialog)
             editor.CreateButtonSizer = self._create_button_sizer
             editor.FindWindowById = self._find_window_by_id
             editor.SetSizerAndFit = lambda _sizer: self.record("SetSizerAndFit")
@@ -551,7 +551,7 @@ class DialogModuleIsolationTest(unittest.TestCase):
 # --- pre-P2-2 tests, rewritten onto the harness (same assertions) -----------
 
 
-class SpeechSymbolsDialogFilterTest(_EditorTestCase):
+class DictionaryEntriesDialogFilterTest(_EditorTestCase):
     def setUp(self) -> None:
         # Beta is added through the entry dialog: the loader drops a Bopomofo row
         # whose braille is not a zhuyin sequence. Row 0 is selected, as before.
@@ -621,7 +621,7 @@ class SpeechSymbolsDialogFilterTest(_EditorTestCase):
         self.assertTrue(skipped)
 
 
-class SpeechSymbolsDialogBuildUiTest(_EditorTestCase):
+class DictionaryEntriesDialogBuildUiTest(_EditorTestCase):
     def test_build_ui_binds_item_activation_to_edit_handler(self) -> None:
         harness = self.open_editor([ALPHA])
         editor = harness.dialog
@@ -636,7 +636,7 @@ class SpeechSymbolsDialogBuildUiTest(_EditorTestCase):
         )
 
 
-class SpeechSymbolsDialogMutationTest(_EditorTestCase):
+class DictionaryEntriesDialogMutationTest(_EditorTestCase):
     def setUp(self) -> None:
         self.harness = self.open_editor([ALPHA, BETA])
 
@@ -734,7 +734,7 @@ class SpeechSymbolsDialogMutationTest(_EditorTestCase):
 # --- new characterization (P2-2 part A) -------------------------------------
 
 
-class SpeechSymbolsDialogConstructionTest(_EditorTestCase):
+class DictionaryEntriesDialogConstructionTest(_EditorTestCase):
     def test_construction_log_is_exact(self) -> None:
         harness = self.open_editor([ALPHA, BETA], keep_log=True)
 
@@ -840,7 +840,7 @@ class SpeechSymbolsDialogConstructionTest(_EditorTestCase):
         self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")
 
 
-class SpeechSymbolsDialogCellTextTest(_EditorTestCase):
+class DictionaryEntriesDialogCellTextTest(_EditorTestCase):
     def test_cells_show_text_braille_and_the_translated_type_label(self) -> None:
         harness = self.open_editor([
             ["Alpha", "\u2801", "General"],
@@ -866,7 +866,7 @@ class SpeechSymbolsDialogCellTextTest(_EditorTestCase):
         self.assertEqual(str(caught.exception), "Unknown column: 3")
 
 
-class SpeechSymbolsDialogFilterBehaviorTest(_EditorTestCase):
+class DictionaryEntriesDialogFilterBehaviorTest(_EditorTestCase):
     def test_filter_uses_casefold_not_lower(self) -> None:
         harness = self.open_editor([["Stra\u00dfe", "\u280e", "General"], ["STRASSE", "", "General"]])
 
@@ -966,7 +966,7 @@ class SpeechSymbolsDialogFilterBehaviorTest(_EditorTestCase):
         )
 
 
-class SpeechSymbolsDialogAddTest(_EditorTestCase):
+class DictionaryEntriesDialogAddTest(_EditorTestCase):
     def test_cancel_changes_nothing(self) -> None:
         harness = self.open_editor([ALPHA])
         before = harness.state()
@@ -1068,7 +1068,7 @@ class SpeechSymbolsDialogAddTest(_EditorTestCase):
         self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Alpine", "\u2801\u2807", GENERAL]])
 
 
-class SpeechSymbolsDialogEditTest(_EditorTestCase):
+class DictionaryEntriesDialogEditTest(_EditorTestCase):
     def test_edit_button_opens_the_selected_entry(self) -> None:
         harness = self.open_editor([ALPHA, BETA])
         harness.select(1)
@@ -1200,7 +1200,7 @@ class SpeechSymbolsDialogEditTest(_EditorTestCase):
         self.assertEqual(harness.rows(), [ALPHA_CELLS])
 
 
-class SpeechSymbolsDialogDeleteTest(_EditorTestCase):
+class DictionaryEntriesDialogDeleteTest(_EditorTestCase):
     def test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index(self) -> None:
         harness = self.open_editor([ALPHA, BETA, ["Gamma", "\u281b", "General"]])
         harness.select(1)
@@ -1271,7 +1271,7 @@ class SpeechSymbolsDialogDeleteTest(_EditorTestCase):
         )
 
 
-class SpeechSymbolsDialogOkTest(_EditorTestCase):
+class DictionaryEntriesDialogOkTest(_EditorTestCase):
     def test_ok_saves_the_full_list_in_order_and_closes(self) -> None:
         harness = self.open_editor([BETA, ALPHA])
         harness.script_entry("Gamma", "\u281b", "Braille")
@@ -1360,9 +1360,9 @@ class SpeechSymbolsDialogOkTest(_EditorTestCase):
 # --- the dialog delegates to the model (P2-2 part C) -------------------------
 
 
-class SpeechSymbolsDialogModelTest(_EditorTestCase):
+class DictionaryEntriesDialogModelTest(_EditorTestCase):
     def test_dictionary_path_is_required(self) -> None:
-        parameter = inspect.signature(SpeechSymbolsDialog.__init__).parameters["dictionary_path"]
+        parameter = inspect.signature(DictionaryEntriesDialog.__init__).parameters["dictionary_path"]
 
         self.assertIs(parameter.default, inspect.Parameter.empty)
 
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index f17de34..7672100 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -928,7 +928,7 @@ class DictionaryManagementFrameTest(unittest.TestCase):
     def _open_management(self, frame, result, edit_name):
         with (
             patch.object(gui, "DictionaryManagementDialog") as dialog_class,
-            patch.object(gui, "SpeechSymbolsDialog") as editor_class,
+            patch.object(gui, "DictionaryEntriesDialog") as editor_class,
         ):
             dialog = dialog_class.return_value.__enter__.return_value
             dialog.ShowModal.return_value = result
@@ -1051,7 +1051,7 @@ class DictionaryManagementFrameTest(unittest.TestCase):
             with self.subTest(module_attribute=name):
                 self.assertFalse(hasattr(gui, name))
         self.assertFalse(hasattr(gui.BrailleFrame, "_get_csv_wildcard"))
-        for name in ("dictionary_path_for_name", "get_dictionary_directory", "DictionaryManagementDialog", "SpeechSymbolsDialog"):
+        for name in ("dictionary_path_for_name", "get_dictionary_directory", "DictionaryManagementDialog", "DictionaryEntriesDialog"):
             with self.subTest(kept=name):
                 self.assertTrue(hasattr(gui, name))
         for name in ("_get_selected_dictionary_path", "_show_file_error"):
diff --git a/client/tests/wx_stub.py b/client/tests/wx_stub.py
index 068062c..d4c865c 100644
--- a/client/tests/wx_stub.py
+++ b/client/tests/wx_stub.py
@@ -375,12 +375,12 @@ def dual_view_stubs():
 
 _GUI_DIALOG_NAMES = (
     "ConvertingDialog",
+    "DictionaryEntriesDialog",
     "DictionaryManagementDialog",
     "DictionaryNameDialog",
     "DocumentNameDialog",
     "FileIssuesDialog",
     "InvalidWorkspaceFilesDialog",
-    "SpeechSymbolsDialog",
     "TranslationSettingsDialog",
     "TranslationTableDialog",
 )
@@ -887,7 +887,7 @@ def settings_dialog_stubs():
     }
 
 
-# --- factory and loader: test_speech_symbols_dialog, test_dictionary_management_dialog
+# --- factory and loader: test_dictionary_entries_dialog, test_dictionary_management_dialog
 
 
 SPEECH_DIALOG_MODULE_NAME = "_speech_symbols_dialog_under_test"
EOF
git -C $REPO diff --cached -M --stat
```

Expected (the test module shows as a rename):

```text
 client/dialog.py                                   |  2 +-
 client/gui.py                                      |  4 +--
 client/tests/test_dialog_validation.py             |  4 +--
 ...dialog.py => test_dictionary_entries_dialog.py} | 30 +++++++++++-----------
 client/tests/test_gui_document_flows.py            |  4 +--
 client/tests/wx_stub.py                            |  4 +--
 6 files changed, 24 insertions(+), 24 deletions(-)
```

- [ ] **Step 2: AC6 grep, focused tests and full suite.**

```bash
grep -rn "SpeechSymbols" . --include=*.py
$PY -m unittest tests.test_dictionary_entries_dialog tests.test_dictionary_entry_list_model tests.test_dialog_validation tests.test_dialog_display tests.test_dictionary_management_dialog tests.test_gui_document_flows tests.test_wx_stub tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (the grep prints nothing):

```text
Ran 334 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 973 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 3: Commit.** Everything is already staged.

```bash
git -C $REPO commit -q -F - <<'EOF'
refactor: rename SpeechSymbolsDialog to DictionaryEntriesDialog

"Speech symbols" is NVDA heritage; the dialog edits dictionary entries
("Custom Dictionary Manager"). Mechanical rename of the class, its
import and use in gui.py, the test references, the gui stub name list
and the test module (now tests/test_dictionary_entries_dialog.py). No
alias for the old name. The wx_stub speech profile names and
AddSymbolDialog keep their names. No msgid changes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: rename SpeechSymbolsDialog to DictionaryEntriesDialog
```

---

### Task 5: Final verification (spec acceptance criteria; no commit)

- [ ] **Step 1: AC1 (roadmap command, verbose) and AC2.**

```bash
$PY -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_dictionary_entries tests.test_dictionary_management_dialog tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n tests.test_translation_golden 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (AC1: 105 tests, all passing; AC2 all green; the 2 skips in `test_gui_document_flows` need a case-insensitive file system):

```text
105
Ran 105 tests
OK
Ran 292 tests
OK (skipped=2)
```

- [ ] **Step 2: AC3 full suite; AC4 both fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
git -C $REPO diff main --stat -- client/tests/fixtures/translation_golden.json
sha256sum tests/fixtures/translation_golden.json
git -C $REPO diff HEAD~3 HEAD --stat -- client/tests/fixtures/dictionary_entries_trace.json
sha256sum tests/fixtures/dictionary_entries_trace.json
$PY -c "import pathlib; from tests import test_dictionary_entries_dialog as module; module.write_trace_fixture(pathlib.Path('$T/trace_after.json'))"
cmp $T/trace_after.json tests/fixtures/dictionary_entries_trace.json && echo 'trace regenerated from the refactored editor: identical'
```

Expected (889 + 84; no diff of either fixture; the refactored editor reproduces the trace byte for byte):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 973 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
trace regenerated from the refactored editor: identical
```

- [ ] **Step 3: AC3, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 973 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=973 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC3, the stub-scope modules alone and in both orders with the model tests.**

```bash
echo "tests.test_dictionary_entry_list_model: $($PY -B -m unittest tests.test_dictionary_entry_list_model 2>&1 | grep -E '^(OK|FAILED)')"
for m in test_dictionary_entries_dialog test_dialog_validation test_dialog_display test_dictionary_management_dialog; do
  for order in "tests.$m" "tests.$m tests.test_dictionary_entry_list_model" "tests.test_dictionary_entry_list_model tests.$m"; do
    echo "$order: $($PY -B -m unittest $order 2>&1 | grep -E '^(OK|FAILED)')"
  done
done
```

Expected:

```text
tests.test_dictionary_entry_list_model: OK
tests.test_dictionary_entries_dialog: OK
tests.test_dictionary_entries_dialog tests.test_dictionary_entry_list_model: OK
tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog: OK
tests.test_dialog_validation: OK
tests.test_dialog_validation tests.test_dictionary_entry_list_model: OK
tests.test_dictionary_entry_list_model tests.test_dialog_validation: OK
tests.test_dialog_display: OK
tests.test_dialog_display tests.test_dictionary_entry_list_model: OK
tests.test_dictionary_entry_list_model tests.test_dialog_display: OK
tests.test_dictionary_management_dialog: OK
tests.test_dictionary_management_dialog tests.test_dictionary_entry_list_model: OK
tests.test_dictionary_entry_list_model tests.test_dictionary_management_dialog: OK
```

- [ ] **Step 5: AC5-AC7.**

```bash
echo AC5
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json
git -C $REPO diff main --stat -- client/locales scripts client/dictionaries/entries.py client/conversion client/translation
echo AC6
grep -rn "SpeechSymbols" $REPO/client --include=*.py
grep -n "filtered_entries\|_identifier_exists\|_normalize_type\|Path(\"data\")" $REPO/client/dialog.py
echo AC7
$PY -m unittest tests.test_dictionary_entry_list_model.ImportGuardTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo end
```

Expected (353 source msgids, the same 4 only-in-pot wildcards and nothing only in source; nothing after AC5's scan and after AC6):

```text
AC5
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
SOURCE == SAVED
AC6
AC7
Ran 1 test
OK
end
```

- [ ] **Step 6: The branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -5
git -C $REPO diff -M --stat HEAD~4 HEAD
```

Expected:

```text
refactor: rename SpeechSymbolsDialog to DictionaryEntriesDialog
refactor: use DictionaryEntryListModel in the entries editor
refactor: add wx-free dictionary entry list model
test: characterize dictionary entries editor
docs: plan dictionary entry list model
 client/dialog.py                                   |  153 +-
 client/dictionaries/entry_list_model.py            |  156 ++
 client/gui.py                                      |    4 +-
 .../tests/fixtures/dictionary_entries_trace.json   | 1162 +++++++++++++++
 client/tests/test_dialog_validation.py             |    4 +-
 client/tests/test_dictionary_entries_dialog.py     | 1513 ++++++++++++++++++++
 client/tests/test_dictionary_entry_list_model.py   |  408 ++++++
 client/tests/test_gui_document_flows.py            |    4 +-
 client/tests/test_speech_symbols_dialog.py         |  459 ------
 client/tests/wx_stub.py                            |    4 +-
 10 files changed, 3287 insertions(+), 580 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): on a packaged zh_TW build with NVDA, Dictionary Management -> Edit opens the editor with row 1 selected and announced; typing in the filter keeps the selected entry; Add of a non-matching entry clears the filter and selects it; Edit, Enter on a row, Delete (the row now at the same index is selected); the duplicate message; OK saves, Cancel discards; paste, cut and undo in the filter box update the list (D3). Byte-compare the CSV written by OK for an unchanged dictionary against `main`. Check what `SetItemCount` does to a selected row of the real virtual list (refinement 11). PyInstaller must pick up `dictionaries/entry_list_model.py` through the static import in `dialog.py` (read, not run). No visual or string change, so no screenshots and no `generate_pot.bat` run.
