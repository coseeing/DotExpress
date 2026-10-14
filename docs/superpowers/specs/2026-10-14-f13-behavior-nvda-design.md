# Behaviour and NVDA Follow-ups (F-13) Design

## Goal

F-13 covers items 1, 2, 3, 5 and 6 of `task.md` section 五, "下一輪要修". The user decided all five on 2026-10-14. They fix behaviour that a screen reader user meets: where the focus goes after a failed conversion, startup boxes that NVDA and Alt+Tab cannot find, a rare crash at logoff, and the text of the dictionary editor's removal list. Item 5 (making the confirmation boxes look like the system's) had a precondition. The probe for that precondition failed, so item 5 is dropped (D5).

Decided by the user (2026-10-14, `task.md` section 五 "下一輪要修"; HANDOFF `2026-10-14-01-handoff` sections 1 and 4). These are not asked again here:

- **U1 (item 1).** After the failure box of a manual conversion whose document is no longer the open one, the focus goes to the source editor through F-9 M-6's `focus_source_editor()`.
- **U2 (item 2).** The 「已復原文件」 and 「已取代字元」 boxes and the invalid-files dialog appear only after the main window is shown, so NVDA reads them and Alt+Tab finds them.
- **U3 (item 3).** At exit, `runtime.close()` (`lou_free()`) is skipped while a background conversion thread is still alive (F-9 review M-8). The fix is verified by a GUI item that sends WM_QUERYENDSESSION/WM_ENDSESSION many times during a conversion.
- **U4 (item 5).** The two F-11 boxes (「移除無法顯示的列」, 「尚未儲存的變更」, `GenericMessageDialog`) become system Yes/No boxes with custom button labels, like the existing four. Esc and Alt+F4 doing nothing is acceptable. **Precondition:** Esc, Alt+F4 and the close button must never answer 「移除並儲存」 or 「放棄變更」. If one does, nothing changes and the user is told. The existing four boxes (delete document, delete all, overwrite, dictionary delete) are not changed.
- **U5 (item 6).** The removal list shows the Bopomofo value exactly as it is in the file, with leading and trailing whitespace. No extra markers and no new strings.
- Items 4, 7 and 8 are task F-14 (see "Relation to F-14").

After this task:

- After the failure box of a conversion that started in another document, the focus is in the open document's source editor. Before, it stayed in the read-only Braille Result editor.
- At startup, the main window appears first and the startup boxes come after it, owned by the visible window.
- A logoff or shutdown during a conversion no longer frees liblouis under the running thread.
- The removal list shows `「ㄇㄚ  」` for a file value `ㄇㄚ␠␠`. Before, it showed `「ㄇㄚ」`.
- The two F-11 boxes stay as they are (D5).

New user-visible strings: **none**. The catalogs change only in their `#:` reference lines, and the `.mo` stays byte-identical.

Non-goals: F-14 (UI language groundwork, the HTML `lang`, the settings backup message); F-10; the deferred items the user declined on 2026-10-14 (export `.tmp` retry, case-insensitive headers, F-9 M-5, the damaged `config.json` notice, F-11 M-4).

## Relation to F-14

F-14 (`D:/workspace/DotExpress-f14`) runs in parallel from the same `main` (`a147fed`). Both tasks touch these files:

| File | F-13 | F-14 (as scoped in `task.md`) |
| --- | --- | --- |
| `client/gui.py` | `BrailleFrame.__init__`, `_load_startup_documents`, `BrailleApp.OnInit`, `BrailleApp.OnExit` | `_report_settings_save_problem` (settings backup message), maybe `_()`-at-import call sites |
| `client/dialog.py` | `_hidden_row_line` | possibly the entry type names shown in the editor (`dictionaries/entries.py` type names) |
| `client/locales/dotexpress.pot`, `zh_TW/LC_MESSAGES/dotexpress.po` | `#:` line numbers only | new msgids and `#:` lines |
| `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` | unchanged (byte-identical) | regenerated |
| `client/tests/test_gui_document_flows.py` | startup, exit and focus tests | settings backup message tests |

Neither task changes a function the other changes. The task merged second rebases onto the first and regenerates the catalogs' `#:` lines (`scripts/generate-pot.bat`, then `msgmerge`). F-13 adds no msgid, so F-14's catalog content wins as it is. F-14's files `i18n.py`, `about.py`, `dictionaries/entries.py`, `settings/dialogs.py`, `dual_view/html.py` and `config.py` are not touched by F-13.

## Current State (verified 2026-10-14 on `main` `a147fed`, worktree `D:/workspace/DotExpress-f13`)

Line numbers are from `a147fed` and are only for orientation. Code is named by function.

### Item 1: focus after a failed conversion

- `ConversionPresenter._on_job_failure` (`client/ui/conversion_presenter.py:287-300`) takes the active job and ends it (`_end_job`: stop the timer, close the converting dialog, `set_conversion_busy(False)`). Then:
  - **export job** (`active.job.export is not None`): `export.on_error(message)`. The export coordinator shows its own box.
  - **manual job**: `show_error(_name_unopened_document(target, message), "錯誤")`. `_name_unopened_document` (`:302-306`) adds `無法轉換文件「X」。` only when `target.document_name is not None` and differs from the open document's name (F-12 D7).
  - The focus is never moved.
