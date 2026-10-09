# Workspace Case Collisions (F-1) Design

## Goal

Fix task F-1 fixes the two priority-1 data-loss defects in the document workspace that the P2 phase review lists under "既有缺陷清單" (`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`, first two rows). Both were found during P1-3 (`docs/superpowers/specs/2026-10-08-p1-3-document-controller-design.md`, "Known defects", items 1 and 2) and are pinned by `# KNOWN BUG` tests:

1. **Case-only Rename loses the document** on case-insensitive file systems (Windows, default macOS). Renaming `Alpha` to `alpha` writes `alpha.dep`, which is the same file as `Alpha.dep`, and then unlinks `Alpha.dep`. The package is gone. Pinned by `test_case_only_rename_on_case_insensitive_file_system_deletes_package`.
2. **Add with a case variant overwrites another document.** Adding `Alpha` while `alpha` exists passes the case-sensitive duplicate check and overwrites `alpha.dep`. Pinned by `test_add_case_variant_on_case_insensitive_file_system_overwrites_package`.

After this task:

- Document names are compared without regard to case (`str.casefold()`) on every platform, in Add and in Rename, as Import already does. `Alpha` is refused while `alpha` exists. The refusal reuses the existing `Document "{name}" already exists.` message and re-prompt.
- A case-only Rename (`Alpha` to `alpha`) is allowed and keeps the document on every file system. On disk the package ends up as exactly `alpha.dep` with `alpha.*` members.
- Rename to a case variant of a *different* document (`beta` to `Alpha` while `alpha` exists) is refused like an exact duplicate. Today it overwrites `alpha.dep` on Windows; this falls out of the same check.
- The case-insensitive behavior is verified on Linux through a case-insensitive file model injected into the rename code, not only on Windows.

This is a behavior change on purpose, limited to case variants. No new user-facing string, no msgid change (353, same set). Every other flow (Save, Import, Delete, Delete All, regular Rename, its failure behavior) stays identical. Priority-2 defect 3 (Rename unlink failure leaves two packages) is **not** included (see D6).

## Current State (verified 2026-10-09 on `fix/f1-workspace-case-collisions`, HEAD `c8ecf66`, all P0-P2 tasks merged)

`$SP` is the session scratchpad, `$PY` is `$SP/venv/bin/python`.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1095 tests`, `FAILED (failures=1, skipped=9)`. The failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. The 9 skips are 7 Windows-only liblouis tests and the two `..._on_case_insensitive_file_system_...` tests in `tests/test_gui_document_flows.py` (Linux is case-sensitive). From the repo root, `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`. Fixtures: `client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.

### Duplicate checks

- `documents/session.py:52-53` (tabs) `document_name_exists(documents, name, exclude_name)` compares **exactly**: `document.name == name and document.name != exclude_name`. `DocumentController.document_name_exists` (`documents/controller.py:70-71`) delegates to it. Its only production caller is `BrailleFrame._prompt_for_document_name` (`gui.py:637-658`), used by Add (`gui.py:733-739`, no exclude) and Rename (`gui.py:741-767`, `exclude_name=` the source name). On a hit it shows `_('Document "{name}" already exists.')` with the typed name, caption `_("Error")`, `wx.OK | wx.ICON_ERROR`, and reopens the dialog prefilled with the typed name.
- Import already compares casefolded names: `documents/workspace.py:152` and `:166-169` (`batch_import_documents`), with the issue text `Document "{name}" already exists.` naming the incoming name. Workspace sorting is also casefold-first (`load_workspace_documents`, `DocumentController.sort_documents`).
- `on_rename_document` returns early when the new name equals the source exactly (`gui.py:756`); a case-only change goes through to the service. The service refuses equal names with `ValueError` (`workspace_service.py:99-100`).

### Package files

- `save_document_package(path, document)` (`documents/workspace.py:50-66`) opens `path` with `zipfile.ZipFile(path, "w")` and writes `<name>.txt`, `<name>.brl` and, for pending braille, `<name>.meta.json`.
- `load_document_package(path)` (`documents/workspace.py:69-93`) takes the document name from the **file name** and requires the member names to match it exactly (`:84`, `txt_base != package_name` raises `"Document package names do not match."`). `load_workspace_documents` reports such a file as invalid, and the startup dialog offers to delete it.
- `DocumentWorkspaceService.rename_document` (`documents/workspace_service.py:98-108`): `save_document_package(new_path, ...)`, then `if old_path.exists(): old_path.unlink()`, then `controller.rename_document`. A write failure propagates with nothing changed; an unlink failure propagates with both packages on disk and the controller unchanged (known defect 3).

