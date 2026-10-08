# Settings Option Source (P2-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every settings option list one definition. A new wx-free `client/settings/options.py` holds frozen descriptors (value plus `N_()` label msgid) for the output modes, view schemes (with their editor colours), braille fonts and translation-table fields, the width and font-size ranges, and four lookup helpers. `settings/translation.py`, `settings/view.py`, `settings/dialogs.py` and `gui.py` read from it, and their own tuples, constants, the hard-coded `UEB`/`Nemeth` list and the `{"default", "math"}` sets are removed. Persisted defaults stay in `config.py`, checked by invariant tests. Nothing a user sees changes: same labels (zh_TW and untranslated), order, selected index, saved value, normalization, spin ranges, editor colours and SimBraille rule; the msgid set stays at 353 and `client/locales` does not change. The spec's quirks K1, K2 and K4 are pinned by tests marked `# KNOWN QUIRK (P2-3 spec, Kn)`, not fixed.

**Architecture:** Five commits in the spec's order. Task 1 characterizes the current panels, normalizers and gui colours with the real zh_TW catalog and without patching `settings.dialogs._` (the panels are built for real under the settings stub scope with recording `wx.Choice`/`wx.SpinCtrl` and a fake `listTables`); the tests pass by construction, and a throwaway mutant runner shows that each of 20 deliberate breakages makes them fail. Task 2 writes the option-source tests first (red: module missing), then the module, then switches config's math default to the leaf constant (red, then green). Tasks 3-5 each start with one red guard test in `tests/test_settings_options.py` (the consumer still keeps its own list or literal values) and then migrate one layer: the normalizers and the two spins (Task 3), the three panels (Task 4), `gui.VIEW_SCHEMES` (Task 5). The Task 1 tests run unchanged and green after every task.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `dataclasses`, `ast`, `types`). wxPython is not installed: the panel tests run against `tests/wx_stub.py`'s settings profile, the colour tests against the gui profile; the option module is tested without any stub scope.

