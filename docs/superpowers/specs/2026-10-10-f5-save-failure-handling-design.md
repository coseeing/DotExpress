# Save-Failure Handling (F-5) Design

## Goal

Task F-5 fixes F-W10 and F-3 review M-4: when the open document cannot be saved, the app should still let the user leave it or quit.

1. **F-W10** (`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`, "新發現"): when the open document's `.dep` is read-only, or another program holds it open, every action that saves first fails. That covers switching documents, Rename, Delete, Import, Export and Close. Close is vetoed, so the app cannot exit until the lock or the attribute goes away. Unchanged documents are rewritten before these actions too, so the failure hits even when there is nothing to save. After F-3 (Q1 accepted) a package held open in **any** share mode blocks Save (`[WinError 5]`). That makes F-W10 more likely.
2. **F-3 review M-4** (`docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/review_task.md`): a lone surrogate in memory, typically from pasted text, makes every Save fail with `'utf-8' codec can't encode character '\ud800' ... surrogates not allowed`. The user cannot see the character, so they cannot fix it. Every action and Close stay blocked, and the only way out is to kill the process. That loses every edit since the last good save.

The user decided (2026-10-10):

- **A.** Skip the write when the open document has not changed. The comparison baseline is the content last written to disk successfully (or loaded from it), tracked separately and never taken from the controller. `save_open_document` updates the controller before it writes, so after a failed save the controller already holds the unsaved text.
- **B.** If saving fails on Close, show a dialog with **Retry / Close without saving / Cancel**. Close without saving discards the edits made since the last good save.
- **C.** Every other action keeps blocking with the existing message when its save fails. With A, that only happens when there are real changes.
- **D.** On save, lone surrogates become U+FFFD, so a save can always encode.
- F-3 Q1 stands: a package held open by another program blocks saving. With A this only matters when the document has changed.

After this task:

- The service remembers, per document, the content last written or loaded and the package's size and modification time. Save writes only when the prepared document differs from that record, or when the package on disk is not the one recorded. The record changes only after a successful write or a load, so a failed save is retried by the next action.
- An unchanged document whose package is read-only, locked, on a full disk or otherwise unwritable no longer blocks switching, Add, Import, Export or Close. Rename and Delete still apply their own rules to that package: F-3 D7 refuses to rename a read-only package, and Windows refuses to delete one.
- If saving fails on Close, the dialog shows the existing message (`Failed to save document: {error}`), a sentence saying the changes since the last good save will be lost if the user closes without saving, and three localized buttons. Retry is the default.
- Text and braille never reach the writer with a lone surrogate, so this fault no longer happens.

New user-visible strings: 4 (msgids 353 -> 357), translated in `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, with `.pot` and `.mo` regenerated.

Non-goals: a "modified" mark in the title bar, a Save command, autosave, recovery of `.tmp` leftovers (F review M-2), F-3 review M-1 (Add, Rename and Import overwriting a kept invalid `.dep`), a clearer message per cause (locked vs read-only), the delete rules, and the conversion of text that holds a lone surrogate.

## Current State (verified 2026-10-10 on `fix/f5-save-failure-handling`, HEAD `918c251`, Windows 11 26200, NTFS)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13.15, wxPython 4.2.5 msw, wxWidgets 3.2.9). `$SP` is the session scratchpad. The prototypes behind this spec are in `$SP\f5spec\` (`dlg.py`, `drive.py`, `probe.py`, `surrogates.py`; not committed). The UIA driver runs in `$SP\uia` (pywinauto 0.6.9, psutil 7.2.2).

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1270 tests`, `FAILED (errors=1, skipped=7)`. The only error is F-W6 (`test_dictionary_name_prompt ... test_case_only_rename_still_renames`). Source msgids: 353; `dotexpress.po` has 354 `msgid` lines including the header. `xgettext`, `msgmerge` and `msgfmt` are installed (`C:\Program Files\gettext-iconv\bin`).

### Save of the open document

`DocumentWorkspaceService.save_open_document` (`client/documents/workspace_service.py:79-86`, 4 spaces):

```python
document = self._controller.get_document(self._controller.open_document_name)
if document is None:
    return None
updated_document = prepare_document_for_save(document, text=text, braille=braille)
self._controller.replace_document(updated_document)      # memory first (documented contract)
save_document_package(self.package_path(updated_document.name), updated_document)
return updated_document
```

`prepare_document_for_save` (`client/documents/workspace.py:248-255`) keeps `braille=None` (pending: written with `<name>.meta.json`) when the controller copy is pending, so the braille editor is ignored. Otherwise it takes the editor's braille. Since F-3, `save_document_package` writes through `write_bytes_atomically`, so a failed save leaves the package byte-identical. Memory is already updated by then. **A comparison against the controller copy would treat a failed save as saved, and the retry would skip the write. That is data loss.**

Memory can also change without any write. `ConversionPresenter._complete_manual` (`client/ui/conversion_presenter.py:198-209`) replaces the open document in the controller with the editor text and the new braille, and nothing is written until the next save.

### Callers in `client/gui.py` (tabs)

| Line | Handler | Behavior on a failed save |
| --- | --- | --- |
| 592-599 | `_open_adjacent_document` (Ctrl+Tab, Ctrl+Shift+Tab) | `_save_open_document_with_feedback()` shows `Failed to save document: {error}`; the switch does not happen |
| 735-742 | `on_open_document` (Open, Enter, double click) | same |
| 744-750 | `on_add_document` | same, before the name dialog |
| 752-778 | `on_rename_document` | same, before the name dialog |
| 780-808 | `on_delete_document` | same, before the confirmation |
| 810-839 | `on_delete_all_documents` | same |
| 841-869 | `on_import_document` | same, before the file dialog |
| 871-878 | `on_export_document` | same |
| 880-885 | `on_export_all_documents` | same |
| 909-918 | `on_output_text_key_down` (Ctrl+E, export BRL) | same |
| 967-980 | `_on_close` | conversion running and vetoable: veto, no save. Otherwise the save fails, the message box appears, and the close is vetoed if `CanVeto()`; if it cannot be vetoed, it returns without `Skip` |

