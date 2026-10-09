# Atomic `.dep` Writes (F-3) Design

## Goal

Fix task F-3 fixes two priority-2 defects in the document workspace:

1. **Save truncates the `.dep` in place (data loss).** `save_document_package` opens the package with `zipfile.ZipFile(path, "w")`, which truncates the file and then writes the members one by one. A failure part-way leaves a broken package: a crash or power loss, a full disk, or a `UnicodeEncodeError` from a lone surrogate in the text. On the next start `load_workspace_documents` reports it as invalid and the startup dialog offers to delete it. Every document switch saves, so this is the most exposed writer in the app. Source: the F review, section 4 and the first row of "剩餘缺陷清單" (`docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md`), and HANDOFF 4.4 (`docs/superpowers/history/2026-10-09-02-handoff/HANDOFF.md`). No test pins it today.
2. **Regular Rename leaves two packages when the old one cannot be deleted (data inconsistency).** A regular (not case-only) rename writes `gamma.dep`, then unlinks `beta.dep`. If the unlink fails, both packages stay on disk while memory keeps only `beta`; the next start lists both. Source: P1-3 known defect 3 (`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`, "既有缺陷清單"). Pinned by the `KNOWN BUG` tests `test_rename_unlink_failure_leaves_both_packages_and_state` (GUI) and `test_rename_unlink_failure_propagates_and_leaves_both_packages` (service), and guarded by `test_regular_rename_does_not_use_package_files` (F-1 D6).

After this task:

- Every write of a `.dep` (Save, Add, Import, the default document, Export as DEP) goes to a new temporary file in the same folder, is flushed to disk, and is installed with `os.replace`. On any failure the package on disk is byte-identical to before (or still absent), and no temporary file is left.
- Every Rename, regular or case-only, uses F-1's `move_document_package`: stage the new package, move the old one aside, install the new one, then remove the moved-aside file. A failure at any step leaves exactly one package (the old one) and an unchanged document list.
- A package the user may not write (Windows read-only attribute, no POSIX write permission) is never replaced or removed by Save or Rename: they fail with `[Errno 13] Permission denied: '<package>'`, the message Save already gives today.
- The UI boundary of Save, Add and Rename catches every `Exception`, not only `OSError`, with the existing `Failed to save document: {error}` message (F review M-1). Import reports any save error as an import issue.

No new user-facing string; msgids unchanged (353, same set). F-W10 (a read-only or locked open `.dep` blocks Rename and Close) stays out of scope; this task changes only which lock modes cause it (D12).

## Corrected after planning (2026-10-09)

Planning (`docs/superpowers/plans/2026-10-09-f3-dep-atomic-write.md`, dry-run on scratch clones) found no error in the decisions D1-D13; the items below record the open questions as decided and the places where the plan refines this spec. Where they differ, these items win.

1. **Q1 and Q2 are decided** by the orchestrator with the recommended defaults (2026-10-09); the user may override either before the merge. **Q1: accept.** A `.dep` held open by another program in any share mode now blocks Save, and every action that saves first (Close included), until that program releases it. **Q2: refuse.** A read-only package cannot be renamed, regular or case-only: `[Errno 13] Permission denied: '<package>'`, and nothing is left on disk.
2. **Baseline with the runtime copied.** The worktree has no git-ignored liblouis runtime, MathCAT or submodule `configure.ac`, hence its baseline `Ran 1138`, `errors=2`, `skipped=7` (Current State). The plan's Task 0 copies those build products from the main checkout (same submodule commit `2aa5f84b`; `louis_helper.py` is byte-identical to `vendor/nvda/liblouis/runtime/louis_helper.py`); the worktree then has the main checkout's baseline (`Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)`), `git status` stays empty, and the `test_liblouis_runtime` error of acceptance criterion 1 does not occur.
3. **37 new tests instead of 34.** Added: `test_rename_of_a_package_held_open_by_another_program` (service, Windows-only, all four share modes: without delete sharing the rename fails with `[WinError 32]` and only the old package stays, where before F-3 both stayed; with delete sharing it completes), `test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package` (service) and `test_startup_ignores_leftover_temporary_files` (GUI, D13 at the startup dialog). A11 and B7 cover the four share modes read, read+write, read+delete and read+write+delete as subtests. Windows-only tests: 8. Expected after the last step: `Ran 1180`, `FAILED (failures=1, errors=1, skipped=7)` (1175 without the runtime copy); after merging `main` at `4953772` (P2-5): `Ran 1248`, `FAILED (errors=1, skipped=7)`, the only error F-W6. This replaces "Expected: worktree `Ran 1172` (main checkout 1177)" in Counts.
4. **Six commits.** A test-only first commit holds the five tests that pass on today's code (B6, B9, B10, B11 and the GUI startup test); the five migration steps follow, each red first. Subjects end with `(F-3)`.
5. **Test helper.** `client/tests/windows_file_handles.py` also provides `SHARE_MODES` (the four modes), `make_read_only` (its clean-up clears the attribute only if the file still exists), `make_hidden` and `is_hidden`; `hold_open` returns a `release` function, so a test can close the handle before it inspects the folder.
6. **Import test.** It fails the second of two documents (`delta` after `beta`), not `beta`, so the old code shows the worse result: `beta.dep` written but never added to the list.
7. **GUI flip.** The GUI module defines its own `_FailingReplacePackageFiles(source_name=...)`; importing the service test module would make `unittest` collect its tests twice.
8. **Acceptance criteria 4 and 8** compare with the merge base (`git merge-base main HEAD`), not `main`, which already contains P2-5. Criterion 4's "no new `_(`/`N_(` literal" applies to production code; the tests call `gui._()` with existing msgids.
9. **Windows verification.** The exe goes to `D:\dxtest\N-f3\DotExpress.exe` (orchestrator), not `D:\dxtest\F3\`. The 2026-10-09-03 scripts are not copied or edited: a wrapper `rerun.py` runs items 18, 19 and 21 with the exe and work folder replaced in memory (19 and 21 start from a copy of item 18's folder), `item20b.py` takes arguments already, and items 30-33 are new scripts; all are in `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/`. Each item runs in a new `D:\dxtest\auto<N>-f3` folder. The build uses the main checkout's `client\.venv` on `PATH` (the worktree has none); a build of the planned code in a scratch clone succeeded and bundled the clone's own modules. Item 34 stays manual and optional.

## Current State (verified 2026-10-09 on `fix/f3-dep-atomic-write`, HEAD `d4a7aa1`, Windows 11 26200, NTFS)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13.15). `$SP` is the session scratchpad; the prototypes used below are in `$SP\f3spec\` (`probe.py`, `probe2.py`, `probe3.py`, `lock.py`).

Baseline: in the worktree, `cd client && $PY -m unittest discover -s tests` gives `Ran 1138 tests`, `FAILED (failures=1, errors=2, skipped=7)`. The failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`; the errors are F-W6 (`test_dictionary_name_prompt ... test_case_only_rename_still_renames`, `FileExistsError` on NTFS) and `test_liblouis_runtime` `setUpClass` (the worktree has no generated `braille/louis_helper.py`). In the main checkout the same suite gives `Ran 1143`, `failures=1`, `errors=1`, `skipped=5`. The focused modules (`tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller`) give `Ran 264`, `OK (skipped=4)` (the four POSIX-only permission tests).