**Spec:** `docs/superpowers/specs/2026-10-08-p2-3-settings-options-design.md` (authoritative, commit `cfd54dc`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p2-3-settings-options`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (12, nothing else): production `client/settings/options.py` (new), `client/settings/translation.py`, `client/settings/view.py`, `client/settings/dialogs.py`, `client/gui.py`, `client/config.py`; tests `client/tests/test_settings_options.py` (new), `client/tests/test_settings_dialogs.py`, `client/tests/test_translation_settings.py`, `client/tests/test_view_settings.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py`. Never touch `client/settings/state.py`, `client/settings/translation_tables.py`, `client/braille/` (in particular `braille/tables/__tables.py`), `client/conversion/`, `client/dual_view/`, `client/main.py`, `client/locales/`, `scripts/` or any fixture.
- Indentation: `client/settings/*.py`, `client/config.py` and every test module above use 4 spaces; `client/gui.py` uses tabs. The patches and file blocks carry the exact characters (the test modules contain zh_TW text as UTF-8); run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes and no msgid changes: the source msgid set is compared with the Task 0 snapshot after Tasks 2 and 4 and at the end (`SOURCE == SAVED`, 353). No `.po`/`.mo` change, no `generate_pot.bat` run.
- Fixtures are never touched: `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`), checked in Task 0 and Task 6.
- Never patch `settings.dialogs._` or `gui._` in a new test (spec Test Plan). Untranslated labels are asserted against the msgid and `i18n._(msgid)`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, and absolute paths are stripped from errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p23impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.4.
- Baseline (re-verified at `cfd54dc`, the spec commit; code identical to `f16bfc8` = `main`): `$PY -m unittest discover -s tests` gives `Ran 973 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: step 3 must also move the two spins in `settings/dialogs.py`.** `settings/dialogs.py` imports `MIN_CONVERSION_WIDTH`/`MAX_CONVERSION_WIDTH` from `.translation` and `VIEW_FONT_SIZE_MIN`/`VIEW_FONT_SIZE_MAX` from `.view` (`dialogs.py:18-28`). Removing them in step 3, as the spec says, while leaving the dialog for step 4 would make `import settings.dialogs` fail (and with it `gui`). Task 3 therefore also switches the width and font-size spins (`min`/`max`/`initial` and both `load_snapshot` clamps, 4 sites) and their imports to `CONVERSION_WIDTH_RANGE`/`VIEW_FONT_SIZE_RANGE`; Task 4 does the choices and the tables panel. No aliases are kept (D9).
2. **Factual correction: `tests/test_settings_dialogs.py` runs 47 tests, not 39.** It defines 39 test methods, but the 8 of the `_SingletonCharacterization` mixin run in both `TextProcessingSingletonTest` and `DotExpressSettingsSingletonTest`. The focused six-module baseline of 57 is right.
3. **Refinement: part A spells values out instead of using the old tuples.** The characterization asserts literal values, labels and ranges (`"unicode"`, `"淺色"`, `(10, 200)`, ...) plus `i18n._(msgid)` and `config.DEFAULT_*`, never `SUPPORTED_OUTPUT_MODES` and the like. So part A is never edited after Task 1, and the spec's "part A's invariant test switches to `option_values(...)`" step is not needed (the invariants live in part B).
4. **Refinement: where part A lives.** Items A1-A3 and A6 go to `tests/test_settings_dialogs.py` (`TranslationPanelOptionsTest`, `ViewPanelOptionsTest`, `TranslationTablesPanelOptionsTest`, `TableDisplayNameGuardTest`), A4 to `tests/test_translation_settings.py` (`TranslationSettingsNormalizeTest`) and `tests/test_view_settings.py` (`ViewSettingsNormalizeTest`), and A5 to `tests/test_gui_document_flows.py` (`EditorViewSettingsCharacterizationTest`), the only module with the gui stub scope. A5 also characterizes `_apply_editor_view_settings` (font size on both editors, the colours and their call order, the SimBraille face for registered font / `win32` / neither, and normalization of unknown values), because Task 5 edits that method and the existing tests always mock it.
5. **Refinement: how the panels are observed.** `build_panel` builds the real panel class from `sys.modules["settings.dialogs"]` with a `SimpleNamespace` owner, `patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin)` and `patch.object(module, "listTables", ...)`. Rows are read from the layout: the stub `FlexGridSizer` records every `Add`, so `grid_rows(panel)` returns the (label, control) pairs in order, and the validation focus target is compared with the row's control. Only the public attribute names `output_choice`, `width_spin`, `dictionary_choice`, `scheme_choice`, `braille_font_choice`, `font_size_spin` are used (to set a selection); `_choice_controls`, `_options_by_key` and the field list are never read. The fake tables mix English display names (source run) with one zh_TW name (packaged run), an upper-case file name (`en-GB-g2.ctb`), a `zhcn` prefix (K4), a non-matching prefix and an `output=False` table.
6. **Refinement: the red step of Tasks 3-5.** The spec adds no test for steps 3-5. Each of these tasks first appends one guard to `OptionSourceConsumerTest` in `tests/test_settings_options.py` and runs it red: the module-level assignments of `settings/translation.py` (only `DEFAULT_TRANSLATION_SETTINGS`) and `settings/view.py` (none), then of `settings/dialogs.py` (only `_DEAD_WINDOW_ERROR_TYPES`, `CommitSettings`) and the class body of `TranslationTablesPanel` (only `title`, `panel_description`, `TABLE_FIELDS`), and no string literal among the option values (`unicode ascii light dark simbraille UEB Nemeth`, plus the table keys for the dialog) in the migrated module. The guards are allow-lists, so they never spell a removed name: AC6's first grep, which also covers `client/tests`, stays empty. `"default"` is not checked in `translation.py`, where it is the default dictionary's name.
7. **Refinement: part B details.** `tests/test_settings_options.py` has 19 tests in Task 2 (lists 6, helpers 5, config invariants 5, module guard 3); "empty prefix" in the spec's helper list is read as the empty option tuple (`option_values(()) == ()`, `option_index((), v) == 0`, `normalize_option_value((), v, d) == d`); the `None` file prefix (every output table) is covered by part A's default row. The config invariant includes an AST check that `DEFAULT_TRANSLATION_TABLES["math"]` is the name `DEFAULT_MATH_BRAILLE_TABLE`, which makes Task 2's config switch red-first.
8. **Refinement: small code choices the spec leaves open.** `options.py` documents each field with an attribute docstring and records the D3 import-cycle reason in its module docstring. `option_value_at` keeps the old `index < 0 or index >= len` test; `normalize_option_value` uses `in option_values(options)` (tuple membership, as before); `IntRange.clamp` is the old `max(minimum, min(maximum, value))`. `is_valid` becomes `all(... for field in TABLE_FIELDS if field.required)` (same calls, same short-circuit as `default and math`). `_options_for_lang` is kept; `_options_for_field` calls it with `field.file_prefix`. The D6 comment sits above the `_(table.displayName)` list. Importing `settings.translation` or `settings.view` now also imports `i18n` (through `options.py`); `i18n` has no side effect beyond loading the bundled catalog, which every GUI process loads anyway.
9. **Refinement: test counts fixed at 50 new tests (973 -> 1023).** Task 1: 27 (`test_settings_dialogs` 47 -> 67, `test_translation_settings` 3 -> 5, `test_view_settings` 2 -> 5, `test_gui_document_flows` +2); Task 2: 20 (19 in the new module, `test_settings_options_uses_shared_i18n`); Tasks 3, 4, 5: 1 guard each. The roadmap command (AC1) runs 99 tests.
10. **Refinement: the KNOWN QUIRK markers.** K1 `ViewPanelOptionsTest.test_save_maps_out_of_range_selections_to_the_first_option` and `OptionHelpersTest.test_option_value_at_maps_out_of_range_indexes_to_the_first_option`; K2 `TranslationTablesPanelOptionsTest.test_unknown_or_missing_file_names_select_the_first_option`; K4 `TranslationTablesPanelOptionsTest.test_each_row_lists_its_tables_sorted_by_translated_name`. K3 (no normalization of tables on load) has no panel-visible effect beyond K2 and is left to the existing `test_translation_tables`. A reviewer should reject any "fix" in this task.

Everything else in the spec was re-checked at `cfd54dc`: the option tables and their line numbers, the panels' selection and save rules, the translation timing (labels translated at import, catalog fixed per process), `__tables.py`'s localedir and the measured D6 facts (198 `addTable` calls, 196 with output, every name translated, `_(_(name)) == _(name)` for all, identical sorted lists, prefix counts en 10 / zh 6 / ja 2), the import cycle of D3, the stub scopes (`isolate=("settings.dialogs",)` and `isolate=("gui", "settings.dialogs", "ui.dual_view")`, both `evict_nothing`), the two `CHOICE_SPECS` tests, the `test_i18n` expectations and AC6's expected grep output.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `cfd54dc` (`$SP/p23plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 5 the 20 shuffle seeds, the pair orders, the msgid scan and every acceptance criterion passed. The file blocks in this plan are the dry clone's committed files and the patches are `git diff`s of its commits (each refactor task split into the red guard step and the implementation step). Then this file's blocks were run in order on fresh clones (`$SP/p23plan/replay1` to `replay3`, each with a stand-in plan commit and a local `main` at `f16bfc8`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 5 commits applied, every expected block matched byte for byte on the final replay, and the resulting `client/` tree is identical to the dry clone's. Final sha256: `client/settings/options.py` `024693b8bf6a4222bf13ad266d4b5b7c1f3e68c1800004b3104be690a62b47c3`, `client/settings/dialogs.py` `bad0d47b9cbf36019291383bcafe714c5978b1e1d05388850fdcc054f43a1e9b`, `client/settings/translation.py` `6efc95378df4404c4a0eb337657a25f2acea3ac5e3938cec6363aaad095e1929`, `client/settings/view.py` `e22073f192903900393cc9fe6b71832a529ebd45efac12feef171758f5e46d5b`, `client/gui.py` `c27a272f1875a4e58d6d5893839657fbdef991483411fecb03c726cde1f23348`, `client/config.py` `c6c27b822566d124aab2ab7b6f0fd86cc846e8a3092c62bfdb05e7093c8ac6b3`, `client/tests/test_settings_options.py` `2ec5fe4a3ade266b0ccf163ba19ecae24cb5008a33d98d2f6cd8a9a0a6050f76`, `client/tests/test_settings_dialogs.py` `924ed18e02c6eec6132bf982641b4e2694ed0fdf359b6e5d336c272a5ee261ed`, `client/tests/test_translation_settings.py` `8427e48b4121fa25bf8669bda8ccbf1589f4b8c18ed018d7acb6e4588e8c817f`, `client/tests/test_view_settings.py` `2500ea564f71edf7a4d6b9b9b2fbba825127c66723e1903397092abe2f8d4f76`, `client/tests/test_gui_document_flows.py` `7526068f65522c28deee465ffecd31a869d46c93477c1fed7fda7219d126bc14`, `client/tests/test_i18n.py` `6c9fa096282010652a70a0a14a4e0bf226eed09361e543117ed9e8bd4d3ab3ee`; both fixtures unchanged. Windows-only behavior (real wx, NVDA, PyInstaller, `generate_pot.bat`) was not run; see the end of Task 6.

## Review Focus

1. **Same labels in production, different timing (D2).** Labels used to be translated when `settings.dialogs` was imported; now `_(option.label)` runs when the control is built. With the fixed per-process catalog the text is identical; part A checks the zh_TW text, never patching `_`. The two existing validation tests that patch `_` to identity still see the English field label (they no longer inject a field list).
2. **Selection rules moved into helpers (D7).** `option_value_at` maps -1 and past-the-end to the first option's value (K1, not the config default), `option_index` maps an unknown value to 0. Part A pins both through the panels, part B through the helpers, and two mutants (`unknown-output-mode-selects-last`, `unset-braille-font-saves-config-default`) show the net catches a "fix".
3. **Table rows (D5).** `required` reproduces both `{"default", "math"}` sets (no "None selected"; validated in field order); `fixed_choices` replaces `if key == "math"`; `file_prefix` keeps the plain lower-case `startswith` (K4). `_load_table_options`, `TableOption`, `_("None selected")` and `_(table.displayName)` (now commented, D6) stay in the dialog.
4. **Stub-scope class identity.** `tests/test_settings_options.py` imports `settings.options` at module level; both scopes that load `settings.dialogs` evict nothing, so every module sees one set of descriptor classes. Guards: 20 shuffled full-suite seeds, and `test_settings_dialogs`/`test_gui_document_flows` alone and in both orders with `test_settings_options`.
5. **Untouched seams.** `config` still owns the defaults and imports nothing new (D3); `settings/state.py`, `settings/translation_tables.py`, `conversion/*` (including `output.py`'s `"ascii"`), `braille/*`, `main.py` and the dictionary choice are unchanged.

## File Map

- Task 1: modify `client/tests/test_settings_dialogs.py`, `client/tests/test_translation_settings.py`, `client/tests/test_view_settings.py`, `client/tests/test_gui_document_flows.py` (additions only).
- Task 2: create `client/tests/test_settings_options.py`, `client/settings/options.py`; modify `client/tests/test_i18n.py`, `client/config.py`.
- Task 3: modify `client/tests/test_settings_options.py`, `client/settings/translation.py`, `client/settings/view.py`, `client/settings/dialogs.py` (imports and the two spins).
- Task 4: modify `client/tests/test_settings_options.py`, `client/settings/dialogs.py`, `client/tests/test_settings_dialogs.py` (two `CHOICE_SPECS` assignments removed).
- Task 5: modify `client/tests/test_settings_options.py`, `client/gui.py`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 973 |
| 1 characterization | 27 | 1000 |
| 2 option source | 20 | 1020 |
| 3 normalizers and spins | 1 | 1021 |
| 4 panels | 1 | 1022 |
| 5 gui schemes | 1 | 1023 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `settings_mutants.py <client_dir> <scratch_dir> [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`) to `<scratch_dir>/client` once, then for each of 20 mutants edits one file of the copy (`settings/dialogs.py`, `settings/translation.py`, `settings/view.py` or `gui.py`), runs the four part-A modules there and restores the file. The repo is never changed. Only meaningful in Task 1 (the patterns match the pre-refactor code).
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
docs: plan settings option source
refactor/p2-3-settings-options
```

- [ ] **Step 2: Create the mutant runner.**

```bash
mkdir -p $T/tools
cat > $T/tools/settings_mutants.py <<'EOF'
"""Run the P2-3 characterization tests against deliberately broken settings code (throwaway).

Usage: python settings_mutants.py <client_dir> <scratch_dir> [mutant ...]
Copies <client_dir> (without .venv, __pycache__, log) to <scratch_dir>/client once,
then for each mutant edits one file in the copy, runs the four characterization
modules there and restores the file. <client_dir> is never changed. Prints
"<mutant>: failures=F errors=E" per mutant (all by default).
Only meaningful before Task 3: the patterns match the pre-P2-3 code.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = [
    "tests.test_settings_dialogs",
    "tests.test_translation_settings",
    "tests.test_view_settings",
    "tests.test_gui_document_flows",
]

# name -> (file, old, new); old must occur exactly once in the file.
MUTANTS = {
    "output-labels-untranslated": (
        "settings/dialogs.py",
        '    ("unicode", _("Unicode")),\n    ("ascii", _("ASCII")),',
        '    ("unicode", "Unicode"),\n    ("ascii", "ascii"),',
    ),
    "scheme-order-swapped": (
        "settings/dialogs.py",
        '    ("light", _("Light")),\n    ("dark", _("Dark")),',
        '    ("dark", _("Dark")),\n    ("light", _("Light")),',
    ),
    "unknown-output-mode-selects-last": (
        "settings/dialogs.py",
        "if key == output_mode),\n            0,",
        "if key == output_mode),\n            len(_OUTPUT_MODES) - 1,",
    ),
    "unset-braille-font-saves-config-default": (
        "settings/dialogs.py",
        "            return _BRAILLE_FONT_OPTIONS[0][0]",
        '            return "simbraille"',
    ),
    "past-the-end-scheme-raises": (
        "settings/dialogs.py",
        "        if index < 0 or index >= len(_VIEW_SCHEME_OPTIONS):",
        "        if index < 0:",
    ),
    "width-spin-max-off-by-one": (
        "settings/dialogs.py",
        "            max=MAX_CONVERSION_WIDTH,",
        "            max=MAX_CONVERSION_WIDTH - 1,",
    ),
    "width-reload-not-clamped": (
        "settings/dialogs.py",
        "        self.width_spin.SetValue(\n"
        "            max(\n"
        "                MIN_CONVERSION_WIDTH,\n"
        "                min(MAX_CONVERSION_WIDTH, settings.width),\n"
        "            )\n"
        "        )",
        "        self.width_spin.SetValue(settings.width)",
    ),
    "font-size-initial-not-clamped": (
        "settings/dialogs.py",
        "            initial=max(\n"
        "                VIEW_FONT_SIZE_MIN,\n"
        "                min(VIEW_FONT_SIZE_MAX, view.font_size),\n"
        "            ),",
        "            initial=view.font_size,",
    ),
    "none-selected-also-for-math": (
        "settings/dialogs.py",
        'if key not in {"default", "math"}:',
        'if key != "default":',
    ),
    "table-field-labels-reordered": (
        "settings/dialogs.py",
        '        ("zh", _("Chinese Translation Table"), "zh"),\n        ("ja", _("Japanese Translation Table"), "ja"),',
        '        ("ja", _("Japanese Translation Table"), "ja"),\n        ("zh", _("Chinese Translation Table"), "zh"),',
    ),
    "math-choices-reversed": (
        "settings/dialogs.py",
        '                TableOption(file_name="UEB", display_name="UEB"),\n'
        '                TableOption(file_name="Nemeth", display_name="Nemeth"),',
        '                TableOption(file_name="Nemeth", display_name="Nemeth"),\n'
        '                TableOption(file_name="UEB", display_name="UEB"),',
    ),
    "table-names-not-retranslated": (
        "settings/dialogs.py",
        "display_name=_(table.displayName)",
        "display_name=table.displayName",
    ),
    "empty-row-stays-enabled": (
        "settings/dialogs.py",
        "            if not options:\n                choice.Disable()",
        "            if not options:\n                pass",
    ),
    "unknown-table-selects-last": (
        "settings/dialogs.py",
        "        if index is None:\n            index = 0",
        "        if index is None:\n            index = len(options) - 1",
    ),
    "validation-checks-math-first": (
        "settings/dialogs.py",
        "        for key, label, _lang in self.CHOICE_SPECS:\n            if key in",
        "        for key, label, _lang in reversed(self.CHOICE_SPECS):\n            if key in",
    ),
    "save-drops-math": (
        "settings/dialogs.py",
        "            for key, _label, _lang in self.CHOICE_SPECS\n        }",
        "            for key, _label, _lang in self.CHOICE_SPECS[:-1]\n        }",
    ),
    "width-not-clamped-below": (
        "settings/translation.py",
        "    return max(MIN_CONVERSION_WIDTH, min(MAX_CONVERSION_WIDTH, width))",
        "    return min(MAX_CONVERSION_WIDTH, width)",
    ),
    "unknown-scheme-becomes-dark": (
        "settings/view.py",
        "else DEFAULT_VIEW_SCHEME,",
        'else "dark",',
    ),
    "dark-foreground-off-by-one": (
        "gui.py",
        '\t"dark": {\n\t\t"background": wx.Colour(0, 0, 0),\n\t\t"foreground": wx.Colour(255, 255, 255),',
        '\t"dark": {\n\t\t"background": wx.Colour(0, 0, 0),\n\t\t"foreground": wx.Colour(255, 255, 254),',
    ),
    "simbraille-face-only-when-registered": (
        "gui.py",
        '\t\t\tand (self._simbraille_font_available or sys.platform == "win32")',
        "\t\t\tand self._simbraille_font_available",
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
ls $T/tools
```

Expected:

```text
settings_mutants.py
```

- [ ] **Step 3: Record the baseline suite, the focused modules, the msgids and both fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
```

Expected (973 tests with the P2-5 failure; the focused set runs 57, `test_settings_dialogs` 47):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 973 tests
FAILED (failures=1, skipped=9)
Ran 57 tests
OK
Ran 47 tests
OK
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
```

---

### Task 1: Characterize the option lists (spec step 1, part A)

Nothing in production changes. Every new test passes on the current code by construction; Step 5 shows that the net fails for each of 20 deliberate breakages.

- [ ] **Step 1: Add the panel characterization and the table-name guard to `tests/test_settings_dialogs.py`.** New imports (`ast`, `SimpleNamespace`, `config`, `i18n`), the recording `wx.Choice`/`wx.SpinCtrl`, the fake tables, `build_panel`/`grid_rows`, and the classes `TranslationPanelOptionsTest` (A1), `ViewPanelOptionsTest` (A2, K1), `TranslationTablesPanelOptionsTest` (A3, K2, K4) and `TableDisplayNameGuardTest` (A6, kept permanently). Additions only.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index ce7d196..085dd27 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -1,8 +1,10 @@
 from __future__ import annotations
 
+import ast
 import sys
 import unittest
 from pathlib import Path
+from types import SimpleNamespace
 from unittest.mock import Mock, call, patch
 
 from tests import wx_stub
@@ -20,6 +22,8 @@ with _SCOPE.loading():
 setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
 
+import config
+import i18n
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
@@ -774,5 +778,423 @@ class SingletonSlotIndependenceTest(unittest.TestCase):
         settings_dialog.Destroy.assert_called_once_with()
 
 
+# --- P2-3 characterization: the option lists as the settings panels show them.
+# The panels are built for real under the settings stub scope and read the real
+# zh_TW catalog. settings.dialogs._ is never patched here (P2-3 spec, Test Plan):
+# the labels must be what a user sees, not what a patched _ returns.
+
+
+class RecordingChoice:
+    """``wx.Choice`` stand-in that keeps its items, selection and enabled state."""
+
+    def __init__(self, parent=None, choices=()):
+        self.items = list(choices)
+        self.selection = -1
+        self.enabled = True
+
+    def AppendItems(self, items):
+        self.items.extend(items)
+
+    def GetSelection(self):
+        return self.selection
+
+    def SetSelection(self, index):
+        self.selection = index
+
+    def Disable(self):
+        self.enabled = False
+
+
+class RecordingSpin:
+    """``wx.SpinCtrl`` stand-in that keeps its range and value."""
+
+    def __init__(self, parent=None, min=0, max=100, initial=0):
+        self.minimum = min
+        self.maximum = max
+        self.value = initial
+
+    def GetValue(self):
+        return self.value
+
+    def SetValue(self, value):
+        self.value = value
+
+    def Bind(self, event, handler):
+        pass
+
+
+def fake_table(file_name, display_name, output=True):
+    return SimpleNamespace(fileName=file_name, displayName=display_name, output=output)
+
+
+# English display names are what a source run gets from braille/tables/__tables.py;
+# the zhcn-g2 name is already translated, as in a packaged run (P2-3 spec D6).
+FAKE_TABLES = (
+    fake_table("zh-tw.ctb", "Chinese (Taiwan, Mandarin)"),
+    fake_table("zhcn-g2.ctb", "中文 (中國) 漢語雙拚盲文"),
+    fake_table("en-ueb-g1.ctb", "Unified English Braille Code grade 1"),
+    fake_table("en-GB-g2.ctb", "English (U.K.) grade 2"),
+    fake_table("ja-kantenji.utb", "Japanese (Kantenji) literary braille"),
+    fake_table("eo-g1.ctb", "Esperanto grade 1"),
+    fake_table("unicode-braille.utb", "Unicode braille", output=False),
+)
+ENGLISH_TABLE_NAMES = {"zhcn-g2.ctb": "Chinese (China, Mandarin) Double-phonic Braille System"}
+
+TABLE_ROW_LABELS = ["預設轉譯表", "英文轉譯表", "中文轉譯表", "日文轉譯表", "數學轉譯表"]
+# What each row lists for FAKE_TABLES: translated, sorted by the lower-cased name,
+# "None selected" first in the en/zh/ja rows only, math as is.
+FAKE_TABLE_ROWS = [
+    ["世界文一級", "中文 (中國) 漢語雙拚盲文", "中文 (台灣) 注音", "日文 (漢點字) 書寫", "英文 (英國) 二級", "英文統一一級"],
+    ["未選擇", "英文 (英國) 二級", "英文統一一級"],
+    ["未選擇", "中文 (中國) 漢語雙拚盲文", "中文 (台灣) 注音"],
+    ["未選擇", "日文 (漢點字) 書寫"],
+    ["UEB", "Nemeth"],
+]
+
+
+def build_panel(
+    panel_name,
+    *,
+    translation=TranslationSettings("unicode", 40, "default"),
+    tables=None,
+    view=ViewSettings(12, "light", "simbraille"),
+    table_list=FAKE_TABLES,
+):
+    """Build a real settings panel with recording choices and spins and a fake ``listTables``."""
+    module = sys.modules["settings.dialogs"]
+    snapshot = DotExpressSettingsSnapshot.create(
+        translation=translation,
+        translation_tables={} if tables is None else tables,
+        view=view,
+    )
+    owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"])
+    with (
+        patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin),
+        patch.object(module, "listTables", Mock(return_value=list(table_list))),
+    ):
+        return getattr(module, panel_name)(None, owner)
+
+
+def grid_rows(panel):
+    """The panel's (label, control) rows, in layout order."""
+    (grid, *_rest), _kwargs = panel.sizer.children[0]
+    widgets = [args[0] for args, _kwargs in grid.children]
+    return [(widgets[index].label, widgets[index + 1]) for index in range(0, len(widgets), 2)]
+
+
+def translation_snapshot(output_mode="unicode", width=40):
+    return DotExpressSettingsSnapshot.create(
+        translation=TranslationSettings(output_mode, width, "default"),
+        translation_tables={},
+        view=ViewSettings(12, "light", "simbraille"),
+    )
+
+
+def view_snapshot(font_size=12, scheme="light", braille_font="simbraille"):
+    return DotExpressSettingsSnapshot.create(
+        translation=TranslationSettings("unicode", 40, "default"),
+        translation_tables={},
+        view=ViewSettings(font_size, scheme, braille_font),
+    )
+
+
+def tables_snapshot(tables):
+    return DotExpressSettingsSnapshot.create(
+        translation=TranslationSettings("unicode", 40, "default"),
+        translation_tables=tables,
+        view=ViewSettings(12, "light", "simbraille"),
+    )
+
+
+class TranslationPanelOptionsTest(unittest.TestCase):
+    def test_rows_and_output_mode_choices_show_the_translated_labels_in_order(self) -> None:
+        panel = build_panel("TranslationSettingsPanel")
+
+        rows = grid_rows(panel)
+        self.assertEqual([label for label, _control in rows], ["點字類型", "寬度", "字典"])
+        self.assertEqual([control for _label, control in rows], [panel.output_choice, panel.width_spin, panel.dictionary_choice])
+        self.assertEqual(panel.output_choice.items, ["Unicode", "ASCII"])
+        self.assertEqual(panel.output_choice.items, [i18n._("Unicode"), i18n._("ASCII")])
+
+    def test_stored_output_mode_selects_its_index_and_unknown_selects_the_first(self) -> None:
+        for output_mode, expected in (("unicode", 0), ("ascii", 1), ("braille", 0), ("ASCII", 0), ("", 0)):
+            with self.subTest(output_mode=output_mode):
+                panel = build_panel(
+                    "TranslationSettingsPanel",
+                    translation=TranslationSettings(output_mode, 40, "default"),
+                )
+                self.assertEqual(panel.output_choice.selection, expected)
+
+    def test_save_maps_each_selection_to_its_value_and_out_of_range_to_the_first(self) -> None:
+        baseline = translation_snapshot()
+        panel = build_panel("TranslationSettingsPanel")
+        for selection, expected in ((0, "unicode"), (1, "ascii"), (-1, "unicode"), (2, "unicode")):
+            with self.subTest(selection=selection):
+                panel.output_choice.SetSelection(selection)
+                self.assertEqual(panel.on_save(baseline).translation.output_mode, expected)
+
+    def test_width_spin_range_and_initial_value_are_clamped(self) -> None:
+        for width, expected in ((5, 10), (10, 10), (40, 40), (200, 200), (500, 200)):
+            with self.subTest(width=width):
+                panel = build_panel(
+                    "TranslationSettingsPanel",
+                    translation=TranslationSettings("unicode", width, "default"),
+                )
+                spin = panel.width_spin
+                self.assertEqual((spin.minimum, spin.maximum, spin.value), (10, 200, expected))
+                self.assertEqual(panel.on_save(translation_snapshot()).translation.width, expected)
+
+    def test_load_snapshot_reselects_the_output_mode_and_clamps_the_width(self) -> None:
+        panel = build_panel("TranslationSettingsPanel")
+
+        panel.load_snapshot(translation_snapshot("ascii", 500))
+        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (1, 200))
+
+        panel.load_snapshot(translation_snapshot("braille", 5))
+        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 10))
+
+        panel.load_snapshot(translation_snapshot("unicode", 64))
+        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 64))
+
+
+class ViewPanelOptionsTest(unittest.TestCase):
+    def test_rows_and_choices_show_the_translated_labels_in_order(self) -> None:
+        panel = build_panel("ViewSettingsPanel")
+
+        rows = grid_rows(panel)
+        self.assertEqual([label for label, _control in rows], ["字型大小", "配色", "點字字型"])
+        self.assertEqual(
+            [control for _label, control in rows],
+            [panel.font_size_spin, panel.scheme_choice, panel.braille_font_choice],
+        )
+        self.assertEqual(panel.scheme_choice.items, ["淺色", "深色"])
+        self.assertEqual(panel.scheme_choice.items, [i18n._("Light"), i18n._("Dark")])
+        self.assertEqual(panel.braille_font_choice.items, ["預設", "SimBraille"])
+        self.assertEqual(panel.braille_font_choice.items, [i18n._("Default"), i18n._("SimBraille")])
+
+    def test_stored_values_select_their_index_and_unknown_values_select_the_first(self) -> None:
+        for scheme, braille_font, expected in (
+            ("light", "default", (0, 0)),
+            ("dark", "simbraille", (1, 1)),
+            ("dark", "default", (1, 0)),
+            ("sepia", "serif", (0, 0)),
+            ("Dark", "SimBraille", (0, 0)),
+        ):
+            with self.subTest(scheme=scheme, braille_font=braille_font):
+                panel = build_panel("ViewSettingsPanel", view=ViewSettings(12, scheme, braille_font))
+                self.assertEqual(
+                    (panel.scheme_choice.selection, panel.braille_font_choice.selection),
+                    expected,
+                )
+
+    def test_save_maps_out_of_range_selections_to_the_first_option(self) -> None:
+        # KNOWN QUIRK (P2-3 spec, K1): -1 and past-the-end save the first option,
+        # "default", not config.DEFAULT_BRAILLE_FONT ("simbraille").
+        self.assertEqual(config.DEFAULT_BRAILLE_FONT, "simbraille")
+        baseline = view_snapshot()
+        panel = build_panel("ViewSettingsPanel")
+        for selection, expected in (
+            (0, ("light", "default")),
+            (1, ("dark", "simbraille")),
+            (-1, ("light", "default")),
+            (2, ("light", "default")),
+        ):
+            with self.subTest(selection=selection):
+                panel.scheme_choice.SetSelection(selection)
+                panel.braille_font_choice.SetSelection(selection)
+                view = panel.on_save(baseline).view
+                self.assertEqual((view.scheme, view.braille_font), expected)
+
+    def test_font_size_spin_range_and_initial_value_are_clamped(self) -> None:
+        for font_size, expected in ((5, 8), (8, 8), (12, 12), (48, 48), (99, 48)):
+            with self.subTest(font_size=font_size):
+                panel = build_panel("ViewSettingsPanel", view=ViewSettings(font_size, "light", "default"))
+                spin = panel.font_size_spin
+                self.assertEqual((spin.minimum, spin.maximum, spin.value), (8, 48, expected))
+                self.assertEqual(panel.on_save(view_snapshot()).view.font_size, expected)
+
+    def test_load_snapshot_reselects_both_choices_and_clamps_the_font_size(self) -> None:
+        panel = build_panel("ViewSettingsPanel")
+
+        panel.load_snapshot(view_snapshot(99, "dark", "default"))
+        self.assertEqual(
+            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
+            (48, 1, 0),
+        )
+
+        panel.load_snapshot(view_snapshot(5, "sepia", "simbraille"))
+        self.assertEqual(
+            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
+            (8, 0, 1),
+        )
+
+
+class TranslationTablesPanelOptionsTest(unittest.TestCase):
+    STORED = {
+        "default": "zh-tw.ctb",
+        "en": "en-GB-g2.ctb",
+        "zh": "",
+        "ja": "ja-kantenji.utb",
+        "math": "Nemeth",
+    }
+
+    def test_rows_show_the_translated_field_labels_in_order(self) -> None:
+        panel = build_panel("TranslationTablesPanel")
+
+        rows = grid_rows(panel)
+        self.assertEqual([label for label, _control in rows], TABLE_ROW_LABELS)
+        self.assertEqual(
+            TABLE_ROW_LABELS,
+            [
+                i18n._("Default Translation Table"),
+                i18n._("English Translation Table"),
+                i18n._("Chinese Translation Table"),
+                i18n._("Japanese Translation Table"),
+                i18n._("Math Translation Table"),
+            ],
+        )
+
+    def test_each_row_lists_its_tables_sorted_by_translated_name(self) -> None:
+        # KNOWN QUIRK (P2-3 spec, K4): the prefix is a plain startswith on the
+        # lower-cased file name, so "zh" also takes zhcn-g2 and "en" takes en-GB-g2.
+        panel = build_panel("TranslationTablesPanel")
+
+        self.assertEqual([control.items for _label, control in grid_rows(panel)], FAKE_TABLE_ROWS)
+        self.assertEqual([control.enabled for _label, control in grid_rows(panel)], [True] * 5)
+
+    def test_source_run_and_packaged_display_names_give_the_same_rows(self) -> None:
+        english = [
+            fake_table(table.fileName, ENGLISH_TABLE_NAMES.get(table.fileName, table.displayName), table.output)
+            for table in FAKE_TABLES
+        ]
+        packaged = [fake_table(table.fileName, i18n._(table.displayName), table.output) for table in english]
+        self.assertNotEqual([table.displayName for table in english], [table.displayName for table in packaged])
+
+        for table_list in (english, packaged):
+            with self.subTest(first=table_list[0].displayName):
+                panel = build_panel("TranslationTablesPanel", table_list=table_list)
+                self.assertEqual([control.items for _label, control in grid_rows(panel)], FAKE_TABLE_ROWS)
+
+    def test_stored_file_names_select_their_rows_and_save_in_field_order(self) -> None:
+        panel = build_panel("TranslationTablesPanel", tables=self.STORED)
+
+        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [2, 1, 0, 1, 1])
+        saved = panel.on_save(tables_snapshot({})).translation_tables
+        self.assertEqual(saved, self.STORED)
+        self.assertEqual(list(saved), ["default", "en", "zh", "ja", "math"])
+        self.assertTrue(panel.is_valid())
+        self.assertIsNone(panel.validation_error())
+
+    def test_unknown_or_missing_file_names_select_the_first_option(self) -> None:
+        # KNOWN QUIRK (P2-3 spec, K2): an unknown stored value silently selects
+        # index 0, and saving then stores that option.
+        panel = build_panel(
+            "TranslationTablesPanel",
+            tables={"default": "missing.ctb", "en": "zh-tw.ctb", "math": "Braille"},
+        )
+
+        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [0, 0, 0, 0, 0])
+        self.assertEqual(
+            panel.on_save(tables_snapshot({})).translation_tables,
+            {"default": "eo-g1.ctb", "en": "", "zh": "", "ja": "", "math": "UEB"},
+        )
+
+    def test_load_snapshot_reselects_every_row(self) -> None:
+        panel = build_panel("TranslationTablesPanel")
+        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [0, 0, 0, 0, 0])
+
+        panel.load_snapshot(tables_snapshot(self.STORED))
+
+        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [2, 1, 0, 1, 1])
+
+    def test_without_tables_the_default_row_is_disabled_and_reported_first(self) -> None:
+        panel = build_panel("TranslationTablesPanel", tables=self.STORED, table_list=())
+
+        rows = grid_rows(panel)
+        self.assertEqual(
+            [(control.items, control.enabled, control.selection) for _label, control in rows],
+            [
+                ([], False, -1),
+                (["未選擇"], True, 0),
+                (["未選擇"], True, 0),
+                (["未選擇"], True, 0),
+                (["UEB", "Nemeth"], True, 1),
+            ],
+        )
+        self.assertFalse(panel.is_valid())
+        self.assertEqual(panel.validation_error(), ("請先選擇預設轉譯表。", rows[0][1]))
+        self.assertEqual(
+            panel.on_save(tables_snapshot({})).translation_tables,
+            {"default": "", "en": "", "zh": "", "ja": "", "math": "Nemeth"},
+        )
+
+    def test_validation_checks_the_required_rows_in_field_order(self) -> None:
+        panel = build_panel("TranslationTablesPanel", tables=self.STORED)
+        rows = grid_rows(panel)
+        default_choice, math_choice = rows[0][1], rows[4][1]
+
+        math_choice.SetSelection(-1)
+        self.assertFalse(panel.is_valid())
+        self.assertEqual(panel.validation_error(), ("請先選擇數學轉譯表。", math_choice))
+
+        default_choice.SetSelection(-1)
+        self.assertEqual(panel.validation_error(), ("請先選擇預設轉譯表。", default_choice))
+
+        for _label, control in rows[1:4]:
+            control.SetSelection(-1)
+        default_choice.SetSelection(0)
+        math_choice.SetSelection(1)
+        self.assertTrue(panel.is_valid())
+        self.assertIsNone(panel.validation_error())
+        self.assertEqual(
+            panel.on_save(tables_snapshot({})).translation_tables,
+            {"default": "eo-g1.ctb", "en": "", "zh": "", "ja": "", "math": "Nemeth"},
+        )
+
+
+def _tables_module_entries():
+    """(file name, display msgid, output) of every addTable call, read without importing __tables.py."""
+    path = Path(__file__).resolve().parents[1] / "braille" / "tables" / "__tables.py"
+    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
+    entries = []
+    for node in ast.walk(tree):
+        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "addTable":
+            file_name, display = node.args[0], node.args[1]
+            assert isinstance(display, ast.Call) and display.func.id == "_", ast.dump(display)
+            output = all(
+                not (keyword.arg == "output" and keyword.value.value is False)
+                for keyword in node.keywords
+            )
+            entries.append((file_name.value, display.args[0].value, output))
+    return entries
+
+
+class TableDisplayNameGuardTest(unittest.TestCase):
+    """Why settings.dialogs translates table names again (P2-3 spec D6). Kept permanently.
+
+    __tables.py looks for its catalog in braille/locales, which only the packaged
+    build has: a source run gets English display names, a packaged run zh_TW ones.
+    The dialog's _() must give the same names either way.
+    """
+
+    def test_translating_a_table_name_twice_changes_nothing(self) -> None:
+        entries = _tables_module_entries()
+        self.assertEqual(len(entries), 198)
+        self.assertEqual(sum(output for _file_name, _name, output in entries), 196)
+
+        not_idempotent = [
+            name for _file_name, name, _output in entries if i18n._(i18n._(name)) != i18n._(name)
+        ]
+        self.assertEqual(not_idempotent, [])
+
+    def test_sorted_output_names_are_the_same_from_english_or_translated_names(self) -> None:
+        names = [name for _file_name, name, output in _tables_module_entries() if output]
+        from_english = sorted((i18n._(name) for name in names), key=str.lower)
+        from_translated = sorted((i18n._(i18n._(name)) for name in names), key=str.lower)
+
+        self.assertEqual(from_english, from_translated)
+        self.assertEqual(from_english[:3], ["世界文一級", "中國通用盲文 (簡體中文字)", "中庫德文一級"])
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_settings_dialogs.py | 422 ++++++++++++++++++++++++++++++++++
 1 file changed, 422 insertions(+)
```

- [ ] **Step 2: Add the normalizer characterization (A4).** `TranslationSettingsNormalizeTest` and `ViewSettingsNormalizeTest`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_translation_settings.py b/client/tests/test_translation_settings.py
index bd201d0..2fce7d7 100644
--- a/client/tests/test_translation_settings.py
+++ b/client/tests/test_translation_settings.py
@@ -8,6 +8,7 @@ from settings.translation import (
     DEFAULT_TRANSLATION_SETTINGS,
     TranslationSettings,
     load_translation_settings,
+    normalize_translation_settings,
     save_translation_settings,
 )
 
@@ -79,5 +80,29 @@ class TranslationSettingsTest(unittest.TestCase):
             )
 
 
+class TranslationSettingsNormalizeTest(unittest.TestCase):
+    """P2-3 characterization: what normalization keeps and replaces."""
+
+    def normalize(self, output_mode="unicode", width=40):
+        return normalize_translation_settings(
+            TranslationSettings(output_mode, width, "default"),
+            ["default"],
+        )
+
+    def test_every_output_mode_is_kept_and_unknown_modes_become_the_default(self) -> None:
+        for output_mode in ("unicode", "ascii"):
+            with self.subTest(output_mode=output_mode):
+                self.assertEqual(self.normalize(output_mode).output_mode, output_mode)
+        self.assertEqual(config.DEFAULT_OUTPUT_MODE, "unicode")
+        for output_mode in ("", "UNICODE", "braille", "default"):
+            with self.subTest(output_mode=output_mode):
+                self.assertEqual(self.normalize(output_mode).output_mode, "unicode")
+
+    def test_width_is_clamped_at_both_ends(self) -> None:
+        for width, expected in ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200)):
+            with self.subTest(width=width):
+                self.assertEqual(self.normalize(width=width).width, expected)
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_view_settings.py b/client/tests/test_view_settings.py
index 351dc89..d93bceb 100644
--- a/client/tests/test_view_settings.py
+++ b/client/tests/test_view_settings.py
@@ -33,5 +33,39 @@ class ViewSettingsTest(unittest.TestCase):
         self.assertEqual(load_view_settings(), expected)
 
 
+class ViewSettingsNormalizeTest(unittest.TestCase):
+    """P2-3 characterization: what normalization keeps and replaces."""
+
+    def test_every_scheme_and_braille_font_is_kept(self) -> None:
+        for scheme in ("light", "dark"):
+            for braille_font in ("default", "simbraille"):
+                with self.subTest(scheme=scheme, braille_font=braille_font):
+                    self.assertEqual(
+                        normalize_view_settings(ViewSettings(12, scheme, braille_font)),
+                        ViewSettings(12, scheme, braille_font),
+                    )
+
+    def test_unknown_values_become_the_config_defaults(self) -> None:
+        self.assertEqual((config.DEFAULT_VIEW_SCHEME, config.DEFAULT_BRAILLE_FONT), ("light", "simbraille"))
+        for scheme, braille_font in (("Dark", "Default"), ("sepia", "serif"), ("", "")):
+            with self.subTest(scheme=scheme, braille_font=braille_font):
+                self.assertEqual(
+                    normalize_view_settings(ViewSettings(12, scheme, braille_font)),
+                    ViewSettings(12, "light", "simbraille"),
+                )
+        self.assertEqual(
+            normalize_view_settings(ViewSettings(12, "dark", "unknown")),
+            ViewSettings(12, "dark", "simbraille"),
+        )
+
+    def test_font_size_is_clamped_at_both_ends(self) -> None:
+        for font_size, expected in ((-1, 8), (7, 8), (8, 8), (12, 12), (48, 48), (49, 48)):
+            with self.subTest(font_size=font_size):
+                self.assertEqual(
+                    normalize_view_settings(ViewSettings(font_size, "light", "default")).font_size,
+                    expected,
+                )
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_settings_dialogs.py     | 422 ++++++++++++++++++++++++++++++
 client/tests/test_translation_settings.py |  25 ++
 client/tests/test_view_settings.py        |  34 +++
 3 files changed, 481 insertions(+)
```

- [ ] **Step 3: Add the gui colour and SimBraille characterization (A5).** `EditorViewSettingsCharacterizationTest` in the gui scope module.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 7672100..9e40d4b 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -3546,5 +3546,84 @@ class FrameExportViewMethodsTest(unittest.TestCase):
         )
 
 
+class _RecordingFont:
+    """``wx.Font`` stand-in: the font it copies and the calls made on it."""
+
+    def __init__(self, base):
+        self.base = base
+        self.calls = []
+
+    def SetPointSize(self, size):
+        self.calls.append(("SetPointSize", size))
+
+    def SetFaceName(self, name):
+        self.calls.append(("SetFaceName", name))
+
+
+class EditorViewSettingsCharacterizationTest(unittest.TestCase):
+    """P2-3 characterization: the editor colours of each scheme and the SimBraille face rule."""
+
+    LIGHT = ((255, 255, 255), (0, 0, 0))
+    DARK = ((0, 0, 0), (255, 255, 255))
+
+    def test_view_schemes_give_each_scheme_its_editor_colours(self) -> None:
+        self.assertEqual(
+            gui.VIEW_SCHEMES,
+            {
+                "light": {"background": (255, 255, 255), "foreground": (0, 0, 0)},
+                "dark": {"background": (0, 0, 0), "foreground": (255, 255, 255)},
+            },
+        )
+        self.assertEqual(list(gui.VIEW_SCHEMES), ["light", "dark"])
+        for colours in gui.VIEW_SCHEMES.values():
+            self.assertEqual(list(colours), ["background", "foreground"])
+            for colour in colours.values():
+                self.assertIsInstance(colour, gui.wx.Colour)
+
+    def test_apply_editor_view_settings_sets_size_colours_and_the_simbraille_face(self) -> None:
+        cases = (
+            # settings, font registered, platform, expected size, colours, SimBraille face
+            (ViewSettings(14, "light", "simbraille"), True, "linux", 14, self.LIGHT, True),
+            (ViewSettings(14, "dark", "simbraille"), False, "linux", 14, self.DARK, False),
+            (ViewSettings(14, "dark", "simbraille"), False, "win32", 14, self.DARK, True),
+            (ViewSettings(20, "light", "default"), True, "win32", 20, self.LIGHT, False),
+            (ViewSettings(99, "sepia", "serif"), True, "linux", 48, self.LIGHT, True),
+        )
+        for settings, registered, platform, size, (background, foreground), face in cases:
+            with self.subTest(settings=settings, registered=registered, platform=platform):
+                frame = object.__new__(gui.BrailleFrame)
+                frame.steps = Mock()
+                frame.input_txt = frame.steps.input_txt
+                frame.output_txt = frame.steps.output_txt
+                frame.Layout = frame.steps.Layout
+                frame._default_output_font = "default-output-font"
+                frame._simbraille_font_available = registered
+                with (
+                    patch.object(gui.wx, "Font", _RecordingFont),
+                    patch.object(gui, "sys", SimpleNamespace(platform=platform)),
+                ):
+                    frame._apply_editor_view_settings(settings)
+
+                output_font = frame.output_txt.SetFont.call_args.args[0]
+                self.assertEqual(output_font.base, "default-output-font")
+                self.assertEqual(
+                    output_font.calls,
+                    [("SetPointSize", size)] + ([("SetFaceName", "SimBraille")] if face else []),
+                )
+                frame.input_txt.GetFont.return_value.SetPointSize.assert_called_once_with(size)
+                self.assertEqual(
+                    [entry for entry in frame.steps.mock_calls if entry[0].endswith(("Colour", "Refresh", "Layout"))],
+                    [
+                        call.input_txt.SetBackgroundColour(background),
+                        call.input_txt.SetForegroundColour(foreground),
+                        call.input_txt.Refresh(),
+                        call.output_txt.SetBackgroundColour(background),
+                        call.output_txt.SetForegroundColour(foreground),
+                        call.output_txt.Refresh(),
+                        call.Layout(),
+                    ],
+                )
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_gui_document_flows.py   |  79 ++++++
 client/tests/test_settings_dialogs.py     | 422 ++++++++++++++++++++++++++++++
 client/tests/test_translation_settings.py |  25 ++
 client/tests/test_view_settings.py        |  34 +++
 4 files changed, 560 insertions(+)
```

- [ ] **Step 4: Run part A on the current code.**

```bash
$PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_gui_document_flows.EditorViewSettingsCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (67 + 5 + 5 + 2, all passing on the unchanged code):

```text
Ran 79 tests
OK
```

- [ ] **Step 5: Mutation check: every mutant must fail part A.** The runner works on a copy under `$T/mut`; the repo is not changed.

```bash
$PY -I $T/tools/settings_mutants.py $REPO/client $T/mut
git -C $REPO status --short
```

Expected (no mutant with `failures=0 errors=0`; `past-the-end-scheme-raises` fails with an `IndexError`; only the four test files are modified):

```text
output-labels-untranslated: failures=1 errors=0
scheme-order-swapped: failures=9 errors=0
unknown-output-mode-selects-last: failures=4 errors=0
unset-braille-font-saves-config-default: failures=2 errors=0
past-the-end-scheme-raises: failures=0 errors=1
width-spin-max-off-by-one: failures=5 errors=0
width-reload-not-clamped: failures=1 errors=0
font-size-initial-not-clamped: failures=2 errors=0
none-selected-also-for-math: failures=8 errors=0
table-field-labels-reordered: failures=6 errors=0
math-choices-reversed: failures=8 errors=0
table-names-not-retranslated: failures=6 errors=0
empty-row-stays-enabled: failures=1 errors=0
unknown-table-selects-last: failures=2 errors=0
validation-checks-math-first: failures=1 errors=0
save-drops-math: failures=4 errors=0
width-not-clamped-below: failures=2 errors=0
unknown-scheme-becomes-dark: failures=5 errors=0
dark-foreground-off-by-one: failures=3 errors=0
simbraille-face-only-when-registered: failures=1 errors=0
 M client/tests/test_gui_document_flows.py
 M client/tests/test_settings_dialogs.py
 M client/tests/test_translation_settings.py
 M client/tests/test_view_settings.py
```

- [ ] **Step 6: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (973 + 27):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1000 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_settings_dialogs.py client/tests/test_translation_settings.py client/tests/test_view_settings.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize settings option lists

Pin, with the real zh_TW catalog and without patching settings.dialogs._,
what the three settings panels show and save: choice labels and order,
selected index for stored and unknown values, saved value for every
selection (K1), spin ranges and clamps, the translation table rows,
their sorted names, "None selected", K2 and K4, the validation order;
the normalizers; the gui scheme colours and the SimBraille face rule;
and a permanent guard that translating a table name twice changes
nothing (D6).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize settings option lists
```

---

### Task 2: Add the option source (spec step 2, part B)

- [ ] **Step 1: Write the failing tests.** The new module `tests/test_settings_options.py` (`OptionListsTest`, `OptionHelpersTest`, `ConfigDefaultsInvariantTest`, `OptionsModuleGuardTest`; 4 spaces; imports `settings.options` at module level, outside any stub scope) and the consumer test in `tests/test_i18n.py`.

```bash
cat > tests/test_settings_options.py <<'EOF'
"""Tests of the settings option source (``settings.options``, P2-3).

``settings.options`` is imported here at module level, outside any stub scope,
so the descriptor classes are the same objects for every test module.
"""

from __future__ import annotations

import ast
import dataclasses
import unittest
from pathlib import Path

import config
from conversion import math_braille_codes
from settings.options import (
    BRAILLE_FONT_DEFAULT,
    BRAILLE_FONT_OPTIONS,
    BRAILLE_FONT_SIMBRAILLE,
    CONVERSION_WIDTH_RANGE,
    OUTPUT_MODE_ASCII,
    OUTPUT_MODE_OPTIONS,
    OUTPUT_MODE_UNICODE,
    TRANSLATION_TABLE_FIELDS,
    VIEW_FONT_SIZE_RANGE,
    VIEW_SCHEME_DARK,
    VIEW_SCHEME_LIGHT,
    VIEW_SCHEME_OPTIONS,
    IntRange,
    SettingOption,
    TranslationTableField,
    ViewSchemeOption,
    normalize_option_value,
    option_index,
    option_value_at,
    option_values,
)

CLIENT_ROOT = Path(__file__).resolve().parents[1]


def _module_tree(relative_path: str) -> ast.Module:
    path = CLIENT_ROOT / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class OptionListsTest(unittest.TestCase):
    def test_output_modes(self) -> None:
        self.assertEqual((OUTPUT_MODE_UNICODE, OUTPUT_MODE_ASCII), ("unicode", "ascii"))
        self.assertEqual(
            OUTPUT_MODE_OPTIONS,
            (SettingOption("unicode", "Unicode"), SettingOption("ascii", "ASCII")),
        )

    def test_view_schemes_carry_their_editor_colours(self) -> None:
        self.assertEqual((VIEW_SCHEME_LIGHT, VIEW_SCHEME_DARK), ("light", "dark"))
        self.assertEqual(
            VIEW_SCHEME_OPTIONS,
            (
                ViewSchemeOption("light", "Light", (255, 255, 255), (0, 0, 0)),
                ViewSchemeOption("dark", "Dark", (0, 0, 0), (255, 255, 255)),
            ),
        )
        for option in VIEW_SCHEME_OPTIONS:
            self.assertIsInstance(option, SettingOption)

    def test_braille_fonts(self) -> None:
        self.assertEqual((BRAILLE_FONT_DEFAULT, BRAILLE_FONT_SIMBRAILLE), ("default", "simbraille"))
        self.assertEqual(
            BRAILLE_FONT_OPTIONS,
            (SettingOption("default", "Default"), SettingOption("simbraille", "SimBraille")),
        )

    def test_integer_ranges(self) -> None:
        self.assertEqual(CONVERSION_WIDTH_RANGE, IntRange(10, 200))
        self.assertEqual(VIEW_FONT_SIZE_RANGE, IntRange(8, 48))

    def test_translation_table_fields(self) -> None:
        self.assertEqual(
            TRANSLATION_TABLE_FIELDS,
            (
                TranslationTableField("default", "Default Translation Table", None, True),
                TranslationTableField("en", "English Translation Table", "en", False),
                TranslationTableField("zh", "Chinese Translation Table", "zh", False),
                TranslationTableField("ja", "Japanese Translation Table", "ja", False),
                TranslationTableField("math", "Math Translation Table", None, True, ("UEB", "Nemeth")),
            ),
        )

    def test_lists_are_tuples_of_frozen_descriptors(self) -> None:
        for options in (OUTPUT_MODE_OPTIONS, VIEW_SCHEME_OPTIONS, BRAILLE_FONT_OPTIONS, TRANSLATION_TABLE_FIELDS):
            with self.subTest(first=options[0]):
                self.assertIs(type(options), tuple)
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    options[0].label = "changed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            CONVERSION_WIDTH_RANGE.minimum = 0
        self.assertEqual(len({*OUTPUT_MODE_OPTIONS, *VIEW_SCHEME_OPTIONS, *BRAILLE_FONT_OPTIONS}), 6)


class OptionHelpersTest(unittest.TestCase):
    def test_option_values_keep_the_visible_order(self) -> None:
        self.assertEqual(option_values(OUTPUT_MODE_OPTIONS), ("unicode", "ascii"))
        self.assertEqual(option_values(VIEW_SCHEME_OPTIONS), ("light", "dark"))
        self.assertEqual(option_values(BRAILLE_FONT_OPTIONS), ("default", "simbraille"))
        self.assertEqual(option_values(()), ())

    def test_normalize_keeps_members_and_replaces_anything_else_with_the_default(self) -> None:
        for value in ("default", "simbraille"):
            with self.subTest(value=value):
                self.assertEqual(normalize_option_value(BRAILLE_FONT_OPTIONS, value, "simbraille"), value)
        for value in ("", "SimBraille", "serif", None):
            with self.subTest(value=value):
                self.assertEqual(normalize_option_value(BRAILLE_FONT_OPTIONS, value, "simbraille"), "simbraille")
        self.assertEqual(normalize_option_value((), "light", "dark"), "dark")

    def test_option_index_finds_the_first_equal_value_or_zero(self) -> None:
        self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, "light"), 0)
        self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, "dark"), 1)
        for value in ("Dark", "", "sepia", None):
            with self.subTest(value=value):
                self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, value), 0)
        repeated = (SettingOption("a", "A"), SettingOption("b", "B"), SettingOption("b", "B again"))
        self.assertEqual(option_index(repeated, "b"), 1)
        self.assertEqual(option_index((), "a"), 0)

    def test_option_value_at_maps_out_of_range_indexes_to_the_first_option(self) -> None:
        # KNOWN QUIRK (P2-3 spec, K1): the first option, not the config default.
        self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, 0), "default")
        self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, 1), "simbraille")
        for index in (-1, -2, 2, 99):
            with self.subTest(index=index):
                self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, index), "default")

    def test_int_range_clamps_at_both_ends(self) -> None:
        cases = ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200))
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(CONVERSION_WIDTH_RANGE.clamp(value), expected)
        self.assertEqual(IntRange(8, 48).clamp(7), 8)
        self.assertEqual(IntRange(8, 48).clamp(49), 48)


class ConfigDefaultsInvariantTest(unittest.TestCase):
    """The persisted defaults stay in config (P2-3 spec D3) and must be valid options."""

    def test_choice_defaults_are_option_values(self) -> None:
        self.assertIn(config.DEFAULT_OUTPUT_MODE, option_values(OUTPUT_MODE_OPTIONS))
        self.assertIn(config.DEFAULT_VIEW_SCHEME, option_values(VIEW_SCHEME_OPTIONS))
        self.assertIn(config.DEFAULT_BRAILLE_FONT, option_values(BRAILLE_FONT_OPTIONS))

    def test_integer_defaults_are_inside_their_ranges(self) -> None:
        self.assertEqual(CONVERSION_WIDTH_RANGE.clamp(config.DEFAULT_CONVERSION_WIDTH), config.DEFAULT_CONVERSION_WIDTH)
        self.assertEqual(VIEW_FONT_SIZE_RANGE.clamp(config.DEFAULT_VIEW_FONT_SIZE), config.DEFAULT_VIEW_FONT_SIZE)

    def test_table_fields_match_the_default_translation_tables(self) -> None:
        self.assertEqual(
            tuple(field.key for field in TRANSLATION_TABLE_FIELDS),
            tuple(config.DEFAULT_TRANSLATION_TABLES),
        )
        self.assertEqual({field.key for field in TRANSLATION_TABLE_FIELDS if field.required}, {"default", "math"})
        self.assertEqual([field.key for field in TRANSLATION_TABLE_FIELDS if field.fixed_choices is not None], ["math"])

    def test_math_choices_and_default_come_from_the_leaf_module(self) -> None:
        math_field = TRANSLATION_TABLE_FIELDS[-1]
        self.assertIs(math_field.fixed_choices, math_braille_codes.MATH_BRAILLE_TABLES)
        self.assertEqual(config.DEFAULT_TRANSLATION_TABLES["math"], math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE)
        self.assertIn(math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE, math_field.fixed_choices)

    def test_config_names_the_math_default_instead_of_repeating_it(self) -> None:
        tables = next(
            node.value
            for node in _module_tree("config.py").body
            if isinstance(node, ast.Assign)
            and [target.id for target in node.targets] == ["DEFAULT_TRANSLATION_TABLES"]
        )
        values = dict(zip((key.value for key in tables.keys), tables.values))
        self.assertIsInstance(values["math"], ast.Name)
        self.assertEqual(values["math"].id, "DEFAULT_MATH_BRAILLE_TABLE")


class OptionsModuleGuardTest(unittest.TestCase):
    ALLOWED_IMPORTS = {"__future__", "collections.abc", "dataclasses", "i18n", "conversion.math_braille_codes"}
    LABEL_CONSTRUCTORS = {"SettingOption", "ViewSchemeOption", "TranslationTableField"}

    def test_imports_only_n_and_the_math_leaf(self) -> None:
        tree = _module_tree("settings/options.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, "no relative (settings sibling) imports")
                imported.add(node.module)
                if node.module == "i18n":
                    self.assertEqual([alias.name for alias in node.names], ["N_"])
        self.assertEqual(imported, self.ALLOWED_IMPORTS)
        for root in ("wx", "gui", "dialog", "ui", "config", "braille", "settings"):
            self.assertFalse(any(name == root or name.startswith(root + ".") for name in imported), root)

    def test_never_translates(self) -> None:
        tree = _module_tree("settings/options.py")
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("_", names)

    def test_every_label_is_a_literal_n_marker(self) -> None:
        labels = []
        for node in ast.walk(_module_tree("settings/options.py")):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in self.LABEL_CONSTRUCTORS:
                label = node.args[1]
                self.assertIsInstance(label, ast.Call)
                self.assertEqual(label.func.id, "N_")
                self.assertIsInstance(label.args[0], ast.Constant)
                labels.append(label.args[0].value)
        expected = [
            option.label
            for options in (OUTPUT_MODE_OPTIONS, VIEW_SCHEME_OPTIONS, BRAILLE_FONT_OPTIONS, TRANSLATION_TABLE_FIELDS)
            for option in options
        ]
        self.assertEqual(sorted(labels), sorted(expected))
        self.assertEqual(len(labels), 11)


if __name__ == "__main__":
    unittest.main()
EOF
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_i18n.py b/client/tests/test_i18n.py
index 6f54a00..2685efc 100644
--- a/client/tests/test_i18n.py
+++ b/client/tests/test_i18n.py
@@ -117,6 +117,9 @@ class SharedSetupConsumerTest(unittest.TestCase):
     def test_settings_dialogs_uses_shared_i18n(self) -> None:
         self.assert_uses_shared_i18n("settings/dialogs.py", {"_"})
 
+    def test_settings_options_uses_shared_i18n(self) -> None:
+        self.assert_uses_shared_i18n("settings/options.py", {"N_"})
+
     def test_dictionary_entries_uses_shared_i18n(self) -> None:
         self.assert_uses_shared_i18n("dictionaries/entries.py", {"_"})
 
EOF
```

- [ ] **Step 2: Run them red.**

```bash
$PY -m unittest tests.test_settings_options tests.test_i18n.SharedSetupConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the module is missing):

```text
ERROR: test_settings_options (unittest.loader._FailedTest.test_settings_options)
ImportError: Failed to import test module: test_settings_options
ModuleNotFoundError: No module named 'settings.options'
ERROR: test_settings_options_uses_shared_i18n (tests.test_i18n.SharedSetupConsumerTest.test_settings_options_uses_shared_i18n)
FileNotFoundError: [Errno 2] No such file or directory: 'client/settings/options.py'
Ran 7 tests
FAILED (errors=2)
```

- [ ] **Step 3: Write `client/settings/options.py`.** Descriptors, lists, ranges, table fields and helpers exactly as the spec's sketch; `N_` labels only; the D3 reason in the module docstring.

```bash
cat > settings/options.py <<'EOF'
"""The one definition of every settings option list (P2-3).

Each list is a tuple of frozen descriptors in the order the settings dialog
shows them. ``value`` is what config.json stores. ``label`` is a msgid marked
with ``N_``; whoever shows it translates it with ``_()``. Math table choices
are proper names, shown as is, and come from ``conversion.math_braille_codes``.

The persisted defaults (``DEFAULT_*``) stay in ``config``: ``config`` cannot
import this module, because importing ``settings.options`` runs
``settings/__init__``, which imports ``settings.translation``, which imports
from ``config`` (an import cycle). Tests check that every default is one of
the values here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from conversion.math_braille_codes import MATH_BRAILLE_TABLES
from i18n import N_

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class SettingOption:
    value: str
    """The value persisted in config.json."""
    label: str
    """The msgid shown for the value; translate it with ``_()`` when shown."""


@dataclass(frozen=True)
class ViewSchemeOption(SettingOption):
    background: RGB
    foreground: RGB


@dataclass(frozen=True)
class IntRange:
    minimum: int
    maximum: int

    def clamp(self, value: int) -> int:
        return max(self.minimum, min(self.maximum, value))


@dataclass(frozen=True)
class TranslationTableField:
    key: str
    """The key in the translation_tables setting."""
    label: str
    """The msgid of the row label."""
    file_prefix: str | None
    """Keep the tables whose lower-cased file name starts with it; None keeps every output table."""
    required: bool
    """No "None selected" entry, and a value must be chosen before Apply."""
    fixed_choices: tuple[str, ...] | None = None
    """Choices shown as is, untranslated, instead of the braille tables."""


OUTPUT_MODE_UNICODE = "unicode"
OUTPUT_MODE_ASCII = "ascii"
VIEW_SCHEME_LIGHT = "light"
VIEW_SCHEME_DARK = "dark"
BRAILLE_FONT_DEFAULT = "default"
BRAILLE_FONT_SIMBRAILLE = "simbraille"

OUTPUT_MODE_OPTIONS = (
    SettingOption(OUTPUT_MODE_UNICODE, N_("Unicode")),
    SettingOption(OUTPUT_MODE_ASCII, N_("ASCII")),
)
VIEW_SCHEME_OPTIONS = (
    ViewSchemeOption(VIEW_SCHEME_LIGHT, N_("Light"), (255, 255, 255), (0, 0, 0)),
    ViewSchemeOption(VIEW_SCHEME_DARK, N_("Dark"), (0, 0, 0), (255, 255, 255)),
)
BRAILLE_FONT_OPTIONS = (
    SettingOption(BRAILLE_FONT_DEFAULT, N_("Default")),
    SettingOption(BRAILLE_FONT_SIMBRAILLE, N_("SimBraille")),
)
CONVERSION_WIDTH_RANGE = IntRange(10, 200)
VIEW_FONT_SIZE_RANGE = IntRange(8, 48)
TRANSLATION_TABLE_FIELDS = (
    TranslationTableField("default", N_("Default Translation Table"), None, True),
    TranslationTableField("en", N_("English Translation Table"), "en", False),
    TranslationTableField("zh", N_("Chinese Translation Table"), "zh", False),
    TranslationTableField("ja", N_("Japanese Translation Table"), "ja", False),
    TranslationTableField("math", N_("Math Translation Table"), None, True, MATH_BRAILLE_TABLES),
)


def option_values(options: Sequence[SettingOption]) -> tuple[str, ...]:
    return tuple(option.value for option in options)


def normalize_option_value(options: Sequence[SettingOption], value: str, default: str) -> str:
    """Return ``value`` when it is one of the option values, else ``default``."""
    if value in option_values(options):
        return value
    return default


def option_index(options: Sequence[SettingOption], value: str) -> int:
    """Return the index of the first option with ``value``, or 0 when there is none."""
    for index, option in enumerate(options):
        if option.value == value:
            return index
    return 0


def option_value_at(options: Sequence[SettingOption], index: int) -> str:
    """Return the value at ``index``; the first option's value when ``index`` is out of range."""
    if index < 0 or index >= len(options):
        return options[0].value
    return options[index].value
EOF
```

- [ ] **Step 4: Run again: only the config check is red.**

```bash
$PY -m unittest tests.test_settings_options tests.test_i18n.SharedSetupConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (config still repeats `"UEB"`):

```text
FAIL: test_config_names_the_math_default_instead_of_repeating_it (tests.test_settings_options.ConfigDefaultsInvariantTest.test_config_names_the_math_default_instead_of_repeating_it)
AssertionError: Constant(value='UEB', kind=None) is not an instance of <class 'ast.Name'>
Ran 25 tests
FAILED (failures=1)
```

- [ ] **Step 5: Name the leaf constant in `config.py` (value unchanged) and run green.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/config.py b/client/config.py
index 6b1c650..a42d074 100644
--- a/client/config.py
+++ b/client/config.py
@@ -31,7 +31,7 @@ DEFAULT_TRANSLATION_TABLES = {
     "en": "en-ueb-g1.ctb",
     "zh": "zh-tw.ctb",
     "ja": "ja-rokutenkanji.utb",
-    "math": "UEB",
+    "math": DEFAULT_MATH_BRAILLE_TABLE,
 }
 DEFAULT_OUTPUT_MODE = "unicode"
 DEFAULT_CONVERSION_WIDTH = 40
EOF
$PY -m unittest tests.test_settings_options tests.test_i18n tests.test_config tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
```

Expected (the `N_` labels are the same msgids the dialog already has):

```text
Ran 283 tests
OK (skipped=2)
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 6: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1000 + 20):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1020 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/settings/options.py client/config.py client/tests/test_settings_options.py client/tests/test_i18n.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add settings option source

Add client/settings/options.py: frozen descriptors for the output modes,
view schemes (with their editor colours), braille fonts and translation
table fields, the width and font-size ranges, and four lookup helpers.
Labels are N_() msgids; math choices are the conversion leaf's tuple.
Nothing reads it yet, except that config's math default now names
DEFAULT_MATH_BRAILLE_TABLE (same value).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add settings option source
```

---

### Task 3: Normalize through the option source (spec step 3, plus the spins: correction 1)

- [ ] **Step 1: Add the guard and run it red.** `OptionSourceConsumerTest.test_normalizers_define_no_option_lists_or_ranges` (refinement 6).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_options.py b/client/tests/test_settings_options.py
index 7120055..72e8510 100644
--- a/client/tests/test_settings_options.py
+++ b/client/tests/test_settings_options.py
@@ -221,5 +221,40 @@ class OptionsModuleGuardTest(unittest.TestCase):
         self.assertEqual(len(labels), 11)
 
 
+# Option values that only settings/options.py (and config's DEFAULT_*) may spell out.
+# "default" is left out: it is also the default dictionary's name.
+OPTION_VALUE_LITERALS = {"unicode", "ascii", "light", "dark", "simbraille", "UEB", "Nemeth"}
+
+
+def _assigned_names(body: list[ast.stmt]) -> set[str]:
+    names = set()
+    for node in body:
+        if isinstance(node, ast.Assign):
+            targets = node.targets
+        elif isinstance(node, ast.AnnAssign):
+            targets = [node.target]
+        else:
+            continue
+        names.update(target.id for target in targets if isinstance(target, ast.Name))
+    return names
+
+
+def _string_constants(tree: ast.AST) -> set[str]:
+    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
+
+
+class OptionSourceConsumerTest(unittest.TestCase):
+    """The consumers keep no option list, range or option value of their own (P2-3 spec D9, AC6)."""
+
+    def test_normalizers_define_no_option_lists_or_ranges(self) -> None:
+        for relative_path, expected in (
+            ("settings/translation.py", {"DEFAULT_TRANSLATION_SETTINGS"}),
+            ("settings/view.py", set()),
+        ):
+            with self.subTest(module=relative_path):
+                tree = _module_tree(relative_path)
+                self.assertEqual(_assigned_names(tree.body), expected)
+                self.assertEqual(_string_constants(tree) & OPTION_VALUE_LITERALS, set())
+
 if __name__ == "__main__":
     unittest.main()
EOF
$PY -m unittest tests.test_settings_options.OptionSourceConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (both modules still define their own tuples and constants):

```text
FAIL: test_normalizers_define_no_option_lists_or_ranges (tests.test_settings_options.OptionSourceConsumerTest.test_normalizers_define_no_option_lists_or_ranges) (module='settings/translation.py')
AssertionError: Items in the first set but not the second:
FAIL: test_normalizers_define_no_option_lists_or_ranges (tests.test_settings_options.OptionSourceConsumerTest.test_normalizers_define_no_option_lists_or_ranges) (module='settings/view.py')
AssertionError: Items in the first set but not the second:
Ran 1 test
FAILED (failures=2)
```

- [ ] **Step 2: Migrate `settings/translation.py`, `settings/view.py` and the dialog's two spins.** The old constants are removed; `_normalize_output_mode`/`_normalize_width` keep their names and call `normalize_option_value`/`CONVERSION_WIDTH_RANGE.clamp`; the dialog imports the two ranges from `.options`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/settings/dialogs.py b/client/settings/dialogs.py
index f806735..6c3c0a3 100644
--- a/client/settings/dialogs.py
+++ b/client/settings/dialogs.py
@@ -14,18 +14,10 @@ from conversion.preprocessing.user_script import (
 )
 from i18n import _
 from ui.dialog_base import SingletonDialogMixin
+from .options import CONVERSION_WIDTH_RANGE, VIEW_FONT_SIZE_RANGE
 from .state import DotExpressSettingsSnapshot
-from .translation import (
-    MAX_CONVERSION_WIDTH,
-    MIN_CONVERSION_WIDTH,
-    TranslationSettings,
-)
-from .view import (
-    VIEW_FONT_SIZE_MAX,
-    VIEW_FONT_SIZE_MIN,
-    ViewSettings,
-    normalize_view_settings,
-)
+from .translation import TranslationSettings
+from .view import ViewSettings, normalize_view_settings
 
 
 class SettingsPanelAccessible(wx.Accessible):
@@ -389,12 +381,9 @@ class TranslationSettingsPanel(SettingsPanel):
         width_label = wx.StaticText(self, label=_("Width"))
         self.width_spin = wx.SpinCtrl(
             self,
-            min=MIN_CONVERSION_WIDTH,
-            max=MAX_CONVERSION_WIDTH,
-            initial=max(
-                MIN_CONVERSION_WIDTH,
-                min(MAX_CONVERSION_WIDTH, settings.width),
-            ),
+            min=CONVERSION_WIDTH_RANGE.minimum,
+            max=CONVERSION_WIDTH_RANGE.maximum,
+            initial=CONVERSION_WIDTH_RANGE.clamp(settings.width),
         )
         grid.Add(width_label, 0, wx.ALIGN_CENTER_VERTICAL)
         grid.Add(self.width_spin, 1, wx.EXPAND)
@@ -412,12 +401,7 @@ class TranslationSettingsPanel(SettingsPanel):
 
     def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
         settings = snapshot.translation
-        self.width_spin.SetValue(
-            max(
-                MIN_CONVERSION_WIDTH,
-                min(MAX_CONVERSION_WIDTH, settings.width),
-            )
-        )
+        self.width_spin.SetValue(CONVERSION_WIDTH_RANGE.clamp(settings.width))
         self._select_output_mode(settings.output_mode)
         self._select_dictionary(settings.selected_dictionary)
 
@@ -600,12 +584,9 @@ class ViewSettingsPanel(SettingsPanel):
         font_size_label = wx.StaticText(self, label=_("Font Size"))
         self.font_size_spin = wx.SpinCtrl(
             self,
-            min=VIEW_FONT_SIZE_MIN,
-            max=VIEW_FONT_SIZE_MAX,
-            initial=max(
-                VIEW_FONT_SIZE_MIN,
-                min(VIEW_FONT_SIZE_MAX, view.font_size),
-            ),
+            min=VIEW_FONT_SIZE_RANGE.minimum,
+            max=VIEW_FONT_SIZE_RANGE.maximum,
+            initial=VIEW_FONT_SIZE_RANGE.clamp(view.font_size),
         )
         grid.Add(font_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
         grid.Add(self.font_size_spin, 1, wx.EXPAND)
@@ -636,12 +617,7 @@ class ViewSettingsPanel(SettingsPanel):
 
     def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
         view = snapshot.view
-        self.font_size_spin.SetValue(
-            max(
-                VIEW_FONT_SIZE_MIN,
-                min(VIEW_FONT_SIZE_MAX, view.font_size),
-            )
-        )
+        self.font_size_spin.SetValue(VIEW_FONT_SIZE_RANGE.clamp(view.font_size))
         self._select_scheme(view.scheme)
         self._select_braille_font(view.braille_font)
         self.font_size_dirty = False
diff --git a/client/settings/translation.py b/client/settings/translation.py
index b4ddab4..17d08e4 100644
--- a/client/settings/translation.py
+++ b/client/settings/translation.py
@@ -13,11 +13,7 @@ from config import (
     set_selected_dictionary,
 )
 from dictionaries.actions import resolve_dictionary_selection
-
-
-MIN_CONVERSION_WIDTH = 10
-MAX_CONVERSION_WIDTH = 200
-SUPPORTED_OUTPUT_MODES = ("unicode", "ascii")
+from .options import CONVERSION_WIDTH_RANGE, OUTPUT_MODE_OPTIONS, normalize_option_value
 
 
 @dataclass(frozen=True)
@@ -35,13 +31,15 @@ DEFAULT_TRANSLATION_SETTINGS = TranslationSettings(
 
 
 def _normalize_output_mode(output_mode: str) -> str:
-    if output_mode in SUPPORTED_OUTPUT_MODES:
-        return output_mode
-    return DEFAULT_TRANSLATION_SETTINGS.output_mode
+    return normalize_option_value(
+        OUTPUT_MODE_OPTIONS,
+        output_mode,
+        DEFAULT_TRANSLATION_SETTINGS.output_mode,
+    )
 
 
 def _normalize_width(width: int) -> int:
-    return max(MIN_CONVERSION_WIDTH, min(MAX_CONVERSION_WIDTH, width))
+    return CONVERSION_WIDTH_RANGE.clamp(width)
 
 
 def normalize_translation_settings(
diff --git a/client/settings/view.py b/client/settings/view.py
index a8eccb4..182cea1 100644
--- a/client/settings/view.py
+++ b/client/settings/view.py
@@ -9,11 +9,12 @@ from config import (
     get_view_scheme,
     set_view_settings,
 )
-
-VIEW_FONT_SIZE_MIN = 8
-VIEW_FONT_SIZE_MAX = 48
-VIEW_SCHEME_KEYS = ("light", "dark")
-BRAILLE_FONT_KEYS = ("default", "simbraille")
+from .options import (
+    BRAILLE_FONT_OPTIONS,
+    VIEW_FONT_SIZE_RANGE,
+    VIEW_SCHEME_OPTIONS,
+    normalize_option_value,
+)
 
 
 @dataclass(frozen=True)
@@ -25,12 +26,12 @@ class ViewSettings:
 
 def normalize_view_settings(settings: ViewSettings) -> ViewSettings:
     return ViewSettings(
-        font_size=max(VIEW_FONT_SIZE_MIN, min(VIEW_FONT_SIZE_MAX, settings.font_size)),
-        scheme=settings.scheme if settings.scheme in VIEW_SCHEME_KEYS else DEFAULT_VIEW_SCHEME,
-        braille_font=(
-            settings.braille_font
-            if settings.braille_font in BRAILLE_FONT_KEYS
-            else DEFAULT_BRAILLE_FONT
+        font_size=VIEW_FONT_SIZE_RANGE.clamp(settings.font_size),
+        scheme=normalize_option_value(VIEW_SCHEME_OPTIONS, settings.scheme, DEFAULT_VIEW_SCHEME),
+        braille_font=normalize_option_value(
+            BRAILLE_FONT_OPTIONS,
+            settings.braille_font,
+            DEFAULT_BRAILLE_FONT,
         ),
     )
 
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/settings/dialogs.py            | 46 +++++++++--------------------------
 client/settings/translation.py        | 16 ++++++------
 client/settings/view.py               | 23 +++++++++---------
 client/tests/test_settings_options.py | 35 ++++++++++++++++++++++++++
 4 files changed, 65 insertions(+), 55 deletions(-)
```

- [ ] **Step 3: Run green: the guard, part A unchanged, the neighbours, the full suite.**

```bash
$PY -m unittest tests.test_settings_options tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_gui_document_flows tests.test_settings_state tests.test_config tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1020 + 1):

```text
Ran 285 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1021 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/settings/translation.py client/settings/view.py client/settings/dialogs.py client/tests/test_settings_options.py
git -C $REPO commit -q -F - <<'EOF'
refactor: normalize settings through option source

settings/translation.py and settings/view.py normalize with the option
source's values and ranges, and the settings dialog's width and font
size spins read the same ranges. SUPPORTED_OUTPUT_MODES,
VIEW_SCHEME_KEYS, BRAILLE_FONT_KEYS and the four min/max constants are
removed (the dialog imported the min/max constants, so its spins move
in this commit).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: normalize settings through option source
```

---

### Task 4: Build the panels from the option source (spec step 4)

- [ ] **Step 1: Add the guard and run it red.** `OptionSourceConsumerTest.test_settings_panels_define_no_option_lists_or_option_values`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_options.py b/client/tests/test_settings_options.py
index 72e8510..6841ba4 100644
--- a/client/tests/test_settings_options.py
+++ b/client/tests/test_settings_options.py
@@ -256,5 +256,16 @@ class OptionSourceConsumerTest(unittest.TestCase):
                 self.assertEqual(_assigned_names(tree.body), expected)
                 self.assertEqual(_string_constants(tree) & OPTION_VALUE_LITERALS, set())
 
+    def test_settings_panels_define_no_option_lists_or_option_values(self) -> None:
+        tree = _module_tree("settings/dialogs.py")
+        self.assertEqual(_assigned_names(tree.body), {"_DEAD_WINDOW_ERROR_TYPES", "CommitSettings"})
+        tables_panel = next(
+            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TranslationTablesPanel"
+        )
+        self.assertEqual(_assigned_names(tables_panel.body), {"title", "panel_description", "TABLE_FIELDS"})
+        table_keys = {field.key for field in TRANSLATION_TABLE_FIELDS}
+        self.assertEqual(_string_constants(tree) & (OPTION_VALUE_LITERALS | table_keys), set())
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
$PY -m unittest tests.test_settings_options.OptionSourceConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (the dialog still has its three tuples, `CHOICE_SPECS` and the literal keys):

```text
FAIL: test_settings_panels_define_no_option_lists_or_option_values (tests.test_settings_options.OptionSourceConsumerTest.test_settings_panels_define_no_option_lists_or_option_values)
AssertionError: Items in the first set but not the second:
Ran 2 tests
FAILED (failures=1)
```

- [ ] **Step 2: Migrate `settings/dialogs.py` and drop the two `CHOICE_SPECS` assignments from the validation tests.** Choices are built with `[_(option.label) for option in ...]`; the six selection helpers call `option_value_at`/`option_index`; `TranslationTablesPanel` walks `TABLE_FIELDS = TRANSLATION_TABLE_FIELDS` with `_(field.label)`, prepends "None selected" when `not field.required`, and `_options_for_field` uses `fixed_choices`; the D6 comment is added. The two tests in `test_settings_dialogs.py` keep everything else (the class default is the same five fields).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/settings/dialogs.py b/client/settings/dialogs.py
index 6c3c0a3..61105a7 100644
--- a/client/settings/dialogs.py
+++ b/client/settings/dialogs.py
@@ -14,7 +14,17 @@ from conversion.preprocessing.user_script import (
 )
 from i18n import _
 from ui.dialog_base import SingletonDialogMixin
-from .options import CONVERSION_WIDTH_RANGE, VIEW_FONT_SIZE_RANGE
+from .options import (
+    BRAILLE_FONT_OPTIONS,
+    CONVERSION_WIDTH_RANGE,
+    OUTPUT_MODE_OPTIONS,
+    TRANSLATION_TABLE_FIELDS,
+    VIEW_FONT_SIZE_RANGE,
+    VIEW_SCHEME_OPTIONS,
+    TranslationTableField,
+    option_index,
+    option_value_at,
+)
 from .state import DotExpressSettingsSnapshot
 from .translation import TranslationSettings
 from .view import ViewSettings, normalize_view_settings
@@ -342,22 +352,6 @@ class TableOption:
     display_name: str
 
 
-_OUTPUT_MODES: list[tuple[str, str]] = [
-    ("unicode", _("Unicode")),
-    ("ascii", _("ASCII")),
-]
-
-_VIEW_SCHEME_OPTIONS: list[tuple[str, str]] = [
-    ("light", _("Light")),
-    ("dark", _("Dark")),
-]
-
-_BRAILLE_FONT_OPTIONS: list[tuple[str, str]] = [
-    ("default", _("Default")),
-    ("simbraille", _("SimBraille")),
-]
-
-
 class TranslationSettingsPanel(SettingsPanel):
     title = _("Translation")
     panel_description = _(
@@ -373,7 +367,7 @@ class TranslationSettingsPanel(SettingsPanel):
         output_label = wx.StaticText(self, label=_("Braille Type"))
         self.output_choice = wx.Choice(
             self,
-            choices=[label for _key, label in _OUTPUT_MODES],
+            choices=[_(option.label) for option in OUTPUT_MODE_OPTIONS],
         )
         grid.Add(output_label, 0, wx.ALIGN_CENTER_VERTICAL)
         grid.Add(self.output_choice, 1, wx.EXPAND)
@@ -414,10 +408,7 @@ class TranslationSettingsPanel(SettingsPanel):
         return snapshot.with_translation(value)
 
     def _selected_output_mode(self) -> str:
-        index = self.output_choice.GetSelection()
-        if index < 0 or index >= len(_OUTPUT_MODES):
-            return _OUTPUT_MODES[0][0]
-        return _OUTPUT_MODES[index][0]
+        return option_value_at(OUTPUT_MODE_OPTIONS, self.output_choice.GetSelection())
 
     def _selected_dictionary(self) -> str:
         if not self.dictionary_names:
@@ -428,11 +419,7 @@ class TranslationSettingsPanel(SettingsPanel):
         return self.dictionary_names[index]
 
     def _select_output_mode(self, output_mode: str) -> None:
-        index = next(
-            (idx for idx, (key, _label) in enumerate(_OUTPUT_MODES) if key == output_mode),
-            0,
-        )
-        self.output_choice.SetSelection(index)
+        self.output_choice.SetSelection(option_index(OUTPUT_MODE_OPTIONS, output_mode))
 
     def _select_dictionary(self, dictionary_name: str) -> None:
         if not self.dictionary_names:
@@ -452,63 +439,58 @@ class TranslationTablesPanel(SettingsPanel):
         "Translation table mappings for different languages"
     )
 
-    CHOICE_SPECS: list[tuple[str, str, str | None]] = [
-        ("default", _("Default Translation Table"), None),
-        ("en", _("English Translation Table"), "en"),
-        ("zh", _("Chinese Translation Table"), "zh"),
-        ("ja", _("Japanese Translation Table"), "ja"),
-        ("math", _("Math Translation Table"), None),
-    ]
+    TABLE_FIELDS: tuple[TranslationTableField, ...] = TRANSLATION_TABLE_FIELDS
 
     def make_settings(self) -> None:
         self.table_options = self._load_table_options()
         self._choice_controls: dict[str, wx.Choice] = {}
         self._options_by_key: dict[str, list[TableOption]] = {}
         language_map = self.owner.snapshot.translation_tables
-        grid = wx.FlexGridSizer(len(self.CHOICE_SPECS), 2, 8, 8)
+        grid = wx.FlexGridSizer(len(self.TABLE_FIELDS), 2, 8, 8)
         grid.AddGrowableCol(1, 1)
-        for key, label, lang_code in self.CHOICE_SPECS:
-            static_lbl = wx.StaticText(self, label=label)
-            options = self._options_for_key(key, lang_code)
-            if key not in {"default", "math"}:
+        for field in self.TABLE_FIELDS:
+            static_lbl = wx.StaticText(self, label=_(field.label))
+            options = self._options_for_field(field)
+            if not field.required:
                 options = [TableOption(file_name="", display_name=_("None selected"))] + options
             choice = wx.Choice(self)
             choice.AppendItems([option.display_name for option in options])
-            self._choice_controls[key] = choice
-            self._options_by_key[key] = options
+            self._choice_controls[field.key] = choice
+            self._options_by_key[field.key] = options
             grid.Add(static_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
             grid.Add(choice, 1, wx.EXPAND)
             if not options:
                 choice.Disable()
-            self._select_choice_value(key, language_map.get(key))
+            self._select_choice_value(field.key, language_map.get(field.key))
         sizer = wx.BoxSizer(wx.VERTICAL)
         sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
         self.SetSizer(sizer)
 
     def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
         language_map = snapshot.translation_tables
-        for key, _label, _lang in self.CHOICE_SPECS:
-            self._select_choice_value(key, language_map.get(key))
+        for field in self.TABLE_FIELDS:
+            self._select_choice_value(field.key, language_map.get(field.key))
 
     def is_valid(self) -> bool:
-        return bool(
-            self._selected_file_name("default")
-            and self._selected_file_name("math")
+        return all(
+            self._selected_file_name(field.key)
+            for field in self.TABLE_FIELDS
+            if field.required
         )
 
     def validation_error(self) -> tuple[str, wx.Window | None] | None:
-        for key, label, _lang in self.CHOICE_SPECS:
-            if key in {"default", "math"} and not self._selected_file_name(key):
+        for field in self.TABLE_FIELDS:
+            if field.required and not self._selected_file_name(field.key):
                 return (
-                    _("Please select a value for {field}.").format(field=label),
-                    self._choice_controls.get(key),
+                    _("Please select a value for {field}.").format(field=_(field.label)),
+                    self._choice_controls.get(field.key),
                 )
         return None
 
     def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
         values = {
-            key: self._selected_file_name(key)
-            for key, _label, _lang in self.CHOICE_SPECS
+            field.key: self._selected_file_name(field.key)
+            for field in self.TABLE_FIELDS
         }
         return snapshot.with_translation_tables(values)
 
@@ -552,16 +534,17 @@ class TranslationTablesPanel(SettingsPanel):
             if option.file_name.lower().startswith(prefix)
         ]
 
-    def _options_for_key(self, key: str, lang_code: str | None) -> list[TableOption]:
-        if key == "math":
-            return [
-                TableOption(file_name="UEB", display_name="UEB"),
-                TableOption(file_name="Nemeth", display_name="Nemeth"),
-            ]
-        return self._options_for_lang(lang_code)
+    def _options_for_field(self, field: TranslationTableField) -> list[TableOption]:
+        if field.fixed_choices is not None:
+            return [TableOption(file_name=value, display_name=value) for value in field.fixed_choices]
+        return self._options_for_lang(field.file_prefix)
 
     def _load_table_options(self) -> list[TableOption]:
         tables = [table for table in listTables() if getattr(table, "output", False)]
+        # _() again on purpose (P2-3 spec D6): __tables.py looks for its catalog in
+        # braille/locales, which only the packaged build has, so a source run gets
+        # English display names here. A packaged run gets them translated already,
+        # and translating them again returns them unchanged.
         options = [
             TableOption(file_name=table.fileName, display_name=_(table.displayName))
             for table in tables
@@ -594,7 +577,7 @@ class ViewSettingsPanel(SettingsPanel):
         scheme_label = wx.StaticText(self, label=_("Scheme"))
         self.scheme_choice = wx.Choice(
             self,
-            choices=[label for _key, label in _VIEW_SCHEME_OPTIONS],
+            choices=[_(option.label) for option in VIEW_SCHEME_OPTIONS],
         )
         grid.Add(scheme_label, 0, wx.ALIGN_CENTER_VERTICAL)
         grid.Add(self.scheme_choice, 1, wx.EXPAND)
@@ -602,7 +585,7 @@ class ViewSettingsPanel(SettingsPanel):
         braille_font_label = wx.StaticText(self, label=_("Braille Font"))
         self.braille_font_choice = wx.Choice(
             self,
-            choices=[label for _key, label in _BRAILLE_FONT_OPTIONS],
+            choices=[_(option.label) for option in BRAILLE_FONT_OPTIONS],
         )
         grid.Add(braille_font_label, 0, wx.ALIGN_CENTER_VERTICAL)
         grid.Add(self.braille_font_choice, 1, wx.EXPAND)
@@ -636,30 +619,16 @@ class ViewSettingsPanel(SettingsPanel):
         self.font_size_dirty = True
 
     def _selected_scheme(self) -> str:
-        index = self.scheme_choice.GetSelection()
-        if index < 0 or index >= len(_VIEW_SCHEME_OPTIONS):
-            return _VIEW_SCHEME_OPTIONS[0][0]
-        return _VIEW_SCHEME_OPTIONS[index][0]
+        return option_value_at(VIEW_SCHEME_OPTIONS, self.scheme_choice.GetSelection())
 
     def _selected_braille_font(self) -> str:
-        index = self.braille_font_choice.GetSelection()
-        if index < 0 or index >= len(_BRAILLE_FONT_OPTIONS):
-            return _BRAILLE_FONT_OPTIONS[0][0]
-        return _BRAILLE_FONT_OPTIONS[index][0]
+        return option_value_at(BRAILLE_FONT_OPTIONS, self.braille_font_choice.GetSelection())
 
     def _select_scheme(self, scheme: str) -> None:
-        index = next(
-            (idx for idx, (key, _label) in enumerate(_VIEW_SCHEME_OPTIONS) if key == scheme),
-            0,
-        )
-        self.scheme_choice.SetSelection(index)
+        self.scheme_choice.SetSelection(option_index(VIEW_SCHEME_OPTIONS, scheme))
 
     def _select_braille_font(self, braille_font: str) -> None:
-        index = next(
-            (idx for idx, (key, _label) in enumerate(_BRAILLE_FONT_OPTIONS) if key == braille_font),
-            0,
-        )
-        self.braille_font_choice.SetSelection(index)
+        self.braille_font_choice.SetSelection(option_index(BRAILLE_FONT_OPTIONS, braille_font))
 
 
 CommitSettings = Callable[
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index 085dd27..fa39f59 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -370,13 +370,6 @@ class TranslationTablesPanelTest(unittest.TestCase):
         default_choice = Mock()
         math_choice = Mock()
         panel = object.__new__(TranslationTablesPanel)
-        panel.CHOICE_SPECS = [
-            ("default", "Default Translation Table", None),
-            ("en", "English Translation Table", "en"),
-            ("zh", "Chinese Translation Table", "zh"),
-            ("ja", "Japanese Translation Table", "ja"),
-            ("math", "Math Translation Table", None),
-        ]
         panel._choice_controls = {
             "default": default_choice,
             "math": math_choice,
@@ -429,13 +422,6 @@ class DotExpressSettingsDialogFlowTest(unittest.TestCase):
         dialog = make_dialog_without_wx_constructor()
         default_choice = Mock()
         panel = object.__new__(TranslationTablesPanel)
-        panel.CHOICE_SPECS = [
-            ("default", "Default Translation Table", None),
-            ("en", "English Translation Table", "en"),
-            ("zh", "Chinese Translation Table", "zh"),
-            ("ja", "Japanese Translation Table", "ja"),
-            ("math", "Math Translation Table", None),
-        ]
         panel._choice_controls = {
             "default": default_choice,
             "math": Mock(),
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/settings/dialogs.py            | 129 +++++++++++++---------------------
 client/tests/test_settings_dialogs.py |  14 ----
 client/tests/test_settings_options.py |  11 +++
 3 files changed, 60 insertions(+), 94 deletions(-)
```

- [ ] **Step 3: Run green, check the msgids, full suite.**

```bash
$PY -m unittest tests.test_settings_options tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_gui_document_flows tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (353 msgids, the same set; 1021 + 1):

```text
Ran 260 tests
OK (skipped=2)
source msgids: 353
SOURCE == SAVED
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1022 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/settings/dialogs.py client/tests/test_settings_dialogs.py client/tests/test_settings_options.py
git -C $REPO commit -q -F - <<'EOF'
refactor: build settings panels from option source

The translation, view and table panels build their choices from the
option source and translate each label with _() when they build the
control (same msgids, same zh_TW text). The six selection helpers use
option_value_at/option_index, and the tables panel walks TABLE_FIELDS:
required replaces the {"default", "math"} sets and fixed_choices the
math dispatch. Keep _(table.displayName), now with a comment (D6). The
two validation tests no longer assign the removed CHOICE_SPECS.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: build settings panels from option source
```

---

### Task 5: Derive the gui view schemes from the option source (spec step 5)

- [ ] **Step 1: Add the guard and run it red.** `OptionSourceConsumerTest.test_gui_spells_out_no_option_values`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_options.py b/client/tests/test_settings_options.py
index 6841ba4..983b6dd 100644
--- a/client/tests/test_settings_options.py
+++ b/client/tests/test_settings_options.py
@@ -267,5 +267,9 @@ class OptionSourceConsumerTest(unittest.TestCase):
         self.assertEqual(_string_constants(tree) & (OPTION_VALUE_LITERALS | table_keys), set())
 
 
+    def test_gui_spells_out_no_option_values(self) -> None:
+        self.assertEqual(_string_constants(_module_tree("gui.py")) & OPTION_VALUE_LITERALS, set())
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
$PY -m unittest tests.test_settings_options.OptionSourceConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (`gui.py` still spells `"light"`, `"dark"` and `"simbraille"`):

```text
FAIL: test_gui_spells_out_no_option_values (tests.test_settings_options.OptionSourceConsumerTest.test_gui_spells_out_no_option_values)
AssertionError: Items in the first set but not the second:
Ran 3 tests
FAILED (failures=1)
```

- [ ] **Step 2: Build `VIEW_SCHEMES` from `VIEW_SCHEME_OPTIONS` and compare with `BRAILLE_FONT_SIMBRAILLE`.** Tabs, as in the rest of `gui.py`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/gui.py b/client/gui.py
index 522f006..91d3f79 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -89,17 +89,15 @@ from settings.view import (
 )
 from settings.state import DotExpressSettingsSnapshot
 from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog, TranslationSettingsPanel
+from settings.options import BRAILLE_FONT_SIMBRAILLE, VIEW_SCHEME_OPTIONS
 
 
 VIEW_SCHEMES = {
-	"light": {
-		"background": wx.Colour(255, 255, 255),
-		"foreground": wx.Colour(0, 0, 0),
-	},
-	"dark": {
-		"background": wx.Colour(0, 0, 0),
-		"foreground": wx.Colour(255, 255, 255),
-	},
+	option.value: {
+		"background": wx.Colour(*option.background),
+		"foreground": wx.Colour(*option.foreground),
+	}
+	for option in VIEW_SCHEME_OPTIONS
 }
 
 logger = get_logger("dotexpress.gui", "gui.log")
@@ -382,7 +380,7 @@ class BrailleFrame(wx.Frame):
 		output_font = wx.Font(self._default_output_font)
 		output_font.SetPointSize(settings.font_size)
 		if (
-			settings.braille_font == "simbraille"
+			settings.braille_font == BRAILLE_FONT_SIMBRAILLE
 			and (self._simbraille_font_available or sys.platform == "win32")
 		):
 			output_font.SetFaceName(SIMBRAILLE_FACE_NAME)
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/gui.py                         | 16 +++++++---------
 client/tests/test_settings_options.py |  4 ++++
 2 files changed, 11 insertions(+), 9 deletions(-)
```

- [ ] **Step 3: Run green and the full suite.**

```bash
$PY -m unittest tests.test_settings_options tests.test_gui_document_flows tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (the 2 skips in `test_gui_document_flows` need a case-insensitive file system; 1022 + 1):

```text
Ran 184 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1023 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_settings_options.py
git -C $REPO commit -q -F - <<'EOF'
refactor: derive gui view schemes from option source

Build gui.VIEW_SCHEMES from the scheme descriptors' colours (same keys,
same wx.Colour values) and compare the braille font with
BRAILLE_FONT_SIMBRAILLE instead of a literal.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: derive gui view schemes from option source
```

---

### Task 6: Final verification against the spec's acceptance criteria (no commit)

- [ ] **Step 1: AC1 roadmap command and AC2 neighbours.**

```bash
$PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_options -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_options 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_translation_golden tests.test_dictionary_entries_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (AC1: 99 tests, all passing; AC2 all green):

```text
99
Ran 99 tests
OK
Ran 290 tests
OK (skipped=2)
```

- [ ] **Step 2: AC3 full suite; AC4 both fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
git -C $REPO diff main --stat -- client/tests/fixtures
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
```

Expected (973 + 50; no fixture diff against `main`):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1023 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
```

- [ ] **Step 3: AC3, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 1023 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=1023 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC3, the option tests alone and in both orders with the stub-scope modules.**

```bash
echo "tests.test_settings_options: $($PY -B -m unittest tests.test_settings_options 2>&1 | grep -E '^(OK|FAILED)')"
for m in test_settings_dialogs test_gui_document_flows; do
  for order in "tests.$m" "tests.$m tests.test_settings_options" "tests.test_settings_options tests.$m"; do
    echo "$order: $($PY -B -m unittest $order 2>&1 | grep -E '^(OK|FAILED)')"
  done
done
```

Expected:

```text
tests.test_settings_options: OK
tests.test_settings_dialogs: OK
tests.test_settings_dialogs tests.test_settings_options: OK
tests.test_settings_options tests.test_settings_dialogs: OK
tests.test_gui_document_flows: OK (skipped=2)
tests.test_gui_document_flows tests.test_settings_options: OK (skipped=2)
tests.test_settings_options tests.test_gui_document_flows: OK (skipped=2)
```

- [ ] **Step 5: AC5-AC7.**

```bash
echo AC5
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json
git -C $REPO diff main --stat -- client/locales scripts client/braille client/conversion client/dual_view client/main.py
echo AC6
cd $REPO
grep -rnE "SUPPORTED_OUTPUT_MODES|VIEW_SCHEME_KEYS|BRAILLE_FONT_KEYS|_OUTPUT_MODES|_VIEW_SCHEME_OPTIONS|_BRAILLE_FONT_OPTIONS|CHOICE_SPECS|_options_for_key|MIN_CONVERSION_WIDTH|MAX_CONVERSION_WIDTH|VIEW_FONT_SIZE_MIN|VIEW_FONT_SIZE_MAX" client --include=*.py
grep -rnE '"(unicode|ascii|light|dark|simbraille|UEB|Nemeth)"' client --include=*.py --exclude-dir=tests | LC_ALL=C sort
cd $REPO/client
echo AC7
$PY -m unittest tests.test_settings_options.OptionsModuleGuardTest tests.test_i18n.SharedSetupConsumerTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo end
```

Expected (353 source msgids, the same 4 only-in-pot wildcards and nothing only in source; nothing from the `main` diff; the first AC6 grep prints nothing, the second (sorted, since `grep -r` follows directory order) only `options.py`, `config.py`'s three `DEFAULT_*`, the math leaf, `output.py` (2), `presenter.py` (1) and `main.py` (1)):

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
client/config.py:36:DEFAULT_OUTPUT_MODE = "unicode"
client/config.py:39:DEFAULT_VIEW_SCHEME = "light"
client/config.py:40:DEFAULT_BRAILLE_FONT = "simbraille"
client/conversion/math_braille_codes.py:1:MATH_BRAILLE_TABLES = ("UEB", "Nemeth")
client/conversion/math_braille_codes.py:2:DEFAULT_MATH_BRAILLE_TABLE = "UEB"
client/conversion/output.py:85:    if request.output_mode == "ascii":
client/conversion/output.py:94:            raise ConversionStageError("ascii", error) from error
client/conversion/presenter.py:84:        "ascii": _("ASCII conversion failed: {error}"),
client/main.py:21:                output_mode="unicode",
client/settings/options.py:63:OUTPUT_MODE_UNICODE = "unicode"
client/settings/options.py:64:OUTPUT_MODE_ASCII = "ascii"
client/settings/options.py:65:VIEW_SCHEME_LIGHT = "light"
client/settings/options.py:66:VIEW_SCHEME_DARK = "dark"
client/settings/options.py:68:BRAILLE_FONT_SIMBRAILLE = "simbraille"
AC7
Ran 9 tests
OK
end
```

- [ ] **Step 6: The branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -6
git -C $REPO diff --stat HEAD~5 HEAD
```

Expected:

```text
refactor: derive gui view schemes from option source
refactor: build settings panels from option source
refactor: normalize settings through option source
refactor: add settings option source
test: characterize settings option lists
docs: plan settings option source
 client/config.py                          |   2 +-
 client/gui.py                             |  16 +-
 client/settings/dialogs.py                | 173 ++++--------
 client/settings/options.py                | 116 ++++++++
 client/settings/translation.py            |  16 +-
 client/settings/view.py                   |  23 +-
 client/tests/test_gui_document_flows.py   |  79 ++++++
 client/tests/test_i18n.py                 |   3 +
 client/tests/test_settings_dialogs.py     | 436 +++++++++++++++++++++++++++++-
 client/tests/test_settings_options.py     | 275 +++++++++++++++++++
 client/tests/test_translation_settings.py |  25 ++
 client/tests/test_view_settings.py        |  34 +++
 12 files changed, 1040 insertions(+), 158 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): on a packaged zh_TW build with NVDA, open Settings on each of the three panels and compare a screenshot and the spoken choice lists with `main` (labels, order, initial selection); switch Scheme and Braille Font and check the editor colours and the SimBraille face; leave en/zh/ja on "None selected" and Apply; an empty Default row shows the validation message and focuses the row. A source run on Windows shows the same translated, sorted table names as the packaged build (D6). `scripts\generate-pot.bat`: the msgid set is unchanged and only the `#:` references of the eleven option labels move to `settings/options.py`. PyInstaller must pick up `settings/options.py` through the static imports in `settings/dialogs.py`, `settings/translation.py`, `settings/view.py` and `gui.py` (read, not run). No visual or string change is intended, so the screenshots are for comparison only.