- On success, `_complete_manual` (`:308-341`) handles case (b) (another document is open) and calls `self._view.focus_source_editor()` at the end (`:341`, F-9 review M-6). Case (a) (the same document) calls `show_conversion_output`, which focuses the Braille Result editor on purpose.
- `BrailleFrame.set_conversion_busy` (`gui.py:1178-1187`) disables the document list and `input_txt` while a job runs. A focused `input_txt` therefore loses the focus, and wx moves it to the Braille Result editor (F-9 review section 2.1, measured). After Ctrl+Tab during the job, `_open_adjacent_document`'s `input_txt.SetFocus()` fails on the disabled control. After the failure box the focus is therefore in the read-only Braille Result editor, in both the switched and the unswitched case (F-12 spec "Out of Scope": "Focus after the D7 box").
- `BrailleFrame.focus_source_editor` (`gui.py:1225-1228`) focuses `input_txt` only while `IsActive()`.
- Tests: `tests/test_conversion_presenter.py` `test_a_failure_after_switching_names_the_document`, `test_a_failure_of_the_open_document_is_not_named`, `test_a_failure_after_switching_away_and_back_is_not_named`, `test_a_failure_without_a_starting_document_is_not_named`, `test_manual_failure_shows_error_after_busy_off` and `test_export_failure_calls_only_on_error`. Each pins the full event list after delivery, so today they pin "no focus call". `tests/test_gui_document_flows.py` `test_focus_source_editor_only_while_the_window_is_active`.

### Item 2: startup boxes before the main window is shown

- `BrailleFrame.__init__` (`gui.py:125-145`) ends with `self._load_startup_documents()` (`:145`).
- `_load_startup_documents` (`:244-248`): `_clear_document_editors()`, `_load_workspace_documents_at_startup()`, `_update_window_title()`, `input_txt.SetFocus()`.
- `_load_workspace_documents_at_startup` (`:807-822`), in this order:
  1. `load_documents()`
  2. `_refresh_document_list()`
  3. `_review_invalid_workspace_files` (`:726-736`): the modal `InvalidWorkspaceFilesDialog`, then the deletion when asked for
  4. the 「已復原文件」 info box (`show_info`, F-8)
  5. `_ensure_open_document_exists` (`:800-805`), which opens the first document (`_open_document_by_name`, `:650-673`, whose 「已取代字元」 warning box comes at `:664-673`) or creates the default document. If that creation fails, `_show_document_save_error` shows an error box.
  6. `_update_window_title()`
- `BrailleApp.OnInit` (`gui.py:1276-1300`) builds the frame (`:1290-1295`), then calls `self.frame.Show()` (`:1298`), then `start_client_init_background`. All startup boxes are therefore owned by a frame that is not yet visible. F-8b review M-8: NVDA may not read them, and Alt+Tab does not list them. F-8b items 70 and 73 record "主視窗出現前顯示".
- No other box is raised during construction. `_initialize_state` and the layout code show nothing. The F-12 settings save warning is raised only at a save.
- Tests that pin the current order:
  - `tests/test_gui_document_flows.py` `DocumentControllerOwnershipTest.STARTUP_STEPS` (the six steps of `__init__`, the last being `_load_startup_documents`).
  - `BrailleAppLifecycleTest.test_app_startup_runs_steps_in_contract_order` (`["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`, with a `Mock` frame).
  - `test_app_builds_runtime_and_passes_it_to_frame` (`frame.Show.assert_called_once_with()`).
  - The eight tests that call `frame._load_workspace_documents_at_startup()` directly (`:318`, `:2134-2240`, `:2390`, `:3434`) test the loading itself, not when it runs.
- The GUI helpers of earlier tasks assume the old order. `2026-10-10-06-f8b-recovery-and-nul/auto/f8bgui.py` `start()` answers boxes until a window whose title ends with `DotExpress` appears, then attaches and returns. F-9's `B.start` and F-11/F-12's `dx.launch` work the same way.

### Item 3: exit during a conversion

- `BrailleApp.OnExit` (`gui.py:1302-1312`): `cleanup_dual_view_html`, then `runtime.close()` without conditions. `TranslationRuntime.close` (`conversion/contracts.py:31-36`) runs the close callbacks in reverse order: MathCAT's `adapter.close` and liblouis's `louis_helper.terminate()` (`lou_free()`; `braille/louis_helper.py` is git-ignored runtime).
- The worker thread is `ConversionJobRunner._thread` (`conversion/jobs.py:57-67`, `daemon=True`). `ConversionJobRunner.is_running()` (`:55-56`) is `_thread is not None and _thread.is_alive()`. `_thread` is cleared only when a result is delivered on the main thread (`_deliver_success` / `_deliver_failure`).
- `ConversionPresenter.is_running()` (`conversion_presenter.py:183-185`) means "a job is active or queued". `shutdown()` (`:238-249`, called from `BrailleFrame._finish_close`, `gui.py:1162-1172`) clears that, so after a close the presenter reports "not running" even though the worker thread may still be inside liblouis.
- `_close` (`gui.py:1136-1147`) vetoes a close that can be vetoed while `is_running()`. A WM_QUERYENDSESSION during a conversion is therefore refused at once (F-9 GUI item 93).
- WM_ENDSESSION produces no close event (F-7 item 60). In wxWidgets 3.2 on MSW, `wxApp::OnEndSession` calls `OnExit()` and then ends the process (reading of the wx source; to be confirmed by GUI item 127). `OnExit` therefore runs while the worker may be inside `lou_translateString`. F-9 saw exit code `-1073740940` (`0xC0000374`, heap corruption) once in five dry-run attempts and once on N-f8b2 (`auto93-f8b2-f9`), each time after a WM_ENDSESSION during a conversion (`2026-10-10-07-f9-conversion-target-document/auto-results.md`, "觀察"; review M-8).
- Reproduction: `2026-10-10-07-f9-conversion-target-document/auto/item85.py` item 93 does the following.
  1. A pending `alpha` with `f9gui.long_text()` (about 15 s of conversion).
  2. Ctrl+Enter.
  3. `f7gui.SessionMessage(w.handle, WM_QUERYENDSESSION)` (lParam `ENDSESSION_LOGOFF`; the answer is 0 while converting).
  4. `SessionMessage(w.handle, WM_ENDSESSION, wparam=1)` during a second conversion.
  5. `f7gui.exit_code(pid, 5)`.
