# Export Coordinator and Conversion Presenter (P1-4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The conversion state machine and the export chains leave `BrailleFrame`. A new wx-free `conversion/presenter.py` (`ConversionPresenter`) owns the job runner, the "converting" dialog timer, busy toggling, error messages, manual and export completion and the dual-view cache write after a manual conversion. A new wx-free `documents/export_coordinator.py` (`ExportCoordinator`) owns single export and the Export All chain. `conversion/jobs.py` loses `ConversionCompletionPolicy` and `ConversionJobRequest` (I-3): nothing UI-related travels through the worker any more. The frame keeps only wx code: menu-handler guards and save-first, dialogs, message boxes, widget toggling and `ConvertingDialog`, behind small public view methods. Two P0-review cleanups ride along: M-9 (`_show_file_error` loses its unused `parent`) and the unused `ConversionStageError` import. Every flow keeps its order of effects **turn by turn** (click turn, worker, timer turn, each `CallAfter` turn), its messages, captions, icons and re-entrancy behavior, including the seven known defects of the spec, which are pinned, not fixed. No user-facing string changes; `client/locales/` and `scripts/` untouched; the msgid scan stays at 353.

**Architecture:** Characterization first. Task 1 adds a deterministic threading harness (`tests/conversion_harness.py`: `FakeThread`, `make_thread_factory`, `DeferredCalls`, `FakeTimers`) and 19 frame-level tests that drive only public entry points of a stub frame and step the worker, each later UI turn and the timers by hand, asserting one ordered event log after every step. They pass on today's code and stay byte-identical (by AST) to the end; only their fixture helper `_wire_conversion` changes (Tasks 4 and 7). Task 2 pins the runner contract. Tasks 3-8 are the spec's migration steps 3-8, one green commit each, red test first. Task 9 is the spec's acceptance run.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `tempfile`, `dataclasses`, `typing.Protocol`, `ast`, `inspect`). wxPython is not installed; `gui` loads through the P0-4 `tests/wx_stub.py` scope that `tests/test_gui_document_flows.py` already uses.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-4-export-conversion-presenters-design.md` (authoritative, commit `caad5d6`). The corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-4-export-conversion-presenters`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (9, nothing else): `client/gui.py`, `client/conversion/jobs.py`, `client/conversion/presenter.py` (new), `client/documents/export_coordinator.py` (new); tests `client/tests/conversion_harness.py` (new, no `test_` prefix), `client/tests/test_conversion_jobs.py`, `client/tests/test_conversion_presenter.py` (new), `client/tests/test_export_coordinator.py` (new), `client/tests/test_gui_document_flows.py`. Never touch `client/locales/`, `scripts/`, `client/documents/export_results.py`, `client/documents/formats.py`, `client/conversion/service.py`, `client/tests/wx_stub.py`, `client/dialog.py`.
- Indentation per file, unchanged: TABS in `gui.py` (the 4-space continuation lines of its import block stay as they are), `conversion/jobs.py` and `tests/test_conversion_jobs.py`; 4 spaces in the two new modules, `tests/test_gui_document_flows.py` and every new test file (AGENTS.md).
- The patches carry the exact characters (tabs, context lines, braille). Run every block as it is; do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- No user-facing string changes. The msgids of the moved call sites move with them (spec, Strings); `Info`, `Error`, `Export Complete` and the other shared literals stay in `gui.py` too, so the msgid set is unchanged. Do not edit `.po`/`.pot`/`.mo`.
- Out of scope, and must not change: the seven known defects of the spec (result of a manual conversion lands in the document open at completion; export conversions skip the running check; HTML export of a pending document uses the cached dual view; untranslated Export All summary and public fallback texts; menus found by translated title; a non-`ConversionStageError` worker exception leaves the UI busy; a writer `ValueError` stops Export All without a summary). Tests that pin them carry `# KNOWN BUG (P1-4 spec, defect N)`. A reviewer should reject any "fix".
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run (see "Dry Run"). "Red" summaries strip the repo path, timings and object ids and use `LC_ALL=C sort | uniq -c`, so order and counts are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p14impl
  export PYTHONDONTWRITEBYTECODE=1
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. `PYTHONDONTWRITEBYTECODE=1` keeps a stale `.pyc` from masking a same-size edit made within the same second.
- Baseline (re-verified at `caad5d6`, the spec commit): `$PY -m unittest discover -s tests` gives `Ran 696 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: the moved GUI tests live in two classes and 27 test lines disappear, not 22.** The spec places all 22 conversion/export tests in `GuiDocumentFlowsTest`. Only five are defined there (`test_write_export_document_*` x3, `test_write_html_export_document_passes_cached_dual_view_results`, `test_export_next_document_uses_registry_extension`); `BrailleAppLifecycleTest` subclasses `GuiDocumentFlowsTest`, so those five run twice, and the other 17 are defined in `BrailleAppLifecycleTest`. Removing them removes 12 test lines in Task 4 and 15 in Task 7. The counts table below and `check_suite.sh` (with its list of the 27 planned removals) use the real numbers.
2. **Factual correction: one moved assertion cannot stay "the same".** `test_export_next_document_uses_registry_extension` asserted `get_format` was called once, because it replaced the writer with a fake. Through the coordinator's public `export_all`, `get_format` is read for the conflict check, for the step and by `write_document`, so the Part D version (`test_export_all_reads_the_format_for_conflicts_each_step_and_each_write`) asserts three calls and the patched extension in the written file name.
3. **Factual correction: acceptance criterion 6 cannot be checked with `git diff`.** A diff does not say whether a change is "inside test methods". Task 0 creates `$T/tools/char_unchanged.py`, which compares every member of the characterization class and of its module-level fakes between the Task 1 commit and the working tree by AST (line numbers ignored); the expected result after Tasks 4, 7 and 9 is that only `_wire_conversion` changed.
4. **Factual correction: the "seeded shuffle shows no new failures" check needs the baseline's order failures.** On the baseline, some seeds already show 8 errors in `test_conversion_service` (the `translate` re-import pollution of the P1-1 plan, refinement 8, which includes the P2-5 test). New modules change the shuffle, so which seeds hit it changes too. Task 0 records the union of `BAD` lines over seeds 1-10 on the baseline; Task 9 checks that no other `BAD` line appears.
5. **Refinement: characterization case 9 is two tests; 19 tests in all.** `test_single_export_with_braille_writes_and_reports` and `test_single_export_write_error_and_extension_correction`. Case 10 opens one document and exports another (selected, pending) one: save-first copies the editor text into the *open* document, so only a non-open document shows that the export converts `document.text`, not the editor text.
6. **Refinement: the event log carries no function names.** `DeferredCalls` logs `("call_after",)` and `FakeTimers` logs `("call_later", ms, args)` and `("timer.Stop", n)`: the code that queues a call moves from the frame to the presenter and the coordinator, and the logs must not change. Busy toggles also log `FindMenu(<translated title>)`, which pins defect 5. `gui_frame_stubs()` resolves `wx.EVT_CLOSE` through the stub module's `__getattr__`, which returns a new class on every access, so the tests patch `gui.wx.EVT_CLOSE` with the string `"EVT_CLOSE"` to compare `Unbind` arguments.
7. **Refinement: expected strings go through `_`.** `i18n` always loads the bundled zh_TW catalog, so in the tests `gui._("Info")` is `資訊`. Expected messages are built with the same `_` (`gui._` in the frame tests, `from i18n import _` in the new modules' tests). The texts that are not msgids (the Export All summary and message, the public fallback texts) are written in English with a `KNOWN BUG (... defect 4)` comment, because that is what the user sees today.
8. **Refinement: Task 4's temporary `_start_export_conversion` checks the table with the module function** `missing_default_table_message(self.translation_tables)` (imported in Task 4, dropped in Task 7) and then calls `self._conversion_presenter.convert_for_export(...)`. The spec's frame helpers use `Mock(spec=ConversionPresenter)` (Part E), so a presenter call for the table check would return a `Mock` and break the two Export All / single-export table tests that stay until Task 7. The function reads the same live `translation_tables` as the presenter's `get_translation_tables`.
9. **Refinement: `test_export_conversion_with_default_table_starts_background_conversion` is deleted in Task 4**, not kept until Task 7: it mocks `_start_conversion`, which Task 4 deletes. Its content is covered by `test_convert_for_export_converts_given_text_without_checks` (Part C) and `test_build_conversion_request_for_text_reads_current_settings` (frame), and the temporary `_start_export_conversion` is exercised end to end by characterization cases 10-12, 14, 16 and 18 until Task 7 deletes it.
10. **Refinement: red tests for the steps that change no behavior.** Task 4: `FrameConversionDelegationTest` (wiring with `wx.CallAfter`/`wx.CallLater`, the frame as view, live tables; `_build_conversion_request_for_text`; Convert and Ctrl+Enter delegate; close asks the presenter before saving) and `FrameViewMethodsTest` (the conversion view methods). Task 5: `test_results_carry_only_the_job_id_and_the_outcome` (plus the four runner tests failing on the new `start(ConversionRequest)` call). Task 7: `FrameExportDelegationTest` and `FrameExportViewMethodsTest`. Task 8: `test_show_file_error_formats_the_error_for_the_frame` (M-9, via the signature). Tasks 1 and 2 are characterization and pass at once; each has a mutation step that shows the new tests fail on a deliberately broken copy, then restores it.
11. **Refinement: imports leave `gui` in the task that stops using them:** `conversion.jobs` (all names), `ConversionOutput`, `get_public_error_message` in Task 4; `ExportContext`, `ExportBatchResult` (and the temporary `missing_default_table_message`) in Task 7; the long-unused `ConversionStageError` in Task 8 (spec step 8). `tests/test_gui_document_flows.py` drops `dataclasses.replace`, `ExportContext` and `get_format` in Task 7 (only the moved tests used them). `gui` gains `DocumentFormatDescriptor` for the `choose_export_path` annotation.
12. **Refinement: harness details.** `make_thread_factory()` returns the factory with a `threads` list attribute. `FakeTimer.fire()` calls the callback even after `Stop()`, so "a timer fired after delivery does nothing" is checked against the presenter's own guards. The presenter and coordinator test modules also carry an AST "imports neither wx nor gui" test, as `test_workspace_service.py` does.
13. **Behavior notes, none user-visible.** The translation settings and dictionary path are read inside `build_request` after busy is set (spec, intentional differences). `_on_job_failure` formats the message before ending the job (pure). `confirm_overwrite_all` keeps its `if not conflicts: return True` although the coordinator only calls it with conflicts.

Everything else in the spec was re-checked at `caad5d6`: every line range it cites in `gui.py` and `conversion/jobs.py`; the 696/1/9 baseline; the focused `tests.test_conversion_jobs tests.test_gui_document_flows` run (`Ran 133 tests`, `OK (skipped=2)`); the msgid scan (353 source msgids, only the four known `.pot`-only orphans); the async order and re-entrancy rows (all 19 characterization tests pass on unchanged code).

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `caad5d6` (`$SP/p14plan/dry`, never the repo), one commit per task; after each task the full suite and the msgid scan gave the counts below. The patches in this file are `git diff`s of those commits, split into the red test step and the implementation step (Tasks 4 and 7 were split on a second scratch clone so that each half is a real state). Mutation checks on the final dry tree (each applied alone to the touched modules, then undone): busy off after the export callback, the cache written for export conversions, the first Export All step deferred through `call_after`, the timer not stopped, a running check in `convert_for_export` (fixing defect 2), the result sent to the converted document (fixing defect 1), no table check for a single pending export, source editor toggled before the list, the dialog not closed on completion, the stale-timer guard removed, and the runner clearing its thread after the callback fail 7, 4, 11, 25, 3, 4, 3, 19, 11, 2 and 1 tests respectively. Then this file's blocks were extracted and run in order on two fresh clones (`$SP/p14plan/replay1`, `replay2`, each with a stand-in plan commit) by a harness that compares every "Expected" block with the real output: all 8 commits applied, every expected block matched byte for byte, and the resulting `client/` tree is identical to the dry clone. Final sha256: `client/gui.py` `b9eca92c6e3b0437048600a8907ebf99c282e2ba41438abf3b3bf1aa1094837b`, `client/conversion/presenter.py` `914a4630fac2be9ec8a42c41fdeba40d1230625e4915ec6955176958f4c0d9cb`, `client/documents/export_coordinator.py` `51338d37de49821c593acd50e95e109cabcdbe945975c0f0d0db2e09d9abb597`, `client/conversion/jobs.py` `b17fc539af3e6b6963e7a5b8568d07a25b94c32235723bff9feb4b746981fd75`.

## Review Focus

1. **Turn boundaries.** Busy off, timer stop and dialog close happen in the delivery turn *before* any callback or box; the first Export All step runs in the menu turn, every later step in its own `call_after` turn; a pending document's step only starts a conversion, its delivery writes and queues the next step. Tests: `test_manual_conversion_success_turn_by_turn`, `test_export_all_mixed_documents_turn_by_turn`, `test_single_export_of_pending_document_converts_its_text_then_writes` (frame), `test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn`, `test_export_all_with_a_real_presenter_turn_by_turn` (coordinator).
2. **Job bookkeeping.** The presenter stores `_ActiveJob(job_id, export)` after `runner.start` returns, which is correct only because `call_after` defers; the runner still filters stale results and clears its thread before the callback. Tests: `test_superseded_job_delivers_nothing`, `test_synchronous_call_after_with_a_manually_run_thread_completes`, `test_later_job_uses_its_own_completion`, the Task 2 runner contract tests.
3. **Manual vs export completion.** Only a manual completion sets and focuses the output, writes the open document and its cache, refreshes the Dual View and shows "Conversion completed."; an export completion only calls its callback. Tests: `test_manual_success_*`, `test_export_success_calls_only_on_success`, characterization case 10.
4. **Known defects stay.** `test_ctrl_s_during_manual_conversion_supersedes_it`, `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document`, `test_convert_between_export_all_steps_is_superseded`, `test_exception_outside_conversion_stage_error_delivers_nothing`, `test_export_all_writer_value_error_stops_the_chain` and the English summary assertions.
5. **Stub masking.** On a stub frame every missing attribute is a no-op function. Every frame helper sets `_conversion_presenter` (and from Task 7 `_export_coordinator`) explicitly; the characterization tests assert real disk, controller and editor state; delegation tests use `Mock(spec=...)`.

## File Map

- Task 1: create `client/tests/conversion_harness.py`; modify `client/tests/test_conversion_jobs.py` (imports `FakeThread` from the harness), `client/tests/test_gui_document_flows.py` (imports; fakes `_dual_view_segment`, `_RecordingEditor`, `_RecordingDocumentList`, `_RecordingMenuBar`, `_RecordingViewer`, `_KeyEvent`, `_CloseEvent`; class `ConversionExportFlowsCharacterizationTest` at the end).
- Task 2: modify `client/tests/test_conversion_jobs.py`.
- Task 3: create `client/conversion/presenter.py`, `client/tests/test_conversion_presenter.py`.
- Task 4: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (new classes `FrameConversionDelegationTest`, `FrameViewMethodsTest`; helpers; 12 tests removed).
- Task 5: modify `client/conversion/jobs.py`, `client/conversion/presenter.py`; test `client/tests/test_conversion_jobs.py`.
- Task 6: create `client/documents/export_coordinator.py`, `client/tests/test_export_coordinator.py`.
- Task 7: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (new classes `FrameExportDelegationTest`, `FrameExportViewMethodsTest`; P1-2 export tests through a real coordinator; helpers; 15 test lines removed).
- Task 8: modify `client/gui.py`; test `client/tests/test_gui_document_flows.py` (one test in `FrameViewMethodsTest`).

## Expected Counts

| After task | test lines added / removed | `discover` `Ran` | new tests ok (suite check) | baseline lines removed | msgid scan |
| --- | --- | --- | --- | --- | --- |
| baseline | - | 696 | 0 | 0 | 353, four `.pot`-only orphans, `SOURCE == SAVED` |
| 1 characterization | +19 | 715 | 19 | 0 | same |
| 2 runner contract | +4 | 719 | 23 | 0 | same |
| 3 presenter | +19 | 738 | 42 | 0 | same |
| 4 frame on presenter | +11 / -12 | 737 | 53 | 12 | same |
| 5 I-3 | +1 | 738 | 54 | 12 | same |
| 6 coordinator | +21 | 759 | 75 | 12 | same |
| 7 frame on coordinator | +9 / -15 | 753 | 84 | 27 | same |
| 8 cleanups | +1 | 754 | 85 | 27 | same |

Every row after the baseline: `FAILED (failures=1, skipped=9)` (the P2-5 case), `NO-UNPLANNED-BASELINE-CHANGES` and `new tests not ok: 0`.

## Throwaway Tooling (not committed)

All outside the repo (Task 0 creates them under `$T/tools`):

- `check_suite.sh <Ran> <new ok> <removed>`: full `discover -v`; every baseline test line must appear unchanged unless it is one of the 27 planned removals in `$T/planned_removals.txt`; counts the non-baseline lines.
- `char_unchanged.py <repo> <rev>`: the AST comparison of spec correction 3.
- `$SP/p12/tools/msgid_scan.py`: the P0-5 AST stand-in for xgettext (source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`). Task 0 saves the starting msgid set to `$T/base_msgids.json`.
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
docs: plan export and conversion presenters
refactor/p1-4-export-conversion-presenters
```

- [ ] **Step 2: Create the tools and record the baseline.**

```bash
mkdir -p $T/tools
cat > $T/tools/check_suite.sh <<'EOF'
#!/bin/bash
# Throwaway (P1-4). usage: check_suite.sh <expected Ran> <expected new ok> <expected removed>   (run from client/)
# Every baseline test line must still be present with the same result, except the moved tests
# listed in $T/planned_removals.txt. "new" counts test lines that are not in the baseline.
export LC_ALL=C
SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
T=${T:-$SP/p14impl}
PY=$SP/venv/bin/python
$PY -B -m unittest discover -s tests -v > $T/run.txt 2>&1
grep ' \.\.\. ' $T/run.txt | sort > $T/run_lines.txt
grep -E '^Ran|^FAILED|^OK' $T/run.txt | sed -E 's/ in [0-9.]+s$//'
grep -E '^(FAIL|ERROR):' $T/run.txt
missing=$(comm -23 $T/baseline_discover_verbose.txt $T/run_lines.txt | sed 's/ \.\.\. .*//')
unplanned=$(comm -23 <(printf '%s\n' "$missing" | sed '/^$/d' | sort) $T/planned_removals.txt)
echo "baseline tests removed: $(printf '%s\n' "$missing" | sed '/^$/d' | wc -l) (expected $3)"
[ -z "$unplanned" ] && echo "NO-UNPLANNED-BASELINE-CHANGES" || { echo "UNPLANNED-BASELINE-CHANGES:"; echo "$unplanned"; }
grep -q "^Ran $1 tests" $T/run.txt && echo "RAN-COUNT-OK ($1)" || echo "RAN-COUNT-MISMATCH (expected $1)"
new=$(comm -13 $T/baseline_discover_verbose.txt $T/run_lines.txt)
echo "new tests ok: $(printf '%s\n' "$new" | grep -c '\.\.\. ok$') (expected $2)"
echo "new tests not ok: $(printf '%s\n' "$new" | sed '/^$/d' | grep -vc '\.\.\. ok$')"
EOF
chmod +x $T/tools/check_suite.sh
cat > $T/tools/char_unchanged.py <<'EOF'
"""Throwaway (P1-4): compare the P1-4 characterization code at <rev> with the working tree.

usage: python -I char_unchanged.py <repo> <rev>
Compares, by AST (line numbers ignored), every member of
ConversionExportFlowsCharacterizationTest and the module-level fakes Task 1 added.
"""
import ast
import subprocess
import sys
from pathlib import Path

CLASS = "ConversionExportFlowsCharacterizationTest"
FAKES = (
    "_dual_view_segment",
    "_RecordingEditor",
    "_RecordingDocumentList",
    "_RecordingMenuBar",
    "_RecordingViewer",
    "_KeyEvent",
    "_CloseEvent",
)
REL = "client/tests/test_gui_document_flows.py"


def members(source: str) -> dict:
    found = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in FAKES:
            found[node.name] = ast.dump(node)
        if isinstance(node, ast.ClassDef) and node.name == CLASS:
            for index, item in enumerate(node.body):
                name = item.name if isinstance(item, ast.FunctionDef) else f"<statement {index}>"
                found[f"{CLASS}.{name}"] = ast.dump(item)
    return found


