# Localized Dialog Buttons, Surrogate-Safe Conversion and Export, Close Re-entry (F-7) Design

## Goal

Task F-7 bundles three hardening items of the error-message and close flows (HANDOFF `docs/superpowers/history/2026-10-10-02-handoff/HANDOFF.md` 5.2):

1. **F-W9** (`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`): dialog buttons show English labels.
   - The document name dialog, shown again after "already exists", has `OK` / `Cancel` instead of the translated labels. The first showing is translated.
   - Every production `wx.MessageBox` shows an English `OK` button.
2. **F-5 review M-7** (`docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/review_task.md`): a lone surrogate typed or pasted into the editor still reaches conversion and export, because only the `.dep` save replaces it (F-5 D4). Exporting the dual-view HTML then fails with `UnicodeEncodeError`, which `ExportCoordinator._write_single` does not catch: the export fails with no message.
3. **F-5 review M-5**: while the modal close dialog of F-5 is open, Windows logoff or shutdown sends `WM_QUERYENDSESSION`, wx sends another close event, and `BrailleFrame._on_close` runs again inside the dialog's modal loop.

Decided by the user (2026-10-10), HANDOFF 5.3; not asked again here:

- **U1.** F-7 is F-W9 + M-7 + M-5 and comes after F-6.
- **U2.** F-W9: only (a) and (b). (a) `localize_standard_buttons` searches only the dialog's own children. (b) The production `wx.MessageBox` calls are replaced by one shared helper built on `wx.MessageDialog` with `SetOKLabel(_("OK"))`. **Not** (c), a global `wx.Locale`.
- **U3.** M-7, in the spirit of F-5 D5: replace lone surrogates only in the text the program reads, never in the editor controls.

Also in scope, as recommended in HANDOFF 5.2 under decision U1:

- Export catches every `Exception`. A non-`OSError` is logged with its traceback, and the user sees the existing "export failed" message. This covers single export and the Export All batch.
- M-5 is first confirmed on a packaged build by sending `WM_QUERYENDSESSION` / `WM_ENDSESSION` (D9). Then a `_closing` re-entrancy guard is added: a re-entered close that can be vetoed is vetoed; one that cannot follows F-5 D8 (log and close).

After this task:

- Each standard button of the app's own dialogs is found among that dialog's children only. Every name dialog, including one shown again after "already exists", shows the translated labels. The zh-TW labels are U+78BA U+5B9A for OK and U+53D6 U+6D88 for Cancel.
- **Newly found and fixed with (a)** (see Current State): with the Settings or Text Processing dialog open, the dictionary editor's OK no longer closes the editor without saving.
- Every message box of the app shows the translated OK label. Yes/No boxes keep Windows' own Yes/No buttons, which are already localized. Each box keeps its icon, default button, keys and return value.
- Conversion and saving read the editors through `replace_lone_surrogates`. A pasted lone surrogate becomes U+FFFD in conversion, braille output, dual view and every export. The editors keep showing what the user typed.
- An export that fails for any reason shows the existing failure message, or is listed in the Export All summary, and Export All goes on with the next document. Unexpected errors are written to `gui.log`.
- A close that arrives while the close dialog is open is vetoed, so there is never a second dialog.

New user-visible strings: none. Every label used already has a translation: `OK`, `Cancel`, `Failed to export document: {error}`, and the Export All summary texts. The msgid count stays what it is on `main` after F-6. The F-6 count is not known when this spec is written; it is 357 before F-6.

Non-goals:

- a global `wx.Locale` and wx's own catalogs (U2);
- app-translated Yes/No labels (D4);
- replacing what the editors display (U3);
- lone surrogates in dictionary entries and the text-processing script (Out of Scope);
- a per-cause export message;
- any change to F-5's close dialog itself.

## Relation to F-6 (robustness)

F-6 is specified in parallel. It changes the Dictionary Management dialog in `client/dialog.py`, adds strings and may add message boxes, and it is merged into `main` before the F-7 plan is written. This spec is written to survive that:

- Call sites are named by function, not by line. The line numbers below are from `main` `e46ff26` and serve as orientation only.
- **Every `wx.MessageBox` call, and every `wx.MessageDialog` without full custom labels, that F-6 adds to production code is migrated to the helper too (D3).** The plan enumerates the call sites again on the post-F-6 `main` with the scan of Test Plan C1, and the scan tests keep it that way.
- F-6's tests that patch `wx.MessageBox` in `tests/test_dictionary_management_dialog.py` are pointed at the helper, like the existing ones (Test Plan C).
- The Windows verification items are numbered after F-6's: 53-64 (the plan's numbering; this spec first used the placeholders `4a`-`4l`).
- The baseline counts (`Ran`, msgids) are taken again on the post-F-6 `main` by the plan.

## Corrected after planning (2026-10-10)