`_save_open_document_with_feedback` (`:607-613`) catches `Exception` and calls `_show_document_save_error` (`:452-461`). That method logs non-`OSError` tracebacks to `gui.log` (F-3 review M-3) and shows `wx.MessageBox(..., _("Error"), wx.OK | wx.ICON_ERROR)`.

### Measurements (prototypes)

**Dialog** (`dlg.py` run with `$PY`, driven by `drive.py` through UIA). This is `wx.MessageDialog(parent, error_line, "無法儲存文件", wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR)` with `SetExtendedMessage(question)` and `SetYesNoCancelLabels("重試(&R)", "不儲存就關閉(&W)", "取消")`:

- `SetYesNoCancelLabels` returns `True`. wxMSW shows a Windows task dialog (`#32770`), owned by the frame: in the UIA tree it is a child of the main window, not a top-level window.
- UIA tree: `Image MainInstructionIcon`, `Text` with automation id `MainInstruction` (the error line), `Text` with automation id `ContentText` (the extended message), `Button` named `重試(R)`, `Button` named `不儲存就關閉(W)`, `Button` named `取消`, and the title bar with the system close button. All labels are the ones passed in. The `&` becomes the underlined mnemonic and is dropped from the UIA name. Nothing is English. `FindWindowById` is not involved, so F-W9 cannot recur here.
- Focus starts on `重試(R)`. Keys: Enter -> `ID_YES`, Esc -> `ID_CANCEL`, Alt+R -> `ID_YES`, Alt+W -> `ID_NO`, Tab then Enter -> `ID_NO`. A plain `W` without Alt does nothing in a task dialog.
- Passing the two paragraphs as one message with a blank line between them gives the same main-instruction/content split. `SetExtendedMessage` states that split explicitly.
- The prototype's content sentence differed slightly from the final wording in "User-Visible Strings". The layout is the same.

**Editor round trip** (`probe.py`, `wx.TextCtrl` with `wx.TE_MULTILINE`, the input and the read-only output style): `SetValue(x)` then `GetValue()` returns `x` unchanged for LF, a trailing LF, tab, NBSP, braille, astral characters (`U+1F600`) and lone surrogates (`a\ud800b`). `\r\n` and `\r` come back as `\n`. **`a\x00b` comes back as `a`**: the Edit control stops at U+0000.

**Package fingerprint** (`probe.py`, `os.stat` of a saved `alpha.dep`): `(st_size, st_mtime_ns)` stays the same after `attrib +r`, `attrib -r`, `attrib +h`, and while another handle holds the file open with share read, read+write or none. `os.stat` works in all of these cases. A failed `save_document_package` leaves it unchanged. Rewriting the same content changes `st_mtime_ns`.

**Lone-surrogate replacement** (`surrogates.py`): `text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")` gives one U+FFFD per lone surrogate (`a\ud800b` -> `a\ufffdb`, a reversed pair -> two U+FFFD, `\udcff` -> one U+FFFD). It joins a split pair (`\ud83d\ude00` -> U+1F600) and leaves everything else alone. The UTF-8 variant gives three U+FFFD per surrogate. The `encode("utf-8", "replace")` that M-4 suggested gives `?`. On 550,000 characters, a `re.search("[\ud800-\udfff]")` scan of clean text takes 1.7 ms and the replacement on dirty text 2.9 ms. Comparing two equal strings of that length takes 0.65 ms.

### Tests that pin today's behavior

- Lone surrogate as the non-`OSError` fault (F-3 D9 and M-3). These stop failing once D4 is in:
  - `test_document_workspace.py`: `test_save_failure_from_a_lone_surrogate_keeps_the_existing_package` and `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`.
  - `test_workspace_service.py`: `test_save_failure_keeps_the_package_and_updates_memory`.
  - `test_gui_document_flows.py`: `test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`, `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`, `test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`, `test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback` and `test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback`.
- Close: `test_close_vetoes_when_save_fails` (error box and veto) and `test_close_asks_presenter_before_saving` (which mocks `_save_open_document_with_feedback`).
- Save always writes: no test asserts that an unchanged document is rewritten. Every GUI and service test builds its controller directly (`_make_workspace_frame`, `_service`), not through `load_documents`, and D3's "no record: write" rule keeps those tests valid.

## Decisions

**D1. The baseline is a per-document "saved record" in `DocumentWorkspaceService`, never the controller copy.** The service keeps `self._saved: dict[str, _SavedPackage]`. The key is the document name as the controller spells it. `_SavedPackage` is a frozen dataclass with `document: Document` (exactly what was written or loaded) and `fingerprint: tuple[int, int] | None` (`(st_size, st_mtime_ns)` of the package right after that write or load). The service is the only place that writes or loads packages, so it is the only place that knows what is on disk. The controller stays a pure in-memory model. Rejected:

- Comparing against the controller copy. The controller is updated before the write (the documented contract that F-3 kept), and conversion updates it without writing. A failed save followed by a retry would be skipped: data loss.
- A "dirty" flag set from `EVT_TEXT`. wx also sends it for `SetValue`, so loading or switching documents would set it. It misses conversion results and failed saves unless every path resets it correctly, and it cannot see a package that changed on disk.
- Content comparison without a fingerprint. If another program deletes or replaces the package while the app runs, an unchanged document would not be written back. Today's Save does write it back. Under "when in doubt, write", the fingerprint keeps that behavior (D2).

**D2. Definition of "unchanged".** Let `prepared = prepare_document_for_save(controller copy, text=editor text, braille=editor braille)`. This is computed after D4, so it holds no lone surrogate. Save skips the write only if all of these hold:

1. a record exists for `prepared.name`;
2. `prepared == record.document` (name, text, and braille including `None`; `None` is exactly "pending metadata written", because workspace saves always pass `include_pending_metadata=True`);
3. `_package_fingerprint(package_path(name))` is not `None` and equals `record.fingerprint`. `_package_fingerprint` calls `os.stat` and returns `None` on any `OSError` or when the path is not a regular file.