repo, rev = sys.argv[1], sys.argv[2]
old = members(subprocess.run(["git", "-C", repo, "show", f"{rev}:{REL}"], capture_output=True, text=True, check=True).stdout)
new = members((Path(repo) / REL).read_text(encoding="utf-8"))
count = lambda found: sum(1 for key in found if key.startswith(f"{CLASS}.test_"))
print(f"characterization tests: {count(old)} at Task 1, {count(new)} now")
changed = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
print(f"changed members: {changed or 'none'}")
EOF
LC_ALL=C sort > $T/planned_removals.txt <<'EOF'
test_convert_with_default_table_starts_conversion_without_message (test_gui_document_flows.BrailleAppLifecycleTest.test_convert_with_default_table_starts_conversion_without_message)
test_convert_without_default_table_shows_info_and_does_not_convert (test_gui_document_flows.BrailleAppLifecycleTest.test_convert_without_default_table_shows_info_and_does_not_convert)
test_export_all_continues_after_conversion_failure (test_gui_document_flows.BrailleAppLifecycleTest.test_export_all_continues_after_conversion_failure)
test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes (test_gui_document_flows.BrailleAppLifecycleTest.test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes)
test_export_all_shows_one_partial_failure_dialog_with_names (test_gui_document_flows.BrailleAppLifecycleTest.test_export_all_shows_one_partial_failure_dialog_with_names)
test_export_all_shows_one_success_dialog (test_gui_document_flows.BrailleAppLifecycleTest.test_export_all_shows_one_success_dialog)
test_export_conversion_calls_error_callback_without_showing_worker_error (test_gui_document_flows.BrailleAppLifecycleTest.test_export_conversion_calls_error_callback_without_showing_worker_error)
test_export_conversion_calls_success_callback_without_manual_message (test_gui_document_flows.BrailleAppLifecycleTest.test_export_conversion_calls_success_callback_without_manual_message)
test_export_conversion_does_not_replace_dual_view_cache (test_gui_document_flows.BrailleAppLifecycleTest.test_export_conversion_does_not_replace_dual_view_cache)
test_export_conversion_with_default_table_starts_background_conversion (test_gui_document_flows.BrailleAppLifecycleTest.test_export_conversion_with_default_table_starts_background_conversion)
test_export_next_document_uses_registry_extension (test_gui_document_flows.BrailleAppLifecycleTest.test_export_next_document_uses_registry_extension)
test_export_next_document_uses_registry_extension (test_gui_document_flows.GuiDocumentFlowsTest.test_export_next_document_uses_registry_extension)
test_later_job_uses_its_own_policy_after_previous_completion (test_gui_document_flows.BrailleAppLifecycleTest.test_later_job_uses_its_own_policy_after_previous_completion)
test_manual_conversion_updates_output_focus_and_shows_completion (test_gui_document_flows.BrailleAppLifecycleTest.test_manual_conversion_updates_output_focus_and_shows_completion)
test_missing_default_table_message_reports_only_unset_default (test_gui_document_flows.BrailleAppLifecycleTest.test_missing_default_table_message_reports_only_unset_default)
test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output (test_gui_document_flows.BrailleAppLifecycleTest.test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output)
test_start_conversion_builds_request_and_starts_runner (test_gui_document_flows.BrailleAppLifecycleTest.test_start_conversion_builds_request_and_starts_runner)
test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer (test_gui_document_flows.BrailleAppLifecycleTest.test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer)
test_text_processing_failure_uses_its_own_message (test_gui_document_flows.BrailleAppLifecycleTest.test_text_processing_failure_uses_its_own_message)
test_write_export_document_passes_cached_results_to_every_writer (test_gui_document_flows.BrailleAppLifecycleTest.test_write_export_document_passes_cached_results_to_every_writer)
test_write_export_document_passes_cached_results_to_every_writer (test_gui_document_flows.GuiDocumentFlowsTest.test_write_export_document_passes_cached_results_to_every_writer)
test_write_export_document_rejects_non_exportable_format (test_gui_document_flows.BrailleAppLifecycleTest.test_write_export_document_rejects_non_exportable_format)
test_write_export_document_rejects_non_exportable_format (test_gui_document_flows.GuiDocumentFlowsTest.test_write_export_document_rejects_non_exportable_format)
test_write_export_document_uses_registry_writer (test_gui_document_flows.BrailleAppLifecycleTest.test_write_export_document_uses_registry_writer)
test_write_export_document_uses_registry_writer (test_gui_document_flows.GuiDocumentFlowsTest.test_write_export_document_uses_registry_writer)
test_write_html_export_document_passes_cached_dual_view_results (test_gui_document_flows.BrailleAppLifecycleTest.test_write_html_export_document_passes_cached_dual_view_results)
test_write_html_export_document_passes_cached_dual_view_results (test_gui_document_flows.GuiDocumentFlowsTest.test_write_html_export_document_passes_cached_dual_view_results)
EOF
$PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | LC_ALL=C sort > $T/baseline_discover_verbose.txt
wc -l < $T/baseline_discover_verbose.txt
LC_ALL=C comm -12 <(sed 's/ \.\.\. .*//' $T/baseline_discover_verbose.txt | LC_ALL=C sort) $T/planned_removals.txt | wc -l
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | sed "s#$T#\$T#"
$PY -m unittest tests.test_conversion_jobs tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for s in $(seq 1 10); do $PY -B -I $SP/shuffle_harness.py $s > $T/shuffle_base_$s.txt; head -1 $T/shuffle_base_$s.txt; done
cat $T/shuffle_base_*.txt | grep '^BAD' | LC_ALL=C sort -u > $T/known_order_bad.txt
wc -l < $T/known_order_bad.txt
```

Expected (696 test lines, all 27 planned removals present in the baseline; the scan's exit status is 1 because of the four known `.pot`-only orphans; the focused set is the spec's 133; some seeds show the pre-existing 8 `test_conversion_service` order errors of spec correction 4 instead of the P2-5 failure, and their union is 8 lines):

```text
696
27
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
saved $T/base_msgids.json
Ran 133 tests
OK (skipped=2)
seed=1 ran=696 failures=1 errors=0 skipped=9
seed=2 ran=696 failures=0 errors=8 skipped=9
seed=3 ran=696 failures=1 errors=0 skipped=9
seed=4 ran=696 failures=0 errors=8 skipped=9
seed=5 ran=696 failures=1 errors=0 skipped=9
seed=6 ran=696 failures=1 errors=0 skipped=9
seed=7 ran=696 failures=0 errors=8 skipped=9
seed=8 ran=696 failures=1 errors=0 skipped=9
seed=9 ran=696 failures=1 errors=0 skipped=9
seed=10 ran=696 failures=0 errors=8 skipped=9
8
```

---

### Task 1: Characterize the conversion and export flows (spec step 1)

**Files:**
- Create: `client/tests/conversion_harness.py`
- Modify: `client/tests/test_conversion_jobs.py` (its `FakeThread` moves to the harness, unchanged apart from indentation)
- Modify: `client/tests/test_gui_document_flows.py` (imports `ConversionOutput`, `ConversionRequest`, `ConversionStageError`, the harness; module-level fakes; class `ConversionExportFlowsCharacterizationTest` at the end)

**Interfaces:**
- Consumes: today's frame entry points `on_convert`, `on_input_text_key_down`, `on_export_document`, `on_export_all_documents`, `on_output_text_key_down`, `on_char_hook`, `_on_close`; the real `DocumentController`, `DocumentWorkspaceService` (temporary workspace) and BRL writer. Patches `gui.wx.MessageBox`, `gui.wx.FileDialog`, `gui.wx.DirDialog`, `gui.wx.CallAfter` (a `DeferredCalls`), `gui.wx.CallLater` (a `FakeTimers`), `gui.wx.EVT_CLOSE`, `gui.ConvertingDialog`, `gui.get_lang`, `gui.get_charset_maps`.
- Produces: `tests/conversion_harness.py` with `FakeThread(*, target, args=(), daemon=None)` (`start()` marks it alive and never runs the target; `run()` runs it and then marks it dead; `is_alive()`), `make_thread_factory()` (returns `thread_factory(*, target, args=(), daemon=None)` with a `threads` list), `DeferredCalls(events=None)` (`__call__(fn, *args, **kwargs)` queues and logs `("call_after",)`; `pending`, `run_next()`, `run_all()`), `FakeTimers(events=None)` (`__call__(ms, fn, *args)` logs `("call_later", ms, args)` and returns a `FakeTimer` with `number` (from 1), `stopped`, `Stop()` (logs `("timer.Stop", number)`) and `fire()`). In the test module: `_wire_conversion(frame)`, the only helper that later changes; `_make_frame(documents, open_name=None, selected_name=None)`; `self.events` entries `("FindMenu", title)`, `("EnableTop", index, enabled)`, `("enable", "list"|"input", enabled)`, `("set", "input"|"output", value)`, `("focus", "input"|"output")`, `("title", text)`, `("dual_view.refresh",)`, `("dual_view.Destroy",)`, `("MessageBox", message, caption, style, parent)`, `("FileDialog", parent, title, defaultFile, wildcard, style)`, `("DirDialog", parent, title)`, `("ConvertingDialog", parent)`, `("dialog.Show"|"dialog.Raise"|"dialog.Destroy",)`, `("dialog.Unbind", event)`, `("close.Veto"|"close.Skip",)`, `("convert", raw_text)` and the harness entries; queues `self.answers`, `self.export_paths`, `self.export_dirs` (`None` cancels) and `self.outputs` (source text to `ConversionOutput` or an exception to raise in the worker).

The 19 tests (spec Part A cases in brackets): manual success [1], no open document [2], failure messages [3], Convert while running [4], no default table [5], converting dialog [6], earlier job's timer [7], close [8], single export with braille [9a] and write error plus extension [9b], pending single export [10], its conversion and table errors [11], Export All mixed [12], all ready [13], no table [14], dialogs [15], Ctrl+S re-entrancy [16], Ctrl+Tab re-entrancy [17], Convert between Export All steps [18]. They run on unchanged code and must pass immediately. If one fails in a later task, the refactor changed behavior: fix the code, not the test.

- [ ] **Step 1: Add the harness and the characterization tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/conversion_harness.py b/client/tests/conversion_harness.py
new file mode 100644
index 0000000..442e30d
--- /dev/null
+++ b/client/tests/conversion_harness.py
@@ -0,0 +1,108 @@
+"""Deterministic stand-ins for the conversion threading seams (no wx, no tests here).
+
+* ``FakeThread`` never runs its target in ``start()``; the test calls ``run()``.
+* ``make_thread_factory()`` returns a ``thread_factory`` that records every thread
+  it creates in its ``threads`` attribute.
+* ``DeferredCalls`` is a ``call_after`` that queues ``(fn, args, kwargs)``; the test
+  runs one later UI turn with ``run_next()`` or all of them with ``run_all()``.
+* ``FakeTimers`` is a ``call_later(ms, fn, *args)`` that returns a ``FakeTimer`` with
+  ``Stop()`` and ``fire()``.
+
+``DeferredCalls`` and ``FakeTimers`` take an optional shared event list and append
+``("call_after",)``, ``("call_later", ms, args)`` and ``("timer.Stop", n)`` (``n`` counts
+timers from 1) to it, so a test sees the order of effects across UI turns. The
+entries carry no function names: the code that queues the call may move.
+
+This module has no ``test_`` prefix, so importing it never runs tests twice.
+"""
+
+from __future__ import annotations
+
+
+class FakeThread:
+    def __init__(self, *, target, args=(), daemon=None):
+        self._target = target
+        self._args = args
+        self.daemon = daemon
+        self.started = False
+        self._alive = False
+
+    def start(self) -> None:
+        self.started = True
+        self._alive = True
+
+    def is_alive(self) -> bool:
+        return self._alive
+
+    def run(self) -> None:
+        try:
+            self._target(*self._args)
+        finally:
+            self._alive = False
+
+
+def make_thread_factory():
+    threads: list[FakeThread] = []
+
+    def thread_factory(*, target, args=(), daemon=None) -> FakeThread:
+        thread = FakeThread(target=target, args=args, daemon=daemon)
+        threads.append(thread)
+        return thread
+
+    thread_factory.threads = threads
+    return thread_factory
+
+
+class DeferredCalls:
+    def __init__(self, events: list | None = None):
+        self.pending: list[tuple] = []
+        self._events = events
+
+    def __call__(self, fn, *args, **kwargs) -> None:
+        self.pending.append((fn, args, kwargs))
+        if self._events is not None:
+            self._events.append(("call_after",))
+
+    def run_next(self):
+        fn, args, kwargs = self.pending.pop(0)
+        return fn(*args, **kwargs)
+
+    def run_all(self) -> int:
+        count = 0
+        while self.pending:
+            self.run_next()
+            count += 1
+        return count
+
+
+class FakeTimer:
+    def __init__(self, timers: FakeTimers, number: int, delay_ms: int, fn, args: tuple):
+        self._timers = timers
+        self.number = number
+        self.delay_ms = delay_ms
+        self.fn = fn
+        self.args = args
+        self.stopped = False
+
+    def Stop(self) -> None:
+        self.stopped = True
+        self._timers._record(("timer.Stop", self.number))
+
+    def fire(self):
+        return self.fn(*self.args)
+
+
+class FakeTimers:
+    def __init__(self, events: list | None = None):
+        self.timers: list[FakeTimer] = []
+        self._events = events
+
+    def __call__(self, delay_ms: int, fn, *args) -> FakeTimer:
+        timer = FakeTimer(self, len(self.timers) + 1, delay_ms, fn, args)
+        self.timers.append(timer)
+        self._record(("call_later", delay_ms, args))
+        return timer
+
+    def _record(self, event: tuple) -> None:
+        if self._events is not None:
+            self._events.append(event)
diff --git a/client/tests/test_conversion_jobs.py b/client/tests/test_conversion_jobs.py
index 4995fe5..b5fe4f3 100644
--- a/client/tests/test_conversion_jobs.py
+++ b/client/tests/test_conversion_jobs.py
@@ -10,28 +10,7 @@ from conversion.jobs import (
 )
 from config import DEFAULT_CHARSET_MAPS
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
-
-
-class FakeThread:
-	def __init__(self, *, target, args=(), daemon=None):
-		self._target = target
-		self._args = args
-		self.daemon = daemon
-		self.started = False
-		self._alive = False
-
-	def start(self) -> None:
-		self.started = True
-		self._alive = True
-
-	def is_alive(self) -> bool:
-		return self._alive
-
-	def run(self) -> None:
-		try:
-			self._target(*self._args)
-		finally:
-			self._alive = False
+from tests.conversion_harness import FakeThread
 
 
 class ConversionJobRunnerTest(unittest.TestCase):
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index fecd863..9c42325 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -10,6 +10,7 @@ from types import SimpleNamespace
 from unittest.mock import ANY, DEFAULT, Mock, call, patch
 
 from tests import wx_stub
+from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
 from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
 
 _SCOPE = wx_stub.StubScope(
@@ -31,6 +32,7 @@ from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
 from documents.formats import ExportContext, get_format
+from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 from dual_view.html import render_dual_view_html
 from dual_view.model import DualViewSegment, build_dual_view_model
 
@@ -2731,5 +2733,905 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
                 event.Skip.assert_called_once_with()
 
 
+
+def _dual_view_segment(raw: str, braille: str) -> DualViewSegment:
+    return DualViewSegment(
+        result=SimpleNamespace(raw=[raw], braille=[braille], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
+        source_kind="text",
+    )
+
+
+class _RecordingEditor(_FakeEditor):
+    def SetValue(self, value: str) -> None:
+        self.events.append(("set", self.name, value))
+        super().SetValue(value)
+
+    def Enable(self, enable: bool = True) -> None:
+        self.events.append(("enable", self.name, enable))
+
+
+class _RecordingDocumentList(_FakeDocumentList):
+    def __init__(self, events: list, names: list[str], selected_index: int):
+        super().__init__(names, selected_index)
+        self.events = events
+
+    def Enable(self, enable: bool = True) -> None:
+        self.events.append(("enable", "list", enable))
+
+
+class _RecordingMenuBar:
+    def __init__(self, events: list):
+        self.events = events
+        self.titles = [gui._("File"), gui._("Translation"), gui._("Help")]
+
+    def FindMenu(self, title: str) -> int:
+        self.events.append(("FindMenu", title))
+        return self.titles.index(title) if title in self.titles else gui.wx.NOT_FOUND
+
+    def EnableTop(self, index: int, enable: bool) -> None:
+        self.events.append(("EnableTop", index, enable))
+
+
+class _RecordingViewer:
+    """Stands for the open Dual View window."""
+
+    def __init__(self, events: list):
+        self.events = events
+        self.html = None
+
+    def refresh_html(self, html: str) -> None:
+        self.html = html
+        self.events.append(("dual_view.refresh",))
+
+    def Destroy(self) -> None:
+        self.events.append(("dual_view.Destroy",))
+
+
+class _KeyEvent:
+    def __init__(self, key_code: int, *, control: bool = True, shift: bool = False):
+        self.key_code = key_code
+        self.control = control
+        self.shift = shift
+        self.skipped = False
+
+    def GetKeyCode(self) -> int:
+        return self.key_code
+
+    def ControlDown(self) -> bool:
+        return self.control
+
+    def ShiftDown(self) -> bool:
+        return self.shift
+
+    def Skip(self) -> None:
+        self.skipped = True
+
+
+class _CloseEvent:
+    def __init__(self, events: list, can_veto: bool):
+        self.events = events
+        self.can_veto = can_veto
+
+    def CanVeto(self) -> bool:
+        return self.can_veto
+
+    def Veto(self) -> None:
+        self.events.append(("close.Veto",))
+
+    def Skip(self) -> None:
+        self.events.append(("close.Skip",))
+
+
+class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
+    """Pins today's conversion and export flows turn by turn; must pass unchanged through P1-4.
+
+    ``wx.CallAfter`` is a ``DeferredCalls`` queue, ``wx.CallLater`` a ``FakeTimers`` recorder and
+    every worker a ``FakeThread``. A test drives a public entry point (the click or menu turn),
+    then steps the worker (``thread.run()``), each later UI turn (``calls.run_next()``) and the
+    timers (``fire()``), and checks the ordered ``self.events`` log after each step.
+    Only ``_wire_conversion`` may change during P1-4.
+    """
+
+    TABLES = {"default": "zh-tw.ctb", "math": "nemeth.ctb"}
+    LANG = "zh_TW"
+    CHARSET_MAPS = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
+    CTRL_S = 83
+    CTRL_TAB = 9
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name)
+        self.workspace = self.root / "workspace"
+        self.export_dir = self.root / "export"
+        self.export_dir.mkdir()
+        self.events: list = []
+        self.answers: list = []
+        self.export_paths: list = []
+        self.export_dirs: list = []
+        self.outputs: dict = {}
+        self.requests: list = []
+        self.runtime = object()
+        self.calls = DeferredCalls(self.events)
+        self.timers = FakeTimers(self.events)
+        self.thread_factory = make_thread_factory()
+        self.threads = self.thread_factory.threads
+        self.menu_bar = _RecordingMenuBar(self.events)
+        for patcher in (
+            patch.object(gui.wx, "MessageBox", self._message_box),
+            patch.object(gui.wx, "FileDialog", self._file_dialog_class()),
+            patch.object(gui.wx, "DirDialog", self._dir_dialog_class()),
+            patch.object(gui.wx, "CallAfter", self.calls),
+            patch.object(gui.wx, "CallLater", self.timers),
+            patch.object(gui.wx, "EVT_CLOSE", "EVT_CLOSE"),
+            patch.object(gui, "ConvertingDialog", self._converting_dialog_class()),
+            patch.object(gui, "get_lang", return_value=self.LANG),
+            patch.object(gui, "get_charset_maps", return_value=dict(self.CHARSET_MAPS)),
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
+    def _file_dialog_class(self):
+        test = self
+
+        class FakeExportFileDialog:
+            def __init__(self, parent, title, defaultFile="", wildcard="", style=0):
+                test.events.append(("FileDialog", parent, title, defaultFile, wildcard, style))
+                self.path = test.export_paths.pop(0)
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.ID_OK if self.path is not None else gui.wx.CANCEL
+
+            def GetPath(self):
+                return str(self.path)
+
+        return FakeExportFileDialog
+
+    def _dir_dialog_class(self):
+        test = self
+
+        class FakeDirDialog:
+            def __init__(self, parent, title):
+                test.events.append(("DirDialog", parent, title))
+                self.path = test.export_dirs.pop(0)
+
+            def __enter__(self):
+                return self
+
+            def __exit__(self, *_exc):
+                return False
+
+            def ShowModal(self):
+                return gui.wx.ID_OK if self.path is not None else gui.wx.CANCEL
+
+            def GetPath(self):
+                return str(self.path)
+
+        return FakeDirDialog
+
+    def _converting_dialog_class(self):
+        test = self
+
+        class FakeConvertingDialog:
+            def __init__(self, parent):
+                test.events.append(("ConvertingDialog", parent))
+
+            def Show(self):
+                test.events.append(("dialog.Show",))
+
+            def Raise(self):
+                test.events.append(("dialog.Raise",))
+
+            def Unbind(self, event):
+                test.events.append(("dialog.Unbind", event))
+
+            def Destroy(self):
+                test.events.append(("dialog.Destroy",))
+
+        return FakeConvertingDialog
+
+    def _convert(self, request, *, runtime):
+        self.assertIs(runtime, self.runtime)
+        self.requests.append(request)
+        self.events.append(("convert", request.raw_text))
+        outcome = self.outputs[request.raw_text]
+        if isinstance(outcome, Exception):
+            raise outcome
+        return outcome
+
+    # --- helpers -----------------------------------------------------------
+
+    def _wire_conversion(self, frame) -> None:
+        """Today's conversion wiring with the fakes. The only helper that changes during P1-4."""
+        frame._conversion_runner = gui.ConversionJobRunner(
+            runtime=frame.translation_runtime,
+            on_success=frame._finish_conversion_success,
+            on_failure=frame._finish_conversion_failure,
+            call_after=self.calls,
+            converter=self._convert,
+            thread_factory=self.thread_factory,
+        )
+        frame._convert_dialog = None
+        frame._convert_dialog_timer = None
+
+    def _make_frame(self, documents, open_name=None, selected_name=None) -> gui.BrailleFrame:
+        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
+        documents = list(documents)
+        selected_name = selected_name or open_name
+        controller = DocumentController(documents=documents, open_name=open_name, selected_name=selected_name)
+        frame._document_controller = controller
+        frame._workspace_service = DocumentWorkspaceService(controller, self.workspace)
+        open_document = controller.get_document(open_name)
+        frame.input_txt = _RecordingEditor("input", self.events, open_document.text if open_document else "")
+        frame.output_txt = _RecordingEditor(
+            "output", self.events, (open_document.braille or "") if open_document else ""
+        )
+        names = [document.name for document in documents]
+        frame.document_list = _RecordingDocumentList(
+            self.events,
+            names,
+            names.index(selected_name) if selected_name in names else gui.wx.NOT_FOUND,
+        )
+        frame.SetTitle = lambda title: self.events.append(("title", title))
+        frame.GetMenuBar = lambda: self.menu_bar
+        frame._dual_view_frame = _RecordingViewer(self.events)
+        frame._document_menu_items = {}
+        frame.translation_runtime = self.runtime
+        frame.translation_tables = dict(self.TABLES)
+        frame.translation_settings = TranslationSettings("ascii", 32, "default")
+        frame.dictionary_dir = self.root / "dictionary"
+        self._wire_conversion(frame)
+        return frame
+
+    def _take(self) -> list:
+        taken = list(self.events)
+        self.events.clear()
+        return taken
+
+    def _busy(self, busy: bool) -> list:
+        return [
+            ("FindMenu", gui._("File")),
+            ("EnableTop", 0, not busy),
+            ("FindMenu", gui._("Translation")),
+            ("EnableTop", 1, not busy),
+            ("enable", "list", not busy),
+            ("enable", "input", not busy),
+        ]
+
+    def _box(self, frame, message: str, caption: str, flags: int) -> tuple:
+        return ("MessageBox", message, caption, flags, frame)
+
+    def _info(self, frame, message: str, caption: str | None = None) -> tuple:
+        caption = gui._("Info") if caption is None else caption
+        return self._box(frame, message, caption, gui.wx.OK | gui.wx.ICON_INFORMATION)
+
+    def _error(self, frame, message: str) -> tuple:
+        return self._box(frame, message, gui._("Error"), gui.wx.OK | gui.wx.ICON_ERROR)
+
+    def _completed(self, frame) -> tuple:
+        return self._info(frame, gui._("Conversion completed."))
+
+    def _exported(self, frame) -> tuple:
+        return self._info(frame, gui._("The document was exported successfully."), gui._("Export Complete"))
+
+    def _export_dialog(self, frame, default_file: str) -> tuple:
+        return (
+            "FileDialog",
+            frame,
+            gui._("Export Document"),
+            default_file,
+            gui._("Braille files (*.brl)|*.brl"),
+            gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
+        )
+
+    def _overwrite_question(self, frame) -> tuple:
+        return self._box(
+            frame,
+            gui._(
+                "The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
+            ),
+            gui._("Confirm Overwrite"),
+            gui.wx.YES_NO | gui.wx.ICON_WARNING,
+        )
+
+    def _os_error_text(self, path: Path) -> str:
+        """``str(exc)`` of writing to ``path`` (a directory), as the BRL writer raises it."""
+        try:
+            path.write_text("", encoding="utf-8")
+        except OSError as exc:
+            return str(exc)
+        self.fail(f"{path} is writable")
+
+    def _request(self, raw_text: str) -> ConversionRequest:
+        return ConversionRequest(
+            raw_text=raw_text,
+            output_mode="ascii",
+            width=32,
+            dictionary_path=self.root / "dictionary" / "default.csv",
+            data_dir=gui.resource_path("data"),
+            translation_tables=self.TABLES,
+            lang=self.LANG,
+            charset_maps=self.CHARSET_MAPS,
+        )
+
+    # --- manual conversion ---------------------------------------------------
+
+    def test_manual_conversion_success_turn_by_turn(self) -> None:
+        segment = _dual_view_segment("a", "⠁")
+        frame = self._make_frame([Document("alpha", "old text", None), Document("beta", "b", "⠃")], "alpha")
+        frame.input_txt.value = "edited text"
+        self.outputs["edited text"] = ConversionOutput("⠑⠙", ("result",), (segment,))
+
+        frame.on_convert(None)
+
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])
+        self.assertEqual([(thread.daemon, thread.started) for thread in self.threads], [(True, True)])
+        self.assertEqual(self.requests, [])
+
+        self.threads[0].run()
+
+        self.assertEqual(self._take(), [("convert", "edited text"), ("call_after",)])
+        self.assertEqual(self.requests, [self._request("edited text")])
+        self.assertIsNot(self.requests[0].translation_tables, frame.translation_tables)
+        self.assertEqual(frame.output_txt.value, "")
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            [("timer.Stop", 1)]
+            + self._busy(False)
+            + [
+                ("set", "output", "⠑⠙"),
+                ("focus", "output"),
+                ("dual_view.refresh",),
+                self._completed(frame),
+            ],
+        )
+        controller = frame._document_controller
+        self.assertEqual(controller.documents, [Document("alpha", "edited text", "⠑⠙"), Document("beta", "b", "⠃")])
+        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
+        self.assertIn('<span class="source">a</span>', frame._dual_view_frame.html)
+        self.assertEqual(self.calls.pending, [])
+        self.assertFalse(self.workspace.exists())
+
+    def test_manual_conversion_without_open_document_updates_output_only(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", None)], open_name=None, selected_name="alpha")
+        frame.input_txt.value = "loose text"
+        self.outputs["loose text"] = ConversionOutput("⠇", ("result",), (_dual_view_segment("l", "⠇"),))
+
+        frame.on_convert(None)
+        self.threads[0].run()
+        self._take()
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            [("timer.Stop", 1)]
+            + self._busy(False)
+            + [("set", "output", "⠇"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
+        )
+        self.assertEqual(frame._document_controller.documents, [Document("alpha", "a", None)])
+        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
+
+    def test_conversion_failure_messages_by_stage_and_public_text(self) -> None:
+        cases = (
+            (ConversionStageError("ascii", RuntimeError("bad map")), gui._("ASCII conversion failed: {error}"), "bad map"),
+            (
+                ConversionStageError("text_processing", RuntimeError("script boom")),
+                gui._("Text processing failed: {error}"),
+                "script boom",
+            ),
+            (ConversionStageError("translation", RuntimeError("boom")), gui._("Translation failed: {error}"), "boom"),
+            (ConversionStageError("other", RuntimeError("odd")), gui._("Translation failed: {error}"), "odd"),
+            # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
+            (
+                ConversionStageError("translation", RuntimeError("")),
+                gui._("Translation failed: {error}"),
+                "An unknown error occurred.",
+            ),
+            (
+                ConversionStageError("translation", RuntimeError("Can't translate: tables zh-tw.ctb inbuf=12")),
+                gui._("Translation failed: {error}"),
+                "The selected translation table could not translate this text.",
+            ),
+        )
+        for error, template, error_text in cases:
+            with self.subTest(stage=error.stage, error=str(error)):
+                self.events.clear()
+                self.threads.clear()
+                self.timers.timers.clear()
+                segment = _dual_view_segment("o", "⠕")
+                frame = self._make_frame([Document("alpha", "source", "⠕")], "alpha")
+                frame._document_controller.set_dual_view_results("alpha", (segment,))
+                self.outputs["source"] = error
+
+                frame.on_convert(None)
+                self.threads[0].run()
+                self._take()
+                self.calls.run_next()
+
+                self.assertEqual(
+                    self._take(),
+                    [("timer.Stop", 1)] + self._busy(False) + [self._error(frame, template.format(error=error_text))],
+                )
+                self.assertEqual(frame.output_txt.value, "⠕")
+                self.assertEqual(frame._document_controller.documents, [Document("alpha", "source", "⠕")])
+                self.assertEqual(frame._document_controller.dual_view_results_by_document, {"alpha": (segment,)})
+
+    def test_convert_while_running_does_nothing(self) -> None:
+        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
+        self.outputs["source"] = ConversionOutput("⠎", ())
+
+        frame.on_convert(None)
+        self._take()
+        frame.on_convert(None)
+        frame.on_input_text_key_down(_KeyEvent(13))
+
+        self.assertEqual(self._take(), [])
+        self.assertEqual(len(self.threads), 1)
+        self.assertEqual(len(self.timers.timers), 1)
+
+    def test_convert_without_default_table_shows_info_only(self) -> None:
+        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
+        frame.translation_tables = {"default": "", "math": "nemeth.ctb"}
+
+        frame.on_convert(None)
+
+        self.assertEqual(self._take(), [self._info(frame, gui._("Please select a translation table first."))])
+        self.assertEqual(self.threads, [])
+        self.assertEqual(self.timers.timers, [])
+
+    def test_converting_dialog_appears_once_and_closes_on_completion(self) -> None:
+        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
+        self.outputs["source"] = ConversionOutput("⠎", ())
+        frame.on_convert(None)
+        self._take()
+
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [("ConvertingDialog", frame), ("dialog.Show",), ("dialog.Raise",)])
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [])
+
+        self.threads[0].run()
+        self._take()
+        self.calls.run_next()
+        self.assertEqual(
+            self._take(),
+            [("timer.Stop", 1), ("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",)]
+            + self._busy(False)
+            + [("set", "output", "⠎"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
+        )
+
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [])
+
+    def test_converting_dialog_timer_of_an_earlier_job_does_nothing(self) -> None:
+        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
+        self.outputs["source"] = ConversionOutput("⠎", ())
+        frame.on_convert(None)
+        self.threads[0].run()
+        self.calls.run_next()
+        frame.on_convert(None)
+        self._take()
+
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [])
+        self.timers.timers[1].fire()
+        self.assertEqual(self._take(), [("ConvertingDialog", frame), ("dialog.Show",), ("dialog.Raise",)])
+
+    def test_close_while_running_vetoes_or_saves_and_closes(self) -> None:
+        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
+        frame.input_txt.value = "edited"
+        self.outputs["edited"] = ConversionOutput("⠑", ())
+        frame.on_convert(None)
+        self.timers.timers[0].fire()
+        self._take()
+
+        frame._on_close(_CloseEvent(self.events, can_veto=True))
+
+        self.assertEqual(self._take(), [("close.Veto",)])
+        self.assertFalse(self.workspace.exists())
+
+        frame._on_close(_CloseEvent(self.events, can_veto=False))
+
+        self.assertEqual(
+            self._take(),
+            [("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",), ("dual_view.Destroy",), ("close.Skip",)],
+        )
+        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
+        self.assertIsNone(frame._dual_view_frame)
+
+    # --- single export -------------------------------------------------------
+
+    def test_single_export_with_braille_writes_and_reports(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "⠁⠃")], "alpha")
+        target = self.export_dir / "alpha.brl"
+        self.export_paths.append(target)
+
+        frame.on_export_document("brl")
+
+        self.assertEqual(self._take(), [self._export_dialog(frame, "alpha.brl"), self._exported(frame)])
+        self.assertEqual(target.read_bytes(), "⠁⠃".encode("utf-8"))
+        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "a", "⠁⠃"))
+        self.assertEqual(self.threads, [])
+
+    def test_single_export_write_error_and_extension_correction(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "⠁")], "alpha")
+        blocked = self.export_dir / "blocked.brl"
+        blocked.mkdir()
+        reason = self._os_error_text(blocked)
+        self.export_paths.extend([blocked, self.export_dir / "renamed.TXT"])
+
+        frame.on_export_document("brl")
+
+        self.assertEqual(
+            self._take(),
+            [
+                self._export_dialog(frame, "alpha.brl"),
+                self._error(frame, gui._("Failed to export document: {error}").format(error=reason)),
+            ],
+        )
+
+        frame.on_export_document("brl")
+
+        self.assertEqual(self._take(), [self._export_dialog(frame, "alpha.brl"), self._exported(frame)])
+        self.assertEqual((self.export_dir / "renamed.brl").read_text(encoding="utf-8"), "⠁")
+        self.assertFalse((self.export_dir / "renamed.TXT").exists())
+
+    def test_single_export_of_pending_document_converts_its_text_then_writes(self) -> None:
+        frame = self._make_frame(
+            [Document("alpha", "alpha text", "⠁"), Document("beta", "beta text", None)],
+            open_name="alpha",
+            selected_name="beta",
+        )
+        frame.input_txt.value = "alpha editor"
+        frame._document_controller.set_dual_view_results("beta", ("cached",))
+        target = self.export_dir / "beta.brl"
+        self.export_paths.append(target)
+        self.outputs["beta text"] = ConversionOutput("⠃⠃", ("result",), (_dual_view_segment("b", "⠃"),))
+
+        frame.on_export_document("brl")
+
+        self.assertEqual(
+            self._take(),
+            [self._export_dialog(frame, "beta.brl")] + self._busy(True) + [("call_later", 2000, (1,))],
+        )
+        self.assertFalse(target.exists())
+
+        self.threads[0].run()
+        self.assertEqual(self._take(), [("convert", "beta text"), ("call_after",)])
+        self.assertEqual(self.requests, [self._request("beta text")])
+
+        self.calls.run_next()
+
+        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._exported(frame)])
+        self.assertEqual(target.read_text(encoding="utf-8"), "⠃⠃")
+        self.assertEqual(frame.output_txt.value, "⠁")
+        self.assertEqual(
+            frame._document_controller.documents,
+            [Document("alpha", "alpha editor", "⠁"), Document("beta", "beta text", None)],
+        )
+        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": ("cached",)})
+
+    def test_single_export_of_pending_document_reports_conversion_or_table_error(self) -> None:
+        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
+        target = self.export_dir / "alpha.brl"
+        self.export_paths.extend([target, target])
+        self.outputs["alpha text"] = ConversionStageError("translation", RuntimeError("boom"))
+
+        frame.on_export_document("brl")
+        self.threads[0].run()
+        self._take()
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            [("timer.Stop", 1)]
+            + self._busy(False)
+            + [self._error(frame, gui._("Translation failed: {error}").format(error="boom"))],
+        )
+        self.assertFalse(target.exists())
+
+        frame.translation_tables = {"default": ""}
+        frame.on_export_document("brl")
+
+        self.assertEqual(
+            self._take(),
+            [self._export_dialog(frame, "alpha.brl"), self._error(frame, gui._("Please select a translation table first."))],
+        )
+        self.assertEqual(len(self.threads), 1)
+        self.assertEqual(len(self.timers.timers), 1)
+        self.assertFalse(target.exists())
+
+    # --- Export All ----------------------------------------------------------
+
+    def test_export_all_mixed_documents_turn_by_turn(self) -> None:
+        documents = [
+            Document("d1-ready", "t1", "⠁"),
+            Document("d2-pending", "t2", None),
+            Document("d3-ready", "t3", "⠉"),
+            Document("d4-write-fail", "t4", "⠙"),
+            Document("d5-convert-fail", "t5", None),
+            Document("d6-pending", "t6", None),
+        ]
+        frame = self._make_frame(documents, "d1-ready")
+        blocked = self.export_dir / "d4-write-fail.brl"
+        blocked.mkdir()
+        write_reason = self._os_error_text(blocked)
+        self.export_dirs.append(self.export_dir)
+        self.answers.append(gui.wx.YES)
+        self.outputs.update(
+            t2=ConversionOutput("⠃", ()),
+            t5=ConversionStageError("translation", RuntimeError("t5 boom")),
+            t6=ConversionOutput("⠋", ()),
+        )
+
+        def written() -> dict:
+            return {path.name: path.read_text(encoding="utf-8") for path in self.export_dir.glob("*.brl") if path.is_file()}
+
+        frame.on_export_all_documents("brl")
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("DirDialog", frame, gui._("Export All Documents")),
+                self._overwrite_question(frame),
+                ("call_after",),
+            ],
+        )
+        self.assertEqual(written(), {"d1-ready.brl": "⠁"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])
+        self.threads[0].run()
+        self.assertEqual(self._take(), [("convert", "t2"), ("call_after",)])
+        self.assertEqual(written(), {"d1-ready.brl": "⠁"})
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [("call_after",)])
+        self.assertEqual(written(), {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("call_after",)])
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("call_after",)])
+        self.assertEqual(written(), {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃", "d3-ready.brl": "⠉"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (2,))])
+        self.threads[1].run()
+        self.calls.run_next()
+        self.assertEqual(
+            self._take(),
+            [("convert", "t5"), ("call_after",), ("timer.Stop", 2)] + self._busy(False) + [("call_after",)],
+        )
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (3,))])
+        self.threads[2].run()
+        self.calls.run_next()
+        self.assertEqual(
+            self._take(),
+            [("convert", "t6"), ("call_after",), ("timer.Stop", 3)] + self._busy(False) + [("call_after",)],
+        )
+
+        self.calls.run_next()
+        # KNOWN BUG (P1-4 spec, defect 4): the partial-export summary is not translated.
+        summary = (
+            "Exported documents: 4\n"
+            "Failed documents: 2\n"
+            "\n"
+            f"d4-write-fail: {write_reason}\n"
+            f"d5-convert-fail: {gui._('Translation failed: {error}').format(error='t5 boom')}"
+        )
+        self.assertEqual(
+            self._take(),
+            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
+        )
+        self.assertEqual(self.calls.pending, [])
+        self.assertEqual(
+            written(),
+            {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃", "d3-ready.brl": "⠉", "d6-pending.brl": "⠋"},
+        )
+        self.assertEqual(frame._document_controller.documents, documents)
+        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
+        self.assertEqual(frame.output_txt.value, "⠁")
+
+    def test_export_all_ready_documents_shows_one_information_summary(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")], "alpha")
+        self.export_dirs.append(self.export_dir)
+
+        frame.on_export_all_documents("brl")
+        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("call_after",)])
+        self.calls.run_next()
+
+        # KNOWN BUG (P1-4 spec, defect 4): the message is not a msgid; only the caption is translated.
+        self.assertEqual(
+            self._take(),
+            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
+        )
+        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl", "beta.brl"])
+
+    def test_export_all_without_default_table_collects_failures_turn_by_turn(self) -> None:
+        frame = self._make_frame([Document("p1", "t1", None), Document("p2", "t2", None)], "p1")
+        frame.translation_tables = {}
+        self.export_dirs.append(self.export_dir)
+        message = gui._("Please select a translation table first.")
+
+        frame.on_export_all_documents("brl")
+        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("call_after",)])
+        self.calls.run_next()
+
+        summary = f"Exported documents: 0\nFailed documents: 2\n\np1: {message}\np2: {message}"
+        self.assertEqual(
+            self._take(),
+            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
+        )
+        self.assertEqual(self.threads, [])
+        self.assertEqual(list(self.export_dir.iterdir()), [])
+
+    def test_export_all_folder_and_overwrite_dialogs(self) -> None:
+        frame = self._make_frame([Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")], "alpha")
+
+        self.export_dirs.append(None)
+        frame.on_export_all_documents("brl")
+        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents"))])
+
+        self.export_dirs.append(self.export_dir)
+        frame.on_export_all_documents("brl")
+        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
+        self.calls.run_all()
+        self.events.clear()
+
+        (self.export_dir / "alpha.brl").write_text("old", encoding="utf-8")
+        (self.export_dir / "beta.brl").unlink()
+        self.export_dirs.append(self.export_dir)
+        self.answers.append(gui.wx.NO)
+        frame.on_export_all_documents("brl")
+        self.assertEqual(
+            self._take(),
+            [("DirDialog", frame, gui._("Export All Documents")), self._overwrite_question(frame)],
+        )
+        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl"])
+        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "old")
+
+        self.export_dirs.append(self.export_dir)
+        self.answers.append(gui.wx.YES)
+        frame.on_export_all_documents("brl")
+        self.calls.run_all()
+        self.assertEqual(
+            self._take(),
+            [
+                ("DirDialog", frame, gui._("Export All Documents")),
+                self._overwrite_question(frame),
+                ("call_after",),
+                ("call_after",),
+                self._info(frame, "All documents were exported successfully.", gui._("Export Complete")),
+            ],
+        )
+        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "⠁")
+        self.assertEqual((self.export_dir / "beta.brl").read_text(encoding="utf-8"), "⠃")
+
+    # --- re-entrancy (known defects 1 and 2) ----------------------------------
+
+    def test_ctrl_s_during_manual_conversion_supersedes_it(self) -> None:
+        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
+        target = self.export_dir / "alpha.brl"
+        self.export_paths.append(target)
+        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ())
+
+        frame.on_convert(None)
+        self._take()
+        event = _KeyEvent(self.CTRL_S)
+        frame.on_output_text_key_down(event)
+
+        # KNOWN BUG (P1-4 spec, defect 2): the export conversion starts without a running check.
+        self.assertEqual(
+            self._take(),
+            [self._export_dialog(frame, "alpha.brl")]
+            + self._busy(True)
+            + [("call_later", 2000, (2,)), ("focus", "output")],
+        )
+        self.assertFalse(event.skipped)
+        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))
+
+        self.threads[0].run()
+        self.threads[1].run()
+        self.assertEqual(self._take(), [("convert", "alpha text"), ("call_after",), ("convert", "alpha text"), ("call_after",)])
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [])
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [self._exported(frame)])
+        self.assertEqual(target.read_text(encoding="utf-8"), "⠁⠁")
+        self.assertFalse(self.timers.timers[0].stopped)
+        self.assertEqual(frame.output_txt.value, "")
+        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])
+
+    def test_ctrl_tab_during_manual_conversion_sends_result_to_new_document(self) -> None:
+        segment = _dual_view_segment("a", "⠁")
+        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
+        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (segment,))
+
+        frame.on_convert(None)
+        self._take()
+        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("set", "input", "beta text"),
+                ("set", "output", "⠃"),
+                ("title", gui._(gui.format_window_title("beta"))),
+                ("dual_view.refresh",),
+                ("focus", "input"),
+            ],
+        )
+        self.assertEqual(frame._document_controller.open_document_name, "beta")
+
+        self.threads[0].run()
+        self.calls.run_next()
+
+        # KNOWN BUG (P1-4 spec, defect 1): alpha's result lands in beta, the document open now.
+        self.assertEqual(
+            self._take(),
+            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 1)]
+            + self._busy(False)
+            + [("set", "output", "⠁⠁"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
+        )
+        self.assertEqual(
+            frame._document_controller.documents,
+            [Document("alpha", "alpha text", None), Document("beta", "beta text", "⠁⠁")],
+        )
+        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": (segment,)})
+
+    def test_convert_between_export_all_steps_is_superseded(self) -> None:
+        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
+        frame.input_txt.value = "manual text"
+        self.export_dirs.append(self.export_dir)
+        self.outputs.update({"manual text": ConversionOutput("⠍", ()), "t2": ConversionOutput("⠃", ())})
+
+        frame.on_export_all_documents("brl")
+        self._take()
+        frame.on_convert(None)
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])
+
+        self.calls.run_next()
+        # KNOWN BUG (P1-4 spec, defect 2): the next pending step starts a second job; the manual one is dropped.
+        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (2,))])
+
+        self.threads[0].run()
+        self.threads[1].run()
+        self.assertEqual(self._take(), [("convert", "manual text"), ("call_after",), ("convert", "t2"), ("call_after",)])
+        self.calls.run_next()
+        self.assertEqual(self._take(), [])
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [("call_after",)])
+        self.calls.run_next()
+        self.assertEqual(
+            self._take(),
+            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
+        )
+        self.assertEqual(frame.output_txt.value, "⠁")
+        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")
+
+
 if __name__ == "__main__":
     unittest.main()
PATCH
git -C $REPO status --short
```