- Tests: `BrailleAppLifecycleTest.test_app_exit_closes_runtime`, `test_app_exit_logs_cleanup_failure_and_still_closes_runtime`, `test_app_exit_cleans_the_validated_dual_view_folder` and `test_app_exit_without_initialized_runtime_is_safe`. Each builds a `BrailleApp` without a frame.

### Item 5: the two F-11 boxes

- `ui/message_box.confirm_box` (`client/ui/message_box.py:36-54`): `wx.GenericMessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING)` + `SetOKCancelLabels(ok_label, cancel_label)`. It returns `True` only for `wx.ID_OK`.
- It is used by `DictionaryEntriesDialog._confirm_hidden_rows` (`dialog.py:609-624`: 「移除無法顯示的列」, `移除並儲存(&S)` / `返回編輯(&B)`) and `_on_cancel` (`:587-598`: 「尚未儲存的變更」, `放棄變更(&D)` / `返回編輯(&B)`). Both are raised from the editor, a modal `wx.Dialog`.
- The existing four Yes/No boxes call `message_box(..., wx.YES_NO [| wx.NO_DEFAULT] | wx.ICON_WARNING)` with the system labels: `gui.py` `on_delete_document` (`:910`, style at `:919`), `on_delete_all_documents` (`:940`, style at `:948`), `confirm_overwrite_all` (`:1254-1262`), and `DictionaryManagementDialog.confirm` (`dialog.py:898-899`).
- F-11 planning (plan "Spec Corrections" 3) measured an OK/Cancel task dialog with custom labels raised from a dialog: Alt+F4 answered OK. With `SetYesNoLabels`, Alt+F4 answered `ID_YES`.
- Tests: `tests/test_message_box.py` `test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default` and `test_confirm_box_closed_any_other_way_is_cancel`; `tests/test_wx_call_sites.py` `test_the_only_generic_message_dialog_is_the_confirmation_box`.

### Item 6: the removal list

- `DictionaryEntriesDialog._hidden_row_line` (`dialog.py:626-634`) formats `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid` (zh_TW `第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確`) with `text=row.text.strip()` and `bopomofo=row.braille.strip()`.
- `PreservedDictionaryRow.braille` (`dictionaries/entries.py:37-57`, built at `:174`) is the field as read, not stripped.
- Whether a Bopomofo row is hidden depends on its value after only the leading whitespace is removed (F-11 D14, review I-1). Checked on `a147fed` with `_is_editable`:
  - `ㄇㄚ␠` and `␠ㄇㄚ␠` are shown.
  - `ㄇㄚ`, `ㄇㄚ␠␠` and `␠ㄇㄚ` are hidden.
  - Today the list shows `「ㄇㄚ」` for all three hidden values.
- Tests: `tests/test_dictionary_entries_dialog.py` `test_a_row_line_shows_the_stripped_source_text_and_sequence` (file value `␠ㄉㄨˋ|ㄗ˙␠`, listed stripped), `test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok` (`ㄇㄚ`, no whitespace) and the trace replay (`zz`/`ab`, no whitespace; the fixture `dictionary_entries_trace.json` does not record the box).

### Probe (item 5 precondition, 2026-10-14)

`docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/probe/` (script, driver, raw output, README). The setup:

- wx 4.2.5, wxWidgets 3.2.9, Windows 11 zh-TW.
- A `wx.MessageDialog(dialog, ..., wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)` with `SetYesNoLabels`, raised from the OK handler of a modal `wx.Dialog` owned by a frame.
- Every run starts a fresh process. Keys are sent only while the probe is in the foreground.

| Box | Esc | Alt+F4 | Close button | Enter |
| --- | --- | --- | --- | --- |
| Yes = `移除並儲存(&S)`, No = `返回編輯(&B)` | nothing | **`ID_YES`: remove and save** (2 of 2 runs) | the box has none; a click on the title-bar corner does nothing | `ID_NO` |
| Yes = `放棄變更(&D)`, No = `返回編輯(&B)` | nothing | nothing (2 of 2) | none; nothing | `ID_NO` |
| Yes = `返回編輯(&B)`, No = `移除並儲存(&S)`, YES_DEFAULT | nothing | **`ID_NO`: remove and save** | none; nothing | `ID_YES` |
| system labels 是(Y)/否(N) (as the existing four) | nothing | nothing | none; nothing | `ID_NO` |
| as the first, access key R instead of S | nothing | nothing | none; nothing | |

More runs showed the following:

- Alt+Numpad4 answers `放棄變更(&D)`.
- Alt+Numpad2 answers `返回編輯(&B)`.
- Alt+F4 answers `移除並儲存(&S)` also from a frame.
- **Alt+F10 answers `是(Y)` in the system box.**