Anything else writes, exactly as today. Dual-view results are not part of a package and do not count. The controller is updated first in both cases. The write-or-skip decision is internal: `save_open_document` keeps its signature and returns `prepared` either way.

Consequences:

- A failed write leaves the record alone, so the retry sees `prepared != record.document` and writes.
- Reverting the text to the saved version after a failed save makes the document unchanged again, so it does not block.
- A conversion result changes `prepared.braille` (a pending document becomes non-pending), so it is written.
- The editor normalizes `\r\n` and `\r` to `\n` and cuts the text at U+0000 (Current State). A loaded document holding those characters counts as changed and is written once, as today. After that its record matches.

**D3. Record lifecycle (every path that writes, loads or removes a package).**

| Path | Record after success | After failure |
| --- | --- | --- |
| `load_documents` (startup) | replaced by the loaded documents, each with the fingerprint of `package_path(name)` | (nothing loaded) |
| `save_open_document`, written | `_saved[name] = (prepared, fingerprint after the write)` | unchanged (the old record or none); the controller holds `prepared` |
| `save_open_document`, skipped | unchanged | - |
| `create_document` (Add, the default `new` document) | `_saved[name] = (document as written, fingerprint)` | none added |
| `import_files` | one record per saved document | none for a document whose write failed |
| `rename_document` (regular and case-only) | `_saved.pop(source)`; `_saved[new] = (Document(new, source.text, source.braille) as written, fingerprint of the new path)` | unchanged (the old name keeps its record) |
| `delete_document` | `_saved.pop(name, None)` after the unlink | unchanged |
| `delete_all_documents`, completed | cleared | reloaded: replaced by the remaining documents, as in `load_documents` |
| Export as DEP (`formats._write_dep`, any user path) | unchanged | unchanged |
| Conversion (`_complete_manual`, memory only) | unchanged | - |
| Documents placed in the controller without the service (tests) | none, so every save writes | - |

"As written" means after D4's replacement. The service records `_encodable(document)`, the same value `_normalized` writes, so the next save compares equal. An Export as DEP aimed at the workspace's own `alpha.dep` changes the fingerprint, so the next save writes the workspace version again: that file was just replaced without its pending metadata.

**D4. Lone surrogates become U+FFFD in the documents layer.** `client/documents/workspace.py` gets the public function `replace_lone_surrogates(text: str) -> str`. If `[\ud800-\udfff]` does not occur, it returns `text` itself. Otherwise it returns `text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")`: one U+FFFD per lone surrogate, a split high-low pair joined into its character, nothing else changed. It is applied in two places:

- `prepare_document_for_save`, to the text and to the braille when it is kept (not `None`). The controller copy, the D2 comparison and the record therefore all hold the replaced text.
- `_normalized`, which every package writer goes through: Save, Add, Import, the staged package of every Rename (`PackageFiles.write`) and Export as DEP. A package write can therefore always encode.

