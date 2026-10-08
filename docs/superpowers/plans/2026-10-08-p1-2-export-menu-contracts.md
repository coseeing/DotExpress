# Export and Menu Contracts (P1-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The format registry (`documents/formats.py`) and the document menu descriptors (`ui/action_menu.py`) become the only places that describe export formats and document menu items. Every export writer takes `(path, document, context: ExportContext)` and returns the written `Path`; `gui._write_export_document` calls them all the same way. The save-dialog wildcard and the Export/Export All submenus come from the registry. Menu state and handlers are keyed by action, and a new wx-free `ui/menu_builder.py` builds and binds both the File menu and the document-list context menu. `gui._MENU_TRANSLATION_MARKERS` is deleted; every label is `N_()`-marked where it is defined. Same menus, same dialogs, same exported bytes, no user-facing string change; `client/locales/` and `scripts/` untouched.

**Architecture:** Characterization first (Task 1): a recording fake of `wx.Menu` pins the exact File-menu, context-menu and menu-bar call logs, the export dialog arguments and the exported bytes on the unchanged code. Tasks 2-6 are the spec's migration steps 2-6, one green commit each, red test first. The characterization tests stay byte-identical from Task 1 to the end. Task 7 is the spec's acceptance run.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `inspect`, `ast`, `zipfile`, `tempfile`, `dataclasses`, `typing.Literal`). wxPython is not installed; `gui` loads through the P0-4 `tests/wx_stub.py` scope that `tests/test_gui_document_flows.py` already uses, and menus are checked with recording fakes.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-2-export-menu-contracts-design.md` (authoritative, latest commit `1673997`, which drops the four orphan import-filter msgids: 357 -> 353). The corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-2-export-menu-contracts`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (15, nothing else): `client/documents/formats.py`, `client/ui/action_menu.py`, `client/ui/menu_builder.py` (new), `client/ui/translation_menu.py`, `client/gui.py`, `client/dialog.py`, `client/conversion/preprocessing/user_script.py`; tests `client/tests/menu_recording.py` (new, helper, not a test module), `client/tests/test_menu_builder.py` (new), `client/tests/test_gui_document_flows.py`, `client/tests/test_document_formats.py`, `client/tests/test_action_menu.py`, `client/tests/test_i18n.py`. Never touch `client/locales/`, `scripts/`, `client/documents/workspace.py`, `client/ui/import_dialog.py`, `client/settings/*`, `client/tests/wx_stub.py`.
- Indentation per file, unchanged: TABS in `gui.py` and `dialog.py` (the 4-space continuation lines in `gui.py`'s import block stay as they are); 4 spaces in every other touched file, including the new `ui/menu_builder.py`, `tests/menu_recording.py` and `tests/test_menu_builder.py`.
- The patches carry the exact characters (tabs, context lines). Run every block as it is; do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes. `"HTML"` and `"HTML files (*.html)|*.html"` stay unmarked (they are not msgids today; marking them would add catalog entries). Do not edit `.po`/`.pot`/`.mo`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run (see "Dry Run"). "Red" summaries use `LC_ALL=C sort | uniq -c` and strip the repo path and the timing, so the order and the counts are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p12impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today.
- Baseline (re-verified at `1673997`, the spec commit; code identical to `029a86e`): `$PY -m unittest discover -s tests` gives `Ran 575 tests`, `FAILED (failures=1, skipped=7)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: one more test pins the marker tuple.** The spec's "Tests that pin the current shape" and "Updated tests" miss `tests/test_i18n.py::ExtractionMarkerTest::test_gui_menu_translation_markers_use_n_`. It parses `gui.py` and asserts that `_MENU_TRANSLATION_MARKERS` exists as a tuple of exactly 48 `N_()` calls, so deleting the tuple (spec step 6) fails it. Its purpose (P0-5) is that the strings translated through variables stay extractable. Task 6 replaces it, in the same commit, with `test_former_marker_strings_are_still_extracted`: the 44 strings of the old tuple that are still shown (48 minus the four group C orphans) must each be the literal first argument of some `_()`/`N_()` call in `client/` outside `tests/` and `.venv/` (the `generate-pot.bat` file set). It does not care where the mark sits, so it is not a placement guard; it fails if a definition site loses its `N_()` (checked by mutation: unmarking `wildcard_label="DEP"` fails it with `['DEP'] != []`). Its explanatory comment avoids the old constant's name so that acceptance grep 2 stays empty.
2. **Refinement: shared recording fakes in `tests/menu_recording.py`.** The spec has a recording `wx.Menu` fake in `test_gui_document_flows.py` and "recording fakes" in `test_menu_builder.py`, and requires the builder log to equal characterization test 1's log. To keep one literal, the fakes (`MenuRecorder`, `RecordedMenu`, `RecordedItem`, `fake_translate`), the literal expected build log `DOCUMENT_MENU_BUILD_LOG` and the `enable_log(...)` helper live in a new helper module `tests/menu_recording.py` (no `test_` prefix, so `discover` does not collect it; no wx import, so no stub scope). Log format: `("new", "menu0")`, `("menu0", "Append", -1, "T[Open]")`, `("menu0", "AppendSubMenu", "menu1", "T[Export]")`, `("menu0", "Bind", "EVT_MENU", "menu1:T[Package DEP]")`, `("Enable", "menu0:T[Open]", False)`, `("menu0", "Destroy")`; an item is named `<owning menu>:<label>`.
3. **Refinement: 11 characterization tests, not 10.** Spec test 4 (context menu) is two tests: `test_context_menu_on_item_selects_it_and_pops_up_below_it` and `test_keyboard_context_menu_without_selection_clears_it`. The keyboard case sets `frame._document_menu_items = {}` because `_clear_document_selection()` calls `_sync_document_menu_state()` without arguments, and on the stub frame a missing attribute is a truthy no-op function (wx_stub masking). Spec test 8's "real writers" also checks that the BRL writer creates a missing parent directory, as today. Mutation checks on the dry run: changing the Open bind target, the HTML wildcard, the HTML writer's parent creation, the Export All handler or the `Enable` order fails 5, 1, 1, 3 and 5 of the 11 tests.
4. **Refinement: `gui` stops importing `get_document_menu_descriptors`.** After Task 5 only `ui/menu_builder.py` reads the descriptors. `tests/test_removed_dead_code.py` only requires the function to exist in `ui.action_menu`, which it still does.
5. **Refinement: `build_document_menu`'s `ValueError` text** is `Document menu handlers do not match the menu actions: missing [...], extra [...].` (`missing` in descriptor order, `extra` sorted). `test_menu_builder` matches the bracketed parts.
6. **Refinement: `ExportContext` alone is a test too.** Task 2 adds `test_export_context_defaults_to_no_results`; Task 6 also checks `get_import_filter_labels()` ends with `ALL_SUPPORTED_FILES_LABEL` and keeps its full value `["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"]`.
7. **Refinement: the zh_TW label test skips comments and obsolete (`#~`) entries** and checks 16 labels (8 document-menu, 3 Export submenu, 5 Translation menu); there are no fuzzy entries in the `.po` today.

Everything else in the spec was re-checked at `1673997`: the line numbers it cites in `gui.py`, `documents/formats.py` and `ui/action_menu.py`; the 48-entry marker tuple and its groups A/B/C; `"HTML files (*.html)|*.html"` is not in the `.pot`; the focused 8-module baseline (`Ran 118 tests`, OK); the msgid scan (357 = `.pot` = `p12/base_msgids.json`); no other production caller of the deleted `gui` names; `requires_braille` has no production reader.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `1673997` (`$SP/p12plan/dry`, never the repo), one commit per task; after each task the full suite and the msgid scan gave the counts below. The patches in this file are `git diff`s of those commits, split into test files (Step 1) and the rest. Then this file's blocks were extracted and run in order on a fresh clone (`$SP/p12plan/replay`) by a harness that compares every "Expected" block with the real output: all 6 commits applied, every expected block matched byte for byte, and the resulting `client/` tree is identical to the dry clone (`git diff` empty). Final sha256: `client/ui/menu_builder.py` `e81b60013e7f88b40ff2a43112afef0953f721fd7b75d957923e162dc3f6c48e`, `client/ui/action_menu.py` `fd0eca2cfce0f5eec29cb75365fc2747284835e45bd67c665b9f9cbcbbbf78a4`, `client/documents/formats.py` `d961c28d62a4c6976b91d460793913f3fcc1ed6ff2012449be99c23f8482ff34`, `client/gui.py` `bcf805dac2c1be127a3780d4a87943c44675152a0c246191d36d6f41a3316eba`.

## Review Focus

1. **Menu wiring the user clicks.** Same items, order, nesting, translated labels, bind target (the top-level menu, also for submenu items), bind order, handler and format key per item, and `Enable` values and order. Tests: characterization `test_file_menu_build_log`, `test_menu_handlers_dispatch_to_frame_methods`, `test_menu_enabled_states_follow_selection_and_documents`, both context-menu tests and `test_menu_bar_menus_items_and_handlers` (Task 1, unchanged through Task 6), plus `test_menu_builder`. Not testable here: real wx event delivery and the zh_TW look (Windows screenshots, see "Windows verification debt").
2. **Exported bytes.** DEP zip members and contents, BRL bytes, HTML render of the per-document cache (or the empty render), and the HTML writer still not creating parent directories. Tests: `test_real_writers_produce_today_bytes`, `test_export_all_html_uses_each_document_cache`, `test_dep_and_brl_writers_ignore_the_context`.
3. **Save dialog.** Title, `defaultFile`, the translated wildcard (the HTML one is still shown in English because it is not a msgid), style flags, and the suffix correction (case-insensitive; a wrong suffix is replaced). Tests: `test_export_dialog_title_default_file_wildcard_and_style`, `test_export_dialog_corrects_only_a_wrong_extension`, `test_export_wildcard_is_the_single_format_save_filter`.
4. **Translations still reach the UI.** Every former marker string is still extracted (353 msgids, only the four orphans gone), and every menu label has a zh_TW entry. Tests: `test_former_marker_strings_are_still_extracted`, `test_menu_labels_have_zh_tw_translations`, acceptance criterion 5.
5. **Fail-loud contracts.** A writer called without a context, a handler map that does not match the descriptors, a state entry with no menu item, and a non-exportable format each raise (`TypeError`, `ValueError`, `KeyError`, `ValueError`). Tests: `test_writers_take_path_document_and_context`, `test_missing_handler_raises_before_any_menu_call`, `test_extra_handler_raises_before_any_menu_call`, `test_apply_state_rejects_unknown_action`, `test_export_wildcard_rejects_non_exportable_format`, `test_write_export_document_rejects_non_exportable_format` (existing).

## File Map

- Task 1: create `client/tests/menu_recording.py`; modify `client/tests/test_gui_document_flows.py` (new class `DocumentMenuAndExportCharacterizationTest`).
- Task 2: modify `client/documents/formats.py`, `client/gui.py`; tests `test_document_formats.py`, `test_gui_document_flows.py`.
- Task 3: modify `client/documents/formats.py`, `client/ui/action_menu.py`, `client/gui.py`; tests `test_document_formats.py`, `test_action_menu.py`, `test_gui_document_flows.py`.
- Task 4: modify `client/ui/action_menu.py`, `client/gui.py`; tests `test_action_menu.py`, `test_gui_document_flows.py`.
- Task 5: create `client/ui/menu_builder.py`, `client/tests/test_menu_builder.py`; modify `client/gui.py`.
- Task 6: modify `client/documents/formats.py`, `client/ui/action_menu.py`, `client/ui/translation_menu.py`, `client/dialog.py`, `client/conversion/preprocessing/user_script.py`, `client/gui.py`; tests `test_document_formats.py`, `test_action_menu.py`, `test_i18n.py`.

## Expected Counts

| After task | new test methods | `discover` `Ran` | new tests ok (suite check) | msgid scan |
| --- | --- | --- | --- | --- |
| baseline | - | 575 | 0 | 357, `SOURCE == POT`, `SOURCE == SAVED` |
| 1 characterization | 11 | 586 | 11 | same |
| 2 writer contract | 5 (one runs twice) | 592 | 17 | same |
| 3 registry wildcard and submenus | 5 | 597 | 22 | same |
| 4 action-keyed state | 4 | 601 | 26 | same |
| 5 menu builder | 11 | 612 | 37 | same |
| 6 mark labels at definitions | 3 (1 replaces an old one) | 614 | 40 | 353, only the four orphans differ |

Every row: `FAILED (failures=1, skipped=7)` (the P2-5 case) and `BASELINE-TESTS-IDENTICAL`. `GuiDocumentFlowsTest` is inherited by `BrailleAppLifecycleTest`, so Task 2's new `test_write_export_document_passes_cached_results_to_every_writer` runs twice. "New tests ok" counts passing test lines that are not in the baseline; Task 6 removes `test_gui_menu_translation_markers_use_n_` (the suite check ignores that one baseline line).

## Throwaway Tooling (not committed)

All in `$T/tools/`, outside the repo (Task 0 creates them):

- `check_suite.sh <Ran> <new ok>`: full `discover -v`; every baseline test line except the replaced marker test must appear unchanged; counts passing non-baseline lines.
- `msgid_scan.py`: the P0-5 AST stand-in for xgettext, copied from `$SP/p12/tools/msgid_scan.py` (the spec author's copy; source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`). `--compare $SP/p12/base_msgids.json` compares with the 357-msgid baseline.
- `shuffle_harness.py <seed> [modules]`: runs test modules in a seeded random order. Copied from `$SP/shuffle_harness.py`.

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
docs: plan export and menu contracts
refactor/p1-2-export-menu-contracts
```

- [ ] **Step 2: Create the tools and record the baseline.**

```bash
mkdir -p $T/tools
cat > $T/tools/check_suite.sh <<'EOF'
#!/bin/bash
# Throwaway (P1-2). usage: check_suite.sh <expected Ran> <expected new-test ok>   (run from client/)
# Every baseline test line must still be present with the same result, except the one test that
# Task 6 replaces (test_gui_menu_translation_markers_use_n_). "new tests ok" counts passing test
# lines that are not in the baseline.
SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
T=${T:-$SP/p12impl}
PY=$SP/venv/bin/python
REPLACED='test_gui_menu_translation_markers_use_n_'
$PY -m unittest discover -s tests -v > $T/run.txt 2>&1
grep ' \.\.\. ' $T/run.txt | sort > $T/run_lines.txt
grep -E '^Ran|^FAILED|^OK' $T/run.txt | sed -E 's/ in [0-9.]+s$//'
grep -E '^(FAIL|ERROR):' $T/run.txt
missing=$(comm -23 <(grep -v "$REPLACED" $T/baseline_discover_verbose.txt) $T/run_lines.txt)
[ -z "$missing" ] && echo "BASELINE-TESTS-IDENTICAL" || { echo "BASELINE-TESTS-CHANGED:"; echo "$missing"; }
grep -q "^Ran $1 tests" $T/run.txt && echo "RAN-COUNT-OK ($1)" || echo "RAN-COUNT-MISMATCH (expected $1)"
echo "new tests ok: $(comm -13 $T/baseline_discover_verbose.txt $T/run_lines.txt | grep -c '\.\.\. ok$') (expected $2)"
EOF
chmod +x $T/tools/check_suite.sh
cp $SP/p12/tools/msgid_scan.py $SP/shuffle_harness.py $T/tools/
$PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | sort > $T/baseline_discover_verbose.txt
wc -l < $T/baseline_discover_verbose.txt
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json
for s in 1 2 3 4 5; do $PY -I $T/tools/shuffle_harness.py $s | head -1; done
```

Expected:

```text
575
source msgids: 357
pot msgids: 357
SOURCE == POT
SOURCE == SAVED
seed=1 ran=575 failures=1 errors=0 skipped=7
seed=2 ran=575 failures=0 errors=8 skipped=7
seed=3 ran=575 failures=1 errors=0 skipped=7
seed=4 ran=575 failures=1 errors=0 skipped=7
seed=5 ran=575 failures=0 errors=8 skipped=7
```

Seeds 2 and 5 show 8 errors in `test_conversion_service` on the unchanged code: a pre-existing module-order pollution (`translate` re-import, see refinement 8 of the P1-1 plan). It is out of scope; Task 7 only checks that the shuffled runs show nothing beyond this known set.

---

### Task 1: Characterize today's menus and exports

**Files:**
- Create: `client/tests/menu_recording.py`
- Modify: `client/tests/test_gui_document_flows.py` (imports; new class `DocumentMenuAndExportCharacterizationTest` at the end)

**Interfaces:**
- Consumes: nothing new. Calls existing frame methods `_create_document_menu()`, `_sync_document_menu_state()`, `on_document_context_menu(event)`, `_create_menu_bar()`, `_export_document_with_dialog(document, key)`, `_write_export_document(path, document, key)`, `_export_next_document(documents, dir, key, result)`, `on_output_text_key_down(event)`. Patches `gui.wx.Menu`, `gui.wx.EVT_MENU` (`create=True`: under the stub every access of a missing wx attribute creates a new class), `gui.wx.MenuBar`, `gui.wx.FileDialog`, `gui.wx.MessageBox`, `gui.wx.CallAfter`, `gui._`.
- Produces (`tests/menu_recording.py`, used again in Task 5): `fake_translate(value) -> "T[value]"`; `MenuRecorder()` with `.new_menu()` (names menus `menu0`, `menu1`, ...), `.log` (list of tuples), `.binds` (list of `(menu name, item name, handler)`), `.menus`; `RecordedMenu.Append(item_id, label)`, `.AppendSubMenu(submenu, label)`, `.Bind(event, handler, item)`, `.Destroy()`; `RecordedItem(log, name)` with `.name` and `.Enable(value)`; `DOCUMENT_MENU_BUILD_LOG` (the literal 29-entry append-then-bind log of today's File menu); `DOCUMENT_MENU_TOP_ITEMS`; `enable_log(*values, items=DOCUMENT_MENU_TOP_ITEMS)`.

These tests run on the unchanged code and must pass immediately: their expected values are what the app does today. They stay byte-identical through Task 6; if one of them fails in a later task, the refactor changed behavior. Fix the code, not the test.

- [ ] **Step 1: Add the recording fakes and the characterization tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/menu_recording.py b/client/tests/menu_recording.py
new file mode 100644
index 0000000..1f8e0a3
--- /dev/null
+++ b/client/tests/menu_recording.py
@@ -0,0 +1,120 @@
+"""Recording fakes for document-menu tests (no wx).
+
+``MenuRecorder.new_menu`` creates menus named ``menu0``, ``menu1``, ... in
+creation order. Every wx-style call lands in one shared ``log`` list:
+
+* ``("new", "menu0")``
+* ``("menu0", "Append", item_id, label)``
+* ``("menu0", "AppendSubMenu", "menu1", label)``
+* ``("menu0", "Bind", event, "menu1:<label>")``
+* ``("Enable", "menu0:<label>", value)``
+* ``("menu0", "Destroy")``
+
+Items are named ``"<owning menu>:<label>"``. ``binds`` keeps
+``(menu name, item name, handler)`` for every ``Bind`` so tests can call the
+handlers.
+
+``DOCUMENT_MENU_BUILD_LOG`` is today's File-menu build log (append pass, then
+bind pass) with labels translated as ``T[...]``, ``wx.ID_ANY == -1`` and the
+event recorded as the string ``"EVT_MENU"``.
+"""
+
+from __future__ import annotations
+
+
+def fake_translate(value: str) -> str:
+    return f"T[{value}]"
+
+
+class RecordedItem:
+    def __init__(self, log: list, name: str):
+        self.log = log
+        self.name = name
+
+    def Enable(self, enabled: bool) -> None:
+        self.log.append(("Enable", self.name, enabled))
+
+
+class RecordedMenu:
+    def __init__(self, recorder: "MenuRecorder", name: str):
+        self.recorder = recorder
+        self.name = name
+
+    def Append(self, item_id, label):
+        self.recorder.log.append((self.name, "Append", item_id, label))
+        return RecordedItem(self.recorder.log, f"{self.name}:{label}")
+
+    def AppendSubMenu(self, submenu, label):
+        self.recorder.log.append((self.name, "AppendSubMenu", submenu.name, label))
+        return RecordedItem(self.recorder.log, f"{self.name}:{label}")
+
+    def Bind(self, event, handler, item):
+        self.recorder.log.append((self.name, "Bind", event, item.name))
+        self.recorder.binds.append((self.name, item.name, handler))
+
+    def Destroy(self) -> None:
+        self.recorder.log.append((self.name, "Destroy"))
+
+
+class MenuRecorder:
+    def __init__(self):
+        self.log: list = []
+        self.binds: list = []
+        self.menus: list[RecordedMenu] = []
+
+    def new_menu(self, *_args, **_kwargs) -> RecordedMenu:
+        menu = RecordedMenu(self, f"menu{len(self.menus)}")
+        self.menus.append(menu)
+        self.log.append(("new", menu.name))
+        return menu
+
+
+DOCUMENT_MENU_BUILD_LOG = [
+    ("new", "menu0"),
+    ("menu0", "Append", -1, "T[Open]"),
+    ("menu0", "Append", -1, "T[Delete]"),
+    ("menu0", "Append", -1, "T[Delete All]"),
+    ("menu0", "Append", -1, "T[Add]"),
+    ("menu0", "Append", -1, "T[Rename]"),
+    ("menu0", "Append", -1, "T[Import]"),
+    ("new", "menu1"),
+    ("menu0", "AppendSubMenu", "menu1", "T[Export]"),
+    ("menu1", "Append", -1, "T[Package DEP]"),
+    ("menu1", "Append", -1, "T[Braille BRL]"),
+    ("menu1", "Append", -1, "T[Dual View HTML]"),
+    ("new", "menu2"),
+    ("menu0", "AppendSubMenu", "menu2", "T[Export All]"),
+    ("menu2", "Append", -1, "T[Package DEP]"),
+    ("menu2", "Append", -1, "T[Braille BRL]"),
+    ("menu2", "Append", -1, "T[Dual View HTML]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Open]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Delete]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Delete All]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Add]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Rename]"),
+    ("menu0", "Bind", "EVT_MENU", "menu0:T[Import]"),
+    ("menu0", "Bind", "EVT_MENU", "menu1:T[Package DEP]"),
+    ("menu0", "Bind", "EVT_MENU", "menu1:T[Braille BRL]"),
+    ("menu0", "Bind", "EVT_MENU", "menu1:T[Dual View HTML]"),
+    ("menu0", "Bind", "EVT_MENU", "menu2:T[Package DEP]"),
+    ("menu0", "Bind", "EVT_MENU", "menu2:T[Braille BRL]"),
+    ("menu0", "Bind", "EVT_MENU", "menu2:T[Dual View HTML]"),
+]
+
+# Top-level items of the default document menu, in Enable order.
+DOCUMENT_MENU_TOP_ITEMS = (
+    "menu0:T[Open]",
+    "menu0:T[Delete]",
+    "menu0:T[Delete All]",
+    "menu0:T[Add]",
+    "menu0:T[Rename]",
+    "menu0:T[Import]",
+    "menu0:T[Export]",
+    "menu0:T[Export All]",
+)
+
+
+def enable_log(*values: bool, items=DOCUMENT_MENU_TOP_ITEMS) -> list:
+    """The expected ``Enable`` entries for the top-level items, in order."""
+    assert len(values) == len(items)
+    return [("Enable", item, value) for item, value in zip(items, values)]
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index f1002f8..835e9fc 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -3,11 +3,14 @@ from __future__ import annotations
 import importlib
 import tempfile
 import unittest
+import zipfile
 from dataclasses import replace
 from pathlib import Path
-from unittest.mock import Mock, patch
+from types import SimpleNamespace
+from unittest.mock import Mock, call, patch
 
 from tests import wx_stub
+from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
 
 _SCOPE = wx_stub.StubScope(
     wx_stub.gui_frame_stubs(),
@@ -26,6 +29,8 @@ from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
 from documents.formats import get_format
+from dual_view.html import render_dual_view_html
+from dual_view.model import DualViewSegment, build_dual_view_model
 
 
 def make_snapshot(
@@ -1222,5 +1227,361 @@ class DictionaryManagementFrameTest(unittest.TestCase):
                 self.assertTrue(hasattr(gui.BrailleFrame, name))
 
 
+class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
+    """Pins today's menu and export behavior; must pass unchanged through P1-2."""
+
+    _make_frame = GuiDocumentFlowsTest._make_frame
+
+    DOCUMENT_HANDLER_NAMES = (
+        "on_open_document",
+        "on_delete_document",
+        "on_delete_all_documents",
+        "on_add_document",
+        "on_rename_document",
+        "on_import_document",
+        "on_export_document",
+        "on_export_all_documents",
+    )
+
+    def _make_menu_frame(self):
+        frame = self._make_frame()
+        frame.handler_calls = Mock()
+        for name in self.DOCUMENT_HANDLER_NAMES:
+            setattr(frame, name, getattr(frame.handler_calls, name))
+        return frame
+
+    def _patch_menus(self, recorder: MenuRecorder):
+        return (
+            patch.object(gui.wx, "Menu", recorder.new_menu),
+            patch.object(gui.wx, "EVT_MENU", "EVT_MENU", create=True),
+            patch.object(gui, "_", fake_translate),
+        )
+
+    def _select_first_of(self, frame, *names: str) -> None:
+        frame.documents = [Document(name, "text", None) for name in names]
+        frame._documents_by_name = {document.name: document for document in frame.documents}
+        frame.document_list = Mock()
+        frame.document_list.GetFirstSelected.return_value = 0
+
+    def test_file_menu_build_log(self) -> None:
+        frame = self._make_menu_frame()
+        recorder = MenuRecorder()
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+
+        with menu_patch, event_patch, translate_patch:
+            menu, _items = frame._create_document_menu()
+
+        self.assertIs(menu, recorder.menus[0])
+        self.assertEqual(
+            recorder.log,
+            DOCUMENT_MENU_BUILD_LOG + enable_log(False, False, False, True, False, True, False, False),
+        )
+
+    def test_menu_handlers_dispatch_to_frame_methods(self) -> None:
+        frame = self._make_menu_frame()
+        recorder = MenuRecorder()
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+        with menu_patch, event_patch, translate_patch:
+            frame._create_document_menu()
+        event = object()
+        expected = [
+            ("menu0:T[Open]", call.on_open_document(event)),
+            ("menu0:T[Delete]", call.on_delete_document(event)),
+            ("menu0:T[Delete All]", call.on_delete_all_documents(event)),
+            ("menu0:T[Add]", call.on_add_document(event)),
+            ("menu0:T[Rename]", call.on_rename_document(event)),
+            ("menu0:T[Import]", call.on_import_document(event)),
+            ("menu1:T[Package DEP]", call.on_export_document("dep")),
+            ("menu1:T[Braille BRL]", call.on_export_document("brl")),
+            ("menu1:T[Dual View HTML]", call.on_export_document("html")),
+            ("menu2:T[Package DEP]", call.on_export_all_documents("dep")),
+            ("menu2:T[Braille BRL]", call.on_export_all_documents("brl")),
+            ("menu2:T[Dual View HTML]", call.on_export_all_documents("html")),
+        ]
+
+        self.assertEqual([item for _menu, item, _handler in recorder.binds], [item for item, _call in expected])
+        for (menu_name, item_name, handler), (_item, expected_call) in zip(recorder.binds, expected):
+            with self.subTest(item=item_name):
+                frame.handler_calls.reset_mock()
+                handler(event)
+                self.assertEqual(menu_name, "menu0")
+                self.assertEqual(frame.handler_calls.mock_calls, [expected_call])
+
+    def test_menu_enabled_states_follow_selection_and_documents(self) -> None:
+        frame = self._make_menu_frame()
+        recorder = MenuRecorder()
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+        with menu_patch, event_patch, translate_patch:
+            _menu, items = frame._create_document_menu()
+        frame._document_menu_items = items
+
+        self.assertEqual(
+            recorder.log[len(DOCUMENT_MENU_BUILD_LOG):],
+            enable_log(False, False, False, True, False, True, False, False),
+        )
+
+        recorder.log.clear()
+        self._select_first_of(frame, "alpha")
+        frame._sync_document_menu_state()
+
+        self.assertEqual(recorder.log, enable_log(True, True, True, True, True, True, True, True))
+
+    def test_context_menu_on_item_selects_it_and_pops_up_below_it(self) -> None:
+        frame = self._make_menu_frame()
+        self._select_first_of(frame, "alpha")
+        frame._selected_document_name = None
+        recorder = MenuRecorder()
+        document_list = frame.document_list
+        document_list.ScreenToClient.return_value = gui.wx.Point(5, 6)
+        document_list.HitTest.return_value = (0, 0)
+        document_list.GetItemRect.return_value = SimpleNamespace(x=10, y=20, height=5)
+        document_list.GetItemCount.return_value = 1
+        document_list.PopupMenu.side_effect = lambda menu, position: recorder.log.append(("PopupMenu", menu.name, position))
+        event = Mock()
+        event.GetPosition.return_value = gui.wx.Point(100, 200)
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+
+        with menu_patch, event_patch, translate_patch:
+            frame.on_document_context_menu(event)
+
+        self.assertEqual(
+            recorder.log,
+            DOCUMENT_MENU_BUILD_LOG
+            + enable_log(True, True, True, True, True, True, True, True)
+            + [("PopupMenu", "menu0", (10, 25)), ("menu0", "Destroy")],
+        )
+        document_list.ScreenToClient.assert_called_once_with(gui.wx.Point(100, 200))
+        document_list.HitTest.assert_called_once_with(gui.wx.Point(5, 6))
+        document_list.Select.assert_called_once_with(0)
+        document_list.Focus.assert_called_once_with(0)
+        self.assertEqual(frame._selected_document_name, "alpha")
+
+    def test_keyboard_context_menu_without_selection_clears_it(self) -> None:
+        frame = self._make_menu_frame()
+        self._select_first_of(frame, "alpha", "beta")
+        frame._selected_document_name = "alpha"
+        frame._document_menu_items = {}
+        recorder = MenuRecorder()
+        document_list = frame.document_list
+        document_list.GetFirstSelected.return_value = gui.wx.NOT_FOUND
+        document_list.HitTest.return_value = (gui.wx.NOT_FOUND, 0)
+        document_list.PopupMenu.side_effect = lambda menu, position: recorder.log.append(("PopupMenu", menu.name, position))
+        event = Mock()
+        event.GetPosition.return_value = gui.wx.DefaultPosition
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+
+        with menu_patch, event_patch, translate_patch:
+            frame.on_document_context_menu(event)
+
+        self.assertEqual(
+            recorder.log,
+            DOCUMENT_MENU_BUILD_LOG
+            + enable_log(False, False, True, True, False, True, False, True)
+            + [("PopupMenu", "menu0", (0, 0)), ("menu0", "Destroy")],
+        )
+        self.assertIsInstance(recorder.log[-2][2], gui.wx.Point)
+        document_list.ScreenToClient.assert_not_called()
+        document_list.Select.assert_not_called()
+        document_list.GetItemRect.assert_not_called()
+        self.assertIsNone(frame._selected_document_name)
+
+    def test_menu_bar_menus_items_and_handlers(self) -> None:
+        frame = self._make_menu_frame()
+        for name in (
+            "on_convert",
+            "on_open_dual_view",
+            "on_open_text_processing",
+            "on_open_dictionary_management",
+            "on_open_settings",
+            "on_open_coseeing_website",
+            "on_about",
+        ):
+            setattr(frame, name, getattr(frame.handler_calls, name))
+        recorder = MenuRecorder()
+        frame.Bind = Mock(side_effect=lambda event, handler, item: recorder.log.append(("frame", "Bind", event, handler, item.name)))
+
+        class RecordedMenuBar:
+            def Append(self, menu, title):
+                recorder.log.append(("menubar", "Append", menu.name, title))
+
+        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
+        with menu_patch, event_patch, translate_patch, patch.object(gui.wx, "MenuBar", RecordedMenuBar):
+            menu_bar = frame._create_menu_bar()
+
+        self.assertIsInstance(menu_bar, RecordedMenuBar)
+        self.assertEqual(
+            recorder.log,
+            DOCUMENT_MENU_BUILD_LOG
+            + enable_log(False, False, False, True, False, True, False, False)
+            + [
+                ("menubar", "Append", "menu0", "T[File]"),
+                ("new", "menu3"),
+                ("menu3", "Append", -1, "T[Convert]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_convert, "menu3:T[Convert]"),
+                ("menu3", "Append", -1, "T[Dual View]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_open_dual_view, "menu3:T[Dual View]"),
+                ("menu3", "Append", -1, "T[Text Processing]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_open_text_processing, "menu3:T[Text Processing]"),
+                ("menu3", "Append", -1, "T[Dictionary Management...]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_open_dictionary_management, "menu3:T[Dictionary Management...]"),
+                ("menu3", "Append", -1, "T[Settings]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_open_settings, "menu3:T[Settings]"),
+                ("menubar", "Append", "menu3", "T[Translation]"),
+                ("new", "menu4"),
+                ("menu4", "Append", -1, "T[Coseeing Website]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_open_coseeing_website, "menu4:T[Coseeing Website]"),
+                ("menu4", "Append", 1, "T[About]"),
+                ("frame", "Bind", "EVT_MENU", frame.on_about, "menu4:T[About]"),
+                ("menubar", "Append", "menu4", "T[Help]"),
+            ],
+        )
+
+    def test_export_dialog_title_default_file_wildcard_and_style(self) -> None:
+        dialogs = []
+
+        class RecordedFileDialog:
+            def __init__(self, *args, **kwargs):
+                dialogs.append((args, kwargs))
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.CANCEL
+
+        expected_wildcards = {
+            "dep": "T[DotExpress files (*.dep)|*.dep]",
+            "brl": "T[Braille files (*.brl)|*.brl]",
+            "html": "T[HTML files (*.html)|*.html]",
+        }
+        for key, wildcard in expected_wildcards.items():
+            with self.subTest(format_key=key):
+                frame = self._make_frame()
+                frame._write_export_document = Mock()
+                frame._start_export_conversion = Mock()
+                dialogs.clear()
+                with patch.object(gui.wx, "FileDialog", RecordedFileDialog), patch.object(gui, "_", fake_translate):
+                    frame._export_document_with_dialog(Document("alpha", "t", "b"), key)
+
+                self.assertEqual(
+                    dialogs,
+                    [
+                        (
+                            (frame, "T[Export Document]"),
+                            {
+                                "defaultFile": f"alpha.{key}",
+                                "wildcard": wildcard,
+                                "style": gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
+                            },
+                        )
+                    ],
+                )
+                frame._write_export_document.assert_not_called()
+                frame._start_export_conversion.assert_not_called()
+
+    def test_export_dialog_corrects_only_a_wrong_extension(self) -> None:
+        for chosen, written in (("/tmp/x/out.TXT", "/tmp/x/out.brl"), ("/tmp/x/out.BRL", "/tmp/x/out.BRL")):
+            with self.subTest(chosen=chosen):
+                frame = self._make_frame()
+                frame._write_export_document = Mock()
+                dialog = Mock()
+                dialog.__enter__ = Mock(return_value=dialog)
+                dialog.__exit__ = Mock(return_value=False)
+                dialog.ShowModal.return_value = gui.wx.ID_OK
+                dialog.GetPath.return_value = chosen
+                document = Document("alpha", "t", "b")
+                with (
+                    patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)),
+                    patch.object(gui.wx, "MessageBox", Mock()) as message_box,
+                ):
+                    frame._export_document_with_dialog(document, "brl")
+
+                frame._write_export_document.assert_called_once_with(Path(written), document, "brl")
+                message_box.assert_called_once()
+
+    def test_real_writers_produce_today_bytes(self) -> None:
+        frame = self._make_frame()
+        results = (
+            DualViewSegment(
+                result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
+                source_kind="text",
+            ),
+        )
+        frame._dual_view_results_by_document["alpha"] = results
+        with tempfile.TemporaryDirectory() as directory:
+            root = Path(directory)
+
+            frame._write_export_document(root / "alpha.dep", Document("alpha", "text", None), "dep")
+            with zipfile.ZipFile(root / "alpha.dep") as archive:
+                members = {name: archive.read(name).decode("utf-8") for name in archive.namelist()}
+            self.assertEqual(members, {"alpha.txt": "text", "alpha.brl": ""})
+
+            frame._write_export_document(root / "nested" / "alpha.brl", Document("alpha", "text", "⠁⠃"), "brl")
+            self.assertEqual((root / "nested" / "alpha.brl").read_bytes(), "⠁⠃".encode("utf-8"))
+
+            frame._write_export_document(root / "alpha.html", Document("alpha", "text", "b"), "html")
+            cached_html = render_dual_view_html(build_dual_view_model(results))
+            self.assertEqual((root / "alpha.html").read_bytes(), cached_html.encode("utf-8"))
+            self.assertIn('<span class="source">a</span>', cached_html)
+
+            frame._write_export_document(root / "beta.html", Document("beta", "text", "b"), "html")
+            empty_html = render_dual_view_html(build_dual_view_model(()))
+            self.assertEqual((root / "beta.html").read_bytes(), empty_html.encode("utf-8"))
+            self.assertNotEqual(cached_html, empty_html)
+
+            with self.assertRaises(OSError):
+                frame._write_export_document(root / "missing" / "alpha.html", Document("alpha", "text", "b"), "html")
+            self.assertFalse((root / "missing").exists())
+
+    def test_export_all_html_uses_each_document_cache(self) -> None:
+        frame = self._make_frame()
+        results = (
+            DualViewSegment(
+                result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
+                source_kind="text",
+            ),
+        )
+        frame._dual_view_results_by_document["alpha"] = results
+        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))
+        documents = [Document("alpha", "text", "a"), Document("beta", "text", "b")]
+
+        with tempfile.TemporaryDirectory() as directory:
+            root = Path(directory)
+            with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
+                frame._export_next_document(documents, root, "html", ExportBatchResult())
+
+            self.assertEqual(
+                (root / "alpha.html").read_text(encoding="utf-8"),
+                render_dual_view_html(build_dual_view_model(results)),
+            )
+            self.assertEqual(
+                (root / "beta.html").read_text(encoding="utf-8"),
+                render_dual_view_html(build_dual_view_model(())),
+            )
+        result = frame._show_export_all_result.call_args.args[0]
+        self.assertTrue(result.all_succeeded)
+
+    def test_ctrl_s_in_output_editor_exports_open_document_as_brl(self) -> None:
+        frame = self._make_frame()
+        steps = Mock()
+        frame._save_open_document_with_feedback = steps.save
+        steps.save.return_value = True
+        frame._export_document_with_dialog = steps.export
+        frame.output_txt = steps.output_txt
+        event = Mock()
+        event.GetKeyCode.return_value = 83
+        event.ControlDown.return_value = True
+
+        frame.on_output_text_key_down(event)
+
+        self.assertEqual(
+            steps.mock_calls,
+            [call.save(), call.export(frame._documents_by_name["alpha"], "brl"), call.output_txt.SetFocus()],
+        )
+        event.Skip.assert_not_called()
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them on the unchanged code.**

```bash
$PY -m unittest tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest -v 2>&1 | grep -E ' \.\.\. |^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (all pass; if one fails, the test is wrong about today's behavior, not the code):

```text
test_context_menu_on_item_selects_it_and_pops_up_below_it (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_context_menu_on_item_selects_it_and_pops_up_below_it) ... ok
test_ctrl_s_in_output_editor_exports_open_document_as_brl (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_ctrl_s_in_output_editor_exports_open_document_as_brl) ... ok
test_export_all_html_uses_each_document_cache (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_export_all_html_uses_each_document_cache) ... ok
test_export_dialog_corrects_only_a_wrong_extension (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_export_dialog_corrects_only_a_wrong_extension) ... ok
test_export_dialog_title_default_file_wildcard_and_style (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_export_dialog_title_default_file_wildcard_and_style) ... ok
test_file_menu_build_log (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_file_menu_build_log) ... ok
test_keyboard_context_menu_without_selection_clears_it (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_keyboard_context_menu_without_selection_clears_it) ... ok
test_menu_bar_menus_items_and_handlers (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_bar_menus_items_and_handlers) ... ok
test_menu_enabled_states_follow_selection_and_documents (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_enabled_states_follow_selection_and_documents) ... ok
test_menu_handlers_dispatch_to_frame_methods (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_handlers_dispatch_to_frame_methods) ... ok
test_real_writers_produce_today_bytes (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_real_writers_produce_today_bytes) ... ok
Ran 11 tests
OK
```

- [ ] **Step 3: Prove the log notices a wiring change, then undo it.**

```bash
sed -i 's/self.on_open_document, menu_items\["Open"\]/self.on_open_document, menu_items["Delete"]/' gui.py
$PY -m unittest tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^FAILED' | LC_ALL=C sort
git -C $REPO checkout -- client/gui.py
git -C $REPO status --short
```

Expected (five tests catch the wrong bind target; afterwards only the two test files are changed):

```text
FAIL: test_context_menu_on_item_selects_it_and_pops_up_below_it (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_context_menu_on_item_selects_it_and_pops_up_below_it)
FAIL: test_file_menu_build_log (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_file_menu_build_log)
FAIL: test_keyboard_context_menu_without_selection_clears_it (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_keyboard_context_menu_without_selection_clears_it)
FAIL: test_menu_bar_menus_items_and_handlers (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_bar_menus_items_and_handlers)
FAIL: test_menu_handlers_dispatch_to_frame_methods (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_handlers_dispatch_to_frame_methods)
FAILED (failures=5)
 M client/tests/test_gui_document_flows.py
?? client/tests/menu_recording.py
```

- [ ] **Step 4: Full-suite check.**

```bash
$T/tools/check_suite.sh 586 11
```

Expected:

```text
Ran 586 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (586)
new tests ok: 11 (expected 11)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/menu_recording.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
test: characterize document menu and export behavior

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
test: characterize document menu and export behavior
```

---

### Task 2: One writer contract with `ExportContext`

**Files:**
- Modify: `client/documents/formats.py` (`ExportContext`, `DocumentLoader`, `DocumentWriter`, descriptor field types, the three writers)
- Modify: `client/gui.py` (import; `_write_export_document`)
- Test: `client/tests/test_document_formats.py`, `client/tests/test_gui_document_flows.py`

**Interfaces:**
- Consumes: nothing from Task 1 except that the characterization tests must stay green.
- Produces: `documents.formats.ExportContext` (frozen dataclass, `dual_view_results: tuple[object, ...] = ()`); `DocumentLoader = Callable[[Path | str], "Document"]`; `DocumentWriter = Callable[[Path | str, "Document", ExportContext], Path]`; `_write_dep(path, document, context) -> Path`, `_write_brl(path, document, context) -> Path`, `_write_html(path, document, context) -> Path` (all three parameters required and positional-or-keyword). `gui._write_export_document(destination_path, document, format_key)` now calls `descriptor.writer(destination_path, document, ExportContext(dual_view_results=self._dual_view_results_by_document.get(document.name, ())))` for every format.

`Document` is imported only under `TYPE_CHECKING` (the runtime `formats` <-> `workspace` cycle stays as it is; the writers still import `documents.workspace` inside the function). `_write_html` still does not create parent directories; it now returns the `Path` instead of the character count (nobody reads it).

- [ ] **Step 1: Write the failing tests.** The HTML writer test passes an `ExportContext` as the third argument; new tests check the three-parameter signature, the `TypeError` for two arguments, the returned `Path`, that DEP/BRL ignore the context, and the `ExportContext` default. In `test_gui_document_flows`, the DEP writer test expects `ExportContext()`, a new sibling expects the cached results for DEP too, and the HTML test expects `ExportContext(dual_view_results=cached_results)`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_document_formats.py b/client/tests/test_document_formats.py
index 5d8cf3a..9b971ce 100644
--- a/client/tests/test_document_formats.py
+++ b/client/tests/test_document_formats.py
@@ -1,9 +1,17 @@
+import inspect
 import unittest
+import zipfile
 from pathlib import Path
 from tempfile import TemporaryDirectory
 from unittest.mock import Mock, patch
 
-from documents.formats import build_import_wildcard, get_exportable_formats, get_format, get_importable_formats
+from documents.formats import (
+    ExportContext,
+    build_import_wildcard,
+    get_exportable_formats,
+    get_format,
+    get_importable_formats,
+)
 from documents.workspace import Document
 from dual_view.model import DualViewSegment
 
@@ -49,12 +57,66 @@ class DocumentFormatsTest(unittest.TestCase):
                 get_format("html").writer(
                     destination,
                     document,
-                    dual_view_results=(DualViewSegment(result=Mock(raw=[], braille=[], raw_to_braille_pos=[]), source_kind="text"),),
+                    ExportContext(
+                        dual_view_results=(DualViewSegment(result=Mock(raw=[], braille=[], raw_to_braille_pos=[]), source_kind="text"),),
+                    ),
                 )
 
             self.assertEqual(destination.read_text(encoding="utf-8"), "雙視內容")
             render.assert_called_once()
 
+    def test_writers_take_path_document_and_context(self) -> None:
+        for descriptor in get_exportable_formats():
+            with self.subTest(format_key=descriptor.key):
+                parameters = list(inspect.signature(descriptor.writer).parameters.values())
+                self.assertEqual([parameter.name for parameter in parameters], ["path", "document", "context"])
+                self.assertTrue(
+                    all(parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for parameter in parameters)
+                )
+                self.assertTrue(all(parameter.default is inspect.Parameter.empty for parameter in parameters))
+                with TemporaryDirectory() as directory:
+                    with self.assertRaises(TypeError):
+                        descriptor.writer(Path(directory) / f"alpha{descriptor.extension}", Document("alpha", "t", "b"))
+
+    def test_writers_return_destination_path(self) -> None:
+        for descriptor in get_exportable_formats():
+            with self.subTest(format_key=descriptor.key):
+                with TemporaryDirectory() as directory:
+                    destination = Path(directory) / f"alpha{descriptor.extension}"
+                    written = descriptor.writer(str(destination), Document("alpha", "t", "b"), ExportContext())
+                    self.assertEqual(written, destination)
+                    self.assertIsInstance(written, Path)
+                    self.assertTrue(destination.is_file())
+
+    def test_dep_and_brl_writers_ignore_the_context(self) -> None:
+        context = ExportContext(
+            dual_view_results=(DualViewSegment(result=Mock(raw=[], braille=[], raw_to_braille_pos=[]), source_kind="text"),),
+        )
+        document = Document("alpha", "text", "\u2801")
+        with TemporaryDirectory() as directory:
+            root = Path(directory)
+            for key in ("dep", "brl"):
+                with self.subTest(format_key=key):
+                    writer = get_format(key).writer
+                    writer(root / "plain" / f"alpha.{key}", document, ExportContext())
+                    writer(root / "context" / f"alpha.{key}", document, context)
+                    if key == "dep":
+                        contents = []
+                        for folder in ("plain", "context"):
+                            with zipfile.ZipFile(root / folder / "alpha.dep") as archive:
+                                contents.append({name: archive.read(name) for name in archive.namelist()})
+                        self.assertEqual(contents[0], contents[1])
+                        self.assertEqual(contents[0], {"alpha.txt": b"text", "alpha.brl": "\u2801".encode("utf-8")})
+                    else:
+                        self.assertEqual(
+                            (root / "plain" / "alpha.brl").read_bytes(),
+                            (root / "context" / "alpha.brl").read_bytes(),
+                        )
+
+    def test_export_context_defaults_to_no_results(self) -> None:
+        self.assertEqual(ExportContext().dual_view_results, ())
+        self.assertEqual(ExportContext(), ExportContext(dual_view_results=()))
+
     def test_import_wildcard_matches_existing_order_and_text(self) -> None:
         self.assertEqual(
             build_import_wildcard(),
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 835e9fc..2fb4539 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -28,7 +28,7 @@ from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
-from documents.formats import get_format
+from documents.formats import ExportContext, get_format
 from dual_view.html import render_dual_view_html
 from dual_view.model import DualViewSegment, build_dual_view_model
 
@@ -79,7 +79,24 @@ class GuiDocumentFlowsTest(unittest.TestCase):
             frame._write_export_document(Path("/tmp/custom.dep"), document, "dep")
 
         get_format_mock.assert_called_once_with("dep")
-        writer.assert_called_once_with(Path("/tmp/custom.dep"), document)
+        writer.assert_called_once_with(Path("/tmp/custom.dep"), document, ExportContext())
+
+    def test_write_export_document_passes_cached_results_to_every_writer(self) -> None:
+        frame = self._make_frame()
+        document = Document("alpha", "text", "braille")
+        cached_results = (Mock(),)
+        frame._dual_view_results_by_document["alpha"] = cached_results
+        writer = Mock()
+        descriptor = replace(get_format("dep"), writer=writer)
+
+        with patch.object(gui, "get_format", return_value=descriptor):
+            frame._write_export_document(Path("/tmp/custom.dep"), document, "dep")
+
+        writer.assert_called_once_with(
+            Path("/tmp/custom.dep"),
+            document,
+            ExportContext(dual_view_results=cached_results),
+        )
 
     def test_write_html_export_document_passes_cached_dual_view_results(self) -> None:
         frame = self._make_frame()
@@ -95,7 +112,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         writer.assert_called_once_with(
             Path("/tmp/custom.html"),
             document,
-            dual_view_results=cached_results,
+            ExportContext(dual_view_results=cached_results),
         )
 
     def test_write_export_document_rejects_non_exportable_format(self) -> None:
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_document_formats tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected (both modules fail to import `ExportContext`):

```text
      1 ERROR: test_document_formats (unittest.loader._FailedTest.test_document_formats)
      1 ERROR: test_gui_document_flows (unittest.loader._FailedTest.test_gui_document_flows)
      1 FAILED (errors=2)
      1 ImportError: Failed to import test module: test_document_formats
      1 ImportError: Failed to import test module: test_gui_document_flows
      2 ImportError: cannot import name 'ExportContext' from 'documents.formats' (client/documents/formats.py)
      1 Ran 2 tests
```

- [ ] **Step 3: Implement the contract.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/formats.py b/client/documents/formats.py
index 40e7f8d..de6af2f 100644
--- a/client/documents/formats.py
+++ b/client/documents/formats.py
@@ -10,6 +10,7 @@ from dual_view.model import build_dual_view_model
 
 if TYPE_CHECKING:
     from documents.importers import ImportedDocument
+    from documents.workspace import Document
 
 
 DEP_EXTENSION = ".dep"
@@ -18,13 +19,24 @@ HTML_EXTENSION = ".html"
 ALL_SUPPORTED_FILTER_KEY = "all"
 
 
+@dataclass(frozen=True)
+class ExportContext:
+    """What an export writer may need besides the document itself."""
+
+    dual_view_results: tuple[object, ...] = ()
+
+
+DocumentLoader = Callable[[Path | str], "Document"]
+DocumentWriter = Callable[[Path | str, "Document", ExportContext], Path]
+
+
 @dataclass(frozen=True)
 class DocumentFormatDescriptor:
     key: str
     extension: str
     wildcard_label: str
-    loader: Callable[[Path | str], object] | None
-    writer: Callable[[Path | str, object], object] | None
+    loader: DocumentLoader | None
+    writer: DocumentWriter | None
     requires_braille: bool
     importable: bool
     exportable: bool
@@ -70,27 +82,26 @@ def _load_dep(path: Path | str) -> object:
     return load_document_package(path)
 
 
-def _write_dep(path: Path | str, document: object) -> object:
+def _write_dep(path: Path | str, document: Document, context: ExportContext) -> Path:
+    del context
     from documents.workspace import save_document_package
 
     return save_document_package(path, document, include_pending_metadata=False)
 
 
-def _write_brl(path: Path | str, document: object) -> object:
+def _write_brl(path: Path | str, document: Document, context: ExportContext) -> Path:
+    del context
     from documents.workspace import export_document_brl
 
     return export_document_brl(path, document)
 
 
-def _write_html(
-    path: Path | str,
-    document: object,
-    *,
-    dual_view_results: tuple[object, ...] = (),
-) -> object:
+def _write_html(path: Path | str, document: Document, context: ExportContext) -> Path:
     del document
-    html = render_dual_view_html(build_dual_view_model(dual_view_results))
-    return Path(path).write_text(html, encoding="utf-8")
+    destination = Path(path)
+    html = render_dual_view_html(build_dual_view_model(context.dual_view_results))
+    destination.write_text(html, encoding="utf-8")
+    return destination
 
 
 DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
diff --git a/client/gui.py b/client/gui.py
index eefdb51..774bb0c 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -27,7 +27,7 @@ from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
 from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
-from documents.formats import get_format
+from documents.formats import ExportContext, get_format
 from documents.session import (
     document_name_exists,
     get_adjacent_document_name,
@@ -1218,14 +1218,8 @@ class BrailleFrame(wx.Frame):
 		descriptor = get_format(format_key)
 		if not descriptor.exportable or descriptor.writer is None:
 			raise ValueError(f'Unsupported export format: "{format_key}".')
-		if descriptor.key == "html":
-			descriptor.writer(
-				destination_path,
-				document,
-				dual_view_results=self._dual_view_results_by_document.get(document.name, ()),
-			)
-			return
-		descriptor.writer(destination_path, document)
+		context = ExportContext(dual_view_results=self._dual_view_results_by_document.get(document.name, ()))
+		descriptor.writer(destination_path, document, context)
 
 	def _continue_single_export(self, document: Document, destination_path: Path, format_key: str) -> None:
 		try:
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the `"html"` grep.**

```bash
$PY -m unittest tests.test_document_formats tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 592 17
grep -n '"html"' gui.py
```

Expected (the one `"html"` left is the wildcard dict that Task 3 deletes):

```text
Ran 94 tests
OK
Ran 592 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (592)
new tests ok: 17 (expected 17)
696:			"html": self._get_html_wildcard,
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/formats.py client/gui.py client/tests/test_document_formats.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: give export writers one context contract

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: give export writers one context contract
```

---

### Task 3: Export wildcard and Export submenus from the registry

**Files:**
- Modify: `client/documents/formats.py` (import `N_`; descriptor fields `export_wildcard`, `export_label`; values for dep/brl/html; `build_export_wildcard`)
- Modify: `client/ui/action_menu.py` (`_EXPORT_FORMATS` from the registry)
- Modify: `client/gui.py` (delete `DEP_WILDCARD`, `BRL_WILDCARD`, `HTML_WILDCARD`, `_get_dep_wildcard`, `_get_brl_wildcard`, `_get_html_wildcard`, `_get_export_wildcard`; use `build_export_wildcard(descriptor, _)`)
- Test: `client/tests/test_document_formats.py`, `client/tests/test_action_menu.py`, `client/tests/test_gui_document_flows.py` (`test_dead_frame_helpers_are_removed` loses its two "still exists" lines: this task deliberately removes `gui.DEP_WILDCARD` and `BrailleFrame._get_brl_wildcard`)

**Interfaces:**
- Consumes: `DocumentFormatDescriptor` from Task 2.
- Produces: `DocumentFormatDescriptor.export_wildcard: str | None = None` and `.export_label: str | None = None` (the last two fields); values dep `N_("DotExpress files (*.dep)|*.dep")` / `N_("Package DEP")`, brl `N_("Braille files (*.brl)|*.brl")` / `N_("Braille BRL")`, html `"HTML files (*.html)|*.html"` (unmarked) / `N_("Dual View HTML")`, `None` for docx/epub/pdf/txt. `build_export_wildcard(descriptor, translate=lambda value: value) -> str` returns `translate(descriptor.export_wildcard)` and raises `ValueError('Unsupported export format: "<key>".')` when it is `None`. `ui.action_menu._EXPORT_FORMATS == (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`, built from `get_exportable_formats()`.

All five marked strings are already msgids (through the `gui` markers, which still exist), so the msgid set does not change in this task. The `ui/action_menu.py` -> `documents.formats` import is new and pure (`ui/import_dialog.py` already does the same).

- [ ] **Step 1: Write the failing tests** (registry invariant, export labels, the three wildcards with and without `translate`, the `txt` error, submenus follow the registry; and relax the two positive guard lines).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_action_menu.py b/client/tests/test_action_menu.py
index 1e244ae..76f0d87 100644
--- a/client/tests/test_action_menu.py
+++ b/client/tests/test_action_menu.py
@@ -1,5 +1,6 @@
 import unittest
 
+from documents.formats import get_exportable_formats
 from ui.action_menu import (
     get_document_menu_descriptors,
     get_document_menu_enabled_state,
@@ -18,6 +19,15 @@ class ActionMenuTest(unittest.TestCase):
                 self.assertEqual(item.action, action)
                 self.assertEqual(item.formats, expected_formats)
 
+    def test_export_submenus_follow_the_format_registry(self) -> None:
+        registry_formats = tuple((descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats())
+        submenus = [item for item in get_document_menu_descriptors() if item.kind == "submenu"]
+
+        self.assertEqual([item.action for item in submenus], ["export", "export_all"])
+        for item in submenus:
+            with self.subTest(action=item.action):
+                self.assertEqual(item.formats, registry_formats)
+
     def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=False, has_documents=False),
diff --git a/client/tests/test_document_formats.py b/client/tests/test_document_formats.py
index 9b971ce..d80f727 100644
--- a/client/tests/test_document_formats.py
+++ b/client/tests/test_document_formats.py
@@ -6,7 +6,9 @@ from tempfile import TemporaryDirectory
 from unittest.mock import Mock, patch
 
 from documents.formats import (
+    DOCUMENT_FORMATS,
     ExportContext,
+    build_export_wildcard,
     build_import_wildcard,
     get_exportable_formats,
     get_format,
@@ -113,6 +115,40 @@ class DocumentFormatsTest(unittest.TestCase):
                             (root / "context" / "alpha.brl").read_bytes(),
                         )
 
+    def test_export_fields_are_all_set_exactly_for_exportable_formats(self) -> None:
+        for descriptor in DOCUMENT_FORMATS:
+            with self.subTest(format_key=descriptor.key):
+                self.assertEqual(
+                    {
+                        descriptor.exportable,
+                        descriptor.writer is not None,
+                        descriptor.export_wildcard is not None,
+                        descriptor.export_label is not None,
+                    },
+                    {descriptor.exportable},
+                )
+
+    def test_export_labels_match_menu_text(self) -> None:
+        self.assertEqual(
+            [(descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats()],
+            [("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")],
+        )
+
+    def test_export_wildcard_is_the_single_format_save_filter(self) -> None:
+        expected = {
+            "dep": "DotExpress files (*.dep)|*.dep",
+            "brl": "Braille files (*.brl)|*.brl",
+            "html": "HTML files (*.html)|*.html",
+        }
+        for key, wildcard in expected.items():
+            with self.subTest(format_key=key):
+                self.assertEqual(build_export_wildcard(get_format(key)), wildcard)
+                self.assertEqual(build_export_wildcard(get_format(key), lambda value: f"T[{value}]"), f"T[{wildcard}]")
+
+    def test_export_wildcard_rejects_non_exportable_format(self) -> None:
+        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
+            build_export_wildcard(get_format("txt"))
+
     def test_export_context_defaults_to_no_results(self) -> None:
         self.assertEqual(ExportContext().dual_view_results, ())
         self.assertEqual(ExportContext(), ExportContext(dual_view_results=()))
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 2fb4539..41be69a 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1071,8 +1071,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         ):
             with self.subTest(frame_attribute=name):
                 self.assertFalse(hasattr(gui.BrailleFrame, name))
-        self.assertTrue(hasattr(gui, "DEP_WILDCARD"))
-        self.assertTrue(hasattr(gui.BrailleFrame, "_get_brl_wildcard"))
 
     def test_save_open_document_saves_prepared_document(self) -> None:
         frame = self._make_frame()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_document_formats tests.test_action_menu 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected:

```text
      1 AttributeError: 'DocumentFormatDescriptor' object has no attribute 'export_label'. Did you mean: 'exportable'?
      1 ERROR: test_document_formats (unittest.loader._FailedTest.test_document_formats)
      1 ERROR: test_export_submenus_follow_the_format_registry (tests.test_action_menu.ActionMenuTest.test_export_submenus_follow_the_format_registry)
      1 FAILED (errors=2)
      1 ImportError: Failed to import test module: test_document_formats
      1 ImportError: cannot import name 'build_export_wildcard' from 'documents.formats' (client/documents/formats.py)
      1 Ran 7 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/formats.py b/client/documents/formats.py
index de6af2f..6626560 100644
--- a/client/documents/formats.py
+++ b/client/documents/formats.py
@@ -7,6 +7,7 @@ from typing import TYPE_CHECKING
 
 from dual_view.html import render_dual_view_html
 from dual_view.model import build_dual_view_model
+from i18n import N_
 
 if TYPE_CHECKING:
     from documents.importers import ImportedDocument
@@ -40,6 +41,8 @@ class DocumentFormatDescriptor:
     requires_braille: bool
     importable: bool
     exportable: bool
+    export_wildcard: str | None = None
+    export_label: str | None = None
 
 
 def _load_imported_document(
@@ -114,6 +117,8 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
         requires_braille=False,
         importable=True,
         exportable=True,
+        export_wildcard=N_("DotExpress files (*.dep)|*.dep"),
+        export_label=N_("Package DEP"),
     ),
     DocumentFormatDescriptor(
         key="docx",
@@ -164,7 +169,10 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
         requires_braille=True,
         importable=False,
         exportable=True,
+        export_wildcard=N_("Braille files (*.brl)|*.brl"),
+        export_label=N_("Braille BRL"),
     ),
+    # "HTML" and the HTML save filter are not msgids; marking them would add new catalog entries.
     DocumentFormatDescriptor(
         key="html",
         extension=HTML_EXTENSION,
@@ -174,6 +182,8 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
         requires_braille=False,
         importable=False,
         exportable=True,
+        export_wildcard="HTML files (*.html)|*.html",
+        export_label=N_("Dual View HTML"),
     ),
 )
 
@@ -212,6 +222,12 @@ def build_import_wildcard(translate=lambda value: value) -> str:
     return "|".join(parts)
 
 
+def build_export_wildcard(descriptor: DocumentFormatDescriptor, translate=lambda value: value) -> str:
+    if descriptor.export_wildcard is None:
+        raise ValueError(f'Unsupported export format: "{descriptor.key}".')
+    return translate(descriptor.export_wildcard)
+
+
 def get_import_filter_labels() -> list[str]:
     return [descriptor.wildcard_label for descriptor in get_importable_formats()] + ["All Supported Files"]
 
diff --git a/client/gui.py b/client/gui.py
index 774bb0c..bbf85f1 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -27,7 +27,7 @@ from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
 from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
-from documents.formats import ExportContext, get_format
+from documents.formats import ExportContext, build_export_wildcard, get_format
 from documents.session import (
     document_name_exists,
     get_adjacent_document_name,
@@ -122,9 +122,6 @@ VIEW_SCHEMES = {
 		"foreground": wx.Colour(255, 255, 255),
 	},
 }
-DEP_WILDCARD = "DotExpress files (*.dep)|*.dep"
-BRL_WILDCARD = "Braille files (*.brl)|*.brl"
-HTML_WILDCARD = "HTML files (*.html)|*.html"
 
 logger = get_logger("dotexpress.gui", "gui.log")
 
@@ -588,9 +585,6 @@ class BrailleFrame(wx.Frame):
 			parent=parent or self,
 		)
 
-	def _get_dep_wildcard(self) -> str:
-		return _(DEP_WILDCARD)
-
 	def _get_document_names(self) -> list[str]:
 		return self._get_document_controller().document_names
 
@@ -683,19 +677,6 @@ class BrailleFrame(wx.Frame):
 		self.input_txt.SetInsertionPoint(0)
 		self.input_txt.ShowPosition(0)
 
-	def _get_brl_wildcard(self) -> str:
-		return _(BRL_WILDCARD)
-
-	def _get_html_wildcard(self) -> str:
-		return _(HTML_WILDCARD)
-
-	def _get_export_wildcard(self, format_key: str) -> str:
-		return {
-			"dep": self._get_dep_wildcard,
-			"brl": self._get_brl_wildcard,
-			"html": self._get_html_wildcard,
-		}[format_key.casefold()]()
-
 	def _build_conversion_request(self, raw_text: str, output_mode: str, width: int, dictionary_path: Path) -> ConversionRequest:
 		return ConversionRequest(
 			raw_text=raw_text,
@@ -730,7 +711,7 @@ class BrailleFrame(wx.Frame):
 	def _export_document_with_dialog(self, document: Document, format_key: str) -> None:
 		descriptor = get_format(format_key)
 		default_file = f"{document.name}{descriptor.extension}"
-		wildcard = self._get_export_wildcard(descriptor.key)
+		wildcard = build_export_wildcard(descriptor, _)
 		with wx.FileDialog(
 			self,
 			_("Export Document"),
diff --git a/client/ui/action_menu.py b/client/ui/action_menu.py
index 9c1e2b8..4ef8469 100644
--- a/client/ui/action_menu.py
+++ b/client/ui/action_menu.py
@@ -2,6 +2,8 @@ from __future__ import annotations
 
 from dataclasses import dataclass
 
+from documents.formats import get_exportable_formats
+
 
 @dataclass(frozen=True)
 class DocumentMenuItem:
@@ -11,6 +13,10 @@ class DocumentMenuItem:
     formats: tuple[tuple[str, str], ...] = ()
 
 
+_EXPORT_FORMATS: tuple[tuple[str, str], ...] = tuple(
+    (descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats()
+)
+
 DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
     DocumentMenuItem("command", "Open", "open"),
     DocumentMenuItem("command", "Delete", "delete"),
@@ -18,18 +24,8 @@ DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
     DocumentMenuItem("command", "Add", "add"),
     DocumentMenuItem("command", "Rename", "rename"),
     DocumentMenuItem("command", "Import", "import"),
-    DocumentMenuItem(
-        "submenu",
-        "Export",
-        "export",
-        (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")),
-    ),
-    DocumentMenuItem(
-        "submenu",
-        "Export All",
-        "export_all",
-        (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")),
-    ),
+    DocumentMenuItem("submenu", "Export", "export", _EXPORT_FORMATS),
+    DocumentMenuItem("submenu", "Export All", "export_all", _EXPORT_FORMATS),
 )
 
 
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the greps.**

```bash
$PY -m unittest tests.test_document_formats tests.test_action_menu tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 597 22
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json
grep -nE '"html"|_WILDCARD|_wildcard' gui.py
```

Expected (no `"html"` and no wildcard constant or method left in `gui.py`; only the registry-backed import and export wildcard builders remain):

```text
Ran 104 tests
OK
Ran 597 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (597)
new tests ok: 22 (expected 22)
source msgids: 357
pot msgids: 357
SOURCE == POT
SOURCE == SAVED
30:from documents.formats import ExportContext, build_export_wildcard, get_format
57:from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
714:		wildcard = build_export_wildcard(descriptor, _)
1069:			wildcard=build_import_wildcard(_),
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/formats.py client/ui/action_menu.py client/gui.py client/tests/test_document_formats.py client/tests/test_action_menu.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: derive export wildcards and submenus from the registry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: derive export wildcards and submenus from the registry
```

---

### Task 4: Key the document menu state by action

**Files:**
- Modify: `client/ui/action_menu.py` (`EnabledWhen`; `DocumentMenuItem.action` and `.enabled_when` required; descriptors built with keyword arguments; action-keyed `get_document_menu_enabled_state`)
- Modify: `client/gui.py` (`_append_document_menu_items` stores top-level items by `item.action`; `_bind_document_menu_handlers` looks them up by action; `_sync_document_menu_state` loops over actions)
- Test: `client/tests/test_action_menu.py`, `client/tests/test_gui_document_flows.py` (`test_sync_document_menu_state_before_document_list_exists` uses action keys)

**Interfaces:**
- Consumes: `_EXPORT_FORMATS` from Task 3.
- Produces: `EnabledWhen = Literal["always", "has_selection", "has_documents"]`; `DocumentMenuItem(kind: str, label: str, action: str, enabled_when: EnabledWhen, formats: tuple[tuple[str, str], ...] = ())`; `get_document_menu_enabled_state(*, has_selection: bool, has_documents: bool) -> dict[str, bool]` keyed by action, in descriptor order. `BrailleFrame._document_menu_items` is now keyed by action (`"open"`, `"delete"`, `"delete_all"`, `"add"`, `"rename"`, `"import"`, `"export"`, `"export_all"`).

`gui`'s binding moves to action keys in this same commit, so no commit mixes label and action keys. The label-keyed `menu_items["open"]` lookups are temporary; Task 5 deletes them.

- [ ] **Step 1: Write the failing tests** (the four enabled-state dicts become action-keyed with the same truth values; new: labels/actions/kinds in order, unique actions, the `enabled_when` rules, dict order equals descriptor order).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_action_menu.py b/client/tests/test_action_menu.py
index 76f0d87..964f8ac 100644
--- a/client/tests/test_action_menu.py
+++ b/client/tests/test_action_menu.py
@@ -28,18 +28,60 @@ class ActionMenuTest(unittest.TestCase):
             with self.subTest(action=item.action):
                 self.assertEqual(item.formats, registry_formats)
 
+    def test_document_menu_labels_and_actions_in_order(self) -> None:
+        self.assertEqual(
+            [(item.label, item.action, item.kind) for item in get_document_menu_descriptors()],
+            [
+                ("Open", "open", "command"),
+                ("Delete", "delete", "command"),
+                ("Delete All", "delete_all", "command"),
+                ("Add", "add", "command"),
+                ("Rename", "rename", "command"),
+                ("Import", "import", "command"),
+                ("Export", "export", "submenu"),
+                ("Export All", "export_all", "submenu"),
+            ],
+        )
+
+    def test_document_menu_actions_are_unique(self) -> None:
+        actions = [item.action for item in get_document_menu_descriptors()]
+        self.assertEqual(len(actions), len(set(actions)))
+        self.assertNotIn("", actions)
+
+    def test_document_menu_enabled_when_uses_known_rules(self) -> None:
+        self.assertEqual(
+            [(item.action, item.enabled_when) for item in get_document_menu_descriptors()],
+            [
+                ("open", "has_selection"),
+                ("delete", "has_selection"),
+                ("delete_all", "has_documents"),
+                ("add", "always"),
+                ("rename", "has_selection"),
+                ("import", "always"),
+                ("export", "has_selection"),
+                ("export_all", "has_documents"),
+            ],
+        )
+
+    def test_document_menu_enabled_state_follows_descriptor_order(self) -> None:
+        for has_selection in (False, True):
+            for has_documents in (False, True):
+                with self.subTest(has_selection=has_selection, has_documents=has_documents):
+                    state = get_document_menu_enabled_state(has_selection=has_selection, has_documents=has_documents)
+                    self.assertEqual(list(state), [item.action for item in get_document_menu_descriptors()])
+
     def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=False, has_documents=False),
             {
-                "Open": False,
-                "Delete": False,
-                "Delete All": False,
-                "Add": True,
-                "Rename": False,
-                "Import": True,
-                "Export": False,
-                "Export All": False,
+                "open": False,
+                "delete": False,
+                "delete_all": False,
+                "add": True,
+                "rename": False,
+                "import": True,
+                "export": False,
+                "export_all": False,
             },
         )
 
@@ -47,14 +89,14 @@ class ActionMenuTest(unittest.TestCase):
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=True, has_documents=True),
             {
-                "Open": True,
-                "Delete": True,
-                "Delete All": True,
-                "Add": True,
-                "Rename": True,
-                "Import": True,
-                "Export": True,
-                "Export All": True,
+                "open": True,
+                "delete": True,
+                "delete_all": True,
+                "add": True,
+                "rename": True,
+                "import": True,
+                "export": True,
+                "export_all": True,
             },
         )
 
@@ -62,14 +104,14 @@ class ActionMenuTest(unittest.TestCase):
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=True, has_documents=False),
             {
-                "Open": True,
-                "Delete": True,
-                "Delete All": False,
-                "Add": True,
-                "Rename": True,
-                "Import": True,
-                "Export": True,
-                "Export All": False,
+                "open": True,
+                "delete": True,
+                "delete_all": False,
+                "add": True,
+                "rename": True,
+                "import": True,
+                "export": True,
+                "export_all": False,
             },
         )
 
@@ -77,14 +119,14 @@ class ActionMenuTest(unittest.TestCase):
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=False, has_documents=True),
             {
-                "Open": False,
-                "Delete": False,
-                "Delete All": True,
-                "Add": True,
-                "Rename": False,
-                "Import": True,
-                "Export": False,
-                "Export All": True,
+                "open": False,
+                "delete": False,
+                "delete_all": True,
+                "add": True,
+                "rename": False,
+                "import": True,
+                "export": False,
+                "export_all": True,
             },
         )
 
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 41be69a..14e8f90 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -148,27 +148,27 @@ class GuiDocumentFlowsTest(unittest.TestCase):
     def test_sync_document_menu_state_before_document_list_exists(self) -> None:
         frame = self._make_frame()
         menu_items = {
-            "Open": Mock(),
-            "Delete": Mock(),
-            "Delete All": Mock(),
-            "Add": Mock(),
-            "Rename": Mock(),
-            "Import": Mock(),
-            "Export": Mock(),
-            "Export All": Mock(),
+            "open": Mock(),
+            "delete": Mock(),
+            "delete_all": Mock(),
+            "add": Mock(),
+            "rename": Mock(),
+            "import": Mock(),
+            "export": Mock(),
+            "export_all": Mock(),
         }
 
         frame._sync_document_menu_state(menu_items)
 
         self.assertNotIn("document_list", frame.__dict__)
-        menu_items["Open"].Enable.assert_called_once_with(False)
-        menu_items["Delete"].Enable.assert_called_once_with(False)
-        menu_items["Delete All"].Enable.assert_called_once_with(False)
-        menu_items["Add"].Enable.assert_called_once_with(True)
-        menu_items["Rename"].Enable.assert_called_once_with(False)
-        menu_items["Import"].Enable.assert_called_once_with(True)
-        menu_items["Export"].Enable.assert_called_once_with(False)
-        menu_items["Export All"].Enable.assert_called_once_with(False)
+        menu_items["open"].Enable.assert_called_once_with(False)
+        menu_items["delete"].Enable.assert_called_once_with(False)
+        menu_items["delete_all"].Enable.assert_called_once_with(False)
+        menu_items["add"].Enable.assert_called_once_with(True)
+        menu_items["rename"].Enable.assert_called_once_with(False)
+        menu_items["import"].Enable.assert_called_once_with(True)
+        menu_items["export"].Enable.assert_called_once_with(False)
+        menu_items["export_all"].Enable.assert_called_once_with(False)
 
     def test_open_dual_view_creates_refreshes_and_shows_viewer(self) -> None:
         frame = self._make_frame()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_action_menu tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
```

Expected:

```text
      1 ERROR: test_document_menu_enabled_when_uses_known_rules (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_when_uses_known_rules)
      1 FAIL: test_document_menu_enabled_state_follows_descriptor_order (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_follows_descriptor_order) (has_selection=False, has_documents=False)
      1 FAIL: test_document_menu_enabled_state_follows_descriptor_order (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_follows_descriptor_order) (has_selection=False, has_documents=True)
      1 FAIL: test_document_menu_enabled_state_follows_descriptor_order (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_follows_descriptor_order) (has_selection=True, has_documents=False)
      1 FAIL: test_document_menu_enabled_state_follows_descriptor_order (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_follows_descriptor_order) (has_selection=True, has_documents=True)
      1 FAIL: test_document_menu_enabled_state_with_documents_but_no_selection (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_with_documents_but_no_selection)
      1 FAIL: test_document_menu_enabled_state_with_selection_and_documents (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_with_selection_and_documents)
      1 FAIL: test_document_menu_enabled_state_with_selection_but_no_documents (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_with_selection_but_no_documents)
      1 FAIL: test_document_menu_enabled_state_without_selection_or_documents (tests.test_action_menu.ActionMenuTest.test_document_menu_enabled_state_without_selection_or_documents)
      1 FAIL: test_sync_document_menu_state_before_document_list_exists (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_sync_document_menu_state_before_document_list_exists)
      1 FAIL: test_sync_document_menu_state_before_document_list_exists (tests.test_gui_document_flows.GuiDocumentFlowsTest.test_sync_document_menu_state_before_document_list_exists)
      1 FAILED (failures=10, errors=1)
      1 Ran 92 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index bbf85f1..0b5aaa2 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -400,10 +400,10 @@ class BrailleFrame(wx.Frame):
 		submenu_items: dict[str, dict[str, wx.MenuItem]] = {}
 		for item in get_document_menu_descriptors():
 			if item.kind == "command":
-				menu_items[item.label] = menu.Append(wx.ID_ANY, _(item.label))
+				menu_items[item.action] = menu.Append(wx.ID_ANY, _(item.label))
 				continue
 			submenu = wx.Menu()
-			menu_items[item.label] = menu.AppendSubMenu(submenu, _(item.label))
+			menu_items[item.action] = menu.AppendSubMenu(submenu, _(item.label))
 			submenu_items[item.action] = {}
 			for format_key, format_label in item.formats:
 				submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
@@ -416,12 +416,12 @@ class BrailleFrame(wx.Frame):
 		menu_items: dict[str, wx.MenuItem],
 		submenu_items: dict[str, dict[str, wx.MenuItem]],
 	) -> None:
-		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["Open"])
-		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["Delete"])
-		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["Delete All"])
-		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["Add"])
-		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["Rename"])
-		menu.Bind(wx.EVT_MENU, self.on_import_document, menu_items["Import"])
+		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["open"])
+		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["delete"])
+		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["delete_all"])
+		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["add"])
+		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["rename"])
+		menu.Bind(wx.EVT_MENU, self.on_import_document, menu_items["import"])
 		for format_key, submenu_item in submenu_items.get("export", {}).items():
 			menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_document(fmt), submenu_item)
 		for format_key, submenu_item in submenu_items.get("export_all", {}).items():
@@ -436,8 +436,8 @@ class BrailleFrame(wx.Frame):
 			has_selection=selected_document is not None,
 			has_documents=bool(self.documents),
 		)
-		for label, enabled in menu_state.items():
-			menu_item = target_items.get(label)
+		for action, enabled in menu_state.items():
+			menu_item = target_items.get(action)
 			if menu_item is not None:
 				menu_item.Enable(enabled)
 
diff --git a/client/ui/action_menu.py b/client/ui/action_menu.py
index 4ef8469..77b43cb 100644
--- a/client/ui/action_menu.py
+++ b/client/ui/action_menu.py
@@ -1,15 +1,19 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+from typing import Literal
 
 from documents.formats import get_exportable_formats
 
+EnabledWhen = Literal["always", "has_selection", "has_documents"]
+
 
 @dataclass(frozen=True)
 class DocumentMenuItem:
     kind: str
     label: str
-    action: str = ""
+    action: str
+    enabled_when: EnabledWhen
     formats: tuple[tuple[str, str], ...] = ()
 
 
@@ -18,14 +22,26 @@ _EXPORT_FORMATS: tuple[tuple[str, str], ...] = tuple(
 )
 
 DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
-    DocumentMenuItem("command", "Open", "open"),
-    DocumentMenuItem("command", "Delete", "delete"),
-    DocumentMenuItem("command", "Delete All", "delete_all"),
-    DocumentMenuItem("command", "Add", "add"),
-    DocumentMenuItem("command", "Rename", "rename"),
-    DocumentMenuItem("command", "Import", "import"),
-    DocumentMenuItem("submenu", "Export", "export", _EXPORT_FORMATS),
-    DocumentMenuItem("submenu", "Export All", "export_all", _EXPORT_FORMATS),
+    DocumentMenuItem(kind="command", label="Open", action="open", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label="Delete", action="delete", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label="Delete All", action="delete_all", enabled_when="has_documents"),
+    DocumentMenuItem(kind="command", label="Add", action="add", enabled_when="always"),
+    DocumentMenuItem(kind="command", label="Rename", action="rename", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label="Import", action="import", enabled_when="always"),
+    DocumentMenuItem(
+        kind="submenu",
+        label="Export",
+        action="export",
+        enabled_when="has_selection",
+        formats=_EXPORT_FORMATS,
+    ),
+    DocumentMenuItem(
+        kind="submenu",
+        label="Export All",
+        action="export_all",
+        enabled_when="has_documents",
+        formats=_EXPORT_FORMATS,
+    ),
 )
 
 
@@ -34,13 +50,5 @@ def get_document_menu_descriptors() -> tuple[DocumentMenuItem, ...]:
 
 
 def get_document_menu_enabled_state(*, has_selection: bool, has_documents: bool) -> dict[str, bool]:
-    return {
-        "Open": has_selection,
-        "Delete": has_selection,
-        "Delete All": has_documents,
-        "Add": True,
-        "Rename": has_selection,
-        "Import": True,
-        "Export": has_selection,
-        "Export All": has_documents,
-    }
+    conditions = {"always": True, "has_selection": has_selection, "has_documents": has_documents}
+    return {item.action: conditions[item.enabled_when] for item in DOCUMENT_MENU_ITEMS}
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_action_menu tests.test_gui_document_flows tests.test_removed_dead_code 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 601 26
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json
```

Expected:

```text
Ran 97 tests
OK
Ran 601 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (601)
new tests ok: 26 (expected 26)
source msgids: 357
pot msgids: 357
SOURCE == POT
SOURCE == SAVED
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/ui/action_menu.py client/gui.py client/tests/test_action_menu.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: key document menu state by action

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: key document menu state by action
```

---

### Task 5: A wx-free menu builder for the File and context menus

**Files:**
- Create: `client/ui/menu_builder.py`
- Create: `client/tests/test_menu_builder.py`
- Modify: `client/gui.py` (import the builder; drop the `get_document_menu_descriptors` import; new `_document_menu_handlers()` and `_append_document_menu(menu)`; `_create_document_menu` and `on_document_context_menu` use them; `_sync_document_menu_state` calls `apply_document_menu_state`; delete `_append_document_menu_items` and `_bind_document_menu_handlers`)

**Interfaces:**
- Consumes: `DocumentMenuItem`, `get_document_menu_descriptors()` (Task 4); `tests/menu_recording.py` (Task 1).
- Produces:
  ```python
  def build_document_menu(
      menu,
      handlers: Mapping[str, Callable[..., None]],
      *,
      translate: Callable[[str], str],
      new_menu: Callable[[], object],
      menu_event: object,
      item_id: int,
      descriptors: Sequence[DocumentMenuItem] | None = None,   # default get_document_menu_descriptors()
  ) -> dict[str, object]   # top-level items (commands and AppendSubMenu results) keyed by action

  def apply_document_menu_state(items_by_action: Mapping[str, object], enabled_by_action: Mapping[str, bool]) -> None
  ```
  `build_document_menu` raises `ValueError` before any menu call when the handler keys differ from the descriptor actions; then appends in descriptor order (`menu.Append(item_id, translate(label))`; a submenu is `new_menu()`, `menu.AppendSubMenu(submenu, translate(label))`, then `submenu.Append(item_id, translate(format_label))` per format); then binds in descriptor order on the top-level `menu` (`menu.Bind(menu_event, handlers[action], item)` for commands; `lambda _event, key=format_key.casefold(), handler=handlers[action]: handler(key)` for format items). `apply_document_menu_state` calls `items_by_action[action].Enable(enabled)` in the given order (unknown action: `KeyError`). In `gui`: `_document_menu_handlers() -> dict[str, object]` (the 8 actions -> `self.on_open_document`, `self.on_delete_document`, `self.on_delete_all_documents`, `self.on_add_document`, `self.on_rename_document`, `self.on_import_document`, `self.on_export_document`, `self.on_export_all_documents`) and `_append_document_menu(menu) -> dict[str, wx.MenuItem]` (passes `translate=_`, `new_menu=wx.Menu`, `menu_event=wx.EVT_MENU`, `item_id=wx.ID_ANY`, read at call time).

The export submenu handlers are now the bound methods captured when the menu is built (today `self.on_export_document` is looked up when the event fires); production never replaces these methods, and the File menu is built once while the context menu is rebuilt for every popup. `ui/menu_builder.py` is first imported by `gui` inside `StubScope.loading()`; it imports neither wx nor gui, so StubScope eviction does not affect it (checked alone and in shuffled order in Task 7).

- [ ] **Step 1: Write the failing builder tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_menu_builder.py b/client/tests/test_menu_builder.py
new file mode 100644
index 0000000..b75ca04
--- /dev/null
+++ b/client/tests/test_menu_builder.py
@@ -0,0 +1,171 @@
+import ast
+import unittest
+from pathlib import Path
+from unittest.mock import Mock, call
+
+from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, RecordedItem, fake_translate
+from ui.action_menu import DocumentMenuItem, get_document_menu_descriptors
+from ui.menu_builder import apply_document_menu_state, build_document_menu
+
+MENU_BUILDER_PATH = Path(__file__).resolve().parents[1] / "ui" / "menu_builder.py"
+DOCUMENT_ACTIONS = ("open", "delete", "delete_all", "add", "rename", "import", "export", "export_all")
+
+
+class MenuBuilderTest(unittest.TestCase):
+    def _build(self, handlers, descriptors=None, recorder=None):
+        recorder = recorder or MenuRecorder()
+        menu = recorder.new_menu()
+        kwargs = {} if descriptors is None else {"descriptors": descriptors}
+        items = build_document_menu(
+            menu,
+            handlers,
+            translate=fake_translate,
+            new_menu=recorder.new_menu,
+            menu_event="EVT_MENU",
+            item_id=-1,
+            **kwargs,
+        )
+        return recorder, items
+
+    def _handlers(self):
+        calls = Mock()
+        return calls, {action: getattr(calls, action) for action in DOCUMENT_ACTIONS}
+
+    def test_default_descriptors_build_today_menu_log(self) -> None:
+        _calls, handlers = self._handlers()
+
+        recorder, _items = self._build(handlers)
+
+        self.assertEqual(recorder.log, DOCUMENT_MENU_BUILD_LOG)
+
+    def test_handlers_receive_event_or_casefolded_format_key(self) -> None:
+        calls, handlers = self._handlers()
+        recorder, _items = self._build(handlers)
+        event = object()
+        expected = [getattr(call, action)(event) for action in DOCUMENT_ACTIONS[:6]]
+        expected += [call.export(key) for key in ("dep", "brl", "html")]
+        expected += [call.export_all(key) for key in ("dep", "brl", "html")]
+
+        self.assertEqual(len(recorder.binds), len(expected))
+        for (menu_name, item_name, handler), expected_call in zip(recorder.binds, expected):
+            with self.subTest(item=item_name):
+                calls.reset_mock()
+                handler(event)
+                self.assertEqual(menu_name, "menu0")
+                self.assertEqual(calls.mock_calls, [expected_call])
+
+    def test_command_handlers_are_bound_as_given(self) -> None:
+        _calls, handlers = self._handlers()
+
+        recorder, _items = self._build(handlers)
+
+        self.assertEqual(
+            [handler for _menu, _item, handler in recorder.binds[:6]],
+            [handlers[action] for action in DOCUMENT_ACTIONS[:6]],
+        )
+
+    def test_returns_top_level_items_by_action(self) -> None:
+        _calls, handlers = self._handlers()
+
+        _recorder, items = self._build(handlers)
+
+        self.assertEqual(list(items), list(DOCUMENT_ACTIONS))
+        self.assertTrue(all(isinstance(item, RecordedItem) for item in items.values()))
+        self.assertEqual(
+            [item.name for item in items.values()],
+            [
+                "menu0:T[Open]",
+                "menu0:T[Delete]",
+                "menu0:T[Delete All]",
+                "menu0:T[Add]",
+                "menu0:T[Rename]",
+                "menu0:T[Import]",
+                "menu0:T[Export]",
+                "menu0:T[Export All]",
+            ],
+        )
+
+    def test_missing_handler_raises_before_any_menu_call(self) -> None:
+        recorder = MenuRecorder()
+        _calls, handlers = self._handlers()
+        del handlers["rename"]
+
+        with self.assertRaisesRegex(ValueError, r"missing \['rename'\], extra \[\]"):
+            self._build(handlers, recorder=recorder)
+
+        self.assertEqual(recorder.log, [("new", "menu0")])
+
+    def test_extra_handler_raises_before_any_menu_call(self) -> None:
+        recorder = MenuRecorder()
+        _calls, handlers = self._handlers()
+        handlers["print"] = Mock()
+
+        with self.assertRaisesRegex(ValueError, r"missing \[\], extra \['print'\]"):
+            self._build(handlers, recorder=recorder)
+
+        self.assertEqual(recorder.log, [("new", "menu0")])
+
+    def test_custom_descriptors_build_and_bind_in_order(self) -> None:
+        descriptors = (
+            DocumentMenuItem(kind="submenu", label="Save As", action="save_as", enabled_when="always", formats=(("TxT", "Text"),)),
+            DocumentMenuItem(kind="command", label="Close", action="close", enabled_when="has_selection"),
+        )
+        calls = Mock()
+        handlers = {"save_as": calls.save_as, "close": calls.close}
+
+        recorder, items = self._build(handlers, descriptors)
+
+        self.assertEqual(
+            recorder.log,
+            [
+                ("new", "menu0"),
+                ("new", "menu1"),
+                ("menu0", "AppendSubMenu", "menu1", "T[Save As]"),
+                ("menu1", "Append", -1, "T[Text]"),
+                ("menu0", "Append", -1, "T[Close]"),
+                ("menu0", "Bind", "EVT_MENU", "menu1:T[Text]"),
+                ("menu0", "Bind", "EVT_MENU", "menu0:T[Close]"),
+            ],
+        )
+        self.assertEqual(list(items), ["save_as", "close"])
+        recorder.binds[0][2]("event")
+        recorder.binds[1][2]("event")
+        self.assertEqual(calls.mock_calls, [call.save_as("txt"), call.close("event")])
+
+    def test_default_descriptors_are_the_action_menu_descriptors(self) -> None:
+        _calls, handlers = self._handlers()
+
+        default_recorder, _items = self._build(handlers)
+        explicit_recorder, _items = self._build(handlers, get_document_menu_descriptors())
+
+        self.assertEqual(default_recorder.log, explicit_recorder.log)
+
+    def test_apply_state_enables_in_given_order(self) -> None:
+        log = []
+        items = {name: RecordedItem(log, name) for name in ("a", "b", "c")}
+
+        apply_document_menu_state(items, {"c": True, "a": False})
+
+        self.assertEqual(log, [("Enable", "c", True), ("Enable", "a", False)])
+
+    def test_apply_state_rejects_unknown_action(self) -> None:
+        items = {"a": RecordedItem([], "a")}
+
+        with self.assertRaises(KeyError):
+            apply_document_menu_state(items, {"a": True, "missing": False})
+
+    def test_menu_builder_does_not_import_wx(self) -> None:
+        tree = ast.parse(MENU_BUILDER_PATH.read_text(encoding="utf-8"))
+        imported = set()
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Import):
+                imported.update(alias.name.split(".")[0] for alias in node.names)
+            elif isinstance(node, ast.ImportFrom) and node.module:
+                imported.add(node.module.split(".")[0])
+
+        self.assertNotIn("wx", imported)
+        self.assertNotIn("gui", imported)
+
+
+if __name__ == "__main__":
+    unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_menu_builder 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected:

```text
      1 ERROR: test_menu_builder (unittest.loader._FailedTest.test_menu_builder)
      1 FAILED (errors=1)
      1 ImportError: Failed to import test module: test_menu_builder
      1 ModuleNotFoundError: No module named 'ui.menu_builder'
      1 Ran 1 test
```

- [ ] **Step 3: Add the builder and route `gui` through it.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index 0b5aaa2..e33d5f5 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -50,11 +50,9 @@ from documents.workspace import (
 from documents.export_results import (
     ExportBatchResult,
 )
-from ui.action_menu import (
-    get_document_menu_enabled_state,
-    get_document_menu_descriptors,
-)
+from ui.action_menu import get_document_menu_enabled_state
 from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
+from ui.menu_builder import apply_document_menu_state, build_document_menu
 from config import (
 	DEFAULT_TRANSLATION_TABLES,
 	get_charset_maps,
@@ -387,45 +385,31 @@ class BrailleFrame(wx.Frame):
 
 	def _create_document_menu(self) -> tuple[wx.Menu, dict[str, wx.MenuItem]]:
 		menu = wx.Menu()
-		menu_items, submenu_items = self._append_document_menu_items(menu)
-		self._bind_document_menu_handlers(menu, menu_items, submenu_items)
+		menu_items = self._append_document_menu(menu)
 		self._sync_document_menu_state(menu_items)
 		return menu, menu_items
 
-	def _append_document_menu_items(
-		self,
-		menu: wx.Menu,
-	) -> tuple[dict[str, wx.MenuItem], dict[str, dict[str, wx.MenuItem]]]:
-		menu_items: dict[str, wx.MenuItem] = {}
-		submenu_items: dict[str, dict[str, wx.MenuItem]] = {}
-		for item in get_document_menu_descriptors():
-			if item.kind == "command":
-				menu_items[item.action] = menu.Append(wx.ID_ANY, _(item.label))
-				continue
-			submenu = wx.Menu()
-			menu_items[item.action] = menu.AppendSubMenu(submenu, _(item.label))
-			submenu_items[item.action] = {}
-			for format_key, format_label in item.formats:
-				submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
-				submenu_items[item.action][format_key.casefold()] = submenu_item
-		return menu_items, submenu_items
-
-	def _bind_document_menu_handlers(
-		self,
-		menu: wx.Menu,
-		menu_items: dict[str, wx.MenuItem],
-		submenu_items: dict[str, dict[str, wx.MenuItem]],
-	) -> None:
-		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["open"])
-		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["delete"])
-		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["delete_all"])
-		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["add"])
-		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["rename"])
-		menu.Bind(wx.EVT_MENU, self.on_import_document, menu_items["import"])
-		for format_key, submenu_item in submenu_items.get("export", {}).items():
-			menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_document(fmt), submenu_item)
-		for format_key, submenu_item in submenu_items.get("export_all", {}).items():
-			menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_all_documents(fmt), submenu_item)
+	def _document_menu_handlers(self) -> dict[str, object]:
+		return {
+			"open": self.on_open_document,
+			"delete": self.on_delete_document,
+			"delete_all": self.on_delete_all_documents,
+			"add": self.on_add_document,
+			"rename": self.on_rename_document,
+			"import": self.on_import_document,
+			"export": self.on_export_document,
+			"export_all": self.on_export_all_documents,
+		}
+
+	def _append_document_menu(self, menu: wx.Menu) -> dict[str, wx.MenuItem]:
+		return build_document_menu(
+			menu,
+			self._document_menu_handlers(),
+			translate=_,
+			new_menu=wx.Menu,
+			menu_event=wx.EVT_MENU,
+			item_id=wx.ID_ANY,
+		)
 
 	def _sync_document_menu_state(self, menu_items: dict[str, wx.MenuItem] | None = None) -> None:
 		target_items = menu_items if menu_items is not None else getattr(self, "_document_menu_items", None)
