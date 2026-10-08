# Font Size Sync (P2-4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the reverse classmethod probe `DotExpressSettingsDialog.sync_open_font_size`. `SingletonDialogMixin` gets a read-only `open_instance()`, `ViewSettingsPanel` gets `sync_font_size(font_size) -> bool` (the pending-edit rule and the spin), `DotExpressSettingsDialog` gets an instance method `sync_font_size(font_size)` plus a private `_view_panel()`, and `gui._set_view_font_size` asks the class for the open dialog and calls the instance method on it. No event bus. Nothing a user sees or hears changes: the same font size reaches the same controls in the same cases, the msgid set stays at 353 and both fixtures are untouched. The spec's quirks 1 and 2 are pinned by tests marked `# KNOWN QUIRK (P2-4 spec, n)`, not fixed.

**Architecture:** Three commits in the spec's order. Task 1 characterizes today's behavior at two levels: the frame (`on_editor_mousewheel` -> `_set_view_font_size` -> the open dialog, in the gui stub scope) and the dialog (the sync on a dialog with no, a clean, a dirty, or a subclassed View panel, in the settings stub scope, with the real `ViewSettingsPanel` built with the dialog as its owner). The dialog-level tests reach the sync through one module helper, so Task 3 changes only that helper. The tests pass by construction; a throwaway mutant runner shows that each of 15 deliberate breakages of the current code makes them fail. Task 2 adds the two hooks red-first. Task 3 switches the helper, renames the two older sync tests and adds an allow-list guard (red), then replaces the probe and the gui call (green); 13 mutants of the new code are all caught.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `types`). wxPython is not installed: the dialog tests run under `tests/wx_stub.py`'s settings profile, the frame tests under its gui profile, `tests/test_dialog_base.py` without any stub scope.

