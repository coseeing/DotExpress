# Conversion Results Go to the Right Document (F-9) Design

## Goal

Task F-9 fixes the races between a running conversion and the document the user is working on (`task.md` ordering item 2, "F-9"). It covers three known defects of the P1-4 spec (`docs/superpowers/specs/2026-10-08-p1-4-export-conversion-presenters-design.md`, "Known defects found during this investigation"), plus one more that the fix depends on:

1. **P1-4 defect 1.** While a manual conversion runs, the user can still switch documents (Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+PageUp, Ctrl+PageDown) or import one (Ctrl+O). The result lands in whatever document is open when the conversion finishes. The next save then writes it into that document's `.dep` (probe 1 below). The output ends up in the wrong place with no message.
2. **P1-4 defect 2.** `ConversionPresenter.convert_for_export` does not check for a running job. A second job (Ctrl+S in the Braille Result editor, or an Export All step) silently replaces the first. The first result is dropped: a manual conversion never shows its output, a single export never writes its file, and an Export All chain stops without its summary (probes 2 and 3).
3. **P1-4 defect 3 (`task.md` #11).** Exporting a pending document as HTML runs a conversion, but the export ignores that conversion's `dual_view_segments` and writes the dual-view cache instead. The cache is empty for a pending document, so the file is the "No conversion data" page (probe 4).
4. **P1-4 defect 6** (in scope, D7). A worker exception that is not a `ConversionStageError` delivers nothing, so the UI stays busy. The queue of D4 would make this worse: a job that never finishes would block every later job. So it is fixed here.

Decided by the user (2026-10-10), `task.md` section 3 question 2; not asked again here:

- **U1.** A running conversion does **not** block switching documents. The result is written back to the document that **started** the conversion.

After this task:

- A manual conversion result goes to the document that was open when the user pressed Convert. If that document is still open (or open again), everything happens as today. If another document is open, the braille editor, the focus and the Dual View of the open document are left alone. The result is stored in the originating document in memory and on disk, and a message names that document.
- If the originating document no longer exists, or its text no longer matches what was converted, the result is discarded and the event is logged. This cannot happen through today's UI (D3).
- An export conversion requested while another conversion is running or being completed waits in a queue and runs afterwards. Nothing is dropped. Each completion keeps its own message, in request order.
- HTML export of a pending document shows the fresh conversion.
- A worker error of any kind ends the busy state with the existing "Translation failed: {error}" message and is logged.
- After the window closes, late conversion results are ignored (P1 review M-10).

New user-visible strings: **one** (D2): `Conversion completed. The result was saved to document "{name}".` The msgid count goes from 364 to 365. F-8 may add strings first; the plan takes the count again on the post-F-8 `main`.

Non-goals:

- blocking shortcuts while busy (rejected by U1);
- changing which commands stay reachable while busy;
- the Export All summary texts (P1-4 defect 4; F-12);
- persisting the dual view across restarts (Out of Scope).

## Relation to F-8 (data safety)

F-8 (atomic writes for the remaining writers, orphan `.tmp` recovery, U+0000 to U+FFFD on load and import) is specified in parallel and will probably merge first. This spec is written to survive that:

- Code is named by function, not by line. The line numbers below are from `main` `861d110` and serve as orientation only.
- The one new disk write (D1) goes through `DocumentWorkspaceService` and the same `save_document_package` call that `save_open_document` uses. It takes whatever F-8 changes there (existence checks, normalization) with no extra work. `save_open_document` and the new `save_document` share one body, so the two paths cannot drift.
- The text guard of D3 compares the document's text in memory with the converted text. Both come from the same editor read (`BrailleFrame._editor_text`). A test pins that a switch-away save stores exactly the text that `get_source_text()` returns (Test Plan E14). If F-8 normalizes more in that path, that test shows it.
- The plan takes the baseline counts again (`Ran`, msgids) on the post-F-8 `main`. Windows verification items are numbered after F-8's (placeholders `9a`-`9i` here).

## Current State (verified 2026-10-10 on `main` `861d110`, worktree `D:\workspace\DotExpress-f9`, Windows 11 26200)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`. Baseline, with the runtime copied as in F-3 plan Task 0: `cd client && $PY -m unittest discover -s tests` gives `Ran 1368`, `FAILED (errors=1, skipped=7)`. The only error is F-W6. The AST msgid scan and the catalog have 364 msgids.

The probes are in the session scratchpad `...\scratchpad\f9\probe_f9.py` and are not committed. They subclass `ConversionExportFlowsCharacterizationTest` (`client/tests/test_gui_document_flows.py`) and use its fakes: a real frame with recording editors, a real `DocumentController`, `DocumentWorkspaceService` and `ConversionPresenter` on a temporary workspace, `FakeThread`, deferred `CallAfter` and fake timers.

### Where things are

| Piece | Location (`861d110`) | Today |
| --- | --- | --- |
| Manual start | `ConversionPresenter.convert` (`ui/conversion_presenter.py` 128-135) | `if is_running(): return`; table check; `_start(view.get_source_text(), export=None)`. The open document is **not** recorded. |
| Export start | `convert_for_export` 137-145 | `_start(raw_text, export=...)` with no running check (comment names defect 2). |
| Start | `_start` 147-153 | busy on, close dialog, `build_request`, `runner.start`, `self._active = _ActiveJob(job_id, export)`, new 2 s timer (an older timer is overwritten, not stopped). |
| Manual completion | `_complete_manual` 198-209 | `view.show_conversion_output(braille)` (set and focus); `open_name = documents.open_document_name` **now**; if set: `replace_document(Document(open_name, view.get_source_text(), braille))` if it exists, `set_dual_view_results(open_name, segments)`; `refresh_dual_view()`; "Conversion completed." |
| Export completion | `_on_job_success` 176-185 | `job.export.on_success(output.display_text)`. The segments are dropped (defect 3). |
| Running | `is_running` 122-123 | `runner.is_running()`, which is "the worker thread is alive". It is `False` between the worker's end and the delivery turn (probe 6). |
| Worker | `ConversionJobRunner._run_job` (`conversion/jobs.py` 68-83, tabs) | Only `ConversionStageError` is delivered as a failure. Anything else escapes the thread, and nothing is delivered (defect 6). |
| Busy | `BrailleFrame.set_conversion_busy` (`gui.py` 1080-1088) | Disables the File and Translation menus, the document list and the source editor. The frame's char hook and the Braille Result editor stay active. |
| Switch | `on_char_hook` 980-1001, `_open_adjacent_document` 615-622 | Save the open document (`save_open_document`: memory first, then the package if changed), then open the other one. |
| Import | `on_import_document` 892-920 (Ctrl+O through the char hook) | Save first; one imported file is opened. |
| Ctrl+S | `on_output_text_key_down` 960-969 | Save, then `export_document(open document, "brl")`; a pending document starts an export conversion. |
| Close | `_close` 1040-1051, `_finish_close` 1066-1073 | Vetoed while `is_running()` and the event can be vetoed (no message). Otherwise save, close the converting dialog, destroy the Dual View. The presenter is not told (P1 review M-10). |
| Save | `DocumentWorkspaceService.save_open_document` (`documents/workspace_service.py` 124-134) | Saves **only the open document**. Other documents are written only by create, import and rename. |
| Export | `ExportCoordinator.export_document` 78-101, `_export_next` 138-183, `write_document` 71-76 (`documents/export_coordinator.py`) | `write_document` always takes `ExportContext(dual_view_results=documents.get_dual_view_results(name))`, the cache. |
| Cache | `DocumentController.dual_view_results_by_document` | Memory only. `load_documents` clears it, so after a restart every document has an empty cache. |

### Reachable while a conversion runs

The File and Translation menus, the document list (with its F2, Delete and context menu) and the source editor are disabled. These remain reachable:

- Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+PageDown and Ctrl+PageUp switch documents.
- Ctrl+O imports through the import dialog. Importing one file opens it.
- Ctrl+S in the Braille Result editor saves and exports the open document.
- F6 moves the focus.
- The window close box.

Rename, Delete and Delete All are **not** reachable while a job is active. The document menu has no accelerators (`ui/menu_builder.py`), and the list is disabled. Between Export All steps no job is active and everything is enabled.

### Probes (all on `861d110`)

1. **Defect 1 persists to disk.** `alpha` (pending, open) and `beta` (`"B"`). Convert `alpha`, press Ctrl+Tab, then let the job complete. Memory now holds `alpha` still pending and `beta` with braille `"AA"` (alpha's result). The cache has `beta`. After the next save, **`beta.dep` holds alpha's braille**, and `alpha.dep` stays pending. The existing pin is `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document` (`KNOWN BUG`, defect 1).
2. **Defect 2, single export.** `alpha` (pending, open) and `beta` (pending, selected). File > Export `beta`, then Ctrl+S on `alpha` before the first job finishes. Two jobs start. Only `alpha.brl` is written, with one "Export Complete" box; **`beta.brl` is never written and nothing says so**. The busy state ends.
3. **Defect 2, Export All.** `open` (pending, open), `p1` and `p2` (pending). Export All starts job 1 for `open`; Ctrl+S then starts job 2. Job 1 is dropped. **The export folder stays empty and no summary appears.** Only the Ctrl+S file is written. The existing pins are `test_ctrl_s_during_manual_conversion_supersedes_it`, `test_convert_between_export_all_steps_is_superseded` (`test_gui_document_flows.py`) and `test_superseded_job_delivers_nothing` (`test_conversion_presenter.py`).
4. **Defect 3.** A pending document `pend` (cache empty) exported as HTML: the file is the "No conversion data is available for this document." page. The fresh segment is missing. Cache and memory are unchanged. There is no existing pin.
5. **Defect 6.** A converter raising `RuntimeError`: the exception escapes `thread.run()`, nothing is delivered, the busy state stays on, `is_running()` is `False` and `_active` is still set. The existing pin is `test_exception_outside_conversion_stage_error_delivers_nothing` (`test_conversion_jobs.py`). In production `convert_text_with_alignment` wraps every `Exception`, so only a `BaseException` reaches this path today.
6. **Delivery gap.** After the worker ends and before its `CallAfter` runs, `is_running()` is `False` while a job is still active. A close in that gap is not vetoed.
7. **Ctrl+S on a converted document during its manual conversion.** No second job starts. The export writes the **previous** braille (`"old"`), then the manual result arrives. This is not a race on the conversion; it stays as it is (Out of Scope).

## Decisions

**D1. A manual job remembers the document that started it; the result goes there (U1).**

- `convert()` records `target = documents.open_document_name` and `source_text = view.get_source_text()` when it starts. Both go into the job. `get_source_text` is called once, as today.
- On success, the completion branches on the target. For clarity, `open_name` below is `documents.open_document_name` at completion.
  - **(a) Target open** (`target == open_name`, also after switching away and back): today's path, unchanged. Show the output and focus it. Replace the document with `Document(target, view.get_source_text(), braille)` (the editor shows the target, so this is the text the user sees). There is no text guard here: the source editor is disabled while busy and a switch back loads the same text, and a guard would have to read the editor before the output is shown, which would change today's event order. Set the cache for the target, refresh the Dual View, and show "Conversion completed.". Nothing is written to disk; the next save writes it, as today.
  - **(b) Target not open** (`target` is set, a different document is open): the open document's editors, focus and Dual View are left alone, so `show_conversion_output` and `refresh_dual_view` are not called. Then:
    1. `document = documents.get_document(target)`;
    2. the guard of D3;
    3. `documents.set_dual_view_results(target, output.dual_view_segments)`;
    4. `view.save_converted_document(Document(target, document.text, braille))`. The text is taken from memory, so only the braille changes; the user's text is never rewritten.
    5. If that returns `True`: `view.show_info(<D2 message>, _("Info"))`. If `False`: the view has already shown the save error, and there is no second box.
  - **(c) No document at start** (`target is None`): if still none is open, today's path (show the output, refresh, "Conversion completed."). If one is open now, the result is discarded (D3).
- **The new write.** `DocumentWorkspaceService.save_document(document) -> Document | None` is added. It is the body of today's `save_open_document`, for a named document:
  - return `None` if the name is not in the controller;
  - `updated = _encodable(document)`: lone surrogates replaced, the braille kept as given;
  - replace it in memory **first**;
  - skip the write if `_is_saved(updated)` (F-5 D2);
  - else `save_document_package` and `_remember`.

  `save_open_document(text=, braille=)` becomes "`prepare_document_for_save(open document, text=, braille=)`, then `save_document`", so its behavior and F-5's tests are unchanged.

  `prepare_document_for_save`'s "pending stays `None`" rule belongs to the editor path only. `save_document` must not apply it, or the braille of a pending document that has just been converted would be erased (Test Plan D5).
- **`ConversionView.save_converted_document(document) -> bool`** is new. The frame implements it as `try: self._workspace_service.save_document(document)`, `except Exception as exc: self._show_document_save_error(exc); return False`, then `return True`. A non-`OSError` is logged, an `OSError` shown, exactly like every other save (F-3, F-5). No new message.
- **Why write at once** (Decided by orchestrator with the recommended default; user may override before merge). The frame saves only the open document. A result kept only in memory for a document that is not open would be lost at exit, unless the user opened that document again before closing. Writing at once is the only way the user's request ("write the result back to the document") survives a restart. The write is the same atomic package write as every save. The F-5 fingerprint record is updated, so a later open-and-switch-away does not rewrite it. When the save fails, the memory copy keeps the result. The next save of that document (open it, then switch away) retries the write, as F-5 retries any failed save.
- **F-5 interplay.**
  - Case (a): unchanged. The result is in memory and the next save writes it.
  - Case (b): the result is on disk at once and `_saved[target]` matches. Opening the target loads the result into the editors, and switching away does not write again.
  - A save failure in (b) leaves `_saved[target]` stale, so the next save retries.
- **Focus.** In (b) nothing in the main window changes focus. The info box is modal and returns the focus to where it was, normally the source editor of the newly opened document.

Rejected:

- Blocking Ctrl+Tab / Ctrl+O while busy (U1).
- Keeping (b)'s result in memory only: lost at exit (above).
- Opening the target document again at completion: it would yank the user away from the document they chose.

**D2. One new message for case (b).**

`_('Conversion completed. The result was saved to document "{name}".')`, caption `_("Info")`, `wx.OK | wx.ICON_INFORMATION` (through `view.show_info`). zh_TW: U+8F49 U+63DB U+5B8C U+6210 U+3002 U+7D50 U+679C U+5DF2 U+5132 U+5B58 U+5230 U+6587 U+4EF6 U+300C `{name}` U+300D U+3002 (that is "conversion completed. the result has been saved to document 'name'."). The quoting follows the existing `Document "{name}" already exists.`. The phrase "save" (U+5132 U+5B58) follows "Cannot Save Document".

Decided by orchestrator with the recommended default; user may override before merge (O1). The user decided where the result goes, but not what the user is told. Reusing "Conversion completed." would add no string, but while the user is on another document it would not say where the result went. That would be a new silent surprise, and the screen reader user hears no output change. The alternative (reuse the old message) is a one-line change if the user prefers it.

**D3. Discard instead of guess.**

The result is discarded, with no message box, and logged (`dotexpress.gui`, `gui.log`, level WARNING, `"Discarded a conversion result: %s"` with the reason and the target name) when any of these holds:

- (b) and `documents.get_document(target)` is `None` (renamed, deleted, Delete All);
- (b) and `document.text != job.source_text` (the document now holds another text);
- (c) and a document is open now.

Busy ends as usual (`_end_job` runs before the branch). No cache entry, no memory change, no write.

- None of these is reachable through today's UI: while a job is active the list and the File menu are disabled, and the source editor too. A switch away saves exactly the editor text that `get_source_text()` read (Test Plan E14). The guard is a safety net for future entry points and for the rename/delete questions of this task.
- A rename is not followed. Name is the only document identity the app has (cache, packages, list). Following it would need a rename hook into the presenter for an unreachable case (Decided by orchestrator with the recommended default; user may override before merge, O2).
- The user asked for "drop silently or log": logging was chosen, so a support log shows it (O3).

**D4. Export conversions wait in a queue instead of replacing the running job (defect 2).**

- The presenter keeps a FIFO queue of pending jobs. Each job holds its request, built when it is submitted, plus its completion: the export callbacks, or the manual target of D1.
- **Submit** (both `convert()` after its checks, and `convert_for_export`): if a job is active, a completion is in progress, or the queue is not empty, append to the queue. Otherwise start now. Building the request at submit time keeps today's rule that the settings, tables and language at the time of the command apply.
- **Completion** (`_on_job_success`, `_on_job_failure`): take the active job, then `_completing = True`, then:
  - `try`: today's steps (`_end_job`: stop the timer, close the dialog, busy off), then the completion (D1, or the export callback, or the error box);
  - `finally`: `_completing = False`, and if the queue is not empty and the presenter is not shut down, start the head.

  A completion's modal box (for example "Conversion completed.") therefore closes before the next job starts. Requests that arrive during that box (an Export All step's `CallAfter` runs inside the modal loop) queue up behind. There is never a second box on top of the first, and the order is the request order.
- **Manual Convert stays as today**: it returns silently while a job is active **or queued** (`is_running()`, D5). It is reachable only from the source editor and the Translation menu, which are disabled while busy. In an Export All gap nothing is active, so Convert starts, and the chain's next pending step queues behind it (it was dropped before).
- Each started job has its own timer and converting dialog, as today. With one job at a time, the "timer overwritten without Stop" quirk of `_start` disappears.
- **When nothing overlaps, the order of every event is exactly today's.** Every characterization test without an overlap passes unchanged, including `test_export_all_with_a_real_presenter_turn_by_turn`.

Rejected:

- `show_info("A conversion is already running")`: one new string, and Export All would list a document as failed because of an unrelated manual conversion.
- Cancelling the running job: it cannot be stopped (liblouis in the worker), and the user asked for both results.

Decided by orchestrator with the recommended default; user may override before merge (O4).

**D5. `is_running()` means "a job is active or queued".**

`ConversionPresenter.is_running()` returns `self._active is not None or bool(self._queue)`, not the thread state. Effects:

- `_close` also vetoes a vetoable close in the delivery gap (probe 6) and while jobs are queued. As today the veto is silent.
- It does not cover a completion box (`_completing` with an empty queue). A close then is not vetoed by this check, as today, so F-7's close behavior during a message box is unchanged.
- `_show_converting_dialog` keeps using the runner (`active_job_id`, thread alive).

D7 makes this safe: every started job now delivers exactly once. A hanging converter keeps a vetoable close vetoed, the same as today's thread check.

**D6. HTML export of a pending document uses its own conversion (defect 3, #11).**

- `convert_for_export(raw_text, *, on_success: Callable[[ConversionOutput], None], on_error)`: the export callback receives the whole `ConversionOutput` instead of `display_text`. `ExportConversions` (the coordinator's protocol) changes the same way.
- `ExportCoordinator.write_document(destination_path, document, format_key, *, dual_view_results=None)`: `None` means the cache, as today. A tuple is used as is.
- `export_document` (pending) and `_export_next` (pending) build `Document(name, text, output.display_text)` and pass `dual_view_results=output.dual_view_segments`. Documents with braille keep using the cache, unchanged.
- The export does **not** write the segments into the cache, and the document stays pending, as today. Export results never changed documents, and caching segments for a pending document would make the Dual View show data that the Braille Result editor does not have (O5).
- BRL and DEP writers ignore the context, so only HTML changes.

**D7. Every worker outcome is delivered (defect 6).**

In `ConversionJobRunner._run_job`, after `except ConversionStageError`, add `except BaseException as error`:

1. log `"Unexpected error in a conversion job"` with `exc_info` (logger `dotexpress.gui`, `gui.log`, bound at call time as in F-6 review M-6 and F-7 D6);
2. deliver `ConversionJobFailure(job_id, ConversionStageError("translation", error))`;
3. return without re-raising.

The user sees the existing "Translation failed: {error}" box with `get_public_error_message(error)` (an empty message gives "An unknown error occurred."), and the busy state ends. `BaseException` is caught, not only `Exception`: a `SystemExit` in a worker thread would otherwise also leave the UI busy. A daemon thread has nothing to hand it to.

O6: Decided by orchestrator with the recommended default; user may override before merge.

**D8. The window's close tells the presenter (P1 review M-10, close guard of F-7).**

- `ConversionPresenter.shutdown()` is new. It stops and clears the timer, clears the active job and the queue, and sets `_shut_down`. Later deliveries find no active job and are ignored. The timer callback and the drain do nothing. It calls no view method.
- `BrailleFrame._finish_close` calls `self._conversion_presenter.shutdown()` right after `_close_finished = True`, before `close_converting_dialog()`.
- **Close while a conversion runs**, with F-7's guard:
  - A vetoable close is vetoed (D5), with no message, as today.
  - A non-vetoable close (F-7's re-entered close that cannot be vetoed, or any forced close) saves the open document per F-5 D8 and closes. F-7 measured that wx 3.2.9 sends no close event on `WM_ENDSESSION` (the process just ends, F-7 item 60). So this path is rare in practice, and D8 is a cheap safety net for it. The running job's result is then **dropped**. For a target that is not open (D1 b) this means its previous braille stays. The user's text is safe, because it was saved when the user switched away. No write happens after the window is gone, and no view method runs on a destroyed frame.
- Effect on existing tests: the non-vetoable close with a running job now records `("timer.Stop", n)` before the dialog's `Unbind`/`Destroy`. `test_close_while_running_vetoes_or_saves_and_closes` is updated accordingly (it is a characterization test of the close order; the plan states it).

**D9. Strings and catalogs.**

- One msgid (D2).
- `scripts\generate-pot.bat`, then `msgmerge`, then the msgstr, then `msgfmt --check --statistics`: 0 fuzzy, 0 untranslated.
- `POT-Creation-Date` stays `2026-10-10 12:00+0800` (HANDOFF section 2).
- Check that `msgmerge` did not fuzzy-match the new msgid to "Conversion completed." (HANDOFF section 2 warns about this); if it did, remove the `#, fuzzy` flag and the previous-msgid lines.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Convert `alpha`, it completes while `alpha` is open | output set and focused, memory updated, cache, Dual View, "Conversion completed." | identical |
| Convert `alpha`, Ctrl+Tab to `beta`, it completes | `beta` gets alpha's braille (editor, memory, cache); saved into `beta.dep` on the next save | `beta` untouched; `alpha` gets the braille in memory, cache and `alpha.dep`; D2 message |
| Same, Ctrl+Tab back to `alpha` before completion | (a) | identical |
| Convert `alpha`, Ctrl+O imports one file, it completes | the imported document gets the braille | as Ctrl+Tab: `alpha` gets it; the imported document stays pending |
| Same, `alpha.dep` cannot be written at completion | (n/a) | "Failed to save document: {error}" error box; `alpha` keeps the result in memory; the next save of `alpha` retries |
| Convert, Ctrl+S on the pending open document | export replaces the manual job; output never shown; one "Export Complete" | "Conversion completed." (output shown), then the export runs, then "Export Complete" |
| File > Export pending `beta`, Ctrl+S pending `alpha` | only `alpha.brl`, one box | `beta.brl` then `alpha.brl`, two boxes in that order |
| Export All with pending documents, Ctrl+S during it | chain stops, no summary, folder empty | the Ctrl+S export waits its turn; every document written; the summary appears |
| Convert in an Export All gap | the next pending step replaces it; manual output never shown | manual completes first ("Conversion completed."), then the chain goes on and ends with its summary |
| Export pending document as HTML | "No conversion data" page | the fresh dual view; cache unchanged; document stays pending |
| Export converted document as HTML | the cache | identical |
| Worker raises a non-stage error | busy forever, no message | "Translation failed: {error}", busy off, logged |
| Close (vetoable) while running | vetoed | identical; also vetoed in the delivery gap and while queued |
| Close (not vetoable) while running | saves, closes; a late delivery would call a destroyed frame | saves, closes; the presenter is shut down; late results ignored |

## Design per File

### `client/ui/conversion_presenter.py` (4 spaces)

- `_ManualTarget(document_name: str | None, source_text: str)` (private, frozen).
- `_Job(request, export: _ExportCallbacks | None, manual: _ManualTarget | None)` replaces `_ActiveJob`'s role for queued jobs; `_ActiveJob(job_id, job)` for the running one (the plan may merge them).
- `self._queue: collections.deque[_Job]`, `self._completing = False`, `self._shut_down = False`.
- `is_running()` (D5), `convert()` and `convert_for_export()` through `_submit` (D4), `_start_next()`, `_on_job_success` / `_on_job_failure` with the `try`/`finally` drain, `_complete_manual(job, output)` with branches (a), (b), (c) and D3, `shutdown()` (D8).
- `ConversionView` gains `save_converted_document(document: Document) -> bool`.
- The export success callback gets the `ConversionOutput` (D6).
- The module still imports neither `wx` nor `gui` (`test_module_imports_neither_wx_nor_gui`).
- The D3 logger is bound at call time.

### `client/conversion/jobs.py` (tabs)

`_run_job`: D7. Nothing else changes: ids, stale filtering, `daemon=True`, `_thread = None` before the callback.

### `client/documents/workspace_service.py` (4 spaces)

`save_document` (D1); `save_open_document` delegates to it. The module docstring's "Save writes only when..." sentence names both.

### `client/documents/export_coordinator.py` (4 spaces)

`ExportConversions.convert_for_export` signature, `write_document(..., dual_view_results=None)`, the two pending paths (D6).

### `client/gui.py` (tabs)

- `save_converted_document` in the `ConversionView` block.
- `_finish_close` calls `shutdown()` (D8).
- Nothing else. `_close`'s check stays `self._conversion_presenter.is_running()`; its meaning widens in the presenter.

### Catalogs

`client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` and `.mo` (D9).

### Not changed

- `set_conversion_busy`, `on_char_hook`, `_open_adjacent_document`, `on_import_document`, `on_output_text_key_down`;
- `DocumentController`;
- the writers in `documents/formats.py`;
- `client/braille/` and every file in HANDOFF section 2's list.

## What Stays Identical

- With no overlap of jobs, the turn-by-turn event logs of every manual conversion, single export, Export All and failure path.
- Every message, caption and icon except the D2 message and the D7 path (which shows an existing message where today nothing appears).
- Case (a), including "nothing is written to disk until the next save".
- Busy toggling per job; the 2 s converting dialog; the manual Convert's silent return while busy.
- Export never changes documents or the cache.
- F-5's fingerprint semantics and F-7's close and re-entry handling, except D5 and D8.

## User-Visible Strings

| msgid | zh_TW msgstr | Where |
| --- | --- | --- |
| `Conversion completed. The result was saved to document "{name}".` | U+8F49 U+63DB U+5B8C U+6210 U+3002 U+7D50 U+679C U+5DF2 U+5132 U+5B58 U+5230 U+6587 U+4EF6 U+300C `{name}` U+300D U+3002 | D1 (b), caption `Info` |

Existing messages newly reachable:

- "Translation failed: {error}" for an unexpected worker error (D7);
- "Failed to save document: {error}" when the D1 (b) write fails.

## Test Plan

TDD: each step's tests are written first and fail for the stated reason, then the code turns them green. Indentation follows each file: `test_conversion_jobs.py` uses tabs, and the other test files named here use 4 spaces. Tests use temporary folders only. Every test that makes the code log uses `assertLogs` (or isolates `dotexpress.gui`), so nothing is written to `client/log/`.

### A. Runner (`client/tests/test_conversion_jobs.py`)

1. **Flip** `test_exception_outside_conversion_stage_error_delivers_nothing` to `test_unexpected_worker_error_is_delivered_as_a_translation_failure`: `RuntimeError("unexpected")` delivers one failure with stage `translation` and `error` the same object; `thread.run()` does not raise; `is_running()` is `False`; one log record with `exc_info`. Red: the exception escapes.
2. `test_base_exception_in_the_worker_is_delivered_too`: `SystemExit("x")`, same expectations. Red.

### B. Presenter (`client/tests/test_conversion_presenter.py`)

The recording view gets `save_converted_document`, which records `("save_converted_document", document)` and returns a configurable result. A small helper "switches" documents the way the frame does: it replaces the open document's text with the view's source text, then calls `documents.open_document(other)`.

1. `test_result_goes_to_the_document_that_started_the_conversion`: start on `alpha`, switch to `beta`, deliver. Events after `_end`: `("save_converted_document", Document("alpha", "source", braille))`, then `show_info(D2 message with alpha, Info)`. No `show_conversion_output`, no `get_source_text`, no `refresh_dual_view`. Cache `{"alpha": segments}`; `beta` unchanged. Red: today `beta` gets it.
2. `test_result_for_the_open_document_follows_todays_path`: switch away and back; the event list equals today's manual completion. Green before and after (a guard).
3. `test_failed_save_of_the_originating_document_shows_no_completion_message`: the view returns `False`; no `show_info`; the cache entry for `alpha` stays; a queued job still starts afterwards. (The memory side is the service's job, D1 and E4.)
4. `test_result_for_a_document_that_is_gone_is_discarded_and_logged` (subTests: deleted; renamed; Delete All): no view call after `_end`, no cache entry, one WARNING. Red.
5. `test_result_for_a_changed_text_is_discarded_and_logged`: (b) with another text in memory. Red.
6. `test_result_without_a_starting_document`: (c), none open at the end gives today's output-only path; one open gives a discard plus a log. Red for the second.
7. **Flip** `test_superseded_job_delivers_nothing` to `test_export_requested_while_a_conversion_runs_waits_for_it`: one thread until the first completes; then `build_request` was recorded at submit time; the export starts after the manual completion's `show_info`; both completions arrive in order; the first timer is stopped. Red.
8. `test_queued_jobs_run_in_request_order`: three exports while one runs; FIFO.
9. `test_queue_drains_after_a_failed_completion`: the first job fails (error box), the queued one starts after it.
10. `test_request_during_a_completion_waits_until_it_returns`: an `on_success` callback that itself calls `convert_for_export` (standing in for a `CallAfter` run inside a modal box) queues; no second `busy True` before the callback returns. Red.
11. `test_queue_drains_when_a_completion_raises`: an `on_success` raising `RuntimeError`; it propagates, and the next job has started (`finally`).
12. `test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap`: no new thread, no events.
13. `test_is_running_covers_the_delivery_gap_and_the_queue`: `True` after the worker ends and before delivery; `True` while queued; `False` during a completion with an empty queue; `False` after. Red for the gap.
14. `test_shutdown_drops_the_running_and_queued_jobs`: `timer.Stop`; a later delivery gives no event; the timer callback gives no event; `is_running()` is `False`; no queued job starts. Red: no `shutdown`.
15. `test_export_success_receives_the_conversion_output`: `on_success` gets the `ConversionOutput` with its segments. Red.

Existing presenter tests whose export callbacks take `braille` are changed to take `output` and record `output.display_text`. Their event lists are unchanged.

### C. Coordinator (`client/tests/test_export_coordinator.py`)

1. `test_html_export_of_a_pending_document_uses_its_conversion`: the real HTML writer; the file contains the fresh segment's source; the cache is unchanged; the document stays pending. Red: the "No conversion data" page.
2. `test_export_all_html_uses_each_pending_documents_conversion`: two pending, one converted with a cache entry; each file shows its own data. Red.
3. `test_write_document_without_results_uses_the_cache`: the existing `write_document` tests, unchanged, plus an explicit `dual_view_results=()` that writes "No conversion data" even with a cache entry.
4. `test_export_all_with_a_real_presenter_turn_by_turn` stays as it is (its events are identical; its fake converter is unchanged).

The fake `ExportConversions` of the module passes a `ConversionOutput` to `on_success`.

### D. Service (`client/tests/test_workspace_service.py`)

1. `test_save_document_writes_a_document_that_is_not_open`: the package holds the new braille; memory is replaced; `_is_saved` is true afterwards.
2. `test_save_document_skips_an_unchanged_document`: no write (mtime and bytes unchanged), as F-5's open-document test.
3. `test_save_document_failure_keeps_memory_and_the_package` (injected `os.replace` failure or a read-only package, as in F-3/F-5 tests): raises; memory has the new braille; the package bytes are unchanged; a later `save_document` retries and writes.
4. `test_save_document_of_an_unknown_name_returns_none`: no write.
5. `test_converted_braille_of_a_pending_document_is_saved`: a pending document gets braille through `save_document` (not erased by the pending rule).
6. The existing `save_open_document` tests stay green unchanged.

### E. Frame and characterization (`client/tests/test_gui_document_flows.py`, `ConversionExportFlowsCharacterizationTest`)

1. **Flip** `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document` to `test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document`:
   - after delivery: `timer.Stop`, busy off, the D2 box, and nothing else (no `set output`, no focus, no `dual_view.refresh`);
   - memory: `alpha` has the braille and `beta` is unchanged;
   - cache: `{"alpha": (segment,)}`;
   - `alpha.dep` holds the braille; `beta.dep` is not rewritten;
   - after Ctrl+Tab back to `alpha` the output editor shows the braille.
   Red.
2. `test_ctrl_tab_away_and_back_during_conversion_keeps_todays_completion`.
3. `test_import_during_manual_conversion_does_not_receive_the_result`: drive `on_import_document` with a fake import file dialog (`GetPaths`, `SetFilterIndex`, `GetFilterIndex`). The plan adds that fake, or calls `_open_document_by_name` after a service import if the fake is too heavy. The imported document stays pending; `alpha` gets the result. Red.
4. `test_failed_save_of_the_starting_document_reports_the_save_error`: `alpha.dep` made unwritable after the switch (F-3/F-5 injection); the "Failed to save document: {error}" error box; no completion box; `alpha` in memory has the braille.
5. **Flip** `test_ctrl_s_during_manual_conversion_supersedes_it` to `..._queues_the_export`: the output is shown and "Conversion completed." is boxed, then the second job starts, then `alpha.brl` is written with "Export Complete". Red.
6. `test_ctrl_s_during_export_all_waits_and_the_summary_appears` (probe 3 as a test). Red.
7. `test_ctrl_s_during_single_export_writes_both_files` (probe 2 as a test). Red.
8. **Flip** `test_convert_between_export_all_steps_is_superseded` to `..._completes_before_the_next_step`. Red.
9. `test_pending_html_export_through_the_frame_shows_the_conversion`. Red.
10. `test_close_in_the_delivery_gap_is_vetoed`. Red.
11. `test_close_that_cannot_be_vetoed_shuts_the_presenter_down`: running job; non-vetoable close; then the worker ends and its delivery runs: no event at all, no write, the target's package unchanged. Red.
12. `test_close_while_running_vetoes_or_saves_and_closes` is updated with `("timer.Stop", 1)` (D8).
13. `test_save_converted_document_reports_failures_like_every_save` (frame method): `OSError` gives the box and no log; `ValueError` gives the box and a log. Uses `gui.message_box` patched as F-7 does.
14. **The invariant of D3:** `test_switch_away_stores_exactly_the_converted_text`. The source editor holds `A` U+D83D `B` (written by script, checked by bytes; HANDOFF section 2); Convert, Ctrl+Tab, deliver. The result is stored, not discarded.

`FrameConversionDelegationTest`: the presenter is still built with the same arguments.

### Counts

About 40 new tests and 5 flipped ones (A 2; B 15; C 3; D 5; E 14). On Windows: `Ran` = the post-F-8 baseline + the new tests, `FAILED (errors=1, skipped=7)`, F-W6 only. The plan fixes the exact counts; the red/green intent is binding.

## Migration Steps (each step one green commit, red first)

1. `fix: deliver every conversion worker error as a failure (F-9)`: D7; tests A.
2. `fix: export pending documents as HTML with their own conversion (F-9)`: D6; tests B15, C, E9. This changes the export callback.
3. `fix: queue conversions instead of dropping the running one (F-9)`: D4, D5; tests B7-B13, E5-E8, E10.
4. `fix: write a conversion result to the document that started it (F-9)`: D1-D3, D9; `save_document`, `save_converted_document`, catalogs; tests B1-B6, D, E1-E4, E13, E14.
5. `fix: ignore conversion results after the window closes (F-9)`: D8; tests B14, E11, E12.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only. Step 4 is the only one that touches `client/locales/`.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, with the runtime copied as in F-3 plan Task 0.

1. Full suite: no failure or error other than F-W6; `Ran` as the plan states.
2. Focused: `$PY -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows -v` passes; both orders of `tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator` pass.
3. `grep -rn "KNOWN BUG (P1-4 spec, defect [1236])" client/tests` prints nothing.
4. Catalogs:
   - one new msgid, with the msgstr of the table above;
   - `msgfmt --check --statistics`: all translated, 0 fuzzy, 0 untranslated;
   - the AST msgid scan equals the catalog count (post-F-8 count + 1);
   - `POT-Creation-Date` is unchanged.
5. Both fixture sha256 values are unchanged (`translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`).
6. App data untouched:
   - in the main checkout, `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after;
   - the worktree gets no `client/log/`, `client/workspace/` or `client/config.json`.
7. `git diff main --stat` touches only the files of "Design per File", the test files above, and the spec, plan and history files.
8. Mutation check (plan). Each mutant is caught by at least one test:
   - (b) using `open_document_name` at completion instead of the job's target;
   - (b) writing memory only (no `save_converted_document`);
   - (a) also writing to disk;
   - (b) calling `show_conversion_output` or `refresh_dual_view`;
   - (b) storing the editor text instead of the memory text;
   - removing the text guard of (b);
   - `save_document` applying the pending rule (erasing new braille);
   - `_submit` starting at once while a job is active (today's supersede);
   - LIFO instead of FIFO;
   - the drain outside `finally`;
   - `_completing` never set;
   - `is_running()` back to the thread state;
   - `shutdown()` not clearing the queue, and separately not called by `_finish_close`;
   - the coordinator ignoring `output.dual_view_segments`;
   - the coordinator writing them into the cache;
   - the runner catching `Exception` only;
   - the runner not logging.
9. Packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build and process rules as in F-7:

- the main checkout's `client\.venv\Scripts` first on `PATH`, then `scripts\build-dotexpress.bat`;
- check in `PYZ-00.toc` that `ui\conversion_presenter.py`, `conversion\jobs.py`, `documents\workspace_service.py`, `documents\export_coordinator.py` and `gui.py` come from the checkout being verified;
- copy the exe to `D:\dxtest\N-f9\`;
- "Before" is the build of `main` after F-8;
- each item runs in a new `D:\dxtest\auto<item>-f9` folder;
- only processes under those folders are ended.

Scripts go to the implementation's history folder `auto/`. They reuse `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `lock.py`) and `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py` without editing. Message boxes are task dialogs read through UIA (`f5gui.describe`).

**A slow conversion.** The items need a conversion that runs for several seconds. The plan calibrates a source text (for example a few hundred thousand characters of mixed Chinese and English pasted by the script) so that the "converting" dialog (U+8F49 U+63DB U+4E2D) appears. Keys are sent within the first 2 s, before that dialog takes the foreground, or after focusing the main window again; the plan picks and records the method. If the build is too fast for a given size, the size is raised, never a sleep inside the app.

Items `9a`-`9i` are placeholders; the final numbers are assigned at plan time, after F-8's items (F-7 ended at 65, F-8 starts at 66).

| # | Steps | Expected after F-9 | Before |
| --- | --- | --- | --- |
| 9a | Documents `alpha` (long text, pending) and `beta` (short, converted, braille `B`). Open `alpha`, Ctrl+Enter, Ctrl+Tab at once. Wait for completion. | the D2 box naming `alpha`, translated OK; `beta`'s braille editor unchanged; Ctrl+Tab back: `alpha` shows braille; after a restart `alpha.dep` holds it and `beta.dep` is unchanged | **`beta` shows alpha's braille, and after a switch `beta.dep` holds it** |
| 9b | As 9a, but Ctrl+Tab twice (back to `alpha`) before completion | "Conversion completed."; the output shows the braille in `alpha` | identical |
| 9c | As 9a, but Ctrl+O and import one `.txt` instead of Ctrl+Tab | the imported document opens and stays pending; the D2 box names `alpha` | the imported document gets alpha's braille |
| 9d | As 9a; after Ctrl+Tab, `lock.py` holds `alpha.dep` (share `r`) until completion | "Failed to save document: ..." error box, no completion box; unlock; open `alpha`: braille shown; switch away; restart: `alpha.dep` holds it | (as 9a "Before") |
| 9e | `alpha` (long, pending) open. Ctrl+Enter, F6 to the Braille Result editor, Ctrl+S, choose a path | "Conversion completed." first, then the export runs, then "Export Complete"; the file holds the braille | **one "Export Complete"; the output never shows the conversion** |
| 9f | Three pending long documents (the open one is among them). File > Export All > BRL to an empty folder; during the first conversion, F6 to the Braille Result editor and Ctrl+S to a second folder | the Ctrl+S file and all three files are written; the summary appears once at the end | **no summary; the Export All folder stays empty** |
| 9g | Import a `.txt` (pending). File > Export > Dual View HTML; also Export All as HTML | each file shows the converted segments | the "No conversion data" page |
| 9h | During a long conversion, post `WM_CLOSE`; then wait for completion; then `WM_CLOSE` again | the first close is vetoed (window stays, no box); after completion the app closes normally | identical (harness check) |
| 9i | During a long conversion that 9a switched away from: `SendMessageTimeoutW(main, WM_QUERYENDSESSION, 0, ENDSESSION_LOGOFF, ...)`; then let it complete; then start another long conversion and send `WM_ENDSESSION` (`wParam` 1, `ENDSESSION_LOGOFF`) | the query returns 0 at once (refused); the app keeps running and the first conversion completes with the D2 box; after `WM_ENDSESSION` the process exits within 5 s with code 0; no `.tmp` is left; no new traceback in `log\gui.log` | identical (harness check of D5/D8 against F-7's logoff handling) |

Never trigger a real logoff or shutdown; messages go only to the test instance's main window. Items that need NVDA stay manual.

**Manual for the user** (number assigned at plan time): with NVDA, item 9a's D2 box is read with the document name, and after OK the focus is back in `beta`'s source editor. Item 9e's two boxes are read one after the other.

## Risks

- **A new disk write outside the open document** (low). It is the same atomic package write and fingerprint record as every save (F-3, F-5). A failure shows the usual save error and keeps the result in memory.
- **The queue lengthens the busy time** (low, intended). Ctrl+S during a long conversion now waits for it instead of replacing it; the converting dialog shows meanwhile.
- **A hanging converter blocks the queue** (low). This is the same as today's busy state, which never ends either. D7 rules out the "no delivery" case.
- **Discarding on a text mismatch** (low). If a later change makes the switch-away save store text that differs from `get_source_text()`, results would be discarded and logged. E14 pins the invariant; the log names the case.
- **F-8 rebase** (medium, mechanical). `workspace_service.py` and possibly `gui.py` are touched by both. Everything is named by function, and the plan rebases on the post-F-8 `main`.
- **Logging from the presenter and the runner** (low). Tests must use `assertLogs`, or the suite writes `client/log/gui.log` (acceptance 6).
- **Test churn** (low). The export callback type changes for every fake `ExportConversions`; the close-order test gains `timer.Stop`.

## Open Questions

None blocking. U1 is the user's (2026-10-10).

Decided by orchestrator with the recommended default; user may override before merge:

- **O1.** Case (b) shows the new D2 message naming the document. The alternative is to reuse "Conversion completed." (no new string).
- **O2.** Document identity is the name; a rename during a conversion (unreachable today) discards the result instead of following it (D3).
- **O3.** Discarded results are logged at WARNING; there is no message box (D3).
- **O4.** Defect 2 is fixed with a FIFO queue, not with a "busy" message (D4).
- **O5.** An export conversion still does not update the cache or the document (D6).
- **O6.** The runner catches `BaseException`, logs it and delivers a "translation" failure (D7).
- **O7.** Case (b) writes `alpha.dep` at once instead of keeping the result in memory only (D1).
- **O8.** `is_running()` covers the delivery gap and the queue, so a vetoable close is vetoed then too; a completion box alone does not veto (D5).
- **O9.** `shutdown()` on close drops running and queued results (D8).

## Out of Scope / Follow-ups

- **HTML export of a converted document after a restart** shows "No conversion data": the dual-view cache is memory only (`load_documents` clears it). Fixing it needs either a conversion during export or a persisted dual view. Follow-up.
- **Ctrl+S during a manual conversion of a converted document** exports the previous braille (probe 7). Unchanged.
- **A vetoed close gives no feedback** while a conversion runs. Unchanged (would need a string).
- The Export All summary localization (P1-4 defect 4, F-12); `FindMenu` by title (defect 5).
- Delete All failure state (P1-3 defect 4).
- Persisting export conversions into the document (a pending document stays pending after export).