### Why the two defects happen, and why "skip the unlink" is not enough

On NTFS and APFS (case-insensitive, case-preserving), `alpha.dep` resolves to the existing entry `Alpha.dep`. Opening it for writing truncates and rewrites **that entry, which keeps its spelling** `Alpha.dep`.

- Defect 1: the write puts `alpha.txt`/`alpha.brl` into `Alpha.dep`; `old_path.exists()` is true; the unlink removes the only file. Memory still holds `alpha` until the app closes; the next start has no such document.
- Defect 2: Add `Alpha` writes `Alpha.*` members into the entry `alpha.dep`. On the next start the file name (`alpha`) no longer matches its members (`Alpha`), so it is reported invalid, and the user is offered to delete it. `alpha`'s text is already gone.

The review suggested "do not unlink when the old and new path are the same file". That alone does not fix defect 1: the package would survive as `Alpha.dep` holding `alpha.*` members, which fails the name check on the next start, exactly like defect 2. The directory entry itself must be renamed. Checked here with a prototype of the model below: the old sequence leaves `[]`; write-without-unlink leaves `Alpha.dep` that `load_workspace_documents` reports as invalid.

### Dictionaries (checked; not affected by data loss)

`dictionaries/manager.py` `create_dictionary` (`:50-60`), `import_dictionary` (`:63-73`) and `rename_dictionary` (`:76-86`) check `destination_path.exists()`, which on a case-insensitive file system also matches a case variant. So a case variant is refused there (`FileExistsError`, shown as `Dictionary "{name}" already exists.`), and `Path.rename` never overwrites. No data loss. The remaining differences are usability and platform divergence: on Windows a case-only dictionary rename is refused as a duplicate (`tests/test_dictionary_presenter.py:397-406` skips there for that reason), while on Linux case variants are allowed. These are not the same mechanism as documents (a dictionary is a plain CSV with no member names, and the selected dictionary name is persisted in `config.json` and matched exactly by `resolve_selected_dictionary`), so changing them needs its own decisions. Follow-up, not in this task (see Out of Scope).

Found while checking (pre-existing, not fixed here): `tests/test_dictionary_name_prompt.py:82` `test_case_only_rename_still_renames` has no case-sensitivity skip; on Windows `rename_dictionary` raises `FileExistsError` for `alpha` to `Alpha`, so this test is expected to error there. Added to the Windows debt list.

## Decisions

**D1. Casefold duplicate checks on every platform.** `session.document_name_exists` compares `document.name.casefold() == name.casefold()`; the exclusion stays **exact** (`document.name != exclude_name`). Reasons: Import, sorting and the review's suggested fix already use casefold; one rule on every platform avoids a workspace that is valid on Linux but collides when copied to Windows; the shipping platform is Windows. The visible change on case-sensitive file systems (Linux): adding `Alpha` next to `alpha` is now refused, as Import already refuses it. The exact exclusion means a case-only rename of the document itself is allowed, and in a legacy workspace that already holds both `Alpha` and `alpha` (possible only on a case-sensitive file system) renaming either one to a third spelling is refused.

**D2. The refusal reuses today's duplicate message.** `Document "{name}" already exists.` with the typed name, then the dialog reopens prefilled with the typed name, exactly as for an exact duplicate. This matches Import, which also names the incoming name. No new string.

**D3. Case-only rename is allowed and implemented safely.** A user who renames `Alpha` to `alpha` means it; refusing it would also contradict the existing case-sensitive test, which expects the rename to work. "Case-only" is decided by name, `source_name != new_name and source_name.casefold() == new_name.casefold()`, not by probing the file system: it is deterministic, works the same everywhere, and can be tested on Linux. The new sequence is file-system-agnostic, so it is also correct on case-sensitive file systems.

**D4. The safe sequence (`move_document_package`).** Never write to, replace onto or remove a name that can alias the other package:

1. Stage: write the new package to a fresh temporary file next to it (`.<new name>.dep.<random>.tmp`). On any failure (also non-`OSError`, for example `UnicodeEncodeError` from a lone surrogate) remove the temporary file and re-raise. Nothing else changed.
2. Move aside: if the old package exists, `os.replace` it to a fresh temporary file `.<old name>.dep.<random>.tmp`. On failure remove both temporary files and re-raise. The old package is untouched.
3. Install: `os.replace(staged, new_path)`. No entry with that name exists any more (on a case-insensitive file system the old entry was moved away), so the new entry gets exactly the new spelling. On failure move the old package back (if step 2 moved it) from its temporary file to its original path (original spelling), remove the staged file, and re-raise.
4. Clean up: remove the moved-aside temporary file. A failure here is **ignored**: the rename is complete and memory and disk agree, and raising would leave the controller on the old name while the disk holds the new one (the next Save would then write `Alpha.*` members into the `alpha.dep` entry on a case-insensitive file system, the defect-2 mismatch). The leftover file ends in `.tmp`, so `load_workspace_documents` (`*.dep`) never lists or offers to delete it.

Temporary names follow the existing pattern in `conversion/preprocessing/user_script.py:53-74` (`save_preprocessing_script`) (`tempfile.NamedTemporaryFile(dir=..., prefix=f".{name}.", suffix=".tmp", delete=False)`, closed at once). The directory is created first (`mkdir(parents=True, exist_ok=True)`), as `save_document_package` does, so a case-only rename whose old package is missing still works. An `OSError` from steps 2-3 names the temporary path in its text (for example `[WinError 32] ...: '...\Alpha.dep' -> '...\.Alpha.dep.k2j1.tmp'`); it is shown with the existing `Failed to save document: {error}` template.

**D5. A file-operations seam, injected, not patched.** The five primitives the sequence uses (`exists`, `write`, `replace`, `remove` and `temporary_path`) live on a small class `PackageFiles` with the real implementations. `move_document_package(..., files=...)` takes it, and `DocumentWorkspaceService.__init__` takes an optional keyword `package_files: PackageFiles | None = None` (default `PackageFiles()`). Tests pass a case-insensitive model (see Test Plan) or a fault injector (a subclass, or a delegating wrapper around `PackageFiles()`). Injection, not `mock.patch` of module globals, because `documents` is in the `wx_stub` restore roots: a test that patches `documents.workspace` in `sys.modules` can miss the module object whose functions the service actually calls. Nothing does `isinstance` checks on it; any object with the five methods works.

**D6. Known defect 3 is not included.** Using `move_document_package` for every rename would fix defect 3 (a failed move-aside would leave only the old package and an unchanged controller). It does not fall out without new decisions, so it stays out:
- error texts for regular renames would name temporary paths instead of `beta.dep`;
- a read-only package on Windows can be renamed but not deleted, so today's "unlink fails, error shown" would become "rename succeeds, a hidden `.tmp` file stays", silently: report it or not is a UX choice;
- the existing fault injection (a non-empty directory as the package) can be renamed, so the two defect-3 tests would have to be redesigned rather than flipped.

Regular (non-case-only) renames therefore keep today's code path byte for byte, and both defect-3 `KNOWN BUG` tests stay as they are. A later task can switch regular renames to `move_document_package` in one line once those choices are made.

**D7. No service-level duplicate guard.** The GUI prompt stays the only gate for Add and Rename, as for exact duplicates today. `create_document` and `rename_document` do not re-check names (no new exception path to handle in `gui.py`).

**D8. Aliasing beyond `casefold()` is out of scope.** NTFS compares with its upcase table and APFS also ignores Unicode normalization, so a few name pairs collide on disk without being casefold-equal (for example NFC `é` against NFD `e` + `U+0301` on macOS, Turkish `ı` against `i` on NTFS). Catching those needs a check against the disk (refusing names because a file already resolves there), which is a separate decision; listed as a follow-up. Names in this app are mostly Chinese, which has no case.

## Design per File

### `client/documents/session.py` (tabs)

`document_name_exists`: casefold the comparison with `name`; keep `document.name != exclude_name` exact. Nothing else in the file changes.

### `client/documents/workspace.py` (4 spaces)

Add `import os` and `import tempfile` and, after `save_document_package`:

- `class PackageFiles` with methods `exists(path) -> bool` (`Path(path).exists()`), `write(path, document) -> None` (`save_document_package(path, document)`), `replace(source, destination) -> None` (`os.replace`), `remove(path) -> None` (`Path(path).unlink(missing_ok=True)`), and `temporary_path(directory, name) -> Path` (creates the directory, then the `NamedTemporaryFile` pattern of D4; returns the closed file's path).
- `move_document_package(old_path, new_path, document, *, files: PackageFiles) -> None` implementing D4 steps 1-4. Its docstring states the guarantee: on return the package exists only at `new_path` (exact spelling) and holds `document`; on an exception the old package is back at `old_path` with its spelling and bytes, and no temporary file is left, except when restoring itself fails (see Risks).

`save_document_package`, `load_document_package` and every other function stay as they are.

### `client/documents/workspace_service.py` (4 spaces)

- `__init__(self, controller, workspace_dir, *, package_files: PackageFiles | None = None)`; stores `package_files or PackageFiles()`.
- `rename_document`: after the existing equal-name check and the source lookup, if `source_name.casefold() == new_name.casefold()`, call `move_document_package(self.package_path(source_name), self.package_path(new_name), Document(new_name, source.text, source.braille), files=self._package_files)` and then `self._controller.rename_document(...)`. Otherwise run today's lines unchanged.
- Module docstring: add that a case-only rename stages the new package and moves the old one aside before installing (D4), while other renames still write the new package before deleting the old one.

### `client/documents/controller.py`, `client/gui.py`

No code change. The controller delegates to `session.document_name_exists`; the GUI already re-prompts on a duplicate and passes a case-only name through to the service.

## What Stays Identical

- Exact-duplicate Add/Rename (message, prefill, re-prompt), cancel, unchanged-name Rename.
- Regular Rename: order, files, controller update, write-failure and unlink-failure behavior (defect 3 still pinned).
- Save, Import (already casefold), Delete, Delete All, startup load and the invalid-file dialog.
- The package format, the loader's exact name check, and every user-facing string (msgids 353, same set).
- `controller.rename_document` moves open/selected names and the dual-view cache for a case-only rename exactly as for any rename.

## Test Plan

All new test code uses 4 spaces (the touched test files use 4 spaces).

### A. Case-insensitive file model (new `client/tests/case_insensitive_package_files.py`, not a test module)

`CaseInsensitivePackageFiles(PackageFiles)` runs on a real temporary directory and models a case-insensitive, case-preserving file system (NTFS/APFS) for the paths it is given. A path resolves to the existing entry in the same directory whose name is casefold-equal, if any. Names are taken from the directory listing (exact name first, then a casefold match) and compared as strings, never through `Path` equality or `exists()`: on Windows both ignore case, so the model behaves the same on every host. The fault injectors in C and E match `path.name` strings for the same reason.

- `exists`/`write`/`remove`: act on the resolved entry. `write` to `alpha.dep` while `Alpha.dep` exists rewrites `Alpha.dep` and keeps that spelling.
- `replace(source, destination)`: if both resolve to the same entry, rename the entry to the destination spelling (what `MoveFileEx`/`rename(2)` do for a case-only rename); if the destination resolves to another existing entry, replace that entry's content and keep its spelling (the pessimistic reading); otherwise a plain `os.replace`. A constructor flag `replace_keeps_existing_spelling=True` lets a test also run the other reading (the destination spelling wins), so the sequence is shown not to depend on it.
- `temporary_path`: inherited (unique real names).

### B. Model self-tests (new `client/tests/test_case_insensitive_package_files.py`)

1. Writing a case variant rewrites the existing entry and keeps its spelling; `load_workspace_documents` then reports it invalid (the defect-2 mechanism).
2. Today's rename sequence through the model (`write(new)`, then `remove(old)` because `exists(old)`) leaves an empty directory (the defect-1 scenario, kept as a regression record of the old failure).
3. `replace` of an entry onto its own case variant renames it. For each flag value, replacing `beta.dep` onto `ALPHA.dep` while `alpha.dep` exists leaves one entry, `alpha.dep` (flag true) or `ALPHA.dep` (flag false), holding beta's bytes: D4 never replaces onto another entry's case variant, so B 4 alone would not test the flag.
4. `move_document_package` through the model, case-only `Alpha` to `alpha`, with both `replace_keeps_existing_spelling` values (subTest): the listing is exactly `["alpha.dep"]`, members `alpha.brl`/`alpha.txt`, `load_document_package` returns the document.

### C. `move_document_package` on the real file system (`client/tests/test_document_workspace.py`)

5. Case-only `Alpha` to `alpha`: listing `["alpha.dep"]`, content and members correct.
6. Different names (`alpha` to `gamma`): listing `["gamma.dep"]`.
7. Old package missing and workspace directory missing: the directory is created, `alpha.dep` written.
8. Pending braille (`braille=None`): `alpha.meta.json` is present and the document loads with `braille=None`.
9. Staging write fails with `OSError` (fault injector `_FailingPackageFiles`, also used by 11-13: a delegating wrapper around `workspace.PackageFiles()`, looked up at call time, not a subclass, so the module still imports before step 1's implementation exists and each new test fails on its own): raises; old package bytes unchanged; no `.tmp` left.
10. Staging write fails with a non-`OSError` (`Document("alpha", "\ud800", "1")` gives `UnicodeEncodeError`): same result.
11. Move-aside fails: raises; old package unchanged; no `.tmp` left.
12. Install fails: raises; `Alpha.dep` is back with its spelling and bytes; no `.tmp` left.
13. Clean-up fails: no exception; `alpha.dep` correct; the leftover is a `.tmp` file and `load_workspace_documents` returns only `alpha` and no invalid paths.
14. `PackageFiles().temporary_path` creates a missing directory and returns a hidden `.tmp` name that does not match `*.dep`.

### D. Duplicate check (`client/tests/test_document_controller.py`)

15. Flip `test_document_name_exists_is_exact_and_honours_exclude` to `test_document_name_exists_ignores_case_and_honours_exact_exclude`: `"Beta"` is now found; `"BETA"` with `exclude_name="beta"` is not (own case-only rename); `"zoo"` with `exclude_name="beta"` is; a controller holding `Alpha` and `alpha` finds `"ALPHA"` with `exclude_name="Alpha"`. (Count unchanged.)

### E. Service (`client/tests/test_workspace_service.py`)

16. Case-only rename on the real file system updates the controller (documents, open, selected, dual-view key) and leaves only `alpha.dep`; a second document `beta` is untouched (17 too).
17. Case-only rename with `package_files=CaseInsensitivePackageFiles()`: same result on the model (the Linux stand-in for Windows).
18. Case-only rename whose install fails (a `PackageFiles` subclass, `_FailingInstallPackageFiles`): raises; controller state unchanged; `Alpha.dep` intact.
19. A regular rename does not touch `package_files` (pass an object whose methods raise `AssertionError`): the rename succeeds, so regular renames keep today's path. The two defect-3 tests stay unchanged.
22. (Added at implementation, beyond the plan.) End to end on the model: the service's real case-only rename `Alpha` to `alpha` with a recording `CaseInsensitivePackageFiles` subclass injected as `package_files`, then a fresh controller and service load the workspace (the next start): no invalid path, the documents are `alpha` (same text and braille) and `beta`, the listing is `["alpha.dep", "beta.dep"]` with `alpha.*` members, and the model recorded the install onto `alpha.dep`. That last check makes it red on Linux when the case-only branch is missing: the old path never calls `package_files` and is correct on a case-sensitive file system.

### F. GUI flows (`client/tests/test_gui_document_flows.py`)

- Merge the two case-only rename tests into `test_case_only_rename_keeps_the_document`, without a skip: listing exactly `["alpha.dep"]`, `self._package("alpha") == Document("alpha", "a", "1")`, members `["alpha.brl", "alpha.txt"]`, controller names `["alpha"]`, events `[("DocumentNameDialog", "Rename Document", "Alpha"), ("title", "alpha - DotExpress")]`. A comment says it replaces the `KNOWN BUG` (P1-3 known defect 1) test, fixed by F-1, and runs on the host's real file system (case-insensitive on Windows/macOS).
- Merge the two Add case-variant tests into `test_add_case_variant_is_refused_as_a_duplicate`, without a skip: `self.names = ["Alpha", None]`; events: the Add dialog, the `Document "Alpha" already exists.` error box (caption `Error`, `wx.OK | wx.ICON_ERROR`, parent frame), the Add dialog prefilled with `Alpha`; listing `["alpha.dep"]`; `alpha.dep` content and members unchanged; controller names `["alpha"]`. Comment: replaces the defect-2 `KNOWN BUG` test.
- 20. New `test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document`: the frame's service is built with `CaseInsensitivePackageFiles()`; same assertions as the merged rename test.
- 21. New `test_rename_to_a_case_variant_of_another_document_is_refused`: `alpha` and `beta` exist, rename `beta`, `self.names = ["Alpha", None]`; the error box names `Alpha`; the dialog reopens prefilled with `Alpha`; both packages and the controller state are unchanged.
- Remove `_skip_unless_case_sensitive`, which nothing uses any more.

Net count: B 4, C 10, E 5 (16-19 and 22), F 2 new; D and the merges replace tests one for one except the two merges (4 tests become 2). Total `1095 + 4 + 10 + 5 + 2 + 2 - 4 = 1114` (the plan's 1113 plus test 22).

**Test names.** B 1 `test_writing_a_case_variant_rewrites_the_existing_entry_and_keeps_its_spelling`, B 2 `test_the_old_rename_sequence_deletes_a_case_only_renamed_package`, B 3 `test_replace_resolves_case_variants`, B 4 `test_move_document_package_keeps_a_case_only_renamed_package`; C 5-14 (class `MoveDocumentPackageTest`) `test_case_only_move_leaves_only_the_new_spelling`, `test_move_to_a_different_name`, `test_missing_old_package_and_directory_writes_the_new_package`, `test_pending_braille_keeps_its_metadata`, `test_staging_write_failure_keeps_the_old_package`, `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`, `test_move_aside_failure_keeps_the_old_package`, `test_install_failure_puts_the_old_package_back`, `test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores`, `test_temporary_path_creates_the_directory_and_is_not_a_package`; E 16 `test_case_only_rename_moves_the_package_and_updates_the_controller`, E 17 `test_case_only_rename_on_a_case_insensitive_file_model`, E 18 `test_case_only_rename_install_failure_propagates_and_keeps_state`, E 19 `test_regular_rename_does_not_use_package_files`, E 22 `test_case_only_rename_on_a_case_insensitive_file_model_survives_a_reload`; D 15, F 20 and F 21 as above.

**Skips.** On Linux the two `..._on_case_insensitive_file_system_...` skips disappear, because the merged tests run on any file system and the case-insensitive behavior is covered by the model: `skipped=7` (the liblouis tests). On Windows/macOS the merged tests run against the real case-insensitive file system.

## Migration Steps (each step one green commit)

1. `fix:` `PackageFiles` and `move_document_package` in `documents/workspace.py`, with tests C 5-14 (red first, then green). Nothing calls the helper yet.
2. `test:` the model (A) and its self-tests B 1-4. B 1-3 record the old failure scenario; B 4 runs the new helper on the model.
3. `fix:` casefold `document_name_exists` (D1), flipping D 15 and merging the Add tests in F, plus F 21 (red first).
4. `fix:` the case-only branch in `DocumentWorkspaceService.rename_document` and the `package_files` parameter (D3, D5), with E 16-19 and 22, the merged rename test and F 20; remove `_skip_unless_case_sensitive`. Red first in two stages, because on a case-sensitive file system today's write-then-unlink rename is correct: the merged rename test and E 16 already pass on Linux before the fix (they are red only on Windows and macOS, Windows debt). The tests that inject `package_files` (E 17-19, E 22, F 20) first error with `TypeError`; after only the constructor keyword is added, E 18 (`OSError not raised`) and E 22 (the model installed nothing) still fail, which shows that case-only renames do not use the safe sequence yet. The old data loss itself is recorded on the model by B 2.

Each commit ends with the `Co-Authored-By` line from the brief. No commit changes `gui.py`, the `.po`/`.mo` files, fixtures or `documents/controller.py`.

## Acceptance Criteria

Run from the paths shown; `$SP`/`$PY` as above.

1. `cd client && $PY -m unittest discover -s tests`: only the known P2-5 failure; `Ran 1114 tests` (the plan's 1113 plus test 22); `skipped=7`.
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`: every seed reports only the P2-5 failure.
3. Focused: `cd client && $PY -m unittest tests.test_case_insensitive_package_files tests.test_document_workspace tests.test_document_controller tests.test_workspace_service tests.test_gui_document_flows -v` passes, with no skip in `tests.test_gui_document_flows`.
4. From the repo root, `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`, same set; `client/locales` unchanged.
5. Both fixture sha256 values are unchanged.
6. App data: `$SP/p26impl/snap.sh` output is identical before and after criteria 1-2.
7. `grep -rn "KNOWN BUG (P1-3 spec, known defect [12]" client/tests` finds nothing; `grep -rn "KNOWN BUG (P1-3 spec, known defect 3" client/tests` still finds the two defect-3 tests, unchanged.
8. `git diff main --stat` touches only `client/documents/session.py`, `client/documents/workspace.py`, `client/documents/workspace_service.py`, the test files named in the Test Plan (including the new model and its test module), and the spec and plan files.
9. Mutation check (plan Task 5 step 7, `f1_mutants.py`): each of the 12 mutants (case-only branch removed, the old sequence in the branch, no move-aside, exact duplicate check, casefolded exclusion, no restore on install failure, raising clean-up, staging clean-up only on `OSError`, temporary files leaked on a move-aside failure, `.dep` temporary names, no directory creation, regular renames through the move) is caught by at least one test. On Linux the removed case-only branch is caught by E 18 and E 22 (on Windows also by the merged GUI test).

## Windows Verification Debt (cannot run here)

- `cd client && python -m unittest tests.test_gui_document_flows tests.test_workspace_service tests.test_document_workspace tests.test_case_insensitive_package_files -v` on Windows (and macOS if available): `test_case_only_rename_keeps_the_document`, `test_case_only_rename_moves_the_package_and_updates_the_controller` and `test_add_case_variant_is_refused_as_a_duplicate` run on a real case-insensitive file system and must pass (the first two fail there on the old code); `MoveDocumentPackageTest` and the model self-tests must pass unchanged there (names are compared as strings); `dir` shows `alpha.dep` in lower case afterwards.
- Packaged build, by hand: create `Alpha`, type text, rename to `alpha`, restart: the document is there with its text, and Explorer shows `alpha.dep`. Add `ALPHA`: the duplicate error appears and nothing changes on disk. Rename another document to `Alpha`: same.
- Case-only rename while the package is open in another program (for example a zip tool): the error box appears, `Alpha` stays in the list, and `Alpha.dep` is unchanged after a restart; no `.tmp` file is left (or, if the restore failed, one `.Alpha.dep.*.tmp` holding the old package).
- Pre-existing, unrelated: `tests.test_dictionary_name_prompt ... test_case_only_rename_still_renames` is expected to error on a case-insensitive file system (no skip); record the result.
- No menu, dialog or string changes: no screenshots, no `generate-pot.bat` run.

## Risks

- **Crash between move-aside and install** (low). If the process dies between steps 2 and 3 of D4, no `.dep` exists for the document; its old package is in `.Alpha.dep.<random>.tmp` and the complete new one in `.alpha.dep.<random>.tmp`, both recoverable by hand. The window is two consecutive same-directory renames.
- **Restore failure** (very low). If the install fails and moving the old package back also fails, the original error is raised and the old package stays in its `.tmp` file. Same recovery.
- **Leftover `.tmp` after a clean-up failure** (low). Invisible to the app; harmless; can accumulate only through repeated failures.
- **The model is a model.** It encodes how NTFS/APFS resolve and preserve names; D4 never relies on the contested part (replace onto an alias), and test B 4 runs both readings. The real check is the Windows debt above.
- **Behavior change on Linux** (low, intended). Add/Rename to a case variant is refused on case-sensitive file systems too (D1). Legacy Linux workspaces that already contain both spellings still load and work; only new collisions are refused.
- **Stub-scope module identity.** Covered by injection (D5); the shuffled runs (criterion 2) check module order.

## Out of Scope / Follow-ups

- **Known defect 3** (Rename unlink failure leaves two packages): switch regular renames to `move_document_package` after deciding D6's questions; flip its two `KNOWN BUG` tests then.
- **Dictionaries:** case-only rename refused on Windows/macOS; case variants allowed on Linux only; `resolve_selected_dictionary` matches the saved name exactly. No data loss; needs its own UX decisions.
- **Aliasing beyond casefold** (D8), and Add/Rename silently overwriting a `.dep` that is on disk but not in the list (an invalid package the user chose to keep at startup): both need a disk-based existence check.
- **Export All** with a legacy workspace holding both `Alpha` and `alpha` writes `Alpha.brl` and `alpha.brl` to the same file on Windows; the second silently replaces the first (the overwrite confirmation only lists files that existed before the export). Only reachable from a workspace created on a case-sensitive file system.