**Spec:** `docs/superpowers/specs/2026-10-08-p2-4-font-size-sync-design.md` (authoritative, commit `bf1c0e0`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p2-4-font-size-sync`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (6, nothing else): production `client/ui/dialog_base.py`, `client/settings/dialogs.py`, `client/gui.py`; tests `client/tests/test_dialog_base.py`, `client/tests/test_settings_dialogs.py`, `client/tests/test_gui_document_flows.py`. Never touch `client/locales/`, `client/tests/fixtures/`, `client/tests/wx_stub.py`, `client/settings/state.py`, `client/settings/view.py`, `client/ui/shortcuts.py`, `client/ui/dual_view.py` or `scripts/`.
- Indentation: `client/ui/dialog_base.py`, `client/settings/dialogs.py` and the three test modules use 4 spaces; `client/gui.py` uses tabs. The patches carry the exact characters (the test modules contain zh_TW text as UTF-8); run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes and no msgid changes: the source msgid set (`source msgids: 353`) is compared with the Task 0 snapshot in Task 4 (`SOURCE == SAVED`). No `.po`/`.mo` change, no `generate_pot.bat` run.
- Fixtures are never touched: `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`), checked in Task 0 and Task 4.
- Every new test that needs an open dialog puts it in the slot with `patch.object(<dialog class>, "_instance", ...)`, never by plain assignment on a real dialog class (spec, Test Plan A). `tests/test_dialog_base.py` keeps its own pattern (a fresh `singleton_class(...)` per subtest).
- No event bus, no `Signal`, no frame-held `_settings_dialog` reference, no liveness probe in `open_instance()`, no alias for `sync_open_font_size` (spec D1, D2, D3, D7).
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, and absolute paths are stripped from errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p24impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.
- Baseline (re-verified at `bf1c0e0`, the spec commit; code identical to `6dd65e3` = `main`): `$PY -m unittest discover -s tests` gives `Ran 1023 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: AC6's `grep -n "_instance" client/gui.py` cannot print nothing.** The spec's own `gui.py` change calls `DotExpressSettingsDialog.open_instance()`, and `open_instance` contains the substring `_instance`, so the grep prints that line (checked on the dry clone). What AC6 means is that `gui.py` never touches the slot attribute; the check is `grep -nw "_instance" client/gui.py` (whole word: `_` is a word character, so `open_instance` does not match). Task 4 runs both and expects the one `open_instance()` line from the plain grep and nothing from `-w`.
2. **Factual correction: Part C's absence assertion would break AC6's first grep.** Part C adds `"sync_open_font_size" not in vars(DotExpressSettingsDialog)` to `tests/test_settings_dialogs.py`, but AC6 requires `grep -rn "sync_open_font_size" client --include=*.py --exclude-dir=.venv` (tests included) to print nothing. The guard is written as an allow-list instead, so it never spells the removed name: `DotExpressSettingsDialogFlowTest.test_font_size_sync_is_one_instance_method` asserts that the only name in `vars(DotExpressSettingsDialog)` containing `font_size` is `sync_font_size`, and that it is a plain function (an instance method, not a `classmethod`). It is red on the old code (`['sync_open_font_size'] != ['sync_font_size']`), which gives Task 3 its failing test.
3. **Refinement: Part A is larger than the spec's list, and N is fixed at 20 (1023 -> 1043).** Task 1 adds 14 tests: 8 in `FontSizeSyncCharacterizationTest` (the spec's 5 items, with the clamp check as its own test that also covers 49/48/8/7 and a built panel, plus two Review Focus tests: a spin whose `SetValue` reports a change like `EVT_TEXT`, and Apply without visiting the View panel) and 6 in `ViewFontSizeSyncCharacterizationTest` (the spec's 5 items, the no-step case also covering `ControlDown()` with rotation 0, plus one Review Focus test: an open Text Processing dialog is left alone; the first test also asserts the settings dialog is not iconized, raised, focused or shown). Task 2 adds 5 (3 `open_instance` tests in `SingletonDialogMixinTest`, 2 `ViewSettingsPanel.sync_font_size` tests, clean and dirty, in `ViewSettingsPanelTest`). Task 3 adds 1 (the allow-list guard). Per module: `test_settings_dialogs` 67 -> 75 -> 77 -> 78, `test_gui_document_flows` 145 -> 151, `test_dialog_base` 23 -> 26.
4. **Refinement: the subclass case of Part A item 2 uses a hand-built panel.** `build_panel` builds panels by name from the module, so the `ViewSettingsPanel` subclass is made with `object.__new__` (with `font_size_dirty = False` and a `RecordingSpin`), stored under index 0 next to a `Mock` panel under index 1, whose `mock_calls` must stay empty (the sync touches only the View panel). `build_panel` gains only the spec's `owner=` keyword.
5. **Refinement: the two older sync tests also move to `patch.object`.** Task 3 renames them to `test_sync_font_size_updates_snapshot_before_view_panel_exists` and `test_sync_font_size_keeps_dirty_view_panel_draft`, calls the helper, and replaces their `try`/`finally` slot assignment with `patch.object` (same effect, matches the rule for new tests). Their assertions are unchanged.
6. **Clarification: the stubs mask a missing `font_size_dirty`.** The spec's risk note (a hand-built panel without the attribute now raises `AttributeError`) holds for real wx. Under `tests/wx_stub.py` every widget masks missing attributes with a no-op function, which is truthy, so the old `getattr(..., False)` and the new direct read both treat such a panel as dirty. No test relies on either; every panel in the tests sets the attribute. The same masking makes the red steps of Tasks 2 and 3 show up as assertion failures (`None is not True`, `12 != 20`) rather than `AttributeError` on instances.

Everything else in the spec was re-checked at `bf1c0e0`: the call graph (one caller, `gui.py:558`; Ctrl+wheel only, no keyboard shortcut; Apply does not sync; Dual View does not use the font size), the probe at `settings/dialogs.py:751-773`, cases 1-6, the slot declared on `DotExpressSettingsDialog` itself (`:648`), the lazy panels (`_get_category_panel`, `:214-220`), the dirty handler (`:618-619`, bound at `:596-597`), `load_snapshot` (`:601-606`), the existing tests (`:391-398`, `:493-525`, `:547-770`; `test_dialog_base` `MixinShapeTest`, `SingletonDialogMixinTest`, `DialogBaseImportTest`; `test_gui_document_flows` `test_open_settings_uses_singleton_dialog`), the baseline counts and AC6's other greps.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `bf1c0e0` (`$SP/p24plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 3 the 20 shuffle seeds, the pair orders, the msgid scan and every acceptance criterion passed. The patches in this plan are `git diff`s of the dry clone's commits (Tasks 2 and 3 split into the test step and the implementation step). Then this file's blocks were run in order on fresh clones (`$SP/p24plan/replay1` to `replay3`, each with a stand-in plan commit and a local `main` at `6dd65e3`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 3 commits applied, every expected block matched byte for byte on the final replay, and the resulting `client/` tree is identical to the dry clone's. Final sha256: `client/gui.py` `23d201e665dac3c383041df0e5641a938a4f53730d390cd759baef4b7b556b42`, `client/settings/dialogs.py` `4f1364b328108ea370a46f9a723f23cc1f0a929e322c0edba60222a7e67a2e46`, `client/ui/dialog_base.py` `245d4ad634fb30b2d31cbb81d4693857ef41450f2dc147e51700478f133701f1`, `client/tests/test_settings_dialogs.py` `7b28b29081dde86ba65d47032940951c3395f9ec67673736134d90fe04a05045`, `client/tests/test_gui_document_flows.py` `42ef4d8d6d3a27596f81ad26219ff5690365c4ceaf1c5ed1a1ca572a0a2dc7ac`, `client/tests/test_dialog_base.py` `e0aa040d537a7c1d7b7fd566e8b55e2506a3057e39ae54ac082a49d1a90d032e`; both fixtures unchanged. Windows-only behavior (real wx, NVDA) was not run; see the end of Task 4.

## Review Focus

Inputs and conditions the spec implies but does not list as tests, most likely to bite first. Each one has a test in the task that owns the code (Task 1, so it guards Tasks 2 and 3 as well).

1. **A platform whose `SpinCtrl.SetValue` emits `EVT_TEXT`** (the reason the probe resets `font_size_dirty` after `SetValue`): the sync must not count its own write as a user edit, so the next wheel step still follows. `FontSizeSyncCharacterizationTest.test_a_spin_that_reports_its_own_change_still_follows_the_next_step` (two syncs, 13 then 14); mutants `probe-keeps-dirty-flag-after-set` and `panel-keeps-dirty-flag-after-set`.
2. **The wheel must not steal focus.** A user scrolling with Ctrl in the editor expects the focus to stay there; an implementation that reused `_raise_existing()` (the obvious neighbour in the mixin) would iconize/raise/focus the dialog. `ViewFontSizeSyncCharacterizationTest.test_ctrl_wheel_saves_then_syncs_only_the_font_size_into_the_open_dialog` asserts no `Iconize`/`Raise`/`SetFocus`/`Show`; mutants `probe-raises-the-dialog`, `gui-raises-the-dialog`, `open-instance-raises-the-dialog`.
3. **Apply or OK without ever opening the View category** after a wheel change commits the wheel size, not the size the dialog opened with (spec case 2, not in its test list). `test_apply_without_visiting_the_view_panel_commits_the_synced_size`.
4. **The Text Processing dialog is open while wheeling.** It has its own slot; it must be neither touched nor mistaken for the settings dialog. `test_an_open_text_processing_dialog_is_left_alone`.
5. **Wheel, Cancel, wheel again.** The first step syncs, Cancel clears the slot, the second step changes and saves only the editors; the closed dialog keeps the first value and is destroyed once. `test_a_cancelled_dialog_is_no_longer_synced` (extends the spec's "closed with `on_cancel()` first").

## File Map

- Task 1: modify `client/tests/test_settings_dialogs.py` (`build_panel(owner=...)`, helper `sync_open_dialog_font_size`, class `FontSizeSyncCharacterizationTest`), `client/tests/test_gui_document_flows.py` (class `ViewFontSizeSyncCharacterizationTest`). Additions only, apart from `build_panel`.
- Task 2: modify `client/tests/test_dialog_base.py`, `client/tests/test_settings_dialogs.py` (tests first), then `client/ui/dialog_base.py` (`open_instance`), `client/settings/dialogs.py` (`ViewSettingsPanel.sync_font_size`).
- Task 3: modify `client/tests/test_settings_dialogs.py` (helper body, two renamed tests, the guard), then `client/settings/dialogs.py` (`sync_font_size`, `_view_panel`, probe removed), `client/gui.py` (`_set_view_font_size`).

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 1023 |
| 1 characterization | 14 | 1037 |
| 2 hooks | 5 | 1042 |
| 3 switch | 1 | 1043 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `font_size_mutants.py <client_dir> <scratch_dir> (old|new) [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`) to `<scratch_dir>/client`, then for each mutant of the set edits one file of the copy (`gui.py`, `settings/dialogs.py` or `ui/dialog_base.py`), runs the tests and restores the file. The repo is never changed. Set `old` (15 mutants, run in Task 1) matches the probe and runs only the two Part A classes; set `new` (13 mutants, run in Task 3) matches the new code and runs the three touched modules.
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
docs: plan font size sync
refactor/p2-4-font-size-sync
```

- [ ] **Step 2: Create the mutant runner.**

```bash
mkdir -p $T/tools
cat > $T/tools/font_size_mutants.py <<'EOF'
"""Run the P2-4 font size sync tests against deliberately broken code (throwaway).

Usage: python font_size_mutants.py <client_dir> <scratch_dir> (old|new) [mutant ...]
Copies <client_dir> (without .venv, __pycache__, log) to <scratch_dir>/client
(fresh each run), then for each mutant of the set edits one file in the copy,
runs the set's tests there and restores the file. <client_dir> is never changed.
Prints "<mutant>: failures=F errors=E" per mutant (all of the set by default).
Set "old" matches the code before Task 3 (the classmethod probe) and runs only
the part A classes; set "new" matches the code after Task 3 and runs the three
touched test modules.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

TESTS = {
    "old": [
        "tests.test_settings_dialogs.FontSizeSyncCharacterizationTest",
        "tests.test_gui_document_flows.ViewFontSizeSyncCharacterizationTest",
    ],
    "new": [
        "tests.test_settings_dialogs",
        "tests.test_gui_document_flows",
        "tests.test_dialog_base",
    ],
}

GUI_SAVE_THEN_SYNC = (
    "\t\tsave_view_settings(self.view_settings)\n"
    "\t\tDotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)\n"
)
GUI_NORMALIZE = (
    "\t\tself.view_settings = normalize_view_settings(\n"
    "\t\t\treplace(self.view_settings, font_size=font_size)\n"
    "\t\t)\n"
)

# set -> name -> (file, old, new); old must occur exactly once in the file.
MUTANTS = {
    "old": {
        "gui-no-sync": (
            "gui.py",
            "\t\tDotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)\n",
            "",
        ),
        "gui-sync-before-save": (
            "gui.py",
            GUI_SAVE_THEN_SYNC,
            "\t\tDotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)\n"
            "\t\tsave_view_settings(self.view_settings)\n",
        ),
        "gui-return-when-unchanged": (
            "gui.py",
            GUI_NORMALIZE,
            "\t\tprevious = self.view_settings\n" + GUI_NORMALIZE + "\t\tif self.view_settings == previous:\n\t\t\treturn\n",
        ),
        "gui-wheel-not-skipped": (
            "gui.py",
            "\t\t\tevent.Skip()\n\t\t\treturn\n\t\tself._set_view_font_size(",
            "\t\t\treturn\n\t\tself._set_view_font_size(",
        ),
        "probe-raises-the-dialog": (
            "settings/dialogs.py",
            "        instance = cls._instance\n",
            "        instance = cls._raise_existing()\n",
        ),
        "probe-ignores-pending-edit": (
            "settings/dialogs.py",
            'if view_panel is not None and getattr(view_panel, "font_size_dirty", False):',
            "if False:",
        ),
        "probe-keeps-dirty-flag-after-set": (
            "settings/dialogs.py",
            "            view_panel.font_size_dirty = False\n",
            "",
        ),
        "probe-not-normalized": (
            "settings/dialogs.py",
            "        normalized_view = normalize_view_settings(\n",
            "        normalized_view = (\n",
        ),
        "probe-overwrites-braille-font": (
            "settings/dialogs.py",
            "                instance.snapshot.view.braille_font,\n",
            '                "default",\n',
        ),
        "probe-writes-snapshot-despite-edit": (
            "settings/dialogs.py",
            "        view_panel = None\n",
            "        instance.snapshot = instance.snapshot.with_view(normalized_view)\n        view_panel = None\n",
        ),
        "probe-exact-panel-type": (
            "settings/dialogs.py",
            "            if isinstance(panel, ViewSettingsPanel):\n",
            "            if type(panel) is ViewSettingsPanel:\n",
        ),
        "probe-fixed-panel-index": (
            "settings/dialogs.py",
            "        for panel in instance.panel_instances.values():\n",
            "        for panel in [instance.panel_instances.get(2)]:\n",
        ),
        "probe-spin-not-set": (
            "settings/dialogs.py",
            "            view_panel.font_size_spin.SetValue(normalized_view.font_size)\n",
            "",
        ),
        "probe-snapshot-not-written": (
            "settings/dialogs.py",
            "        instance.snapshot = instance.snapshot.with_view(normalized_view)\n",
            "",
        ),
        "destroy-keeps-the-slot": (
            "ui/dialog_base.py",
            "            owner._instance = None\n",
            "            pass\n",
        ),
    },
    "new": {
        "open-instance-inherits-parent-slot": (
            "ui/dialog_base.py",
            '        return cls.__dict__.get("_instance")\n',
            '        return getattr(cls, "_instance", None)\n',
        ),
        "open-instance-raises-the-dialog": (
            "ui/dialog_base.py",
            '        return cls.__dict__.get("_instance")\n',
            "        return cls._raise_existing()\n",
        ),
        "panel-ignores-pending-edit": (
            "settings/dialogs.py",
            "        if self.font_size_dirty:\n            return False\n",
            "",
        ),
        "panel-keeps-dirty-flag-after-set": (
            "settings/dialogs.py",
            "        self.font_size_spin.SetValue(font_size)\n        self.font_size_dirty = False\n",
            "        self.font_size_spin.SetValue(font_size)\n",
        ),
        "panel-reports-refusal-as-accepted": (
            "settings/dialogs.py",
            "        if self.font_size_dirty:\n            return False\n",
            "        if self.font_size_dirty:\n            return True\n",
        ),
        "dialog-writes-snapshot-despite-edit": (
            "settings/dialogs.py",
            "        if view_panel is not None and not view_panel.sync_font_size(view.font_size):\n            return\n",
            "        if view_panel is not None:\n            view_panel.sync_font_size(view.font_size)\n",
        ),
        "dialog-not-normalized": (
            "settings/dialogs.py",
            "        view = normalize_view_settings(\n",
            "        view = (\n",
        ),
        "dialog-overwrites-scheme": (
            "settings/dialogs.py",
            "            ViewSettings(font_size, self.snapshot.view.scheme, self.snapshot.view.braille_font)\n",
            '            ViewSettings(font_size, "dark", self.snapshot.view.braille_font)\n',
        ),
        "dialog-exact-panel-type": (
            "settings/dialogs.py",
            "            if isinstance(panel, ViewSettingsPanel):\n",
            "            if type(panel) is ViewSettingsPanel:\n",
        ),
        "dialog-snapshot-not-written": (
            "settings/dialogs.py",
            "        self.snapshot = self.snapshot.with_view(view)\n",
            "",
        ),
        "gui-no-sync": (
            "gui.py",
            "\t\t\tsettings_dialog.sync_font_size(self.view_settings.font_size)\n",
            "\t\t\tpass\n",
        ),
        "gui-raises-the-dialog": (
            "gui.py",
            "\t\tsettings_dialog = DotExpressSettingsDialog.open_instance()\n",
            "\t\tsettings_dialog = DotExpressSettingsDialog._raise_existing()\n",
        ),
        "gui-sync-before-save": (
            "gui.py",
            "\t\tsave_view_settings(self.view_settings)\n"
            "\t\tsettings_dialog = DotExpressSettingsDialog.open_instance()\n"
            "\t\tif settings_dialog is not None:\n"
            "\t\t\tsettings_dialog.sync_font_size(self.view_settings.font_size)\n",
            "\t\tsettings_dialog = DotExpressSettingsDialog.open_instance()\n"
            "\t\tif settings_dialog is not None:\n"
            "\t\t\tsettings_dialog.sync_font_size(self.view_settings.font_size)\n"
            "\t\tsave_view_settings(self.view_settings)\n",
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
$PY -I -m py_compile $T/tools/font_size_mutants.py && echo compiled
```

Expected:

```text
compiled
```

- [ ] **Step 3: Record the baseline suite, the focused modules, the msgids and both fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs tests.test_dialog_base tests.test_gui_document_flows tests.test_view_settings 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for m in test_settings_dialogs test_dialog_base test_gui_document_flows; do echo "$m: $($PY -m unittest tests.$m 2>&1 | grep -E '^Ran' | sed -E 's/ in [0-9.]+s$//')"; done
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --save $T/base_msgids.json) | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
```

Expected (1023 tests with the P2-5 failure; `test_settings_dialogs` 67, `test_dialog_base` 23, `test_gui_document_flows` 145, `test_view_settings` 5):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1023 tests
FAILED (failures=1, skipped=9)
Ran 240 tests
OK (skipped=2)
test_settings_dialogs: Ran 67 tests
test_dialog_base: Ran 23 tests
test_gui_document_flows: Ran 145 tests
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
```

---

### Task 1: Characterize the font size sync (spec step 1, part A)

Nothing in production changes. Every new test passes on the current code by construction; Step 4 shows that the net fails for each of 15 deliberate breakages.

**Interfaces:**
- Consumes: today's `DotExpressSettingsDialog.sync_open_font_size(font_size)` (classmethod), `BrailleFrame.on_editor_mousewheel(event)`, `gui.save_view_settings`, `ViewSettingsPanel._on_font_size_changed(event)`, `ViewSettingsPanel.load_snapshot(snapshot)`, the existing test helpers `make_dialog_without_wx_constructor()`, `view_snapshot(font_size, scheme, braille_font)`, `build_panel(panel_name, ...)`, `RecordingSpin` (`.value`, `SetValue`), `RecordingChoice` (`.selection`, `SetSelection`) and, in the gui module, `make_snapshot(view=...)`.
- Produces: `build_panel(panel_name, *, ..., owner=None)` (a given owner replaces the default `SimpleNamespace`; the snapshot keyword arguments are then unused); `sync_open_dialog_font_size(dialog_class, font_size)` in `tests/test_settings_dialogs.py` (Task 3 rewrites its body only); classes `FontSizeSyncCharacterizationTest` and `ViewFontSizeSyncCharacterizationTest`, which are never edited afterwards.

- [ ] **Step 1: Add `owner=` to `build_panel`, the helper and the dialog-level characterization.** In `tests/test_settings_dialogs.py`, after the P2-3 section. The pending-edit test carries `# KNOWN QUIRK (P2-4 spec, 2)`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index fa39f59..f6db5d0 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -845,15 +845,20 @@ def build_panel(
     tables=None,
     view=ViewSettings(12, "light", "simbraille"),
     table_list=FAKE_TABLES,
+    owner=None,
 ):
-    """Build a real settings panel with recording choices and spins and a fake ``listTables``."""
+    """Build a real settings panel with recording choices and spins and a fake ``listTables``.
+
+    ``owner`` (for example a dialog) replaces the default owner; the snapshot arguments are then unused.
+    """
     module = sys.modules["settings.dialogs"]
-    snapshot = DotExpressSettingsSnapshot.create(
-        translation=translation,
-        translation_tables={} if tables is None else tables,
-        view=view,
-    )
-    owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"])
+    if owner is None:
+        snapshot = DotExpressSettingsSnapshot.create(
+            translation=translation,
+            translation_tables={} if tables is None else tables,
+            view=view,
+        )
+        owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"])
     with (
         patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin),
         patch.object(module, "listTables", Mock(return_value=list(table_list))),
@@ -1182,5 +1187,148 @@ class TableDisplayNameGuardTest(unittest.TestCase):
         self.assertEqual(from_english[:3], ["世界文一級", "中國通用盲文 (簡體中文字)", "中庫德文一級"])
 
 
+
+# --- P2-4 characterization: a font size changed in the main window (Ctrl+wheel)
+# reaching the open settings dialog. The View panel is the real panel, built with
+# the dialog as its owner. The dialog goes into its slot with patch.object only.
+
+
+def sync_open_dialog_font_size(dialog_class, font_size):
+    """Pass a font size to the open dialog of ``dialog_class`` the way the main window does."""
+    dialog_class.sync_open_font_size(font_size)
+
+
+class FontSizeSyncCharacterizationTest(unittest.TestCase):
+    def setUp(self) -> None:
+        from settings.dialogs import DotExpressSettingsDialog
+
+        self.dialog_class = DotExpressSettingsDialog
+        self.dialog = make_dialog_without_wx_constructor()
+        self.dialog.snapshot = view_snapshot(12, "light", "simbraille")
+
+    def open_dialog(self):
+        return patch.object(self.dialog_class, "_instance", self.dialog)
+
+    def sync(self, font_size) -> None:
+        sync_open_dialog_font_size(self.dialog_class, font_size)
+
+    def add_view_panel(self, index=2):
+        panel = build_panel("ViewSettingsPanel", owner=self.dialog)
+        self.dialog.panel_instances[index] = panel
+        return panel
+
+    def test_without_an_open_dialog_nothing_happens(self) -> None:
+        with patch.object(self.dialog_class, "_instance", None):
+            self.sync(20)
+
+        self.assertEqual(self.dialog.snapshot, view_snapshot(12, "light", "simbraille"))
+
+    def test_without_a_view_panel_only_the_snapshot_font_size_changes(self) -> None:
+        with self.open_dialog():
+            self.sync(20)
+
+        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))
+        self.assertEqual(self.dialog.panel_instances, {})
+        panel = build_panel("ViewSettingsPanel", owner=self.dialog)
+        self.assertEqual(
+            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
+            (20, 0, 1),
+        )
+
+    def test_sizes_are_clamped_to_the_spin_range(self) -> None:
+        for font_size, expected in ((99, 48), (49, 48), (48, 48), (8, 8), (7, 8), (3, 8)):
+            with self.subTest(font_size=font_size):
+                self.dialog.snapshot = view_snapshot(12, "light", "simbraille")
+                self.dialog.panel_instances = {}
+                with self.open_dialog():
+                    self.sync(font_size)
+                self.assertEqual(self.dialog.snapshot.view, ViewSettings(expected, "light", "simbraille"))
+
+                self.dialog.snapshot = view_snapshot(12, "light", "simbraille")
+                panel = self.add_view_panel()
+                with self.open_dialog():
+                    self.sync(font_size)
+                self.assertEqual((panel.font_size_spin.value, self.dialog.snapshot.view.font_size), (expected, expected))
+
+    def test_a_clean_view_panel_shows_the_size_and_keeps_the_other_drafts(self) -> None:
+        panel = self.add_view_panel()
+        panel.scheme_choice.SetSelection(1)  # a draft: Dark, not applied yet
+
+        with self.open_dialog():
+            self.sync(20)
+
+        self.assertEqual(panel.font_size_spin.value, 20)
+        self.assertFalse(panel.font_size_dirty)
+        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))
+        self.assertEqual((panel.scheme_choice.selection, panel.braille_font_choice.selection), (1, 1))
+        self.assertEqual(panel.on_save(self.dialog.snapshot).view, ViewSettings(20, "dark", "simbraille"))
+
+    def test_a_pending_edit_blocks_the_sync_until_the_snapshot_is_reloaded(self) -> None:
+        panel = self.add_view_panel()
+        panel.font_size_spin.SetValue(30)
+        panel._on_font_size_changed(None)  # bound to EVT_SPINCTRL and EVT_TEXT
+
+        with self.open_dialog():
+            self.sync(20)
+
+        # KNOWN QUIRK (P2-4 spec, 2): the pending edit wins, and the snapshot keeps 12 too.
+        self.assertEqual(panel.font_size_spin.value, 30)
+        self.assertTrue(panel.font_size_dirty)
+        self.assertEqual(self.dialog.snapshot, view_snapshot(12, "light", "simbraille"))
+
+        panel.load_snapshot(self.dialog.snapshot)  # what Apply does after the commit
+        self.assertFalse(panel.font_size_dirty)
+        with self.open_dialog():
+            self.sync(20)
+
+        self.assertEqual(panel.font_size_spin.value, 20)
+        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))
+
+    def test_a_view_panel_subclass_under_any_index_is_found(self) -> None:
+        from settings.dialogs import ViewSettingsPanel
+
+        class CustomViewPanel(ViewSettingsPanel):
+            pass
+
+        panel = object.__new__(CustomViewPanel)
+        panel.font_size_dirty = False
+        panel.font_size_spin = RecordingSpin(initial=12)
+        other = Mock()
+        self.dialog.panel_instances = {0: panel, 1: other}
+
+        with self.open_dialog():
+            self.sync(20)
+
+        self.assertEqual(panel.font_size_spin.value, 20)
+        self.assertEqual(self.dialog.snapshot.view.font_size, 20)
+        self.assertEqual(other.mock_calls, [])
+
+    def test_a_spin_that_reports_its_own_change_still_follows_the_next_step(self) -> None:
+        panel = self.add_view_panel()
+        spin = panel.font_size_spin
+
+        def set_value_and_report(value):
+            RecordingSpin.SetValue(spin, value)
+            panel._on_font_size_changed(None)  # a platform whose SetValue emits EVT_TEXT
+
+        spin.SetValue = set_value_and_report
+        with self.open_dialog():
+            self.sync(13)
+            self.sync(14)
+
+        self.assertEqual(spin.value, 14)
+        self.assertFalse(panel.font_size_dirty)
+        self.assertEqual(self.dialog.snapshot.view.font_size, 14)
+
+    def test_apply_without_visiting_the_view_panel_commits_the_synced_size(self) -> None:
+        self.dialog.commit = Mock(side_effect=lambda snapshot: snapshot)
+
+        with self.open_dialog():
+            self.sync(20)
+            self.assertTrue(self.dialog.on_apply())
+
+        self.dialog.commit.assert_called_once_with(view_snapshot(20, "light", "simbraille"))
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_settings_dialogs.py | 162 ++++++++++++++++++++++++++++++++--
 1 file changed, 155 insertions(+), 7 deletions(-)
```

- [ ] **Step 2: Add the frame-level characterization.** `ViewFontSizeSyncCharacterizationTest` at the end of `tests/test_gui_document_flows.py` (the only module with the gui stub scope; it uses `gui.DotExpressSettingsDialog` and `gui.TextProcessingDialog`, the classes loaded under that scope). The clamp test carries `# KNOWN QUIRK (P2-4 spec, 1)`.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 9e40d4b..62ee69d 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -3625,5 +3625,136 @@ class EditorViewSettingsCharacterizationTest(unittest.TestCase):
                 )
 
 
+
+class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
+    """P2-4 characterization: Ctrl+wheel in an editor and the open settings dialog's font size."""
+
+    FRAME_VIEW = ViewSettings(12, "dark", "default")
+    DIALOG_VIEW = ViewSettings(12, "light", "simbraille")
+
+    def make_frame(self, view=FRAME_VIEW) -> gui.BrailleFrame:
+        frame = object.__new__(gui.BrailleFrame)
+        frame.view_settings = view
+        frame._apply_editor_view_settings = Mock()
+        return frame
+
+    def make_dialog(self):
+        dialog = object.__new__(gui.DotExpressSettingsDialog)
+        dialog.snapshot = make_snapshot(view=self.DIALOG_VIEW)
+        dialog.panel_instances = {}
+        dialog.Destroy = Mock()
+        dialog.window_calls = Mock()
+        for name in ("Iconize", "Raise", "SetFocus", "Show"):
+            setattr(dialog, name, getattr(dialog.window_calls, name))
+        return dialog
+
+    @staticmethod
+    def wheel(rotation, control_down=True):
+        return SimpleNamespace(
+            GetWheelRotation=lambda: rotation,
+            ControlDown=lambda: control_down,
+            Skip=Mock(),
+        )
+
+    @staticmethod
+    def open_dialog(dialog):
+        return patch.object(gui.DotExpressSettingsDialog, "_instance", dialog)
+
+    def test_ctrl_wheel_saves_then_syncs_only_the_font_size_into_the_open_dialog(self) -> None:
+        frame = self.make_frame()
+        dialog = self.make_dialog()
+        dialog_size_when_saved = []
+        event = self.wheel(120)
+
+        with (
+            self.open_dialog(dialog),
+            patch.object(
+                gui,
+                "save_view_settings",
+                side_effect=lambda _view: dialog_size_when_saved.append(dialog.snapshot.view.font_size),
+            ) as save,
+        ):
+            frame.on_editor_mousewheel(event)
+
+        expected = ViewSettings(13, "dark", "default")
+        self.assertEqual(frame.view_settings, expected)
+        frame._apply_editor_view_settings.assert_called_once_with(expected)
+        save.assert_called_once_with(expected)
+        self.assertEqual(dialog_size_when_saved, [12])
+        self.assertEqual(dialog.snapshot, make_snapshot(view=ViewSettings(13, "light", "simbraille")))
+        self.assertEqual(dialog.window_calls.mock_calls, [])  # the editor keeps the focus
+        event.Skip.assert_not_called()
+
+    def test_a_clamped_step_still_saves_and_syncs_the_clamped_size(self) -> None:
+        for start, rotation in ((8, -120), (48, 120)):
+            with self.subTest(start=start, rotation=rotation):
+                frame = self.make_frame(ViewSettings(start, "dark", "default"))
+                dialog = self.make_dialog()
+                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
+                    frame.on_editor_mousewheel(self.wheel(rotation))
+
+                # KNOWN QUIRK (P2-4 spec, 1): the size did not change, but it is saved and synced again.
+                expected = ViewSettings(start, "dark", "default")
+                self.assertEqual(frame.view_settings, expected)
+                frame._apply_editor_view_settings.assert_called_once_with(expected)
+                save.assert_called_once_with(expected)
+                self.assertEqual(dialog.snapshot.view, ViewSettings(start, "light", "simbraille"))
+
+    def test_a_wheel_without_a_step_is_skipped_and_changes_nothing(self) -> None:
+        for rotation, control_down in ((120, False), (-120, False), (0, True)):
+            with self.subTest(rotation=rotation, control_down=control_down):
+                frame = self.make_frame()
+                dialog = self.make_dialog()
+                event = self.wheel(rotation, control_down)
+                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
+                    frame.on_editor_mousewheel(event)
+
+                event.Skip.assert_called_once_with()
+                self.assertEqual(frame.view_settings, self.FRAME_VIEW)
+                frame._apply_editor_view_settings.assert_not_called()
+                save.assert_not_called()
+                self.assertEqual(dialog.snapshot.view, self.DIALOG_VIEW)
+
+    def test_without_an_open_dialog_the_editors_and_the_config_still_change(self) -> None:
+        frame = self.make_frame()
+        with self.open_dialog(None), patch.object(gui, "save_view_settings") as save:
+            frame.on_editor_mousewheel(self.wheel(-120))
+
+        expected = ViewSettings(11, "dark", "default")
+        self.assertEqual(frame.view_settings, expected)
+        frame._apply_editor_view_settings.assert_called_once_with(expected)
+        save.assert_called_once_with(expected)
+
+    def test_a_cancelled_dialog_is_no_longer_synced(self) -> None:
+        frame = self.make_frame()
+        dialog = self.make_dialog()
+        with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
+            frame.on_editor_mousewheel(self.wheel(120))
+            dialog.on_cancel()
+            self.assertIsNone(gui.DotExpressSettingsDialog._instance)
+            frame.on_editor_mousewheel(self.wheel(120))
+
+        dialog.Destroy.assert_called_once_with()
+        self.assertEqual(frame.view_settings, ViewSettings(14, "dark", "default"))
+        self.assertEqual(
+            save.call_args_list,
+            [call(ViewSettings(13, "dark", "default")), call(ViewSettings(14, "dark", "default"))],
+        )
+        self.assertEqual(dialog.snapshot.view, ViewSettings(13, "light", "simbraille"))
+
+    def test_an_open_text_processing_dialog_is_left_alone(self) -> None:
+        frame = self.make_frame()
+        text_dialog = Mock()
+        with (
+            patch.object(gui.TextProcessingDialog, "_instance", text_dialog),
+            self.open_dialog(None),
+            patch.object(gui, "save_view_settings") as save,
+        ):
+            frame.on_editor_mousewheel(self.wheel(120))
+
+        save.assert_called_once_with(ViewSettings(13, "dark", "default"))
+        self.assertEqual(text_dialog.mock_calls, [])
+
+
 if __name__ == "__main__":
     unittest.main()
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_gui_document_flows.py | 131 ++++++++++++++++++++++++++
 client/tests/test_settings_dialogs.py   | 162 ++++++++++++++++++++++++++++++--
 2 files changed, 286 insertions(+), 7 deletions(-)
```

- [ ] **Step 3: Run part A on the current code, then the two modules in full.**

```bash
$PY -m unittest tests.test_settings_dialogs.FontSizeSyncCharacterizationTest tests.test_gui_document_flows.ViewFontSizeSyncCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (14 new tests, all passing; the two modules 75 + 151):

```text
Ran 14 tests
OK
Ran 226 tests
OK (skipped=2)
```

- [ ] **Step 4: Mutation check: every mutant of the probe must fail part A.** The runner works on a copy under `$T/mut`; the repo is not changed.

```bash
$PY -I $T/tools/font_size_mutants.py $REPO/client $T/mut old
git -C $REPO status --short -- client/gui.py client/settings client/ui
```

Expected (every line FAILED; no production file changed in the repo):

```text
gui-no-sync: failures=4 errors=0 (FAILED (failures=4))
gui-sync-before-save: failures=1 errors=0 (FAILED (failures=1))
gui-return-when-unchanged: failures=2 errors=0 (FAILED (failures=2))
gui-wheel-not-skipped: failures=3 errors=0 (FAILED (failures=3))
probe-raises-the-dialog: failures=1 errors=0 (FAILED (failures=1))
probe-ignores-pending-edit: failures=1 errors=0 (FAILED (failures=1))
probe-keeps-dirty-flag-after-set: failures=1 errors=0 (FAILED (failures=1))
probe-not-normalized: failures=4 errors=0 (FAILED (failures=4))
probe-overwrites-braille-font: failures=14 errors=0 (FAILED (failures=14))
probe-writes-snapshot-despite-edit: failures=1 errors=0 (FAILED (failures=1))
probe-exact-panel-type: failures=1 errors=0 (FAILED (failures=1))
probe-fixed-panel-index: failures=1 errors=0 (FAILED (failures=1))
probe-spin-not-set: failures=10 errors=0 (FAILED (failures=10))
probe-snapshot-not-written: failures=16 errors=0 (FAILED (failures=16))
destroy-keeps-the-slot: failures=1 errors=0 (FAILED (failures=1))
```

- [ ] **Step 5: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1023 + 14):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1037 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/tests/test_settings_dialogs.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize font size sync

