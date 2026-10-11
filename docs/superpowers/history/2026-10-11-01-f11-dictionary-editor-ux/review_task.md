# F-11 Dictionary Editor UX review record

- Date: 2026-10-11. Written in English at the orchestrator's request (HANDOFF section 1 says Traditional Chinese; the fix record may follow either).
- Scope: worktree `D:\workspace\DotExpress-f11`, branch `fix/f11-dictionary-editor-ux`, range `1ce6ce5..HEAD` (13 commits: `cc8c002` spec, `2ddc887` plan, `a02fe0a` D10, `d585aa4` D11, `5dc8bfe` D5/D6, `bc7368a` D9, `19fe19d` D2/D8, `8b9804f` D14, `2f6e70d` D12, `1df105f` D1, `f9e66d6` D3/D4/D7, `5d5f2fd` D13, `4d229b4` GUI record). Production diff (changed lines): `client/dictionaries/entries.py` 174 (loader, layout, writer, `canonical_bopomofo`), `client/dictionaries/entry_list_model.py` 125, `client/dialog.py` 163, `client/dictionaries/manager.py` 38, `client/dictionaries/presenter.py` 5, `client/gui.py` 16, `client/ui/message_box.py` 21, `client/conversion/text/dictionary_rules.py` 27; twelve test modules; the three catalogs; spec (EN and zh-TW, 665 lines each), plan (8787 lines), `auto-results.md` and ten `auto/` scripts. 37 files, exactly the plan's "Files that may change" plus the history folder (acceptance 7). `HEAD:client` is `0d0f93c8...`, the plan's Task 10 tree id. Every commit carries the `Co-Authored-By: Claude Opus 5.5` trailer; `AGENTS.md`, the fixtures, `scripts/`, `client/braille/` are not in the range.
- Read against: the spec (D1-D15, "Corrected after planning (F-11)" 1-13, behavior table, Test Plan A-G, acceptance 1-9, Windows items 95-107, Risks, O1-O13, the defaults list), the plan (Global Constraints, Spec Corrections, Review Focus, Expected Counts, the 51-mutant list, Implementation Notes 1-5), `auto-results.md`, `task.md` section 三 and #8 (read-only), HANDOFF sections 1-2, `AGENTS.md`, the F-9 review record (format).
- Method: line-by-line reading of the eight production diffs plus the surrounding code (`AddSymbolDialog._on_ok`, `DictionaryEntriesDialog._build_ui`, the presenter's `rename`/`import_from_file`, `dictionary_state.py`, `name_prompt.py`, `atomic_write.py`, `dictionary_rules.from_paths`); the twelve test diffs, the trace runner and its two adaptations; the catalog diffs; the full suite on Windows 11; a 504-row editor/conversion parity probe and ten loader/writer edge-case probes with the real parser; 30 self-written mutants on a scratch copy of the worktree's `client/` under the session scratchpad `f11review\`; the 25 `D:\dxtest\auto*-f11*.log` files and both exe hashes. No GUI run (no finding needed one; the record's logs cover every keyboard path, and the only open item is the user's NVDA item 107). No clipboard access anywhere; no process started or ended. Nothing was staged or committed; the worktree's `git status --short` is empty and it has no `client/log/`, `client/workspace/` or `client/config.json`; the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` were not touched (not opened by any probe; the probes use temporary folders only). Statements that could not be measured are marked "reasoning".
- This record is written to disk only, not committed.

## Verification (Windows 11 26200, `$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`, `$SP` = session scratchpad `f11review\`)

| Item | Command | Result |
| --- | --- | --- |
| full suite (acceptance 1) | `cd D:\workspace\DotExpress-f11\client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1553 tests`, `OK (skipped=6)`, as the plan's Expected Counts and Implementation Notes 1; the worktree got no `log/`, `workspace/` or `config.json` |
| focused modules (acceptance 2, scratch copy) | the ten modules of acceptance 2 plus `test_message_box`, `test_wx_call_sites`, `test_translation_golden`, `test_translation_liblouis_golden` on `$SP\copy\client` | `Ran 565`, `OK` (after copying `scripts/` next to the copy: `test_generate_pot_extracts_n_keyword` reads `generate-pot.bat`; environmental) |
| `KNOWN BUG` pins (acceptance 3) | `grep -rn "KNOWN BUG (P2-2 spec, Q[24568])" client/tests` | nothing |
| catalogs (acceptance 4) | `msgfmt --check --statistics -o $SP/fresh.mo ...dotexpress.po`; `sha256sum` of both `.mo`; `grep -c '^msgid '`; `grep -c '^#, fuzzy'`; `git diff 1ce6ce5..HEAD -- client/locales` | 380 translated, 0 fuzzy, 381 `msgid` lines in `.po` and `.pot` (380 + header); the freshly compiled `.mo` is byte-identical to the committed one (`ee45926d...`); the `.po` diff adds exactly the eleven entries of the spec's table with `#, python-brace-format` on the six brace strings; `POT-Creation-Date` `2026-10-10 12:00+0800` in both; `#: dialog.py:606` of `Remove and &Save` points at the call |
| fixtures (acceptance 5) | `git show HEAD:client/tests/fixtures/<f> \| sha256sum` | `translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`, `translation_liblouis_golden.json` `8dc8572e...`: unchanged. Both golden test modules pass on the F-11 code, so conversion output is unchanged for dictionaries without hidden rows |
| app data (acceptance 6) | - | no probe touched the main checkout; the worktree has no `client/log/`, `client/workspace/`, `client/config.json` |
| commits (acceptance 7) | `git log --oneline 1ce6ce5..HEAD`; `git diff --stat`; `git diff --name-status` | thirteen commits, no merge; 37 files as listed above; no stray file, debug print, `breakpoint`, environment switch or test-only hook in the production diff (`grep` over the added lines); the ten `auto/` scripts contain no clipboard call; `f11gui.keys` sends keys only while the app's window is the foreground window |
| parity probe (D13, D14) | `$PY -B -X utf8 $SP\parity.py` (504 rows: 6 source texts x 21 Bopomofo whitespace variants x 4 types, the real parser and `data/Bopomofo2Braille.csv`) | "shown by `load_dictionary_rows`" equals "a rule of `from_paths`" for every row (0 mismatches); the four first-tone cases in section 2.1 |
| edge-case probes (D5, D6) | `$PY -B -X utf8 $SP\probes.py` | section 2.3: S1-S10 |
| mutants (30) | `$PY -B -X utf8 $SP\mutants.py $SP\copy\client $PY` (one edit per mutant, old text exactly once, CRLF kept, restored and byte-compared afterwards; the 14 modules above) | section 2.2 |
| GUI record audit | the 25 logs in `D:\dxtest\`; `sha256sum D:\dxtest\N-f11\DotExpress.exe D:\dxtest\N-f9b\DotExpress.exe` | every key line of `auto-results.md` for items 95, 96, 99 and 100 matches its log verbatim (the D1 box's title, four text lines, both buttons and focus; Esc, Enter and Alt+F4 each leaving the editor open with the file's bytes and mtime unchanged and the focus on 確定; the D7 box on Esc, Cancel and Alt+F4; the close box of the D7 box returning to 取消); `N-f11` `3cec35ce...` 48,778,355 bytes and `N-f9b` `b5ad9bfa...` 48,765,092 bytes as recorded; 22 logs plus the three `b` re-runs |
| not run | - | item 107 (NVDA, the user's); POSIX-only tests (6 skips); the plan's shuffle seeds and its 51 mutants (replayed by the implementation, Implementation Notes 2) |

## Conclusion

**Ready to merge after one user decision (I-1) and the cheap Minor fixes.** No Critical finding. One Important finding, I-1, is not a defect in what the spec asked for but a user-visible inconsistency that the orchestrator's default O13 introduced between D14 (the editor shows a first-tone row typed without its space as `ㄇㄚ `) and D13 (conversion keeps using the raw fallback `⠍⠜`, without the first-tone cell, until an unrelated save rewrites the row); the user asked for the editor and conversion to agree (#8) and was told the row "converts as today". The fix is one line plus one golden case, but it changes conversion output for such rows, so it is the user's call.

The data-safety core is sound. OK writes nothing without a change (D3/D4: value-and-order comparison, copies at load, pinned by tests, mutants and GUI 97/23/24, file bytes and `st_mtime_ns` unchanged); hidden rows leave the file only through the D1 box's `Remove and &Save`, never through Cancel, Esc, Alt+F4, the close box, Enter or a save after `Back to Editing` (D1/D7: `wx.GenericMessageDialog` with `CANCEL_DEFAULT`, every exit path measured in GUI 95 and 99, the user's hard requirement from O12 holds); a failed Remove and Save keeps the rows in the model and asks again (O4); the write is still `write_text_atomically` (temp file, fsync, `os.replace`); a changed file keeps its BOM, its header order, every extra and overflow field of its unchanged and edited rows, and gets `text,braille,type` appended only when missing (D5/D6, parity with `DictReader` pinned on the F-4/F-6 corpora and by my probes). Delete and Edit act on the selected object (D9), the duplicate check runs inside the entry dialog with the input kept and the source text selected (D8), conversion skips exactly the rows the editor hides (D13; 504-row parity, both golden fixtures unchanged), a case-only rename works and `config.json` follows (D10), a locked Import source gets F-6's reason (D11), and a read error no longer leaves a hidden dialog (D12). The eleven strings are natural Taiwan Traditional Chinese with consistent placeholders and access keys, and the `.mo` is in sync. The trace replay's two adaptations are faithful (section 1.4).

Minor findings: M-1 (wrong-header files are listed as "no source text" and emptied on Remove and Save), M-2 (three test gaps found by surviving mutants: the stripped values in a row line, a `,,` record, the focus captured before the box), M-3 (spec bodies still describe the task dialog), M-4 (selection after deleting a twin, O10), M-5 (an overflow field overwritten when a required column is appended).

## 1. Path analysis

### 1.1 The writer and the file (D3-D6; "could a user's dictionary lose rows, columns, the BOM or quoting?")

| Question | Result | Basis |
| --- | --- | --- |
| A write when nothing changed | None. `_on_ok` goes `hidden_rows` -> `has_changes()` -> `Skip`; `has_changes` compares `_entries` (order, text, braille, type; `fields` is `compare=False`) with copies taken at load and after each save. The filter, an add undone by a delete and an edit to equal values are no change; a reorder is. A missing file is not created (O11) | `entry_list_model.py:86-99`, `dialog.py:555-570`; C1, B1; GUI 97, 23, 24; mutants r26, plan's `has-changes-*` |
| Hidden rows removed without consent | Impossible: `model.save` is reached only from `_save()`, called after `_confirm_hidden_rows()` returned `True` or when there are no hidden rows. Cancel never writes (`_on_cancel` only decides whether to `Skip`). `Back to Editing` keeps the rows (mutant r14 caught) | `dialog.py:555-625`; C3, C4; GUI 95a-c, 35a |
| Rows lost on a changed file | A shown row is written from its own record (`fields`), padded, with text/braille/type set at `DictReader`'s positions (the last of a duplicated name). Overflow fields beyond the header are kept (mutant r02 caught). Hidden rows are dropped only after the D1 box | `entries.py:183-212`; A4, B6; GUI 98, 102 |
| Columns lost | The header is written as read; `text`, `braille`, `type` are appended only when missing. Extra columns keep their values on unchanged and edited rows (`replace` copies `fields`), new rows get `""` | `entries.py:197-199`, `entry_list_model.py:188-196`; A4, B3; GUI 98 |
| BOM lost or added | `has_bom` is read from the first three bytes; the writer uses `utf-8-sig` only then. New dictionaries still have none | `entries.py:129, 211-212`; A4; GUI 98, 24, 25-29 |
| Quoting and line ends | `csv.writer` (excel dialect): minimal quoting, CRLF. A changed file loses needless quotes (`"a"` -> `a`) and LF line ends (probe S4, GUI 98 `bom_lf.csv`); documented as O9 and Out of Scope. An unchanged file keeps every byte because it is not written | `entries.py:201-209` |
| Atomic write | `write_text_atomically` unchanged: temp file in the folder, `fsync`, `os.replace`; on an error the target keeps its bytes and the temp file is removed; a replace failure shows `Failed to save` and the editor stays open | `shared/atomic_write.py`; C4; GUI 25-29 |
| Parity with `DictReader` | The `csv.reader` loader takes the first record as the header (even `[]`), skips `[]` records, gives a missing field as `""` and a duplicated name its last value; pinned against `DictReader` on the F-4/F-6 corpora (A3) and matched by my probes S1-S8 | `entries.py:117-172` |
| Line numbers | `line = previous reader.line_num + 1`, header = 1; a blank line and a quoted line break count (A2; mutant r29 caught). This is what Notepad shows | `entries.py:136-142` |
| Files whose header is not recognised | Pre-existing classification (every row hidden as "no source text"); new consequence under D1: see M-1 | probes S5, S8 |

### 1.2 The two boxes (D1, D7; "every exit path, focus afterwards, Remove-and-Save failure")

| Path | D1 box (hidden rows) | D7 box (discard) | Basis |
| --- | --- | --- | --- |
| Shown when | `hidden_rows` non-empty, before the change test, so also without a change | `has_changes()` on a Cancel click, which wx also generates for Esc (`OnCharHook` -> `EmulateButtonClickIfPresent(GetEscapeId())`) and the close box / Alt+F4 (`OnCloseWindow`), synchronously; without `Skip` the dialog stays | `dialog.py:557-561, 572-584`; C3, C5; GUI 95, 99, 100 (Esc, Cancel, Alt+F4 each show the box) |
| Esc / Enter / Alt+F4 / close box in the box | `wx.ID_CANCEL` -> `False` -> `_restore_focus`, nothing written (GUI 95a-c: file bytes and mtime unchanged, focus back on 確定) | same (GUI 99: Esc -> focus on the list item `x`; close box -> focus on 取消) | `message_box.py:36-54`; `test_confirm_box_*`; mutants r04, plan's `ok-is-the-default`, `native-task-dialog` |
| Access keys | Alt+S removes and saves, Alt+B returns | Alt+D discards, Alt+B returns | GUI 95d, 35a, 99, 100 |
| Enter | the default (and initially focused) button is `返回編輯`, so Enter returns; Tab + Enter or Space on `移除並儲存` / `放棄變更` is the user's explicit choice (reasoning; `wxGenericMessageDialog::CreateMessageDialogButtonSizer` sets the Cancel button as default and focuses it under `wxCANCEL_DEFAULT`) | same | GUI 95b (Enter in the D1 box), 99 (`focus: 返回編輯(B)`) |
| Remove and Save fails | `Failed to save: {error}`, editor open, `focused` restored, hidden rows still in the model, the next OK asks again (O4) | - | C4; GUI 25-29 |
| Focus after Back to Editing | `wx.Window.FindFocus()` captured at the start of the handler (before the box), restored if `self.IsDescendant(window)`; a foreign window is left alone (mutant r03) | same | `dialog.py:621-625`; C3, C5; GUI 95, 99 |
| Discard / Remove and Save | `Skip` -> the editor ends; the focus returns to the main window's 來源文字 (GUI 99 after Alt+D) | | |
| Delete | never asks (U3.2); undone by Cancel -> Discard | | C6; GUI 100 |
| Cancel with hidden rows and no change | closes at once, hidden rows stay in the file (U3.1: not unsaved changes) | | C5 subTest "hidden rows" |

Accessibility of the generic dialog (reasoning from wx 4.2.5's `generic/msgdlgg.cpp`, consistent with the UIA readings in the logs): the caption is the window title; `CreateTextSizer` turns each line of the message into its own `wxStaticText` (the log's `text` list has four items: lead-in, two row lines, question; blank lines make no control), which UIA exposes as Text elements and NVDA reads as the dialog's text when the dialog gains focus; the tab order is `移除並儲存` then `返回編輯` (creation order), with the initial focus and the default on `返回編輯`; both buttons carry access keys. Whether NVDA reads all four lines is item 107. With a 10-row list and long source texts the box is tall but each row line is short.

### 1.3 Identity, duplicates, the entry dialog (D2, D8, D9)

| Question | Result | Basis |
| --- | --- | --- |
| Delete removes the selected object | `del self._rows[self._full_index(current_entry)]` (identity). With `[a, b, a]` and row 3 selected, row 3 goes and row 1 keeps its `note` (GUI 102) | `entry_list_model.py:198-205`; B2 |
| Edit keeping a twin's text | `is_duplicate` returns `False` when `text == editing.text`; another row cannot take the pair's text | `:162-172`; B5; GUI 102 |
| Selection | by identity after Add and Replace (`_selection_after(..., by_identity=True)`), by equality after Delete and a filter change (O10, the golden trace). Mutant r07 (Replace by equality) is caught; r08 (Add by equality) is equivalent: a new entry can never equal an existing one, because its text would be a duplicate | `:178-196, 219-237` |
| Duplicate check | `AddSymbolDialog._on_ok`: `get_entry` (stripped, canonical Bopomofo) -> format checks -> `is_duplicate(entry.text)` -> message with the entry dialog as parent, focus on `identifier_ctrl` + `SelectAll`, no `Skip`. The editor passes `lambda text: self._model.is_duplicate(text, editing=entry)`; preserved rows are not duplicates (D2) | `dialog.py:171-201, 544-550`; D; C7; GUI 101, 103 |
| The model's `DuplicateEntryError` backstop | kept; no UI path reaches it (the entry dialog checks first) | `:178-196` |

### 1.4 The golden trace (D9, "faithful, or weakened?")

The replay keeps `assertEqual(got, want)` on every step including the OK step's `csv`, so the written bytes are still compared with the pre-F-4 recording. Two adaptations: (a) `ok_log[0]` must equal the exact D1 box record (caption, the two row lines `第 5 列：沒有來源文字` / `第 8 列：「zz」的注音「ab」格式不正確`, both labels) and is then dropped; (b) the open step's `["Bind", "cancel", "EVT_BUTTON"]` is removed when present (conditional, but `test_construction_log_is_exact` pins the whole construction log, so a missing bind fails there). The scripted entry dialog mirrors D8: on a duplicate it records the same `MessageBox` and takes the next scripted answer; `_perform_trace_action` scripts exactly one answer per step and clears the queue, so the dialog "cancels" as the recording's closed dialog did and the step's log is unchanged. The belt-and-braces check that `_TRACE_KEPT_ROWS` are absent is in addition to, not instead of, the byte comparison. Probe 1 of the spec (identity for `remove` passes the trace; identity in the selection after Delete would break seeds 23, 29, 33, 37) is consistent with what the code does. Verdict: faithful; the trace is not weakened.

### 1.5 Conversion (D13, D14, #8)

| Question | Result | Basis |
| --- | --- | --- |
| Editor and conversion agree on hidden rows | `from_paths` skips `not source.strip()` and, for `type_ == "Bopomofo"` (exact, as `normalize_entry_type`), a target that the raw parse rejects and `_editor_shows_bopomofo` rejects too (`strip()`, then `strip() + " "`). `canonical_bopomofo` is the same test with the same parser. 504-row parity probe: 0 mismatches; the module still imports nothing from `dictionaries` | `dictionary_rules.py:83-98, 200-210`; F; `EditorParityTest` |
| Output unchanged for dictionaries without hidden rows | A row that stays is parsed once, on its raw value, as before (`test_the_parser_is_called_on_the_raw_sequence_first`); `translation_golden.json` and `translation_liblouis_golden.json` pass unchanged | fixtures, goldens |
| Output for whitespace-only texts and invalid Bopomofo rows | gone, by the user's decision (#8); the D1 box lists them on the next OK | golden case flipped; GUI 96, 35 |
| First-tone final rows (D14) | the editor shows `ㄓㄨㄥ ㄒㄧㄣ ` and accepts `ㄓㄨㄥ ㄒㄧㄣ` / `ㄇㄚ` typed without the space, stores them with it; conversion of a file row that has the space is unchanged (`⠍⠜⠄`). A file row **without** the space is shown as `ㄇㄚ ` but converts through the fallback to `⠍⠜`: I-1 | probes (section 2.1); GUI 106 |
| No other whitespace accidentally kept | `str.strip()` removes `\t`, U+3000, NBSP, CR, LF; only the one `" "` is added back, and only when the stripped sequence fails and the spaced one parses. `ㄇㄚ\u3000` -> `ㄇㄚ ` (the U+3000 is not kept as a tone space; the parser rejects it) | parity probe variants |
| A header lacking `type`/`braille` | the editor shows the rows, conversion raises `CSV must contain columns` (probe S10). Pre-existing, outside #8 (which is about hidden rows); noted | - |

### 1.6 Rename, Import, opening the editor (D10-D12)

- **D10.** `rename_dictionary` refuses an existing destination unless `os.path.samefile(source, destination)`; `Path.rename` then does the case-only rename (Windows `MoveFileEx`). `name_prompt` still treats an identical name as a no-op. The presenter's `plan_dictionary_state_after_rename` moves the active name when `active_name == previous_name` and `resolve_dictionary_selection` finds `Alpha` in the fresh listing, so `config.json` follows (GUI 104: `selected_dictionary` `Alpha`, a conversion still uses it). `default` -> `Default` is stopped by `is_default_dictionary` (casefold) before any file operation; `alpha` -> `Default` is refused as existing (samefile `False`). The new test patches `samefile` to `False` to pin the case-sensitive refusal on Windows.
- **D11.** `validate_dictionary_csv` and `read_bytes` run inside one `try`; only `PermissionError` is wrapped in `DictionaryImportSourceError` (not an `OSError`, `.error` and `__cause__` set); the copy is written from the bytes outside the `try`, so a `PermissionError` from `os.replace` keeps today's raw message (O7; mutant r25 that wraps every `OSError` is caught by the `FileNotFoundError`-style tests). The presenter catches it before `OSError`. Dictionaries are small; reading them whole is fine.
- **D12.** `DictionaryEntriesDialog(parent, path, model=None)` loads before `super().__init__`; the frame loads itself and passes `model=`, so a read error creates no dialog (F-6's reason, no traceback) and a build error destroys the half-built dialog, logs `Unexpected error while opening the dictionary editor` with `exc_info` to `dotexpress.gui` and shows string 11. GUI 44/47 equal the F-6 logs.

### 1.7 Localization (D15)

| # | msgid | msgstr | Reading |
| --- | --- | --- | --- |
| 1 | `Remove Rows That Cannot Be Shown` | `移除無法顯示的列` | natural; `列` for row follows Excel zh-TW |
| 2 | `Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?` | `字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？` | natural; placeholders and blank lines identical; quotation marks follow `字典「{name}」已存在。` |
| 3 | `Row {line}: no source text` | `第 {line} 列：沒有來源文字` | fine; `來源文字` is the entry dialog's field name |
| 4 | `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid` | `第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確` | natural; `格式不正確` matches the entry dialog's wording style |
| 5 | `Other rows not listed: {count}` | `另有 {count} 列未列出` | fine |
| 6 | `Remove and &Save` | `移除並儲存(&S)` | access-key style of F-5's `重試(&R)`; S and B distinct in the D1 box |
| 7 | `&Back to Editing` | `返回編輯(&B)` | shared by both boxes |
| 8 | `Unsaved Changes` | `尚未儲存的變更` | fine |
| 9 | `Do you want to discard the changes you made to dictionary "{name}"?` | `要放棄對字典「{name}」所做的變更嗎？` | natural |
| 10 | `&Discard Changes` | `放棄變更(&D)` | D and B distinct in the D7 box; the labels are the ones `task.md` section 三 asked for |
| 11 | `Failed to open the dictionary editor: {error}` | `無法開啟字典編輯器：{error}` | follows `無法刪除字典：{error}` |

The two wrong fuzzy guesses of `msgmerge` named in Spec Corrections 10 are replaced (0 fuzzy). `#, python-brace-format` is present on 2, 3, 4, 5, 9, 11 in the `.pot` and `.po`. `test_i18n` pins all eleven msgstr values against the compiled `.mo`.

## 2. Probes and mutants

### 2.1 First-tone rows with and without the tone space (`$SP\parity.py`, `$SP\probes.py` S9; real parser, `data/Bopomofo2Braille.csv`)

| File value of `抹` | `canonical_bopomofo` (what the editor shows) | raw parse | conversion of `抹` |
| --- | --- | --- | --- |
| `ㄇㄚ ` | `ㄇㄚ ` | ok | `⠍⠜⠄` |
| `ㄇㄚ` | `ㄇㄚ ` | fails | `⠍⠜` (fallback: raw symbols through the Bopomofo trie, no first-tone cell) |
| `ㄓㄨㄥ ㄒㄧㄣ ` | same | ok | `⠁⠯⠄⠑⠹⠄` |
| `ㄓㄨㄥ ㄒㄧㄣ` | `ㄓㄨㄥ ㄒㄧㄣ ` | fails | `⠁⠯⠄⠑⠹` |

S9: a dictionary `抹,ㄇㄚ,Bopomofo`; the editor lists `ㄇㄚ ` and `has_changes()` is `False` (no write); conversion gives `⠍⠜`; after adding an unrelated entry and saving, the file holds `抹,ㄇㄚ ,Bopomofo` and conversion gives `⠍⠜⠄`. See I-1.

### 2.2 Self-written mutants (`$SP\mutants.py`; the eight F-11 modules; 14 test modules; unmutated `Ran 565`, `OK`)

```text
r01 loader does not canonicalize a shown Bopomofo row ................ caught (7 tests)
r02 writer drops overflow fields ..................................... caught
r03 _restore_focus without the IsDescendant check .................... caught
r04 confirm_box True for anything but Cancel ......................... caught
r05 model.save keeps the hidden rows in the model .................... caught
r06 model.save does not refresh the snapshot ......................... caught
r07 replace selects by equality ...................................... caught
r08 add selects by equality .......................................... SURVIVED, equivalent (a new entry's text is never a duplicate, so it equals no row)
r09 hidden-row line uses the unstripped text and sequence ............ SURVIVED  (M-2 a)
r10 loader skips a record of empty fields (",,") ..................... SURVIVED  (M-2 b)
r11 conversion compares the stripped type ............................ caught
r12 conversion editor test without the tone-space candidate .......... caught (6 tests)
r13 _on_ok asks about hidden rows only after a change ................ caught (9 tests)
r14 Back to Editing falls through to the save ........................ caught (6 tests)
r15 _on_cancel asks without a change ................................. caught
r16 reason uses the raw text ......................................... caught
r17 _column takes the first position ................................. caught
r18 BOM always written ............................................... caught (70 tests)
r19 writer header: required columns prepended, not appended .......... caught
r20 entry dialog closes after the duplicate box (Skip) ............... caught
r21 is_duplicate without the keep-own-text rule ...................... caught
r22 editor gives the entry dialog an add-style check when editing .... caught (11 tests)
r23 get_entry keeps the stripped sequence (no tone space) ............ caught
r24 frame logs the build error without exc_info ...................... caught
r25 import wraps every OSError of the source ......................... caught
r26 has_changes compares the entries as sets ......................... caught
r27 Remove and Save writes the full list (hidden rows included) ...... caught (46 tests)
r28 whitespace-only source is a rule again ........................... caught (6 tests)
r29 load_dictionary_file counts lines from 0 ......................... SURVIVED, equivalent (only the header's unused line value changes; data rows keep their lines)
r30 _on_ok captures the focus after the boxes ........................ SURVIVED  (M-2 c; a harness limitation)
```

25 caught, 5 survived: r08 and r29 are equivalent; r09, r10 and r30 are M-2. The plan's 51 mutants (all caught per Implementation Notes 2) cover acceptance criterion 8; r09, r10 and r30 are outside that list.

### 2.3 Loader/writer edge cases (`$SP\probes.py`)

| # | File | Editor | After a change is saved | Reading |
| --- | --- | --- | --- | --- |
| S1 | header `text,braille`, row `a,⠁,Bopomofo,extra` | `a` shown, type General (no `type` column) | `text,braille,type` / `a,⠁,General,extra` | the appended `type` column lands on the overflow field `Bopomofo`, which is overwritten (M-5) |
| S2 | header `text, braille, type` (spaces) | rows shown with empty braille (pre-existing: `DictReader` keys are ` braille`) | header `text, braille, type,braille,type`, values in the appended columns | the file was already unusable; before F-11 the writer silently replaced the header and dropped the odd columns. Now the junk is kept and the right columns appended. Acceptable; part of M-1's family |
| S3 | BOM only | no rows | `<BOM>text,braille,type` + the new row | correct |
| S4 | needless quotes, a quoted `x\r\ny` | both rows shown | `"a"` -> `a`; the embedded line break stays quoted | O9 |
| S5 | header `Text,Braille,Type` | every row hidden as "no source text" (pre-existing classification) | after Remove and Save: `Text,Braille,Type,text,braille,type` and the new rows only; **every original row deleted** | M-1 |
| S6 | LF file, hidden row ` 肚子 , ㄉㄨˋ|ㄗ˙ ,Bopomofo` | hidden, line 2 | CRLF, the row removed after the box | the box line shows the stripped `肚子` / `ㄉㄨˋ|ㄗ˙` |
| S7 | header `text,text,braille,type` | `second` shown | `first,second2,⠁,General` | the last position, as `DictReader` |
| S8 | blank first line, then `text,braille,type` and a row | header `()`, both lines hidden as "no source text" (lines 2 and 3) | after Remove and Save: `text,braille,type` only; **the data row deleted** | M-1 (same as `DictReader`, and conversion rejects the file anyway) |
| S10 | header `text,braille` | one row shown | - | conversion raises `CSV must contain columns`; pre-existing, outside #8 |

## 3. Tests, logging, isolation

- Red-first and counts: the plan's `Ran` sequence 1483 -> 1485 -> 1490 -> 1508 -> 1512 -> 1516 -> 1522 -> 1526 -> 1539 -> 1551 -> 1553 and the ten tree ids are the committed ones (Implementation Notes 1); the dry run was replayed twice with 0 mismatches.
- The frame tests use `assertLogs("dotexpress.gui")`; the dialog tests run on temporary folders with `os.fsync` stubbed while an editor is open; no `log/` appeared in the worktree or the scratch copy.
- Strong points: the D1 and D7 boxes are compared as exact records (caption, every line, both labels, parent); file bytes and `st_mtime_ns` are compared for the no-write cases; the writer tests compare bytes; the parity tests compare against `DictReader` on the corpora; `test_wx_call_sites` pins that `GenericMessageDialog` has one call site.
- Gaps: M-2 (section 2.2).

## 4. Spec, plan, record, process

- Spec D1-D15, the behavior table, "Corrected after planning (F-11)" 1-13, Test Plan A-G and acceptance 1-8 have matching code and tests; "Design per File" matches the diff exactly (`gui.py` has only the load/build split; `presenter.py` only the new `except`; `read_problems.py`, `name_prompt.py`, `dictionary_state.py`, `validate_dictionary_csv`, `atomic_write.py` untouched).
- Corrections 3 (generic dialog) and 6 (O13) are appended, not edited into the bodies: D1, D7, "Design per File" (`ui/message_box.py`), the Accessibility section ("Task dialogs present their full text to NVDA") and the Risks still describe `wx.MessageDialog`; the zh-TW twin has the same sentences. The project's convention is to append (M-3).
- The plan's Implementation Notes record the tree ids, the build, the memory wait and the three `b` re-runs with reasons; `auto-results.md` records the exe hashes, the per-item results on both builds, the pre-existing observations, and item 107 as the user's manual item. The record does not quote other programs' window names (the N-f9b item 95 focus line is described, not quoted).
- HANDOFF section 2: no restricted file touched; fixtures not in the range; `AGENTS.md` not in the diff; `POT-Creation-Date` pinned; commit trailers present; no push; no clipboard use.
- Dry-run leftovers: none found. The production diff has no debug code, no environment switch, no test-only hook (the `model=` keyword of the editor is used by `gui.py`, not only by tests); `__pycache__` under the history `auto/` folder is git-ignored and untracked.

## 5. Defaults O2-O11, O13

- **O2** (value comparison, not a dirty flag): sound; an add undone by a delete writes nothing and asks nothing (C1, mutant r26 and the plan's three).
- **O3** (cap 10 + count line): sound; pinned at 10, 11 and 13 rows.
- **O4** (ask again after a failed Remove and Save): sound; the rows stay in the model (plan's `failed-save-drops-hidden-rows`).
- **O5** (an edited row keeps its extras): sound (`replace` copies `fields`).
- **O6** (twin edit keeping its text): sound.
- **O7** (only a source `PermissionError` gets the reason): sound; destination errors keep their text.
- **O8** (file line, header = 1): sound and tested with blank lines and a quoted line break.
- **O9** (CRLF, minimal quoting): see S4; acceptable, the user decided the BOM only.
- **O10** (equality after Delete): see M-4.
- **O11** (a missing file is not created by an unchanged OK): sound.
- **O13** (rows that stay convert from their raw value, the fallback included): see I-1.

## 6. Findings

### Critical

None.

### Important

**I-1 A first-tone row typed without its tone space is shown as `ㄇㄚ ` but converts without the first-tone cell until an unrelated save** (`client/conversion/text/dictionary_rules.py:205-210`, `client/dictionaries/entries.py:165-166`; spec O13 / "Corrected after planning" 6; golden case "first-tone Bopomofo rows convert as before" in `client/tests/test_conversion_text_dictionary_rules.py:143-152`)
- Scenario (probe S9, real parser): a hand-edited dictionary holds `抹,ㄇㄚ,Bopomofo` (the natural way to type a first-tone reading; the editor itself now accepts `ㄇㄚ` typed without the space, item 106). The editor lists the row as `ㄇㄚ `, OK without a change writes nothing, and converting `抹` gives `⠍⠜` (the raw symbols through the Bopomofo trie, no `⠄`). The user adds an unrelated entry and presses OK: the file is rewritten with `ㄇㄚ ` and the same conversion now gives `⠍⠜⠄`. The editor shows one reading, conversion uses another, and the braille of an untouched entry changes because of an unrelated edit. `中心,ㄓㄨㄥ ㄒㄧㄣ,Bopomofo` behaves the same (`⠁⠯⠄⠑⠹` vs `⠁⠯⠄⠑⠹⠄`). The user's #8 decision was that the editor and conversion agree, and O1 (b) was explained as "轉換照常使用"; O13 was an orchestrator default ("user may override before merge") that kept the pre-F-11 fallback for such rows.
- Suggested fix (cheap, one user decision): in `from_paths`, when `processing(target)` raises, use the candidate that the editor accepts instead of the raw string: let `_editor_shows_bopomofo` return the parsed value (`processing(sequence)` or `processing(sequence + " ")`) or `None`, and `continue` only on `None`. Then every shown row converts from the value the editor shows, `抹,ㄇㄚ` gives `⠍⠜⠄` before and after a save, and the fallback scan is reached only for rows the editor hides (which are skipped) so it can go. Flip the golden case to `\[⠍⠜⠄\]`, add a case for `ㄓㄨㄥ ㄒㄧㄣ` without the space, and edit O13 / correction 6 and the Risks in both spec files. This changes conversion output for such rows in existing files (toward what the editor shows and what a later save would produce), so the user should confirm; if the user prefers the current default, the spec's Risks should say that the braille of a first-tone row without its space changes on the first save after any edit.

### Minor

**M-1 A file whose header record is not recognised is listed as "no source text" rows and emptied by Remove and Save** (`client/dialog.py:612-619` `_hidden_row_line`, `client/dictionaries/entries.py:152-167`; probes S5, S8)
- Scenario: a dictionary copied by hand into `dictionary\` with the header `Text,Braille,Type` (Excel capitalises), or with a blank first line, is read as every row hidden (pre-existing: `DictReader` and conversion agree, Dictionary Management counts 0, conversion rejects the file). The editor is empty; OK shows the D1 box with `第 2 列：沒有來源文字`, `第 3 列：...` up to ten lines and `另有 N 列未列出`, which is wrong for rows that plainly have text; `移除並儲存` writes `Text,Braille,Type,text,braille,type` with no data rows. Before F-4 OK dropped them silently; F-4 kept them; F-11 asks, so the user can refuse, but the reason it gives points the wrong way. Import cannot produce such a file (`validate_dictionary_csv`), so only a hand-copied file is affected.
- Suggested fix (cheap, one new string or none): in `_confirm_hidden_rows`, when `self._model` reports a header that lacks any of `text`, `braille`, `type` (expose `layout.header` from the model), put a single line such as `The header does not have the columns text, braille, type` (F-12 may own the wording) before the row lines, or show the raw record (`row.fields`) in the row line when the text is empty. Alternatively document it under Out of Scope. Not a blocker.

**M-2 Three test gaps found by surviving mutants** (section 2.2; all cheap)
- (a) `_hidden_row_line` strips the text and the sequence (`client/dialog.py:612-619`, spec D1 "the values are the stripped text and the stripped sequence"), but no test has a hidden Bopomofo row with surrounding spaces (mutant r09 survives). Scenario under the mutant: ` 肚子 , ㄉㄨˋ|ㄗ˙ ,Bopomofo` is listed as `第 2 列：「 肚子 」的注音「 ㄉㄨˋ|ㄗ˙ 」格式不正確`. Fix: one case in `DictionaryEntriesDialogHiddenRowsTest` with probe S6's row, expecting `_invalid_bopomofo(2, "肚子", "ㄉㄨˋ|ㄗ˙")`.
- (b) A record of empty fields (`,,`) is a hidden row with a line number in the loader and in `DictReader`, but no corpus row pins it (mutant r10, `elif any(record)`, survives). Scenario under the mutant: the row is neither listed nor written after a change, so it vanishes without the D1 box naming it. Harmless data (no field has a value), but the `DictReader` parity (D6) and the line numbering are the contract. Fix: add `,,` and `,,,` rows to `DictionaryLayoutTest.test_values_and_classes_equal_those_of_dictreader` and to the start-line test.
- (c) `_on_ok` and `_on_cancel` read `wx.Window.FindFocus()` before the box (D7 "the editor remembers ... before showing the box"), but the harness's fake `confirm_box` leaves `harness.focus` untouched, so a version that reads it after the box (mutant r30) passes. Fix: let `_EditorHarness._confirm_box` set `self.focus` to a foreign object (or `None`) while it "shows" the box, so only the value captured before the box can be restored; `test_back_to_editing_writes_nothing_and_puts_the_focus_back` then fails under r30.

**M-3 The spec bodies still describe the task dialog** (`docs/superpowers/specs/2026-10-11-f11-dictionary-editor-ux-design.md` D1 line 127, D7 lines 197-202, "Design per File" `ui/message_box.py` line 336, Accessibility line 414, Risks; the zh-TW twin at the same places)
- Scenario: a reader of D7 or of "Design per File" implements or reviews `wx.MessageDialog` with `SetOKCancelLabels`, the variant that answers Alt+F4 with OK when shown from the editor (correction 3). The correction is appended under "Corrected after planning", the project's convention, and the plan and code are right.
- Suggested fix (cheap): one sentence at each place ("`wx.GenericMessageDialog`; see correction 3"), in both files; optional.

**M-4 After deleting one of two identical rows the selection jumps to the other twin, not to the neighbour** (`client/dictionaries/entry_list_model.py:198-205, 219-237`; spec O10, D9 "Selection")
- Scenario: `[a, b, a]`, row 3 selected, Delete: the list is `[a, b]` and the selection goes to row 1 (the first equal row), while deleting a non-twin selects the row now at that index. For an NVDA user who hears "a" selected after deleting "a", it can sound as if nothing was deleted. Before F-11 the first `a` was removed and the remaining `a` (now row 2) was selected, so the heard row was the same. The spec keeps equality because the golden trace pins it (probe 1: seeds 23, 29, 33, 37 differ otherwise).
- Suggested fix: none now; re-recording the trace is not cheap and the user confirmed O10 by default. Listed so the user sees it; a follow-up could restore the selection by index after Delete (fallback first) when the trace is next re-recorded.

**M-5 An appended required column overwrites an overflow field at that position** (`client/dictionaries/entries.py:198-209`; probe S1)
- Scenario: header `text,braille` (no `type`), row `a,⠁,Bopomofo,extra`. The loader reads type as missing (General), the writer appends `type` as column 3 and writes `General` there, over the overflow value `Bopomofo`; `extra` survives. The file was malformed and `DictReader` already ignored that value for the type, so nothing the editor showed is lost.
- Suggested fix (cheap, optional): when a required column is appended, insert `""` at that position in each row's `fields` before setting the value (so the overflow fields shift right and stay), or accept and note it under O9. Not a blocker.

## 7. Items for the user (not findings)

- Item 107 (NVDA): the only unverified behaviour is whether NVDA reads the generic dialog's four text lines in full; the UIA readings show them as separate Text elements under the dialog, which NVDA normally reads on dialog focus.
- The release notes should say that whitespace-only and invalid Bopomofo rows no longer convert (spec Risks), and, depending on I-1, what happens to first-tone rows without their space.

## 修正記錄 (disposition, 2026-10-11)

Fixed test first on `fix/f11-dictionary-editor-ux` (worktree `D:/workspace/DotExpress-f11`). Commits: `584d78a` (M-2 tests), `bb36417` (M-5), `7c4037b` (M-1, string 12, catalogs; `HEAD:client` `0281ca0a8cc5f45142c732ae9f48896649bc5680`), `976440f` (spec, EN and zh-TW: "Corrected after review (F-11, 2026-10-11)" 1-5 and M-3 in the bodies), `ad55043` (GUI record for the build `N-f11b`, new `auto/item108.py` and `auto/safe_run.py`, item 108 in both spec files, plan Implementation Notes, fix phase), and this record. Full suite at `7c4037b` and after: `Ran 1564` (1553 + 3 M-2 + 1 M-5 + 7 M-1), `OK (skipped=6)`; the acceptance-criterion-2 set `Ran 560`, `OK`; `KNOWN BUG` grep empty. msgids 380 -> 381, 381 translated, 0 fuzzy, a second `msgmerge` a no-op, `POT-Creation-Date` `2026-10-10 12:00+0800`. Fixture sha256s unchanged (`e67d95a1...`, `f493da52...`, `8dc8572e...`); no `client/log/`, `client/workspace/` or `client/config.json` in the worktree; the main checkout's application data was not touched.

| Finding | Disposition |
| --- | --- |
| I-1 | **Resolved per the user's decision (2026-10-11).** Not the suggested fix (convert from the re-appended sequence) but the user's rule: a Bopomofo field loses only its leading whitespace, trailing whitespace is kept as in the file or as typed, and nothing appends a tone space anywhere. A sequence that does not parse as it is (`ㄇㄚ`, `ㄇㄚ  `) is invalid: the editor hides it, OK lists it in the D1 box, conversion ignores it; `from_paths` parses `target.lstrip()` once, the editor's rule, with no fallback. `ㄇㄚ ` and `ㄓㄨㄥˋㄒㄧㄣ ` stay valid and convert as before. The entry dialog no longer strips the end of a Bopomofo field, so `ㄇㄚ` gets the existing format error (no new string). Commits `a79c51f` (code, tests, catalog references; `HEAD:client` `5e130210420bf7a3828936094ac0af5868c32801`, `Ran 1567`, `OK (skipped=6)`) and `d5c28aa` (spec, both languages: D13, D14, correction 6/O13, O1, Risks, item 106). The golden case "first-tone Bopomofo rows convert as before" keeps the row with the space and drops the one without it; two cases added. The three fixtures are unchanged. Thirteen mutants caught. GUI on `N-f11c`: item 106 (adjusted, `auto/item106.py`), 95/96, 103, 35 on both builds, 97/98, 101/102, 99/100 on N-f11c; see `auto-results.md` 「審查 I-1 階段」. |
| M-1 | **Fixed (code, one new string).** `LoadedDictionary.header_recognized` is False when the header names no `text` column and at least one row is hidden (a capitalized header, another name, a blank first line); the model takes it from the load and its `save` raises `ValueError` without writing while it is False; `_on_ok` checks it first and shows `Dictionary "{name}" cannot be saved: its header is not recognized. The first line of the file must contain the text, braille, and type headers.` / `無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。` (caption 錯誤), writes nothing, keeps the editor open and restores the focus, with or without a change; no D1 box. Cancel unchanged; opening the editor unchanged; a header without `text` and without data rows still saves (nothing to lose). Chosen as the simplest safe design (one check in OK, one guard in the model; the loader's `DictReader`-equal classification and the opening path untouched); refusing to open the editor and a header line inside the D1 box were rejected. Recorded in both spec files as "Corrected after review" 1, marked "Decided by orchestrator with the recommended default; user may override before merge"; defaults list item 11. Tests: `HeaderRecognizedTest` (3), `DictionaryEntriesDialogUnrecognizedHeaderTest` (3), `test_unrecognized_dictionary_header_string_is_translated`. Mutants f1-f5 (no check in OK, no guard in `save`, the flag always True, the flag ignoring hidden rows, `load` dropping it) all caught. GUI item 108 (new): N-f11b shows the error box, offers no removal, keeps both files byte-identical and the editor open; N-f9b (before F-11) rewrites both files with one `,,` per row. |
| M-2 | **Fixed (tests).** (a) `test_a_row_line_shows_the_stripped_source_text_and_sequence` (probe S6's row); (b) `EMPTY_FIELDS_CSV` in the `DictReader` parity corpus and `test_a_record_of_empty_fields_is_a_hidden_row_on_its_line`; (c) the harness's `message_box` and `confirm_box` now move `focus` to a box button (as a real box takes the focus), plus `test_a_failed_save_puts_the_focus_back_where_it_was_before_the_message`. On a scratch copy of `client/` (`f11fix\m2copy`): r09, r10, r30 and a new r30b (`_restore_focus` reading `FindFocus` after the box) all survive the tests of `4d229b4` and are caught by the new tests (r09 by (a); r10 by both (b) tests; r30 by the failed-save test; r30b by four focus tests). |
| M-3 | **Fixed (spec only, EN and zh-TW).** D1, D7, "Design per File" (`ui/message_box.py`), Accessibility and Risks now describe `wx.GenericMessageDialog` (labels by `SetOKCancelLabels`, Esc/Enter/Alt+F4/close box answer Cancel, one text element per line, NVDA reading is item 107); "Corrected after review" 3. |
| M-4 | **Listed for the user.** No code change; the selection after deleting one of two identical rows still goes to the first equal row (O10, pinned by the golden trace). |
| M-5 | **Fixed (code, no string).** The writer puts appended required columns after the header's fields and before the overflow fields, which move right (`text,braille` / `a,⠁,Bopomofo,extra` -> `text,braille,type` / `a,⠁,General,Bopomofo,extra`); without a header (the default layout) a record's first fields are still text, braille, type, so callers without a layout keep their bytes. Test `test_an_appended_column_goes_before_the_overflow_fields` (red first); mutant f6 (the old line) caught. "Corrected after review" 2 and D5, marked as an orchestrator default; defaults list item 12. |

GUI (build `D:/dxtest/N-f11b`, sha256 `41E7575D...`, from `976440f`): fix items 95/96, 97/98, 101/102, 103/106, 35, 23/24, 25-29 and 108 on N-f9b and N-f11b, regression item 99/100 on N-f11b; every log equals the first run's apart from folder names (and, on N-f9b, the focus, which is not compared), except `auto35-f11b`, stopped by a `SetForegroundWindow` tool error while the user was using the desktop and re-run as `auto35b-f11b` (equal). The scripts ran through `auto/safe_run.py`, which sends a key only while the app under test is in the foreground and writes `<another program>` instead of a foreign element's name. Only processes under the new `D:/dxtest/*-f11b` folders were ended; nothing touched the clipboard. Item 107 (NVDA) stays unchecked for the user.

User-visible changes the user has not confirmed: the M-1 behaviour and its string 12 (wording included), the M-5 column order in a malformed file; both marked as orchestrator defaults in the spec.

Update (2026-10-11): the user accepted M-1 (string 12, no removal and no write for an unrecognised header) and M-5 (appended columns before the overflow fields); both spec files now mark them "accepted by the user (2026-10-11)". I-1 is resolved per the user's decision (table above). Consequences of that rule beyond its examples, for the user to know: a Bopomofo row with a trailing space after a tone mark (`ㄉㄨˋㄗ˙ `) or a trailing tab or U+3000 is now invalid too (hidden, listed, not converted; before it was shown and converted through the fallback), and the entry dialog refuses such input; a row with leading whitespace (` ㄇㄚ `) now converts from the sequence without it (`⠍⠜⠄`) instead of the fallback's `⠄⠍⠜⠄`, the value it gave after any save. The D1 box line still shows the stripped sequence, so `ㄇㄚ  ` and `ㄉㄨˋㄗ˙ ` are listed as 「ㄇㄚ」 and 「ㄉㄨˋㄗ˙」 (unchanged behaviour of D1).
