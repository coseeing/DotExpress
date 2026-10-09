# Dictionary File Safety (F-2) Design

## Goal

Fix task F-2 fixes the two priority-1 data-loss defects in dictionary files that the P2 phase review lists under "既有缺陷清單" (`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`, rows 3 and 4). Both are pinned by `# KNOWN BUG` tests:

1. **A dictionary CSV with a UTF-8 BOM is lost on OK.** Excel ("CSV UTF-8") and Notepad save UTF-8 with a byte order mark. Every reader opens dictionary CSVs with `encoding="utf-8"`, so the first header is read as `"\ufefftext"`. The entries editor (`DictionaryEntriesDialog`) shows no rows, and OK overwrites the file with only the header (P2-2 spec Q1, pinned by `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header`). The same file makes every conversion fail with `CSV must contain columns: text, braille, type` (P1-6 spec known defect 1), Import rejects it with "Imported file must contain text, braille, and type headers.", and Dictionary Management shows 0 entries for it.
2. **OK truncates the dictionary before writing it.** `save_dictionary_entries` opens the file with `"w"` and writes row by row. A failure part-way (for example `UnicodeEncodeError` from a lone surrogate) leaves the header and the rows before the failing one; the rest is gone (P2-2 Q3). A non-`OSError` also escapes the OK handler, so nothing is shown (P2-2 Q7). Both pinned by `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file`.

After this task:

- Every CSV reader in the client (the dictionary readers and the three bundled data files in `client/data`) reads with `encoding="utf-8-sig"`: a leading UTF-8 BOM is ignored, a file without one reads exactly as before.
- The editor's OK writes the dictionary to a temporary file in the same directory and installs it with `os.replace`. On any failure the dictionary on disk is byte-identical to before and no temporary file is left.
- The OK handler catches every `Exception` from the save and shows the existing `Failed to save: {error}` message; the dialog stays open with the edits.
- What is written does not change: header `text,braille,type`, columns in that order, UTF-8 **without** BOM, `\r\n` line ends.

This is a behavior change on purpose, limited to BOM files and save failures. No new user-facing string, no msgid change (353, same set). P2-2 Q2 (an unchanged dictionary is rewritten in normalized form), Q4-Q6 and Q8 stay as they are.

## Corrections (2026-10-09, after the plan and the implementation)

The sections below already include these corrections; this list says what changed against the first version (commit `1f9aae8`) and why.

1. **Permission bits are kept (orchestrator amendment; supersedes the accepted mode `0600`).** On POSIX the installed dictionary keeps the permission bits of the file it replaces (`stat.S_IMODE(os.stat(path).st_mode)`, set on the temporary file with `os.chmod` before `os.replace`; `os.stat` follows a symbolic link). A new file gets `0o666 & ~umask`, the mode a plain `open(path, "w")` gives. On Windows nothing is copied (`os.chmod` only toggles the read-only attribute).
2. **The kernel applies the umask; the umask is never read (orchestrator refinement 1).** The plan's first version read the umask with an `os.umask(0)` round trip, which is process-wide and races with any other thread creating a file. Instead the helper creates the temporary file itself with `os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666)` under its own name `.<name>.<random>.tmp` in the target's directory (`<random>` is `secrets.token_hex(8)`), trying another name on `FileExistsError` (100 attempts, then `FileExistsError`). `tempfile.NamedTemporaryFile` is therefore not used (D4). A guard test fails if any production module calls `os.umask`.
3. **A target the user may not write keeps its old verdict (orchestrator refinement 2).** A rename needs only a writable folder, so without a check OK would replace a `0444` (or Windows read-only) dictionary that the old in-place `open("w")` refused. Before writing, if the target exists and `not os.access(target, os.W_OK)`, the helper raises `PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(target))` (`[Errno 13] Permission denied: '<path>'`, the text `open("w")` gave) and creates nothing; the editor shows it through the unchanged `Failed to save: {error}` handler. A privileged user (root) could write such a file in place before and still can.
4. **`open(..., opener=...)` owns the descriptor (found while implementing).** Wrapping the `os.open` descriptor with `os.fdopen` and closing it on failure is wrong: `os.fdopen` already closes the descriptor when building the text stream fails (for example an unknown encoding), so a second `os.close` raised `EBADF` over the real error and could close an unrelated descriptor. The helper opens the temporary file with `open(candidate, "w", encoding=encoding, newline=newline, opener=...)`; the opener performs the `os.open` of correction 2 and records the temporary path as soon as the file exists, so every later failure removes it. Separate commit, red first.
5. **Red stages and names (plan).** Migration step 1's first red is one loader error (`ModuleNotFoundError: No module named 'shared.atomic_write'`), not one failure per test. Step 2 is red for four of the spec's tests, not three: the updated OS-error test also fails on the old message, which has no ` -> '<path>'` suffix. The `apply_dictionary` table test is `DictionaryFileSemanticsTest.test_malformed_files_raise_the_recorded_errors`. The doubled BOM (D1) is pinned by an 11th `_error_cases()` row, "dictionary with a doubled BOM" (column message before and after); table rows are subtests, so the test count does not change.
6. **Counts.** 24 new tests instead of 15 (Test Plan): `Ran 1138` instead of 1129; the skips stay 7 on Linux (the three POSIX-only helper tests run here and skip on Windows). Per commit: 1114, 1128, 1132, 1137, 1138. 25 mutants instead of 12 (Acceptance Criteria 10).