Pin how a Ctrl+wheel font size change reaches the open settings
dialog before the classmethod probe is replaced (P2-4 part A): the
frame saves first and syncs only the size; no dialog, a cancelled
dialog and the Text Processing dialog are left alone; the dialog
clamps, keeps a pending View panel edit (snapshot too) until Apply
reloads it, finds a View panel subclass under any index and keeps
the other drafts. build_panel gains an owner= keyword.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize font size sync
```

---

### Task 2: Add the open-dialog and panel hooks (spec step 2, part B)

**Interfaces:**
- Consumes: `SingletonDialogMixin` (`_show_new`, `_destroy`, the class's own `_instance` read through `cls.__dict__`), `ViewSettingsPanel.font_size_dirty` / `font_size_spin` (set in `make_settings`), and from `tests/test_dialog_base.py` `DIALOG_BASES` and `singleton_class(base)`.
- Produces: `SingletonDialogMixin.open_instance(cls)` (classmethod) -> the dialog in `cls.__dict__["_instance"]` or `None`, with no call on the dialog; `ViewSettingsPanel.sync_font_size(self, font_size: int) -> bool` -> `False` and no change while `font_size_dirty` is set, else `SetValue(font_size)` on the spin, `font_size_dirty = False`, `True`. The caller passes an already clamped size. Nothing in production calls them until Task 3.

- [ ] **Step 1: Write the failing tests.** Three `open_instance` tests in `SingletonDialogMixinTest` (empty slot and filled slot with `mock_calls == []`, a subclass without its own slot gets `None`, `None` again after `_destroy`) and two `sync_font_size` tests in `ViewSettingsPanelTest` (clean: `True`, spin 20, flag clear; dirty: `False`, spin stays 30, flag set).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_dialog_base.py b/client/tests/test_dialog_base.py
index 054cb71..0371be5 100644
--- a/client/tests/test_dialog_base.py
+++ b/client/tests/test_dialog_base.py
@@ -338,6 +338,42 @@ class SingletonDialogMixinTest(unittest.TestCase):
                 other.Destroy.assert_called_once_with()
                 parent_dialog.Destroy.assert_not_called()
 
+    def test_open_instance_returns_the_slot_without_touching_the_dialog(self) -> None:
+        for base in DIALOG_BASES:
+            with self.subTest(base=base.__name__):
+                dialog_class = singleton_class(base)
+                self.assertIsNone(dialog_class.open_instance())
+                existing = Mock()
+                dialog_class._instance = existing
+                self.assertIs(dialog_class.open_instance(), existing)
+                self.assertIs(dialog_class._instance, existing)
+                self.assertEqual(existing.mock_calls, [])
+
+    def test_open_instance_of_a_subclass_without_its_own_slot_is_none(self) -> None:
+        for base in DIALOG_BASES:
+            with self.subTest(base=base.__name__):
+                parent_class = singleton_class(base)
+                existing = Mock()
+                parent_class._instance = existing
+                child_class = type("Child", (parent_class,), {})
+
+                self.assertIsNone(child_class.open_instance())
+                self.assertIs(parent_class.open_instance(), existing)
+                self.assertEqual(existing.mock_calls, [])
+
+    def test_open_instance_is_none_after_destroy(self) -> None:
+        for base in DIALOG_BASES:
+            with self.subTest(base=base.__name__):
+                dialog_class = singleton_class(base)
+                dialog = dialog_class()
+                dialog.Show = Mock()
+                dialog.Destroy = Mock()
+                dialog_class._show_new(dialog)
+                self.assertIs(dialog_class.open_instance(), dialog)
+
+                dialog._destroy()
+                self.assertIsNone(dialog_class.open_instance())
+
 
 class DialogBaseImportTest(unittest.TestCase):
     def test_module_imports_only_the_standard_library_i18n_and_name_validation(self) -> None:
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index f6db5d0..3becb72 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -397,6 +397,22 @@ class ViewSettingsPanelTest(unittest.TestCase):
         panel._on_font_size_changed(None)
         self.assertTrue(panel.font_size_dirty)
 
+    def test_sync_font_size_sets_a_clean_spin(self) -> None:
+        panel = build_panel("ViewSettingsPanel")
+
+        self.assertIs(panel.sync_font_size(20), True)
+        self.assertEqual(panel.font_size_spin.value, 20)
+        self.assertFalse(panel.font_size_dirty)
+
+    def test_sync_font_size_leaves_a_pending_edit_alone(self) -> None:
+        panel = build_panel("ViewSettingsPanel")
+        panel.font_size_spin.SetValue(30)
+        panel._on_font_size_changed(None)
+
+        self.assertIs(panel.sync_font_size(20), False)
+        self.assertEqual(panel.font_size_spin.value, 30)
+        self.assertTrue(panel.font_size_dirty)
+
 
 class DotExpressSettingsDialogFlowTest(unittest.TestCase):
     def test_apply_validates_all_panels_before_commit(self) -> None:
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_dialog_base.py      | 36 +++++++++++++++++++++++++++++++++++
 client/tests/test_settings_dialogs.py | 16 ++++++++++++++++
 2 files changed, 52 insertions(+)
```

