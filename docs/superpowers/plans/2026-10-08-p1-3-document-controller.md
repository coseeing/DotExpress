# Document Controller Adoption (P1-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DocumentController` becomes the only owner of document state, and a new wx-free `documents/workspace_service.py` (`DocumentWorkspaceService`) does every workspace disk operation of the document flows together with the matching controller update. `BrailleFrame` loses its four forwarding properties, the lazy `_get_document_controller()`, its one-line wrappers, `_persist_documents`, the `workspace_dir` attribute and the two `hasattr` init-order guards; it keeps the dialogs, confirmations, error boxes, list refreshes and editor updates. Every flow keeps its disk effects and their order, its dialogs and messages, its selection, focus and title results. No user-facing string changes; `client/locales/` and `scripts/` untouched. The known data-loss defects listed in the spec stay exactly as they are (pinned, not fixed).

**Architecture:** Characterization first (Task 1): 32 tests drive the real document flows of a stub frame against a real temporary workspace and a real `DocumentController`, with faults injected through the file system (a directory where a `.dep` should be). They pass on today's code and stay unchanged to the end, except for one helper line in Task 5. Tasks 2-7 are the spec's migration steps 2-7, one green commit each, red test first. Task 8 is the spec's acceptance run.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `tempfile`, `zipfile`, `ast`, `dataclasses`). wxPython is not installed; `gui` loads through the P0-4 `tests/wx_stub.py` scope that `tests/test_gui_document_flows.py` already uses.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-3-document-controller-design.md` (authoritative, commit `7b19da2`). The corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-3-document-controller`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (7, nothing else): `client/gui.py`, `client/documents/controller.py`, `client/documents/workspace_service.py` (new); tests `client/tests/test_gui_document_flows.py`, `client/tests/test_document_controller.py`, `client/tests/test_workspace_service.py` (new). Never touch `client/locales/`, `scripts/`, `client/documents/workspace.py`, `client/documents/session.py`, `client/tests/wx_stub.py`, `client/dialog.py`.
- Indentation per file, unchanged: TABS in `gui.py` (the 4-space continuation lines of its import block stay as they are); 4 spaces in `documents/controller.py`, the new `documents/workspace_service.py` and every test file.
- The patches carry the exact characters (tabs, context lines). Run every block as it is; do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes. Every `_("...")` literal stays in `gui.py` (two of them move into a `lambda` at the same call site). Do not edit `.po`/`.pot`/`.mo`.
- Out of scope, and must not change: the four known defects of the spec (case-only rename on case-insensitive file systems, Add with a case variant overwriting a package, a failed rename unlink leaving both packages, a Delete All rollback without a valid document creating no default document). Task 1 pins them where the platform allows.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run (see "Dry Run"). "Red" summaries strip the repo path, timings and object addresses and use `LC_ALL=C sort | uniq -c`, so order and counts are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p13impl
  export PYTHONDONTWRITEBYTECODE=1
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. `PYTHONDONTWRITEBYTECODE=1` keeps a stale `.pyc` from masking a same-size edit made within the same second (seen once in the dry run's mutation checks).
- Baseline (re-verified at `7b19da2`, the spec commit): `$PY -m unittest discover -s tests` gives `Ran 614 tests`, `FAILED (failures=1, skipped=7)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: acceptance criterion 3's grep cannot print nothing.** `load_workspace_documents` is a substring of `_load_workspace_documents_at_startup`, a method the spec itself keeps (and its caller in `_load_startup_documents`), so the spec's command prints two lines even after a correct migration. Task 8 uses word boundaries: `grep -nE '\b(save_document_package|load_workspace_documents|ensure_workspace_directory|document_package_path_for_name|batch_import_documents|prepare_document_for_save)\b|\.unlink\(' gui.py`. Same intent, and it still catches every direct call or import.
2. **Factual correction: `test_save_open_document_saves_prepared_document` must be rewritten in step 5, not step 7.** It patches `gui.save_document_package`; step 5 moves the save into the service, which calls `documents.workspace_service.save_document_package`, so from step 5 on the patch would not intercept the write and the test would fail (and write a real package into a relative directory). Task 5 rewrites it as the temporary-directory test the spec describes. `test_delete_all_partial_failure_...` does stay until Task 7, because Delete All moves only in step 7.
3. **Refinement (requested by the orchestrator): the platform-dependent known defects are pinned too, with skips.** Task 1 adds four tests beyond the spec's 28 cases: case-only rename and Add with a case variant, each once for a case-sensitive file system (Linux: runs) and once for a case-insensitive one (Windows, default macOS: skipped here). The case-insensitive pair pins known defects 1 and 2 exactly as they behave today (the document's package is deleted; `alpha.dep` is overwritten with `Alpha.*` members); a later fix task flips them. The file system is probed at run time (`<ws>/case-probe` vs `<ws>/CASE-PROBE`), not guessed from `sys.platform`. Consequence for acceptance criterion 10: on Linux the full suite reports `skipped=9` (the 7 Windows-only liblouis skips plus these 2), not `skipped=7`; on Windows the other two of the four would skip instead. Known defects 3 and 4 are platform-independent and are pinned by `test_rename_unlink_failure_leaves_both_packages_and_state` and `test_delete_all_failure_without_valid_document_clears_editors_only`.
4. **Refinement: the characterization fakes.** The frame gets `_FakeEditor`s (values, focus recorded) and a `_FakeDocumentList` (items and selection, so `_refresh_document_list` and the selection lookups run for real) instead of `Mock`s; `SetTitle`, `wx.MessageBox`, `DocumentNameDialog`, `InvalidWorkspaceFilesDialog`, `FileIssuesDialog` and `wx.FileDialog` append to one ordered `self.events` list, which replaces the spec's "shared `Mock` parent" with the same purpose (error box before the review dialog, title calls, focus calls). Error boxes are checked by caption, flags, parent, the template prefix and the failing package's file name (part of `str(exc)` on every platform; the full path is not, because Windows doubles backslashes in the message).
5. **Refinement: the characterization helper loses `frame.workspace_dir` in Task 5** in the same line that gains the service (`frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)`). From Task 5 on, `gui` must not read `workspace_dir`; on a stub frame a stray read would get a no-op function and fail loudly. That one line is the only change the 32 tests get (checked in Task 8).
6. **Refinement: a red test for every refactor step.** Steps 4-7 change no behavior, so their red tests pin the new wiring rather than new behavior: `DocumentControllerOwnershipTest` (Task 4: the controller exists before `_initialize_frame()` builds the menu bar; `_initialize_state` keeps it) and `FrameWorkspaceServiceDelegationTest` (Tasks 5-7: each flow hands its IO to the service with the right arguments and shows the service's result and errors through the same frame calls, with a `Mock` service). These are positive contract tests the P1-4 work can reuse, not absence guards (spec, P0 review M-2). No absence guard is added for `set_state` or the removed frame members; the Task 8 greps do that job.
7. **Refinement: `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` uses the spec's stub-service option.** A file-system fault cannot make `beta`'s unlink fail while `beta` reloads as a valid document (a directory package is invalid on reload), so the test keeps its scenario and assertions with a stub `delete_all_documents` that calls `on_error`, restores `[beta]` through the controller and returns `DeleteAllResult(completed=False, invalid_paths=[])`. It also checks the error box and the review call now. The real file-system rollback is covered by characterization test `test_delete_all_failure_reports_then_reloads_and_reviews` and the service tests.
8. **Refinement: the Delete All order check.** The spec's service test records "the directory listing inside the callback", which cannot tell "before the reload" from "after" because the reload does not change the disk. `test_delete_all_failure_reports_before_reload_and_restores_from_disk` also records the controller's names inside `on_error` (still the four original names, so the restore has not run), and `test_delete_all_reload_error_propagates_after_on_error` turns the workspace into a file inside `on_error`, so the reload fails only if it runs after the callback. Mutation-checked (see "Dry Run").
9. **Refinement: imports leave `gui` when they become unused,** not all in step 7: `document_name_exists` and `get_adjacent_document_name` in Task 4; `ensure_workspace_directory` and `prepare_document_for_save` in Task 5; `batch_import_documents` in Task 6; `document_package_path_for_name`, `load_workspace_documents` and `save_document_package` in Task 7. `get_workspace_directory` stays (tests patch it on `gui`). The only unused import left in `gui` is the pre-existing `ConversionStageError` (P1-4 territory, spec Out of Scope).
10. **Behavior notes, none user-visible.** `_save_open_document` now reads both editors even when no document is open (the service then does nothing). `document_name_at` returns `None` for every negative index, where today's `self.documents[selection]` would have wrapped for `-2` and below; `wx` only returns `-1` or a valid index. `load_documents` replaces the cache dict instead of clearing it in place (nothing else holds a reference).

Everything else in the spec was re-checked at `7b19da2`: the line numbers it cites in `gui.py` and `documents/controller.py`; the 22 `self.documents` reads; `set_state` has no callers; the 614/1/7 baseline; the focused four-module run (`Ran 120 tests`, OK); the msgid scan (353 source msgids, only the four known `.pot`-only orphans).

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `7b19da2` (`$SP/p13plan/dry`, never the repo), one commit per task; after each task the full suite and the msgid scan gave the counts below. The patches in this file are `git diff`s of those commits, split into the red test step and the implementation step. Mutation checks on the final dry tree (each applied alone, then undone): service save writing before the memory update, rename unlinking before writing, Delete All reloading before `on_error`, import listing save issues first, invalid-file deletion stopping at the first error, create adding before writing, a default document after a failed Delete All, a casefold duplicate check, and no default document after deleting the last document fail 2, 4, 2, 2, 2, 2, 2, 2 and 1 tests respectively. Then this file's blocks were extracted and run in order on two fresh clones (`$SP/p13plan/replay1`, `replay2`, each with a stand-in plan commit) by a harness that compares every "Expected" block with the real output: all 7 commits applied, every expected block matched byte for byte, and the resulting `client/` tree is identical to the dry clone. Final sha256: `client/gui.py` `61fa19ad33b235daff4edc1da32ebb064f0190a015b9963e50e8b3cc64206975`, `client/documents/controller.py` `9acb23dea7c7421b20008643feb7dffa2682a8e8cc35b710aadd933e063a6862`, `client/documents/workspace_service.py` `3dfc43238a15cbe312a3f8bb92f018a58a3ce879f812d5b62751a9e284fd21bd`.

## Review Focus

1. **Order of side effects.** Save updates memory before the write; rename writes the new package before it unlinks the old one; Delete All shows the error box before the reload (and the reload can itself raise afterwards); import lists load issues before save issues; invalid-file deletion continues after an error. Tests: characterization `test_save_failure_reports_error_after_updating_memory`, `test_rename_write_failure_keeps_old_package_and_state`, `test_rename_unlink_failure_leaves_both_packages_and_state`, `test_delete_all_failure_reports_then_reloads_and_reviews`, `test_import_reports_load_issues_before_save_issues`, `test_startup_invalid_file_delete_error_continues_with_next_file`; and the service tests `test_save_failure_propagates_after_memory_update`, `test_rename_write_failure_propagates_and_keeps_state`, `test_rename_unlink_failure_propagates_and_leaves_both_packages`, `test_delete_all_failure_reports_before_reload_and_restores_from_disk`, `test_delete_all_reload_error_propagates_after_on_error`, `test_import_files_lists_load_issues_before_save_issues`, `test_delete_invalid_files_reports_each_error_and_continues`.
2. **Init order and the first menu sync.** The controller is created in `__init__` before `_initialize_frame()`; `_sync_document_menu_state` lost its two `hasattr` guards but keeps the `document_list` check. Tests: `test_frame_creates_its_controller_before_building_the_menu_bar`, the P1-2 `test_file_menu_build_log` and `test_sync_document_menu_state_before_document_list_exists` (unchanged expected logs).
3. **Controller identity.** The frame creates the controller once; `_initialize_state` builds the service on that same object. Tests: `test_initialize_state_keeps_the_frame_controller`, `test_initialize_state_creates_service_for_frame_controller`.
4. **Known defects stay as they are.** The case-sensitive and case-insensitive rename/Add tests (two run here, two only on Windows/macOS), the rename-unlink and the Delete-All-rollback tests. A reviewer should reject any "fix" in this task.
5. **Stub masking.** Every frame helper sets `_document_controller` and (from Task 5) `_workspace_service` explicitly; assertions read real disk and controller state, so a missing object fails loudly.

## File Map

- Task 1: modify `client/tests/test_gui_document_flows.py` (imports; `_FakeEditor`, `_FakeDocumentList`, new class `DocumentWorkspaceFlowsCharacterizationTest` at the end).
- Task 2: modify `client/documents/controller.py`; test `client/tests/test_document_controller.py`.
- Task 3: create `client/documents/workspace_service.py`, `client/tests/test_workspace_service.py`.
- Task 4: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (setup moves to a real controller; new class `DocumentControllerOwnershipTest`).
- Task 5: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (new class `FrameWorkspaceServiceDelegationTest`; frame helpers get a service; save test rewritten; characterization helper line).
- Task 6: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py`.
- Task 7: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (Delete All test rewritten).

## Expected Counts

| After task | new test methods | `discover` `Ran` | new tests ok / skipped (suite check) | msgid scan |
| --- | --- | --- | --- | --- |
| baseline | - | 614 | 0 / 0 | 353, four `.pot`-only orphans, `SOURCE == SAVED` |
| 1 characterization | 32 | 646 | 30 / 2 | same |
| 2 controller methods | 10 | 656 | 40 / 2 | same |
| 3 workspace service | 25 | 681 | 65 / 2 | same |
| 4 frame on controller | 2 | 683 | 67 / 2 | same |
| 5 startup, save, create | 6 | 689 | 73 / 2 | same |
| 6 import | 1 | 690 | 74 / 2 | same |
| 7 rename, delete | 6 | 696 | 80 / 2 | same |

Every row after the baseline: `FAILED (failures=1, skipped=9)` (the P2-5 case) and `BASELINE-TESTS-IDENTICAL`. The two new skips are the case-insensitive file-system tests (on Linux). The rewritten `test_save_open_document_saves_prepared_document` (Task 5) and `test_delete_all_partial_failure_...` (Task 7) keep their names and pass, so they count as baseline lines.

## Throwaway Tooling (not committed)

All outside the repo (Task 0 creates `$T/tools/check_suite.sh`):