## Current State (verified 2026-10-09 on `fix/f2-dictionary-file-safety`, HEAD `aced6f8`)

`$SP` is the session scratchpad, `$PY` is `$SP/venv/bin/python`.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1114 tests`, `FAILED (failures=1, skipped=7)`; the failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`, the skips are the Windows-only liblouis tests. From the repo root, `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`. Fixtures: `client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.

### Every CSV read in the client

A grep for `open(`, `read_text`, `csv.` over `client/` (excluding `.venv` and `tests`) finds five CSV readers, all `open("r", newline="", encoding="utf-8")` + `csv.DictReader`:

| # | Where | Reads | Used by | BOM today |
| --- | --- | --- | --- | --- |
| R1 | `dictionaries/entries.py:48-69` `load_dictionary_entries` (tabs) | user dictionary | the entries editor (`DictionaryEntryListModel.load`, `dictionaries/entry_list_model.py:57-60`); the entry counts in Dictionary Management (`dialog.py:578-582`) | no column matches; `row.get("text")` is `None` for every row, so every row is skipped: empty list, count 0 |
| R2 | `dictionaries/manager.py:41-47` `validate_dictionary_csv` (4 spaces) | file chosen for Import | `import_dictionary` (`:63-73`) | `ValueError`; the presenter (`dictionaries/presenter.py:176-178`) shows "Imported file must contain text, braille, and type headers." |
| R3 | `conversion/text/dictionary_rules.py:168` in `LoadedDictionaryRules.from_paths` (4 spaces) | user dictionary | every conversion through `DictionaryRulesLoader` | `ValueError("CSV must contain columns: text, braille, type")`, shown as `轉譯失敗：...` (stage `translation`) |
| R4 | `conversion/text/dictionary_rules.py:152` (same method) | `client/data/Bopomofo2Braille.csv` | same | `ValueError("CSV must contain columns: Bopomofo, Braille")` |
| R5 | `conversion/text/char_maps.py:14` `_load_char_mapping` (4 spaces) | `client/data/BopomofoChar2Braille.csv`, `client/data/Braille2Ascii.csv` | text processing, ASCII output | `ValueError("CSV must contain columns: ...")` |

The three bundled data files have no BOM today (checked: they start with `Bopomofo,` / `Braille,`). No other code reads CSV: `config.py` reads JSON, `user_script.py` the preprocessing script, `documents/` text and packages; `server/` and `scripts/` contain no CSV code.

### Every dictionary write

| Where | What | Pattern |
| --- | --- | --- |
| `dictionaries/entries.py:72-84` `save_dictionary_entries` | the editor's OK (`DictionaryEntryListModel.save`, `entry_list_model.py:62-64`) | `mkdir(parents=True)`, `open("w")` (truncates), `DictWriter` header + rows. **Overwrites user data.** |
| `dictionaries/manager.py:18-26` `ensure_default_dictionary` | header-only `default.csv` | only when the file does not exist |
| `dictionaries/manager.py:50-60` `create_dictionary` | header-only new dictionary | only after `exists()` is false |
| `dictionaries/manager.py:63-73` `import_dictionary` | `shutil.copyfile(source, new path)` | only after `exists()` is false |
| `dictionaries/manager.py:89-93` `export_dictionary` | `shutil.copyfile(managed, user-chosen path)` | the user confirmed overwriting in the save dialog |

Only `save_dictionary_entries` overwrites an existing user dictionary. The other four create a file that did not exist (a failure leaves a partial new file, the source is never touched) or copy to a path the user chose outside the app. They do not use a shared helper with the editor's save (see D6).

### The OK handler

`dialog.py:491-497` (tabs):

```python
def _on_ok(self, event: wx.CommandEvent) -> None:
	try:
		self._model.save(self.dictionary_path)
	except IOError as exc:
		wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
		return
	event.Skip()
```

`IOError` is `OSError`. Anything else propagates out of the wx handler (wx prints it; the dialog stays open, the user sees nothing). The msgid `Failed to save: {error}` is translated `儲存失敗：{error}`.

### Existing atomic-write code

`conversion/preprocessing/user_script.py:53-74` (`save_preprocessing_script`) and `documents/workspace.py` (`PackageFiles.temporary_path`, F-1) already stage writes in `tempfile.NamedTemporaryFile(dir=<target dir>, prefix=f".{name}.", suffix=".tmp", delete=False)` and install with `os.replace`. `save_preprocessing_script` records the temporary path only **after** writing, so a write failure there leaks the `.tmp` file (pre-existing, not fixed here; see Follow-ups).

### Tests that pin the defects

- `tests/test_dictionary_entries_dialog.py:823-830` Q1 (BOM opens empty, OK writes the header).
- `tests/test_dictionary_entries_dialog.py:1344-1360` Q3 + Q7 (an entry `"\ud800"` replaces Alpha; OK raises `UnicodeEncodeError`; the file holds only the header).
- `tests/test_dictionary_entries_dialog.py:1312-1342` `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` makes the dictionary path a directory and expects the message built from `path.open("w")`'s error. Not a `KNOWN BUG`, but its expected text changes (see D5).
- `tests/test_conversion_text_dictionary_rules.py:178-193` two rows of `_error_cases()`, "Bopomofo header with BOM" and "dictionary header with BOM", expect `ValueError` with the column message. Used by `test_apply_dictionary_raises_the_recorded_errors` (`:470`) and `test_from_paths_raises_the_recorded_errors` (`:501`).

Checked with a prototype (Python 3.14 in the venv): `utf-8-sig` reads `b"\xef\xbb\xbftext,..."` as `text`; a file holding only a BOM reads as empty (`fieldnames is None`); a second BOM is not stripped. `os.replace` of a temporary file onto a directory raises `IsADirectoryError: [Errno 21] Is a directory: '<dir>/.dictionary.csv.<random>.tmp' -> '<dir>/dictionary.csv'`. A `NamedTemporaryFile` on Linux has mode `0600`.

## Decisions

**D1. `utf-8-sig` in all five readers, data files included.** One rule for every CSV the app reads: R1-R5 change only `encoding="utf-8"` to `encoding="utf-8-sig"`. `utf-8-sig` decodes a file without BOM exactly like `utf-8` (including the `UnicodeDecodeError` for invalid bytes), so every file the app or its tests write today reads the same. The data files are included even though they ship without BOM: a maintainer who edits `Bopomofo2Braille.csv` in Excel or Notepad would otherwise break every conversion, and it keeps R3 and R4 (same method) consistent. Edge cases, both pinned: a file holding only a BOM now gives `CSV must contain header row.` (before: the column message); a doubled BOM still fails the column check. UTF-16 files (Excel "Unicode Text") are not supported, as today.

The literal is repeated in the five call sites, not shared through a constant: `conversion/text` does not import `dictionaries` or `shared` today, and the behavior is pinned per reader by tests.

**D2. Output encoding stays UTF-8 without BOM.** `save_dictionary_entries` keeps `encoding="utf-8"`, `newline=""` and `DictWriter`'s `\r\n`. A BOM dictionary therefore loses its BOM on the first OK. This keeps every byte the app writes identical (the P2-2 golden trace records the saved CSV) and is what the brief asks. Writing a BOM so that double-clicked exports open correctly in Excel is a separate UX choice (Follow-ups).

**D3. Import and Export stay byte copies.** After D1, `validate_dictionary_csv` accepts a BOM header and `shutil.copyfile` copies the file with its BOM; every reader accepts it. Stripping the BOM on import would turn the copy into a rewrite. Unchanged.

**D4. A shared atomic text-write helper: `client/shared/atomic_write.py`.** New module (4 spaces, like `shared/name_validation.py`), pure, no wx, no i18n:

```python
def write_text_atomically(
    path: Path | str,
    write: Callable[[TextIO], None],
    *,
    encoding: str = "utf-8",
    newline: str | None = "",
) -> None:
```

Behavior (corrected, see Corrections 1-4):
0. If `path` exists and `not os.access(path, os.W_OK)`, raise `PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(path))`; nothing is created.
1. Open a new temporary file `.<name>.<random>.tmp` in `path`'s directory with `open(candidate, "w", encoding=encoding, newline=newline, opener=...)`. The opener calls `os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666)`: an existing file is never reused, and the kernel applies the umask, as for `open(path, "w")`. `<random>` is `secrets.token_hex(8)`; on `FileExistsError` another name is tried, 100 times, then `FileExistsError` propagates. The directory must exist; the helper does not create it (callers do, as `save_dictionary_entries` already does).
2. The opener records the temporary path as soon as the file exists, so **before** `write(stream)` (and before a failure building the text stream); then `stream.flush()` and `os.fsync(stream.fileno())`, then close. `open` owns the descriptor and closes it on every failure.
3. On POSIX, if `path` exists, `os.chmod(temporary, stat.S_IMODE(os.stat(path).st_mode))`. Then `os.replace(temporary, path)`, called as `os.replace` (attribute lookup at call time, so tests can patch `os.replace` independent of `wx_stub` module copies; `os.access`, `os.fsync` and `os.chmod` likewise).
4. In a `finally`, if the install did not happen, remove the temporary file (`unlink(missing_ok=True)`); the original exception propagates unchanged. This covers every `BaseException` (also `KeyboardInterrupt`). A failure of that removal is not masked: the original exception still propagates (the `unlink` error is suppressed with `contextlib.suppress(OSError)`).

Guarantee (docstring): on return `path` holds exactly what `write` produced; on an exception `path` is unchanged (same bytes, or still absent) and no temporary file is left, unless removing it failed. Permissions follow a plain `open(path, "w")`: a target the user may not write raises `PermissionError` and is left alone; a new file gets `0o666 & ~umask`; on POSIX a replaced file's permission bits are kept. The process umask is never read or changed.

`fsync` is included because the point of the change is that a dictionary is never left half-written; without it a power loss right after the rename can leave an empty file on some file systems. Dictionaries are small, so the cost is one flush per OK.

Location: `shared/` because the helper is generic (dictionaries now, possibly the preprocessing script and others later) and `shared` is not a `wx_stub` restore root, so every copy of `dictionaries.entries` uses the same module. `save_preprocessing_script` and `PackageFiles` are **not** migrated (scope; Follow-ups). The helper does not use `tempfile.NamedTemporaryFile` (Corrections 2): it would create the file with mode `0600`, and setting the new-file mode afterwards needs the umask, which can only be read by setting it.

**D5. `save_dictionary_entries` writes through the helper.** It keeps `dictionary_path.parent.mkdir(parents=True, exist_ok=True)`, then calls `write_text_atomically(dictionary_path, <write header and rows with DictWriter>, encoding="utf-8", newline="")`. Same bytes as today. Visible consequence: an `OSError` raised by `os.replace` names the temporary path and the dictionary (`... '<dir>\.default.csv.k2j1.tmp' -> '<dir>\default.csv'`); one raised while creating the temporary file names the temporary path; a dictionary the user may not write gives `[Errno 13] Permission denied: '<path>'`, as the old `open("w")` did (Corrections 3). The message template is unchanged. `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` therefore checks that the message starts with `儲存失敗：` and ends with ` -> ` + `repr(str(path))` (CPython formats two-path `OSError`s as `%R -> %R` on Linux and Windows), instead of rebuilding it from `path.open("w")`.

**D6. Only the editor's save changes on the write side.** The four `manager.py` writers do not share code with `save_dictionary_entries` (two `csv.writer` header writes, two `shutil.copyfile`) and never overwrite an existing managed dictionary: their worst failure leaves a partial **new** file (an empty or partial `name.csv` after a failed create/import) or a partial export at the user's chosen path. That is a consistency problem, not loss of a dictionary the user built. Listed as a follow-up; switching them to the helper later is a one-line change each for the two header writers.

**D7. The OK handler catches `Exception`.** `except IOError as exc` becomes `except Exception as exc`, with the same `wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)` and `return` (no `Skip`, the dialog stays open, the edits stay). Reasons: this is the UI boundary of a save; after D4 every failure leaves the file intact, so the only question is whether the user is told, and an uncaught exception tells them nothing; the review's suggested fix says the same; `conversion/output.py` and `gui.py:343` use the same width at their boundaries. Realistic non-`OSError` failures are `UnicodeEncodeError` (lone surrogate) and `csv.Error`; anything else is a bug that is now at least visible. `BaseException` (`KeyboardInterrupt`, `SystemExit`) still propagates. The text after `儲存失敗：` is Python's English error text, as it already is for `OSError`. No new msgid.

**D8. No retry on Windows sharing violations.** `os.replace` can fail where the old in-place write worked: a program holding the dictionary open without `FILE_SHARE_DELETE` (an editor, an antivirus scan, an indexer, a sync client). The result is the existing error message with the edits kept; pressing OK again retries. A timed retry loop would add sleeps and a policy without a way to verify it here. Recorded under Risks and Windows debt.

## Design per File

### `client/shared/atomic_write.py` (new, 4 spaces)

`write_text_atomically` as in D4, with two private helpers: `_open_temporary_file(destination, opener, encoding, newline)` (the name loop) and `_existing_mode(destination)` (the permission bits, or `None`). Imports `contextlib`, `errno`, `os`, `secrets`, `stat`, `Path`, `Callable`, `TextIO`. Module docstring: the guarantee, that the temporary file is `.<name>.<random>.tmp` in the same directory, and the permission rules.

### `client/dictionaries/entries.py` (tabs)

- `load_dictionary_entries`: `encoding="utf-8-sig"`.
- `save_dictionary_entries`: body as in D5 (a nested `def _write(stream)` with the existing `DictWriter` lines). Add a one-line docstring: "Replace the file atomically; on an error it is unchanged."
- Import `from shared.atomic_write import write_text_atomically`.

### `client/dictionaries/manager.py` (4 spaces)

`validate_dictionary_csv`: `encoding="utf-8-sig"`. Nothing else.

### `client/conversion/text/dictionary_rules.py`, `client/conversion/text/char_maps.py` (4 spaces)

`encoding="utf-8-sig"` at `dictionary_rules.py:152` and `:168` and `char_maps.py:14`. Messages, order and everything else unchanged. The `from_paths` docstring gets "A leading UTF-8 BOM is ignored."

### `client/dialog.py` (tabs)

`DictionaryEntriesDialog._on_ok`: `except IOError as exc:` becomes `except Exception as exc:`. Nothing else.

### `client/dictionaries/entry_list_model.py`

No code change. The `save` docstring ("errors propagate") stays true.

## What Stays Identical

- Bytes written by OK for any dictionary (header, column order, quoting, UTF-8 without BOM, `\r\n`), including the normalized rewrite of an unchanged dictionary (Q2, still pinned).
- Reading any file without a BOM: rows, skipping, stripping, error types and messages, the Bopomofo-first read order (`OpenRecorder`).
- Import/Export/Create/Rename/Delete flows and their messages; the editor's Add/Edit/Delete/filter; Q4, Q5, Q6, Q8 tests unchanged.
- `client/tests/fixtures/dictionary_entries_trace.json`: the trace's `TRACE_CSV` has no BOM and none of its texts is unencodable, so every recorded `csv` (the bytes after OK) is the same through the helper. Not regenerated.
- `client/tests/fixtures/translation_golden.json`: its dictionary is written by the test with `encoding="utf-8"` (no BOM) and it reads the bundled data files (no BOM), so D1 does not change any input. Not regenerated.
- msgids: 353, same set; `client/locales` unchanged.

## Test Plan

New test code follows each file's indentation (tabs in `test_dictionary_entries.py` and `test_dictionary_management_dialog.py`, 4 spaces elsewhere). All tests use temporary directories; nothing touches `client/dictionary/` (real user data).

### A. Helper (new `client/tests/test_atomic_write.py`, class `WriteTextAtomicallyTest`)

1. `test_replaces_an_existing_file_with_the_written_text`: existing `d.csv` with other bytes; the write callback writes `"a,b\r\n"`; the bytes are exactly `b"a,b\r\n"` (no BOM, newline untranslated) and the directory listing is `["d.csv"]`.
2. `test_creates_a_file_that_does_not_exist`.
3. `test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file`: the callback writes a line, then `"\ud800"`; `UnicodeEncodeError` propagates; original bytes identical; listing `["d.csv"]`.
4. `test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file`: `patch("os.replace", side_effect=PermissionError(13, "denied"))`; the recorded source argument is in the same directory, named `.d.csv.*.tmp`; the error propagates; bytes identical; listing `["d.csv"]`.
5. `test_interrupt_leaves_no_temporary_file_and_propagates`: the callback raises `KeyboardInterrupt`.
6. `test_failure_without_an_existing_file_creates_nothing`: as 3 with no file; listing `[]`.
7. `test_data_is_flushed_to_disk_before_the_replace`: `os.fsync` and `os.replace` wrapped (`wraps=`) on a shared `Mock` parent; call order is `fsync` then `replace`.

Added by the corrections (A8-A15):

- A8 `test_keeps_the_permission_bits_of_an_existing_file` (POSIX only): an existing `0o640` file stays `0o640`.
- A9 `test_a_new_file_gets_the_default_mode_for_the_umask` (POSIX only): with umask `0o002` set by the test (restored by `addCleanup`), a new file is `0o664`. `0o640` and `0o664` differ from `0o600` (`mkstemp`) and from `0o644` (the usual default), so no constant passes both.
- A10 `test_a_read_only_file_gets_the_same_verdict_as_writing_it_in_place` (POSIX only): a `0o444` file; the test first opens it with `"r+b"` to learn what the old in-place write would have done. Refused (a normal user): `PermissionError` with `errno.EACCES` and the target as `filename`, bytes unchanged. Allowed (root with `CAP_DAC_OVERRIDE`): the new text is installed. Either way the mode stays `0o444` and only `d.csv` is listed. This machine runs as root, so the refused branch was also run with `setpriv --bounding-set=-dac_override,-dac_read_search`.
- A11 `test_a_file_without_write_access_raises_permission_error_and_is_kept` (every platform): `os.access` patched to `False`; it was asked about the target with `os.W_OK`; the error text is exactly `[Errno 13] Permission denied: '<path>'`; bytes unchanged; no `.tmp`.
- A12 `test_an_unknown_encoding_raises_it_and_leaves_no_temporary_file`: `encoding="no-such-codec"`; `LookupError` (not `EBADF`) propagates; bytes unchanged; no `.tmp` (Corrections 4).
- A13 `test_a_taken_temporary_name_is_skipped_and_kept`: `secrets.token_hex` patched to give `aaaa`, then `bbbb`, with `.d.csv.aaaa.tmp` already present: the write succeeds, two names were drawn, and the other file is untouched (the name is created with `O_EXCL`, never reused).
- A14 `test_gives_up_when_every_temporary_name_is_taken`: every name taken: `FileExistsError` after more than one attempt; target and the other file unchanged.
- A15 `ProductionCodeDoesNotSetTheUmaskTest.test_no_production_module_calls_os_umask`: an AST scan of every `client/` module outside `.venv` and `tests` finds no `.umask` attribute and no `from ... import umask` (and `shared/atomic_write.py` is among the scanned files).

### B. Dictionary storage (`client/tests/test_dictionary_entries.py`, `DictionaryEntryStorageTest`)

8. `test_load_ignores_a_utf8_bom`: `b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n"` gives `[DictionaryEntry("Alpha", "\u2801", "General")]`.
9. `test_save_writes_utf8_without_a_bom`: bytes exactly `b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n"`.
10. `test_save_failure_leaves_the_existing_file_unchanged`: existing two-row file; save `[Alpha, DictionaryEntry("\ud800", ...)]` raises `UnicodeEncodeError`; bytes identical; listing unchanged (regression record of Q3 at the storage level).