- [ ] **Step 2: Run them red.**

```bash
$PY -m unittest tests.test_dialog_base tests.test_settings_dialogs.ViewSettingsPanelTest 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
```

Expected (6 errors: the mixin has no `open_instance`, one per stub base; 2 failures: the stub panel masks the missing method and returns `None`):

```text
ERROR: test_open_instance_is_none_after_destroy (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_is_none_after_destroy) (base='PlainDialog')
AttributeError: type object 'FakeSingleton' has no attribute 'open_instance'
ERROR: test_open_instance_is_none_after_destroy (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_is_none_after_destroy) (base='MaskingDialog')
AttributeError: type object 'FakeSingleton' has no attribute 'open_instance'
ERROR: test_open_instance_of_a_subclass_without_its_own_slot_is_none (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_of_a_subclass_without_its_own_slot_is_none) (base='PlainDialog')
AttributeError: type object 'Child' has no attribute 'open_instance'
ERROR: test_open_instance_of_a_subclass_without_its_own_slot_is_none (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_of_a_subclass_without_its_own_slot_is_none) (base='MaskingDialog')
AttributeError: type object 'Child' has no attribute 'open_instance'
ERROR: test_open_instance_returns_the_slot_without_touching_the_dialog (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_returns_the_slot_without_touching_the_dialog) (base='PlainDialog')
AttributeError: type object 'FakeSingleton' has no attribute 'open_instance'
ERROR: test_open_instance_returns_the_slot_without_touching_the_dialog (tests.test_dialog_base.SingletonDialogMixinTest.test_open_instance_returns_the_slot_without_touching_the_dialog) (base='MaskingDialog')
AttributeError: type object 'FakeSingleton' has no attribute 'open_instance'
FAIL: test_sync_font_size_leaves_a_pending_edit_alone (tests.test_settings_dialogs.ViewSettingsPanelTest.test_sync_font_size_leaves_a_pending_edit_alone)
AssertionError: None is not False
FAIL: test_sync_font_size_sets_a_clean_spin (tests.test_settings_dialogs.ViewSettingsPanelTest.test_sync_font_size_sets_a_clean_spin)
AssertionError: None is not True
Ran 29 tests
FAILED (failures=2, errors=6)
```