Expected:

```text
 M client/tests/test_conversion_jobs.py
 M client/tests/test_gui_document_flows.py
?? client/tests/conversion_harness.py
```

- [ ] **Step 2: Run them; they pass on today's code.**

```bash
$PY -m unittest tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest -v 2>&1 | grep -E ' \.\.\. |^Ran|^OK|^FAILED' | sed -E 's/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//'
$PY -m unittest tests.test_conversion_jobs 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
test_close_while_running_vetoes_or_saves_and_closes ... ok
test_conversion_failure_messages_by_stage_and_public_text ... ok
test_convert_between_export_all_steps_is_superseded ... ok
test_convert_while_running_does_nothing ... ok
test_convert_without_default_table_shows_info_only ... ok
test_converting_dialog_appears_once_and_closes_on_completion ... ok
test_converting_dialog_timer_of_an_earlier_job_does_nothing ... ok
test_ctrl_s_during_manual_conversion_supersedes_it ... ok
test_ctrl_tab_during_manual_conversion_sends_result_to_new_document ... ok
test_export_all_folder_and_overwrite_dialogs ... ok
test_export_all_mixed_documents_turn_by_turn ... ok
test_export_all_ready_documents_shows_one_information_summary ... ok
test_export_all_without_default_table_collects_failures_turn_by_turn ... ok
test_manual_conversion_success_turn_by_turn ... ok
test_manual_conversion_without_open_document_updates_output_only ... ok
test_single_export_of_pending_document_converts_its_text_then_writes ... ok
test_single_export_of_pending_document_reports_conversion_or_table_error ... ok
test_single_export_with_braille_writes_and_reports ... ok
test_single_export_write_error_and_extension_correction ... ok
Ran 19 tests
OK
Ran 4 tests
OK
```

- [ ] **Step 3: Show that they bite (mutation check, then restore).** Two deliberate breaks of today's `gui.py`, one at a time: the Export All chain calls its next step directly instead of through `wx.CallAfter`, and the converting-dialog timer is never stopped.

```bash
sed -i 's/wx.CallAfter(self._export_next_document, /self._export_next_document(/' gui.py
$PY -m unittest tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest 2>&1 | grep -E '^(FAIL|ERROR):|^FAILED' | sed -E 's/ \(tests\.[^)]*\)//' | LC_ALL=C sort
git -C $REPO checkout -- client/gui.py
sed -i 's/self._convert_dialog_timer.Stop()/pass/' gui.py
$PY -m unittest tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest 2>&1 | grep -E '^FAILED'
git -C $REPO checkout -- client/gui.py
git -C $REPO status --short
```

Expected (the first break fails every test that steps an Export All chain; the second fails every test that reaches a delivery turn; `gui.py` is restored):

```text
FAIL: test_convert_between_export_all_steps_is_superseded
FAIL: test_export_all_folder_and_overwrite_dialogs
FAIL: test_export_all_mixed_documents_turn_by_turn
FAIL: test_export_all_ready_documents_shows_one_information_summary
FAIL: test_export_all_without_default_table_collects_failures_turn_by_turn
FAILED (failures=5)
FAILED (failures=15)
 M client/tests/test_conversion_jobs.py
 M client/tests/test_gui_document_flows.py
?? client/tests/conversion_harness.py
```

- [ ] **Step 4: Suite check and msgid scan.**

```bash
$T/tools/check_suite.sh 715 19 0
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
```

Expected:

```text
Ran 715 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 0 (expected 0)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (715)
new tests ok: 19 (expected 19)
new tests not ok: 0
source msgids: 353
SOURCE == SAVED
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/conversion_harness.py client/tests/test_conversion_jobs.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
test: characterize conversion and export flows

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
test: characterize conversion and export flows
```

---

### Task 2: Pin the conversion job runner contract (spec step 2)

**Files:**
- Modify: `client/tests/test_conversion_jobs.py` (4 tests; tabs)

**Interfaces:**
- Consumes: today's `ConversionJobRunner(*, runtime, on_success, on_failure, call_after, converter, thread_factory)`, `start`, `is_running`, `active_job_id`; the harness `make_thread_factory`.
- Produces: `test_each_start_creates_and_starts_one_daemon_thread` (ids 1, 2; `active_job_id` 0, 1, 2; `(daemon, started) == (True, True)` per thread), `test_is_running_is_false_inside_completion_callbacks` (a synchronous `call_after` delivers while the worker is still alive; both callbacks see `False`), `test_stale_delivery_keeps_the_current_job_running`, `test_exception_outside_conversion_stage_error_delivers_nothing` (the `RuntimeError` escapes `run()`; nothing delivered; `is_running()` false; defect 6).

- [ ] **Step 1: Add the runner contract tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_jobs.py b/client/tests/test_conversion_jobs.py
index b5fe4f3..1aa722a 100644
--- a/client/tests/test_conversion_jobs.py
+++ b/client/tests/test_conversion_jobs.py
@@ -10,7 +10,7 @@ from conversion.jobs import (
 )
 from config import DEFAULT_CHARSET_MAPS
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
-from tests.conversion_harness import FakeThread
+from tests.conversion_harness import FakeThread, make_thread_factory
 
 
 class ConversionJobRunnerTest(unittest.TestCase):
@@ -146,6 +146,77 @@ class ConversionJobRunnerTest(unittest.TestCase):
 			[ConversionJobFailure(job_id=second_job_id, error=error, completion_policy=second_policy)],
 		)
 
+	def test_each_start_creates_and_starts_one_daemon_thread(self) -> None:
+		runner, _successes, _failures, threads = self.make_runner(
+			converter=lambda _request, *, runtime: ConversionOutput("braille", ()),
+		)
+
+		self.assertEqual(runner.active_job_id, 0)
+		self.assertFalse(runner.is_running())
+		first_job_id = runner.start(self.make_request())
+		self.assertEqual((first_job_id, runner.active_job_id, len(threads)), (1, 1, 1))
+		second_job_id = runner.start(self.make_request())
+		self.assertEqual((second_job_id, runner.active_job_id, len(threads)), (2, 2, 2))
+
+		self.assertEqual([(thread.daemon, thread.started) for thread in threads], [(True, True), (True, True)])
+		self.assertTrue(runner.is_running())
+
+	def test_is_running_is_false_inside_completion_callbacks(self) -> None:
+		seen: list[tuple[str, bool]] = []
+		outcomes = [ConversionOutput("braille", ()), ConversionStageError("translation", RuntimeError("boom"))]
+
+		def converter(_request, *, runtime):
+			outcome = outcomes.pop(0)
+			if isinstance(outcome, Exception):
+				raise outcome
+			return outcome
+
+		thread_factory = make_thread_factory()
+		runner = ConversionJobRunner(
+			runtime=object(),
+			on_success=lambda _result: seen.append(("success", runner.is_running())),
+			on_failure=lambda _result: seen.append(("failure", runner.is_running())),
+			call_after=lambda fn, *args: fn(*args),
+			converter=converter,
+			thread_factory=thread_factory,
+		)
+
+		# The synchronous call_after delivers while the worker thread is still alive.
+		runner.start(self.make_request())
+		thread_factory.threads[0].run()
+		runner.start(self.make_request())
+		thread_factory.threads[1].run()
+
+		self.assertEqual(seen, [("success", False), ("failure", False)])
+
+	def test_stale_delivery_keeps_the_current_job_running(self) -> None:
+		runner, successes, failures, threads = self.make_runner(
+			converter=lambda _request, *, runtime: ConversionOutput("braille", ()),
+		)
+
+		runner.start(self.make_request())
+		runner.start(self.make_request())
+		threads[0].run()
+
+		self.assertEqual((successes, failures), ([], []))
+		self.assertTrue(runner.is_running())
+		self.assertEqual(runner.active_job_id, 2)
+
+	def test_exception_outside_conversion_stage_error_delivers_nothing(self) -> None:
+		def converter(_request, *, runtime):
+			raise RuntimeError("unexpected")
+
+		runner, successes, failures, threads = self.make_runner(converter=converter)
+
+		runner.start(self.make_request())
+		# KNOWN BUG (P1-4 spec, defect 6): nothing is delivered, so the UI would stay busy.
+		with self.assertRaisesRegex(RuntimeError, "unexpected"):
+			threads[0].run()
+
+		self.assertEqual((successes, failures), ([], []))
+		self.assertFalse(runner.is_running())
+		self.assertEqual(runner.active_job_id, 1)
+
 
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them; they pass on today's code.**

```bash
$PY -m unittest tests.test_conversion_jobs -v 2>&1 | grep -E ' \.\.\. |^Ran|^OK|^FAILED' | sed -E 's/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//'
```

Expected:

```text
test_each_start_creates_and_starts_one_daemon_thread ... ok
test_exception_outside_conversion_stage_error_delivers_nothing ... ok
test_is_running_is_false_inside_completion_callbacks ... ok
test_reports_conversion_stage_error_failure ... ok
test_stale_delivery_keeps_the_current_job_running ... ok
test_stale_failure_completion_is_ignored ... ok
test_stale_job_completion_is_ignored ... ok
test_start_runs_conversion_and_reports_success ... ok
Ran 8 tests
OK
```

- [ ] **Step 3: Show that they bite (mutation check, then restore).** Non-daemon threads, then a runner that clears its thread after the callback instead of before it.

```bash
sed -i 's/daemon=True,/daemon=False,/' conversion/jobs.py
$PY -m unittest tests.test_conversion_jobs 2>&1 | grep -E '^(FAIL|ERROR):|^FAILED' | sed -E 's/ \(tests\.[^)]*\)//'
git -C $REPO checkout -- client/conversion/jobs.py
$PY - <<'EOF'
from pathlib import Path
path = Path("conversion/jobs.py")
source = path.read_text(encoding="utf-8")
old = "\t\tself._thread = None\n\t\tself._on_success(result)\n"
assert source.count(old) == 1
path.write_text(source.replace(old, "\t\tself._on_success(result)\n\t\tself._thread = None\n"), encoding="utf-8")
EOF
$PY -m unittest tests.test_conversion_jobs 2>&1 | grep -E '^(FAIL|ERROR):|^FAILED' | sed -E 's/ \(tests\.[^)]*\)//'
git -C $REPO checkout -- client/conversion/jobs.py
git -C $REPO status --short
```

Expected:

```text
FAIL: test_each_start_creates_and_starts_one_daemon_thread
FAILED (failures=1)
FAIL: test_is_running_is_false_inside_completion_callbacks
FAILED (failures=1)
 M client/tests/test_conversion_jobs.py
```

- [ ] **Step 4: Suite check.**

```bash
$T/tools/check_suite.sh 719 23 0
```

Expected:

```text
Ran 719 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 0 (expected 0)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (719)
new tests ok: 23 (expected 23)
new tests not ok: 0
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_jobs.py
git -C $REPO commit -q -F - <<'MSG'
test: pin the conversion job runner contract

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
test: pin the conversion job runner contract
```

---

### Task 3: The wx-free conversion presenter (spec step 3)

**Files:**
- Create: `client/tests/test_conversion_presenter.py` (19 tests, no wx, no stub scope)
- Create: `client/conversion/presenter.py`