### Every `.dep` write

| Caller | Path | Writes with | Failure today |
| --- | --- | --- | --- |
| `DocumentWorkspaceService.save_open_document` (`documents/workspace_service.py:78-85`) | Save before every document action and before Close | `save_document_package(package_path(open name))`, after `controller.replace_document` (memory first, the documented contract) | truncated package |
| `create_document` (`:87-89`) | Add, the default `new` document | `save_document_package`, then `controller.add_document` | partial new package (only matters if one existed: an invalid package kept at startup) |
| `import_files` (`:91-108`) | Import | `save_document_package` per document; `except OSError` becomes a `BatchIssue` | partial new package; a non-`OSError` escapes and skips `controller.add_documents` for the documents already written |
| `rename_document`, regular (`:124-128`) | Rename `beta` to `gamma` | `save_document_package(gamma.dep)`, then `beta.dep.unlink()` | write failure: partial `gamma.dep`; unlink failure: both packages (defect 3) |
| `rename_document`, case-only (`:116-123`) | Rename `Alpha` to `alpha` | `move_document_package` (F-1) | safe; see below |
| `PackageFiles.write` (`documents/workspace.py:79-80`) | the staged file of `move_document_package` | `save_document_package(staged path)`; no `fsync` | staged file removed, old package kept |
| `formats._write_dep` (`documents/formats.py:89-94`) | Export as DEP to a user-chosen path | `save_document_package(path, include_pending_metadata=False)` | truncated export (the user confirmed overwriting it) |

`save_document_package` (`documents/workspace.py:54-70`) normalizes the name, creates the folder, and writes `<name>.txt`, `<name>.brl` and, for pending braille, `<name>.meta.json` with `ZIP_DEFLATED`. `zipfile` opens a path for mode `"w"` with `open(path, "w+b")`, which on Windows is `CREATE_ALWAYS`.

`move_document_package` (`:101-156`, F-1 D4 and the M-3 fix) stages the new package in `PackageFiles.temporary_path` (`tempfile.NamedTemporaryFile(prefix=".<name>.", suffix=".tmp", delete=False)`, closed at once), moves the old package aside to another such file, copies the permission bits (POSIX), installs with `os.replace`, then removes the aside file and ignores a failure there.

`load_workspace_documents` (`:221-231`) lists `directory.glob("*.dep")`. Checked with `probe2.py`: `.alpha.dep.0123456789abcdef.tmp` and `..alpha.dep.x.tmp.y.tmp` are not listed and not reported invalid.

### The UI boundary (`client/gui.py`, tabs)

| Handler | Catches | Message |
| --- | --- | --- |
| `_save_open_document_with_feedback` (`:596-602`), used before Open, Ctrl+Tab, Add, Rename, Delete, Delete All, Import, Export, Export All, Ctrl+E and by `_on_close` (`:956-969`, which vetoes when it returns `False`) | `OSError` | `Failed to save document: {error}` (`儲存文件失敗：{error}`) |
| `_create_document` (`:617-635`) | `OSError` | same |
| `on_rename_document` (`:741-767`, `except` at `:760`) | `OSError` | same |
| `on_delete_document` (`:785`), `delete_all_documents` (`workspace_service.py:142`) | `OSError` | `Failed to delete document: {error}` |

A non-`OSError` (realistically `UnicodeEncodeError`) escapes the wx handler: nothing is shown; in `_on_close` the event is neither vetoed nor skipped, so the window stays open without a message.

### Windows NTFS measurements (prototypes, real files)

A second process (`lock.py`) or the same process (`probe2.py`, `probe3.py`) opens the target with `CreateFileW(GENERIC_READ, share)`. "Old" is today's code, "new" is the design below.