### C. Conversion rules (`client/tests/test_conversion_text_dictionary_rules.py`)

- `_error_cases()`: replace the two "header with BOM" rows by "Bopomofo file is only a BOM" (`b"\xef\xbb\xbf"` → `ValueError`, `NO_HEADER`) and "dictionary is only a BOM" (same). Still 10 cases; both table tests keep their counts. A comment says F-2 made the BOM headers valid (test 11).
11. `test_from_paths_ignores_a_utf8_bom_in_both_files`: a dictionary with a Braille row and a Bopomofo row plus `TEST_BOPOMOFO`, each written with and without BOM; the two `LoadedDictionaryRules` are equal and `apply` gives the same result.

### D. Character maps (`client/tests/test_conversion_text_char_maps.py`)

12. `test_translate_mapping_char_ignores_a_utf8_bom`: `"\ufeffsource,target\r\na,x\r\n"` maps `"abc"` to `"xbc"`.

### E. Import (`client/tests/test_dictionary_manager.py`)

13. `test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes`: `validate_dictionary_csv` does not raise; the imported file's bytes equal the source bytes (BOM kept); `load_dictionary_entries` on it gives the row.

### F. Dictionary Management counts (`client/tests/test_dictionary_management_dialog.py`)

14. `test_utf8_bom_dictionary_counts_its_entries`: like `test_refresh_sets_virtual_count_and_valid_entry_counts` with a BOM file; the count column shows `"1"`.