**Interfaces:**
- Consumes: `ConversionJobRunner` (unchanged in this task: `start` still takes a `ConversionJobRequest`, built with the default, unused policy); `conversion.service` (`ConversionOutput`, `ConversionRequest`, `ConversionStageError`, `convert_text_with_alignment`, `get_public_error_message`); `DocumentController` (`open_document_name`, `get_document`, `replace_document`, `set_dual_view_results`); `Document`; `i18n._`.
- Produces: `CONVERTING_DIALOG_DELAY_MS = 2000`; `Timer`, `ConversionView` (protocols: `get_source_text`, `set_conversion_busy`, `show_converting_dialog`, `close_converting_dialog`, `show_conversion_output`, `refresh_dual_view`, `show_info`, `show_error`); `missing_default_table_message(tables) -> str | None`; `format_conversion_error(error) -> str`; `ConversionPresenter(view, documents, *, runtime, build_request, get_translation_tables, call_after, call_later, thread_factory=threading.Thread, converter=convert_text_with_alignment)` with `is_running()`, `missing_table_message()`, `convert()`, `convert_for_export(raw_text, *, on_success, on_error)`. Order of effects: `convert()` checks running, then the table (`show_info(message, _("Info"))`), then reads the source text; `_start` sets busy, closes the dialog, builds the request, starts the job, records `_ActiveJob(job_id, export)` and arms `call_later(2000, _show_converting_dialog, job_id)`; the timer callback returns unless the job is the active one and still running; a delivery stops and clears the timer, closes the dialog, clears busy, then either calls the export callback or completes the manual conversion (output set and focused, open document replaced with the source text and braille, cache written under the open name, Dual View refreshed, "Conversion completed."), or shows the formatted error.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_presenter.py b/client/tests/test_conversion_presenter.py
new file mode 100644
index 0000000..a7a4869
--- /dev/null
+++ b/client/tests/test_conversion_presenter.py
@@ -0,0 +1,446 @@
+from __future__ import annotations
+
+import ast
+import unittest
+from pathlib import Path
+
+from conversion.presenter import (
+    CONVERTING_DIALOG_DELAY_MS,
+    ConversionPresenter,
+    format_conversion_error,
+    missing_default_table_message,
+)
+from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
+from documents.controller import DocumentController
+from documents.workspace import Document
+from i18n import _
+from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
+
+PRESENTER_PATH = Path(__file__).resolve().parents[1] / "conversion" / "presenter.py"
+
+
+class RecordingConversionView:
+    """Implements ``ConversionView``; every call lands in the shared event list."""
+
+    def __init__(self, events: list, source_text: str = ""):
+        self.events = events
+        self.source_text = source_text
+
+    def get_source_text(self) -> str:
+        self.events.append(("get_source_text",))
+        return self.source_text
+
+    def set_conversion_busy(self, busy: bool) -> None:
+        self.events.append(("busy", busy))
+
+    def show_converting_dialog(self) -> None:
+        self.events.append(("show_converting_dialog",))
+
+    def close_converting_dialog(self) -> None:
+        self.events.append(("close_converting_dialog",))
+
+    def show_conversion_output(self, text: str) -> None:
+        self.events.append(("show_conversion_output", text))
+
+    def refresh_dual_view(self) -> None:
+        self.events.append(("refresh_dual_view",))
+
+    def show_info(self, message: str, caption: str) -> None:
+        self.events.append(("show_info", message, caption))
+
+    def show_error(self, message: str, caption: str) -> None:
+        self.events.append(("show_error", message, caption))
+
+
+class ConversionPresenterTest(unittest.TestCase):
+    def setUp(self) -> None:
+        self.events: list = []
+        self.view = RecordingConversionView(self.events, "source")
+        self.documents = DocumentController(
+            documents=[Document("alpha", "old", None), Document("beta", "b", "⠃")],
+            open_name="alpha",
+            selected_name="alpha",
+        )
+        self.tables = {"default": "zh-tw.ctb"}
+        self.calls = DeferredCalls(self.events)
+        self.timers = FakeTimers(self.events)
+        self.thread_factory = make_thread_factory()
+        self.threads = self.thread_factory.threads
+        self.runtime = object()
+        self.outputs: dict = {}
+        self.requests: list = []
+
+    def _build_request(self, raw_text: str) -> ConversionRequest:
+        self.events.append(("build_request", raw_text))
+        return ConversionRequest(
+            raw_text=raw_text,
+            output_mode="unicode",
+            width=40,
+            dictionary_path=Path("dictionary/default.csv"),
+            data_dir=Path("data"),
+            translation_tables=dict(self.tables),
+            lang="zh_TW",
+            charset_maps={},
+        )
+
+    def _convert(self, request, *, runtime):
+        self.assertIs(runtime, self.runtime)
+        self.requests.append(request)
+        self.events.append(("convert", request.raw_text))
+        outcome = self.outputs[request.raw_text]
+        if isinstance(outcome, Exception):
+            raise outcome
+        return outcome
+
+    def _presenter(self, *, call_after=None) -> ConversionPresenter:
+        return ConversionPresenter(
+            self.view,
+            self.documents,
+            runtime=self.runtime,
+            build_request=self._build_request,
+            get_translation_tables=lambda: self.tables,
+            call_after=self.calls if call_after is None else call_after,
+            call_later=self.timers,
+            thread_factory=self.thread_factory,
+            converter=self._convert,
+        )
+
+    def _take(self) -> list:
+        taken = list(self.events)
+        self.events.clear()
+        return taken
+
+    def _export_callbacks(self) -> dict:
+        return {
+            "on_success": lambda braille: self.events.append(("on_success", braille)),
+            "on_error": lambda message: self.events.append(("on_error", message)),
+        }
+
+    def _end(self, timer_number: int = 1) -> list:
+        return [("timer.Stop", timer_number), ("close_converting_dialog",), ("busy", False)]
+
+    # --- module helpers ------------------------------------------------------
+
+    def test_module_imports_neither_wx_nor_gui(self) -> None:
+        tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
+        imported = set()
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Import):
+                imported.update(alias.name.split(".")[0] for alias in node.names)
+            elif isinstance(node, ast.ImportFrom):
+                imported.add((node.module or "").split(".")[0])
+
+        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)
+
+    def test_missing_default_table_message_reports_only_unset_default(self) -> None:
+        self.assertIsNone(missing_default_table_message({"default": "zh-tw.ctb"}))
+        for tables in ({}, {"default": ""}, {"default": None}):
+            with self.subTest(tables=tables):
+                self.assertEqual(
+                    missing_default_table_message(tables),
+                    _("Please select a translation table first."),
+                )
+
+    def test_format_conversion_error_by_stage(self) -> None:
+        for stage, template in (
+            ("ascii", "ASCII conversion failed: {error}"),
+            ("text_processing", "Text processing failed: {error}"),
+            ("translation", "Translation failed: {error}"),
+            ("other", "Translation failed: {error}"),
+        ):
+            with self.subTest(stage=stage):
+                self.assertEqual(
+                    format_conversion_error(ConversionStageError(stage, RuntimeError("script boom"))),
+                    _(template).format(error="script boom"),
+                )
+
+    def test_format_conversion_error_public_texts(self) -> None:
+        # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
+        for raw, public in (
+            ("", "An unknown error occurred."),
+            ("Can't translate: tables zh-tw.ctb inbuf=12", "The selected translation table could not translate this text."),
+        ):
+            with self.subTest(raw=raw):
+                self.assertEqual(
+                    format_conversion_error(ConversionStageError("translation", RuntimeError(raw))),
+                    _("Translation failed: {error}").format(error=public),
+                )
+
+    # --- convert -------------------------------------------------------------
+
+    def test_convert_reads_source_text_then_starts_job_and_timer(self) -> None:
+        presenter = self._presenter()
+
+        presenter.convert()
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("get_source_text",),
+                ("busy", True),
+                ("close_converting_dialog",),
+                ("build_request", "source"),
+                ("call_later", CONVERTING_DIALOG_DELAY_MS, (1,)),
+            ],
+        )
+        self.assertEqual(CONVERTING_DIALOG_DELAY_MS, 2000)
+        self.assertEqual([(thread.daemon, thread.started) for thread in self.threads], [(True, True)])
+        self.assertTrue(presenter.is_running())
+        self.assertEqual(self.requests, [])
+
+    def test_convert_without_default_table_shows_info_only(self) -> None:
+        self.tables = {"default": ""}
+        presenter = self._presenter()
+
+        presenter.convert()
+
+        self.assertEqual(
+            self._take(),
+            [("show_info", _("Please select a translation table first."), _("Info"))],
+        )
+        self.assertEqual(self.threads, [])
+
+    def test_convert_while_running_returns_before_table_check(self) -> None:
+        presenter = self._presenter()
+        presenter.convert()
+        self._take()
+        self.tables = {}
+
+        presenter.convert()
+
+        self.assertEqual(self._take(), [])
+        self.assertEqual(len(self.threads), 1)
+
+    def test_is_running_and_missing_table_message_read_live_state(self) -> None:
+        self.outputs["source"] = ConversionOutput("⠎", ())
+        presenter = self._presenter()
+
+        self.assertFalse(presenter.is_running())
+        self.assertIsNone(presenter.missing_table_message())
+        self.tables = {"default": None}
+        self.assertEqual(presenter.missing_table_message(), _("Please select a translation table first."))
+        self.tables = {"default": "zh-tw.ctb"}
+        presenter.convert()
+        self.assertTrue(presenter.is_running())
+        self.threads[0].run()
+        self.assertFalse(presenter.is_running())
+
+    # --- converting dialog timer ----------------------------------------------
+
+    def test_timer_shows_dialog_only_for_the_running_active_job(self) -> None:
+        self.outputs["source"] = ConversionOutput("⠎", ())
+        presenter = self._presenter()
+        presenter.convert()
+        self._take()
+
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [("show_converting_dialog",)])
+
+        self.threads[0].run()
+        self._take()
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [])
+
+        self.calls.run_next()
+        presenter.convert()
+        self._take()
+        self.timers.timers[0].fire()
+        self.assertEqual(self._take(), [])
+        self.timers.timers[1].fire()
+        self.assertEqual(self._take(), [("show_converting_dialog",)])
+
+    # --- manual completion ----------------------------------------------------
+
+    def test_manual_success_updates_output_document_cache_then_reports(self) -> None:
+        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
+        presenter = self._presenter()
+        presenter.convert()
+        self.threads[0].run()
+        self.assertEqual(self._take()[-2:], [("convert", "source"), ("call_after",)])
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end()
+            + [
+                ("show_conversion_output", "⠎"),
+                ("get_source_text",),
+                ("refresh_dual_view",),
+                ("show_info", _("Conversion completed."), _("Info")),
+            ],
+        )
+        self.assertEqual(self.documents.documents, [Document("alpha", "source", "⠎"), Document("beta", "b", "⠃")])
+        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})
+        self.assertFalse(presenter.is_running())
+
+    def test_manual_success_without_open_document_touches_no_document(self) -> None:
+        self.documents.open_name = None
+        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
+        presenter = self._presenter()
+        presenter.convert()
+        self.threads[0].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end()
+            + [
+                ("show_conversion_output", "⠎"),
+                ("refresh_dual_view",),
+                ("show_info", _("Conversion completed."), _("Info")),
+            ],
+        )
+        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
+        self.assertEqual(self.documents.dual_view_results_by_document, {})
+
+    def test_manual_success_with_open_name_missing_from_list_still_writes_cache(self) -> None:
+        self.documents.open_name = "ghost"
+        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
+        presenter = self._presenter()
+        presenter.convert()
+        self.threads[0].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end()
+            + [
+                ("show_conversion_output", "⠎"),
+                ("refresh_dual_view",),
+                ("show_info", _("Conversion completed."), _("Info")),
+            ],
+        )
+        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
+        self.assertEqual(self.documents.dual_view_results_by_document, {"ghost": ("segment",)})
+
+    def test_manual_failure_shows_error_after_busy_off(self) -> None:
+        self.outputs["source"] = ConversionStageError("text_processing", RuntimeError("script boom"))
+        presenter = self._presenter()
+        presenter.convert()
+        self.threads[0].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end() + [("show_error", _("Text processing failed: {error}").format(error="script boom"), _("Error"))],
+        )
+        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
+        self.assertEqual(self.documents.dual_view_results_by_document, {})
+
+    # --- export completion ----------------------------------------------------
+
+    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
+        self.tables = {}
+        presenter = self._presenter()
+
+        presenter.convert_for_export("doc text", **self._export_callbacks())
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("busy", True),
+                ("close_converting_dialog",),
+                ("build_request", "doc text"),
+                ("call_later", 2000, (1,)),
+            ],
+        )
+        self.assertEqual(len(self.threads), 1)
+
+    def test_export_success_calls_only_on_success(self) -> None:
+        self.documents.set_dual_view_results("alpha", ("manual",))
+        self.outputs["doc text"] = ConversionOutput("⠙", ("result",), ("export-segment",))
+        presenter = self._presenter()
+        presenter.convert_for_export("doc text", **self._export_callbacks())
+        self.threads[0].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(self._take(), self._end() + [("on_success", "⠙")])
+        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
+        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("manual",)})
+
+    def test_export_failure_calls_only_on_error(self) -> None:
+        self.outputs["doc text"] = ConversionStageError("ascii", RuntimeError("bad map"))
+        presenter = self._presenter()
+        presenter.convert_for_export("doc text", **self._export_callbacks())
+        self.threads[0].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end() + [("on_error", _("ASCII conversion failed: {error}").format(error="bad map"))],
+        )
+
+    def test_later_job_uses_its_own_completion(self) -> None:
+        self.outputs.update({"doc text": ConversionOutput("first", ()), "source": ConversionOutput("second", ())})
+        presenter = self._presenter()
+        presenter.convert_for_export("doc text", **self._export_callbacks())
+        self.threads[0].run()
+        self.calls.run_next()
+        presenter.convert()
+        self.threads[1].run()
+        self._take()
+
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            self._end(2)
+            + [
+                ("show_conversion_output", "second"),
+                ("get_source_text",),
+                ("refresh_dual_view",),
+                ("show_info", _("Conversion completed."), _("Info")),
+            ],
+        )
+
+    def test_superseded_job_delivers_nothing(self) -> None:
+        self.outputs.update({"source": ConversionOutput("manual", ()), "doc text": ConversionOutput("export", ())})
+        presenter = self._presenter()
+        presenter.convert()
+        # KNOWN BUG (P1-4 spec, defect 2): convert_for_export does not check for a running job.
+        presenter.convert_for_export("doc text", **self._export_callbacks())
+        self.threads[0].run()
+        self.threads[1].run()
+        self._take()
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [])
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), self._end(2) + [("on_success", "export")])
+        self.assertFalse(self.timers.timers[0].stopped)
+
+    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
+        self.outputs["source"] = ConversionOutput("⠎", ())
+        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
+        presenter.convert()
+        self._take()
+
+        self.threads[0].run()
+
+        self.assertEqual(
+            self._take(),
+            [("convert", "source")]
+            + self._end()
+            + [
+                ("show_conversion_output", "⠎"),
+                ("get_source_text",),
+                ("refresh_dual_view",),
+                ("show_info", _("Conversion completed."), _("Info")),
+            ],
+        )
+
+
+if __name__ == "__main__":
+    unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_conversion_presenter 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (the module does not exist yet):

```text
      1 ERROR: test_conversion_presenter (unittest.loader._FailedTest.test_conversion_presenter)
      1 FAILED (errors=1)
      1 ImportError: Failed to import test module: test_conversion_presenter
      1 ModuleNotFoundError: No module named 'conversion.presenter'
      1 Ran 1 test
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/presenter.py b/client/conversion/presenter.py
new file mode 100644
index 0000000..4a3399c
--- /dev/null
+++ b/client/conversion/presenter.py
@@ -0,0 +1,210 @@
+"""Conversion state machine of the main window, without wx.
+
+``ConversionPresenter`` starts conversion jobs, arms the "converting" dialog timer,
+toggles the busy state and completes manual and export conversions. It talks to the
+frame through ``ConversionView``. Threading is injected: ``call_after`` must defer to a
+later UI turn (as ``wx.CallAfter`` does), so the active job is recorded before any
+result can be delivered.
+"""
+
+from __future__ import annotations
+
+import threading
+from collections.abc import Callable, Mapping
+from dataclasses import dataclass
+from typing import Protocol
+
+from adapters.translation.contracts import TranslationRuntime
+from conversion.jobs import (
+    ConversionJobFailure,
+    ConversionJobRequest,
+    ConversionJobRunner,
+    ConversionJobSuccess,
+    ThreadFactory,
+)
+from conversion.service import (
+    ConversionOutput,
+    ConversionRequest,
+    ConversionStageError,
+    convert_text_with_alignment,
+    get_public_error_message,
+)
+from documents.controller import DocumentController
+from documents.workspace import Document
+from i18n import _
+
+CONVERTING_DIALOG_DELAY_MS = 2000
+
+
+class Timer(Protocol):
+    def Stop(self) -> object: ...
+
+
+CallAfter = Callable[..., object]
+CallLater = Callable[..., Timer]
+
+
+class ConversionView(Protocol):
+    def get_source_text(self) -> str: ...
+
+    def set_conversion_busy(self, busy: bool) -> None: ...
+
+    def show_converting_dialog(self) -> None: ...
+
+    def close_converting_dialog(self) -> None: ...
+
+    def show_conversion_output(self, text: str) -> None: ...
+
+    def refresh_dual_view(self) -> None: ...
+
+    def show_info(self, message: str, caption: str) -> None: ...
+
+    def show_error(self, message: str, caption: str) -> None: ...
+
+
+@dataclass(frozen=True)
+class _ExportCallbacks:
+    on_success: Callable[[str], None]
+    on_error: Callable[[str], None]
+
+
+@dataclass(frozen=True)
+class _ActiveJob:
+    job_id: int
+    export: _ExportCallbacks | None  # None: a manual conversion
+
+
+def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None:
+    if translation_tables.get("default"):
+        return None
+    return _("Please select a translation table first.")
+
+
+def format_conversion_error(error: ConversionStageError) -> str:
+    message_templates = {
+        "ascii": _("ASCII conversion failed: {error}"),
+        "text_processing": _("Text processing failed: {error}"),
+    }
+    message_template = message_templates.get(error.stage, _("Translation failed: {error}"))
+    error_text = _(get_public_error_message(error.error))
+    return message_template.format(error=error_text)
+
+
+class ConversionPresenter:
+    def __init__(
+        self,
+        view: ConversionView,
+        documents: DocumentController,
+        *,
+        runtime: TranslationRuntime,
+        build_request: Callable[[str], ConversionRequest],
+        get_translation_tables: Callable[[], Mapping[str, object]],
+        call_after: CallAfter,
+        call_later: CallLater,
+        thread_factory: ThreadFactory = threading.Thread,
+        converter: Callable[..., ConversionOutput] = convert_text_with_alignment,
+    ) -> None:
+        self._view = view
+        self._documents = documents
+        self._build_request = build_request
+        self._get_translation_tables = get_translation_tables
+        self._call_later = call_later
+        self._runner = ConversionJobRunner(
+            runtime=runtime,
+            on_success=self._on_job_success,
+            on_failure=self._on_job_failure,
+            call_after=call_after,
+            converter=converter,
+            thread_factory=thread_factory,
+        )
+        self._active: _ActiveJob | None = None
+        self._timer: Timer | None = None
+
+    def is_running(self) -> bool:
+        return self._runner.is_running()
+
+    def missing_table_message(self) -> str | None:
+        return missing_default_table_message(self._get_translation_tables())
+
+    def convert(self) -> None:
+        if self.is_running():
+            return
+        message = self.missing_table_message()
+        if message is not None:
+            self._view.show_info(message, _("Info"))
+            return
+        self._start(self._view.get_source_text(), export=None)
+
+    def convert_for_export(
+        self,
+        raw_text: str,
+        *,
+        on_success: Callable[[str], None],
+        on_error: Callable[[str], None],
+    ) -> None:
+        # No running check, as before (P1-4 spec, known defect 2): a running job is superseded.
+        self._start(raw_text, export=_ExportCallbacks(on_success, on_error))
+
+    def _start(self, raw_text: str, export: _ExportCallbacks | None) -> None:
+        self._view.set_conversion_busy(True)
+        self._view.close_converting_dialog()
+        request = self._build_request(raw_text)
+        job_id = self._runner.start(ConversionJobRequest(conversion_request=request))
+        self._active = _ActiveJob(job_id, export)
+        self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)
+
+    def _show_converting_dialog(self, job_id: int) -> None:
+        if job_id != self._runner.active_job_id:
+            return
+        if not self._runner.is_running():
+            return
+        self._view.show_converting_dialog()
+
+    def _take_active(self, job_id: int) -> _ActiveJob | None:
+        job = self._active
+        if job is None or job.job_id != job_id:
+            return None
+        self._active = None
+        return job
+
+    def _end_job(self) -> None:
+        if self._timer is not None:
+            self._timer.Stop()
+            self._timer = None
+        self._view.close_converting_dialog()
+        self._view.set_conversion_busy(False)
+
+    def _on_job_success(self, result: ConversionJobSuccess) -> None:
+        job = self._take_active(result.job_id)
+        if job is None:
+            return
+        self._end_job()
+        output = result.conversion_output
+        if job.export is not None:
+            job.export.on_success(output.display_text)
+            return
+        self._complete_manual(output)
+
+    def _on_job_failure(self, result: ConversionJobFailure) -> None:
+        job = self._take_active(result.job_id)
+        if job is None:
+            return
+        message = format_conversion_error(result.error)
+        self._end_job()
+        if job.export is not None:
+            job.export.on_error(message)
+            return
+        self._view.show_error(message, _("Error"))
+
+    def _complete_manual(self, output: ConversionOutput) -> None:
+        braille = output.display_text
+        self._view.show_conversion_output(braille)
+        # The result goes to the document open now, as before (P1-4 spec, known defect 1).
+        open_name = self._documents.open_document_name
+        if open_name:
+            document = self._documents.get_document(open_name)
+            if document is not None:
+                self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))
+            self._documents.set_dual_view_results(open_name, output.dual_view_segments)
+        self._view.refresh_dual_view()
+        self._view.show_info(_("Conversion completed."), _("Info"))
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the import grep (acceptance criterion 3 for the new module).**

```bash
$PY -m unittest tests.test_conversion_presenter 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 738 42 0
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo AC3; grep -nE "^(import wx|from wx)|^(import|from) gui" conversion/presenter.py
echo end
```

Expected (nothing between the labels):

```text
Ran 19 tests
OK
Ran 738 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 0 (expected 0)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (738)
new tests ok: 42 (expected 42)
new tests not ok: 0
source msgids: 353
SOURCE == SAVED
AC3
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/presenter.py client/tests/test_conversion_presenter.py
git -C $REPO commit -q -F - <<'MSG'
refactor: add the wx-free conversion presenter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: add the wx-free conversion presenter
```

---

### Task 4: Route conversion through the presenter (spec step 4)

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`

**Interfaces:**
- Consumes: Task 3's `ConversionPresenter` and `missing_default_table_message`.
- Produces in `gui.BrailleFrame`: `_initialize_conversion_state()` sets `_convert_dialog = None` and `_conversion_presenter = ConversionPresenter(self, self._document_controller, runtime=self.translation_runtime, build_request=self._build_conversion_request_for_text, get_translation_tables=lambda: self.translation_tables, call_after=wx.CallAfter, call_later=wx.CallLater)`; `_build_conversion_request_for_text(raw_text)` (current settings and dictionary path, then the unchanged `_build_conversion_request`); `on_convert` calls `presenter.convert()`; `_on_close` asks `presenter.is_running()` and calls `close_converting_dialog()`; public view methods `get_source_text`, `set_conversion_busy`, `show_converting_dialog`, `close_converting_dialog`, `show_conversion_output`, `refresh_dual_view`, `show_info`, `show_error`; a temporary `_start_export_conversion` (same signature and result as today; table check through `missing_default_table_message(self.translation_tables)`, then `presenter.convert_for_export(document.text, on_success=..., on_error=...)`; refinement 8). Deleted: `_set_conversion_busy`, `_start_conversion`, `_show_converting_dialog`, `_close_converting_dialog`, `_complete_conversion`, `_finish_conversion_success`, `_finish_conversion_failure`, `_missing_default_table_message`, `_conversion_runner`, `_convert_dialog_timer`; imports `conversion.jobs`, `ConversionOutput`, `get_public_error_message`.
- Test helpers: `GuiDocumentFlowsTest._make_frame` and `DocumentWorkspaceFlowsCharacterizationTest._make_workspace_frame` set `_conversion_presenter = Mock(spec=gui.ConversionPresenter)` (`is_running` false) instead of the runner, timer, busy and dialog mocks; `_make_workspace_frame` mocks `close_converting_dialog`, and `test_close_vetoes_when_save_fails` checks it. `_wire_conversion` builds a real `gui.ConversionPresenter` with the harness fakes and the scripted converter.

- [ ] **Step 1: Write the failing frame tests** (`FrameConversionDelegationTest`, 4 tests; `FrameViewMethodsTest`, 7 tests; appended at the end).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 9c42325..fd348a6 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -3633,5 +3633,200 @@ class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
         self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")
 
 
+
+class FrameConversionDelegationTest(unittest.TestCase):
+    """The frame wires the conversion presenter and hands it the conversion commands."""
+
+    def _make_frame(self) -> gui.BrailleFrame:
+        frame = object.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController()
+        frame.translation_runtime = Mock()
+        frame.translation_tables = {"default": "zh-tw.ctb"}
+        return frame
+
+    def test_initialize_conversion_state_wires_presenter_with_wx_scheduling(self) -> None:
+        frame = self._make_frame()
+
+        with patch.object(gui, "ConversionPresenter") as presenter_class:
+            frame._initialize_conversion_state()
+
+        presenter_class.assert_called_once_with(
+            frame,
+            frame._document_controller,
+            runtime=frame.translation_runtime,
+            build_request=frame._build_conversion_request_for_text,
+            get_translation_tables=ANY,
+            call_after=gui.wx.CallAfter,
+            call_later=gui.wx.CallLater,
+        )
+        self.assertIs(frame._conversion_presenter, presenter_class.return_value)
+        self.assertIsNone(frame._convert_dialog)
+        get_tables = presenter_class.call_args.kwargs["get_translation_tables"]
+        self.assertIs(get_tables(), frame.translation_tables)
+        frame.translation_tables = {"default": "en-ueb-g1.ctb"}
+        self.assertIs(get_tables(), frame.translation_tables)
+
+    def test_build_conversion_request_for_text_reads_current_settings(self) -> None:
+        frame = self._make_frame()
+        frame.translation_settings = TranslationSettings("ascii", 32, "math")
+        frame.dictionary_dir = Path("dictionaries")
+
+        with patch.object(gui, "get_lang", return_value="zh_TW"), patch.object(
+            gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}
+        ):
+            request = frame._build_conversion_request_for_text("text")
+
+        self.assertEqual(
+            request,
+            ConversionRequest(
+                raw_text="text",
+                output_mode="ascii",
+                width=32,
+                dictionary_path=Path("dictionaries/math.csv"),
+                data_dir=gui.resource_path("data"),
+                translation_tables={"default": "zh-tw.ctb"},
+                lang="zh_TW",
+                charset_maps={"CJKCharactersLanguage": "zh"},
+            ),
+        )
+
+    def test_convert_command_and_ctrl_enter_delegate_to_presenter(self) -> None:
+        frame = self._make_frame()
+        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
+        event = Mock()
+        event.GetKeyCode.return_value = 13
+        event.ControlDown.return_value = True
+
+        frame.on_convert(None)
+        frame.on_input_text_key_down(event)
+
+        self.assertEqual(frame._conversion_presenter.mock_calls, [call.convert(), call.convert()])
+        event.Skip.assert_not_called()
+
+    def test_close_asks_presenter_before_saving(self) -> None:
+        frame = self._make_frame()
+        steps = Mock()
+        frame._conversion_presenter = steps.presenter
+        frame._save_open_document_with_feedback = steps.save
+        frame.close_converting_dialog = steps.close_converting_dialog
+        frame._dual_view_frame = None
+        event = steps.event
+
+        steps.presenter.is_running.return_value = True
+        event.CanVeto.return_value = True
+        frame._on_close(event)
+        self.assertEqual(steps.mock_calls, [call.presenter.is_running(), call.event.CanVeto(), call.event.Veto()])
+
+        steps.reset_mock()
+        steps.presenter.is_running.return_value = False
+        steps.save.return_value = True
+        frame._on_close(event)
+        self.assertEqual(
+            steps.mock_calls,
+            [call.presenter.is_running(), call.save(), call.close_converting_dialog(), call.event.Skip()],
+        )
+
+
+class FrameViewMethodsTest(unittest.TestCase):
+    """The frame's small wx methods behind the presenter view protocols."""
+
+    def _make_frame(self, menu_bar=None) -> gui.BrailleFrame:
+        frame = object.__new__(gui.BrailleFrame)
+        frame.steps = Mock()
+        frame.input_txt = frame.steps.input_txt
+        frame.output_txt = frame.steps.output_txt
+        frame.document_list = frame.steps.document_list
+        frame.GetMenuBar = lambda: menu_bar
+        frame._convert_dialog = None
+        return frame
+
+    def test_get_source_text_reads_the_source_editor(self) -> None:
+        frame = self._make_frame()
+        frame.input_txt.GetValue.return_value = "source"
+
+        self.assertEqual(frame.get_source_text(), "source")
+
+    def test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source(self) -> None:
+        menu_bar = Mock()
+        menu_bar.FindMenu.side_effect = lambda title: {gui._("File"): 0, gui._("Translation"): 1}.get(
+            title, gui.wx.NOT_FOUND
+        )
+        frame = self._make_frame(menu_bar)
+        frame.steps.attach_mock(menu_bar, "menu_bar")
+
+        for busy in (True, False):
+            with self.subTest(busy=busy):
+                frame.steps.reset_mock()
+                frame.set_conversion_busy(busy)
+                self.assertEqual(
+                    frame.steps.mock_calls,
+                    [
+                        call.menu_bar.FindMenu(gui._("File")),
+                        call.menu_bar.EnableTop(0, not busy),
+                        call.menu_bar.FindMenu(gui._("Translation")),
+                        call.menu_bar.EnableTop(1, not busy),
+                        call.document_list.Enable(not busy),
+                        call.input_txt.Enable(not busy),
+                    ],
+                )
+
+    def test_set_conversion_busy_without_menu_bar_or_menus_still_toggles_controls(self) -> None:
+        missing = Mock()
+        missing.FindMenu.return_value = gui.wx.NOT_FOUND
+        for menu_bar in (None, missing):
+            with self.subTest(menu_bar=menu_bar):
+                frame = self._make_frame(menu_bar)
+                frame.set_conversion_busy(True)
+                self.assertEqual(
+                    frame.steps.mock_calls,
+                    [call.document_list.Enable(False), call.input_txt.Enable(False)],
+                )
+        missing.EnableTop.assert_not_called()
+
+    def test_converting_dialog_is_shown_once_and_closed_once(self) -> None:
+        frame = self._make_frame()
+        with patch.object(gui, "ConvertingDialog") as dialog_class, patch.object(gui.wx, "EVT_CLOSE", "EVT_CLOSE"):
+            frame.show_converting_dialog()
+            frame.show_converting_dialog()
+            dialog = dialog_class.return_value
+            self.assertEqual(dialog_class.call_args_list, [call(frame)])
+            self.assertEqual(dialog.mock_calls, [call.Show(), call.Raise()])
+
+            frame.close_converting_dialog()
+            frame.close_converting_dialog()
+
+        self.assertEqual(dialog.mock_calls, [call.Show(), call.Raise(), call.Unbind("EVT_CLOSE"), call.Destroy()])
+        self.assertIsNone(frame._convert_dialog)
+
+    def test_show_conversion_output_sets_then_focuses_braille_result(self) -> None:
+        frame = self._make_frame()
+
+        frame.show_conversion_output("⠃")
+
+        self.assertEqual(frame.steps.mock_calls, [call.output_txt.SetValue("⠃"), call.output_txt.SetFocus()])
+
+    def test_refresh_dual_view_uses_the_frame_refresh(self) -> None:
+        frame = self._make_frame()
+        frame._refresh_dual_view = Mock()
+
+        frame.refresh_dual_view()
+
+        frame._refresh_dual_view.assert_called_once_with()
+
+    def test_message_methods_use_one_message_box_each(self) -> None:
+        frame = self._make_frame()
+        with patch.object(gui.wx, "MessageBox") as message_box:
+            frame.show_info("info text", "Info caption")
+            frame.show_error("error text", "Error caption")
+
+        self.assertEqual(
+            message_box.call_args_list,
+            [
+                call("info text", "Info caption", gui.wx.OK | gui.wx.ICON_INFORMATION, parent=frame),
+                call("error text", "Error caption", gui.wx.OK | gui.wx.ICON_ERROR, parent=frame),
+            ],
+        )
+
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_gui_document_flows.FrameConversionDelegationTest tests.test_gui_document_flows.FrameViewMethodsTest 2>&1 | grep -E '^(ERROR|FAIL):|^(Attribute|Type)Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//; s/id='[0-9]+'/id=?/g" | LC_ALL=C sort | uniq -c
```

Expected (`gui` has no presenter yet, so the wiring and delegation tests cannot patch or spec it; on the stub frame the missing view methods are no-op functions, so their tests fail on the recorded calls (the `AssertionError` texts are left out because they contain object addresses); `_on_close` still asks the missing `_conversion_runner`):

```text
      1 AttributeError: 'function' object has no attribute 'is_running'
      1 AttributeError: <module 'gui' from 'client/gui.py'> does not have the attribute 'ConversionPresenter'
      1 AttributeError: module 'gui' has no attribute 'ConversionPresenter'. Did you mean: 'ConversionJobRunner'?
      1 ERROR: test_close_asks_presenter_before_saving
      1 ERROR: test_convert_command_and_ctrl_enter_delegate_to_presenter
      1 ERROR: test_initialize_conversion_state_wires_presenter_with_wx_scheduling
      1 FAIL: test_build_conversion_request_for_text_reads_current_settings
      1 FAIL: test_converting_dialog_is_shown_once_and_closed_once
      1 FAIL: test_get_source_text_reads_the_source_editor
      1 FAIL: test_message_methods_use_one_message_box_each
      1 FAIL: test_refresh_dual_view_uses_the_frame_refresh
      1 FAIL: test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source (busy=False)
      1 FAIL: test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source (busy=True)
      1 FAIL: test_set_conversion_busy_without_menu_bar_or_menus_still_toggles_controls (menu_bar=<Mock id=?>)
      1 FAIL: test_set_conversion_busy_without_menu_bar_or_menus_still_toggles_controls (menu_bar=None)
      1 FAIL: test_show_conversion_output_sets_then_focuses_braille_result
      1 FAILED (failures=10, errors=3)
      1 Ran 11 tests