| Target condition | `open(path, "w+b")` (old Save) | `os.replace(tmp, target)` (new Save) | `os.replace(target, aside)` (move aside) | `unlink(target)` (old regular Rename) | `os.access(W_OK)` |
| --- | --- | --- | --- | --- | --- |
| read-only attribute | `[Errno 13] Permission denied: '<target>'` | `[WinError 5]` | succeeds | `[WinError 5]` | `False` |
| open, share read | `[Errno 13]` | `[WinError 5] ...: '<tmp>' -> '<target>'` | `[WinError 32] ...: '<target>' -> '<aside>'` | `[WinError 32]` | `True` |
| open, share read+write | **succeeds** (rewrites under the reader) | `[WinError 5]` | `[WinError 32]` | `[WinError 32]` | `True` |
| open, share read+write+delete | succeeds | `[WinError 5]` | succeeds | succeeds | `True` |
| open, share read+delete | `[Errno 13]` | `[WinError 5]` | succeeds | succeeds | `True` |
| hidden or system attribute | `[Errno 13]` (`CREATE_ALWAYS` refuses a hidden/system file) | succeeds; the attribute is gone | succeeds | succeeds | `True` |
| ACL denies write data, allows delete | `[Errno 13]` | succeeds; the deny ACE is gone | - | - | `True` |
| a non-empty directory (the tests' `_block`) | error | `[WinError 5]` | **succeeds** (Linux: `ENOTDIR`) | error | `True` |
| `Alpha.dep` exists, target spelled `alpha.dep` | - | succeeds; the entry is named `alpha.dep` | - | - | - |

`os.replace` is `MoveFileExW(MOVEFILE_REPLACE_EXISTING)`: it refuses a destination that any handle has open, **even with `FILE_SHARE_DELETE`**, and a read-only destination. Moving a file aside needs only delete access to it, so it works on a read-only file and under a delete-sharing holder. Windows error texts are localized in the packaged zh-TW build (`存取被拒。`, `程序無法存取檔案，因為檔案正由另一個程序使用。`); `[Errno N]` texts come from the C runtime and stay English.

Today's Save under faults (`probe2.py`): a lone surrogate in the text or in the braille, and `ENOSPC` raised on the second member, each leave `alpha.dep` as a valid zip without its `.txt` member, which loads as `ValueError: Document package must contain one .txt and one .brl file.` (`ZipFile.__exit__` still writes the central directory). The old text is lost; the next start offers to delete the package. With the design below the same three faults leave `alpha.dep` byte-identical and loadable.

`os.fsync` plus `os.replace` of a 2 KB file costs a median of 1.0 ms here (30 runs, max 2.8 ms). Writing the zip to a stream opened `"wb"` gives exactly the same bytes as writing it to the path when the timestamp is the same (`probe2.py`, `time.time` patched).

Today's regular rename vs `move_document_package` (`probe3.py`, renaming `beta` to `gamma`):

| `beta.dep` is | today | `move_document_package` (no write check) |
| --- | --- | --- |
| open, share read or read+write | `[WinError 32] ...: '<beta.dep>'`; **`beta.dep` and `gamma.dep`**, both listed at start | `[WinError 32] ...: '<beta.dep>' -> '<.beta.dep.x.tmp>'`; only `beta.dep` |
| open, share read+write+delete | renamed | renamed |
| read-only | `[WinError 5] ...: '<beta.dep>'`; **both packages** | renamed, and a read-only `.beta.dep.<random>.tmp` stays (cannot be deleted) |
| hidden | renamed (the new package is not hidden) | same |

### Real GUI findings (`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`)

- 18 (case-only rename, restart, duplicates) passed. 21 (Defender on, 10 case-only renames) had no transient failure and no `.tmp`.
- 19: with `alpha.dep` held open with share read, the Save **before** the rename already failed (`[Errno 13]`), so the name dialog never appeared; with share read+write the Save succeeded and the case-only rename failed with `[WinError 32] ... 'alpha.dep' -> '.alpha.dep.<random>.tmp'`. List and content unchanged, no `.tmp`.
- 20: with `alpha.dep` read-only, the Save before the rename failed (`[Errno 13]`), so F-1's "rename leaves a read-only `.tmp`" path was not reached through the open document; Close was vetoed by the same Save failure (F-W10).
- F-W10: a read-only or share-read-locked open `.dep` makes every action that saves first fail, including Close; unmodified documents are rewritten before those actions too.
- 27 (F-2, dictionaries): replacing a hidden file succeeds and drops the hidden attribute (F review M-8).

### Tests that pin the defects

- `tests/test_gui_document_flows.py:2071` `test_rename_unlink_failure_leaves_both_packages_and_state` and `tests/test_workspace_service.py:293` `test_rename_unlink_failure_propagates_and_leaves_both_packages`: `KNOWN BUG (P1-3 spec, known defect 3)`. Both make the old package a non-empty directory (`_block`) so the unlink fails.
- `tests/test_workspace_service.py:366` `test_regular_rename_does_not_use_package_files`, with `_UnusablePackageFiles` (`:44-50`): the F-1 D6 guard; it must flip.
- Nothing pins the truncating Save.

## Decisions

**D1. A binary variant of F-2's helper, not `PackageFiles` staging, for Save.** `client/shared/atomic_write.py` gets `write_bytes_atomically(path, write)`, with the same steps and guarantee as `write_text_atomically` (F-2 D4 and its corrections): write check, a new `.<name>.<16 hex>.tmp` created with `O_EXCL` and mode `0o666` in the target's folder, `write(stream)`, `flush`, `fsync`, close, POSIX mode copied from the existing target, `os.replace`, temporary file removed on every failure (`finally`, any `BaseException`). The two variants share one private core; the text variant's behavior and its 15 tests stay unchanged. Reasons:

- It already has everything Save needs and F-1's staging lacks: `fsync` before the rename (without it a power loss right after the rename can leave an empty package, the failure this task removes), the write-access verdict of an in-place write (D3), `0o666` creation so the kernel applies the umask (`NamedTemporaryFile` gives `0600`, F review M-3), and the temporary path recorded before anything is written.
- Save replaces the file in one `os.replace`. Reusing `move_document_package` with the same old and new path would add a window with no `.dep` at all (between moving the old package aside and installing the new one) to the most frequent write in the app. It would also make Save succeed under delete-sharing holders, where a plain replace fails (see the table); that is the only advantage, and Defender, the realistic delete-sharing holder, caused no failure in items 21 and 28.
- One helper for both text and binary keeps one implementation of the rules F-2 fixed after review (descriptor ownership, umask, `O_EXCL` name loop).

Rejected: `ReplaceFileW` through `ctypes` (keeps attributes and ACLs, but is Windows-only, has its own partial-failure codes, and cannot be tested on Linux); a timed retry (F-2 D8).

**D2. `save_document_package` writes through the helper.** It keeps its signature, the name normalization, `package_path.parent.mkdir(parents=True, exist_ok=True)` and the return value. The zip is written by a new private `_write_package(stream, document, *, include_pending_metadata)` holding today's three `writestr` lines; `save_document_package` calls `write_bytes_atomically(package_path, lambda stream: _write_package(...))`. `zipfile.ZipFile(stream, "w")` does not close a stream it was given, so the helper flushes and syncs the complete archive. The bytes are identical to today's for the same timestamp (checked). Every caller in the table above gets the atomic behavior without a change, Export as DEP included.

**D3. The write-access verdict is kept, and shared.** Step 0 of `write_text_atomically` (if the target exists and `not os.access(target, os.W_OK)`, raise `PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(target))`) becomes a public `ensure_writable(path)` in `shared/atomic_write.py`, used by both write variants and by D7. Effect on Save: a read-only package still fails with exactly `[Errno 13] Permission denied: '<package>'`, the text `zipfile` gives today (measured), and nothing is created. Without it, `os.replace` would fail anyway with `[WinError 5]` naming the temporary file, but on POSIX a `0444` package would be replaced.

**D4. The staged file of a move is written directly and synced.** `PackageFiles.write(path, document)` stops calling `save_document_package` (which would now stage a second temporary file inside the first) and writes the package into the given new private file: `open(path, "wb")`, `_write_package(..., include_pending_metadata=True)`, `flush`, `fsync`, with the same name normalization as `save_document_package`. The atomic step of a rename is the install `os.replace`; the `fsync` makes the installed package durable before the old one is removed, as Save's is.

**D5. Every Rename goes through `move_document_package` (fixes defect 3).** `rename_document` drops its case-only branch and calls `move_document_package(package_path(source), package_path(new), Document(new, source.text, source.braille), files=self._package_files)` for every rename, then `controller.rename_document`, as the F review and F-1 D6 recommend. The `ValueError` for an identical name stays. Results:

- The old package cannot be moved aside (another program has it open without delete sharing): nothing is installed, the staged file is removed, the error propagates, the controller is unchanged. One package, the old one.
- Install fails: the old package is moved back, the staged file removed. One package.
- Removing the moved-aside file fails: ignored, as in F-1 (the rename is complete; the leftover `.tmp` is never loaded). With D7 this no longer happens for a read-only package; it can still happen if another program opens the aside file in the millisecond between the two calls.
- Aliasing that `casefold()` misses (F-1 D8: NTFS upcase table, APFS normalization) can no longer delete a package on Rename, because nothing is removed under a name that can alias the new one.

Rejected alternative: "install the new package, then unlink the old one, and remove the new one again if the unlink fails". It keeps today's message text and turns a crash between the two steps into two listed packages rather than none, but an aliasing pair it does not detect replaces and then deletes the same file (the F-1 defect-1 mechanism), and it is a second sequence next to F-1's. Data safety on every non-crash path outweighs the message text (D6) and the crash window (Risks).

**D6. Error texts may name temporary paths (F-1 D6, first question).** A failed regular rename now shows, for example, `儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '...\beta.dep' -> '...\.beta.dep.k2j1abcd.tmp'` instead of `...: '...\beta.dep'`; a failed Save shows `儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<16 hex>.tmp' -> '...\alpha.dep'` instead of `[Errno 13] Permission denied: '...\alpha.dep'`. The template is unchanged and the package name is still in the text. Accepted as in F-1 D4 and F-2 D5: the text after the template is Python's error text in every existing case; rewriting it would need new strings.

**D7. A package the user may not write is never renamed (F-1 D6, second question).** `PackageFiles` gets `ensure_writable(path)` (calls D3's function), and `move_document_package` calls `files.ensure_writable(old_path)` before staging. A read-only package (Windows attribute; on POSIX, no write permission for this user) is refused with `[Errno 13] Permission denied: '<old package>'`, and nothing is created or moved. This applies to case-only renames too. Reasons: Save already refuses such a package with the same text (D3), and Delete refuses it on Windows (`[WinError 5]`), so the rule becomes "the app never replaces or removes a package the user marked read-only"; it never leaves a read-only `.tmp` that the app cannot delete (the measured result without the check); and it never silently drops the read-only attribute, which the renamed package would not carry (new files have default attributes). Visible changes: a regular rename of a read-only package used to fail too, with `[WinError 5]` and two packages left; it now fails with `[Errno 13]` and one package. A case-only rename of a read-only package that is not the open document used to succeed and leave a read-only `.tmp`; it is now refused (Open question Q2). On POSIX a `0444` package could be renamed before; it is now refused (not a shipping platform). The model `CaseInsensitivePackageFiles` resolves the path before checking.

**D8. Defect-3 fault injection is redesigned (F-1 D6, third question).** `_block` (a non-empty directory as the old package) does not fail a move aside on Windows: `os.replace(directory, aside_file)` succeeds there (measured), while Linux raises `ENOTDIR`. The flipped tests therefore inject through `package_files`: a `PackageFiles` subclass whose `replace` raises `PermissionError(errno.EACCES, "injected", str(source), None, str(destination))` when `Path(source).name` equals a given name (string comparison, F-1 D5). The text is `[Errno 13] injected: '<...beta.dep>' -> '<...aside>'`, so the GUI assertion that the message contains `beta.dep` still holds. `_block` stays valid where it is used today for install failures (`os.replace(file, directory)` fails on both platforms: `IsADirectoryError` on Linux, `[WinError 5]` on Windows), and for Save, Add and Import failures (the replace onto the directory fails, the temporary file is removed).

**D9. Every `Exception` from a save is reported at the UI boundary (F review M-1).** In `gui.py`, `_save_open_document_with_feedback`, `_create_document` and `on_rename_document` catch `Exception` instead of `OSError`, with the same `_show_file_error(_("Failed to save document: {error}"), exc)` and the same return. `_on_close` therefore vetoes with a message instead of failing silently. In `import_files` the per-document `except OSError` becomes `except Exception` (the reason is `str(exc)`, as for `OSError`), so one unencodable document no longer aborts the batch after earlier documents were written but not added to the list. Same width and reasons as F-2 D7; `BaseException` still propagates. Delete and Delete All (`unlink` only) stay `OSError`.

**D10. No retry and no fallback for Save.** When `os.replace` fails (a program has the package open in any share mode, an antivirus is scanning it), Save shows the message, keeps the package and the edits in memory, and the user's next action retries. No in-place fallback (it is the defect), no move-aside fallback (D1). Same as F-2 D8.

**D11. File metadata follows F-2.** Save installs a new file:

| Property | Today (in-place) | After |
| --- | --- | --- |
| POSIX permission bits | kept | kept (copied before the replace); a new package gets `0o666 & ~umask`, as today |
| Windows read-only attribute | Save refused, `[Errno 13]` | Save refused, same text (D3) |
| Windows hidden / system attribute | Save refused, `[Errno 13]` (`CREATE_ALWAYS`) | Save succeeds; the attribute is dropped (as F-2 item 27) |
| Explicit ACL entries on the file | kept; a deny-write entry refuses Save | the folder's inherited ACL; a deny-write-allow-delete entry no longer refuses Save and is dropped (as F-2 item 29) |
| Alternate data streams (e.g. `Zone.Identifier`), owner, creation time | kept | not kept (new file) |
| Symbolic link at the package path | written through | replaced by a regular file |

For Rename: the renamed package is a new file today too; after the change it also keeps the old package's POSIX bits (F-1 M-3 `copy_permissions`), but if the old package is missing it is `0600` (`NamedTemporaryFile`, F-1 note; POSIX only). The workspace is per-user app data; none of this is expected to matter, and the hidden/system change turns a Save that could never succeed into one that does.

**D12. F-W10 is out of scope; its trigger set changes.** F-W10 (Close and Rename blocked by a failing Save; unmodified documents rewritten) needs its own decisions: skipping the write of an unchanged document needs a "last saved" record because memory is updated before the write, and closing without saving needs a new dialog and strings. F-3 does not change the control flow. Its exact effect on F-W10, for the open document's package:

| Package condition | Today | After F-3 |
| --- | --- | --- |
| read-only | blocks (`[Errno 13] ... '<pkg>'`) | blocks, identical text |
| open, share read (7-Zip style) | blocks (`[Errno 13]`) | blocks (`[WinError 5] ... '<tmp>' -> '<pkg>'`) |
| open, share read+write | does not block; Save rewrites the file under the other program | **blocks** (`[WinError 5]`) |
| open, share read+write+delete (antivirus, indexer style) | does not block | **blocks while the handle is open** (`[WinError 5]`) |
| hidden or system | blocks (`[Errno 13]`) | does not block; attribute dropped |
| ACL deny write, allow delete | blocks | does not block; entry dropped |
| unchanged document | rewritten before every action | rewritten (atomically) |

The added blocking cases are Open question Q1. A non-`OSError` from Save (D9) now blocks Close with a message; before, Close silently did nothing.

**D13. Temporary names.** Save's temporary file is `.<package name>.<16 hex>.tmp` (`.alpha.dep.0123456789abcdef.tmp`); the move keeps F-1's `NamedTemporaryFile` names (`.alpha.dep.<8 chars>.tmp`). Both start with a dot and end in `.tmp`, so `Path.glob("*.dep")` never lists them (checked; pathlib matching is pure Python on Windows, not 8.3 names) and the startup dialog never offers to delete them. A leftover can only come from a crash or a failed clean-up; it is harmless and can be deleted by hand. Unifying the two schemes (F review M-3, M-4) is a follow-up. A leading dot does not hide a file on Windows; the `temporary_path` docstring that says "hidden" is corrected (F review M-7).

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Save (`save_open_document`, before every document action and Close) | memory updated, then the package truncated and rewritten in place; a failure part-way leaves a broken package (invalid at next start, offered for deletion); `OSError` shown, others escape | memory updated (unchanged contract), then staged, synced and replaced; any failure leaves the package byte-identical, no `.tmp`; every `Exception` shown with the same template, action stopped |
| Add / default document (`create_document`) | package written in place, then added to memory; failure: nothing added, a partial file may remain | written atomically, then added; failure: nothing added, nothing new on disk (an existing file at that name is unchanged) |
| Import (`import_files`) | per document: write in place; `OSError` becomes an issue; other errors abort the batch (earlier packages on disk but not in the list) | per document: atomic write; any `Exception` becomes an issue with `str(exc)`; the batch continues |
| Regular Rename | write `gamma.dep` in place, unlink `beta.dep`; unlink failure: both packages, memory `beta` (defect 3) | refuse an unwritable `beta.dep` (`[Errno 13]`); stage `gamma`, move `beta.dep` aside, install `gamma.dep`, remove the aside file; any failure: only `beta.dep`, memory `beta` |
| Case-only Rename | F-1 move; a read-only package (not the open one) renamed, read-only `.tmp` left | same move, preceded by the write check: a read-only package is refused (`[Errno 13]`), nothing left; the staged package is synced |
| Close | Save; failure vetoes with the message; a non-`OSError` escapes (window stays open, no message) | Save; any failure vetoes with the message (lock cases as in D12) |
| Delete / Delete All | `unlink`; failure shown, nothing changed (Delete All reloads) | unchanged |
| Startup load | `glob("*.dep")`; broken packages offered for deletion | unchanged; `.tmp` leftovers never listed; Save can no longer produce a broken package |
| Export as DEP | written in place to the chosen path | written atomically to the chosen path (same messages; a hidden target is now replaced) |

## Failure Modes on Windows NTFS (Save of the open document unless stated)

"Message" is what the packaged zh-TW build shows (caption `錯誤`).

| Fault | Before: disk | Before: user sees | After: disk | After: user sees |
| --- | --- | --- | --- | --- |
| Package read-only | unchanged | `儲存文件失敗：[Errno 13] Permission denied: '...\alpha.dep'`; action blocked | unchanged, no `.tmp` | identical |
| Package open, share read (zip tool) | unchanged | `[Errno 13] Permission denied: '...\alpha.dep'`; blocked | unchanged, no `.tmp` | `儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`; blocked |
| Package open, share read+write | rewritten under the reader | nothing | unchanged, no `.tmp` | `[WinError 5]` as above; blocked (Q1) |
| Antivirus / indexer holds it (share all) at that moment | rewritten | nothing | unchanged, no `.tmp` | `[WinError 5]` once; the next action retries (none in 20 measured attempts, items 21 and 28) |
| Antivirus holds the new temporary file | - | - | unchanged; the `.tmp` may stay if its removal also fails (never loaded) | `[WinError 5]` or `[WinError 32]` naming the `.tmp` |
| Disk full | **broken package** (valid zip missing members) | `[Errno 28] No space left on device` (expected; verify) | unchanged; `.tmp` removed | same message; edits kept in memory |
| Lone surrogate in text or braille | **broken package** | nothing (exception escapes; Close silently does nothing) | unchanged, no `.tmp` | `儲存文件失敗：'utf-8' codec can't encode character '\ud800' in position N: surrogates not allowed`; action blocked |
| Crash / power loss during the write | **broken package**; next start offers to delete it | invalid-package dialog | the old or the new package, complete (`fsync` before the replace); possibly a `.tmp` leftover | nothing |
| Hidden or system attribute | unchanged | `[Errno 13]`; blocked | replaced, attribute dropped | nothing |
| ACL denies write, allows delete | unchanged | `[Errno 13]`; blocked | replaced, entry dropped | nothing |
| Rename (regular), old package open, share read or read+write | **both packages**; memory old name | `[WinError 32] ...: '...\beta.dep'` | only `beta.dep` | `[WinError 32] ...: '...\beta.dep' -> '...\.beta.dep.<rnd>.tmp'` |
| Rename (regular), old package read-only | **both packages** | `[WinError 5] ...: '...\beta.dep'` | only `beta.dep` | `[Errno 13] Permission denied: '...\beta.dep'` |
| Rename (case-only), old package read-only, not open | renamed, read-only `.Alpha.dep.<rnd>.tmp` left | nothing | unchanged | `[Errno 13] Permission denied: '...\Alpha.dep'` (Q2) |
| Rename, crash between move aside and install | (regular: not possible; case-only: no `.dep`, data in two `.tmp`) | document missing at next start | no `.dep` for this document, data in two `.tmp` (now for regular renames too) | document missing at next start; recoverable by hand (Risks) |

## Design per File

### `client/shared/atomic_write.py` (4 spaces)

- `ensure_writable(path: Path | str) -> None`: today's step 0, public, with a docstring ("the verdict an in-place `open(path, "w")` gives; a rename would not ask").
- `_open_temporary_file(destination, opener, **open_arguments)`: the name loop, passing `mode`, `encoding`, `newline` through to `open`.
- `_write_atomically(destination, write, **open_arguments)`: today's body of `write_text_atomically` after step 0 (opener recording the path, `write`, `flush`, `fsync`, POSIX `chmod`, `os.replace`, `finally` clean-up).
- `write_text_atomically(path, write, *, encoding="utf-8", newline="")`: `ensure_writable`, then the core with `mode="w"`. Same behavior and signature.
- `write_bytes_atomically(path, write: Callable[[BinaryIO], None]) -> None`: `ensure_writable`, then the core with `mode="wb"`. Docstring: same guarantee; the directory must exist.
- Module docstring: mention both variants.

### `client/documents/workspace.py` (4 spaces)

- Import `ensure_writable` and `write_bytes_atomically` from `shared.atomic_write`.
- `_normalized(document) -> Document` (the name normalization `save_document_package` does today) and `_write_package(stream, document, *, include_pending_metadata)` (today's `ZipFile` block, on a stream).
- `save_document_package`: D2.
- `PackageFiles.ensure_writable(path)`: D7. `PackageFiles.write`: D4, docstring "Write the package into the new private file ``path`` and flush it to disk." `temporary_path` docstring: "dot-prefixed `.tmp` file, never matched by `*.dep`" (M-7).
- `move_document_package`: `files.ensure_writable(old_path)` first; docstring adds the refusal and that it is used for every rename.

### `client/documents/workspace_service.py` (4 spaces)

- `rename_document`: D5 (one `move_document_package` call for both kinds). The `save_document_package` import stays (Save, Add, Import).
- `import_files`: `except Exception as exc` (D9).
- Module docstring: Save writes through a temporary file; every rename stages the new package and moves the old one aside before installing it.

### `client/gui.py` (tabs)

Three `except OSError as exc:` become `except Exception as exc:` (lines 599, 628, 760). Nothing else.

### `client/tests/case_insensitive_package_files.py` (4 spaces)

`ensure_writable(path)`: `super().ensure_writable(self.resolve(path))`.

### Not changed

`documents/controller.py`, `documents/formats.py`, `documents/export_coordinator.py`, the dialogs, `.po`/`.mo`, fixtures.

## What Stays Identical

- The package format and bytes for the same timestamp; member names; pending metadata; the loader and its checks.
- The memory-before-write order of Save, the write-then-add order of Add, the controller updates of Rename, Delete and Delete All.
- Every message template and caption; the text for a read-only package on Save.
- Case-only rename results on success (F-1 tests unchanged), Add/Rename duplicate checks.
- `write_text_atomically` behavior (its 15 tests unchanged).
- msgids (353, same set), `client/locales`, both fixture sha256 values.

## User-Visible Strings

No new or changed msgid. The visible differences are only the Python error text inside `{error}` (D6, D12) and messages now appearing for non-`OSError` failures (D9). No `.po`/`.mo` update is needed; acceptance checks that `git diff main -- client/locales` is empty.

## Test Plan

TDD: each step's tests are written first and fail for the stated reason, then the code turns them green. Test files keep their indentation (4 spaces in all files below). Every test uses temporary directories; nothing touches `client/dictionary/`, `client/workspace/` or `config.json`. Fault injection is through `package_files` (F-1 D5) or `patch` of `os` functions (`os.replace`, `os.access`, `os.fsync`; looked up at call time, unaffected by `wx_stub` module copies), never by patching `documents.*` module globals from GUI tests.

New helper `client/tests/windows_file_handles.py` (not a test module): `hold_open(test_case, path, share)` opens `path` with `CreateFileW(GENERIC_READ, share, OPEN_EXISTING)` through `ctypes` and registers `CloseHandle` with `addCleanup`; constants `SHARE_READ = 1`, `SHARE_READ_WRITE = 3`. Sharing checks apply to every handle, including the test's own process (measured). Windows-only tests that set the read-only attribute register `os.chmod(path, stat.S_IWRITE | stat.S_IREAD)` with `addCleanup` after the temporary directory's clean-up, so it runs first.

### A. Helper (`client/tests/test_atomic_write.py`, new class `WriteBytesAtomicallyTest`)

Red: `AttributeError: ... has no attribute 'write_bytes_atomically'` / `'ensure_writable'`.

1. `test_replaces_an_existing_file_with_the_written_bytes`: listing `["d.dep"]`, exact bytes.
2. `test_creates_a_file_that_does_not_exist`.
3. `test_disk_full_while_writing_keeps_the_original_bytes_and_leaves_no_temporary_file`: the callback writes, then raises `OSError(errno.ENOSPC, ...)`.
4. `test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file`: `os.replace` patched; the recorded source is in the same folder and matches `\.d\.dep\.[0-9a-f]{16}\.tmp`.
5. `test_interrupt_leaves_no_temporary_file_and_propagates` (`KeyboardInterrupt`).
6. `test_data_is_flushed_to_disk_before_the_replace`: at `fsync`, `os.fstat(fd).st_size` is the full length; `fsync` is called before `replace` (I-1 style).
7. `test_a_file_without_write_access_raises_permission_error_and_is_kept`: `os.access` patched to `False`; exact text `[Errno 13] Permission denied: '<path>'`; nothing created.
8. `test_ensure_writable_accepts_missing_and_writable_files_and_refuses_others`.
9. POSIX only: `test_keeps_the_permission_bits_of_an_existing_file` (`0o640`).
10. Windows only: `test_a_read_only_file_is_refused_with_the_in_place_verdict` (`os.chmod(path, stat.S_IREAD)`; exact `[Errno 13]` text; bytes unchanged; no `.tmp`).
11. Windows only: `test_a_file_held_open_by_another_handle_is_kept` (share read+write: `PermissionError` with `winerror == 5`; bytes unchanged; no `.tmp`).

### B. Packages (`client/tests/test_document_workspace.py`)

Save (`DocumentWorkspaceTest` or a new class `AtomicSaveDocumentPackageTest`):

1. `test_save_failure_from_a_lone_surrogate_keeps_the_existing_package` (subTests: text, braille): `UnicodeEncodeError`; bytes unchanged; listing `["alpha.dep"]`; loads. **Red today**: the package is left without its `.txt`.
2. `test_save_failure_while_writing_keeps_the_existing_package`: `zipfile.ZipFile.writestr` patched to raise `OSError(errno.ENOSPC)` on the second member. **Red**: broken package.
3. `test_save_install_failure_keeps_the_existing_package`: `os.replace` patched. **Red**: no exception today.
4. `test_save_installs_a_temporary_file_from_the_same_folder`: recorded `os.replace` source name matches `\.alpha\.dep\.[0-9a-f]{16}\.tmp`, destination is the package. **Red**.
5. `test_save_refuses_a_package_without_write_access`: `os.access` patched; exact `[Errno 13]` text; bytes unchanged. **Red**.
6. Windows only: `test_save_of_a_read_only_package_gives_the_old_message`: exact `[Errno 13] Permission denied: '<package>'`. Green today (pins D3).
7. Windows only: `test_save_of_a_package_held_open_keeps_it` (share read+write): `winerror == 5`; bytes unchanged; no `.tmp`. **Red**: today Save succeeds in place.
8. Windows only: `test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute`. **Red**: `[Errno 13]` today. Pins D11.
9. POSIX only: `test_save_keeps_the_permission_bits_of_the_package` (`0o640`). Green today (regression guard).
10. `test_save_writes_the_same_bytes_as_the_in_place_writer`: `time.time` patched to a constant; compared with a `ZipFile(path, "w")` reference written in the test. Green today (pins the format).
11. `test_load_workspace_documents_ignores_leftover_temporary_files` (`.alpha.dep.0123456789abcdef.tmp`, `.alpha.dep.k2j1abcd.tmp`). Green today (pins D13).

Move (`MoveDocumentPackageTest`):

12. `test_unwritable_old_package_is_refused_before_anything_changes`: `os.access` patched to `False`; `PermissionError` naming the old package; listing and bytes unchanged; no `.tmp`. **Red**: the move succeeds today.
13. Windows only: `test_read_only_old_package_is_refused_and_leaves_no_temporary_file` (case-only `Alpha` to `alpha` and regular `Alpha` to `gamma`, subTests). **Red**: today renamed with a read-only `.tmp` left.
14. `test_staged_package_is_written_directly_and_flushed_to_disk`: `PackageFiles().write(staged, document)` calls `os.fsync` on a descriptor whose size (`os.fstat`) is the full archive, and calls no `os.replace` (it writes the given file, no nested staging); the file loads. **Red**: no `fsync` today.

`_FailingPackageFiles` gets `ensure_writable` (delegating, with `_check("ensure_writable", path)`).

### C. Service (`client/tests/test_workspace_service.py`)

- `_FailingInstallPackageFiles` becomes `_FailingReplacePackageFiles(*, source_name=None, destination_name=None)` (D8 error text); the case-only install test passes `destination_name="alpha.dep"`. `_UnusablePackageFiles` is removed.
- **Flip** `test_rename_unlink_failure_propagates_and_leaves_both_packages` to `test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state` (`source_name="alpha.dep"`): raises; listing `["alpha.dep"]`; bytes and state unchanged. Comment: was the P1-3 known defect 3 `KNOWN BUG`, fixed by F-3. **Red**: today's path ignores `package_files` and renames.
- **Flip** `test_regular_rename_does_not_use_package_files` to `test_regular_rename_moves_the_old_package_aside_before_installing`: a recording `PackageFiles` subclass; the `replace` calls are exactly `alpha.dep -> .alpha.dep.*.tmp`, then `.gamma.dep.*.tmp -> gamma.dep`; listing `["gamma.dep"]`. **Red**.
- New `test_regular_rename_install_failure_puts_the_old_package_back` (`destination_name="gamma.dep"`). **Red**.
- New `test_rename_of_an_unwritable_package_is_refused` (`os.access` patched): `PermissionError` naming `alpha.dep`; listing and state unchanged. **Red**.
- New `test_save_failure_keeps_the_package_and_updates_memory`: `save_open_document(text="\ud800", ...)` raises; memory holds the edit (contract); the package bytes are unchanged. **Red**.
- New `test_import_files_reports_any_save_error_as_an_issue`: `patch.object(workspace_service, "save_document_package", side_effect=...)` raising `UnicodeEncodeError` for `beta` only; `delta` saved and added; the issue for `beta.dep` carries the error text. **Red**: the error escapes.
- `test_rename_write_failure_propagates_and_keeps_state` (`_block("gamma")`) stays; add a listing check `["alpha.dep", "gamma.dep"]` (the blocking folder, no `.tmp`).

### D. GUI flows (`client/tests/test_gui_document_flows.py`)

- **Flip** `test_rename_unlink_failure_leaves_both_packages_and_state` to `test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state`: the frame's service gets `package_files=` a local `_FailingReplacePackageFiles(source_name="beta.dep")` (as `_rename_alpha_case_only` does); events: the rename dialog, then the error box (template, contains `beta.dep`); listing `["alpha.dep", "beta.dep"]`; `beta.dep` bytes and state unchanged. **Red**.
- New `test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`: input `"x\ud800"`; `_save_open_document_with_feedback()` returns `False`; one error box starting with the template prefix and containing `surrogates not allowed`; package bytes unchanged. **Red**: the exception escapes and the package is broken.
- New `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`. **Red**.
- New `test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`: renaming the non-open `beta`, whose text in memory is `"\ud800"`; error box; listing and state unchanged. **Red**.
- New `test_add_failure_that_is_not_an_os_error_shows_the_message`: `create_document` patched on the frame's service instance to raise `ValueError("boom")`; error box `Failed to save document: boom`; nothing added. **Red**.
- New, Windows only: `test_rename_of_a_read_only_package_is_refused_with_the_save_message`: `beta.dep` read-only, not open; rename to `gamma`; error box containing `[Errno 13]` and `beta.dep`; listing `["alpha.dep", "beta.dep"]`; no `.tmp`. **Red**: today both packages remain.
- Unchanged and still green: `test_save_failure_reports_error_after_updating_memory`, `test_close_vetoes_when_save_fails`, `test_add_write_failure_shows_error_and_keeps_state`, `test_rename_write_failure_keeps_old_package_and_state`, the F-1 case-only tests.

### Counts

New: A 11, B 14, C 4, D 5 = 34; flips replace tests one for one. Expected: worktree `Ran 1172` (main checkout 1177). Windows-only: A10, A11, B6, B7, B8, B13, D-read-only (7, skipped on POSIX); POSIX-only: A9, B9 (2, skipped on Windows). On Windows the skip count rises by 2. The plan may adjust the counts; the spec's red/green intent is binding.

## Migration Steps (each step one green commit, red first)

1. `refactor: share the atomic write core and add a bytes variant`: A 1-11 (red: missing attributes). Text-variant tests unchanged and green.
2. `fix: save document packages atomically`: D2, D4, D13 docstring; B 1-11, B 14, C "save failure keeps the package". Red first: B 1-5, 7, 8, 14 and the service test.
3. `fix: refuse renaming a package the user may not write`: D7 (`ensure_writable` seam, model, `_FailingPackageFiles`); B 12-13. Red first: both.
4. `fix: route every rename through move_document_package`: D5, D8; the two flips, the guard flip, C install-failure and unwritable tests, D flip and the Windows read-only GUI test; module docstring. Red first: all of them.
5. `fix: report every save error at the document UI boundary`: D9; C import test, D 4 non-`OSError` tests. Red first: all five.

Each commit ends with the `Co-Authored-By` line from the brief and stages explicit paths only. No commit changes `.po`/`.mo`, fixtures, `client/dictionary/`, `client/braille/`.

## Acceptance Criteria

Run on Windows (the development machine) from `client/` with `$PY`.

1. Full suite: no failure or error other than the known P2-5 failure, F-W6 and (worktree only) the `test_liblouis_runtime` import error; `Ran` = baseline + 34.
2. Focused: `$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller -v` passes; the seven Windows-only tests run (not skipped).
3. If a shuffle harness is available (HANDOFF section 5), five seeds report only the known failures.
4. `git diff main -- client/locales` is empty; no new `_(`/`N_(` literal in `git diff main -- client`.
5. Both fixture sha256 values unchanged.
6. App data untouched: `client/dictionary/` sha256 identical before and after the suite; no `client/workspace/` or `client/config.json` created.
7. `git grep -n "KNOWN BUG (P1-3 spec, known defect 3" -- client/tests` finds nothing; the defect-4 marker remains.
8. `git diff main --stat` touches only `client/shared/atomic_write.py`, `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/gui.py`, the test files and helpers named above, and the spec/plan files.
9. Mutation check (plan): each mutant is caught by at least one test: `save_document_package` back to `ZipFile(path, "w")`; no `fsync` in the bytes core; no `flush`; clean-up only on `OSError`; temporary file in the system temp folder; no write check in `write_bytes_atomically`; the write check applied to a missing file; `PackageFiles.write` without `fsync`; `PackageFiles.write` back to `save_document_package` (nested staging; caught by B 14's "no `os.replace`" assertion); no `ensure_writable` in the move; regular rename back to write-then-unlink; each of the three GUI handlers back to `except OSError`; `import_files` back to `except OSError`.
10. Packaged GUI verification below, results appended to the implementation record.

## Windows Verification (packaged build)

Build per `docs/superpowers/history/2026-10-09-03-windows-verification/test.md` section 0.1, in this worktree: copy `client\braille\liblouis.dll`, `client\braille\liblouis\` and `client\mathcat\assets\` from the main checkout (as for build B; the submodule revision is the same), plus `vendor\nvda\liblouis\runtime\louis_helper.py` to `client\braille\`, run `scripts\build-dotexpress.bat`, copy `client\dist\DotExpress.exe` to `D:\dxtest\F3\`. Copy the scripts in `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` to the implementation's history folder, change only the hard-coded `EXE` to `D:\dxtest\F3\DotExpress.exe` and the data folder to `D:\dxtest\auto-f3*`, and run them in a separate venv with `pywinauto` and `psutil`. Compare zip members, not whole files (timestamps change).

| # | Script | Expected after F-3 | Before (N) |
| --- | --- | --- | --- |
| 18 | `item18.py` | unchanged: case-only rename keeps the document; duplicates refused; no `.tmp` | same |
| 19 r | `item19.py`, share read | the Save before the rename fails: `儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`; no name dialog; list, content unchanged; no `.tmp`; restart unchanged | `[Errno 13]` |
| 19 rw | `item19.py`, share read+write | **the Save fails as for share read** (Q1) | Save succeeded, rename failed `[WinError 32]` |
| 20 | `item19.py` second half and `item20b.py` (read-only open document) | unchanged: `[Errno 13] Permission denied: '...\alpha.dep'`; Close vetoed (F-W10) | same |
| 21 | `item21.py` (Defender, 10 case-only renames) | 10/10, no `.tmp` | same |
| 30 (new) | regular rename of the non-open `beta` while `beta.dep` is held open (share read, then read+write) | `儲存文件失敗：[WinError 32] ...: '...\beta.dep' -> '...\.beta.dep.<rnd>.tmp'`; list unchanged; only `beta.dep` (no `gamma.dep`, no `.tmp`); restart unchanged | `gamma.dep` and `beta.dep` both on disk and listed after restart |
| 31 (new) | regular and case-only rename of the non-open `beta`/`Beta` with `attrib +r` | `[Errno 13] Permission denied: '...\beta.dep'`; nothing changes; no `.tmp` | regular: `[WinError 5]`, both packages; case-only: renamed, read-only `.tmp` left |
| 32 (new) | `attrib +h` on the open document, type, switch document, restart | Save succeeds; content kept; the file is no longer hidden | Save failed `[Errno 13]`, switch blocked |
| 33 (new) | Defender on, 20 document switches with an edit before each | 0 failures expected; record any `[WinError 5]`; no `.tmp` | - |
| 34 (optional, manual) | app folder on a small VHD filled to a few KB free; paste a large text; switch document; restart | message (record the text, expected `[Errno 28] No space left on device`); after restart the package loads with the old text | broken package, offered for deletion |

Real 7-Zip remains manual (item 19 note): record which share mode it uses and therefore which row applies.

## Risks

- **Locked packages block Save in more cases** (medium, Q1). Programs holding the package open in any share mode now make Save fail where share read+write and read+write+delete holders did not before; every action that saves first, Close included, is blocked until the handle is closed. Safe (message, package and edits kept) and retried by the next action. Measured Defender behavior (items 21, 28) shows no transient failures.
- **Crash window in regular renames** (low). Between moving the old package aside and installing the new one (two consecutive same-folder renames, milliseconds) a crash leaves no `.dep` for the document; its data is in `.<old>.dep.<rnd>.tmp` and `.<new>.dep.<rnd>.tmp`, and the next start does not mention it (F review M-2). Before, a regular rename's crash windows left a broken new package next to the intact old one, or both packages. Accepted for alias safety (D5); M-2's startup recovery is the follow-up.
- **Restore failure** (very low). Install fails and moving the old package back fails too: the error is shown and the old package stays in its `.tmp`; memory is unchanged, so the next Save of that document (if it is open) writes it again.
- **File metadata** (low, D11). Hidden/system attributes, explicit ACL entries, alternate data streams and creation time are not kept by Save; a symbolic link is replaced by a file.
- **The write check** (low, D3/D7). `os.access` on Windows sees only the read-only attribute; an ACL that denies writing is not seen, and Save then replaces the file. A file made read-only between the check and the replace fails at the replace (`[WinError 5]`), safely.
- **Broader catch** (low, D9). A programming error during Save now shows a message instead of a traceback (the packaged build has no console either way). With a lone surrogate in the text, Close is vetoed with a message every time until the character is removed; before, Close silently did nothing and the package was broken.
- **Two temporary-name schemes** (low, D13). Both are dot-prefixed `.tmp`; never loaded.
- **Test time** (low). One extra `fsync` per Save: 1 ms median on this machine; on Linux the F review measured 50-70 ms per `fsync`. If the GUI flow tests slow down by more than 2 s on Linux, replace `os.fsync` with a no-op in their harness as F review M-6 did; `test_atomic_write` keeps the real call.

## Open Questions for the User (decided 2026-10-09, see "Corrected after planning")

**Q1. A `.dep` held open by another program now blocks Save in two more share modes.** Today Save rewrites the file in place when the other program allows writing (share read+write, with or without delete); after F-3 `os.replace` refuses any open target, so Save fails with `[WinError 5]` and the action (switch, rename, Close, ...) is blocked until that program closes the file, as already happens with zip tools that share read only. **Recommended: accept.** Writing under another program's open handle is what F-3 removes (that program may be reading a half-written archive), the failure is visible and safe, and the measured antivirus behavior shows no transient failures. Alternatives: (a) when the replace fails, fall back to moving the old package aside and installing (helps only delete-sharing holders; adds a no-`.dep` crash window to every such Save); (b) bring the F-W10 follow-up forward (skip writing unchanged documents; let Close exit without saving after a failed Save). **Decided: accept.** Decided by orchestrator with the recommended default; user may override before merge.

**Q2. A read-only package can no longer be renamed.** Both rename kinds refuse it with `[Errno 13] Permission denied: '<package>'` (D7). Today a regular rename of it fails with two packages left, and a case-only rename of a read-only package that is not the open document succeeds but leaves a read-only `.tmp` the app cannot delete. **Recommended: refuse**, matching Save and Delete, which already refuse it. Alternative: allow it by clearing the read-only attribute of the moved-aside file before deleting it; the renamed package would then lose the read-only attribute and later Saves would overwrite it. **Decided: refuse.** Decided by orchestrator with the recommended default; user may override before merge.

## Out of Scope / Follow-ups

- **F-W10**: skip the write of an unchanged document (needs a "last saved" record); offer to close without saving after a failed Save; a clearer message for locked files (new strings).
- **F review M-2**: at startup, find orphan `.<name>.dep.<rnd>.tmp` files without a matching `.dep` and offer to restore them (now relevant to regular renames too).
- **F review M-3/M-4**: make `PackageFiles.temporary_path` use the helper's `O_EXCL`/`0o666` name loop and stop pre-creating the aside file.
- **P1-3 defect 4** (Delete All rollback without a valid document), Delete/Delete All semantics: unchanged.
- **Other writers**: Export BRL/HTML (`write_text`), `config.json`, `save_preprocessing_script`, `dictionaries/manager.py` header writes and copies (F review section 4).
- **Export's non-`OSError` handling** (P1-4 defect 7): unchanged; Export as DEP only gains atomicity.
- **F-1 D8** for Add: a `.dep` on disk that is not in the list (kept invalid package) is still replaced by Add/Import of the same name.
- Keeping hidden/system attributes or ACLs on replace (`ReplaceFileW`): not planned unless the user asks.