The rule behind these results is in the README. A key pressed with Alt presses the button whose access key has the same character code as the key's virtual-key code: F4 = 0x73 = `s`, Numpad4 = 0x64 = `d`, F10 = 0x79 = `y`. The button's position does not matter. Every letter a-z has such a key: Numpad1-9 for a-i, the numpad operators for j-o, F1-F11 for p-z. The F-11 planning measurement is the same effect.

## Decisions

**D1. Focus after the failure box of a conversion whose document is no longer open (item 1, U1).**

- In `ConversionPresenter._on_job_failure`, manual branch: after `show_error`, call `self._view.focus_source_editor()` when the job's document is no longer the open one. The condition is the same as `_name_unopened_document`'s naming condition: `target.document_name is not None and target.document_name != self._documents.open_document_name`. The plan factors it into one helper (for example `_left_document(target) -> bool`) used by both places, so the message and the focus cannot disagree.
- Failure paths and their focus:

  | Path | Box | Focus after the box |
  | --- | --- | --- |
  | manual, starting document no longer open (switched with Ctrl+Tab or opened by an import during the job) | `無法轉換文件「X」。` + reason | **the open document's source editor** (new; only while the main window is active, as F-9 M-6) |
  | manual, starting document open (no switch, or away and back) | reason alone | unchanged: where wx left it (the Braille Result editor; see O1) |
  | manual, no starting document (none open when it started), with or without one opened since | reason alone | unchanged |
  | export (single or Export All step) | the export coordinator's box or summary | unchanged |

- The call comes after `show_error` returns, inside the existing `try` and before `_finish_completion`, in the same place as in `_complete_manual`. A job queued behind this one starts after the focus call, as before.
- No new string.

**D2. Load the workspace and show the startup boxes after the main window is shown (item 2, U2).**

- `BrailleFrame.__init__` no longer loads the workspace. Its last step becomes a light one that leaves the window in a defined empty state: `_clear_document_editors()` and `_update_window_title()` (title `DotExpress`).
- The old `_load_startup_documents` becomes a public `load_startup_documents()` with the same body (`_clear_document_editors`, `_load_workspace_documents_at_startup`, `_update_window_title`, `input_txt.SetFocus()`) and two guards:
  - It runs at most once.
  - It does nothing if the window has already closed (`_close_finished`): a close or logoff before the deferred call ran.