```

- [ ] **Step 3: Implement, and move the frame's conversion tests.** The patch routes `gui` through the presenter, deletes the frame's conversion state machine, switches the three frame helpers (refinement 8 and the Interfaces above) and deletes the 12 conversion tests of `BrailleAppLifecycleTest` that Task 3 now covers (spec Part E rows 2-4; refinement 9).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index 7142f7d..3973fbe 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -10,18 +10,10 @@ from i18n import _, resource_path
 from app_paths import ApplicationDataError, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
-from conversion.jobs import (
-	ConversionCompletionPolicy,
-	ConversionJobFailure,
-	ConversionJobRequest,
-	ConversionJobRunner,
-	ConversionJobSuccess,
-)
+from conversion.presenter import ConversionPresenter, missing_default_table_message
 from conversion.service import (
-	ConversionOutput,
 	ConversionRequest,
 	ConversionStageError,
-	get_public_error_message,
 )
 from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
@@ -220,14 +212,16 @@ class BrailleFrame(wx.Frame):
 		return editors_box
 
 	def _initialize_conversion_state(self) -> None:
-		self._conversion_runner = ConversionJobRunner(
+		self._convert_dialog = None
+		self._conversion_presenter = ConversionPresenter(
+			self,
+			self._document_controller,
 			runtime=self.translation_runtime,
-			on_success=self._finish_conversion_success,
-			on_failure=self._finish_conversion_failure,
+			build_request=self._build_conversion_request_for_text,
+			get_translation_tables=lambda: self.translation_tables,
 			call_after=wx.CallAfter,
+			call_later=wx.CallLater,
 		)
-		self._convert_dialog = None
-		self._convert_dialog_timer = None
 
 	def _apply_initial_settings(self, initial_settings: ViewSettings) -> None:
 		self._apply_editor_view_settings(initial_settings)
@@ -553,6 +547,15 @@ class BrailleFrame(wx.Frame):
 			charset_maps=get_charset_maps(),
 		)
 
+	def _build_conversion_request_for_text(self, raw_text: str) -> ConversionRequest:
+		settings = self.translation_settings
+		return self._build_conversion_request(
+			raw_text,
+			settings.output_mode,
+			settings.width,
+			self._get_selected_dictionary_path(),
+		)
+
 	def _format_batch_issue_lines(self, issues: list[BatchIssue]) -> list[str]:
 		return [f"{issue.path.name}: {issue.reason}" for issue in issues]
 
@@ -1031,11 +1034,6 @@ class BrailleFrame(wx.Frame):
 			parent=self,
 		)
 
-	def _missing_default_table_message(self) -> str | None:
-		if self.translation_tables.get("default"):
-			return None
-		return _("Please select a translation table first.")
-
 	def _start_export_conversion(
 		self,
 		document: Document,
@@ -1046,24 +1044,14 @@ class BrailleFrame(wx.Frame):
 		on_error=None,
 		on_missing_table=None,
 	) -> bool:
-		message = self._missing_default_table_message()
+		message = missing_default_table_message(self.translation_tables)
 		if message is not None:
 			if on_missing_table is not None:
 				on_missing_table(message)
 			elif on_error is not None:
 				on_error(message)
 			return False
-		settings = self.translation_settings
-		self._start_conversion(
-			document.text,
-			settings.width,
-			settings.output_mode,
-			self._get_selected_dictionary_path(),
-			on_success=on_success,
-			on_error=on_error,
-			update_output=False,
-			show_success=False,
-		)
+		self._conversion_presenter.convert_for_export(document.text, on_success=on_success, on_error=on_error)
 		return True
 
 	def _export_next_document(
@@ -1122,43 +1110,29 @@ class BrailleFrame(wx.Frame):
 		)
 
 	def on_convert(self, _evt):
-		if self._conversion_runner.is_running():
-			return
-
-		message = self._missing_default_table_message()
-		if message is not None:
-			wx.MessageBox(
-				message,
-				_("Info"),
-				wx.OK | wx.ICON_INFORMATION,
-				parent=self,
-			)
-			return
-		raw_text = self.input_txt.GetValue()
-		settings = self.translation_settings
-		self._start_conversion(
-			raw_text,
-			settings.width,
-			settings.output_mode,
-			self._get_selected_dictionary_path(),
-		)
+		self._conversion_presenter.convert()
 
 	def _on_close(self, evt: wx.CloseEvent):
-		if self._conversion_runner.is_running() and evt.CanVeto():
+		if self._conversion_presenter.is_running() and evt.CanVeto():
 			evt.Veto()
 			return
 		if not self._save_open_document_with_feedback():
 			if evt.CanVeto():
 				evt.Veto()
 			return
-		self._close_converting_dialog()
+		self.close_converting_dialog()
 		if self._dual_view_frame is not None:
 			viewer = self._dual_view_frame
 			self._dual_view_frame = None
 			viewer.Destroy()
 		evt.Skip()
 
-	def _set_conversion_busy(self, busy: bool):
+	# --- ConversionView (conversion/presenter.py) ---------------------------
+
+	def get_source_text(self) -> str:
+		return self.input_txt.GetValue()
+
+	def set_conversion_busy(self, busy: bool) -> None:
 		menu_bar = self.GetMenuBar()
 		if menu_bar is not None:
 			for menu_label in (_("File"), _("Translation")):
@@ -1168,51 +1142,14 @@ class BrailleFrame(wx.Frame):
 		self.document_list.Enable(not busy)
 		self.input_txt.Enable(not busy)
 
-	def _start_conversion(
-		self,
-		raw_text: str,
-		width: int,
-		output_mode: str,
-		dictionary_path: Path,
-		*,
-		on_success=None,
-		on_error=None,
-		update_output: bool = True,
-		show_success: bool = True,
-	):
-		self._set_conversion_busy(True)
-		self._close_converting_dialog()
-		policy = ConversionCompletionPolicy(
-			on_success=on_success,
-			on_error=on_error,
-			update_output=update_output,
-			show_success=show_success,
-		)
-		job_id = self._conversion_runner.start(
-			ConversionJobRequest(
-			conversion_request=self._build_conversion_request(
-				raw_text,
-				output_mode,
-					width,
-					dictionary_path,
-				),
-				completion_policy=policy,
-			)
-		)
-		self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)
-
-	def _show_converting_dialog(self, job_id: int):
-		if job_id != self._conversion_runner.active_job_id:
-			return
-		if not self._conversion_runner.is_running():
-			return
+	def show_converting_dialog(self) -> None:
 		if self._convert_dialog is not None:
 			return
 		self._convert_dialog = ConvertingDialog(self)
 		self._convert_dialog.Show()
 		self._convert_dialog.Raise()
 
-	def _close_converting_dialog(self):
+	def close_converting_dialog(self) -> None:
 		if self._convert_dialog is None:
 			return
 		dialog = self._convert_dialog
@@ -1220,77 +1157,18 @@ class BrailleFrame(wx.Frame):
 		dialog.Unbind(wx.EVT_CLOSE)
 		dialog.Destroy()
 
-	def _complete_conversion(
-		self,
-		policy: ConversionCompletionPolicy,
-		conversion_output: ConversionOutput | None = None,
-		error_message: str | None = None,
-		display_text: str | None = None,
-	):
-		if self._convert_dialog_timer is not None:
-			self._convert_dialog_timer.Stop()
-			self._convert_dialog_timer = None
-		self._close_converting_dialog()
-		self._set_conversion_busy(False)
-		on_success = policy.on_success
-		on_error = policy.on_error
-		update_output = policy.update_output
-		show_success = policy.show_success
-
-		if error_message is not None:
-			if on_error is not None:
-				on_error(error_message)
-			else:
-				wx.MessageBox(
-					error_message,
-					_("Error"),
-					wx.OK | wx.ICON_ERROR,
-					parent=self,
-				)
-			return
+	def show_conversion_output(self, text: str) -> None:
+		self.output_txt.SetValue(text)
+		self.output_txt.SetFocus()
 
-		output = conversion_output or ConversionOutput(display_text or "", ())
-		converted_braille = output.display_text
-		if update_output:
-			self.output_txt.SetValue(converted_braille)
-			self.output_txt.SetFocus()
-			controller = self._document_controller
-			open_name = controller.open_document_name
-			if open_name:
-				document = controller.get_document(open_name)
-				if document is not None:
-					controller.replace_document(
-						Document(
-							document.name,
-							self.input_txt.GetValue(),
-							converted_braille,
-						)
-					)
-				controller.set_dual_view_results(open_name, output.dual_view_segments)
-			self._refresh_dual_view()
-		if on_success is not None:
-			on_success(converted_braille)
-		if show_success:
-			wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
-
-	def _finish_conversion_success(self, result: ConversionJobSuccess) -> None:
-		self._complete_conversion(result.completion_policy, conversion_output=result.conversion_output)
-
-	def _finish_conversion_failure(self, result: ConversionJobFailure) -> None:
-		message_templates = {
-			"ascii": _("ASCII conversion failed: {error}"),
-			"text_processing": _("Text processing failed: {error}"),
-		}
-		message_template = message_templates.get(
-			result.error.stage,
-			_("Translation failed: {error}"),
-		)
-		error_text = _(get_public_error_message(result.error.error))
-		self._complete_conversion(
-			result.completion_policy,
-			error_message=message_template.format(error=error_text),
-		)
+	def refresh_dual_view(self) -> None:
+		self._refresh_dual_view()
+
+	def show_info(self, message: str, caption: str) -> None:
+		wx.MessageBox(message, caption, wx.OK | wx.ICON_INFORMATION, parent=self)
 
+	def show_error(self, message: str, caption: str) -> None:
+		wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR, parent=self)
 
 def _show_application_data_error(error: ApplicationDataError) -> None:
 	wx.MessageBox(
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index fd348a6..7ee9da8 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -54,13 +54,9 @@ class GuiDocumentFlowsTest(unittest.TestCase):
     def _make_frame(self, documents=(Document("alpha", "source", None),), open_name="alpha") -> gui.BrailleFrame:
         frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
         frame.translation_runtime = Mock()
-        frame._conversion_runner = Mock()
-        frame._conversion_runner.is_running.return_value = False
-        frame._conversion_runner.start = Mock(return_value=7)
-        frame._convert_dialog_timer = Mock()
+        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
+        frame._conversion_presenter.is_running.return_value = False
         frame._convert_dialog = Mock()
-        frame._set_conversion_busy = Mock()
-        frame._close_converting_dialog = Mock()
         frame.input_txt = Mock()
         frame.output_txt = Mock()
         frame._show_export_all_result = Mock()
@@ -709,131 +705,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         log_exception.assert_called_once_with("Failed to clean up dual-view HTML")
         runtime.close.assert_called_once_with()
 
-    def test_start_conversion_builds_request_and_starts_runner(self) -> None:
-        frame = self._make_frame()
-        frame._build_conversion_request = Mock(return_value=Mock())
-        with patch.object(gui.wx, "CallLater", return_value=Mock()) as call_later:
-            frame._start_conversion(
-                "source",
-                40,
-                "unicode",
-                Path("dictionary/default.csv"),
-            )
-
-        frame._build_conversion_request.assert_called_once_with(
-            "source",
-            "unicode",
-            40,
-            Path("dictionary/default.csv"),
-        )
-        frame._conversion_runner.start.assert_called_once_with(
-            gui.ConversionJobRequest(
-                conversion_request=frame._build_conversion_request.return_value,
-                completion_policy=gui.ConversionCompletionPolicy(),
-            )
-        )
-        frame._set_conversion_busy.assert_called_once_with(True)
-        frame._close_converting_dialog.assert_called_once_with()
-        call_later.assert_called_once_with(2000, frame._show_converting_dialog, 7)
-
-    def test_manual_conversion_updates_output_focus_and_shows_completion(self) -> None:
-        frame = self._make_frame()
-        frame.input_txt.GetValue.return_value = "source"
-        policy = gui.ConversionCompletionPolicy()
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame._complete_conversion(policy, display_text="braille")
-
-        frame.output_txt.SetValue.assert_called_once_with("braille")
-        frame.output_txt.SetFocus.assert_called_once_with()
-        self.assertEqual(frame._document_controller.get_document("alpha").braille, "braille")
-        message_box.assert_called_once_with(
-            gui._("Conversion completed."),
-            gui._("Info"),
-            gui.wx.OK | gui.wx.ICON_INFORMATION,
-            parent=frame,
-        )
-
-    def test_export_conversion_calls_success_callback_without_manual_message(self) -> None:
-        frame = self._make_frame()
-        on_success = Mock()
-        policy = gui.ConversionCompletionPolicy(
-            on_success=on_success,
-            update_output=False,
-            show_success=False,
-        )
-
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame._complete_conversion(policy, display_text="braille")
-
-        on_success.assert_called_once_with("braille")
-        frame.output_txt.SetValue.assert_not_called()
-        frame.output_txt.SetFocus.assert_not_called()
-        message_box.assert_not_called()
-
-    def test_export_conversion_calls_error_callback_without_showing_worker_error(self) -> None:
-        frame = self._make_frame()
-        on_error = Mock()
-        policy = gui.ConversionCompletionPolicy(
-            on_error=on_error,
-            update_output=False,
-            show_success=False,
-        )
-
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame._complete_conversion(policy, error_message="boom")
-
-        on_error.assert_called_once_with("boom")
-        message_box.assert_not_called()
-
-    def test_text_processing_failure_uses_its_own_message(self) -> None:
-        frame = self._make_frame()
-        result = gui.ConversionJobFailure(
-            job_id=1,
-            error=gui.ConversionStageError("text_processing", RuntimeError("script boom")),
-            completion_policy=gui.ConversionCompletionPolicy(),
-        )
-        frame._complete_conversion = Mock()
-
-        frame._finish_conversion_failure(result)
-
-        frame._complete_conversion.assert_called_once_with(
-            result.completion_policy,
-            error_message=gui._("Text processing failed: {error}").format(error="script boom"),
-        )
-
-    def test_later_job_uses_its_own_policy_after_previous_completion(self) -> None:
-        frame = self._make_frame()
-        first_policy = gui.ConversionCompletionPolicy(
-            on_success=Mock(),
-            update_output=False,
-            show_success=False,
-        )
-        second_policy = gui.ConversionCompletionPolicy()
-        first_result = gui.ConversionJobSuccess(
-            job_id=1,
-            conversion_output=gui.ConversionOutput("first", ("old",)),
-            completion_policy=first_policy,
-        )
-        second_result = gui.ConversionJobSuccess(
-            job_id=2,
-            conversion_output=gui.ConversionOutput("second", ("new",)),
-            completion_policy=second_policy,
-        )
-
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame._finish_conversion_success(first_result)
-            frame._finish_conversion_success(second_result)
-
-        first_policy.on_success.assert_called_once_with("first")
-        frame.output_txt.SetValue.assert_called_once_with("second")
-        frame.output_txt.SetFocus.assert_called_once_with()
-        message_box.assert_called_once_with(
-            gui._("Conversion completed."),
-            gui._("Info"),
-            gui.wx.OK | gui.wx.ICON_INFORMATION,
-            parent=frame,
-        )
-
     def test_export_all_continues_after_conversion_failure(self) -> None:
         frame = self._make_frame()
         written: list[tuple[str, str]] = []
@@ -902,41 +773,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         result = frame._show_export_all_result.call_args.args[0]
         self.assertTrue(result.all_succeeded)
 
-    def test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer(self) -> None:
-        frame = self._make_frame()
-        policy = gui.ConversionCompletionPolicy(show_success=False)
-        frame._dual_view_frame = Mock()
-        frame._refresh_dual_view = Mock()
-        conversion_output = gui.ConversionOutput("braille", ("segment",), dual_view_segments=("segment",))
-
-        with patch.object(gui.wx, "MessageBox"):
-            frame._finish_conversion_success(
-                gui.ConversionJobSuccess(
-                    job_id=1,
-                    conversion_output=conversion_output,
-                    completion_policy=policy,
-                )
-            )
-
-        self.assertEqual(frame._document_controller.get_dual_view_results("alpha"), ("segment",))
-        frame._refresh_dual_view.assert_called_once_with()
-
-    def test_export_conversion_does_not_replace_dual_view_cache(self) -> None:
-        frame = self._make_frame()
-        policy = gui.ConversionCompletionPolicy(update_output=False)
-        frame._document_controller.set_dual_view_results("alpha", ("manual",))
-        conversion_output = gui.ConversionOutput("export", ("export-segment",))
-
-        frame._finish_conversion_success(
-            gui.ConversionJobSuccess(
-                job_id=1,
-                conversion_output=conversion_output,
-                completion_policy=policy,
-            )
-        )
-
-        self.assertEqual(frame._document_controller.get_dual_view_results("alpha"), ("manual",))
-
     def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
         frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._dual_view_frame = Mock()
@@ -1287,88 +1123,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         self.assertEqual(get_lang.call_count, 2)
         self.assertEqual(get_charset_maps.call_count, 2)
 
-    def test_convert_without_default_table_shows_info_and_does_not_convert(self) -> None:
-        frame = self._make_frame()
-        frame.translation_tables = {"default": ""}
-        frame._start_conversion = Mock()
-
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame.on_convert(None)
-
-        message_box.assert_called_once_with(
-            gui._("Please select a translation table first."),
-            gui._("Info"),
-            gui.wx.OK | gui.wx.ICON_INFORMATION,
-            parent=frame,
-        )
-        frame._start_conversion.assert_not_called()
-
-    def test_convert_with_default_table_starts_conversion_without_message(self) -> None:
-        frame = self._make_frame()
-        frame.translation_tables = {"default": "zh-tw.ctb"}
-        frame.translation_settings = TranslationSettings("ascii", 32, "default")
-        frame.input_txt.GetValue.return_value = "source"
-        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
-        frame._start_conversion = Mock()
-
-        with patch.object(gui.wx, "MessageBox") as message_box:
-            frame.on_convert(None)
-
-        frame._start_conversion.assert_called_once_with(
-            "source",
-            32,
-            "ascii",
-            Path("dictionary/default.csv"),
-        )
-        message_box.assert_not_called()
-
-    def test_export_conversion_with_default_table_starts_background_conversion(self) -> None:
-        frame = self._make_frame()
-        frame.translation_tables = {"default": "zh-tw.ctb"}
-        frame.translation_settings = TranslationSettings("ascii", 32, "default")
-        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
-        frame._start_conversion = Mock()
-        on_success = Mock()
-        on_error = Mock()
-        on_missing_table = Mock()
-
-        started = frame._start_export_conversion(
-            Document("alpha", "text", None),
-            Path("/tmp/export/alpha.brl"),
-            "brl",
-            on_success=on_success,
-            on_error=on_error,
-            on_missing_table=on_missing_table,
-        )
-
-        self.assertTrue(started)
-        frame._start_conversion.assert_called_once_with(
-            "text",
-            32,
-            "ascii",
-            Path("dictionary/default.csv"),
-            on_success=on_success,
-            on_error=on_error,
-            update_output=False,
-            show_success=False,
-        )
-        on_missing_table.assert_not_called()
-        on_error.assert_not_called()
-
-    def test_missing_default_table_message_reports_only_unset_default(self) -> None:
-        frame = self._make_frame()
-        frame.translation_tables = {"default": "zh-tw.ctb"}
-
-        self.assertIsNone(frame._missing_default_table_message())
-
-        for tables in ({}, {"default": ""}, {"default": None}):
-            with self.subTest(tables=tables):
-                frame.translation_tables = tables
-                self.assertEqual(
-                    frame._missing_default_table_message(),
-                    gui._("Please select a translation table first."),
-                )
-
     def test_translation_tables_are_not_module_state(self) -> None:
         self.assertFalse(hasattr(gui, "language_map_translate_table"))
 
@@ -2104,9 +1858,9 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
         frame.SetTitle = lambda title: self.events.append(("title", title))
         frame._dual_view_frame = None
         frame._document_menu_items = {}
-        frame._conversion_runner = Mock()
-        frame._conversion_runner.is_running.return_value = False
-        frame._close_converting_dialog = Mock()
+        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
+        frame._conversion_presenter.is_running.return_value = False
+        frame.close_converting_dialog = Mock()
         return frame
 
     def _write_packages(self, *documents: Document) -> None:
@@ -2333,7 +2087,7 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
 
         event.Veto.assert_called_once_with()
         event.Skip.assert_not_called()
-        frame._close_converting_dialog.assert_not_called()
+        frame.close_converting_dialog.assert_not_called()
 
     # --- rename ------------------------------------------------------------
 
@@ -2955,16 +2709,18 @@ class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
 
     def _wire_conversion(self, frame) -> None:
         """Today's conversion wiring with the fakes. The only helper that changes during P1-4."""
-        frame._conversion_runner = gui.ConversionJobRunner(
+        frame._convert_dialog = None
+        frame._conversion_presenter = gui.ConversionPresenter(
+            frame,
+            frame._document_controller,
             runtime=frame.translation_runtime,
-            on_success=frame._finish_conversion_success,
-            on_failure=frame._finish_conversion_failure,
+            build_request=frame._build_conversion_request_for_text,
+            get_translation_tables=lambda: frame.translation_tables,
             call_after=self.calls,
-            converter=self._convert,
+            call_later=self.timers,
             thread_factory=self.thread_factory,
+            converter=self._convert,
         )
-        frame._convert_dialog = None
-        frame._convert_dialog_timer = None
 
     def _make_frame(self, documents, open_name=None, selected_name=None) -> gui.BrailleFrame:
         frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
PATCH
```

- [ ] **Step 4: Run the touched modules, the characterization comparison, the suite check and the msgid scan.**

```bash
$PY -m unittest tests.test_gui_document_flows tests.test_conversion_presenter tests.test_conversion_jobs 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $T/tools/char_unchanged.py $REPO $(git -C $REPO log --format=%h --grep='^test: characterize conversion and export flows$' -1)
$T/tools/check_suite.sh 737 53 12
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo grep; grep -nE "_start_conversion|_complete_conversion|_finish_conversion_|_missing_default_table_message|_conversion_runner|_convert_dialog_timer|_set_conversion_busy|_show_converting_dialog|_close_converting_dialog|conversion\.jobs|\bConversionOutput\b|get_public_error_message" gui.py
echo end
```

Expected (the 19 characterization tests unchanged, only their wiring helper differs; nothing between `grep` and `end`):

```text
Ran 174 tests
OK (skipped=2)
characterization tests: 19 at Task 1, 19 now
changed members: ['ConversionExportFlowsCharacterizationTest._wire_conversion']
Ran 737 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 12 (expected 12)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (737)
new tests ok: 53 (expected 53)
new tests not ok: 0
source msgids: 353
SOURCE == SAVED
grep
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: route conversion through the presenter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: route conversion through the presenter
```

---

### Task 5: Keep completion state out of conversion jobs (I-3, spec step 5)

**Files:**
- Modify: `client/tests/test_conversion_jobs.py` (tabs)
- Modify: `client/conversion/jobs.py` (tabs), `client/conversion/presenter.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `ConversionJobSuccess(job_id, conversion_output)` and `ConversionJobFailure(job_id, error)` (frozen, no policy field); `ConversionJobRunner.start(request: ConversionRequest) -> int`; `_run_job(job_id, request)` calls `converter(request, runtime=...)`. `ConversionCompletionPolicy` and `ConversionJobRequest` are deleted; the presenter calls `runner.start(request)`. Everything else in the runner is unchanged (ids, daemon threads, stale filtering, `_thread = None` before the callback, escaping non-stage exceptions).

- [ ] **Step 1: Update the runner tests.** `make_request()` returns a plain `ConversionRequest`; the four original tests lose their policy arguments and keep their assertions; new `test_results_carry_only_the_job_id_and_the_outcome`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_jobs.py b/client/tests/test_conversion_jobs.py
index 1aa722a..dedc5fe 100644
--- a/client/tests/test_conversion_jobs.py
+++ b/client/tests/test_conversion_jobs.py
@@ -1,10 +1,9 @@
+from dataclasses import fields
 from pathlib import Path
 import unittest
 
 from conversion.jobs import (
-	ConversionCompletionPolicy,
 	ConversionJobFailure,
-	ConversionJobRequest,
 	ConversionJobRunner,
 	ConversionJobSuccess,
 )
@@ -14,19 +13,16 @@ from tests.conversion_harness import FakeThread, make_thread_factory
 
 
 class ConversionJobRunnerTest(unittest.TestCase):
-	def make_request(self, *, completion_policy=None) -> ConversionJobRequest:
-		return ConversionJobRequest(
-			conversion_request=ConversionRequest(
-				raw_text="source",
-				output_mode="unicode",
-				width=40,
-				dictionary_path=Path("dictionary/default.csv"),
-				data_dir=Path("data"),
-				translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
-				lang="zh_TW",
-				charset_maps=dict(DEFAULT_CHARSET_MAPS),
-			),
-			completion_policy=ConversionCompletionPolicy() if completion_policy is None else completion_policy,
+	def make_request(self) -> ConversionRequest:
+		return ConversionRequest(
+			raw_text="source",
+			output_mode="unicode",
+			width=40,
+			dictionary_path=Path("dictionary/default.csv"),
+			data_dir=Path("data"),
+			translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
+			lang="zh_TW",
+			charset_maps=dict(DEFAULT_CHARSET_MAPS),
 		)
 
 	def make_runner(self, *, converter):
@@ -51,29 +47,23 @@ class ConversionJobRunnerTest(unittest.TestCase):
 
 	def test_start_runs_conversion_and_reports_success(self) -> None:
 		output = ConversionOutput("braille", ("segment",))
-		policy = ConversionCompletionPolicy()
 
 		def converter(request, *, runtime):
-			self.assertEqual(request, self.make_request().conversion_request)
+			self.assertEqual(request, self.make_request())
 			self.assertIsNotNone(runtime)
 			return output
 
 		runner, successes, failures, threads = self.make_runner(converter=converter)
 
-		request = self.make_request(completion_policy=policy)
-		job_id = runner.start(request)
+		job_id = runner.start(self.make_request())
 		threads[0].run()
 
 		self.assertEqual(job_id, 1)
-		self.assertEqual(
-			successes,
-			[ConversionJobSuccess(job_id=1, conversion_output=output, completion_policy=policy)],
-		)
+		self.assertEqual(successes, [ConversionJobSuccess(job_id=1, conversion_output=output)])
 		self.assertEqual(failures, [])
 
 	def test_reports_conversion_stage_error_failure(self) -> None:
 		error = ConversionStageError("translation", RuntimeError("boom"))
-		policy = ConversionCompletionPolicy()
 
 		def converter(_request, *, runtime):
 			self.assertIsNotNone(runtime)
@@ -81,23 +71,17 @@ class ConversionJobRunnerTest(unittest.TestCase):
 
 		runner, successes, failures, threads = self.make_runner(converter=converter)
 
-		request = self.make_request(completion_policy=policy)
-		job_id = runner.start(request)
+		job_id = runner.start(self.make_request())
 		threads[0].run()
 
 		self.assertEqual(successes, [])
-		self.assertEqual(
-			failures,
-			[ConversionJobFailure(job_id=job_id, error=error, completion_policy=policy)],
-		)
+		self.assertEqual(failures, [ConversionJobFailure(job_id=job_id, error=error)])
 
 	def test_stale_job_completion_is_ignored(self) -> None:
 		outputs = [
 			ConversionOutput("first", ("old",)),
 			ConversionOutput("second", ("new",)),
 		]
-		first_policy = ConversionCompletionPolicy()
-		second_policy = ConversionCompletionPolicy()
 
 		def converter(_request, *, runtime):
 			self.assertIsNotNone(runtime)
@@ -105,8 +89,8 @@ class ConversionJobRunnerTest(unittest.TestCase):
 
 		runner, successes, failures, threads = self.make_runner(converter=converter)
 
-		first_job_id = runner.start(self.make_request(completion_policy=first_policy))
-		second_job_id = runner.start(self.make_request(completion_policy=second_policy))
+		first_job_id = runner.start(self.make_request())
+		second_job_id = runner.start(self.make_request())
 		threads[0].run()
 		threads[1].run()
 
@@ -118,7 +102,6 @@ class ConversionJobRunnerTest(unittest.TestCase):
 				ConversionJobSuccess(
 					job_id=2,
 					conversion_output=ConversionOutput("second", ("new",)),
-					completion_policy=second_policy,
 				)
 			],
 		)
@@ -126,8 +109,6 @@ class ConversionJobRunnerTest(unittest.TestCase):
 
 	def test_stale_failure_completion_is_ignored(self) -> None:
 		error = ConversionStageError("translation", RuntimeError("boom"))
-		first_policy = ConversionCompletionPolicy()
-		second_policy = ConversionCompletionPolicy()
 
 		def converter(_request, *, runtime):
 			self.assertIsNotNone(runtime)
@@ -135,16 +116,13 @@ class ConversionJobRunnerTest(unittest.TestCase):
 
 		runner, successes, failures, threads = self.make_runner(converter=converter)
 
-		runner.start(self.make_request(completion_policy=first_policy))
-		second_job_id = runner.start(self.make_request(completion_policy=second_policy))
+		runner.start(self.make_request())
+		second_job_id = runner.start(self.make_request())
 		threads[0].run()
 		threads[1].run()
 
 		self.assertEqual(successes, [])
-		self.assertEqual(
-			failures,
-			[ConversionJobFailure(job_id=second_job_id, error=error, completion_policy=second_policy)],
-		)
+		self.assertEqual(failures, [ConversionJobFailure(job_id=second_job_id, error=error)])
 
 	def test_each_start_creates_and_starts_one_daemon_thread(self) -> None:
 		runner, _successes, _failures, threads = self.make_runner(
@@ -218,5 +196,9 @@ class ConversionJobRunnerTest(unittest.TestCase):
 		self.assertEqual(runner.active_job_id, 1)
 
 
+	def test_results_carry_only_the_job_id_and_the_outcome(self) -> None:
+		self.assertEqual([field.name for field in fields(ConversionJobSuccess)], ["job_id", "conversion_output"])
+		self.assertEqual([field.name for field in fields(ConversionJobFailure)], ["job_id", "error"])
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_conversion_jobs 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected (today's runner unwraps `request.conversion_request` in the worker; the result dataclasses still carry the policy):

```text
      1 AssertionError: Lists differ: ['job_id', 'conversion_output', 'completion_policy'] != ['job_id', 'conversion_output']
      7 AttributeError: 'ConversionRequest' object has no attribute 'conversion_request'
      1 ERROR: test_exception_outside_conversion_stage_error_delivers_nothing
      1 ERROR: test_is_running_is_false_inside_completion_callbacks
      1 ERROR: test_reports_conversion_stage_error_failure
      1 ERROR: test_stale_delivery_keeps_the_current_job_running
      1 ERROR: test_stale_failure_completion_is_ignored
      1 ERROR: test_stale_job_completion_is_ignored
      1 ERROR: test_start_runs_conversion_and_reports_success
      1 FAIL: test_results_carry_only_the_job_id_and_the_outcome
      1 FAILED (failures=1, errors=7)
      1 Ran 9 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/jobs.py b/client/conversion/jobs.py
