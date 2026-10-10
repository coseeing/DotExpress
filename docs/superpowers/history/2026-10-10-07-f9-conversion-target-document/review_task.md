# F-9 Conversion Results Go to the Right Document review record

- Date: 2026-10-11. Written in English at the orchestrator's request (HANDOFF section 1 says Traditional Chinese; the fix record may follow either).
- Scope: worktree `D:\workspace\DotExpress-f9`, branch `fix/f9-conversion-target-document`, range `7aba2be..HEAD` (8 commits: `a39d207` spec, `e05e0ce` plan and spec corrections, `3ec0e95` D7, `dd25bcc` D6, `33fc5ed` D4/D5, `4347c5a` D8, `b18112e` D1-D3/D9, `eba7188` GUI record). Production diff: `client/ui/conversion_presenter.py` +144/-38, `client/conversion/jobs.py` +11, `client/documents/export_coordinator.py` +29/-10, `client/documents/workspace_service.py` +18/-4, `client/gui.py` +11; tests: `test_conversion_presenter.py` +364, `test_gui_document_flows.py` +373, `test_export_coordinator.py` +68, `test_workspace_service.py` +59, `test_conversion_jobs.py` +35, `test_i18n.py` +9; catalogs `.pot`/`.po`/`.mo`; spec (EN and zh-TW, 526 lines each), plan (4866 lines), `auto-results.md` and three `auto/` scripts. 21 files, exactly the spec's "Design per File" plus the test, catalog and document files (acceptance 7). `HEAD:client` is `2fffcc5e1cefbfe656061f1c477dcdaadd00115a`, the plan's Task 5 tree id.
- Read against: spec `docs/superpowers/specs/2026-10-10-f9-conversion-target-document-design.md` (D1-D9, "Corrected after planning (F-9)" 1-14, behavior table, Test Plan A-E, acceptance 1-9, Windows items 9a-9i, Risks, O1-O11), plan `docs/superpowers/plans/2026-10-10-f9-conversion-target-document.md` (overview, mutant list, Implementation Notes), `auto-results.md`, HANDOFF sections 1-2, `AGENTS.md`, the F-8b review record (format).
- Method: line-by-line reading of the five production diffs plus the surrounding code (`BrailleFrame` close, switch, import, Ctrl+S, busy, menu layout, `OnExit`; `ConversionJobRunner`; `DocumentController`; `DocumentWorkspaceService`; `ExportCoordinator`; `ConvertingDialog`; `message_box`; `log.get_logger`; `TranslationRuntime.close`); the six test diffs; the catalog diffs; the full suite on Windows 11; 16 self-written mutants on a scratch copy of `HEAD:client` (`git archive` plus the git-ignored liblouis runtime and `mathcat/`, under the session scratchpad `f9review\`); one GUI probe of the keyboard focus on a fresh copy of `D:\dxtest\N-f9` in `D:\dxtest\auto85-f9review` (item 85's flow); the 19 `D:\dxtest\auto8*-f9*.log` / `auto9*-f9*.log` files and the exe hash. No clipboard access anywhere (the probe sends Ctrl+Enter and Ctrl+Tab only, through `f9gui.keys`, which sends a key only while the main window is the foreground window). Nothing was staged or committed; the worktree's `git status --short` is empty and it has no `client/log/`, `client/workspace/` or `client/config.json`; the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 as in the F-8b review (table below). Statements that could not be measured are marked "reasoning" or "hypothesis".
- This record is written to disk only, not committed.

## Verification (Windows 11 26200, `$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`, `$SP` = session scratchpad `f9review\`)

| Item | Command | Result |
| --- | --- | --- |
| app data (main checkout) | `(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum` | 4 files: `config.json` `508a65ea...`, `dictionary/default.csv` `8f0594e9...`, `log/init.log` `9c153f43...`, `workspace/new.dep` `a2f2a7f1...`; identical to the F-8b review's values; mtimes 20:02-20:07 predate this review |
| full suite (acceptance 1) | `cd D:\workspace\DotExpress-f9\client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1478 tests`, `FAILED (errors=1, skipped=7)`; the only error is F-W6 `test_case_only_rename_still_renames`. 1478 = 1444 + 34, as "Corrected after planning" 1 and the plan's Implementation Notes |
| focused modules (acceptance 2, scratch copy) | `$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows` | `Ran 363`, `OK`; no `log/` folder created |
| catalogs (acceptance 4) | `msgfmt --check --statistics -o $SP/fresh.mo ...dotexpress.po`; `sha256sum` of both `.mo`; `grep -c '^msgid '`; `grep -c '^#, fuzzy'`; `git diff 7aba2be..HEAD -- client/locales` | 369 translated, 0 fuzzy, 370 `msgid` lines (369 + header); the freshly compiled `.mo` is byte-identical to the committed one (`b14647d5...`); the `.pot` and `.po` diffs add exactly the one entry with `#, python-brace-format` and refresh `#:` lines; `POT-Creation-Date` `2026-10-10 12:00+0800` in both; `msgmerge` did not fuzzy-match it (0 fuzzy) |
| commits | `git log --oneline 7aba2be..HEAD`; `git diff --stat` | eight commits, no merge; 21 files as listed above; `gui.py` changes are the two of "Design per File" (tab-indented) and nothing else |
| GUI record audit | the 19 logs in `D:\dxtest\`; `sha256sum D:\dxtest\N-f9\DotExpress.exe` | every key line of `auto-results.md` matches its log verbatim (85/87 D2 box content, 88 the `[WinError 5]` error box and no completion box, 89 the two boxes in order, 93 `WM_QUERYENDSESSION` result 0 within 2 s and `WM_ENDSESSION` exit code 0 on N-f9; `-1073740940` on the first N-f8b2 run, 0 on `auto93b`); 89/90 on N-f8b2 "the app has ended by itself"; exe `5de1acdb...`, 48,767,217 bytes, as recorded; each `auto*-f9` folder has one log |
| mutants (16) | `$PY -B -X utf8 $SP\mutants.py $SP\copy\client $PY` (one edit per mutant, old text exactly once, CRLF kept, restored and byte-compared afterwards) | 10 caught, 6 survived (r1, r2, r3, r8, r10, r13); r8/r10/r13 are equivalent mutants; r1-r3 are findings M-1 to M-3: section 2.2 |
| focus probe | `$SP\uia\Scripts\python.exe $SP\focus_probe.py D:\dxtest\N-f9\DotExpress.exe D:\dxtest\auto85-f9review` (`GetGUIThreadInfo` of the app's UI thread at each step) | section 2.1; the app closed with `exited`, no process left |
| not run | - | item 94 (NVDA, the user's); POSIX-only tests (7 skips); F-W6; the plan's shuffle seeds and its 30 mutants (replayed by the implementation, Implementation Notes) |

## Conclusion

**Ready to merge after the cheap Minor fixes.** No Critical and no Important finding. The queue (D4) is sound: one worker at a time, FIFO, requests built at submit time, the drain in `finally`, nothing starts while a completion or its modal box is in progress; `is_running()` (D5) covers the delivery gap and the queue, so a vetoable close is vetoed there; every worker outcome is delivered once (D7); `shutdown()` (D8) makes a late delivery a no-op and refuses new jobs. A manual result goes to the document recorded at submit time (D1), through the same atomic package write and F-5 fingerprint as every save; the guard (D3) is a safety net that nothing in today's UI can trigger (the list, both menus with Rename, Delete, Delete All, Settings and Dictionary Management, and the source editor are disabled while a job is active, and between completion and the next queued start no event is processed). I found no path where a result is written to the wrong document, written twice, written after a rename/delete/Delete All, or lost other than by design (shutdown) or by a reported save failure (M-5). HTML export of a pending document uses the fresh segments without touching the cache or the document (D6). The one new string is translated, brace-format-flagged, and the `.mo` is in sync. The GUI record is consistent with its logs and the build hash.

Nine Minor findings: M-1 to M-4 are test gaps found by surviving mutants or by reading (cheap); M-5 to M-7 are spec accuracy items (the focus after the D2 box, the fate of a result whose save failed, O10's wording); M-8 is a pre-existing exit-time hazard that F-9's spec already lists as a risk, with a cheap mitigation and a hypothesis about its cause; M-9 is a message that does not name the document. None blocks the merge.

## 1. Path analysis

### 1.1 Queue and delivery (D4, D5, D7, D8)

| Question | Result | Basis |
| --- | --- | --- |
| Two liblouis conversions at once | Impossible from the presenter: `_start` runs only from `_submit` when `_active is None and not _completing and not _queue`, or from `_finish_completion` after the previous job's completion returned; `_active` stays set from `_start` until `_take_active` in the delivery turn, so a worker that has ended but is not yet delivered still blocks. No other liblouis caller exists outside `conversion/` (grep for `louis.`, `translation_runtime`, `convert_text_with_alignment`, `translate_with_language`): the Dual View renders the cache, `apply_settings_from_dialog` touches only the tables dict, and Settings and Dictionary Management sit under the Translation menu, which is disabled while busy | `conversion_presenter.py:186-211`, `gui.py:246-262`, `gui.py:1108-1116`; GUI 89/90 (the N-f8b2 crash is gone) |
| Result to the wrong document | (a) needs `target.document_name == open_document_name`; the same name can be a different document only after Delete+Import or Rename of another document to that name, both unreachable while busy. (b) writes to the name recorded at submit time; the guard rejects a vanished name or another text | `conversion_presenter.py:277-307`; B1, B2, B4, B5, E1-E3; GUI 85-87 |
| Result lost | By design after `shutdown()` (D8) and in the discard cases (D3, unreachable). After a failed (b) save: kept in memory and the cache, written by the next save of that document, which only happens if the user opens it again (M-5) | `conversion_presenter.py:302-307`, `workspace_service.py:196-211`; E4; GUI 88 |
| Result written twice | (b) writes once and `_remember`s; opening the target and switching away compares equal (`_is_saved`) and writes nothing (D1 test "does not write it again", mutant r5 caught). (a) writes nothing at completion, as before | `workspace_service.py:203-211`; D1; E2 |
| Written after rename / delete / Delete All | Unreachable while a job is active (list and File menu disabled; no accelerators for those commands, `ui/menu_builder.py`). If it happened anyway: `get_document(target)` is `None`, discard, log; nothing written. A rename is not followed (O2) | B4 (three subTests); reasoning for reachability |
| Written after the F-8b startup recovery | Recovery runs once in the constructor before any conversion; a recovered document is an ordinary listed document by then. A crash between the (b) write's `.tmp` and `os.replace` leaves a class-L4 leftover (name taken, content unique) that F-8b keeps; a crash after the replace leaves nothing. No interaction | reasoning; F-8b review section 7 |
| Text changed after the start | The only writer of the target's text while busy is the switch-away / import save, which stores `_encodable(_editor_text(input_txt))`; the job stores `replace_lone_surrogates(input_txt.GetValue())`; `_encodable` applies the same function, idempotent; the source editor is disabled meanwhile. E14 pins it with a lone surrogate; GUI 85 (520,000 characters with newlines) passed the guard on a real `wx.TextCtrl` | `gui.py:636-644`, `workspace.py:95-98, 319-326`; E14 |
| Thread safety | The worker touches only the frozen request, the runtime and `wx.CallAfter`; `self._thread`, `_active`, `_queue`, `_completing` are written on the UI thread only. D7's `get_logger` from the worker: `gui.py:100` already created the handler at import, so the `if not logger.handlers` branch never runs on the worker in the packaged app; logging's handler lock covers the write (reasoning) | `jobs.py:69-94`, `log.py:11-31` |
| Delivery after close | `_finish_close` -> `shutdown()` before `close_converting_dialog()`; a later `wx.CallAfter` runs `_deliver_success` (sets `_thread = None`) -> `_on_job_success` -> `_take_active` returns `None`. No view call. The stopped `wx.CallLater` never fires; `_show_converting_dialog` also checks `_shut_down` | `gui.py:1092-1101`, `conversion_presenter.py:213-231`; B14, E11, E12 |
| `WM_QUERYENDSESSION` while running | wx turns it into a vetoable close; `_close` vetoes while `is_running()`; the query returns 0 at once (GUI 93, within 2 s). `WM_ENDSESSION`: no close event (F-7 item 60); the process ends. See M-8 for the exit code | GUI 93 |
| Close during a completion box | `is_running()` is `False` during `_completing` with an empty queue (D5, O8, pinned by B13 and mutant r12). A posted `WM_CLOSE` then closes the frame under the modal box, as before F-9 (F-7 territory); a queued job keeps the veto | reasoning; B13 |
| Modal boxes and re-entrancy | `_completing` makes a `convert_for_export` issued from inside a completion (an Export All step whose `CallAfter` runs inside the modal loop, if wx processes pending events there) queue instead of start; if wx does not process them inside the native task dialog, the step runs after the box with `_completing` already `False` and starts directly. Both orders are correct; the test B10 pins the first | `conversion_presenter.py:186-196`; B10; GUI 90 order |
| A completion that raises | `finally` drains; the exception propagates to `wx.CallAfter` (logged by wx, invisible in the packaged build). Pinned for the success path (B11), not for the failure path (M-2) | `conversion_presenter.py:247-275` |
| `_build_request` raising | Queued path: at submit, propagates to the caller (`_export_next` or `convert`), nothing queued. Direct path: inside `_start` after `set_conversion_busy(True)`, as before F-9. Not a regression | reasoning |

### 1.2 Interaction with the frame

| Path | Result | Basis |
| --- | --- | --- |
| Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+PageUp / PageDown while busy | `_open_adjacent_document`: save (editor text, pending stays pending), open, `input_txt.SetFocus()`. The source editor is disabled, so the `SetFocus` is a no-op and the focus stays in the Braille Result editor (measured, section 2.1). The user can read the other document, not edit it | `gui.py:627-634`; probe |
| Ctrl+O while busy | `on_import_document`: save, import, open the one imported document (pending). (b) then saves the starting document | `gui.py:918-946`; E3; GUI 87 |
| Ctrl+S in the Braille Result editor while busy | `on_output_text_key_down`: save, `export_document` (file dialog), then `convert_for_export` queued for a pending document, or a direct write for a converted one (probe 7, unchanged). After the manual completion the queued export converts the same text again (the request was built at Ctrl+S time; the captured `Document` is the pending one) and writes the file: correct, one extra conversion | `gui.py:986-995`; E5-E7; GUI 89/90 |
| Ctrl+S then Ctrl+Tab | manual (b) saves `alpha.dep`, D2 box; then the queued export writes `alpha.brl`. Not pinned by a test but follows from B1 + B7 | reasoning |
| F-8a atomic writers and the unlisted-`.dep` rule | `save_document` writes the listed document's own package through `save_document_package` (temp file + `os.replace`); the "never replace an unlisted package" rule applies to Add/Rename/Import/default, not to a save of a listed name, so the behaviour equals `save_open_document` (whose body it now is). `_is_saved` skips an unchanged write | `workspace_service.py:189-211`; D1-D5 |
| (b) save failure (item 88) | `save_document` has replaced memory and set the cache before the write raises; the frame shows "Failed to save document: {error}" (the `OSError` text names the `.tmp` and the package path on Windows); no completion box; `_saved[alpha]` stale. Opening `alpha` shows the braille; the next save of `alpha` (switch away from it, or close while it is open) writes it (GUI 88). Closing the app from another document drops it: the close saves only the open document (M-5) | `gui.py:1146-1153`, `gui.py:654-668`; E4; GUI 88 |
| Dual View | (b) does not call `refresh_dual_view`; the viewer keeps the open document's data; switching to the target refreshes from the cache set in (b) | `gui.py:602-613`; E1 |
| Export All step after a non-vetoable close | `_submit` returns (O10) for a pending document, so the chain stops silently. For a document with braille the step still writes the file and the last step calls `show_info` on the destroyed frame (`RuntimeError` inside `wx.CallAfter`, invisible). Reachable only through a close that cannot be vetoed while a chain is between steps; no such close exists today (`WM_ENDSESSION` gives no close event; `_on_close_reentered`'s non-vetoable branch needs a non-vetoable second event). Pre-existing; M-7 | `export_coordinator.py:157-203` |

### 1.3 HTML export of pending documents (D6)

`write_document(..., dual_view_results=None)` reads the cache; a tuple is used as given, also `()`. The single export and each Export All step pass `output.dual_view_segments` for a pending document only; converted documents keep the cache. Nothing writes the segments into the cache or the document (C1, C2, E9; GUI 91 `pend.html` 23 segments, cache and `pend.dep` unchanged). The empty-segments fallback (mutant r10) is equivalent: a pending document never has a cache entry. HTML export of a converted document after a restart stays "No conversion data" (Out of Scope, unchanged).

### 1.4 Localization (D2, D9)

| msgid | msgstr | Reading |
| --- | --- | --- |
| `Conversion completed. The result was saved to document "{name}".` | `轉換完成。結果已儲存到文件「{name}」。` | natural Taiwan usage; `{name}` identical; the quotation marks follow `Document "{name}" already exists.` (`文件「{name}」`); `儲存` follows `Cannot Save Document` (`無法儲存文件`); `轉換` is the app's term for the command (F-8b M-5). `#, python-brace-format` present in `.pot` and `.po`; F1 checks the compiled `.mo` with `.format(name="alpha")` |

The task dialog shows it as content with no main instruction (`main: None` in GUI 85/87): NVDA reads the caption `資訊` and the full sentence with the name.

## 2. Probes and mutants

### 2.1 Focus probe (`$SP\focus_probe.py`, N-f9 copy in `D:\dxtest\auto85-f9review`, item 85's flow)

| Step | Focus (UI thread, `GetGUIThreadInfo`) |
| --- | --- |
| start, `alpha` open | source editor (enabled) |
| after Ctrl+Enter | Braille Result editor (the source editor was disabled; wx moved the focus) |
| after Ctrl+Tab to `beta` | Braille Result editor of `beta` (`input_txt.SetFocus()` in `_open_adjacent_document` fails on the disabled control) |
| 2 s later, converting dialog | the dialog's static text; the dialog is the foreground window (`STAY_ON_TOP`, `Raise()`) |
| D2 box | `{'title': '資訊', 'main': None, 'content': '轉換完成。結果已儲存到文件「alpha」。', 'buttons': ['確定'], 'focus': '確定'}` |
| after Enter | Braille Result editor of `beta` (read-only), enabled; `beta`'s editors unchanged |
| Ctrl+Tab back to `alpha` | source editor (enabled now); the Braille Result editor shows alpha's braille |

So the spec's "normally the source editor of the newly opened document" (D1 "Focus", line 154) is not what happens: the focus is in the read-only Braille Result editor, before and after the box. Before F-9 it was there too (the completion then focused the output editor explicitly), so this is not a regression; see M-6.

### 2.2 Self-written mutants (`$SP\mutants.py`; the five F-9 modules; unmutated `Ran 363`, `OK`)

```text
r1  _on_job_failure does not set _completing ..................... SURVIVED  (M-1)
r2  _on_job_failure drains only on a normal return (no finally) ... SURVIVED  (M-2)
r3  a queued manual job is stored without its target ............. SURVIVED  (M-3)
r4  _finish_close shuts down only when is_running() .............. caught (FrameConversionDelegationTest, incidentally through the Mock call list)
r5  save_document does not _remember the write ................... caught (4 tests)
r6  save_document updates memory only after the write ............ caught (10 tests)
r7  the target is the selected, not the open, document ........... caught (4 tests)
r8  (b) stores target.source_text instead of document.text ....... SURVIVED, equivalent under the guard
r9  export callback gets display_text ............................ caught (15 tests)
r10 empty fresh segments fall back to the cache .................. SURVIVED, equivalent (a pending document has no cache entry)
r11 the runner delivers the raw error, not a ConversionStageError  caught (A1, A2)
r12 is_running() also covers a completion in progress ............ caught (B13)
r13 the drain runs before _completing is cleared ................. SURVIVED, equivalent (nothing submits during _start)
r14 (b) sets the cache only after a successful save .............. caught (B3)
r15 the discard log line drops the reason ........................ caught (5 tests)
r16 shutdown() does not set _shut_down ........................... caught (B14)
```

The plan's 30 mutants (all caught per the Implementation Notes) cover acceptance criterion 8; r1-r3 are outside that list.

## 3. Tests, logging, isolation

- Red-first: each plan task names its red reason (missing `shutdown`, superseded job, `AttributeError` on `save_document`, the escaping worker exception, the "No conversion data" page); the counts 1444 -> 1445 -> 1450 -> 1459 -> 1461 -> 1478 and the tree ids are the plan's (Implementation Notes 1).
- `test_conversion_jobs` and `test_conversion_presenter` now isolate `dotexpress.gui` in `setUpModule`; the D3 and D7 tests use `assertLogs(level="ERROR")` and check the message and `exc_info` identity; the worktree and the scratch copy have no `log/` after the runs.
- The frame tests compare boxes without the frame object (`_boxes`), run jobs to exhaustion (`_finish_jobs`), and drive Ctrl+O through a fake `wx.FileDialog`; E14 writes the lone surrogate as a `LONE_SURROGATE` constant (HANDOFF section 2).
- Assertions are event-list equalities, so the order busy-off -> box -> next busy-on is pinned (B7, E5, E8). The `timer.Stop` numbering pins that each job has its own timer.
- Gaps: M-1 to M-4.

## 4. Spec, plan, record, process

- Spec D1-D9, the behavior table, "Corrected after planning (F-9)" 1-14, Test Plan A-E and acceptance 1-8 all have matching code and tests; the counts (34 new, 5 flipped; 1478; 369 msgids) are the committed ones. "Design per File" matches the diff exactly: `gui.py` has only `save_converted_document` and the `shutdown()` call; `_close` still asks `is_running()`.
- Corrections 4 (ERROR, not WARNING) and 5 (no new job after `shutdown()`) are in the code; the spec body (D3, O3) still says WARNING with the correction appended rather than edited, which is the project's convention.
- The plan's Implementation Notes record the tree ids, the build and the one GUI re-run; `auto-results.md` lists the build hash, the 18 matching logs, the `auto93b` re-run with its reason, the pre-existing observations, and item 94 as the user's manual item, unticked.
- HANDOFF section 2 constraints: no restricted file touched; fixtures not in the range; `AGENTS.md` not in the diff; `POT-Creation-Date` pinned; commit trailers present; no push.
- Spec statements that need an edit (section 6): D1 "Focus" (M-6), D1 "Why write at once" last sentence and the Risks bullet "A new disk write" (M-5), O10 (M-7), optionally Risks "Ending the process while a conversion runs" (M-8). The zh-TW twin has the same sentences.

## 5. Defaults O10 and O11

- **O10** (no new job after `shutdown()`): sound. Without it an Export All step's `CallAfter` that runs after the close would call `set_conversion_busy` and `close_converting_dialog` on a destroyed frame. The wording "does nothing" is true only for a pending document's step; a converted document's step still writes its file and the last step shows the summary on the destroyed frame (M-7). Not reachable today.
- **O11** (discard logged at `ERROR`): sound. `dotexpress.gui` and its `gui.log` handler are bound at `ERROR` (`log.py:14`), so a `WARNING` would be dropped; the event is a safety-net violation that support should see. The level name overstates it slightly; the alternative (a configurable logger level) is out of scope.

## 6. Findings

### Critical

None.

### Important

None.

### Minor

**M-1 The failure completion's `_completing` is not pinned** (`client/ui/conversion_presenter.py:262-275`; mutant r1 survives)
- Scenario under the mutant: an `on_error` callback that submits a job synchronously (none does today; `conversion_failed` defers through `call_after`) would start it inside the failure completion, before the error box of a single export closes, and a second box could open on top of the first, the case D4 excludes for the success path. The shipped code is correct; the pin is missing.
- Suggested fix (cheap): a failure twin of B10, `test_request_during_a_failed_completion_waits_until_it_returns`: an `on_error` that calls `convert_for_export`; expect `build_request` and the callback's return before `busy True`.

**M-2 The failure path's drain-in-`finally` is not pinned** (`client/ui/conversion_presenter.py:268-275`; mutant r2 survives)
- Scenario under the mutant: `show_error` or an `on_error` callback raising (a destroyed window, a bug) leaves `_completing = True` and the queued export never starts; `is_running()` stays `True` and every later close is vetoed with no message, until a restart. The shipped code drains in `finally`.
- Suggested fix (cheap): a failure twin of B11, `test_queue_drains_when_a_failed_completion_raises`.

**M-3 A queued manual job's completion is never exercised** (`client/ui/conversion_presenter.py:194`; mutant r3 survives; B12 queues a manual job through `first_done` but never runs its worker)
- Scenario under the mutant: a manual job queued during a completion (only possible from a `CallAfter` that runs inside a completion, not from the user today) would complete with `target is None` and raise `AttributeError` in `_complete_manual`, leaving `_completing` cleared by `finally` but the busy state on. The shipped code stores the target.
- Suggested fix (cheap): extend B12 to run `threads[2]` and `calls.run_next()` and assert today's manual completion events for `alpha`, or add `test_queued_manual_job_keeps_its_target`.

**M-4 Ctrl+S followed by Ctrl+Tab during a manual conversion has no test** (`client/tests/test_gui_document_flows.py`, `ConversionExportFlowsCharacterizationTest`; E5 and E1 cover the two halves separately)
- Scenario: Convert `alpha` (pending), Ctrl+S (export queued with the pending `Document`), Ctrl+Tab to `beta`. Expected: (b) writes `alpha.dep` and shows the D2 box, then the queued export converts again and writes `alpha.brl` with "Export Complete". The code does this by B1 + B7 (reasoning), but the combination of a queue and a switch is the new surface and deserves one pin.
- Suggested fix (cheap): one frame test, `test_ctrl_s_then_ctrl_tab_during_manual_conversion`, asserting the box order, `alpha.dep` and `alpha.brl`, and `beta` untouched.

**M-5 A result whose (b) save failed is lost when the app is closed from another document** (`client/ui/conversion_presenter.py:302-307`, `client/gui.py:654-668`; spec D1 "Why write at once" line 149, Risks line 489)
- Scenario: as item 88 (`alpha.dep` locked at completion): the error box appears, the result stays in memory and the cache. The user keeps working in `beta` and closes the app from `beta`: `_save_open_document_before_close` saves `beta` only; `alpha.dep` stays pending; the result is gone without a second message. (The text is safe and the conversion can be repeated.) The spec says "the next save of that document (open it, then switch away) retries the write, as F-5 retries any failed save" but not that there is no retry at close unless `alpha` is the open document; F-5's close dialog does not cover it.
- Suggested fix (cheap, documentation): say so in D1 and in the Risks bullet, EN and zh-TW, and in the behavior table row "`alpha.dep` cannot be written at completion". Code alternative (not cheap, F-5 scope): have the close path also save documents whose memory differs from their saved record, with the F-5 dialog; a candidate for F-12 if the user wants it.

**M-6 The spec's focus statement is wrong: after the D2 box the focus is in the read-only Braille Result editor, not the source editor** (spec D1 "Focus", line 154, and its zh-TW twin; `client/gui.py:634` `input_txt.SetFocus()` on a disabled control; measured in section 2.1)
- Scenario (accessibility): an NVDA user converts `alpha`, presses Ctrl+Tab, hears `beta`'s title, then `資訊 轉換完成。結果已儲存到文件「alpha」。`, presses Enter, and is in `beta`'s Braille Result editor (read-only): typing does nothing until Shift+Tab or F6. Before F-9 the focus ended in the same editor (the completion focused the output), so this is not a regression; item 94 point (1) asks the user to report where the focus is, and the answer will be "the Braille Result editor".
- Suggested fix (cheap for the spec; moderately cheap for the code): correct the sentence to "the Braille Result editor of the newly opened document, where the switch left it because the source editor was disabled". If the user prefers the source editor: in `set_conversion_busy(False)`, when the focus is in `output_txt` and a switch happened while busy, call `input_txt.SetFocus()`; or make `_open_adjacent_document` and `on_import_document` remember the failed focus request and replay it when busy ends. Case (a) must keep focusing the output. Needs one frame test and a re-run of GUI 85/87.

**M-7 O10 is stated too broadly** (spec "Corrected after planning" 5 and O10, line 516; `client/documents/export_coordinator.py:183-186, 162`)
- Scenario: a close that cannot be vetoed arrives between two Export All steps (no such close exists today, see 1.2 last row). The next step's `CallAfter` runs after the frame is destroyed: for a pending document `_submit` returns (O10 as stated); for a document with braille `write_document` still writes the file and, if it was the last, `show_info` runs on the destroyed frame. Harmless in practice, but O10 says "an Export All step that runs after the close does nothing".
- Suggested fix (cheap): reword O10 to "no conversion starts; a step that needs no conversion still writes its file (pre-existing, unreachable today)". Optional code (cheap): `ExportCoordinator` could take a `closed` predicate; not needed now.

**M-8 Exit while a worker is inside liblouis: `OnExit` frees liblouis under the running thread** (`client/gui.py:1227-1236` `runtime.close()` -> `louis_helper.terminate()` -> `lou_free()`, `client/braille/louis_helper.py:149-157`; spec Risks line 496; `auto-results.md` observation 1; pre-existing, not in F-9's diff)
- Scenario: `WM_ENDSESSION` during a conversion. wx sends no close event (F-7 item 60); if it ends the main loop on that message, `BrailleApp.OnExit` runs and calls `lou_free()` while the daemon worker is inside `lou_translateString`. The exit code `-1073740940` (`0xC0000374`, heap corruption) seen once in five dry-run attempts and once on N-f8b2 (`auto93-f8b2-f9`) is what a free under a running translation would give. Hypothesis, not measured (verifying it needs a build with the change, or a log line in `OnExit`). No data is at risk: the open document was saved before, and the result is dropped as the spec says.
- Suggested fix (cheap, 3 lines, outside F-9's files): in `OnExit`, skip `runtime.close()` when a conversion thread is still alive (expose `ConversionJobRunner.is_running()` through the presenter, or keep a flag), since the process is ending anyway. Can be deferred to F-12 with a note in the spec's Risks bullet naming the suspected cause.

**M-9 A failed manual conversion whose document is no longer open reports no document name** (`client/ui/conversion_presenter.py:272-273`; existing string "Translation failed: {error}")
- Scenario: Convert `alpha`, Ctrl+Tab to `beta`, the conversion fails (missing table file, text processing error). The user on `beta` reads "Translation failed: ..." and may take it for `beta`. The spec's "What Stays Identical" keeps every message, so this is by design for F-9.
- Suggested fix: not cheap under the string policy (a new msgid, catalogs, F1-style test, GUI re-run); record it for F-12 next to the Export All summary strings.

## 7. Other observations (no action)

1. **Focus during the conversion.** The converting dialog (`STAY_ON_TOP`, `Raise()`) takes the foreground and the focus 2 s after Ctrl+Enter, also when the user has switched to another document; when the job ends the dialog is destroyed and the focus returns to the frame. Pre-existing; item 94 will tell whether NVDA reads it twice.
2. **Ctrl+S during a manual conversion of a pending document converts the text twice** (the manual job, then the queued export). Correct and documented by the behavior table; about 15 s more on a 520,000-character text.
3. **The manual completion can run inside the export file dialog.** Ctrl+S opens the Save dialog; if the manual conversion ends while it is open and wx processes the pending `CallAfter` there, the "Conversion completed." box appears over the file dialog. Pre-existing; GUI 89 answers the dialog before that.
4. **`convert()` while a job is queued** returns silently, as before (D4 "Manual Convert stays as today"); reachable only in an Export All gap through the Translation menu, where nothing is queued.
5. The GUI scripts send keys only while the main window is the foreground window (`f9gui.keys`); the focus probe reused them unchanged. `D:\dxtest\auto85-f9review` holds the probe's copy and its workspace; no other `D:\dxtest` folder was created or changed; no process was ended except the probe's own.
6. The review tooling (`$SP\mutants.py`, `$SP\focus_probe.py`, the scratch copy, the fresh `.mo`) stays in the session scratchpad.

## 修正記錄 (disposition, 2026-10-11)

Fixed test first on `fix/f9-conversion-target-document` (worktree `D:/workspace/DotExpress-f9`). Commits: `e2a6e6e` (M-1, M-2, M-3), `f226557` (M-4), `f755e3c` (M-6, `HEAD:client` `a64da653f7348440a9a8b7419cb9aaea1e7a3440`), `38cefef` (spec, EN and zh-TW: M-5, M-6, M-7, M-8, M-9; "Corrected after review (F-9, 2026-10-11)"), `969b069` (GUI re-run record, `auto/focus_check.py`, plan Implementation Notes, fix phase), and this record. Full suite at `f755e3c`: `Ran 1483` (1478 + 5), `FAILED (errors=1, skipped=7)`, F-W6 only; the acceptance-criterion-2 set `Ran 368`, `OK`. Fixture sha256s unchanged; no `client/log/`, `client/workspace/` or `client/config.json` in the worktree.

| Finding | Disposition |
| --- | --- |
| M-1 | Fixed: `test_request_during_a_failed_completion_waits_until_it_returns`. Mutant r1 survives without it and fails only this test with it. |
| M-2 | Fixed: `test_queue_drains_when_a_failed_completion_raises` (also runs the queued job to its completion). Mutant r2: survives without, caught by this test only. |
| M-3 | Fixed: `test_queued_manual_job_keeps_its_target` (a Convert asked for inside an export completion queues with alpha as its target; after a switch to beta the result is saved to alpha). Mutant r3: survives without, caught by this test only (`AttributeError`). |
| M-4 | Fixed: `test_ctrl_s_then_ctrl_tab_during_manual_conversion` (boxes D2 for alpha then Export Complete; two conversions of alpha's text; `alpha.dep` and `alpha.brl` hold the braille; beta untouched). The review had no mutant for it; a new one, r17 (a saved case (b) result clears the queue), survives every other test and is caught by this one. |
| M-5 | Spec only (EN and zh-TW): D1 "Why write at once", the behavior table row, Risks "A new disk write", "Corrected after review" 2, and an Out of Scope line (saving such a document at close is F-5 scope, for F-12). |
| M-6 | Code. After a case (b) box (the D2 message or the save error) the presenter calls the new `ConversionView.focus_source_editor()`; the frame focuses `input_txt` only while `IsActive()`, so a file dialog or another program keeps the focus. Small (twelve added lines, eight without blanks and comments; no new string; catalogs refresh only their `#:` lines, `.mo` byte-identical) and pinned by B1, B3, E1, E3, E4, E14 and `test_focus_source_editor_only_while_the_window_is_active`. Rebuilt as `D:/dxtest/N-f9b` (sha256 `B5AD9BFA...`); items 85, 87, 88, 93 re-run in `D:/dxtest/auto<N>-f9b` with logs identical to N-f9; `auto/focus_check.py` measured the focus after the box of items 85 and 88: `beta`'s source editor (enabled) on N-f9b, its Braille Result editor on N-f9. Spec D1 "Focus", the behavior table, Design per File, Test Plan E1, the manual item and "Corrected after review" 1 updated, marked "Decided by orchestrator with the recommended default; user may override before merge". Item 94 now names N-f9b and expects the source editor; still unticked for the user. Not measured in the GUI: a completion while the Ctrl+S file dialog is open (unit test only). |
| M-7 | Spec only (EN and zh-TW): O10 and "Corrected after review" 3. |
| M-8 | Deferred to F-12 (no code). The spec's Risks bullet names the suspected cause (a hypothesis), and Out of Scope lists it. |
| M-9 | Deferred to F-12 (no code; it needs a new string). Listed in the spec's Out of Scope. |

The review's mutant tooling was reused from the session scratchpad (`f9review`, copied to `f9fix` with r17 added); nothing of it is committed. No GUI script touched the clipboard; only processes under the new `D:/dxtest/*-f9b` folders were ended, and no DotExpress of the user's was running.