Rejected: `encode("utf-8", "replace")` (M-4's suggestion) gives `?`, not U+FFFD. The UTF-8 `surrogatepass` round trip gives three U+FFFD per character. Writing with `surrogatepass` would make the package unreadable, because the loader decodes strictly.

**D5. The editors are not touched, and nothing is shown or logged.** After a save that replaced a surrogate, `input_txt` still holds it. Setting the control's value would move the caret and make NVDA re-read, in the middle of an action the user started. The surrogate was invisible anyway. The control is reloaded from the controller the next time a document is opened. Until then each save replaces it again, compares equal to the record (D2) and skips the write. Conversion still reads the control text (out of scope, see Out of Scope). Nothing is logged: `gui.log` is configured at `ERROR`, and this is a successful, expected repair, not an error.

**D6. Close asks when the save fails.** `_on_close`:

1. If a conversion is running and the event can be vetoed: veto, nothing saved (unchanged).
2. Try `_save_open_document()`. If it succeeds, or D2 skips it, close as today.
3. If it raises any `Exception` and the event can be vetoed: log it as M-3 does (non-`OSError` only, with traceback) and show the dialog (D7).
   - **Retry**: go back to step 2. If it fails again, the dialog appears again with the new error text.
   - **Close without saving**: close as today (`close_converting_dialog`, destroy the dual view, `evt.Skip()`). The package on disk is the last good save (F-3 guarantees that a failed write left it byte-identical). The edits in memory are dropped.
   - **Cancel**, Esc, or the dialog's close box: veto. Memory and editors keep the edits, and the user can fix the cause and retry by closing again or through any action.
4. If it raises and the event cannot be vetoed: D8.

The plain error box is not shown on Close any more; the dialog carries the same text. Retry is a loop in the handler, not a new close event, so `CanVeto()` stays the same throughout.

**D7. The dialog is a `wx.MessageDialog` with custom labels (a Windows task dialog).**

```python
with wx.MessageDialog(
	self,
	_("Failed to save document: {error}").format(error=error),
	_("Cannot Save Document"),
	wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,
) as dialog:
	dialog.SetExtendedMessage(_("Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost."))
	dialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))
	return dialog.ShowModal()  # ID_YES: retry, ID_NO: close without saving, else cancel
```

- **Keeps the existing error text** as the main instruction, unchanged: same msgid, the same Python error text after it (F-3 D6). The new sentence is the content text.
- **Accessibility**: a standard Windows task dialog, which NVDA reads as a dialog: title, main instruction, content, then the focused button. Every label is passed in through `SetYesNoCancelLabels`, so all three are localized (measured through UIA), and nothing walks the window tree. That avoids F-W9's `FindWindowById` bug. Keyboard: Retry is focused and the default (Enter), Alt+R and Alt+W are mnemonics, and Esc or the close box mean Cancel. The destructive choice is never the default.
- **Order** Retry, Close without saving, Cancel: the order wx gives the Yes/No/Cancel buttons on Windows, and the usual "retry first, way out last" pattern.
- **Icon** `ICON_ERROR`, matching the existing failure box.
- If `SetYesNoCancelLabels` returns `False` (no shipping platform does), the dialog still works, with the platform's Yes/No/Cancel labels. This is not handled further.
- The helper is a frame method `_ask_after_close_save_failure(error) -> int`, so tests can patch `wx.MessageDialog` and assert every argument.

Rejected:

- A custom `wx.Dialog`: more code, its own focus and accessible-name work, and the F-W9-style standard-button localization problem.
- `wx.MessageBox`: no custom labels; its buttons show English `OK` (F-W9).
- Two questions in a row (error box, then "close anyway?"): more steps for screen-reader users, and the error text is gone by the time the decision comes.

**D8. A close that cannot be vetoed (Windows ending the session) does not ask.** If `evt.CanVeto()` is false, the handler tries the save once. On failure it logs it (`logger.error("Failed to save the open document while closing", exc_info=error)`, for every exception type, because nobody sees a message) and closes (`Skip`). Today it shows a modal error box and returns without `Skip`, which leaves the window alive while Windows ends the process anyway. Either way, the edits since the last good save are lost. The package is intact (F-3). wx only sends a non-vetoable close after the vetoable query-end-session close has already gone through the dialog, so this path is rare.

**D9. Logging.** The M-3 logic moves into `_log_unexpected_save_error(error)`, which logs non-`OSError` with traceback. `_show_document_save_error` calls it, and so does step 3 of D6, once per failed attempt. `OSError` stays unlogged (expected, and named in the dialog), except in D8.

**D10. Other actions are unchanged (decision C).** `_save_open_document_with_feedback` and its ten call sites keep their code. They block with the existing error box only when the save really writes and fails. F-3 Q1 stands: any open handle on the package fails the write. Rename and Delete then apply their own rules to the package (F-3 D7, Windows delete semantics), unchanged.

**D11. No new indicator, command or setting.** No "modified" mark in the title, no Save menu item, no autosave, no preference to turn off the dirty check.

**D12. Catalogs.** Four new msgids in `gui.py`, translated in `dotexpress.po`. Regenerate with `scripts\generate-pot.bat`, then `msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot` with default wrapping (W-3 D5). Fill the msgstr values, clear any `fuzzy` flag `msgmerge` adds, and build with `msgfmt --check -o locales\zh_TW\LC_MESSAGES\dotexpress.mo locales\zh_TW\LC_MESSAGES\dotexpress.po`. `msgfmt` is installed, so no fallback is needed. If it is missing on the implementing machine, build the `.mo` with a script that is verified to give byte-identical output for the current `.po` before it is used (AGENTS.md).

## Behavior per Path, Before and After

"Unchanged" means D2 holds. "Fails" means the write raises.

| Path | Before | After |
| --- | --- | --- |
| Switch (Open, Enter, Ctrl+Tab), unchanged | rewritten; if the write fails: error box, no switch | not written; switches |
| Switch, changed | written; fails: error box, no switch | identical |
| Add, Import, Export, Export All, Ctrl+E, unchanged | rewritten; fails: error box, action stopped | not written; action proceeds |
| Same actions, changed | written; fails: error box, stopped | identical |
| Rename, unchanged open document | rewritten; fails: error box before the name dialog | not written; name dialog; the rename itself then applies F-3 rules (read-only: `[Errno 13]`; held open without delete sharing: `[WinError 32]`) |
| Delete / Delete All, unchanged | rewritten; fails: error box | not written; confirmation; the unlink applies today's rules (read-only on Windows: `[WinError 5]` "Failed to delete document") |
| Close, unchanged | rewritten; fails: error box, Close vetoed (F-W10) | not written; closes |
| Close, changed, write succeeds | closes | identical |
| Close, changed, write fails | error box, Close vetoed; a non-`OSError` is also logged | dialog D7: Retry (loop), Close without saving (closes, package = last good save), Cancel (vetoed, edits kept); a non-`OSError` is logged per attempt |
| Close, conversion running | vetoed (vetoable) | identical |
| Close, cannot be vetoed, write fails | error box, then return without `Skip` | logged; closes (D8) |
| Lone surrogate typed or pasted, any save | `UnicodeEncodeError`: error box (or Close vetoed), every time; impossible to leave without killing the app | saved with U+FFFD, no message; the editor keeps the character until the document is reopened; later saves skip (D5) |
| Startup | packages loaded | identical, plus records and fingerprints |
| Package deleted or replaced on disk while open, unchanged in memory | rewritten at the next save | identical (fingerprint differs: written) |
| Export as DEP to any path | written atomically | identical; a lone surrogate is written as U+FFFD |

## Failure Modes on Windows NTFS

"Message" is today's text in the packaged zh-TW build (`儲存文件失敗：{error}`, caption `錯誤`). "Switch" stands for every action except Close. Rename and Delete then apply their own rules, as in the table above.

### The open document is unchanged since its last load or write

| Fault on its `.dep` | Before: switch / other | Before: Close | After: switch / other | After: Close |
| --- | --- | --- | --- | --- |
| read-only attribute | `[Errno 13] Permission denied: '...\alpha.dep'`; blocked | same message; vetoed; the app cannot exit (F-W10) | proceeds, nothing written | closes |
| held open, share read (zip tool) | `[WinError 5] ...: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`; blocked | same; vetoed | proceeds | closes |
| held open, share read+write / +delete (F-3 Q1) | `[WinError 5]`; blocked | same; vetoed | proceeds | closes |
| disk full | `[Errno 28]` or an error naming the `.tmp`; blocked | same; vetoed | proceeds | closes |
| lone surrogate | cannot occur: a package never holds one (the loader decodes strictly), and a pasted one makes the document changed | - | - | - |
| non-`OSError` in the writer (a bug) | message + `gui.log` traceback; blocked | same; vetoed | proceeds; the writer is not called | closes |
| package deleted or replaced by another program | rewritten | rewritten, closes | rewritten (fingerprint, D2); succeeds or fails as a changed document | same |

### The open document has unsaved changes

| Fault | Before: switch / other | Before: Close | After: switch / other | After: Close |
| --- | --- | --- | --- | --- |
| read-only attribute | `[Errno 13]`; blocked | same; vetoed | identical: message, blocked; memory keeps the edit | dialog with `[Errno 13] ...`; Retry fails again until `attrib -r`, then saves and closes; Close without saving exits, package unchanged; Cancel keeps the app open |
| held open, any share mode | `[WinError 5]`; blocked | same; vetoed | identical | dialog; Retry after the other program closes the file saves and exits; the other choices as above |
| disk full | `[Errno 28]` (or the `.tmp` error); blocked | same; vetoed | identical | dialog; Retry after freeing space saves |
| lone surrogate (pasted) | `UnicodeEncodeError` message; blocked, every time | same; vetoed every time | saved with U+FFFD; proceeds | saved with U+FFFD; closes |
| non-`OSError` in the writer (a bug) | message + traceback; blocked | same; vetoed | identical | dialog with the error text; traceback logged per attempt; Close without saving is the way out |
| any of the above, close cannot be vetoed | - | error box, window not destroyed | - | logged, closes (D8) |

In every row the package on disk is the last good save (F-3), and no `.tmp` is left.

## Design per File

### `client/documents/workspace.py` (4 spaces)

- `_LONE_SURROGATE = re.compile("[\ud800-\udfff]")` and the public `replace_lone_surrogates(text: str) -> str` (D4). Docstring: "Replace every unpaired UTF-16 surrogate with U+FFFD so the text can be encoded as UTF-8; a split pair is joined."
- `_encodable(document) -> Document`: the same name, text and braille through `replace_lone_surrogates`, with braille `None` kept.
- `_normalized(document)`: also applies `_encodable` (name normalization unchanged).
- `prepare_document_for_save`: returns `_encodable(Document(name, text, saved_braille))`.

### `client/documents/workspace_service.py` (4 spaces)

- `_SavedPackage` (frozen dataclass: `document`, `fingerprint`), `_package_fingerprint(path) -> tuple[int, int] | None`.
- `__init__`: `self._saved: dict[str, _SavedPackage] = {}`.
- `_remember(document)`: stores `_SavedPackage(_encodable(document), _package_fingerprint(self.package_path(document.name)))`. `_is_saved(document) -> bool` implements D2. `_reset_saved(documents)` is used by `load_documents` and by the failure branch of `delete_all_documents`.
- `save_open_document`: as today up to `replace_document`; then `if self._is_saved(updated_document): return updated_document`; then the write, `_remember`, and the return.
- `create_document`, `import_files`, `rename_document`, `delete_document`, `delete_all_documents`: the record updates of D3, each after the disk effect succeeded.
- Module docstring: "Save writes only when the open document differs from what was last written to or loaded from its package; that record changes only after a successful write, so a failed save is retried by the next one."

### `client/gui.py` (tabs)

- `_log_unexpected_save_error(error)` (D9); `_show_document_save_error` calls it.
- `_ask_after_close_save_failure(error) -> int` (D7).
- `_save_open_document_before_close(can_veto: bool) -> bool` (D6, D8):

```python
def _save_open_document_before_close(self, can_veto: bool) -> bool:
	"""Save before closing; True if the frame may close."""
	while True:
		try:
			self._save_open_document()
			return True
		except Exception as error:
			if not can_veto:
				logger.error("Failed to save the open document while closing", exc_info=error)
				return True
			self._log_unexpected_save_error(error)
			answer = self._ask_after_close_save_failure(error)
			if answer == wx.ID_YES:
				continue
			return answer == wx.ID_NO
```

- `_on_close`: the conversion check stays first. Then `if not self._save_open_document_before_close(evt.CanVeto()): evt.Veto(); return`. The rest is unchanged.

### `client/locales/` (D12)

`dotexpress.pot`, `zh_TW/LC_MESSAGES/dotexpress.po`, `zh_TW/LC_MESSAGES/dotexpress.mo`.

### `client/tests/wx_stub.py` (4 spaces)

`gui_frame_stubs`: add `wx.ID_YES`, `wx.ID_NO`, `wx.ID_CANCEL` and `wx.YES_DEFAULT`, with values distinct from the existing ids and flags (in real wx `YES_DEFAULT` is 0; the stub makes it visible in style assertions). `_MessageDialog` gains `SetExtendedMessage` and `SetYesNoCancelLabels` (which returns `True`).

### Not changed

`documents/controller.py`, `documents/session.py`, `documents/formats.py`, `documents/export_coordinator.py`, `ui/conversion_presenter.py`, `shared/atomic_write.py`, `dialog.py` (including `localize_standard_buttons`), every other dialog, the package format, `client/dictionary/`, `client/braille/`.

## What Stays Identical

- Package format and bytes for the same document and timestamp. Text without lone surrogates is written exactly as before.
- The memory-before-write order of Save. Every disk effect and controller update of Add, Import, Rename, Delete and Delete All.
- Every existing message template and caption. The error box and blocking of every non-Close action whose save writes and fails.
- Close is vetoed while a conversion runs.
- F-3: atomic writes, the read-only verdict, the lock behavior of Q1 and the rename refusal of Q2.
- Both fixture sha256 values.

## User-Visible Strings

New msgids, all in `client/gui.py` (D7):

| msgid | msgstr (zh_TW) | Where |
| --- | --- | --- |
| `Cannot Save Document` | `無法儲存文件` | dialog title |
| `Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost.` | `上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。` | content text, below the error line |
| `&Retry` | `重試(&R)` | button (Yes), default |
| `Close &Without Saving` | `不儲存就關閉(&W)` | button (No) |

Reused: `Failed to save document: {error}` (`儲存文件失敗：{error}`) as the main instruction, and `Cancel` (`取消`) for the third button. The mnemonic style follows the catalog (`&Categories:` -> `分類(&C)：`). The log message of D8 is not translated (log texts never are). msgids 353 -> 357.

## Test Plan

TDD: each step's new tests are written first and fail for the stated reason, then the code turns them green. Test files keep their indentation (4 spaces in all files below). Every test uses temporary directories and never touches `client/dictionary/`, `client/workspace/` or `config.json`.

Fault injection:

- `patch("os.replace", ...)` for a write that fails after staging (looked up at call time, unaffected by `wx_stub` module copies).
- `patch("zipfile.ZipFile.writestr", side_effect=ValueError("injected"))` for a non-`OSError` raised while the archive is written. This replaces the lone-surrogate injector.
- `package_files=` for Rename.
- The Windows-only helpers in `client/tests/windows_file_handles.py` (`hold_open`, `SHARE_MODES`, `make_read_only`).
- GUI tests never patch `documents.*` globals (F-3 rule). A "not written" assertion uses `patch.object(workspace_service, "save_document_package", wraps=...)` in service tests, and `os.replace` call counts plus package bytes and `st_mtime_ns` in GUI tests.

### A. Documents layer (`client/tests/test_document_workspace.py`)

New, red because `replace_lone_surrogates` is missing or the write raises `UnicodeEncodeError`:

1. `test_replace_lone_surrogates_replaces_each_unpaired_surrogate`, with subTests: lone high, lone low, a reversed pair (two U+FFFD), two highs, a high at the end, `\udcff`.
2. `test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text`: `\ud83d\ude00` -> U+1F600; astral, CJK, braille and `""` unchanged; clean input is returned as the same object.
3. `test_prepare_document_for_save_replaces_lone_surrogates`: text and braille; a pending document stays `None`.
4. `test_save_replaces_lone_surrogates_with_the_replacement_character` (subTests: text, braille): the package loads with U+FFFD, and the `.txt` member holds `EF BF BD`.
5. `test_staged_package_replaces_lone_surrogates`: `PackageFiles().write` and `move_document_package` with a surrogate in the text.

Changed (the injector, not the intent):

- `test_save_failure_from_a_lone_surrogate_keeps_the_existing_package` becomes `test_save_failure_that_is_not_an_os_error_keeps_the_existing_package`: `writestr` raises `ValueError` on the first, then on the second member (subTests); bytes unchanged, loadable, no `.tmp`.
- `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`: the same `writestr` injector instead of `"\ud800"`.

### B. Service (`client/tests/test_workspace_service.py`, new class `SaveOnlyWhenChangedTest`)

Red: today every save writes (or raises `UnicodeEncodeError`). Unless stated, each test starts from `load_documents()` and `controller.open_document("alpha")`.

1. `test_unchanged_document_is_not_written`: `save_document_package` is not called; package bytes and `st_mtime_ns` unchanged.
2. `test_changed_text_is_written`.
3. `test_changed_braille_is_written`.
4. `test_converted_pending_document_is_written`: the controller copy gets braille (as `_complete_manual` does); the save writes it, and `alpha.meta.json` is gone.
5. `test_failed_save_is_retried_by_the_next_save`. **The must-have case.** `os.replace` fails once: the first save raises and the controller holds `"edited"`. The second identical save writes, and the package holds `"edited"`. This catches a controller-copy baseline and a record written before the write.
6. `test_reverting_after_a_failed_save_is_not_written`: after the failed save, a save with the original text does not call the writer, even while `os.replace` still fails.
7. `test_lone_surrogate_text_is_saved_once`: `"x\ud800"` is written as `"x\ufffd"`; a second save with `"x\ud800"` is not written.
8. `test_package_removed_on_disk_is_written_again`.
9. `test_package_replaced_on_disk_is_written_again` (subTests: different size; same bytes with `os.utime` to another time): the save writes the memory version.
10. `test_document_without_a_record_is_written`: a controller filled directly, which documents the conservative default.
11. `test_created_document_is_not_written_again`.
12. `test_imported_document_is_not_written_again`.
13. `test_renamed_document_is_not_written_again` (subTests: regular `alpha` to `gamma`; case-only `alpha` to `Alpha`): the open document is renamed, then saved unchanged.
14. `test_failed_rename_keeps_the_record_of_the_old_name`: `_FailingReplacePackageFiles(source_name="alpha.dep")`; a later unchanged save of `alpha` is not written.
15. `test_deleted_then_created_document_is_written` (delete `beta`, create `beta`, edit, save: written) and `test_documents_reloaded_after_a_failed_delete_all_are_not_written_again`.
16. Windows only: `test_unchanged_unwritable_package_saves_without_error`, with subTests for read-only (`make_read_only`) and each of `SHARE_MODES` (`hold_open`): no exception, bytes unchanged.
17. `test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk`.

Changed: `test_save_failure_keeps_the_package_and_updates_memory` uses the `writestr` `ValueError` injector with the text `"edited"`.

### C. GUI flows (`client/tests/test_gui_document_flows.py`, class `DocumentWorkspaceFlowsCharacterizationTest`)

The `setUp` patcher list gains a fake `wx.MessageDialog`. It records `("MessageDialog", message, caption, style, extended, labels, parent)` in `self.events`, takes its `ShowModal` result from a new `self.dialog_answers` list, and supports `with`. Startup-based tests call `frame._load_workspace_documents_at_startup()` on a prepared workspace.

New:

1. `test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next`: `os.replace` patched to raise; Ctrl+Tab opens `beta`; no error box; `os.replace` not called. Red: today the error box appears and nothing opens.
2. Windows only: `test_unchanged_read_only_document_blocks_neither_switch_nor_close`: real `attrib +r`; switch, then `_on_close` with a vetoable event: `Skip` called, no dialog. Red.
3. `test_switch_from_a_changed_document_whose_save_fails_still_blocks`: loaded, edited, `os.replace` fails; the existing error box; still on `alpha`; memory holds the edit. A regression guard; green after step 1 too.
4. `test_close_with_an_unchanged_document_whose_save_would_fail_closes`. Red.
5. `test_close_save_failure_asks_and_cancel_keeps_the_window_open`: asserts the dialog event (message `gui._("Failed to save document: {error}").format(error=...)`, caption `gui._("Cannot Save Document")`, style `YES_NO | CANCEL | YES_DEFAULT | ICON_ERROR`, the extended text, the labels `(gui._("&Retry"), gui._("Close &Without Saving"), gui._("Cancel"))`, parent frame); answer `ID_CANCEL`; `Veto` called, no `Skip`; no error box; memory and editor keep the edit; package unchanged. Red: today's error box.
6. `test_close_retry_after_the_cause_is_gone_saves_and_closes`: `os.replace` fails once, then works; answer `ID_YES`; one dialog; `Skip`; the package holds the edit.
7. `test_close_retry_that_fails_again_asks_again`: two failures; answers `ID_YES`, then `ID_CANCEL`; two dialogs, each with its own error text; `Veto`.
8. `test_close_without_saving_closes_and_keeps_the_last_saved_package`: answer `ID_NO`; `close_converting_dialog` called, the dual view destroyed, `Skip`; package bytes unchanged; no `.tmp`.
9. `test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes`: `CanVeto()` false; no dialog, no error box; `assertLogs` with `exc_info` of the `PermissionError`; `Skip`.
10. `test_pasted_lone_surrogate_is_saved_as_replacement_character`: the editor holds `"x\ud800"`; the save succeeds with no event; memory and package hold `"x\ufffd"`; the editor still holds `"x\ud800"`. (That a second save is then skipped is B7, step 2.)
11. `test_close_dialog_strings_are_translated`: `i18n.load_translation()` maps the four new msgids to the zh-TW texts above.

Flipped or changed:

- `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error` becomes `test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks`: `writestr` `ValueError`; the dialog's message contains `injected`; one log record with traceback; answer `ID_CANCEL`; `Veto`; package bytes unchanged. Red: today's error box.
- `test_close_vetoes_when_save_fails`: the dialog answer is `ID_CANCEL`; it asserts the dialog instead of the error box (renamed `test_close_save_failure_cancel_vetoes`).
- `test_close_asks_presenter_before_saving` (class at about line 3620): mocks `_save_open_document` (the raw save) instead of `_save_open_document_with_feedback`. The expected order is unchanged.
- The four tests that inject `"\ud800"` into a save or rename get new injectors. The save tests (`test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`, `test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback`) use `writestr` `ValueError`, with expected text `injected` and type `ValueError`. The rename tests (`test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`, `test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback`) give the frame's service `package_files=` a local `PackageFiles` subclass whose `write` raises `ValueError("injected")`. A `writestr` patch would fail the save of the open document first.
- Unchanged and still green: every other save, Add, Rename, Delete, Import and Export flow test (their controllers have no records, so every save writes), and `test_close_while_running_vetoes_or_saves_and_closes`.

### Counts

New tests: A 5, B 18 (B15 is two tests), C 11 = 34. Flips and changes replace tests one for one. Expected: `Ran 1304`, `FAILED (errors=1, skipped=7)` on Windows, F-W6 only. The 2 new Windows-only tests (B16, C2) are skipped on POSIX. The plan may adjust the counts; the red/green intent is binding.

## Migration Steps (each step one green commit, red first)

1. `fix: save lone surrogates as U+FFFD (F-5)`: D4, D5. A 1-5, B17, C10. The injector changes of A, B and C go in the same commit, because this step removes the injected fault. That includes `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`, which gets the `writestr` injector here and keeps its error-box assertions until step 3 flips it.
2. `fix: skip saving an unchanged document (F-5)`: D1-D3. B 1-16, C 1-4.
3. `fix: offer retry or close without saving when saving fails on close (F-5)`: D6-D9, D12, the `wx_stub` additions. C 5-9 and 11, the three close flips. `.pot`, `.po` and `.mo` are regenerated in this commit.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`.

1. Full suite: no failure or error other than F-W6; `Ran` = 1270 + the new tests.
2. Focused: `$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n tests.test_atomic_write tests.test_document_controller -v` passes; the Windows-only tests run (not skipped).
3. Catalogs: `$PY -I` AST scan of `_`/`N_` gives 357 source msgids; `msgfmt --statistics` on the `.po` reports 357 translated, no fuzzy, no untranslated; the `.mo` loads with `gettext.GNUTranslations` and translates the four new msgids; `scripts\generate-pot.bat` run twice gives identical output apart from `POT-Creation-Date`.
4. Both fixture sha256 values unchanged (`translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`).
5. App data untouched: `client/dictionary/` sha256 identical before and after the suite; no `client/workspace/`, `client/config.json` or `client/log/` created.
6. `git diff main --stat` touches only `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/gui.py`, the three locale files, `client/tests/wx_stub.py`, the test files named above, and the spec, plan and history files.
7. Mutation check (plan): each mutant is caught by at least one test. The mutants:
   - The baseline taken from the controller copy.
   - The record updated before the write.
   - The record updated even when the write fails.
   - No fingerprint check.
   - Rename does not move the record.
   - The failure branch of `delete_all_documents` does not reset the records.
   - The replacement skipped in `prepare_document_for_save`.
   - The replacement skipped in `_normalized`.
   - The braille not replaced.
   - Close without saving saves anyway.
   - Retry closes without retrying.
   - Cancel closes.
   - A non-vetoable close shows the dialog.
   - The dialog without `YES_DEFAULT`, or with the labels in another order.
8. Packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build as in F-4: the main checkout's `client\.venv\Scripts` first on `PATH`, `scripts\build-dotexpress.bat`. Check in `client\build\DotExpress\PYZ-00.toc` and `Analysis-00.toc` that `documents\workspace.py`, `documents\workspace_service.py` and `gui.py` come from the checkout being verified. Copy `client\dist\DotExpress.exe` to `D:\dxtest\N-f5\`. Each item runs in a new `D:\dxtest\auto<N>-f5` folder; only processes whose exe lies under those folders are ended (`dx.kill_under`). The scripts reuse `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `lock.py`) and `.../2026-10-09-05-f3-dep-atomic-write/auto/f3gui.py` without editing them. New scripts and a helper `f5gui.py` go to `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/`. They run in the pywinauto venv (`$SP\uia`). Packages are compared by zip member hashes (`docs.ws_state`) and `st_mtime_ns`.