index bd3f31b..d425344 100644
--- a/client/conversion/jobs.py
+++ b/client/conversion/jobs.py
@@ -1,4 +1,4 @@
-from dataclasses import dataclass, field
+from dataclasses import dataclass
 import threading
 from typing import Callable
 
@@ -11,32 +11,16 @@ from conversion.service import (
 )
 
 
-@dataclass(frozen=True)
-class ConversionCompletionPolicy:
-	on_success: Callable[[str], object] | None = None
-	on_error: Callable[[str], object] | None = None
-	update_output: bool = True
-	show_success: bool = True
-
-
-@dataclass(frozen=True)
-class ConversionJobRequest:
-	conversion_request: ConversionRequest
-	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)
-
-
 @dataclass(frozen=True)
 class ConversionJobSuccess:
 	job_id: int
 	conversion_output: ConversionOutput
-	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)
 
 
 @dataclass(frozen=True)
 class ConversionJobFailure:
 	job_id: int
 	error: ConversionStageError
-	completion_policy: ConversionCompletionPolicy = field(default_factory=ConversionCompletionPolicy)
 
 
 ThreadFactory = Callable[..., threading.Thread]
@@ -70,7 +54,7 @@ class ConversionJobRunner:
 	def is_running(self) -> bool:
 		return self._thread is not None and self._thread.is_alive()
 
