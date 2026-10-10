# Data Safety Cleanup (F-8) Design

## Goal

Task F-8 closes the remaining data-loss paths of the refactor ("資料安全收尾" in the user's task list `task.md`, items #5, #10, #6 and the F-7 export follow-up):

1. **F-3 review M-1** (`docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/review_task.md`): Add, Rename, Import and the default document overwrite a `.dep` that is on disk but not in the document list. Such a file exists when the user chose "Keep Invalid Files" at startup. `os.replace` (`REPLACE_EXISTING`) replaces it without a message.
2. **F review M-2 / F-3 Risks** (`docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md`, priority 3): a crash between "move the old package aside" and "install the new one" during a Rename leaves no `.dep` for that document. Its data is in dot-prefixed `.tmp` files that startup never mentions. The document is gone from the user's point of view.
3. **Priority 3 in-place writers** (same review; HANDOFF section 6): `save_preprocessing_script`, the writers of `dictionaries/manager.py` (header writes and the `shutil.copyfile` of dictionary Import and Export) and `ConfigStore._save` write in place or leave temporary files behind. The same review asked what `ConfigStore._load` does with a damaged `config.json`.
4. **F-7 review M-4**: a failing export writer leaves an empty or partial file. When it overwrites an existing export, the good file is lost.
5. **Item #6, U+0000**: the Windows Edit control ends its text at U+0000. A document holding U+0000 shows only the text before it, and the next save writes that cut text back to the `.dep`. Everything after the first U+0000 is lost.

Decided by the user (2026-10-10), `task.md`; not asked again here:

- **U1.** U+0000 is replaced with U+FFFD (the replacement character) when text enters the app: loading `.dep` packages and importing documents. The user is told, for example "文件中有 N 個無法顯示的字元，已以 U+FFFD 標示". The form is for this spec to choose, and NVDA must be able to read it.
- **U2.** F-9 (a later task, specified in parallel) sends a conversion result back to the document that started the conversion. F-8 does not specify it and must not conflict with it.

After this task:

- No action of the app replaces or removes a `.dep` that is not in the document list. Add and Rename refuse such a name with the existing "already exists" message, Import lists it as an import issue, and the default document takes a free name.
- At startup, a document whose Rename or Save was interrupted by a crash is put back under its package name, if that name is free and no listed document already holds the same content. The user is told which documents were recovered. The temporary files that recovery decided not to use are then deleted, except one that holds the only copy of its text (the user's decision of 2026-10-10, after the F-8b review; "Corrected after planning (F-8b)" 10).
- Every remaining writer of user data goes through `shared/atomic_write.py`: the text-processing script, the dictionary files that Add, Import and the default dictionary create, dictionary Export, `config.json`, and the BRL and HTML exports. A failure leaves the target byte-identical (or still absent) and leaves no temporary file. The bytes written on success are unchanged.
- `config.json` that cannot be used no longer stops the app or is silently thrown away: a file that is not a JSON object is treated like a damaged one, a UTF-8 BOM is accepted, a file that cannot be read is not overwritten, and a damaged file is copied to `config.json.bak` before it is replaced.
- U+0000 never reaches the editors. Opening a document that had U+0000 shows a message box that names the document and the number of characters, once per document per session. The first save writes the replaced text, so the next start shows nothing.

New user-visible strings: 4 (msgid 364 -> 368). See "User-Visible Strings".

Non-goals: U+0000 in dictionary entries and in the text-processing script (Out of Scope); deleting or cleaning up temporary files other than the package leftovers that startup recovery does not use (D3 step 7); keeping attributes, ACLs or alternate data streams on replace (F-3 D11 applies); the `config.json` read-modify-write race between threads; F-9's conversion routing.

**Split proposal.** The work divides cleanly into two tasks. The recommendation is to implement it as **F-8a** (D1-D2, D6-D11: no strings, no new UI) and then **F-8b** (D3-D5, D12-D15: the two notices and the 4 new msgids), each with its own plan, review and build. This spec covers both, so that the decisions stay consistent. If the orchestrator keeps one task, the migration steps below run in order unchanged (Decided by orchestrator with the recommended default; user may override before merge).

## Relation to F-9

F-9 (conversion results go back to the document that started the conversion) is specified in parallel in `D:\workspace\DotExpress-f9`. F-8 is written to stay out of its way:

- F-8 does not touch `ui/conversion_presenter.py`, `conversion/`, the dual-view modules or the conversion parts of `gui.py`.
- The U+0000 notice (D13) is added at the end of `BrailleFrame._open_document_by_name`. It reads only the service's bookkeeping, never the editors or the conversion state.
- The service's new bookkeeping (pending U+0000 counts, D12) is keyed by document name and follows Rename and Delete, as the F-5 saved records already do. A conversion result that F-9 stores into a document that is not open goes through `DocumentController.replace_document` and never creates U+0000, so it needs nothing from F-8.
- Whichever task merges second re-runs the full suite on the merged `main`; the plan names the line numbers again.

## Corrected after planning (2026-10-10)

The plan for F-8a (`docs/superpowers/plans/2026-10-10-f8a-data-safety-cleanup.md`, dry-run on scratch clones of `bfd24db`: Tasks 0-5 replayed exactly, every step also applied with the plan's own block script, and the GUI items 66-69 and 76-82 run against a packaged build of the same code and against `N-f7`) found no error in decisions D1, D2 and D6-D11 or in their rows of the behavior table. Where the plan refines this spec, this section wins. D3-D5 and D12-D15 belong to F-8b and are planned later; this section does not change them.

1. **The split is adopted (O1).** F-8a = D1, D2, D6-D11, migration steps 1-4, Test Plan A-C, no new strings or UI, on `fix/f8-data-safety-cleanup`. F-8b = D3-D5, D12-D15, steps 5-6, Test Plan D-F, the two notices and the 4 msgids, with its own plan on a new branch after F-8a is merged. Windows items 66-69 and 76-82 and manual item 84 belong to F-8a; items 70-75 and manual item 83 to F-8b. The numbering stays.
2. **Counts for F-8a:** `Ran 1378`, `1386`, `1389`, `1400` after steps 1-4 (10, 8, 3, 11 new tests; baseline 1368; `FAILED (errors=1, skipped=7)` throughout, F-W6 only; msgids stay 364). Test Plan C has 10 tests (C3 is two tests: the third file, and a case-only rename through `CaseInsensitivePackageFiles`; C9 is the existing `test_case_only_rename_keeps_the_document`, which already renames `Alpha` to `alpha` through the frame on the real NTFS); A has 14 (A4 is a changed test); B has 8 (B7 is two tests). The acceptance-criterion-2 set goes from `Ran 502` to `Ran 534`, `OK (skipped=7)`.
3. **One fault injection for every writer.** A new test helper `client/tests/full_disk.py` (`full_disk(folder, after=N, pattern=...)`) patches `builtins.open` and `io.open` for a `with` block: a file opened for writing inside `folder` takes `N` characters or bytes and then raises `OSError(ENOSPC)`. It reaches the old in-place writers (`Path.write_text`, `shutil.copyfile`, `open("w")`, `NamedTemporaryFile`) and `shared.atomic_write` alike. It replaces the patches of `shutil.copyfileobj` (A6, A7; on Windows `copyfile` does not call it), `json.dump` (A14) and `os.replace` (A11).
4. **Five existing tests used a folder at `<name>.dep` to make a write fail.** D1 makes such a name taken, so they now inject the failure with `full_disk` (Add, and Import in the service and the frame) or with a failing install (Rename, `_FailingReplacePackageFiles(destination_name=...)`), and keep their intent; their messages are now compared exactly (`[Errno 28] No space left on device`). Tests that block a name for Save, Delete or Delete All are unchanged.
5. **The `Mock` service harness** sets `package_name_taken.return_value = False` and `free_document_name.side_effect = lambda base: base`; the other two settings of the Test Plan belong to F-8b.
6. **D8: an export onto a folder keeps today's message.** Through `write_text_atomically` alone, an export onto a folder of the same name would fail with a failed replace that names the temporary file (`[WinError 5] ...: '<dir>\.alpha.brl.<random>.tmp' -> '<dir>\alpha.brl'`) instead of `[Errno 13] Permission denied: '<dir>\alpha.brl'`, which F-7's export tests and item 56 pin. `documents/workspace.py` therefore gets `write_export_text(path, text)`: a folder at `path` raises the error an in-place write gives (Windows `PermissionError` 13, elsewhere `IsADirectoryError`); otherwise it calls `write_text_atomically(..., encoding="utf-8", newline=None)`. `export_document_brl` and `_write_html` (which imports it inside the function) use it. `shared/atomic_write.py` stays unchanged: changing `ensure_writable` would also change the dictionary editor's message for a folder, which F-2 D5 pins.
7. **D6, D7 names.** The header writer is the private `_write_header(stream)`; `dictionaries/manager.py` gains a module docstring that states the atomic writes; `save_preprocessing_script` drops its `os` and `tempfile` imports.
8. **D10, D11 details.** A non-object raises `ValueError("config.json does not hold a JSON object (<type>)")` inside `_load`'s `try` (type names `NoneType`, `list`, `str`, `int`), so it is logged as before. A skipped save logs `Config file %s was not saved because it could not be read` at `WARNING`, once per distinct read error per path (`_logged_skipped_saves`, cleared by a successful load), with the read error attached (`_log_current_exception` gains an `exc_info` keyword). `_backup_unreadable` reads the current bytes and writes `config.json.bak` with `write_bytes_atomically`; any failure there is logged as a failed save and nothing is written.
9. **`test_config` isolates `dotexpress.config`** in `setUpModule` (the work runs in the main checkout; a test that logs outside `assertLogs` must not write the user's `client/log/config.log`).
10. **Test details.** A1's script holds a `\r\n`, so newline translation would show; A3 checks the error's file name first; A9 releases its holder before the folder is removed; A12 compares with `os.linesep`; B2 also checks the logged `ValueError` text; B5 makes two setting changes and expects one skipped-save warning; B6 patches `config.write_bytes_atomically` with `create=True`.
11. **The app writes `config.json` at startup.** The client-init thread stores the client id right after the main window is shown, so "the next change" of the behavior table happens at startup: before F-8, a file with a BOM is already replaced by `{"client": {"id": ...}}` at startup (measured on `N-f7`, item 80; a truncated or non-UTF-8 file takes the same path); after F-8 that first write keeps `config.json.bak` first when the file is damaged (item 79) and is skipped with one warning when it cannot be read (item 81).
12. **Windows items.** The font size is changed with Ctrl + one wheel notch over the source editor. 80 checks that the BOM file's width 30 is kept instead of changing the width in Settings. 81 holds `config.json` with share mode **write only** (others may write but not read), not "none": with "none" the existing writability probe at startup (`prepare_application_directories` opens `config.json` for append) fails and both builds show the existing "Startup Error", which is not the D11 case. 79 before F-8: no main window, the process exits with code 1 after about 3 s, nothing is logged. 77 and 78 hold the target with `lockshare.py` (share read+write). 82 compares the bytes of both builds for the same steps.
13. **Acceptance criterion 7.** The remaining direct writes in production code outside `shared/atomic_write.py` are `app_paths.py`'s append probe of `config.json` (writes nothing), `PackageFiles.write` and `PackageFiles.temporary_path` (F-3's private staged file of a Rename, synced and installed with `os.replace`), and `dual_view/files.py` (excluded).

## Corrected after planning (F-8b, 2026-10-10)

The plan for F-8b (`docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md`, dry-run on scratch clones of `main` at `1b19290`: Tasks 0-3 replayed exactly, every step also applied with the plan's own block script and the catalog commands as written, and the GUI items 70-75 run against a packaged build of the same code and against `N-f8a2`) re-checked D3-D5 and D12-D15 against the code after F-8a and found no error in them or in their rows of the behavior table. Where the plan refines this spec, this section wins.

1. **Counts.** `Ran 1419` after step 5 (16 new tests) and `Ran 1434` after step 6 (15 new); baseline 1403 (F-8a's 1400 plus its three review tests); `FAILED (errors=1, skipped=7)` throughout, F-W6 only; msgids 364 -> 366 -> 368. Test Plan D has 15 tests: D1-D9 in `test_document_workspace` plus two (files that are not package leftovers are ignored; two interrupted renames are recovered oldest first), D8 also recording `os.replace` (`test_recovery_never_deletes_or_replaces_a_file`, renamed in the review fix, see 10); D11, D12 and "a load without leftovers recovers nothing" in `test_workspace_service`; D13. Test Plan E has 14: E1-E13 (E13 is `test_editors_receive_the_full_text`) plus `test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened` (item 75's flow). The acceptance-criterion-2 set goes from `Ran 537` to `Ran 568`, `OK (skipped=7)`.
2. **F1 is split in two,** one per step, so that each catalog regeneration is red first: `test_recovery_strings_are_translated` (step 5) and `test_replaced_character_strings_are_translated` (step 6).
3. **Log isolation.** `test_document_workspace` and `test_workspace_service` isolate `dotexpress.gui` in `setUpModule`. The recovery tests assert that nothing is logged, except D9: on Windows `os.rename` refuses a taken name, so a missing name rule would otherwise only show in the log.
4. **D9** simulates the race with a patched `os.rename` that creates the target first. The log line is `Cannot recover interrupted document package <path>: [WinError 183] ...` at `ERROR`, without traceback.
5. **D3 details.** The pattern is `^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$`, regular files only. `_read_package(package_path, package_name)` alone already skips a file whose stem is not a valid document name (member names are normalized and must equal the stem); rule 1's explicit check stays and D6 pins the behavior. The logger is bound at call time. The recovered documents are merged into the loaded list in its order (`casefold`, then name); the box names them in recovery order, oldest first.
6. **D12 helper.** `documents/workspace_service.py` gets `_displayable_documents(documents) -> (documents, counts)`, used at load and in the Delete All reload; `take_replaced_character_count` pops the count.
7. **Catalogs.** `msgmerge` fuzzy-matches `Documents Recovered` to `Documents` (`文件`) in step 5; the plan drops the flag. Nothing is fuzzy in step 6. Both regenerations also refresh `#:` reference lines that F-8a left stale.
8. **Windows items.** "Before" is `N-f8a2`. wx shows each box as a task dialog whose main instruction is the first paragraph and whose content is the rest; UIA does not expose the icon (the unit tests pin it). The boxes that startup shows come before the main window. Items 74 and 75 import `zero.txt`: `nul` is a reserved Windows name, so `nul.txt` is an import issue. Before F-8b, items 73-75 also show the loss on disk: once the document was opened and the app closed (or another document opened), the package holds only the text before the first U+0000. Item 70 gets a third start: alpha's text is changed, the app closed and started again (see 9).
9. **New Risk, measured: a leftover that recovery skips can be recovered at a later start.** Rules 1-4 are checked again at every start, and skipped files stay on disk. After an interrupted Rename of alpha to gamma, alpha is recovered and the staged `.gamma.dep.<8>.tmp` stays; once the user edits alpha, the next start recovers the staged copy as a new document `gamma` with the old text and shows "已復原文件" naming `gamma` (item 70, third start, on the F-8b build). Likewise the leftover of a completed Rename comes back under the old name once the renamed document is edited, and the leftover of an interrupted Save once its document is renamed or deleted. Nothing is lost; an extra document appears, possibly long after the crash, and the box names it. Avoiding it needs a decision this spec does not make (for example remembering handled leftovers, or renaming them out of the pattern, which touches the user's files). Open question for the user, not blocking; F-8b implements D3 as written above. **Decided by the user on 2026-10-10, see 10:** the leftovers recovery does not use are deleted, so only a leftover that holds the only copy of its text can still come back at a later start (Risks).
10. **Corrected after the F-8b review (2026-10-10, I-1): at startup, the temporary files that recovery has decided not to use are deleted** (decided by the user, 2026-10-10). D3 gains step 7. After the last rename every file the pattern matches is in one class:
    - **L0**, not a leftover of a valid document name: a folder or symbolic link, a stem that is not its own normalization, a zip archive that is not a package of `stem` or whose member data is damaged. Untouched (it cannot be DotExpress's own file).
    - **L1**, a leftover of a valid name that is no zip archive at all (`zipfile.BadZipFile`, and `zipfile.is_zipfile` is false): an empty pre-created file, a write cut short. Deleted: it never holds the only copy of the user's text.
    - **L2**, recovered (renamed to `<stem>.dep`).
    - **L3**, a valid package that was skipped and whose `(text, braille)` a listed or recovered document holds: the staged twin of an interrupted Rename, the aside file of a completed Rename, a Save file identical to its package, two empty documents (Risks). Deleted. The comparison waits until every rename is done: a file skipped early can duplicate a document recovered after it.
    - **L4**, a valid package that was skipped because its name is taken and whose content no package holds: the newer text of an interrupted Save, a leftover behind a kept invalid package or a folder named `<stem>.dep`. **Kept, untouched**, because it is the only copy of that text and so not "decided not to use" (Decided by orchestrator with the recommended default; user may override before merge).
    - **L5**, a valid package whose rename failed (D9): kept and logged, as before; looked at again at the next start.
    Deletion is the last step of the same call, after every rename. It uses only `os.unlink` on this call's candidate paths: never a `.dep`, never a symbolic link, never `os.replace` or `shutil.rmtree`. Each file is `lstat`ed again first and left alone if it is no longer a regular file or its size or modification time changed since it was read (another program touched it). An `OSError` (the file is held open, read-only, already gone) is logged as one line `Cannot remove unused temporary file <path>: <error>` on `dotexpress.gui`, without traceback, and the file stays until the next start. The line is at `ERROR`, not the review's `WARNING`: `dotexpress.gui` and its `gui.log` handler pass nothing below `ERROR` (`log.get_logger`'s default), so a warning would never reach `gui.log`. No new string: the deletions are the app's own temporary files and are not reported. Only startup deletes; the Delete All reload still does not recover. Tests: `Ran 1444` (1434 + 7 in `test_document_workspace` + 3 in `test_workspace_service`, the latter and one of the former being the review's M-1 to M-4), `FAILED (errors=1, skipped=7)`, F-W6 only; `test_recovery_never_deletes_or_replaces_a_file` became `test_recovery_never_replaces_and_removes_only_unused_leftovers`, `test_invalid_and_empty_temporary_files_are_ignored` became `test_invalid_and_empty_temporary_files_are_removed`, `test_startup_ignores_leftover_temporary_files` became `test_startup_removes_unreadable_leftover_temporary_files_without_a_message`. Windows item 70b is added; items 70 and 71 now expect the leftover gone.
11. **Corrected after the F-8b review (2026-10-10, M-5).** The zh-TW text of the U+0000 box says `轉換前` (before converting), because the app calls the action 轉換 (`執行轉換`) and keeps 轉譯 for the translation tables (`轉譯表`); `替代字元` stays (the usual zh-TW name of U+FFFD). "User-Visible Strings" shows the new text; the msgid is unchanged.

## Current State (verified 2026-10-10 on `main` `861d110`, Windows 11 26200, NTFS)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13.15, wxPython 4.2.5 msw). `$SP` is the session scratchpad. The probes are in `$SP\f8\probes\` and are not committed. They ran against `$SP\f8\copy\client` (a `git archive` of `861d110` plus the git-ignored liblouis and MathCAT runtime copied from the main checkout) and wrote only below `$SP\f8\`:

- `nul_sources.py`: which import paths let U+0000 into a `Document` (real import code, hand-made sample files);
- `nul_editor.py`: U+0000 in the two `wx.TextCtrl` styles of the main window, typing and paste;
- `workspace_probe.py`: M-1, crash leftovers (a child process ends itself with `os._exit` at a chosen step), and the U+0000 save path;
- `config_probe.py`: `ConfigStore` on unusual `config.json` files;
- `export_probe.py`: export bytes and failure behavior.

Baseline: `cd client && $PY -B -X utf8 -m unittest discover -s tests` gives `Ran 1368`, `FAILED (errors=1, skipped=7)` on `main` (F-7 review record); the only error is F-W6 (`test_dictionary_name_prompt ... test_case_only_rename_still_renames`). msgids: 364 (`dotexpress.po` has 365 `msgid` lines with the header).

### M-1: files on disk that are not in the list (`workspace_probe.py m1`)

Each workspace held a valid `alpha.dep` and an invalid `bad.dep` (kept at startup: `load_documents` returns it in `invalid_paths`, the controller does not list it).

| Action | Code path | Result |
| --- | --- | --- |
| Add `bad` | `DocumentWorkspaceService.create_document` -> `save_document_package` -> `os.replace` | no error; `bad.dep` replaced by an empty document |
| Rename `alpha` -> `bad` | `rename_document` -> `move_document_package` (install `os.replace(staged, bad.dep)`) | no error; `bad.dep` replaced, `alpha.dep` gone |
| Import `bad.txt` | `import_files` -> `batch_import_documents(existing_names=controller names)` -> `save_document_package` | no issue; `bad.dep` replaced |
| Start with only an invalid `new.dep` kept | `_ensure_open_document_exists` -> `_create_default_document` -> `create_document("new")` | no error; `new.dep` replaced by an empty document |

`BrailleFrame._prompt_for_document_name` (`gui.py:699-720`) checks only `DocumentController.document_name_exists`, which knows only listed documents.

### Crash leftovers (`workspace_probe.py crash`)

`alpha.dep` was saved, then the child process saved or renamed and died at the named step.

| Interrupted step | Files afterwards | Next start (`load_workspace_documents`) |
| --- | --- | --- |
| Rename `alpha` -> `gamma`, after the move aside, before the install | `.alpha.dep._vw4x6f_.tmp` (members `alpha.txt`/`alpha.brl`, mtime = the old package's mtime), `.gamma.dep.mlw4jang.tmp` (members `gamma.*`, same text, mtime = now) | **no document at all**; nothing reported |
| Rename completed, removing the moved-aside file failed (injected) | `gamma.dep`, `.alpha.dep.7gdjw2yi.tmp` (same content as `gamma`) | `gamma` |
| Save of `alpha`, after `fsync`, before `os.replace` | `alpha.dep` (old text), `.alpha.dep.97dc8315c5cf865f.tmp` (complete, new text) | `alpha` with the old text |

- `os.replace` keeps the moved file's modification time, so the moved-aside package is always older than the staged one.
- A temporary file whose write was interrupted, and the empty files that `PackageFiles.temporary_path` creates before anything is written, are not valid zip archives.
- The two temporary-name schemes are `.<package>.<16 hex>.tmp` (`write_bytes_atomically`, Save/Add/Import) and `.<package>.<8 characters>.tmp` (`tempfile.NamedTemporaryFile` in `PackageFiles.temporary_path`, staged and moved-aside files of a Rename). `*.dep` matches neither (F-3 D13, pinned by `test_load_workspace_documents_ignores_leftover_temporary_files` and `test_startup_ignores_leftover_temporary_files`).
- On NTFS, `os.rename(src, dst)` fails with `FileExistsError` (`winerror` 183) when `dst` exists, also when only its case differs (`Alpha.dep`) and when `dst` is a folder. It never replaces.

### Writers that still write in place

| Writer | Code | On failure today |
| --- | --- | --- |
| `save_preprocessing_script` (`conversion/preprocessing/user_script.py:53-74`) | `NamedTemporaryFile(prefix=".preprocessing.py.")` + `os.replace`; no `fsync`; the temporary path is recorded only after the write | an exception while writing leaves the `.tmp`; no `fsync`; POSIX mode `0600`. A read-only script gives `[WinError 5] 存取被拒。: '...\.preprocessing.py.<8>.tmp' -> '...\preprocessing.py'` (measured) |
| `ensure_default_dictionary` (`dictionaries/manager.py:18-26`), `create_dictionary` (`:58-68`) | `path.open("w", newline="")` + `csv.writer` header | a partial new file; bytes on success `text,braille,type\r\n` (measured) |
| `import_dictionary` (`:71-81`) | `shutil.copyfile(source, destination)` after F-6's full validation | a partial new dictionary, which is listed |
| `export_dictionary` (`:97-101`) | `shutil.copyfile` to the user's path | a partial file; an existing file there is truncated first |
| `ConfigStore._save` (`config.py:113-127`) | `open(path, "w")` + `json.dump(indent=2)`; any exception is logged to `config.log` and swallowed | a truncated `config.json`. Bytes on success use CRLF (text mode, measured) |
| `export_document_brl` (`documents/workspace.py:256-260`, BRL export and Ctrl+E) | `Path.write_text(encoding="utf-8")`, CRLF | **an existing good file becomes empty** (measured: `b"OLD GOOD EXPORT"` -> `b""` when the write raises) |
| `formats._write_html` (`documents/formats.py:104-109`) | renders first, then `Path.write_text`, CRLF (measured: 25 CRLF in an empty dual view) | a render error leaves the old file untouched; a write error truncates it |
| `formats._write_dep`, `save_document_package` | `write_bytes_atomically` (F-3) | atomic already |
| `dictionaries/entries.py` (`save`) | `write_text_atomically` (F-2) | atomic already |
| `dual_view/files.write_dual_view_html` | `write_text` of an app-owned temporary page in `paths.dual_view`, removed at exit | not user data; out of scope |

### `ConfigStore` on unusual files (`config_probe.py`)

`_load` (`config.py:92-111`) catches `FileNotFoundError` (empty dict, nothing logged) and every other `Exception` (one `WARNING` "Failed to read config file %s; using defaults" per distinct failure, empty dict). It returns whatever `json.load` returns.

| `config.json` | Getters | First setting change (`set_output_mode("ascii")`) |
| --- | --- | --- |
| missing | defaults | creates the file, with the `language_detection` defaults first |
| empty, truncated JSON, cp950 bytes, **UTF-8 with BOM** | defaults; one warning | **replaces the file with `{"conversion": {"output_mode": "ascii"}}`**: every other setting is gone, the old content too |
| `[1, 2]`, `"text"`, `null` (valid JSON, not an object) | **every getter raises `AttributeError`** (`'list' object has no attribute 'get'`) | raises too |
| a section that is not an object (`{"conversion": [1], "view": 3}`) | defaults for that section | the section is replaced; others kept |
| a good file | its values | merged, other values kept |

- `BrailleFrame.__init__` reads settings through these getters, and `BrailleApp.OnInit` does not catch exceptions there. A `config.json` holding `null` or a list therefore stops the app at startup without a message in the packaged build (by code reading; Windows item 79 confirms).
- A UTF-8 BOM comes from editors that write one (older Notepad "UTF-8"). Such a file is reported as damaged, and the next setting change throws all its settings away.
- An `OSError` while reading (for example a sharing violation) also gives defaults, and the next setting change then replaces the whole file with that one value (by code reading).
- `start_client_init_background` calls `get_or_create_client_id` on another thread (read-modify-write, no lock). Known defect; unchanged.

### U+0000: where it comes from (`nul_sources.py`, real import code)

| Source | Result |
| --- | --- |
| `.txt` with NUL bytes (`load_text_document`, UTF-8) | **kept**: `'A\x00B\nline2\x00\x00end\n'`, 3 NUL |
| `.txt` in UTF-16LE **without** BOM (`"AB"`) | **kept**: decodes as UTF-8 to `'A\x00B\x00'`, one NUL after each ASCII character |
| `.txt` in UTF-16 with BOM | `UnicodeDecodeError` (an import issue; unchanged) |
| `.dep` with NUL in the `.txt` and `.brl` members (`load_document_package`, startup and Import) | **kept** in text and braille |
| `.pdf`, string `(A\000B)` with a standard font, untagged (pymupdf path) | **kept**: `'A\x00B'` |
| `.pdf`, same string in a tagged PDF (pypdf MCID path) | **kept**: `'A\x00B'` |
| `.pdf`, `ToUnicode` CMap mapping a code to `<0000>` | not kept: pymupdf gives the glyph's own character |
| `.docx`, raw NUL byte or `&#0;` (also `&#1;`) | `ExpatError` (an import issue; unchanged) |
| `.docx`, `_x0000_` or `<w:sym w:char="0000"/>` | no NUL (`_x0000_` stays literal text) |
| `.epub`, raw NUL byte or `&#0;` | no NUL (dropped) |

DotExpress also writes NUL into its own packages: an import with NUL is saved to `.dep` as is, so a NUL from a PDF or a text file stays in the workspace.

### U+0000 in the editors (`nul_editor.py`, `wx.TextCtrl` with `TE_MULTILINE`, and with `TE_MULTILINE | TE_READONLY`)

| Operation | Result (both styles) |
| --- | --- |
| `SetValue("a\x00b")` / `ChangeValue` | `GetValue()` is `'a'` |
| `SetValue("line1\nli\x00ne2\nline3")` | `'line1\nli'`: everything after the first NUL is gone, across lines |
| `SetValue("\x00abc")` | `''` |
| `SetValue("a\ufffd\ufffdb\n\ufffd")` | returned unchanged |
| `WM_CHAR` with code 0 (what Ctrl+@ would send) | ignored; nothing inserted |
| `EM_REPLACESEL "X\x00Y"`, `WriteText("X\x00Y")` | only `X` inserted |
| `WM_PASTE` of a `CF_UNICODETEXT` holding `"P\x00Q tail"` | only `P` pasted; `wx.TheClipboard` also reads `'P'` |

So typing and pasting cannot put U+0000 into an editor. A paste stops at the NUL, but nothing that is already in the document is lost, and the user sees what was pasted. The only paths are `SetValue` from a document (`_load_document_into_editors`, `gui.py:554-556`) and from a conversion result (`show_conversion_output`). Conversion reads the editor (F-7 `_editor_text`), which cannot hold NUL, so a conversion result for the open document has no NUL source except the user's text-processing script (Out of Scope).

Note: the paste probe saves and restores the clipboard's Unicode text. In the run recorded here the restore failed (`OpenClipboard` was busy for a moment), so the clipboard was emptied instead. Later probes must retry `OpenClipboard`.

**The save path** (`workspace_probe.py nul`, real service and a real `wx.TextCtrl`): `alpha.dep` with text `"first line\nsecond\x00 line after NUL\nthird"`. After `controller.open_document("alpha")` and `SetValue`, the editor shows `'first line\nsecond'`. `save_open_document(text=editor text, ...)` (what every document switch does) writes `'first line\nsecond'`. The rest of the document is lost. F-5 D2 writes it because the editor text differs from the saved record.

Measured costs: on 550,000 characters, `str.count("\x00")` takes 0.15 ms on clean text, and count plus `replace` 0.6 ms.

### Main window presentation

The main window has no status bar (`_create_main_layout`, `gui.py:167-176`: a document list and two editors). NVDA does not announce status bar changes on its own anyway. Every existing notice of the main window is a message box through `ui.message_box.message_box` (F-7): `show_info`, `show_warning`, `show_error` (`gui.py:1112-1121`). NVDA reads a message box's title, text and button when it appears.

### Tests that pin today's behavior

- `test_document_workspace.py` `test_load_workspace_documents_ignores_leftover_temporary_files` and `test_gui_document_flows.py` `test_startup_ignores_leftover_temporary_files`: the leftovers are `b"not a zip"`. They stay green (an invalid archive is never recovered, D3).
- `test_user_preprocessing_script.py` `test_save_uses_utf8_and_atomic_replace` patches `conversion.preprocessing.user_script.os.replace` and globs `.preprocessing.py.*.tmp`.
- `test_config.py`: `ConfigLoadFailureLoggingTest` (one warning per distinct failure, defaults), `test_store_writes_the_documented_config_bytes` (reads with `read_text`, so CRLF is not visible), `ConfigSaveFailureLoggingTest`.
- `test_dictionary_manager.py`: copy and header tests compare bytes or rows.
- `test_gui_document_flows.py` `_make_frame` builds a frame with a `Mock` service. New service methods would return a truthy `Mock` there (Test Plan).
- No test pins M-1, the export truncation or U+0000.

## Decisions

### M-1: never replace a package that is not listed

**D1. A name whose package is on disk counts as taken.**

- `DocumentWorkspaceService.package_name_taken(name: str, *, exclude_name: str | None = None) -> bool`: `False` if `exclude_name` is given and `name.casefold() == exclude_name.casefold()` (a Rename's own package, including a case-only rename on NTFS); otherwise `os.path.lexists(self.package_path(name))`. On NTFS the check is case-insensitive, and a folder or a broken link counts too.
- `BrailleFrame._prompt_for_document_name`: the existing check becomes `self._document_controller.document_name_exists(document_name, exclude_name=exclude_name) or self._workspace_service.package_name_taken(document_name, exclude_name=exclude_name)`. The user sees the existing box `Document "{name}" already exists.` (`文件「{name}」已存在。`) and the name dialog again, prefilled. This covers Add and Rename. No new string.
- `DocumentWorkspaceService.create_document`: before writing, `if os.path.lexists(path): raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(path))`. This catches a file created after the prompt (a race). `_create_document` shows it with the existing `Failed to save document: {error}`.
- `move_document_package`: the install `try` block starts with `if files.exists(new_path): raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(new_path))`. At that point the old package has been moved aside, so for a case-only rename on a case-insensitive file system `new_path` no longer exists, and anything found is a third file. The existing `except` puts the old package back and removes the staged file. One package stays, the old one (F-3's failure contract).
- `import_files`: `existing_names` becomes the controller's names plus the stems of every `*.dep` on disk (`{path.stem for path in workspace.glob("*.dep")}`). A file whose name is taken gets the existing issue text `Document "{name}" already exists.` with the source file's path, as a listed duplicate does today.

Save of the open document is unchanged: its own package is the target.

**D2. The default document takes a free name.** `DocumentWorkspaceService.free_document_name(base: str) -> str` returns `base` if neither the controller nor the disk (D1) has it, else the first of `f"{base} (2)"`, `f"{base} (3)"`, ... that is free. `_create_default_document` uses `free_document_name(DEFAULT_DOCUMENT_NAME)`. Today's startup with a kept invalid `new.dep` therefore creates `new (2)` and leaves `new.dep` alone. Nothing changes when `new.dep` is absent (Decided by orchestrator with the recommended default; user may override before merge). `new (2)` passes `normalize_base_name` (checked). Rejected: refusing to create a default document (the editor would then accept typing that can never be saved).

### Interrupted saves and renames

**D3. Startup puts interrupted packages back without replacing anything, then deletes the leftovers it did not use.** New `recover_interrupted_packages(directory: Path, listed: list[Document]) -> list[Document]` in `documents/workspace.py`:

1. Candidates are the regular files in `directory` whose name matches `^\.(?P<stem>.+)\.dep\.[A-Za-z0-9_]+\.tmp$` (`.dep` case-insensitive). Both schemes of Current State match. `stem` must equal `normalize_document_name(stem)`; otherwise the file is skipped.
2. Each candidate is read with the package loader's checks, against the name `stem` (a new private `_read_package(path, package_name)`; `load_document_package` keeps its `.dep` check and calls it). A file that is not a valid package (an interrupted write, an empty pre-created file) is skipped.
3. Candidates are processed in the order `(st_mtime_ns, stem.casefold(), stem)`. The moved-aside package keeps the old package's mtime, so after an interrupted Rename it comes first and the document returns under its old name, as F-3 promises for a failed Rename.
4. A candidate is skipped if any `*.dep` in the folder (listed or not, any case) has its stem (`casefold`), or if a listed or already recovered document has the same `(text, braille)`. The second rule skips the leftover aside file of a Rename that completed, and the staged twin of a file just recovered.
5. Otherwise the file is renamed with `os.rename(candidate, directory / f"{stem}.dep")`. On Windows this never replaces an existing file (Current State). On POSIX, step 4 is the guard (not a shipping platform). The recovered `Document` is added to the result.
6. An `OSError` from the rename is logged (`dotexpress.gui` logger bound at call time, as F-7 D6: `Cannot recover interrupted document package %s: %s`, one line) and the file stays.
7. (Added after the F-8b review, the user's decision of 2026-10-10; details in "Corrected after planning (F-8b)" 10.) After every rename, the leftovers that were not used are deleted with `os.unlink`: a candidate of a valid name that is no zip archive at all, and a skipped package whose `(text, braille)` a listed or recovered document now holds. A skipped package that holds the only copy of its text stays, as do a file whose rename failed and every file that step 1 does not accept. A file that changed after it was read is left; a failed deletion is logged (`Cannot remove unused temporary file %s: %s`, one line) and the file stays.

Nothing else is deleted: every other file stays on disk, as today (F-3 D13). `DocumentWorkspaceService.load_documents` calls it after `load_workspace_documents`, adds the recovered documents to the loaded list before the controller and the saved records see it, and keeps their names for D4. Only startup recovers. The reload after a failed Delete All does not.

Results for the measured leftovers: interrupted Rename -> `alpha` is back with its text, and `.gamma.dep.<8>.tmp` is deleted (same content). Completed Rename with a leftover aside file -> the aside file is deleted (same content as the renamed document). Interrupted Save with `alpha.dep` present -> nothing happens (the name is taken), and the `.tmp` stays: it holds the only copy of the newer text. The complete newer temporary file is not offered: from the user's point of view that save never completed, like edits lost in a crash. Two documents with identical content (two empty documents, for example) whose Rename was interrupted: the interrupted one is not recovered and its leftover is deleted (Risks). A valid leftover whose name an invalid package holds is skipped and kept; if the user deletes that package in the invalid-files dialog, which comes after recovery, the leftover is recovered at the next start (F-8b review M-7). Rejected: offering every leftover in a dialog (new UI for files that are almost always duplicates); restoring the newest file (would turn an interrupted Rename into a completed one, which F-3 never does). "Deleting duplicates" was rejected here at first (the user's data, never deleted silently); the user decided otherwise on 2026-10-10 (step 7).

**D4. The user is told what was recovered.** `DocumentWorkspaceService.take_recovered_document_names() -> list[str]` returns and clears the names of D3. `BrailleFrame._load_workspace_documents_at_startup` calls it after `_review_invalid_workspace_files` and, if it is not empty, calls `self.show_info(_("DotExpress was interrupted ...").format(names="\n".join(names)), _("Documents Recovered"))` (strings below). Then `_ensure_open_document_exists` and the title update run as today. A message box, because the main window has no status bar and NVDA reads a message box completely (Current State). Information icon: nothing is wrong now (Decided by orchestrator with the recommended default; user may override before merge).

**D5. Temporary names and leftovers are otherwise unchanged.** `PackageFiles.temporary_path` keeps `NamedTemporaryFile` (F review M-3/M-4 stay follow-ups). Startup deletes only the unused leftovers of D3 step 7, never lists a `.tmp` as invalid and never offers to delete one.

### Atomic writers

**D6. The text-processing script.** `save_preprocessing_script` validates as today, creates the folder as today, then calls `write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")`. The bytes are unchanged (no newline translation, as `NamedTemporaryFile(newline="")` today). Gains: `fsync` before the replace, no `.tmp` left after any failure, `0o666 & ~umask` on POSIX. The `tempfile` and `os` imports go if nothing else uses them. Visible change: a read-only `preprocessing.py` now gives `[Errno 13] Permission denied: '<script>'` (F-3 D3's verdict) instead of `[WinError 5] ...: '<tmp>' -> '<script>'`, inside the existing `Unable to save text processing script: {error}`.

**D7. Dictionary files.** In `dictionaries/manager.py`:

- `ensure_default_dictionary` and `create_dictionary` write the header with `write_text_atomically(path, write_header, encoding="utf-8", newline="")`, where `write_header(stream)` is `csv.writer(stream).writerow(DEFAULT_HEADER)`. Same bytes (`text,braille,type\r\n`). The existence checks stay where they are.
- `import_dictionary` and `export_dictionary` copy with `write_bytes_atomically(destination, lambda stream: _copy_file_into(source, stream))`, where `_copy_file_into` opens the source with `open(source, "rb")` and calls `shutil.copyfileobj`. Same bytes as `shutil.copyfile`. An error opening or reading the source is raised inside the callback, so nothing is installed and the temporary file is removed. Error texts for a missing or locked source are the same `OSError`s as before.
- An existing export destination (the user confirmed overwriting it in the file dialog) is replaced only after the copy is complete and synced. A read-only destination gives `[Errno 13] Permission denied: '<destination>'`, the text `copyfile` gives today. Exporting a dictionary onto its own file, which `copyfile` refuses with `SameFileError`, now rewrites it with the same bytes. Corrected after the F-8a review (2026-10-10, M-5): a folder at the destination is checked first in `export_dictionary` and fails with the error an in-place write gives (on Windows `[Errno 13] Permission denied: '<destination>'`, the text `copyfile` gives; `IsADirectoryError` elsewhere), as D8's `write_export_text` does, not with a failed replace that names the temporary file.

**D8. Export BRL and HTML.** `export_document_brl` keeps `mkdir(parents=True, exist_ok=True)` and writes with `write_text_atomically(destination_path, lambda stream: stream.write(document.braille or ""), encoding="utf-8", newline=None)`. `_write_html` keeps rendering first and writes the result the same way. `newline=None` keeps today's CRLF bytes exactly (Current State). The BRL path also covers Ctrl+E and Export All. A failing export (any exception, F-7 D6 messages unchanged) leaves an existing file byte-identical and creates no file. `_write_dep` is already atomic.

**D9. `config.json` is written atomically.** `ConfigStore._save` keeps building `data` as today, keeps `os.makedirs`, and writes with `write_text_atomically(path, lambda stream: json.dump(data, stream, ensure_ascii=False, indent=2), encoding="utf-8", newline=None)`. `newline=None` keeps today's CRLF bytes. Errors are still logged and swallowed. A read-only `config.json` still fails with `[Errno 13]` (logged); a hidden one is now replaced and loses the attribute (F-3 D11).

**D10. `ConfigStore._load` accepts a BOM and rejects anything that is not an object.**

- The file is read with `encoding="utf-8-sig"`, as F-2 made every dictionary reader do. A file with a UTF-8 BOM is read normally. Without a BOM nothing changes.
- A parsed value that is not a `dict` is treated like a parse error: one warning as today (the signature names the type, for example `ValueError: config.json does not hold a JSON object (list)`), and defaults. The app starts with a `config.json` holding `null` or a list.
- On every failure other than `FileNotFoundError`, `_load` returns an empty `_UnreadableConfig` instead of a plain `{}`. It is a private `dict` subclass with one attribute, `error`. The getters see an empty dict, as today.

**D11. A setting change never silently throws away an unusable `config.json`.** The setters pass on the dict that `_load` returned (`data[...] = ...; self._save(data)` keeps it the same object), so `_save` sees whether the load failed:

- `error` is an `OSError` (the file exists but cannot be read, for example locked or denied): `_save` does not write. It logs once per distinct error, at `WARNING`: `Config file %s was not saved because it could not be read`. The file keeps the user's settings. The change applies for this session only (the app's state already holds it).
- Any other `error` (the file was read but is not usable JSON): `_save` first copies the current bytes to `config.json.bak` in the same folder (`write_bytes_atomically`, replacing an older `.bak`), then writes the new file. If the copy fails, `_save` does not write and logs the error (`ERROR`, as save failures today).
- No error: unchanged.

No UI and no string: settings files are not something the app shows. The `.bak` is never read by the app (Decided by orchestrator with the recommended default; user may override before merge). Rejected: refusing every save after a damaged load (the user could never change a setting again); a timestamped backup per incident (files pile up).

### U+0000

**D12. U+0000 becomes U+FFFD where documents enter the app (U1).** `documents/workspace.py` gets:

```python
def replace_nul_characters(text: str) -> tuple[str, int]:
    """Replace each U+0000 with U+FFFD; return the text and how many were replaced (F-8).

    The Windows Edit control ends its text at U+0000, so a document shown with one
    would be saved without everything after it.
    """
```

It returns `(text, 0)` for clean text, the same object. `_displayable(document) -> tuple[Document, int]` applies it to the text and to the braille when it is not `None`, and adds the counts.

`DocumentWorkspaceService` applies it at every place where packages or imports enter the controller:

| Entry | Controller receives | Saved record (F-5) | Pending count |
| --- | --- | --- | --- |
| `load_documents` (startup, including recovered documents, D3) | replaced documents | the documents **as read** (with U+0000) | set for each document with a count > 0 |
| `delete_all_documents`, failure reload | replaced documents | as read | kept only for names that were still pending |
| `import_files` | replaced documents | as written | set for each saved document with a count > 0 |

- **Load: the record keeps what is on disk.** F-5 D1 says the record is "exactly what was written or loaded". The editor then shows the replaced text, which differs from the record, so the first save of that document writes it. The package then holds U+FFFD, and the next start shows nothing. A document that is never opened keeps its U+0000 on disk, harmlessly: it is replaced again at every load, and no write happens without the user. Rejected: rewriting packages at startup (a write the user did not ask for, which can fail on read-only or locked packages).
- **Import: the replaced text is what gets saved.** Import writes a new package anyway, and U1 places the replacement at the entry.
- The pending counts (`self._nul_pending: dict[str, int]`) follow the document: `rename_document` moves the entry to the new name, `delete_document` drops it, a completed Delete All clears it.
- `take_replaced_character_count(name: str) -> int` returns the count and removes it (0 if none).
- Nothing changes for text without U+0000: same objects, same records, no message.
- `prepare_document_for_save` and `_encodable` (F-5 D4) do not replace U+0000. No path can bring it to a save after D12 (Current State), and doing it there would make an unopened document compare as saved while its package still holds U+0000.

**D13. The notice when such a document is opened (U1).** At the end of `BrailleFrame._open_document_by_name` (after the editors, list, title and dual view are updated): `count = self._workspace_service.take_replaced_character_count(document.name)`. If `count` is positive: `self.show_warning(_('Some characters in document "{name}" ...').format(name=document.name, count=count, mark="\ufffd"), _("Characters Replaced"))`.

- When: the moment the user first sees the document in this session. That covers startup (the first document), Open, Ctrl+Tab, the single-document Import (which opens it), and the document opened after Delete. Each document is reported once per session, so switching back and forth does not repeat it.
- Why a message box: the main window has no status bar, and NVDA reads a message box (title, text, the translated OK of F-7) when it appears. After OK, focus goes where the caller puts it (`on_open_document` and `_open_adjacent_document` focus the source editor, as today).
- Warning icon: the document's text differs from its file, and the user should look (Decided by orchestrator with the recommended default; user may override before merge).
- The text names the character in words ("the replacement character") next to the glyph, because a screen reader may not speak U+FFFD (manual item 83). The second paragraph says what happens if the user keeps them: liblouis writes an escape for U+FFFD (`\xfffd`, F-7 measurement).
- Rejected: one summary at startup and one after Import (it would come back at every start for each document that is never opened); a status bar (not announced by NVDA); a notice for documents that are only exported, never opened (they are written with U+FFFD; Risks).

**D14. Nothing else handles U+0000.** The editor reads (`_editor_text`), paste, conversion and the save path stay as they are: the editor cannot hold U+0000 (Current State). F-5's lone-surrogate rule and D12 are consistent: both use U+FFFD and keep the position. They differ in one way on purpose: a lone surrogate is invisible clipboard debris and is replaced silently (F-5 D5); U+0000 comes from the user's files, and the user decided to be told (U1).

**D15. Catalogs.** Four new msgids, all in `gui.py`: two for D4 and two for D13. Regenerate as in F-6 D11: `scripts\generate-pot.bat`, `POT-Creation-Date` pinned to `2026-10-10 12:00+0800`, `msgmerge --update --backup=none`, fill the four msgstr values, remove any `fuzzy` flag, `msgfmt --check -o ...dotexpress.mo ...dotexpress.po`. `msgfmt --check --statistics` must report 368 translated, 0 fuzzy, 0 untranslated. The messages with `{name}`, `{count}`, `{mark}` and `{names}` get `#, python-brace-format`. Check that `msgmerge` does not fuzzy-match `Documents Recovered` to `Document` captions or the long messages to other `{name}` messages.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Add `bad` while a kept invalid `bad.dep` is on disk | `bad.dep` replaced by an empty document | `文件「bad」已存在。`; name dialog again; `bad.dep` unchanged |
| Rename to `bad` (same) | `bad.dep` replaced; old package gone | same message; nothing changes on disk |
| Rename, a third file appears at the target after the prompt (race) | replaced | `儲存文件失敗：[Errno 17] File exists: '...\bad.dep'`; old package back, no `.tmp` |
| Import `bad.txt` (same) | `bad.dep` replaced | Import Issues: `bad.txt: Document "bad" already exists.`; `bad.dep` unchanged |
| Start with only a kept invalid `new.dep` | `new.dep` replaced by an empty `new` | `new (2)` created and opened; `new.dep` unchanged |
| Start after a crash inside Rename (no `.dep`, two `.tmp`) | the document is missing; nothing said | the document is back under its old name; "Documents Recovered" box; the other `.tmp` (same content) is deleted |
| Start with the leftover aside file of a completed Rename | nothing | no message; the `.tmp` is deleted (same content is listed) |
| Start with a leftover Save `.tmp` next to its package | nothing | identical: the `.tmp` stays (the only copy of the newer text) |
| Start with an empty `.tmp` or one that is no zip archive | nothing | no message; the `.tmp` is deleted (one held open by another program stays, one log line) |
| Text Processing Apply | atomic without `fsync`; `.tmp` may stay after a write error | atomic with `fsync`; nothing left; same bytes; read-only: `[Errno 13]` text |
| Default dictionary created, dictionary Add | in place | atomic; same bytes |
| Dictionary Import | `copyfile`; partial file on failure | atomic copy; nothing on failure |
| Dictionary Export over an existing file | truncated, then copied; partial on failure | old file kept until the copy is complete |
| Export BRL / HTML / Export All / Ctrl+E, success | CRLF file | identical bytes |
| Same, writer fails over an existing file | **old file becomes empty or partial** | old file byte-identical; no `.tmp`; same message or summary |
| Same, destination held open by another program sharing write | may be rewritten under the holder | `[WinError 5]` failure message; old file kept (Risks, O6) |
| Setting change, normal `config.json` | rewritten in place (CRLF) | atomic; identical bytes |
| `config.json` with a UTF-8 BOM | defaults; the next change wipes the file | read normally; the next change writes it without BOM |
| `config.json` holding `null` or a list | app does not start (no message) | starts with defaults (one warning); the next change keeps a `.bak` first |
| `config.json` truncated or not UTF-8 | defaults; next change wipes it | defaults; next change keeps a `.bak` first |
| `config.json` unreadable (locked, denied) | defaults; next change replaces it with one value | defaults; changes are not written (warning in `config.log`) |
| Open a document whose package had U+0000 | editor shows text up to the first U+0000; **the next save writes that cut text** | editor shows the whole text with U+FFFD; "Characters Replaced" box once; the next save writes the full text with U+FFFD |
| Import a `.txt`/`.pdf`/`.dep` with U+0000 | saved with U+0000; cut when opened | saved with U+FFFD; the box when it is first opened |
| Export a document with U+0000 that was never opened | U+0000 in the export / conversion | U+FFFD in the export / conversion |
| Paste text with U+0000 | stops at the U+0000 (clipboard semantics) | identical |
| Documents without U+0000, every other path | - | identical |

## Design per File

### `client/documents/workspace.py` (4 spaces)

- `replace_nul_characters`, `_displayable` (D12).
- `_read_package(path, package_name) -> Document`: today's body of `load_document_package` after the suffix check; `load_document_package` calls it with `normalize_document_name(path.stem)`.
- `_INTERRUPTED_PACKAGE` (compiled pattern) and `recover_interrupted_packages` (D3), with a docstring that states "never replaces" and which leftovers it deletes (step 7, `_remove_unused_leftover`).
- `move_document_package`: the `files.exists(new_path)` check at the start of the install block (D1). Docstring: "A file already at ``new_path`` (a package that is not listed) raises ``FileExistsError``; the old package is put back."
- `export_document_brl`: `write_text_atomically` (D8); import it from `shared.atomic_write`.

### `client/documents/workspace_service.py` (4 spaces)

- `package_name_taken`, `free_document_name` (D1, D2); `create_document`'s existence check (D1); `import_files`' `existing_names` (D1), `_displayable` and the pending counts (D12).
- `load_documents`: `load_workspace_documents`, then `recover_interrupted_packages`, then `_displayable` for the controller, raw documents for `_reset_saved`, pending counts. Return value unchanged (`list[Path]`).
- `take_recovered_document_names`, `take_replaced_character_count` (D4, D12); `rename_document`, `delete_document` and `delete_all_documents` maintain `_nul_pending` (D12).
- Module docstring: one sentence each for D1, D3 and D12.

### `client/documents/formats.py` (4 spaces)

`_write_html` writes with `write_text_atomically(..., newline=None)` after rendering (D8).

### `client/gui.py` (tabs)

- `_prompt_for_document_name`: the disk check (D1).
- `_create_default_document`: `free_document_name` (D2).
- `_load_workspace_documents_at_startup`: the recovery notice (D4).
- `_open_document_by_name`: the U+0000 notice (D13).
- The four msgids (D15).

### `client/conversion/preprocessing/user_script.py` (4 spaces)

`save_preprocessing_script` (D6).

### `client/dictionaries/manager.py` (4 spaces)

D7: `write_header`, `_copy_file_into`, the four writers; `shutil` stays for `copyfileobj`.

### `client/config.py` (4 spaces)

D9-D11: `_UnreadableConfig`, `_load`, `_save`, `_backup_unreadable(path)`; the module docstring of `ConfigStore` adds one sentence for each.

### `client/locales/`

`dotexpress.pot`, `zh_TW/LC_MESSAGES/dotexpress.po`, `zh_TW/LC_MESSAGES/dotexpress.mo` (D15).

### Not changed

`shared/atomic_write.py` (both variants already exist; `newline=None` is already accepted), `dialog.py`, `documents/controller.py`, `documents/export_coordinator.py` (its messages already cover every failure, F-7 D6), `ui/`, `conversion/` except `user_script.py`, `dictionaries/entries.py`, `dual_view/`, `client/braille/`, the package format, both fixtures.

## What Stays Identical

- The bytes of every successful write: packages, dictionary files, the script, `config.json` (CRLF), BRL and HTML exports (CRLF).
- Every existing message, caption and button. The F-5 save comparison and close dialog, F-7's export reporting.
- Startup, Add, Rename and Import when no unlisted `.dep` is on disk and no interrupted package can be recovered.
- Documents without U+0000: what the editors show, what is saved and exported, and no message.
- Temporary files are never deleted by the app, except the package leftovers that startup recovery does not use (D3 step 7).
- Both fixture sha256 values (`translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`).

## User-Visible Strings

New msgids (364 -> 368), all in `gui.py`:

| msgid | msgstr (zh_TW) | Where |
| --- | --- | --- |
| `Characters Replaced` | `已取代字元` | caption of the U+0000 box (D13) |
| `Some characters in document "{name}" cannot be shown ({count} in all). Each one has been replaced with the replacement character {mark}, so the text after it is kept.\n\nDelete or change these {mark} characters before converting. Otherwise each one appears in the braille as an escape code.` | `文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。\n\n轉換前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。` | text of the U+0000 box; `{mark}` is U+FFFD (D13) |
| `Documents Recovered` | `已復原文件` | caption of the recovery box (D4) |
| `DotExpress was interrupted while saving or renaming a document. These documents were recovered:\n\n{names}\n\nCheck that their content is what you expect.` | `DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。` | text of the recovery box; one name per line (D4) |

- The msgids stay ASCII: the glyph comes in through `{mark}`. The English text avoids a plural, because `i18n` has no `ngettext`; the shipped catalog is zh_TW (`LOCALE_LANGUAGES`), where the count needs no plural.
- Reused without change: `Document "{name}" already exists.`, `Error`, `Failed to save document: {error}`, the import issue text `Document "{name}" already exists.` (not a msgid today, unchanged), `Unable to save text processing script: {error}`, the dictionary messages, `Failed to export document: {error}` and the Export All summary.

The U+0000 box reads, in zh-TW (U+FFFD shown as `<U+FFFD>`):

```
已取代字元

文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。

轉換前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。

[確定]
```

## Test Plan

TDD: each step's new tests are written first and fail for the stated reason; then the code turns them green. Test files keep their indentation (4 spaces in every file named here). Tests use temporary directories only and never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/`.

**Log isolation is mandatory.** `recover_interrupted_packages` binds `dotexpress.gui` when it logs; `config.py` logs to `dotexpress.config`. Every new test module that can make production code log calls `unittest.addModuleCleanup(isolate_file_logs(...))` in `setUpModule` (`tests/file_log_isolation.py`), and log assertions use `assertLogs`. `test_gui_document_flows.py` already isolates `dotexpress.gui`; `test_config.py` keeps its own `patch.object(config, "logger")` pattern.

**U+0000 and U+FFFD in test sources** are written as `"\x00"` and `"\ufffd"` escapes by script, and the file bytes are checked, never typed through the Edit/Write tools (HANDOFF section 2).

**The `Mock` service harness** (`test_gui_document_flows.py` `_make_frame`) sets `package_name_taken.return_value = False`, `free_document_name.side_effect = lambda base: base`, `take_recovered_document_names.return_value = []` and `take_replaced_character_count.return_value = 0`; otherwise a truthy `Mock` loops the name prompt or shows boxes.

**Windows-only tests** use `tests/windows_file_handles.py` (`hold_open`, `make_read_only`) and `@unittest.skipUnless(os.name == "nt", ...)`.

### A. Atomic writers

`test_user_preprocessing_script.py`:

1. `test_save_installs_through_the_shared_atomic_writer`: `patch("shared.atomic_write.os.fsync", wraps=os.fsync)` is called once, the recorded `os.replace` source matches `\.preprocessing\.py\.[0-9a-f]{16}\.tmp`. Red: no `fsync`, 8-character name.
2. `test_write_error_leaves_no_temporary_file_and_keeps_the_script`: an `OSError(errno.ENOSPC)` raised while the script text is written (the plan picks an injection point that reaches both today's `NamedTemporaryFile` stream and the helper's stream); the old bytes stay; no `.tmp`. Red: today the `.tmp` stays (its path is recorded only after the write).
3. Windows only: `test_read_only_script_is_refused_with_the_in_place_verdict`: exact `[Errno 13] Permission denied: '<script>'`; no `.tmp`. Red: `[WinError 5]`.
4. `test_save_uses_utf8_and_atomic_replace` keeps its assertions; its patch target becomes `os.replace` (the module may no longer import `os`). Bytes unchanged.

`test_dictionary_manager.py`:

5. `test_header_writers_install_through_a_synced_temporary_file` (subTests: `ensure_default_dictionary`, `create_dictionary`): `os.fsync` called; bytes `text,braille,type\r\n`; no `.tmp`. Red: no `fsync`.
6. `test_import_copy_failure_leaves_no_dictionary` : `shutil.copyfileobj` patched to write half and raise `OSError(errno.ENOSPC)`; `list_dictionary_names` unchanged; no `.tmp`. Red: a partial `.csv` is left and listed.
7. `test_export_failure_keeps_the_existing_destination`: destination holds `b"OLD"`; same injection; destination still `b"OLD"`. Red: truncated.
8. `test_export_copies_the_same_bytes` (BOM, CRLF, CJK): byte-identical to the source. Green today (guard).
9. Windows only: `test_export_onto_a_destination_held_open_keeps_it` (`hold_open` share read+write): `PermissionError` with `winerror == 5`; bytes unchanged. Red: today the copy succeeds under the holder.

`test_document_workspace.py` / `test_document_formats.py` (the plan picks the module that already tests each writer):

10. `test_brl_export_failure_keeps_the_existing_file`: destination `b"OLD GOOD EXPORT"`; the braille holds a lone surrogate written by script, so the encoder fails mid-write; bytes unchanged; no `.tmp`. Red: `b""` (measured).
11. `test_html_export_failure_keeps_the_existing_file`: `shared.atomic_write.os.replace` patched to raise; bytes unchanged. Red: today there is no `os.replace` and the new file is written.
12. `test_exports_keep_their_crlf_bytes` (subTests BRL, HTML): exact bytes with `\r\n`. Green today (guard against `newline=""`).

`test_config.py`:

13. `test_save_installs_through_a_synced_temporary_file`: `os.fsync` called once per save; no `.tmp`. Red.
14. `test_save_failure_keeps_the_previous_file`: `json.dump` patched to write part of the text and raise; old bytes unchanged; the failure is logged (existing pattern). Red: truncated.
15. `test_saved_bytes_use_crlf_on_windows` (Windows only): exact bytes. Green today (guard).

### B. `ConfigStore` load hardening (`test_config.py`)

1. `test_a_utf8_bom_is_read` : `b"\xef\xbb\xbf{...}"` gives the stored values; no warning. Red.
2. `test_json_that_is_not_an_object_gives_defaults_and_one_warning` (subTests `null`, `[1, 2]`, `"text"`, `3`): getters return defaults; one warning whose message names the path. Red: `AttributeError`.
3. `test_a_change_after_a_damaged_load_keeps_a_backup` (subTests: truncated JSON, cp950 bytes, `[1, 2]`): after `set_output_mode("ascii")`, `config.json.bak` holds the old bytes exactly and `config.json` holds the new setting. Red: no `.bak`.
4. `test_a_second_backup_replaces_the_first`. Red.
5. `test_a_change_after_an_unreadable_load_does_not_write` : `open` patched to raise `PermissionError` for reads of the path only; `set_output_mode` leaves the bytes unchanged, writes no `.bak`, logs one warning `was not saved because it could not be read`. Red: the file is replaced by one value.
6. `test_a_failed_backup_prevents_the_write`: `write_bytes_atomically` for the `.bak` raises; `config.json` unchanged; error logged. Red.
7. `test_a_missing_file_is_created_without_backup` and `test_a_good_file_is_updated_without_backup`. Green today (guards).
8. `ConfigLoadFailureLoggingTest` and the bytes test stay green unchanged.

### C. M-1 (`test_document_workspace.py`, `test_workspace_service.py`, `test_gui_document_flows.py`)

1. Service: `test_create_document_refuses_a_package_that_is_not_listed`: invalid `bad.dep` kept (`load_documents` returned it); `create_document(Document("bad", ...))` raises `FileExistsError` naming `bad.dep`; bytes unchanged; not added. Red: replaced.
2. Service: `test_rename_onto_a_package_that_is_not_listed_keeps_both_files` (`move_document_package` guard): `alpha` -> `bad`; `FileExistsError`; `alpha.dep` and `bad.dep` byte-identical; no `.tmp`; controller unchanged. Red.
3. Workspace: `test_move_onto_an_existing_third_file_puts_the_old_package_back`, also the case-only rename through `CaseInsensitivePackageFiles` still succeeds (guard against checking before the move aside). Red / green.
4. Service: `test_import_treats_packages_on_disk_as_existing`: issue `bad.txt: Document "bad" already exists.`; `bad.dep` unchanged; other files imported. Red.
5. Service: `test_package_name_taken` (subTests: missing, listed, unlisted file, folder, other case on NTFS (Windows only), `exclude_name` equal ignoring case). Red: method missing.
6. Service: `test_free_document_name` (subTests: free, `new.dep` on disk -> `new (2)`, `new.dep` and `new (2).dep` -> `new (3)`, a listed `new`). Red.
7. GUI: `test_add_of_a_name_whose_package_is_on_disk_asks_again`: events: name dialog, `message_box('Document "bad" already exists.', 'Error', OK | ICON_ERROR)`, name dialog prefilled `bad`, cancel; listing unchanged. Red.
8. GUI: `test_rename_to_a_name_whose_package_is_on_disk_asks_again`. Red.
9. GUI: `test_case_only_rename_is_not_blocked_by_its_own_package` (Windows only, `Alpha` -> `alpha`): renamed. Green today; guards `exclude_name`.
10. GUI: `test_startup_with_only_a_kept_invalid_new_package_creates_new_2`: `new.dep` unchanged; list `["new (2)"]`. Red.

### D. Recovery

`test_document_workspace.py`:

1. `test_interrupted_rename_is_recovered_under_the_old_name`: the two `.tmp` files written as the probe found them (aside with the old mtime set by `os.utime`, staged newer); result `[alpha]`; `alpha.dep` exists with the old bytes; the staged `.tmp` stays (deleted since the F-8b review fix, step 7). Red: function missing.
2. `test_leftover_of_a_completed_rename_is_not_recovered` (`gamma.dep` listed with the same content). Red (function missing), then green by rule 4.
3. `test_leftover_save_next_to_its_package_is_not_recovered`. 
4. `test_invalid_and_empty_temporary_files_are_ignored` (also `b"not a zip"`, a zero-byte file).
5. `test_name_held_by_an_unlisted_package_is_not_recovered` (kept invalid `alpha.dep`, any case).
6. `test_names_that_are_not_valid_document_names_are_ignored` (`.CON.dep.x.tmp`, `.a<b.dep.x.tmp` is not creatable on Windows; the plan uses names that can exist).
7. `test_member_names_must_match_the_temporary_file_name`.
8. `test_recovery_never_deletes_a_file`: a recording `os.unlink`/`os.remove`/`Path.unlink` patch sees no call. Since the F-8b review fix: `test_recovery_never_replaces_and_removes_only_unused_leftovers`, `os.unlink` only for the unused leftovers (step 7), no other call.
9. Windows only: `test_recovery_does_not_replace_a_file_created_meanwhile`: the disk check patched to miss; `os.rename` raises `FileExistsError`; the existing file unchanged; the `.tmp` stays; one log line (`assertLogs("dotexpress.gui", "ERROR")`).
10. The F-3 test `test_load_workspace_documents_ignores_leftover_temporary_files` stays green unchanged.

`test_workspace_service.py`:

11. `test_load_documents_recovers_and_reports_names_once`: controller lists `alpha`; `take_recovered_document_names()` is `["alpha"]`, then `[]`; the record makes the next unchanged save skip (F-5). Red.
12. `test_delete_all_failure_reload_does_not_recover`. Guard.

`test_gui_document_flows.py` (real service in a temporary workspace, as the existing startup tests):

13. `test_startup_reports_recovered_documents`: events: the invalid-files dialog if any, then `message_box(<recovery text with "alpha">, "Documents Recovered", OK | ICON_INFORMATION, parent=frame)`, then the title. Red.
14. `test_startup_ignores_leftover_temporary_files` stays green unchanged (no message). Since the F-8b review fix: `test_startup_removes_unreadable_leftover_temporary_files_without_a_message` (no message; the files are deleted).

### E. U+0000

`test_document_workspace.py`:

1. `test_replace_nul_characters` (subTests: clean text returns the same object and 0; `"a\x00b"`; leading, trailing, consecutive; CRLF around it). Red.
2. `test_displayable_counts_text_and_braille_and_keeps_pending_braille`. Red.

`test_workspace_service.py`:

3. `test_load_replaces_nul_for_the_controller_and_keeps_the_record_as_read`: package text `"a\x00b"`, braille `"\u2801\x00"`; controller holds U+FFFD; the package bytes unchanged after load; `take_replaced_character_count("alpha") == 2`, then 0. Red.
4. `test_first_save_after_load_writes_the_replaced_text`: `save_open_document(text="a\ufffdb", braille="\u2801\ufffd")` writes; the package then holds U+FFFD and loads with count 0. Red (load still gives U+0000 to the controller before the change).
5. `test_unopened_document_keeps_its_package_and_count`. Red.
6. `test_import_saves_the_replaced_text_and_counts_it` (a `.txt` with NUL bytes, a `.dep` with NUL). Red.
7. `test_pending_count_follows_rename_and_is_dropped_by_delete`. Red.
8. `test_delete_all_failure_reload_keeps_only_pending_counts`. Red.
9. `test_text_without_nul_is_unchanged` (same objects, records, no counts). Green guard.

`test_gui_document_flows.py`:

10. `test_opening_a_document_with_nul_shows_the_notice_once`: open `alpha` -> one `message_box(<text with "alpha", 2, U+FFFD>, "Characters Replaced", OK | ICON_WARNING, parent=frame)` after the editors hold the replaced text; open `beta`, open `alpha` again -> no second box. Red.
11. `test_startup_opens_the_first_document_and_shows_its_notice`. Red.
12. `test_single_import_with_nul_shows_the_notice`: order: the notice (from the open), then the import issues dialog if any. Red.
13. `test_editor_receives_the_full_text`: `input_txt.SetValue` called with `"a\ufffdb tail"`. Red.

### F. Catalog (`test_i18n.py`)

1. `test_f8_messages_are_translated`: the four msgids are in the compiled catalog with the msgstr values above (compared through `gettext` on `dotexpress.mo`), and the formatted strings accept `name`, `count`, `mark` and `names`. Red: missing.

### Counts

New tests: A 15, B 7, C 10, D 13, E 13, F 1, about 59 (subTests count once). Windows-only: A3, A9, A15, C5's NTFS subTest, C9, D9 (5 tests). Expected after all steps: `Ran` = 1368 + the new tests, `FAILED (errors=1, skipped=7)` on Windows, F-W6 only. The plan fixes the exact numbers; the red/green intent is binding. If F-8 is split, F-8a has A, B, C; F-8b has D, E, F.

## Migration Steps (each step one green commit, red first)

F-8a:

1. `fix: never replace a document package that is not listed (F-8)`: D1, D2; Test Plan C.
2. `fix: write the text-processing script and dictionary files atomically (F-8)`: D6, D7; A1-A9.
3. `fix: keep the previous export when an export fails (F-8)`: D8; A10-A12.
4. `fix: write config.json atomically and never discard an unusable one (F-8)`: D9-D11; A13-A15, B.

F-8b:

5. `fix: recover documents whose save or rename was interrupted (F-8)`: D3-D5 and Test Plan D, with the two recovery msgids and the catalog regeneration (D15 for those two).
6. `fix: replace U+0000 when documents are loaded or imported, and say so (F-8)`: D12-D14; Test Plan E and F, with the other two msgids and the catalog regeneration.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only. Only steps 5 and 6 touch `client/locales/`.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, the runtime copied as in F-3 plan Task 0 when in a worktree.

1. Full suite: no failure or error other than F-W6; `Ran` = baseline + the new tests.
2. Focused: `$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_document_formats tests.test_export_coordinator tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_call_sites -v` passes; the Windows-only tests run.
3. Catalogs: the AST msgid scan gives 368; `msgfmt --check --statistics` reports 368 translated, 0 fuzzy, 0 untranslated; `git diff main -- client/locales` changes only the four entries and reference lines.
4. Both fixture sha256 values unchanged.
5. App data untouched: in the main checkout, `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after; in a worktree, none of them is created.
6. `git diff main --stat` touches only the files of "Design per File", the test files named above, and the spec, plan and history files.
7. A source scan (or `grep`) finds no `shutil.copyfile`, no `Path.write_text` and no `open(..., "w")` writing user data in `client/` production code outside `shared/atomic_write.py` and `dual_view/files.py`.
8. Mutation check (plan). Each mutant is caught by at least one test:
   - the prompt without the disk check; `package_name_taken` ignoring `exclude_name`; `create_document` without its check; the move guard before the move aside (breaks case-only renames) or removed; `import_files` with controller names only; `free_document_name` returning `base`;
   - recovery: deleting a skipped candidate (since the F-8b review fix: deleting a leftover that step 7 keeps, or deleting before every rename is done); using `os.replace` instead of `os.rename`; no content-duplicate rule; newest-first order; recovering invalid archives; recovering in the Delete All reload;
   - each writer back to its old call (`copyfile`, `write_text`, `open("w")`, `NamedTemporaryFile`); `newline=""` for BRL, HTML or config;
   - `_load` without `utf-8-sig`; accepting a non-dict; `_save` writing after an `OSError` load; no `.bak`; writing when the `.bak` fails;
   - `replace_nul_characters` not counting braille; the record built from the replaced text; the notice on every open; no notice; the count not moved on Rename; U+0000 replaced in `_encodable`.
9. Packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build as in F-7: the main checkout's `client\.venv\Scripts` first on `PATH`, `scripts\build-dotexpress.bat`; check in `PYZ-00.toc` / `Analysis-00.toc` that the changed modules come from the checkout under test; copy the exe to `D:\dxtest\N-f8\` (or `N-f8a`, `N-f8b` if split). "Before" is `D:\dxtest\N-f7\DotExpress.exe`.

Each item runs in a new `D:\dxtest\auto<item>-f8` folder with the exe copied in; `dictionary\`, `workspace\`, `log\` and `config.json` live next to it. Only processes whose exe lies under that folder are ended (`dx.kill_under`; `taskkill /T` for `lock.py`). Message boxes are task dialogs and are read through UIA (`f5gui.describe`). Scripts go to the implementation's history folder `auto/` and reuse, without editing, `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `dicts.py`, `lock.py`), F-5's `f5gui.py` and F-7's `f7gui.py`. Test workspaces are built by script (zip members written with `zipfile`; U+0000 and U+FFFD as escapes). The pywinauto venv is `$SP\uia` (rebuild with `py -3.13 -m venv` and `pip install pywinauto==0.6.9 psutil`).

Items continue after F-7's 65:

| # | Steps | Expected after F-8 | Before (N-f7) |
| --- | --- | --- | --- |
| 66 | Workspace: `alpha.dep` valid, `bad.dep` invalid. Start; "Keep Invalid Files". Add `bad` | `錯誤` box `文件「bad」已存在。` with `確定`; the name dialog again, prefilled `bad`; Esc; `bad.dep` sha256 unchanged | `bad` added; `bad.dep` replaced |
| 67 | As 66; Rename `alpha` to `bad`; then Rename `alpha` to `Alpha` | first: same box, nothing changes; second: renamed (case-only) | first: `bad.dep` replaced, `alpha.dep` gone |
| 68 | As 66; Import `bad.txt` and `ok.txt` | Import Issues lists `bad.txt: Document "bad" already exists.`; `ok` imported; `bad.dep` unchanged | `bad.dep` replaced |
| 69 | Workspace with only an invalid `new.dep`; Keep | `new (2)` listed and open; `new.dep` unchanged | `new` created, `new.dep` replaced |
| 70 | Workspace built like the interrupted Rename (aside `.alpha.dep.<8>.tmp` with the old mtime, staged `.gamma.dep.<8>.tmp`, no `.dep`); start | `已復原文件` box listing `alpha`, information icon, `確定`; list `alpha` with its text; `alpha.dep` exists; `.gamma.dep.*.tmp` deleted (F-8b review fix; before the fix it stayed); restart: no box; after alpha is edited, a third start: no box | empty list, a new `new` document, no message |
| 70b | (added by the F-8b review fix) `alpha.dep` plus an empty `.beta.dep.k2j1abcd.tmp`, a `not a zip` `.alpha.dep.0123456789abcdef.tmp` and a `not a zip` `.gamma.dep.x2y3z4w5.tmp` held open by `lockshare.py` (share read); start; end the holder; start again | no box; the first two are deleted; the held one stays and `log\gui.log` has one line `Cannot remove unused temporary file ...`; the second start deletes it | no box; all three stay |
| 71 | `gamma.dep` + leftover `.alpha.dep.<8>.tmp` with the same content; start | no box; list `gamma`; `.tmp` deleted (F-8b review fix; before the fix it stayed untouched) | no box; `.tmp` untouched |
| 72 | `alpha.dep` + leftover `.alpha.dep.<16 hex>.tmp` with newer text; start | no box; `alpha` with the package's text; `.tmp` untouched (the only copy of the newer text) | identical |
| 73 | `alpha.dep` text `"first line\nsecond\x00 after\nthird"`, braille with one U+0000; `beta.dep` clean; start | `已取代字元` box, warning icon, text naming `alpha` and `2`, `確定`; source editor (`WM_GETTEXT`) holds the whole text with U+FFFD; Ctrl+Tab to `beta` and back: no second box; close; `alpha.dep` holds U+FFFD and `third`; restart: no box | editor holds `first line\nsecond`; after Ctrl+Tab `alpha.dep` holds only `first line\nsecond` (**the data loss**) |
| 74 | Import a `.txt` with NUL bytes (single file) | the document opens and the box names it; the package holds U+FFFD | the editor shows the text up to the NUL; the package holds U+0000 |
| 75 | Import the `.txt` and a `.pdf` whose text has code 0 (two files); then open each | no box at import; one box per document on first open | no box; cut text |
| 76 | Export BRL of `alpha` to a new file; Export HTML; compare with N-f7's output of the same workspace | identical bytes (CRLF) and no `.tmp` in the folder | reference |
| 77 | Export BRL over an existing `old.brl` held open by `lock.py` (share read+write) | `匯出文件失敗：[WinError 5] ...`; `old.brl` unchanged; no `.tmp` | the export succeeds and rewrites the file under the holder |
| 78 | Export All BRL into a folder where `beta.brl` is held open (share read+write), Overwrite: Yes | the summary lists `beta` as failed; `alpha.brl` written; `beta.brl` unchanged | all written |
| 79 | `config.json` = `null`; start | the main window appears with defaults; change the font size (Ctrl+wheel or Settings); `config.json.bak` = `null`; `config.json` holds the font size | no main window; the process exits (record how) |
| 80 | `config.json` with a UTF-8 BOM and font size 20; start; change the width in Settings | font size 20 at start; afterwards the file holds both values, no BOM, CRLF; no `.bak` | font size default; the change leaves only the width |
| 81 | `config.json` held open by `lock.py` with share **none**; start; change the font size; release; restart | starts with defaults; after the change the file is byte-identical; `log\config.log` has `was not saved because it could not be read`; restart reads the old values | the file is replaced with the font size only (or record the actual result) |
| 82 | Dictionary Management: Add `d1`; Import a valid CSV `d2`; Export `d1` over an existing file; Text Processing: Apply a script | dictionary files byte-identical to N-f7's for the same steps; no `.tmp` in `dictionary\` or the export folder; the export target replaced | reference |

Never touch a real workspace; every item builds its own. Item 81 holds `config.json` with share none only in its own folder.

Manual items for the user (the implementation adds them to the user's list; never ticked by an agent):

- **83 (NVDA).** In a copy of the F-8 build, with NVDA running, open the workspace of item 73 and the one of item 70. Record what NVDA reads for the `已取代字元` box (in particular how it speaks the replacement character) and for the `已復原文件` box, and whether the focus goes to the source editor after OK.
- **84 (optional).** Item 34's small VHD filled to a few KB free: export a large BRL over an existing file; the old file must stay intact and the message must name the disk-full error.

## Risks

- **An export over a file another program holds open now fails** (medium, O6). `os.replace` refuses any open target, so an export over a file that an embosser program or editor keeps open fails with `[WinError 5]` where a sharing holder let it through before. The message is shown, the old file is kept, and the user can close the other program and export again. Same trade as F-3 Q1.
- **Hidden or read-only targets** (low, F-3 D11). Hidden exports, dictionary files, scripts and `config.json` are replaced and lose the attribute; read-only ones are refused as before.
- **Temporary files in the export folder** (low). An export briefly creates `.<name>.<16 hex>.tmp` next to the target (also on USB sticks and network shares). A program that watches the folder may see it; it is normally removed or renamed within the export. Corrected after the F-8a review (2026-10-10, M-4): if a scanner such as antivirus software holds the temporary file open at the moment of `os.replace`, the export fails (`[WinError 32]`), the old file stays intact, and the temporary file is left behind, because removing it fails too (`shared/atomic_write.py` ignores that error, as it has for packages since F-3); the user can delete it by hand. Retrying the removal is a follow-up.
- **A folder where files can be overwritten but not created** (very low; F review). Atomic writes need to create the temporary file there.
- **Recovery restores a document the user had deliberately renamed** (low). Only when the Rename was interrupted by a crash: the document comes back under its old name, as a failed Rename leaves it (F-3). The staged copy duplicates it and is deleted (step 7).
- **A leftover that holds the only copy of its text can be recovered at a later start** (low; added after planning F-8b, narrowed by the user's decision of 2026-10-10, see "Corrected after planning (F-8b)" 9 and 10). Every other skipped leftover is deleted at the start that skips it. A skipped leftover whose content no package holds (class L4: the newer text of an interrupted Save, a leftover behind a kept invalid package) stays, and comes back at a later start once its own name is free: the user renames or deletes that document, or deletes the invalid package. Nothing is lost; the box names it.
- **Two different documents with identical content** (low, empty documents; corrected after the F-8b review, M-6). If the interrupted document's text and braille are identical to another listed or recovered document's, it is not recovered (rule 4) and its leftover is deleted (step 7): no text is lost, but the document and its name are. This is not rare for empty documents (`new` and `new (2)`) or two imports of the same file under different names. The content rule cannot tell this case from the aside file of a completed Rename, which must be skipped.
- **A name freed in the invalid-files dialog is recovered one start later** (low; F-8b review M-7). Recovery runs inside the load, before the invalid-files dialog. A valid leftover whose name an invalid package holds is skipped and kept (L4); if the user then chooses "Delete Invalid Files", the leftover is recovered at the next start, with the box. Nothing is lost. Recovering it at once would need a second service call after the dialog and a change of the startup order; not done.
- **The newer text of an interrupted Save is not offered** (low, D3). It is the same as edits lost in a crash; the `.tmp` stays on disk for manual recovery.
- **A document that is only exported, never opened, is exported with U+FFFD without a notice** (low, D13).
- **Many U+FFFD from a UTF-16 file without BOM** (low). Every ASCII character is followed by U+FFFD; the notice's count makes the wrong encoding obvious. Detecting UTF-16 is out of scope.
- **`config.json` stays locked** (low, D11). Setting changes apply for the session but are not saved until the file can be read again; `config.log` says why.
- **`config.json.bak` holds a damaged file** (by design). The app never reads it.
- **Thread race on `config.json`** (unchanged, known): `get_or_create_client_id` on the client-init thread.

## Open Questions

None blocking. U1 and U2 are the user's (2026-10-10).

Decided by orchestrator with the recommended default; user may override before merge:

- **O1.** Split into F-8a (no strings) and F-8b (notices and 4 msgids), in that order (Goal, Migration Steps).
- **O2.** The default document takes `new (2)`, `new (3)`, ... when `new.dep` is on disk but not listed (D2).
- **O3.** Interrupted packages are recovered automatically at startup and reported in one information box (D3, D4). (Before the F-8b review: "nothing is ever deleted, and duplicates are left on disk"; the user decided on 2026-10-10 that the unused leftovers are deleted, D3 step 7.)
- **O4.** `config.json`: a damaged file is copied to `config.json.bak` before the first change replaces it; an unreadable file is not overwritten; a BOM is accepted; a non-object counts as damaged (D10, D11).
- **O5.** The U+0000 notice is a warning box shown the first time each affected document is opened in a session, not a startup summary (D13).
- **O6.** Exports become atomic and therefore fail over a target that another program holds open, like F-3 Q1 for packages (D8, Risks).
- **O7.** U+0000 is not replaced in `_encodable` / `prepare_document_for_save` (D12).
- **O8.** At startup, a skipped leftover whose content no package holds (class L4) is kept, not deleted: it is the only copy of that text (D3 step 7, "Corrected after planning (F-8b)" 10). The literal reading of the user's decision would delete it too.

Raised by the F-8b plan: whether a leftover that recovery skipped may be recovered at a later start ("Corrected after planning (F-8b)" 9). Decided by the user on 2026-10-10: the leftovers that recovery decides not to use are deleted ("Corrected after planning (F-8b)" 10); keeping the only copy of a text is O8.

## Out of Scope / Follow-ups

- **U+0000 in dictionary entries.** Python 3.13's `csv` reads `a\x00b` (measured); the entries editor's text field would cut it, and OK would save the cut entry. A dictionary task should apply the same replacement when entries are loaded.
- **U+0000 in the text-processing script.** The script editor would cut it; `ast.parse` already refuses such a script at conversion.
- **U+0000 returned by the user's text-processing script** into the braille output.
- **Unifying the temporary-name schemes** (F review M-3/M-4) and cleaning up other leftover `.tmp` files (export, dictionary and `config.json` writers; not planned). The package leftovers that startup recovery does not use are deleted since the F-8b review fix (the user's decision of 2026-10-10, D3 step 7).
- **The startup boxes come before the main window is shown** (F-8b review M-8): the recovery box and the first document's U+0000 box are owned by a frame that is not shown yet, as the invalid-files dialog has been since F-3. Deferred to F-12 (UI polish); manual item 83 checks what NVDA reads.
- **Offering the newer text of an interrupted Save.**
- **`dual_view/files.write_dual_view_html`** (app-owned temporary page).
- **UTF-16 text import** (with BOM: today an import issue; without BOM: many U+FFFD).
- **The `config.json` read-modify-write race** between the UI and the client-init thread.
- Everything else in `task.md` (F-9 to F-12).