`f5gui.py` reads the new dialog through UIA, because the win32 backend's `dx.dismiss` cannot see task-dialog buttons. It finds the dialog as `Desktop(backend="uia").window(handle=<main>).child_window(title="無法儲存文件", control_type="Window")`, reads the `MainInstruction` and `ContentText` texts by automation id and the three button names, records which element has focus, and answers with Enter, Esc or Alt+W (or a button's `invoke()`). `docs.close` cannot be used for these items. `f5gui.close_and_answer(app, w, answers)` posts `WM_CLOSE` and answers each dialog in turn. A lone surrogate is put on the clipboard with `ctypes` (`OpenClipboard`, `SetClipboardData(CF_UNICODETEXT)` with raw UTF-16 code units `41 00 3D D8 42 00 00 00`) and pasted with `WM_PASTE` (0x0302) on the input `Edit`.

| # | Steps | Expected after F-5 | Before (N-f4) |
| --- | --- | --- | --- |
| 36 | Add `alpha` and `beta` (text in both), close, restart; `attrib +r alpha.dep`; with `alpha` open and unchanged: Ctrl+Tab, Add `gamma`, back to `alpha`, Close | no message; switches and Add work; the app exits; `alpha.dep` bytes and `st_mtime_ns` unchanged; still `R` | `[Errno 13]` on every action; Close vetoed (item 20) |
| 37 | As 36, but `lock.py` holds `alpha.dep` (share `r`, then `rw`) instead of the attribute | same as 36 for both share modes | `[WinError 5]` on every action; Close vetoed |
| 38 | `alpha` open; type an edit; `lock.py` holds `alpha.dep` (share `r`); Ctrl+Tab; then Close | Ctrl+Tab: today's message `儲存文件失敗：[WinError 5] ...`, still on `alpha`. Close: dialog `無法儲存文件`; `MainInstruction` = the same `儲存文件失敗：...` line; `ContentText` = the new sentence; buttons `重試(R)`, `不儲存就關閉(W)`, `取消`; focus on `重試(R)`. Esc: the app stays open and the edit is still in the editor. Close again, Enter (Retry) while locked: the dialog again. Kill the lock, Enter: the app exits. Restart: `alpha` holds the edit | Ctrl+Tab same; Close: the error box `確定` only, vetoed |
| 39 | As 38 up to the dialog; Alt+W (Close without saving) | the app exits; `alpha.dep` members unchanged since before the edit; no `.tmp`; restart shows the old text | not possible (vetoed) |
| 40 | `alpha` open; paste the clipboard holding `A\ud83dB`; Ctrl+Tab; Ctrl+Tab back; Ctrl+Tab again | no message; `alpha.txt` in the package holds `41 EF BF BD 42`; the second switch away leaves `st_mtime_ns` unchanged (not rewritten); restart: `alpha` shows `A\ufffdB` | `儲存文件失敗：'utf-8' codec can't encode character '\ud83d' ...` on every switch; Close vetoed |
| 41 (manual, user) | With NVDA running, repeat 38 up to the dialog | NVDA reads the title, the error line and the sentence, then "重試 按鈕" (or the NVDA equivalent); Tab and Shift+Tab move through the three buttons and NVDA names each; Alt+R, Alt+W and Esc work. Record what NVDA says | - |