-	def start(self, request: ConversionJobRequest) -> int:
+	def start(self, request: ConversionRequest) -> int:
 		self._job_id += 1
 		job_id = self._job_id
 		self._thread = self._thread_factory(
@@ -81,29 +65,21 @@ class ConversionJobRunner:
 		self._thread.start()
 		return job_id
 
-	def _run_job(self, job_id: int, request: ConversionJobRequest) -> None:
+	def _run_job(self, job_id: int, request: ConversionRequest) -> None:
 		try:
 			conversion_output = self._converter(
-				request.conversion_request,
+				request,
 				runtime=self._runtime,
 			)
 		except ConversionStageError as error:
 			self._call_after(
 				self._deliver_failure,
-				ConversionJobFailure(
-					job_id=job_id,
-					error=error,
-					completion_policy=request.completion_policy,
-				),
+				ConversionJobFailure(job_id=job_id, error=error),
 			)
 			return
 		self._call_after(
 			self._deliver_success,
-			ConversionJobSuccess(
-				job_id=job_id,
-				conversion_output=conversion_output,
-				completion_policy=request.completion_policy,
-			),
+			ConversionJobSuccess(job_id=job_id, conversion_output=conversion_output),
 		)
 
 	def _deliver_success(self, result: ConversionJobSuccess) -> None:
diff --git a/client/conversion/presenter.py b/client/conversion/presenter.py
index 4a3399c..df27fa7 100644
--- a/client/conversion/presenter.py
+++ b/client/conversion/presenter.py
@@ -17,7 +17,6 @@ from typing import Protocol
 from adapters.translation.contracts import TranslationRuntime
 from conversion.jobs import (
     ConversionJobFailure,
-    ConversionJobRequest,
     ConversionJobRunner,
     ConversionJobSuccess,
     ThreadFactory,
@@ -149,7 +148,7 @@ class ConversionPresenter:
         self._view.set_conversion_busy(True)
         self._view.close_converting_dialog()
         request = self._build_request(raw_text)
-        job_id = self._runner.start(ConversionJobRequest(conversion_request=request))
+        job_id = self._runner.start(request)
         self._active = _ActiveJob(job_id, export)
         self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)
 
PATCH
```

- [ ] **Step 4: Run the tests, acceptance criterion 1 and the suite check.**

```bash
$PY -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo AC1; grep -rn "ConversionCompletionPolicy\|ConversionJobRequest" $REPO/client
echo end
$T/tools/check_suite.sh 738 54 12
```

Expected (nothing between `AC1` and `end`):

```text
Ran 175 tests
OK (skipped=2)
AC1
end
Ran 738 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 12 (expected 12)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (738)
new tests ok: 54 (expected 54)
new tests not ok: 0
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/jobs.py client/conversion/presenter.py client/tests/test_conversion_jobs.py
git -C $REPO commit -q -F - <<'MSG'
refactor: keep completion state out of conversion jobs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: keep completion state out of conversion jobs
```

---

### Task 6: The wx-free export coordinator (spec step 6)

**Files:**
- Create: `client/tests/test_export_coordinator.py` (21 tests, no wx, no stub scope)
- Create: `client/documents/export_coordinator.py`

**Interfaces:**
- Consumes: `DocumentController` (`documents_snapshot`, `get_dual_view_results`); `documents.formats` (`DocumentFormatDescriptor`, `ExportContext`, `get_format`, the registry writers); `ExportBatchResult`; `Document`; `i18n._`; Task 3's `ConversionPresenter` (satisfies `ExportConversions`; used by the integration test only).
- Produces: `ExportView` (protocol: `choose_export_path(default_file, descriptor) -> Path | None`, `choose_export_directory() -> Path | None`, `confirm_overwrite_all(conflicts) -> bool`, `show_info`, `show_warning`, `show_error`); `ExportConversions` (protocol: `missing_table_message()`, `convert_for_export(raw_text, *, on_success, on_error)`); `ExportCoordinator(view, documents, conversions, *, call_after)` with `write_document(destination_path, document, format_key)` (registry writer, `ExportContext` with the written document's cache, `ValueError` for a non-exportable format), `export_document(document, format_key)` (the body of `_export_document_with_dialog` and `_continue_single_export`) and `export_all(format_key)` (folder, snapshot, conflict question only when needed, first step in the caller's turn, each later step through `call_after`, one summary: `show_info` if all succeeded, else `show_warning`). The tests import the module as `documents.export_coordinator` to patch `get_format` (P0 review I-1 style).

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_export_coordinator.py b/client/tests/test_export_coordinator.py
new file mode 100644
index 0000000..f67dc21
--- /dev/null
+++ b/client/tests/test_export_coordinator.py
@@ -0,0 +1,517 @@
+from __future__ import annotations
+
+import ast
+import tempfile
+import unittest
+from dataclasses import replace
+from pathlib import Path
+from unittest.mock import Mock, call, patch
+
+import documents.export_coordinator as coordinator_module
+from conversion.presenter import ConversionPresenter
+from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
+from documents.controller import DocumentController
+from documents.export_coordinator import ExportCoordinator
+from documents.formats import ExportContext, get_format
+from documents.workspace import Document
+from i18n import _
+from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
+
+COORDINATOR_PATH = Path(__file__).resolve().parents[1] / "documents" / "export_coordinator.py"
+MISSING_TABLE = "missing table"
+
+
+class RecordingExportView:
+    """Implements ``ExportView`` (and ``ConversionView`` for the integration test)."""
+
+    def __init__(self, events: list):
+        self.events = events
+        self.paths: list = []
+        self.directories: list = []
+        self.overwrite_answers: list = []
+
+    def choose_export_path(self, default_file, descriptor):
+        self.events.append(("choose_export_path", default_file, descriptor.key))
+        return self.paths.pop(0)
+
+    def choose_export_directory(self):
+        self.events.append(("choose_export_directory",))
+        return self.directories.pop(0)
+
+    def confirm_overwrite_all(self, conflicts):
+        self.events.append(("confirm_overwrite_all", [path.name for path in conflicts]))
+        return self.overwrite_answers.pop(0)
+
+    def show_info(self, message, caption):
+        self.events.append(("show_info", message, caption))
+
+    def show_warning(self, message, caption):
+        self.events.append(("show_warning", message, caption))
+
+    def show_error(self, message, caption):
+        self.events.append(("show_error", message, caption))
+
+    # ConversionView, used only with a real ConversionPresenter
+    def get_source_text(self):
+        return ""
+
+    def set_conversion_busy(self, busy):
+        self.events.append(("busy", busy))
+
+    def show_converting_dialog(self):
+        self.events.append(("show_converting_dialog",))
+
+    def close_converting_dialog(self):
+        self.events.append(("close_converting_dialog",))
+
+    def show_conversion_output(self, text):
+        self.events.append(("show_conversion_output", text))
+
+    def refresh_dual_view(self):
+        self.events.append(("refresh_dual_view",))
+
+
+class FakeExportConversions:
+    """Implements ``ExportConversions``; the test calls the stored callbacks."""
+
+    def __init__(self, events: list):
+        self.events = events
+        self.missing_message: str | None = None
+        self.started: list = []
+
+    def missing_table_message(self):
+        self.events.append(("missing_table_message",))
+        return self.missing_message
+
+    def convert_for_export(self, raw_text, *, on_success, on_error):
+        self.events.append(("convert_for_export", raw_text))
+        self.started.append((on_success, on_error))
+
+
+class ExportCoordinatorTest(unittest.TestCase):
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name)
+        self.events: list = []
+        self.view = RecordingExportView(self.events)
+        self.conversions = FakeExportConversions(self.events)
+        self.calls = DeferredCalls(self.events)
+        self.documents = DocumentController(documents=[Document("alpha", "a", "⠁"), Document("beta", "b", None)])
+        self.coordinator = ExportCoordinator(self.view, self.documents, self.conversions, call_after=self.calls)
+
+    def _take(self) -> list:
+        taken = list(self.events)
+        self.events.clear()
+        return taken
+
+    def _written(self) -> dict:
+        return {path.name: path.read_text(encoding="utf-8") for path in sorted(self.root.glob("*.brl")) if path.is_file()}
+
+    def _exported(self) -> tuple:
+        return ("show_info", _("The document was exported successfully."), _("Export Complete"))
+
+    def _all_exported(self) -> tuple:
+        # KNOWN BUG (P1-4 spec, defect 4): the message is not a msgid; only the caption is translated.
+        return ("show_info", "All documents were exported successfully.", _("Export Complete"))
+
+    def _os_error_text(self, path: Path) -> str:
+        try:
+            path.write_text("", encoding="utf-8")
+        except OSError as exc:
+            return str(exc)
+        self.fail(f"{path} is writable")
+
+    def test_module_imports_neither_wx_nor_gui(self) -> None:
+        tree = ast.parse(COORDINATOR_PATH.read_text(encoding="utf-8"))
+        imported = set()
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Import):
+                imported.update(alias.name.split(".")[0] for alias in node.names)
+            elif isinstance(node, ast.ImportFrom):
+                imported.add((node.module or "").split(".")[0])
+
+        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)
+
+    # --- write_document --------------------------------------------------------
+
+    def test_write_document_uses_registry_writer(self) -> None:
+        document = Document("alpha", "text", "braille")
+        writer = Mock()
+        descriptor = replace(get_format("dep"), writer=writer)
+
+        with patch.object(coordinator_module, "get_format", return_value=descriptor) as get_format_mock:
+            self.coordinator.write_document(Path("/tmp/custom.dep"), document, "dep")
+
+        get_format_mock.assert_called_once_with("dep")
+        writer.assert_called_once_with(Path("/tmp/custom.dep"), document, ExportContext())
+
+    def test_write_document_passes_cached_results_to_every_writer(self) -> None:
+        document = Document("alpha", "text", "braille")
+        cached_results = (Mock(),)
+        self.documents.set_dual_view_results("alpha", cached_results)
+        for key in ("dep", "brl", "html"):
+            with self.subTest(format_key=key):
+                writer = Mock()
+                descriptor = replace(get_format(key), writer=writer)
+                with patch.object(coordinator_module, "get_format", return_value=descriptor):
+                    self.coordinator.write_document(Path(f"/tmp/custom.{key}"), document, key)
+
+                writer.assert_called_once_with(
+                    Path(f"/tmp/custom.{key}"),
+                    document,
+                    ExportContext(dual_view_results=cached_results),
+                )
+
+    def test_write_document_reads_the_cache_of_the_written_document(self) -> None:
+        self.documents.set_dual_view_results("alpha", ("alpha-cache",))
+        writer = Mock()
+        descriptor = replace(get_format("html"), writer=writer)
+
+        with patch.object(coordinator_module, "get_format", return_value=descriptor):
+            self.coordinator.write_document(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), "html")
+
+        writer.assert_called_once_with(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), ExportContext())
+
+    def test_write_document_rejects_non_exportable_format(self) -> None:
+        descriptor = replace(get_format("txt"), writer=Mock())
+
+        with patch.object(coordinator_module, "get_format", return_value=descriptor):
+            with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
+                self.coordinator.write_document(Path("/tmp/custom.txt"), Document("alpha", "t", "b"), "txt")
+
+        descriptor.writer.assert_not_called()
+
+    # --- export_document ---------------------------------------------------------
+
+    def test_export_document_passes_default_file_and_descriptor_and_stops_on_cancel(self) -> None:
+        self.view.paths.append(None)
+
+        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")
+
+        self.assertEqual(self._take(), [("choose_export_path", "alpha.brl", "brl")])
+        self.assertEqual(self._written(), {})
+
+    def test_export_document_with_braille_writes_and_reports(self) -> None:
+        self.view.paths.append(self.root / "alpha.brl")
+
+        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")
+
+        self.assertEqual(self._take(), [("choose_export_path", "alpha.brl", "brl"), self._exported()])
+        self.assertEqual(self._written(), {"alpha.brl": "⠁"})
+
+    def test_export_document_corrects_only_a_wrong_extension(self) -> None:
+        for chosen, written in (("out.TXT", "out.brl"), ("out.BRL", "out.BRL")):
+            with self.subTest(chosen=chosen):
+                self.coordinator.write_document = Mock()
+                self.view.paths.append(self.root / chosen)
+
+                self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")
+
+                self.coordinator.write_document.assert_called_once_with(
+                    self.root / written, Document("alpha", "a", "⠁"), "brl"
+                )
+
+    def test_export_document_write_error_shows_one_error(self) -> None:
+        blocked = self.root / "blocked.brl"
+        blocked.mkdir()
+        reason = self._os_error_text(blocked)
+        self.view.paths.append(blocked)
+
+        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("choose_export_path", "alpha.brl", "brl"),
+                ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
+            ],
+        )
+
+    def test_export_document_pending_converts_document_text_then_writes(self) -> None:
+        self.view.paths.append(self.root / "beta.brl")
+
+        self.coordinator.export_document(Document("beta", "b", None), "brl")
+
+        self.assertEqual(
+            self._take(),
+            [("choose_export_path", "beta.brl", "brl"), ("missing_table_message",), ("convert_for_export", "b")],
+        )
+        self.assertEqual(self._written(), {})
+
+        on_success, _on_error = self.conversions.started[0]
+        on_success("⠃⠃")
+
+        self.assertEqual(self._take(), [self._exported()])
+        self.assertEqual(self._written(), {"beta.brl": "⠃⠃"})
+        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))
+
+    def test_export_document_pending_conversion_error_shows_it(self) -> None:
+        self.view.paths.append(self.root / "beta.brl")
+        self.coordinator.export_document(Document("beta", "b", None), "brl")
+        self._take()
+
+        _on_success, on_error = self.conversions.started[0]
+        on_error("boom")
+
+        self.assertEqual(self._take(), [("show_error", "boom", _("Error"))])
+        self.assertEqual(self._written(), {})
+
+    def test_export_document_pending_without_table_shows_error_only(self) -> None:
+        self.conversions.missing_message = MISSING_TABLE
+        self.view.paths.append(self.root / "beta.brl")
+
+        self.coordinator.export_document(Document("beta", "b", None), "brl")
+
+        self.assertEqual(
+            self._take(),
+            [
+                ("choose_export_path", "beta.brl", "brl"),
+                ("missing_table_message",),
+                ("show_error", MISSING_TABLE, _("Error")),
+            ],
+        )
+        self.assertEqual(self.conversions.started, [])
+
+    # --- export_all ----------------------------------------------------------------
+
+    def test_export_all_folder_cancel_does_nothing(self) -> None:
+        self.view.directories.append(None)
+
+        self.coordinator.export_all("brl")
+
+        self.assertEqual(self._take(), [("choose_export_directory",)])
+        self.assertEqual(self.calls.pending, [])
+
+    def test_export_all_takes_the_snapshot_after_the_folder_dialog(self) -> None:
+        self.documents.documents = [Document("alpha", "a", "⠁")]
+
+        def choose_export_directory():
+            self.events.append(("choose_export_directory",))
+            self.documents.add_document(Document("gamma", "g", "⠛"))
+            return self.root
+
+        self.view.choose_export_directory = choose_export_directory
+
+        self.coordinator.export_all("brl")
+        self.calls.run_all()
+
+        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
+
+    def test_export_all_asks_about_conflicts_only_when_needed(self) -> None:
+        self.documents.documents = [Document("alpha", "a", "⠁"), Document("gamma", "g", "⠛")]
+        self.view.directories.extend([self.root, self.root, self.root])
+        self.view.overwrite_answers.extend([False, True])
+
+        self.coordinator.export_all("brl")
+        self.calls.run_all()
+        self.assertEqual(
+            self._take(),
+            [("choose_export_directory",), ("call_after",), ("call_after",), self._all_exported()],
+        )
+        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
+
+        (self.root / "alpha.brl").write_text("old", encoding="utf-8")
+        (self.root / "gamma.brl").unlink()
+        self.coordinator.export_all("brl")
+        self.assertEqual(self._take(), [("choose_export_directory",), ("confirm_overwrite_all", ["alpha.brl"])])
+        self.assertEqual(self._written(), {"alpha.brl": "old"})
+
+        self.coordinator.export_all("brl")
+        self.calls.run_all()
+        self.assertEqual(
+            self._take(),
+            [
+                ("choose_export_directory",),
+                ("confirm_overwrite_all", ["alpha.brl"]),
+                ("call_after",),
+                ("call_after",),
+                self._all_exported(),
+            ],
+        )
+        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
+
+    def test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn(self) -> None:
+        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", None), Document("gamma", "g", "⠛")]
+        self.view.directories.append(self.root)
+
+        self.coordinator.export_all("brl")
+        self.assertEqual(self._take(), [("choose_export_directory",), ("call_after",)])
+        self.assertEqual(self._written(), {"alpha.brl": "⠁"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("missing_table_message",), ("convert_for_export", "b")])
+        self.assertEqual(self.calls.pending, [])
+
+        on_success, _on_error = self.conversions.started[0]
+        on_success("⠃")
+        self.assertEqual(self._take(), [("call_after",)])
+        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("call_after",)])
+        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃", "gamma.brl": "⠛"})
+
+        self.calls.run_next()
+        self.assertEqual(self._take(), [self._all_exported()])
+        self.assertEqual(self.calls.pending, [])
+
+    def test_export_all_reads_the_format_for_conflicts_each_step_and_each_write(self) -> None:
+        self.documents.documents = [Document("alpha", "a", "⠁")]
+        self.view.directories.append(self.root)
+        descriptor = replace(get_format("brl"), extension=".braille")
+
+        with patch.object(coordinator_module, "get_format", return_value=descriptor) as get_format_mock:
+            self.coordinator.export_all("brl")
+            self.calls.run_all()
+
+        self.assertEqual(get_format_mock.call_args_list, [call("brl"), call("brl"), call("brl")])
+        self.assertEqual((self.root / "alpha.braille").read_text(encoding="utf-8"), "⠁")
+
+    def test_export_all_partial_failure_summary_lists_each_failure(self) -> None:
+        blocked = self.root / "write-fail.brl"
+        blocked.mkdir()
+        reason = self._os_error_text(blocked)
+        self.documents.documents = [
+            Document("alpha", "a", "⠁"),
+            Document("convert-fail", "c", None),
+            Document("write-fail", "w", "⠺"),
+        ]
+        self.view.directories.append(self.root)
+        self.view.overwrite_answers.append(True)
+
+        self.coordinator.export_all("brl")
+        self.calls.run_next()
+        _on_success, on_error = self.conversions.started[0]
+        on_error("Translation failed")
+        self.calls.run_all()
+
+        # KNOWN BUG (P1-4 spec, defect 4): the partial-export summary is not translated.
+        self.assertEqual(
+            self._take()[-1],
+            (
+                "show_warning",
+                f"Exported documents: 1\nFailed documents: 2\n\nconvert-fail: Translation failed\nwrite-fail: {reason}",
+                "Export Complete with Errors",
+            ),
+        )
+        self.assertEqual(self._written(), {"alpha.brl": "⠁"})
+
+    def test_export_all_missing_table_accumulates_failures_without_per_file_messages(self) -> None:
+        self.conversions.missing_message = MISSING_TABLE
+        self.documents.documents = [Document("alpha", "a", None), Document("beta", "b", None)]
+        self.view.directories.append(self.root)
+
+        self.coordinator.export_all("brl")
+        self.assertEqual(
+            self._take(),
+            [("choose_export_directory",), ("missing_table_message",), ("call_after",)],
+        )
+        self.calls.run_next()
+        self.assertEqual(self._take(), [("missing_table_message",), ("call_after",)])
+        self.calls.run_next()
+
+        self.assertEqual(
+            self._take(),
+            [
+                (
+                    "show_warning",
+                    f"Exported documents: 0\nFailed documents: 2\n\nalpha: {MISSING_TABLE}\nbeta: {MISSING_TABLE}",
+                    "Export Complete with Errors",
+                )
+            ],
+        )
+        self.assertEqual(self.conversions.started, [])
+
+    def test_export_all_writer_value_error_stops_the_chain(self) -> None:
+        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")]
+        self.view.directories.append(self.root)
+
+        # KNOWN BUG (P1-4 spec, defect 7): the error escapes and no summary is shown.
+        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
+            self.coordinator.export_all("txt")
+
+        self.assertEqual(self._take(), [("choose_export_directory",)])
+        self.assertEqual(self.calls.pending, [])
+
+
+class ExportThroughConversionPresenterTest(unittest.TestCase):
+    def test_export_all_with_a_real_presenter_turn_by_turn(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        root = Path(temp_dir.name)
+        events: list = []
+        view = RecordingExportView(events)
+        view.directories.append(root)
+        documents = DocumentController(
+            documents=[Document("ready", "r", "⠗"), Document("pending", "p", None), Document("broken", "x", None)],
+        )
+        documents.set_dual_view_results("pending", ("cached",))
+        outcomes = {
+            "p": ConversionOutput("⠏", ("result",), ("fresh",)),
+            "x": ConversionStageError("translation", RuntimeError("bad")),
+        }
+
+        def converter(request, *, runtime):
+            events.append(("convert", request.raw_text))
+            outcome = outcomes[request.raw_text]
+            if isinstance(outcome, Exception):
+                raise outcome
+            return outcome
+
+        calls = DeferredCalls(events)
+        timers = FakeTimers(events)
+        thread_factory = make_thread_factory()
+        presenter = ConversionPresenter(
+            view,
+            documents,
+            runtime=object(),
+            build_request=lambda raw_text: ConversionRequest(
+                raw_text, "unicode", 40, Path("d.csv"), Path("data"), {"default": "t"}, "zh_TW", {}
+            ),
+            get_translation_tables=lambda: {"default": "t"},
+            call_after=calls,
+            call_later=timers,
+            thread_factory=thread_factory,
+            converter=converter,
+        )
+        coordinator = ExportCoordinator(view, documents, presenter, call_after=calls)
+
+        coordinator.export_all("brl")
+        calls.run_next()
+        thread_factory.threads[0].run()
+        calls.run_next()
+        calls.run_next()
+        thread_factory.threads[1].run()
+        calls.run_next()
+        calls.run_next()
+
+        busy_on = [("busy", True), ("close_converting_dialog",)]
+        busy_off = [("close_converting_dialog",), ("busy", False)]
+        self.assertEqual(
+            events,
+            [("choose_export_directory",), ("call_after",)]
+            + busy_on
+            + [("call_later", 2000, (1,)), ("convert", "p"), ("call_after",), ("timer.Stop", 1)]
+            + busy_off
+            + [("call_after",)]
+            + busy_on
+            + [("call_later", 2000, (2,)), ("convert", "x"), ("call_after",), ("timer.Stop", 2)]
+            + busy_off
+            + [
+                ("call_after",),
+                (
+                    "show_warning",
+                    "Exported documents: 2\nFailed documents: 1\n\nbroken: "
+                    + _("Translation failed: {error}").format(error="bad"),
+                    "Export Complete with Errors",
+                ),
+            ],
+        )
+        self.assertEqual((root / "pending.brl").read_text(encoding="utf-8"), "⠏")
+        self.assertEqual(documents.dual_view_results_by_document, {"pending": ("cached",)})
+        self.assertEqual(calls.pending, [])
+
+
+if __name__ == "__main__":
+    unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_export_coordinator 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ in [0-9.]+s$//; s/0x[0-9a-f]+/0x?/g" | LC_ALL=C sort | uniq -c
```

Expected (the module does not exist yet):

```text
      1 ERROR: test_export_coordinator (unittest.loader._FailedTest.test_export_coordinator)
      1 FAILED (errors=1)
      1 ImportError: Failed to import test module: test_export_coordinator
      1 ModuleNotFoundError: No module named 'documents.export_coordinator'
      1 Ran 1 test
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/export_coordinator.py b/client/documents/export_coordinator.py
new file mode 100644
index 0000000..9e9d4bd
--- /dev/null
+++ b/client/documents/export_coordinator.py
@@ -0,0 +1,174 @@
+"""Export flows of the main window, without wx.
+
+``ExportCoordinator`` owns single export (choose a path, fix the extension, convert
+first if the document is pending, write, report) and the Export All chain (choose a
+folder, check conflicts, then one document per UI turn through ``call_after``, then
+one summary). The view owns its dialogs and their texts; the coordinator owns the
+outcome messages. The first Export All step runs in the caller's turn.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Callable
+from pathlib import Path
+from typing import Protocol
+
+from documents.controller import DocumentController
+from documents.export_results import ExportBatchResult
+from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
+from documents.workspace import Document
+from i18n import _
+
+CallAfter = Callable[..., object]
+
+
+class ExportView(Protocol):
+    def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None: ...
+
+    def choose_export_directory(self) -> Path | None: ...
+
+    def confirm_overwrite_all(self, conflicts: list[Path]) -> bool: ...
+
+    def show_info(self, message: str, caption: str) -> None: ...
+
+    def show_warning(self, message: str, caption: str) -> None: ...
+
+    def show_error(self, message: str, caption: str) -> None: ...
+
+
+class ExportConversions(Protocol):
+    """Satisfied by ``conversion.presenter.ConversionPresenter``."""
+
+    def missing_table_message(self) -> str | None: ...
+
+    def convert_for_export(
+        self,
+        raw_text: str,
+        *,
+        on_success: Callable[[str], None],
+        on_error: Callable[[str], None],
+    ) -> None: ...
+
+
+class ExportCoordinator:
+    def __init__(
+        self,
+        view: ExportView,
+        documents: DocumentController,
+        conversions: ExportConversions,
+        *,
+        call_after: CallAfter,
+    ) -> None:
+        self._view = view
+        self._documents = documents
+        self._conversions = conversions
+        self._call_after = call_after
+
+    def write_document(self, destination_path: Path, document: Document, format_key: str) -> None:
+        descriptor = get_format(format_key)
+        if not descriptor.exportable or descriptor.writer is None:
+            raise ValueError(f'Unsupported export format: "{format_key}".')
+        context = ExportContext(dual_view_results=self._documents.get_dual_view_results(document.name))
+        descriptor.writer(destination_path, document, context)
+
+    def export_document(self, document: Document, format_key: str) -> None:
+        descriptor = get_format(format_key)
+        destination_path = self._view.choose_export_path(f"{document.name}{descriptor.extension}", descriptor)
+        if destination_path is None:
+            return
+        target_suffix = descriptor.extension
+        if destination_path.suffix.casefold() != target_suffix:
+            destination_path = destination_path.with_suffix(target_suffix)
+        if document.braille is None:
+            message = self._conversions.missing_table_message()
+            if message is not None:
+                self._view.show_error(message, _("Error"))
+                return
+            self._conversions.convert_for_export(
+                document.text,
+                on_success=lambda braille: self._write_single(
+                    Document(document.name, document.text, braille),
+                    destination_path,
+                    format_key,
+                ),
+                on_error=lambda message: self._view.show_error(message, _("Error")),
+            )
+            return
+        self._write_single(document, destination_path, format_key)
+
+    def _write_single(self, document: Document, destination_path: Path, format_key: str) -> None:
+        try:
+            self.write_document(destination_path, document, format_key)
+        except OSError as exc:
+            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
+            return
+        self._view.show_info(_("The document was exported successfully."), _("Export Complete"))
+
+    def export_all(self, format_key: str) -> None:
+        destination_dir = self._view.choose_export_directory()
+        if destination_dir is None:
+            return
+        suffix = get_format(format_key).extension
+        documents = self._documents.documents_snapshot()
+        conflicts = [
+            destination_dir / f"{document.name}{suffix}"
+            for document in documents
+            if (destination_dir / f"{document.name}{suffix}").exists()
+        ]
+        if conflicts and not self._view.confirm_overwrite_all(conflicts):
+            return
+        self._export_next(documents, destination_dir, format_key, ExportBatchResult())
+
+    def _export_next(
+        self,
+        remaining: list[Document],
+        destination_dir: Path,
+        format_key: str,
+        result: ExportBatchResult,
+    ) -> None:
+        if not remaining:
+            self._show_batch_result(result)
+            return
+
+        descriptor = get_format(format_key)
+        document = remaining[0]
+        rest = remaining[1:]
+        destination_path = destination_dir / f"{document.name}{descriptor.extension}"
+
+        def continue_batch() -> None:
+            self._call_after(self._export_next, rest, destination_dir, format_key, result)
+
+        def write_document(export_document: Document) -> None:
+            try:
+                self.write_document(destination_path, export_document, format_key)
+            except OSError as exc:
+                result.add_failure(document.name, str(exc))
+            else:
+                result.add_success(document.name)
+            continue_batch()
+
+        if document.braille is not None:
+            write_document(document)
+            return
+
+        def conversion_failed(message: str) -> None:
+            result.add_failure(document.name, message)
+            continue_batch()
+
+        message = self._conversions.missing_table_message()
+        if message is not None:
+            conversion_failed(message)
+            return
+        self._conversions.convert_for_export(
+            document.text,
+            on_success=lambda braille: write_document(Document(document.name, document.text, braille)),
+            on_error=conversion_failed,
+        )
+
+    def _show_batch_result(self, result: ExportBatchResult) -> None:
+        message = _(result.summary_template).format(**result.summary_values)
+        caption = _(result.summary_title)
+        if result.all_succeeded:
+            self._view.show_info(message, caption)
+        else:
+            self._view.show_warning(message, caption)
PATCH
```

- [ ] **Step 4: Run the tests, the suite check, the msgid scan and the import grep.**

```bash
$PY -m unittest tests.test_export_coordinator 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$T/tools/check_suite.sh 759 75 12
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo AC3; grep -nE "^(import wx|from wx)|^(import|from) gui" documents/export_coordinator.py
echo end
```

Expected (nothing between the labels):

```text
Ran 21 tests
OK
Ran 759 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 12 (expected 12)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (759)
new tests ok: 75 (expected 75)
new tests not ok: 0
source msgids: 353
SOURCE == SAVED
AC3
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/export_coordinator.py client/tests/test_export_coordinator.py
git -C $REPO commit -q -F - <<'MSG'
refactor: add the wx-free export coordinator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: add the wx-free export coordinator
```

---

### Task 7: Route export through the coordinator (spec step 7)

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`

**Interfaces:**
- Consumes: Task 6's `ExportCoordinator`.
- Produces in `gui.BrailleFrame`: `_initialize_conversion_state()` also sets `_export_coordinator = ExportCoordinator(self, self._document_controller, self._conversion_presenter, call_after=wx.CallAfter)`; `on_export_document` and `on_output_text_key_down` keep their guards and save-first and end with `self._export_coordinator.export_document(document, key)`; `on_export_all_documents` keeps its two guards and ends with `self._export_coordinator.export_all(key)`; public view methods `show_warning`, `choose_export_path(default_file, descriptor)` (the file dialog of `_export_document_with_dialog`, wildcard computed first as today), `choose_export_directory()` (the folder dialog), `confirm_overwrite_all(conflicts)` (renamed, same body). Deleted: `_confirm_overwrite_all`, `_export_document_with_dialog`, `_write_export_document`, `_continue_single_export`, the temporary `_start_export_conversion`, `_export_next_document`, `_show_export_all_result`; imports `ExportContext`, `ExportBatchResult`, `missing_default_table_message`.
- Test changes: `_make_frame` sets `_export_coordinator = Mock(spec=gui.ExportCoordinator)` instead of the `_show_export_all_result` mock; the P1-2 class gets `_make_export_frame()` (a real `gui.ExportCoordinator` with the frame as view, the mock presenter and a synchronous `call_after`), and its four export tests enter through it with unchanged expectations (the `gui._` patch still reaches the dialog title and wildcard); the Ctrl+S test expects `call.coordinator.export_document(<open document>, "brl")`; `_wire_conversion` also builds the coordinator; the 10 moved export tests are deleted (15 test lines, spec correction 1).

- [ ] **Step 1: Write the failing frame tests** (`FrameExportDelegationTest`, 5 tests; `FrameExportViewMethodsTest`, 4 tests; appended at the end).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 7ee9da8..725e0ee 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -3584,5 +3584,160 @@ class FrameViewMethodsTest(unittest.TestCase):
         )
 
 
+
+class FrameExportDelegationTest(unittest.TestCase):
+    """The frame wires the export coordinator; the entry points keep their guards and save first."""
+
+    def _make_frame(self, documents=(Document("alpha", "a", None), Document("beta", "b", "⠃"))) -> gui.BrailleFrame:
+        frame = object.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController(documents=list(documents), open_name="alpha")
+        frame.steps = Mock()
+        frame._export_coordinator = frame.steps.coordinator
+        frame._save_open_document_with_feedback = frame.steps.save
+        frame.output_txt = frame.steps.output_txt
+        frame.steps.save.return_value = True
+        return frame
+
+    def test_initialize_conversion_state_wires_coordinator_to_presenter(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        frame._document_controller = DocumentController()
+        frame.translation_runtime = Mock()
+
+        with patch.object(gui, "ConversionPresenter") as presenter_class, patch.object(
+            gui, "ExportCoordinator"
+        ) as coordinator_class:
+            frame._initialize_conversion_state()
+
+        coordinator_class.assert_called_once_with(
+            frame,
+            frame._document_controller,
+            presenter_class.return_value,
+            call_after=gui.wx.CallAfter,
+        )
+        self.assertIs(frame._export_coordinator, coordinator_class.return_value)
+
+    def test_export_menu_saves_then_exports_the_reread_selection(self) -> None:
+        frame = self._make_frame()
+        frame._get_selected_document = Mock(
+            side_effect=[Document("beta", "b", "⠃"), Document("beta", "b2", "⠃⠃")]
+        )
+
+        frame.on_export_document("html")
+
+        self.assertEqual(
+            frame.steps.mock_calls,
+            [call.save(), call.coordinator.export_document(Document("beta", "b2", "⠃⠃"), "html")],
+        )
+
+    def test_export_menu_without_selection_or_with_failed_save_does_nothing_more(self) -> None:
+        frame = self._make_frame()
+        frame._get_selected_document = Mock(return_value=None)
+        frame.on_export_document("brl")
+        self.assertEqual(frame.steps.mock_calls, [])
+
+        frame._get_selected_document = Mock(return_value=Document("beta", "b", "⠃"))
+        frame.steps.save.return_value = False
+        frame.on_export_document("brl")
+        self.assertEqual(frame.steps.mock_calls, [call.save()])
+
+    def test_export_all_menu_keeps_guards_and_save_first(self) -> None:
+        frame = self._make_frame(documents=())
+        frame.on_export_all_documents("dep")
+        self.assertEqual(frame.steps.mock_calls, [])
+
+        frame = self._make_frame()
+        frame.steps.save.return_value = False
+        frame.on_export_all_documents("dep")
+        self.assertEqual(frame.steps.mock_calls, [call.save()])
+
+        frame.steps.reset_mock()
+        frame.steps.save.return_value = True
+        frame.on_export_all_documents("dep")
+        self.assertEqual(frame.steps.mock_calls, [call.save(), call.coordinator.export_all("dep")])
+
+    def test_ctrl_s_without_open_document_or_with_failed_save_only_refocuses(self) -> None:
+        event = Mock()
+        event.GetKeyCode.return_value = 83
+        event.ControlDown.return_value = True
+        frame = self._make_frame()
+        frame._document_controller.open_name = None
+        frame.on_output_text_key_down(event)
+        self.assertEqual(frame.steps.mock_calls, [call.save(), call.output_txt.SetFocus()])
+
+        frame = self._make_frame()
+        frame.steps.save.return_value = False
+        frame.on_output_text_key_down(event)
+        self.assertEqual(frame.steps.mock_calls, [call.save(), call.output_txt.SetFocus()])
+        event.Skip.assert_not_called()
+
+
+class FrameExportViewMethodsTest(unittest.TestCase):
+    """The frame's dialogs behind ``ExportView``."""
+
+    def _dialog(self, result, path: str = ""):
+        dialog = Mock()
+        dialog.__enter__ = Mock(return_value=dialog)
+        dialog.__exit__ = Mock(return_value=False)
+        dialog.ShowModal.return_value = result
+        dialog.GetPath.return_value = path
+        return dialog
+
+    def test_choose_export_path_shows_the_save_dialog(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        for result, expected in ((gui.wx.ID_OK, Path("/tmp/out.brl")), (gui.wx.CANCEL, None)):
+            with self.subTest(result=result):
+                dialog_class = Mock(return_value=self._dialog(result, "/tmp/out.brl"))
+                with patch.object(gui.wx, "FileDialog", dialog_class), patch.object(gui, "_", fake_translate):
+                    chosen = frame.choose_export_path("alpha.brl", gui.get_format("brl"))
+
+                self.assertEqual(chosen, expected)
+                dialog_class.assert_called_once_with(
+                    frame,
+                    "T[Export Document]",
+                    defaultFile="alpha.brl",
+                    wildcard="T[Braille files (*.brl)|*.brl]",
+                    style=gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
+                )
+
+    def test_choose_export_directory_shows_the_folder_dialog(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        for result, expected in ((gui.wx.ID_OK, Path("/tmp/folder")), (gui.wx.CANCEL, None)):
+            with self.subTest(result=result):
+                dialog_class = Mock(return_value=self._dialog(result, "/tmp/folder"))
+                with patch.object(gui.wx, "DirDialog", dialog_class):
+                    chosen = frame.choose_export_directory()
+
+                self.assertEqual(chosen, expected)
+                dialog_class.assert_called_once_with(frame, gui._("Export All Documents"))
+
+    def test_confirm_overwrite_all_asks_only_for_conflicts(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        with patch.object(gui.wx, "MessageBox") as message_box:
+            self.assertTrue(frame.confirm_overwrite_all([]))
+            message_box.assert_not_called()
+            for answer, expected in ((gui.wx.YES, True), (gui.wx.NO, False)):
+                with self.subTest(answer=answer):
+                    message_box.reset_mock()
+                    message_box.return_value = answer
+                    self.assertIs(frame.confirm_overwrite_all([Path("/tmp/alpha.brl")]), expected)
+                    message_box.assert_called_once_with(
+                        gui._(
+                            "The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
+                        ),
+                        gui._("Confirm Overwrite"),
+                        gui.wx.YES_NO | gui.wx.ICON_WARNING,
+                        parent=frame,
+                    )
+
+    def test_show_warning_uses_the_warning_icon(self) -> None:
+        frame = object.__new__(gui.BrailleFrame)
+        with patch.object(gui.wx, "MessageBox") as message_box:
+            frame.show_warning("warning text", "Warning caption")
+
+        message_box.assert_called_once_with(
+            "warning text", "Warning caption", gui.wx.OK | gui.wx.ICON_WARNING, parent=frame
+        )
+
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them to see them fail.**

```bash
$PY -m unittest tests.test_gui_document_flows.FrameExportDelegationTest tests.test_gui_document_flows.FrameExportViewMethodsTest 2>&1 | grep -E '^(ERROR|FAIL):|^(Attribute|Type)Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//; s/id='[0-9]+'/id=?/g" | LC_ALL=C sort | uniq -c
```

Expected (`gui` has no coordinator yet; the entry points still run today's chains, whose `wx.FileDialog`/`wx.DirDialog` stubs are not context managers; the new view methods are stub no-ops; `AssertionError` texts left out):

```text
      1 AttributeError: <module 'gui' from 'client/gui.py'> does not have the attribute 'ExportCoordinator'
      1 ERROR: test_export_all_menu_keeps_guards_and_save_first
      1 ERROR: test_export_menu_saves_then_exports_the_reread_selection
      1 ERROR: test_initialize_conversion_state_wires_coordinator_to_presenter
      1 FAIL: test_choose_export_directory_shows_the_folder_dialog (result=2)
      1 FAIL: test_choose_export_directory_shows_the_folder_dialog (result=8)
      1 FAIL: test_choose_export_path_shows_the_save_dialog (result=2)
      1 FAIL: test_choose_export_path_shows_the_save_dialog (result=8)
      1 FAIL: test_confirm_overwrite_all_asks_only_for_conflicts
      1 FAIL: test_show_warning_uses_the_warning_icon
      1 FAILED (failures=6, errors=3)
      1 Ran 9 tests
      1 TypeError: 'tests.wx_stub.gui_frame_stubs.<locals>._DirDialog' object does not support the context manager protocol (missed __exit__ method)
      1 TypeError: 'tests.wx_stub.gui_frame_stubs.<locals>._FileDialog' object does not support the context manager protocol (missed __exit__ method)
```

- [ ] **Step 3: Implement, and move the frame's export tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index 3973fbe..b37eb2f 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -10,7 +10,7 @@ from i18n import _, resource_path
 from app_paths import ApplicationDataError, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
-from conversion.presenter import ConversionPresenter, missing_default_table_message
+from conversion.presenter import ConversionPresenter
 from conversion.service import (
 	ConversionRequest,
 	ConversionStageError,
@@ -19,7 +19,8 @@ from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
 from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
-from documents.formats import ExportContext, build_export_wildcard, get_format
+from documents.export_coordinator import ExportCoordinator
+from documents.formats import DocumentFormatDescriptor, build_export_wildcard, get_format
 from documents.session import (
     format_window_title,
 )
@@ -32,9 +33,6 @@ from documents.workspace import (
     normalize_document_name,
 )
 from documents.workspace_service import DocumentWorkspaceService
-from documents.export_results import (
-    ExportBatchResult,
-)
 from ui.action_menu import get_document_menu_enabled_state
 from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
 from ui.menu_builder import apply_document_menu_state, build_document_menu
@@ -222,6 +220,12 @@ class BrailleFrame(wx.Frame):
 			call_after=wx.CallAfter,
 			call_later=wx.CallLater,
 		)
+		self._export_coordinator = ExportCoordinator(
+			self,
+			self._document_controller,
+			self._conversion_presenter,
+			call_after=wx.CallAfter,
+		)
 
 	def _apply_initial_settings(self, initial_settings: ViewSettings) -> None:
 		self._apply_editor_view_settings(initial_settings)
@@ -565,53 +569,6 @@ class BrailleFrame(wx.Frame):
 		with FileIssuesDialog(self, title=title, message=message, issues=self._format_batch_issue_lines(issues)) as dialog:
 			dialog.ShowModal()
 
-	def _confirm_overwrite_all(self, conflicts: list[Path]) -> bool:
-		if not conflicts:
-			return True
-		message = _(
-			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
-		)
-		return (
-			wx.MessageBox(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
-		)
-
-	def _export_document_with_dialog(self, document: Document, format_key: str) -> None:
-		descriptor = get_format(format_key)
-		default_file = f"{document.name}{descriptor.extension}"
-		wildcard = build_export_wildcard(descriptor, _)
-		with wx.FileDialog(
-			self,
-			_("Export Document"),
-			defaultFile=default_file,
-			wildcard=wildcard,
-			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
-		) as file_dialog:
-			if file_dialog.ShowModal() != wx.ID_OK:
-				return
-			destination_path = Path(file_dialog.GetPath())
-		target_suffix = descriptor.extension
-		if destination_path.suffix.casefold() != target_suffix:
-			destination_path = destination_path.with_suffix(target_suffix)
-		if document.braille is None:
-			self._start_export_conversion(
-				document,
-				destination_path,
-				format_key,
-				on_success=lambda braille: self._continue_single_export(
-					Document(document.name, document.text, braille),
-					destination_path,
-					format_key,
-				),
-				on_error=lambda message: wx.MessageBox(
-					message,
-					_("Error"),
-					wx.OK | wx.ICON_ERROR,
-					parent=self,
-				),
-			)
-			return
-		self._continue_single_export(document, destination_path, format_key)
-
 	def _set_view_font_size(self, font_size: int) -> None:
 		self.view_settings = normalize_view_settings(
 			replace(self.view_settings, font_size=font_size)
@@ -919,23 +876,14 @@ class BrailleFrame(wx.Frame):
 		if not self._save_open_document_with_feedback():
 			return
 		selected_document = self._get_selected_document() or selected_document
-		self._export_document_with_dialog(selected_document, format_key)
+		self._export_coordinator.export_document(selected_document, format_key)
 
 	def on_export_all_documents(self, format_key: str) -> None:
 		if not self._document_controller.has_documents:
 			return
 		if not self._save_open_document_with_feedback():
 			return
-		with wx.DirDialog(self, _("Export All Documents")) as dir_dialog:
-			if dir_dialog.ShowModal() != wx.ID_OK:
-				return
-			destination_dir = Path(dir_dialog.GetPath())
-		suffix = get_format(format_key).extension
-		documents = self._document_controller.documents_snapshot()
-		conflicts = [destination_dir / f"{document.name}{suffix}" for document in documents if (destination_dir / f"{document.name}{suffix}").exists()]
-		if conflicts and not self._confirm_overwrite_all(conflicts):
-			return
-		self._export_next_document(documents, destination_dir, format_key, ExportBatchResult())
+		self._export_coordinator.export_all(format_key)
 
 	def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
 		step = get_font_size_step_from_wheel(event.GetWheelRotation(), event.ControlDown())
@@ -965,7 +913,7 @@ class BrailleFrame(wx.Frame):
 				controller = self._document_controller
 				document = controller.get_document(controller.open_document_name)
 				if document is not None:
-					self._export_document_with_dialog(document, get_format("brl").key)
+					self._export_coordinator.export_document(document, get_format("brl").key)
 			self.output_txt.SetFocus()
 			return
 		event.Skip()
@@ -1014,101 +962,6 @@ class BrailleFrame(wx.Frame):
 		with SpeechSymbolsDialog(self, dictionary_path=dictionary_path) as editor:
 			editor.ShowModal()
 
-	def _write_export_document(self, destination_path: Path, document: Document, format_key: str) -> None:
-		descriptor = get_format(format_key)
-		if not descriptor.exportable or descriptor.writer is None:
-			raise ValueError(f'Unsupported export format: "{format_key}".')
-		context = ExportContext(dual_view_results=self._document_controller.get_dual_view_results(document.name))
-		descriptor.writer(destination_path, document, context)
-
-	def _continue_single_export(self, document: Document, destination_path: Path, format_key: str) -> None:
-		try:
-			self._write_export_document(destination_path, document, format_key)
-		except OSError as exc:
-			self._show_file_error(_("Failed to export document: {error}"), exc)
-			return
-		wx.MessageBox(
-			_("The document was exported successfully."),
-			_("Export Complete"),
-			wx.OK | wx.ICON_INFORMATION,
-			parent=self,
-		)
-
-	def _start_export_conversion(
-		self,
-		document: Document,
-		destination_path: Path,
-		format_key: str,
-		*,
-		on_success=None,
-		on_error=None,
-		on_missing_table=None,
-	) -> bool:
-		message = missing_default_table_message(self.translation_tables)
-		if message is not None:
-			if on_missing_table is not None:
-				on_missing_table(message)
-			elif on_error is not None:
-				on_error(message)
-			return False
-		self._conversion_presenter.convert_for_export(document.text, on_success=on_success, on_error=on_error)
-		return True
-
-	def _export_next_document(
-		self,
-		remaining: list[Document],
-		destination_dir: Path,
-		format_key: str,
-		result: ExportBatchResult,
-	) -> None:
-		if not remaining:
-			self._show_export_all_result(result)
-			return
-
-		descriptor = get_format(format_key)
-		document = remaining[0]
-		rest = remaining[1:]
-		destination_path = destination_dir / f"{document.name}{descriptor.extension}"
-
-		def continue_batch() -> None:
-			wx.CallAfter(self._export_next_document, rest, destination_dir, format_key, result)
-
-		def write_document(export_document: Document) -> None:
-			try:
-				self._write_export_document(destination_path, export_document, format_key)
-			except OSError as exc:
-				result.add_failure(document.name, str(exc))
-			else:
-				result.add_success(document.name)
-			continue_batch()
-
-		if document.braille is not None:
-			write_document(document)
-			return
-
-		def conversion_failed(message: str) -> None:
-			result.add_failure(document.name, message)
-			continue_batch()
-
-		self._start_export_conversion(
-			document,
-			destination_path,
-			format_key,
-			on_success=lambda braille: write_document(Document(document.name, document.text, braille)),
-			on_error=conversion_failed,
-			on_missing_table=conversion_failed,
-		)
-
-	def _show_export_all_result(self, result: ExportBatchResult) -> None:
-		style = wx.OK | (wx.ICON_INFORMATION if result.all_succeeded else wx.ICON_WARNING)
-		message = _(result.summary_template).format(**result.summary_values)
-		wx.MessageBox(
-			message,
-			_(result.summary_title),
-			style,
-			parent=self,
-		)
-
 	def on_convert(self, _evt):
 		self._conversion_presenter.convert()
 
@@ -1170,6 +1023,40 @@ class BrailleFrame(wx.Frame):
 	def show_error(self, message: str, caption: str) -> None:
 		wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR, parent=self)
 
+	# --- ExportView (documents/export_coordinator.py) -----------------------
+
+	def show_warning(self, message: str, caption: str) -> None:
+		wx.MessageBox(message, caption, wx.OK | wx.ICON_WARNING, parent=self)
+
+	def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None:
+		wildcard = build_export_wildcard(descriptor, _)
+		with wx.FileDialog(
+			self,
+			_("Export Document"),
+			defaultFile=default_file,
+			wildcard=wildcard,
+			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
+		) as file_dialog:
+			if file_dialog.ShowModal() != wx.ID_OK:
+				return None
+			return Path(file_dialog.GetPath())
+
+	def choose_export_directory(self) -> Path | None:
+		with wx.DirDialog(self, _("Export All Documents")) as dir_dialog:
+			if dir_dialog.ShowModal() != wx.ID_OK:
+				return None
+			return Path(dir_dialog.GetPath())
+
+	def confirm_overwrite_all(self, conflicts: list[Path]) -> bool:
+		if not conflicts:
+			return True
+		message = _(
+			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
+		)
+		return (
+			wx.MessageBox(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
+		)
+
 def _show_application_data_error(error: ApplicationDataError) -> None:
 	wx.MessageBox(
 		_(
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 725e0ee..f4b8a27 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -4,7 +4,6 @@ import importlib
 import tempfile
 import unittest
 import zipfile
-from dataclasses import replace
 from pathlib import Path
 from types import SimpleNamespace
 from unittest.mock import ANY, DEFAULT, Mock, call, patch
@@ -31,7 +30,6 @@ from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
-from documents.formats import ExportContext, get_format
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 from dual_view.html import render_dual_view_html
 from dual_view.model import DualViewSegment, build_dual_view_model
@@ -59,89 +57,13 @@ class GuiDocumentFlowsTest(unittest.TestCase):
         frame._convert_dialog = Mock()
         frame.input_txt = Mock()
         frame.output_txt = Mock()
-        frame._show_export_all_result = Mock()
+        frame._export_coordinator = Mock(spec=gui.ExportCoordinator)
         frame._dual_view_frame = None
         frame._document_controller = DocumentController(documents=list(documents), open_name=open_name)
         frame._workspace_service = DocumentWorkspaceService(frame._document_controller, Path("unused-workspace"))
         frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
         return frame
 
-    def test_write_export_document_uses_registry_writer(self) -> None:
-        frame = self._make_frame()
-        document = Document("alpha", "text", "braille")
-        writer = Mock()
-        descriptor = replace(get_format("dep"), writer=writer)
-
-        with patch.object(gui, "get_format", return_value=descriptor) as get_format_mock:
-            frame._write_export_document(Path("/tmp/custom.dep"), document, "dep")
-
-        get_format_mock.assert_called_once_with("dep")
-        writer.assert_called_once_with(Path("/tmp/custom.dep"), document, ExportContext())
-
-    def test_write_export_document_passes_cached_results_to_every_writer(self) -> None:
-        frame = self._make_frame()
-        document = Document("alpha", "text", "braille")
-        cached_results = (Mock(),)
-        frame._document_controller.set_dual_view_results("alpha", cached_results)
-        writer = Mock()
-        descriptor = replace(get_format("dep"), writer=writer)
-
-        with patch.object(gui, "get_format", return_value=descriptor):
-            frame._write_export_document(Path("/tmp/custom.dep"), document, "dep")
-
-        writer.assert_called_once_with(
-            Path("/tmp/custom.dep"),
-            document,
-            ExportContext(dual_view_results=cached_results),
-        )
-
-    def test_write_html_export_document_passes_cached_dual_view_results(self) -> None:
-        frame = self._make_frame()
-        document = Document("alpha", "text", "braille")
-        cached_results = (Mock(),)
-        frame._document_controller.set_dual_view_results("alpha", cached_results)
-        writer = Mock()
-        descriptor = replace(get_format("html"), writer=writer)
-
-        with patch.object(gui, "get_format", return_value=descriptor):
-            frame._write_export_document(Path("/tmp/custom.html"), document, "html")
-
-        writer.assert_called_once_with(
-            Path("/tmp/custom.html"),
-            document,
-            ExportContext(dual_view_results=cached_results),
-        )
-
-    def test_write_export_document_rejects_non_exportable_format(self) -> None:
-        frame = self._make_frame()
-        document = Document("alpha", "text", "braille")
-        descriptor = replace(get_format("txt"), writer=Mock())
-
-        with patch.object(gui, "get_format", return_value=descriptor):
-            with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
-                frame._write_export_document(Path("/tmp/custom.txt"), document, "txt")
-
-    def test_export_next_document_uses_registry_extension(self) -> None:
-        frame = self._make_frame()
-        written: list[Path] = []
-        document = Document("alpha", "text", "braille")
-        descriptor = replace(get_format("brl"), extension=".braille")
-
-        def write_export_document(destination_path: Path, export_document: Document, format_key: str) -> None:
-            written.append(destination_path)
-
-        frame._write_export_document = write_export_document
-        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))
-
-        with (
-            patch.object(gui, "get_format", return_value=descriptor) as get_format_mock,
-            patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
-        ):
-            frame._export_next_document([document], Path("/tmp/export"), "brl", ExportBatchResult())
-
-        self.assertEqual(written, [Path("/tmp/export/alpha.braille")])
-        get_format_mock.assert_called_once_with("brl")
-
     def test_sync_document_menu_state_before_document_list_exists(self) -> None:
         frame = self._make_frame(documents=())
         menu_items = {
@@ -705,74 +627,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         log_exception.assert_called_once_with("Failed to clean up dual-view HTML")
         runtime.close.assert_called_once_with()
 
-    def test_export_all_continues_after_conversion_failure(self) -> None:
-        frame = self._make_frame()
-        written: list[tuple[str, str]] = []
-
-        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
-            written.append((destination_path.name, document.name))
-
-        def start_export_conversion(document: Document, destination_path: Path, format_key: str, *, on_success=None, on_error=None, on_missing_table=None):
-            if document.name == "pending":
-                on_error("Translation failed")
-            else:
-                raise AssertionError("unexpected conversion request")
-            return True
-
-        frame._write_export_document = write_export_document
-        frame._start_export_conversion = start_export_conversion
-
-        documents = [
-            Document("ready-one", "text", "braille-one"),
-            Document("pending", "text", None),
-            Document("ready-two", "text", "braille-two"),
-        ]
-
-        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
-            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())
-
-        self.assertEqual(
-            written,
-            [
-                ("ready-one.brl", "ready-one"),
-                ("ready-two.brl", "ready-two"),
-            ],
-        )
-        frame._show_export_all_result.assert_called_once()
-        result = frame._show_export_all_result.call_args.args[0]
-        self.assertFalse(result.all_succeeded)
-        self.assertEqual(
-            result.summary_values,
-            {
-                "success_count": 2,
-                "failure_count": 1,
-                "failures": "pending: Translation failed",
-            },
-        )
-
-    def test_export_all_shows_one_success_dialog(self) -> None:
-        frame = self._make_frame()
-        written: list[str] = []
-
-        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
-            written.append(destination_path.name)
-
-        frame._write_export_document = write_export_document
-        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))
-
-        documents = [
-            Document("alpha", "text", "a"),
-            Document("beta", "text", "b"),
-        ]
-
-        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
-            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())
-
-        self.assertEqual(written, ["alpha.brl", "beta.brl"])
-        frame._show_export_all_result.assert_called_once()
-        result = frame._show_export_all_result.call_args.args[0]
-        self.assertTrue(result.all_succeeded)
-
     def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
         frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
         frame._dual_view_frame = Mock()
@@ -894,115 +748,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame._refresh_dual_view.assert_called_once_with()
         frame._open_document_by_name.assert_called_once_with("beta")
 
-    def test_export_all_shows_one_partial_failure_dialog_with_names(self) -> None:
-        frame = self._make_frame()
-        written: list[str] = []
-
-        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
-            if document.name == "write-fail":
-                raise OSError("disk full")
-            written.append(destination_path.name)
-
-        def start_export_conversion(document: Document, destination_path: Path, format_key: str, *, on_success=None, on_error=None, on_missing_table=None):
-            if document.name == "convert-fail":
-                on_error("Translation failed")
-            else:
-                on_success("converted-braille")
-            return True
-
-        frame._write_export_document = write_export_document
-        frame._start_export_conversion = start_export_conversion
-
-        documents = [
-            Document("alpha", "text", "a"),
-            Document("convert-fail", "text", None),
-            Document("write-fail", "text", "w"),
-        ]
-
-        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
-            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())
-
-        self.assertEqual(written, ["alpha.brl"])
-        frame._show_export_all_result.assert_called_once()
-        result = frame._show_export_all_result.call_args.args[0]
-        self.assertFalse(result.all_succeeded)
-        self.assertEqual(
-            result.summary_values,
-            {
-                "success_count": 1,
-                "failure_count": 2,
-                "failures": "convert-fail: Translation failed\nwrite-fail: disk full",
-            },
-        )
-
-    def test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes(self) -> None:
-        frame = self._make_frame()
-        frame.translation_settings = Mock()
-        frame._write_export_document = Mock()
-        missing_table_message = gui._("Please select a translation table first.")
-
-        documents = [
-            Document("alpha", "text", None),
-            Document("beta", "text", None),
-        ]
-
-        frame.translation_tables = {"default": ""}
-        with (
-            patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
-            patch.object(gui.wx, "MessageBox") as message_box,
-        ):
-            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())
-
-        frame._write_export_document.assert_not_called()
-        message_box.assert_not_called()
-        frame._show_export_all_result.assert_called_once()
-        result = frame._show_export_all_result.call_args.args[0]
-        self.assertFalse(result.all_succeeded)
-        self.assertEqual(
-            result.summary_values,
-            {
-                "success_count": 0,
-                "failure_count": 2,
-                "failures": f"alpha: {missing_table_message}\nbeta: {missing_table_message}",
-            },
-        )
-
-    def test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output(self) -> None:
-        frame = self._make_frame()
-        frame.translation_settings = Mock()
-        frame._write_export_document = Mock()
-
-        class _AcceptedFileDialog:
-            def __init__(self, *_args, **_kwargs):
-                pass
-
-            def __enter__(self):
-                return self
-
-            def __exit__(self, exc_type, exc, tb):
-                return False
-
-            def ShowModal(self):
-                return gui.wx.ID_OK
-
-            def GetPath(self):
-                return "/tmp/exported"
-
-        frame.translation_tables = {"default": ""}
-        with (
-            patch.object(gui.wx, "FileDialog", _AcceptedFileDialog),
-            patch.object(gui.wx, "MessageBox") as message_box,
-        ):
-            frame._export_document_with_dialog(Document("alpha", "text", None), "brl")
-
-        frame._write_export_document.assert_not_called()
-        message_box.assert_called_once_with(
-            gui._("Please select a translation table first."),
-            gui._("Error"),
-            gui.wx.OK | gui.wx.ICON_ERROR,
-            parent=frame,
-        )
-
     def test_apply_settings_from_dialog_updates_all_live_state(self) -> None:
         frame = object.__new__(gui.BrailleFrame)
         frame._apply_editor_view_settings = Mock()
@@ -1341,6 +1086,16 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
             patch.object(gui, "_", fake_translate),
         )
 
+    def _make_export_frame(self):
+        frame = self._make_frame()
+        frame._export_coordinator = gui.ExportCoordinator(
+            frame,
+            frame._document_controller,
+            frame._conversion_presenter,
+            call_after=lambda fn, *args, **kwargs: fn(*args, **kwargs),
+        )
+        return frame
+
     def _select_first_of(self, frame, *names: str) -> None:
         frame._document_controller.load_documents([Document(name, "text", None) for name in names])
         frame.document_list = Mock()
@@ -1542,12 +1297,11 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         }
         for key, wildcard in expected_wildcards.items():
             with self.subTest(format_key=key):
-                frame = self._make_frame()
-                frame._write_export_document = Mock()
-                frame._start_export_conversion = Mock()
+                frame = self._make_export_frame()
+                frame._export_coordinator.write_document = Mock()
                 dialogs.clear()
                 with patch.object(gui.wx, "FileDialog", RecordedFileDialog), patch.object(gui, "_", fake_translate):
-                    frame._export_document_with_dialog(Document("alpha", "t", "b"), key)
+                    frame._export_coordinator.export_document(Document("alpha", "t", "b"), key)
 
                 self.assertEqual(
                     dialogs,
@@ -1562,14 +1316,14 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                         )
                     ],
                 )
-                frame._write_export_document.assert_not_called()
-                frame._start_export_conversion.assert_not_called()
+                frame._export_coordinator.write_document.assert_not_called()
+                frame._conversion_presenter.convert_for_export.assert_not_called()
 
     def test_export_dialog_corrects_only_a_wrong_extension(self) -> None:
         for chosen, written in (("/tmp/x/out.TXT", "/tmp/x/out.brl"), ("/tmp/x/out.BRL", "/tmp/x/out.BRL")):
             with self.subTest(chosen=chosen):
-                frame = self._make_frame()
-                frame._write_export_document = Mock()
+                frame = self._make_export_frame()
+                frame._export_coordinator.write_document = Mock()
                 dialog = Mock()
                 dialog.__enter__ = Mock(return_value=dialog)
                 dialog.__exit__ = Mock(return_value=False)
@@ -1580,13 +1334,13 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                     patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)),
                     patch.object(gui.wx, "MessageBox", Mock()) as message_box,
                 ):
-                    frame._export_document_with_dialog(document, "brl")
+                    frame._export_coordinator.export_document(document, "brl")
 
-                frame._write_export_document.assert_called_once_with(Path(written), document, "brl")
+                frame._export_coordinator.write_document.assert_called_once_with(Path(written), document, "brl")
                 message_box.assert_called_once()
 
     def test_real_writers_produce_today_bytes(self) -> None:
-        frame = self._make_frame()
+        frame = self._make_export_frame()
         results = (
             DualViewSegment(
                 result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
@@ -1597,30 +1351,30 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
         with tempfile.TemporaryDirectory() as directory:
             root = Path(directory)
 
-            frame._write_export_document(root / "alpha.dep", Document("alpha", "text", None), "dep")
+            frame._export_coordinator.write_document(root / "alpha.dep", Document("alpha", "text", None), "dep")
             with zipfile.ZipFile(root / "alpha.dep") as archive:
                 members = {name: archive.read(name).decode("utf-8") for name in archive.namelist()}
             self.assertEqual(members, {"alpha.txt": "text", "alpha.brl": ""})
 
-            frame._write_export_document(root / "nested" / "alpha.brl", Document("alpha", "text", "⠁⠃"), "brl")
+            frame._export_coordinator.write_document(root / "nested" / "alpha.brl", Document("alpha", "text", "⠁⠃"), "brl")
             self.assertEqual((root / "nested" / "alpha.brl").read_bytes(), "⠁⠃".encode("utf-8"))
 
-            frame._write_export_document(root / "alpha.html", Document("alpha", "text", "b"), "html")
+            frame._export_coordinator.write_document(root / "alpha.html", Document("alpha", "text", "b"), "html")
             cached_html = render_dual_view_html(build_dual_view_model(results))
             self.assertEqual((root / "alpha.html").read_bytes(), cached_html.encode("utf-8"))
             self.assertIn('<span class="source">a</span>', cached_html)
 
-            frame._write_export_document(root / "beta.html", Document("beta", "text", "b"), "html")
+            frame._export_coordinator.write_document(root / "beta.html", Document("beta", "text", "b"), "html")
             empty_html = render_dual_view_html(build_dual_view_model(()))
             self.assertEqual((root / "beta.html").read_bytes(), empty_html.encode("utf-8"))
             self.assertNotEqual(cached_html, empty_html)
 
             with self.assertRaises(OSError):
-                frame._write_export_document(root / "missing" / "alpha.html", Document("alpha", "text", "b"), "html")
+                frame._export_coordinator.write_document(root / "missing" / "alpha.html", Document("alpha", "text", "b"), "html")
             self.assertFalse((root / "missing").exists())
 
     def test_export_all_html_uses_each_document_cache(self) -> None:
-        frame = self._make_frame()
+        frame = self._make_export_frame()
         results = (
             DualViewSegment(
                 result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
@@ -1628,13 +1382,15 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
             ),
         )
         frame._document_controller.set_dual_view_results("alpha", results)
-        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))
+        frame._conversion_presenter.convert_for_export.side_effect = AssertionError("conversion should not run")
         documents = [Document("alpha", "text", "a"), Document("beta", "text", "b")]
+        frame._document_controller.documents = documents
+        frame.show_info = Mock()
 
         with tempfile.TemporaryDirectory() as directory:
             root = Path(directory)
-            with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
-                frame._export_next_document(documents, root, "html", ExportBatchResult())
+            frame.choose_export_directory = Mock(return_value=root)
+            frame._export_coordinator.export_all("html")
 
             self.assertEqual(
                 (root / "alpha.html").read_text(encoding="utf-8"),
@@ -1644,15 +1400,17 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                 (root / "beta.html").read_text(encoding="utf-8"),
                 render_dual_view_html(build_dual_view_model(())),
             )
-        result = frame._show_export_all_result.call_args.args[0]
-        self.assertTrue(result.all_succeeded)
+        frame.show_info.assert_called_once_with(
+            gui._(ExportBatchResult().summary_template),
+            gui._(ExportBatchResult().summary_title),
+        )
 
     def test_ctrl_s_in_output_editor_exports_open_document_as_brl(self) -> None:
         frame = self._make_frame()
         steps = Mock()
         frame._save_open_document_with_feedback = steps.save
         steps.save.return_value = True
-        frame._export_document_with_dialog = steps.export
+        frame._export_coordinator = steps.coordinator
         frame.output_txt = steps.output_txt
         event = Mock()
         event.GetKeyCode.return_value = 83
@@ -1662,7 +1420,11 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
 
         self.assertEqual(
             steps.mock_calls,
-            [call.save(), call.export(frame._document_controller.get_document("alpha"), "brl"), call.output_txt.SetFocus()],
+            [
+                call.save(),
+                call.coordinator.export_document(frame._document_controller.get_document("alpha"), "brl"),
+                call.output_txt.SetFocus(),
+            ],
         )
         event.Skip.assert_not_called()
 
@@ -2721,6 +2483,12 @@ class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
             thread_factory=self.thread_factory,
             converter=self._convert,
         )
+        frame._export_coordinator = gui.ExportCoordinator(
+            frame,
+            frame._document_controller,
+            frame._conversion_presenter,
+            call_after=self.calls,
+        )
 
     def _make_frame(self, documents, open_name=None, selected_name=None) -> gui.BrailleFrame:
         frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
PATCH
```

- [ ] **Step 4: Run the touched modules, the characterization comparison, the suite check, the msgid scan and acceptance criteria 2 and 4.**

```bash
$PY -m unittest tests.test_gui_document_flows tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_jobs 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $T/tools/char_unchanged.py $REPO $(git -C $REPO log --format=%h --grep='^test: characterize conversion and export flows$' -1)
$T/tools/check_suite.sh 753 84 27
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo AC2; grep -nE "_start_conversion|_complete_conversion|_finish_conversion_|_start_export_conversion|_export_next_document|_write_export_document|_continue_single_export|_show_export_all_result|_missing_default_table_message|_export_document_with_dialog|_conversion_runner|_convert_dialog_timer|_set_conversion_busy|_show_converting_dialog|_close_converting_dialog|_confirm_overwrite_all" gui.py
echo AC4; grep -n "wx.CallAfter\|wx.CallLater" gui.py
echo end
```

Expected (nothing after `AC2` until `AC4`; criterion 4 lists only the three lines of `_initialize_conversion_state`):

```text
Ran 190 tests
OK (skipped=2)
characterization tests: 19 at Task 1, 19 now
changed members: ['ConversionExportFlowsCharacterizationTest._wire_conversion']
Ran 753 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 27 (expected 27)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (753)
new tests ok: 84 (expected 84)
new tests not ok: 0
source msgids: 353
SOURCE == SAVED
AC2
AC4
220:			call_after=wx.CallAfter,
221:			call_later=wx.CallLater,
227:			call_after=wx.CallAfter,
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: route export through the export coordinator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: route export through the export coordinator
```

---

### Task 8: Drop the unused import and the file-error parent (spec step 8, M-3 and M-9)

**Files:**
- Modify: `client/tests/test_gui_document_flows.py` (`import inspect`; one test in `FrameViewMethodsTest`)
- Modify: `client/gui.py`

**Interfaces:**
- Produces: `BrailleFrame._show_file_error(self, message, error)` (no `parent`; no caller ever passed one; the box keeps `parent=self`); `gui` imports only `ConversionRequest` from `conversion.service`.

- [ ] **Step 1: Write the failing test.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index f4b8a27..4dcf75b 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 import importlib
+import inspect
 import tempfile
 import unittest
 import zipfile
@@ -3351,6 +3352,19 @@ class FrameViewMethodsTest(unittest.TestCase):
             ],
         )
 