- `check_suite.sh <Ran> <new ok> <new skipped>`: full `discover -v`; every baseline test line must appear unchanged; counts the non-baseline lines by result.
- `$SP/p12/tools/msgid_scan.py`: the P0-5 AST stand-in for xgettext (source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`). Task 0 saves the starting msgid set to `$T/base_msgids.json`; every later scan compares with it.
- `$SP/shuffle_harness.py <seed> [modules]`: runs test modules in a seeded random order.

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
docs: plan document controller adoption
refactor/p1-3-document-controller
```

- [ ] **Step 2: Create the tool and record the baseline.**

```bash
mkdir -p $T/tools
cat > $T/tools/check_suite.sh <<'EOF'
#!/bin/bash
# Throwaway (P1-3). usage: check_suite.sh <expected Ran> <expected new ok> <expected new skipped>   (run from client/)
# Every baseline test line must still be present with the same result. "new" counts test lines
# that are not in the baseline, by result.
SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
T=${T:-$SP/p13impl}
PY=$SP/venv/bin/python
$PY -B -m unittest discover -s tests -v > $T/run.txt 2>&1
grep ' \.\.\. ' $T/run.txt | sort > $T/run_lines.txt
grep -E '^Ran|^FAILED|^OK' $T/run.txt | sed -E 's/ in [0-9.]+s$//'
grep -E '^(FAIL|ERROR):' $T/run.txt
missing=$(comm -23 $T/baseline_discover_verbose.txt $T/run_lines.txt)
[ -z "$missing" ] && echo "BASELINE-TESTS-IDENTICAL" || { echo "BASELINE-TESTS-CHANGED:"; echo "$missing"; }
grep -q "^Ran $1 tests" $T/run.txt && echo "RAN-COUNT-OK ($1)" || echo "RAN-COUNT-MISMATCH (expected $1)"
new=$(comm -13 $T/baseline_discover_verbose.txt $T/run_lines.txt)
echo "new tests ok: $(grep -c '\.\.\. ok$' <<< "$new") (expected $2)"
echo "new tests skipped: $(grep -c '\.\.\. skipped ' <<< "$new") (expected $3)"
EOF
chmod +x $T/tools/check_suite.sh
$PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | sort > $T/baseline_discover_verbose.txt
wc -l < $T/baseline_discover_verbose.txt
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | sed "s#$T#\$T#"
$PY -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for s in 1 2 3 4 5; do $PY -B -I $SP/shuffle_harness.py $s | head -1; done
```

Expected (614 test lines; the scan's exit status is 1 because of the four known `.pot`-only orphans; the focused set is the spec's 120; seeds 2 and 5 show the pre-existing `test_conversion_service` order pollution, refinement 8 of the P1-1 plan, out of scope):

```text
614
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
saved $T/base_msgids.json
Ran 120 tests
OK
seed=1 ran=614 failures=1 errors=0 skipped=7
seed=2 ran=614 failures=0 errors=8 skipped=7
seed=3 ran=614 failures=1 errors=0 skipped=7
seed=4 ran=614 failures=1 errors=0 skipped=7
seed=5 ran=614 failures=0 errors=8 skipped=7
```

---

### Task 1: Characterize the document workspace flows (spec step 1)

**Files:**
- Modify: `client/tests/test_gui_document_flows.py` (imports `DocumentController`, `load_document_package`, `save_document_package`; new module-level fakes `_FakeEditor`, `_FakeDocumentList`; new class `DocumentWorkspaceFlowsCharacterizationTest` at the end)

**Interfaces:**
- Consumes: today's frame methods `on_add_document`, `on_rename_document`, `on_delete_document`, `on_delete_all_documents`, `on_import_document`, `on_document_selection_changed`, `_ensure_open_document_exists`, `_load_workspace_documents_at_startup`, `_save_open_document_with_feedback`, `_on_close`. Patches `gui.wx.MessageBox`, `gui.wx.FileDialog`, `gui.DocumentNameDialog`, `gui.InvalidWorkspaceFilesDialog`, `gui.FileIssuesDialog`.
- Produces: `_make_workspace_frame(documents=(), open_name=None, selected_name=None)` (sets `frame._document_controller = DocumentController(...)` and, until Task 5, `frame.workspace_dir`); `_write_packages(*documents)`; `_block(name)` (a non-empty directory at `<ws>/<name>.dep`: writing and unlinking it raise `OSError`, loading it reports it invalid); `_listing()`, `_package(name)`, `_members(name)`, `_state(frame)` (`(documents, open_name, selected_name, cache)` read from the controller's attributes, which exist before and after); `self.events` (ordered: `("MessageBox", message, caption, style, parent)`, `("DocumentNameDialog", title, initial_name)`, `("InvalidWorkspaceFilesDialog", paths)`, `("FileIssuesDialog", title, message, lines)`, `("FileDialog", title, style)`, `("title", text)`, `("focus", "input")`); queues `self.answers` (MessageBox return values) and `self.names` (dialog names; `None` cancels).

The 32 tests (spec cases in brackets): Add [1-3], default document [4], startup [5-7], save [8-9], close [10], rename [11-15], four case-sensitivity tests (refinement 3), delete [16-20], Delete All [21-24], import [25-27], selection [28]. They run on the unchanged code and must pass immediately: their expected values are what the app does today. They stay byte-identical through Task 7 except the one helper line of Task 5; if one fails in a later task, the refactor changed behavior. Fix the code, not the test.

- [ ] **Step 1: Add the characterization tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 14e8f90..1e4088e 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -23,7 +23,8 @@ with _SCOPE.loading():
 setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
 
-from documents.workspace import Document
+from documents.controller import DocumentController
+from documents.workspace import Document, load_document_package, save_document_package
 from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
@@ -1598,5 +1599,818 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         )
         event.Skip.assert_not_called()
 
+
+class _FakeEditor:
+    def __init__(self, name: str, events: list, value: str = ""):
+        self.name = name
+        self.events = events
+        self.value = value
+
+    def SetValue(self, value: str) -> None:
+        self.value = value
+
+    def GetValue(self) -> str:
+        return self.value
+
+    def SetFocus(self) -> None:
+        self.events.append(("focus", self.name))
+
+    def SetInsertionPoint(self, _position: int) -> None:
+        pass
+
+    def ShowPosition(self, _position: int) -> None:
+        pass
+
+
+class _FakeDocumentList:
+    def __init__(self, names: list[str], selected_index: int):
+        self.items = list(names)
+        self.selected = selected_index
+
+    def DeleteAllItems(self) -> None:
+        self.items = []
+        self.selected = gui.wx.NOT_FOUND
+
+    def InsertItem(self, index: int, label: str) -> None:
+        self.items.insert(index, label)
+
+    def GetItemCount(self) -> int:
+        return len(self.items)
+
+    def Select(self, index: int, on: int = 1) -> None:
+        self.selected = index if on else gui.wx.NOT_FOUND
+
+    def Focus(self, _index: int) -> None:
+        pass
+
+    def GetFirstSelected(self) -> int:
+        return self.selected
+
+
+class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
+    """Pins today's document flows: disk effects, dialogs, state; must pass unchanged through P1-3.
+
+    Faults come from the file system: a directory at ``<ws>/<name>.dep`` makes the package
+    write and the unlink fail with an ``OSError`` and is loaded as an invalid package.
+    """
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name)
+        self.workspace = self.root / "workspace"
+        self.events: list = []
+        self.answers: list = []
+        self.names: list = []
+        self.delete_invalid = False
+        self.import_paths: list[str] = []
+        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
+        for patcher in (
+            patch.object(gui.wx, "MessageBox", self._message_box),
+            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
+            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
+            patch.object(gui, "FileIssuesDialog", self._issues_dialog_class()),
+            patch.object(gui.wx, "FileDialog", self._import_dialog_class()),
+        ):
+            patcher.start()
+            self.addCleanup(patcher.stop)
+
+    # --- fakes -------------------------------------------------------------
+
+    def _message_box(self, message, caption, style, parent=None):
+        self.events.append(("MessageBox", message, caption, style, parent))
+        return self.answers.pop(0) if self.answers else gui.wx.OK
+
+    def _name_dialog_class(self):
+        test = self
+
+        class FakeDocumentNameDialog:
+            def __init__(self, parent, title, initial_name=""):
+                test.events.append(("DocumentNameDialog", title, initial_name))
+                self.name = test.names.pop(0)
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.ID_OK if self.name is not None else gui.wx.CANCEL
+
+            def get_document_name(self):
+                return self.name
+
+        return FakeDocumentNameDialog
+
+    def _invalid_files_dialog_class(self):
+        test = self
+
+        class FakeInvalidWorkspaceFilesDialog:
+            def __init__(self, parent, invalid_paths):
+                test.events.append(("InvalidWorkspaceFilesDialog", list(invalid_paths)))
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.ID_OK
+
+            def should_delete_invalid_files(self):
+                return test.delete_invalid
+
+        return FakeInvalidWorkspaceFilesDialog
+
+    def _issues_dialog_class(self):
+        test = self
+
+        class FakeFileIssuesDialog:
+            def __init__(self, parent, title, message, issues):
+                test.events.append(("FileIssuesDialog", title, message, list(issues)))
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.ID_OK
+
+        return FakeFileIssuesDialog
+
+    def _import_dialog_class(self):
+        test = self
+
+        class FakeImportDialog:
+            def __init__(self, parent, title, wildcard="", style=0):
+                test.events.append(("FileDialog", title, style))
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def SetFilterIndex(self, index):
+                pass
+
+            def ShowModal(self):
+                return gui.wx.ID_OK
+
+            def GetFilterIndex(self):
+                return test.import_filter_index
+
+            def GetPaths(self):
+                return list(test.import_paths)
+
+        return FakeImportDialog
+
+    # --- helpers -----------------------------------------------------------
+
+    def _make_workspace_frame(self, documents=(), open_name=None, selected_name=None) -> gui.BrailleFrame:
+        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
+        documents = list(documents)
+        frame._document_controller = DocumentController(
+            documents=documents,
+            open_name=open_name,
+            selected_name=selected_name,
+        )
+        frame.workspace_dir = self.workspace
+        open_document = next((document for document in documents if document.name == open_name), None)
+        frame.input_txt = _FakeEditor("input", self.events, open_document.text if open_document else "")
+        frame.output_txt = _FakeEditor("output", self.events, (open_document.braille or "") if open_document else "")
+        names = [document.name for document in documents]
+        frame.document_list = _FakeDocumentList(
+            names,
+            names.index(selected_name) if selected_name in names else gui.wx.NOT_FOUND,
+        )
+        frame.SetTitle = lambda title: self.events.append(("title", title))
+        frame._dual_view_frame = None
+        frame._document_menu_items = {}
+        frame._conversion_runner = Mock()
+        frame._conversion_runner.is_running.return_value = False
+        frame._close_converting_dialog = Mock()
+        return frame
+
+    def _write_packages(self, *documents: Document) -> None:
+        for document in documents:
+            save_document_package(self.workspace / f"{document.name}.dep", document)
+
+    def _block(self, name: str) -> Path:
+        """Make ``<ws>/<name>.dep`` a non-empty directory: writes and unlinks of it fail."""
+        path = self.workspace / f"{name}.dep"
+        (path / "keep").mkdir(parents=True)
+        return path
+
+    def _listing(self) -> list[str]:
+        return sorted(path.name for path in self.workspace.iterdir())
+
+    def _package(self, name: str) -> Document:
+        return load_document_package(self.workspace / f"{name}.dep")
+
+    def _members(self, name: str) -> list[str]:
+        with zipfile.ZipFile(self.workspace / f"{name}.dep") as archive:
+            return sorted(archive.namelist())
+
+    def _state(self, frame) -> tuple:
+        controller = frame._document_controller
+        return (
+            list(controller.documents),
+            controller.open_name,
+            controller.selected_name,
+            dict(controller.dual_view_results_by_document),
+        )
+
+    def _assert_error_box(self, event, template: str, path_name: str, frame) -> None:
+        kind, message, caption, style, parent = event
+        self.assertEqual(kind, "MessageBox")
+        self.assertTrue(message.startswith(gui._(template).partition("{error}")[0]), message)
+        self.assertIn(path_name, message)
+        self.assertEqual(caption, gui._("Error"))
+        self.assertEqual(style, gui.wx.OK | gui.wx.ICON_ERROR)
+        self.assertIs(parent, frame)
+
+    def _confirm(self, message: str, title: str, frame) -> tuple:
+        return (
+            "MessageBox",
+            message,
+            title,
+            gui.wx.YES_NO | gui.wx.NO_DEFAULT | gui.wx.ICON_WARNING,
+            frame,
+        )
+
+    def _skip_unless_case_sensitive(self, sensitive: bool) -> None:
+        self.workspace.mkdir(parents=True, exist_ok=True)
+        probe = self.workspace / "case-probe"
+        probe.write_text("", encoding="utf-8")
+        is_sensitive = not (self.workspace / "CASE-PROBE").exists()
+        probe.unlink()
+        if is_sensitive != sensitive:
+            self.skipTest("needs a case-%s file system" % ("sensitive" if sensitive else "insensitive"))
+
+    # --- Add and default document ------------------------------------------
+
+    def test_add_saves_open_document_then_creates_and_opens_new_document(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        frame.input_txt.SetValue("a edited")
+        self.names = ["beta"]
+
+        frame.on_add_document(None)
+
+        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))
+        self.assertEqual(self._package("beta"), Document("beta", "", ""))
+        self.assertEqual(self._members("beta"), ["beta.brl", "beta.txt"])
+        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
+        self.assertEqual(frame._document_controller.open_name, "beta")
+        self.assertEqual(frame._document_controller.selected_name, "beta")
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))
+        self.assertEqual(frame.document_list.items, ["alpha", "beta"])
+        self.assertEqual(frame.document_list.selected, 1)
+        self.assertEqual(
+            self.events,
+            [("DocumentNameDialog", gui._("Add Document"), ""), ("title", "beta - DotExpress")],
+        )
+
+    def test_add_duplicate_name_reprompts_with_that_name(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.names = ["alpha", "beta"]
+
+        frame.on_add_document(None)
+
+        self.assertEqual(
+            self.events[:3],
+            [
+                ("DocumentNameDialog", gui._("Add Document"), ""),
+                (
+                    "MessageBox",
+                    gui._('Document "{name}" already exists.').format(name="alpha"),
+                    gui._("Error"),
+                    gui.wx.OK | gui.wx.ICON_ERROR,
+                    frame,
+                ),
+                ("DocumentNameDialog", gui._("Add Document"), "alpha"),
+            ],
+        )
+        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
+
+    def test_add_write_failure_shows_error_and_keeps_state(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        self._block("beta")
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        before = self._state(frame)
+        self.names = ["beta"]
+
+        frame.on_add_document(None)
+
+        self.assertEqual(len(self.events), 2)
+        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
+        self.assertEqual(self._state(frame), before)
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
+
+    def test_default_document_is_pending_opened_and_focused(self) -> None:
+        frame = self._make_workspace_frame()
+
+        frame._ensure_open_document_exists()
+
+        self.assertEqual(self._listing(), ["new.dep"])
+        self.assertEqual(self._package("new"), Document("new", "", None))
+        self.assertEqual(self._members("new"), ["new.brl", "new.meta.json", "new.txt"])
+        self.assertEqual(frame._document_controller.document_names, ["new"])
+        self.assertEqual(frame._document_controller.open_name, "new")
+        self.assertEqual(self.events, [("title", "new - DotExpress"), ("focus", "input")])
+
+    # --- startup -----------------------------------------------------------
+
+    def test_startup_with_missing_workspace_creates_it_and_default_document(self) -> None:
+        frame = self._make_workspace_frame()
+
+        frame._load_workspace_documents_at_startup()
+
+        self.assertEqual(self._listing(), ["new.dep"])
+        self.assertEqual(frame._document_controller.document_names, ["new"])
+        self.assertEqual(frame._document_controller.open_name, "new")
+        self.assertEqual(
+            self.events,
+            [("title", "new - DotExpress"), ("focus", "input"), ("title", "new - DotExpress")],
+        )
+
+    def test_startup_reviews_invalid_packages_and_opens_first_valid_one(self) -> None:
+        self._write_packages(Document("good", "g", "1"))
+        (self.workspace / "bad.dep").write_bytes(b"not a zip")
+        self.delete_invalid = True
+        frame = self._make_workspace_frame()
+
+        frame._load_workspace_documents_at_startup()
+
+        self.assertEqual(
+            self.events,
+            [
+                ("InvalidWorkspaceFilesDialog", [self.workspace / "bad.dep"]),
+                ("title", "good - DotExpress"),
+                ("title", "good - DotExpress"),
+            ],
+        )
+        self.assertEqual(self._listing(), ["good.dep"])
+        self.assertEqual(frame._document_controller.document_names, ["good"])
+        self.assertEqual(frame._document_controller.open_name, "good")
+        self.assertEqual(frame.input_txt.value, "g")
+
+    def test_startup_invalid_file_delete_error_continues_with_next_file(self) -> None:
+        self._block("a-blocked")
+        (self.workspace / "b-corrupt.dep").write_bytes(b"not a zip")
+        self._write_packages(Document("good", "g", "1"))
+        self.delete_invalid = True
+        frame = self._make_workspace_frame()
+
+        frame._load_workspace_documents_at_startup()
+
+        self.assertEqual(
+            self.events[0],
+            ("InvalidWorkspaceFilesDialog", [self.workspace / "a-blocked.dep", self.workspace / "b-corrupt.dep"]),
+        )
+        self._assert_error_box(self.events[1], "Failed to delete invalid workspace file: {error}", "a-blocked.dep", frame)
+        self.assertEqual(self.events[2:], [("title", "good - DotExpress"), ("title", "good - DotExpress")])
+        self.assertEqual(self._listing(), ["a-blocked.dep", "good.dep"])
+
+    # --- save --------------------------------------------------------------
+
+    def test_save_open_document_keeps_pending_document_pending(self) -> None:
+        alpha = Document("alpha", "a", None)
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        frame.input_txt.SetValue("edited")
+        frame.output_txt.SetValue("ignored braille")
+
+        self.assertTrue(frame._save_open_document_with_feedback())
+
+        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", None)])
+        self.assertEqual(self._package("alpha"), Document("alpha", "edited", None))
+        self.assertIn("alpha.meta.json", self._members("alpha"))
+        self.assertEqual(self.events, [])
+
+    def test_save_failure_reports_error_after_updating_memory(self) -> None:
+        self._block("alpha")
+        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        frame.input_txt.SetValue("edited")
+        frame.output_txt.SetValue("edited braille")
+
+        self.assertFalse(frame._save_open_document_with_feedback())
+
+        self.assertEqual(len(self.events), 1)
+        self._assert_error_box(self.events[0], "Failed to save document: {error}", "alpha.dep", frame)
+        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", "edited braille")])
+
+    def test_close_vetoes_when_save_fails(self) -> None:
+        self._block("alpha")
+        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        event = Mock()
+        event.CanVeto.return_value = True
+
+        frame._on_close(event)
+
+        event.Veto.assert_called_once_with()
+        event.Skip.assert_not_called()
+        frame._close_converting_dialog.assert_not_called()
+
+    # --- rename ------------------------------------------------------------
+
+    def test_rename_writes_new_package_deletes_old_and_moves_state(self) -> None:
+        alpha = Document("alpha", "a", None)
+        beta = Document("beta", "b", "2")
+        self._write_packages(alpha, beta)
+        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="alpha")
+        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",), "beta": ("seg-b",)})
+        self.names = ["gamma"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "a", None))
+        self.assertIn("gamma.meta.json", self._members("gamma"))
+        self.assertEqual(
+            self._state(frame),
+            (
+                [Document("beta", "b", "2"), Document("gamma", "a", None)],
+                "gamma",
+                "gamma",
+                {"gamma": ("seg-a",), "beta": ("seg-b",)},
+            ),
+        )
+        self.assertEqual(frame.document_list.items, ["beta", "gamma"])
+        self.assertEqual(frame.document_list.selected, 1)
+        self.assertEqual(
+            self.events,
+            [("DocumentNameDialog", gui._("Rename Document"), "alpha"), ("title", "gamma - DotExpress")],
+        )
+
+    def test_rename_with_missing_old_package_writes_new_one(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        beta = Document("beta", "b", "2")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
+        self.names = ["gamma"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "b", "2"))
+        self.assertEqual(frame._document_controller.document_names, ["alpha", "gamma"])
+        self.assertEqual(frame._document_controller.open_name, "alpha")
+        self.assertEqual(frame._document_controller.selected_name, "gamma")
+
+    def test_rename_write_failure_keeps_old_package_and_state(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        self._block("gamma")
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        before = self._state(frame)
+        self.names = ["gamma"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(len(self.events), 2)
+        self._assert_error_box(self.events[1], "Failed to save document: {error}", "gamma.dep", frame)
+        self.assertEqual(self._package("alpha"), alpha)
+        self.assertEqual(self._state(frame), before)
+
+    def test_rename_unlink_failure_leaves_both_packages_and_state(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        beta = Document("beta", "b", "2")
+        self._write_packages(alpha)
+        self._block("beta")
+        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
+        before = self._state(frame)
+        self.names = ["gamma"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(len(self.events), 2)
+        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep", "gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "b", "2"))
+        self.assertEqual(self._state(frame), before)
+
+    def test_rename_cancelled_or_unchanged_does_nothing(self) -> None:
+        for answer in (None, "alpha"):
+            with self.subTest(answer=answer):
+                self.events.clear()
+                alpha = Document("alpha", "a", "1")
+                self._write_packages(alpha)
+                frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+                before = self._state(frame)
+                self.names = [answer]
+
+                frame.on_rename_document(None)
+
+                self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "alpha")])
+                self.assertEqual(self._listing(), ["alpha.dep"])
+                self.assertEqual(self._state(frame), before)
+
+    def test_case_only_rename_on_case_sensitive_file_system(self) -> None:
+        self._skip_unless_case_sensitive(True)
+        alpha = Document("Alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="Alpha", selected_name="Alpha")
+        self.names = ["alpha"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
+        self.assertEqual(frame._document_controller.document_names, ["alpha"])
+
+    def test_case_only_rename_on_case_insensitive_file_system_deletes_package(self) -> None:
+        # Known defect 1 of the P1-3 spec, pinned as it is today: the new package
+        # is the old file, so the unlink that follows removes the document.
+        self._skip_unless_case_sensitive(False)
+        alpha = Document("Alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="Alpha", selected_name="Alpha")
+        self.names = ["alpha"]
+
+        frame.on_rename_document(None)
+
+        self.assertEqual(self._listing(), [])
+        self.assertEqual(frame._document_controller.document_names, ["alpha"])
+        self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "Alpha"), ("title", "alpha - DotExpress")])
+
+    def test_add_case_variant_on_case_sensitive_file_system(self) -> None:
+        self._skip_unless_case_sensitive(True)
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.names = ["Alpha"]
+
+        frame.on_add_document(None)
+
+        self.assertEqual(self._listing(), ["Alpha.dep", "alpha.dep"])
+        self.assertEqual(self._package("alpha"), alpha)
+        self.assertEqual(frame._document_controller.document_names, ["Alpha", "alpha"])
+
+    def test_add_case_variant_on_case_insensitive_file_system_overwrites_package(self) -> None:
+        # Known defect 2 of the P1-3 spec, pinned as it is today: the case-sensitive
+        # duplicate check accepts "Alpha", and its package replaces alpha's.
+        self._skip_unless_case_sensitive(False)
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.names = ["Alpha"]
+
+        frame.on_add_document(None)
+
+        self.assertEqual([name.casefold() for name in self._listing()], ["alpha.dep"])
+        self.assertEqual(self._members(self._listing()[0][: -len(".dep")]), ["Alpha.brl", "Alpha.txt"])
+        self.assertEqual(frame._document_controller.document_names, ["Alpha", "alpha"])
+
+    # --- delete ------------------------------------------------------------
+
+    def test_delete_open_middle_document_opens_previous_neighbour(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("gamma", "c", "3")]
+        self._write_packages(*documents)
+        frame = self._make_workspace_frame(documents, open_name="beta", selected_name="beta")
+        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",), "beta": ("seg-b",)})
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_document(None)
+
+        self.assertEqual(
+            self.events,
+            [
+                self._confirm(
+                    gui._('Do you want to delete document "{name}"?').format(name="beta"),
+                    gui._("Confirm Delete Document"),
+                    frame,
+                ),
+                ("title", "alpha - DotExpress"),
+            ],
+        )
+        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
+        self.assertEqual(
+            self._state(frame),
+            ([documents[0], documents[2]], "alpha", "alpha", {"alpha": ("seg-a",)}),
+        )
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
+
+    def test_delete_selected_document_that_is_not_open_keeps_editors(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write_packages(*documents)
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="beta")
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_document(None)
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._state(frame), ([documents[0]], "alpha", "alpha", {}))
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
+        self.assertEqual(len(self.events), 1)
+
+    def test_delete_last_document_creates_default_document(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_document(None)
+
+        self.assertEqual(self._listing(), ["new.dep"])
+        self.assertEqual(self._package("new"), Document("new", "", None))
+        self.assertEqual(self._state(frame), ([Document("new", "", None)], "new", "new", {}))
+        self.assertEqual(
+            self.events[1:],
+            [("title", "DotExpress"), ("title", "new - DotExpress"), ("focus", "input")],
+        )
+
+    def test_delete_answered_no_changes_nothing(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        before = self._state(frame)
+        self.answers = [gui.wx.NO]
+
+        frame.on_delete_document(None)
+
+        self.assertEqual(len(self.events), 1)
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._state(frame), before)
+
+    def test_delete_unlink_failure_shows_error_and_keeps_state(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write_packages(documents[0])
+        self._block("beta")
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="beta")
+        before = self._state(frame)
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_document(None)
+
+        self.assertEqual(len(self.events), 2)
+        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
+        self.assertEqual(self._state(frame), before)
+
+    # --- Delete All --------------------------------------------------------
+
+    def test_delete_all_success_removes_packages_and_creates_default_document(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write_packages(*documents)
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
+        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",)})
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_all_documents(None)
+
+        self.assertEqual(
+            self.events,
+            [
+                self._confirm(
+                    gui._("Delete All will remove all documents. Do you want to continue?"),
+                    gui._("Confirm Delete All"),
+                    frame,
+                ),
+                ("title", "DotExpress"),
+                ("title", "new - DotExpress"),
+                ("focus", "input"),
+            ],
+        )
+        self.assertEqual(self._listing(), ["new.dep"])
+        self.assertEqual(self._state(frame), ([Document("new", "", None)], "new", "new", {}))
+
+    def test_delete_all_failure_reports_then_reloads_and_reviews(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("gamma", "c", "3")]
+        self._write_packages(documents[0], documents[2])
+        self._block("beta")
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
+        frame._document_controller.dual_view_results_by_document.update(
+            {"alpha": ("seg-a",), "beta": ("seg-b",), "gamma": ("seg-c",)}
+        )
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_all_documents(None)
+
+        self.assertEqual(len(self.events), 4)
+        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
+        self.assertEqual(
+            self.events[2:],
+            [
+                ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]),
+                ("title", "gamma - DotExpress"),
+            ],
+        )
+        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep"])
+        self.assertEqual(self._state(frame), ([documents[2]], "gamma", "gamma", {"gamma": ("seg-c",)}))
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("c", "3"))
+
+    def test_delete_all_failure_without_valid_document_clears_editors_only(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write_packages(documents[0])
+        self._block("beta")
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
+        self.answers = [gui.wx.YES]
+
+        frame.on_delete_all_documents(None)
+
+        self.assertEqual(len(self.events), 3)
+        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
+        self.assertEqual(self.events[2], ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]))
+        self.assertEqual(self._listing(), ["beta.dep"])
+        self.assertEqual(self._state(frame), ([], None, None, {}))
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))
+
+    def test_delete_all_without_documents_does_nothing(self) -> None:
+        frame = self._make_workspace_frame()
+        frame._save_open_document_with_feedback = Mock()
+
+        frame.on_delete_all_documents(None)
+
+        frame._save_open_document_with_feedback.assert_not_called()
+        self.assertEqual(self.events, [])
+        self.assertFalse(self.workspace.exists())
+
+    # --- import ------------------------------------------------------------
+
+    def _write_sources(self, **texts: str) -> list[str]:
+        source_dir = self.root / "sources"
+        source_dir.mkdir(exist_ok=True)
+        paths = []
+        for stem, text in texts.items():
+            path = source_dir / f"{stem}.txt"
+            path.write_text(text, encoding="utf-8")
+            paths.append(str(path))
+        return paths
+
+    def test_import_two_files_adds_them_and_keeps_open_document(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.import_paths = self._write_sources(delta="d", beta="b")
+
+        frame.on_import_document(None)
+
+        self.assertEqual(self.events, [("FileDialog", gui._("Import Document"), gui.wx.FD_OPEN | gui.wx.FD_MULTIPLE)])
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep", "delta.dep"])
+        self.assertEqual(self._package("delta"), Document("delta", "d", None))
+        self.assertEqual(
+            self._state(frame),
+            ([alpha, Document("beta", "b", None), Document("delta", "d", None)], "alpha", "alpha", {}),
+        )
+        self.assertEqual(frame.document_list.items, ["alpha", "beta", "delta"])
+
+    def test_import_one_file_opens_it(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.import_paths = self._write_sources(beta="b")
+
+        frame.on_import_document(None)
+
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
+        self.assertEqual(frame._document_controller.open_name, "beta")
+        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("b", ""))
+        self.assertEqual(self.events[1:], [("title", "beta - DotExpress")])
+
+    def test_import_reports_load_issues_before_save_issues(self) -> None:
+        alpha = Document("alpha", "a", "1")
+        self._write_packages(alpha)
+        self._block("delta")
+        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
+        self.import_paths = self._write_sources(Alpha="dup", beta="b", delta="d")
+
+        frame.on_import_document(None)
+
+        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
+        self.assertEqual(frame._document_controller.open_name, "beta")
+        kind, title, message, lines = self.events[-1]
+        self.assertEqual((kind, title, message), ("FileIssuesDialog", gui._("Import Issues"), gui._("Some files were skipped during import.")))
+        self.assertEqual(len(lines), 2)
+        self.assertEqual(lines[0], 'Alpha.txt: Document "Alpha" already exists.')
+        self.assertTrue(lines[1].startswith("delta.dep: "), lines[1])
+        self.assertIn("delta.dep", lines[1][len("delta.dep: "):])
+
+    # --- selection ---------------------------------------------------------
+
+    def test_selection_change_maps_index_to_name(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
+        for index, expected in ((1, "beta"), (gui.wx.NOT_FOUND, None), (2, None), (0, "alpha")):
+            with self.subTest(index=index):
+                frame.document_list.selected = index
+                event = Mock()
+
+                frame.on_document_selection_changed(event)
+
+                self.assertEqual(frame._document_controller.selected_name, expected)
+                event.Skip.assert_called_once_with()
+
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them on the unchanged code.**

```bash
$PY -m unittest tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest -v 2>&1 | grep -E ' \.\.\. |^Ran|^OK|^FAILED' | sed -E 's/ \(tests\.test_gui_document_flows\.DocumentWorkspaceFlowsCharacterizationTest\.[a-z_]+\)//; s/ in [0-9.]+s$//'
```

Expected (30 pass, the two case-insensitive tests skip on Linux; if one fails, the test is wrong about today's behavior, not the code):

```text
test_add_case_variant_on_case_insensitive_file_system_overwrites_package ... skipped 'needs a case-insensitive file system'
test_add_case_variant_on_case_sensitive_file_system ... ok
test_add_duplicate_name_reprompts_with_that_name ... ok
test_add_saves_open_document_then_creates_and_opens_new_document ... ok
test_add_write_failure_shows_error_and_keeps_state ... ok
test_case_only_rename_on_case_insensitive_file_system_deletes_package ... skipped 'needs a case-insensitive file system'
test_case_only_rename_on_case_sensitive_file_system ... ok
test_close_vetoes_when_save_fails ... ok
test_default_document_is_pending_opened_and_focused ... ok
test_delete_all_failure_reports_then_reloads_and_reviews ... ok
test_delete_all_failure_without_valid_document_clears_editors_only ... ok
test_delete_all_success_removes_packages_and_creates_default_document ... ok
test_delete_all_without_documents_does_nothing ... ok
test_delete_answered_no_changes_nothing ... ok
test_delete_last_document_creates_default_document ... ok
test_delete_open_middle_document_opens_previous_neighbour ... ok
test_delete_selected_document_that_is_not_open_keeps_editors ... ok
test_delete_unlink_failure_shows_error_and_keeps_state ... ok
test_import_one_file_opens_it ... ok
test_import_reports_load_issues_before_save_issues ... ok
test_import_two_files_adds_them_and_keeps_open_document ... ok
test_rename_cancelled_or_unchanged_does_nothing ... ok
test_rename_unlink_failure_leaves_both_packages_and_state ... ok
test_rename_with_missing_old_package_writes_new_one ... ok
test_rename_write_failure_keeps_old_package_and_state ... ok
test_rename_writes_new_package_deletes_old_and_moves_state ... ok
test_save_failure_reports_error_after_updating_memory ... ok
test_save_open_document_keeps_pending_document_pending ... ok
test_selection_change_maps_index_to_name ... ok
test_startup_invalid_file_delete_error_continues_with_next_file ... ok
test_startup_reviews_invalid_packages_and_opens_first_valid_one ... ok
test_startup_with_missing_workspace_creates_it_and_default_document ... ok
Ran 32 tests
OK (skipped=2)
```

- [ ] **Step 3: Prove the tests notice an order change, then undo it.** Three mutations of today's `gui.py`: invalid-file deletion stops at the first error; the save writes before it updates memory; a failed Delete All without valid documents also creates the default document (that would "fix" known defect 4).

```bash
$PY - <<'EOF'
from pathlib import Path
path = Path("gui.py")
text = path.read_text(encoding="utf-8")
mutations = [
    (
        'self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc)\n',
        'self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc)\n\t\t\t\treturn\n',
    ),
    (
        "\t\tself._replace_document(updated_document)\n"
        "\t\tsave_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)\n",
        "\t\tsave_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)\n"
        "\t\tself._replace_document(updated_document)\n",
    ),
    (
        "\t\t\t\telse:\n\t\t\t\t\tself._clear_document_editors()\n\t\t\t\tself._refresh_dual_view()\n",
        "\t\t\t\telse:\n\t\t\t\t\tself._clear_document_editors()\n\t\t\t\t\tself._ensure_open_document_exists()\n\t\t\t\tself._refresh_dual_view()\n",
    ),
]
for old, new in mutations:
    assert text.count(old) == 1, old
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
EOF
$PY -m unittest tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^FAILED' | LC_ALL=C sort
git -C $REPO checkout -- client/gui.py
git -C $REPO status --short
```

Expected (one test per mutation; afterwards only the test file is changed):

```text
FAIL: test_delete_all_failure_without_valid_document_clears_editors_only (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_delete_all_failure_without_valid_document_clears_editors_only)
FAIL: test_save_failure_reports_error_after_updating_memory (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_save_failure_reports_error_after_updating_memory)
FAIL: test_startup_invalid_file_delete_error_continues_with_next_file (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_invalid_file_delete_error_continues_with_next_file)
FAILED (failures=3, skipped=2)
 M client/tests/test_gui_document_flows.py
```

- [ ] **Step 4: Full-suite check.**

```bash
$T/tools/check_suite.sh 646 30 2
```

Expected:

```text
Ran 646 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (646)
new tests ok: 30 (expected 30)
new tests skipped: 2 (expected 2)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
test: characterize document workspace flows

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
test: characterize document workspace flows
```

---

### Task 2: Controller state methods (spec step 2)

**Files:**
- Modify: `client/documents/controller.py` (imports `document_name_exists`, `get_adjacent_document_name` from `documents.session`; delete `set_state`; add the methods below)
- Test: `client/tests/test_document_controller.py` (10 new tests)

**Interfaces:**
- Consumes: `documents.session.document_name_exists(documents, name, exclude_name=None)`, `documents.session.get_adjacent_document_name(documents, current_name, step)`.
- Produces on `DocumentController`: properties `has_documents -> bool`, `first_document_name -> str | None`; methods `documents_snapshot() -> list[Document]` (a new list), `document_name_at(index: int) -> str | None` (`None` for `index < 0` or `index >= len`), `document_name_exists(name: str, exclude_name: str | None = None) -> bool` (exact, case-sensitive), `adjacent_document_name(step: int) -> str | None` (from `open_name or selected_name`), `add_document(document) -> None` (append, no sort, no duplicate check), `add_documents(documents) -> None` (append in order), `load_documents(documents) -> None` (list replaced by `list(documents)`; open and selected names `None`; cache `{}`), `select_document(name: str | None) -> None` (no validation), `get_dual_view_results(name: str | None) -> tuple` (`cache.get(name or "", ())`), `set_dual_view_results(name: str, results) -> None`. Existing members unchanged; `set_state` deleted (no callers).

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_document_controller.py b/client/tests/test_document_controller.py
index f5e5145..e545eb2 100644
--- a/client/tests/test_document_controller.py
+++ b/client/tests/test_document_controller.py
@@ -173,6 +173,104 @@ class DocumentControllerTest(unittest.TestCase):
         self.assertEqual(controller.selected_document_name, "alpha")
         self.assertEqual(controller.dual_view_results_by_document, {"alpha": ("keep",), "zoo": ("keep-zoo",)})
 
+    def test_add_document_appends_without_sorting(self) -> None:
+        controller = DocumentController(documents=[self.documents[2]])
+
+        controller.add_document(self.documents[0])
+
+        self.assertEqual(controller.document_names, ["zoo", "alpha"])
+
+    def test_add_documents_appends_in_given_order(self) -> None:
+        controller = DocumentController(documents=[self.documents[1]])
+
+        controller.add_documents([self.documents[2], self.documents[0]])
+
+        self.assertEqual(controller.document_names, ["beta", "zoo", "alpha"])
+
+    def test_load_documents_replaces_list_and_clears_names_and_cache(self) -> None:
+        loaded = [self.documents[1], self.documents[2]]
+        controller = DocumentController(
+            documents=[self.documents[0]],
+            open_name="alpha",
+            selected_name="alpha",
+            dual_view_results_by_document={"alpha": ("segment",)},
+        )
+
+        controller.load_documents(loaded)
+        loaded.append(self.documents[0])
+
+        self.assertEqual(controller.document_names, ["beta", "zoo"])
+        self.assertIsNone(controller.open_document_name)
+        self.assertIsNone(controller.selected_document_name)
+        self.assertEqual(controller.get_dual_view_results("alpha"), ())
+
+    def test_select_document_sets_name_without_validation(self) -> None:
+        controller = DocumentController(documents=list(self.documents), selected_name="alpha")
+
+        controller.select_document("missing")
+        self.assertEqual(controller.selected_document_name, "missing")
+        controller.select_document(None)
+        self.assertIsNone(controller.selected_document_name)
+
+    def test_document_name_at_returns_none_outside_the_list(self) -> None:
+        controller = DocumentController(documents=list(self.documents))
+
+        self.assertEqual(controller.document_name_at(0), "alpha")
+        self.assertEqual(controller.document_name_at(2), "zoo")
+        self.assertIsNone(controller.document_name_at(-1))
+        self.assertIsNone(controller.document_name_at(3))
+
+    def test_has_documents_and_first_document_name(self) -> None:
+        empty = DocumentController()
+        controller = DocumentController(documents=[self.documents[1], self.documents[0]])
+
+        self.assertFalse(empty.has_documents)
+        self.assertIsNone(empty.first_document_name)
+        self.assertTrue(controller.has_documents)
+        self.assertEqual(controller.first_document_name, "beta")
+
+    def test_documents_snapshot_is_a_copy(self) -> None:
+        controller = DocumentController(documents=list(self.documents))
+
+        snapshot = controller.documents_snapshot()
+        snapshot.clear()
+
+        self.assertEqual(controller.document_names, ["alpha", "beta", "zoo"])
+        self.assertEqual(controller.documents_snapshot(), self.documents)
+        self.assertIsNot(controller.documents_snapshot(), controller.documents)
+
+    def test_adjacent_document_name_prefers_open_over_selected(self) -> None:
+        controller = DocumentController(documents=list(self.documents), open_name="beta", selected_name="zoo")
+
+        self.assertEqual(controller.adjacent_document_name(1), "zoo")
+        self.assertEqual(controller.adjacent_document_name(-1), "alpha")
+
+        controller.open_name = None
+        self.assertEqual(controller.adjacent_document_name(1), "alpha")
+        self.assertIsNone(DocumentController().adjacent_document_name(1))
+
+    def test_document_name_exists_is_exact_and_honours_exclude(self) -> None:
+        controller = DocumentController(documents=list(self.documents))
+
+        self.assertTrue(controller.document_name_exists("beta"))
+        self.assertFalse(controller.document_name_exists("Beta"))
+        self.assertFalse(controller.document_name_exists("beta", exclude_name="beta"))
+        self.assertTrue(controller.document_name_exists("zoo", exclude_name="beta"))
+
+    def test_dual_view_results_get_and_set(self) -> None:
+        controller = DocumentController(documents=list(self.documents))
+
+        self.assertEqual(controller.get_dual_view_results("alpha"), ())
+        self.assertEqual(controller.get_dual_view_results(None), ())
+        controller.set_dual_view_results("alpha", ("segment",))
+        controller.set_dual_view_results("ghost", ("other",))
+
+        self.assertEqual(controller.get_dual_view_results("alpha"), ("segment",))
+        self.assertEqual(
+            controller.dual_view_results_by_document,
+            {"alpha": ("segment",), "ghost": ("other",)},
+        )
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_document_controller 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (the ten new tests error on the missing methods):

```text
      1 AttributeError: 'DocumentController' object has no attribute 'add_document'. Did you mean: 'get_document'?
      1 AttributeError: 'DocumentController' object has no attribute 'add_documents'. Did you mean: 'documents'?
      1 AttributeError: 'DocumentController' object has no attribute 'adjacent_document_name'. Did you mean: 'open_document_name'?
      1 AttributeError: 'DocumentController' object has no attribute 'document_name_at'. Did you mean: 'document_names'?
      1 AttributeError: 'DocumentController' object has no attribute 'document_name_exists'. Did you mean: 'document_names'?
      1 AttributeError: 'DocumentController' object has no attribute 'documents_snapshot'
      1 AttributeError: 'DocumentController' object has no attribute 'get_dual_view_results'
      1 AttributeError: 'DocumentController' object has no attribute 'has_documents'. Did you mean: 'documents'?
      1 AttributeError: 'DocumentController' object has no attribute 'load_documents'. Did you mean: 'sort_documents'?
      1 AttributeError: 'DocumentController' object has no attribute 'select_document'. Did you mean: 'delete_document'?
      1 ERROR: test_add_document_appends_without_sorting (tests.test_document_controller.DocumentControllerTest.test_add_document_appends_without_sorting)
      1 ERROR: test_add_documents_appends_in_given_order (tests.test_document_controller.DocumentControllerTest.test_add_documents_appends_in_given_order)
      1 ERROR: test_adjacent_document_name_prefers_open_over_selected (tests.test_document_controller.DocumentControllerTest.test_adjacent_document_name_prefers_open_over_selected)
      1 ERROR: test_document_name_at_returns_none_outside_the_list (tests.test_document_controller.DocumentControllerTest.test_document_name_at_returns_none_outside_the_list)
      1 ERROR: test_document_name_exists_is_exact_and_honours_exclude (tests.test_document_controller.DocumentControllerTest.test_document_name_exists_is_exact_and_honours_exclude)
      1 ERROR: test_documents_snapshot_is_a_copy (tests.test_document_controller.DocumentControllerTest.test_documents_snapshot_is_a_copy)
      1 ERROR: test_dual_view_results_get_and_set (tests.test_document_controller.DocumentControllerTest.test_dual_view_results_get_and_set)
      1 ERROR: test_has_documents_and_first_document_name (tests.test_document_controller.DocumentControllerTest.test_has_documents_and_first_document_name)
      1 ERROR: test_load_documents_replaces_list_and_clears_names_and_cache (tests.test_document_controller.DocumentControllerTest.test_load_documents_replaces_list_and_clears_names_and_cache)
      1 ERROR: test_select_document_sets_name_without_validation (tests.test_document_controller.DocumentControllerTest.test_select_document_sets_name_without_validation)
      1 FAILED (errors=10)
      1 Ran 21 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/controller.py b/client/documents/controller.py
index a7baa5a..e31ba74 100644
--- a/client/documents/controller.py
+++ b/client/documents/controller.py
@@ -2,6 +2,8 @@ from __future__ import annotations
 
 from documents.session import (
     DeleteDocumentDecision,
+    document_name_exists,
+    get_adjacent_document_name,
     plan_delete_document,
     plan_open_document,
     rename_document_in_list,
@@ -49,18 +51,48 @@ class DocumentController:
     def sort_documents(self) -> None:
         self.documents.sort(key=lambda document: (document.name.casefold(), document.name))
 
-    def set_state(
-        self,
-        *,
-        documents: list[Document],
-        open_name: str | None,
-        selected_name: str | None,
-        dual_view_results_by_document: dict[str, tuple[object, ...]],
-    ) -> None:
-        self.documents = documents
-        self.open_name = open_name
-        self.selected_name = selected_name
-        self.dual_view_results_by_document = dual_view_results_by_document
+    @property
+    def has_documents(self) -> bool:
+        return bool(self.documents)
+
+    @property
+    def first_document_name(self) -> str | None:
+        return self.documents[0].name if self.documents else None
+
+    def documents_snapshot(self) -> list[Document]:
+        return list(self.documents)
+
+    def document_name_at(self, index: int) -> str | None:
+        if index < 0 or index >= len(self.documents):
+            return None
+        return self.documents[index].name
+
+    def document_name_exists(self, name: str, exclude_name: str | None = None) -> bool:
+        return document_name_exists(self.documents, name, exclude_name=exclude_name)
+
+    def adjacent_document_name(self, step: int) -> str | None:
+        return get_adjacent_document_name(self.documents, self.open_name or self.selected_name, step)
+
+    def add_document(self, document: Document) -> None:
+        self.documents.append(document)
+
+    def add_documents(self, documents: list[Document]) -> None:
+        self.documents.extend(documents)
+
+    def load_documents(self, documents: list[Document]) -> None:
+        self.documents = list(documents)
+        self.open_name = None
+        self.selected_name = None
+        self.dual_view_results_by_document = {}
+
+    def select_document(self, name: str | None) -> None:
+        self.selected_name = name
+
+    def get_dual_view_results(self, name: str | None) -> tuple[object, ...]:
+        return self.dual_view_results_by_document.get(name or "", ())
+
+    def set_dual_view_results(self, name: str, results: tuple[object, ...]) -> None:
+        self.dual_view_results_by_document[name] = results
 
     def open_document(self, name: str | None) -> Document | None:
         decision = plan_open_document(self.documents, name)
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the `set_state` grep.**

```bash
$PY -m unittest tests.test_document_controller 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 656 40 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
grep -rn 'set_state' --include='*.py' $REPO/client | grep -v '/\.venv/'
```

Expected (`set_state` is gone everywhere):

```text
Ran 21 tests
OK
Ran 656 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (656)
new tests ok: 40 (expected 40)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/controller.py client/tests/test_document_controller.py
git -C $REPO commit -q -F - <<'MSG'
refactor: add document controller state methods

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: add document controller state methods
```

---

### Task 3: The wx-free workspace service (spec step 3)

**Files:**
- Create: `client/documents/workspace_service.py`
- Create: `client/tests/test_workspace_service.py` (25 tests, no wx, no stub scope)

**Interfaces:**
- Consumes: Task 2's controller methods; `documents.workspace` (`BatchIssue`, `Document`, `batch_import_documents`, `document_package_path_for_name`, `ensure_workspace_directory`, `load_workspace_documents`, `prepare_document_for_save`, `save_document_package`, all unchanged); `documents.session.DeleteDocumentDecision`.
- Produces: `ImportResult(saved: list[Document], issues: list[BatchIssue])` and `DeleteAllResult(completed: bool, invalid_paths: list[Path])` (frozen dataclasses); `DocumentWorkspaceService(controller, workspace_dir)` with `workspace_dir` (property), `package_path(name) -> Path`, `load_documents() -> list[Path]`, `delete_invalid_files(paths, *, on_error)`, `save_open_document(*, text, braille) -> Document | None`, `create_document(document) -> None`, `import_files(paths, *, format_key) -> ImportResult`, `rename_document(source_name, new_name) -> Document | None` (`ValueError` for equal names, before any IO), `delete_document(name) -> DeleteDocumentDecision`, `delete_all_documents(*, on_error) -> DeleteAllResult`. Each method does what the spec's flow table lists, in the same order; only `OSError` is handled (by the caller, or by `on_error` in the two callback methods). The service reads the controller through methods only (acceptance criterion 7).

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_workspace_service.py b/client/tests/test_workspace_service.py
new file mode 100644
index 0000000..5e8b231
--- /dev/null
+++ b/client/tests/test_workspace_service.py
@@ -0,0 +1,397 @@
+from __future__ import annotations
+
+import ast
+import tempfile
+import unittest
+import zipfile
+from pathlib import Path
+
+from documents.controller import DocumentController
+from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
+from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
+
+SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"
+
+
+class DocumentWorkspaceServiceTest(unittest.TestCase):
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name)
+        self.workspace = self.root / "workspace"
+
+    def _service(self, documents=(), **state) -> DocumentWorkspaceService:
+        self.controller = DocumentController(documents=list(documents), **state)
+        return DocumentWorkspaceService(self.controller, self.workspace)
+
+    def _write(self, *documents: Document) -> None:
+        for document in documents:
+            save_document_package(self.workspace / f"{document.name}.dep", document)
+
+    def _block(self, name: str) -> Path:
+        """A non-empty directory at ``<ws>/<name>.dep``: writing or unlinking it raises ``OSError``."""
+        path = self.workspace / f"{name}.dep"
+        (path / "keep").mkdir(parents=True)
+        return path
+
+    def _listing(self) -> list[str]:
+        return sorted(path.name for path in self.workspace.iterdir())
+
+    def _package(self, name: str) -> Document:
+        return load_document_package(self.workspace / f"{name}.dep")
+
+    def _members(self, name: str) -> list[str]:
+        with zipfile.ZipFile(self.workspace / f"{name}.dep") as archive:
+            return sorted(archive.namelist())
+
+    def _state(self) -> tuple:
+        return (
+            list(self.controller.documents),
+            self.controller.open_name,
+            self.controller.selected_name,
+            dict(self.controller.dual_view_results_by_document),
+        )
+
+    # --- basics ------------------------------------------------------------
+
+    def test_workspace_dir_and_package_path(self) -> None:
+        service = self._service()
+
+        self.assertEqual(service.workspace_dir, self.workspace)
+        self.assertEqual(service.package_path("alpha"), self.workspace / "alpha.dep")
+        self.assertFalse(self.workspace.exists())
+
+    def test_module_imports_neither_wx_nor_gui(self) -> None:
+        tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
+        imported = set()
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Import):
+                imported.update(alias.name.split(".")[0] for alias in node.names)
+            elif isinstance(node, ast.ImportFrom):
+                imported.add((node.module or "").split(".")[0])
+
+        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)
+
+    # --- load and invalid files ------------------------------------------
+
+    def test_load_documents_creates_directory_and_loads_sorted_documents(self) -> None:
+        service = self._service(
+            [Document("old", "o", "1")],
+            open_name="old",
+            selected_name="old",
+            dual_view_results_by_document={"old": ("segment",)},
+        )
+
+        self.assertEqual(service.load_documents(), [])
+        self.assertTrue(self.workspace.is_dir())
+        self.assertEqual(self._state(), ([], None, None, {}))
+
+        self._write(Document("beta", "b", "2"), Document("Alpha", "a", None))
+        (self.workspace / "bad.dep").write_bytes(b"not a zip")
+
+        invalid_paths = service.load_documents()
+
+        self.assertEqual(invalid_paths, [self.workspace / "bad.dep"])
+        self.assertEqual(self.controller.documents, [Document("Alpha", "a", None), Document("beta", "b", "2")])
+
+    def test_delete_invalid_files_reports_each_error_and_continues(self) -> None:
+        blocked = self._block("a-blocked")
+        corrupt = self.workspace / "b-corrupt.dep"
+        corrupt.write_bytes(b"not a zip")
+        missing = self.workspace / "c-missing.dep"
+        errors: list[OSError] = []
+
+        self._service().delete_invalid_files([blocked, corrupt, missing], on_error=errors.append)
+
+        self.assertEqual(len(errors), 1)
+        self.assertIsInstance(errors[0], OSError)
+        self.assertIn("a-blocked.dep", str(errors[0]))
+        self.assertEqual(self._listing(), ["a-blocked.dep"])
+
+    # --- save --------------------------------------------------------------
+
+    def test_save_open_document_updates_memory_and_disk(self) -> None:
+        service = self._service([Document("alpha", "a", "1"), Document("beta", "b", None)], open_name="alpha")
+
+        saved = service.save_open_document(text="edited", braille="edited braille")
+
+        self.assertEqual(saved, Document("alpha", "edited", "edited braille"))
+        self.assertEqual(self.controller.get_document("alpha"), saved)
+        self.assertEqual(self._package("alpha"), saved)
+        self.assertEqual(self._listing(), ["alpha.dep"])
+
+    def test_save_open_document_keeps_pending_braille_pending(self) -> None:
+        service = self._service([Document("alpha", "a", None)], open_name="alpha")
+
+        saved = service.save_open_document(text="edited", braille="ignored")
+
+        self.assertEqual(saved, Document("alpha", "edited", None))
+        self.assertEqual(self._package("alpha"), Document("alpha", "edited", None))
+        self.assertIn("alpha.meta.json", self._members("alpha"))
+
+    def test_save_without_open_document_does_nothing(self) -> None:
+        for state in ({}, {"open_name": "ghost"}):
+            with self.subTest(state=state):
+                service = self._service([Document("alpha", "a", "1")], **state)
+
+                self.assertIsNone(service.save_open_document(text="edited", braille="b"))
+                self.assertEqual(self.controller.documents, [Document("alpha", "a", "1")])
+                self.assertFalse(self.workspace.exists())
+
+    def test_save_failure_propagates_after_memory_update(self) -> None:
+        self._block("alpha")
+        service = self._service([Document("alpha", "a", "1")], open_name="alpha")
+
+        with self.assertRaises(OSError):
+            service.save_open_document(text="edited", braille="edited braille")
+
+        self.assertEqual(self.controller.documents, [Document("alpha", "edited", "edited braille")])
+
+    # --- create ------------------------------------------------------------
+
+    def test_create_document_writes_then_adds(self) -> None:
+        service = self._service([Document("zoo", "z", "1")])
+
+        service.create_document(Document("alpha", "", ""))
+        service.create_document(Document("new", "", None))
+
+        self.assertEqual(self.controller.document_names, ["zoo", "alpha", "new"])
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
+        self.assertEqual(self._members("new"), ["new.brl", "new.meta.json", "new.txt"])
+
+    def test_create_document_failure_adds_nothing(self) -> None:
+        self._block("alpha")
+        service = self._service()
+
+        with self.assertRaises(OSError):
+            service.create_document(Document("alpha", "", ""))
+
+        self.assertEqual(self.controller.documents, [])
+
+    # --- import ------------------------------------------------------------
+
+    def _sources(self, **texts: str) -> list[Path]:
+        source_dir = self.root / "sources"
+        source_dir.mkdir(exist_ok=True)
+        paths = []
+        for stem, text in texts.items():
+            path = source_dir / f"{stem}.txt"
+            path.write_text(text, encoding="utf-8")
+            paths.append(path)
+        return paths
+
+    def test_import_files_saves_and_adds_in_order(self) -> None:
+        service = self._service([Document("zoo", "z", "1")])
+
+        result = service.import_files(self._sources(delta="d", beta="b"), format_key="all")
+
+        expected = [Document("beta", "b", None), Document("delta", "d", None)]
+        self.assertEqual(result, ImportResult(saved=expected, issues=[]))
+        self.assertEqual(self.controller.document_names, ["zoo", "beta", "delta"])
+        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])
+
+    def test_import_files_lists_load_issues_before_save_issues(self) -> None:
+        self._block("delta")
+        service = self._service([Document("alpha", "a", "1")])
+        sources = self._sources(Alpha="dup", beta="b", delta="d")
+
+        result = service.import_files(sources, format_key="all")
+
+        self.assertEqual(result.saved, [Document("beta", "b", None)])
+        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
+        self.assertEqual(len(result.issues), 2)
+        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason='Document "Alpha" already exists.'))
+        self.assertEqual(result.issues[1].path, self.workspace / "delta.dep")
+        self.assertIn("delta.dep", result.issues[1].reason)
+
+    def test_import_files_rejects_unknown_format(self) -> None:
+        service = self._service()
+
+        with self.assertRaisesRegex(ValueError, 'Unsupported import format: "nope"'):
+            service.import_files(self._sources(beta="b"), format_key="nope")
+
+        self.assertEqual(self.controller.documents, [])
+
+    # --- rename ------------------------------------------------------------
+
+    def test_rename_writes_new_package_deletes_old_and_updates_controller(self) -> None:
+        self._write(Document("alpha", "a", None))
+        service = self._service(
+            [Document("alpha", "a", None), Document("beta", "b", "2")],
+            open_name="alpha",
+            selected_name="alpha",
+            dual_view_results_by_document={"alpha": ("segment",)},
+        )
+
+        renamed = service.rename_document("alpha", "gamma")
+
+        self.assertEqual(renamed, Document("gamma", "a", None))
+        self.assertEqual(self._listing(), ["gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "a", None))
+        self.assertEqual(
+            self._state(),
+            ([Document("gamma", "a", None), Document("beta", "b", "2")], "gamma", "gamma", {"gamma": ("segment",)}),
+        )
+
+    def test_rename_with_missing_old_package(self) -> None:
+        service = self._service([Document("alpha", "a", "1")])
+
+        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))
+        self.assertEqual(self._listing(), ["gamma.dep"])
+
+    def test_rename_write_failure_propagates_and_keeps_state(self) -> None:
+        self._write(Document("alpha", "a", "1"))
+        self._block("gamma")
+        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        before = self._state()
+
+        with self.assertRaises(OSError):
+            service.rename_document("alpha", "gamma")
+
+        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
+        self.assertEqual(self._state(), before)
+
+    def test_rename_unlink_failure_propagates_and_leaves_both_packages(self) -> None:
+        self._block("alpha")
+        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        before = self._state()
+
+        with self.assertRaises(OSError):
+            service.rename_document("alpha", "gamma")
+
+        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
+        self.assertEqual(self._state(), before)
+
+    def test_rename_unknown_source_does_nothing(self) -> None:
+        service = self._service([Document("alpha", "a", "1")])
+
+        self.assertIsNone(service.rename_document("ghost", "gamma"))
+        self.assertFalse(self.workspace.exists())
+
+    def test_rename_to_the_same_name_is_refused(self) -> None:
+        self._write(Document("alpha", "a", "1"))
+        service = self._service([Document("alpha", "a", "1")])
+
+        with self.assertRaises(ValueError):
+            service.rename_document("alpha", "alpha")
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
+
+    # --- delete ------------------------------------------------------------
+
+    def test_delete_document_unlinks_and_applies_decision(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("zoo", "z", "3")]
+        self._write(*documents)
+        service = self._service(
+            documents,
+            open_name="beta",
+            selected_name="beta",
+            dual_view_results_by_document={"alpha": ("keep",), "beta": ("drop",)},
+        )
+
+        decision = service.delete_document("beta")
+
+        self.assertEqual((decision.preferred_name, decision.was_open), ("alpha", True))
+        self.assertEqual(self._listing(), ["alpha.dep", "zoo.dep"])
+        self.assertEqual(self._state(), ([documents[0], documents[2]], "alpha", "alpha", {"alpha": ("keep",)}))
+
+    def test_delete_document_with_missing_package(self) -> None:
+        service = self._service([Document("alpha", "a", "1")])
+
+        service.delete_document("alpha")
+
+        self.assertEqual(self.controller.documents, [])
+        self.assertFalse(self.workspace.exists())
+
+    def test_delete_document_unlink_failure_keeps_state(self) -> None:
+        self._block("alpha")
+        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        before = self._state()
+
+        with self.assertRaises(OSError):
+            service.delete_document("alpha")
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._state(), before)
+
+    # --- Delete All --------------------------------------------------------
+
+    def test_delete_all_success_clears_disk_and_controller(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write(*documents)
+        errors: list[OSError] = []
+        service = self._service(
+            documents,
+            open_name="alpha",
+            selected_name="beta",
+            dual_view_results_by_document={"alpha": ("segment",)},
+        )
+
+        result = service.delete_all_documents(on_error=errors.append)
+
+        self.assertEqual(result, DeleteAllResult(completed=True, invalid_paths=[]))
+        self.assertEqual(errors, [])
+        self.assertEqual(self._listing(), [])
+        self.assertEqual(self._state(), ([], None, None, {}))
+
+    def test_delete_all_failure_reports_before_reload_and_restores_from_disk(self) -> None:
+        documents = [
+            Document("alpha", "a", "1"),
+            Document("beta", "b", "2"),
+            Document("gamma", "c", "3"),
+            Document("zoo", "z", "4"),
+        ]
+        self._write(documents[0], documents[2], Document("zoo", "z on disk", "4"))
+        self._block("beta")
+        seen: list[tuple] = []
+        errors: list[OSError] = []
+
+        def on_error(error: OSError) -> None:
+            errors.append(error)
+            seen.append((self._listing(), self.controller.document_names))
+
+        service = self._service(
+            documents,
+            open_name="alpha",
+            selected_name="zoo",
+            dual_view_results_by_document={"alpha": ("a",), "beta": ("b",), "zoo": ("z",), "ghost": ("g",)},
+        )
+
+        result = service.delete_all_documents(on_error=on_error)
+
+        self.assertEqual(result, DeleteAllResult(completed=False, invalid_paths=[self.workspace / "beta.dep"]))
+        self.assertEqual(len(errors), 1)
+        self.assertIn("beta.dep", str(errors[0]))
+        self.assertEqual(seen, [(["beta.dep", "gamma.dep", "zoo.dep"], ["alpha", "beta", "gamma", "zoo"])])
+        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep", "zoo.dep"])
+        self.assertEqual(
+            self._state(),
+            ([documents[2], Document("zoo", "z on disk", "4")], None, "zoo", {"zoo": ("z",)}),
+        )
+
+    def test_delete_all_reload_error_propagates_after_on_error(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        self._write(documents[0])
+        self._block("beta")
+        calls: list[str] = []
+        service = self._service(documents)
+
+        def on_error(_error: OSError) -> None:
+            calls.append("on_error")
+            # Make the reload fail: the workspace directory is replaced by a file.
+            for path in sorted(self.workspace.rglob("*"), reverse=True):
+                path.rmdir() if path.is_dir() else path.unlink()
+            self.workspace.rmdir()
+            self.workspace.write_text("", encoding="utf-8")
+
+        with self.assertRaises(OSError):
+            service.delete_all_documents(on_error=on_error)
+
+        self.assertEqual(calls, ["on_error"])
+        self.assertEqual(self.controller.documents, documents)
+
+
+if __name__ == "__main__":
+    unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_workspace_service 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (the module does not exist yet):

```text
      1 ERROR: test_workspace_service (unittest.loader._FailedTest.test_workspace_service)
      1 FAILED (errors=1)
      1 ImportError: Failed to import test module: test_workspace_service
      1 ModuleNotFoundError: No module named 'documents.workspace_service'
      1 Ran 1 test
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/workspace_service.py b/client/documents/workspace_service.py
new file mode 100644
index 0000000..ecbaf26
--- /dev/null
+++ b/client/documents/workspace_service.py
@@ -0,0 +1,128 @@
+"""Workspace disk operations of the document flows, with the matching controller update.
+
+No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
+The order of memory and disk effects is part of the contract: save updates memory
+before writing, rename writes the new package before deleting the old one, and
+Delete All reports a failure before it reloads the workspace.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Callable, Iterable
+from dataclasses import dataclass
+from pathlib import Path
+
+from documents.controller import DocumentController
+from documents.session import DeleteDocumentDecision
+from documents.workspace import (
+    BatchIssue,
+    Document,
+    batch_import_documents,
+    document_package_path_for_name,
+    ensure_workspace_directory,
+    load_workspace_documents,
+    prepare_document_for_save,
+    save_document_package,
+)
+
+
+@dataclass(frozen=True)
+class ImportResult:
+    saved: list[Document]
+    issues: list[BatchIssue]
+
+
+@dataclass(frozen=True)
+class DeleteAllResult:
+    completed: bool
+    invalid_paths: list[Path]
+
+
+class DocumentWorkspaceService:
+    def __init__(self, controller: DocumentController, workspace_dir: Path) -> None:
+        self._controller = controller
+        self._workspace_dir = Path(workspace_dir)
+
+    @property
+    def workspace_dir(self) -> Path:
+        return self._workspace_dir
+
+    def package_path(self, name: str) -> Path:
+        return document_package_path_for_name(name, self._workspace_dir)
+
+    def load_documents(self) -> list[Path]:
+        ensure_workspace_directory(self._workspace_dir)
+        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
+        self._controller.load_documents(documents)
+        return invalid_paths
+
+    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
+        for path in paths:
+            try:
+                path.unlink(missing_ok=True)
+            except OSError as exc:
+                on_error(exc)
+
+    def save_open_document(self, *, text: str, braille: str) -> Document | None:
+        document = self._controller.get_document(self._controller.open_document_name)
+        if document is None:
+            return None
+        updated_document = prepare_document_for_save(document, text=text, braille=braille)
+        self._controller.replace_document(updated_document)
+        save_document_package(self.package_path(updated_document.name), updated_document)
+        return updated_document
+
+    def create_document(self, document: Document) -> None:
+        save_document_package(self.package_path(document.name), document)
+        self._controller.add_document(document)
+
+    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
+        documents, load_issues = batch_import_documents(
+            list(paths),
+            format_key=format_key,
+            existing_names=set(self._controller.document_names),
+        )
+        saved: list[Document] = []
+        save_issues: list[BatchIssue] = []
+        for document in documents:
+            package_path = self.package_path(document.name)
+            try:
+                save_document_package(package_path, document)
+            except OSError as exc:
+                save_issues.append(BatchIssue(path=package_path, reason=str(exc)))
+                continue
+            saved.append(document)
+        self._controller.add_documents(saved)
+        return ImportResult(saved=saved, issues=load_issues + save_issues)
+
+    def rename_document(self, source_name: str, new_name: str) -> Document | None:
+        if source_name == new_name:
+            raise ValueError("A document cannot be renamed to its own name.")
+        source = self._controller.get_document(source_name)
+        if source is None:
+            return None
+        save_document_package(self.package_path(new_name), Document(new_name, source.text, source.braille))
+        old_path = self.package_path(source_name)
+        if old_path.exists():
+            old_path.unlink()
+        return self._controller.rename_document(source_name, new_name)
+
+    def delete_document(self, name: str) -> DeleteDocumentDecision:
+        package_path = self.package_path(name)
+        if package_path.exists():
+            package_path.unlink()
+        return self._controller.delete_document(name)
+
+    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
+        for document in self._controller.documents_snapshot():
+            package_path = self.package_path(document.name)
+            try:
+                if package_path.exists():
+                    package_path.unlink()
+            except OSError as exc:
+                on_error(exc)
+                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
+                self._controller.restore_documents_after_delete_all_failure(remaining_documents)
+                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
+        self._controller.delete_all_documents()
+        return DeleteAllResult(completed=True, invalid_paths=[])
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the service greps (acceptance criteria 6 and 7).**

```bash
$PY -m unittest tests.test_workspace_service 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 681 65 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo AC6; grep -nE '^(import wx|from wx)|^from gui|^import gui' documents/workspace_service.py documents/controller.py; grep -n 'set_state' documents/controller.py
echo AC7; grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' documents/workspace_service.py
echo end
```

Expected (nothing between the labels):

```text
Ran 25 tests
OK
Ran 681 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (681)
new tests ok: 65 (expected 65)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
AC6
AC7
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/workspace_service.py client/tests/test_workspace_service.py
git -C $REPO commit -q -F - <<'MSG'
refactor: add wx-free document workspace service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: add wx-free document workspace service
```

---

### Task 4: The frame uses controller methods only (spec step 4)

**Files:**
- Modify: `client/gui.py` (`__init__` creates the controller; delete `_get_document_controller`, the four property pairs, `_get_document_names`, `_sort_documents`, `_get_document_by_name`, `_replace_document`, `_document_name_exists`; drop the two `hasattr` guards; every state read and write goes through controller methods; drop the `document_name_exists` and `get_adjacent_document_name` imports). Disk IO still runs in `gui` and reads `self.workspace_dir`.
- Test: `client/tests/test_gui_document_flows.py` (new class `DocumentControllerOwnershipTest`; `GuiDocumentFlowsTest._make_frame(documents=(Document("alpha", "source", None),), open_name="alpha")` builds a real controller; the `_documents_by_name` dict and the two lambdas are gone; every property assignment or read in the existing tests becomes a controller constructor argument or a controller call; `documents=()` for `test_sync_document_menu_state_before_document_list_exists` and `DocumentMenuAndExportCharacterizationTest._make_menu_frame`; `_select_first_of` uses `load_documents`)

**Interfaces:**
- Consumes: Task 2's controller methods.
- Produces: `BrailleFrame.__init__` sets `self._document_controller = DocumentController()` right after `self.translation_runtime = runtime`; `_initialize_state` no longer touches the controller. Kept methods keep their names and callers (spec list). `_refresh_document_list` selects `names.index(selected_name)`.

- [ ] **Step 1: Write the failing tests and move the existing setup to the controller.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 1e4088e..e7a3216 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -7,7 +7,7 @@ import zipfile
 from dataclasses import replace
 from pathlib import Path
 from types import SimpleNamespace
-from unittest.mock import Mock, call, patch
+from unittest.mock import DEFAULT, Mock, call, patch
 
 from tests import wx_stub
 from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
@@ -48,7 +48,7 @@ def make_snapshot(
 
 
 class GuiDocumentFlowsTest(unittest.TestCase):
-    def _make_frame(self) -> gui.BrailleFrame:
+    def _make_frame(self, documents=(Document("alpha", "source", None),), open_name="alpha") -> gui.BrailleFrame:
         frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
         frame.translation_runtime = Mock()
         frame._conversion_runner = Mock()
@@ -62,11 +62,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame.output_txt = Mock()
         frame._show_export_all_result = Mock()
         frame._dual_view_frame = None
-        frame._dual_view_results_by_document = {}
-        frame._open_document_name = "alpha"
-        frame._documents_by_name = {"alpha": Document("alpha", "source", None)}
-        frame._get_document_by_name = lambda name: frame._documents_by_name.get(name)
-        frame._replace_document = lambda document: frame._documents_by_name.__setitem__(document.name, document)
+        frame._document_controller = DocumentController(documents=list(documents), open_name=open_name)
         frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
         return frame
 
@@ -86,7 +82,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame = self._make_frame()
         document = Document("alpha", "text", "braille")
         cached_results = (Mock(),)
-        frame._dual_view_results_by_document["alpha"] = cached_results
+        frame._document_controller.set_dual_view_results("alpha", cached_results)
         writer = Mock()
         descriptor = replace(get_format("dep"), writer=writer)
 
@@ -103,7 +99,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame = self._make_frame()
         document = Document("alpha", "text", "braille")
         cached_results = (Mock(),)
-        frame._dual_view_results_by_document["alpha"] = cached_results
+        frame._document_controller.set_dual_view_results("alpha", cached_results)
         writer = Mock()
         descriptor = replace(get_format("html"), writer=writer)
 
@@ -147,7 +143,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         get_format_mock.assert_called_once_with("brl")
 
     def test_sync_document_menu_state_before_document_list_exists(self) -> None:
-        frame = self._make_frame()
+        frame = self._make_frame(documents=())
         menu_items = {
             "open": Mock(),
             "delete": Mock(),
@@ -173,7 +169,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
 
     def test_open_dual_view_creates_refreshes_and_shows_viewer(self) -> None:
         frame = self._make_frame()
-        frame._dual_view_results_by_document["alpha"] = ("segment",)
+        frame._document_controller.set_dual_view_results("alpha", ("segment",))
         viewer = Mock()
         frame._create_dual_view_frame = Mock(return_value=viewer)
         frame._render_dual_view_for_open_document = Mock(return_value="<html>alpha</html>")
@@ -231,6 +227,53 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame._show_file_error.assert_called_once_with(gui._("Failed to open dual view: {error}"), error)
 
 
+class DocumentControllerOwnershipTest(unittest.TestCase):
+    STARTUP_STEPS = (
+        "_initialize_state",
+        "_create_main_layout",
+        "_initialize_conversion_state",
+        "_apply_initial_settings",
+        "_bind_events",
+        "_load_startup_documents",
+    )
+
+    def test_frame_creates_its_controller_before_building_the_menu_bar(self) -> None:
+        seen = []
+
+        def initialize_frame(frame) -> None:
+            seen.append(frame.__dict__.get("_document_controller"))
+
+        with (
+            patch.object(gui.BrailleFrame, "_initialize_frame", autospec=True, side_effect=initialize_frame),
+            patch.multiple(gui.BrailleFrame, **{name: DEFAULT for name in self.STARTUP_STEPS}),
+        ):
+            frame = gui.BrailleFrame(None, runtime=Mock())
+
+        self.assertEqual(len(seen), 1)
+        self.assertIsInstance(seen[0], gui.DocumentController)
+        self.assertIs(frame._document_controller, seen[0])
+        self.assertEqual(seen[0].documents, [])
+
+    def test_initialize_state_keeps_the_frame_controller(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        controller = DocumentController(documents=[Document("alpha", "a", "1")], open_name="alpha")
+        frame._document_controller = controller
+        frame._register_output_font = Mock(return_value=False)
+        with (
+            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
+            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
+            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
+            patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
+            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
+            patch.object(gui, "load_translation_tables", return_value={}),
+        ):
+            frame._initialize_state()
+
+        self.assertIs(frame._document_controller, controller)
+        self.assertEqual(controller.document_names, ["alpha"])
+        self.assertEqual(controller.open_document_name, "alpha")
+
+
 class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
         frame = object.__new__(gui.BrailleFrame)
@@ -431,7 +474,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
         frame.output_txt.SetValue.assert_called_once_with("braille")
         frame.output_txt.SetFocus.assert_called_once_with()
-        self.assertEqual(frame._documents_by_name["alpha"].braille, "braille")
+        self.assertEqual(frame._document_controller.get_document("alpha").braille, "braille")
         message_box.assert_called_once_with(
             gui._("Conversion completed."),
             gui._("Info"),
@@ -604,13 +647,13 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
                 )
             )
 
-        self.assertEqual(frame._dual_view_results_by_document["alpha"], ("segment",))
+        self.assertEqual(frame._document_controller.get_dual_view_results("alpha"), ("segment",))
         frame._refresh_dual_view.assert_called_once_with()
 
     def test_export_conversion_does_not_replace_dual_view_cache(self) -> None:
         frame = self._make_frame()
         policy = gui.ConversionCompletionPolicy(update_output=False)
-        frame._dual_view_results_by_document["alpha"] = ("manual",)
+        frame._document_controller.set_dual_view_results("alpha", ("manual",))
         conversion_output = gui.ConversionOutput("export", ("export-segment",))
 
         frame._finish_conversion_success(
@@ -621,11 +664,10 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
             )
         )
 
-        self.assertEqual(frame._dual_view_results_by_document["alpha"], ("manual",))
+        self.assertEqual(frame._document_controller.get_dual_view_results("alpha"), ("manual",))
 
     def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
-        frame = self._make_frame()
-        frame.documents = [Document("beta", "new text", "braille")]
+        frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._dual_view_frame = Mock()
         frame._refresh_dual_view = Mock()
         frame._load_document_into_editors = Mock()
@@ -637,8 +679,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame._refresh_dual_view.assert_called_once_with()
 
     def test_open_document_moves_input_cursor_to_start(self) -> None:
-        frame = self._make_frame()
-        frame.documents = [Document("beta", "new text", "braille")]
+        frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._refresh_dual_view = Mock()
         frame._refresh_document_list = Mock()
         frame._update_window_title = Mock()
@@ -651,14 +692,15 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame.input_txt.ShowPosition.assert_called_once_with(0)
 
     def test_char_hook_cycles_forward_to_first_document_from_last(self) -> None:
-        frame = self._make_frame()
-        frame.documents = [
-            Document("alpha", "a", "1"),
-            Document("beta", "b", "2"),
-            Document("zoo", "z", "3"),
-        ]
-        frame._open_document_name = "zoo"
-        frame._selected_document_name = "zoo"
+        frame = self._make_frame(
+            documents=(
+                Document("alpha", "a", "1"),
+                Document("beta", "b", "2"),
+                Document("zoo", "z", "3"),
+            ),
+            open_name="zoo",
+        )
+        frame._document_controller.select_document("zoo")
         frame._save_open_document_with_feedback = Mock(return_value=True)
         frame._open_document_by_name = Mock()
         event = Mock()
@@ -672,14 +714,15 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         event.Skip.assert_not_called()
 
     def test_char_hook_cycles_backward_to_last_document_from_first(self) -> None:
-        frame = self._make_frame()
-        frame.documents = [
-            Document("alpha", "a", "1"),
-            Document("beta", "b", "2"),
-            Document("zoo", "z", "3"),
-        ]
-        frame._open_document_name = "alpha"
-        frame._selected_document_name = "alpha"
+        frame = self._make_frame(
+            documents=(
+                Document("alpha", "a", "1"),
+                Document("beta", "b", "2"),
+                Document("zoo", "z", "3"),
+            ),
+            open_name="alpha",
+        )
+        frame._document_controller.select_document("alpha")
         frame._save_open_document_with_feedback = Mock(return_value=True)
         frame._open_document_by_name = Mock()
         event = Mock()
@@ -707,17 +750,16 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         event.Skip.assert_called_once_with()
 
     def test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer(self) -> None:
-        frame = self._make_frame()
-        frame.documents = [
-            Document("alpha", "text-a", "braille-a"),
-            Document("beta", "text-b", "braille-b"),
-        ]
+        frame = self._make_frame(
+            documents=(
+                Document("alpha", "text-a", "braille-a"),
+                Document("beta", "text-b", "braille-b"),
+            ),
+        )
         frame.workspace_dir = Path("/workspace")
-        frame._dual_view_results_by_document = {
-            "alpha": ("stale-alpha",),
-            "beta": ("fresh-beta",),
-            "ghost": ("stale-ghost",),
-        }
+        frame._document_controller.set_dual_view_results("alpha", ("stale-alpha",))
+        frame._document_controller.set_dual_view_results("beta", ("fresh-beta",))
+        frame._document_controller.set_dual_view_results("ghost", ("stale-ghost",))
         frame._save_open_document_with_feedback = Mock(return_value=True)
         frame._show_file_error = Mock()
         frame._refresh_document_list = Mock()
@@ -740,7 +782,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         ):
             frame.on_delete_all_documents(None)
 
-        self.assertEqual(frame._dual_view_results_by_document, {"beta": ("fresh-beta",)})
+        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": ("fresh-beta",)})
         frame._refresh_dual_view.assert_called_once_with()
         frame._open_document_by_name.assert_called_once_with("beta")
 
@@ -1074,8 +1116,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
                 self.assertFalse(hasattr(gui.BrailleFrame, name))
 
     def test_save_open_document_saves_prepared_document(self) -> None:
-        frame = self._make_frame()
-        frame._documents_by_name = {"alpha": Document("alpha", "source", "old braille")}
+        frame = self._make_frame(documents=(Document("alpha", "source", "old braille"),))
         frame.workspace_dir = Path("workspace")
         frame.input_txt.GetValue.return_value = "edited"
         frame.output_txt.GetValue.return_value = "edited braille"
@@ -1084,7 +1125,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
             frame._save_open_document()
 
         expected = Document("alpha", "edited", "edited braille")
-        self.assertEqual(frame._documents_by_name["alpha"], expected)
+        self.assertEqual(frame._document_controller.get_document("alpha"), expected)
         save_package.assert_called_once_with(
             gui.document_package_path_for_name("alpha", Path("workspace")),
             expected,
@@ -1260,7 +1301,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
     )
 
     def _make_menu_frame(self):
-        frame = self._make_frame()
+        frame = self._make_frame(documents=())
         frame.handler_calls = Mock()
         for name in self.DOCUMENT_HANDLER_NAMES:
             setattr(frame, name, getattr(frame.handler_calls, name))
@@ -1274,8 +1315,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         )
 
     def _select_first_of(self, frame, *names: str) -> None:
-        frame.documents = [Document(name, "text", None) for name in names]
-        frame._documents_by_name = {document.name: document for document in frame.documents}
+        frame._document_controller.load_documents([Document(name, "text", None) for name in names])
         frame.document_list = Mock()
         frame.document_list.GetFirstSelected.return_value = 0
 
@@ -1345,7 +1385,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
     def test_context_menu_on_item_selects_it_and_pops_up_below_it(self) -> None:
         frame = self._make_menu_frame()
         self._select_first_of(frame, "alpha")
-        frame._selected_document_name = None
+        frame._document_controller.select_document(None)
         recorder = MenuRecorder()
         document_list = frame.document_list
         document_list.ScreenToClient.return_value = gui.wx.Point(5, 6)
@@ -1370,12 +1410,12 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         document_list.HitTest.assert_called_once_with(gui.wx.Point(5, 6))
         document_list.Select.assert_called_once_with(0)
         document_list.Focus.assert_called_once_with(0)
-        self.assertEqual(frame._selected_document_name, "alpha")
+        self.assertEqual(frame._document_controller.selected_document_name, "alpha")
 
     def test_keyboard_context_menu_without_selection_clears_it(self) -> None:
         frame = self._make_menu_frame()
         self._select_first_of(frame, "alpha", "beta")
-        frame._selected_document_name = "alpha"
+        frame._document_controller.select_document("alpha")
         frame._document_menu_items = {}
         recorder = MenuRecorder()
         document_list = frame.document_list
@@ -1399,7 +1439,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         document_list.ScreenToClient.assert_not_called()
         document_list.Select.assert_not_called()
         document_list.GetItemRect.assert_not_called()
-        self.assertIsNone(frame._selected_document_name)
+        self.assertIsNone(frame._document_controller.selected_document_name)
 
     def test_menu_bar_menus_items_and_handlers(self) -> None:
         frame = self._make_menu_frame()
@@ -1526,7 +1566,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                 source_kind="text",
             ),
         )
-        frame._dual_view_results_by_document["alpha"] = results
+        frame._document_controller.set_dual_view_results("alpha", results)
         with tempfile.TemporaryDirectory() as directory:
             root = Path(directory)
 
@@ -1560,7 +1600,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                 source_kind="text",
             ),
         )
-        frame._dual_view_results_by_document["alpha"] = results
+        frame._document_controller.set_dual_view_results("alpha", results)
         frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))
         documents = [Document("alpha", "text", "a"), Document("beta", "text", "b")]
 
@@ -1595,7 +1635,7 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
 
         self.assertEqual(
             steps.mock_calls,
-            [call.save(), call.export(frame._documents_by_name["alpha"], "brl"), call.output_txt.SetFocus()],
+            [call.save(), call.export(frame._document_controller.get_document("alpha"), "brl"), call.output_txt.SetFocus()],
         )
         event.Skip.assert_not_called()
 
PATCH
```

- [ ] **Step 2: Run them to see the new ones fail.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (only the two ownership tests fail; the moved setup already works through today's forwarding properties):

```text
      1 AssertionError: <documents.controller.DocumentController object at 0x?> is not <documents.controller.DocumentController object at 0x?>
      1 AssertionError: None is not an instance of <class 'documents.controller.DocumentController'>
      1 FAIL: test_frame_creates_its_controller_before_building_the_menu_bar (tests.test_gui_document_flows.DocumentControllerOwnershipTest.test_frame_creates_its_controller_before_building_the_menu_bar)
      1 FAIL: test_initialize_state_keeps_the_frame_controller (tests.test_gui_document_flows.DocumentControllerOwnershipTest.test_initialize_state_keeps_the_frame_controller)
      1 FAILED (failures=2, skipped=2)
      1 Ran 116 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index 5ce5b2a..0109608 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -29,8 +29,6 @@ from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
 from documents.formats import ExportContext, build_export_wildcard, get_format
 from documents.session import (
-    document_name_exists,
-    get_adjacent_document_name,
     format_window_title,
 )
 from documents.workspace import (
@@ -157,6 +155,7 @@ class BrailleFrame(wx.Frame):
 	def __init__(self, *args, runtime: TranslationRuntime, **kwargs):
 		super().__init__(*args, **kwargs)
 		self.translation_runtime = runtime
+		self._document_controller = DocumentController()
 
 		self._initialize_frame()
 		initial_settings = self._initialize_state()
@@ -166,45 +165,6 @@ class BrailleFrame(wx.Frame):
 		self._bind_events()
 		self._load_startup_documents()
 
-	def _get_document_controller(self) -> DocumentController:
-		controller = self.__dict__.get("_document_controller")
-		if controller is None:
-			controller = DocumentController()
-			self._document_controller = controller
-		return controller
-
-	@property
-	def documents(self) -> list[Document]:
-		return self._get_document_controller().documents
-
-	@documents.setter
-	def documents(self, value: list[Document]) -> None:
-		self._get_document_controller().documents = value
-
-	@property
-	def _open_document_name(self) -> str | None:
-		return self._get_document_controller().open_name
-
-	@_open_document_name.setter
-	def _open_document_name(self, value: str | None) -> None:
-		self._get_document_controller().open_name = value
-
-	@property
-	def _selected_document_name(self) -> str | None:
-		return self._get_document_controller().selected_name
-
-	@_selected_document_name.setter
-	def _selected_document_name(self, value: str | None) -> None:
-		self._get_document_controller().selected_name = value
-
-	@property
-	def _dual_view_results_by_document(self) -> dict[str, tuple[object, ...]]:
-		return self._get_document_controller().dual_view_results_by_document
-
-	@_dual_view_results_by_document.setter
-	def _dual_view_results_by_document(self, value: dict[str, tuple[object, ...]]) -> None:
-		self._get_document_controller().dual_view_results_by_document = value
-
 	def _initialize_frame(self) -> None:
 		self.SetSize((900, 600))
 		self.SetMenuBar(self._create_menu_bar())
@@ -220,13 +180,8 @@ class BrailleFrame(wx.Frame):
 		self.translation_settings = load_translation_settings(self._dictionary_presenter.dictionary_names)
 		self.translation_tables = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
 		self.workspace_dir = get_workspace_directory()
-		self._document_controller = DocumentController()
-		self.documents = []
 		self._simbraille_font_available = self._register_output_font()
-		self._selected_document_name = None
-		self._open_document_name = None
 		self._dual_view_frame: DualViewFrame | None = None
-		self._dual_view_results_by_document = {}
 
 		self.view_settings = load_view_settings()
 		return self.view_settings
@@ -361,17 +316,17 @@ class BrailleFrame(wx.Frame):
 
 	def _sync_document_menu_state(self, menu_items: dict[str, wx.MenuItem] | None = None) -> None:
 		target_items = menu_items if menu_items is not None else getattr(self, "_document_menu_items", None)
-		if not target_items or not hasattr(self, "documents") or not hasattr(self, "_selected_document_name"):
+		if not target_items:
 			return
 		selected_document = self._get_selected_document() if "document_list" in self.__dict__ else None
 		menu_state = get_document_menu_enabled_state(
 			has_selection=selected_document is not None,
-			has_documents=bool(self.documents),
+			has_documents=self._document_controller.has_documents,
 		)
 		apply_document_menu_state(target_items, menu_state)
 
 	def _update_window_title(self) -> None:
-		self.SetTitle(_(format_window_title(self._open_document_name)))
+		self.SetTitle(_(format_window_title(self._document_controller.open_document_name)))
 
 	def _create_dual_view_frame(self) -> DualViewFrame:
 		return DualViewFrame(self, title=_("Dual View"), on_closed=self._on_dual_view_closed)
@@ -381,7 +336,8 @@ class BrailleFrame(wx.Frame):
 			self._dual_view_frame = None
 
 	def _render_dual_view_for_open_document(self) -> str:
-		results = self._dual_view_results_by_document.get(self._open_document_name or "", ())
+		controller = self._document_controller
+		results = controller.get_dual_view_results(controller.open_document_name)
 		return render_dual_view_html(
 			build_dual_view_model(results),
 			empty_message=_("No conversion data is available for this document."),
@@ -514,9 +470,6 @@ class BrailleFrame(wx.Frame):
 			parent=parent or self,
 		)
 
-	def _get_document_names(self) -> list[str]:
-		return self._get_document_controller().document_names
-
 	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
 		try:
 			webbrowser.open(about.url)
@@ -555,43 +508,30 @@ class BrailleFrame(wx.Frame):
 			viewer.raise_without_activating()
 		event.Skip()
 
-	def _sort_documents(self) -> None:
-		self._get_document_controller().sort_documents()
-
-	def _get_document_by_name(self, name: str | None) -> Document | None:
-		return self._get_document_controller().get_document(name)
-
-	def _replace_document(self, updated_document: Document) -> None:
-		self._get_document_controller().replace_document(updated_document)
-
-	def _document_name_exists(self, name: str, exclude_name: str | None = None) -> bool:
-		return document_name_exists(self._get_document_controller().documents, name, exclude_name=exclude_name)
-
 	def _clear_document_selection(self) -> None:
 		selection = self.document_list.GetFirstSelected()
 		while selection != wx.NOT_FOUND:
 			self.document_list.Select(selection, on=0)
 			selection = self.document_list.GetFirstSelected()
-		self._selected_document_name = None
+		self._document_controller.select_document(None)
 		self._sync_document_menu_state()
 
 	def _refresh_document_list(self, preferred_name: str | None = None) -> None:
-		self._sort_documents()
+		controller = self._document_controller
+		controller.sort_documents()
 		self.document_list.DeleteAllItems()
-		documents = self.documents
-		for document in documents:
-			self.document_list.InsertItem(self.document_list.GetItemCount(), document.name)
-		if not documents:
-			self._selected_document_name = None
+		names = controller.document_names
+		for name in names:
+			self.document_list.InsertItem(self.document_list.GetItemCount(), name)
+		if not names:
+			controller.select_document(None)
 			self._sync_document_menu_state()
 			return
-		selected_name = preferred_name if preferred_name in self._get_document_names() else documents[0].name
-		self._selected_document_name = selected_name
-		for index, document in enumerate(documents):
-			if document.name == selected_name:
-				self.document_list.Select(index)
-				self.document_list.Focus(index)
-				break
+		selected_name = preferred_name if preferred_name in names else names[0]
+		controller.select_document(selected_name)
+		index = names.index(selected_name)
+		self.document_list.Select(index)
+		self.document_list.Focus(index)
 		self._sync_document_menu_state()
 
 	def _clear_document_editors(self) -> None:
@@ -683,7 +623,7 @@ class BrailleFrame(wx.Frame):
 		DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)
 
 	def _open_document_by_name(self, name: str | None) -> None:
-		document = self._get_document_controller().open_document(name)
+		document = self._document_controller.open_document(name)
 		if document is None:
 			self._clear_document_editors()
 			self._update_window_title()
@@ -691,16 +631,12 @@ class BrailleFrame(wx.Frame):
 			return
 		self._load_document_into_editors(document)
 		self._reset_input_cursor_to_start()
-		self._refresh_document_list(self._selected_document_name)
+		self._refresh_document_list(self._document_controller.selected_document_name)
 		self._update_window_title()
 		self._refresh_dual_view()
 
 	def _open_adjacent_document(self, step: int) -> None:
-		target_name = get_adjacent_document_name(
-			self.documents,
-			self._open_document_name or self._selected_document_name,
-			step,
-		)
+		target_name = self._document_controller.adjacent_document_name(step)
 		if not target_name:
 			return
 		if not self._save_open_document_with_feedback():
@@ -709,9 +645,10 @@ class BrailleFrame(wx.Frame):
 		self.input_txt.SetFocus()
 
 	def _save_open_document(self) -> None:
-		if not self._open_document_name:
+		open_name = self._document_controller.open_document_name
+		if not open_name:
 			return
-		document = self._get_document_by_name(self._open_document_name)
+		document = self._document_controller.get_document(open_name)
 		if document is None:
 			return
 		updated_document = prepare_document_for_save(
@@ -719,7 +656,7 @@ class BrailleFrame(wx.Frame):
 			text=self.input_txt.GetValue(),
 			braille=self.output_txt.GetValue(),
 		)
-		self._replace_document(updated_document)
+		self._document_controller.replace_document(updated_document)
 		save_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)
 
 	def _save_open_document_with_feedback(self) -> bool:
@@ -758,7 +695,7 @@ class BrailleFrame(wx.Frame):
 		except OSError as exc:
 			self._show_file_error(_("Failed to save document: {error}"), exc)
 			return False
-		self.documents.append(document)
+		self._document_controller.add_document(document)
 		self._refresh_document_list(document.name)
 		self._open_document_by_name(document.name)
 		if focus_input:
@@ -777,7 +714,7 @@ class BrailleFrame(wx.Frame):
 				if dialog.ShowModal() != wx.ID_OK:
 					return None
 				document_name = normalize_document_name(dialog.get_document_name())
-			if self._document_name_exists(document_name, exclude_name=exclude_name):
+			if self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):
 				wx.MessageBox(
 					_('Document "{name}" already exists.').format(name=document_name),
 					_("Error"),
@@ -798,9 +735,9 @@ class BrailleFrame(wx.Frame):
 		)
 
 	def _ensure_open_document_exists(self) -> None:
-		documents = self.documents
-		if documents:
-			self._open_document_by_name(documents[0].name)
+		first_name = self._document_controller.first_document_name
+		if first_name is not None:
+			self._open_document_by_name(first_name)
 			return
 		self._create_default_document()
 
@@ -819,29 +756,25 @@ class BrailleFrame(wx.Frame):
 	def _load_workspace_documents_at_startup(self) -> None:
 		self.workspace_dir = ensure_workspace_directory(self.workspace_dir)
 		documents, invalid_paths = load_workspace_documents(self.workspace_dir)
-		self.documents = documents
+		self._document_controller.load_documents(documents)
 		self._refresh_document_list()
 		self._review_invalid_workspace_files(invalid_paths)
 		self._ensure_open_document_exists()
 		self._update_window_title()
 
 	def _get_selected_document_name(self) -> str | None:
+		controller = self._document_controller
 		if "document_list" not in self.__dict__:
-			return self._selected_document_name
-		selection = self.document_list.GetFirstSelected()
-		if selection == wx.NOT_FOUND or selection >= len(self.documents):
-			return self._selected_document_name
-		return self.documents[selection].name
+			return controller.selected_document_name
+		name = controller.document_name_at(self.document_list.GetFirstSelected())
+		return name if name is not None else controller.selected_document_name
 
 	def _get_selected_document(self) -> Document | None:
-		return self._get_document_by_name(self._get_selected_document_name())
+		return self._document_controller.get_document(self._get_selected_document_name())
 
 	def on_document_selection_changed(self, event: wx.ListEvent) -> None:
-		selection = self.document_list.GetFirstSelected()
-		if selection == wx.NOT_FOUND or selection >= len(self.documents):
-			self._selected_document_name = None
-		else:
-			self._selected_document_name = self.documents[selection].name
+		controller = self._document_controller
+		controller.select_document(controller.document_name_at(self.document_list.GetFirstSelected()))
 		self._sync_document_menu_state()
 		event.Skip()
 
@@ -853,10 +786,11 @@ class BrailleFrame(wx.Frame):
 		client_position = self.document_list.ScreenToClient(position) if position != wx.DefaultPosition else wx.Point(0, 0)
 		item_index, _flags = self.document_list.HitTest(client_position)
 		selected_index = self.document_list.GetFirstSelected()
-		if item_index != wx.NOT_FOUND and item_index < len(self.documents):
+		item_name = self._document_controller.document_name_at(item_index)
+		if item_name is not None:
 			self.document_list.Select(item_index)
 			self.document_list.Focus(item_index)
-			self._selected_document_name = self.documents[item_index].name
+			self._document_controller.select_document(item_name)
 		elif position == wx.DefaultPosition and selected_index != wx.NOT_FOUND:
 			item_index = selected_index
 		else:
@@ -888,12 +822,12 @@ class BrailleFrame(wx.Frame):
 
 	def on_rename_document(self, _evt) -> None:
 		selected_name = self._get_selected_document_name()
-		selected_document = self._get_document_by_name(selected_name)
+		selected_document = self._document_controller.get_document(selected_name)
 		if selected_document is None:
 			return
 		if not self._save_open_document_with_feedback():
 			return
-		selected_document = self._get_document_by_name(selected_name)
+		selected_document = self._document_controller.get_document(selected_name)
 		if selected_document is None:
 			return
 		new_name = self._prompt_for_document_name(
@@ -941,10 +875,11 @@ class BrailleFrame(wx.Frame):
 			self._show_file_error(_("Failed to delete document: {error}"), exc)
 			return
 		delete_decision = self._document_controller.delete_document(selected_document.name)
-		self._refresh_document_list(self._selected_document_name)
-		if self.documents:
-			if delete_decision.was_open and self._open_document_name:
-				self._open_document_by_name(self._open_document_name)
+		self._refresh_document_list(self._document_controller.selected_document_name)
+		if self._document_controller.has_documents:
+			open_name = self._document_controller.open_document_name
+			if delete_decision.was_open and open_name:
+				self._open_document_by_name(open_name)
 		else:
 			self._update_window_title()
 			self._clear_document_editors()
@@ -952,7 +887,7 @@ class BrailleFrame(wx.Frame):
 		self._refresh_dual_view()
 
 	def on_delete_all_documents(self, _evt) -> None:
-		if not self.documents:
+		if not self._document_controller.has_documents:
 			return
 		if not self._save_open_document_with_feedback():
 			return
@@ -964,7 +899,7 @@ class BrailleFrame(wx.Frame):
 		)
 		if confirmation != wx.YES:
 			return
-		for document in list(self.documents):
+		for document in self._document_controller.documents_snapshot():
 			try:
 				package_path = document_package_path_for_name(document.name, self.workspace_dir)
 				if package_path.exists():
@@ -975,8 +910,8 @@ class BrailleFrame(wx.Frame):
 				self._document_controller.restore_documents_after_delete_all_failure(remaining_documents)
 				self._refresh_document_list()
 				self._review_invalid_workspace_files(invalid_paths)
-				if self.documents:
-					self._open_document_by_name(self.documents[0].name)
+				if self._document_controller.has_documents:
+					self._open_document_by_name(self._document_controller.first_document_name)
 				else:
 					self._clear_document_editors()
 				self._refresh_dual_view()
@@ -1009,14 +944,15 @@ class BrailleFrame(wx.Frame):
 		documents, issues = batch_import_documents(
 			source_paths,
 			format_key=format_key,
-			existing_names=set(self._get_document_names()),
+			existing_names=set(self._document_controller.document_names),
 		)
 		saved_documents, save_issues = self._persist_documents(documents)
-		self.documents.extend(saved_documents)
+		self._document_controller.add_documents(saved_documents)
 		if len(saved_documents) == 1:
 			self._open_document_by_name(saved_documents[0].name)
 		else:
-			self._refresh_document_list(self._open_document_name or self._selected_document_name)
+			controller = self._document_controller
+			self._refresh_document_list(controller.open_document_name or controller.selected_document_name)
 		self._show_file_issues_dialog(
 			_("Import Issues"),
 			_("Some files were skipped during import."),
@@ -1033,7 +969,7 @@ class BrailleFrame(wx.Frame):
 		self._export_document_with_dialog(selected_document, format_key)
 
 	def on_export_all_documents(self, format_key: str) -> None:
-		if not self.documents:
+		if not self._document_controller.has_documents:
 			return
 		if not self._save_open_document_with_feedback():
 			return
@@ -1042,10 +978,11 @@ class BrailleFrame(wx.Frame):
 				return
 			destination_dir = Path(dir_dialog.GetPath())
 		suffix = get_format(format_key).extension
-		conflicts = [destination_dir / f"{document.name}{suffix}" for document in self.documents if (destination_dir / f"{document.name}{suffix}").exists()]
+		documents = self._document_controller.documents_snapshot()
+		conflicts = [destination_dir / f"{document.name}{suffix}" for document in documents if (destination_dir / f"{document.name}{suffix}").exists()]
 		if conflicts and not self._confirm_overwrite_all(conflicts):
 			return
-		self._export_next_document(list(self.documents), destination_dir, format_key, ExportBatchResult())
+		self._export_next_document(documents, destination_dir, format_key, ExportBatchResult())
 
 	def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
 		step = get_font_size_step_from_wheel(event.GetWheelRotation(), event.ControlDown())
@@ -1072,7 +1009,8 @@ class BrailleFrame(wx.Frame):
 	def on_output_text_key_down(self, event: wx.KeyEvent) -> None:
 		if is_brl_export_shortcut(event.GetKeyCode(), event.ControlDown()):
 			if self._save_open_document_with_feedback():
-				document = self._get_document_by_name(self._open_document_name)
+				controller = self._document_controller
+				document = controller.get_document(controller.open_document_name)
 				if document is not None:
 					self._export_document_with_dialog(document, get_format("brl").key)
 			self.output_txt.SetFocus()
@@ -1127,7 +1065,7 @@ class BrailleFrame(wx.Frame):
 		descriptor = get_format(format_key)
 		if not descriptor.exportable or descriptor.writer is None:
 			raise ValueError(f'Unsupported export format: "{format_key}".')
-		context = ExportContext(dual_view_results=self._dual_view_results_by_document.get(document.name, ()))
+		context = ExportContext(dual_view_results=self._document_controller.get_dual_view_results(document.name))
 		descriptor.writer(destination_path, document, context)
 
 	def _continue_single_export(self, document: Document, destination_path: Path, format_key: str) -> None:
@@ -1366,17 +1304,19 @@ class BrailleFrame(wx.Frame):
 		if update_output:
 			self.output_txt.SetValue(converted_braille)
 			self.output_txt.SetFocus()
-			if self._open_document_name:
-				document = self._get_document_by_name(self._open_document_name)
+			controller = self._document_controller
+			open_name = controller.open_document_name
+			if open_name:
+				document = controller.get_document(open_name)
 				if document is not None:
-					self._replace_document(
+					controller.replace_document(
 						Document(
 							document.name,
 							self.input_txt.GetValue(),
 							converted_braille,
 						)
 					)
-				self._dual_view_results_by_document[self._open_document_name] = output.dual_view_segments
+				controller.set_dual_view_results(open_name, output.dual_view_segments)
 			self._refresh_dual_view()
 		if on_success is not None:
 			on_success(converted_braille)
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and acceptance criteria 1, 2 and 5.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 683 67 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo AC1; grep -nE '@property|\.setter|_get_document_controller' gui.py
echo AC2; grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' gui.py
echo AC5; grep -nE 'hasattr\(self, "(documents|_selected_document_name)"\)' gui.py
echo end
```

Expected (nothing between the labels):

```text
Ran 116 tests
OK (skipped=2)
Ran 683 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (683)
new tests ok: 67 (expected 67)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
AC1
AC2
AC5
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: move document frame state onto the controller

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: move document frame state onto the controller
```

---

### Task 5: Startup, invalid-file review, save and create through the service (spec step 5)

**Files:**
- Modify: `client/gui.py` (import `DocumentWorkspaceService`; `_initialize_state` creates `self._workspace_service = DocumentWorkspaceService(self._document_controller, get_workspace_directory())` instead of `self.workspace_dir`; `_save_open_document`, `_review_invalid_workspace_files`, `_create_document`, `_load_workspace_documents_at_startup` call the service; the IO still in `gui` (import persistence, rename, delete, Delete All) reads `self._workspace_service.workspace_dir` until Tasks 6-7; drop the `ensure_workspace_directory` and `prepare_document_for_save` imports)
- Test: `client/tests/test_gui_document_flows.py` (new class `FrameWorkspaceServiceDelegationTest` with 6 tests; `GuiDocumentFlowsTest._make_frame` adds a service on the placeholder directory `Path("unused-workspace")`; the two `_initialize_state` tests set `frame._document_controller = DocumentController()` first; `test_save_open_document_saves_prepared_document` rewritten with a temporary workspace (spec correction 2); the Delete All test drops its dead `frame.workspace_dir`; then, with the implementation, the characterization helper's `workspace_dir` line becomes the service line)

**Interfaces:**
- Consumes: Task 3's service.
- Produces: `BrailleFrame._workspace_service` (created once in `_initialize_state`, bound to the frame's controller); `FrameWorkspaceServiceDelegationTest._make_frame(documents=(), open_name=None, selected_name=None)` (a `Mock` service whose `workspace_dir` is a temporary directory; the frame's UI steps `_refresh_document_list`, `_open_document_by_name`, `_update_window_title`, `_refresh_dual_view`, `_clear_document_editors`, `_ensure_open_document_exists`, `_review_invalid_workspace_files`, `_show_file_issues_dialog` are recorded in order on `frame.ui`).

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index e7a3216..66de928 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -7,7 +7,7 @@ import zipfile
 from dataclasses import replace
 from pathlib import Path
 from types import SimpleNamespace
-from unittest.mock import DEFAULT, Mock, call, patch
+from unittest.mock import ANY, DEFAULT, Mock, call, patch
 
 from tests import wx_stub
 from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
@@ -25,6 +25,7 @@ tearDownModule = _SCOPE.deactivate
 
 from documents.controller import DocumentController
 from documents.workspace import Document, load_document_package, save_document_package
+from documents.workspace_service import DocumentWorkspaceService
 from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
@@ -63,6 +64,7 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame._show_export_all_result = Mock()
         frame._dual_view_frame = None
         frame._document_controller = DocumentController(documents=list(documents), open_name=open_name)
+        frame._workspace_service = DocumentWorkspaceService(frame._document_controller, Path("unused-workspace"))
         frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
         return frame
 
@@ -274,6 +276,130 @@ class DocumentControllerOwnershipTest(unittest.TestCase):
         self.assertEqual(controller.open_document_name, "alpha")
 
 
+class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
+    """The frame hands workspace IO to its service and keeps the dialogs and UI updates."""
+
+    UI_STEPS = (
+        "_refresh_document_list",
+        "_open_document_by_name",
+        "_update_window_title",
+        "_refresh_dual_view",
+        "_clear_document_editors",
+        "_ensure_open_document_exists",
+        "_review_invalid_workspace_files",
+        "_show_file_issues_dialog",
+    )
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.workspace = Path(temp_dir.name)
+
+    def _make_frame(self, documents=(), open_name=None, selected_name=None) -> gui.BrailleFrame:
+        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController(
+            documents=list(documents),
+            open_name=open_name,
+            selected_name=selected_name,
+        )
+        frame._workspace_service = Mock()
+        frame._workspace_service.workspace_dir = self.workspace
+        frame.input_txt = Mock()
+        frame.output_txt = Mock()
+        frame._show_file_error = Mock()
+        frame._save_open_document_with_feedback = Mock(return_value=True)
+        frame.ui = Mock()
+        for name in self.UI_STEPS:
+            setattr(frame, name, getattr(frame.ui, name))
+        return frame
+
+    def test_initialize_state_creates_service_for_frame_controller(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController()
+        frame._register_output_font = Mock(return_value=False)
+        with (
+            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
+            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
+            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
+            patch.object(gui, "get_workspace_directory", return_value=self.workspace),
+            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
+            patch.object(gui, "load_translation_tables", return_value={}),
+        ):
+            frame._initialize_state()
+
+        service = frame._workspace_service
+        self.assertEqual(service.workspace_dir, self.workspace)
+        service.create_document(Document("beta", "", ""))
+        self.assertEqual(frame._document_controller.document_names, ["beta"])
+        self.assertTrue((self.workspace / "beta.dep").is_file())
+
+    def test_startup_loads_through_service_and_reviews_returned_paths(self) -> None:
+        frame = self._make_frame()
+        invalid_paths = [self.workspace / "bad.dep"]
+        frame._workspace_service.load_documents.return_value = invalid_paths
+
+        frame._load_workspace_documents_at_startup()
+
+        frame._workspace_service.load_documents.assert_called_once_with()
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [
+                call._refresh_document_list(),
+                call._review_invalid_workspace_files(invalid_paths),
+                call._ensure_open_document_exists(),
+                call._update_window_title(),
+            ],
+        )
+
+    def test_save_open_document_passes_editor_text_to_service(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha")
+        frame.input_txt.GetValue.return_value = "edited"
+        frame.output_txt.GetValue.return_value = "edited braille"
+
+        frame._save_open_document()
+
+        frame._workspace_service.save_open_document.assert_called_once_with(text="edited", braille="edited braille")
+
+    def test_create_document_adds_through_service_then_opens_it(self) -> None:
+        frame = self._make_frame()
+
+        self.assertTrue(frame._create_document("beta", focus_input=True))
+
+        frame._workspace_service.create_document.assert_called_once_with(Document("beta", "", ""))
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [call._refresh_document_list("beta"), call._open_document_by_name("beta")],
+        )
+        frame.input_txt.SetFocus.assert_called_once_with()
+
+    def test_create_document_failure_shows_error_and_stops(self) -> None:
+        frame = self._make_frame()
+        error = OSError("disk full")
+        frame._workspace_service.create_document.side_effect = error
+
+        self.assertFalse(frame._create_document("beta"))
+
+        frame._show_file_error.assert_called_once_with(gui._("Failed to save document: {error}"), error)
+        self.assertEqual(frame.ui.mock_calls, [])
+
+    def test_invalid_file_review_deletes_through_service_and_reports_errors(self) -> None:
+        frame = self._make_frame()
+        invalid_paths = [self.workspace / "bad.dep", self.workspace / "worse.dep"]
+        error = OSError("locked")
+        frame._workspace_service.delete_invalid_files.side_effect = lambda paths, on_error: on_error(error)
+        dialog = Mock()
+        dialog.__enter__ = Mock(return_value=dialog)
+        dialog.__exit__ = Mock(return_value=False)
+        dialog.should_delete_invalid_files.return_value = True
+
+        with patch.object(gui, "InvalidWorkspaceFilesDialog", Mock(return_value=dialog)) as dialog_class:
+            gui.BrailleFrame._review_invalid_workspace_files(frame, invalid_paths)
+
+        dialog_class.assert_called_once_with(frame, invalid_paths)
+        frame._workspace_service.delete_invalid_files.assert_called_once_with(invalid_paths, on_error=ANY)
+        frame._show_file_error.assert_called_once_with(gui._("Failed to delete invalid workspace file: {error}"), error)
+
+
 class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
         frame = object.__new__(gui.BrailleFrame)
@@ -756,7 +882,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
                 Document("beta", "text-b", "braille-b"),
             ),
         )
-        frame.workspace_dir = Path("/workspace")
         frame._document_controller.set_dual_view_results("alpha", ("stale-alpha",))
         frame._document_controller.set_dual_view_results("beta", ("fresh-beta",))
         frame._document_controller.set_dual_view_results("ghost", ("stale-ghost",))
@@ -923,6 +1048,7 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def _initialize_state_with_loaded_tables(self, loaded_tables: dict[str, str]):
         frame = object.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController()
         frame._register_output_font = Mock(return_value=False)
         with (
             patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
@@ -1117,19 +1243,18 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def test_save_open_document_saves_prepared_document(self) -> None:
         frame = self._make_frame(documents=(Document("alpha", "source", "old braille"),))
-        frame.workspace_dir = Path("workspace")
         frame.input_txt.GetValue.return_value = "edited"
         frame.output_txt.GetValue.return_value = "edited braille"
 
-        with patch.object(gui, "save_document_package") as save_package:
+        with tempfile.TemporaryDirectory() as directory:
+            workspace = Path(directory)
+            frame._workspace_service = DocumentWorkspaceService(frame._document_controller, workspace)
             frame._save_open_document()
+            saved = load_document_package(workspace / "alpha.dep")
 
         expected = Document("alpha", "edited", "edited braille")
         self.assertEqual(frame._document_controller.get_document("alpha"), expected)
-        save_package.assert_called_once_with(
-            gui.document_package_path_for_name("alpha", Path("workspace")),
-            expected,
-        )
+        self.assertEqual(saved, expected)
 
     def test_open_settings_uses_singleton_dialog(self) -> None:
         frame = object.__new__(gui.BrailleFrame)
@@ -1209,6 +1334,7 @@ class DictionaryManagementFrameTest(unittest.TestCase):
             dictionary_dir = Path(temp_dir)
             (dictionary_dir / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
             frame = object.__new__(gui.BrailleFrame)
+            frame._document_controller = DocumentController()
             frame._register_output_font = Mock(return_value=False)
             with (
                 patch.object(gui, "get_dictionary_directory", return_value=dictionary_dir),
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (today's code reads `self.workspace_dir`, which the new frames do not set, so the stub hands it a function; the review test sees no service call; the service test finds no service):

```text
      1 AssertionError: Expected 'delete_invalid_files' to be called once. Called 0 times.
      1 AttributeError: 'function' object has no attribute 'workspace_dir'
      1 ERROR: test_create_document_adds_through_service_then_opens_it (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_create_document_adds_through_service_then_opens_it)
      1 ERROR: test_create_document_failure_shows_error_and_stops (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_create_document_failure_shows_error_and_stops)
      1 ERROR: test_initialize_state_creates_service_for_frame_controller (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_initialize_state_creates_service_for_frame_controller)
      1 ERROR: test_save_open_document_passes_editor_text_to_service (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_save_open_document_passes_editor_text_to_service)
      1 ERROR: test_save_open_document_saves_prepared_document (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_save_open_document_saves_prepared_document)
      1 ERROR: test_startup_loads_through_service_and_reviews_returned_paths (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_startup_loads_through_service_and_reviews_returned_paths)
      1 FAIL: test_invalid_file_review_deletes_through_service_and_reports_errors (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_invalid_file_review_deletes_through_service_and_reports_errors)
      1 FAILED (failures=1, errors=6, skipped=2)
      1 Ran 122 tests
      5 TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
```

- [ ] **Step 3: Implement, and give the characterization helper the service.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index 0109608..d683377 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -38,13 +38,12 @@ from documents.workspace import (
     batch_import_documents,
     create_default_document,
     document_package_path_for_name,
-    ensure_workspace_directory,
 	get_workspace_directory,
     load_workspace_documents,
     normalize_document_name,
-    prepare_document_for_save,
     save_document_package,
 )
+from documents.workspace_service import DocumentWorkspaceService
 from documents.export_results import (
     ExportBatchResult,
 )
@@ -179,7 +178,7 @@ class BrailleFrame(wx.Frame):
 		self._dictionary_presenter.refresh()
 		self.translation_settings = load_translation_settings(self._dictionary_presenter.dictionary_names)
 		self.translation_tables = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
-		self.workspace_dir = get_workspace_directory()
+		self._workspace_service = DocumentWorkspaceService(self._document_controller, get_workspace_directory())
 		self._simbraille_font_available = self._register_output_font()
 		self._dual_view_frame: DualViewFrame | None = None
 
@@ -645,19 +644,10 @@ class BrailleFrame(wx.Frame):
 		self.input_txt.SetFocus()
 
 	def _save_open_document(self) -> None:
-		open_name = self._document_controller.open_document_name
-		if not open_name:
-			return
-		document = self._document_controller.get_document(open_name)
-		if document is None:
-			return
-		updated_document = prepare_document_for_save(
-			document,
+		self._workspace_service.save_open_document(
 			text=self.input_txt.GetValue(),
 			braille=self.output_txt.GetValue(),
 		)
-		self._document_controller.replace_document(updated_document)
-		save_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)
 
 	def _save_open_document_with_feedback(self) -> bool:
 		try:
@@ -675,11 +665,10 @@ class BrailleFrame(wx.Frame):
 			delete_invalid = dialog.should_delete_invalid_files()
 		if not delete_invalid:
 			return
-		for invalid_path in invalid_paths:
-			try:
-				invalid_path.unlink(missing_ok=True)
-			except OSError as exc:
-				self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc)
+		self._workspace_service.delete_invalid_files(
+			invalid_paths,
+			on_error=lambda exc: self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc),
+		)
 
 	def _create_document(
 		self,
@@ -691,11 +680,10 @@ class BrailleFrame(wx.Frame):
 	) -> bool:
 		document = Document(name=document_name, text=text, braille=braille)
 		try:
-			save_document_package(document_package_path_for_name(document.name, self.workspace_dir), document)
+			self._workspace_service.create_document(document)
 		except OSError as exc:
 			self._show_file_error(_("Failed to save document: {error}"), exc)
 			return False
-		self._document_controller.add_document(document)
 		self._refresh_document_list(document.name)
 		self._open_document_by_name(document.name)
 		if focus_input:
@@ -746,17 +734,15 @@ class BrailleFrame(wx.Frame):
 		issues: list[BatchIssue] = []
 		for document in documents:
 			try:
-				save_document_package(document_package_path_for_name(document.name, self.workspace_dir), document)
+				save_document_package(document_package_path_for_name(document.name, self._workspace_service.workspace_dir), document)
 			except OSError as exc:
-				issues.append(BatchIssue(path=document_package_path_for_name(document.name, self.workspace_dir), reason=str(exc)))
+				issues.append(BatchIssue(path=document_package_path_for_name(document.name, self._workspace_service.workspace_dir), reason=str(exc)))
 				continue
 			saved_documents.append(document)
 		return saved_documents, issues
 
 	def _load_workspace_documents_at_startup(self) -> None:
-		self.workspace_dir = ensure_workspace_directory(self.workspace_dir)
-		documents, invalid_paths = load_workspace_documents(self.workspace_dir)
-		self._document_controller.load_documents(documents)
+		invalid_paths = self._workspace_service.load_documents()
 		self._refresh_document_list()
 		self._review_invalid_workspace_files(invalid_paths)
 		self._ensure_open_document_exists()
@@ -839,8 +825,8 @@ class BrailleFrame(wx.Frame):
 			return
 		try:
 			renamed_document = Document(name=new_name, text=selected_document.text, braille=selected_document.braille)
-			save_document_package(document_package_path_for_name(renamed_document.name, self.workspace_dir), renamed_document)
-			old_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
+			save_document_package(document_package_path_for_name(renamed_document.name, self._workspace_service.workspace_dir), renamed_document)
+			old_path = document_package_path_for_name(selected_document.name, self._workspace_service.workspace_dir)
 			if old_path.exists():
 				old_path.unlink()
 		except OSError as exc:
@@ -868,7 +854,7 @@ class BrailleFrame(wx.Frame):
 		if confirmation != wx.YES:
 			return
 		try:
-			package_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
+			package_path = document_package_path_for_name(selected_document.name, self._workspace_service.workspace_dir)
 			if package_path.exists():
 				package_path.unlink()
 		except OSError as exc:
@@ -901,12 +887,12 @@ class BrailleFrame(wx.Frame):
 			return
 		for document in self._document_controller.documents_snapshot():
 			try:
-				package_path = document_package_path_for_name(document.name, self.workspace_dir)
+				package_path = document_package_path_for_name(document.name, self._workspace_service.workspace_dir)
 				if package_path.exists():
 					package_path.unlink()
 			except OSError as exc:
 				self._show_file_error(_("Failed to delete document: {error}"), exc)
-				remaining_documents, invalid_paths = load_workspace_documents(self.workspace_dir)
+				remaining_documents, invalid_paths = load_workspace_documents(self._workspace_service.workspace_dir)
 				self._document_controller.restore_documents_after_delete_all_failure(remaining_documents)
 				self._refresh_document_list()
 				self._review_invalid_workspace_files(invalid_paths)
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 66de928..117d1fe 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1945,7 +1945,7 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
             open_name=open_name,
             selected_name=selected_name,
         )
-        frame.workspace_dir = self.workspace
+        frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)
         open_document = next((document for document in documents if document.name == open_name), None)
         frame.input_txt = _FakeEditor("input", self.events, open_document.text if open_document else "")
         frame.output_txt = _FakeEditor("output", self.events, (open_document.braille or "") if open_document else "")
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 689 73 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
grep -nE '\bworkspace_dir\b' gui.py | sed -E 's/^([0-9]+):.*(self\._workspace_service\.workspace_dir).*/\1: \2/'
git -C $REPO status --short
```

Expected (seven direct-IO reads of the service's directory remain, all removed by Tasks 6-7; no stray `unused-workspace` directory):

```text
Ran 122 tests
OK (skipped=2)
Ran 689 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (689)
new tests ok: 73 (expected 73)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
737: self._workspace_service.workspace_dir
739: self._workspace_service.workspace_dir
828: self._workspace_service.workspace_dir
829: self._workspace_service.workspace_dir
857: self._workspace_service.workspace_dir
890: self._workspace_service.workspace_dir
895: self._workspace_service.workspace_dir
 M client/gui.py
 M client/tests/test_gui_document_flows.py
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: route startup, save and create through the workspace service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: route startup, save and create through the workspace service
```

---

### Task 6: Import through the service (spec step 6)

**Files:**
- Modify: `client/gui.py` (`on_import_document` calls `import_files` and uses `result.saved` / `result.issues`; delete `_persist_documents`; drop the `batch_import_documents` import)
- Test: `client/tests/test_gui_document_flows.py` (one new delegation test)

**Interfaces:**
- Consumes: `DocumentWorkspaceService.import_files(paths, *, format_key) -> ImportResult`.
- Produces: no new names. The dialog part of `on_import_document` is unchanged.

- [ ] **Step 1: Write the failing test.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 117d1fe..d98966d 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -24,8 +24,8 @@ setUpModule = _SCOPE.activate
 tearDownModule = _SCOPE.deactivate
 
 from documents.controller import DocumentController
-from documents.workspace import Document, load_document_package, save_document_package
-from documents.workspace_service import DocumentWorkspaceService
+from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
+from documents.workspace_service import DocumentWorkspaceService, ImportResult
 from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
@@ -399,6 +399,39 @@ class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
         frame._workspace_service.delete_invalid_files.assert_called_once_with(invalid_paths, on_error=ANY)
         frame._show_file_error.assert_called_once_with(gui._("Failed to delete invalid workspace file: {error}"), error)
 
+    def test_import_hands_chosen_files_to_service_and_shows_its_result(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha")
+        issue = BatchIssue(path=Path("x.txt"), reason="bad")
+        frame._workspace_service.import_files.return_value = ImportResult(
+            saved=[Document("beta", "b", None)],
+            issues=[issue],
+        )
+        dialog = Mock()
+        dialog.__enter__ = Mock(return_value=dialog)
+        dialog.__exit__ = Mock(return_value=False)
+        dialog.ShowModal.return_value = gui.wx.ID_OK
+        dialog.GetFilterIndex.return_value = gui.ALL_SUPPORTED_FILTER_INDEX
+        dialog.GetPaths.return_value = [str(self.workspace / "beta.txt")]
+
+        with patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)):
+            frame.on_import_document(None)
+
+        frame._workspace_service.import_files.assert_called_once_with(
+            [self.workspace / "beta.txt"],
+            format_key=gui.get_import_filters()[gui.ALL_SUPPORTED_FILTER_INDEX].key,
+        )
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [
+                call._open_document_by_name("beta"),
+                call._show_file_issues_dialog(
+                    gui._("Import Issues"),
+                    gui._("Some files were skipped during import."),
+                    [issue],
+                ),
+            ],
+        )
+
 
 class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
PATCH
```

- [ ] **Step 2: Run it to see it fail.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected:

```text
      1 AssertionError: Expected 'import_files' to be called once. Called 0 times.
      1 FAIL: test_import_hands_chosen_files_to_service_and_shows_its_result (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_import_hands_chosen_files_to_service_and_shows_its_result)
      1 FAILED (failures=1, skipped=2)
      1 Ran 123 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index d683377..df7d076 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -35,7 +35,6 @@ from documents.workspace import (
     BatchIssue,
     DEFAULT_DOCUMENT_NAME,
     Document,
-    batch_import_documents,
     create_default_document,
     document_package_path_for_name,
 	get_workspace_directory,
@@ -729,18 +728,6 @@ class BrailleFrame(wx.Frame):
 			return
 		self._create_default_document()
 
-	def _persist_documents(self, documents: list[Document]) -> tuple[list[Document], list[BatchIssue]]:
-		saved_documents: list[Document] = []
-		issues: list[BatchIssue] = []
-		for document in documents:
-			try:
-				save_document_package(document_package_path_for_name(document.name, self._workspace_service.workspace_dir), document)
-			except OSError as exc:
-				issues.append(BatchIssue(path=document_package_path_for_name(document.name, self._workspace_service.workspace_dir), reason=str(exc)))
-				continue
-			saved_documents.append(document)
-		return saved_documents, issues
-
 	def _load_workspace_documents_at_startup(self) -> None:
 		invalid_paths = self._workspace_service.load_documents()
 		self._refresh_document_list()
@@ -927,22 +914,16 @@ class BrailleFrame(wx.Frame):
 				filter_index = ALL_SUPPORTED_FILTER_INDEX
 			format_key = import_filters[filter_index].key
 			source_paths = [Path(path) for path in file_dialog.GetPaths()]
-		documents, issues = batch_import_documents(
-			source_paths,
-			format_key=format_key,
-			existing_names=set(self._document_controller.document_names),
-		)
-		saved_documents, save_issues = self._persist_documents(documents)
-		self._document_controller.add_documents(saved_documents)
-		if len(saved_documents) == 1:
-			self._open_document_by_name(saved_documents[0].name)
+		result = self._workspace_service.import_files(source_paths, format_key=format_key)
+		if len(result.saved) == 1:
+			self._open_document_by_name(result.saved[0].name)
 		else:
 			controller = self._document_controller
 			self._refresh_document_list(controller.open_document_name or controller.selected_document_name)
 		self._show_file_issues_dialog(
 			_("Import Issues"),
 			_("Some files were skipped during import."),
-			issues + save_issues,
+			result.issues,
 		)
 
 	def on_export_document(self, format_key: str) -> None:
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 690 74 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
grep -cE '_persist_documents|batch_import_documents' gui.py
```

Expected:

```text
Ran 123 tests
OK (skipped=2)
Ran 690 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (690)
new tests ok: 74 (expected 74)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
0
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: route document import through the workspace service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: route document import through the workspace service
```

---

### Task 7: Rename, Delete and Delete All through the service (spec step 7)

**Files:**
- Modify: `client/gui.py` (`on_rename_document`, `on_delete_document`, `on_delete_all_documents` call the service inside the same `try/except OSError` and error boxes; Delete All passes `on_error=lambda exc: self._show_file_error(_("Failed to delete document: {error}"), exc)` and branches on `result.completed`; drop the `document_package_path_for_name`, `load_workspace_documents` and `save_document_package` imports)
- Test: `client/tests/test_gui_document_flows.py` (6 new delegation tests; `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` rewritten with a stub service, refinement 7)

**Interfaces:**
- Consumes: `rename_document`, `delete_document`, `delete_all_documents` of the service.
- Produces: no new names. After this task `gui.py` does no workspace IO itself.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index d98966d..7882759 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -25,7 +25,7 @@ tearDownModule = _SCOPE.deactivate
 
 from documents.controller import DocumentController
 from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
-from documents.workspace_service import DocumentWorkspaceService, ImportResult
+from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
 from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
@@ -432,6 +432,116 @@ class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
             ],
         )
 
+    def _patch_name_dialog(self, name: str):
+        dialog = Mock()
+        dialog.__enter__ = Mock(return_value=dialog)
+        dialog.__exit__ = Mock(return_value=False)
+        dialog.ShowModal.return_value = gui.wx.ID_OK
+        dialog.get_document_name.return_value = name
+        return patch.object(gui, "DocumentNameDialog", Mock(return_value=dialog))
+
+    def test_rename_goes_through_service_then_refreshes(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        frame._workspace_service.rename_document.return_value = Document("gamma", "a", "1")
+
+        with self._patch_name_dialog("gamma"):
+            frame.on_rename_document(None)
+
+        frame._workspace_service.rename_document.assert_called_once_with("alpha", "gamma")
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [call._refresh_document_list("gamma"), call._update_window_title(), call._refresh_dual_view()],
+        )
+        frame._show_file_error.assert_not_called()
+
+    def test_rename_failure_from_service_shows_save_error(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        error = OSError("locked")
+        frame._workspace_service.rename_document.side_effect = error
+
+        with self._patch_name_dialog("gamma"):
+            frame.on_rename_document(None)
+
+        frame._show_file_error.assert_called_once_with(gui._("Failed to save document: {error}"), error)
+        self.assertEqual(frame.ui.mock_calls, [])
+
+    def test_delete_goes_through_service_then_refreshes(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
+        frame._workspace_service.delete_document.side_effect = frame._document_controller.delete_document
+
+        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
+            frame.on_delete_document(None)
+
+        frame._workspace_service.delete_document.assert_called_once_with("beta")
+        self.assertEqual(frame.ui.mock_calls, [call._refresh_document_list("alpha"), call._refresh_dual_view()])
+        frame._show_file_error.assert_not_called()
+
+    def test_delete_failure_from_service_shows_delete_error(self) -> None:
+        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
+        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
+        error = OSError("locked")
+        frame._workspace_service.delete_document.side_effect = error
+
+        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
+            frame.on_delete_document(None)
+
+        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
+        self.assertEqual(frame.ui.mock_calls, [])
+        self.assertEqual(frame._document_controller.documents, documents)
+
+    def test_delete_all_success_goes_through_service(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        controller = frame._document_controller
+
+        def delete_all_documents(*, on_error):
+            controller.delete_all_documents()
+            return DeleteAllResult(completed=True, invalid_paths=[])
+
+        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents
+
+        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
+            frame.on_delete_all_documents(None)
+
+        frame._workspace_service.delete_all_documents.assert_called_once_with(on_error=ANY)
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [
+                call._update_window_title(),
+                call._refresh_document_list(),
+                call._clear_document_editors(),
+                call._ensure_open_document_exists(),
+                call._refresh_dual_view(),
+            ],
+        )
+
+    def test_delete_all_failure_reviews_paths_from_service(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
+        controller = frame._document_controller
+        error = OSError("locked")
+        invalid_paths = [self.workspace / "alpha.dep"]
+
+        def delete_all_documents(*, on_error):
+            on_error(error)
+            controller.restore_documents_after_delete_all_failure([])
+            return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
+
+        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents
+
+        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
+            frame.on_delete_all_documents(None)
+
+        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
+        self.assertEqual(
+            frame.ui.mock_calls,
+            [
+                call._refresh_document_list(),
+                call._review_invalid_workspace_files(invalid_paths),
+                call._clear_document_editors(),
+                call._refresh_dual_view(),
+            ],
+        )
+
 
 class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
     def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
@@ -925,21 +1035,23 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame._open_document_by_name = Mock()
         frame._clear_document_editors = Mock()
         frame._refresh_dual_view = Mock()
+        error = OSError("unlink failed")
+        controller = frame._document_controller
 
-        alpha_path = Mock()
-        alpha_path.exists.return_value = True
-        alpha_path.unlink.return_value = None
-        beta_path = Mock()
-        beta_path.exists.return_value = True
-        beta_path.unlink.side_effect = OSError("unlink failed")
+        def delete_all_documents(*, on_error):
+            # Stub service: alpha's package is deleted, beta's unlink fails, the reload finds beta.
+            on_error(error)
+            controller.restore_documents_after_delete_all_failure([Document("beta", "reloaded", "braille-b")])
+            return DeleteAllResult(completed=False, invalid_paths=[])
 
-        with (
-            patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES),
-            patch.object(gui, "document_package_path_for_name", side_effect=[alpha_path, beta_path]),
-            patch.object(gui, "load_workspace_documents", return_value=([Document("beta", "reloaded", "braille-b")], [])),
-        ):
+        frame._workspace_service = Mock()
+        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents
+
+        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
             frame.on_delete_all_documents(None)
 
+        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
+        frame._review_invalid_workspace_files.assert_called_once_with([])
         self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": ("fresh-beta",)})
         frame._refresh_dual_view.assert_called_once_with()
         frame._open_document_by_name.assert_called_once_with("beta")
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (today's code does the IO itself in the temporary directory, so the `Mock` service is never called; the rewritten Delete All test's stub service has no real `workspace_dir`):

```text
      1 AssertionError: Expected 'delete_all_documents' to be called once. Called 0 times.
      1 AssertionError: Expected 'delete_document' to be called once. Called 0 times.
      3 AssertionError: Expected 'mock' to be called once. Called 0 times.
      1 AssertionError: Expected 'rename_document' to be called once. Called 0 times.
      1 ERROR: test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer)
      1 FAIL: test_delete_all_failure_reviews_paths_from_service (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_delete_all_failure_reviews_paths_from_service)
      1 FAIL: test_delete_all_success_goes_through_service (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_delete_all_success_goes_through_service)
      1 FAIL: test_delete_failure_from_service_shows_delete_error (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_delete_failure_from_service_shows_delete_error)
      1 FAIL: test_delete_goes_through_service_then_refreshes (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_delete_goes_through_service_then_refreshes)
      1 FAIL: test_rename_failure_from_service_shows_save_error (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_rename_failure_from_service_shows_save_error)
      1 FAIL: test_rename_goes_through_service_then_refreshes (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_rename_goes_through_service_then_refreshes)
      1 FAILED (failures=6, errors=1, skipped=2)
      1 Ran 129 tests
      1 TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'Mock'
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index df7d076..7142f7d 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -36,11 +36,8 @@ from documents.workspace import (
     DEFAULT_DOCUMENT_NAME,
     Document,
     create_default_document,
-    document_package_path_for_name,
 	get_workspace_directory,
-    load_workspace_documents,
     normalize_document_name,
-    save_document_package,
 )
 from documents.workspace_service import DocumentWorkspaceService
 from documents.export_results import (
@@ -811,15 +808,10 @@ class BrailleFrame(wx.Frame):
 		if new_name is None or new_name == selected_document.name:
 			return
 		try:
-			renamed_document = Document(name=new_name, text=selected_document.text, braille=selected_document.braille)
-			save_document_package(document_package_path_for_name(renamed_document.name, self._workspace_service.workspace_dir), renamed_document)
-			old_path = document_package_path_for_name(selected_document.name, self._workspace_service.workspace_dir)
-			if old_path.exists():
-				old_path.unlink()
+			renamed_document = self._workspace_service.rename_document(selected_document.name, new_name)
 		except OSError as exc:
 			self._show_file_error(_("Failed to save document: {error}"), exc)
 			return
-		renamed_document = self._document_controller.rename_document(selected_document.name, new_name)
 		if renamed_document is None:
 			return
 		self._refresh_document_list(renamed_document.name)
@@ -841,13 +833,10 @@ class BrailleFrame(wx.Frame):
 		if confirmation != wx.YES:
 			return
 		try:
-			package_path = document_package_path_for_name(selected_document.name, self._workspace_service.workspace_dir)
-			if package_path.exists():
-				package_path.unlink()
+			delete_decision = self._workspace_service.delete_document(selected_document.name)
 		except OSError as exc:
 			self._show_file_error(_("Failed to delete document: {error}"), exc)
 			return
-		delete_decision = self._document_controller.delete_document(selected_document.name)
 		self._refresh_document_list(self._document_controller.selected_document_name)
 		if self._document_controller.has_documents:
 			open_name = self._document_controller.open_document_name
@@ -872,24 +861,18 @@ class BrailleFrame(wx.Frame):
 		)
 		if confirmation != wx.YES:
 			return
-		for document in self._document_controller.documents_snapshot():
-			try:
-				package_path = document_package_path_for_name(document.name, self._workspace_service.workspace_dir)
-				if package_path.exists():
-					package_path.unlink()
-			except OSError as exc:
-				self._show_file_error(_("Failed to delete document: {error}"), exc)
-				remaining_documents, invalid_paths = load_workspace_documents(self._workspace_service.workspace_dir)
-				self._document_controller.restore_documents_after_delete_all_failure(remaining_documents)
-				self._refresh_document_list()
-				self._review_invalid_workspace_files(invalid_paths)
-				if self._document_controller.has_documents:
-					self._open_document_by_name(self._document_controller.first_document_name)
-				else:
-					self._clear_document_editors()
-				self._refresh_dual_view()
-				return
-		self._document_controller.delete_all_documents()
+		result = self._workspace_service.delete_all_documents(
+			on_error=lambda exc: self._show_file_error(_("Failed to delete document: {error}"), exc),
+		)
+		if not result.completed:
+			self._refresh_document_list()
+			self._review_invalid_workspace_files(result.invalid_paths)
+			if self._document_controller.has_documents:
+				self._open_document_by_name(self._document_controller.first_document_name)
+			else:
+				self._clear_document_editors()
+			self._refresh_dual_view()
+			return
 		self._update_window_title()
 		self._refresh_document_list()
 		self._clear_document_editors()
PATCH
```

- [ ] **Step 4: Run the tests, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 696 80 2
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
```

Expected:

```text
Ran 129 tests
OK (skipped=2)
Ran 696 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (696)
new tests ok: 80 (expected 80)
new tests skipped: 2 (expected 2)
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: route rename and delete through the workspace service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: route rename and delete through the workspace service
```

---

### Task 8: Final verification (spec acceptance criteria, no commit)

- [ ] **Step 1: Acceptance criteria 1-7 (greps; criterion 3 with the word boundaries of spec correction 1) and the untouched trees of criterion 8.**

```bash
echo AC1; grep -nE '@property|\.setter|_get_document_controller' gui.py
echo AC2; grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' gui.py
echo AC3; grep -nE '\b(save_document_package|load_workspace_documents|ensure_workspace_directory|document_package_path_for_name|batch_import_documents|prepare_document_for_save)\b|\.unlink\(' gui.py
echo AC4; grep -nE '_sort_documents|_get_document_by_name|_replace_document|_document_name_exists|_get_document_names|_persist_documents|\bworkspace_dir\b' gui.py
echo AC5; grep -nE 'hasattr\(self, "(documents|_selected_document_name)"\)' gui.py
echo AC6; grep -nE '^(import wx|from wx)|^from gui|^import gui' documents/workspace_service.py documents/controller.py; grep -n 'set_state' documents/controller.py
echo AC7; grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' documents/workspace_service.py
echo AC8; git -C $REPO diff main --stat -- client/locales scripts
echo end
echo "spec AC3 as written:"; grep -nE 'save_document_package|load_workspace_documents|ensure_workspace_directory|document_package_path_for_name|batch_import_documents|prepare_document_for_save|\.unlink\(' gui.py
```

Expected (nothing between the labels; the spec's own AC3 command prints only the kept startup method and its caller):

```text
AC1
AC2
AC3
AC4
AC5
AC6
AC7
AC8
end
spec AC3 as written:
251:		self._load_workspace_documents_at_startup()
728:	def _load_workspace_documents_at_startup(self) -> None:
```

- [ ] **Step 2: Acceptance criterion 8 (msgid scan, full output).**

```bash
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json; echo "scan exit: $?"
```

Expected (the same as Task 0: 353 source msgids, only the four known `.pot`-only orphans, `SOURCE == SAVED`):

```text
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
SOURCE == SAVED
scan exit: 1
```

- [ ] **Step 3: Acceptance criterion 9 (focused verification), each new or touched module alone, and the characterization helper diff.**

```bash
$PY -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_removed_dead_code tests.test_menu_builder tests.test_action_menu tests.test_wx_stub 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for m in test_workspace_service test_document_controller test_gui_document_flows; do printf '%s: ' $m; $PY -m unittest tests.$m 2>&1 | tail -1; done
first=$(git -C $REPO log --format=%h --grep='^test: characterize document workspace flows' -1)
diff <(git -C $REPO show $first:client/tests/test_gui_document_flows.py | awk '/^class _FakeEditor/{f=1} f') <(awk '/^class _FakeEditor/{f=1} f' tests/test_gui_document_flows.py)
```

Expected (the characterization code differs from Task 1 only in the helper line of Task 5):

```text
Ran 202 tests
OK (skipped=2)
Ran 47 tests
OK
test_workspace_service: OK
test_document_controller: OK
test_gui_document_flows: OK (skipped=2)
180c180
<         frame.workspace_dir = self.workspace
---
>         frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)
```

- [ ] **Step 4: Acceptance criterion 10 (full suite).**

```bash
$T/tools/check_suite.sh 696 80 2
```

Expected (614 + 82 new = 696; only the known P2-5 failure; `skipped=9`, spec correction 3):

```text
Ran 696 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
BASELINE-TESTS-IDENTICAL
RAN-COUNT-OK (696)
new tests ok: 80 (expected 80)
new tests skipped: 2 (expected 2)
```

- [ ] **Step 5: Acceptance criterion 11 (shuffled runs).**

```bash
for s in 1 2 3 4 5; do $PY -B -I $SP/shuffle_harness.py $s tests.test_workspace_service tests.test_gui_document_flows tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_menu_builder tests.test_action_menu tests.test_removed_dead_code tests.test_wx_stub | head -1; done
for s in 1 2 3 4 5; do $PY -B -I $SP/shuffle_harness.py $s | grep -v '^order=' | sed -E 's/ \(test_conversion_service\.ConversionServiceTest\.[a-z_]+\)$//'; done
```

Expected (the touched modules are clean in every order; the full runs show only the known set from Task 0: the P2-5 failure, or the 8 pre-existing `test_conversion_service` order errors; which seeds hit the pollution changes with the module list, because the new module changes the shuffle):

```text
seed=1 ran=249 failures=0 errors=0 skipped=2
seed=2 ran=249 failures=0 errors=0 skipped=2
seed=3 ran=249 failures=0 errors=0 skipped=2
seed=4 ran=249 failures=0 errors=0 skipped=2
seed=5 ran=249 failures=0 errors=0 skipped=2
seed=1 ran=696 failures=1 errors=0 skipped=9
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
seed=2 ran=696 failures=0 errors=8 skipped=9
BAD test_conversion_uses_processed_text_for_translation_and_dual_view
BAD test_dual_view_segments_boundary_space_is_text
BAD test_dual_view_segments_exposes_math_source_kind
BAD test_dual_view_segments_exposes_text_source_kind
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
BAD test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment
BAD test_translate_with_language_merges_text_and_math_segments_in_order
BAD test_translate_with_language_passes_selected_math_braille_code
seed=3 ran=696 failures=1 errors=0 skipped=9
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
seed=4 ran=696 failures=0 errors=8 skipped=9
BAD test_conversion_uses_processed_text_for_translation_and_dual_view
BAD test_dual_view_segments_boundary_space_is_text
BAD test_dual_view_segments_exposes_math_source_kind
BAD test_dual_view_segments_exposes_text_source_kind
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
BAD test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment
BAD test_translate_with_language_merges_text_and_math_segments_in_order
BAD test_translate_with_language_passes_selected_math_braille_code
seed=5 ran=696 failures=1 errors=0 skipped=9
BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math
```

- [ ] **Step 6: The commits and the final tree.**

```bash
git -C $REPO log --format=%s main..HEAD
git -C $REPO diff main --stat -- client
sha256sum gui.py documents/controller.py documents/workspace_service.py tests/test_workspace_service.py
```

Expected:

```text
refactor: route rename and delete through the workspace service
refactor: route document import through the workspace service
refactor: route startup, save and create through the workspace service
refactor: move document frame state onto the controller
refactor: add wx-free document workspace service
refactor: add document controller state methods
test: characterize document workspace flows
docs: plan document controller adoption
docs: spec document controller adoption
 client/documents/controller.py           |   56 +-
 client/documents/workspace_service.py    |  128 +++
 client/gui.py                            |  282 ++-----
 client/tests/test_document_controller.py |   98 +++
 client/tests/test_gui_document_flows.py  | 1281 ++++++++++++++++++++++++++++--
 client/tests/test_workspace_service.py   |  397 +++++++++
 6 files changed, 1956 insertions(+), 286 deletions(-)
61fa19ad33b235daff4edc1da32ebb064f0190a015b9963e50e8b3cc64206975  gui.py
9acb23dea7c7421b20008643feb7dffa2682a8e8cc35b710aadd933e063a6862  documents/controller.py
3dfc43238a15cbe312a3f8bb92f018a58a3ce879f812d5b62751a9e284fd21bd  documents/workspace_service.py
8eb6ded97d779b04b55f3298da50d7b64c7eddffe6fa916243bf917fb5275a76  tests/test_workspace_service.py
```

- [ ] **Step 7: Report.** List the seven commits, the commands above with their results, the spec corrections, and the Windows verification debt below as not run.

## Windows verification debt (not possible on this Linux host)

- Run `tests.test_gui_document_flows` on Windows (and, if available, macOS): the two case-insensitive tests (`test_case_only_rename_on_case_insensitive_file_system_deletes_package`, `test_add_case_variant_on_case_insensitive_file_system_overwrites_package`) run there and must pass, pinning known defects 1 and 2 as they are; the two case-sensitive ones skip. The directory-as-package faults raise `PermissionError` there instead of `IsADirectoryError`; the tests only rely on `OSError` and the file name in the message.
- Walk through Add, Rename, Delete, Delete All, Import (single and multiple files, with a duplicate), Ctrl+Tab and window close on a packaged build, before and after this change, and compare the workspace folder contents and the list, title and editor state.
- Delete All with one `.dep` held open by another program (for example in a zip tool), to trigger the rollback: the error box, then the invalid-file dialog if any, then the reloaded list.
- Start with a corrupt `.dep` in the workspace and check the invalid-file dialog and both of its choices.
- No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed for this task.