The plan (`docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md`, dry-run on scratch clones of `d10dd94`: Tasks 0-4, 6 and 7 replayed exactly, every step also applied with the plan's own block script, and the GUI items 53-64 run against a packaged build of the same code and against `N-f6b`) found no error in decisions D1-D9 or in the behavior table. Where the plan refines this spec, this section wins. The Windows verification items `4a`-`4l` below are renumbered **53-64**; the manual NVDA item is **65**.

1. **Call sites after F-6** (`fb7aff9`): 20 production `wx.MessageBox` calls (7 in `dialog.py`, 11 in `gui.py`, 2 in `settings/dialogs.py`) plus the About box. F-6 added **site 21**, `BrailleFrame.on_open_dictionary_management` (its editor guard: `describe_unreadable_dictionary(...)`, `_("Error")`, `OK | ICON_ERROR`, `parent=self`); it is migrated like the others. F-6's Edit error box in Dictionary Management is site 6. F-6 added no `wx.MessageDialog` and no `FindWindowById`. Lines on `fb7aff9`: `dialog.py` 149, 166, 489, 500, 755, 758, 761 (sites 1-7); `gui.py` 446, 511, 705, 830, 859, 1075, 1078, 1083, 1111, 1115 (sites 8-17), 493 (`on_about`, site 20), 1010 (site 21); `settings/dialogs.py` 158, 695 (sites 18, 19). The two lookups of D1 are `dialog.py` 56 and 393.
2. **Counts.** Baseline `Ran 1337` (after F-6); per migration step `Ran 1342`, `1352`, `1355`, `1361`, `1365` (5, 10, 3, 6, 4 new tests, 28 in all), `FAILED (errors=1, skipped=7)` throughout, F-W6 only. msgids stay 364. The new tests beyond Test Plan A-E: `test_scan_reads_the_production_modules` (the scan is not empty), `test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text` (site 1 had no test) and `test_importing_binds_no_log_file` (item 7).
3. **Scan tests** (C1-C3) are in a new module `client/tests/test_wx_call_sites.py` (4 spaces); a hit reads `<file>:<class>.<function>`.
4. **Re-pointing** (C4) is done in the green step of migration step 2, not in its red step: a patch of `message_box` before the helper exists fails with `AttributeError` in every re-pointed test. The recorded events keep their label `"MessageBox"`. Site 18's existing test only checked that a box was shown; it now asserts message, caption, style and parent (C5).
5. **The editor harness** (`test_dictionary_entries_dialog.py`) keeps both lookups: `FindWindow` (the editor's own buttons) and `FindWindowById` modeled as wx's global search (an older dialog's buttons first, when a test sets them). The existing editor tests therefore pass before and after D1, and B3 sets the other dialog's buttons.
6. **Stub scopes:** `ui.message_box` is an `isolate` name of every scope whose code under test imports it (`wx_stub.load_speech_dialog`, `test_dialog_validation`, `test_converting_dialog`, `test_settings_dialogs`, `test_gui_document_flows`). The `gui_frame_stubs` `_MessageDialog` also gets `__enter__`/`__exit__` and a `ShowModal` returning `wx.ID_OK`, so an unpatched box still answers `wx.OK` like the old stub `wx.MessageBox`.
7. **D6's logger** is bound when an error is logged (inside `_log_unexpected_export_error`), not at import, as F-6 review M-6 did for `read_problems`; `test_export_coordinator` isolates `dotexpress.gui`.
8. **D6 also fixes P1-4 defect 7** (Export All with a format that has no writer raised `ValueError` without a summary); the test that pinned that KNOWN BUG is rewritten to the fixed behavior.
9. **Catalogs (D8):** byte-identical. A fresh `generate-pot.bat` differs from the committed template only in `POT-Creation-Date` and in `#:` reference lines (moved lines, and `ui/message_box.py` now refers to `OK` and `Cancel`); they stay until the next string change regenerates the template.
10. **GUI scripts and items:** `item53.py` (53, 56, 57), `item54.py` (54, 55), `item58.py` (58-60), `item61.py` (61-63), shared `f7gui.py`; 64 runs F-5's `item38.py` directly with `38` and `39` (F-5's `rerun.py` does not pass that argument). 56's failing document is a folder named `alpha.brl` in the export folder (overwrite question: Yes), not a lock. 61 first converts `A` U+FFFD `B` and compares: after F-7 the pasted surrogate gives the same braille (`⡳⠭⠋⠋⠋⠙`, the escape `\xfffd`); before, `⡳⠭⠙⠦⠒⠙` (`\xd83d`). 58 counts the process's top-level windows titled `無法儲存文件` and answers the topmost first; after F-7 the call returns at once (`0.0 s`, result 0), not "within about 1 s".
11. **62 and 63, Before:** no message, but an empty `alpha.html` is left (`Path.write_text` creates the file before the encoder fails); Export All leaves an empty `alpha.html`, no `new.html` and no summary. A writer that fails with any error can still leave an empty or partial file after F-7 (the writers are not atomic); follow-up.
12. **D9 confirmed by the planner** on `D:\dxtest\N-f6b\DotExpress.exe` (`fb7aff9`'s code): item 58 showed two close dialogs within 3 s, and the `SendMessageTimeoutW` call returned (`result 0`, after 3.6 s and 4.2 s in two runs) only when the inner dialog was answered. Item 55 on the same build: the editor showed `OK` / `Cancel`, and its OK closed without saving with either Text Processing or Settings open (`d1.csv` kept only its header). The plan's Task 5 repeats both before the D7 commit.
13. **Small fixes:** migration step 5 reads "(Before this step: D9, item 58 ...)"; acceptance criterion 2 adds `tests.test_wx_call_sites` and `tests.test_converting_dialog`; criterion 7's list adds `test_wx_call_sites.py`, `test_converting_dialog.py` and `test_dialog_validation.py`; `_editor_text` is annotated `control: wx.TextCtrl`; the docstring of `localize_standard_buttons` does not name `FindWindowById`, so a plain `grep` of the production code finds none.

## Current State (verified 2026-10-10 on `main` `e46ff26`, worktree `D:\workspace\DotExpress-f7`, Windows 11 26200)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13.15, wxPython 4.2.5 msw, wxWidgets 3.2.9). The prototypes behind this spec are in the session scratchpad `...\scratchpad\f7\` and are not committed:

- `probe_buttons.py`, `probe_flow.py` and `probe_modeless.py`: lookups and labels;
- `probe_esc.py`: keys;
- `probe_surrogate_conversion.py`: M-7;
- `probe_endsession.py`: M-5.

They create their own wx windows and read them through win32 (`EnumChildWindows`, `GetWindowText`, `TDM_CLICK_BUTTON`, `BM_CLICK`). No other window is touched, and no logoff or shutdown is requested.

Baseline, with the liblouis runtime and MathCAT copied as in F-3 plan Task 0: `cd client && $PY -B -X utf8 -m unittest discover -s tests` gives `Ran 1307 tests`, `FAILED (errors=1, skipped=7)`. The only error is F-W6 (`test_dictionary_name_prompt ... test_case_only_rename_still_renames`). `dotexpress.po`: `OK` -> U+78BA U+5B9A, `Cancel` -> U+53D6 U+6D88, `Apply`, `Close` translated. There is **no** msgid `Yes`, `&Yes`, `No` or `&No`.

### F-W9 (a): the button lookups in `client/dialog.py` (tabs)

`localize_standard_buttons(dialog, flags, button_sizer=None)` (`:37-57`) relabels the standard buttons it finds with `button = dialog.FindWindowById(button_id)`. If that finds nothing, it falls back to `button_sizer.GetAffirmativeButton()`, `GetCancelButton()`, `GetApplyButton()` and `GetCloseButton()`. There are five lookups of this kind (the handoff counts them as "5 call sites"):

| Where (function) | Call |
| --- | --- |
| `DictionaryNameDialog.__init__` | `localize_standard_buttons(self, wx.OK \| wx.CANCEL, button_sizer)` |
| `DocumentNameDialog.__init__` | same |
| `DictionaryEntriesDialog.__init__` | `localize_standard_buttons(self, wx.OK \| wx.CANCEL, button_bar)`, then `ok_button = self.FindWindowById(wx.ID_OK)` and `ok_button.Bind(wx.EVT_BUTTON, self._on_ok)` |
| `DictionaryManagementDialog.__init__` | `localize_standard_buttons(self, wx.CLOSE, button_bar)` |

Two more dialogs have standard buttons:

- `FileIssuesDialog.__init__` builds `CreateButtonSizer(wx.OK)` and never localizes it, so its OK is always English.
- `AddSymbolDialog`, `TextProcessingDialog` and `DotExpressSettingsDialog` create their buttons with explicit `_("OK")` / `_("Cancel")` labels and are not affected.

`FindWindowById` occurs nowhere else in production code.

**Measured** (`probe_buttons.py`, `probe_flow.py`, `probe_modeless.py`):

- `wx.Window.FindWindowById(id, parent=None)` is a static method in wxPython. Called as `dialog.FindWindowById(id)`, it does not pass the dialog as `parent`, so it searches every top-level window, oldest first. `dialog.FindWindow(id)` and `wx.Window.FindWindowById(id, dialog)` both return the dialog's own button.
- `Destroy()` on a dialog only schedules its deletion. The dialog stays in `wx.GetTopLevelWindows()` until the next idle event, and a native message box's modal loop does not run wx idle processing.
- Replaying `BrailleFrame._prompt_for_document_name` (show, end with OK, `Destroy`, "already exists" message box, new dialog; three rounds):
  - with `FindWindowById`, round 0 is translated and rounds 1 and 2 are `['OK', 'Cancel']`;
  - with `FindWindow`, every round is translated.
  - In each round exactly one destroyed name dialog was still a top-level window after the message box. **This confirms the root cause of the F-W9 symptom:** the new dialog's lookup relabels the buttons of the destroyed previous dialog, and its own buttons keep wx's untranslated stock labels `OK` / `Cancel`.
- The dictionary name prompt (`prompt_dictionary_name_until_success`: name dialog, `show_error`, name dialog again) follows the same pattern, so it has the same symptom (by code reading).
- `wx.StdDialogButtonSizer` in wxPython 4.2.5 has only `SetAffirmativeButton`, `SetCancelButton` and `SetNegativeButton`; the `Get*Button` getters do not exist. The sizer fallback of `localize_standard_buttons` therefore never finds a button on the shipping wxPython. Only the `FindWindowById` lookup works today.

**Newly found: the dictionary editor's OK can lose the edits** (measured in plain wx with `probe_modeless.py`; the app path is by code reading and is confirmed by GUI item 55).

- `TextProcessingDialog` and `DotExpressSettingsDialog` are modeless singletons, and each has a `wx.Button(self, wx.ID_OK, ...)`. While one of them is open, the user can open Dictionary Management and choose Edit.
- `DictionaryEntriesDialog.__init__` then finds **that dialog's** OK through `self.FindWindowById(wx.ID_OK)` and binds `_on_ok` to it. `_on_ok` is the handler that calls `self._model.save(...)`.
- The editor's own OK button keeps wx's default handling: `EndModal(wx.ID_OK)` without saving. `on_open_dictionary_management` ignores the result, so every edit made in that session of the editor is lost without a message.
- The probe: a modeless dialog with `ID_OK` open, then an editor-like modal dialog, then `BM_CLICK` on the editor's own OK. With `FindWindowById`: `ShowModal` returned `ID_OK` and the save handler did not run. With `FindWindow`: the handler ran.
- The same lookup also relabels the other dialog's buttons instead of the editor's, so the editor shows English `OK` / `Cancel`. With either modeless dialog open, the name dialogs are English even on their first showing.

### F-W9 (b): the message boxes

Production `wx.MessageBox` calls (`grep -rn "wx.MessageBox" client --include=*.py`, excluding `tests/`): **19**.

| # | File | Function | Style | Return value used |
| --- | --- | --- | --- | --- |
| 1 | `dialog.py:144` | `AddSymbolDialog._on_ok` | `OK \| ICON_INFORMATION`, `parent=self` | no |
| 2 | `dialog.py:161` | `_NameDialog._show_name_error` | `OK \| ICON_INFORMATION`, `parent=self` | no |
| 3 | `dialog.py:484` | `DictionaryEntriesDialog._show_duplicate_error` | `OK \| ICON_ERROR`, `parent=self` | no |
| 4 | `dialog.py:495` | `DictionaryEntriesDialog._on_ok` | `OK \| ICON_ERROR`, `parent=self` | no |
| 5 | `dialog.py:688` | `DictionaryManagementDialog.show_info` | `OK \| ICON_INFORMATION`, `parent=self` | no |
| 6 | `dialog.py:691` | `DictionaryManagementDialog.show_error` | `OK \| ICON_ERROR`, `parent=self` | no |
| 7 | `dialog.py:694` | `DictionaryManagementDialog.confirm` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`, `parent=self` | `== wx.YES` |
| 8 | `gui.py:445` | `BrailleFrame._show_file_error` | `OK \| ICON_ERROR`, `parent=self` | no |
| 9 | `gui.py:510` | `BrailleFrame.on_open_text_processing` | `OK \| ICON_ERROR`, `parent=self` | no |
| 10 | `gui.py:704` | `BrailleFrame._prompt_for_document_name` | `OK \| ICON_ERROR`, `parent=self` | no |
| 11 | `gui.py:829` | `BrailleFrame.on_delete_document` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`, `parent=self` | `!= wx.YES` |
| 12 | `gui.py:858` | `BrailleFrame.on_delete_all_documents` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`, `parent=self` | `!= wx.YES` |
| 13 | `gui.py:1062` | `BrailleFrame.show_info` | `OK \| ICON_INFORMATION`, `parent=self` | no |
| 14 | `gui.py:1065` | `BrailleFrame.show_error` | `OK \| ICON_ERROR`, `parent=self` | no |
| 15 | `gui.py:1070` | `BrailleFrame.show_warning` | `OK \| ICON_WARNING`, `parent=self` | no |
| 16 | `gui.py:1098` | `BrailleFrame.confirm_overwrite_all` | `YES_NO \| ICON_WARNING` (Yes is the default), `parent=self` | `== wx.YES` |
| 17 | `gui.py:1102` | `_show_application_data_error` (module level, startup) | `OK \| ICON_ERROR`, no parent | no |
| 18 | `settings/dialogs.py:158` | `TextProcessingDialog.on_apply` | `OK \| ICON_ERROR`, `parent=self` | no |
| 19 | `settings/dialogs.py:695` | `DotExpressSettingsDialog._collect` | `OK \| ICON_ERROR`, parent `self` **positional** | no |

`wx.MessageDialog` in production code:

- `BrailleFrame.on_about` (`gui.py:492`, `OK | ICON_INFORMATION`, no labels set): it also shows English `OK` (call site 20 below).
- F-5's `BrailleFrame._ask_after_close_save_failure` sets all three labels and is correct.

Every call passes an explicit icon. Indentation: `dialog.py` and `gui.py` use tabs, `settings/dialogs.py` uses 4 spaces.

**Measured** (`probe_buttons.py`, `probe_esc.py`). wxMSW shows these boxes as task dialogs.

| Box | Buttons (window text) | Focus | Return |
| --- | --- | --- | --- |
| `wx.MessageBox(..., OK \| ICON_ERROR)` | `OK` (English) | `OK` | `wx.OK`; Esc and Enter both close it and return `wx.OK` |
| `wx.MessageDialog(..., OK \| ICON_ERROR)` + `SetOKLabel(<OK msgstr>)` | U+78BA U+5B9A | that button | `ID_OK`; Esc and Enter both close it with `ID_OK`; `SetOKLabel` returns `True` |
| same, `parent=None` | U+78BA U+5B9A | - | `ID_OK` |
| `wx.MessageBox(..., YES_NO \| NO_DEFAULT \| ICON_WARNING)` | U+662F `(&Y)`, U+5426 `(&N)`: **Windows' own common buttons**, already in the system language | No | `wx.NO` (`8`) for IDNO |
| `wx.MessageDialog(..., YES_NO \| NO_DEFAULT ...)` + `SetYesNoLabels(...)` | the given labels | No | `ID_YES` / `ID_NO` |
| `wx.MessageDialog(..., YES_NO ...)` (Yes default) + `SetYesNoLabels(...)` | the given labels | Yes | `ID_NO` for IDNO |

Conclusions:

- wx draws the OK of an OK-only box as a custom button labeled from wx's own catalog, which the app never loads; hence English `OK`.
- Yes/No boxes use Windows' common buttons, which the system labels. On this zh-TW system they are already Chinese.
- As soon as one label is set, wx draws every button of that box as a custom button, so a box with OK and Cancel must set both labels.
- `wx.MessageBox` is `wx.MessageDialog(parent, message, caption, style).ShowModal()` with the result mapped as `ID_OK -> OK`, `ID_YES -> YES`, `ID_NO -> NO`, `ID_CANCEL -> CANCEL`. The measured return values match that.

The existing GUI automation (`docs/superpowers/history/2026-10-09-03-windows-verification/auto/dx.py` `dismiss`, `docs.py`, `dicts.py`, and F-5's `f5gui.dismiss`) presses `OK` or U+78BA U+5B9A, and `dx.dismiss` also presses the Yes/No labels. The old scripts therefore keep working after F-7.

### M-7: where the editors are read (`client/gui.py`)

- `BrailleFrame._save_open_document` passes `text=self.input_txt.GetValue()` and `braille=self.output_txt.GetValue()` to `save_open_document`. F-5 D4 replaces lone surrogates later, in `prepare_document_for_save` and `_normalized`.
- `BrailleFrame.get_source_text` returns `self.input_txt.GetValue()` unchanged. `ConversionPresenter.convert` (manual conversion) and `_complete_manual` call it. `_complete_manual` stores the result as the open document's text in the controller.

There is no other `GetValue()` of `input_txt` or `output_txt`.

**Measured** (`probe_surrogate_conversion.py`, real liblouis from the worktree's runtime copy, default tables, `lang="zh_TW"`). The inputs were `A`+U+D83D+`B`, U+4E2D U+D83D U+6587, `abc` U+4E2D U+6587 U+DC00 ` def`, and U+D83D alone.

- Conversion succeeds. The braille shows the surrogate in liblouis' escape notation for an undefined character (`\xd83d`, as braille cells), and the display text contains no surrogate.
- Writing the result: BRL succeeds and DEP succeeds (F-5 D4). **HTML (dual view) raises `UnicodeEncodeError: 'utf-8' codec can't encode character '\ud83d' ... surrogates not allowed`**, because the dual-view segments carry the source text.
- With the input passed through `replace_lone_surrogates` first, all three writers succeed. The braille then shows the escape for U+FFFD (`\xfffd`).

The paths that reach the HTML writer:

- Export of the open document: `on_export_document` saves first, and the controller then holds clean text. But `ExportContext.dual_view_results` are the segments of the last conversion of the raw editor text.
- Export All of the same document, through the same segments.

`ExportCoordinator._write_single` catches only `OSError`, so the exception leaves the menu handler. wx prints it to a console the packaged build does not have, and the user sees nothing. In `_export_next`, `write_document` also catches only `OSError`: the batch stops at that document and no summary is shown. The browser dual view (`_open_dual_view_in_browser`) already catches `Exception`, so there the user sees "Failed to open dual view: ...".

### M-5: close re-entry

`BrailleFrame._on_close` (`gui.py:1010`):

1. The conversion check comes first.
2. `_save_open_document_before_close(evt.CanVeto())` runs (F-5 D6/D8). When a vetoable close fails to save, it shows `_ask_after_close_save_failure`, which runs a modal task dialog.
3. Then the event is vetoed, or the cleanup runs and `evt.Skip()` follows.

There is no re-entrancy guard. Only the frame binds this handler (`self.Bind(wx.EVT_CLOSE, self._on_close)`). The app does not override wx's session-end handling; `BrailleApp` defines only `OnInit` and `OnExit`.

**Measured** (`probe_endsession.py`). A frame's close handler shows a task dialog (vetoable close from `WM_CLOSE`). Another thread then sends `WM_QUERYENDSESSION` (`lParam = ENDSESSION_LOGOFF`) to the frame with `SendMessageTimeoutW`.

- **Handler as today:** the close handler is entered a second time (`depth 2`, `CanVeto True`) while the first dialog is open, and a second dialog opens on top of the first; both were counted. The `SendMessageTimeoutW` call returns only after the inner dialog is answered: result `0` (may not end) after about 2 s, the time the test took to answer.
- **With a `_closing` guard that vetoes a re-entered vetoable close:** the second entry vetoes at once. `SendMessageTimeoutW` returns within the same tick with result `0`. Only one dialog is open, and it is answered normally afterwards.
- **`WM_ENDSESSION` (`wParam = TRUE`) while the dialog is open:** the process exits at once with exit code 0, in both variants, and **no second close event is delivered**. wx 3.2's default `wxApp::OnEndSession` calls `OnExit()` and `exit()` instead of closing the window. The package on disk is then the last good save (F-3 atomic writes). F-5 D8's remark "wx only sends a non-vetoable close after the vetoable query-end-session close" therefore does not describe wx 3.2.9: a session end never produces a non-vetoable close event. A non-vetoable close comes only from `Close(force=True)`, which DotExpress never calls. D8's code path stays as a defensive branch.

So M-5 is confirmed in plain wx for `WM_QUERYENDSESSION`: the nested dialog, and a nested Close without saving destroying the frame under the outer dialog's modal loop. The packaged build is checked in D9 / item 58 before the guard is written.

### Tests that pin today's behavior

- `tests/test_dialog_display.py`: three tests of `localize_standard_buttons` set `dialog.FindWindowById`, one of them with the sizer fallback.
- `tests/test_dictionary_entries_dialog.py` (`editor.FindWindowById = self._find_window_by_id`, about line 330) feeds the editor's OK binding.
- `wx.MessageBox` is patched or recorded in:
  - `tests/test_dialog_validation.py` (about lines 264-285, 363);
  - `tests/test_dictionary_entries_dialog.py` (the harness's `MessageBox=self._message_box`);
  - `tests/test_dictionary_management_dialog.py` (about lines 365-393);
  - `tests/test_gui_document_flows.py` (more than 20 places, including the `setUp` of `DocumentWorkspaceFlowsCharacterizationTest`);
  - `tests/test_settings_dialogs.py` (about lines 174, 451).
- `tests/test_wx_stub.py` tests the stubs' own `MessageBox` and stays as is.
- `tests/test_export_coordinator.py` pins the `OSError` handling of both export paths and that the module imports neither `wx` nor `gui`.
- The F-5 close tests (`test_close_*`, about lines 2098-2372; `test_close_asks_presenter_before_saving`, about line 3910) pin the close flow.

## Decisions

**D1. A dialog's standard buttons are looked up among its own children (U2 a).**

- In `localize_standard_buttons`, `button = dialog.FindWindowById(button_id)` becomes `button = dialog.FindWindow(button_id)`.
  - `wxWindow::FindWindow(id)` searches the window and its descendants, so it finds the buttons that `CreateButtonSizer` created for this dialog, and nothing else.
  - The signature, the flag table, the labels and the `button_sizer` fallback stay unchanged. The fallback does nothing on wxPython 4.2.5 (Current State), but it is harmless and its test stays (Decided by orchestrator with the recommended default; user may override before merge).
- In `DictionaryEntriesDialog.__init__`, `ok_button = self.FindWindowById(wx.ID_OK)` becomes `ok_button = self.FindWindow(wx.ID_OK)`. This fixes the lost-edits defect.
- `FileIssuesDialog.__init__` calls `localize_standard_buttons(self, wx.OK, button_sizer)` inside its existing `if button_sizer:` block, so its OK is translated too. This applies the user's decision U2 to a dialog the handoff did not list (Decided by orchestrator with the recommended default; user may override before merge).
- Production code calls `FindWindowById` nowhere afterwards (scan test C3).

Rejected:

- `wx.Window.FindWindowById(id, dialog)`: correct, but easy to get wrong again, and the handoff named `FindWindow`.
- The sizer getters: they do not exist in wxPython 4.2.5.
- Giving each dialog explicit `wx.Button(self, wx.ID_OK, _("OK"))` buttons: more code per dialog, for the same result.

**D2. One shared helper: `client/ui/message_box.py` (new, 4 spaces) (U2 b).**

```python
"""``wx.MessageBox`` with the application's own button labels (F-7, F-W9).

wx draws the OK button of a message box with a label from its own catalog, which
DotExpress does not load, so ``wx.MessageBox`` shows an English "OK". Yes and No
are Windows' common buttons, which Windows labels in the system language.
"""

from __future__ import annotations

import wx

from i18n import _


def message_box(message: str, caption: str, style: int, parent: wx.Window | None = None) -> int:
    """Show a message box like ``wx.MessageBox``: same arguments and return values.

    Returns ``wx.OK``, ``wx.YES``, ``wx.NO`` or ``wx.CANCEL``. An OK button (and a
    Cancel button next to it) gets the translated label; a Yes/No box keeps the
    system's labels.
    """
    with wx.MessageDialog(parent, message, caption, style) as dialog:
        if not style & wx.YES_NO:
            if style & wx.CANCEL:
                dialog.SetOKCancelLabels(_("OK"), _("Cancel"))
            else:
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)
```

- **The drop-in contract.** The parameters keep the order and meaning of `wx.MessageBox(message, caption, style, parent)`, including a positional `parent` (site 19). The return values are wx's own mapping (Current State); `ID_CANCEL` and anything unexpected map to `wx.CANCEL`, as in `wxMessageBox`. `wx.HELP` is not supported, and no site uses it. The style goes to `wx.MessageDialog` unchanged, so icon, `NO_DEFAULT` and the Yes default stay the same.
- **Labels.**
  - OK only: `SetOKLabel(_("OK"))`.
  - OK with Cancel (no site today; for future callers): `SetOKCancelLabels(_("OK"), _("Cancel"))`. Once one label is set, every button is custom (measured), so both are set.
  - Yes/No: no label at all (D4).
  - A setter that returns `False` (no shipping platform does) leaves the platform labels; the box still works.
- **Keys and accessibility.** It is the same task dialog wx showed before, now with a translated OK: Enter and Esc both close an OK box (measured), the focus starts on the default button, and NVDA reads it as before with the new label.
- `from __future__ import annotations` keeps the `wx.Window` annotation unevaluated, so the module imports cleanly under every test stub.

Rejected:

- `wx.GenericMessageDialog`: not native, with different focus and accessibility.
- Calling `localize_standard_buttons` on the task dialog: it has no wx child buttons.
- A per-call-site `SetOKLabel`: twenty copies.

**D3. Every message box goes through the helper.**

- The 19 `wx.MessageBox(...)` calls (Current State table) become `message_box(...)` with the same arguments.
- `BrailleFrame.on_about` becomes `message_box(about.aboutMessage, _("About DotExpress"), wx.OK | wx.ICON_INFORMATION, parent=self)`; this is call site 20.
- `dialog.py`, `gui.py` and `settings/dialogs.py` import it with `from ui.message_box import message_box`. Each call keeps its message, caption, style, parent and its use of the return value, so the confirmations still compare with `wx.YES`.
- F-5's `_ask_after_close_save_failure` stays a direct `wx.MessageDialog`, because it already sets all its labels.
- **F-6:** any `wx.MessageBox` call, or any `wx.MessageDialog` that does not set every label, that F-6 adds to production code is migrated the same way.
- Afterwards no production module contains `wx.MessageBox`. Every production `wx.MessageDialog` is either in `ui/message_box.py` or in `BrailleFrame._ask_after_close_save_failure` (scan tests C1, C2).

**D4. No new strings; Yes/No stay the system's buttons.**

- The helper uses only `OK` and `Cancel`, which are already translated.
- Yes/No boxes (sites 7, 11, 12, 16) are not given app labels. They already show the system's localized Yes/No (measured on this zh-TW Windows), and app labels would need two new msgids. On a Windows with another display language they stay in that language, exactly as today.
- (Decided by orchestrator with the recommended default; user may override before merge. App-translated `&Yes` / `&No` would be a small follow-up with two new msgids.)

**D5. The editors are read through the surrogate replacement (M-7, U3).** `BrailleFrame` gets:

```python
def _editor_text(self, control) -> str:
	"""The control's text with each lone surrogate replaced by U+FFFD (F-7, M-7); the control is not changed."""
	return replace_lone_surrogates(control.GetValue())
```

- `_save_open_document` passes `text=self._editor_text(self.input_txt)` and `braille=self._editor_text(self.output_txt)`.
- `get_source_text` returns `self._editor_text(self.input_txt)`.
- `replace_lone_surrogates` comes from `documents.workspace`, which `gui.py` already imports from. Clean text is returned as the same object, and the check costs about 1.7 ms for 550,000 characters (F-5 measurement).
- Nothing calls `SetValue` (U3, F-5 D5): the caret does not move and NVDA does not re-read.
- F-5 D4 in the documents layer stays as the second line of defense for every writer.
- Effects:
  - Conversion, its braille, the dual-view segments and the controller copy stored by `_complete_manual` all hold U+FFFD.
  - The braille of such a character changes from liblouis' escape for the surrogate (`\xd83d`) to the escape for U+FFFD (`\xfffd`). Both stand for a character that the user cannot see and that was never valid text.
  - The save comparison of F-5 D2 is unchanged, because `prepare_document_for_save` gets the same text it produced before.
- Nothing is logged: the replacement is an expected repair, as in F-5 D5.

**D6. Export reports every failure (M-7, HANDOFF 5.2).** In `client/documents/export_coordinator.py` (4 spaces):

- `_write_single`: `except OSError` becomes `except Exception as exc`. It calls `self._log_unexpected_export_error(exc)` and shows the existing `_("Failed to export document: {error}").format(error=exc)` with caption `_("Error")`. The success message is not shown.
- `_export_next.write_document`: `except OSError` becomes `except Exception as exc`, with the same logging, and `result.add_failure(document.name, str(exc))`. The batch then goes on with `continue_batch()`, exactly as for an `OSError`. The summary lists the failure.
- `_log_unexpected_export_error(error)` logs only non-`OSError`s, as F-3 review M-3 does for saving: `logger.error("Unexpected error while exporting a document", exc_info=error)`. An `OSError` is expected, and the message names it fully.
- `logger = get_logger("dotexpress.gui", "gui.log")` at module level, with `from log import get_logger`. This is the same logger and file as `gui.py`, so all unexpected errors are in one file (Decided by orchestrator with the recommended default; user may override before merge). The module still imports neither `wx` nor `gui`, so `test_module_imports_neither_wx_nor_gui` stays green.
- Both paths are covered: an export of a converted document and the `on_success` callback after a conversion for export. The conversion-failure callbacks are unchanged.
- Rejected: catching only `UnicodeEncodeError` (the review's narrower option). Any other writer bug would still be silent, which is what F-3 M-3 fixed for saving.

**D7. A close that arrives during a close is vetoed (M-5).** In `client/gui.py` (tabs), on `BrailleFrame`:

```python
	# Class attributes, so frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False

	def _on_close(self, evt: wx.CloseEvent):
		if self._closing:
			self._on_close_reentered(evt)
			return
		self._closing = True
		try:
			self._close(evt)
		finally:
			self._closing = False

	def _close(self, evt: wx.CloseEvent) -> None:
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		may_close = self._save_open_document_before_close(evt.CanVeto())
		if self._close_finished:
			# A nested close that could not be vetoed already closed the frame (M-5).
			return
		if not may_close:
			evt.Veto()
			return
		self._finish_close(evt)

	def _on_close_reentered(self, evt: wx.CloseEvent) -> None:
		"""A close event while another close is still asking (F-7, M-5).

		Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs.
		A close that can be vetoed is vetoed: the open dialog decides. One that cannot
		follows F-5 D8: one save attempt, a logged failure, and the frame closes.
		"""
		if evt.CanVeto():
			evt.Veto()
			return
		self._save_open_document_before_close(False)
		self._finish_close(evt)

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
			self._dual_view_frame = None
			viewer.Destroy()
		evt.Skip()
```

`_save_open_document_before_close` gets one line after `answer = self._ask_after_close_save_failure(error)`: `if self._close_finished: return True`. When a nested non-vetoable close has already finished, the outer loop neither retries nor asks again. `_close` then returns without `Veto` or `Skip`.

- **Vetoable re-entry** (the measured case, `WM_QUERYENDSESSION` while the dialog is open): the nested event is vetoed at once. There is no second save attempt, no second dialog, and no log entry (it is expected, not an error). For a real logoff, Windows then lists DotExpress as preventing sign-out. The user goes back to the open dialog, which still decides. This matches the intent of F-5 B (never lose edits silently).
- **Non-vetoable re-entry** (defensive: a session end does not produce one in wx 3.2.9, see Current State): F-5 D8 once. The save is attempted, a failure is logged as `Failed to save the open document while closing`, and the cleanup and `Skip` run.
- `_closing` is reset in `finally`, so the next close after a veto or an exception works. `_close_finished` is never reset: the frame is going away.
- Behavior without re-entry is unchanged, line for line: the conversion check, the F-5 dialog loop, D8, the cleanup and `Skip`.
- Rejected:
  - Disabling the handler with `Unbind` during the dialog: then a re-entered close would get wx's default handling, which destroys the frame.
  - A counter instead of a flag: there is never more than one level to allow.

**D8. No catalog change.** `dotexpress.pot`, `.po` and `.mo` are not regenerated. The plan checks that the AST msgid scan and `msgfmt --statistics` give the same numbers before and after.

**D9. M-5 is confirmed on a packaged build before D7 is written.**

1. The implementation agent builds the pre-F-7 `main` (after F-6, or reuses that task's build).
2. It runs item 58 against it (Windows Verification).
3. It records the nested dialog and the blocked `SendMessageTimeoutW` in the history folder.
4. Only then is the D7 commit written.

If the packaged build does **not** re-enter, the agent stops before the D7 commit and reports to the orchestrator, because the plain-wx probe predicts that it does. Messages are only sent to DotExpress's own main window. Never call `ExitWindowsEx`, `InitiateSystemShutdownEx`, `shutdown.exe` or `logoff`.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Name dialog (document or dictionary), first showing, nothing else open | translated OK / Cancel | identical |
| Name dialog shown again after "already exists" | English `OK` / `Cancel` (F-W9) | translated |
| Any name dialog or the dictionary editor while Settings or Text Processing is open | English `OK` / `Cancel`; the other dialog's buttons are relabeled | translated; the other dialog is untouched |
| Dictionary editor OK while Settings or Text Processing is open | **closes without saving; the edits are lost silently** | saves (or shows "Failed to save: ..."), then closes |
| Dictionary editor OK otherwise | saves, closes | identical |
| File-issues dialog (import skipped files) | English `OK` | translated |
| Every OK-only message box (sites 1-6, 8-10, 13-15, 17-20) | English `OK`; Enter or Esc closes | translated OK; Enter or Esc closes; same text, caption, icon and owner |
| Yes/No confirmations (sites 7, 11, 12, 16) | system Yes/No, `No` default (7, 11, 12) or `Yes` default (16) | identical (same dialog; no labels set) |
| F-5 close dialog | Retry / Close without saving / Cancel | identical |
| Convert with a lone surrogate in the input | succeeds; the braille shows the escape of the surrogate | succeeds; the braille shows the escape of U+FFFD; the editor still holds the surrogate |
| Export HTML (dual view) after that conversion | `UnicodeEncodeError` escapes; no message, no file | succeeds; the file holds U+FFFD |
| Export All after that conversion | stops at that document; no summary | completes; summary as usual |
| Export, writer raises any non-`OSError` (a bug) | escapes; no message; Export All stops | "Failed to export document: ..." (single) or listed in the summary (batch); traceback in `gui.log`; the batch goes on |
| Export, writer raises `OSError` | message / summary | identical; not logged |
| Save with a lone surrogate in an editor | saved as U+FFFD (F-5) | identical (also replaced at the read) |
| `WM_QUERYENDSESSION` while the close dialog is open | nested `_on_close`: a second save, a second dialog; Windows waits until the inner one is answered | vetoed at once; one dialog; Windows sees "may not end" |
| `WM_QUERYENDSESSION`, no close in progress | `_on_close` as F-5 (closes, or asks if the save fails) | identical |
| `WM_ENDSESSION` (forced logoff) | wx calls `OnExit` and exits; no close event; package = last good save | identical |
| Non-vetoable close while a close is in progress (`Close(True)`, not used by the app) | nested D8 runs, then the outer dialog continues on a frame being destroyed | D8 once; the outer stops after its dialog returns |

## Design per File

### `client/ui/message_box.py` (new, 4 spaces)

D2. The module docstring is as in D2.

### `client/dialog.py` (tabs)

- `localize_standard_buttons`: `dialog.FindWindow(button_id)` (D1). The docstring gains "Only the dialog's own children are searched (F-W9)."
- `DictionaryEntriesDialog.__init__`: `self.FindWindow(wx.ID_OK)` (D1).
- `FileIssuesDialog.__init__`: `localize_standard_buttons(self, wx.OK, button_sizer)` (D1).
- `from ui.message_box import message_box`; sites 1-7 call it (D3).

### `client/gui.py` (tabs)

- `from ui.message_box import message_box`; sites 8-17 and `on_about` call it (D3).
- `_editor_text`, `_save_open_document`, `get_source_text` (D5); `replace_lone_surrogates` added to the existing `from documents.workspace import (...)`.
- `_closing`, `_close_finished`, `_on_close`, `_close`, `_on_close_reentered`, `_finish_close`, and the one-line check in `_save_open_document_before_close` (D7).

### `client/settings/dialogs.py` (4 spaces)

`from ui.message_box import message_box`; sites 18 and 19 call it, site 19 still with a positional `self` (D3).

### `client/documents/export_coordinator.py` (4 spaces)

D6: `from log import get_logger`, `logger`, `_log_unexpected_export_error`, and the two `except Exception` blocks. The module docstring gains "Every write failure is reported: an `OSError` by its message, anything else also with its traceback in `gui.log`."

### `client/tests/wx_stub.py` (4 spaces)

- `gui_frame_stubs()`: `_MessageDialog` gains `SetOKLabel`, `SetOKCancelLabels` and `SetYesNoLabels`, each returning `True` (the real signatures).
- Each `StubScope` whose code under test imports `ui.message_box` (directly or through `dialog`, `gui` or `settings.dialogs`) keeps that module out of the shared module table, through `isolate` or its `evict` rule. Otherwise the scope raises `StubLeakError`. The plan picks the mechanism per scope.

### Not changed

- F-5's close dialog and `_save_open_document_before_close` apart from the one line;
- `documents/workspace.py`, `documents/workspace_service.py`, `documents/formats.py` and `ui/conversion_presenter.py`;
- the dual-view modules;
- `client/locales/`, `client/braille/` and `client/dictionary/`;
- the package format.

## What Stays Identical

- Every message, caption, icon, default button and owner of every box. Yes/No labels. Every return value and decision the code takes from a box.
- The first showing of every name dialog. Every dialog's layout, focus and accelerators.
- Text without lone surrogates: conversion input, braille, packages and exports are byte-identical.
- The editors' contents. The F-5 save comparison, close dialog, D8 and the vetoed close during conversion.
- Exports that succeed or fail with an `OSError`: the same messages and summary.
- Both fixture sha256 values. The catalogs.

## User-Visible Strings

None new (D4, D8). Labels that change:

| Where | Before | After (msgid) |
| --- | --- | --- |
| OK button of every OK-only message box and of the About box | `OK` | `OK` -> U+78BA U+5B9A |
| Name dialogs shown again; any standard-button dialog while Settings or Text Processing is open | `OK` / `Cancel` | `OK`, `Cancel` -> U+53D6 U+6D88 |
| File-issues dialog | `OK` | `OK` |

## Test Plan

TDD: each step's new tests are written first and fail for the stated reason, then the code turns them green. Every test file keeps its indentation; `test_dialog_display.py` uses tabs, and the files named below otherwise use 4 spaces. Tests use temporary directories only and never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/`. Every test that makes the code log uses `assertLogs`, which replaces the handlers, so nothing is written to `client/log/gui.log`.

### A. Helper (`client/tests/test_message_box.py`, new, 4 spaces)

The module has its own `StubScope` with a minimal fake `wx`:

- distinct values for `OK`, `CANCEL`, `YES`, `NO`, `YES_NO` (`YES | NO`), `NO_DEFAULT`, the `ICON_*` flags, `ID_OK`, `ID_CANCEL`, `ID_YES` and `ID_NO`;
- a recording `MessageDialog` that supports `with` and records the constructor arguments, each setter call and `ShowModal`; it answers from a queue and returns `True` from the setters unless told otherwise.

`ui.message_box` is isolated. The translations are the real catalog through `i18n`.

1. `test_ok_box_sets_the_translated_ok_label`: `(parent, message, caption, OK | ICON_ERROR)` reach `MessageDialog` unchanged. `SetOKLabel(_("OK"))` is the only setter, and `_("OK")` is the zh-TW msgstr. There is one `ShowModal`, and the dialog is closed (`__exit__`). It returns `OK` for `ID_OK`. Red: the module does not exist.
2. `test_ok_cancel_box_sets_both_labels`: `SetOKCancelLabels(_("OK"), _("Cancel"))`; `ID_CANCEL` -> `CANCEL`.
3. `test_yes_no_box_keeps_the_system_labels` (subTests: with `NO_DEFAULT`, without): no setter is called, the style is passed unchanged, `ID_YES` -> `YES` and `ID_NO` -> `NO`.
4. `test_unexpected_result_maps_to_cancel` (`ID_CANCEL` and an unknown id).
5. `test_parent_can_be_omitted_or_positional`: `message_box(m, c, s)` passes `None`; `message_box(m, c, s, frame)` passes `frame`.
6. `test_a_label_the_platform_refuses_still_shows_the_box`: the setter returns `False`; `ShowModal` is still called once.

### B. Button lookup (`client/tests/test_dialog_display.py`, tabs; `client/tests/test_dictionary_entries_dialog.py`)

1. The three existing `localize_standard_buttons` tests set `dialog.FindWindow` instead of `dialog.FindWindowById`. Red: today's code calls `FindWindowById`, which is a `Mock` returning another `Mock`, so the expected buttons get no label. The sizer test keeps `FindWindow` returning `None`.
2. `test_localize_ignores_buttons_of_other_windows`: `dialog.FindWindowById` returns a foreign button, and `dialog.FindWindow` returns the dialog's own. Only the own button is relabeled, and `FindWindowById` is not called.
3. `test_entries_dialog_binds_ok_to_its_own_button`: the harness's `editor.FindWindowById` hook becomes `editor.FindWindow`. A new test gives `FindWindowById` a foreign button and checks that `_on_ok` is bound to the button from `FindWindow`.
4. `test_file_issues_dialog_localizes_its_ok_button` (in the module whose stub can build `FileIssuesDialog`; the plan picks it): `localize_standard_buttons` is called with `(dialog, wx.OK, button_sizer)`.

### C. Call sites

1. `test_no_production_module_calls_wx_message_box`: an AST scan of every `.py` under `client/`, excluding `tests/`, `.venv/`, `build/`, `dist/`, `mathcat/` and `braille/liblouis/`. It finds no attribute `MessageBox` on a name `wx`. Red: 19 hits (more if F-6 adds some).
2. `test_message_dialogs_are_the_helper_or_set_every_label`: every `wx.MessageDialog` call in the same scan is in `ui/message_box.py` or in `BrailleFrame._ask_after_close_save_failure`. Red: `on_about`.
3. `test_no_production_code_searches_windows_by_id_globally`: no `FindWindowById` attribute in the scan. Red: two hits in `dialog.py`.
4. **Re-pointed tests.** Every test that patches or records `wx.MessageBox` for production code now patches the module global `message_box` of the module under test (`gui.message_box`, `dialog_module.message_box`, `settings.dialogs.message_box`). The fake keeps the signature `(message, caption, style, parent=None)` and the return values, so every existing assertion on message, caption, style, parent and answers stays as it is. That includes the `setUp` of `DocumentWorkspaceFlowsCharacterizationTest`, the dictionary editor harness, the management dialog tests, the validation tests and the settings tests. F-6's new tests are re-pointed the same way.
5. **Coverage per site.** Each of the 20 sites is exercised by at least one test that asserts the `message_box` arguments, either an existing test (re-pointed) or a new one. The plan lists which. `test_about_box_uses_the_helper` is new and checks `(about.aboutMessage, _("About DotExpress"), OK | ICON_INFORMATION, parent=frame)`. Red: `on_about` uses `wx.MessageDialog`.

### D. Surrogates and export

GUI tests are in `client/tests/test_gui_document_flows.py`. Surrogate strings are written by script and checked by bytes, never typed through the Edit/Write tools (HANDOFF 2).

1. `test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor`: `input_txt` holds `A` + U+D83D + `B`. `frame.get_source_text()` returns `A` + U+FFFD + `B`. The editor still holds the surrogate, and no `SetValue` event is recorded. Red: the raw value is returned.
2. `test_save_reads_both_editors_through_the_replacement`: `patch.object(frame._workspace_service, "save_open_document", wraps=...)`. `_save_open_document` passes text and braille with U+FFFD, and both editors are unchanged. Red: the raw values are passed.
3. `test_manual_conversion_stores_replaced_text` (with the frame's view methods and a fake runner, as the existing conversion GUI tests do; the plan picks the harness): the controller copy after `_complete_manual` holds U+FFFD.

In `client/tests/test_export_coordinator.py`:

4. `test_single_export_error_that_is_not_an_os_error_shows_the_failure_message`: the writer (patched descriptor, as `test_write_document_uses_registry_writer` does) raises `ValueError("injected")`. `show_error(_("Failed to export document: {error}").format(error=...), _("Error"))` is shown; there is no success message; `assertLogs("dotexpress.gui", "ERROR")` sees one record with `exc_info` of the `ValueError`. Red: the exception escapes.
5. `test_single_export_os_error_is_not_logged`: `assertNoLogs`; the message is as before. This guards the existing behavior.
6. `test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure`: the real HTML writer with a dual-view segment whose source holds U+D83D shows the failure message with `surrogates not allowed`, and logs it. This pins the M-7 trigger at the coordinator. Red.
7. `test_export_all_goes_on_after_an_error_that_is_not_an_os_error`: three documents. The second one's write raises `ValueError("injected")`. The first and third are written, the summary warning lists the second with `injected`, and one log record is written. Red: the batch stops and no summary appears.
8. `test_pending_export_failure_after_conversion_is_reported`: the `on_success` path of `convert_for_export` with a raising writer shows the failure message. Red.

### E. Close re-entry (`client/tests/test_gui_document_flows.py`, the F-5 close tests' class)

The fake `MessageDialog` of that class gets an optional one-shot hook. The first `ShowModal` runs it (it calls `frame._on_close(inner_event)`) before it answers; later dialogs do not.

1. `test_close_reentered_while_the_close_dialog_is_open_is_vetoed`: the outer close is vetoable, the save fails, and the dialog hook sends an inner vetoable event. The inner event is vetoed and never skipped. Exactly one `MessageDialog` event is recorded, and the save is attempted once (`os.replace` call count). The outer answer `ID_CANCEL` then vetoes the outer event, and the package is unchanged. Red: today the inner close saves again and records a second dialog.
2. `test_close_reentered_that_cannot_be_vetoed_closes_once`: the hook sends a non-vetoable inner event, and the outer dialog's answer is `ID_YES` (retry). The inner run attempts the save once and logs `Failed to save the open document while closing` (`assertLogs`). Then `close_converting_dialog` is called once, the dual view is destroyed once, and the inner event is skipped. The outer neither retries (no second dialog) nor vetoes nor skips. Red: today the outer retries and asks again.
3. `test_close_works_again_after_a_vetoed_close`: the first close is answered `ID_CANCEL` (vetoed). The lock is released, and a second close saves and skips. This guards the `finally` reset; it is green before the change (the flag does not exist yet) and stays green.
4. `test_close_flag_is_reset_when_the_close_raises`: `_save_open_document_before_close` is patched to raise `RuntimeError`. `_on_close` propagates it, and `frame._closing` is `False` afterwards. Red: the attribute does not exist.

The existing F-5 close tests and `test_close_asks_presenter_before_saving` stay green unchanged. Their call order is unchanged, because `_close` is the former body.

### Counts

New tests: A 6, B 3 (+1 changed harness hook, 3 changed), C 4 (+ any site tests the plan finds missing), D 8, E 4, about 25. Re-pointed tests replace their assertions one for one. On Windows the expectation is `Ran` = the post-F-6 baseline + the new tests, `FAILED (errors=1, skipped=7)`, F-W6 only. The plan fixes the exact counts; the red/green intent is binding.

## Migration Steps (each step one green commit, red first)

1. `fix: look up standard dialog buttons among the dialog's own children (F-7)`: D1, B1-B4, C3.
2. `fix: show message boxes with the translated OK button (F-7)`: D2-D4. This adds `ui/message_box.py`, migrates the 20 sites (plus F-6's) and adds the `wx_stub` changes, with A1-A6, C1, C2, C4 and C5.
3. `fix: read the editors without lone surrogates (F-7)`: D5, D1-D3 of Test Plan D.
4. `fix: report every export failure (F-7)`: D6, Test Plan D4-D8.
5. (Before this step: D9, item 58 on the pre-F-7 build, recorded.) `fix: veto a close that arrives while another close is asking (F-7)`: D7, E1-E4.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only. Locale files are not touched (D8).

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, the runtime copied as in F-3 plan Task 0.

1. Full suite: no failure or error other than F-W6; `Ran` = the post-F-6 baseline + the new tests.
2. Focused: `$PY -m unittest tests.test_message_box tests.test_dialog_display tests.test_dialog_validation tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_export_coordinator tests.test_wx_stub -v` passes.
3. Scans: no `wx.MessageBox` and no `FindWindowById` in production code. Every production `wx.MessageDialog` is in the two allowed places.
4. Catalogs unchanged. `git diff main -- client/locales` is empty, the AST msgid scan gives the post-F-6 count, and `msgfmt --check --statistics` reports that count translated, 0 fuzzy and 0 untranslated.
5. Both fixture sha256 values unchanged (`translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`).
6. App data untouched: in the main checkout, `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after. In the worktree, no `client/log/`, `client/workspace/` or `client/config.json` is created by the tests.
7. `git diff main --stat` touches only `client/ui/message_box.py`, `client/dialog.py`, `client/gui.py`, `client/settings/dialogs.py`, `client/documents/export_coordinator.py`, `client/tests/wx_stub.py`, the test files named above, and the spec, plan and history files.
8. Mutation check (plan). Each mutant is caught by at least one test:
   - `FindWindow` reverted to `FindWindowById` in `localize_standard_buttons`, and separately in the entries dialog;
   - the helper without `SetOKLabel`;
   - the helper setting labels on Yes/No;
   - the helper returning the raw `ShowModal` value;
   - one call site reverted to `wx.MessageBox`;
   - `get_source_text` without the replacement;
   - the save read without the replacement (text, and separately braille);
   - `_write_single` back to `except OSError`;
   - the batch back to `except OSError`;
   - logging `OSError` too;
   - the guard removed;
   - the re-entry branch skipping instead of vetoing;
   - `_closing` not reset in `finally`;
   - the outer loop ignoring `_close_finished`.
9. Packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build as in F-5: the main checkout's `client\.venv\Scripts` first on `PATH`, then `scripts\build-dotexpress.bat`. Check in `client\build\DotExpress\PYZ-00.toc` and `Analysis-00.toc` that `ui\message_box.py`, `dialog.py`, `gui.py`, `settings\dialogs.py` and `documents\export_coordinator.py` come from the checkout being verified. Copy the exe to `D:\dxtest\N-f7\`.

"Before" is the build of `main` after F-6 (the F-6 task's build, or a new one). Each item runs in a new `D:\dxtest\auto<item>-f7` folder; the app's `dictionary\`, `workspace\` and `log\` live next to the copied exe. Only processes whose exe lies under those folders are ended (`dx.kill_under`, `taskkill /T` for helpers). The user may have DotExpress open.

The scripts go to the implementation's history folder `auto/`. They reuse, without editing:

- `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `dicts.py`, `lock.py`);
- `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`.

They run in the pywinauto venv (`$SP\uia`; rebuild it with `py -3.13 -m venv` and `pip install pywinauto==0.6.9 psutil` if missing). Message boxes and the F-5 dialog are task dialogs, so they are read through UIA, as in `f5gui.describe`: title, `MainInstruction`/`ContentText`, button names, focus.

Items are numbered 53-64, after F-6's 42-52 (assigned by the plan; the placeholders were `4a`-`4l`).

| # | Steps | Expected after F-7 | Before |
| --- | --- | --- | --- |
| 53 | Add `alpha`; Add again, type `alpha`, Enter | the "already exists" box: one button, the translated OK; Enter closes it; the name dialog shown again has the translated OK / Cancel, prefilled `alpha`; Esc cancels; the list is unchanged | box button `OK`; the dialog shown again has `OK` / `Cancel` (F-W9) |
| 54 | Dictionary Management: Add `d1`; Add again `d1` | as 53 for the dictionary name dialog; the "already exists" box has the translated OK | English, as 53 |
| 55 | Open Text Processing (keep it open), open Dictionary Management, select `d1`, Edit; Add the entry `x` / `1`; OK. Edit `d1` again | the editor's buttons are translated. OK saves: on reopening, `x` is listed and `dictionary\d1.csv` holds it. Then the Text Processing dialog's own Cancel closes it normally. Repeat with the Settings dialog open instead | **the editor's buttons are `OK` / `Cancel`; OK closes without saving: `x` is missing and `d1.csv` is unchanged** (records the newly found defect) |
| 56 | The OK-only boxes, one of each kind: the "already exists" error (53); "Conversion completed." after Ctrl+Enter; the About box; an Export All with one failing document (the summary warning; the plan names how to make one fail, for example a destination file held open by `lock.py`) | each shows its old text, caption and icon, the translated OK, focus on it; Enter closes one and Esc another | the same boxes with `OK` |
| 57 | Delete document `alpha` (No, then again Yes); Export All into a folder with a conflict (Overwrite: No) | system Yes/No labels as before; the focus is on No for Delete and on Yes for Overwrite; Alt+N / Alt+Y answer; No keeps the document / files | identical |
| 58 (D9) | `alpha` open; type an edit; `lock.py` holds `alpha.dep` (share `r`); post `WM_CLOSE`. The close dialog appears. From a driver thread: `SendMessageTimeoutW(main, WM_QUERYENDSESSION, 0, ENDSESSION_LOGOFF, SMTO_NORMAL, 10000)`. Count the `Cannot Save Document` dialogs under the main window for 3 s, and record the call's return time and result. Answer whatever is open with Esc; then unlock and close with Enter (Retry) | within about 1 s the call returns with result 0; there is exactly one dialog throughout; after Esc the app runs and the edit is in the editor; after unlock + Enter the app exits and `alpha` holds the edit after a restart | **two dialogs (nested); the call returns only after the inner one is answered** (confirms M-5) |
| 59 | `alpha` open and unchanged; send `WM_QUERYENDSESSION` as in 58 | the call returns 1; the app exits; `alpha.dep` unchanged | identical (harness check) |
| 60 | As 58 up to the dialog; send `WM_ENDSESSION` (`wParam` 1, `lParam` `ENDSESSION_LOGOFF`) | the process exits within 5 s with code 0; `alpha.dep` members are unchanged (the last good save), no `.tmp`; no new traceback in `log\gui.log` | identical (wx exits without a close event) |
| 61 | Paste `A` + U+D83D + `B` (`f5gui.paste_text_with_lone_surrogate`); Ctrl+Enter | "Conversion completed." with the translated OK; the braille shows the U+FFFD escape (`\xfffd` cells), not `\xd83d`; the editor still reads `A` + U+D83D + `B` | the braille shows the `\xd83d` escape |
| 62 | After 61: File > Export > HTML (dual view) to a new file | "The document was exported successfully."; the file exists and holds `EF BF BD`, no `ED A0 BD` | **no message, no file** |
| 63 | After 61: Export All as HTML into an empty folder | the success summary; one file per document | **no summary; the batch stops at `alpha`** |
| 64 | Re-run F-5 items 38 and 39 (the existing `item38.py` through `rerun.py`) | as recorded for F-5, except the Ctrl+Tab error box now shows the translated OK | the F-5 results |

Never trigger a real logoff or shutdown; messages go only to the test instance's main window. Items needing NVDA stay manual and are added to the user's list. The manual item (user): with NVDA, one OK box (56) and the re-shown name dialog (53) read the translated labels. This is item 65.

## Risks

- **Yes/No on a non-Chinese Windows** (low, D4). Unchanged: the system labels them. An English Windows shows English Yes/No beside Chinese text, as today.
- **`FindWindow` finds a nested child with the same id** (very low). None of the app's dialogs has two windows with the same standard id.
- **A changed label disturbs automation or NVDA habits** (low). The text is the translation the first showing already used. The old scripts accept both labels.
- **The `_closing` veto keeps Windows waiting at logoff** (by design). While the dialog is open, DotExpress answers "may not end", and Windows shows its "this app is preventing sign-out" screen. "Sign out anyway" ends the process through wx's `OnEndSession` (60); the edits since the last good save are then lost, and the package is intact. Today the same choice comes after a nested dialog.
- **Braille of a lone surrogate changes** (very low). It shows the U+FFFD escape instead of the surrogate's escape, for a character that was invisible and never valid.
- **`gui.log` from the documents layer** (low). The coordinator now imports `log`; a test that makes it log without `assertLogs` would write `client/log/gui.log` in the checkout. The test rule above, and acceptance 6, guard this.

## Open Questions

None for the user. The decisions U1-U3 are the user's (2026-10-10).

Decided by orchestrator with the recommended default; user may override before merge:

- **O1.** Yes/No boxes keep the system's labels; no new msgids (D4).
- **O2.** The helper is `client/ui/message_box.py`, `message_box(message, caption, style, parent=None) -> int`, a drop-in for `wx.MessageBox` (D2).
- **O3.** The About box and the file-issues dialog are included in F-W9 (D1, D3).
- **O4.** The dead `button_sizer` fallback of `localize_standard_buttons` is kept (D1).
- **O5.** Unexpected export errors are logged to `gui.log` with the `dotexpress.gui` logger; an `OSError` is not logged (D6).
- **O6.** A re-entered close that cannot be vetoed runs F-5 D8 once, and the outer close stops after its dialog returns. A vetoed re-entry is not logged (D7).
- **O7.** M-7 is applied in the GUI's editor reads (`_editor_text`); F-5 D4 stays in the documents layer (D5).
- **O8.** Source-scan tests guard against `wx.MessageBox`, unlabeled `wx.MessageDialog` and `FindWindowById`, including what F-6 adds (Test Plan C).
- **O9.** The dictionary editor keeps binding its OK button directly (`self.FindWindow(wx.ID_OK)`) instead of switching to `self.Bind(..., id=wx.ID_OK)` (D1).

## Out of Scope / Follow-ups

- **App-translated Yes/No** (`&Yes`, `&No`; two msgids) for non-Chinese Windows.
- **Lone surrogates in other inputs.**
  - A dictionary entry with one fails to save with "Failed to save: ..." (`DictionaryEntriesDialog._on_ok` catches it).
  - The text-processing script editor reports `UnicodeEncodeError` as a `ValueError` message.
  - Neither one hangs or loses data silently; they are unchanged.
- **F-5 spec D8's remark** about a non-vetoable close after the vetoable one: measured not to happen in wx 3.2.9 (Current State). The F-5 spec is not edited by this task. The review may add a note there.
- **The global `wx.Locale` and wx's catalogs** (U2 c, rejected).
- The F-5 follow-ups that are still open: U+0000 truncation, orphan `.tmp` recovery, and F-3 review M-1.