- [ ] **Step 3: Add `open_instance` after `_show_new` and `ViewSettingsPanel.sync_font_size` after `_on_font_size_changed`.** The docstring and shape of the mixin and the imports of both modules stay as they are.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/settings/dialogs.py b/client/settings/dialogs.py
index 61105a7..4712e41 100644
--- a/client/settings/dialogs.py
+++ b/client/settings/dialogs.py
@@ -618,6 +618,17 @@ class ViewSettingsPanel(SettingsPanel):
     def _on_font_size_changed(self, _event) -> None:
         self.font_size_dirty = True
 
+    def sync_font_size(self, font_size: int) -> bool:
+        """Show a font size changed in the main window, unless the user has edited it here.
+
+        Returns ``False``, changing nothing, while that edit is pending (until Apply or OK).
+        """
+        if self.font_size_dirty:
+            return False
+        self.font_size_spin.SetValue(font_size)
+        self.font_size_dirty = False
+        return True
+
     def _selected_scheme(self) -> str:
         return option_value_at(VIEW_SCHEME_OPTIONS, self.scheme_choice.GetSelection())
 
diff --git a/client/ui/dialog_base.py b/client/ui/dialog_base.py
index ccecad4..f283d8f 100644
--- a/client/ui/dialog_base.py
+++ b/client/ui/dialog_base.py
@@ -121,6 +121,11 @@ class SingletonDialogMixin:
         instance.Show()
         return instance
 