@@ -436,10 +420,7 @@ class BrailleFrame(wx.Frame):
 			has_selection=selected_document is not None,
 			has_documents=bool(self.documents),
 		)
-		for action, enabled in menu_state.items():
-			menu_item = target_items.get(action)
-			if menu_item is not None:
-				menu_item.Enable(enabled)
+		apply_document_menu_state(target_items, menu_state)
 
 	def _update_window_title(self) -> None:
 		self.SetTitle(_(format_window_title(self._open_document_name)))
@@ -934,8 +915,7 @@ class BrailleFrame(wx.Frame):
 			self._clear_document_selection()
 		rect = self.document_list.GetItemRect(item_index) if item_index != wx.NOT_FOUND and item_index < self.document_list.GetItemCount() else None
 		menu = wx.Menu()
-		menu_items, submenu_items = self._append_document_menu_items(menu)
-		self._bind_document_menu_handlers(menu, menu_items, submenu_items)
+		menu_items = self._append_document_menu(menu)
 		self._sync_document_menu_state(menu_items)
 		popup_position = (rect.x, rect.y + rect.height) if rect is not None else client_position
 		self.document_list.PopupMenu(menu, popup_position)
diff --git a/client/ui/menu_builder.py b/client/ui/menu_builder.py
new file mode 100644
index 0000000..610f744
--- /dev/null
+++ b/client/ui/menu_builder.py
@@ -0,0 +1,67 @@
+"""Build, bind and enable the document menu from its descriptors.
+
+This module does not import wx. The caller passes the wx pieces in
+(``new_menu=wx.Menu``, ``menu_event=wx.EVT_MENU``, ``item_id=wx.ID_ANY``),
+so tests can use recording fakes.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Callable, Mapping, Sequence
+
+from ui.action_menu import DocumentMenuItem, get_document_menu_descriptors
+
+
+def build_document_menu(
+    menu,
+    handlers: Mapping[str, Callable[..., None]],
+    *,
+    translate: Callable[[str], str],
+    new_menu: Callable[[], object],
+    menu_event: object,
+    item_id: int,
+    descriptors: Sequence[DocumentMenuItem] | None = None,
+) -> dict[str, object]:
+    """Append every descriptor to ``menu``, then bind every item on ``menu``.
+
+    Commands call ``handlers[action](event)``. Submenu format items call
+    ``handlers[action](format_key)`` with the casefolded format key. Returns the
+    top-level items (commands and submenus) keyed by action.
+    """
+    items = tuple(get_document_menu_descriptors() if descriptors is None else descriptors)
+    actions = [item.action for item in items]
+    missing = [action for action in actions if action not in handlers]
+    extra = sorted(set(handlers) - set(actions))
+    if missing or extra:
+        raise ValueError(f"Document menu handlers do not match the menu actions: missing {missing}, extra {extra}.")
+
+    top_items: dict[str, object] = {}
+    format_items: dict[str, list[tuple[str, object]]] = {}
+    for item in items:
+        if item.kind == "command":
+            top_items[item.action] = menu.Append(item_id, translate(item.label))
+            continue
+        submenu = new_menu()
+        top_items[item.action] = menu.AppendSubMenu(submenu, translate(item.label))
+        format_items[item.action] = [
+            (format_key.casefold(), submenu.Append(item_id, translate(format_label)))
+            for format_key, format_label in item.formats
+        ]
+
+    for item in items:
+        handler = handlers[item.action]
+        if item.kind == "command":
+            menu.Bind(menu_event, handler, top_items[item.action])
+            continue
+        for format_key, format_item in format_items[item.action]:
+            menu.Bind(menu_event, lambda _event, key=format_key, handler=handler: handler(key), format_item)
+    return top_items
+
+
+def apply_document_menu_state(
+    items_by_action: Mapping[str, object],
+    enabled_by_action: Mapping[str, bool],
+) -> None:
+    """Enable or disable each item, in the order of ``enabled_by_action``."""
+    for action, enabled in enabled_by_action.items():
+        items_by_action[action].Enable(enabled)
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the label-lookup grep.**

```bash
$PY -m unittest tests.test_menu_builder tests.test_gui_document_flows tests.test_action_menu 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_menu_builder 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 612 37
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json
grep -nE 'menu_items\["|"Delete All"|"Export All"|_append_document_menu_items|_bind_document_menu_handlers' gui.py
```

Expected (the only hits left are the two marker entries that Task 6 deletes):

```text
Ran 103 tests
OK
Ran 11 tests
OK
Ran 612 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (612)
new tests ok: 37 (expected 37)
source msgids: 357
pot msgids: 357
SOURCE == POT
SOURCE == SAVED
139:	N_("Export All"),
149:	N_("Delete All"),
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/ui/menu_builder.py client/tests/test_menu_builder.py client/gui.py
git -C $REPO commit -q -F - <<'MSG'
refactor: build document menus with a wx-free menu builder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: build document menus with a wx-free menu builder
```

---

### Task 6: Mark translatable labels where they are defined

**Files:**
- Modify: `client/documents/formats.py` (`ALL_SUPPORTED_FILES_LABEL = N_("All Supported Files")`, used by `build_import_wildcard` and `get_import_filter_labels`; `wildcard_label=N_(...)` for DEP, DOCX, EPUB, PDF, TXT, BRL; `"HTML"` stays unmarked)
- Modify: `client/ui/action_menu.py` (`from i18n import N_`; the 8 labels)
- Modify: `client/ui/translation_menu.py` (`from i18n import N_`; the 5 labels)
- Modify: `client/dialog.py` (`from i18n import N_, _`; `CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")`)
- Modify: `client/conversion/preprocessing/user_script.py` (`from i18n import N_`; the two `ValueError` messages)
- Modify: `client/gui.py` (delete `_MENU_TRANSLATION_MARKERS` and its comment; `from i18n import _, resource_path`)
- Test: `client/tests/test_document_formats.py`, `client/tests/test_action_menu.py`, `client/tests/test_i18n.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `documents.formats.ALL_SUPPORTED_FILES_LABEL == "All Supported Files"`. No value changes anywhere (`N_` returns its argument). Modules outside the UI import only `N_`, never `_`; `i18n` imports only the standard library, so there is no `config` import and no cycle.

This task deliberately changes what two P0 guards check, in the same commit: `SharedSetupConsumerTest` (`gui.py` imports `{"_", "resource_path"}`, `dialog.py` imports `{"N_", "_"}`) and the marker test (spec correction 1). `test_menu_labels_have_zh_tw_translations` and `test_former_marker_strings_are_still_extracted` pass before and after the implementation step: they are the guards that make deleting the marker tuple safe.

- [ ] **Step 1: Write the tests** (the zh_TW label test, `ALL_SUPPORTED_FILES_LABEL`, the two `SharedSetupConsumerTest` sets, and the marker-test replacement).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_action_menu.py b/client/tests/test_action_menu.py
index 964f8ac..517d659 100644
--- a/client/tests/test_action_menu.py
+++ b/client/tests/test_action_menu.py
@@ -1,10 +1,39 @@
+import ast
 import unittest
+from pathlib import Path
 
 from documents.formats import get_exportable_formats
 from ui.action_menu import (
     get_document_menu_descriptors,
     get_document_menu_enabled_state,
 )
+from ui.translation_menu import get_translation_menu_items
+
+ZH_TW_PO_PATH = Path(__file__).resolve().parents[1] / "locales" / "zh_TW" / "LC_MESSAGES" / "dotexpress.po"
+
+
+def read_po_translations(path: Path) -> dict[str, str]:
+    """msgid -> msgstr for the active entries of a .po file (comments and obsolete entries skipped)."""
+    translations: dict[str, str] = {}
+    msgid = None
+    msgstr = ""
+    field = None
+    for line in path.read_text(encoding="utf-8").splitlines():
+        if line.startswith("msgid "):
+            if msgid is not None:
+                translations[msgid] = msgstr
+            msgid, msgstr, field = ast.literal_eval(line[len("msgid "):]), "", "msgid"
+        elif line.startswith("msgstr "):
+            msgstr, field = ast.literal_eval(line[len("msgstr "):]), "msgstr"
+        elif line.startswith('"') and field == "msgid":
+            msgid += ast.literal_eval(line)
+        elif line.startswith('"') and field == "msgstr":
+            msgstr += ast.literal_eval(line)
+        else:
+            field = None
+    if msgid is not None:
+        translations[msgid] = msgstr
+    return translations
 
 
 class ActionMenuTest(unittest.TestCase):
@@ -70,6 +99,17 @@ class ActionMenuTest(unittest.TestCase):
                     state = get_document_menu_enabled_state(has_selection=has_selection, has_documents=has_documents)
                     self.assertEqual(list(state), [item.action for item in get_document_menu_descriptors()])
 
+    def test_menu_labels_have_zh_tw_translations(self) -> None:
+        translations = read_po_translations(ZH_TW_PO_PATH)
+        labels = [item.label for item in get_document_menu_descriptors()]
+        labels += [descriptor.export_label for descriptor in get_exportable_formats()]
+        labels += [label for _key, label in get_translation_menu_items()]
+
+        self.assertEqual(len(labels), 16)
+        for label in labels:
+            with self.subTest(label=label):
+                self.assertTrue(translations.get(label), f"{label!r} has no zh_TW translation")
+
     def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
         self.assertEqual(
             get_document_menu_enabled_state(has_selection=False, has_documents=False),
diff --git a/client/tests/test_document_formats.py b/client/tests/test_document_formats.py
index d80f727..1cb4479 100644
--- a/client/tests/test_document_formats.py
+++ b/client/tests/test_document_formats.py
@@ -6,12 +6,14 @@ from tempfile import TemporaryDirectory
 from unittest.mock import Mock, patch
 
 from documents.formats import (
+    ALL_SUPPORTED_FILES_LABEL,
     DOCUMENT_FORMATS,
     ExportContext,
     build_export_wildcard,
     build_import_wildcard,
     get_exportable_formats,
     get_format,
+    get_import_filter_labels,
     get_importable_formats,
 )
 from documents.workspace import Document
@@ -166,6 +168,11 @@ class DocumentFormatsTest(unittest.TestCase):
             ),
         )
 
+    def test_all_supported_files_label_is_the_last_import_filter_label(self) -> None:
+        self.assertEqual(ALL_SUPPORTED_FILES_LABEL, "All Supported Files")
+        self.assertEqual(get_import_filter_labels()[-1], ALL_SUPPORTED_FILES_LABEL)
+        self.assertEqual(get_import_filter_labels(), ["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"])
+
     def test_export_requires_braille_policy_matches_format(self) -> None:
         self.assertFalse(get_format("dep").requires_braille)
         self.assertTrue(get_format("brl").requires_braille)
diff --git a/client/tests/test_i18n.py b/client/tests/test_i18n.py
index 9198d25..6f54a00 100644
--- a/client/tests/test_i18n.py
+++ b/client/tests/test_i18n.py
@@ -112,7 +112,7 @@ class SharedSetupConsumerTest(unittest.TestCase):
         self.assertEqual(assigned & LEGACY_SETUP_GLOBALS, set(), f"{relative_path} still builds its own catalog")
 
     def test_dialog_uses_shared_i18n(self) -> None:
-        self.assert_uses_shared_i18n("dialog.py", {"_"})
+        self.assert_uses_shared_i18n("dialog.py", {"N_", "_"})
 
     def test_settings_dialogs_uses_shared_i18n(self) -> None:
         self.assert_uses_shared_i18n("settings/dialogs.py", {"_"})
@@ -124,7 +124,7 @@ class SharedSetupConsumerTest(unittest.TestCase):
         self.assert_uses_shared_i18n("about.py", {"_"})
 
     def test_gui_uses_shared_i18n(self) -> None:
-        self.assert_uses_shared_i18n("gui.py", {"N_", "_", "resource_path"})
+        self.assert_uses_shared_i18n("gui.py", {"_", "resource_path"})
 
 
 class DuplicateSetupGuardTest(unittest.TestCase):
@@ -151,19 +151,77 @@ class DuplicateSetupGuardTest(unittest.TestCase):
 
 
 class ExtractionMarkerTest(unittest.TestCase):
-    def test_gui_menu_translation_markers_use_n_(self) -> None:
-        tree = _module_tree("gui.py")
-        markers = [
-            node.value
-            for node in tree.body
-            if isinstance(node, ast.Assign)
-            and any(isinstance(target, ast.Name) and target.id == "_MENU_TRANSLATION_MARKERS" for target in node.targets)
-        ]
+    # The strings that the marker tuple in gui.py kept extractable before P1-2
+    # (its 48 entries minus the four import filters that nothing displays).
+    # Each one is now marked with _() or N_() where it is defined.
+    FORMER_MARKER_MSGIDS = (
+        "Add",
+        "Edit",
+        "Delete",
+        "Import",
+        "Export",
+        "Open",
+        "Dual View",
+        "Rename",
+        "Default",
+        "Braille Font",
+        "SimBraille",
+        "Export All",
+        "DEP",
+        "Package DEP",
+        "TXT",
+        "PDF",
+        "DOCX",
+        "EPUB",
+        "BRL",
+        "Braille BRL",
+        "Dual View HTML",
+        "Delete All",
+        "Translation",
+        "No conversion data is available for this document.",
+        "Convert",
+        "Settings",
+        "Dictionary Management...",
+        "Text Processing",
+        "Text Processing Python Code",
+        "Unable to open text processing script: {error}",
+        "Unable to save text processing script: {error}",
+        "Text processing failed: {error}",
+        "The script must define exactly one top-level synchronous main function.",
+        "main must define exactly one positional parameter and no other parameters.",
+        "Confirm Delete Dictionary",
+        "Do you want to delete dictionary \"{name}\"?",
+        "Rename Dictionary",
+        "Help",
+        "Coseeing Website",
+        "About DotExpress",
+        "CSV files (*.csv)|*.csv",
+        "DotExpress files (*.dep)|*.dep",
+        "Braille files (*.brl)|*.brl",
+        "All Supported Files",
+    )
 
-        self.assertEqual(len(markers), 1)
-        self.assertIsInstance(markers[0], ast.Tuple)
-        callees = [getattr(getattr(element, "func", None), "id", None) for element in markers[0].elts]
-        self.assertEqual(callees, ["N_"] * 48)
+    def test_former_marker_strings_are_still_extracted(self) -> None:
+        extracted = set()
+        for dirpath, dirnames, filenames in os.walk(CLIENT_ROOT):
+            dirnames[:] = [name for name in dirnames if name not in {"tests", ".venv", "__pycache__"}]
+            for filename in filenames:
+                if not filename.endswith(".py"):
+                    continue
+                path = Path(dirpath) / filename
+                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
+                    if (
+                        isinstance(node, ast.Call)
+                        and isinstance(node.func, ast.Name)
+                        and node.func.id in {"_", "N_"}
+                        and node.args
+                        and isinstance(node.args[0], ast.Constant)
+                        and isinstance(node.args[0].value, str)
+                    ):
+                        extracted.add(node.args[0].value)
+
+        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 44)
+        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])
 
     def test_generate_pot_extracts_n_keyword(self) -> None:
         script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")
PATCH
```

- [ ] **Step 2: Run them to see the right ones fail.**

```bash
$PY -m unittest tests.test_document_formats tests.test_action_menu tests.test_i18n 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected (`test_document_formats` cannot import `ALL_SUPPORTED_FILES_LABEL`; the two consumer tests fail on the import sets; everything else, including the two guard tests, passes):

```text
      1 AssertionError: Items in the first set but not the second:
      1 AssertionError: Items in the second set but not the first:
      1 ERROR: test_document_formats (unittest.loader._FailedTest.test_document_formats)
      1 FAIL: test_dialog_uses_shared_i18n (tests.test_i18n.SharedSetupConsumerTest.test_dialog_uses_shared_i18n)
      1 FAIL: test_gui_uses_shared_i18n (tests.test_i18n.SharedSetupConsumerTest.test_gui_uses_shared_i18n)
      1 FAILED (failures=2, errors=1)
      1 ImportError: Failed to import test module: test_document_formats
      1 ImportError: cannot import name 'ALL_SUPPORTED_FILES_LABEL' from 'documents.formats' (client/documents/formats.py)
      1 Ran 28 tests
```

- [ ] **Step 3: Mark the definitions and delete the marker tuple.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/preprocessing/user_script.py b/client/conversion/preprocessing/user_script.py
index 0190d2e..8842594 100644
--- a/client/conversion/preprocessing/user_script.py
+++ b/client/conversion/preprocessing/user_script.py
@@ -5,6 +5,8 @@ import os
 import tempfile
 from pathlib import Path
 
+from i18n import N_
+
 
 PREPROCESSING_FILENAME = "preprocessing.py"
 DEFAULT_PREPROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"
@@ -36,7 +38,7 @@ def validate_preprocessing_script(
         and node.name == "main"
     ]
     if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
-        raise ValueError("The script must define exactly one top-level synchronous main function.")
+        raise ValueError(N_("The script must define exactly one top-level synchronous main function."))
     arguments = main_definitions[0].args
     positional = [*arguments.posonlyargs, *arguments.args]
     if (
@@ -45,7 +47,7 @@ def validate_preprocessing_script(
         or arguments.vararg is not None
         or arguments.kwarg is not None
     ):
-        raise ValueError("main must define exactly one positional parameter and no other parameters.")
+        raise ValueError(N_("main must define exactly one positional parameter and no other parameters."))
 
 
 def save_preprocessing_script(path: Path | str, source: str) -> None:
diff --git a/client/dialog.py b/client/dialog.py
index 4e6d7c8..ae59b0c 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -23,9 +23,9 @@ from dictionaries.manager import (
 )
 from dictionaries.presenter import DictionaryManagementActions
 from documents.workspace import normalize_document_name
-from i18n import _
+from i18n import N_, _
 
-CSV_WILDCARD = "CSV files (*.csv)|*.csv"
+CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")
 
 
 def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
diff --git a/client/documents/formats.py b/client/documents/formats.py
index 6626560..2afa6c7 100644
--- a/client/documents/formats.py
+++ b/client/documents/formats.py
@@ -18,6 +18,7 @@ DEP_EXTENSION = ".dep"
 BRL_EXTENSION = ".brl"
 HTML_EXTENSION = ".html"
 ALL_SUPPORTED_FILTER_KEY = "all"
+ALL_SUPPORTED_FILES_LABEL = N_("All Supported Files")
 
 
 @dataclass(frozen=True)
@@ -111,7 +112,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="dep",
         extension=DEP_EXTENSION,
-        wildcard_label="DEP",
+        wildcard_label=N_("DEP"),
         loader=_load_dep,
         writer=_write_dep,
         requires_braille=False,
@@ -123,7 +124,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="docx",
         extension=".docx",
-        wildcard_label="DOCX",
+        wildcard_label=N_("DOCX"),
         loader=_load_docx,
         writer=None,
         requires_braille=False,
@@ -133,7 +134,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="epub",
         extension=".epub",
-        wildcard_label="EPUB",
+        wildcard_label=N_("EPUB"),
         loader=_load_epub,
         writer=None,
         requires_braille=False,
@@ -143,7 +144,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="pdf",
         extension=".pdf",
-        wildcard_label="PDF",
+        wildcard_label=N_("PDF"),
         loader=_load_pdf,
         writer=None,
         requires_braille=False,
@@ -153,7 +154,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="txt",
         extension=".txt",
-        wildcard_label="TXT",
+        wildcard_label=N_("TXT"),
         loader=_load_txt,
         writer=None,
         requires_braille=False,
@@ -163,7 +164,7 @@ DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
     DocumentFormatDescriptor(
         key="brl",
         extension=BRL_EXTENSION,
-        wildcard_label="BRL",
+        wildcard_label=N_("BRL"),
         loader=None,
         writer=_write_brl,
         requires_braille=True,
@@ -218,7 +219,7 @@ def build_import_wildcard(translate=lambda value: value) -> str:
             )
         )
     all_patterns = ";".join(f"*{descriptor.extension}" for descriptor in get_importable_formats())
-    parts.extend((f"{translate('All Supported Files')} ({all_patterns})", all_patterns))
+    parts.extend((f"{translate(ALL_SUPPORTED_FILES_LABEL)} ({all_patterns})", all_patterns))
     return "|".join(parts)
 
 
@@ -229,7 +230,7 @@ def build_export_wildcard(descriptor: DocumentFormatDescriptor, translate=lambda
 
 
 def get_import_filter_labels() -> list[str]:
-    return [descriptor.wildcard_label for descriptor in get_importable_formats()] + ["All Supported Files"]
+    return [descriptor.wildcard_label for descriptor in get_importable_formats()] + [ALL_SUPPORTED_FILES_LABEL]
 
 
 def get_format_keys(importable: bool | None = None) -> tuple[str, ...]:
diff --git a/client/gui.py b/client/gui.py
index e33d5f5..5ce5b2a 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -6,7 +6,7 @@ import webbrowser
 import wx
 
 import about
-from i18n import N_, _, resource_path
+from i18n import _, resource_path
 from app_paths import ApplicationDataError, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
@@ -123,58 +123,6 @@ VIEW_SCHEMES = {
 
 logger = get_logger("dotexpress.gui", "gui.log")
 
-# Keep dynamic context-menu labels discoverable to gettext extraction.
-_MENU_TRANSLATION_MARKERS = (
-	N_("Add"),
-	N_("Edit"),
-	N_("Delete"),
-	N_("Import"),
-	N_("Export"),
-	N_("Open"),
-	N_("Dual View"),
-	N_("Rename"),
-	N_("Default"),
-	N_("Braille Font"),
-	N_("SimBraille"),
-	N_("Export All"),
-	N_("DEP"),
-	N_("Package DEP"),
-	N_("TXT"),
-	N_("PDF"),
-	N_("DOCX"),
-	N_("EPUB"),
-	N_("BRL"),
-	N_("Braille BRL"),
-	N_("Dual View HTML"),
-	N_("Delete All"),
-	N_("Translation"),
-	N_("No conversion data is available for this document."),
-	N_("Convert"),
-	N_("Settings"),
-	N_("Dictionary Management..."),
-	N_("Text Processing"),
-	N_("Text Processing Python Code"),
-	N_("Unable to open text processing script: {error}"),
-	N_("Unable to save text processing script: {error}"),
-	N_("Text processing failed: {error}"),
-	N_("The script must define exactly one top-level synchronous main function."),
-	N_("main must define exactly one positional parameter and no other parameters."),
-	N_("Confirm Delete Dictionary"),
-	N_("Do you want to delete dictionary \"{name}\"?"),
-	N_("Rename Dictionary"),
-	N_("Help"),
-	N_("Coseeing Website"),
-	N_("About DotExpress"),
-	N_("CSV files (*.csv)|*.csv"),
-	N_("DotExpress files (*.dep)|*.dep"),
-	N_("Text files (*.txt)|*.txt"),
-	N_("PDF files (*.pdf)|*.pdf"),
-	N_("Word documents (*.docx)|*.docx"),
-	N_("EPUB books (*.epub)|*.epub"),
-	N_("Braille files (*.brl)|*.brl"),
-	N_("All Supported Files"),
-)
-
 
 class ConvertingDialog(wx.Dialog):
 	def __init__(self, parent: wx.Window):
diff --git a/client/ui/action_menu.py b/client/ui/action_menu.py
index 77b43cb..8f51e1f 100644
--- a/client/ui/action_menu.py
+++ b/client/ui/action_menu.py
@@ -4,6 +4,7 @@ from dataclasses import dataclass
 from typing import Literal
 
 from documents.formats import get_exportable_formats
+from i18n import N_
 
 EnabledWhen = Literal["always", "has_selection", "has_documents"]
 
@@ -22,22 +23,22 @@ _EXPORT_FORMATS: tuple[tuple[str, str], ...] = tuple(
 )
 
 DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
-    DocumentMenuItem(kind="command", label="Open", action="open", enabled_when="has_selection"),
-    DocumentMenuItem(kind="command", label="Delete", action="delete", enabled_when="has_selection"),
-    DocumentMenuItem(kind="command", label="Delete All", action="delete_all", enabled_when="has_documents"),
-    DocumentMenuItem(kind="command", label="Add", action="add", enabled_when="always"),
-    DocumentMenuItem(kind="command", label="Rename", action="rename", enabled_when="has_selection"),
-    DocumentMenuItem(kind="command", label="Import", action="import", enabled_when="always"),
+    DocumentMenuItem(kind="command", label=N_("Open"), action="open", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label=N_("Delete"), action="delete", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label=N_("Delete All"), action="delete_all", enabled_when="has_documents"),
+    DocumentMenuItem(kind="command", label=N_("Add"), action="add", enabled_when="always"),
+    DocumentMenuItem(kind="command", label=N_("Rename"), action="rename", enabled_when="has_selection"),
+    DocumentMenuItem(kind="command", label=N_("Import"), action="import", enabled_when="always"),
     DocumentMenuItem(
         kind="submenu",
-        label="Export",
+        label=N_("Export"),
         action="export",
         enabled_when="has_selection",
         formats=_EXPORT_FORMATS,
     ),
     DocumentMenuItem(
         kind="submenu",
-        label="Export All",
+        label=N_("Export All"),
         action="export_all",
         enabled_when="has_documents",
         formats=_EXPORT_FORMATS,
diff --git a/client/ui/translation_menu.py b/client/ui/translation_menu.py
index 896731d..2d23e16 100644
--- a/client/ui/translation_menu.py
+++ b/client/ui/translation_menu.py
@@ -1,11 +1,13 @@
 from __future__ import annotations
 
+from i18n import N_
+
 
 def get_translation_menu_items() -> list[tuple[str, str]]:
     return [
-        ("convert", "Convert"),
-        ("dual_view", "Dual View"),
-        ("text_processing", "Text Processing"),
-        ("dictionaries", "Dictionary Management..."),
-        ("settings", "Settings"),
+        ("convert", N_("Convert")),
+        ("dual_view", N_("Dual View")),
+        ("text_processing", N_("Text Processing")),
+        ("dictionaries", N_("Dictionary Management...")),
+        ("settings", N_("Settings")),
     ]
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_document_formats tests.test_action_menu tests.test_i18n tests.test_translation_menu tests.test_user_preprocessing_script tests.test_dictionary_management_dialog 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 614 40
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json; echo "scan exit: $?"
```

Expected (353 source msgids; the only differences, against the `.pot` and the saved baseline, are the four group C orphans; exit 1 is expected because of exactly those):

```text
Ran 83 tests
OK
Ran 614 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (614)
new tests ok: 40 (expected 40)
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
differs from saved: +[] -['EPUB books (*.epub)|*.epub', 'PDF files (*.pdf)|*.pdf', 'Text files (*.txt)|*.txt', 'Word documents (*.docx)|*.docx']
scan exit: 1
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/formats.py client/ui/action_menu.py client/ui/translation_menu.py client/dialog.py client/conversion/preprocessing/user_script.py client/gui.py client/tests/test_document_formats.py client/tests/test_action_menu.py client/tests/test_i18n.py
git -C $REPO commit -q -F - <<'MSG'
refactor: mark translatable labels where they are defined

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: mark translatable labels where they are defined
```

---

### Task 7: Final verification (spec acceptance criteria, no commit)

- [ ] **Step 1: Acceptance criteria 1-4 and 6 (greps and the untouched trees).**

```bash
echo AC1; grep -n '"html"' gui.py
echo AC2; grep -rnE '_MENU_TRANSLATION_MARKERS|DEP_WILDCARD|BRL_WILDCARD|HTML_WILDCARD|_get_export_wildcard|_get_(dep|brl|html)_wildcard|_append_document_menu_items|_bind_document_menu_handlers' $REPO/client --include='*.py'
echo AC3; grep -nE 'menu_items\["|"Delete All"|"Export All"' gui.py
echo AC4; grep -nE '\bN_\b' gui.py; grep -nE '^(import wx|from wx)' ui/menu_builder.py
echo AC6; git -C $REPO diff main --stat -- client/locales scripts
echo end
```

Expected (nothing between the labels):

```text
AC1
AC2
AC3
AC4
AC6
end
```

- [ ] **Step 2: Acceptance criterion 5 (msgid scan).**

```bash
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $SP/p12/base_msgids.json; echo "scan exit: $?"
```

Expected (353; exactly the four group C strings differ; any other line fails the criterion):

```text
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
differs from saved: +[] -['EPUB books (*.epub)|*.epub', 'PDF files (*.pdf)|*.pdf', 'Text files (*.txt)|*.txt', 'Word documents (*.docx)|*.docx']
scan exit: 1
```

- [ ] **Step 3: Acceptance criterion 7 (focused verification), and each new or touched module alone.**

```bash
$PY -m unittest tests.test_document_formats tests.test_action_menu tests.test_menu_builder tests.test_gui_document_flows tests.test_i18n tests.test_removed_dead_code tests.test_translation_menu tests.test_export_results tests.test_user_preprocessing_script tests.test_dictionary_management_dialog tests.test_wx_stub -v 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for m in test_menu_builder test_gui_document_flows test_action_menu test_document_formats test_i18n; do printf '%s: ' $m; $PY -m unittest tests.$m 2>&1 | tail -1; done
```

Expected:

```text
Ran 203 tests
OK
test_menu_builder: OK
test_gui_document_flows: OK
test_action_menu: OK
test_document_formats: OK
test_i18n: OK
```

- [ ] **Step 4: Acceptance criterion 8 (full suite).**

```bash
$T/tools/check_suite.sh 614 40
```

Expected (575 + 39 net new = 614; only the known P2-5 failure):

```text
Ran 614 tests
FAILED (failures=1, skipped=7)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (614)
new tests ok: 40 (expected 40)
```

- [ ] **Step 5: Acceptance criterion 9 (shuffled runs).**

```bash
for s in 1 2 3 4 5; do $PY -I $T/tools/shuffle_harness.py $s tests.test_menu_builder tests.test_gui_document_flows tests.test_action_menu tests.test_document_formats | head -1; done
for s in 1 2 3 4 5; do $PY -I $T/tools/shuffle_harness.py $s | grep -v '^order=' | sed -E 's/ \(test_conversion_service\.ConversionServiceTest\.[a-z_]+\)$//'; done
```

Expected (the four focused modules are clean in every order; the full runs show only the known set from Task 0: the P2-5 failure, or the 8 pre-existing `test_conversion_service` order errors):

```text
seed=1 ran=121 failures=0 errors=0 skipped=0
seed=2 ran=121 failures=0 errors=0 skipped=0
seed=3 ran=121 failures=0 errors=0 skipped=0
seed=4 ran=121 failures=0 errors=0 skipped=0
seed=5 ran=121 failures=0 errors=0 skipped=0
seed=1 ran=614 failures=1 errors=0 skipped=7
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
seed=2 ran=614 failures=0 errors=8 skipped=7
BAD test_conversion_uses_processed_text_for_translation_and_dual_view
BAD test_dual_view_segments_boundary_space_is_text
BAD test_dual_view_segments_exposes_math_source_kind
BAD test_dual_view_segments_exposes_text_source_kind
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
BAD test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment
BAD test_translate_with_language_merges_text_and_math_segments_in_order
BAD test_translate_with_language_passes_selected_math_braille_code
seed=3 ran=614 failures=1 errors=0 skipped=7
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
seed=4 ran=614 failures=1 errors=0 skipped=7
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
seed=5 ran=614 failures=0 errors=8 skipped=7
BAD test_conversion_uses_processed_text_for_translation_and_dual_view
BAD test_dual_view_segments_boundary_space_is_text
BAD test_dual_view_segments_exposes_math_source_kind
BAD test_dual_view_segments_exposes_text_source_kind
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
BAD test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment
BAD test_translate_with_language_merges_text_and_math_segments_in_order
BAD test_translate_with_language_passes_selected_math_braille_code
```

- [ ] **Step 6: The commits and the final tree.**

```bash
git -C $REPO log --format=%s main..HEAD
git -C $REPO diff main --stat -- client
sha256sum ui/menu_builder.py ui/action_menu.py documents/formats.py gui.py tests/menu_recording.py tests/test_menu_builder.py
```

Expected:

```text
refactor: mark translatable labels where they are defined
refactor: build document menus with a wx-free menu builder
refactor: key document menu state by action
refactor: derive export wildcards and submenus from the registry
refactor: give export writers one context contract
test: characterize document menu and export behavior
docs: plan export and menu contracts
docs: drop orphan import filter msgids from menu spec
docs: spec export and menu contracts
 client/conversion/preprocessing/user_script.py |   6 +-
 client/dialog.py                               |   4 +-
 client/documents/formats.py                    |  68 ++--
 client/gui.py                                  | 159 ++--------
 client/tests/menu_recording.py                 | 120 +++++++
 client/tests/test_action_menu.py               | 156 +++++++--
 client/tests/test_document_formats.py          | 109 ++++++-
 client/tests/test_gui_document_flows.py        | 420 +++++++++++++++++++++++--
 client/tests/test_i18n.py                      |  86 ++++-
 client/tests/test_menu_builder.py              | 171 ++++++++++
 client/ui/action_menu.py                       |  55 ++--
 client/ui/menu_builder.py                      |  67 ++++
 client/ui/translation_menu.py                  |  12 +-
 13 files changed, 1181 insertions(+), 252 deletions(-)
e81b60013e7f88b40ff2a43112afef0953f721fd7b75d957923e162dc3f6c48e  ui/menu_builder.py
fd0eca2cfce0f5eec29cb75365fc2747284835e45bd67c665b9f9cbcbbbf78a4  ui/action_menu.py
d961c28d62a4c6976b91d460793913f3fcc1ed6ff2012449be99c23f8482ff34  documents/formats.py
bcf805dac2c1be127a3780d4a87943c44675152a0c246191d36d6f41a3316eba  gui.py
75b697c1123de49b0cc0fa92c86f686937b019cc8ff88476747f891ff3d4737a  tests/menu_recording.py
4d335dcbe115d248b2f2ca9e65a0747f9ac9e4887bca737350e69615caa5193e  tests/test_menu_builder.py
```

- [ ] **Step 7: Report.** List the six commits, the commands above with their results, and the Windows verification debt below as not run.

## Windows verification debt (not possible on this Linux host)

- Screenshots of the File menu, the Export and Export All submenus, and the document-list context menu (on an item, and from the keyboard menu key with no item selected), before and after, in the shipped zh_TW UI, with no documents, with documents but no selection, and with a selection.
- Manually export each format (single and Export All) from a pre-change and a post-change build and compare: DEP zip members and contents, BRL bytes, HTML bytes. Ctrl+S in the output editor opens the BRL save dialog.
- Run `scripts\generate-pot.bat`; the regenerated `.pot` must have the baseline msgid set minus exactly the four orphan import filters (besides `#:` references and the creation date). Then `msgmerge` the zh_TW `.po` (the four become obsolete `#~` entries) and recompile the `.mo`.