+    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
+        frame = self._make_frame()
+        with patch.object(gui.wx, "MessageBox") as message_box:
+            frame._show_file_error("Failed: {error}", OSError("disk full"))
+
+        message_box.assert_called_once_with(
+            "Failed: disk full", gui._("Error"), gui.wx.OK | gui.wx.ICON_ERROR, parent=frame
+        )
+        self.assertEqual(
+            list(inspect.signature(gui.BrailleFrame._show_file_error).parameters),
+            ["self", "message", "error"],
+        )
+
 
 
 class FrameExportDelegationTest(unittest.TestCase):
PATCH
```

- [ ] **Step 2: Run it to see it fail.**

```bash
$PY -m unittest tests.test_gui_document_flows.FrameViewMethodsTest 2>&1 | grep -E '^(ERROR|FAIL):|^[A-Za-z]*Error:|^Ran|^FAILED|^OK' | sed -E "s#$REPO/##; s/ \(tests\.[^)]*\)//; s/ in [0-9.]+s$//" | LC_ALL=C sort | uniq -c
```

Expected:

```text
      1 AssertionError: Lists differ: ['self', 'message', 'error', 'parent'] != ['self', 'message', 'error']
      1 FAIL: test_show_file_error_formats_the_error_for_the_frame
      1 FAILED (failures=1)
      1 Ran 8 tests
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index b37eb2f..a9d135a 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -11,10 +11,7 @@ from app_paths import ApplicationDataError, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
 from conversion.presenter import ConversionPresenter
-from conversion.service import (
-	ConversionRequest,
-	ConversionStageError,
-)
+from conversion.service import ConversionRequest
 from conversion.preprocessing.user_script import preprocessing_script_path
 from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
 from dictionaries.presenter import DictionaryManagementPresenter
@@ -455,12 +452,12 @@ class BrailleFrame(wx.Frame):
 	def _get_selected_dictionary_path(self) -> Path:
 		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)
 
-	def _show_file_error(self, message: str, error: Exception, parent: wx.Window | None = None) -> None:
+	def _show_file_error(self, message: str, error: Exception) -> None:
 		wx.MessageBox(
 			message.format(error=error),
 			_("Error"),
 			wx.OK | wx.ICON_ERROR,
-			parent=parent or self,
+			parent=self,
 		)
 
 	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
PATCH
```

- [ ] **Step 4: Run the module, acceptance criterion 5 and the suite check.**

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo AC5; grep -nE "\b(ConversionStageError|ConversionOutput|get_public_error_message|ExportContext|ExportBatchResult)\b|conversion\.jobs" gui.py; grep -n "parent: wx.Window | None = None" gui.py
echo end
$T/tools/check_suite.sh 754 85 27
```

Expected (nothing between `AC5` and `end`):

```text
Ran 142 tests
OK (skipped=2)
AC5
end
Ran 754 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 27 (expected 27)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (754)
new tests ok: 85 (expected 85)
new tests not ok: 0
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'MSG'
refactor: drop unused conversion imports and file-error parent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
refactor: drop unused conversion imports and file-error parent
```

---

### Task 9: Final verification (spec acceptance criteria, no commit)

- [ ] **Step 1: Acceptance criteria 1-5 (greps) and the untouched trees of criterion 7.**

```bash
echo AC1; grep -rn "ConversionCompletionPolicy\|ConversionJobRequest" $REPO/client
echo AC2; grep -nE "_start_conversion|_complete_conversion|_finish_conversion_|_start_export_conversion|_export_next_document|_write_export_document|_continue_single_export|_show_export_all_result|_missing_default_table_message|_export_document_with_dialog|_conversion_runner|_convert_dialog_timer|_set_conversion_busy|_show_converting_dialog|_close_converting_dialog|_confirm_overwrite_all" gui.py
echo AC3; grep -nE "^(import wx|from wx)|^(import|from) gui" conversion/presenter.py documents/export_coordinator.py conversion/jobs.py
echo AC4; grep -n "wx.CallAfter\|wx.CallLater" gui.py
echo AC5; grep -nE "\b(ConversionStageError|ConversionOutput|get_public_error_message|ExportContext|ExportBatchResult)\b|conversion\.jobs" gui.py; grep -n "parent: wx.Window | None = None" gui.py
echo AC7; git -C $REPO diff main --stat -- client/locales scripts
echo end
```

Expected (only the three `_initialize_conversion_state` lines under `AC4`):

```text
AC1
AC2
AC3
AC4
217:			call_after=wx.CallAfter,
218:			call_later=wx.CallLater,
224:			call_after=wx.CallAfter,
AC5
AC7
end
```

- [ ] **Step 2: Acceptance criteria 6 and 7 (characterization unchanged; msgid scan, full output).**

```bash
$PY -I $T/tools/char_unchanged.py $REPO $(git -C $REPO log --format=%h --grep='^test: characterize conversion and export flows$' -1)
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json; echo "scan exit: $?"
```

Expected (the same scan result as Task 0: 353 source msgids, only the four known `.pot`-only orphans, `SOURCE == SAVED`):

```text
characterization tests: 19 at Task 1, 19 now
changed members: ['ConversionExportFlowsCharacterizationTest._wire_conversion']
source msgids: 353
pot msgids: 357
only in pot: 'EPUB books (*.epub)|*.epub'
only in pot: 'PDF files (*.pdf)|*.pdf'
only in pot: 'Text files (*.txt)|*.txt'
only in pot: 'Word documents (*.docx)|*.docx'
SOURCE == SAVED
scan exit: 1
```

- [ ] **Step 3: Acceptance criterion 8 (roadmap verification, with the venv interpreter instead of the spec's bare `python3`, which lacks the dependencies here) and the extra modules.**

```bash
$PY -m unittest tests.test_conversion_jobs tests.test_export_coordinator tests.test_conversion_presenter tests.test_gui_document_flows -v 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_menu_builder tests.test_workspace_service 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
Ran 191 tests
OK (skipped=2)
Ran 77 tests
OK
```

- [ ] **Step 4: Acceptance criterion 9 (full suite).**

```bash
$T/tools/check_suite.sh 754 85 27
```

Expected (696 - 27 moved + 85 new = 754; only the known P2-5 failure; `skipped=9`):

```text
Ran 754 tests
FAILED (failures=1, skipped=9)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
baseline tests removed: 27 (expected 27)
NO-UNPLANNED-BASELINE-CHANGES
RAN-COUNT-OK (754)
new tests ok: 85 (expected 85)
new tests not ok: 0
```

- [ ] **Step 5: Acceptance criterion 10 (stub-scope order and shuffled runs).**

```bash
for m in test_conversion_presenter test_export_coordinator; do printf '%s alone: ' $m; $PY -m unittest tests.$m 2>&1 | tail -1; done
printf 'gui, presenter, coordinator: '; $PY -m unittest tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator 2>&1 | tail -1
printf 'coordinator, presenter, gui: '; $PY -m unittest tests.test_export_coordinator tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | tail -1
for s in 1 2 3 4 5; do $PY -B -I $SP/shuffle_harness.py $s tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_menu_builder tests.test_workspace_service | head -1; done
for s in $(seq 1 10); do $PY -B -I $SP/shuffle_harness.py $s | grep '^BAD'; done | LC_ALL=C sort -u | LC_ALL=C comm -23 - $T/known_order_bad.txt
echo "end of unknown BAD lines"
```

Expected (the touched modules are clean alone, in both orders and in every shuffled order; the full shuffled runs show no `BAD` line outside the baseline's known set, spec correction 4):

```text
test_conversion_presenter alone: OK
test_export_coordinator alone: OK
gui, presenter, coordinator: OK (skipped=2)
coordinator, presenter, gui: OK (skipped=2)
seed=1 ran=268 failures=0 errors=0 skipped=2
seed=2 ran=268 failures=0 errors=0 skipped=2
seed=3 ran=268 failures=0 errors=0 skipped=2
seed=4 ran=268 failures=0 errors=0 skipped=2
seed=5 ran=268 failures=0 errors=0 skipped=2
end of unknown BAD lines
```

- [ ] **Step 6: The commits and the final tree.**

```bash
git -C $REPO log --format=%s main..HEAD
git -C $REPO diff main --stat -- client
sha256sum gui.py conversion/presenter.py documents/export_coordinator.py conversion/jobs.py
```

Expected:

```text
refactor: drop unused conversion imports and file-error parent
refactor: route export through the export coordinator
refactor: add the wx-free export coordinator
refactor: keep completion state out of conversion jobs
refactor: route conversion through the presenter
refactor: add the wx-free conversion presenter
test: pin the conversion job runner contract
test: characterize conversion and export flows
docs: plan export and conversion presenters
docs: spec export and conversion presenters
 client/conversion/jobs.py                 |   36 +-
 client/conversion/presenter.py            |  209 ++++
 client/documents/export_coordinator.py    |  174 +++
 client/gui.py                             |  408 ++-----
 client/tests/conversion_harness.py        |  108 ++
 client/tests/test_conversion_jobs.py      |  160 ++-
 client/tests/test_conversion_presenter.py |  446 +++++++
 client/tests/test_export_coordinator.py   |  517 ++++++++
 client/tests/test_gui_document_flows.py   | 1854 ++++++++++++++++++++---------
 9 files changed, 2963 insertions(+), 949 deletions(-)
b9eca92c6e3b0437048600a8907ebf99c282e2ba41438abf3b3bf1aa1094837b  gui.py
914a4630fac2be9ec8a42c41fdeba40d1230625e4915ec6955176958f4c0d9cb  conversion/presenter.py
51338d37de49821c593acd50e95e109cabcdbe945975c0f0d0db2e09d9abb597  documents/export_coordinator.py
b17fc539af3e6b6963e7a5b8568d07a25b94c32235723bff9feb4b746981fd75  conversion/jobs.py
```

- [ ] **Step 7: Report.** List the eight commits, the commands above with their results, the spec corrections, and the Windows verification debt below as not run.

## Windows verification debt (not possible on this Linux host)

- On a packaged build, before and after: Convert a short text and a long one (the "converting" dialog appears only after 2 s and closes on completion; the File and Translation menus, the document list and the source editor are disabled meanwhile; the Help menu and the Braille Result editor stay enabled); a conversion error (wrong table) with its message; closing the window during a long conversion (vetoed).
- Export (DEP, BRL, HTML) of a converted and of a pending document; Ctrl+S in the Braille Result editor; Export All with a mix of pending and converted documents, with existing files (overwrite question, both answers), and with a read-only target file (partial summary). The directory-as-target faults of the tests raise `PermissionError` on Windows instead of `IsADirectoryError`; the tests compute the expected text from the same write, so they hold there too.
- With the zh_TW catalog: all messages above in Chinese as before (and the Export All summary in English, known defect 4).
- Known defects 1 and 2 behave as before (Ctrl+Tab and Ctrl+S during a long conversion).
- Real threads, `wx.CallAfter`, `wx.CallLater`, `ConvertingDialog`, `EnableTop` and message boxes run only in the packaged app; the tests use fakes for all of them.
- No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed for this task.