### G. Entries editor (`client/tests/test_dictionary_entries_dialog.py`)

- Flip Q1: `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header` becomes `test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom`: rows `[ALPHA_CELLS]`; OK returns `True`; `saved_csv() == HEADER + "Alpha,\u2801,General\r\n"` and the raw bytes do not start with the BOM. Comment: was the Q1 `KNOWN BUG`, fixed by F-2.
- Flip Q3/Q7: `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file` becomes `test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged`: same setup (the `"\ud800"` edit, the regression scenario); the original bytes are read first; OK returns `False`; the log is exactly `[["MessageBox", "儲存失敗：'utf-8' codec can't encode character '\\ud800' in position 0: surrogates not allowed", ERROR_TITLE, ERROR_FLAGS]]` (built from the `UnicodeEncodeError` text; Python's message, the same on Linux and Windows); the file bytes are identical; the directory holds only `dictionary.csv`; the rows still show the edit. Comment: was the Q3/Q7 `KNOWN BUG`.
- Update `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` as in D5 (prefix and ` -> 'path'` suffix; plus: the directory holds only the `dictionary.csv` directory, no `.tmp`).
15. `test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds`: Add Beta, `patch("os.replace", side_effect=PermissionError(13, "denied"))`; OK returns `False`; message `儲存失敗：[Errno 13] denied`; bytes identical; no `.tmp`; after the patch ends, OK returns `True` and saves Alpha and Beta.
16. `test_dictionary_without_write_access_shows_the_message_and_keeps_the_file` (Corrections 3): as 15 with `os.access` patched to `False`; the message is `儲存失敗：[Errno 13] Permission denied: '<path>'`, the dialog is the parent, the file is unchanged, no `.tmp`, the rows are kept, and a later OK succeeds.

Net count: A 15, B 3, C 1, D 1, E 1, F 1, G 2 = 24 new; the flips and the update replace tests one for one. Total `1114 + 24 = 1138`.

## Migration Steps (each step one green commit, red first)

1. `fix: add an atomic text-write helper` — `shared/atomic_write.py` with tests A 1-11 and A13-A15 (red: `ModuleNotFoundError`; then, with the first `NamedTemporaryFile` version of D4, A8-A11, A13 and A14 fail). Nothing uses it yet. 1128 tests.
2. `fix: save dictionary entries atomically` — D5 and D7; tests B 9-10, G flip Q3/Q7, G update, G 15. Red first: B 10, the flipped Q3/Q7 test and G 15 fail on the old code (truncated file / escaping exception / `PermissionError` never raised by the old path). B 9 already passes (it pins D2). G 16 is added here too (red: the old in-place write never asks `os.access`, so OK succeeds and no message appears). 1132 tests.
3. `fix: read dictionary and data CSVs with utf-8-sig` — D1 in R1-R5; tests B 8, C (table change and 11), D 12, E 13, F 14, G flip Q1. Red first: each new test fails on `utf-8`, and the flipped Q1 test fails. 1137 tests.
4. `fix: let open() own the atomic write's temporary descriptor` — Corrections 4; test A12 (red: `OSError: [Errno 9] Bad file descriptor` over the `LookupError`). 1138 tests.

Each commit ends with the `Co-Authored-By` line from the brief. No commit changes `.po`/`.mo` files, fixtures, `gui.py` or `entry_list_model.py`.

## Acceptance Criteria

Run from the paths shown; `$SP`/`$PY` as above.

1. `cd client && $PY -m unittest discover -s tests`: `Ran 1138 tests`, `FAILED (failures=1, skipped=7)`, the one failure being the known P2-5 case.
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`: every seed reports only the P2-5 failure.
3. Focused: `cd client && $PY -m unittest tests.test_atomic_write tests.test_dictionary_entries tests.test_dictionary_entries_dialog tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps -v` passes.
4. From the repo root, `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`, same set; `git diff main -- client/locales` is empty.
5. Both fixture sha256 values unchanged.
6. App data: `$SP/p26impl/snap.sh` output identical before and after criteria 1-2 (`client/dictionary/` is real user data and is never written).
7. `grep -rn "KNOWN BUG (P2-2 spec, Q[137]" client/tests` finds nothing; the Q2, Q4, Q5, Q6, Q8 markers are unchanged.
8. `grep -rn "csv.DictReader" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` lists the five readers R1-R5, and `grep -rn "utf-8-sig" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` lists exactly their five `open` calls.
9. `git diff main --stat` touches only `client/shared/atomic_write.py`, `client/dictionaries/entries.py`, `client/dictionaries/manager.py`, `client/conversion/text/dictionary_rules.py`, `client/conversion/text/char_maps.py`, `client/dialog.py`, the test files named above, and the spec/plan files.
10. Mutation check (plan): each mutant is caught by at least one test: each of R1-R5 back to `utf-8` (5); `save_dictionary_entries` back to a direct `open("w")`; the helper cleaning up only on `OSError`; recording the temporary path after `write`; no `fsync`; the temporary file in the system temp directory; output encoding `utf-8-sig`; the dialog catching `OSError` only. Added by the corrections (13): the permission bits not set; the existing mode not kept; a new file created `0o644` or `0o600` instead of `0o666` (2); the umask read by an `os.umask` round trip (only the guard A15 catches it); no `O_EXCL`; a taken name not retried; a single attempt; the descriptor closed twice after `os.fdopen`; no write-access check; the check applied to a missing file; the `PermissionError` without the path. 25 in all.

## Windows Verification Debt (cannot run here)

- `cd client && python -m unittest tests.test_atomic_write tests.test_dictionary_entries_dialog tests.test_dictionary_entries -v` on Windows: the replace-onto-a-directory test now fails in `os.replace` with `PermissionError [WinError 5]`; its message must still end with ` -> '<path>'`. A8, A9 and A10 report `skipped` (POSIX only); A11 and G 16 run (patched `os.access`); A4's temporary path has the `.d.csv.<random>.tmp` form; `O_BINARY` is set, so the bytes are exactly `\r\n` as written.
- Packaged build, by hand: save a dictionary from Excel as "CSV UTF-8" and from Notepad (UTF-8 with BOM); Import it; Dictionary Management shows its entry count; the editor shows its rows; OK keeps them; a conversion uses them.
- Open a dictionary in Excel (which locks it), press OK in the editor: the `儲存失敗：` message appears, the edits stay, the file is unchanged; close Excel, OK again succeeds. No `.default.csv.*.tmp` remains in the dictionary folder.
- With real-time antivirus on, edit and OK a dictionary ten times in a row; record any transient failure (D8).
- Mark a dictionary read-only in Explorer, press OK: `儲存失敗：[Errno 13] Permission denied: '<path>'` appears (from the `os.access` check, Corrections 3), the file is unchanged, no `.tmp` remains; clear the attribute, OK succeeds and the file keeps default attributes.

## Risks

- **Windows sharing modes** (low-medium, D8). Programs that keep the CSV open without `FILE_SHARE_DELETE` now make OK fail where the old in-place write succeeded. The failure is visible and safe (message, edits kept, file unchanged), and a second OK retries. Excel locks the file entirely, which failed before too.
- **File metadata** (low, narrowed by Corrections 1). The installed file is a new file: on POSIX it keeps the old permission bits (or gets the umask default), but not the owner, ACLs or extended attributes; on Windows it takes the folder's inherited ACL and default attributes. A symbolic link at the dictionary path is replaced by a regular file (with the link target's mode). The dictionary folder is per-user app data, so none of this is expected to matter.
- **The write-access check** (low, Corrections 3). `os.access` is asked before the rename; a target made read-only in between is still replaced. On Windows `os.access(W_OK)` sees only the read-only attribute; an ACL that denies writing is not seen by the check, and whether `os.replace` then fails depends on the folder's and file's delete rights (Windows debt; any failure takes the same message flow). `os.access` uses the real user ID, which is the effective one for this app.
- **Own temporary-name generation** (low, Corrections 2). Replaces `tempfile`'s name loop: `O_EXCL` guarantees that no existing file is opened or overwritten, names carry 64 random bits, and after 100 taken names the save fails with `FileExistsError` (shown as `儲存失敗：...`).
- **Leftover `.tmp` after a crash** (low). A crash between creating and installing the temporary file leaves `.<name>.csv.<random>.tmp`. `list_dictionary_names` globs `*.csv`, so it is never listed or loaded; it is harmless and removable by hand.
- **Broader catch** (low, D7). A programming error during save now shows a message instead of a traceback; the traceback is no longer printed. Acceptable at this boundary, and the file is intact either way.
- **Behavior change for BOM files** (intended). A BOM dictionary that showed empty and failed conversions now works; on the first OK it is saved without BOM (D2).

## Out of Scope / Follow-ups

- P2-2 Q2 (OK rewrites an unchanged dictionary in normalized form), Q4-Q6, Q8: unchanged, still pinned.
- `manager.py` writers (D6): create/ensure-default header writes, import/export `shutil.copyfile`: route through the helper (and a binary variant for the copies) so a failure never leaves a partial new dictionary or a truncated export.
- `save_preprocessing_script` (`user_script.py:53-74`) leaks its `.tmp` file when the write fails (temporary path recorded after the write); migrate it to `write_text_atomically`. `PackageFiles` (F-1) can stay as it is (binary zip, injected seam).
- Writing a BOM on Export (or on every save) so Excel opens UTF-8 dictionaries correctly: UX decision.
- Other text inputs that a BOM breaks: the preprocessing script (`read_text(encoding="utf-8")`, a BOM there is a `SyntaxError`) and imported `.txt` documents (`documents/workspace.py:178-185` `load_text_document`, the BOM becomes part of the text). Separate tasks if wanted.