Re-runs with changed expectations (same scripts via `rerun.py`, exe and folder replaced):

- **19** (`alpha` unchanged, held open with share `r`, then `rw`, case-only rename to `Alpha`): the save is skipped and the name dialog appears. The rename then fails with `[WinError 32] ...: '...\alpha.dep' -> '...\.alpha.dep.<rnd>.tmp'` (F-3 D5). List and content unchanged, no `.tmp`, Close exits. Before (F-3): the save failed, with no name dialog.
- **20 / 20b** (`attrib +r`, unchanged, rename): the name dialog appears, then the rename is refused with `[Errno 13] Permission denied: '...\alpha.dep'` (F-3 D7). Close exits. Before: the save failed first, and Close was vetoed (F-W10).
- **33** (optional, Defender on, 20 switches with an edit before each): 0 failures, no `.tmp`, as with F-3.

## Risks

- **A changed package with an unchanged fingerprint is not rewritten** (very low). Another program would have to replace the package with the same size and the same modification time to the 100 ns. An unchanged document is then left as that program wrote it, where today's Save would overwrite it.
- **Close without saving loses edits by choice** (low). The dialog defaults to Retry, says the changes will be lost, and the destructive button is never the default. Screen-reader users hear the sentence before the buttons.
- **Documents the editor normalizes count as changed once** (low). A `\r`, `\r\n` or U+0000 in a loaded text makes the document "changed" at the first save. If that package is also read-only or locked, that first action is blocked as today; Close then offers the dialog.
- **U+0000 truncation** (existing, out of scope). The Edit control cuts the text at U+0000, so a package whose text contains one loses the rest at its first save after opening. Same today; listed as a follow-up.
- **Silent replacement** (low). A lone surrogate becomes U+FFFD without a message. It was invisible, could not be saved, and blocked the app; U+FFFD is the standard visible marker.
- **Session end** (low, D8). A failed save while Windows ends the session is only logged. Today the edits are lost too, after a message nobody can act on.
- **Logging volume** (low). A non-`OSError` on Close is logged once per Retry. Retries are user-driven.

## Open Questions

None. The user decided A-D. D5 (editors untouched), D8 (non-vetoable close) and the dialog wording follow from those decisions and are recorded above so they can be reviewed.

## Out of Scope / Follow-ups

- **U+0000 in document text**: the Edit control truncates at it (measured), and the next save writes the truncated text. Same today. A follow-up should decide whether to keep, replace or reject U+0000 on import and load.
- **Conversion of text with a lone surrogate**: `get_source_text` still passes the editor value to conversion. Unchanged by F-5.
- **F review M-2** (recover orphan `.tmp` files at startup), **F-3 review M-1** (Add, Rename, Import or the default document replacing a kept invalid `.dep`), **F-3 review M-6** (real disk-full and 7-Zip checks).
- A per-cause message (locked vs read-only), a "modified" indicator, a Save command, autosave.
- **F-W9** elsewhere (`localize_standard_buttons`, `wx.MessageBox` OK buttons): not touched. The new dialog does not use them.