+    @classmethod
+    def open_instance(cls):
+        """The open dialog of this class, or ``None``. Nothing is raised, focused or checked."""
+        return cls.__dict__.get("_instance")
+
     def _destroy(self) -> None:
         owner = type(self)
         if owner.__dict__.get("_instance") is self:
EOF
git -C $REPO diff --stat -- client/ui client/settings
```

Expected:

```text
 client/settings/dialogs.py | 11 +++++++++++
 client/ui/dialog_base.py   |  5 +++++
 2 files changed, 16 insertions(+)
```

- [ ] **Step 4: Run green: the new tests, the mixin shape and import guards, the touched modules and the full suite.**

```bash
$PY -m unittest tests.test_dialog_base tests.test_settings_dialogs.ViewSettingsPanelTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_dialog_base.MixinShapeTest tests.test_dialog_base.DialogBaseImportTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs tests.test_dialog_base tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (29; the two guards unchanged and green; 77 + 26 + 151 = 254; 1037 + 5):

```text
Ran 29 tests
OK
Ran 2 tests
OK
Ran 254 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1042 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/ui/dialog_base.py client/settings/dialogs.py client/tests/test_dialog_base.py client/tests/test_settings_dialogs.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add open dialog and panel font size hooks

SingletonDialogMixin.open_instance() returns the dialog in the class's
own slot without raising or focusing it, and
ViewSettingsPanel.sync_font_size() owns the pending-edit rule and the
font size spin (P2-4 step 2). Nothing calls them yet except tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add open dialog and panel font size hooks
```

---

### Task 3: Sync through the open settings dialog (spec step 3, part C)

**Interfaces:**
- Consumes: `SingletonDialogMixin.open_instance()` and `ViewSettingsPanel.sync_font_size(font_size) -> bool` from Task 2; `normalize_view_settings`, `ViewSettings` (already imported in `settings/dialogs.py`); `DotExpressSettingsDialog.snapshot`, `.panel_instances`.
- Produces: `DotExpressSettingsDialog.sync_font_size(self, font_size: int) -> None` (normalizes `ViewSettings(font_size, snapshot scheme, snapshot braille font)`, asks the View panel if there is one, returns early when it refuses, else replaces the snapshot's view) and `DotExpressSettingsDialog._view_panel(self) -> ViewSettingsPanel | None` (first `isinstance` match over `panel_instances.values()`). `gui._set_view_font_size` ends with `settings_dialog = DotExpressSettingsDialog.open_instance()` and, when not `None`, `settings_dialog.sync_font_size(self.view_settings.font_size)`. `sync_open_font_size` no longer exists.

- [ ] **Step 1: Switch the helper, move the two older sync tests onto it, add the guard.** The helper body becomes `open_instance()` + `sync_font_size()`; the older tests are renamed and use `patch.object` (refinement 5); `test_font_size_sync_is_one_instance_method` is the allow-list guard (correction 2). `FunctionType` joins the `types` import. Part A's classes are not edited.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_settings_dialogs.py b/client/tests/test_settings_dialogs.py
index 3becb72..62d0d2a 100644
--- a/client/tests/test_settings_dialogs.py
+++ b/client/tests/test_settings_dialogs.py
@@ -4,7 +4,7 @@ import ast
 import sys
 import unittest
 from pathlib import Path
-from types import SimpleNamespace
+from types import FunctionType, SimpleNamespace
 from unittest.mock import Mock, call, patch
 
 from tests import wx_stub
@@ -506,22 +506,18 @@ class DotExpressSettingsDialogFlowTest(unittest.TestCase):
                 commit=Mock(),
             )
 
-    def test_sync_open_font_size_updates_snapshot_before_view_panel_exists(self) -> None:
+    def test_sync_font_size_updates_snapshot_before_view_panel_exists(self) -> None:
         from settings.dialogs import DotExpressSettingsDialog
 
         dialog = make_dialog_without_wx_constructor()
         dialog.snapshot = make_snapshot(font_size=12)
         dialog.panel_instances = {}
-        original_instance = DotExpressSettingsDialog._instance
-        DotExpressSettingsDialog._instance = dialog
-        try:
-            DotExpressSettingsDialog.sync_open_font_size(20)
-        finally:
-            DotExpressSettingsDialog._instance = original_instance
+        with patch.object(DotExpressSettingsDialog, "_instance", dialog):
+            sync_open_dialog_font_size(DotExpressSettingsDialog, 20)
 
         self.assertEqual(dialog.snapshot.view.font_size, 20)
 
