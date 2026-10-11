# Dictionary Editor UX (F-11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** The custom dictionary editor behaves as the user decided on 2026-10-10 (U1-U6) and 2026-10-11 (O1 (b)). OK writes the file only after a change and then keeps its BOM, header and extra columns; rows the editor cannot show are listed in a box on OK and removed only after Remove and Save; Cancel, Esc and the close box ask before discarding changes; a duplicate source text is reported inside the entry dialog, which keeps the input; Delete and Edit act on the selected row; a Bopomofo sequence whose last syllable is first tone keeps its tone space and is shown; conversion ignores exactly the rows the editor hides; a case-only dictionary rename works (F-W6, the only failing test); a locked Import source gets F-6's reason; the editor reads its file before its window exists. Eleven new msgids (369 -> 380).

**Architecture:** Ten commits on the client, each red first, the spec's migration steps in another order (Spec Corrections 2). Task 1 lets `rename_dictionary` rename a file to another case of its own name (`os.path.samefile`, D10). Task 2 wraps a `PermissionError` reading an Import source in `DictionaryImportSourceError`, which the presenter shows with F-6's reason (D11). Task 3 replaces the `DictReader` loader by `load_dictionary_file` (`csv.reader`, the same values, plus each record's fields and start line and the file's BOM and header) and makes the writer keep that layout (D5, D6). Task 4 makes `remove` and `replace` act by identity and adds `is_duplicate` (D9). Task 5 checks duplicates over the shown entries only and moves the check into the entry dialog's OK (D2, D8). Task 6 keeps the tone space of a final first-tone syllable (`canonical_bopomofo`, D14). Task 7 reads the dictionary before the editor's native dialog exists, in the frame and in the constructor, with string 11 (D12). Task 8 adds `ui.message_box.confirm_box` (wx's generic dialog, Spec Corrections 3) and the hidden-rows box on OK, with strings 1-7 (D1). Task 9 adds `has_changes`, writes only after a change and asks on Cancel, Esc and the close box, with strings 8-10 (D3, D4, D7). Task 10 makes conversion skip the rows the editor hides (D13). Task 11 verifies (suite, shuffled order, catalogs, fixtures, application data, 51 mutants), Task 12 builds the exe and runs the GUI checks (items 95-106 and the re-runs of 23-29, 35, 44 and 47; item 107 stays manual).

**Tech Stack:** Python 3.13 standard library (`csv`, `codecs`, `dataclasses`, `os.path.samefile`, `logging`, `unittest`, `unittest.mock`), wxPython 4.2.5 (`wx.GenericMessageDialog` for the two confirmation boxes; the other boxes stay `ui.message_box.message_box`), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-11-f11-dictionary-editor-ux-design.md` (+ `_zh-TW.md`), with the section "Corrected after planning (F-11, 2026-10-11)" / 「規劃後的修正（F-11，2026-10-11）」 added in the plan commit (both languages); O1 is decided there ((b), the user, 2026-10-11) and GUI item 106 is in scope. The user decided U1-U6 (2026-10-10), O1 (2026-10-11) and O12 (2026-10-11, the classic dialog of Spec Corrections 3). O2-O11 are the orchestrator's recommended defaults; the plan adds O13 (Spec Corrections 6), also a default the user may override before the merge.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f11`, branch `fix/f11-dictionary-editor-ux` (HEAD is the plan commit on top of the spec commit `cc8c002`, which is on `main` at `1ce6ce5`, the F-9 merge). Never switch branches, never push, never merge, never rewrite history. The worktree has no `client\.venv`: `PY` is the main checkout's interpreter, run with the working directory inside the worktree. Do not work in the main checkout `D:\workspace\DotExpress` (the user may run the app from source there) and do not touch `D:\workspace\DotExpress-6e5819f` or `D:\workspace\DotExpress-f9`.
- Files that may change (25 under `client/`, nothing else there): production `client/dictionaries/entries.py`, `client/dictionaries/entry_list_model.py`, `client/dictionaries/presenter.py`, `client/dialog.py`, `client/gui.py` (**tabs**), `client/dictionaries/manager.py`, `client/ui/message_box.py`, `client/conversion/text/dictionary_rules.py` (4 spaces); tests `client/tests/test_dictionary_entries.py`, `client/tests/test_dictionary_entry_list_model.py`, `client/tests/test_dictionary_name_prompt.py`, `client/tests/test_dictionary_presenter.py` (**tabs**), `client/tests/test_dictionary_entries_dialog.py`, `client/tests/test_dialog_validation.py`, `client/tests/test_dictionary_manager.py`, `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py`, `client/tests/test_message_box.py`, `client/tests/test_wx_call_sites.py` (4 spaces); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`; in Task 12 the new history folder `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/` (scripts with tabs, results) and this plan's Implementation Notes.
- Never touch, in the main checkout `D:\workspace\DotExpress`, `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data; Task 0 and Task 11 only hash them), or its untracked `client2/`, `preprocessing/`, `testdata/` and `task.md` (read-only). In the worktree no test may create `client/log/`, `client/workspace/` or `client/config.json`: the modules whose code under test logs already isolate `dotexpress.gui` (`test_gui_document_flows`), and the new tests use temporary folders. Never touch `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in either checkout: only packaged copies, each in a new `D:\dxtest\auto*-f11` folder. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (no `SetClipboardData`, no Ctrl+C/V/X, no `wx.TheClipboard`; text reaches the app through files and `set_edit_text`). `git status --short -- client docs scripts` must stay empty between commits (`docs/` holds the history folder of Task 12 only until Task 12 commits it).
- The worktree uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compared with CRLF converted to LF; the file keeps its line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc (it turns `\\` into `\`). Several test files hold backslash-u escapes (`test_dictionary_entries.py`, `test_dictionary_entry_list_model.py`, `test_dictionary_entries_dialog.py`, `test_dictionary_presenter.py`), and so do the blocks that edit them: the Edit/Write tools turn such an escape into its character, so never rewrite or patch these files through them. `apply_blocks.py` reads and writes bytes; the tree id check after each commit catches any other change.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, `translation_liblouis_golden.json` `8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e` (`git show HEAD:<path> | sha256sum`), unchanged.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- The only failing test before F-11 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames`; Task 1 fixes it, so from Task 1 on the suite ends `OK (skipped=6)` (Spec Corrections 1).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (F-9's: FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`, object addresses as `<addr>`). A failure line that shows a path inside the system temporary folder in a cut diff (`[84 chars]`) depends on the length of that folder's name; on another account it can differ in that count only. Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks. Tests run as `$PY -B -X utf8 -m unittest ...` (no bytecode in the worktree).
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f11
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f11impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: only its interpreter is used, its git-ignored runtime is copied into the worktree (Task 0 Step 2), and its application data is hashed read-only (Task 0 Step 4, Task 11 Step 5). The dry run used scratch clones as `REPO`. Task 12 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning (F-11, 2026-10-11)" in the plan commit. Re-checked against the code of `main` `1ce6ce5`: every decision D1-D14, the behavior table and the reachability list hold, with the refinements below.

1. **Baseline and counts.** On `1ce6ce5` the suite gives `Ran 1483`, `FAILED (errors=1, skipped=7)` (F-W6 only) and the catalogs hold 369 msgids. F-11 adds 70 tests net: `Ran 1485` after Task 1, `1490` after Task 2, `1508` after Task 3, `1512` after Task 4, `1516` after Task 5, `1522` after Task 6, `1526` after Task 7, `1539` after Task 8, `1551` after Task 9, `1553` after Task 10 (the spec estimated about 60 new tests and 8 flipped or removed). The end state is `OK (skipped=6)`, not `skipped=7`: `test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file` skipped itself on a case-insensitive file system ("a case-only rename is reported as a duplicate", which is F-W6); Task 1 removes that skip, so the test runs on Windows. msgids 369 -> 380: string 11 in Task 7, strings 1-7 in Task 8, strings 8-10 in Task 9; D14 adds none (re-checked). The acceptance-criterion-2 set (the ten modules of the spec) goes from `Ran 482`, `FAILED (errors=1, skipped=1)` to `Ran 549`, `OK`.
2. **Migration order.** The tasks are: 1 D10, 2 D11, 3 D5 and D6, 4 D9, 5 D2 and D8, 6 D14, 7 D12 (string 11), 8 D1 (strings 1-7), 9 D3, D4 and D7 (strings 8-10), 10 D13; each commit keeps the spec's subject. Reasons: (a) D1 comes before D4. With D4 alone, OK on a golden-trace sequence that ends without a net change would write nothing, so the recorded CSV would be missing until D1; D1's box makes every trace OK write (`TRACE_CSV` has two hidden rows), so the trace passes in every commit. (b) The catalogs are regenerated only in the three tasks that add strings, and Task 9 is the last task that moves lines above msgids (Task 10 changes no file with msgids), so no `#:` reference is stale at the end. (c) D14 comes before D13, so the conversion rule and its parity test include the first-tone case from the start. (d) String 7, `&Back to Editing`, is first used by D1's box, so it comes with Task 8.
3. **`confirm_box` is wx's generic dialog (O12).** Measured while planning (wx 4.2.5, Windows 11 zh-TW, a wx dialog that shows the box from its OK handler, as the editor does): a native task dialog with custom labels (`wx.MessageDialog`, `wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`, `SetOKCancelLabels`) returns `wx.ID_OK` for **Alt+F4**, while Esc, Enter and the close box return `wx.ID_CANCEL`. With only the OK label customized it is the same; with `SetYesNoLabels` Alt+F4 returns `wx.ID_YES`; with the standard labels it returns `wx.ID_CANCEL`. The spec's probe 2 showed the box over a frame with no modal dialog running; that setup still returns `wx.ID_CANCEL` (re-run while planning). With a task dialog, Alt+F4 in the D1 box would remove the hidden rows and in the D7 box discard the changes. `wx.GenericMessageDialog` with the same style and labels answers Esc, Alt+F4, Enter and the close box with `wx.ID_CANCEL`; Alt+S, Alt+B and Alt+D press the labelled buttons; the focus starts on 返回編輯(B) (in the packaged build: GUI items 95, 99, 35). For the user, the two boxes are classic dialogs (a warning icon, one text line per line of the message, no bold main instruction) instead of task dialogs; whether NVDA reads them in full is manual item 107. `message_box`, the task dialog of every other box, is unchanged. Decided by the user (2026-10-11): use the classic dialog, as built. The user's hard requirement is that Esc, Alt+F4 and the close box never trigger Remove and Save or Discard Changes; that they answer Back to Editing is not required in itself. (F-5's close dialog also has custom labels; it is shown from the frame, not from a modal dialog, so this measurement does not apply to it; not checked here.)
4. **The F-W6 test's last assertion** `assertFalse((directory / "alpha.csv").exists())` cannot hold on a case-insensitive file system: after the rename the file still answers to `alpha.csv`. Task 1 replaces it with the folder listing `["Alpha.csv", "default.csv"]`, which holds on every file system.
5. **D11: the source is read before the copy is written.** `import_dictionary` validates and reads the source inside one `try` (`validate_dictionary_csv`, then `Path.read_bytes`) and writes the copy from those bytes, so a `PermissionError` of the source is told apart from one writing the copy without looking inside `write_bytes_atomically`. Dictionaries are small CSV files; the bytes copied are the same.
6. **D13: rows that stay convert as before; the raw value is parsed first (O13).** `from_paths` parses a Bopomofo row's raw value as before; only when that raises does it apply the editor's test (the stripped sequence, then with the tone space of D14) and skip the row if that fails too. With the real parser a raw value that parses always passes the editor's test (it has no leading space and at most the one final tone space), so the rule equals `_is_editable`; `EditorParityTest` checks 23 rows, and a test pins that a row that stays is parsed once, on its raw value. A Bopomofo row the editor shows converts exactly as before, so a hand-written final first-tone row without its space (`抹,ㄇㄚ,Bopomofo`) keeps today's fallback conversion of its raw symbols; the editor shows it as `ㄇㄚ ` and writes the space only when the file is saved after a change. Decided by orchestrator with the recommended default; user may override before merge.
7. **The trace replay has two adaptations, not one.** Besides answering the D1 box and taking its record out of the OK step (D1), the replay takes the editor's new `Bind` of its Cancel button out of the open step's log when it is there (D7); `test_construction_log_is_exact` pins the whole construction log. The fake entry dialog keeps the dialog open after a duplicate and takes the next scripted answer, cancelling when none is left, so the recorded `MessageBox` events stay the same. `dictionary_entries_trace.json` is unchanged (`f493da52...`).
8. **D9: after Delete the selection goes to the first equal row.** With two identical rows, deleting the second selects the first: the equality rule the golden trace records (O10). Edit keeping a twin's text and Replace select by identity.
9. **D12 in the frame:** `gui.py` imports `DictionaryEntryListModel`, loads the model and passes `model=`; the unexpected-error line goes to `gui.py`'s module logger `dotexpress.gui` (`gui.log`). In the constructor the path and model are set after the native `__init__`, and a failure while building calls `Destroy` and re-raises.
10. **Strings.** The duplicate message keeps one call site (`show_duplicate_source_text` in `dialog.py`), used by the entry dialog and by the editor's backstop, so D8 adds no msgid. `msgmerge` guesses two wrong fuzzy translations: `Failed to open the dictionary editor: {error}` <- `無法刪除字典：{error}` (Task 7) and `Do you want to discard the changes you made to dictionary "{name}"?` <- `要刪除字典「{name}」嗎？` (Task 9); the fill steps replace both msgstr values and drop the fuzzy flag.
11. **Tests the spec did not list:** `test_wx_call_sites` (the only `GenericMessageDialog` is `confirm_box`), `test_message_box` (`confirm_box`, two tests), `test_dialog_validation` (D8: three tests; D14: two), the conversion golden cases (one flipped, three added), `test_dictionary_entries`' round trip (the hidden rows are no longer rules), the presenter's case-only rename (unskipped). The validation test of D14 collects the error messages instead of letting the parser's error escape: `text.zhuyin.ParseError` is a frozen dataclass, and unittest cannot attach a traceback to it (the run stops without a `Ran` line).
12. **Windows items:** 95-106 as the spec numbers them, the manual NVDA item is 107; "Before" is `D:\dxtest\N-f9b` (F-9 after its review, the code of `1ce6ce5`); the new build goes to `D:\dxtest\N-f11`. Corrections: item 98 expected "bom_lf.csv stays without BOM", but `bom_lf.csv` has a BOM (and LF line ends): after the edit it keeps its BOM and gets CRLF. Item 106 uses readings that differ from liblouis's own, so that the output shows that both rules are used: `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` in `tone1.csv` and the Add `抹`/`ㄇㄚ` (a first-tone reading typed without its space). Item 105 takes the share-none lock after the Import file dialog has closed: the Windows file dialog does not accept a file that no one may share, and in use another program takes the file while the name is typed. Items 23-29 run in the new scripts `rerun23.py` (23, 24) and `rerun25.py` (25-29), which edit a row first so that OK writes; item 35 runs in a new `item35.py`; items 44 and 47 run F-6's `item42.py` and `item47.py` unchanged (their logs are equal on both builds apart from the folder name in item 47's `gui.log` line).
13. **D14 is adopted (O1 (b), decided by the user on 2026-10-11).** Task 6 implements it; GUI item 106 is in scope.

## Dry Run

The plan was replayed on scratch clones of the repository at the spec commit `cc8c002` with a stand-in plan commit (this plan and the corrected spec files) on `fix/f11-dictionary-editor-ux` (`$SP/f11plan/r*`, never the worktree or the main checkout), by F-9's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. That replay of Tasks 0-11 produced every expected block of this plan (0 mismatches), including all red runs, the catalog steps, the per-commit tree ids, the six shuffle seeds and the 51 mutants; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. The code itself was developed on a separate clone, red first, in the same ten steps; the blocks are that clone's diffs, and its tree ids equal the replay's.

Then (the user merged planning and implementation into one run, 2026-10-11) a fresh clone of the branch with the plan commit applied every step with Task 0 Step 3's `apply_blocks.py` and committed each task; its commits became the worktree's commits. Task 12 then ran once, on the build of the worktree (`D:\dxtest\N-f11`) against `N-f9b`. Both are recorded in the Implementation Notes.

Drafts of the GUI scripts, run against a development build and `N-f9b`, found the problems that shaped Task 12 and Spec Corrections 3 and 12: pywinauto's `send_keys` drops a space, so buttons are pressed with `BM_CLICK` after `set_focus` (the focus stays on the button, as after a click); the Windows file dialog does not accept a file that no one may share; a task dialog with custom labels shown from the editor answers Alt+F4 with OK; the readings of item 106 had to differ from liblouis's to show that the rules are used; `ㄓㄨㄥˋ ㄒㄧㄣ` (with a space after the fourth tone) does not parse, the right sequence is `ㄓㄨㄥˋㄒㄧㄣ `. No script wrote to the clipboard.

## Review Focus

1. **The hidden rows** (D1, D2, D6): the start line of each hidden row (header = 1, blank lines and quoted line breaks counted), the box text and its cap, Remove and Save writing the shown entries only, Back to Editing writing nothing and putting the focus back, a failed save asking again; the trace replay's two adaptations (Spec Corrections 7) (A2, A5, B6, C3, C4, C10; 8 mutants; GUI 95, 103, 35).
2. **What a change is and when OK writes** (D3, D4, D7): `has_changes` by value and order, a missing file not created, Cancel/Esc/close box asking only after a change, and the generic dialog that makes Alt+F4 mean Back to Editing (Spec Corrections 3) (B1, C1, C5; 12 mutants; GUI 97, 99, 100, 23-29).
3. **The layout** (D5, D6): the `csv.reader` loader equals `DictReader` (parity tests on the F-4/F-6 corpora), the BOM detected from the bytes, the header kept and completed, extra and overflow fields kept, an edited row keeping its fields (A1-A4; 6 mutants; GUI 97, 98, 23, 24).
4. **Duplicates and identity** (D2, D8, D9): the entry dialog's check after the format checks, the input kept and the source text selected; the twin rule; identity for Delete/Edit and the selection rules (B2-B5, C7, C8, D; 8 mutants; GUI 101, 102).
5. **Bopomofo with a final first tone** (D14) and **conversion** (D13): `canonical_bopomofo`, the entry dialog and the loader; conversion skipping exactly what the editor hides, kept rows converting as before (Spec Corrections 6) (A6, F; 7 mutants; GUI 96, 106).
6. **Rename, Import, opening the editor** (D10-D12) (E, C9; 9 mutants; GUI 104, 105, 44, 47).
7. **Catalogs and strings:** eleven msgids, 380 translated, 0 fuzzy; two wrong fuzzy guesses of `msgmerge` replaced (Spec Corrections 10).

## File Map

- Task 1: `client/tests/test_dictionary_name_prompt.py` (F-W6's listing, the samefile test), `client/tests/test_dictionary_presenter.py` (the case-only rename unskipped, the active one); `client/dictionaries/manager.py` (`rename_dictionary`, `_is_same_file`).
- Task 2: `client/tests/test_dictionary_manager.py` (three tests), `client/tests/test_dictionary_presenter.py` (two); `client/dictionaries/manager.py` (`DictionaryImportSourceError`, `import_dictionary`), `client/dictionaries/presenter.py` (`import_from_file`).
- Task 3: `client/tests/test_dictionary_entries.py` (the oracle `_dictreader_rows`, `DictionaryLayoutTest`, `DictionaryWriterLayoutTest`), `client/tests/test_dictionary_entry_list_model.py` (two), `client/tests/test_dictionary_entries_dialog.py` (the BOM test flipped, extra columns); `client/dictionaries/entries.py` (`DictionaryEntry.fields`, `PreservedDictionaryRow.line`/`fields`, `DictionaryLayout`, `LoadedDictionary`, `load_dictionary_file`, the writer), `client/dictionaries/entry_list_model.py` (the layout, `replace` copying `fields`).
- Task 4: `client/tests/test_dictionary_entry_list_model.py` (two Q4 pins flipped, five tests), `client/tests/test_dictionary_entries_dialog.py` (two Q4 pins flipped); `client/dictionaries/entry_list_model.py` (`is_duplicate`, `_full_index`, identity in `remove`/`replace`, `_selection_after(by_identity=...)`, docstring).
- Task 5: `client/tests/test_dictionary_entry_list_model.py` (F-4 D5's two tests replaced by one), `client/tests/test_dictionary_entries_dialog.py` (the fake entry dialog, two Q6 pins flipped, three tests), `client/tests/test_dialog_validation.py` (`AddSymbolDialogDuplicateTest`); `client/dictionaries/entry_list_model.py` (`source_text_exists`), `client/dialog.py` (`show_duplicate_source_text`, `AddSymbolDialog(is_duplicate=...)`, `_open_entry_dialog`).
- Task 6: `client/tests/test_dictionary_entries.py` (`MIXED_ROWS`, the oracle, `CanonicalBopomofoTest`), `client/tests/test_dictionary_entry_list_model.py` (a comment), `client/tests/test_dictionary_entries_dialog.py`, `client/tests/test_dialog_validation.py` (`AddSymbolDialogEntryTest`); `client/dictionaries/entries.py` (`canonical_bopomofo`, `_is_editable`, `_read_row`, `validate_dictionary_entry`), `client/dialog.py` (`get_entry`).
- Task 7: `client/tests/test_dictionary_entries_dialog.py` (the harness's `model`, the Q8 pin flipped, three tests), `client/tests/test_gui_document_flows.py` (`DictionaryManagementFrameTest`), `client/tests/test_i18n.py`; `client/dialog.py` (`DictionaryEntriesDialog.__init__`), `client/gui.py` (`on_open_dictionary_management`); the three catalogs.
- Task 8: `client/tests/test_dictionary_entries_dialog.py` (the harness's `confirm_box`, focus and `IsDescendant`; the hidden-rows tests; the Q2 pin for a file with hidden rows; the trace replay), `client/tests/test_dictionary_entry_list_model.py`, `client/tests/test_dictionary_entries.py`, `client/tests/test_message_box.py`, `client/tests/test_wx_call_sites.py`, `client/tests/test_i18n.py`; `client/dictionaries/entries.py` (`reason`), `client/dictionaries/entry_list_model.py` (`hidden_rows`, `save`), `client/ui/message_box.py` (`confirm_box`), `client/dialog.py` (`_on_ok`, `_save`, `_confirm_hidden_rows`, `_hidden_row_line`, `_restore_focus`); the three catalogs.
- Task 9: `client/tests/test_dictionary_entries_dialog.py` (`press_cancel`, the construction log, the Q5 pins, `DictionaryEntriesDialogChangesTest`, the trace replay), `client/tests/test_dictionary_entry_list_model.py` (`HasChangesTest`), `client/tests/test_i18n.py`; `client/dictionaries/entry_list_model.py` (`has_changes`), `client/dialog.py` (the Cancel binding, `_on_ok`, `_on_cancel`); the three catalogs.
- Task 10: `client/tests/test_conversion_text_dictionary_rules.py` (one golden case flipped, three added, `EditorParityTest`), `client/tests/test_dictionary_entries.py` (the round trip); `client/conversion/text/dictionary_rules.py` (`_editor_shows_bopomofo`, `from_paths`).
- Task 12: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/` (`auto/f11gui.py`, `auto/item95.py`, `auto/item97.py`, `auto/item99.py`, `auto/item101.py`, `auto/item103.py`, `auto/item104.py`, `auto/rerun23.py`, `auto/rerun25.py`, `auto/item35.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | `HEAD:client` |
| --- | --- | --- | --- | --- | --- |
| baseline (`1ce6ce5` + spec + plan) | - | 1483 | `FAILED (errors=1, skipped=7)` | 369 | `a64da653f7348440a9a8b7419cb9aaea1e7a3440` |
| 1 case-only rename | 2 | 1485 | `OK (skipped=6)` | 369 | `18b797ebc38fc1bb937e4484fe664bbba6de2d54` |
| 2 locked Import source | 5 | 1490 | `OK (skipped=6)` | 369 | `3c987c0912f1144fe237e6acbf5af2e675d1608c` |
| 3 layout | 18 | 1508 | `OK (skipped=6)` | 369 | `eafdc94c70fa1cc7259b80b0bc0494b695e086f3` |
| 4 identity | 4 | 1512 | `OK (skipped=6)` | 369 | `8c7487cb749098f0cfd54c0bf18821e690219062` |
| 5 duplicates in the entry dialog | 4 | 1516 | `OK (skipped=6)` | 369 | `b2cfda106215f90233282722b2d06f37bfabee15` |
| 6 first-tone final syllables | 6 | 1522 | `OK (skipped=6)` | 369 | `6c3946d1eaa1c8749e826e06d1590f721df1bbf9` |
| 7 read before building | 4 | 1526 | `OK (skipped=6)` | 370 | `8dcde92c72263e3d333f789965aacbda99f791ab` |
| 8 hidden rows | 13 | 1539 | `OK (skipped=6)` | 377 | `b3da7431a5bb6408e0b209b7bc2a3b0c24147dba` |
| 9 changes, Cancel | 12 | 1551 | `OK (skipped=6)` | 380 | `239eaf1dc896559c9bb450ea5177399ea56729ec` |
| 10 conversion | 2 | 1553 | `OK (skipped=6)` | 380 | `0d0f93c8340a7ca86bcaf46775b7970ad90b4935` |
| 12 GUI results (docs only) | - | 1553 | `OK (skipped=6)` | 380 | `0d0f93c8340a7ca86bcaf46775b7970ad90b4935` |

"Tests added" is the net count (new tests minus removed ones; a renamed or flipped test counts as neither). The 6 skips are POSIX-only tests; the seventh skip of the baseline was the case-only rename of `test_dictionary_presenter`, which Task 1 runs (Spec Corrections 1).

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (F-9's, unchanged), `mo_check.py` (listing the eleven F-11 msgids), `f11_mutants.py` (51 mutants of the code after Task 10, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-9's with its docstring naming this plan; applies the `File:` and `Edit:` blocks of one step).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~1 HEAD~2 HEAD~2:client
git -C $REPO diff --stat 1ce6ce5 -- client
```

Expected (`status` and the diff print nothing; `HEAD~1` is the spec commit, `HEAD~2` is `main` at `1ce6ce5`):

```text
docs: plan for dictionary editor UX (F-11)
fix/f11-dictionary-editor-ux
cc8c002d1bc1ebf6ba21f30f90acdc992f9bf35a
1ce6ce5b3eb65d3df16cb2e90484a81e71cb5a1e
a64da653f7348440a9a8b7419cb9aaea1e7a3440
```

- [ ] **Step 2: The git-ignored runtime the tests load.** The worktree was made without the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac`; the guarded copies below bring them from the main checkout, as F-3's Task 0 did (in a worktree that has them already they do nothing). Never stage these files.

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/liblouis
test -e $REPO/client/mathcat || cp -r $MAIN/client/mathcat $REPO/client/mathcat
test -e $REPO/include/liblouis/configure.ac || { mkdir -p $REPO/include/liblouis && cp $MAIN/include/liblouis/configure.ac $REPO/include/liblouis/; }
for f in client/braille/liblouis.dll client/braille/louis_helper.py client/braille/liblouis/tables client/mathcat/assets include/liblouis/configure.ac; do test -e $REPO/$f && echo "present: $f"; done
git -C $MAIN submodule status include/liblouis | cut -c2-41
git -C $REPO rev-parse HEAD:include/liblouis
cmp $REPO/client/braille/louis_helper.py $REPO/vendor/nvda/liblouis/runtime/louis_helper.py && echo "louis_helper.py is the vendored file"
git -C $REPO status --short -- client docs scripts
```

Expected (`status` prints nothing):

```text
present: client/braille/liblouis.dll
present: client/braille/louis_helper.py
present: client/braille/liblouis/tables
present: client/mathcat/assets
present: include/liblouis/configure.ac
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
louis_helper.py is the vendored file
```

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` are F-9's, unchanged; `mo_check.py` lists the F-11 msgids; `apply_blocks.py` is F-9's with its docstring naming this plan.

File: `$T/tools/brief.py`

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers and exception lines, cut to 160 characters (a cut line is
printed once, so the subtests of one test give one header), the "Ran" line without its
timing and the final OK/FAILED line, so that outputs can be compared with the plan. The
client directory is shown as <client>; temporary directories (tempfile.mkdtemp names,
also in repr form with doubled backslashes) as <tmp>; random temporary-file suffixes as
<rnd>; object addresses (the frame's repr in a message-box event, F-9) as <addr>, also
when unittest's diff has cut the repr down to its last characters.
"""
import re
import sys
from pathlib import Path

CLIENT = str(Path.cwd())
CLIENT_REPR = CLIENT.replace("\\", "\\\\")
TMPDIR = re.compile(r"[A-Za-z]:(?:\\\\|\\)(?:[^'\"\s]*?(?:\\\\|\\))?tmp[a-z0-9_]{8}")
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.(?:dep|csv|py|json|brl|html)\.)[a-z0-9_]{8,16}(\.tmp)")
ADDRESS = re.compile(r" at 0x[0-9A-Fa-f]+>")
CUT_ADDRESS = re.compile(r"(\[\d+ chars\])[0-9A-F]{1,16}>")
seen = set()
for line in sys.stdin:
    line = line.rstrip("\n").replace(CLIENT_REPR, "<client>").replace(CLIENT, "<client>")
    line = TMPDIR.sub("<tmp>", line)
    line = RANDOM_TMP.sub(r"\1<rnd>\2", line)
    line = CUT_ADDRESS.sub(r"\1<addr>", ADDRESS.sub(" at <addr>>", line))
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception|Interrupt|Exit): ", line):
        line = line[:160]
        if line not in seen:
            seen.add(line)
            print(line)
    elif line.startswith("Ran "):
        print(re.sub(r" in [0-9.]+s$", "", line))
    elif line.startswith(("OK", "FAILED")):
        print(line)
````

File: `$T/tools/msgid_scan.py`

````python
"""List the gettext msgids of a client tree (throwaway, not committed).

Usage: python -I msgid_scan.py <client_dir>
AST stand-in for scripts/generate-pot.bat: keywords _ and N_, every *.py under
client_dir except .venv/, tests/, build/, dist/ (and the generated braille/liblouis/).
Prints the msgid count and the SHA-256 of the sorted, newline-joined msgids.
"""
import ast
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
msgids = set()
for path in sorted(root.rglob("*.py")):
    relative = path.relative_to(root)
    if relative.parts[0] in {".venv", "tests", "build", "dist"} or relative.parts[:2] == ("braille", "liblouis"):
        continue
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"_", "N_"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            msgids.add(node.args[0].value)
digest = hashlib.sha256("\n".join(sorted(msgids)).encode("utf-8")).hexdigest()
print(f"source msgids: {len(msgids)} sha256 {digest}")
````

File: `$T/tools/shuffle_harness.py`

````python
"""Run every test module in a seeded random order in one process (throwaway).

Usage (from client/): python shuffle_harness.py <seed> [<seed> ...]
Prints one line per seed: seed, tests run, failures, errors, skipped, and the ids
of the failing or erroring tests.
"""
import io
import random
import sys
import unittest

sys.path.insert(0, ".")

for seed in (int(arg) for arg in sys.argv[1:]):
    suite = unittest.defaultTestLoader.discover("tests")
    modules = list(suite)
    random.Random(seed).shuffle(modules)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.TestSuite(modules))
    bad = sorted(test.id().rsplit(".", 1)[-1] for test, _trace in result.failures + result.errors)
    print(
        f"seed {seed}: ran={result.testsRun} failures={len(result.failures)} "
        f"errors={len(result.errors)} skipped={len(result.skipped)} {bad}"
    )
````

File: `$T/tools/pin_pot_date.py`

````python
"""Set the POT-Creation-Date header of a .pot file to a fixed value (throwaway, not committed).

Usage: python pin_pot_date.py <file.pot> "<YYYY-MM-DD HH:MM+ZZZZ>"

xgettext writes the current time there, msgmerge copies it into the .po and msgfmt into
the .mo. A fixed value keeps the three catalogs, and so the commit's tree id, the same in
every run of the plan. Nothing else in the file changes; line ends are kept.
"""
import re
import sys
from pathlib import Path

path, value = Path(sys.argv[1]), sys.argv[2]
data = path.read_bytes().decode("utf-8")
pattern = re.compile(r'^"POT-Creation-Date: [^"\\]*\\n"$', re.M)
if len(pattern.findall(data)) != 1:
    sys.exit(f"{path}: expected one POT-Creation-Date line")
data = pattern.sub(lambda _match: f'"POT-Creation-Date: {value}\\n"', data)
path.write_bytes(data.encode("utf-8"))
print(f"{path.name}: POT-Creation-Date {value}")
````

File: `$T/tools/mo_check.py`

````python
"""Load a compiled catalog with gettext.GNUTranslations and print what it holds (throwaway).

Usage: python -I mo_check.py <file.mo>
Prints the number of catalog keys (the msgids plus the header) and the translation of
each msgid that F-11 adds (msgfmt 0.23 leaves POT-Creation-Date out of the .mo header, so
the .mo does not depend on it). A msgid the catalog does not hold prints as "(missing)".
Output is UTF-8 (-I ignores PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = (
    "Failed to open the dictionary editor: {error}",
    "Remove Rows That Cannot Be Shown",
    'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:'
    "\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?",
    "Row {line}: no source text",
    'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid',
    "Other rows not listed: {count}",
    "Remove and &Save",
    "&Back to Editing",
    "Unsaved Changes",
    'Do you want to discard the changes you made to dictionary "{name}"?',
    "&Discard Changes",
)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for msgid in MSGIDS:
    translated = catalog._catalog.get(msgid, "(missing)")
    print(f"{msgid!r} -> {translated!r}")
````

File: `$T/tools/f11_mutants.py`

````python
"""Run the F-11 tests against deliberately broken code (throwaway, not committed).

Usage: python f11_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-11 test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 10. Exit status 1 if a mutant is not caught or
its pattern is not found exactly once. Python runs with -B (no bytecode is written): a
restored file can have the size and modification second of the mutant, and a cached
.pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

DIALOG = "dialog.py"
ENTRIES = "dictionaries/entries.py"
MODEL = "dictionaries/entry_list_model.py"
MANAGER = "dictionaries/manager.py"
PRESENTER = "dictionaries/presenter.py"
BOX = "ui/message_box.py"
RULES = "conversion/text/dictionary_rules.py"
GUI = "gui.py"
MUTANTS = {
	# D3: what a change is.
	"has-changes-always-true": (MODEL, "\t\treturn self._entries != self._loaded_entries\n", "\t\treturn True\n"),
	"has-changes-ignores-order": (
		MODEL,
		"\t\treturn self._entries != self._loaded_entries\n",
		"\t\treturn sorted(map(repr, self._entries)) != sorted(map(repr, self._loaded_entries))\n",
	),
	"has-changes-counts-hidden-rows": (
		MODEL,
		"\t\treturn self._entries != self._loaded_entries\n",
		"\t\treturn self._entries != self._loaded_entries or bool(self.hidden_rows)\n",
	),
	"loaded-entries-not-copied": (
		MODEL,
		"\t\treturn [DictionaryEntry(entry.text, entry.braille, entry.entry_type) for entry in self._entries]\n",
		"\t\treturn list(self._entries)\n",
	),
	# D1: the hidden rows.
	"hidden-rows-box-without-hidden-rows": (DIALOG, "\t\tif self._model.hidden_rows:\n", "\t\tif True:\n"),
	"remove-and-save-writes-hidden-rows": (
		MODEL,
		"\t\tentries = self._entries\n\t\tsave_dictionary_entries(path, entries, self._layout)\n",
		"\t\tentries = self._entries\n\t\tsave_dictionary_entries(path, self._rows, self._layout)\n",
	),
	"back-to-editing-still-writes": (
		DIALOG,
		"\t\t\tif not self._confirm_hidden_rows():\n\t\t\t\tself._restore_focus(focused)\n\t\t\t\treturn\n",
		"\t\t\tif not self._confirm_hidden_rows():\n\t\t\t\tself._save()\n\t\t\t\tself._restore_focus(focused)\n\t\t\t\treturn\n",
	),
	"hidden-rows-cap-9": (DIALOG, "HIDDEN_ROWS_LISTED = 10\n", "HIDDEN_ROWS_LISTED = 9\n"),
	"hidden-rows-cap-11": (DIALOG, "HIDDEN_ROWS_LISTED = 10\n", "HIDDEN_ROWS_LISTED = 11\n"),
	"start-line-off-by-one": (ENTRIES, "\t\t\tline, next_line = next_line, reader.line_num + 1\n", "\t\t\tline, next_line = next_line, reader.line_num\n"),
	"reason-of-whitespace-text": (
		ENTRIES,
		'\t\treturn "no_source_text" if not self.text.strip() else "invalid_bopomofo"\n',
		'\t\treturn "no_source_text" if not self.text else "invalid_bopomofo"\n',
	),
	"failed-save-drops-hidden-rows": (
		MODEL,
		"\t\tentries = self._entries\n\t\tsave_dictionary_entries(path, entries, self._layout)\n\t\tself._rows = list(entries)\n",
		"\t\tentries = self._entries\n\t\tself._rows = list(entries)\n\t\tsave_dictionary_entries(path, entries, self._layout)\n",
	),
	# D7: the boxes.
	"ok-is-the-default": (BOX, "wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING", "wx.OK | wx.CANCEL | wx.ICON_WARNING"),
	"native-task-dialog": (BOX, "    with wx.GenericMessageDialog(parent,", "    with wx.MessageDialog(parent,"),
	"cancel-skips-without-asking": (DIALOG, "\t\tif self._model.has_changes() and not confirm_box(\n", "\t\tif False and not confirm_box(\n"),
	"cancel-asks-without-a-change": (DIALOG, "\t\tif self._model.has_changes() and not confirm_box(\n", "\t\tif not confirm_box(\n"),
	"cancel-not-bound": (DIALOG, "\t\t\t\tcancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)\n", "\t\t\t\tpass\n"),
	"ok-writes-without-a-change": (DIALOG, "\t\telif not self._model.has_changes():\n", "\t\telif False:\n"),
	"focus-not-restored": (DIALOG, "\t\tif window is not None and self.IsDescendant(window):\n", "\t\tif False:\n"),
	"focus-restored-outside-the-editor": (DIALOG, "\t\tif window is not None and self.IsDescendant(window):\n", "\t\tif window is not None:\n"),
	# D2, D8, D9: duplicates and identity.
	"duplicate-check-includes-hidden-rows": (
		MODEL,
		"\t\treturn any(entry.text == text and entry is not exclude_entry for entry in self._entries)\n",
		"\t\treturn any(row.text == text and row is not exclude_entry for row in self._rows)\n",
	),
	"duplicate-check-keeps-the-edited-entry": (
		MODEL,
		"\t\tif editing is not None and text == editing.text:\n\t\t\treturn False\n\t\treturn self.source_text_exists(text, exclude_entry=editing)\n",
		"\t\treturn self.source_text_exists(text)\n",
	),
	"twin-cannot-keep-its-text": (MODEL, "\t\tif editing is not None and text == editing.text:\n", "\t\tif False:\n"),
	"entry-dialog-closes-on-a-duplicate": (
		DIALOG,
		"\t\t\tshow_duplicate_source_text(entry.text, self)\n",
		"\t\t\tshow_duplicate_source_text(entry.text, self)\n\t\t\tevent.Skip()\n",
	),
	"source-text-not-focused": (
		DIALOG,
		"\t\t\t\tself.identifier_ctrl.SetFocus()\n\t\t\t\tself.identifier_ctrl.SelectAll()\n",
		"\t\t\t\tself.identifier_ctrl.SelectAll()\n",
	),
	"editor-passes-no-duplicate-check": (
		DIALOG,
		"is_duplicate=lambda text: self._model.is_duplicate(text, editing=entry)",
		"is_duplicate=None",
	),
	"remove-by-equality": (MODEL, "\t\tdel self._rows[self._full_index(current_entry)]\n", "\t\tself._rows.remove(current_entry)\n"),
	"replace-drops-fields": (MODEL, "\t\tentry.fields = current_entry.fields\n", ""),
	"replace-selects-by-equality": (
		MODEL,
		"\t\treturn EntryListUpdate(self._selection_after(entry, visible_index, by_identity=True))\n",
		"\t\treturn EntryListUpdate(self._selection_after(entry, visible_index))\n",
	),
	# D5, D6: the layout.
	"bom-dropped": (ENTRIES, '\tencoding = "utf-8-sig" if layout.has_bom else "utf-8"\n', '\tencoding = "utf-8"\n'),
	"bom-always-written": (ENTRIES, '\tencoding = "utf-8-sig" if layout.has_bom else "utf-8"\n', '\tencoding = "utf-8-sig"\n'),
	"extra-columns-dropped": (
		ENTRIES,
		'\t\t\tfields = list(row.fields) + [""] * (len(header) - len(row.fields))\n',
		'\t\t\tfields = [""] * len(header)\n',
	),
	"header-reordered": (
		ENTRIES,
		"\theader = list(layout.header)\n",
		"\theader = sorted(layout.header)\n",
	),
	"column-named-twice-first-position": (ENTRIES, "\treturn positions[-1] if positions else None\n", "\treturn positions[0] if positions else None\n"),
	"bom-not-detected": (ENTRIES, "\t\thas_bom = raw.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8\n", "\t\thas_bom = False\n"),
	# D14: the tone space of a final first-tone syllable.
	"no-tone-space-retry": (ENTRIES, '\tfor candidate in (sequence, sequence + " "):\n', "\tfor candidate in (sequence,):\n"),
	"entry-dialog-strips-the-tone-space": (DIALOG, "\t\t\tbraille = canonical_bopomofo(braille) or braille\n", "\t\t\tbraille = braille\n"),
	"loader-keeps-the-stripped-sequence": (ENTRIES, "\t\tentry.braille = canonical_bopomofo(entry.braille)\n", "\t\tentry.braille = entry.braille\n"),
	# D13: conversion.
	"conversion-keeps-whitespace-texts": (RULES, "                if not source.strip():\n", "                if not source:\n"),
	"conversion-validates-the-raw-target": (RULES, "    sequence = target.strip()\n", "    sequence = target\n"),
	"conversion-keeps-invalid-bopomofo": (
		RULES,
		"                        if not _editor_shows_bopomofo(target, processing):\n",
		"                        if False:\n",
	),
	"conversion-without-the-tone-space-retry": (RULES, '    for candidate in (sequence, sequence + " "):\n', "    for candidate in (sequence,):\n"),
	# D10, D11, D12.
	"rename-without-samefile": (MANAGER, "    if destination_path.exists() and not _is_same_file(source_path, destination_path):\n", "    if False:\n"),
	"rename-refuses-the-same-file": (MANAGER, "        return os.path.samefile(source, destination)\n", "        return False\n"),
	"import-wraps-destination-errors": (
		MANAGER,
		"    write_bytes_atomically(destination_path, lambda stream: stream.write(data))\n",
		"    try:\n        write_bytes_atomically(destination_path, lambda stream: stream.write(data))\n"
		"    except PermissionError as error:\n        raise DictionaryImportSourceError(error) from error\n",
	),
	"import-source-error-not-wrapped": (MANAGER, "        raise DictionaryImportSourceError(error) from error\n", "        raise\n"),
	"import-source-error-raw-text": (
		PRESENTER,
		'_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc.error))',
		'_("Failed to import dictionary: {error}").format(error=exc.error)',
	),
	"frame-builds-the-editor-before-loading": (
		GUI,
		"\t\t\teditor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path, model=model)\n",
		"\t\t\teditor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path)\n",
	),
	"build-error-described-as-unreadable": (
		GUI,
		'\t\t\t\t_("Failed to open the dictionary editor: {error}").format(error=error),\n',
		"\t\t\t\tdescribe_unreadable_dictionary(edit_name, error),\n",
	),
	"editor-reads-after-the-native-dialog": (
		DIALOG,
		"\t\tif model is None:\n\t\t\tmodel = DictionaryEntryListModel.load(dictionary_path)\n"
		'\t\tsuper().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)\n',
		'\t\tsuper().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)\n'
		"\t\tif model is None:\n\t\t\tmodel = DictionaryEntryListModel.load(dictionary_path)\n",
	),
	"build-failure-not-destroyed": (DIALOG, "\t\texcept BaseException:\n\t\t\tself.Destroy()\n\t\t\traise\n", "\t\texcept BaseException:\n\t\t\traise\n"),
}
MODULES = (
	"tests.test_dictionary_entries",
	"tests.test_dictionary_entry_list_model",
	"tests.test_dictionary_entries_dialog",
	"tests.test_dialog_validation",
	"tests.test_dictionary_name_prompt",
	"tests.test_dictionary_manager",
	"tests.test_dictionary_presenter",
	"tests.test_conversion_text_dictionary_rules",
	"tests.test_gui_document_flows",
	"tests.test_message_box",
)
IGNORE = shutil.ignore_patterns(".venv", "log", "dictionary", "workspace", "build", "dist", "config.json", "__pycache__")
FAILED = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", re.M)


def main() -> int:
	client_dir, scratch_dir, *selected = sys.argv[1:]
	copy = Path(scratch_dir) / "client"
	if copy.exists():
		shutil.rmtree(copy)
	shutil.copytree(client_dir, copy, ignore=IGNORE)
	status = 0
	for mutant in selected or list(MUTANTS):
		relative, old, new = MUTANTS[mutant]
		path = copy / relative
		original = path.read_bytes()
		text = original.decode("utf-8").replace("\r\n", "\n")
		if text.count(old) != 1:
			print(f"{mutant}: pattern found {text.count(old)} times in {relative}")
			status = 1
			continue
		path.write_bytes(text.replace(old, new).encode("utf-8"))
		try:
			completed = subprocess.run(
				[sys.executable, "-B", "-m", "unittest", *MODULES],
				cwd=copy, capture_output=True, text=True, encoding="utf-8",
			)
		finally:
			path.write_bytes(original)
		names = sorted({f"{where.split('.')[1]}.{test}" for test, where in FAILED.findall(completed.stderr)})
		shown = names if len(names) <= 4 else names[:4] + [f"and {len(names) - 4} more"]
		print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
		if not names:
			status = 1
	return status


if __name__ == "__main__":
	sys.exit(main())
````

File: `$T/tools/apply_blocks.py`

````python
"""Apply the File: and Edit: blocks of one step of the F-11 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f11 <T> "Task 1" "Step 1"

The step is the "- [ ] **Step N" item under the "### Task N" heading. A File: block is
written as is (a path starting with $T goes under <T>, any other path under <repo>); an
Edit: block is the line "Edit: `path`" and the next two fenced blocks, the old text and
its replacement. The old text must occur exactly once in the file at that point
(compared with CRLF as LF; the file keeps its line endings). Blocks are applied in plan
order. Prints one line per block; stops with exit status 1 at the first block that does
not apply. Reads and writes bytes, so escapes such as \\u81fa stay as they are.
"""
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^(`{3,})[\w-]*\s*$")


def fenced(lines, start):
    """(body, index after the closing fence) of the first fenced block at or after ``start``."""
    index = start
    while not FENCE.match(lines[index]):
        index += 1
    fence = FENCE.match(lines[index]).group(1)
    end = index + 1
    while lines[end].strip() != fence:
        end += 1
    body = lines[index + 1:end]
    return "".join(line + "\n" for line in body), end + 1


def main() -> int:
    plan, repo, tdir, task, step = sys.argv[1:6]
    lines = Path(plan).read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n")
    in_task = in_step = False
    applied = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("### "):
            in_task = line.startswith(f"### {task}:")
            in_step = False
        elif line.startswith("- [ ] **Step"):
            in_step = in_task and line.startswith(f"- [ ] **{step}:")
        match = re.match(r"^(File|Edit): `([^`]+)`$", line) if in_step else None
        if not match:
            index += 1
            continue
        kind, path = match.groups()
        target = Path(tdir) / path[3:] if path.startswith("$T/") else Path(repo) / path
        if kind == "File":
            body, index = fenced(lines, index + 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body.encode("utf-8"))
            print(f"wrote {path}")
        else:
            old, index = fenced(lines, index + 1)
            new, index = fenced(lines, index)
            raw = target.read_bytes().decode("utf-8")
            crlf = "\r\n" in raw
            text = raw.replace("\r\n", "\n")
            count = text.count(old)
            if count != 1:
                print(f"edit of {path} (plan line {index}): old text found {count} times")
                return 1
            text = text.replace(old, new)
            target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
            print(f"edited {path}")
        applied += 1
    print(f"{applied} blocks applied ({task}, {step})")
    return 0 if applied else 1


if __name__ == "__main__":
    sys.exit(main())
````

Write `apply_blocks.py` first by extracting it from this file as bytes (never through the Edit/Write tools), then let it write the step's blocks (it rewrites `apply_blocks.py` with the same bytes):

```bash
mkdir -p $T/tools
PLAN=$REPO/docs/superpowers/plans/2026-10-11-f11-dictionary-editor-ux.md
$PY -c "import sys; from pathlib import Path; text = Path(sys.argv[1]).read_bytes().decode('utf-8').replace(chr(13) + chr(10), chr(10)); start = text.index('File: \`\$T/tools/apply_blocks.py\`'); body = text[text.index(chr(10), text.index('\`\`\`\`python', start)) + 1:text.index(chr(10) + '\`\`\`\`' + chr(10), start)]; Path(sys.argv[2]).write_bytes((body + chr(10)).encode('utf-8')); print('apply_blocks.py extracted')" "$PLAN" "$T/tools/apply_blocks.py"
$PY $T/tools/apply_blocks.py "$PLAN" $REPO $T "Task 0" "Step 3"
```

Expected:

```text
apply_blocks.py extracted
wrote $T/tools/brief.py
wrote $T/tools/msgid_scan.py
wrote $T/tools/shuffle_harness.py
wrote $T/tools/pin_pot_date.py
wrote $T/tools/mo_check.py
wrote $T/tools/f11_mutants.py
wrote $T/tools/apply_blocks.py
7 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-11-f11-dictionary-editor-ux.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 7; Task 1 Step 1: 4, Step 2: 1; Task 2 Step 1: 2, Step 2: 4; Task 3 Step 1: 8, Step 2: 10; Task 4 Step 1: 5, Step 2: 4; Task 5 Step 1: 15, Step 2: 6; Task 6 Step 1: 8, Step 2: 4; Task 7 Step 1: 14, Step 2: 3, Step 5: 1; Task 8 Step 1: 26, Step 2: 8, Step 5: 2; Task 9 Step 1: 9, Step 2: 5, Step 5: 1; Task 10 Step 1: 5, Step 2: 4; Task 12 Step 2: 10).

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_conversion_text_dictionary_rules tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set; the F-11 msgids are missing; the number after the tree id counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 11; if the user has used the app since the dry run, that number differs, which is fine; the worktree has no application data):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1483 tests
FAILED (errors=1, skipped=7)
ERROR: test_case_only_rename_still_renames (tests.test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 482 tests
FAILED (errors=1, skipped=1)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
source msgids: 369 sha256 a94d370e253c7c605c90ea5896f725ef09030d45cf5e2906d98333556a2ec0e4
locales/dotexpress.pot:370
locales/zh_TW/LC_MESSAGES/dotexpress.po:370
369 translated messages.
msgfmt rebuilds the committed .mo byte for byte
catalog keys: 370
'Failed to open the dictionary editor: {error}' -> '(missing)'
'Remove Rows That Cannot Be Shown' -> '(missing)'
'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?' -> '(missing)'
'Row {line}: no source text' -> '(missing)'
'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid' -> '(missing)'
'Other rows not listed: {count}' -> '(missing)'
'Remove and &Save' -> '(missing)'
'&Back to Editing' -> '(missing)'
'Unsaved Changes' -> '(missing)'
'Do you want to discard the changes you made to dictionary "{name}"?' -> '(missing)'
'&Discard Changes' -> '(missing)'
a64da653f7348440a9a8b7419cb9aaea1e7a3440
4
worktree application data checked
```

### Task 1: Allow a case-only dictionary rename (D10)

- [ ] **Step 1: Red: Test Plan E (rename).** `test_dictionary_name_prompt.py` (tabs): the F-W6 test `test_case_only_rename_still_renames` checks the folder listing instead of `exists()` (Spec Corrections 4), and a new test patches `os.path.samefile` to `False`: a distinct file under another case is still refused. `test_dictionary_presenter.py` (tabs): `test_rename_case_only_change_renames_file` loses its skip (it skipped itself on a case-insensitive file system because of F-W6) and checks that the inactive name stays; a new test renames the active dictionary and expects `set_active_name("Alpha")` (D10).

Edit: `client/tests/test_dictionary_name_prompt.py`

```python
import unittest
from pathlib import Path

from dictionaries.manager import DEFAULT_HEADER, create_dictionary, ensure_default_dictionary
from dictionaries.name_prompt import prompt_dictionary_name_until_success
```

```python
import unittest
from pathlib import Path
from unittest.mock import patch

from dictionaries.manager import DEFAULT_HEADER, create_dictionary, ensure_default_dictionary
from dictionaries.name_prompt import prompt_dictionary_name_until_success
```

Edit: `client/tests/test_dictionary_name_prompt.py`

```python

			self.assertEqual(result, directory / "Alpha.csv")
			self.assertTrue(result.exists())
			self.assertFalse((directory / "alpha.csv").exists())


if __name__ == "__main__":
```

```python

			self.assertEqual(result, directory / "Alpha.csv")
			self.assertTrue(result.exists())
			# F-W6, fixed by F-11 (D10). The listing, not exists(): on a case-insensitive file
			# system "alpha.csv" still exists after the rename, as the same file.
			self.assertEqual(sorted(path.name for path in directory.iterdir()), ["Alpha.csv", "default.csv"])

	def test_rename_onto_another_file_under_another_case_is_refused(self) -> None:
		# F-11 (D10): only the same file may be renamed under another case. On a case-sensitive
		# file system "Alpha.csv" can be another dictionary; os.path.samefile tells them apart.
		from tempfile import TemporaryDirectory

		from dictionaries.name_prompt import rename_dictionary_after_name_prompt

		with TemporaryDirectory() as td:
			directory = Path(td)
			ensure_default_dictionary(directory)
			source_path = create_dictionary(directory, "alpha")
			source_path.write_text(",".join(DEFAULT_HEADER) + "\nterm,braille,General\n", encoding="utf-8")
			if not (directory / "Alpha.csv").exists():
				create_dictionary(directory, "Alpha")
			original_content = source_path.read_bytes()

			with patch("os.path.samefile", return_value=False), self.assertRaises(FileExistsError):
				rename_dictionary_after_name_prompt(directory, "alpha", "Alpha")

			self.assertEqual(source_path.read_bytes(), original_content)


if __name__ == "__main__":
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
		self.set_active_name.assert_not_called()

	def test_rename_case_only_change_renames_file(self):
		presenter = self.make_presenter("alpha")
		if (self.dictionary_dir / "ALPHA.csv").exists():
			self.skipTest("case-insensitive file system: a case-only rename is reported as a duplicate")
		view = FakeView(names=["Alpha"])

		result = presenter.rename(view, "alpha")
```

```python
		self.set_active_name.assert_not_called()

	def test_rename_case_only_change_renames_file(self):
		# Was skipped on a case-insensitive file system, where the rename was reported as a
		# duplicate (F-W6); F-11 (D10) renames it there too.
		presenter = self.make_presenter("alpha")
		view = FakeView(names=["Alpha"])

		result = presenter.rename(view, "alpha")
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
		self.assertEqual(result, "Alpha")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["Alpha", "default"])

	def test_rename_duplicate_shows_error_and_prompts_again_with_typed_name(self):
		presenter = self.make_presenter("alpha", "beta")
```

```python
		self.assertEqual(result, "Alpha")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["Alpha", "default"])
		self.assertEqual(presenter.dictionary_names, ["Alpha", "default"])
		self.set_active_name.assert_not_called()

	def test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name(self):
		# F-11 (D10): config.json follows through set_active_name, as for any other rename.
		presenter = self.make_presenter("alpha", active="alpha")
		view = FakeView(names=["Alpha"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "Alpha")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["Alpha", "default"])
		self.set_active_name.assert_called_once_with("Alpha")
		self.assertEqual(self.active, ["Alpha"])

	def test_rename_duplicate_shows_error_and_prompts_again_with_typed_name(self):
		presenter = self.make_presenter("alpha", "beta")
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_name_prompt tests.test_dictionary_presenter 2>&1 | $PY $T/tools/brief.py
```

Expected (the rename is refused as a duplicate; in the presenter the refusal asks for a name again and the fake view has none left):

```text
ERROR: test_case_only_rename_still_renames (tests.test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
ERROR: test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_c
IndexError: pop from empty list
ERROR: test_rename_case_only_change_renames_file (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file)
Ran 52 tests
FAILED (errors=3)
```

- [ ] **Step 2: Green: rename to the same file under another case** (`client/dictionaries/manager.py`, 4 spaces).

Edit: `client/dictionaries/manager.py`

```python
    destination_normalized = normalize_dictionary_name(new_name)
    source_path = dictionary_path_for_name(source_normalized, dictionary_dir)
    destination_path = dictionary_path_for_name(destination_normalized, dictionary_dir)
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
    return destination_path


def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
```

```python
    destination_normalized = normalize_dictionary_name(new_name)
    source_path = dictionary_path_for_name(source_normalized, dictionary_dir)
    destination_path = dictionary_path_for_name(destination_normalized, dictionary_dir)
    if destination_path.exists() and not _is_same_file(source_path, destination_path):
        raise FileExistsError(f"Dictionary '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
    return destination_path


def _is_same_file(source: Path, destination: Path) -> bool:
    """Whether ``destination`` names ``source`` itself: a case-only rename on a
    case-insensitive file system, such as ``alpha`` to ``Alpha`` on Windows (F-W6, F-11 D10).

    Another file that only differs in case (a case-sensitive file system) is not the same file.
    """
    try:
        return os.path.samefile(source, destination)
    except OSError:
        return False


def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_name_prompt tests.test_dictionary_presenter -v 2>&1 | grep -E "^(test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name|test_rename_onto_another_file_under_another_case_is_refused) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_name_prompt tests.test_dictionary_presenter 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_rename_onto_another_file_under_another_case_is_refused ok
test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name ok
Ran 52 tests
OK
Ran 1485 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_name_prompt.py client/tests/test_dictionary_presenter.py client/dictionaries/manager.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: allow a case-only dictionary rename (F-11, F-W6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dictionaries/manager.py              | 14 +++++++++++++-
 client/tests/test_dictionary_name_prompt.py | 26 +++++++++++++++++++++++++-
 client/tests/test_dictionary_presenter.py   | 19 +++++++++++++++++--
 3 files changed, 55 insertions(+), 4 deletions(-)
18b797ebc38fc1bb937e4484fe664bbba6de2d54
```

### Task 2: Explain a locked dictionary Import source (D11)

- [ ] **Step 1: Red: Test Plan E (Import).** `test_dictionary_manager.py` (4 spaces): a `PermissionError` opening the source (patched `Path.open` for that path) and one reading it after the check (patched `Path.read_bytes`) give `DictionaryImportSourceError`, which is not an `OSError` and keeps the original as `error` and `__cause__`; a `PermissionError` installing the copy (patched `os.replace`) stays a `PermissionError`. The tests import the new name inside the test, so only they fail. `test_dictionary_presenter.py` (tabs): the source error shows `Failed to import dictionary: {error}` with F-6's CANNOT_OPEN reason; a copy that cannot be installed keeps the raw text (O7).

Edit: `client/tests/test_dictionary_manager.py`

```python

        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    # --- atomic writes (F-8, D7) -------------------------------------------

    def _temporary_files(self, folder: Path) -> list[str]:
```

```python

        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    # --- an Import source that cannot be opened (F-11, D11) --------------------

    def test_import_source_that_cannot_be_opened_raises_the_import_source_error(self) -> None:
        # F-6 review M-4: a source held by another program gave the raw PermissionError, as a
        # failure writing the copy does. It is told apart now; nothing is copied.
        from dictionaries.manager import DictionaryImportSourceError

        source_path = Path(self._tmpdir.name) / "locked.csv"
        source_path.write_bytes(EXCEL_DICTIONARY)
        denied = PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(source_path))
        real_open = Path.open

        def open_except_the_source(path, *args, **kwargs):
            if path == source_path:
                raise denied
            return real_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_except_the_source), self.assertRaises(DictionaryImportSourceError) as raised:
            import_dictionary(self.dictionary_dir, source_path, "locked")

        self.assertIs(raised.exception.error, denied)
        self.assertIs(raised.exception.__cause__, denied)
        self.assertNotIsInstance(raised.exception, OSError)
        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    def test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error(self) -> None:
        # The copy reads the source again; a lock taken after the check is the source's problem too.
        from dictionaries.manager import DictionaryImportSourceError

        source_path = Path(self._tmpdir.name) / "locked.csv"
        source_path.write_bytes(EXCEL_DICTIONARY)
        denied = PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(source_path))

        with patch.object(Path, "read_bytes", side_effect=denied), self.assertRaises(DictionaryImportSourceError) as raised:
            import_dictionary(self.dictionary_dir, source_path, "locked")

        self.assertIs(raised.exception.error, denied)
        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    def test_import_copy_that_cannot_be_installed_keeps_its_permission_error(self) -> None:
        # Installing the copy in the dictionary folder is not the source's problem (O7).
        source_path = Path(self._tmpdir.name) / "excel.csv"
        source_path.write_bytes(EXCEL_DICTIONARY)
        denied = PermissionError(errno.EACCES, os.strerror(errno.EACCES))

        with patch("os.replace", side_effect=denied), self.assertRaises(PermissionError) as raised:
            import_dictionary(self.dictionary_dir, source_path, "science")

        self.assertIs(raised.exception, denied)
        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    # --- atomic writes (F-8, D7) -------------------------------------------

    def _temporary_files(self, folder: Path) -> list[str]:
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("long"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_cancelled_name_prompt_imports_nothing(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
```

```python
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("long"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason(self):
		# F-11 (D11, F-6 review M-4): the raw "[Errno 13] Permission denied: ..." was shown.
		source = self.write_source("locked")
		presenter = self.make_presenter()
		view = FakeView(names=["locked"], import_path=source)
		denied = PermissionError(13, "Permission denied", str(source))
		real_open = Path.open

		def open_except_the_source(path, *args, **kwargs):
			if path == source:
				raise denied
			return real_open(path, *args, **kwargs)

		with patch.object(Path, "open", open_except_the_source):
			result = presenter.import_from_file(view)

		reason = describe_dictionary_read_error(denied)
		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.choose_call(),
				self.prompt_call("locked"),
				("error", _("Failed to import dictionary: {error}").format(error=reason)),
			],
		)
		self.assertTrue(reason.startswith("\u7121\u6cd5\u958b\u555f\u6a94\u6848\u3002"), reason)
		self.assertEqual(self.files(), ["default"])

	def test_import_copy_that_cannot_be_installed_shows_the_error(self):
		# The copy into the dictionary folder keeps today's message with the raw error (O7).
		source = self.write_source("words")
		presenter = self.make_presenter()
		view = FakeView(names=["words"], import_path=source)
		denied = PermissionError(13, "Permission denied")

		with patch("os.replace", side_effect=denied):
			result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.choose_call(),
				self.prompt_call("words"),
				("error", _("Failed to import dictionary: {error}").format(error=denied)),
			],
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_cancelled_name_prompt_imports_nothing(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter 2>&1 | $PY $T/tools/brief.py
```

Expected (the new exception does not exist yet; the presenter shows the raw `[Errno 13]`; the two tests of the copy pass already):

```text
ERROR: test_import_source_that_cannot_be_opened_raises_the_import_source_error (tests.test_dictionary_manager.DictionaryManagerTest.test_import_source_that_cann
ImportError: cannot import name 'DictionaryImportSourceError' from 'dictionaries.manager' (<client>\dictionaries\manager.py)
ERROR: test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error (tests.test_dictionary_manager.DictionaryManagerTest.test_import_so
FAIL: test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason (tests.test_dictionary_presenter.PresenterImportTest.test_import_source_that_cannot_
AssertionError: Lists differ: [('ch[58 chars]or', "匯入字典失敗：[Errno 13] Permission denied: 'C:[84 chars]v'")] != [('ch[58 chars]or', '匯入字典失敗：無法開啟檔案。檔案可能正被其他程式使用，或你
Ran 73 tests
FAILED (failures=1, errors=2)
```

- [ ] **Step 2: Green: `DictionaryImportSourceError`** (`client/dictionaries/manager.py`, 4 spaces; `client/dictionaries/presenter.py`, tabs). The source is checked and read inside one `try`, before the copy is written from those bytes (Spec Corrections 5).

Edit: `client/dictionaries/manager.py`

```python
DEFAULT_DICTIONARY_NAME = "default"
DEFAULT_HEADER = ["text", "braille", "type"]
MAX_DICTIONARY_NAME_LENGTH = MAX_NAME_LENGTH


def dictionary_path_for_name(name: str, dictionary_dir: Path) -> Path:
```

```python
DEFAULT_DICTIONARY_NAME = "default"
DEFAULT_HEADER = ["text", "braille", "type"]
MAX_DICTIONARY_NAME_LENGTH = MAX_NAME_LENGTH


class DictionaryImportSourceError(Exception):
    """The Import source cannot be opened or read: another program holds it, or reading it
    is not permitted (F-11 D11, F-6 review M-4).

    ``error`` (also ``__cause__``) is the ``PermissionError``. Not an ``OSError``, so a
    caller can give it F-6's reason while an ``OSError`` writing the copy into the
    dictionary folder keeps its own message.
    """

    def __init__(self, error: PermissionError) -> None:
        super().__init__(str(error))
        self.error = error


def dictionary_path_for_name(name: str, dictionary_dir: Path) -> Path:
```

Edit: `client/dictionaries/manager.py`

```python
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    validate_dictionary_csv(source)
    write_bytes_atomically(destination_path, lambda stream: _copy_file_into(source, stream))
    return destination_path


```

```python
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    try:
        validate_dictionary_csv(source)
        # Read before the copy is written, so that an error reading the source is told
        # apart from an error writing the copy.
        data = source.read_bytes()
    except PermissionError as error:
        raise DictionaryImportSourceError(error) from error
    write_bytes_atomically(destination_path, lambda stream: stream.write(data))
    return destination_path


```

Edit: `client/dictionaries/presenter.py`

```python

from dictionaries.actions import is_default_dictionary
from dictionaries.manager import (
	create_dictionary,
	delete_dictionary,
	dictionary_path_for_name,
```

```python

from dictionaries.actions import is_default_dictionary
from dictionaries.manager import (
	DictionaryImportSourceError,
	create_dictionary,
	delete_dictionary,
	dictionary_path_for_name,
```

Edit: `client/dictionaries/presenter.py`

```python
			# F-6 (D9): before ValueError, which UnicodeDecodeError also is. Nothing was copied.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
			return None
		except ValueError:
			view.show_error(_("Imported file must contain text, braille, and type headers."))
			return None
```

```python
			# F-6 (D9): before ValueError, which UnicodeDecodeError also is. Nothing was copied.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
			return None
		except DictionaryImportSourceError as exc:
			# F-11 (D11): the source is held by another program or cannot be read; F-6's reason.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc.error)))
			return None
		except ValueError:
			view.show_error(_("Imported file must contain text, braille, and type headers."))
			return None
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter -v 2>&1 | grep -E "^(test_import_copy_that_cannot_be_installed_keeps_its_permission_error|test_import_copy_that_cannot_be_installed_shows_the_error|test_import_source_that_cannot_be_opened_raises_the_import_source_error|test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason|test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_import_copy_that_cannot_be_installed_keeps_its_permission_error ok
test_import_source_that_cannot_be_opened_raises_the_import_source_error ok
test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error ok
test_import_copy_that_cannot_be_installed_shows_the_error ok
test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason ok
Ran 73 tests
OK
Ran 1490 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_manager.py client/tests/test_dictionary_presenter.py client/dictionaries/manager.py client/dictionaries/presenter.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: explain a locked dictionary import source (F-11, F-6 M-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dictionaries/manager.py            | 24 +++++++++++++--
 client/dictionaries/presenter.py          |  5 +++
 client/tests/test_dictionary_manager.py   | 51 +++++++++++++++++++++++++++++++
 client/tests/test_dictionary_presenter.py | 50 ++++++++++++++++++++++++++++++
 4 files changed, 128 insertions(+), 2 deletions(-)
3c987c0912f1144fe237e6acbf5af2e675d1608c
```

### Task 3: Keep the BOM, header and extra columns of a dictionary (D5, D6)

- [ ] **Step 1: Red: Test Plan A1-A4, B3, C2.** `test_dictionary_entries.py` (tabs): `EXTRA_CSV` (a BOM, a note column, CRLF), `ODD_RECORDS_CSV` (a blank line, a quoted field over two lines, a short row, an overflow field, a whitespace-only line), `TWICE_CSV` (a column named twice); the oracle `_dictreader_rows`, the loader before F-11 verbatim; `DictionaryLayoutTest` (the layout, the start lines, the fields of each record, parity with the oracle on the F-4/F-6 corpora, equal read errors) and `DictionaryWriterLayoutTest` (BOM kept and never added, header kept and completed, extra and overflow fields, a new and an edited row, a column named twice, hidden rows, the default layout's bytes). `test_dictionary_entry_list_model.py` (tabs): a replaced entry gets the replaced row's fields; a loaded model saves with the file's layout. `test_dictionary_entries_dialog.py` (4 spaces): the BOM test now makes a change and keeps the BOM (F-2 to F-9 dropped it), and OK after a change keeps the header and the note column. Some parity tests pass already: they pin today's values.

Edit: `client/tests/test_dictionary_entries.py`

```python
from pathlib import Path

from conversion.text.dictionary_rules import LoadedDictionaryRules
from dictionaries.entries import (
	DictionaryEntry,
	PreservedDictionaryRow,
```

```python
from pathlib import Path

from conversion.text.dictionary_rules import LoadedDictionaryRules
from dictionaries import entries as entries_module
from dictionaries.entries import (
	DictionaryEntry,
	PreservedDictionaryRow,
```

Edit: `client/tests/test_dictionary_entries.py`

```python
	save_dictionary_entries,
	validate_dictionary_entry,
)
from text.zhuyin import normalize_zhuyin_sequence

BOPOMOFO_DATA = Path(__file__).resolve().parents[1] / "data" / "Bopomofo2Braille.csv"
```

```python
	save_dictionary_entries,
	validate_dictionary_entry,
)
from tests.unreadable_dictionary_files import FIELD_LIMIT, LATE_BIG5
from text.zhuyin import normalize_zhuyin_sequence

BOPOMOFO_DATA = Path(__file__).resolve().parents[1] / "data" / "Bopomofo2Braille.csv"
```

Edit: `client/tests/test_dictionary_entries.py`

```python
# What saving MIXED_ROWS writes: the same bytes, except that the row with a missing
# field gets its empty third field.
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))


class NormalizeEntryTypeTest(unittest.TestCase):
```

```python
# What saving MIXED_ROWS writes: the same bytes, except that the row with a missing
# field gets its empty third field.
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))
BOM = b"\xef\xbb\xbf"
# A dictionary kept in Excel (F-11 D5): a BOM, a column of notes between the required
# ones, CRLF. The writer keeps all three.
EXTRA_CSV = BOM + (
	"text,note,braille,type\r\n"
	"Alpha,first,\u2801,General\r\n"
	"Beta,,\u2803,General\r\n"
).encode("utf-8")
# Records the loader reads differently from a plain table (F-11 D6, probe 5): a blank
# line, a quoted field over two lines, a short row, an overflow field, a whitespace-only
# line.
ODD_RECORDS_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	"\r\n"
	",\u2803,General\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"short\r\n"
	"Beta,\u2803,General,overflow\r\n"
	" \r\n"
	"\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
).encode("utf-8")
# A column named twice: csv.DictReader reads the last position, so the second row has no
# source text.
TWICE_CSV = "text,braille,type,text\r\nAlpha,\u2801,General,Alpha2\r\nBeta,\u2803,General\r\n".encode("utf-8")


def _dictreader_rows(path: Path) -> list:
	"""The loader before F-11 (csv.DictReader), verbatim: the oracle of the parity tests."""
	if not path.exists():
		return []

	rows = []
	with path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if entries_module._is_editable(entry):
				rows.append(entry)
			else:
				rows.append(
					PreservedDictionaryRow(
						text=row.get("text") or "",
						braille=row.get("braille") or "",
						entry_type=row.get("type") or "",
					)
				)
	return rows


def _values(rows) -> list:
	return [(type(row).__name__, row.text, row.braille, row.entry_type) for row in rows]


class NormalizeEntryTypeTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual(after, before)
		self.assertIn("\u809a\u5b50", [source for source, _replacement in before.replacement_rules])

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
```

```python
		self.assertEqual(after, before)
		self.assertIn("\u809a\u5b50", [source for source, _replacement in before.replacement_rules])

	def test_rows_carry_their_record_and_entries_still_compare_by_value(self) -> None:
		# F-11 (D6): the record's fields and the start line are kept, outside equality.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)

			rows = load_dictionary_rows(path)

		self.assertEqual(rows, MIXED_ROWS)
		self.assertEqual(rows[0].fields, ("Alpha", "\u2801", "General"))
		self.assertEqual(rows[5].fields, ("", "\u2803"))
		self.assertEqual(rows[6].fields, ('q,"x"', "a\r\nb", "Bopomofo"))
		self.assertEqual([row.line for row in rows if isinstance(row, PreservedDictionaryRow)], [3, 4, 5, 6, 7, 8])
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
```

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual([entry].count(preserved), 0)


if __name__ == "__main__":
	unittest.main()
```

```python
		self.assertEqual([entry].count(preserved), 0)


class DictionaryLayoutTest(unittest.TestCase):
	"""The loader records what the writer keeps of the file (F-11 D5, D6)."""

	def load(self, data: bytes | None):
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			if data is not None:
				path.write_bytes(data)
			return entries_module.load_dictionary_file(path)

	def test_layout_records_the_bom_and_the_header_as_read(self) -> None:
		cases = (
			("no BOM", b"text,braille,type\r\nAlpha,x,General\r\n", False, ("text", "braille", "type")),
			("BOM and an extra column", EXTRA_CSV, True, ("text", "note", "braille", "type")),
			("a column named twice", TWICE_CSV, False, ("text", "braille", "type", "text")),
			("no type column", b"text,braille\r\nAlpha,x\r\n", False, ("text", "braille")),
			("an empty file", b"", False, ()),
			("only a BOM", BOM, True, ()),
			("a blank first line", b"\r\ntext,braille,type\r\n", False, ()),
		)
		for name, data, has_bom, header in cases:
			with self.subTest(name):
				self.assertEqual(self.load(data).layout, entries_module.DictionaryLayout(has_bom, header))

	def test_a_missing_file_has_no_rows_and_the_default_layout(self) -> None:
		loaded = self.load(None)

		self.assertEqual(loaded.rows, ())
		self.assertEqual(loaded.layout, entries_module.DictionaryLayout(False, ()))

	def test_hidden_rows_record_the_line_on_which_their_record_starts(self) -> None:
		# The header is line 1; a blank line is skipped but counted; a quoted field over two
		# lines makes the next record start two lines later (probe 5).
		rows = self.load(ODD_RECORDS_CSV).rows

		self.assertEqual(
			[(row.line, row.text) for row in rows if isinstance(row, PreservedDictionaryRow)],
			[(4, ""), (5, 'q,"x"'), (9, " "), (10, "\u809a\u5b50")],
		)

	def test_rows_keep_every_field_of_their_record(self) -> None:
		rows = self.load(ODD_RECORDS_CSV).rows

		self.assertEqual(
			[row.fields for row in rows],
			[
				("Alpha", "\u2801", "General"),
				("", "\u2803", "General"),
				('q,"x"', "a\r\nb", "Bopomofo"),
				("short",),
				("Beta", "\u2803", "General", "overflow"),
				(" ",),
				("\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9", "Bopomofo"),
			],
		)

	def test_values_and_classes_equal_those_of_dictreader(self) -> None:
		# A column named twice takes the value of its last position, a missing field is "",
		# blank records are skipped, the first record is the header even when it is blank.
		corpora = {
			"MIXED_CSV": MIXED_CSV,
			"DICT_BADBOPO": DICT_BADBOPO,
			"EXTRA_CSV": EXTRA_CSV,
			"ODD_RECORDS_CSV": ODD_RECORDS_CSV,
			"TWICE_CSV": TWICE_CSV,
			"blank first line": b"\r\ntext,braille,type\r\nAlpha,x,General\r\n",
			"LF and quotes": 'text,braille,type\n"Alpha",\u2801,General\nZhuyin,invalid,Bopomofo\n'.encode("utf-8"),
			"no type column": b"text,braille\r\nAlpha,x\r\n",
			"empty": b"",
		}
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			for name, data in corpora.items():
				with self.subTest(name):
					path.write_bytes(data)

					self.assertEqual(_values(load_dictionary_rows(path)), _values(_dictreader_rows(path)))

	def test_read_errors_equal_those_of_dictreader(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			for name, data in (("late Big5", LATE_BIG5), ("field limit", FIELD_LIMIT)):
				with self.subTest(name):
					path.write_bytes(data)
					with self.assertRaises(Exception) as expected:
						_dictreader_rows(path)

					with self.assertRaises(type(expected.exception)) as actual:
						load_dictionary_rows(path)

					self.assertEqual(str(actual.exception), str(expected.exception))


class DictionaryWriterLayoutTest(unittest.TestCase):
	"""The writer keeps the BOM, the header and the extra fields of the file (F-11 D5)."""

	def save(self, rows, layout=None) -> bytes:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			if layout is None:
				save_dictionary_entries(path, rows)
			else:
				save_dictionary_entries(path, rows, layout)
			return path.read_bytes()

	def round_trip(self, data: bytes) -> bytes:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(data)
			loaded = entries_module.load_dictionary_file(path)
			save_dictionary_entries(path, loaded.rows, loaded.layout)
			return path.read_bytes()

	def test_bom_is_kept_and_never_added(self) -> None:
		alpha = DictionaryEntry("Alpha", "\u2801", "General")
		with_bom = self.save([alpha], entries_module.DictionaryLayout(True, ("text", "braille", "type")))
		without = self.save([alpha], entries_module.DictionaryLayout(False, ("text", "braille", "type")))

		self.assertEqual(with_bom, BOM + "text,braille,type\r\nAlpha,\u2801,General\r\n".encode("utf-8"))
		self.assertEqual(without, "text,braille,type\r\nAlpha,\u2801,General\r\n".encode("utf-8"))

	def test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte(self) -> None:
		self.assertEqual(self.round_trip(EXTRA_CSV), EXTRA_CSV)

	def test_header_order_is_kept_and_missing_required_columns_are_appended(self) -> None:
		layout = entries_module.DictionaryLayout(False, ("type", "note", "text"))

		data = self.save([DictionaryEntry("Alpha", "\u2801", "Braille")], layout)

		self.assertEqual(data, "type,note,text,braille\r\nBraille,,Alpha,\u2801\r\n".encode("utf-8"))

	def test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized(self) -> None:
		data = (
			"text,note,braille,type\r\n"
			" Alpha ,first,  \u2801 ,Custom,overflow\r\n"
			"short\r\n"
		).encode("utf-8")

		self.assertEqual(
			self.round_trip(data),
			"text,note,braille,type\r\nAlpha,first,\u2801,General,overflow\r\nshort,,,General\r\n".encode("utf-8"),
		)

	def test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them(self) -> None:
		layout = entries_module.DictionaryLayout(False, ("text", "note", "braille", "type"))
		edited = DictionaryEntry("Alpine", "\u2801\u2807", "General", ("Alpha", "first", "\u2801", "General"))
		new = DictionaryEntry("Gamma", "\u281b", "Braille")

		data = self.save([edited, new], layout)

		self.assertEqual(
			data,
			"text,note,braille,type\r\nAlpine,first,\u2801\u2807,General\r\nGamma,,\u281b,Braille\r\n".encode("utf-8"),
		)

	def test_a_column_named_twice_gets_the_value_at_its_last_position(self) -> None:
		# DictReader reads the last position, so the writer writes there; the other keeps its value.
		layout = entries_module.DictionaryLayout(False, ("text", "braille", "type", "text"))
		entry = DictionaryEntry("Zeta", "\u2801", "General", ("Alpha", "\u2801", "General", "Alpha2"))

		data = self.save([entry], layout)

		self.assertEqual(data, "text,braille,type,text\r\nAlpha,\u2801,General,Zeta\r\n".encode("utf-8"))

	def test_hidden_rows_are_written_with_their_fields(self) -> None:
		# Until the editor removes them (F-11 D1), the rows it hides keep their whole record.
		data = "text,note,braille,type\r\n,kept,\u2803,General\r\n".encode("utf-8")

		self.assertEqual(self.round_trip(data), data)

	def test_default_layout_gives_the_bytes_of_the_writer_before_f11(self) -> None:
		entries = [DictionaryEntry("Alpha", "\u2801", "General"), DictionaryEntry("q,\"x\"", "a b", "Braille")]

		self.assertEqual(
			self.save(entries),
			'text,braille,type\r\nAlpha,\u2801,General\r\n"q,""x""",a b,Braille\r\n'.encode("utf-8"),
		)
		self.assertEqual(self.save(entries, entries_module.DictionaryLayout()), self.save(entries))


if __name__ == "__main__":
	unittest.main()
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.alpine, bravo])

	def test_same_text_is_accepted(self) -> None:
		changed = _entry("Alpha", "\u2801\u2801", "Braille")

```

```python
		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.alpine, bravo])

	def test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none(self) -> None:
		# F-11 (D5, O5): an edited row keeps its extra columns; the entry dialog gives none.
		self.alpine.fields = ("Alpine", "note", "\u2801\u2807", "General")
		bravo, gamma = _entry("Bravo", "\u2803\u2817"), _entry("Gamma", "\u281b")

		self.model.replace(1, bravo)
		self.model.add(gamma)

		self.assertEqual(self.model.entries[1].fields, ("Alpine", "note", "\u2801\u2807", "General"))
		self.assertIs(self.model.entries[1], bravo)
		self.assertEqual(gamma.fields, ())

	def test_same_text_is_accepted(self) -> None:
		changed = _entry("Alpha", "\u2801\u2801", "Braille")

```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python

		self.assertEqual(target.read_bytes(), MIXED_CSV_SAVED)


class ImportGuardTest(unittest.TestCase):
	def test_model_imports_no_ui_or_translation_module(self) -> None:
```

```python

		self.assertEqual(target.read_bytes(), MIXED_CSV_SAVED)

	def test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file(self) -> None:
		# F-11 (D5): the layout comes from the load; a new entry gets empty extra fields.
		path = self.directory / "excel.csv"
		path.write_bytes(b"\xef\xbb\xbf" + "text,note,braille,type\r\nAlpha,first,\u2801,General\r\n".encode("utf-8"))
		model = DictionaryEntryListModel.load(path)
		model.add(_entry("Beta", "\u2803"))

		model.save(path)

		self.assertEqual(
			path.read_bytes(),
			b"\xef\xbb\xbf" + "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,,\u2803,General\r\n".encode("utf-8"),
		)


class ImportGuardTest(unittest.TestCase):
	def test_model_imports_no_ui_or_translation_module(self) -> None:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

        self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])

    def test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom(self) -> None:
        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
        # "\ufefftext", the editor showed no rows and OK wrote the header only.
        harness = self.open_editor(data=b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")

        self.assertEqual(harness.rows(), [ALPHA_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\n")
        self.assertFalse(harness.path.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
        harness = self.open_editor([ALPHA])
```

```python

        self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])

    def test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom(self) -> None:
        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
        # "\ufefftext", the editor showed no rows and OK wrote the header only. Since F-11
        # (D5) the BOM is kept (F-2 to F-9 wrote the file without it).
        harness = self.open_editor(data=b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
        harness.script_entry(*BETA)
        harness.click("Add")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), "\ufeff" + HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_ok_after_a_change_keeps_the_header_and_the_extra_columns(self) -> None:
        # F-11 (D5): "note" was dropped. The edited row keeps its note (O5), the new one has none.
        data = "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803,General\r\n".encode("utf-8")
        harness = self.open_editor(data=data)
        harness.select(1)
        harness.script_entry("Beta", "\u2803\u2803")
        harness.click("Edit")
        harness.script_entry("Gamma", "\u281b", "Braille")
        harness.click("Add")

        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803\u2803,General\r\nGamma,,\u281b,Braille\r\n",
        )

    def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
        harness = self.open_editor([ALPHA])
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (the new loader, layout and fields do not exist yet):

```text
ERROR: test_rows_carry_their_record_and_entries_still_compare_by_value (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_rows_carry_their_record_an
AttributeError: 'DictionaryEntry' object has no attribute 'fields'
ERROR: test_a_missing_file_has_no_rows_and_the_default_layout (tests.test_dictionary_entries.DictionaryLayoutTest.test_a_missing_file_has_no_rows_and_the_defaul
AttributeError: module 'dictionaries.entries' has no attribute 'load_dictionary_file'. Did you mean: 'load_dictionary_rows'?
ERROR: test_hidden_rows_record_the_line_on_which_their_record_starts (tests.test_dictionary_entries.DictionaryLayoutTest.test_hidden_rows_record_the_line_on_whi
ERROR: test_layout_records_the_bom_and_the_header_as_read (tests.test_dictionary_entries.DictionaryLayoutTest.test_layout_records_the_bom_and_the_header_as_read
ERROR: test_rows_keep_every_field_of_their_record (tests.test_dictionary_entries.DictionaryLayoutTest.test_rows_keep_every_field_of_their_record)
ERROR: test_a_column_named_twice_gets_the_value_at_its_last_position (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_a_column_named_twice_gets_th
AttributeError: module 'dictionaries.entries' has no attribute 'DictionaryLayout'. Did you mean: 'DictionaryRow'?
ERROR: test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_a_new_row_has_empty_ext
ERROR: test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_an_unc
ERROR: test_bom_is_kept_and_never_added (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_bom_is_kept_and_never_added)
ERROR: test_default_layout_gives_the_bytes_of_the_writer_before_f11 (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_default_layout_gives_the_byte
ERROR: test_header_order_is_kept_and_missing_required_columns_are_appended (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_header_order_is_kept_a
ERROR: test_hidden_rows_are_written_with_their_fields (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_hidden_rows_are_written_with_their_fields)
ERROR: test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized (tests.test_dictionary_entries.DictionaryWriterLayoutTest.test_rows_keep_extra_a
ERROR: test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none (tests.test_dictionary_entry_list_model.ReplaceTest.test_replacement_gets_t
FAIL: test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file (tests.test_dictionary_entry_list_model.LoadSaveTest.test_save_keeps_the_bom_header_an
AssertionError: b'text,braille,type\r\nAlpha,\xe2\xa0\x81,G[35 chars]\r\n' != b'\xef\xbb\xbftext,note,braille,type\r\nAlp[59 chars]\r\n'
FAIL: test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.
AssertionError: 'text,braille,type\r\nAlpha,⠁,General\r\nBeta,⠃,General\r\n' != '\ufefftext,braille,type\r\nAlpha,⠁,General\r\nBeta,⠃,General\r\n'
FAIL: test_ok_after_a_change_keeps_the_header_and_the_extra_columns (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_ok_after_
AssertionError: 'text,braille,type\r\nAlpha,⠁,General\r\nBeta,⠃[28 chars]\r\n' != 'text,note,braille,type\r\nAlpha,first,⠁,Genera[47 chars]\r\n'
Ran 154 tests
FAILED (failures=3, errors=20)
```

- [ ] **Step 2: Green: `load_dictionary_file` and the layout-keeping writer** (`client/dictionaries/entries.py` and `client/dictionaries/entry_list_model.py`, tabs). The BOM is read from the first three bytes; the records come from `csv.reader` over the same `utf-8-sig` stream as before, so the read errors are the same; the writer encodes with `utf-8-sig` when the file had a BOM (no BOM character in the source).

Edit: `client/dictionaries/entries.py`

```python
from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from i18n import _
```

```python
from __future__ import annotations

import codecs
import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from i18n import _
```

Edit: `client/dictionaries/entries.py`

```python
ENTRY_TYPE_LABELS = {key: label for key, label in ENTRY_TYPE_OPTIONS}
DEFAULT_ENTRY_TYPE = ENTRY_TYPE_OPTIONS[0][0]
BRAILLE_UNICODE_PATTERNS_START = 0x2800


@dataclass
```

```python
ENTRY_TYPE_LABELS = {key: label for key, label in ENTRY_TYPE_OPTIONS}
DEFAULT_ENTRY_TYPE = ENTRY_TYPE_OPTIONS[0][0]
BRAILLE_UNICODE_PATTERNS_START = 0x2800
# The columns every dictionary has; the writer adds the ones a header lacks (F-11 D5).
REQUIRED_COLUMNS = ("text", "braille", "type")


@dataclass
```

Edit: `client/dictionaries/entries.py`

```python
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE


@dataclass(frozen=True)
```

```python
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE
	# Every field of the record the entry was read from, extra columns included; the
	# writer starts from them (F-11 D5). Empty for a new entry. Not part of equality.
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)


@dataclass(frozen=True)
```

Edit: `client/dictionaries/entries.py`

```python

	Kept as read (fields not stripped, a missing field as "") and written back
	unchanged at its place in the file. Never equal to a ``DictionaryEntry``
	(dataclass equality requires the same class).
	"""

	text: str
	braille: str
	entry_type: str


DictionaryRow = DictionaryEntry | PreservedDictionaryRow


def normalize_entry_type(entry_type: str | None) -> str:
```

```python

	Kept as read (fields not stripped, a missing field as "") and written back
	unchanged at its place in the file. Never equal to a ``DictionaryEntry``
	(dataclass equality requires the same class). ``line`` is the file line on which
	its record starts, the header being line 1, and ``fields`` the record as read
	(F-11 D1, D6); neither takes part in equality.
	"""

	text: str
	braille: str
	entry_type: str
	line: int = field(default=0, compare=False)
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)


DictionaryRow = DictionaryEntry | PreservedDictionaryRow


@dataclass(frozen=True)
class DictionaryLayout:
	"""What the writer keeps of a dictionary file: its UTF-8 BOM and its header record (F-11 D5)."""

	has_bom: bool = False
	header: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedDictionary:
	rows: tuple[DictionaryRow, ...]
	layout: DictionaryLayout


def normalize_entry_type(entry_type: str | None) -> str:
```

Edit: `client/dictionaries/entries.py`

```python

def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]:
	"""Every data row of the file in file order: an entry, or a row the editor keeps hidden."""
	if not dictionary_path.exists():
		return []

	rows: list[DictionaryRow] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if _is_editable(entry):
				rows.append(entry)
			else:
				rows.append(
					PreservedDictionaryRow(
						text=row.get("text") or "",
						braille=row.get("braille") or "",
						entry_type=row.get("type") or "",
					)
				)
	return rows


def _is_editable(entry: DictionaryEntry) -> bool:
```

```python

def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]:
	"""Every data row of the file in file order: an entry, or a row the editor keeps hidden."""
	return list(load_dictionary_file(dictionary_path).rows)


def load_dictionary_file(dictionary_path: Path) -> LoadedDictionary:
	"""The rows of ``load_dictionary_rows`` and the layout of the file (F-11 D6).

	The values are the ones ``csv.DictReader`` gives: the first record is the header
	(even a blank one), blank records are skipped, a missing field is "" and a column
	named twice takes the value of its last position. A missing file has no rows and
	the default layout. Read errors propagate.
	"""
	if not dictionary_path.exists():
		return LoadedDictionary((), DictionaryLayout())

	with dictionary_path.open("rb") as raw:
		has_bom = raw.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8
	header: list[str] | None = None
	rows: list[DictionaryRow] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.reader(fp)
		next_line = 1
		for record in reader:
			# A record starts on the line after the previous one ends; a quoted field can
			# span lines, and a blank line is a record of its own.
			line, next_line = next_line, reader.line_num + 1
			if header is None:
				header = record
			elif record:
				rows.append(_read_row(header, record, line))
	return LoadedDictionary(tuple(rows), DictionaryLayout(has_bom, tuple(header or ())))


def _column(header: list[str], name: str) -> int | None:
	"""The position ``csv.DictReader`` reads ``name`` from: its last one in the header."""
	positions = [index for index, column in enumerate(header) if column == name]
	return positions[-1] if positions else None


def _read_row(header: list[str], record: list[str], line: int) -> DictionaryRow:
	text, braille, entry_type = (
		record[index] if index is not None and index < len(record) else ""
		for index in (_column(header, name) for name in REQUIRED_COLUMNS)
	)
	entry = DictionaryEntry(
		text=text.strip(),
		braille=braille.strip(),
		entry_type=normalize_entry_type(entry_type),
		fields=tuple(record),
	)
	if _is_editable(entry):
		return entry
	return PreservedDictionaryRow(text=text, braille=braille, entry_type=entry_type, line=line, fields=tuple(record))


def _is_editable(entry: DictionaryEntry) -> bool:
```

Edit: `client/dictionaries/entries.py`

```python
	return [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]


def save_dictionary_entries(dictionary_path: Path, rows: Iterable[DictionaryRow]) -> None:
	"""Replace the file atomically; on an error it is unchanged."""
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)

	def _write(fp) -> None:
		writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		for row in rows:
			writer.writerow(
				{
					"text": row.text,
					"braille": row.braille,
					"type": row.entry_type,
				}
			)

	write_text_atomically(dictionary_path, _write, encoding="utf-8", newline="")
```

```python
	return [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]


def save_dictionary_entries(
	dictionary_path: Path,
	rows: Iterable[DictionaryRow],
	layout: DictionaryLayout = DictionaryLayout(),
) -> None:
	"""Replace the file atomically; on an error it is unchanged.

	The file gets the BOM of ``layout`` and its header, with the required columns it
	lacks appended (``text,braille,type`` without a header). Each row is its record as
	read, padded to the header, with its text, braille and type in their columns (the
	last position of a column named twice): extra columns and overflow fields are kept,
	a new row has them empty (F-11 D5). UTF-8, CRLF, minimal quoting.
	"""
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)
	header = list(layout.header)
	header.extend(name for name in REQUIRED_COLUMNS if name not in header)
	positions = [_column(header, name) for name in REQUIRED_COLUMNS]

	def _write(fp) -> None:
		writer = csv.writer(fp)
		writer.writerow(header)
		for row in rows:
			fields = list(row.fields) + [""] * (len(header) - len(row.fields))
			for position, value in zip(positions, (row.text, row.braille, row.entry_type)):
				fields[position] = value
			writer.writerow(fields)

	# utf-8-sig writes the BOM first.
	encoding = "utf-8-sig" if layout.has_bom else "utf-8"
	write_text_atomically(dictionary_path, _write, encoding=encoding, newline="")
```

Edit: `client/dictionaries/entry_list_model.py`

```python
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed: they keep their place in the file and ``save``
writes them back unchanged (F-4). ``entries`` and the visible list hold the
entries only.

Comparison rules, kept from the pre-P2-2 dialog (a file may hold identical rows):

```

```python
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed: they keep their place in the file and ``save``
writes them back unchanged (F-4). ``entries`` and the visible list hold the
entries only. ``save`` writes with the layout of the loaded file (its BOM and
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).

Comparison rules, kept from the pre-P2-2 dialog (a file may hold identical rows):

```

Edit: `client/dictionaries/entry_list_model.py`

```python
from dictionaries.entries import (
	ENTRY_TYPE_LABELS,
	DictionaryEntry,
	DictionaryRow,
	load_dictionary_rows,
	save_dictionary_entries,
)

```

```python
from dictionaries.entries import (
	ENTRY_TYPE_LABELS,
	DictionaryEntry,
	DictionaryLayout,
	DictionaryRow,
	load_dictionary_file,
	save_dictionary_entries,
)

```

Edit: `client/dictionaries/entry_list_model.py`

```python
class DictionaryEntryListModel:
	"""Full list, filter and visible list of one dictionary CSV."""

	def __init__(self, rows: Iterable[DictionaryRow] = ()) -> None:
		self._rows: list[DictionaryRow] = list(rows)
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read every row of ``path`` with ``load_dictionary_rows``; errors propagate."""
		return cls(load_dictionary_rows(path))

	def save(self, path: Path) -> None:
		"""Write every row (preserved rows unchanged, in place); errors propagate."""
		save_dictionary_entries(path, self._rows)

	@property
	def _entries(self) -> list[DictionaryEntry]:
```

```python
class DictionaryEntryListModel:
	"""Full list, filter and visible list of one dictionary CSV."""

	def __init__(self, rows: Iterable[DictionaryRow] = (), layout: DictionaryLayout = DictionaryLayout()) -> None:
		self._rows: list[DictionaryRow] = list(rows)
		self._layout = layout
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read every row of ``path`` and its layout with ``load_dictionary_file``; errors propagate."""
		loaded = load_dictionary_file(path)
		return cls(loaded.rows, loaded.layout)

	def save(self, path: Path) -> None:
		"""Write every row (preserved rows unchanged, in place) with the layout; errors propagate."""
		save_dictionary_entries(path, self._rows, self._layout)

	@property
	def _entries(self) -> list[DictionaryEntry]:
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		if self.source_text_exists(entry.text, exclude_entry=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index))
```

```python
		if self.source_text_exists(entry.text, exclude_entry=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)
		entry.fields = current_entry.fields
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index))
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v 2>&1 | grep -E "^(test_a_column_named_twice_gets_the_value_at_its_last_position|test_a_missing_file_has_no_rows_and_the_default_layout|test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them|test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte|test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom|test_bom_is_kept_and_never_added|test_default_layout_gives_the_bytes_of_the_writer_before_f11|test_header_order_is_kept_and_missing_required_columns_are_appended|test_hidden_rows_are_written_with_their_fields|test_hidden_rows_record_the_line_on_which_their_record_starts|test_layout_records_the_bom_and_the_header_as_read|test_ok_after_a_change_keeps_the_header_and_the_extra_columns|test_read_errors_equal_those_of_dictreader|test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none|test_rows_carry_their_record_and_entries_still_compare_by_value|test_rows_keep_every_field_of_their_record|test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized|test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file|test_values_and_classes_equal_those_of_dictreader) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_rows_carry_their_record_and_entries_still_compare_by_value ok
test_a_missing_file_has_no_rows_and_the_default_layout ok
test_hidden_rows_record_the_line_on_which_their_record_starts ok
test_layout_records_the_bom_and_the_header_as_read ok
test_read_errors_equal_those_of_dictreader ok
test_rows_keep_every_field_of_their_record ok
test_values_and_classes_equal_those_of_dictreader ok
test_a_column_named_twice_gets_the_value_at_its_last_position ok
test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them ok
test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte ok
test_bom_is_kept_and_never_added ok
test_default_layout_gives_the_bytes_of_the_writer_before_f11 ok
test_header_order_is_kept_and_missing_required_columns_are_appended ok
test_hidden_rows_are_written_with_their_fields ok
test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized ok
test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file ok
test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none ok
test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom ok
test_ok_after_a_change_keeps_the_header_and_the_extra_columns ok
Ran 154 tests
OK
Ran 1508 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries.py client/tests/test_dictionary_entry_list_model.py client/tests/test_dictionary_entries_dialog.py client/dictionaries/entries.py client/dictionaries/entry_list_model.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: keep the BOM, header and extra columns of a dictionary (F-11)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dictionaries/entries.py                   | 134 +++++++++---
 client/dictionaries/entry_list_model.py          |  20 +-
 client/tests/test_dictionary_entries.py          | 254 +++++++++++++++++++++++
 client/tests/test_dictionary_entries_dialog.py   |  28 ++-
 client/tests/test_dictionary_entry_list_model.py |  26 +++
 5 files changed, 416 insertions(+), 46 deletions(-)
eafdc94c70fa1cc7259b80b0bc0494b695e086f3
```

### Task 4: Delete and edit the selected dictionary entry (D9)

- [ ] **Step 1: Red: Test Plan B2, B5, C8.** `test_dictionary_entry_list_model.py` (tabs): `is_duplicate` (the twin rule, O6); the two Q4 pins of the model flipped (a twin keeps its text; the selected twin is removed and the selection goes to the remaining equal row); identity selection after Replace; another row cannot take a twin's text; removing the second twin keeps the first one's record. `test_dictionary_entries_dialog.py` (4 spaces): both Q4 pins flipped (the twin Edit keeps its text; Delete removes the selected row and the first row's note stays).

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))


class ApplyFilterTest(_ModelTestCase):
	def setUp(self) -> None:
```

```python
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))

	def test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text(self) -> None:
		# F-11 (D9, O6): with two identical rows, either one can be edited without changing
		# its source text; the edit adds no new duplicate.
		first, beta, second = _entry("a"), _entry("b", "\u2803"), _entry("a")
		model = DictionaryEntryListModel([first, beta, second])

		self.assertTrue(model.is_duplicate("a"))
		self.assertFalse(model.is_duplicate("c"))
		self.assertFalse(model.is_duplicate("a", editing=second))
		self.assertFalse(model.is_duplicate("c", editing=second))
		self.assertTrue(model.is_duplicate("b", editing=second))
		self.assertTrue(model.is_duplicate("a", editing=beta))
		self.assertFalse(model.is_duplicate("A", editing=beta))


class ApplyFilterTest(_ModelTestCase):
	def setUp(self) -> None:
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.beta], "bet")

	def test_identical_rows_replace_the_visible_object_but_cannot_keep_their_text(self) -> None:
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])

		with self.assertRaises(DuplicateEntryError):
			model.replace(2, _entry("a", "\u2803"))
		c = _entry("c")
		update = model.replace(2, c)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[0], first)
		self.assertIs(model.entries[2], c)

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		self.model.apply_filter("alp")
```

```python
		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.beta], "bet")

	def test_identical_rows_replace_the_visible_object_and_can_keep_their_text(self) -> None:
		# Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made the text a
		# duplicate. Fixed by F-11 (D9, O6).
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])
		changed = _entry("a", "\u2803")

		update = model.replace(2, changed)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[0], first)
		self.assertIs(model.entries[2], changed)

	def test_replacement_is_selected_by_identity_even_when_it_equals_another_row(self) -> None:
		# F-11 (D9): equality would select the first of two identical rows.
		first, braille = _entry("a"), _entry("a", "\u2801", "Braille")
		model = DictionaryEntryListModel([first, _entry("b"), braille])
		twin = _entry("a")

		update = model.replace(2, twin)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[2], twin)

	def test_another_row_cannot_take_the_text_of_an_identical_pair(self) -> None:
		first, beta, second = _entry("a"), _entry("b"), _entry("a")
		model = DictionaryEntryListModel([first, beta, second])

		with self.assertRaises(DuplicateEntryError):
			model.replace(1, _entry("a", "\u2803"))

		self.assertSameObjects(model.entries, [first, beta, second])

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		self.model.apply_filter("alp")
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.assertEqual(self.model.remove(0), EntryListUpdate(None))
		self.assertUnchanged(self.model, [self.alpha, self.beta], [], "gam")

	def test_identical_rows_remove_the_first_equal_and_select_the_remaining_twin(self) -> None:
		first, braille, second = _entry("a"), _entry("a", "\u2801", "Braille"), _entry("a")
		beta = _entry("Beta", "\u2803")
		model = DictionaryEntryListModel([first, beta, braille, second])

		update = model.remove(3)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(model.entries, [beta, braille, second])

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		for index in (-1, 3):
```

```python
		self.assertEqual(self.model.remove(0), EntryListUpdate(None))
		self.assertUnchanged(self.model, [self.alpha, self.beta], [], "gam")

	def test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin(self) -> None:
		# Was the P2-2 Q4 KNOWN BUG (second half): the first equal row was removed. Fixed by
		# F-11 (D9); the selection still goes to an equal row (by equality, as the golden
		# trace records).
		first, braille, second = _entry("a"), _entry("a", "\u2801", "Braille"), _entry("a")
		beta = _entry("Beta", "\u2803")
		model = DictionaryEntryListModel([first, beta, braille, second])

		update = model.remove(3)

		self.assertEqual(update, EntryListUpdate(0))
		self.assertSameObjects(model.entries, [first, beta, braille])

	def test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first(self) -> None:
		# F-11 (D9, B2): the saved order is a, b, with the first a's record.
		first, beta, second = _entry("a"), _entry("b", "\u2803"), _entry("a")
		first.fields, second.fields = ("a", "\u2801", "General", "first"), ("a", "\u2801", "General", "third")
		model = DictionaryEntryListModel([first, beta, second])

		model.remove(2)

		self.assertEqual([entry.fields for entry in model.entries], [("a", "\u2801", "General", "first"), ()])
		self.assertIs(model.entries[0], first)

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		for index in (-1, 3):
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
        self.assertEqual(harness.state(), before)

    def test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "General"]])
        harness.select(2)
        harness.script_entry("a", "\u2803")

        harness.click("Edit")

        # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the other
        # identical row makes its own text a duplicate.
        self.assertEqual(harness.take_log()[-1], ["MessageBox", _duplicate_message("a"), ERROR_TITLE, ERROR_FLAGS])
        harness.script_entry("c", "\u2809")

        harness.click("Edit")

        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], BETA_CELLS, ["c", "\u2809", GENERAL]])
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "a,\u2801,General\r\nBeta,\u2803,General\r\nc,\u2809,General\r\n",
        )

    def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
```

```python
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
        self.assertEqual(harness.state(), before)

    def test_identical_rows_edit_of_the_selected_row_can_keep_its_text(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made its own text
        # a duplicate. Fixed by F-11 (D9, O6).
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "General"]])
        harness.select(2)
        harness.take_log()
        harness.script_entry("a", "\u2803")

        harness.click("Edit")

        self.assertNotIn("MessageBox", [event[0] for event in harness.take_log()])
        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], BETA_CELLS, ["a", "\u2803", GENERAL]])
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "a,\u2801,General\r\nBeta,\u2803,General\r\na,\u2803,General\r\n",
        )

    def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_identical_rows_delete_removes_the_first_equal_row(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "Braille"], ["a", "\u2801", "General"]])
        harness.select(3)

        harness.click("Delete")

        # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the first equal
        # row goes, not the selected one; the remaining equal row gets the selection.
        self.assertEqual(
            harness.rows(),
            [BETA_CELLS, ["a", "\u2801", UNICODE_BRAILLE], ["a", "\u2801", GENERAL]],
        )
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Beta,\u2803,General\r\na,\u2801,Braille\r\na,\u2801,General\r\n",
        )


```

```python
        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_identical_rows_delete_removes_the_selected_row(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (second half): the first equal row went, not the selected
        # one. Fixed by F-11 (D9); the remaining equal row gets the selection, as before.
        data = (HEADER + "a,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\na,\u2801,General,fourth\r\n")
        harness = self.open_editor(data=data.replace(HEADER, "text,braille,type,note\r\n").encode("utf-8"))
        harness.select(3)

        harness.click("Delete")

        self.assertEqual(
            harness.rows(),
            [["a", "\u2801", GENERAL], BETA_CELLS, ["a", "\u2801", UNICODE_BRAILLE]],
        )
        self.assertEqual(harness.list.selected, 0)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            "text,braille,type,note\r\na,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\n",
        )


```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (the first equal row is removed, the twin's own text is a duplicate, `is_duplicate` does not exist):

```text
ERROR: test_identical_rows_replace_the_visible_object_and_can_keep_their_text (tests.test_dictionary_entry_list_model.ReplaceTest.test_identical_rows_replace_th
dictionaries.entry_list_model.DuplicateEntryError: a
ERROR: test_replacement_is_selected_by_identity_even_when_it_equals_another_row (tests.test_dictionary_entry_list_model.ReplaceTest.test_replacement_is_selected
ERROR: test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text (tests.test_dictionary_entry_list_model.SourceTextExistsTest.test_is_duplicate_excl
AttributeError: 'DictionaryEntryListModel' object has no attribute 'is_duplicate'
FAIL: test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin (tests.test_dictionary_entry_list_model.RemoveTest.test_identical_rows_remove_th
AssertionError: EntryListUpdate(selection=2, filter_cleared=False) != EntryListUpdate(selection=0, filter_cleared=False)
FAIL: test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first (tests.test_dictionary_entry_list_model.RemoveTest.test_removing_the_second_o
AssertionError: Lists differ: [(), ('a', '⠁', 'General', 'third')] != [('a', '⠁', 'General', 'first'), ()]
FAIL: test_identical_rows_delete_removes_the_selected_row (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogDeleteTest.test_identical_rows_delete_rem
AssertionError: Lists differ: [['Beta', '⠃', '一般'], ['a', '⠁', 'Unicode 點字'], ['a', '⠁', '一般']] != [['a', '⠁', '一般'], ['Beta', '⠃', '一般'], ['a', '⠁', 'Unicode 點
FAIL: test_identical_rows_edit_of_the_selected_row_can_keep_its_text (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogEditTest.test_identical_rows_e
AssertionError: 'MessageBox' unexpectedly found in ['AddSymbolDialog', 'MessageBox']
Ran 126 tests
FAILED (failures=4, errors=3)
```

- [ ] **Step 2: Green: identity and the twin rule** (`client/dictionaries/entry_list_model.py`, tabs).

Edit: `client/dictionaries/entry_list_model.py`

```python
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).

Comparison rules, kept from the pre-P2-2 dialog (a file may hold identical rows):

* the selection is restored by equality: the first visible entry equal to the
  previous one wins;
* ``replace`` swaps the full-list item that *is* the visible entry (identity);
* ``remove`` removes the first full-list entry *equal* to the visible one;
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  row, entries hidden by the filter and preserved rows included, and excludes
  the edited entry by identity.
"""

from __future__ import annotations
```

```python
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).

Comparison rules (a file may hold identical rows):

* ``replace`` and ``remove`` act on the full-list item that *is* the visible
  entry (identity; ``remove`` took the first *equal* one before F-11, P2-2 Q4);
* after ``add`` and ``replace`` the new entry is selected by identity; after
  ``remove`` and a filter change the selection is restored by equality, the
  first visible entry equal to the previous one winning (as the golden trace
  records);
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  row, entries hidden by the filter and preserved rows included, and excludes
  the edited entry by identity; an edit that keeps the edited entry's own text
  is never a duplicate (F-11 D9).
"""

from __future__ import annotations
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		"""
		return any(row.text == text and row is not exclude_entry for row in self._rows)

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate:
		preferred_entry = self.visible_entry(selected_index)
		self._filter_text = filter_text
```

```python
		"""
		return any(row.text == text and row is not exclude_entry for row in self._rows)

	def is_duplicate(self, text: str, editing: DictionaryEntry | None = None) -> bool:
		"""Whether adding (``editing`` None) or editing ``editing`` to ``text`` duplicates a row.

		An edit that keeps the entry's own text adds no duplicate, even when an identical
		row exists (F-11 D9).
		"""
		if editing is not None and text == editing.text:
			return False
		return self.source_text_exists(text, exclude_entry=editing)

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate:
		preferred_entry = self.visible_entry(selected_index)
		self._filter_text = filter_text
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		if filter_cleared:
			self._filter_text = ""
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, 0), filter_cleared=filter_cleared)

	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		if self.source_text_exists(entry.text, exclude_entry=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)
		entry.fields = current_entry.fields
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index))

	def remove(self, visible_index: int) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		self._rows.remove(current_entry)
		self._refilter()
		return EntryListUpdate(self._selection_after(current_entry, visible_index))

	def _visible_at(self, index: int) -> DictionaryEntry:
		if index < 0 or index >= len(self._visible):
```

```python
		if filter_cleared:
			self._filter_text = ""
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, 0, by_identity=True), filter_cleared=filter_cleared)

	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		if self.is_duplicate(entry.text, editing=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = self._full_index(current_entry)
		entry.fields = current_entry.fields
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index, by_identity=True))

	def remove(self, visible_index: int) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		del self._rows[self._full_index(current_entry)]
		self._refilter()
		return EntryListUpdate(self._selection_after(current_entry, visible_index))

	def _full_index(self, entry: DictionaryEntry) -> int:
		"""The full-list position of the row that *is* ``entry`` (F-11 D9)."""
		return next(index for index, candidate in enumerate(self._rows) if candidate is entry)

	def _visible_at(self, index: int) -> DictionaryEntry:
		if index < 0 or index >= len(self._visible):
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		else:
			self._visible = list(self._entries)

	def _selection_after(self, preferred_entry: DictionaryEntry | None, fallback_index: int) -> int | None:
		if not self._visible:
			return None
		index = min(fallback_index, len(self._visible) - 1)
		if preferred_entry is not None:
			try:
				index = self._visible.index(preferred_entry)
			except ValueError:
				pass
		return index
```

```python
		else:
			self._visible = list(self._entries)

	def _selection_after(
		self,
		preferred_entry: DictionaryEntry | None,
		fallback_index: int,
		*,
		by_identity: bool = False,
	) -> int | None:
		if not self._visible:
			return None
		index = min(fallback_index, len(self._visible) - 1)
		if preferred_entry is not None:
			if by_identity:
				index = next((position for position, entry in enumerate(self._visible) if entry is preferred_entry), index)
			else:
				try:
					index = self._visible.index(preferred_entry)
				except ValueError:
					pass
		return index
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v 2>&1 | grep -E "^(test_another_row_cannot_take_the_text_of_an_identical_pair|test_identical_rows_delete_removes_the_selected_row|test_identical_rows_edit_of_the_selected_row_can_keep_its_text|test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin|test_identical_rows_replace_the_visible_object_and_can_keep_their_text|test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text|test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first|test_replacement_is_selected_by_identity_even_when_it_equals_another_row) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin ok
test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first ok
test_another_row_cannot_take_the_text_of_an_identical_pair ok
test_identical_rows_replace_the_visible_object_and_can_keep_their_text ok
test_replacement_is_selected_by_identity_even_when_it_equals_another_row ok
test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text ok
test_identical_rows_delete_removes_the_selected_row ok
test_identical_rows_edit_of_the_selected_row_can_keep_its_text ok
Ran 126 tests
OK
Ran 1512 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entry_list_model.py client/tests/test_dictionary_entries_dialog.py client/dictionaries/entry_list_model.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: delete and edit the selected dictionary entry (F-11, #9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dictionaries/entry_list_model.py          | 60 +++++++++++++++------
 client/tests/test_dictionary_entries_dialog.py   | 32 ++++++------
 client/tests/test_dictionary_entry_list_model.py | 66 ++++++++++++++++++++----
 3 files changed, 115 insertions(+), 43 deletions(-)
8c7487cb749098f0cfd54c0bf18821e690219062
```

### Task 5: Report a duplicate source text inside the entry dialog (D2, D8)

- [ ] **Step 1: Red: Test Plan B4, C7, D.** `test_dictionary_entry_list_model.py` (tabs): F-4 D5's two tests are replaced by one (a preserved row's text is not a duplicate, D2). `test_dialog_validation.py` (4 spaces): `AddSymbolDialogDuplicateTest` (the duplicate box on the entry dialog, the source text focused and selected, no `Skip`; the format checked first; no duplicate or no check closes the dialog); the existing OK test sets `_is_duplicate`. `test_dictionary_entries_dialog.py` (4 spaces): the fake entry dialog runs the editor's `is_duplicate`, records the same `MessageBox` with itself as parent and takes the next scripted answer (none left: cancel), so the golden trace records stay the same; both Q6 pins flipped, a cancel after the duplicate, the check the editor passes, and F-4 D5's editor test flipped (the text of a hidden row can be added).

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.assertFalse(model.source_text_exists("Alpha", exclude_entry=alpha))
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))

	def test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text(self) -> None:
		# F-11 (D9, O6): with two identical rows, either one can be edited without changing
```

```python
		self.assertFalse(model.source_text_exists("Alpha", exclude_entry=alpha))
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))
		self.assertTrue(model.is_duplicate("Alpha"))

	def test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text(self) -> None:
		# F-11 (D9, O6): with two identical rows, either one can be edited without changing
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python


class PreservedRowsTest(_ModelTestCase):
	"""Rows the editor does not show stay hidden, keep their place and count as duplicates (F-4)."""

	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
```

```python


class PreservedRowsTest(_ModelTestCase):
	"""Rows the editor does not show stay hidden and keep their place (F-4); since F-11 (D2)
	their source texts are not duplicates."""

	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, delta, self.blank])

	def test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate(self) -> None:
		valid = _entry(DUZI, VALID_DUZI, "Bopomofo")
		changes = (("add", lambda: self.model.add(valid)), ("replace", lambda: self.model.replace(1, valid)))
		for name, change in changes:
			with self.subTest(change=name):
				with self.assertRaises(DuplicateEntryError) as caught:
					change()

				self.assertEqual(caught.exception.identifier, DUZI)
				self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])

	def test_remove_of_an_entry_leaves_a_preserved_row_with_the_same_source_text(self) -> None:
		# Only a file can hold both rows (D5); remove must not match the hidden row by its text.
```

```python

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, delta, self.blank])

	def test_the_source_text_of_a_preserved_row_is_not_a_duplicate(self) -> None:
		# F-4 D5 refused it; F-11 (D2) accepts it: OK lists the hidden row, so the user sees
		# which row the new entry replaces (D1).
		self.assertFalse(self.model.source_text_exists(DUZI))
		self.assertFalse(self.model.is_duplicate(DUZI))
		self.assertFalse(self.model.is_duplicate("", editing=self.alpha))
		valid = _entry(DUZI, VALID_DUZI, "Bopomofo")

		self.assertEqual(self.model.add(valid), EntryListUpdate(2))

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank, valid])

	def test_remove_of_an_entry_leaves_a_preserved_row_with_the_same_source_text(self) -> None:
		# Only a file can hold both rows (D5); remove must not match the hidden row by its text.
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python

		self.assertSameObjects(model.rows, [self.alpha, self.kept])

	def test_a_preserved_row_blocks_only_its_raw_unstripped_source_text(self) -> None:
		spaced = PreservedDictionaryRow(DUZI + " ", INVALID_DUZI, "Bopomofo")
		valid = _entry(DUZI, VALID_DUZI, "Bopomofo")
		model = DictionaryEntryListModel([self.alpha, spaced])

		self.assertEqual(model.add(valid), EntryListUpdate(1))

		self.assertSameObjects(model.rows, [self.alpha, spaced, valid])


class LoadSaveTest(unittest.TestCase):
```

```python

		self.assertSameObjects(model.rows, [self.alpha, self.kept])



class LoadSaveTest(unittest.TestCase):
```

Edit: `client/tests/test_dialog_validation.py`

```python
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: DictionaryEntry("", "x", "General")
        event = Mock()

        with (
```

```python
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: DictionaryEntry("", "x", "General")
        dialog._is_duplicate = None
        event = Mock()

        with (
```

Edit: `client/tests/test_dialog_validation.py`

```python
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()


class DialogContextManagerTest(unittest.TestCase):
```

```python
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()


class AddSymbolDialogDuplicateTest(unittest.TestCase):
    """The duplicate check runs in the entry dialog's OK, after the format checks (F-11 D8)."""

    ERROR_TITLE = "錯誤"

    def make_dialog(self, entry: DictionaryEntry, is_duplicate):
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: entry
        dialog._is_duplicate = is_duplicate
        return dialog

    def press_ok(self, dialog):
        event = Mock()
        with (
            patch.object(dialog_module, "message_box") as message_box,
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
            patch.object(dialog_module.wx, "ICON_ERROR", 512, create=True),
        ):
            AddSymbolDialog._on_ok(dialog, event)
        return message_box, event

    def test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text(self) -> None:
        # P2-2 Q6: the entry dialog closed first and the typed entry was lost.
        is_duplicate = Mock(return_value=True)
        dialog = self.make_dialog(DictionaryEntry("Alpha", "⠁", "General"), is_duplicate)

        message_box, event = self.press_ok(dialog)

        is_duplicate.assert_called_once_with("Alpha")
        message_box.assert_called_once_with('來源文字「Alpha」已存在。', self.ERROR_TITLE, 4 | 512, parent=dialog)
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertTrue(dialog.identifier_ctrl.selected_all)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()

    def test_format_is_checked_before_the_duplicate(self) -> None:
        is_duplicate = Mock(return_value=True)
        dialog = self.make_dialog(DictionaryEntry("Alpha", "abc", "Braille"), is_duplicate)

        message_box, event = self.press_ok(dialog)

        is_duplicate.assert_not_called()
        message_box.assert_called_once_with(_("Please enter the a valid Unicode Braille sequence."), INFO_TITLE, 4 | 128, parent=dialog)
        self.assertTrue(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()

    def test_entry_that_is_not_a_duplicate_closes_the_dialog(self) -> None:
        for is_duplicate in (Mock(return_value=False), None):
            with self.subTest(check=is_duplicate is not None):
                dialog = self.make_dialog(DictionaryEntry("Alpha", "⠁", "General"), is_duplicate)

                message_box, event = self.press_ok(dialog)

                message_box.assert_not_called()
                event.Skip.assert_called_once_with()


class DialogContextManagerTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python


class _ScriptedEntryDialog:
    def __init__(self, result: int, entry: DictionaryEntry | None) -> None:
        self._result = result
        self._entry = entry

    def __enter__(self) -> '_ScriptedEntryDialog':
        return self
```

```python


class _ScriptedEntryDialog:
    """The entry dialog: each OK takes the next scripted answer.

    Like ``AddSymbolDialog._on_ok`` (F-11 D8), an answer whose source text the editor's
    ``is_duplicate`` reports shows the duplicate message with the entry dialog as parent
    and keeps the dialog open: the next scripted answer follows (the user fixes the text,
    or cancels); with none left, the user cancels.
    """

    def __init__(self, harness: '_EditorHarness', is_duplicate) -> None:
        self._harness = harness
        self._is_duplicate = is_duplicate
        self._entry = None

    def __enter__(self) -> '_ScriptedEntryDialog':
        return self
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        return None

    def ShowModal(self) -> int:
        return self._result

    def get_entry(self) -> DictionaryEntry | None:
        return self._entry
```

```python
        return None

    def ShowModal(self) -> int:
        harness = self._harness
        while harness.script:
            result, entry = harness.script.pop(0)
            if result != ID_OK or self._is_duplicate is None or not self._is_duplicate(entry.text):
                self._entry = entry
                return result
            harness.record("MessageBox", _duplicate_message(entry.text), ERROR_TITLE, ERROR_FLAGS)
            harness.message_box_parents.append(self)
        return ID_CANCEL

    def get_entry(self) -> DictionaryEntry | None:
        return self._entry
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.other_dialog_buttons: dict[int, _FakeButton] = {}
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
```

```python
        self.other_dialog_buttons: dict[int, _FakeButton] = {}
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.entry_dialogs: list[_ScriptedEntryDialog] = []
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
        if not self.script:
            raise AssertionError("the entry dialog opened without a scripted result")
        result, scripted = self.script.pop(0)
        return _ScriptedEntryDialog(result, scripted)

    # recording

```

```python
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None, *, is_duplicate=None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
        if not self.script:
            raise AssertionError("the entry dialog opened without a scripted result")
        entry_dialog = _ScriptedEntryDialog(self, is_duplicate)
        self.entry_dialogs.append(entry_dialog)
        return entry_dialog

    # recording

```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_duplicate_of_a_hidden_entry_is_rejected_with_the_exact_message(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("bet")
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u281b", "Braille")

        harness.click("Add")

```

```python
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open(self) -> None:
        # Was the P2-2 Q6 KNOWN BUG: the entry dialog closed, then the editor showed the
        # message and the typed entry was lost. Fixed by F-11 (D8): the entry dialog shows
        # it and stays open with the input, so the user can change the text.
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("bet")
        harness.take_log()
        harness.script_entry("Alpha", "\u281b", "Braille")
        harness.script_entry("Gamma", "\u281b", "Braille")

        harness.click("Add")

```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            [
                ["AddSymbolDialog", None],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry
        # is discarded; the entry dialog is not opened again.
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.script, [])

    def test_case_different_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA])
```

```python
            [
                ["AddSymbolDialog", None],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
                ["ChangeValue", ""],
                ["SetItemCount", 3],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 2, True],
                ["Focus", 2],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.message_box_parents, harness.entry_dialogs)
        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS, ["Gamma", "\u281b", UNICODE_BRAILLE]])
        self.assertEqual(harness.script, [])

    def test_duplicate_then_cancel_in_the_entry_dialog_changes_nothing(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("bet")
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u281b", "Braille")
        harness.script_cancel()

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [["AddSymbolDialog", None], ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.state(), before)

    def test_case_different_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA])
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python


class DictionaryEntriesDialogEditTest(_EditorTestCase):
    def test_edit_button_opens_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
```

```python


class DictionaryEntriesDialogEditTest(_EditorTestCase):
    def test_the_entry_dialog_gets_the_duplicate_check_of_the_model(self) -> None:
        # F-11 (D8, D9): an Add checks every entry; an Edit excludes the edited one.
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.script_cancel()
        harness.click("Edit")
        harness.script_cancel()
        harness.click("Add")

        edit_check, add_check = (entry_dialog._is_duplicate for entry_dialog in harness.entry_dialogs)
        self.assertEqual([edit_check(text) for text in ("Alpha", "Beta", "Gamma")], [True, False, False])
        self.assertEqual([add_check(text) for text in ("Alpha", "Beta", "Gamma")], [True, True, False])

    def test_edit_button_opens_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.rows(), [["Alpha", "\u2801\u2801", UNICODE_BRAILLE], BETA_CELLS])
        self.assertEqual(harness.list.selected, 0)

    def test_duplicate_is_rejected_with_the_exact_message_and_nothing_changes(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u2803")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", BETA],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
        self.assertEqual(harness.state(), before)

    def test_identical_rows_edit_of_the_selected_row_can_keep_its_text(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made its own text
```

```python
        self.assertEqual(harness.rows(), [["Alpha", "\u2801\u2801", UNICODE_BRAILLE], BETA_CELLS])
        self.assertEqual(harness.list.selected, 0)

    def test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted(self) -> None:
        # Was the P2-2 Q6 KNOWN BUG (the typed entry was discarded); fixed by F-11 (D8).
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.take_log()
        harness.script_entry("Alpha", "\u2803")
        harness.script_entry("Bravo", "\u2803")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log()[:2],
            [
                ["AddSymbolDialog", BETA],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, harness.entry_dialogs)
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Bravo", "\u2803", GENERAL]])
        self.assertEqual(harness.list.selected, 1)

    def test_identical_rows_edit_of_the_selected_row_can_keep_its_text(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made its own text
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

        self.assertEqual(harness.saved_csv(), HEADER + BADBOPO_HIDDEN_ROWS)

    def test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.script_entry("\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", "Bopomofo")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [["AddSymbolDialog", None], ["MessageBox", _duplicate_message("\u809a\u5b50"), ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)


class DictionaryEntriesDialogModelTest(_EditorTestCase):
```

```python

        self.assertEqual(harness.saved_csv(), HEADER + BADBOPO_HIDDEN_ROWS)

    def test_the_source_text_of_a_hidden_row_can_be_added(self) -> None:
        # F-4 (D5) refused it with the duplicate message; F-11 (D2) checks the shown entries only.
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.script_entry("\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", "Bopomofo")

        harness.click("Add")

        self.assertNotIn("MessageBox", [event[0] for event in harness.take_log()])
        self.assertEqual(harness.rows(), [TAIPEI_CELLS, ["\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", BOPOMOFO]])


class DictionaryEntriesDialogModelTest(_EditorTestCase):
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation 2>&1 | $PY $T/tools/brief.py
```

Expected (the editor checks after the entry dialog closed and gives it no check; hidden rows still count):

```text
ERROR: test_the_entry_dialog_gets_the_duplicate_check_of_the_model (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogEditTest.test_the_entry_dialog_g
TypeError: 'NoneType' object is not callable
FAIL: test_the_source_text_of_a_preserved_row_is_not_a_duplicate (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_the_source_text_of_a_preserved_r
AssertionError: True is not false
FAIL: test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogAddTest.tes
AssertionError: Lists differ: [['Ad[65 chars]8528]] != [['Ad[65 chars]8528], ['ChangeValue', ''], ['SetItemCount', 3[115 chars]rue]]
FAIL: test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogEditTest.test_d
AssertionError: Lists differ: [<_speech_symbols_dialog_under_test.Diction[42 chars]<addr>] != [<tests.test_dictionary_entries_dialog._Scr[42 chars]<addr>]
FAIL: test_the_source_text_of_a_hidden_row_can_be_added (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_the_source_text_of_a_hi
AssertionError: 'MessageBox' unexpectedly found in ['AddSymbolDialog', 'MessageBox']
FAIL: test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text (tests.test_dialog_validation.AddSymbolDialogDuplicateTest.
AssertionError: Expected 'mock' to be called once. Called 0 times.
Ran 151 tests
FAILED (failures=5, errors=1)
```

- [ ] **Step 2: Green: the check in the entry dialog** (`client/dictionaries/entry_list_model.py` and `client/dialog.py`, tabs). The duplicate message keeps one call site (`show_duplicate_source_text`), used by the entry dialog and by the editor's backstop.

Edit: `client/dictionaries/entry_list_model.py`

```python

Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed: they keep their place in the file and ``save``
writes them back unchanged (F-4). ``entries`` and the visible list hold the
entries only. ``save`` writes with the layout of the loaded file (its BOM and
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).
```

```python

Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed, and their source texts are not duplicates (F-11
D2): they keep their place in the file and ``save`` writes them back unchanged
(F-4). ``entries`` and the visible list hold the
entries only. ``save`` writes with the layout of the loaded file (its BOM and
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).
```

Edit: `client/dictionaries/entry_list_model.py`

```python
  first visible entry equal to the previous one winning (as the golden trace
  records);
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  row, entries hidden by the filter and preserved rows included, and excludes
  the edited entry by identity; an edit that keeps the edited entry's own text
  is never a duplicate (F-11 D9).
"""

from __future__ import annotations
```

```python
  first visible entry equal to the previous one winning (as the golden trace
  records);
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  entry, entries hidden by the filter included, preserved rows not (F-11 D2),
  and excludes the edited entry by identity; an edit that keeps the edited
  entry's own text is never a duplicate (F-11 D9).
"""

from __future__ import annotations
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool:
		"""Whether a row other than ``exclude_entry`` has exactly this source text.

		Preserved rows compare their raw, unstripped text (the source R3 uses), so a
		hidden ``"x "`` does not block ``"x"``. Callers pass a validated entry: an
		empty ``text`` would match a preserved blank-text row, but the entry dialog
		strips and requires a source text, so no UI path reaches that case.
		"""
		return any(row.text == text and row is not exclude_entry for row in self._rows)

	def is_duplicate(self, text: str, editing: DictionaryEntry | None = None) -> bool:
		"""Whether adding (``editing`` None) or editing ``editing`` to ``text`` duplicates a row.
```

```python
		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool:
		"""Whether an entry other than ``exclude_entry`` has exactly this source text.

		Preserved rows do not count: OK lists them before removing them (F-11 D1, D2).
		"""
		return any(entry.text == text and entry is not exclude_entry for entry in self._entries)

	def is_duplicate(self, text: str, editing: DictionaryEntry | None = None) -> bool:
		"""Whether adding (``editing`` None) or editing ``editing`` to ``text`` duplicates a row.
```

Edit: `client/dialog.py`

```python
				button.SetLabel(label)


class AddSymbolDialog(ContextManagedDialog, wx.Dialog):
	"""Dialog to create or edit a dictionary entry."""

	def __init__(self, parent: wx.Window | None, entry: DictionaryEntry | None = None):
		title = _("Edit Dictionary Entry") if entry else _("Add Dictionary Entry")
		super().__init__(parent, title=title)

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
```

```python
				button.SetLabel(label)


def show_duplicate_source_text(identifier: str, parent: wx.Window | None) -> None:
	"""Tell the user that another entry already has the source text ``identifier``."""
	message_box(
		_('Source text "{identifier}" already exists.').format(identifier=identifier),
		_("Error"),
		wx.OK | wx.ICON_ERROR,
		parent=parent,
	)


class AddSymbolDialog(ContextManagedDialog, wx.Dialog):
	"""Dialog to create or edit a dictionary entry.

	``is_duplicate(text)`` (optional) runs in OK after the format checks: a duplicate
	source text is reported here and the dialog stays open with the input (F-11 D8).
	"""

	def __init__(
		self,
		parent: wx.Window | None,
		entry: DictionaryEntry | None = None,
		*,
		is_duplicate: Callable[[str], bool] | None = None,
	):
		title = _("Edit Dictionary Entry") if entry else _("Add Dictionary Entry")
		super().__init__(parent, title=title)
		self._is_duplicate = is_duplicate

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
```

Edit: `client/dialog.py`

```python
					self.identifier_ctrl.SetFocus()
				else:
					self.braille_ctrl.SetFocus()
			except RuntimeError:
				pass
			return
```

```python
					self.identifier_ctrl.SetFocus()
				else:
					self.braille_ctrl.SetFocus()
			except RuntimeError:
				pass
			return

		if self._is_duplicate is not None and self._is_duplicate(entry.text):
			show_duplicate_source_text(entry.text, self)
			try:
				self.identifier_ctrl.SetFocus()
				self.identifier_ctrl.SelectAll()
			except RuntimeError:
				pass
			return
```

Edit: `client/dialog.py`

```python
		self._render(self._model.remove(visible_index))

	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
		with AddSymbolDialog(self, entry) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_entry()

	def _show_duplicate_error(self, identifier: str) -> None:
		message_box(
			_('Source text "{identifier}" already exists.').format(identifier=identifier),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=self,
		)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
```

```python
		self._render(self._model.remove(visible_index))

	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
		# The entry dialog checks for a duplicate itself and stays open on one (F-11 D8);
		# the model's DuplicateEntryError stays as a backstop.
		with AddSymbolDialog(self, entry, is_duplicate=lambda text: self._model.is_duplicate(text, editing=entry)) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_entry()

	def _show_duplicate_error(self, identifier: str) -> None:
		show_duplicate_source_text(identifier, self)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation -v 2>&1 | grep -E "^(test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted|test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open|test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text|test_duplicate_then_cancel_in_the_entry_dialog_changes_nothing|test_entry_that_is_not_a_duplicate_closes_the_dialog|test_format_is_checked_before_the_duplicate|test_the_entry_dialog_gets_the_duplicate_check_of_the_model|test_the_source_text_of_a_hidden_row_can_be_added|test_the_source_text_of_a_preserved_row_is_not_a_duplicate) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_the_source_text_of_a_preserved_row_is_not_a_duplicate ok
test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open ok
test_duplicate_then_cancel_in_the_entry_dialog_changes_nothing ok
test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted ok
test_the_entry_dialog_gets_the_duplicate_check_of_the_model ok
test_the_source_text_of_a_hidden_row_can_be_added ok
test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text ok
test_entry_that_is_not_a_duplicate_closes_the_dialog ok
test_format_is_checked_before_the_duplicate ok
Ran 151 tests
OK
Ran 1516 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entry_list_model.py client/tests/test_dialog_validation.py client/tests/test_dictionary_entries_dialog.py client/dictionaries/entry_list_model.py client/dialog.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: report a duplicate source text inside the entry dialog (F-11, P2-2 Q6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                                 |  45 ++++++++--
 client/dictionaries/entry_list_model.py          |  20 ++---
 client/tests/test_dialog_validation.py           |  61 +++++++++++++
 client/tests/test_dictionary_entries_dialog.py   | 108 +++++++++++++++++------
 client/tests/test_dictionary_entry_list_model.py |  29 +++---
 5 files changed, 199 insertions(+), 64 deletions(-)
b2cfda106215f90233282722b2d06f37bfabee15
```

### Task 6: Keep the tone space of a first-tone final syllable (D14)

- [ ] **Step 1: Red: Test Plan A6 (O1 (b), decided by the user on 2026-10-11).** `test_dictionary_entries.py` (tabs): `MIXED_ROWS`' first-tone row becomes an entry with its tone space (its line leaves the hidden lines), the oracle applies the canonical sequence, `validate_dictionary_entry` accepts a sequence without its final space, and `CanonicalBopomofoTest` (`canonical_bopomofo`, the loader and a round trip). The validation test collects the messages instead of letting the parser's error escape: `text.zhuyin.ParseError` is a frozen dataclass, and unittest cannot attach a traceback to it. `test_dictionary_entries_dialog.py` (4 spaces): a first-tone row is shown and an added one is saved with its space. `test_dialog_validation.py` (4 spaces): `get_entry` gives the canonical sequence for 注音 only.

Edit: `client/tests/test_dictionary_entries.py`

```python
DICT_BADBOPO_SHA256 = "c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4"

# Every kind of row the editor does not show, between two entries (F-4): a blank and a
# whitespace-only source text, an invalid Bopomofo sequence with spaces around it, a
# first-tone sequence whose tone space the editor would strip, a row with a missing
# field, and a quoted row whose fields hold a comma, quotes and a line break.
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
```

```python
DICT_BADBOPO_SHA256 = "c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4"

# Every kind of row the editor does not show, between two entries (F-4): a blank and a
# whitespace-only source text, an invalid Bopomofo sequence with spaces around it, a row
# with a missing field, and a quoted row whose fields hold a comma, quotes and a line
# break. The first-tone sequence was hidden too, because the editor stripped its tone
# space; since F-11 (D14) it is an entry that keeps it.
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
```

Edit: `client/tests/test_dictionary_entries.py`

```python
	PreservedDictionaryRow("", "\u2803", "General"),
	PreservedDictionaryRow("  ", "\u2803", "General"),
	PreservedDictionaryRow("\u809a\u5b50", " \u3109\u3128\u02cb|\u3117\u02d9 ", "Bopomofo"),
	PreservedDictionaryRow("\u5abd", "\u3107\u311a ", "Bopomofo"),
	PreservedDictionaryRow("", "\u2803", ""),
	PreservedDictionaryRow('q,"x"', "a\r\nb", "Bopomofo"),
	DictionaryEntry("Beta", "\u2803", "General"),
```

```python
	PreservedDictionaryRow("", "\u2803", "General"),
	PreservedDictionaryRow("  ", "\u2803", "General"),
	PreservedDictionaryRow("\u809a\u5b50", " \u3109\u3128\u02cb|\u3117\u02d9 ", "Bopomofo"),
	DictionaryEntry("\u5abd", "\u3107\u311a ", "Bopomofo"),
	PreservedDictionaryRow("", "\u2803", ""),
	PreservedDictionaryRow('q,"x"', "a\r\nb", "Bopomofo"),
	DictionaryEntry("Beta", "\u2803", "General"),
```

Edit: `client/tests/test_dictionary_entries.py`

```python
				entry_type=normalize_entry_type(row.get("type")),
			)
			if entries_module._is_editable(entry):
				rows.append(entry)
			else:
				rows.append(
```

```python
				entry_type=normalize_entry_type(row.get("type")),
			)
			if entries_module._is_editable(entry):
				if entry.entry_type == "Bopomofo":
					# F-11 (D14): a final first-tone syllable keeps its tone space.
					entry.braille = entries_module.canonical_bopomofo(entry.braille)
				rows.append(entry)
			else:
				rows.append(
```

Edit: `client/tests/test_dictionary_entries.py`

```python

	def test_valid_unicode_braille_is_accepted(self) -> None:
		validate_dictionary_entry(DictionaryEntry("Alpha", "\u2801\u2803", "Braille"))


class DictionaryEntryStorageTest(unittest.TestCase):
```

```python

	def test_valid_unicode_braille_is_accepted(self) -> None:
		validate_dictionary_entry(DictionaryEntry("Alpha", "\u2801\u2803", "Braille"))

	def test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space(self) -> None:
		# F-11 (D14): the entry dialog strips the space; the sequence is valid with it.
		rejected = []
		for braille in ("\u3107\u311a", "\u3107\u311a ", "\u3113\u3128\u3125 \u3112\u3127\u3123", "\u3107\u311a\u02c9", "\u3109\u3128\u02cb|\u3117\u02d9"):
			try:
				validate_dictionary_entry(DictionaryEntry("\u5abd", braille, "Bopomofo"))
			except ValueError as error:
				rejected.append((braille, str(error)))

		message = "\u8acb\u8f38\u5165\u6709\u6548\u7684\u6ce8\u97f3\u5e8f\u5217\u3002"
		self.assertEqual(rejected, [("\u3107\u311a\u02c9", message), ("\u3109\u3128\u02cb|\u3117\u02d9", message)])


class CanonicalBopomofoTest(unittest.TestCase):
	"""The Bopomofo sequence the editor shows and saves (F-11 D14, spec O1 (b))."""

	def test_a_final_first_tone_syllable_keeps_its_tone_space(self) -> None:
		cases = (
			("\u3107\u311a", "\u3107\u311a "),
			("\u3107\u311a ", "\u3107\u311a "),
			("  \u3107\u311a  ", "\u3107\u311a "),
			("\u3107\u311a\u3000", "\u3107\u311a "),
			("\u3113\u3128\u3125 \u3112\u3127\u3123", "\u3113\u3128\u3125 \u3112\u3127\u3123 "),
			("\u3109\u3128\u02cb\u3117\u02d9", "\u3109\u3128\u02cb\u3117\u02d9"),
			(" \u3109\u3128\u02cb\u3117\u02d9 ", "\u3109\u3128\u02cb\u3117\u02d9"),
			("", ""),
			("\u3109\u3128\u02cb|\u3117\u02d9", None),
			("\u3107\u311a\u02c9", None),
			("\u3107\u311a  \u3107\u311a", None),
			("invalid", None),
		)
		for braille, expected in cases:
			with self.subTest(braille=braille):
				self.assertEqual(entries_module.canonical_bopomofo(braille), expected)

	def test_loader_shows_a_row_whose_last_syllable_is_first_tone(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "tone1.csv"
			path.write_bytes("text,braille,type\r\n\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n\u5abd, \u3107\u311a,Bopomofo\r\n".encode("utf-8"))

			rows = load_dictionary_rows(path)
			loaded = entries_module.load_dictionary_file(path)
			save_dictionary_entries(path, loaded.rows, loaded.layout)
			saved = path.read_bytes()

		self.assertEqual(rows, [DictionaryEntry("\u4e2d\u5fc3", "\u3113\u3128\u3125 \u3112\u3127\u3123 ", "Bopomofo"), DictionaryEntry("\u5abd", "\u3107\u311a ", "Bopomofo")])
		self.assertEqual(saved, "text,braille,type\r\n\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n\u5abd,\u3107\u311a ,Bopomofo\r\n".encode("utf-8"))


class DictionaryEntryStorageTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual(rows[0].fields, ("Alpha", "\u2801", "General"))
		self.assertEqual(rows[5].fields, ("", "\u2803"))
		self.assertEqual(rows[6].fields, ('q,"x"', "a\r\nb", "Bopomofo"))
		self.assertEqual([row.line for row in rows if isinstance(row, PreservedDictionaryRow)], [3, 4, 5, 6, 7, 8])
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

```

```python
		self.assertEqual(rows[0].fields, ("Alpha", "\u2801", "General"))
		self.assertEqual(rows[5].fields, ("", "\u2803"))
		self.assertEqual(rows[6].fields, ('q,"x"', "a\r\nb", "Bopomofo"))
		self.assertEqual([row.line for row in rows if isinstance(row, PreservedDictionaryRow)], [3, 4, 5, 7, 8])
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
DUZI = "\u809a\u5b50"
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): two entries around every kind of row the
# editor does not show, and what saving it writes (the row with a missing field gets
# its empty third field).
MIXED_CSV = (
```

```python
DUZI = "\u809a\u5b50"
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): entries around every kind of row the
# editor does not show, and what saving it writes (the row with a missing field gets
# its empty third field).
MIXED_CSV = (
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.rows(), [TAIPEI_CELLS, ["\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", BOPOMOFO]])


class DictionaryEntriesDialogModelTest(_EditorTestCase):
    def test_dictionary_path_is_required(self) -> None:
        parameter = inspect.signature(DictionaryEntriesDialog.__init__).parameters["dictionary_path"]
```

```python
        self.assertEqual(harness.rows(), [TAIPEI_CELLS, ["\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", BOPOMOFO]])


class DictionaryEntriesDialogFirstToneTest(_EditorTestCase):
    """Bopomofo rows whose last syllable is first tone are shown and saved with their tone
    space (F-11 D14; before, the editor stripped the space and hid them)."""

    def test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space(self) -> None:
        harness = self.open_editor(data="text,braille,type\r\n\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n".encode("utf-8"))

        self.assertEqual(harness.rows(), [["\u4e2d\u5fc3", "\u3113\u3128\u3125 \u3112\u3127\u3123 ", BOPOMOFO]])
        harness.script_entry("\u5abd", "\u3107\u311a ", "Bopomofo")
        harness.click("Add")

        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n\u5abd,\u3107\u311a ,Bopomofo\r\n")


class DictionaryEntriesDialogModelTest(_EditorTestCase):
    def test_dictionary_path_is_required(self) -> None:
        parameter = inspect.signature(DictionaryEntriesDialog.__init__).parameters["dictionary_path"]
```

Edit: `client/tests/test_dialog_validation.py`

```python
                event.Skip.assert_called_once_with()


class DialogContextManagerTest(unittest.TestCase):
    def make_dialog(self, dialog_class):
        dialog = object.__new__(dialog_class)
```

```python
                event.Skip.assert_called_once_with()


class _Choice:
    def __init__(self, selection: int) -> None:
        self.selection = selection

    def GetSelection(self) -> int:
        return self.selection


class AddSymbolDialogEntryTest(unittest.TestCase):
    def make_dialog(self, text: str, braille: str, type_index: int):
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.identifier_ctrl.SetValue(text)
        dialog.braille_ctrl = _TextCtrl()
        dialog.braille_ctrl.SetValue(braille)
        dialog.type_choice = _Choice(type_index)
        return dialog

    def entry(self, text: str, braille: str, type_index: int) -> DictionaryEntry:
        with patch.object(dialog_module.wx, "NOT_FOUND", -1, create=True):
            return AddSymbolDialog.get_entry(self.make_dialog(text, braille, type_index))

    def test_a_final_first_tone_syllable_keeps_its_tone_space(self) -> None:
        # F-11 (D14): the stripped "ㄓㄨㄥ ㄒㄧㄣ" did not parse, so it could not be entered.
        self.assertEqual(self.entry(" 中心 ", " ㄓㄨㄥ ㄒㄧㄣ ", 1), DictionaryEntry("中心", "ㄓㄨㄥ ㄒㄧㄣ ", "Bopomofo"))
        self.assertEqual(self.entry("媽", "ㄇㄚ", 1), DictionaryEntry("媽", "ㄇㄚ ", "Bopomofo"))
        self.assertEqual(self.entry("肚子", "ㄉㄨˋㄗ˙ ", 1), DictionaryEntry("肚子", "ㄉㄨˋㄗ˙", "Bopomofo"))

    def test_other_types_and_invalid_sequences_are_only_stripped(self) -> None:
        self.assertEqual(self.entry("媽", " ㄇㄚ ", 0), DictionaryEntry("媽", "ㄇㄚ", "General"))
        self.assertEqual(self.entry("媽", " ㄇㄚˉ ", 1), DictionaryEntry("媽", "ㄇㄚˉ", "Bopomofo"))


class DialogContextManagerTest(unittest.TestCase):
    def make_dialog(self, dialog_class):
        dialog = object.__new__(dialog_class)
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation 2>&1 | $PY $T/tools/brief.py
```

Expected (the strip hides the row and drops the space; `canonical_bopomofo` does not exist):

```text
ERROR: test_a_final_first_tone_syllable_keeps_its_tone_space (tests.test_dictionary_entries.CanonicalBopomofoTest.test_a_final_first_tone_syllable_keeps_its_ton
AttributeError: module 'dictionaries.entries' has no attribute 'canonical_bopomofo'
FAIL: test_loader_shows_a_row_whose_last_syllable_is_first_tone (tests.test_dictionary_entries.CanonicalBopomofoTest.test_loader_shows_a_row_whose_last_syllable
AssertionError: Lists differ: [PreservedDictionaryRow(text='中心', braille[119 chars]e=3)] != [DictionaryEntry(text='中心', braille='ㄓㄨㄥ ㄒ[89 chars]fo')]
FAIL: test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_load_rows_keeps_the_ro
AssertionError: Lists differ: [Dict[129 chars]line=3), PreservedDictionaryRow(text='  ', bra[422 chars]al')] != [Dict[129 chars]line=0), PreservedDictionaryRow(
FAIL: test_rows_carry_their_record_and_entries_still_compare_by_value (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_rows_carry_their_record_and
FAIL: test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space (tests.test_dictionary_entries.DictionaryEntryValidationTest.test_bopomofo_with_a
AssertionError: Lists differ: [('ㄇㄚ', '請輸入有效的注音序列。'), ('ㄓㄨㄥ ㄒㄧㄣ', '請輸入有效的注音序[51 chars]列。')] != [('ㄇㄚˉ', '請輸入有效的注音序列。'), ('ㄉㄨˋ|ㄗ˙', '請輸入有效的注音序列。')]
FAIL: test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogFirstToneTest.test_a_
AssertionError: Lists differ: [] != [['中心', 'ㄓㄨㄥ ㄒㄧㄣ ', '注音']]
FAIL: test_a_final_first_tone_syllable_keeps_its_tone_space (tests.test_dialog_validation.AddSymbolDialogEntryTest.test_a_final_first_tone_syllable_keeps_its_to
AssertionError: DictionaryEntry(text='中心', braille='ㄓㄨㄥ ㄒㄧㄣ', entry_type='Bopomofo') != DictionaryEntry(text='中心', braille='ㄓㄨㄥ ㄒㄧㄣ ', entry_type='Bopomofo')
Ran 189 tests
FAILED (failures=6, errors=12)
```

- [ ] **Step 2: Green: `canonical_bopomofo`** (`client/dictionaries/entries.py` and `client/dialog.py`, tabs). The loader's value, `_is_editable`, `validate_dictionary_entry` and the entry dialog's `get_entry` use it.

Edit: `client/dictionaries/entries.py`

```python
	return DEFAULT_ENTRY_TYPE


def validate_dictionary_entry(entry: DictionaryEntry) -> None:
	if not entry.text.strip():
		raise ValueError(_("Please enter the source text."))
	if normalize_entry_type(entry.entry_type) == "Bopomofo":
		try:
			normalize_zhuyin_sequence(entry.braille)
		except Exception as exc:
			raise ValueError(_("Please enter the a valid Bopomofo sequence.")) from exc
	elif normalize_entry_type(entry.entry_type) == "Braille":
		for braille_character in entry.braille:
			if not BRAILLE_UNICODE_PATTERNS_START <= ord(braille_character) < BRAILLE_UNICODE_PATTERNS_START + 256:
```

```python
	return DEFAULT_ENTRY_TYPE


def canonical_bopomofo(braille: str) -> str | None:
	"""The Bopomofo sequence the editor shows and saves for ``braille``; None if it does not parse.

	Surrounding whitespace is stripped, as from every field, except the tone space of a
	final first-tone syllable: the parser marks a first tone with a space, so a sequence
	that only parses with that space gets it back (F-11 D14).
	"""
	sequence = braille.strip()
	for candidate in (sequence, sequence + " "):
		try:
			normalize_zhuyin_sequence(candidate)
		except Exception:
			continue
		return candidate
	return None


def validate_dictionary_entry(entry: DictionaryEntry) -> None:
	if not entry.text.strip():
		raise ValueError(_("Please enter the source text."))
	if normalize_entry_type(entry.entry_type) == "Bopomofo":
		if canonical_bopomofo(entry.braille) is None:
			raise ValueError(_("Please enter the a valid Bopomofo sequence."))
	elif normalize_entry_type(entry.entry_type) == "Braille":
		for braille_character in entry.braille:
			if not BRAILLE_UNICODE_PATTERNS_START <= ord(braille_character) < BRAILLE_UNICODE_PATTERNS_START + 256:
```

Edit: `client/dictionaries/entries.py`

```python
		entry_type=normalize_entry_type(entry_type),
		fields=tuple(record),
	)
	if _is_editable(entry):
		return entry
	return PreservedDictionaryRow(text=text, braille=braille, entry_type=entry_type, line=line, fields=tuple(record))


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses."""
	if not entry.text:
		return False
	if entry.entry_type == "Bopomofo":
		try:
			normalize_zhuyin_sequence(entry.braille)
		except Exception:
			return False
	return True


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
```

```python
		entry_type=normalize_entry_type(entry_type),
		fields=tuple(record),
	)
	if not _is_editable(entry):
		return PreservedDictionaryRow(text=text, braille=braille, entry_type=entry_type, line=line, fields=tuple(record))
	if entry.entry_type == "Bopomofo":
		entry.braille = canonical_bopomofo(entry.braille)
	return entry


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses
	(once a final first-tone syllable has its tone space back, F-11 D14)."""
	if not entry.text:
		return False
	return entry.entry_type != "Bopomofo" or canonical_bopomofo(entry.braille) is not None


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
```

Edit: `client/dialog.py`

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	validate_dictionary_entry,
)
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
```

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	canonical_bopomofo,
	validate_dictionary_entry,
)
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
```

Edit: `client/dialog.py`

```python
		return key if key in ENTRY_TYPE_LABELS else DEFAULT_ENTRY_TYPE

	def get_entry(self) -> DictionaryEntry:
		return DictionaryEntry(
			text=self.get_identifier(),
			braille=self.get_braille(),
			entry_type=self.get_entry_type(),
		)

	def _apply_initial_values(self, entry: DictionaryEntry | None) -> None:
		if entry:
```

```python
		return key if key in ENTRY_TYPE_LABELS else DEFAULT_ENTRY_TYPE

	def get_entry(self) -> DictionaryEntry:
		text = self.get_identifier()
		braille = self.get_braille()
		entry_type = self.get_entry_type()
		if entry_type == "Bopomofo":
			# The strip took the tone space of a final first-tone syllable (F-11 D14).
			braille = canonical_bopomofo(braille) or braille
		return DictionaryEntry(text=text, braille=braille, entry_type=entry_type)

	def _apply_initial_values(self, entry: DictionaryEntry | None) -> None:
		if entry:
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation -v 2>&1 | grep -E "^(test_a_final_first_tone_syllable_keeps_its_tone_space|test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space|test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space|test_loader_shows_a_row_whose_last_syllable_is_first_tone|test_other_types_and_invalid_sequences_are_only_stripped) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_final_first_tone_syllable_keeps_its_tone_space ok
test_loader_shows_a_row_whose_last_syllable_is_first_tone ok
test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space ok
test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space ok
test_a_final_first_tone_syllable_keeps_its_tone_space ok
test_other_types_and_invalid_sequences_are_only_stripped ok
Ran 189 tests
OK
Ran 1522 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries.py client/tests/test_dictionary_entry_list_model.py client/tests/test_dictionary_entries_dialog.py client/tests/test_dialog_validation.py client/dictionaries/entries.py client/dialog.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: keep the tone space of a first-tone final syllable (F-11)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                                 | 13 +++--
 client/dictionaries/entries.py                   | 41 ++++++++++------
 client/tests/test_dialog_validation.py           | 33 +++++++++++++
 client/tests/test_dictionary_entries.py          | 62 ++++++++++++++++++++++--
 client/tests/test_dictionary_entries_dialog.py   | 15 ++++++
 client/tests/test_dictionary_entry_list_model.py |  2 +-
 6 files changed, 141 insertions(+), 25 deletions(-)
6c3946d1eaa1c8749e826e06d1590f721df1bbf9
```

### Task 7: Read the dictionary before building its editor (D12)

- [ ] **Step 1: Red: Test Plan C9, E (frame), G (string 11).** `test_dictionary_entries_dialog.py` (4 spaces): the harness passes a `model`; the file is read before the native dialog (the Q8 pin flipped: a read error leaves no `Dialog.__init__`); a given model is shown without reading the file; a failure while building destroys the dialog and propagates. `test_gui_document_flows.py` (4 spaces): the frame loads the model (patched `gui.DictionaryEntryListModel`) and passes it; a read error shows F-6's text and builds no editor; an unexpected read error is logged with its traceback as before; a build error shows string 11 and logs `Unexpected error while opening the dictionary editor` with the traceback. `test_i18n.py`: string 11.

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
class _EditorHarness:
    """Build the real editor against fake widgets and drive it like a user."""

    def __init__(self, path: Path, on_base_init=None) -> None:
        self.path = path
        self.parent = object()
        self.on_base_init = on_base_init
        self.base_parent = None
        self.log: list[list] = []
        self.buttons: dict[str, _FakeButton] = {}
```

```python
class _EditorHarness:
    """Build the real editor against fake widgets and drive it like a user."""

    def __init__(self, path: Path, on_base_init=None, model=None) -> None:
        self.path = path
        self.parent = object()
        self.on_base_init = on_base_init
        self.model = model
        self.base_parent = None
        self.log: list[list] = []
        self.buttons: dict[str, _FakeButton] = {}
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            editor.Centre = lambda: self.record("Centre")
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            editor.__init__(self.parent, dictionary_path=self.path)
        except BaseException:
            stack.close()
            raise
```

```python
            editor.Centre = lambda: self.record("Centre")
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            if self.model is None:
                editor.__init__(self.parent, dictionary_path=self.path)
            else:
                editor.__init__(self.parent, dictionary_path=self.path, model=self.model)
        except BaseException:
            stack.close()
            raise
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name) / name

    def open_editor(self, rows=(), *, path=None, data=None, on_base_init=None, keep_log=False) -> _EditorHarness:
        """Write ``rows`` (or the raw ``data``) to a new CSV and open the editor on it.

        ``rows=None`` leaves the file missing. The construction log is dropped
        unless ``keep_log`` is set.
        """
        if path is None:
            path = self.make_path()
```

```python
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name) / name

    def open_editor(self, rows=(), *, path=None, data=None, on_base_init=None, keep_log=False, model=None) -> _EditorHarness:
        """Write ``rows`` (or the raw ``data``) to a new CSV and open the editor on it.

        ``rows=None`` leaves the file missing. The construction log is dropped
        unless ``keep_log`` is set. ``model`` is passed to the editor (F-11 D12).
        """
        if path is None:
            path = self.make_path()
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
                path.write_bytes(data)
            elif rows is not None:
                _write_rows(path, rows)
        harness = _EditorHarness(path, on_base_init=on_base_init)
        harness.open()
        self.addCleanup(harness.close)
        if not keep_log:
```

```python
                path.write_bytes(data)
            elif rows is not None:
                _write_rows(path, rows)
        harness = _EditorHarness(path, on_base_init=on_base_init, model=model)
        harness.open()
        self.addCleanup(harness.close)
        if not keep_log:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        )
        self.assertIs(harness.base_parent, harness.parent)

    def test_native_dialog_exists_before_the_dictionary_is_read(self) -> None:
        path = self.make_path()

        harness = self.open_editor(path=path, on_base_init=lambda: _write_rows(path, [ALPHA]))

        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_empty_dictionary_shows_no_rows_and_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([], keep_log=True)
```

```python
        )
        self.assertIs(harness.base_parent, harness.parent)

    def test_the_dictionary_is_read_before_the_native_dialog_exists(self) -> None:
        # F-11 (D12, F-6 review M-5): the native dialog was created first. The rows written
        # while it is created are not read now; the file was read before.
        path = self.make_path()

        harness = self.open_editor(path=path, on_base_init=lambda: _write_rows(path, [ALPHA]))

        self.assertEqual(harness.rows(), [])

    def test_a_given_model_is_shown_without_reading_the_file(self) -> None:
        # The frame reads the file itself and passes the model (F-11 D12).
        path = self.make_path()
        path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")
        model = DictionaryEntryListModel([DictionaryEntry(*ALPHA), DictionaryEntry(*BETA)])

        harness = self.open_editor(path=path, model=model)

        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertIs(harness.dialog._model, model)

    def test_a_failure_while_building_destroys_the_dialog_and_propagates(self) -> None:
        # F-6 review M-5: a half-built dialog stayed behind as a hidden child of the frame.
        path = self.make_path()
        _write_rows(path, [ALPHA])
        harness = _EditorHarness(path)
        error = RuntimeError("injected")

        def failing_list_ctrl(*_args, **_kwargs):
            raise error

        harness._list_ctrl = failing_list_ctrl

        with self.assertRaises(RuntimeError) as raised:
            harness.open()

        log = harness.take_log()
        self.assertIs(raised.exception, error)
        self.assertEqual(log[0], ["Dialog.__init__", TITLE, DIALOG_STYLE])
        self.assertEqual([event for event in log if event == ["Destroy"]], [["Destroy"]])
        self.assertEqual(log[-1], ["Destroy"])

    def test_empty_dictionary_shows_no_rows_and_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([], keep_log=True)
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.rows(), [])
        self.assertFalse(harness.path.exists())

    def test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog(self) -> None:
        # KNOWN BUG (P2-2 spec, Q8), pinned as it is today, NOT desired: the load error
        # escapes the constructor after the native dialog was created; nothing destroys it.
        path = self.make_path()
        path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")
        harness = _EditorHarness(path)
```

```python
        self.assertEqual(harness.rows(), [])
        self.assertFalse(harness.path.exists())

    def test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog(self) -> None:
        # Was the P2-2 Q8 KNOWN BUG: the load error escaped the constructor after the native
        # dialog was created, and nothing destroyed it. Fixed by F-11 (D12).
        path = self.make_path()
        path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")
        harness = _EditorHarness(path)
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        with self.assertRaises(UnicodeDecodeError):
            harness.open()

        self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])

    def test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom(self) -> None:
        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
```

```python
        with self.assertRaises(UnicodeDecodeError):
            harness.open()

        self.assertEqual(harness.take_log(), [])

    def test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom(self) -> None:
        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame._dictionary_presenter = Mock()
        return frame

    def _open_management(self, frame, result, edit_name, editor_error=None):
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "DictionaryEntriesDialog", side_effect=editor_error) as editor_class,
        ):
            dialog = dialog_class.return_value.__enter__.return_value
            dialog.ShowModal.return_value = result
            dialog.edit_dictionary_name = edit_name
```

```python
        frame._dictionary_presenter = Mock()
        return frame

    def _open_management(self, frame, result, edit_name, editor_error=None, load_error=None):
        # The frame reads the dictionary before it builds the editor (F-11 D12).
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "DictionaryEntriesDialog", side_effect=editor_error) as editor_class,
            patch.object(gui, "DictionaryEntryListModel") as self.model_class,
        ):
            self.model_class.load.side_effect = load_error
            dialog = dialog_class.return_value.__enter__.return_value
            dialog.ShowModal.return_value = result
            dialog.edit_dictionary_name = edit_name
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha")

        presenter.dictionary_path.assert_called_once_with("alpha")
        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_editor_that_cannot_read_its_dictionary_shows_the_reason(self) -> None:
        # F-6 (D6): the file went bad between the check in Dictionary Management and the editor.
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = big5_decode_error()
```

```python
        _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha")

        presenter.dictionary_path.assert_called_once_with("alpha")
        self.model_class.load.assert_called_once_with(Path("dictionary/alpha.csv"))
        editor_class.assert_called_once_with(
            frame, dictionary_path=Path("dictionary/alpha.csv"), model=self.model_class.load.return_value
        )
        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_editor_that_cannot_read_its_dictionary_shows_the_reason(self) -> None:
        # F-6 (D6): the file went bad between the check in Dictionary Management and the editor.
        # Since F-11 (D12) it is read first, and no editor is built.
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = big5_decode_error()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
```

```python
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", load_error=error)

        self.model_class.load.assert_called_once_with(Path("dictionary/alpha.csv"))
        editor_class.assert_not_called()
        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )
        self.assertIsNone(logs.records[0].exc_info)

    def test_editor_failure_that_is_unexpected_is_logged_with_its_traceback(self) -> None:
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = RuntimeError("injected")
```

```python
        )
        self.assertIsNone(logs.records[0].exc_info)

    def test_unexpected_error_reading_the_dictionary_is_logged_with_its_traceback(self) -> None:
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = RuntimeError("injected")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
```

```python
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", load_error=error)

        editor_class.assert_not_called()
        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ['Unexpected error while reading dictionary "alpha.csv"'],
        )
        self.assertIs(logs.records[0].exc_info[1], error)

```

```python
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ['Unexpected error while reading dictionary "alpha.csv"'],
        )
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback(self) -> None:
        # F-11 (D12, F-6 review M-5): an error building the editor was described as a file
        # that cannot be read.
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = RuntimeError("injected")

        with (
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        editor_class.assert_called_once_with(
            frame, dictionary_path=Path("dictionary/alpha.csv"), model=self.model_class.load.return_value
        )
        message_box.assert_called_once_with(
            gui._("Failed to open the dictionary editor: {error}").format(error=error),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ["Unexpected error while opening the dictionary editor"],
        )
        self.assertIs(logs.records[0].exc_info[1], error)

```

Edit: `client/tests/test_i18n.py`

```python

        self.assertEqual(translation.gettext(message), "轉換完成。結果已儲存到文件「{name}」。")
        self.assertEqual(translation.gettext(message).format(name="alpha"), "轉換完成。結果已儲存到文件「alpha」。")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python

        self.assertEqual(translation.gettext(message), "轉換完成。結果已儲存到文件「{name}」。")
        self.assertEqual(translation.gettext(message).format(name="alpha"), "轉換完成。結果已儲存到文件「alpha」。")

    def test_dictionary_editor_failure_string_is_translated(self) -> None:
        # F-11 (D12): building the dictionary editor failed for a reason other than its file.
        message = "Failed to open the dictionary editor: {error}"
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "無法開啟字典編輯器：{error}")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the editor reads after `Dialog.__init__` and has no `model`; the frame has no model to load; the msgid is not translated):

```text
ERROR: test_a_given_model_is_shown_without_reading_the_file (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_a_given_model_is_
TypeError: DictionaryEntriesDialog.__init__() got an unexpected keyword argument 'model'
ERROR: test_edit_result_opens_speech_symbols_for_presenter_path (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_edit_result_opens_speech_symbo
AttributeError: <module 'gui' from '<client>\\gui.py'> does not have the attribute 'DictionaryEntryListModel'
ERROR: test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_edito
ERROR: test_editor_that_cannot_read_its_dictionary_shows_the_reason (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_editor_that_cannot_read_it
ERROR: test_open_management_passes_presenter_and_refreshed_selection (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_open_management_passes_pr
ERROR: test_other_results_open_no_editor (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_other_results_open_no_editor) (result=2, edit_name='a
ERROR: test_other_results_open_no_editor (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_other_results_open_no_editor) (result=5030, edit_name
ERROR: test_unexpected_error_reading_the_dictionary_is_logged_with_its_traceback (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_unexpected_er
FAIL: test_a_failure_while_building_destroys_the_dialog_and_propagates (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_a_fail
AssertionError: Lists differ: [] != [['Destroy']]
FAIL: test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_
AssertionError: Lists differ: [['Dialog.__init__', '自訂字典管理器', 3]] != []
FAIL: test_the_dictionary_is_read_before_the_native_dialog_exists (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_the_diction
AssertionError: Lists differ: [['Alpha', '⠁', '一般']] != []
FAIL: test_dictionary_editor_failure_string_is_translated (tests.test_i18n.TranslationTest.test_dictionary_editor_failure_string_is_translated)
AssertionError: 'Failed to open the dictionary editor: {error}' != '無法開啟字典編輯器：{error}'
Ran 314 tests
FAILED (failures=4, errors=8)
```

- [ ] **Step 2: Green: load first, destroy on a build failure** (`client/dialog.py` and `client/gui.py`, tabs). The frame logs with `gui.py`'s module logger (`dotexpress.gui`, bound at import as before).

Edit: `client/dialog.py`

```python

	Supervising controller: the widgets and the selected row live here, the
	entries and the filter in ``DictionaryEntryListModel``.
	"""

	def __init__(self, parent: wx.Window | None, dictionary_path: Path):
		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = Path(dictionary_path)
		self._model = DictionaryEntryListModel.load(self.dictionary_path)
		self._build_ui()
		self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
		self._update_button_states()

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)
```

```python

	Supervising controller: the widgets and the selected row live here, the
	entries and the filter in ``DictionaryEntryListModel``.

	The file is read before the native dialog exists (``model`` when the caller read
	it, as the frame does), so a read error leaves no dialog behind; an error while
	building the dialog destroys it before it propagates (F-11 D12).
	"""

	def __init__(
		self,
		parent: wx.Window | None,
		dictionary_path: Path,
		model: DictionaryEntryListModel | None = None,
	):
		dictionary_path = Path(dictionary_path)
		if model is None:
			model = DictionaryEntryListModel.load(dictionary_path)
		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = dictionary_path
		self._model = model
		try:
			self._build_ui()
			self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
			self._update_button_states()
		except BaseException:
			self.Destroy()
			raise

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)
```

Edit: `client/gui.py`

```python
from conversion.math_service import latex_to_mathml
from conversion.service import ConversionRequest
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.manager import dictionary_path_for_name
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_unreadable_dictionary, log_dictionary_read_error
```

```python
from conversion.math_service import latex_to_mathml
from conversion.service import ConversionRequest
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.entry_list_model import DictionaryEntryListModel
from dictionaries.manager import dictionary_path_for_name
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_unreadable_dictionary, log_dictionary_read_error
```

Edit: `client/gui.py`

```python
			return
		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
		try:
			editor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path)
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			message_box(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
```

```python
			return
		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
		try:
			# Read before the editor exists (F-11 D12).
			model = DictionaryEntryListModel.load(dictionary_path)
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			message_box(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		try:
			editor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path, model=model)
		except Exception as error:
			# The editor destroyed what it had built (F-11 D12); this is not about the file.
			logger.error("Unexpected error while opening the dictionary editor", exc_info=error)
			message_box(
				_("Failed to open the dictionary editor: {error}").format(error=error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
```

- [ ] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the catalog test fails):

```text
FAIL: test_dictionary_editor_failure_string_is_translated (tests.test_i18n.TranslationTest.test_dictionary_editor_failure_string_is_translated)
AssertionError: 'Failed to open the dictionary editor: {error}' != '無法開啟字典編輯器：{error}'
Ran 314 tests
FAILED (failures=1)
```

- [ ] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (no `xgettext` warning on stderr; `msgmerge` guesses a wrong fuzzy translation for string 11, the msgstr of `Failed to delete dictionary: {error}` (Spec Corrections 10); the next step replaces it; nothing is untranslated):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
369 translated messages, 1 fuzzy translation.
#: gui.py:1058
#, fuzzy, python-brace-format
msgid "Failed to open the dictionary editor: {error}"
msgstr "無法刪除字典：{error}"
```

- [ ] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "匯入時有部分檔案被略過。"

#: gui.py:1058
#, fuzzy, python-brace-format
msgid "Failed to open the dictionary editor: {error}"
msgstr "無法刪除字典：{error}"

#: gui.py:1183
msgid "Export Document"
```

```po
msgstr "匯入時有部分檔案被略過。"

#: gui.py:1058
#, python-brace-format
msgid "Failed to open the dictionary editor: {error}"
msgstr "無法開啟字典編輯器：{error}"

#: gui.py:1183
msgid "Export Document"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (370 translated, no fuzzy; 371 `msgid` lines with the header; the 31 obsolete entries unchanged; no absolute, backslash, test or venv reference):

```text
a second msgmerge changes nothing
msgfmt exit 0
370 translated messages.
0
catalog keys: 371
'Failed to open the dictionary editor: {error}' -> '無法開啟字典編輯器：{error}'
'Remove Rows That Cannot Be Shown' -> '(missing)'
'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?' -> '(missing)'
'Row {line}: no source text' -> '(missing)'
'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid' -> '(missing)'
'Other rows not listed: {count}' -> '(missing)'
'Remove and &Save' -> '(missing)'
'&Back to Editing' -> '(missing)'
'Unsaved Changes' -> '(missing)'
'Do you want to discard the changes you made to dictionary "{name}"?' -> '(missing)'
'&Discard Changes' -> '(missing)'
29283
locales/dotexpress.pot:371
locales/zh_TW/LC_MESSAGES/dotexpress.po:371
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 370 sha256 5048db91c53fffbc31af416178263835c19e30a86acb6f2d683dd49d7da85f33
```

- [ ] **Step 6: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_i18n -v 2>&1 | grep -E "^(test_a_failure_while_building_destroys_the_dialog_and_propagates|test_a_given_model_is_shown_without_reading_the_file|test_dictionary_editor_failure_string_is_translated|test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback|test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog|test_the_dictionary_is_read_before_the_native_dialog_exists|test_unexpected_error_reading_the_dictionary_is_logged_with_its_traceback) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_failure_while_building_destroys_the_dialog_and_propagates ok
test_a_given_model_is_shown_without_reading_the_file ok
test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog ok
test_the_dictionary_is_read_before_the_native_dialog_exists ok
test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback ok
test_unexpected_error_reading_the_dictionary_is_logged_with_its_traceback ok
test_dictionary_editor_failure_string_is_translated ok
Ran 314 tests
OK
Ran 1526 tests
OK (skipped=6)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries_dialog.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/dialog.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: read the dictionary before building its editor (F-11, F-6 M-5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                               |  28 ++-
 client/gui.py                                  |  16 +-
 client/locales/dotexpress.pot                  | 231 +++++++++++++------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 29183 -> 29283 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 231 +++++++++++++------------
 client/tests/test_dictionary_entries_dialog.py |  60 +++++--
 client/tests/test_gui_document_flows.py        |  49 +++++-
 client/tests/test_i18n.py                      |   7 +
 8 files changed, 372 insertions(+), 250 deletions(-)
8dcde92c72263e3d333f789965aacbda99f791ab
```

### Task 8: Confirm and remove dictionary rows the editor cannot show (D1)

- [ ] **Step 1: Red: Test Plan A5, B6, C3, C4, C10, G (strings 1-7); `confirm_box`.** `test_dictionary_entries_dialog.py` (4 spaces): the zh_TW texts of the box; the harness patches `confirm_box` (`create=True`, so the red run reaches the tests), answers it from `script_confirm` and fakes `wx.Window.FindFocus`, `IsDescendant` and `SetFocus`; the hidden-rows tests (the box and Remove and Save, Back to Editing and the focus, the focus outside the editor, deleting every shown row, start lines, the cap of 10, a failed save asking again, item 103's case); the Q2 pin for a file with hidden rows; the trace replay answers the box with Remove and Save, checks and drops its record and expects no hidden row in the CSV (`_run_trace_sequence` gets `before_ok`). `test_dictionary_entry_list_model.py` (tabs): `hidden_rows`, a failed save keeps them, `save` writes the entries only. `test_dictionary_entries.py`: `reason`. `test_message_box.py` (4 spaces): `confirm_box` is a `GenericMessageDialog` with Cancel as default (the recorder is tagged by class). `test_wx_call_sites.py`: the only `GenericMessageDialog` is `confirm_box`. `test_i18n.py`: strings 1-7.

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
```

```python
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

	def test_a_preserved_row_tells_why_the_editor_hides_it(self) -> None:
		# F-11 (D1): the box on OK gives the reason of each row.
		cases = (
			(PreservedDictionaryRow("", "\u2803", "General"), "no_source_text"),
			(PreservedDictionaryRow(" \u3000", "\u2803", "General"), "no_source_text"),
			(PreservedDictionaryRow("\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9", "Bopomofo"), "invalid_bopomofo"),
		)
		for row, reason in cases:
			with self.subTest(row=row):
				self.assertEqual(row.reason, reason)

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): entries around every kind of row the
# editor does not show, and what saving it writes (the row with a missing field gets
# its empty third field).
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
```

```python
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): entries around every kind of row the
# editor does not show.
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))


def _entry(text: str, braille: str = "\u2801", entry_type: str = "General") -> DictionaryEntry:
```

```python
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")


def _entry(text: str, braille: str = "\u2801", entry_type: str = "General") -> DictionaryEntry:
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		self.blank = PreservedDictionaryRow("", "\u2803", "General")
		self.model = DictionaryEntryListModel([self.alpha, self.kept, self.beta, self.blank])

	def test_preserved_rows_are_not_entries_and_never_visible(self) -> None:
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.alpha, self.beta], "")
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])
```

```python
		self.blank = PreservedDictionaryRow("", "\u2803", "General")
		self.model = DictionaryEntryListModel([self.alpha, self.kept, self.beta, self.blank])

	def test_hidden_rows_are_the_preserved_rows_in_file_order(self) -> None:
		self.assertSameObjects(self.model.hidden_rows, [self.kept, self.blank])
		self.model.remove(0)

		self.assertSameObjects(self.model.hidden_rows, [self.kept, self.blank])

	def test_a_failed_save_keeps_the_hidden_rows(self) -> None:
		# O4: OK asks again after a failed Remove and Save.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "dictionary.csv"
			path.mkdir()

			with self.assertRaises(OSError):
				self.model.save(path)

		self.assertSameObjects(self.model.hidden_rows, [self.kept, self.blank])

	def test_preserved_rows_are_not_entries_and_never_visible(self) -> None:
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.alpha, self.beta], "")
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)

	def test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place(self) -> None:
		source = self.directory / "source.csv"
		source.write_bytes(MIXED_CSV)
		target = self.directory / "target.csv"

		DictionaryEntryListModel.load(source).save(target)

		self.assertEqual(target.read_bytes(), MIXED_CSV_SAVED)

	def test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file(self) -> None:
		# F-11 (D5): the layout comes from the load; a new entry gets empty extra fields.
```

```python
		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)

	def test_save_writes_the_entries_only_and_then_holds_no_hidden_rows(self) -> None:
		# F-4 wrote the preserved rows back in place; since F-11 (D1) the editor removes them
		# once the user agrees, so save writes the entries only.
		source = self.directory / "source.csv"
		source.write_bytes(MIXED_CSV)
		target = self.directory / "target.csv"
		model = DictionaryEntryListModel.load(source)

		model.save(target)

		self.assertEqual(
			target.read_bytes(),
			"text,braille,type\r\nAlpha,\u2801,General\r\n\u5abd,\u3107\u311a ,Bopomofo\r\nBeta,\u2803,General\r\n".encode("utf-8"),
		)
		self.assertEqual(model.hidden_rows, ())
		self.assertEqual(model.rows, model.entries)

	def test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file(self) -> None:
		# F-11 (D5): the layout comes from the load; a new entry gets empty extra fields.
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
    return "\u4f86\u6e90\u6587\u5b57\u300c" + identifier + "\u300d\u5df2\u5b58\u5728\u3002"


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
    if entry is None:
        return None
```

```python
    return "\u4f86\u6e90\u6587\u5b57\u300c" + identifier + "\u300d\u5df2\u5b58\u5728\u3002"


# zh_TW texts of the box that lists the hidden rows on OK (F-11 D1).
REMOVE_ROWS_TITLE = "\u79fb\u9664\u7121\u6cd5\u986f\u793a\u7684\u5217"  # Remove Rows That Cannot Be Shown
REMOVE_AND_SAVE = "\u79fb\u9664\u4e26\u5132\u5b58(&S)"  # Remove and &Save
BACK_TO_EDITING = "\u8fd4\u56de\u7de8\u8f2f(&B)"  # &Back to Editing


def _hidden_rows_message(name: str, *lines: str) -> str:
    return (
        "\u5b57\u5178\u300c" + name + "\u300d\u4e2d\u6709\u4e9b\u5217\u7121\u6cd5\u5728\u7de8\u8f2f\u5668\u4e2d\u986f\u793a\uff0c\u5132\u5b58\u6642\u6703\u5f9e\u6a94\u6848\u4e2d\u79fb\u9664\uff1a\n\n"
        + "\n".join(lines)
        + "\n\n\u8981\u79fb\u9664\u9019\u4e9b\u5217\u4e26\u5132\u5b58\u5b57\u5178\u55ce\uff1f"
    )


def _no_source_text(line: int) -> str:
    return f"\u7b2c {line} \u5217\uff1a\u6c92\u6709\u4f86\u6e90\u6587\u5b57"


def _invalid_bopomofo(line: int, text: str, bopomofo: str) -> str:
    return f"\u7b2c {line} \u5217\uff1a\u300c{text}\u300d\u7684\u6ce8\u97f3\u300c{bopomofo}\u300d\u683c\u5f0f\u4e0d\u6b63\u78ba"


def _hidden_rows_box(name: str, *lines: str) -> list:
    return ["ConfirmBox", _hidden_rows_message(name, *lines), REMOVE_ROWS_TITLE, REMOVE_AND_SAVE, BACK_TO_EDITING]


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
    if entry is None:
        return None
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
    def Bind(self, event: str, handler) -> None:
        self._harness.record("Bind", self.name, event)
        self.bindings.append((event, handler))

    def fire(self, event_type: str) -> bool:
        """Call every handler bound to ``event_type``; return whether one called ``Skip``."""
```

```python
    def Bind(self, event: str, handler) -> None:
        self._harness.record("Bind", self.name, event)
        self.bindings.append((event, handler))

    def SetFocus(self) -> None:
        self._harness.record("SetFocus", self.name)
        self._harness.focus = self

    def fire(self, event_type: str) -> bool:
        """Call every handler bound to ``event_type``; return whether one called ``Skip``."""
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.entry_dialogs: list[_ScriptedEntryDialog] = []
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
```

```python
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.entry_dialogs: list[_ScriptedEntryDialog] = []
        # The answers of the confirmation boxes (True: the OK button), and their parents (F-11).
        self.confirm_answers: list[bool] = []
        self.confirm_parents: list[object] = []
        # What wx.Window.FindFocus returns; a fake control's SetFocus sets it.
        self.focus = None
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            ID_APPLY=5102,
            ID_CLOSE=5103,
            NOT_FOUND=-1,
            BoxSizer=lambda _orientation: _FakeSizer(),
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
```

```python
            ID_APPLY=5102,
            ID_CLOSE=5103,
            NOT_FOUND=-1,
            Window=types.SimpleNamespace(FindFocus=lambda: self.focus),
            BoxSizer=lambda _orientation: _FakeSizer(),
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            stack.enter_context(patch.object(dialog, "message_box", self._message_box))
            # Editor tests check the dialog and the saved bytes, not durability: every OK
            # would otherwise wait for a real fsync (40 in the trace replay alone).
            # tests.test_atomic_write keeps the real fsync.
```

```python
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            stack.enter_context(patch.object(dialog, "message_box", self._message_box))
            stack.enter_context(patch.object(dialog, "confirm_box", self._confirm_box, create=True))
            # Editor tests check the dialog and the saved bytes, not durability: every OK
            # would otherwise wait for a real fsync (40 in the trace replay alone).
            # tests.test_atomic_write keeps the real fsync.
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            editor.GetParent = lambda: self.parent
            editor.CentreOnParent = lambda: self.record("CentreOnParent")
            editor.Centre = lambda: self.record("Centre")
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            if self.model is None:
```

```python
            editor.GetParent = lambda: self.parent
            editor.CentreOnParent = lambda: self.record("CentreOnParent")
            editor.Centre = lambda: self.record("Centre")
            editor.IsDescendant = self._is_descendant
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            if self.model is None:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None, *, is_duplicate=None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
```

```python
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _confirm_box(self, message: str, caption: str, ok_label: str, cancel_label: str, parent=None) -> bool:
        self.record("ConfirmBox", message, caption, ok_label, cancel_label)
        self.confirm_parents.append(parent)
        if not self.confirm_answers:
            raise AssertionError("a confirmation box opened without a scripted answer")
        return self.confirm_answers.pop(0)

    def _is_descendant(self, window) -> bool:
        """``wxWindow::IsDescendant``: the editor's own widgets."""
        return window in (self.ok_button, self.cancel_button, self.filter, self.list, *self.buttons.values())

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None, *, is_duplicate=None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

    def script_cancel(self) -> None:
        self.script.append((ID_CANCEL, None))

    def type_filter(self, text: str) -> bool:
        self.filter.value = text
```

```python

    def script_cancel(self) -> None:
        self.script.append((ID_CANCEL, None))

    def script_confirm(self, answer: bool) -> None:
        """The next confirmation box returns ``answer`` (True: its OK button)."""
        self.confirm_answers.append(answer)

    def type_filter(self, text: str) -> bool:
        self.filter.value = text
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            HEADER + "Beta,\u2803,General\r\nAlpha,\u2801,General\r\nGamma,\u281b,Braille\r\n",
        )

    def test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form(self) -> None:
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file, stripping the shown rows and writing an unknown type as
        # General. Since F-4 the rows the editor does not show (blank source text,
        # invalid Bopomofo) are written back unchanged at their place.
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
```

```python
            HEADER + "Beta,\u2803,General\r\nAlpha,\u2801,General\r\nGamma,\u281b,Braille\r\n",
        )

    def test_unchanged_dictionary_with_hidden_rows_asks_and_is_rewritten_without_them(self) -> None:
        # Was the P2-2 Q2 KNOWN BUG for this file: OK always rewrote it, keeping the hidden
        # rows since F-4. F-11 (D1, U2.1): with hidden rows the box appears even without a
        # change; Remove and Save writes the shown entries, stripped and with an unknown
        # type written as General (U2.2).
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)

        self.assertTrue(harness.press_ok())

        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Alpha,\u2801,General\r\n,\u2803,General\r\nZhuyin,invalid,Bopomofo\r\nBeta,\u2803,General\r\n",
        )

    def test_missing_parent_directory_is_created(self) -> None:
        path = self.make_path("nested") / "deeper" / "dictionary.csv"
```

```python
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)
        harness.script_confirm(True)

        self.assertTrue(harness.press_ok())

        self.assertEqual(
            harness.take_log(),
            [
                _hidden_rows_box("dictionary", _no_source_text(3), _invalid_bopomofo(4, "Zhuyin", "invalid")),
                ["Skip"],
            ],
        )
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_missing_parent_directory_is_created(self) -> None:
        path = self.make_path("nested") / "deeper" / "dictionary.csv"
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python


class DictionaryEntriesDialogHiddenRowsTest(_EditorTestCase):
    """Rows the editor cannot show are kept, hidden, through OK (F-4, F-W11)."""

    def test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical(self) -> None:
        # F-W11: OK used to delete the two Bopomofo rows the editor cannot show (4 lines -> 2).
        harness = self.open_editor(data=DICT_BADBOPO)

        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])

    def test_deleting_every_shown_row_keeps_the_hidden_rows(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.select(0)
        harness.click("Delete")

        self.assertEqual(harness.rows(), [])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + BADBOPO_HIDDEN_ROWS)

    def test_the_source_text_of_a_hidden_row_can_be_added(self) -> None:
        # F-4 (D5) refused it with the duplicate message; F-11 (D2) checks the shown entries only.
```

```python


class DictionaryEntriesDialogHiddenRowsTest(_EditorTestCase):
    """Rows the editor cannot show stay hidden; OK lists them and removes them only when the
    user agrees (F-11 D1). F-4 kept them through OK (F-W11); before F-4, OK dropped them
    without a word."""

    BADBOPO_BOX = _hidden_rows_box(
        "dictionary",
        _invalid_bopomofo(3, "\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9"),
        _invalid_bopomofo(4, "\u6578\u5b78", "\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca"),
    )

    def test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        harness.take_log()
        harness.script_confirm(True)

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [self.BADBOPO_BOX, ["Skip"]])
        self.assertEqual(harness.confirm_parents, [harness.dialog])
        self.assertEqual(harness.saved_csv(), HEADER + "\u81fa\u5317,\u281e\u283a,Braille\r\n")
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])

    def test_back_to_editing_writes_nothing_and_puts_the_focus_back(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.focus = harness.ok_button
        harness.take_log()
        harness.script_confirm(False)

        self.assertFalse(harness.press_ok())

        self.assertEqual(harness.take_log(), [self.BADBOPO_BOX, ["SetFocus", "ok"]])
        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)
        self.assertEqual(harness.rows(), [TAIPEI_CELLS])

    def test_focus_outside_the_editor_is_left_alone(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.focus = object()
        harness.take_log()
        harness.script_confirm(False)

        self.assertFalse(harness.press_ok())

        self.assertEqual(harness.take_log(), [self.BADBOPO_BOX])

    def test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.select(0)
        harness.click("Delete")
        harness.script_confirm(True)

        self.assertEqual(harness.rows(), [])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER)

    def test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on(self) -> None:
        # The header is line 1, a blank line counts; whitespace-only text is no source text.
        data = (HEADER + "Alpha,\u2801,General\r\n\r\n,\u2803,General\r\n\u3000 ,\u2803,General\r\n").encode("utf-8")
        harness = self.open_editor(data=data)
        harness.take_log()
        harness.script_confirm(False)

        harness.press_ok()

        self.assertEqual(harness.take_log(), [_hidden_rows_box("dictionary", _no_source_text(4), _no_source_text(5))])

    def test_at_most_ten_hidden_rows_are_listed(self) -> None:
        for count, listed, other in ((10, 10, None), (11, 10, "\u53e6\u6709 1 \u5217\u672a\u5217\u51fa"), (13, 10, "\u53e6\u6709 3 \u5217\u672a\u5217\u51fa")):
            with self.subTest(count=count):
                data = (HEADER + "Alpha,\u2801,General\r\n" + ",\u2803,General\r\n" * count).encode("utf-8")
                harness = self.open_editor(data=data)
                harness.take_log()
                harness.script_confirm(False)

                harness.press_ok()

                lines = [_no_source_text(line) for line in range(3, 3 + listed)] + ([other] if other else [])
                self.assertEqual(harness.take_log(), [_hidden_rows_box("dictionary", *lines)])

    def test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again(self) -> None:
        # O4: the hidden rows are still in the model, so they are listed again.
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.focus = harness.ok_button
        harness.take_log()
        harness.script_confirm(True)

        with patch("os.replace", side_effect=PermissionError(13, "denied")):
            skipped = harness.press_ok()

        self.assertFalse(skipped)
        self.assertEqual(
            harness.take_log(),
            [
                self.BADBOPO_BOX,
                ["MessageBox", "\u5132\u5b58\u5931\u6557\uff1a[Errno 13] denied", ERROR_TITLE, ERROR_FLAGS],
                ["SetFocus", "ok"],
            ],
        )
        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)
        harness.script_confirm(True)
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.take_log(), [self.BADBOPO_BOX, ["Skip"]])
        self.assertEqual(harness.saved_csv(), HEADER + "\u81fa\u5317,\u281e\u283a,Braille\r\n")

    def test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok(self) -> None:
        # GUI item 103: the box names the hidden row the new entry replaces (D1, D2).
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.script_entry("\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", "Bopomofo")
        harness.click("Add")
        harness.take_log()
        harness.script_confirm(True)

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [self.BADBOPO_BOX, ["Skip"]])
        self.assertEqual(harness.saved_csv(), HEADER + "\u81fa\u5317,\u281e\u283a,Braille\r\n\u809a\u5b50,\u3109\u3128\u02cb\u3117\u02d9,Bopomofo\r\n")

    def test_the_source_text_of_a_hidden_row_can_be_added(self) -> None:
        # F-4 (D5) refused it with the duplicate message; F-11 (D2) checks the shown entries only.
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
_TRACE_FILTERS = ("", "", "a", "A", "b", "ab", "ss", "STRASSE", "\u00df", " ", "\u2801", "x", "General")
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")
# The two TRACE_CSV rows the editor does not show (blank source text, invalid Bopomofo).
# The fixture was recorded before F-4, when OK dropped them; since F-4 OK writes them
# back unchanged, so the replay checks them and removes them before comparing.
_TRACE_KEPT_ROWS = (",\u2803,General", "zz,ab,Bopomofo")


```

```python
_TRACE_FILTERS = ("", "", "a", "A", "b", "ab", "ss", "STRASSE", "\u00df", " ", "\u2801", "x", "General")
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")
# The two TRACE_CSV rows the editor does not show (blank source text, invalid Bopomofo).
# The fixture was recorded before F-4, when OK dropped them. F-4 wrote them back; since
# F-11 (D1) OK lists them and Remove and Save drops them again, so the replay answers
# that box and checks that neither row is written.
_TRACE_KEPT_ROWS = (",\u2803,General", "zz,ab,Bopomofo")


```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        harness.script.clear()


def _run_trace_sequence(path: Path, next_action) -> list[dict]:
    """Open the editor on ``TRACE_CSV``, run 25 actions and OK; return every step's observations.

    A step's ``state`` has no ``rows`` when the visible rows did not change
    since the previous step (keeps the fixture small).
    """
    path.write_bytes(TRACE_CSV.encode("utf-8"))
    with _EditorHarness(path) as harness:
```

```python
        harness.script.clear()


def _run_trace_sequence(path: Path, next_action, before_ok=None) -> list[dict]:
    """Open the editor on ``TRACE_CSV``, run 25 actions and OK; return every step's observations.

    A step's ``state`` has no ``rows`` when the visible rows did not change
    since the previous step (keeps the fixture small). ``before_ok(harness)`` runs
    just before OK (the replay scripts the answer of a box there).
    """
    path.write_bytes(TRACE_CSV.encode("utf-8"))
    with _EditorHarness(path) as harness:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            action = next_action(harness, index)
            _perform_trace_action(harness, action)
            steps.append({"action": action, "log": harness.take_log(), "state": harness.state()})
        harness.press_ok()
        steps.append({
            "action": ["ok"],
```

```python
            action = next_action(harness, index)
            _perform_trace_action(harness, action)
            steps.append({"action": action, "log": harness.take_log(), "state": harness.state()})
        if before_ok is not None:
            before_ok(harness)
        harness.press_ok()
        steps.append({
            "action": ["ok"],
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
                    actual = _run_trace_sequence(
                        Path(temp_dir) / f"trace{seed}.csv",
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                    )
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first kept row.
                    lines = actual[-1]["csv"].split("\r\n")
                    self.assertEqual([line for line in lines if line in _TRACE_KEPT_ROWS], list(_TRACE_KEPT_ROWS))
                    actual[-1]["csv"] = "\r\n".join(line for line in lines if line not in _TRACE_KEPT_ROWS)
                    for index, (got, want) in enumerate(zip(actual, expected)):
                        self.assertEqual(got, want, f"seed {seed}, step {index}: {want['action']}")

```

```python
                    actual = _run_trace_sequence(
                        Path(temp_dir) / f"trace{seed}.csv",
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                        before_ok=lambda harness: harness.script_confirm(True),
                    )
                    # F-11 (D1): OK lists the two hidden rows; the box is answered with Remove
                    # and Save and its record taken out of the OK step before comparing.
                    ok_log = actual[-1]["log"]
                    self.assertEqual(
                        ok_log[0],
                        _hidden_rows_box(f"trace{seed}", _no_source_text(5), _invalid_bopomofo(8, "zz", "ab")),
                    )
                    actual[-1]["log"] = ok_log[1:]
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first hidden row.
                    lines = actual[-1]["csv"].split("\r\n")
                    self.assertEqual([line for line in lines if line in _TRACE_KEPT_ROWS], [])
                    for index, (got, want) in enumerate(zip(actual, expected)):
                        self.assertEqual(got, want, f"seed {seed}, step {index}: {want['action']}")

```

Edit: `client/tests/test_message_box.py`

```python
    wx = types.ModuleType("wx")
    wx.Window = type("Window", (), {})
    wx.MessageDialog = type("MessageDialog", (), {})
    wx.YES = 0x2
    wx.OK = 0x4
    wx.NO = 0x8
    wx.YES_NO = wx.YES | wx.NO
    wx.CANCEL = 0x10
    wx.NO_DEFAULT = 0x80
    wx.ICON_WARNING = 0x100
    wx.ICON_ERROR = 0x200
    wx.ICON_INFORMATION = 0x800
```

```python
    wx = types.ModuleType("wx")
    wx.Window = type("Window", (), {})
    wx.MessageDialog = type("MessageDialog", (), {})
    wx.GenericMessageDialog = type("GenericMessageDialog", (), {})
    wx.YES = 0x2
    wx.OK = 0x4
    wx.NO = 0x8
    wx.YES_NO = wx.YES | wx.NO
    wx.CANCEL = 0x10
    wx.NO_DEFAULT = 0x80
    wx.CANCEL_DEFAULT = 0x80000000
    wx.ICON_WARNING = 0x100
    wx.ICON_ERROR = 0x200
    wx.ICON_INFORMATION = 0x800
```

Edit: `client/tests/test_message_box.py`

```python

message_box = message_box_module.message_box
wx = message_box_module.wx


class MessageBoxTest(unittest.TestCase):
```

```python

message_box = message_box_module.message_box
wx = message_box_module.wx
CONFIRM_STYLE = 0x4 | 0x10 | 0x80000000 | 0x100  # OK | CANCEL | CANCEL_DEFAULT | ICON_WARNING


class MessageBoxTest(unittest.TestCase):
```

Edit: `client/tests/test_message_box.py`

```python
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dialog_class(self):
        test = self

        class RecordingMessageDialog:
            def __init__(self, *args):
                test.calls.append(("MessageDialog", *args))

            def __enter__(self):
                test.calls.append(("enter",))
```

```python
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dialog_class(self, name="MessageDialog"):
        test = self

        class RecordingMessageDialog:
            def __init__(self, *args):
                test.calls.append((name, *args))

            def __enter__(self):
                test.calls.append(("enter",))
```

Edit: `client/tests/test_message_box.py`

```python
            ],
        )

    def test_a_label_the_platform_refuses_still_shows_the_box(self) -> None:
        self.label_result = False
        self.answers = [wx.ID_OK]
```

```python
            ],
        )

    def test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default(self) -> None:
        # F-11 (D1, D7): Esc, Alt+F4, the close button and Enter all answer Cancel, which
        # keeps the user's work. wx's generic dialog, not the native task dialog: shown from
        # a modal dialog, a task dialog with its own labels answers Alt+F4 with its first
        # button (measured while planning F-11), here the one that changes the user's work.
        parent = object()
        self.answers = [wx.ID_OK, wx.ID_CANCEL]

        with patch.object(wx, "GenericMessageDialog", self._dialog_class("GenericMessageDialog")):
            first = message_box_module.confirm_box("message", "caption", "&Discard", "&Back", parent=parent)
            second = message_box_module.confirm_box("message", "caption", "&Discard", "&Back")

        self.assertEqual((first, second), (True, False))
        self.assertEqual(
            self.calls[:5],
            [
                ("GenericMessageDialog", parent, "message", "caption", CONFIRM_STYLE),
                ("enter",),
                ("SetOKCancelLabels", "&Discard", "&Back"),
                ("ShowModal",),
                ("exit",),
            ],
        )
        self.assertEqual(self.calls[5], ("GenericMessageDialog", None, "message", "caption", CONFIRM_STYLE))

    def test_confirm_box_closed_any_other_way_is_cancel(self) -> None:
        self.answers = [wx.ID_YES]

        with patch.object(wx, "GenericMessageDialog", self._dialog_class("GenericMessageDialog")):
            self.assertIs(message_box_module.confirm_box("message", "caption", "&Discard", "&Back"), False)

    def test_a_label_the_platform_refuses_still_shows_the_box(self) -> None:
        self.label_result = False
        self.answers = [wx.ID_OK]
```

Edit: `client/tests/test_wx_call_sites.py`

```python
            ["gui.py:BrailleFrame._ask_after_close_save_failure", "ui/message_box.py:message_box"],
        )

    def test_no_production_module_imports_wx_names_around_the_scans(self) -> None:
        # from wx import MessageBox, or import wx as _wx, would let a use slip past the
        # scans above (F-7 review M-1).
```

```python
            ["gui.py:BrailleFrame._ask_after_close_save_failure", "ui/message_box.py:message_box"],
        )

    def test_the_only_generic_message_dialog_is_the_confirmation_box(self) -> None:
        # F-11: ui.message_box.confirm_box uses wx's generic dialog and sets both labels.
        self.assertEqual(find_in_production(is_attribute("GenericMessageDialog")), ["ui/message_box.py:confirm_box"])

    def test_no_production_module_imports_wx_names_around_the_scans(self) -> None:
        # from wx import MessageBox, or import wx as _wx, would let a use slip past the
        # scans above (F-7 review M-1).
```

Edit: `client/tests/test_i18n.py`

```python
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "無法開啟字典編輯器：{error}")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "無法開啟字典編輯器：{error}")

    def test_hidden_rows_box_strings_are_translated(self) -> None:
        # F-11 (D1): the box that lists the rows the editor cannot show before removing them.
        message = (
            'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:'
            "\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?"
        )
        expected = {
            "Remove Rows That Cannot Be Shown": "移除無法顯示的列",
            message: "字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？",
            "Row {line}: no source text": "第 {line} 列：沒有來源文字",
            'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid': "第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確",
            "Other rows not listed: {count}": "另有 {count} 列未列出",
            "Remove and &Save": "移除並儲存(&S)",
            "&Back to Editing": "返回編輯(&B)",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n 2>&1 | $PY $T/tools/brief.py > $T/red8.txt
grep -v -e '(seed=' -e '「trace' $T/red8.txt
grep -c '^FAIL: test_replay_matches_every_recorded_step .*(seed=' $T/red8.txt
```

Expected (no box, `hidden_rows`, `reason` or `confirm_box` yet; the trace replay fails for each of its 40 sequences at the box check, shown here as a count):

```text
ERROR: test_a_preserved_row_tells_why_the_editor_hides_it (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_a_preserved_row_tells_why_the_editor_hi
AttributeError: 'PreservedDictionaryRow' object has no attribute 'reason'
ERROR: test_a_failed_save_keeps_the_hidden_rows (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_a_failed_save_keeps_the_hidden_rows)
AttributeError: 'DictionaryEntryListModel' object has no attribute 'hidden_rows'
ERROR: test_hidden_rows_are_the_preserved_rows_in_file_order (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_hidden_rows_are_the_preserved_rows_i
ERROR: test_confirm_box_closed_any_other_way_is_cancel (tests.test_message_box.MessageBoxTest.test_confirm_box_closed_any_other_way_is_cancel)
AttributeError: module 'ui.message_box' has no attribute 'confirm_box'
ERROR: test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default (tests.test_message_box.MessageBoxTest.test_confirm_box_is_a_generic_warning_who
FAIL: test_save_writes_the_entries_only_and_then_holds_no_hidden_rows (tests.test_dictionary_entry_list_model.LoadSaveTest.test_save_writes_the_entries_only_and
AssertionError: b'tex[43 chars]l\r\n,\xe2\xa0\x83,General\r\n  ,\xe2\xa0\x83,[229 chars]\r\n' != b'tex[43 chars]l\r\n\xe5\xaa\xbd,\xe3\x84\x87\xe3\x84\x9a ,Bo[3
FAIL: test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHid
AssertionError: Lists differ: [['MessageBox', '儲存失敗：[Errno 13] denied', '錯誤', 278528]] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[200 chars]ok']]
FAIL: test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_an_en
AssertionError: Lists differ: [['Skip']] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[134 chars]ip']]
FAIL: test_at_most_ten_hidden_rows_are_listed (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_at_most_ten_hidden_rows_are_liste
AssertionError: Lists differ: [['Skip']] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[209 chars]B)']]
AssertionError: Lists differ: [['Skip']] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[220 chars]B)']]
FAIL: test_back_to_editing_writes_nothing_and_puts_the_focus_back (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_back_to_editi
AssertionError: True is not false
FAIL: test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.t
AssertionError: 'text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n' != 'text,braille,type\r\n'
FAIL: test_focus_outside_the_editor_is_left_alone (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_focus_outside_the_editor_is_l
FAIL: test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.tes
FAIL: test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.
AssertionError: Lists differ: [['Skip']] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[94 chars]B)']]
FAIL: test_unchanged_dictionary_with_hidden_rows_asks_and_is_rewritten_without_them (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogOkTest.test_unc
AssertionError: Lists differ: [['Skip']] != [['ConfirmBox', '字典「dictionary」中有些列無法在編輯器中顯示[123 chars]ip']]
FAIL: test_the_only_generic_message_dialog_is_the_confirmation_box (tests.test_wx_call_sites.WxCallSitesTest.test_the_only_generic_message_dialog_is_the_confirm
AssertionError: Lists differ: [] != ['ui/message_box.py:confirm_box']
FAIL: test_hidden_rows_box_strings_are_translated (tests.test_i18n.TranslationTest.test_hidden_rows_box_strings_are_translated)
AssertionError: {'Rem[28 chars]n': 'Remove Rows That Cannot Be Shown', 'Some [662 chars]ing'} != {'Rem[28 chars]n': '移除無法顯示的列', 'Some rows of dictionary "{nam[4
Ran 213 tests
FAILED (failures=54, errors=7)
40
```

- [ ] **Step 2: Green: the hidden-rows box** (`client/dictionaries/entries.py`, `client/dictionaries/entry_list_model.py` and `client/dialog.py`, tabs; `client/ui/message_box.py`, 4 spaces). `confirm_box` is wx's generic dialog (Spec Corrections 3).

Edit: `client/dictionaries/entries.py`

```python
	entry_type: str
	line: int = field(default=0, compare=False)
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)


DictionaryRow = DictionaryEntry | PreservedDictionaryRow
```

```python
	entry_type: str
	line: int = field(default=0, compare=False)
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)

	@property
	def reason(self) -> str:
		"""Why the editor hides the row: ``"no_source_text"`` or ``"invalid_bopomofo"`` (F-11 D1)."""
		return "no_source_text" if not self.text.strip() else "invalid_bopomofo"


DictionaryRow = DictionaryEntry | PreservedDictionaryRow
```

Edit: `client/dictionaries/entry_list_model.py`

```python
Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed, and their source texts are not duplicates (F-11
D2): they keep their place in the file and ``save`` writes them back unchanged
(F-4). ``entries`` and the visible list hold the
entries only. ``save`` writes with the layout of the loaded file (its BOM and
header); a replaced entry takes over the fields of the row it replaces, so its
extra columns are kept (F-11 D5).

Comparison rules (a file may hold identical rows):

```

```python
Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed, and their source texts are not duplicates (F-11
D2). ``hidden_rows`` lists them for the dialog, which asks before saving;
``save`` writes the entries only, so it removes them from the file (F-11 D1;
F-4 wrote them back). ``entries`` and the visible list hold the entries only.
``save`` writes with the layout of the loaded file (its BOM and header); a
replaced entry takes over the fields of the row it replaces, so its extra
columns are kept (F-11 D5).

Comparison rules (a file may hold identical rows):

```

Edit: `client/dictionaries/entry_list_model.py`

```python
	DictionaryEntry,
	DictionaryLayout,
	DictionaryRow,
	load_dictionary_file,
	save_dictionary_entries,
)
```

```python
	DictionaryEntry,
	DictionaryLayout,
	DictionaryRow,
	PreservedDictionaryRow,
	load_dictionary_file,
	save_dictionary_entries,
)
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		return cls(loaded.rows, loaded.layout)

	def save(self, path: Path) -> None:
		"""Write every row (preserved rows unchanged, in place) with the layout; errors propagate."""
		save_dictionary_entries(path, self._rows, self._layout)

	@property
	def _entries(self) -> list[DictionaryEntry]:
```

```python
		return cls(loaded.rows, loaded.layout)

	def save(self, path: Path) -> None:
		"""Write the entries with the layout of the loaded file; errors propagate.

		The hidden rows are not written (F-11 D1); after a successful write the model
		holds the entries only. After an error the hidden rows are still there.
		"""
		entries = self._entries
		save_dictionary_entries(path, entries, self._layout)
		self._rows = list(entries)

	@property
	def hidden_rows(self) -> tuple[PreservedDictionaryRow, ...]:
		"""The rows the editor does not show, in file order (F-11 D1)."""
		return tuple(row for row in self._rows if isinstance(row, PreservedDictionaryRow))

	@property
	def _entries(self) -> list[DictionaryEntry]:
```

Edit: `client/ui/message_box.py`

```python
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)
```

```python
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)


def confirm_box(
    message: str,
    caption: str,
    ok_label: str,
    cancel_label: str,
    parent: wx.Window | None = None,
) -> bool:
    """Ask before something that changes or loses the user's work; True only for the OK button.

    A warning box with the buttons ``ok_label`` and ``cancel_label``; Cancel is the
    default, and Esc, Alt+F4 and the close button answer it too (F-11 D1, D7). A Yes/No
    box would ignore Esc and Alt+F4. It is wx's generic dialog, not the native task
    dialog of ``message_box``: shown from a modal dialog, a task dialog with its own
    button labels answers Alt+F4 with its first button (measured with wx 4.2.5 on
    Windows 11 while planning F-11), here the one that changes the user's work.
    """
    with wx.GenericMessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING) as dialog:
        dialog.SetOKCancelLabels(ok_label, cancel_label)
        return dialog.ShowModal() == wx.ID_OK
```

Edit: `client/dialog.py`

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	canonical_bopomofo,
	validate_dictionary_entry,
)
```

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	PreservedDictionaryRow,
	canonical_bopomofo,
	validate_dictionary_entry,
)
```

Edit: `client/dialog.py`

```python
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")


def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
```

```python
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import confirm_box, message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")
# The hidden rows the box on OK lists by line; a count stands for the rest (F-11 D1).
HIDDEN_ROWS_LISTED = 10


def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
```

Edit: `client/dialog.py`

```python
		show_duplicate_source_text(identifier, self)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
			self._model.save(self.dictionary_path)
		except Exception as exc:
			message_box(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()


class DictionaryManagementDialog(ContextManagedDialog, wx.Dialog):
```

```python
		show_duplicate_source_text(identifier, self)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		focused = wx.Window.FindFocus()
		# Rows the editor cannot show are listed, and removed only once the user agrees (F-11 D1).
		if self._model.hidden_rows and not self._confirm_hidden_rows():
			self._restore_focus(focused)
			return
		if not self._save():
			self._restore_focus(focused)
			return
		event.Skip()

	def _save(self) -> bool:
		try:
			self._model.save(self.dictionary_path)
		except Exception as exc:
			message_box(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return False
		return True

	def _confirm_hidden_rows(self) -> bool:
		hidden_rows = self._model.hidden_rows
		lines = [self._hidden_row_line(row) for row in hidden_rows[:HIDDEN_ROWS_LISTED]]
		if len(hidden_rows) > HIDDEN_ROWS_LISTED:
			lines.append(_("Other rows not listed: {count}").format(count=len(hidden_rows) - HIDDEN_ROWS_LISTED))
		message = _(
			'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:'
			"\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?"
		).format(name=self.dictionary_path.stem, rows="\n".join(lines))
		return confirm_box(
			message,
			_("Remove Rows That Cannot Be Shown"),
			_("Remove and &Save"),
			_("&Back to Editing"),
			parent=self,
		)

	@staticmethod
	def _hidden_row_line(row: PreservedDictionaryRow) -> str:
		if row.reason == "no_source_text":
			return _("Row {line}: no source text").format(line=row.line)
		return _('Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid').format(
			line=row.line,
			text=row.text.strip(),
			bopomofo=row.braille.strip(),
		)

	def _restore_focus(self, window: wx.Window | None) -> None:
		"""Put the focus back where it was before a box, if that is still one of the editor's
		controls; Windows usually does it alone, but not always (F-9 review M-6, F-11 D7)."""
		if window is not None and self.IsDescendant(window):
			window.SetFocus()


class DictionaryManagementDialog(ContextManagedDialog, wx.Dialog):
```

- [ ] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_message_box tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
```

Expected (the modules without translated texts pass; the editor and catalog tests need the catalogs):

```text
Ran 105 tests
OK
```

- [ ] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (no fuzzy guess; the seven new msgids are untranslated, five of them `python-brace-format`):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
370 translated messages, 7 untranslated messages.
#: dialog.py:574
#, python-brace-format
msgid "Other rows not listed: {count}"
msgstr ""

#: dialog.py:576
#, python-brace-format
msgid ""
"Some rows of dictionary \"{name}\" cannot be shown in the editor. Saving "
"removes them from the file:\n"
"\n"
"{rows}\n"
"\n"
"Do you want to remove these rows and save the dictionary?"
msgstr ""

#: dialog.py:581
msgid "Remove Rows That Cannot Be Shown"
msgstr ""

#: dialog.py:582
msgid "Remove and &Save"
msgstr ""

#: dialog.py:583
msgid "&Back to Editing"
msgstr ""

#: dialog.py:590
#, python-brace-format
msgid "Row {line}: no source text"
msgstr ""

#: dialog.py:591
#, python-brace-format
msgid "Row {line}: \"{text}\", Bopomofo \"{bopomofo}\" is not valid"
msgstr ""
```

- [ ] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
#: dialog.py:574
#, python-brace-format
msgid "Other rows not listed: {count}"
msgstr ""

#: dialog.py:576
#, python-brace-format
```

```po
#: dialog.py:574
#, python-brace-format
msgid "Other rows not listed: {count}"
msgstr "另有 {count} 列未列出"

#: dialog.py:576
#, python-brace-format
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"\n"
"Do you want to remove these rows and save the dictionary?"
msgstr ""

#: dialog.py:581
msgid "Remove Rows That Cannot Be Shown"
msgstr ""

#: dialog.py:582
msgid "Remove and &Save"
msgstr ""

#: dialog.py:583
msgid "&Back to Editing"
msgstr ""

#: dialog.py:590
#, python-brace-format
msgid "Row {line}: no source text"
msgstr ""

#: dialog.py:591
#, python-brace-format
msgid "Row {line}: \"{text}\", Bopomofo \"{bopomofo}\" is not valid"
msgstr ""

#: dialog.py:615
msgid "Dictionary Management"
```

```po
"\n"
"Do you want to remove these rows and save the dictionary?"
msgstr ""
"字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n"
"\n"
"{rows}\n"
"\n"
"要移除這些列並儲存字典嗎？"

#: dialog.py:581
msgid "Remove Rows That Cannot Be Shown"
msgstr "移除無法顯示的列"

#: dialog.py:582
msgid "Remove and &Save"
msgstr "移除並儲存(&S)"

#: dialog.py:583
msgid "&Back to Editing"
msgstr "返回編輯(&B)"

#: dialog.py:590
#, python-brace-format
msgid "Row {line}: no source text"
msgstr "第 {line} 列：沒有來源文字"

#: dialog.py:591
#, python-brace-format
msgid "Row {line}: \"{text}\", Bopomofo \"{bopomofo}\" is not valid"
msgstr "第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確"

#: dialog.py:615
msgid "Dictionary Management"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (377 translated, no fuzzy; 378 `msgid` lines with the header):

```text
a second msgmerge changes nothing
msgfmt exit 0
377 translated messages.
0
catalog keys: 378
'Failed to open the dictionary editor: {error}' -> '無法開啟字典編輯器：{error}'
'Remove Rows That Cannot Be Shown' -> '移除無法顯示的列'
'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?' -> '字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？'
'Row {line}: no source text' -> '第 {line} 列：沒有來源文字'
'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid' -> '第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確'
'Other rows not listed: {count}' -> '另有 {count} 列未列出'
'Remove and &Save' -> '移除並儲存(&S)'
'&Back to Editing' -> '返回編輯(&B)'
'Unsaved Changes' -> '(missing)'
'Do you want to discard the changes you made to dictionary "{name}"?' -> '(missing)'
'&Discard Changes' -> '(missing)'
30122
locales/dotexpress.pot:378
locales/zh_TW/LC_MESSAGES/dotexpress.po:378
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 377 sha256 ebc57eb1e3b3aecb9b1110e2ae8cf733f36c2f3bbe2e0d1d2b60abd0af218432
```

- [ ] **Step 6: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n -v 2>&1 | grep -E "^(test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again|test_a_failed_save_keeps_the_hidden_rows|test_a_preserved_row_tells_why_the_editor_hides_it|test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok|test_at_most_ten_hidden_rows_are_listed|test_back_to_editing_writes_nothing_and_puts_the_focus_back|test_confirm_box_closed_any_other_way_is_cancel|test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default|test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header|test_focus_outside_the_editor_is_left_alone|test_hidden_rows_are_the_preserved_rows_in_file_order|test_hidden_rows_box_strings_are_translated|test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries|test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on|test_save_writes_the_entries_only_and_then_holds_no_hidden_rows|test_the_only_generic_message_dialog_is_the_confirmation_box|test_unchanged_dictionary_with_hidden_rows_asks_and_is_rewritten_without_them) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_preserved_row_tells_why_the_editor_hides_it ok
test_save_writes_the_entries_only_and_then_holds_no_hidden_rows ok
test_a_failed_save_keeps_the_hidden_rows ok
test_hidden_rows_are_the_preserved_rows_in_file_order ok
test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again ok
test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok ok
test_at_most_ten_hidden_rows_are_listed ok
test_back_to_editing_writes_nothing_and_puts_the_focus_back ok
test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header ok
test_focus_outside_the_editor_is_left_alone ok
test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries ok
test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on ok
test_unchanged_dictionary_with_hidden_rows_asks_and_is_rewritten_without_them ok
test_confirm_box_closed_any_other_way_is_cancel ok
test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default ok
test_the_only_generic_message_dialog_is_the_confirmation_box ok
test_hidden_rows_box_strings_are_translated ok
Ran 213 tests
OK
Ran 1539 tests
OK (skipped=6)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries.py client/tests/test_dictionary_entry_list_model.py client/tests/test_dictionary_entries_dialog.py client/tests/test_message_box.py client/tests/test_wx_call_sites.py client/tests/test_i18n.py client/dictionaries/entries.py client/dictionaries/entry_list_model.py client/ui/message_box.py client/dialog.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: confirm and remove dictionary rows the editor cannot show (F-11, #7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                                 |  53 +++++-
 client/dictionaries/entries.py                   |   5 +
 client/dictionaries/entry_list_model.py          |  27 ++-
 client/locales/dotexpress.pot                    | 130 +++++++++-----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo   | Bin 29283 -> 30122 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po   | 135 ++++++++++-----
 client/tests/test_dictionary_entries.py          |  11 ++
 client/tests/test_dictionary_entries_dialog.py   | 208 ++++++++++++++++++++---
 client/tests/test_dictionary_entry_list_model.py |  35 +++-
 client/tests/test_i18n.py                        |  19 +++
 client/tests/test_message_box.py                 |  38 ++++-
 client/tests/test_wx_call_sites.py               |   4 +
 client/ui/message_box.py                         |  21 +++
 13 files changed, 555 insertions(+), 131 deletions(-)
b3da7431a5bb6408e0b209b7bc2a3b0c24147dba
```

### Task 9: Save a dictionary only after a change and ask before discarding changes (D3, D4, D7)

- [ ] **Step 1: Red: Test Plan B1, C1, C5, C6, G (strings 8-10).** `test_dictionary_entries_dialog.py` (4 spaces): `press_cancel`; the construction log binds Cancel; the Q5 pin of the handlers flipped and the Q5 comment of the Delete test turned into the decided behavior (U3.2); `DictionaryEntriesDialogChangesTest` (OK without a change writes nothing and keeps the modification time, a missing file is not created, an Add undone by a Delete is no change, Cancel without a change and with hidden rows only closes, Cancel after a change shows the box, Discard closes without writing, Back to Editing keeps the editor and puts the focus back, OK afterwards writes); the trace replay drops the Cancel binding from the open step when present (Spec Corrections 7). `test_dictionary_entry_list_model.py` (tabs): `HasChangesTest`. `test_i18n.py`: strings 8-10.

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

def _hidden_rows_box(name: str, *lines: str) -> list:
    return ["ConfirmBox", _hidden_rows_message(name, *lines), REMOVE_ROWS_TITLE, REMOVE_AND_SAVE, BACK_TO_EDITING]


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
```

```python

def _hidden_rows_box(name: str, *lines: str) -> list:
    return ["ConfirmBox", _hidden_rows_message(name, *lines), REMOVE_ROWS_TITLE, REMOVE_AND_SAVE, BACK_TO_EDITING]


def _discard_box(name: str) -> list:
    """The box Cancel, Esc and the close box show after a change (F-11 D7)."""
    return ["ConfirmBox", "\u8981\u653e\u68c4\u5c0d\u5b57\u5178\u300c" + name + "\u300d\u6240\u505a\u7684\u8b8a\u66f4\u55ce\uff1f", "\u5c1a\u672a\u5132\u5b58\u7684\u8b8a\u66f4", "\u653e\u68c4\u8b8a\u66f4(&D)", BACK_TO_EDITING]


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
    def press_ok(self) -> bool:
        return self.ok_button.fire("EVT_BUTTON")

    # observations

    def cell(self, row: int, column: int) -> str:
```

```python
    def press_ok(self) -> bool:
        return self.ok_button.fire("EVT_BUTTON")

    def press_cancel(self) -> bool:
        """Cancel; wx turns Esc and the close box into this click as well."""
        return self.cancel_button.fire("EVT_BUTTON")

    # observations

    def cell(self, row: int, column: int) -> str:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
                ["SetLabel", "ok", "\u78ba\u5b9a"],
                ["SetLabel", "cancel", "\u53d6\u6d88"],
                ["Bind", "ok", "EVT_BUTTON"],
                ["SetSizerAndFit"],
                ["CentreOnParent"],
                ["SetItemCount", 2],
```

```python
                ["SetLabel", "ok", "\u78ba\u5b9a"],
                ["SetLabel", "cancel", "\u53d6\u6d88"],
                ["Bind", "ok", "EVT_BUTTON"],
                ["Bind", "cancel", "EVT_BUTTON"],
                ["SetSizerAndFit"],
                ["CentreOnParent"],
                ["SetItemCount", 2],
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803\u2803,General\r\nGamma,,\u281b,Braille\r\n",
        )

    def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
        harness = self.open_editor([ALPHA])

        self.assertEqual([event for event, _handler in harness.ok_button.bindings], ["EVT_BUTTON"])
        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: Cancel has no
        # handler of its own, so it discards every edit without asking.
        self.assertEqual(harness.cancel_button.bindings, [])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")

```

```python
            "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803\u2803,General\r\nGamma,,\u281b,Braille\r\n",
        )

    def test_ok_and_cancel_get_handlers_and_both_standard_buttons_are_localized(self) -> None:
        # Was the P2-2 Q5 KNOWN BUG: Cancel had no handler of its own, so it discarded every
        # edit without asking. F-11 (D7) asks after a change.
        harness = self.open_editor([ALPHA])

        self.assertEqual([event for event, _handler in harness.ok_button.bindings], ["EVT_BUTTON"])
        self.assertEqual([event for event, _handler in harness.cancel_button.bindings], ["EVT_BUTTON"])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")

```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

        harness.click("Delete")

        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: no confirmation.
        self.assertEqual(
            harness.take_log(),
            [
```

```python

        harness.click("Delete")

        # No confirmation: a wrong delete is undone with Cancel and Discard Changes (F-11, U3.2).
        self.assertEqual(
            harness.take_log(),
            [
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            harness.saved_csv(),
            "text,braille,type,note\r\na,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\n",
        )


class DictionaryEntriesDialogOkTest(_EditorTestCase):
```

```python
            harness.saved_csv(),
            "text,braille,type,note\r\na,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\n",
        )


class DictionaryEntriesDialogChangesTest(_EditorTestCase):
    """OK writes only after a change; Cancel, Esc and the close box ask only after one
    (F-11 D3, D4, D7; P2-2 Q2, Q5)."""

    def test_ok_without_a_change_writes_nothing(self) -> None:
        # Was the P2-2 Q2 KNOWN BUG: OK always rewrote the file (no BOM, extra columns lost).
        data = b"\xef\xbb\xbftext,note,braille,type\r\n Alpha ,first,\xe2\xa0\x81,Custom\r\n"
        harness = self.open_editor(data=data)
        before = os.stat(harness.path).st_mtime_ns
        harness.type_filter("alp")
        harness.take_log()

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [["Skip"]])
        self.assertEqual(harness.path.read_bytes(), data)
        self.assertEqual(os.stat(harness.path).st_mtime_ns, before)

    def test_ok_without_a_change_does_not_create_a_missing_file(self) -> None:
        # O11: OK used to create a dictionary deleted after Dictionary Management listed it.
        harness = self.open_editor(None)

        self.assertTrue(harness.press_ok())

        self.assertFalse(harness.path.exists())

    def test_an_add_undone_by_a_delete_is_no_change(self) -> None:
        harness = self.open_editor([ALPHA])
        original = harness.path.read_bytes()
        harness.script_entry(*BETA)
        harness.click("Add")
        harness.click("Delete")
        harness.take_log()

        self.assertTrue(harness.press_cancel())
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [["Skip"], ["Skip"]])
        self.assertEqual(harness.path.read_bytes(), original)

    def test_cancel_without_a_change_closes_without_asking(self) -> None:
        # Hidden rows are not unsaved changes (U3.1).
        for name, data in (("plain", "text,braille,type\r\nAlpha,\u2801,General\r\n".encode("utf-8")), ("hidden rows", DICT_BADBOPO)):
            with self.subTest(name):
                harness = self.open_editor(data=data)
                harness.type_filter("x")
                harness.take_log()

                self.assertTrue(harness.press_cancel())

                self.assertEqual(harness.take_log(), [["Skip"]])
                self.assertEqual(harness.path.read_bytes(), data)

    def test_cancel_after_a_change_asks_and_discard_closes_without_writing(self) -> None:
        harness = self.open_editor([ALPHA])
        original = harness.path.read_bytes()
        harness.script_entry(*BETA)
        harness.click("Add")
        harness.take_log()
        harness.script_confirm(True)

        self.assertTrue(harness.press_cancel())

        self.assertEqual(harness.take_log(), [_discard_box("dictionary"), ["Skip"]])
        self.assertEqual(harness.confirm_parents, [harness.dialog])
        self.assertEqual(harness.path.read_bytes(), original)

    def test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.select(0)
        harness.click("Delete")
        harness.focus = harness.list
        harness.take_log()
        harness.script_confirm(False)

        self.assertFalse(harness.press_cancel())

        self.assertEqual(harness.take_log(), [_discard_box("dictionary"), ["SetFocus", "ListCtrl"]])
        self.assertEqual(harness.rows(), [])
        harness.script_confirm(True)
        self.assertTrue(harness.press_cancel())

    def test_ok_after_back_to_editing_writes_the_change(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.script_entry(*BETA)
        harness.click("Add")
        harness.script_confirm(False)
        harness.press_cancel()
        harness.take_log()

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [["Skip"]])
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")


class DictionaryEntriesDialogOkTest(_EditorTestCase):
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
                        _hidden_rows_box(f"trace{seed}", _no_source_text(5), _invalid_bopomofo(8, "zz", "ab")),
                    )
                    actual[-1]["log"] = ok_log[1:]
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first hidden row.
                    lines = actual[-1]["csv"].split("\r\n")
```

```python
                        _hidden_rows_box(f"trace{seed}", _no_source_text(5), _invalid_bopomofo(8, "zz", "ab")),
                    )
                    actual[-1]["log"] = ok_log[1:]
                    # F-11 (D7): the editor binds its Cancel button as well (the whole
                    # construction log is pinned by test_construction_log_is_exact).
                    if ["Bind", "cancel", "EVT_BUTTON"] in actual[0]["log"]:
                        actual[0]["log"].remove(["Bind", "cancel", "EVT_BUTTON"])
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first hidden row.
                    lines = actual[-1]["csv"].split("\r\n")
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python



class LoadSaveTest(unittest.TestCase):
	def setUp(self) -> None:
		temp_dir = tempfile.TemporaryDirectory()
```

```python



class HasChangesTest(_ModelTestCase):
	"""Whether the entries, in order, differ by value from the loaded ones (F-11 D3)."""

	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.model = DictionaryEntryListModel([self.alpha, PreservedDictionaryRow("", "\u2803", "General"), self.beta])

	def test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values(self) -> None:
		self.assertFalse(self.model.has_changes())
		self.model.apply_filter("alp")
		self.assertFalse(self.model.has_changes())
		self.model.apply_filter("")
		self.model.add(_entry("Gamma", "\u281b"))
		self.model.remove(2)
		self.assertFalse(self.model.has_changes())
		self.model.replace(0, _entry("Alpha", "\u2801"))

		self.assertFalse(self.model.has_changes())

	def test_a_changed_value_a_removal_and_a_new_order_are_changes(self) -> None:
		changes = {
			"text": lambda model: model.replace(0, _entry("alpha", "\u2801")),
			"braille": lambda model: model.replace(0, _entry("Alpha", "\u2801\u2801")),
			"type": lambda model: model.replace(0, _entry("Alpha", "\u2801", "Braille")),
			"removal": lambda model: model.remove(1),
			"order": lambda model: (model.remove(0), model.add(_entry("Alpha", "\u2801"))),
		}
		for name, change in changes.items():
			with self.subTest(name):
				model = DictionaryEntryListModel([_entry("Alpha", "\u2801"), _entry("Beta", "\u2803")])

				change(model)

				self.assertTrue(model.has_changes())

	def test_the_loaded_values_are_copies(self) -> None:
		# A later in-place change of an entry object cannot hide a change.
		self.alpha.text = "Changed"

		self.assertTrue(self.model.has_changes())

	def test_a_saved_model_has_no_changes(self) -> None:
		self.model.add(_entry("Gamma", "\u281b"))
		with tempfile.TemporaryDirectory() as temp_dir:
			self.model.save(Path(temp_dir) / "dictionary.csv")

		self.assertFalse(self.model.has_changes())


class LoadSaveTest(unittest.TestCase):
	def setUp(self) -> None:
		temp_dir = tempfile.TemporaryDirectory()
```

Edit: `client/tests/test_i18n.py`

```python
            "Other rows not listed: {count}": "另有 {count} 列未列出",
            "Remove and &Save": "移除並儲存(&S)",
            "&Back to Editing": "返回編輯(&B)",
        }
        translation = i18n.load_translation()

```

```python
            "Other rows not listed: {count}": "另有 {count} 列未列出",
            "Remove and &Save": "移除並儲存(&S)",
            "&Back to Editing": "返回編輯(&B)",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_discard_changes_box_strings_are_translated(self) -> None:
        # F-11 (D7): Cancel, Esc or the close box after a change in the dictionary editor.
        expected = {
            "Unsaved Changes": "尚未儲存的變更",
            'Do you want to discard the changes you made to dictionary "{name}"?': "要放棄對字典「{name}」所做的變更嗎？",
            "&Discard Changes": "放棄變更(&D)",
        }
        translation = i18n.load_translation()

```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (OK always writes, Cancel has no handler, `has_changes` does not exist, the msgids are not translated):

```text
ERROR: test_a_changed_value_a_removal_and_a_new_order_are_changes (tests.test_dictionary_entry_list_model.HasChangesTest.test_a_changed_value_a_removal_and_a_ne
AttributeError: 'DictionaryEntryListModel' object has no attribute 'has_changes'
ERROR: test_a_saved_model_has_no_changes (tests.test_dictionary_entry_list_model.HasChangesTest.test_a_saved_model_has_no_changes)
ERROR: test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values (tests.test_dictionary_entry_list_model.HasChangesTest.test_no_change_afte
ERROR: test_the_loaded_values_are_copies (tests.test_dictionary_entry_list_model.HasChangesTest.test_the_loaded_values_are_copies)
FAIL: test_an_add_undone_by_a_delete_is_no_change (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test_an_add_undone_by_a_delete_is_no_
AssertionError: False is not true
FAIL: test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test
AssertionError: Lists differ: [] != [['ConfirmBox', '要放棄對字典「dictionary」所做的變更嗎？[59 chars]rl']]
FAIL: test_cancel_after_a_change_asks_and_discard_closes_without_writing (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test_cancel_af
FAIL: test_cancel_without_a_change_closes_without_asking (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test_cancel_without_a_change_c
FAIL: test_ok_without_a_change_does_not_create_a_missing_file (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test_ok_without_a_change_
AssertionError: True is not false
FAIL: test_ok_without_a_change_writes_nothing (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogChangesTest.test_ok_without_a_change_writes_nothing)
AssertionError: b'\xef\xbb\xbftext,note,braille,type\r\nAlpha,first,\xe2\xa0\x81,General\r\n' != b'\xef\xbb\xbftext,note,braille,type\r\n Alpha ,first,\xe2\xa0\
FAIL: test_construction_log_is_exact (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_construction_log_is_exact)
AssertionError: Lists differ: [['Di[651 chars]], ['SetSizerAndFit'], ['CentreOnParent'], ['S[156 chars]rue]] != [['Di[651 chars]], ['Bind', 'cancel', 'EVT_BUTTO
FAIL: test_ok_and_cancel_get_handlers_and_both_standard_buttons_are_localized (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test
AssertionError: Lists differ: [] != ['EVT_BUTTON']
FAIL: test_discard_changes_box_strings_are_translated (tests.test_i18n.TranslationTest.test_discard_changes_box_strings_are_translated)
AssertionError: {'Unsaved Changes': 'Unsaved Changes', 'Do you want to discard[153 chars]ges'} != {'Unsaved Changes': '尚未儲存的變更', 'Do you want to discard the cha
Ran 173 tests
FAILED (failures=10, errors=8)
```

- [ ] **Step 2: Green: `has_changes`, OK only after a change, the Cancel handler** (`client/dictionaries/entry_list_model.py` and `client/dialog.py`, tabs).

Edit: `client/dictionaries/entry_list_model.py`

```python
``save`` writes with the layout of the loaded file (its BOM and header); a
replaced entry takes over the fields of the row it replaces, so its extra
columns are kept (F-11 D5).

Comparison rules (a file may hold identical rows):

```

```python
``save`` writes with the layout of the loaded file (its BOM and header); a
replaced entry takes over the fields of the row it replaces, so its extra
columns are kept (F-11 D5).

``has_changes`` compares the entries, in order and by value, with those loaded
or last saved; hidden rows and the filter do not count, and an add undone by a
delete is no change (F-11 D3). The dialog writes and asks only after a change.

Comparison rules (a file may hold identical rows):

```

Edit: `client/dictionaries/entry_list_model.py`

```python
		self._layout = layout
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
```

```python
		self._layout = layout
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)
		self._loaded_entries = self._copy_of_entries()

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		entries = self._entries
		save_dictionary_entries(path, entries, self._layout)
		self._rows = list(entries)

	@property
	def hidden_rows(self) -> tuple[PreservedDictionaryRow, ...]:
```

```python
		entries = self._entries
		save_dictionary_entries(path, entries, self._layout)
		self._rows = list(entries)
		self._loaded_entries = self._copy_of_entries()

	def has_changes(self) -> bool:
		"""Whether the entries, in order, differ by value from those loaded or last saved (F-11 D3)."""
		return self._entries != self._loaded_entries

	def _copy_of_entries(self) -> list[DictionaryEntry]:
		# Copies, so that an entry changed in place later cannot hide a change.
		return [DictionaryEntry(entry.text, entry.braille, entry.entry_type) for entry in self._entries]

	@property
	def hidden_rows(self) -> tuple[PreservedDictionaryRow, ...]:
```

Edit: `client/dialog.py`

```python
			ok_button = self.FindWindow(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

		finalize_dialog_layout(self, main_sizer)

```

```python
			ok_button = self.FindWindow(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
			cancel_button = self.FindWindow(wx.ID_CANCEL)
			if cancel_button:
				# wx turns Esc and the close box into a click on this button (F-11 D7).
				cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)

		finalize_dialog_layout(self, main_sizer)

```

Edit: `client/dialog.py`

```python

	def _on_ok(self, event: wx.CommandEvent) -> None:
		focused = wx.Window.FindFocus()
		# Rows the editor cannot show are listed, and removed only once the user agrees (F-11 D1).
		if self._model.hidden_rows and not self._confirm_hidden_rows():
			self._restore_focus(focused)
			return
		if not self._save():
			self._restore_focus(focused)
			return
		event.Skip()
```

```python

	def _on_ok(self, event: wx.CommandEvent) -> None:
		focused = wx.Window.FindFocus()
		if self._model.hidden_rows:
			# Rows the editor cannot show are listed, and removed only once the user agrees,
			# even without another change (F-11 D1).
			if not self._confirm_hidden_rows():
				self._restore_focus(focused)
				return
		elif not self._model.has_changes():
			# Nothing to write: the file keeps its bytes (F-11 D4).
			event.Skip()
			return
		if not self._save():
			self._restore_focus(focused)
			return
		event.Skip()

	def _on_cancel(self, event: wx.CommandEvent) -> None:
		focused = wx.Window.FindFocus()
		# Ask only after a change; hidden rows are not one (F-11 D7).
		if self._model.has_changes() and not confirm_box(
			_('Do you want to discard the changes you made to dictionary "{name}"?').format(name=self.dictionary_path.stem),
			_("Unsaved Changes"),
			_("&Discard Changes"),
			_("&Back to Editing"),
			parent=self,
		):
			self._restore_focus(focused)
			return
		event.Skip()
```

- [ ] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model 2>&1 | $PY $T/tools/brief.py
```

Expected (the model passes; the editor and catalog tests need the catalogs):

```text
Ran 57 tests
OK
```

- [ ] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (`msgmerge` guesses a wrong fuzzy translation for string 9, the msgstr of `Do you want to delete dictionary "{name}"?` (Spec Corrections 10); strings 8 and 10 are untranslated; the next step fills all three and drops the fuzzy flag):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
377 translated messages, 1 fuzzy translation, 2 untranslated messages.
#: dialog.py:576
#, fuzzy, python-brace-format
msgid "Do you want to discard the changes you made to dictionary \"{name}\"?"
msgstr "要刪除字典「{name}」嗎？"
#: dialog.py:577
msgid "Unsaved Changes"
msgstr ""

#: dialog.py:578
msgid "&Discard Changes"
msgstr ""
```

- [ ] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "刪除"

#: dialog.py:576
#, fuzzy, python-brace-format
msgid "Do you want to discard the changes you made to dictionary \"{name}\"?"
msgstr "要刪除字典「{name}」嗎？"

#: dialog.py:577
msgid "Unsaved Changes"
msgstr ""

#: dialog.py:578
msgid "&Discard Changes"
msgstr ""

#: dialog.py:579 dialog.py:607
msgid "&Back to Editing"
```

```po
msgstr "刪除"

#: dialog.py:576
#, python-brace-format
msgid "Do you want to discard the changes you made to dictionary \"{name}\"?"
msgstr "要放棄對字典「{name}」所做的變更嗎？"

#: dialog.py:577
msgid "Unsaved Changes"
msgstr "尚未儲存的變更"

#: dialog.py:578
msgid "&Discard Changes"
msgstr "放棄變更(&D)"

#: dialog.py:579 dialog.py:607
msgid "&Back to Editing"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (380 translated, no fuzzy; 381 `msgid` lines with the header):

```text
a second msgmerge changes nothing
msgfmt exit 0
380 translated messages.
0
catalog keys: 381
'Failed to open the dictionary editor: {error}' -> '無法開啟字典編輯器：{error}'
'Remove Rows That Cannot Be Shown' -> '移除無法顯示的列'
'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?' -> '字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？'
'Row {line}: no source text' -> '第 {line} 列：沒有來源文字'
'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid' -> '第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確'
'Other rows not listed: {count}' -> '另有 {count} 列未列出'
'Remove and &Save' -> '移除並儲存(&S)'
'&Back to Editing' -> '返回編輯(&B)'
'Unsaved Changes' -> '尚未儲存的變更'
'Do you want to discard the changes you made to dictionary "{name}"?' -> '要放棄對字典「{name}」所做的變更嗎？'
'&Discard Changes' -> '放棄變更(&D)'
30362
locales/dotexpress.pot:381
locales/zh_TW/LC_MESSAGES/dotexpress.po:381
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 380 sha256 5b4b3a19fe0c09dd66c8a421262904b029f34af3827f9d27a2a0fff3114faf3e
```

- [ ] **Step 6: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_i18n -v 2>&1 | grep -E "^(test_a_changed_value_a_removal_and_a_new_order_are_changes|test_a_saved_model_has_no_changes|test_an_add_undone_by_a_delete_is_no_change|test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back|test_cancel_after_a_change_asks_and_discard_closes_without_writing|test_cancel_without_a_change_closes_without_asking|test_discard_changes_box_strings_are_translated|test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values|test_ok_after_back_to_editing_writes_the_change|test_ok_and_cancel_get_handlers_and_both_standard_buttons_are_localized|test_ok_without_a_change_does_not_create_a_missing_file|test_ok_without_a_change_writes_nothing|test_the_loaded_values_are_copies) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_changed_value_a_removal_and_a_new_order_are_changes ok
test_a_saved_model_has_no_changes ok
test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values ok
test_the_loaded_values_are_copies ok
test_an_add_undone_by_a_delete_is_no_change ok
test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back ok
test_cancel_after_a_change_asks_and_discard_closes_without_writing ok
test_cancel_without_a_change_closes_without_asking ok
test_ok_after_back_to_editing_writes_the_change ok
test_ok_without_a_change_does_not_create_a_missing_file ok
test_ok_without_a_change_writes_nothing ok
test_ok_and_cancel_get_handlers_and_both_standard_buttons_are_localized ok
test_discard_changes_box_strings_are_translated ok
Ran 173 tests
OK
Ran 1551 tests
OK (skipped=6)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries_dialog.py client/tests/test_dictionary_entry_list_model.py client/tests/test_i18n.py client/dictionaries/entry_list_model.py client/dialog.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: save a dictionary only after a change and ask before discarding changes (F-11, P2-2 Q2, Q5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                                 |  30 +++++-
 client/dictionaries/entry_list_model.py          |  14 +++
 client/locales/dotexpress.pot                    |  61 +++++++-----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo   | Bin 30122 -> 30362 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po   |  61 +++++++-----
 client/tests/test_dictionary_entries_dialog.py   | 120 ++++++++++++++++++++++-
 client/tests/test_dictionary_entry_list_model.py |  50 ++++++++++
 client/tests/test_i18n.py                        |  11 +++
 8 files changed, 291 insertions(+), 56 deletions(-)
239eaf1dc896559c9bb450ea5177399ea56729ec
```

### Task 10: Ignore hidden dictionary rows when converting (D13)

- [ ] **Step 1: Red: Test Plan F.** `test_conversion_text_dictionary_rules.py` (4 spaces): the golden case "Bopomofo row with a processing that raises" flips (the row is not a rule); new cases: whitespace-only sources, a row the real parser rejects, first-tone rows that convert as before; `EditorParityTest`: 23 rows, each a rule exactly when `load_dictionary_rows` shows it, and the parser called once on the raw value of a row that stays. `test_dictionary_entries.py` (tabs): the round trip keeps the rules, which no longer include the hidden rows.

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
    apply_dictionary,
    split_bracket_segments,
)
from text.zhuyin import normalize_zhuyin_sequence


```

```python
    apply_dictionary,
    split_bracket_segments,
)
from dictionaries.entries import DictionaryEntry, load_dictionary_rows
from text.zhuyin import normalize_zhuyin_sequence


```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
        r"\[⠙⠨\]\[⠗⠂\]",
    ),
    DictionaryCase(
        "Bopomofo row with a processing that raises",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋㄗ˙,Bopomofo\n",
        TEST_BOPOMOFO,
        "raises",
        "肚子",
        r"\[肚子\]",
        r"\[⠙⠨⠗⠂\]",
    ),
    DictionaryCase(
        "Bopomofo row with the real zhuyin parser and data file",
```

```python
        r"\[⠙⠨\]\[⠗⠂\]",
    ),
    DictionaryCase(
        # Was a rule through the fallback (r"\[肚子\]", r"\[⠙⠨⠗⠂\]"); since F-11 (D13) a
        # Bopomofo row the parser rejects is ignored, as the dictionary editor hides it.
        "Bopomofo row with a processing that raises is not a rule",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋㄗ˙,Bopomofo\n",
        TEST_BOPOMOFO,
        "raises",
        "肚子",
        "肚子",
        "肚子",
    ),
    DictionaryCase(
        # F-11 (D13): whitespace-only source texts replaced spaces before (r"\[x\]\[t\]\[y\]").
        "whitespace-only source is not a rule",
        DICTIONARY_HEADER + "  ,x,Braille\n　,y,Braille\n台,t,\n",
        BOPOMOFO_HEADER,
        "identity",
        "  台　",
        r"  \[台\]　",
        r"  \[t\]　",
    ),
    DictionaryCase(
        # F-11 (D13): was the fallback rule r"\[⠙⠌⠐|⠓⠁\]".
        "Bopomofo row the real parser rejects is not a rule",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\n",
        None,
        "zhuyin",
        "肚子",
        "肚子",
        "肚子",
    ),
    DictionaryCase(
        # Rows whose last syllable is first tone, which the editor shows since F-11 (D14),
        # stay rules and convert as before, also without the tone space (the fallback).
        "first-tone Bopomofo rows convert as before",
        DICTIONARY_HEADER + "中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo\n媽,ㄇㄚ,Bopomofo\n",
        None,
        "zhuyin",
        "中心媽",
        r"\[中\]\[心\]\[媽\]",
        r"\[⠁⠯⠄\]\[⠑⠹⠄\]\[⠍⠜\]",
    ),
    DictionaryCase(
        "Bopomofo row with the real zhuyin parser and data file",
```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})


class DictionaryRulesLoaderTest(DictionaryFilesTestCase):
    def test_constructing_a_loader_reads_nothing(self) -> None:
        with OpenRecorder() as recorder, patch.object(
```

```python
        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})


class EditorParityTest(DictionaryFilesTestCase):
    """Conversion ignores exactly the rows the dictionary editor hides (F-11 D13, U6)."""

    # (text, braille, type, whether the editor shows the row): the F-4 cases, the rows of
    # dict_badbopo.csv, whitespace variants, other types, and the first-tone cases of D14.
    ROWS = (
        ("Alpha", "⠁", "General", True),
        ("", "⠃", "General", False),
        ("  ", "⠃", "General", False),
        ("　", "⠃", "Braille", False),
        ("\t", "x", "General", False),
        ("臺北", "⠞⠺", "Braille", True),
        ("肚子", "ㄉㄨˋ|ㄗ˙", "Bopomofo", False),
        ("肚子", " ㄉㄨˋ|ㄗ˙ ", "Bopomofo", False),
        ("數學", "ㄕㄨˋ ㄒㄩㄝˊ", "Bopomofo", False),
        ("肚子", "ㄉㄨˋㄗ˙", "Bopomofo", True),
        ("肚子", " ㄉㄨˋㄗ˙ ", "Bopomofo", True),
        ("媽", "ㄇㄚ ", "Bopomofo", True),
        ("媽", "ㄇㄚ", "Bopomofo", True),
        ("媽", " ㄇㄚ", "Bopomofo", True),
        ("媽", "ㄇㄚ  ", "Bopomofo", True),
        ("中心", "ㄓㄨㄥ ㄒㄧㄣ", "Bopomofo", True),
        ("媽", "ㄇㄚˉ", "Bopomofo", False),
        ("空", "", "Bopomofo", True),
        ("q", "invalid", "bopomofo", True),
        ("q", "invalid", " Bopomofo", True),
        ("q", "invalid", "Unknown", True),
        ("q", "invalid", "", True),
        ('q,"x"', "a\r\nb", "Bopomofo", False),
    )

    def test_a_row_is_a_rule_exactly_when_the_editor_shows_it(self) -> None:
        for text, braille, type_, shown in self.ROWS:
            with self.subTest(text=text, braille=braille, type=type_):
                with self.dictionary_path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["text", "braille", "type"])
                    writer.writerow([text, braille, type_])

                rules = LoadedDictionaryRules.from_paths(
                    self.dictionary_path, DATA_DIR / "Bopomofo2Braille.csv", processing=normalize_zhuyin_sequence
                )

                self.assertEqual(isinstance(load_dictionary_rows(self.dictionary_path)[0], DictionaryEntry), shown)
                self.assertEqual(bool(rules.raw_rules), shown)

    def test_the_parser_is_called_on_the_raw_sequence_first(self) -> None:
        # A row that stays converts exactly as before: the raw value is parsed once, as today.
        calls = []

        def processing(text):
            calls.append(text)
            return text

        self.dictionary_path.write_text(DICTIONARY_HEADER + "肚子, ㄉㄨˋ ,Bopomofo\n", encoding="utf-8")
        self.bopomofo_path.write_text(TEST_BOPOMOFO, encoding="utf-8")

        LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=processing)

        self.assertEqual(calls, [" ㄉㄨˋ "])


class DictionaryRulesLoaderTest(DictionaryFilesTestCase):
    def test_constructing_a_loader_reads_nothing(self) -> None:
        with OpenRecorder() as recorder, patch.object(
```

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual(data, "text,braille,type\r\n\u809a\u5b50,\u3109,Bopomofo\r\n".encode("utf-8"))

	def test_round_trip_keeps_the_conversion_rules(self) -> None:
		# Conversion also uses the rows the editor hides (an invalid Bopomofo sequence
		# falls back to its raw symbols), so a load/save round trip must not change them.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)
```

```python
		self.assertEqual(data, "text,braille,type\r\n\u809a\u5b50,\u3109,Bopomofo\r\n".encode("utf-8"))

	def test_round_trip_keeps_the_conversion_rules(self) -> None:
		# A load/save round trip must not change the conversion rules. Since F-11 (D13)
		# conversion ignores the rows the editor hides, as the hidden invalid sequence.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)
```

Edit: `client/tests/test_dictionary_entries.py`

```python
			after = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

		self.assertEqual(after, before)
		self.assertIn("\u809a\u5b50", [source for source, _replacement in before.replacement_rules])

	def test_rows_carry_their_record_and_entries_still_compare_by_value(self) -> None:
		# F-11 (D6): the record's fields and the start line are kept, outside equality.
```

```python
			after = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

		self.assertEqual(after, before)
		self.assertEqual([source for source, _replacement in before.replacement_rules], ["Alpha", "\u5abd", "Beta"])

	def test_rows_carry_their_record_and_entries_still_compare_by_value(self) -> None:
		# F-11 (D6): the record's fields and the start line are kept, outside equality.
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
```

Expected (whitespace-only and invalid Bopomofo rows are still rules):

```text
FAIL: test_apply_dictionary_gives_the_recorded_output_for_every_case (tests.test_conversion_text_dictionary_rules.DictionaryRulesCasesTest.test_apply_dictionary
AssertionError: {'raw': '\\[肚子\\]', 'replacement': '\\[⠙⠨⠗⠂\\]'} != {'raw': '肚子', 'replacement': '肚子'}
AssertionError: {'raw': '\\[  \\]\\[台\\]\\[\u3000\\]', 'replacement': '\\[x\\]\\[t\\]\\[y\\]'} != {'raw': '  \\[台\\]\u3000', 'replacement': '  \\[t\\]\u3000'}
AssertionError: {'raw': '\\[肚子\\]', 'replacement': '\\[⠙⠌⠐|⠓⠁\\]'} != {'raw': '肚子', 'replacement': '肚子'}
FAIL: test_a_row_is_a_rule_exactly_when_the_editor_shows_it (tests.test_conversion_text_dictionary_rules.EditorParityTest.test_a_row_is_a_rule_exactly_when_the_
AssertionError: True != False
FAIL: test_from_paths_gives_the_recorded_output_for_every_case (tests.test_conversion_text_dictionary_rules.LoadedDictionaryRulesTest.test_from_paths_gives_the_
FAIL: test_round_trip_keeps_the_conversion_rules (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_round_trip_keeps_the_conversion_rules)
AssertionError: Lists differ: ['Alpha', '  ', '肚子', '媽', 'q,"x"', 'Beta'] != ['Alpha', '媽', 'Beta']
Ran 59 tests
FAILED (failures=15)
```

- [ ] **Step 2: Green: skip what the editor hides** (`client/conversion/text/dictionary_rules.py`, 4 spaces). The raw value is parsed first, as before; only when that raises is the editor's test applied (Spec Corrections 6).

Edit: `client/conversion/text/dictionary_rules.py`

```python
    return _scan_trie(text, _build_trie(replacements))


def _wrap_atomic_parts(parts: list[str]) -> str:
    return (
        DICTIONARY_MARKER_OPEN
```

```python
    return _scan_trie(text, _build_trie(replacements))


def _editor_shows_bopomofo(target: str, processing: Callable[[str], object]) -> bool:
    """Whether the dictionary editor shows a Bopomofo row with this sequence (F-11 D13).

    The editor's test (``dictionaries.entries.canonical_bopomofo``) with ``processing`` as
    the parser: the stripped sequence parses, or it does once a final first-tone syllable
    has its tone space (D14). This module imports nothing from ``dictionaries``.
    """
    sequence = target.strip()
    for candidate in (sequence, sequence + " "):
        try:
            processing(candidate)
        except Exception:
            continue
        return True
    return False


def _wrap_atomic_parts(parts: list[str]) -> str:
    return (
        DICTIONARY_MARKER_OPEN
```

Edit: `client/conversion/text/dictionary_rules.py`

```python
        """Read the dictionary and Bopomofo rule files.

        A missing dictionary gives empty rules without opening the Bopomofo file.
        A leading UTF-8 BOM is ignored.
        """
        dictionary_path = Path(dictionary_path)
        if not dictionary_path.exists():
```

```python
        """Read the dictionary and Bopomofo rule files.

        A missing dictionary gives empty rules without opening the Bopomofo file.
        A leading UTF-8 BOM is ignored. A row the dictionary editor hides is not a rule:
        a source text that is empty once stripped, or a Bopomofo sequence the editor
        rejects (F-11 D13). Every other row converts as before, from its raw values.
        """
        dictionary_path = Path(dictionary_path)
        if not dictionary_path.exists():
```

Edit: `client/conversion/text/dictionary_rules.py`

```python
            for row in reader:
                source = (row.get("text") or "")
                target = (row.get("braille") or "")
                if not source:
                    continue

                type_ = (row.get("type") or "")
```

```python
            for row in reader:
                source = (row.get("text") or "")
                target = (row.get("braille") or "")
                if not source.strip():
                    continue

                type_ = (row.get("type") or "")
```

Edit: `client/conversion/text/dictionary_rules.py`

```python
                    try:
                        target = processing(target)
                    except Exception:
                        pass
                    if isinstance(target, str):
                        target_parts = [target]
                    else:
```

```python
                    try:
                        target = processing(target)
                    except Exception:
                        # The raw sequence is scanned as it is, unless the editor hides the row.
                        if not _editor_shows_bopomofo(target, processing):
                            continue
                    if isinstance(target, str):
                        target_parts = [target]
                    else:
```

- [ ] **Step 3: Green: the new and changed tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_dictionary_entries -v 2>&1 | grep -E "^(test_a_row_is_a_rule_exactly_when_the_editor_shows_it|test_the_parser_is_called_on_the_raw_sequence_first) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_row_is_a_rule_exactly_when_the_editor_shows_it ok
test_the_parser_is_called_on_the_raw_sequence_first ok
Ran 59 tests
OK
Ran 1553 tests
OK (skipped=6)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_text_dictionary_rules.py client/tests/test_dictionary_entries.py client/conversion/text/dictionary_rules.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: ignore hidden dictionary rows when converting (F-11, #8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/text/dictionary_rules.py         |  27 +++++-
 .../tests/test_conversion_text_dictionary_rules.py | 102 ++++++++++++++++++++-
 client/tests/test_dictionary_entries.py            |   6 +-
 3 files changed, 126 insertions(+), 9 deletions(-)
0d0f93c8340a7ca86bcaf46775b7970ad90b4935
```
### Task 11: Verification (no commit)

`BASE` is `main` at `1ce6ce5`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1483 + 70; no failure and no error, F-W6 is fixed):

```text
Ran 1553 tests
OK (skipped=6)
```

- [ ] **Step 2: Criterion 2, focused modules; the F-11 tests (new and renamed) ran and passed; two orders of three modules.** The verbose run is kept in `$T/verbose.txt`, so a failure there is named.

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_conversion_text_dictionary_rules tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_dictionary_entry_list_model tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entries_dialog tests.test_dictionary_entry_list_model 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_conversion_text_dictionary_rules tests.test_gui_document_flows tests.test_i18n tests.test_message_box tests.test_wx_call_sites -v > $T/verbose.txt 2>&1; grep -cE "^(test_a_changed_value_a_removal_and_a_new_order_are_changes|test_a_column_named_twice_gets_the_value_at_its_last_position|test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again|test_a_failed_save_keeps_the_hidden_rows|test_a_failure_while_building_destroys_the_dialog_and_propagates|test_a_final_first_tone_syllable_keeps_its_tone_space|test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space|test_a_given_model_is_shown_without_reading_the_file|test_a_missing_file_has_no_rows_and_the_default_layout|test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them|test_a_preserved_row_tells_why_the_editor_hides_it|test_a_row_is_a_rule_exactly_when_the_editor_shows_it|test_a_saved_model_has_no_changes|test_an_add_undone_by_a_delete_is_no_change|test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok|test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte|test_another_row_cannot_take_the_text_of_an_identical_pair|test_at_most_ten_hidden_rows_are_listed|test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back|test_back_to_editing_writes_nothing_and_puts_the_focus_back|test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom|test_bom_is_kept_and_never_added|test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space|test_cancel_after_a_change_asks_and_discard_closes_without_writing|test_cancel_without_a_change_closes_without_asking|test_confirm_box_closed_any_other_way_is_cancel|test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default|test_default_layout_gives_the_bytes_of_the_writer_before_f11|test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header|test_dictionary_editor_failure_string_is_translated|test_discard_changes_box_strings_are_translated|test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted|test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open|test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text|test_duplicate_then_cancel_in_the_entry_dialog_changes_nothing|test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback|test_entry_that_is_not_a_duplicate_closes_the_dialog|test_focus_outside_the_editor_is_left_alone|test_format_is_checked_before_the_duplicate|test_header_order_is_kept_and_missing_required_columns_are_appended|test_hidden_rows_are_the_preserved_rows_in_file_order|test_hidden_rows_are_written_with_their_fields|test_hidden_rows_box_strings_are_translated|test_hidden_rows_record_the_line_on_which_their_record_starts|test_identical_rows_delete_removes_the_selected_row|test_identical_rows_edit_of_the_selected_row_can_keep_its_text|test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin|test_identical_rows_replace_the_visible_object_and_can_keep_their_text|test_import_copy_that_cannot_be_installed_keeps_its_permission_error|test_import_copy_that_cannot_be_installed_shows_the_error|test_import_source_that_cannot_be_opened_raises_the_import_source_error|test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason|test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error|test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog|test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text|test_layout_records_the_bom_and_the_header_as_read|test_loader_shows_a_row_whose_last_syllable_is_first_tone|test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values|test_ok_after_a_change_keeps_the_header_and_the_extra_columns|test_ok_after_back_to_editing_writes_the_change|test_ok_and_cancel_get_handlers_and_both_standard_buttons_are_localized|test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries|test_ok_without_a_change_does_not_create_a_missing_file|test_ok_without_a_change_writes_nothing|test_other_types_and_invalid_sequences_are_only_stripped|test_read_errors_equal_those_of_dictreader|test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first|test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name|test_rename_onto_another_file_under_another_case_is_refused|test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none|test_replacement_is_selected_by_identity_even_when_it_equals_another_row|test_rows_carry_their_record_and_entries_still_compare_by_value|test_rows_keep_every_field_of_their_record|test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized|test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on|test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file|test_save_writes_the_entries_only_and_then_holds_no_hidden_rows|test_the_dictionary_is_read_before_the_native_dialog_exists|test_the_entry_dialog_gets_the_duplicate_check_of_the_model|test_the_loaded_values_are_copies|test_the_only_generic_message_dialog_is_the_confirmation_box|test_the_parser_is_called_on_the_raw_sequence_first|test_the_source_text_of_a_hidden_row_can_be_added|test_the_source_text_of_a_preserved_row_is_not_a_duplicate|test_unchanged_dictionary_with_hidden_rows_asks_and_is_rewritten_without_them|test_unexpected_error_reading_the_dictionary_is_logged_with_its_traceback|test_values_and_classes_equal_those_of_dictreader) .* ok$" $T/verbose.txt; grep -E "^(FAIL|ERROR):" $T/verbose.txt; tail -1 $T/verbose.txt
```

Expected (the count is 88: the names of the tests each red step added or renamed; two names occur in two modules):

```text
Ran 549 tests
OK
Ran 185 tests
OK
Ran 185 tests
OK
88
OK
```

- [ ] **Step 3: Criterion 3 (no KNOWN BUG pin of P2-2 Q2, Q4, Q5, Q6 or Q8 is left) and the shuffled module order, six seeds** (one process each, about two minutes).

```bash
grep -rn "KNOWN BUG (P2-2 spec, Q[24568])" tests | wc -l
for s in 0 1 2 3 4 5; do $PY -B $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
0
      6 ran=1553 failures=0 errors=0 skipped=6 []
```

- [ ] **Step 4: Criterion 4, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; `git diff` against `main` adds exactly the eleven entries (plus `#:` reference lines); 380 msgids, all translated, 0 fuzzy.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
grep -c '^#, fuzzy' locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO diff 1ce6ce5 -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
```

Expected (no entry is fuzzy; the last command lists every changed line of the `.po` that is not a `#:` reference: the eleven new entries, and the duplicate message and `Error`, which move up in the file with `show_duplicate_source_text` (Task 5) with their texts unchanged):

```text
generate-pot exit 0
fresh template identical apart from POT-Creation-Date
380 translated messages.
0
source msgids: 380 sha256 5b4b3a19fe0c09dd66c8a421262904b029f34af3827f9d27a2a0fff3114faf3e
+#, python-brace-format
+msgid "Source text \"{identifier}\" already exists."
+msgstr "來源文字「{identifier}」已存在。"
+
+msgid "Error"
+msgstr "錯誤"
+
-msgid "Source text \"{identifier}\" already exists."
-msgstr "來源文字「{identifier}」已存在。"
+msgid "Do you want to discard the changes you made to dictionary \"{name}\"?"
+msgstr "要放棄對字典「{name}」所做的變更嗎？"
-msgid "Error"
-msgstr "錯誤"
+msgid "Unsaved Changes"
+msgstr "尚未儲存的變更"
+
+msgid "&Discard Changes"
+msgstr "放棄變更(&D)"
+
+msgid "&Back to Editing"
+msgstr "返回編輯(&B)"
+#, python-brace-format
+msgid "Other rows not listed: {count}"
+msgstr "另有 {count} 列未列出"
+
+#, python-brace-format
+msgid ""
+"Some rows of dictionary \"{name}\" cannot be shown in the editor. Saving "
+"removes them from the file:\n"
+"\n"
+"{rows}\n"
+"\n"
+"Do you want to remove these rows and save the dictionary?"
+msgstr ""
+"字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n"
+"\n"
+"{rows}\n"
+"\n"
+"要移除這些列並儲存字典嗎？"
+
+msgid "Remove Rows That Cannot Be Shown"
+msgstr "移除無法顯示的列"
+
+msgid "Remove and &Save"
+msgstr "移除並儲存(&S)"
+
+#, python-brace-format
+msgid "Row {line}: no source text"
+msgstr "第 {line} 列：沒有來源文字"
+
+#, python-brace-format
+msgid "Row {line}: \"{text}\", Bopomofo \"{bopomofo}\" is not valid"
+msgstr "第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確"
+
+#, python-brace-format
+msgid "Failed to open the dictionary editor: {error}"
+msgstr "無法開啟字典編輯器：{error}"
+
```

- [ ] **Step 5: Criteria 5-7: fixtures, untouched modules, touched files, application data.**

```bash
BASE=1ce6ce5
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/dictionaries/read_problems.py client/dictionaries/name_prompt.py client/dictionaries/actions.py client/translation client/shared client/text client/config.py client/log.py client/documents client/settings client/braille client/tests/fixtures && echo "read_problems, name_prompt, actions, translation, shared, text, config, log, documents, settings, braille and the fixtures unchanged"
git -C $REPO diff --stat=200 $BASE -- client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
read_problems, name_prompt, actions, translation, shared, text, config, log, documents, settings, braille and the fixtures unchanged
 client/conversion/text/dictionary_rules.py            |  27 ++++++-
 client/dialog.py                                      | 163 ++++++++++++++++++++++++++++++++++------
 client/dictionaries/entries.py                        | 174 ++++++++++++++++++++++++++++++++-----------
 client/dictionaries/entry_list_model.py               | 125 ++++++++++++++++++++++---------
 client/dictionaries/manager.py                        |  38 +++++++++-
 client/dictionaries/presenter.py                      |   5 ++
 client/gui.py                                         |  16 +++-
 client/locales/dotexpress.pot                         | 274 ++++++++++++++++++++++++++++++++++++++++---------------------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo        | Bin 29183 -> 30362 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po        | 283 ++++++++++++++++++++++++++++++++++++++++++---------------------------
 client/tests/test_conversion_text_dictionary_rules.py | 102 ++++++++++++++++++++++++-
 client/tests/test_dialog_validation.py                |  94 +++++++++++++++++++++++
 client/tests/test_dictionary_entries.py               | 331 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 client/tests/test_dictionary_entries_dialog.py        | 567 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---------------------
 client/tests/test_dictionary_entry_list_model.py      | 204 ++++++++++++++++++++++++++++++++++++++++++--------
 client/tests/test_dictionary_manager.py               |  51 +++++++++++++
 client/tests/test_dictionary_name_prompt.py           |  26 ++++++-
 client/tests/test_dictionary_presenter.py             |  69 ++++++++++++++++-
 client/tests/test_gui_document_flows.py               |  49 ++++++++++--
 client/tests/test_i18n.py                             |  37 +++++++++
 client/tests/test_message_box.py                      |  38 +++++++++-
 client/tests/test_wx_call_sites.py                    |   4 +
 client/ui/message_box.py                              |  21 ++++++
 23 files changed, 2233 insertions(+), 465 deletions(-)
application data unchanged
worktree application data checked
```

- [ ] **Step 6: Criterion 8, mutation check** (51 mutants: the spec's 27 as 28 mutants, its item 22 being two (the cap at 9 and at 11) and its item 11 being "the duplicate check neither excluding the edited entry nor letting it keep its text" (excluding the edited entry alone is implied by the twin rule, so that mutant would change nothing); and 23 more: the loaded entries not copied, a failed save dropping the hidden rows, the reason of a whitespace-only text, the native task dialog, the Cancel button not bound, OK writing without a change, the focus not restored or restored outside the editor (two), the editor passing no duplicate check, Replace selecting by equality, a column named twice read at its first position, the BOM not detected, the tone-space retry dropped (the editor's test, the entry dialog, the loader's value, conversion: four), conversion keeping invalid Bopomofo rows, the rename refusing the same file, the import source error not wrapped or shown raw (two), a build error described as unreadable, the editor reading after its native dialog, a build failure not destroyed; about three minutes). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f11_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
has-changes-always-true: 6 caught: test_dictionary_entries_dialog.test_an_add_undone_by_a_delete_is_no_change, test_dictionary_entries_dialog.test_cancel_without_a_change_closes_without_asking, test_dictionary_entries_dialog.test_ok_without_a_change_does_not_create_a_missing_file, test_dictionary_entries_dialog.test_ok_without_a_change_writes_nothing, and 2 more
has-changes-ignores-order: 1 caught: test_dictionary_entry_list_model.test_a_changed_value_a_removal_and_a_new_order_are_changes
has-changes-counts-hidden-rows: 2 caught: test_dictionary_entries_dialog.test_cancel_without_a_change_closes_without_asking, test_dictionary_entry_list_model.test_no_change_after_load_a_filter_an_add_undone_or_an_edit_to_the_same_values
loaded-entries-not-copied: 1 caught: test_dictionary_entry_list_model.test_the_loaded_values_are_copies
hidden-rows-box-without-hidden-rows: 17 caught: test_dictionary_entries_dialog.test_a_first_tone_row_is_shown_and_an_added_one_is_saved_with_its_space, test_dictionary_entries_dialog.test_an_add_undone_by_a_delete_is_no_change, test_dictionary_entries_dialog.test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom, test_dictionary_entries_dialog.test_dictionary_without_write_access_shows_the_message_and_keeps_the_file, and 13 more
remove-and-save-writes-hidden-rows: 7 caught: test_dictionary_entries_dialog.test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again, test_dictionary_entries_dialog.test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok, test_dictionary_entries_dialog.test_deleting_every_shown_row_and_removing_the_hidden_ones_leaves_the_header, test_dictionary_entries_dialog.test_ok_lists_the_hidden_rows_and_remove_and_save_writes_the_shown_entries, and 3 more
back-to-editing-still-writes: 1 caught: test_dictionary_entries_dialog.test_back_to_editing_writes_nothing_and_puts_the_focus_back
hidden-rows-cap-9: 1 caught: test_dictionary_entries_dialog.test_at_most_ten_hidden_rows_are_listed
hidden-rows-cap-11: 1 caught: test_dictionary_entries_dialog.test_at_most_ten_hidden_rows_are_listed
start-line-off-by-one: 11 caught: test_dictionary_entries.test_hidden_rows_record_the_line_on_which_their_record_starts, test_dictionary_entries.test_rows_carry_their_record_and_entries_still_compare_by_value, test_dictionary_entries_dialog.test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again, test_dictionary_entries_dialog.test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok, and 7 more
reason-of-whitespace-text: 2 caught: test_dictionary_entries.test_a_preserved_row_tells_why_the_editor_hides_it, test_dictionary_entries_dialog.test_rows_without_a_source_text_are_listed_by_the_line_their_record_starts_on
failed-save-drops-hidden-rows: 2 caught: test_dictionary_entries_dialog.test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again, test_dictionary_entry_list_model.test_a_failed_save_keeps_the_hidden_rows
ok-is-the-default: 1 caught: test_message_box.test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default
native-task-dialog: 1 caught: test_message_box.test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default
cancel-skips-without-asking: 2 caught: test_dictionary_entries_dialog.test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back, test_dictionary_entries_dialog.test_cancel_after_a_change_asks_and_discard_closes_without_writing
cancel-asks-without-a-change: 2 caught: test_dictionary_entries_dialog.test_an_add_undone_by_a_delete_is_no_change, test_dictionary_entries_dialog.test_cancel_without_a_change_closes_without_asking
cancel-not-bound: 6 caught: test_dictionary_entries_dialog.test_an_add_undone_by_a_delete_is_no_change, test_dictionary_entries_dialog.test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back, test_dictionary_entries_dialog.test_cancel_after_a_change_asks_and_discard_closes_without_writing, test_dictionary_entries_dialog.test_cancel_without_a_change_closes_without_asking, and 2 more
ok-writes-without-a-change: 2 caught: test_dictionary_entries_dialog.test_ok_without_a_change_does_not_create_a_missing_file, test_dictionary_entries_dialog.test_ok_without_a_change_writes_nothing
focus-not-restored: 3 caught: test_dictionary_entries_dialog.test_a_failed_save_after_remove_and_save_keeps_the_editor_open_and_the_next_ok_asks_again, test_dictionary_entries_dialog.test_back_to_editing_keeps_the_editor_and_the_change_and_puts_the_focus_back, test_dictionary_entries_dialog.test_back_to_editing_writes_nothing_and_puts_the_focus_back
focus-restored-outside-the-editor: 1 caught: test_dictionary_entries_dialog.test_focus_outside_the_editor_is_left_alone
duplicate-check-includes-hidden-rows: 3 caught: test_dictionary_entries_dialog.test_an_entry_added_with_the_text_of_a_hidden_row_replaces_it_on_ok, test_dictionary_entries_dialog.test_the_source_text_of_a_hidden_row_can_be_added, test_dictionary_entry_list_model.test_the_source_text_of_a_preserved_row_is_not_a_duplicate
duplicate-check-keeps-the-edited-entry: 11 caught: test_dictionary_entries_dialog.test_identical_rows_edit_of_the_selected_row_can_keep_its_text, test_dictionary_entries_dialog.test_ok_after_a_change_keeps_the_header_and_the_extra_columns, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entries_dialog.test_same_source_text_is_accepted, and 7 more
twin-cannot-keep-its-text: 4 caught: test_dictionary_entries_dialog.test_identical_rows_edit_of_the_selected_row_can_keep_its_text, test_dictionary_entry_list_model.test_identical_rows_replace_the_visible_object_and_can_keep_their_text, test_dictionary_entry_list_model.test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text, test_dictionary_entry_list_model.test_replacement_is_selected_by_identity_even_when_it_equals_another_row
entry-dialog-closes-on-a-duplicate: 1 caught: test_dialog_validation.test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text
source-text-not-focused: 1 caught: test_dialog_validation.test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text
editor-passes-no-duplicate-check: 3 caught: test_dictionary_entries_dialog.test_duplicate_is_reported_in_the_entry_dialog_and_a_changed_text_is_accepted, test_dictionary_entries_dialog.test_duplicate_of_a_hidden_entry_is_reported_in_the_entry_dialog_which_stays_open, test_dictionary_entries_dialog.test_the_entry_dialog_gets_the_duplicate_check_of_the_model
remove-by-equality: 3 caught: test_dictionary_entries_dialog.test_identical_rows_delete_removes_the_selected_row, test_dictionary_entry_list_model.test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin, test_dictionary_entry_list_model.test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first
replace-drops-fields: 2 caught: test_dictionary_entries_dialog.test_ok_after_a_change_keeps_the_header_and_the_extra_columns, test_dictionary_entry_list_model.test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none
replace-selects-by-equality: 1 caught: test_dictionary_entry_list_model.test_replacement_is_selected_by_identity_even_when_it_equals_another_row
bom-dropped: 4 caught: test_dictionary_entries.test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte, test_dictionary_entries.test_bom_is_kept_and_never_added, test_dictionary_entries_dialog.test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom, test_dictionary_entry_list_model.test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file
bom-always-written: 31 caught: test_dictionary_entries.test_a_column_named_twice_gets_the_value_at_its_last_position, test_dictionary_entries.test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them, test_dictionary_entries.test_bom_is_kept_and_never_added, test_dictionary_entries.test_default_layout_gives_the_bytes_of_the_writer_before_f11, and 27 more
extra-columns-dropped: 8 caught: test_dictionary_entries.test_a_column_named_twice_gets_the_value_at_its_last_position, test_dictionary_entries.test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them, test_dictionary_entries.test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte, test_dictionary_entries.test_hidden_rows_are_written_with_their_fields, and 4 more
header-reordered: 27 caught: test_dictionary_entries.test_a_column_named_twice_gets_the_value_at_its_last_position, test_dictionary_entries.test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them, test_dictionary_entries.test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte, test_dictionary_entries.test_bom_is_kept_and_never_added, and 23 more
column-named-twice-first-position: 2 caught: test_dictionary_entries.test_a_column_named_twice_gets_the_value_at_its_last_position, test_dictionary_entries.test_values_and_classes_equal_those_of_dictreader
bom-not-detected: 4 caught: test_dictionary_entries.test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte, test_dictionary_entries.test_layout_records_the_bom_and_the_header_as_read, test_dictionary_entries_dialog.test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom, test_dictionary_entry_list_model.test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file
no-tone-space-retry: 9 caught: test_conversion_text_dictionary_rules.test_a_row_is_a_rule_exactly_when_the_editor_shows_it, test_dialog_validation.test_a_final_first_tone_syllable_keeps_its_tone_space, test_dictionary_entries.test_a_final_first_tone_syllable_keeps_its_tone_space, test_dictionary_entries.test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space, and 5 more
entry-dialog-strips-the-tone-space: 1 caught: test_dialog_validation.test_a_final_first_tone_syllable_keeps_its_tone_space
loader-keeps-the-stripped-sequence: 7 caught: test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order, test_dictionary_entries.test_loader_shows_a_row_whose_last_syllable_is_first_tone, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entries.test_rows_carry_their_record_and_entries_still_compare_by_value, and 3 more
conversion-keeps-whitespace-texts: 4 caught: test_conversion_text_dictionary_rules.test_a_row_is_a_rule_exactly_when_the_editor_shows_it, test_conversion_text_dictionary_rules.test_apply_dictionary_gives_the_recorded_output_for_every_case, test_conversion_text_dictionary_rules.test_from_paths_gives_the_recorded_output_for_every_case, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules
conversion-validates-the-raw-target: 1 caught: test_conversion_text_dictionary_rules.test_a_row_is_a_rule_exactly_when_the_editor_shows_it
conversion-keeps-invalid-bopomofo: 4 caught: test_conversion_text_dictionary_rules.test_a_row_is_a_rule_exactly_when_the_editor_shows_it, test_conversion_text_dictionary_rules.test_apply_dictionary_gives_the_recorded_output_for_every_case, test_conversion_text_dictionary_rules.test_from_paths_gives_the_recorded_output_for_every_case, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules
conversion-without-the-tone-space-retry: 3 caught: test_conversion_text_dictionary_rules.test_a_row_is_a_rule_exactly_when_the_editor_shows_it, test_conversion_text_dictionary_rules.test_apply_dictionary_gives_the_recorded_output_for_every_case, test_conversion_text_dictionary_rules.test_from_paths_gives_the_recorded_output_for_every_case
rename-without-samefile: 1 caught: test_dictionary_name_prompt.test_rename_onto_another_file_under_another_case_is_refused
rename-refuses-the-same-file: 3 caught: test_dictionary_name_prompt.test_case_only_rename_still_renames, test_dictionary_presenter.test_rename_case_only_change_of_the_active_dictionary_activates_the_new_name, test_dictionary_presenter.test_rename_case_only_change_renames_file
import-wraps-destination-errors: 2 caught: test_dictionary_manager.test_import_copy_that_cannot_be_installed_keeps_its_permission_error, test_dictionary_presenter.test_import_copy_that_cannot_be_installed_shows_the_error
import-source-error-not-wrapped: 3 caught: test_dictionary_manager.test_import_source_that_cannot_be_opened_raises_the_import_source_error, test_dictionary_manager.test_import_source_that_cannot_be_read_after_the_check_raises_the_import_source_error, test_dictionary_presenter.test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason
import-source-error-raw-text: 1 caught: test_dictionary_presenter.test_import_source_that_cannot_be_opened_shows_the_cannot_open_reason
frame-builds-the-editor-before-loading: 2 caught: test_gui_document_flows.test_edit_result_opens_speech_symbols_for_presenter_path, test_gui_document_flows.test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback
build-error-described-as-unreadable: 1 caught: test_gui_document_flows.test_editor_that_cannot_be_built_shows_the_general_failure_and_logs_its_traceback
editor-reads-after-the-native-dialog: 2 caught: test_dictionary_entries_dialog.test_invalid_utf8_raises_from_the_constructor_before_the_native_dialog, test_dictionary_entries_dialog.test_the_dictionary_is_read_before_the_native_dialog_exists
build-failure-not-destroyed: 1 caught: test_dictionary_entries_dialog.test_a_failure_while_building_destroys_the_dialog_and_propagates
exit 0
```

### Task 12: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. The dry run built the same code (the tree of Task 10) and ran Step 2's scripts against it and against `N-f9b`; the blocks of Step 4 are those logs (see Dry Run). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*`, `N-f7`, `N-f8a*`, `N-f8b*`, `N-f9`, `N-f9b` (only read and copied by the scripts) or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f11`. Only processes whose exe lies under that folder are ended (`dx.kill_under`); `lockx.py` and `lock.py`, which the scripts start, are ended with `taskkill /T`. The user may have DotExpress open: never end any other process. No script writes to the clipboard: text reaches the app through files and `set_edit_text`, and keys go only to a window of the app under test while it is in the foreground (`f11gui.keys`, `f5gui.answer`).

**Fix and regression items** (user, 2026-10-11). A **fix** item is one whose expected result differs between the builds, or whose code path F-11 touches; any other item is a **regression** item. Fix items run on both builds (`N-f9b`, then `N-f11`); a regression item runs on `N-f11` only, and on `N-f9b` too only when it misses its expectation (that run is then reported). Every item of this task is a fix item: 95-106 expect different results on the two builds; the re-runs of 23-29 and 35 expect different results (the BOM, no write without a change, the hidden-rows box); 44 and 47 expect the same log on both builds, but they go through the editor's loading, which D12 changes. So there is no regression item and every item runs on both builds, as Step 3 does.

- [ ] **Step 1: Build** (PowerShell, in the worktree). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`; `scripts\build-dotexpress.bat` calls `pyinstaller` from `PATH` and assumes no venv of its own.

```powershell
Set-Location D:\workspace\DotExpress-f11
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f11-build.log 2>&1"
if (Select-String -Path $env:TEMP\f11-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "dialog.py", "dictionaries\\entries.py", "dictionaries\\entry_list_model.py", "dictionaries\\manager.py", "dictionaries\\presenter.py", "ui\\message_box.py", "conversion\\text\\dictionary_rules.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f11\\client\\$m" -Quiet) { "$m bundled from the worktree" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress-f11\\client\\gui.py" -Quiet) { "gui.py analyzed from the worktree" }
New-Item -ItemType Directory -Force D:\dxtest\N-f11 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f11\DotExpress.exe
(Get-Item D:\dxtest\N-f11\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f11\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f11-build.log`), the seven `bundled from the worktree` lines (printed with their doubled backslash), `gui.py analyzed from the worktree`, a size near 48.78 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). The `.mo` is bundled through `--add-data "locales;locales"`; items 95, 99, 103 and 105 show its new strings.

- [ ] **Step 2: Write the GUI scripts** into the new history folder with `apply_blocks.py` ("Task 12", "Step 2": 10 blocks). They reuse, unchanged, F-6's `f6gui.py` and `lockx.py`, F-7's `f7gui.py`, F-5's `f5gui.py` and `dx.py`, `docs.py`, `dicts.py`, `lock.py` and the data of `2026-10-09-03-windows-verification/auto/`. Scripts use tabs.

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/f11gui.py`

````python
"""Shared helpers for the F-11 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f6gui.py of F-6 (Dictionary Management, file and name dialogs, the
share-none lock lockx.py) and f7gui.py of F-7 (message boxes, which are task dialogs, read
and answered through UIA), and through them f5gui.py and dx.py, docs.py, dicts.py of the
2026-10-09-03 Windows verification. The dictionary editor and the entry dialog are wx
dialogs read through win32. Test dictionaries come from 2026-10-09-03/auto/data or are
built here; every item records the sha256, size and st_mtime_ns of each dictionary file.
No script touches the clipboard: text goes in with set_edit_text, and keys go only to a
window of the app under test while it is in the foreground (``keys``).
"""
import ctypes
import hashlib
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-10-03-f6-unreadable-dictionaries", "auto"))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-10-04-f7-dialog-buttons-surrogates-close", "auto"))
import f6gui as S  # noqa: E402  (puts 2026-10-09-03/auto on sys.path)
import f7gui as G  # noqa: E402  (puts F-5's auto folder on sys.path)
from f7gui import D, F, X, dx  # noqa: E402

DATA = os.path.join(HISTORY, "2026-10-09-03-windows-verification", "auto", "data")
F.KEYS.update({"alt-s": "%s", "alt-b": "%b", "alt-d": "%d"})
MGR = "字典管理"
EDITOR = "自訂字典管理器"
ADD_ENTRY = "新增字典項目"
EDIT_ENTRY = "編輯字典項目"
SETTINGS = "DotExpress 設定"
EM_GETSEL = 0x00B0
GW_OWNER = 4
BOM = b"\xef\xbb\xbf"


RANDOM_TMP = re.compile(r"(\.[\w.]+?\.csv\.)[A-Za-z0-9_]{8,16}(\.tmp)")


def data(name):
	with open(os.path.join(DATA, name), "rb") as stream:
		return stream.read()


def masked(d, value):
	"""``value`` as text, with the work folder as <d> and the random part of a temporary
	file name as <rnd>; a path inside an error message is a repr, so it can be escaped twice."""
	shown = value if isinstance(value, str) else repr(value)
	for form in (d.replace("\\", "\\" * 4), d.replace("\\", "\\" * 2), d):
		shown = shown.replace(form, "<d>")
	return RANDOM_TMP.sub(r"\1<rnd>\2", shown)


def dictionary(d, name=None):
	folder = S.dictionary(d)
	return folder if name is None else os.path.join(folder, f"{name}.csv")


def setup(exe, d, files=None):
	"""A new work folder ``d``: start once (the app creates dictionary\\default.csv), close,
	write ``files`` ({file name: bytes}) into dictionary\\ and start again. Returns (app, w)."""
	app, w = dx.launch(exe, d)
	print("first start, close:", D.close(app, w))
	for name, content in (files or {}).items():
		S.write(os.path.join(dictionary(d), name), content)
	print("dictionary:", files_state(d))
	return dx.launch(exe, d, fresh=False)


def state(path):
	"""(sha256 prefix, size, st_mtime_ns) of a file, or "missing"."""
	if not os.path.exists(path):
		return "missing"
	with open(path, "rb") as stream:
		content = stream.read()
	return (hashlib.sha256(content).hexdigest()[:16], len(content), os.stat(path).st_mtime_ns)


def files_state(d):
	"""{file name: (sha256 prefix, size)} of the dictionary folder (the time is kept apart)."""
	folder = dictionary(d)
	return {name: state(os.path.join(folder, name))[:2] for name in sorted(os.listdir(folder))}


def same(before, path):
	"""Whether the file still has the bytes and the modification time of ``before`` (state())."""
	now = state(path)
	return {"bytes": now[:2] == before[:2], "time": now[2:] == before[2:]}


def text(path):
	"""The file as text, the BOM shown as "<BOM>", so line ends and spaces are visible in a repr."""
	if not os.path.exists(path):
		return "missing"
	with open(path, "rb") as stream:
		content = stream.read()
	prefix = "<BOM>" if content.startswith(BOM) else ""
	return prefix + content[len(BOM) if prefix else 0:].decode("utf-8")


def manager(app, w):
	return X.windows(app, w).get(MGR) or S.open_mgr(app, w)


def close_manager(app, w):
	mgr = X.windows(app, w).get(MGR)
	if mgr is not None:
		X.close_mgr(app, w, mgr)


def count(app, w, name):
	return [row[1] for row in X.mgr_items(manager(app, w))[1] if row[0] == name]


def editor(app, w, name):
	return X.open_editor(app, w, manager(app, w), name)


def windows(app, w):
	return sorted(X.windows(app, w))


def keys(win, sequence, wait=1.0):
	"""Bring ``win`` (a window of the app under test) to the foreground and press ``sequence``."""
	import win32gui
	from pywinauto.keyboard import send_keys

	for _attempt in range(10):
		if win32gui.GetForegroundWindow() == win.handle:
			send_keys(sequence)
			time.sleep(wait)
			return
		win.set_focus()
		time.sleep(0.3)
	raise RuntimeError(f"{win.window_text()!r} is not in the foreground; {sequence!r} was not sent")


def button(win, *labels):
	return X.btn(win, *labels)


def press_button(win, *labels, wait=1.5):
	"""Focus a win32 button of an app dialog, then press it (BM_CLICK): the focus stays on
	the button, as after a click with the mouse."""
	target = button(win, *labels)
	target.set_focus()
	time.sleep(0.3)
	target.click()
	time.sleep(wait)


def focused():
	"""(control type, name) of the element that has the keyboard focus (UIA)."""
	from pywinauto.uia_defines import IUIA
	from pywinauto.uia_element_info import UIAElementInfo

	info = UIAElementInfo(IUIA().iuia.GetFocusedElement())
	return info.control_type, info.name


def open_boxes(app):
	"""The open message boxes of ``app`` as UIA wrappers: the task dialogs of
	ui.message_box.message_box and the generic dialogs of confirm_box (F-11), which are
	#32770 windows that hold no edit field or list."""
	from pywinauto import Desktop

	found = []
	for dialog in dx.dialogs(app):
		if dialog.window_text() in (MGR, EDITOR, ADD_ENTRY, EDIT_ENTRY):
			continue
		classes = {c.class_name() for c in dialog.wrapper_object().descendants()}
		if G.is_task_dialog(dialog) or not classes & {"Edit", "SysListView32", "ComboBox"}:
			found.append(Desktop(backend="uia").window(handle=dialog.handle))
	return found


def describe(found):
	"""What a screen reader gets from a box: f5gui.describe for a task dialog (title, main
	instruction, content, buttons, focus); for a generic dialog its title, its lines of
	text (one Text element each), buttons and focus. Plus the title of its owner window."""
	import win32gui

	if any(c.class_name() == "DirectUIHWND" for c in found.wrapper_object().children()):
		described = F.describe(found)
	else:
		found.set_focus()
		time.sleep(0.5)
		buttons = [
			b.window_text() for b in found.descendants(control_type="Button") if b.element_info.parent.control_type != "TitleBar"
		]
		described = {
			"title": found.window_text(),
			"text": [t.window_text() for t in found.descendants(control_type="Text")],
			"buttons": buttons,
			"focus": focused()[1],
		}
	owner = win32gui.GetWindow(found.handle, GW_OWNER)
	described["owner"] = win32gui.GetWindowText(owner) if owner else None
	return described


def box(app, timeout=5):
	"""(description, UIA wrapper) of the next message box, or (None, None) if none opens
	within ``timeout`` seconds."""
	end = time.time() + timeout
	while time.time() < end:
		found = open_boxes(app)
		if found:
			return describe(found[0]), found[0]
		time.sleep(0.3)
	return None, None


def answer(found, key):
	"""Press ``key`` (a key of f5gui.KEYS, or f5gui.CLOSE_BOX) in the box; f5gui.answer
	presses again if the key was lost. How often is left out of the logs."""
	F.answer(found, key)
	time.sleep(0.5)


def next_box(app, key, timeout=5):
	"""The next box, answered with ``key``; None if no box opens."""
	described, found = box(app, timeout)
	if found is not None:
		answer(found, key)
	return described


def entry_dialog(app, w, title, timeout=10):
	return X.wait_window(app, w, title, timeout)


def entry_fields(dialog):
	"""(source text, braille, type) as the entry dialog shows them."""
	controls = dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	combo = [c for c in controls if c.class_name() == "ComboBox"][0]
	return edits[0].window_text(), edits[1].window_text(), combo.selected_text()


def fill_entry(dialog, source, braille, type_label=None):
	controls = dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	edits[0].set_edit_text(source)
	edits[1].set_edit_text(braille)
	if type_label is not None:
		[c for c in controls if c.class_name() == "ComboBox"][0].select(type_label)


def source_selection(dialog):
	"""(start, end) of the selection in the entry dialog's source text field (EM_GETSEL)."""
	edit = [c for c in dialog.wrapper_object().descendants() if c.class_name() == "Edit"][0]
	start, end = ctypes.c_ulong(), ctypes.c_ulong()
	ctypes.windll.user32.SendMessageW(edit.handle, EM_GETSEL, ctypes.byref(start), ctypes.byref(end))
	return start.value, end.value


def select_row(ed, index):
	"""Select row ``index`` of the editor's list and put the focus in the list."""
	rows = [c for c in ed.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	rows.get_item(index).select()
	rows.set_focus()
	time.sleep(0.5)


def convert(app, w, word):
	"""Convert ``word`` in the open document: the Braille Result text without its trailing
	blank cells (U+2800), and the boxes shown."""
	close_manager(app, w)
	D.set_input(w, word)
	output, shown = X.convert(app, w)
	return output.rstrip(chr(0x2800)), shown


def set_dictionary(app, w, name):
	close_manager(app, w)
	X.set_dictionary(app, w, name)


def config_dictionary(d):
	"""conversion.selected_dictionary in config.json."""
	import json

	path = os.path.join(d, "config.json")
	with open(path, encoding="utf-8") as stream:
		return json.load(stream).get("conversion", {}).get("selected_dictionary")


def finish(app, w, d):
	S.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item95.py`

````python
"""Items 95 and 96 (F-11 D1, D13): dict_badbopo.csv and the box that lists its hidden rows.

Usage: python item95.py <exe> <work folder>
Import dict_badbopo.csv (2026-10-09-03 data: 臺北 and two Bopomofo rows that do not
parse). 96: select it in Settings and convert 肚子數學, and the same with the default
dictionary. 95: open the editor and press OK (the button has the focus): the box; Esc
in it; OK again, Enter; OK again, Alt+F4; each time the editor, the file and the focus.
Then OK and Alt+S (Remove and Save): the file and the count. 96 again: the conversion.
Before F-11 (N-f9b) there is no box: OK closes the editor and keeps the file (F-4), so
each step reopens the editor.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAME = "dict_badbopo"
WORD = "肚子數學"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d)
source = os.path.join(d, "data", "dict_badbopo.csv")
H.S.write(source, H.data("dict_badbopo.csv"))
path = H.dictionary(d, NAME)
print("95 import:", H.S.import_as(app, w, H.manager(app, w), source, NAME))
print("95 imported identical:", H.state(path)[:2] == H.state(source)[:2], "count:", H.count(app, w, NAME))
H.close_manager(app, w)
H.D.select(w, "new")
H.set_dictionary(app, w, NAME)
first = H.convert(app, w, WORD)
H.set_dictionary(app, w, "default")
default = H.convert(app, w, WORD)
print("96 before the save:", repr(first[0]), first[1], "| default:", repr(default[0]), "| equal:", first[0] == default[0])


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, NAME)


before = H.state(path)
for label, key in (("95a Esc", "esc"), ("95b Enter", "enter"), ("95c Alt+F4", "alt-f4")):
	ed = editor()
	if label.startswith("95a"):
		print("95 rows:", H.X.editor_rows(ed))
	H.press_button(ed, "確定")
	described = H.next_box(app, key)
	print(f"{label}: box {described}")
	print(f"{label}: windows {H.windows(app, w)} file {H.same(before, path)} focus {H.focused()}")
ed = editor()
H.press_button(ed, "確定")
print("95d Alt+S: box", H.next_box(app, "alt-s"))
print("95d Alt+S: windows", H.windows(app, w), "file", repr(H.text(path)), "count:", H.count(app, w, NAME))
H.set_dictionary(app, w, NAME)
second = H.convert(app, w, WORD)
print("96 after the save:", repr(second[0]), second[1], "| equal to default:", second[0] == default[0], "| equal to before:", second[0] == first[0])
H.set_dictionary(app, w, "default")
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item97.py`

````python
"""Items 97 and 98 (F-11 D4, D5): OK writes only after a change and keeps the file's layout.

Usage: python item97.py <exe> <work folder>
extra.csv: a BOM, the header text,note,braille,type, a row with spaces around its fields
and the type Custom, CRLF. 97: open it, OK: no box, the file keeps its bytes and its
modification time. 98: open it, edit row 1's braille (⠁ to ⠁⠁), add Gamma / ⠛, OK: the
BOM, the header and the notes stay, the new row's note is empty, every row is stripped
and Custom is written as General. The same edit on bom_lf.csv (2026-10-09-03 data: a BOM
and LF line ends): the BOM stays, the line ends become CRLF.
Before F-11 (N-f9b): every OK rewrites the file without the BOM and drops the note column.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

EXTRA = H.BOM + "text,note,braille,type\r\n Alpha ,first, ⠁ ,Custom\r\nBeta,second,⠃,General\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"extra.csv": EXTRA, "bom_lf.csv": H.data("bom_lf.csv")})


def edit_first_row(ed, braille):
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	print("   entry dialog shows:", H.entry_fields(dialog))
	source, _braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")


def add_row(ed, source, braille):
	H.press_button(ed, "新增")
	dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")


path = H.dictionary(d, "extra")
before = H.state(path)
ed = H.editor(app, w, "extra")
print("97 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("97 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("97 file:", H.same(before, path), repr(H.text(path)))

ed = H.editor(app, w, "extra")
edit_first_row(ed, "⠁⠁")
add_row(ed, "Gamma", "⠛")
print("98 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("98 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("98 extra.csv:", repr(H.text(path)))

path = H.dictionary(d, "bom_lf")
ed = H.editor(app, w, "bom_lf")
print("98 bom_lf rows:", H.X.editor_rows(ed))
edit_first_row(ed, "⠑⠋⠁")
H.press_button(ed, "確定")
print("98 bom_lf OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("98 bom_lf.csv:", repr(H.text(path)))
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item99.py`

````python
"""Items 99 and 100 (F-11 D3, D7): Cancel, Esc and the close box ask only after a change.

Usage: python item99.py <exe> <work folder>
alpha.csv holds two rows. 99: open it, add x / ⠭; press Esc in the editor: the box, Esc
in it; press Cancel (the button has the focus): the box, its close box; press Alt+F4 in
the editor: the box, Alt+D (Discard Changes). Each time the editor, its rows and the focus.
100: open alpha, Esc (no change): it closes at once. Open it again, delete row 1 (no
box), Cancel: the box, Alt+D. The file never changes.
Before F-11 (N-f9b): Esc, Cancel and Alt+F4 close the editor at once; x is lost.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ALPHA = "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"alpha.csv": ALPHA})
path = H.dictionary(d, "alpha")
before = H.state(path)


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, "alpha")


def report(label):
	ed = H.X.windows(app, w).get(H.EDITOR)
	rows = H.X.editor_rows(ed) if ed is not None else None
	print(f"{label}: windows {H.windows(app, w)} rows {rows} focus {H.focused()} file {H.same(before, path)}")


ed = editor()
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "x", "⠭")
H.press_button(dialog, "確定")
print("99 rows:", H.X.editor_rows(ed))
H.select_row(ed, 2)
H.keys(ed, "{ESC}")
print("99 Esc in the editor: box", H.next_box(app, "esc"))
report("99 after Esc in the box")
ed = editor()
H.press_button(ed, "取消")
print("99 Cancel: box", H.next_box(app, H.F.CLOSE_BOX))
report("99 after the close box of the box")
ed = editor()
H.keys(ed, "%{F4}")
print("99 Alt+F4 in the editor: box", H.next_box(app, "alt-d"))
report("99 after Alt+D")

ed = editor()
H.select_row(ed, 0)
H.keys(ed, "{ESC}")
print("100 Esc without a change: box", H.next_box(app, "esc", timeout=3))
report("100 after Esc")
ed = editor()
H.select_row(ed, 0)
H.press_button(ed, "刪除")
print("100 Delete: box", H.next_box(app, "esc", timeout=3), "rows", H.X.editor_rows(ed))
H.press_button(ed, "取消")
print("100 Cancel: box", H.next_box(app, "alt-d"))
report("100 after Alt+D")
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item101.py`

````python
"""Items 101 and 102 (F-11 D8, D9): duplicates in the entry dialog; the selected twin.

Usage: python item101.py <exe> <work folder>
twins.csv: text,braille,type,note / a,⠁,General,first / b,⠃,General, / a,⠁,General,third.
101: Add b / ⠃: the box, its owner; after Enter the entry dialog with its fields, the
focus and the selection of the source text; then c, OK: added. Cancel, Alt+D.
102: (1) select row 3, Edit, braille ⠉, OK: the rows; Cancel, Alt+D. (2) Open it again,
select row 3, Delete, OK: the file.
Before F-11 (N-f9b): the entry dialog closes, then the editor shows the box and the input
is lost; the Edit of row 3 is refused; Delete removes row 1 (the first equal row).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

TWINS = "text,braille,type,note\r\na,⠁,General,first\r\nb,⠃,General,\r\na,⠁,General,third\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"twins.csv": TWINS})
path = H.dictionary(d, "twins")
before = H.state(path)


def entry_state(title):
	dialog = H.X.windows(app, w).get(title)
	if dialog is None:
		return "closed"
	return f"open, fields {H.entry_fields(dialog)}, focus {H.focused()}, selection {H.source_selection(dialog)}"


def discard():
	ed = H.X.windows(app, w).get(H.EDITOR)
	if ed is None:
		return "no editor"
	H.press_button(ed, "取消")
	return H.next_box(app, "alt-d", timeout=3)


ed = H.editor(app, w, "twins")
print("101 rows:", H.X.editor_rows(ed))
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "b", "⠃")
H.press_button(dialog, "確定")
print("101 OK with b: box", H.next_box(app, "enter"))
print("101 entry dialog:", entry_state(H.ADD_ENTRY))
dialog = H.X.windows(app, w).get(H.ADD_ENTRY)
if dialog is not None:
	H.fill_entry(dialog, "c", "⠉")
	H.press_button(dialog, "確定")
	print("101 OK with c: box", H.next_box(app, "enter", timeout=3), "entry dialog", entry_state(H.ADD_ENTRY))
print("101 rows:", H.X.editor_rows(H.X.windows(app, w)[H.EDITOR]))
print("101 Cancel: box", discard(), "windows", H.windows(app, w), "file", H.same(before, path))

ed = H.editor(app, w, "twins")
H.select_row(ed, 2)
H.press_button(ed, "編輯")
dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
print("102 entry dialog shows:", H.entry_fields(dialog))
H.fill_entry(dialog, "a", "⠉")
H.press_button(dialog, "確定")
print("102 (1) OK: box", H.next_box(app, "enter", timeout=3), "entry dialog", entry_state(H.EDIT_ENTRY))
dialog = H.X.windows(app, w).get(H.EDIT_ENTRY)
if dialog is not None:
	H.press_button(dialog, "取消")
print("102 (1) rows:", H.X.editor_rows(H.X.windows(app, w)[H.EDITOR]))
print("102 (1) Cancel: box", discard(), "windows", H.windows(app, w), "file", H.same(before, path))
ed = H.editor(app, w, "twins")
H.select_row(ed, 2)
H.press_button(ed, "刪除")
print("102 (2) rows after Delete:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("102 (2) OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("102 (2) twins.csv:", repr(H.text(path)))
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item103.py`

````python
"""Items 103 and 106 (F-11 D2, D1, D14): adding entries in dictionaries with special rows.

Usage: python item103.py <exe> <work folder>
103: dict_badbopo (2026-10-09-03 data): Add 肚子 / ㄉㄨˋㄗ˙ / 注音; OK; Alt+S: the file.
106: tone1.csv holds 中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo (its last syllable is first tone): the
rows; Add 抹 / ㄇㄚ / 注音, typed without the tone space; OK: the file. Then convert
中心抹 with tone1 and with the default dictionary (both readings differ from the
default conversion, so the output shows that both rules are used).
Before F-11 (N-f9b): 103's Add is refused as a duplicate (F-4 D5); 106's row is hidden
and the Add shows the format error.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

TONE1 = "text,braille,type\r\n中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"dict_badbopo.csv": H.data("dict_badbopo.csv"), "tone1.csv": TONE1})


def add(ed, source, braille, type_label):
	"""Add through the real entry dialog: the box after OK (answered with Enter) and
	whether the entry dialog is still open (then it is cancelled)."""
	H.press_button(ed, "新增")
	dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
	H.fill_entry(dialog, source, braille, type_label)
	H.press_button(dialog, "確定")
	shown = H.next_box(app, "enter", timeout=3)
	still = H.X.windows(app, w).get(H.ADD_ENTRY)
	if still is not None:
		H.press_button(still, "取消")
	return shown, still is not None


path = H.dictionary(d, "dict_badbopo")
ed = H.editor(app, w, "dict_badbopo")
print("103 add:", add(ed, "肚子", "ㄉㄨˋㄗ˙", "注音"))
print("103 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("103 OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("103 dict_badbopo.csv:", repr(H.text(path)))

path = H.dictionary(d, "tone1")
ed = H.editor(app, w, "tone1")
print("106 rows:", H.X.editor_rows(ed))
print("106 add:", add(ed, "抹", "ㄇㄚ", "注音"))
print("106 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("106 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("106 tone1.csv:", repr(H.text(path)))
H.D.select(w, "new")
H.set_dictionary(app, w, "tone1")
with_tone1 = H.convert(app, w, "中心抹")
H.set_dictionary(app, w, "default")
default = H.convert(app, w, "中心抹")
print("106 convert 中心抹 with tone1:", repr(with_tone1[0]), with_tone1[1], "| default:", repr(default[0]))
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item104.py`

````python
"""Items 104 and 105 (F-11 D10, D11): a case-only rename; an Import source that is locked.

Usage: python item104.py <exe> <work folder>
104: select alpha in Settings; Dictionary Management, Rename alpha to Alpha: the boxes,
the list, the files, config.json; convert 甲乙 (alpha has 甲乙,⠁⠃,Braille).
105: Import data\\src.csv; once the file dialog has closed, lockx.py holds it without
sharing; name it src: the box; the files.
Before F-11 (N-f9b): 104 shows 字典「Alpha」已存在。 and the name dialog again (it is
cancelled); 105 shows the raw [Errno 13].
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ALPHA = "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"alpha.csv": ALPHA})
H.D.select(w, "new")
H.set_dictionary(app, w, "alpha")
print("104 config before:", H.config_dictionary(d))
mgr = H.manager(app, w)
H.X.mgr_select(mgr, "alpha")
H.S.click(mgr, "重新命名", wait=0.5)
print("104 rename: boxes", H.S.name_dialog(app, w, "重新命名字典", "Alpha"))
again = H.X.windows(app, w).get("重新命名字典")
if again is not None:
	print("104 the name dialog is open again; cancelled")
	H.press_button(again, "取消")
print("104 list:", H.S.rows(H.manager(app, w)))
print("104 files:", sorted(os.listdir(H.dictionary(d))), "config:", H.config_dictionary(d))
H.close_manager(app, w)
print("104 convert 甲乙:", repr(H.convert(app, w, "甲乙")[0]))

source = os.path.join(d, "data", "src.csv")
H.S.write(source, ALPHA)
mgr = H.manager(app, w)
H.S.click(mgr, "匯入", wait=0.5)
H.S.file_dialog(app, w, "匯入字典", source)
# The file dialog does not open a file that no one may share, so the lock comes after it,
# as when another program takes the file while the name is typed.
holder = H.S.lock_none(source)
try:
	print("105 import: boxes", [H.masked(d, shown) for shown in H.S.name_dialog(app, w, "新增字典", "src")])
finally:
	H.S.unlock(holder)
print("105 list:", H.S.rows(H.manager(app, w)))
print("105 files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/rerun23.py`

````python
"""Items 23 and 24 again (F-11 D4, D5): OK without a change writes nothing; an edit is
written with the file's BOM.

Usage: python rerun23.py <exe> <work folder>
The 2026-10-09-03 data, imported through Dictionary Management: dict23 (no BOM, CRLF) and
bom_excel, bom_notepad, bom_lf (a BOM; bom_lf has LF line ends). For each: the count, the
rows, OK without a change (the file keeps its bytes and its modification time), then an
edit of row 1's braille (the cell ⠿ added) and OK: the file. Then 24's conversions with
each dictionary selected in Settings.
Before F-11 (N-f9b): every OK rewrites the file, without the BOM.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAMES = ("dict23", "bom_excel", "bom_notepad", "bom_lf")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d)
for name in NAMES:
	source = os.path.join(d, "data", f"{name}.csv")
	H.S.write(source, H.data(f"{name}.csv"))
	print(name, "import:", H.S.import_as(app, w, H.manager(app, w), source, name), "count:", H.count(app, w, name))
	path = H.dictionary(d, name)
	before = H.state(path)
	ed = H.editor(app, w, name)
	rows = H.X.editor_rows(ed)
	print(name, "rows:", rows)
	H.press_button(ed, "確定")
	print(name, "OK without a change: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w), "file", H.same(before, path))
	ed = H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, name)
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	source_text, braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source_text, braille + "⠿")
	H.press_button(dialog, "確定")
	H.press_button(ed, "確定")
	print(name, "OK after the edit: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
	print(name, "file:", repr(H.text(path)))
H.close_manager(app, w)
H.D.select(w, "new")
for name, word, cells in (("default", "甲乙丙丁", None), ("bom_excel", "甲乙", "⠁⠃⠿"), ("bom_notepad", "丙丁", "⠉⠙⠿"), ("bom_lf", "戊己", "⠑⠋⠿")):
	H.set_dictionary(app, w, name)
	output, shown = H.convert(app, w, word)
	print("24 convert with", name, repr(word), "->", repr(output), "uses the dictionary:", (cells in output) if cells else "-", shown)
H.set_dictionary(app, w, "default")
print("files:", H.files_state(d))
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/rerun25.py`

````python
"""Items 25 to 29 again (F-11 D4, D5): each OK follows an edit, so that OK writes.

Usage: python rerun25.py <exe> <work folder>
bom_lf.csv (2026-10-09-03 data: a BOM, LF) is reset before each item; an edit sets row
1's braille (⠑⠋ to ⠑⠋⠁, in 28 alternately ⠑⠋⠁ and ⠑⠋⠃) and OK saves. 25: the file is
held open with share read (lock.py); OK; unlock; OK. 26: read-only (attrib +r); OK; -r;
OK. 27: hidden (+h); OK. 28: ten edits and OKs with Defender on. 29: icacls denies the
user writing (WD,AD,WEA,WA); OK; the deny entry is removed again.
The state of the file: ORIG (as reset), SAVED(<braille>) (a BOM, CRLF, the edit) or OTHER.
Before F-11 (N-f9b): SAVED has no BOM, so the state shows OTHER.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ORIG = H.data("bom_lf.csv")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"bom_lf.csv": ORIG})
P = H.dictionary(d, "bom_lf")


def state():
	with open(P, "rb") as stream:
		content = stream.read()
	if content == ORIG:
		kind = "ORIG"
	else:
		kind = f"OTHER {H.masked(d, H.text(P))!r}"
		for braille in ("⠑⠋⠁", "⠑⠋⠃"):
			if content == H.BOM + f"text,braille,type\r\n戊己,{braille},Braille\r\n".encode("utf-8"):
				kind = f"SAVED({braille})"
	return kind, sorted(os.listdir(H.dictionary(d)))


def attrib():
	return subprocess.run(["cmd", "/c", "attrib", P], capture_output=True, text=True).stdout.strip().replace(P, "<file>")


def reset():
	subprocess.run(["attrib", "-r", "-h", P])
	with open(P, "wb") as stream:
		stream.write(ORIG)


def edit(braille):
	"""Open the editor and set row 1's braille; the editor stays open."""
	ed = H.editor(app, w, "bom_lf")
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	source, _braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")
	return ed


def ok(label):
	"""Press OK in the open editor; print the box (answered with Enter), whether the editor
	is still open and the state. Returns whether it is still open."""
	ed = H.X.windows(app, w)[H.EDITOR]
	H.press_button(ed, "確定")
	shown = H.next_box(app, "enter", timeout=3)
	still = H.EDITOR in H.windows(app, w)
	print(label, "box:", H.masked(d, shown), "editor open:", still, "state:", state())
	return still


def cancel():
	ed = H.X.windows(app, w).get(H.EDITOR)
	if ed is not None:
		H.press_button(ed, "取消")
		H.next_box(app, "alt-d", timeout=3)


# 25: held open by another program with share read (Excel)
reset()
edit("⠑⠋⠁")
holder = H.F.lock(P, "r")
still = ok("25 locked:")
H.F.unlock(holder)
if still:
	ok("25 after unlock:")
cancel()
# 26: read-only
reset()
subprocess.run(["attrib", "+r", P])
edit("⠑⠋⠁")
still = ok("26 +r:")
subprocess.run(["attrib", "-r", P])
if still:
	ok("26 after -r:")
print("26 attrib:", attrib())
cancel()
# 27: hidden
reset()
subprocess.run(["attrib", "+h", P])
edit("⠑⠋⠁")
ok("27 +h:")
print("27 attrib:", attrib())
cancel()
subprocess.run(["attrib", "-h", P])
# 28: ten saves with Defender's real-time protection on
reset()
failures = 0
for index in range(10):
	braille = ("⠑⠋⠁", "⠑⠋⠃")[index % 2]
	edit(braille)
	ed = H.X.windows(app, w)[H.EDITOR]
	H.press_button(ed, "確定")
	shown = H.next_box(app, "enter", timeout=2)
	kind, files = state()
	if shown or H.EDITOR in H.windows(app, w) or kind != f"SAVED({braille})" or any(name.endswith(".tmp") for name in files):
		failures += 1
		print("28 iteration", index + 1, H.masked(d, shown), kind, files)
		cancel()
print("28 failures:", failures, "state:", state())
# 29: the user may not write the file (F-W13)
reset()
user = os.environ["USERNAME"]
print("29 icacls deny:", subprocess.run(["icacls", P, "/deny", f"{user}:(WD,AD,WEA,WA)"], capture_output=True, text=True).stdout.strip().splitlines()[0].replace(P, "<file>"))
print("29 deny entries before:", "DENY" in subprocess.run(["icacls", P], capture_output=True, text=True).stdout.upper())
edit("⠑⠋⠁")
ok("29 deny:")
print("29 deny entries left:", "DENY" in subprocess.run(["icacls", P], capture_output=True, text=True).stdout.upper())
subprocess.run(["icacls", P, "/remove:d", user], capture_output=True)
cancel()
H.close_manager(app, w)
print("close:", H.D.close(app, w))
print("final:", state(), attrib())
H.dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item35.py`

````python
"""Item 35 again (F-11 D1, D2, D13): dict_badbopo.csv through Dictionary Management and the editor.

Usage: python item35.py <exe> <work folder>
As F-4's item 35, with the expectations of F-11. Import dict_badbopo.csv (2026-10-09-03
data); convert 肚子數學 with it. 35a: OK: the box lists the two hidden rows; Back to
Editing (Alt+B) keeps the file; OK again, Remove and Save (Alt+S): 臺北 only; convert
again. 35b: Add 肚子 / ㄉㄨˋㄗ˙ / 注音: accepted; OK: written. 35c: delete 臺北, OK; the
count. 35d: restart: the count and the rows; Cancel.
Before F-11 (N-f9b, F-4): no box, the file is kept; the Add is refused; the hidden rows
stay through 35c and 35d.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAME = "dict_badbopo"
WORD = "肚子數學"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d)
source = os.path.join(d, "data", "dict_badbopo.csv")
H.S.write(source, H.data("dict_badbopo.csv"))
path = H.dictionary(d, NAME)
print("import:", H.S.import_as(app, w, H.manager(app, w), source, NAME), "count:", H.count(app, w, NAME))
H.close_manager(app, w)
H.D.select(w, "new")
H.set_dictionary(app, w, NAME)
first = H.convert(app, w, WORD)
print("convert 1:", repr(first[0]), first[1])


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, NAME)


before = H.state(path)
ed = editor()
print("35a rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35a OK: box", H.next_box(app, "alt-b", timeout=3))
print("35a after Alt+B: windows", H.windows(app, w), "file", H.same(before, path))
ed = editor()
H.press_button(ed, "確定")
print("35a OK again: box", H.next_box(app, "alt-s", timeout=3) is not None, "windows", H.windows(app, w))
print("35a file:", repr(H.text(path)), "files:", sorted(os.listdir(H.dictionary(d))))
second = H.convert(app, w, WORD)
print("35a convert 2:", repr(second[0]), "same as convert 1:", second[0] == first[0])

ed = editor()
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "肚子", "ㄉㄨˋㄗ˙", "注音")
H.press_button(dialog, "確定")
print("35b add: box", H.next_box(app, "enter", timeout=3), "entry dialog open:", H.ADD_ENTRY in H.windows(app, w))
print("35b rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35b OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("35b file:", repr(H.text(path)))

ed = editor()
H.select_row(ed, 0)
H.press_button(ed, "刪除")
print("35c rows after delete:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35c OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("35c file:", repr(H.text(path)), "count:", H.count(app, w, NAME))
H.close_manager(app, w)
print("close:", H.D.close(app, w))

app, w = H.dx.launch(EXE, d, fresh=False)
print("35d count:", H.count(app, w, NAME))
ed = editor()
print("35d rows:", H.X.editor_rows(ed))
H.press_button(ed, "取消")
print("35d Cancel: box", H.next_box(app, "alt-d", timeout=3), "windows", H.windows(app, w))
print("35d file:", repr(H.text(path)), "files:", sorted(os.listdir(H.dictionary(d))))
H.finish(app, w, d)
````

- [ ] **Step 3: The items on both builds** (Git Bash, from the repository root): first `D:\dxtest\N-f9b\DotExpress.exe` ("Before", folders `auto<N>-f9b-f11`), then the new build (folders `auto<N>-f11`). Each script deletes its work folder first (after ending any process under it), copies the exe into it, starts it once so that it creates `dictionary\default.csv`, closes it, writes its test files and starts it again. Items 44 and 47 are run with F-6's `item42.py` (42-45) and `item47.py`, unchanged. Read each log against Step 4 before the next run. The whole loop takes about 30 minutes.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto
F6=docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto
export PYTHONIOENCODING=utf-8
cd $REPO
for build in N-f9b N-f11; do
  tag=$([ $build = N-f9b ] && echo -f9b-f11 || echo -f11)
  for s in item95 item97 item99 item101 item103 item104 rerun23 rerun25 item35; do n=${s#item}; "$UIA" $H/$s.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$n$tag > /d/dxtest/auto$n$tag.log 2>&1; done
  "$UIA" $F6/item42.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto44$tag > /d/dxtest/auto44$tag.log 2>&1
  "$UIA" $F6/item47.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto47$tag > /d/dxtest/auto47$tag.log 2>&1
done
```

- [ ] **Step 4: Expected behaviour.** Each log must show the behaviour of its item below (the run of this plan's execution is the only run; its logs are quoted in `auto-results.md`). A box is read through UIA: a task dialog (`ui.message_box`) as `{'title', 'main', 'content', 'buttons', 'focus', 'owner'}` (a message without a blank line has no main instruction, so `main` is `None`), a generic dialog (`confirm_box`, F-11) as `{'title', 'text': [one entry per line], 'buttons', 'focus', 'owner'}`; `owner` is the title of the window that owns the box; how often a key had to be pressed is left out. `focus` is read from the system's focused element half a second after the box is brought forward, and `focus (...)` after a box from the focused element then; a notification of another program can show up there instead (a tool artifact: note it and run that item again in a new folder). A file is shown as text, a BOM as `<BOM>`; `{'bytes': ..., 'time': ...}` says whether a file kept its bytes and its modification time; `<d>` is the work folder, `<rnd>` the random part of a temporary file name. Item 47's `gui.log` line names its work folder as it is. If a key or a click goes to another window (a pywinauto `RuntimeError` from `f11gui.keys`, or a box that never opens), that is a tool problem: run the item again in a new folder and record it.

- **95, 96** (D1, D13). Import `dict_badbopo.csv`; conversion of `肚子數學` with it and with `default`; in the editor OK (the button has the focus): the generic box `移除無法顯示的列` lists rows 3 and 4 (the start lines of their records) between the lead-in and the question, the buttons `移除並儲存(S)` / `返回編輯(B)`, the focus on `返回編輯(B)`, owned by the editor. Esc, Enter and Alt+F4 in the box each leave the editor open, the file with its bytes and time, and the focus back on `確定`. Alt+S: the editor closes and the file holds `臺北` only; the count stays 1. Both conversions equal `default`'s (the two hidden rows are not rules, D13). Before: no box; OK closes the editor and rewrites the file with the same bytes (F-4; a new time), and both conversions use the two Bopomofo rules (`⠙⠌⠐⠳...`), so they differ from `default`'s. Logs: `D:\dxtest\auto95-f11.log`, `D:\dxtest\auto95-f9b-f11.log`.
- **97, 98** (D4, D5). `extra.csv` (a BOM, a note column, a row with spaces and the type Custom): OK without a change writes nothing (bytes and time kept). After an Edit of row 1 and an Add, the file keeps its BOM, header and notes, the new row's note is empty, every row is stripped and Custom is written as General. `bom_lf.csv` (a BOM, LF): after an edit it keeps the BOM and gets CRLF (Spec Corrections 12). Before: every OK rewrites the file without the BOM and drops the note column. Logs: `D:\dxtest\auto97-f11.log`, `D:\dxtest\auto97-f9b-f11.log`.
- **99, 100** (D3, D7). After an Add, Esc in the editor, Cancel and Alt+F4 in the editor each show the generic box `尚未儲存的變更` (`要放棄對字典「alpha」所做的變更嗎？`, `放棄變更(D)` / `返回編輯(B)`, the focus on `返回編輯(B)`); Esc and the box's close box return to the editor with the row kept and the focus where it was (the list, then `取消`); Alt+D closes the editor; the file never changes. Without a change Esc closes at once; Delete asks nothing; Cancel after it shows the box. Before: Esc, Cancel and Alt+F4 close the editor at once. Logs: `D:\dxtest\auto99-f11.log`, `D:\dxtest\auto99-f9b-f11.log`.
- **101, 102** (D8, D9). Add `b`: the task dialog `來源文字「b」已存在。` owned by `新增字典項目`; after Enter the entry dialog is still open with `b` and `⠃`, the focus in `來源文字` and `b` selected (0, 1); `c` is then added. Edit of row 3 keeping `a` is accepted. Delete of row 3 and OK: the file keeps rows 1 and 2 and row 1's note `first`. Before: the box belongs to the editor after the entry dialog closed and the input is lost; the Edit is refused; Delete removes the first `a`, and the note column is dropped. Logs: `D:\dxtest\auto101-f11.log`, `D:\dxtest\auto101-f9b-f11.log`.
- **103, 106** (D2, D1, D14). `dict_badbopo`: Add `肚子` / `ㄉㄨˋㄗ˙` is accepted; OK shows the box with rows 3 and 4; Alt+S writes `臺北` and the new `肚子` row. `tone1.csv`: the row `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` is shown with its tone space; Add `抹` / `ㄇㄚ` is accepted and saved as `ㄇㄚ `; converting `中心抹` with `tone1` uses both readings (`⠁⠯⠐...⠍⠜⠄` against `default`'s `⠁⠯⠄...⠍⠣⠈`). Before: the Add of `肚子` is refused (F-4 D5) and OK keeps the file; the `中心` row is hidden, the Add shows the format error `請輸入有效的注音序列。` in the entry dialog, and only the `中心` rule is used. Logs: `D:\dxtest\auto103-f11.log`, `D:\dxtest\auto103-f9b-f11.log`.
- **104, 105** (D10, D11). `alpha` selected in Settings, renamed to `Alpha`: no box, the list shows `Alpha` selected, `Alpha.csv`, `config.json` follows, a conversion uses it. Import of a source locked without sharing after the file dialog: `匯入字典失敗：無法開啟檔案。…` and nothing copied. Before: `字典「Alpha」已存在。` and the name dialog again (cancelled); the Import shows `[Errno 13] Permission denied: ...`. Logs: `D:\dxtest\auto104-f11.log`, `D:\dxtest\auto104-f9b-f11.log`.
- **23, 24 again** (D4, D5). `dict23`, `bom_excel`, `bom_notepad`, `bom_lf` imported: OK without a change keeps bytes and time; an edit of row 1 (`⠿` added) is written with the file's BOM (dict23 has none), CRLF; the conversions use each dictionary. Before: every OK rewrites the file without the BOM. Logs: `D:\dxtest\autorerun23-f11.log`, `D:\dxtest\autorerun23-f9b-f11.log`.
- **25-29 again** (D4, D5; the F-2 write path). Each item edits row 1 first. 25: held open with share read, the save error (the editor stays, the file `ORIG`, no `.tmp`), after the unlock `SAVED(⠑⠋⠁)` with the BOM. 26: read-only, the error, after `-r` saved. 27: hidden, saved (the attribute goes, as before). 28: ten saves with Defender, no failure. 29: the deny entry is there before, the save replaces the file and the entry is gone. Before: the same messages, but every saved file lacks the BOM (`OTHER`), so 28 counts ten failures of this script's check (each save itself works). Logs: `D:\dxtest\autorerun25-f11.log`, `D:\dxtest\autorerun25-f9b-f11.log`.
- **35 again** (D1, D2, D13). 35a: OK shows the box (rows 3, 4); Alt+B keeps the file; OK and Alt+S leave `臺北` only; the conversion is the same before and after (the hidden rows were not rules). 35b: Add `肚子` is accepted and written. 35c: Delete `臺北`, OK: `肚子` only, count 1. 35d: after a restart count 1, the row, Cancel closes without a box. Before (F-4): no box, the file keeps the hidden rows, the Add is refused, 35c leaves the two hidden rows (count 0). Logs: `D:\dxtest\auto35-f11.log`, `D:\dxtest\auto35-f9b-f11.log`.
- **44 again** (F-6's `item42.py`, 42-45; the editor now reads before its window exists, D12): the same log on both builds: the unreadable `big5` row, its reason, the error box on 編輯 with Dictionary Management staying open, and the editor opening once the file is UTF-8. Logs: `D:\dxtest\auto44-f11.log`, `D:\dxtest\auto44-f9b-f11.log`.
- **47 again** (F-6's `item47.py`): the same log on both builds apart from the folder name in the `gui.log` line: after the unlock 編輯 opens the editor with the row. Logs: `D:\dxtest\auto47-f11.log`, `D:\dxtest\auto47-f9b-f11.log`.

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto-results.md` in the style of `2026-10-10-07-f9-conversion-target-document/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the method, then one row per item (95-106, then 23-29, 35, 44, 47) with ✔/△/✘, the observed boxes, editors and files after F-11 and the "Before" observations on N-f9b. Any deviation from Step 4 is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 107, worded for the user (do not mark it done):

  > 107（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f11\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual107-f11\`，執行一次後關閉，把 `docs\superpowers\history\2026-10-09-03-windows-verification\auto\data\dict_badbopo.csv` 與 `alpha.csv`（`text,braille,type` / `甲乙,⠁⠃,Braille` / `丙丁,⠉⠙,Braille`）複製到 `D:\dxtest\manual107-f11\dictionary\`，再執行 DotExpress，開啟「字典管理」。(1) 編輯 `dict_badbopo`，按「確定」：「移除無法顯示的列」對話框是否讀出整段說明與兩列（第 3 列、第 4 列），焦點是否在「返回編輯」；按 Esc 後焦點回到哪裡。(2) 編輯 `alpha`，新增一筆後按 Esc：「尚未儲存的變更」對話框是否讀出問題與兩個按鈕；按 Esc 後是否回到編輯器、焦點在哪裡；再按 Alt+F4，在對話框中按 Alt+D 放棄變更。(3) 在 `alpha` 新增 `甲乙`（已存在）：「來源文字「甲乙」已存在。」之後，是否回到「新增字典項目」並讀出「來源文字」欄位與選取的文字。(4) 回到 (1) 按「移除並儲存」之後，焦點是否回到主視窗。這兩個確認框是 wx 的一般對話框（不是其他訊息框用的 task dialog），若 NVDA 只讀標題或按鈕、沒有讀出內容，請告訴我們。

Then add a section **Implementation Notes** at the end of this plan (what was applied, any deviation, the commit hashes and tree ids, the exe), as the F-9 plan has.

```bash
cd $REPO
git add docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto-results.md docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/f11gui.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item95.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item97.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item99.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item101.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item103.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item104.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/rerun23.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/rerun25.py docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto/item35.py docs/superpowers/plans/2026-10-11-f11-dictionary-editor-ux.md docs/superpowers/specs/2026-10-11-f11-dictionary-editor-ux-design.md docs/superpowers/specs/2026-10-11-f11-dictionary-editor-ux-design_zh-TW.md
git diff --cached --stat
git commit -q -m "docs: record the F-11 packaged-build GUI checks (F-11)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the fourteen files in the `--stat` (the two spec files carry the one-line note that the before build runs only fix items), no `status` output, and the Task 10 tree id `0d0f93c8340a7ca86bcaf46775b7970ad90b4935` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.

## Implementation Notes (2026-10-11)

Planning and implementation were merged into one run (the user, 2026-10-11). The fill replay (a scratch clone, every expected block filled from a real run) and the final replay (a fresh clone of the branch at `2ddc887`, every step's blocks applied by Task 0 Step 3's `apply_blocks.py`, every bash block run and compared with its expected block) both ended with 0 mismatches; the final replay's task commits were fast-forwarded into the worktree `D:\workspace\DotExpress-f11`. `PY` was the main checkout's `client\.venv\Scripts\python.exe`; the worktree got the git-ignored runtime as in Task 0 Step 2 (never staged).

1. **Commits and trees** (`HEAD:client`, each the plan's): Task 1 `a02fe0a` `18b797ebc38fc1bb937e4484fe664bbba6de2d54`; Task 2 `d585aa4` `3c987c0912f1144fe237e6acbf5af2e675d1608c`; Task 3 `5dc8bfe` `eafdc94c70fa1cc7259b80b0bc0494b695e086f3`; Task 4 `bc7368a` `8c7487cb749098f0cfd54c0bf18821e690219062`; Task 5 `19fe19d` `b2cfda106215f90233282722b2d06f37bfabee15`; Task 6 `8b9804f` `6c3946d1eaa1c8749e826e06d1590f721df1bbf9`; Task 7 `2f6e70d` `8dcde92c72263e3d333f789965aacbda99f791ab`; Task 8 `1df105f` `b3da7431a5bb6408e0b209b7bc2a3b0c24147dba`; Task 9 `f9e66d6` `239eaf1dc896559c9bb450ea5177399ea56729ec`; Task 10 `5d5f2fd` `0d0f93c8340a7ca86bcaf46775b7970ad90b4935`; Task 12 (docs only) keeps `0d0f93c8...`. `Ran` 1483 (baseline, `FAILED (errors=1, skipped=7)`) -> 1485 -> 1490 -> 1508 -> 1512 -> 1516 -> 1522 -> 1526 -> 1539 -> 1551 -> 1553, `OK (skipped=6)`; msgids 369 -> 370 (Task 7) -> 377 (Task 8) -> 380 (Task 9), all translated, 0 fuzzy; the `.mo` 29,183 -> 30,362 bytes.
2. **Task 11.** The acceptance-criterion-2 set `Ran 482`, `FAILED (errors=1, skipped=1)` -> `Ran 549`, `OK`; six shuffle seeds, each `Ran 1553` with no failure; a fresh `.pot` equal to the committed one apart from `POT-Creation-Date`; the fixture sha256s unchanged (`e67d95a1...`, `f493da52...`, `8dc8572e...`); the main checkout's application data unchanged; all 51 mutants caught. The full suite in the worktree at `5d5f2fd`: `Ran 1553`, `OK (skipped=6)`.
3. **Build.** `D:\dxtest\N-f11\DotExpress.exe` from `5d5f2fd` (Step 1's command; PyInstaller 6.21.0, Python 3.13.15, `Build complete!` in about 54 s; the seven modules and `gui.py` from the worktree), 48,778,355 bytes, sha256 `3CEC35CE8A5C2102EC9CA1D9B8EC911B815B1F5B2DBBFF20D7E8BF01F46CC355`.
4. **GUI items** (all fix items, both builds). Step 3's loop ran once, as written, with one addition: before each item it waited until at least 1 GB of memory was available (the machine was short of memory; the waits only delayed the starts). All 11 N-f11 logs matched Step 4 at the first run. Three N-f9b runs stopped on tool problems while the user was using the desktop, and were re-run in new folders as Step 4 provides: `auto97-f9b-f11` and `auto101-f9b-f11` (`pywintypes.error` from `SetForegroundWindow` when opening Dictionary Management) as `auto97b-f9b-f11` and `auto101b-f9b-f11`; `auto44-f9b-f11` (`no window 自訂字典管理器` after the file was made UTF-8, its first 19 lines equal to N-f11's) as `auto44b-f9b-f11`, whose log equals `auto44-f11.log` apart from the folder name. Every re-run matched Step 4. No key went to another program (`f11gui.keys` checks the foreground first), only processes under the scripts' own folders were ended, and no script touched the clipboard. Results in `docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/auto-results.md`; item 107 (NVDA) stays manual for the user.
5. **Deviations.** (a) The plan as committed had a wrong Task 10 tree id in two rows of Expected Counts and in Task 12 Step 5 (`18b797eb...` with an extra digit); this commit puts the real one, `0d0f93c8...`, which Task 10 Step 4 already gave. (b) The fix/regression rule came after the plan commit; this commit adds it to Task 12 and, as a one-line note, to the Windows Verification section of both spec files, so Step 5's commit holds fourteen files. (c) The memory wait and the three re-runs above. Nothing else.