- `BrailleApp.OnInit`: after `self.frame.Show()`, `wx.CallAfter(self.frame.load_startup_documents)`, then `start_client_init_background(config_store)` as today. The call runs when the main loop processes its first pending events. By then the frame is visible, and every startup box is owned by a visible window.
- Everything else stays as it is: the order of the boxes (invalid files, then recovered, then replaced, or the default document's save error), their texts, the Keep/Delete outcome, the default document rule (`new`, `new (2)`), the title after loading and the final focus in the source editor.
- What the user sees: the main window appears with an empty document list and the title `DotExpress`, and at once the first box appears over it. When no box is needed, the list fills in a moment later. NVDA first announces the main window, then the box.
- Why the whole load and not only the boxes: the invalid-files answer decides which files exist before `_ensure_open_document_exists` picks the first document or the free default name. Deferring only the boxes would change those results or need a second pass.

**D3. Do not free the translation runtime at exit while a conversion thread is alive (item 3, U3).**

- `ConversionPresenter` gets a query for the worker thread (for example `worker_alive() -> bool`), returning `self._runner.is_running()`. It stays true after `shutdown()` while the thread runs. `ConversionPresenter.is_running()` keeps its meaning (job active or queued).
- `BrailleFrame` exposes that query, for example `conversion_worker_alive()`.
- `BrailleApp.OnInit` keeps a callable that reads the presenter, not the frame (for example `self._conversion_worker_alive = self.frame.conversion_worker_check()`, returning the presenter's bound method). `OnExit` may run after the frame has been destroyed (wx's end-session path), so it must not touch the wx frame.
- `BrailleApp.OnExit`:
  1. `cleanup_dual_view_html` as today.
  2. If `runtime is not None`, call `runtime.close()` only when no worker is alive. When the app has no such callable (no frame was built, as in the existing tests), it counts as "not alive".
  3. Return 0.
- When a worker is alive, the whole `runtime.close()` is skipped: the liblouis and the MathCAT callbacks alike (the worker may be in either). The process ends right after `OnExit`, and Windows releases the memory. Nothing is joined or waited for: Windows gives an ending session little time, and a conversion can take many seconds.
- No log line (O4). No change to the close veto, to `shutdown()` or to the job runner.

**D4. (item 4 is F-14.)**

**D5. Item 5 is not done: the two F-11 boxes stay `wx.GenericMessageDialog` (U4 precondition failed).**

- The probe (Current State, "Probe") shows that a system Yes/No box with the label `移除並儲存(&S)`, raised from the editor, answers **Alt+F4** with that button. Its position or the default button makes no difference. This is exactly what U4's precondition forbids. By U4 ("若會觸發，就不改，回報使用者"), nothing changes: `ui/message_box.confirm_box`, `_confirm_hidden_rows`, `_on_cancel` and their tests stay as they are, and the user is told.
- The 「尚未儲存的變更」 box alone would pass the three keys the user named. But Alt+Numpad4 would answer `放棄變更(&D)`, and the item asks for both boxes together.
- The user may choose an alternative later (Q1). No code in F-13 depends on it.

**D6. The removal list shows the raw Bopomofo value (item 6, U5).**

- `_hidden_row_line`: `bopomofo=row.braille` (not stripped). The `no_source_text` line and the source text (`text=row.text.strip()`) are unchanged: U5 names only the Bopomofo value.
- The value appears between `「` and `」` exactly as read, including spaces, tabs and ideographic spaces. A quoted CSV field with a line break would show the break too (O5). No marker, no new string.

## Behaviour per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Convert `alpha`, Ctrl+Tab to `beta`, the conversion fails | box `無法轉換文件「alpha」。…`; then the focus is in `beta`'s Braille Result editor | same box; then the focus is in `beta`'s source editor |
| Convert `alpha`, no switch, the conversion fails | box with the reason; the focus is in the Braille Result editor | unchanged |
| A failed single export or Export All step | the export's box | unchanged |
| Startup with an interrupted save or rename | 「已復原文件」 box while no window of DotExpress is visible; then the main window | the main window (title `DotExpress`, list filled, no document open yet), then the box over it; after OK: as before |
| Startup with a document containing U+0000 | 「已取代字元」 box before the main window | the main window (`alpha - DotExpress`, text loaded), then the box over it |
| Startup with invalid workspace files | the invalid-files dialog before the main window | the main window, then the dialog over it; Keep or Delete as before |
| Startup without any box | the main window with the first document open | the main window; the document opens a moment later |
| WM_ENDSESSION during a conversion | exit code 0, sometimes `0xC0000374` | exit code 0 (liblouis is not freed under the worker) |
| Normal exit, no conversion running | `runtime.close()` | unchanged |
| Removal list, file value `ㄇㄚ␠␠` or `␠ㄇㄚ` | `「ㄇㄚ」` | `「ㄇㄚ␠␠」`, `「␠ㄇㄚ」` |
| The two F-11 boxes, the four Yes/No boxes | | unchanged |

## Design per File

### `client/ui/conversion_presenter.py` (4 spaces)

- D1: the helper for "the job's document is no longer the open one", used by `_name_unopened_document` and `_on_job_failure`; the `focus_source_editor()` call in the manual failure branch.
- D3: `worker_alive()`.

### `client/gui.py` (tabs)

- D2: `__init__`'s last step; `load_startup_documents()` (renamed from `_load_startup_documents`, with the two guards); `BrailleApp.OnInit` posts it with `wx.CallAfter` after `Show()`.
- D3: `BrailleFrame.conversion_worker_check()` (or an equivalent that hands out the presenter's query); `BrailleApp.OnInit` keeps the callable; `BrailleApp.OnExit` skips `runtime.close()` while it returns true.

### `client/dialog.py` (tabs)

- D6: `_hidden_row_line`.

### Catalogs

Regenerate `dotexpress.pot` and `zh_TW/LC_MESSAGES/dotexpress.po` once at the end so that no `#:` reference is stale (lines in `gui.py`, `dialog.py` and `conversion_presenter.py` move). There are no msgid or msgstr changes. `dotexpress.mo` must be byte-identical to `a147fed`'s. `POT-Creation-Date` stays unchanged, as in F-12.

### Not changed

`client/ui/message_box.py` (D5), `conversion/jobs.py` (`is_running` already exists), `conversion/contracts.py`, everything under `client/braille/`, `dictionaries/`, the export coordinator, the four Yes/No boxes, the fixtures.

## What Stays Identical

- Every box text, caption, button and default; the access keys.
- The startup order of boxes and their outcomes, and the documents, title and focus after startup.
- The close veto while a conversion runs (F-9 D8), the save at close (F-5), and the session messages' answers.
- Conversion output: both golden fixtures, unchanged sha256.
- The editor's load, save, hidden-row and change rules (F-11), apart from the list line text of D6.

## User-Visible Strings

None. The msgid count stays at 407. The `.mo` is byte-identical.

## Accessibility (NVDA)

- D1: after the failure box, NVDA announces the source editor (editable, with the open document's text) instead of the read-only Braille Result editor. The user can type at once.
- D2: the startup boxes become ordinary owned dialogs of a visible main window. NVDA announces the main window, then the box (title, content, focused button). Alt+Tab lists the main window, and choosing it brings back the box. Whether NVDA reads them in full is manual item 131.
- D6: NVDA's reading of leading or trailing spaces depends on its punctuation level. The quotes `「」` show where the value starts and ends, both on screen and on a braille display. No marker is added (U5).

## Test Plan

Each test is written red first, where that is possible, against `a147fed`.

### A. Focus after failure (`tests/test_conversion_presenter.py`)

1. **Flip** `test_a_failure_after_switching_names_the_document`: the events end with `("focus_source_editor",)` after `show_error`. (red)
2. A new test: a failure after the starting document was replaced by an import (`documents.open_document` of a new name) also ends with the focus call. (red)
3. Unchanged and still pinning "no focus call": `test_a_failure_of_the_open_document_is_not_named`, `..._after_switching_away_and_back_...`, `..._without_a_starting_document_...`, `test_manual_failure_shows_error_after_busy_off`, `test_export_failure_calls_only_on_error`.
4. A new test: with a job queued behind the failing one, the focus call comes before the queued job starts (the order of the events). (red)

### B. Startup after Show (`tests/test_gui_document_flows.py`)

1. **Change** `DocumentControllerOwnershipTest.STARTUP_STEPS`: the last step of `__init__` is the new light step, not `load_startup_documents`. A new test: building a frame (startup steps patched) does not call `load_startup_documents` or the workspace service's `load_documents`. (red)
2. **Extend** `test_app_startup_runs_steps_in_contract_order`, with `gui.wx.CallAfter` as a `DeferredCalls` queue and the frame's `load_startup_documents` recorded: the order is `["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`. Running the queue appends `"load"`, so the load comes after `show`. (red)
3. A new test: `load_startup_documents` after `_close_finished` does nothing (no workspace load, no box). (red)
4. A new test: a second call of `load_startup_documents` does nothing. (red)
5. A new test: after `load_startup_documents`, the boxes run in the old order (invalid files, recovered, replaced) and the focus call on `input_txt` comes last. This uses the existing fakes of the `_load_workspace_documents_at_startup` tests.
6. Unchanged: the eight tests that call `_load_workspace_documents_at_startup` directly.

### C. Exit (`tests/test_gui_document_flows.py`, `tests/test_conversion_presenter.py`)

1. A new test: `OnExit` with a worker-alive callable that returns `True` does not call `runtime.close()`, still cleans the dual view folder and returns 0. (red)
2. A new test: with the callable returning `False`, `runtime.close()` is called once.
3. Unchanged: the four existing `OnExit` tests (no frame, so no callable: the runtime is closed).
4. A new test: `OnInit` keeps a callable that does not touch the frame. With the frame `Mock` set to raise `RuntimeError` on any attribute access after `OnInit`, calling it still answers. (red)
5. Presenter tests (`make_thread_factory`'s `FakeThread`):
   - `worker_alive()` is `False` before a job.
   - It is `True` while the thread runs, also after `shutdown()`.
   - It is `False` once the thread has ended. (red for the new method)

### D. Removal list (`tests/test_dictionary_entries_dialog.py`)

1. **Flip** `test_a_row_line_shows_the_stripped_source_text_and_sequence`: the expected line has the source text stripped (`肚子`) and the sequence raw (`␠ㄉㄨˋ|ㄗ˙␠`). Rename it, for example `test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence`. (red)
2. A new test: the file values `ㄇㄚ␠␠`, `␠ㄇㄚ`, `ㄇㄚ\t` and `ㄇㄚ\u3000` each appear unchanged in the list line. (red)
3. Unchanged: `test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok`, the trace replay, every F-11 confirm-box test (D5).

### E. Unchanged on purpose

`tests/test_message_box.py`, `tests/test_wx_call_sites.py` (D5).

### Mutation check (the plan runs these; each must be caught)

1. D1 focus called on every manual failure.
2. D1 focus called before `show_error`.
3. D1 focus never called.
4. D1 condition inverted.
5. D2 load still called from `__init__`.
6. D2 load posted before `Show()`.
7. D2 no `_close_finished` guard.
8. D2 no run-once guard.
9. D3 `close()` always called.
10. D3 `close()` never called.
11. D3 `worker_alive` reading the presenter's `is_running()` (active or queued) instead of the thread.
12. D3 the callable reading the frame.
13. D6 `.strip()` kept.
14. D6 `.rstrip()` only.
15. D6 the source text no longer stripped.

### Counts

About 14 new tests and 4 changed (A 3 new + 1 flip; B 4 new + 2 changed; C 4 new + presenter 3; D 1 new + 1 flip). The plan fixes the exact `Ran`. The full suite on `a147fed` is `Ran 1632`, `OK (skipped=6)`.

## Migration Steps (each step is one green commit, red first)

1. `fix: focus the source editor after a failed conversion of a document that is no longer open (F-13)`: D1; tests A.
2. `fix: show the startup boxes after the main window (F-13, F-8b review M-8)`: D2; tests B.
3. `fix: keep liblouis loaded at exit while a conversion is still running (F-13, F-9 review M-8)`: D3; tests C.
4. `fix: list the Bopomofo value of a hidden row as it is in the file (F-13)`: D6; tests D; catalog `#:` refresh.

As HANDOFF section 5 requires, each commit stages explicit paths only and has no `Co-Authored-By` line. The plan may move the catalog refresh into a final commit `chore: refresh catalog references (F-13)` if two steps change lines above msgids.

## Acceptance Criteria

Run on Windows from `client/` with the main checkout's `.venv` python. The runtime is copied as in F-3 plan Task 0, never staged.

1. Full suite: no failure and no error; `Ran` as the plan states; `OK (skipped=6)`.
2. Focused: `-m unittest tests.test_conversion_presenter tests.test_gui_document_flows tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n -v` passes.
3. Catalogs: 407 msgids, all translated, 0 fuzzy; `.mo` sha256 equal to `a147fed`'s; no stale `#:` line (regenerating gives no diff).
4. The three fixture sha256 values are unchanged (HANDOFF section 5).
5. App data untouched: the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` are unchanged, and the worktree gets none of them.
6. `git diff main --stat` touches only `client/ui/conversion_presenter.py`, `client/gui.py`, `client/dialog.py`, the catalogs, the tests named above, and the spec, plan and history files. `client/ui/message_box.py` is unchanged.
7. The mutation check above.
8. The packaged GUI verification below, with results in the history folder.

## Windows Verification (packaged build)

The rules are those of F-12, with the HANDOFF section 3 updates:

- Build with the main checkout's `client/.venv/Scripts` first on `PATH`, then `scripts/build-dotexpress.bat`. Check in `PYZ-00.toc` that the changed modules come from the worktree.
- The new build goes to `D:/dxtest/N-f13/`. The old build is `D:/dxtest/N-f12b`.
- Each item runs in a new `D:/dxtest/auto<item>-f13` (or `-f12b-f13`) folder with a copy of the exe. Only processes under those folders are ended. Check that available memory is at least 600 MB before each item, and run one item at a time.
- **fix** items run on both builds. **regression** items run on `N-f13` only, and on `N-f12b` only when they miss their expectation.
- Scripts go through F-11/F-12's `safe_run.py`: keys only while DotExpress is in the foreground, and no names of other programs in the logs. **No script reads or writes the clipboard.** Files are written by the script before launch.
- **Start helper.** The old helpers (`f8bgui.start`, `B.start`, `dx.launch`) return as soon as a window titled `…DotExpress` appears. On `N-f13` that window appears before the startup boxes and before the documents load. The plan adds an `f13gui.start(d)` that does the following:
  1. waits for the main window;
  2. then answers the invalid-files dialog (Keep) and each box (Enter), as the old helper does;
  3. records for each one `main_visible` (`IsWindowVisible` of the main window), `owner_is_main` (`GW_OWNER` is the main window) and the main window's title at that moment;
  4. returns once the main window is enabled, no box of the process has been open for 1 s, and the title is not the bare `DotExpress`, or the document list is non-empty.

  On `N-f12b` the same helper records boxes seen before any main window. Regression re-runs of earlier items use this helper in place of the old start.

| # | Class | Steps | Expected on N-f13 | N-f12b |
| --- | --- | --- | --- | --- |
| 121 | fix | `preprocessing.py` whose `main` sleeps 5 s, then raises `ValueError("boom")` (F-12 item 115). (a) Open `alpha`, Ctrl+Enter, at once Ctrl+Tab to `beta`, wait for the box, Enter. (b) As (a) without Ctrl+Tab. | (a) box `無法轉換文件「alpha」。` + `文字處理失敗：boom`; after Enter the focus is `beta`'s source editor (`('Edit', '來源文字')`, enabled); `beta`'s editors unchanged. (b) box `文字處理失敗：boom`; the focus after Enter is where it was before (record it; expected the Braille Result editor) | (a) the focus is `beta`'s Braille Result editor; (b) same as N-f13 |
| 122 | fix | F-8b item 70 workspace (interrupted rename `alpha` -> `gamma`); start with `f13gui.start` | the 「已復原文件」 box (name `alpha`) with `main_visible True`, `owner_is_main True`, main title `DotExpress`; after Enter: `docs ['alpha']`, title `alpha - DotExpress`, focus in the source editor; files as F-8b 70 | box seen with no visible main window |
| 123 | fix | F-8b item 73 workspace (`alpha.dep` with U+0000) | the 「已取代字元」 box (`alpha`, 2) with `main_visible True`, `owner_is_main True`, main title `alpha - DotExpress`; afterwards as F-8b 73 | box before the main window |
| 124 | fix | F-8a item 66 workspace (`alpha.dep` valid, `bad.dep` invalid); Keep | the invalid-files dialog (`['bad.dep']`) with `main_visible True`, `owner_is_main True`; afterwards `docs ['alpha']`, focus in the source editor | dialog before the main window |
| 125 | fix | One workspace with all three: `bad.dep` invalid, an interrupted rename of `alpha`, and `beta.dep` (first in the list after `alpha`) with U+0000. Keep. | the boxes in the old order: invalid-files dialog, 「已復原文件」, then 「已取代字元」 for the first opened document if it contains U+0000. Each has `main_visible True` and `owner_is_main True`. Final title, documents and focus as on N-f12b. (The plan picks the names so that the opened document holds the U+0000.) | the same order, all before the main window |
| 126 | regression | Re-run with `f13gui.start`: F-8b 70, 70b, 71, 72, 73; F-8a 66, 69, 79; F-12 113 (startup and Add part); plus a plain start (one valid `alpha`, no box) and a first start in an empty folder | every recorded line as in its original log, except where a box appears relative to the main window; plain start: no box, `docs ['alpha']`, title `alpha - DotExpress`, focus in the source editor; empty folder: `docs ['new']` | (only if a result misses) |
| 127 | fix | F-9 item 93's workspace (`alpha` long pending text, `beta`). **20 runs**, each a fresh start: Ctrl+Enter on `alpha`; after 1 s `WM_QUERYENDSESSION` (`ENDSESSION_LOGOFF`); then `WM_ENDSESSION` (wParam 1); exit code within 10 s | each query answers 0 within 2 s; **exit code 0 in all 20 runs, never `-1073740940` (`0xC0000374`)**; `alpha.dep`, `beta.dep` readable; no new `gui.log` line | record the count of `-1073740940` (F-9 saw it about 1 run in 5). If N-f12b shows none in 20 runs, the GUI evidence is inconclusive; record that, and the item still passes on N-f13's 20 clean exits plus tests C |
| 128 | regression | F-9 item 93 (full script); F-7 item 59 (`WM_QUERYENDSESSION` with nothing to save: exit code 0); a normal Close after a completed conversion (F-12 item 118 (a), then Close) | as in their logs; the normal Close gives exit code 0 | (only if a result misses) |
| 129 | fix | Dictionary `raw.csv`: `text,braille,type` / `抹,ㄇㄚ␠␠,Bopomofo` / `媽,␠ㄇㄚ,Bopomofo` / `甲乙,⠁⠃,Braille`. Edit it, press OK; read the box text through UIA; press 返回編輯; then OK, 移除並儲存 | the list lines `第 2 列：「抹」的注音「ㄇㄚ␠␠」格式不正確` and `第 3 列：「媽」的注音「␠ㄇㄚ」格式不正確` (spaces kept); then the file holds only `甲乙` | `「ㄇㄚ」` in both lines |
| 130 | regression | F-11 items 95 and 99 (both confirmation boxes; Esc, Enter, Alt+F4, the close button) | as in their N-f11 logs (D5: the boxes are unchanged; `dict_badbopo.csv` has no whitespace around its values, so the list text is the same) | (only if a result misses) |

Never trigger a real logoff or shutdown. Items 127 and 128 send the session messages to DotExpress's main window only.

**Manual for the user (item 131, NVDA):** run `D:/dxtest/N-f13` with NVDA on.

1. Start with the workspace of item 125 (the plan writes a copy into `D:/dxtest/manual131-f13/`). Does NVDA announce the main window and then read each startup box in full? While a box is open, does Alt+Tab list DotExpress, and does choosing it bring back the box?
2. Item 121 (a): after the failure box, does NVDA announce the source editor?
3. Item 129: how does NVDA read the list line with `ㄇㄚ␠␠`?

## Risks

- **A visible window before the documents load** (low). For a moment the main window is empty with the title `DotExpress`. A key pressed in that moment acts on an empty window, as after Delete All. The load is posted before the first user input can normally arrive.
- **A close before the deferred load** (low). It is guarded by `_close_finished` (test B3). A WM_QUERYENDSESSION while a startup box is open behaves as today: the frame's close handler runs with whatever is loaded.
- **GUI helpers** (medium, mechanical). Every earlier start helper returns too early on the new build. Item 126 and the new helper cover the startup items. Other regression scripts that start the app must use `f13gui.start` or wait for the documents.
- **The end-session path** (low). The reading that wx calls `OnExit` on WM_ENDSESSION comes from the wx source, not from a measurement. If `OnExit` were not called there, D3 would change nothing for logoff, and item 127 would show exit codes like N-f12b's. The tests still pin `OnExit`'s rule, which also covers a normal exit after a non-vetoable close.
- **Memory not freed** (none). The process ends right after `OnExit`.
- **Raw values with control characters** (low). A tab shows as a tab. A quoted line break breaks the list line (O5).
- **F-14 rebase** (low, mechanical). See "Relation to F-14".

## Open Questions

**Decided by the user (2026-10-14):** U1-U5. D5 follows U4's own rule for a failed precondition.

**Decided by orchestrator with the recommended default; user may override before merge:**

- **O1.** D1 applies only when the job's document is no longer open, as the user worded it. After the failure of a conversion of the open document, the focus stays where wx left it (the Braille Result editor), as before F-9. Extending D1 to that case would be a one-line change.
- **O2.** D2 defers the whole workspace load, not only the boxes, so that the invalid-files answer still comes before the default document is chosen. The main window appears empty for a moment.
- **O3.** D2's load is posted with `wx.CallAfter` right after `Show()`, without waiting for the window to be painted or activated. Item 125 records `main_visible`. If NVDA misses the window (item 131), the plan can switch to an `EVT_ACTIVATE`/`EVT_SHOW` trigger.
- **O4.** D3 skips the whole `runtime.close()` (liblouis and MathCAT), does not join the thread and writes no log line.
- **O5.** D6 shows the value as read, including tabs, ideographic spaces and a quoted line break, and keeps the source text stripped.

**Questions for the user** (not blocking; F-13 proceeds without them):

- **Q1. Item 5 after the failed precondition.** In a native Yes/No box with custom labels, Alt plus the key whose virtual-key code equals an access key's character presses that button. Alt+F4 is `s`: it would press 「移除並儲存(S)」. Options:
  - (a) **Recommended:** keep the two F-11 boxes as they are (classic `GenericMessageDialog`: Esc, Enter, Alt+F4 and the close button all mean 返回編輯). This is what F-13 does.
  - (b) Use the system box and change the zh access key of 「移除並儲存」 from S to another letter. The msgstr changes; the msgid stays. Esc, Alt+F4 and the close button would then do nothing (probed with R). But another Alt+key would still press each affirmative button: Alt+F3 for R, Alt+Numpad4 for 放棄變更(D).
  - (c) Another design, for a later task.
- **Q2. The existing four Yes/No boxes and Alt+F10.** The probe found that Alt+F10 answers 是(Y) in a system Yes/No box raised from a dialog, which is how the dictionary delete confirmation is raised. The three boxes raised from the main window (delete document, delete all, overwrite) were not measured. This is pre-existing and outside F-13 (the user decided to leave these boxes as they are). Report only; a follow-up if the user wants it.

## User-Visible Defaults Introduced by This Spec (not decided by the user)

1. The focus rule of O1 (unchanged for the open document's failure).
2. The empty main window for a moment at startup (O2), and the trigger of O3.
3. No log line when exit skips `runtime.close()` (O4).
4. Raw control characters and line breaks in the removal list (O5).

## Out of Scope / Follow-ups

- **Item 5** (D5, Q1).
- **Alt+F10 and the existing four Yes/No boxes** (Q2; pre-existing).
- F-14: items 4, 7, 8.
- F-10 (UEB line breaks, `$`).
- Deferred and declined by the user on 2026-10-14: export `.tmp` retry, case-insensitive headers, F-9 M-5 (a failed case (b) save lost at close), the damaged `config.json` notice, F-11 M-4.