-    def test_sync_open_font_size_keeps_dirty_view_panel_draft(self) -> None:
+    def test_sync_font_size_keeps_dirty_view_panel_draft(self) -> None:
         from settings.dialogs import DotExpressSettingsDialog, ViewSettingsPanel
 
         dialog = make_dialog_without_wx_constructor()
@@ -530,16 +526,19 @@ class DotExpressSettingsDialogFlowTest(unittest.TestCase):
         view_panel.font_size_dirty = True
         view_panel.font_size_spin = Mock()
         dialog.panel_instances = {2: view_panel}
-        original_instance = DotExpressSettingsDialog._instance
-        DotExpressSettingsDialog._instance = dialog
-        try:
-            DotExpressSettingsDialog.sync_open_font_size(20)
-        finally:
-            DotExpressSettingsDialog._instance = original_instance
+        with patch.object(DotExpressSettingsDialog, "_instance", dialog):
+            sync_open_dialog_font_size(DotExpressSettingsDialog, 20)
 
         self.assertEqual(dialog.snapshot.view.font_size, 12)
         view_panel.font_size_spin.SetValue.assert_not_called()
 
+    def test_font_size_sync_is_one_instance_method(self) -> None:
+        from settings.dialogs import DotExpressSettingsDialog
+
+        members = vars(DotExpressSettingsDialog)
+        self.assertEqual([name for name in members if "font_size" in name], ["sync_font_size"])
+        self.assertIs(type(members["sync_font_size"]), FunctionType)
+
     def test_title_format_uses_localizable_template(self) -> None:
         from settings.dialogs import DotExpressSettingsDialog
 
@@ -1211,7 +1210,9 @@ class TableDisplayNameGuardTest(unittest.TestCase):
 
 def sync_open_dialog_font_size(dialog_class, font_size):
     """Pass a font size to the open dialog of ``dialog_class`` the way the main window does."""
-    dialog_class.sync_open_font_size(font_size)
+    dialog = dialog_class.open_instance()
+    if dialog is not None:
+        dialog.sync_font_size(font_size)
 
 
 class FontSizeSyncCharacterizationTest(unittest.TestCase):
EOF
git -C $REPO diff --stat
```

Expected:

```text
 client/tests/test_settings_dialogs.py | 33 +++++++++++++++++----------------
 1 file changed, 17 insertions(+), 16 deletions(-)
```

- [ ] **Step 2: Run red.** The helper now calls an instance method the dialog does not have yet (the stub masks it, so nothing changes), and the guard still sees the classmethod.

```bash
$PY -m unittest tests.test_settings_dialogs 2>&1 | grep -E '^(FAIL|ERROR):|Error:|^Ran|^OK|^FAILED' | sed -E "s/ in [0-9.]+s$//; s#$REPO/##"
$PY -m unittest tests.test_gui_document_flows.ViewFontSizeSyncCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (9 failing tests, 14 `FAIL` lines: the guard, the renamed snapshot test, and 7 of the 8 part A dialog tests, the clamp test once per failing subtest; the renamed dirty-panel test and part A's no-dialog test still pass because nothing changes in either; the frame-level part A still passes against the old gui call):

```text
FAIL: test_font_size_sync_is_one_instance_method (tests.test_settings_dialogs.DotExpressSettingsDialogFlowTest.test_font_size_sync_is_one_instance_method)
AssertionError: Lists differ: ['sync_open_font_size'] != ['sync_font_size']
FAIL: test_sync_font_size_updates_snapshot_before_view_panel_exists (tests.test_settings_dialogs.DotExpressSettingsDialogFlowTest.test_sync_font_size_updates_snapshot_before_view_panel_exists)
AssertionError: 12 != 20
FAIL: test_a_clean_view_panel_shows_the_size_and_keeps_the_other_drafts (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_a_clean_view_panel_shows_the_size_and_keeps_the_other_drafts)
AssertionError: 12 != 20
FAIL: test_a_pending_edit_blocks_the_sync_until_the_snapshot_is_reloaded (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_a_pending_edit_blocks_the_sync_until_the_snapshot_is_reloaded)
AssertionError: 12 != 20
FAIL: test_a_spin_that_reports_its_own_change_still_follows_the_next_step (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_a_spin_that_reports_its_own_change_still_follows_the_next_step)
AssertionError: 12 != 14
FAIL: test_a_view_panel_subclass_under_any_index_is_found (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_a_view_panel_subclass_under_any_index_is_found)
AssertionError: 12 != 20
FAIL: test_apply_without_visiting_the_view_panel_commits_the_synced_size (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_apply_without_visiting_the_view_panel_commits_the_synced_size)
AssertionError: expected call not found.
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=99)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=48, scheme='light', braille_font='simbraille')
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=49)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=48, scheme='light', braille_font='simbraille')
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=48)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=48, scheme='light', braille_font='simbraille')
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=8)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=8, scheme='light', braille_font='simbraille')
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=7)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=8, scheme='light', braille_font='simbraille')
FAIL: test_sizes_are_clamped_to_the_spin_range (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_sizes_are_clamped_to_the_spin_range) (font_size=3)
AssertionError: ViewSettings(font_size=12, scheme='light', braille_font='simbraille') != ViewSettings(font_size=8, scheme='light', braille_font='simbraille')
FAIL: test_without_a_view_panel_only_the_snapshot_font_size_changes (tests.test_settings_dialogs.FontSizeSyncCharacterizationTest.test_without_a_view_panel_only_the_snapshot_font_size_changes)
AssertionError: DotEx[154 chars]tings(font_size=12, scheme='light', braille_font='simbraille')) != DotEx[154 chars]tings(font_size=20, scheme='light', braille_font='simbraille'))
Ran 78 tests
FAILED (failures=14)
Ran 6 tests
OK
```

- [ ] **Step 3: Replace the probe and the gui call.** In `settings/dialogs.py` the classmethod `sync_open_font_size` becomes the instance method `sync_font_size` plus `_view_panel` (4 spaces); in `gui.py` the last line of `_set_view_font_size` becomes the three-line `open_instance()` call (tabs). The first three statements of `_set_view_font_size` and their order are unchanged; the import line `gui.py:91` is unchanged.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/gui.py b/client/gui.py
index 91d3f79..cb3bfe7 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -555,7 +555,9 @@ class BrailleFrame(wx.Frame):
 		)
 		self._apply_editor_view_settings(self.view_settings)
 		save_view_settings(self.view_settings)
-		DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)
+		settings_dialog = DotExpressSettingsDialog.open_instance()
+		if settings_dialog is not None:
+			settings_dialog.sync_font_size(self.view_settings.font_size)
 
 	def _open_document_by_name(self, name: str | None) -> None:
 		document = self._document_controller.open_document(name)
diff --git a/client/settings/dialogs.py b/client/settings/dialogs.py
index 4712e41..42cfe96 100644
--- a/client/settings/dialogs.py
+++ b/client/settings/dialogs.py
@@ -759,26 +759,21 @@ class DotExpressSettingsDialog(SingletonDialogMixin, MultiCategorySettingsDialog
             )
         )
 
-    @classmethod
-    def sync_open_font_size(cls, font_size: int) -> None:
-        instance = cls._instance
-        if instance is None:
-            return
-        normalized_view = normalize_view_settings(
-            ViewSettings(
-                font_size,
-                instance.snapshot.view.scheme,
-                instance.snapshot.view.braille_font,
-            )
+    def sync_font_size(self, font_size: int) -> None:
+        """Take a font size changed in the main window (Ctrl+wheel).
+
+        A View panel with an unsaved font size edit keeps it, and then the snapshot is left alone too.
+        """
+        view = normalize_view_settings(
+            ViewSettings(font_size, self.snapshot.view.scheme, self.snapshot.view.braille_font)
         )
-        view_panel = None
-        for panel in instance.panel_instances.values():
-            if isinstance(panel, ViewSettingsPanel):
-                view_panel = panel
-                break
-        if view_panel is not None and getattr(view_panel, "font_size_dirty", False):
+        view_panel = self._view_panel()
+        if view_panel is not None and not view_panel.sync_font_size(view.font_size):
             return
-        instance.snapshot = instance.snapshot.with_view(normalized_view)
-        if view_panel is not None:
-            view_panel.font_size_spin.SetValue(normalized_view.font_size)
-            view_panel.font_size_dirty = False
+        self.snapshot = self.snapshot.with_view(view)
+
+    def _view_panel(self) -> ViewSettingsPanel | None:
+        for panel in self.panel_instances.values():
+            if isinstance(panel, ViewSettingsPanel):
+                return panel
+        return None
EOF
git -C $REPO diff --stat -- client/gui.py client/settings
```

Expected:

```text
 client/gui.py              |  4 +++-
 client/settings/dialogs.py | 37 ++++++++++++++++---------------------
 2 files changed, 19 insertions(+), 22 deletions(-)
```

- [ ] **Step 4: Run green: the touched modules, the P2-1 singleton characterization, the full suite.**

```bash
$PY -m unittest tests.test_settings_dialogs tests.test_dialog_base tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_settings_dialogs.TextProcessingSingletonTest tests.test_settings_dialogs.DotExpressSettingsSingletonTest tests.test_settings_dialogs.SingletonSlotIndependenceTest tests.test_gui_document_flows.BrailleAppLifecycleTest.test_open_settings_uses_singleton_dialog 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (78 + 26 + 151 = 255; the P2-1 singleton characterization (8 + 11 + 1) and the open-settings test unchanged and green; 1042 + 1):

```text
Ran 255 tests
OK (skipped=2)
Ran 21 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1043 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Mutation check of the new code.** Every mutant must fail the three touched modules.

```bash
$PY -I $T/tools/font_size_mutants.py $REPO/client $T/mut new
git -C $REPO status --short -- client/gui.py client/settings client/ui
```

Expected (every line FAILED; `skipped=2` is the gui module's usual Windows-only skips; the `status` lines are this task's two production files, not committed yet):

```text
open-instance-inherits-parent-slot: failures=2 errors=0 (FAILED (failures=2, skipped=2))
open-instance-raises-the-dialog: failures=5 errors=1 (FAILED (failures=5, errors=1, skipped=2))
panel-ignores-pending-edit: failures=3 errors=0 (FAILED (failures=3, skipped=2))
panel-keeps-dirty-flag-after-set: failures=1 errors=0 (FAILED (failures=1, skipped=2))
panel-reports-refusal-as-accepted: failures=3 errors=0 (FAILED (failures=3, skipped=2))
dialog-writes-snapshot-despite-edit: failures=2 errors=0 (FAILED (failures=2, skipped=2))
dialog-not-normalized: failures=4 errors=0 (FAILED (failures=4, skipped=2))
dialog-overwrites-scheme: failures=14 errors=0 (FAILED (failures=14, skipped=2))
dialog-exact-panel-type: failures=1 errors=0 (FAILED (failures=1, skipped=2))
dialog-snapshot-not-written: failures=17 errors=0 (FAILED (failures=17, skipped=2))
gui-no-sync: failures=4 errors=0 (FAILED (failures=4, skipped=2))
gui-raises-the-dialog: failures=1 errors=0 (FAILED (failures=1, skipped=2))
gui-sync-before-save: failures=1 errors=0 (FAILED (failures=1, skipped=2))
 M client/gui.py
 M client/settings/dialogs.py
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/settings/dialogs.py client/gui.py client/tests/test_settings_dialogs.py
git -C $REPO commit -q -F - <<'EOF'
refactor: sync font size through the open settings dialog

The main window asks DotExpressSettingsDialog.open_instance() for the
open dialog and calls its sync_font_size(); the dialog finds its own
View panel and the panel decides about a pending edit. The reverse
classmethod probe sync_open_font_size is removed (P2-4 step 3, no
alias); behavior is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: sync font size through the open settings dialog
```

---

### Task 4: Final verification against the spec's acceptance criteria (no commit)

- [ ] **Step 1: AC1, the roadmap command and the neighbours.**

```bash
$PY -m unittest tests.test_settings_dialogs -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_settings_dialogs 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_dialog_base tests.test_gui_document_flows tests.test_view_settings tests.test_input_shortcuts tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (AC1: 78 tests, all `ok`; the neighbours green):

```text
78
Ran 78 tests
OK
Ran 228 tests
OK (skipped=2)
```

- [ ] **Step 2: AC2, the full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (1023 + 20; only the P2-5 failure; no errors):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 1043 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 3: AC3, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 1043 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=1043 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC3, the three touched modules alone and in both orders of each pair.**

```bash
for order in tests.test_settings_dialogs tests.test_dialog_base tests.test_gui_document_flows \
  "tests.test_settings_dialogs tests.test_dialog_base" "tests.test_dialog_base tests.test_settings_dialogs" \
  "tests.test_settings_dialogs tests.test_gui_document_flows" "tests.test_gui_document_flows tests.test_settings_dialogs" \
  "tests.test_dialog_base tests.test_gui_document_flows" "tests.test_gui_document_flows tests.test_dialog_base"; do
  echo "$order: $($PY -B -m unittest $order 2>&1 | grep -E '^(OK|FAILED)')"
done
```

Expected:

```text
tests.test_settings_dialogs: OK
tests.test_dialog_base: OK
tests.test_gui_document_flows: OK (skipped=2)
tests.test_settings_dialogs tests.test_dialog_base: OK
tests.test_dialog_base tests.test_settings_dialogs: OK
tests.test_settings_dialogs tests.test_gui_document_flows: OK (skipped=2)
tests.test_gui_document_flows tests.test_settings_dialogs: OK (skipped=2)
tests.test_dialog_base tests.test_gui_document_flows: OK (skipped=2)
tests.test_gui_document_flows tests.test_dialog_base: OK (skipped=2)
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

- [ ] **Step 6: AC6 greps (correction 1 for the `gui.py` one).**

```bash
cd $REPO
echo 1; grep -rn "sync_open_font_size" client --include=*.py --exclude-dir=.venv
echo 2; grep -n "_instance" client/gui.py
echo 3; grep -nw "_instance" client/gui.py
echo 4; grep -n "isinstance(panel, ViewSettingsPanel)" client/settings/dialogs.py
echo 5; grep -n "font_size_dirty\|font_size_spin" client/settings/dialogs.py
echo 6; grep -nE "^class ViewSettingsPanel|^CommitSettings|def _view_panel" client/settings/dialogs.py
cd $REPO/client
```

Expected (1: nothing; 2: only the `open_instance()` line; 3: nothing; 4: one line, inside `_view_panel` (line 6 shows `_view_panel` starts just above it); 5: every line between `class ViewSettingsPanel` and `CommitSettings`):

```text
1
2
558:		settings_dialog = DotExpressSettingsDialog.open_instance()
3
4
777:            if isinstance(panel, ViewSettingsPanel):
5
562:        self.font_size_dirty = False
568:        self.font_size_spin = wx.SpinCtrl(
575:        grid.Add(self.font_size_spin, 1, wx.EXPAND)
596:        self.font_size_spin.Bind(wx.EVT_SPINCTRL, self._on_font_size_changed)
597:        self.font_size_spin.Bind(wx.EVT_TEXT, self._on_font_size_changed)
603:        self.font_size_spin.SetValue(VIEW_FONT_SIZE_RANGE.clamp(view.font_size))
606:        self.font_size_dirty = False
611:                self.font_size_spin.GetValue(),
619:        self.font_size_dirty = True
626:        if self.font_size_dirty:
628:        self.font_size_spin.SetValue(font_size)
629:        self.font_size_dirty = False
6
555:class ViewSettingsPanel(SettingsPanel):
645:CommitSettings = Callable[
775:    def _view_panel(self) -> ViewSettingsPanel | None:
```

- [ ] **Step 7: AC7, the branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -4
git -C $REPO diff main --name-only
git -C $REPO diff --stat HEAD~3 HEAD
```

Expected (only the six code files and the docs differ from `main`):

```text
refactor: sync font size through the open settings dialog
refactor: add open dialog and panel font size hooks
test: characterize font size sync
docs: plan font size sync
client/gui.py
client/settings/dialogs.py
client/tests/test_dialog_base.py
client/tests/test_gui_document_flows.py
client/tests/test_settings_dialogs.py
client/ui/dialog_base.py
docs/superpowers/plans/2026-10-08-p2-4-font-size-sync.md
docs/superpowers/specs/2026-10-08-p2-4-font-size-sync-design.md
docs/superpowers/specs/2026-10-08-p2-4-font-size-sync-design_zh-TW.md
 client/gui.py                           |   4 +-
 client/settings/dialogs.py              |  48 ++++----
 client/tests/test_dialog_base.py        |  36 ++++++
 client/tests/test_gui_document_flows.py | 131 ++++++++++++++++++++
 client/tests/test_settings_dialogs.py   | 209 ++++++++++++++++++++++++++++----
 client/ui/dialog_base.py                |   5 +
 6 files changed, 389 insertions(+), 44 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): with real wxPython on Windows and NVDA, open Settings > View, Ctrl+wheel in an editor: the Font Size spin follows. Type a size in the spin, Ctrl+wheel: the spin keeps the typed value. Apply, then Ctrl+wheel: the spin follows again. Open Settings on the Translation category, Ctrl+wheel, then switch to View: it shows the new size. Close the dialog (OK, Cancel, close box, Escape), then Ctrl+wheel: no error. Also check that Ctrl+wheel leaves the focus in the editor while the dialog is open (Review Focus 2) and whether the real `wx.SpinCtrl.SetValue` emits `EVT_TEXT` (Review Focus 1; the code handles both). No visible or spoken change is intended, so no screenshot is needed.
