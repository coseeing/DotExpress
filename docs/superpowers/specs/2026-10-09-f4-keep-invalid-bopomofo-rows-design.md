# Keep Invalid Bopomofo Rows (F-4) Design

## Goal

Fix task F-4 fixes F-W11, a data-loss defect found by the GUI automation of the Windows verification (`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`, "新發現"; test dictionary `auto/data/dict_badbopo.csv`):

> Invalid Bopomofo rows (for example `ㄉㄨˋ|ㄗ˙`, `ㄕㄨˋ ㄒㄩㄝˊ`) are silently skipped on load; Dictionary Management's entry count excludes them. Pressing OK in the entries editor, even without a change, deletes them from the file (4 lines -> 2 lines). Same in the old baseline `6e5819f`.

It is the "skipped rows" half of P2-2 quirk Q2 ("OK always rewrites the file, silently dropping rows the loader skipped (empty text, invalid zhuyin) and the whitespace it stripped"), listed as priority 2 in the defect lists of the P2 review and the F review, and pinned by `# KNOWN BUG (P2-2 spec, Q2)` `test_unchanged_dictionary_is_rewritten_in_normalized_form`.

The user chose option A: **rows the editor cannot show are kept in the file untouched; the editor does not show them and cannot delete them; OK writes them back.**

After this task:

- The entries editor shows exactly the rows it shows today. Every other data row of the file (a blank source text, or a `Bopomofo` row whose sequence does not parse) is kept, hidden, at its place in the file.
- OK writes every row back in file order. A hidden row is written with its three fields exactly as read (not stripped, type not normalized); with today's writer (F-2: UTF-8 without BOM, `\r\n`, minimal quoting) a row that was already written that way is byte-identical. `dict_badbopo.csv` survives OK byte for byte.
- Adding or editing an entry whose source text equals a hidden row's source text is refused with the existing duplicate message.
- Dictionary Management's count, Import, Export, Rename, Delete and conversion are unchanged.

No new user-visible string; msgids unchanged (353, same set). No change to `client/shared/atomic_write.py`, `client/dialog.py`, `client/gui.py` or `client/conversion/`.

Non-goals: showing, editing or repairing hidden rows in the editor; telling the user they exist (Q2); changing how conversion treats them (Q3); the rest of Q2 (an unchanged OK still strips the shown rows, rewrites unknown types as `General`, drops a BOM, extra columns and overflow fields, and normalizes line ends and quoting); writing only when something changed; Import/Export/Rename (they keep every row already, D8).

## Corrected after planning (2026-10-09)

The plan (`docs/superpowers/plans/2026-10-09-f4-keep-invalid-bopomofo-rows.md`, dry-run on scratch clones) found no error in decisions D1-D9, in Current State or in the counts of the three migration steps (1212, 1218, 1226). Below are the decided open questions and where the plan refines this spec; where they differ, this section wins.

1. **Q1-Q3 decided** by the orchestrator with the recommended defaults (2026-10-09); the user may override any of them before the merge. **Q1: refuse** with the existing duplicate message (D5). **Q2: no notice in F-4**; that the hidden rows are invisible in the editor and not counted in Dictionary Management is a known defect, left to a follow-up UX task (it needs new msgids). **Q3: conversion unchanged** (D7, no change under `client/conversion/`); making conversion ignore invalid rows is a follow-up together with P1-6 defect 2.
2. **Model tests use four rows.** `PreservedRowsTest` is built from `alpha, kept, beta, blank`, where `blank` is the trailing preserved row `PreservedDictionaryRow("", "\u2803", "General")`. M2 removes the second entry (`beta`) and adds `gamma`: rows `(alpha, kept, blank, gamma)`. M3 replaces `beta` with `delta`: `(alpha, kept, delta, blank)`. M4 uses the same model; M1 also filters by `|`. With three rows and index 0, a new entry inserted before a trailing preserved row, or a remove/replace by visible index, would go unnoticed.
3. **Test details.** E1-E3 form a new class `DictionaryEntriesDialogHiddenRowsTest`; E1 also checks that no temporary file is left, E3 that the shown rows are unchanged. S3 also asserts that the embedded bytes have the sha256 of `dict_badbopo.csv`; S6 compares in both directions. The test data constants are repeated in the modules that need them (no new helper module, so acceptance criterion 5 holds); new test code is ASCII with `\u` escapes, like the existing tests.
4. **Mutation check: 19 mutants**, each caught (plan Task 4). "`remove` by equality over rows matching a preserved row" is checked as a field-wise `__eq__` on `PreservedDictionaryRow`, caught by S6 only: through the editor an entry and a preserved row never have equal fields (the classification is a function of the fields), so S6 is the guard. The mutation tool runs Python with `-B`, because a restored file can have the size and modification second of the mutant before it and its cached bytecode would be used.
5. **Counts after F-3.** F-3 was merged into `main` as `b793704`; `main` alone gives `Ran 1253`, `FAILED (errors=1, skipped=7)` (F-3's review added tests). After merging `main` into F-4: `Ran 1268`, `FAILED (errors=1, skipped=7)`, F-W6 only. This replaces "expected `Ran 1263` (1211 + F-3's 37 + F-4's 15)" in "Interaction with F-3". F-3 also changed `client/gui.py` (a `_show_document_save_error` helper and logging) and `client/tests/test_gui_document_flows.py`; neither overlaps F-4's files and the merge is clean.
6. **Windows verification.** History folder `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/`; the new item keeps number 35. `rerun.py` takes only the script name (each script's build and folders are fixed) and has a `--check` mode that prints the replaced lines without running. Item 23 runs in `D:\dxtest\auto23-f4-B` and `D:\dxtest\auto23-f4-N-f4` (the script puts the build label into the folder name); items 24, 25 and 29 use `D:\dxtest\auto24-f4`. Item 35's Add of `肚子` / `ㄉㄨˋㄗ˙` / Bopomofo is automated through the real entry dialog, not manual. Item 23's dict23 output is `sha ef319c2140b1465e` (the 2026-10-09-03 result `ef319c21…`).

## Current State (verified 2026-10-09 on `fix/f4-keep-invalid-bopomofo-rows`, HEAD `4953772`, Windows 11 26200)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13); `$SP` is the session scratchpad, where the prototypes of this spec live (`$SP/f4spec/`, not committed). The worktree lacks the git-ignored liblouis runtime and MathCAT; with them copied from the main checkout as in the F-3 plan's Task 0 (`client/braille/liblouis.dll`, `client/braille/louis_helper.py`, `client/braille/liblouis/`, `client/mathcat/`, `include/liblouis/configure.ac`; submodule `2aa5f84b` in both; `git status` stays empty), `cd client && $PY -m unittest discover -s tests` gives `Ran 1211 tests`, `FAILED (errors=1, skipped=5)`; the error is F-W6 (`test_dictionary_name_prompt ... test_case_only_rename_still_renames`). `client` tree `c609d363`. msgids: `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c`. Fixtures (`git show HEAD:<path> | sha256sum`): `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, `translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`. `dict_badbopo.csv` sha256 `c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4`.

### Every CSV reader (F-2's R1-R5) and what it drops

`grep -rn "csv.DictReader\|utf-8-sig" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` lists the same five readers as F-2. Only R1 feeds a writer.

| # | Where | Reads | Rows it does not use | Writes back? |
| --- | --- | --- | --- | --- |
| R1 | `dictionaries/entries.py:49-70` `load_dictionary_entries` | user dictionary, for the entries editor (`DictionaryEntryListModel.load`) and the counts in Dictionary Management (`dialog.py:578-582`) | (a) source text blank after `strip()` (`""`, `"  "`, missing field); (b) normalized type `Bopomofo` whose stripped braille fails `normalize_zhuyin_sequence`. Both `continue`: the row is gone from the list | **yes**: the editor's OK (`save_dictionary_entries`) writes the list, so (a) and (b) are deleted from the file |
| R2 | `dictionaries/manager.py:41-47` `validate_dictionary_csv` | file chosen for Import | reads the header only | no (Import is `shutil.copyfile`) |
| R3 | `conversion/text/dictionary_rules.py:169-197` `LoadedDictionaryRules.from_paths` | user dictionary, for every conversion | only rows whose **unstripped** text is `""`. It does **not** skip invalid Bopomofo rows (below) | no |
| R4 | same method, `:153-163` | bundled `client/data/Bopomofo2Braille.csv` | rows with empty `Bopomofo` | no |
| R5 | `conversion/text/char_maps.py:14` | bundled `BopomofoChar2Braille.csv`, `Braille2Ascii.csv` | sources that are not one character | no |

Other things R1 + OK do to a row (mutations, not drops): text and braille are stripped; a type other than `General`/`Bopomofo`/`Braille` (case-sensitive, also empty or missing) becomes `General`; columns other than `text,braille,type` and fields beyond the header (`DictReader` puts them under the key `None`) are dropped; the header becomes `text,braille,type`; a BOM is dropped and line ends become `\r\n` (F-2 D2); quoting is normalized. Completely empty lines are skipped by `csv.DictReader` itself. Invalid `Braille` rows (characters outside U+2800-U+28FF) are **not** dropped: the loader does not validate them (`test_load_preserves_invalid_braille_rows`).

### Conversion uses the rows the editor drops

The brief assumed invalid rows are ignored by translation. They are not. R3 runs `processing` (`normalize_zhuyin_sequence`) on a `Bopomofo` row's braille; on an exception it keeps the raw string and scans it with the `Bopomofo2Braille.csv` trie, so the row still becomes a rule. Prototype (`$SP/f4spec/probe_translation.py`, real data file and parser) on `dict_badbopo.csv`:

| Input | Rules from the file | After the editor's OK today |
| --- | --- | --- |
| `肚子` | replacement `\[⠙⠌⠐|⠓⠁\]` | no rule, text unchanged |
| `數學` | replacement `\[⠊⠌⠐⠄⠑⠦⠂\]` | no rule |
| `臺北` | `\[⠞⠺\]` | `\[⠞⠺\]` |

R3 also keeps a row whose text is only whitespace (`"  "` is a rule that replaces two spaces), which R1 drops. And because R1 strips before validating, a first-tone sequence ending in its tone space (`ㄇㄚ `) is valid for R3 but invalid for R1. So today an unchanged OK changes conversion output. These paths are pinned by the golden cases "Bopomofo row with a processing that raises" and "Bopomofo row with the real zhuyin parser and data file" (`tests/test_conversion_text_dictionary_rules.py:103-125`). R3 keeps the **first** of two rules with the same source (`_build_trie`, "the first duplicate source wins"), so row order matters for conversion.

### Writers

`save_dictionary_entries` (`entries.py:73-89`, F-2: `write_text_atomically`, `DictWriter`, UTF-8 without BOM, `\r\n`) is the only writer that rewrites a user dictionary. `manager.py`: `ensure_default_dictionary` and `create_dictionary` write a header to a new file; `import_dictionary` and `export_dictionary` are `shutil.copyfile`; `rename_dictionary` is `Path.rename`; `delete_dictionary` is `unlink`. None of them parses rows, so none drops one. There is no copy action.

### The model (`dictionaries/entry_list_model.py`, P2-2)

`DictionaryEntryListModel` holds `_entries` (the full list in file order), the filter text and `_visible`. `add` appends; `replace` swaps by identity; `remove` removes the first **equal** entry (`list.remove`); `source_text_exists` compares `text` exactly over the full list (filter-hidden rows included). `save` passes `_entries` to `save_dictionary_entries`. The dialog (`dialog.py:330-497`) touches only the model's public surface.

### Tests that pin the defect

- `tests/test_dictionary_entries_dialog.py:1312` `test_unchanged_dictionary_is_rewritten_in_normalized_form` (`# KNOWN BUG (P2-2 spec, Q2)`): input `" Alpha ,  ⠁ ,General"`, `",⠃,General"`, `"Zhuyin,invalid,Bopomofo"`, `"Beta,⠃,Custom"` (LF); OK writes only `Alpha,⠁,General` and `Beta,⠃,General`.
- The golden trace (`DictionaryEntriesTraceTest`): `TRACE_CSV` holds the blank-text row `,⠃,General` and the invalid Bopomofo row `zz,ab,Bopomofo`; every one of the 40 recorded sequences ends with an OK whose saved CSV lacks both rows.
- `test_load_filters_empty_and_invalid_bopomofo_rows` (`test_dictionary_entries.py`), `test_loads_only_rows_accepted_by_the_editor` (`test_dictionary_entries_dialog.py:513`) and `test_refresh_sets_virtual_count_and_valid_entry_counts` (`test_dictionary_management_dialog.py:105`) pin what `load_dictionary_entries` returns and what Dictionary Management counts. They stay true (D6).

## Decisions

**D1. Scope: every row R1 skips today, not only invalid Bopomofo.** R1 has two skip branches in the same loop: blank source text and invalid Bopomofo. Both are the same mechanism (`continue` in the loader, then OK writes the list) and the same loss (a row the user wrote, which R3 may use, disappears on an unchanged OK). Fixing one and leaving the other would keep the same bug class one branch away; the golden trace and the Q2 test already contain one of each. Both kinds are kept by the same code (D2). Not in scope: completely empty lines (no data; R3 ignores them too), and the mutations listed in Current State (stripping, type normalization, dropped extra columns and overflow fields, header, BOM, line ends, quoting). They change a row rather than delete it, and fixing them means not rewriting unchanged rows at all, which changes F-2's verified output (items 23 and 24 expect CRLF without BOM after OK). They stay under Q2 (Follow-ups).

**D2. Storage: `PreservedDictionaryRow` and `load_dictionary_rows` in `dictionaries/entries.py`.**

```python
@dataclass(frozen=True)
class PreservedDictionaryRow:
	text: str
	braille: str
	entry_type: str

DictionaryRow = DictionaryEntry | PreservedDictionaryRow

def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]: ...
def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]: ...  # unchanged result
def save_dictionary_entries(dictionary_path: Path, rows: Iterable[DictionaryRow]) -> None: ...
```

`load_dictionary_rows` is today's loop with the two `continue` branches turned into `rows.append(PreservedDictionaryRow(row.get("text") or "", row.get("braille") or "", row.get("type") or ""))`; the classification is today's rule exactly (blank stripped text, or normalized type `Bopomofo` whose stripped braille fails `normalize_zhuyin_sequence`), moved into a private `_is_editable(entry)`. It is **not** `validate_dictionary_entry`: that would also hide invalid `Braille` rows the editor shows today. `load_dictionary_entries` becomes `[row for row in load_dictionary_rows(path) if isinstance(row, DictionaryEntry)]`, so its result, the counts and its three pinning tests do not change. `save_dictionary_entries` keeps its name, its F-2 body and its bytes for entries; it accepts both kinds and writes `row.text`, `row.braille`, `row.entry_type` for each (both classes have these attributes). A separate class (not a flag on `DictionaryEntry`) because a preserved row must never be shown, edited, matched by the filter or removed, and a frozen dataclass of another class is never equal to a `DictionaryEntry` (dataclass `__eq__` requires the same class), so the model's `list.remove` and equality-based selection can never pick it.

**D3. Byte-level preservation: field-exact, re-serialized by the same `DictWriter`.** A preserved row keeps its three field values exactly as `csv.DictReader` returned them (a missing field becomes `""`) and is written by the same writer as the entries. Result: a row written by DotExpress (or by any writer using UTF-8, `\r\n`, the three columns in header order and minimal quoting) is written back byte-identically; any other row comes back with the same field values for every reader (R1 and R3 both use `row.get(...) or ""`), with these normalizations, which today apply to every row of the file anyway: no BOM, `\r\n` line ends, minimal quoting, a missing trailing field written as an empty field (`,⠃` becomes `,⠃,`), extra columns and overflow fields dropped, header `text,braille,type` in that order. A header without a `text` column (for example `foo,bar`, or none of the three columns) makes every data row a preserved row with three empty fields, written back as `,,` lines where the pre-F-4 editor wrote the header only; no rule is lost, since R3 already rejects such a header and skips a blank source text (F-4 review M-3). Raw-line preservation was rejected: `csv` does not expose a record's source text (quoted fields may span lines, so `line_num` arithmetic is fragile), the header and the other rows are re-serialized anyway (a raw LF row among CRLF rows would mix line ends), and every consumer compares fields, not bytes. No change to `shared/atomic_write.py` is needed: the text helper's signature and behavior are what F-2 delivered and F-3 keeps.

**D4. Position: preserved rows stay at their original place.** The model keeps one ordered list of all file rows (`_rows: list[DictionaryRow]`); the editable entries and the visible list are derived from it. Each operation keeps its P2-2 meaning on the entries and leaves preserved rows where they are: `add` appends to the end of the file (after a trailing preserved row), `replace` swaps the entry in place (identity), `remove` deletes the first equal entry (never a preserved row, D2). So a preserved row keeps its neighbours except those the user deleted, and an unchanged OK reproduces the file's row order exactly. One imprecision, from P2-2 Q4's first-equal remove: with identical entries on both sides of a preserved row of the same source text (`a,⠁,General` / hidden `a,ㄉ|,Bopomofo` / `a,⠁,General`), removing the second visible `a` deletes the first one, so the preserved row becomes the first rule for `a` and conversion switches to its fallback; before F-4 the preserved row was deleted on OK instead. Fixing it means an identity remove, which flips the tests that pin Q4, so it goes with P2-2 Q4 (F-4 review M-2). Reasons: (1) conversion keeps the first of two rules with the same source, so moving preserved rows to the end would change which rule wins for a duplicated source after an unchanged OK; (2) the file the user maintains elsewhere (Excel, a text editor) keeps its layout, and a diff of the file before and after OK shows only real edits; (3) no anchors to maintain: a single list makes position preservation structural rather than bookkept, which is less fragile than "append at the end" plus re-anchoring. Appending at the end was rejected for (1).

**D5. Duplicate check: a preserved row's source text counts.** `source_text_exists` compares `text` exactly over all rows, preserved rows included (raw, unstripped text, the value R3 uses as the rule's source). Adding or editing an entry to a source text that a hidden row already has is refused with the existing `Source text "{identifier}" already exists.` (`來源文字「{identifier}」已存在。`), exactly as today for an entry hidden by the filter. Reason: R3 keeps the first rule of a duplicated source. If the editor accepted `肚子` with a valid sequence while an invalid `肚子` row stays earlier in the file, the new entry would be appended after it and silently never used, the opposite of what the user meant; before F-4 the old row was deleted on OK, so the new one did work. Refusing tells the user something is in the way; the remedy (fix or remove the row in the CSV outside the app) is the same remedy option A gives for any hidden row. Blank-text rows never collide through the dialog (the entry dialog strips and requires a source text); the model assumes a validated entry, so a direct `add` of a blank source text would be refused against a preserved blank-text row, which no UI path can do (F-4 review M-7, documented in `source_text_exists`). Side effect, same as P2-2 Q4: a file that already has a valid and an invalid row with the same source text cannot have the valid one edited without changing its text. See Q1 for the alternatives.

**D6. Dictionary Management counts only the entries the editor shows (unchanged).** `_load_dictionary_counts` keeps calling `load_dictionary_entries`. `dict_badbopo.csv` keeps showing `1`. Counting all rows would show a number the editor cannot match, and a "1 + 2 hidden" display needs new strings (Q2). Pinned by a new test (P1).

**D7. Conversion is unchanged.** No change under `client/conversion/`. Invalid Bopomofo rows keep being used through R3's fallback and blank-text rows keep being skipped by it; whitespace-only text rows keep being rules. What changes for conversion is indirect and intended: an OK no longer deletes those rows, so conversion output no longer changes because the user pressed OK. Making conversion ignore invalid rows would change output for existing dictionaries (Q3, not recommended).

**D8. Import, Export, Rename, Delete, Create: out of scope, nothing to fix.** They copy, rename, unlink or create files without parsing rows, so they keep every row (and the BOM) byte for byte. Their partial-new-file failure modes are F-2 D6's follow-up, unrelated to rows.

**D9. No new user-visible string, no change to `dialog.py`.** The dialog already talks only to the model; the model's public surface keeps its meaning (`entries`, `visible_entries`, `visible_count`, `cell_text`, `add`, `replace`, `remove`, `apply_filter`, `save`, `load`). A notice such as "2 rows cannot be shown and are kept" would need a new msgid and `.po`/`.mo` updates; not essential for the data-loss fix (Q2).

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Open the entries editor | rows with blank text or invalid Bopomofo skipped silently | same rows shown; the skipped rows are kept hidden in the model, in file order |
| Filter | over the shown rows | unchanged; preserved rows never match (they are not shown) |
| Add | duplicate check over every shown row (filter-hidden included); appended at the end | duplicate check also over preserved rows' text (existing message); appended at the end of the file, after any trailing preserved row |
| Edit | identity replace; same duplicate rule | same; preserved rows keep their places |
| Delete | removes the first equal entry | unchanged; a preserved row is never removed |
| OK | writes the shown rows only: preserved rows deleted from the file (F-W11) | writes all rows in file order; preserved rows field-exact (D3); same atomic write, same error messages; the Q2 normalization of shown rows remains |
| Cancel | nothing written | unchanged |
| Dictionary Management count | shown rows only | unchanged (D6) |
| Import / Export / Rename / Delete / Create | byte copy, rename, unlink, header-only file | unchanged |
| Conversion (R3) | uses invalid Bopomofo rows (fallback) and whitespace-only sources; output changes after any OK | code unchanged; output no longer changes after an unchanged OK |

`dict_badbopo.csv` (`text,braille,type` / `臺北,⠞⠺,Braille` / `肚子,ㄉㄨˋ|ㄗ˙,Bopomofo` / `數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo`, CRLF, no BOM): the editor shows one row; count `1`; OK leaves the file byte-identical (before: 2 lines); deleting `臺北` and pressing OK leaves the header and the two Bopomofo rows; adding `肚子` shows `來源文字「肚子」已存在。`.

## Design per File

### `client/dictionaries/entries.py` (tabs)

- `from collections.abc import Iterable`.
- `PreservedDictionaryRow` (frozen dataclass, D2) with a docstring: a row the editor does not show (blank source text, or a Bopomofo row whose sequence does not parse); kept as read and written back unchanged at its place in the file. `DictionaryRow = DictionaryEntry | PreservedDictionaryRow`.
- `load_dictionary_rows(path)` (D2): missing file gives `[]`; same `open(..., newline="", encoding="utf-8-sig")`, same `DictReader`; errors propagate as today (P2-2 Q8 unchanged).
- `_is_editable(entry)`: `False` for blank text; for type `Bopomofo`, `False` when `normalize_zhuyin_sequence(entry.braille)` raises any `Exception` (today's `except Exception`). It calls `normalize_zhuyin_sequence` through the module global, so `test_loads_only_rows_accepted_by_the_editor`'s `patch("dictionaries.entries.normalize_zhuyin_sequence", ...)` still applies.
- `load_dictionary_entries(path)`: the filter of D2, docstring "The rows the editor shows and Dictionary Management counts."
- `save_dictionary_entries(path, rows: Iterable[DictionaryRow])`: body unchanged apart from the loop variable; docstring unchanged ("Replace the file atomically; on an error it is unchanged.").

### `client/dictionaries/entry_list_model.py` (tabs)

- Import `DictionaryRow` and `load_dictionary_rows` instead of `load_dictionary_entries`.
- `__init__(self, rows: Iterable[DictionaryRow] = ())`: `self._rows = list(rows)`; `_entries` becomes a private property `[row for row in self._rows if isinstance(row, DictionaryEntry)]` (dictionaries are small; the filter already rebuilds a list per keystroke).
- New property `rows -> tuple[DictionaryRow, ...]` (every row in file order; used by tests). `entries`, `visible_entries` keep their meaning (editable entries only).
- `load` calls `load_dictionary_rows`; `save` passes `self._rows`, docstring "Write every row (preserved rows unchanged, in place); errors propagate."
- `source_text_exists`: over `self._rows` (D5). `add`: `self._rows.append`. `replace`: identity search in `self._rows`. `remove`: `self._rows.remove(current_entry)`.
- Module docstring: the model owns every file row in file order; rows that are not a `DictionaryEntry` are never shown, filtered, edited or removed and keep their place; the duplicate rule covers them.
- `ImportGuardTest`'s import set is unchanged.

### Not changed

`client/dialog.py`, `client/gui.py`, `client/shared/atomic_write.py`, `client/dictionaries/manager.py`, `client/dictionaries/presenter.py`, `client/conversion/`, `client/locales/`, `client/tests/fixtures/`.

## What Stays Identical

- The rows the editor shows, their order, the filter, the selection rules, every wx call (the golden trace's 1,040 per-action observations of the 40 sequences replay unchanged; see Test Plan G).
- The bytes OK writes for a dictionary without preserved rows (dict23: item 23's sha256 `ef319c21…`).
- `load_dictionary_entries`'s result; Dictionary Management counts.
- Conversion rules for every dictionary file, and the conversion golden `translation_golden.json`.
- Import/Export/Rename/Delete/Create; F-2's atomic write and messages.
- msgids 353, same set; `client/locales` unchanged.
- Fixtures: `dictionary_entries_trace.json` and `translation_golden.json` byte-identical (sha256 above).

## Test Plan

New test code follows each file's indentation (tabs in `test_dictionary_entries.py`, `test_dictionary_entry_list_model.py`, `test_dictionary_management_dialog.py`; 4 spaces in `test_dictionary_entries_dialog.py`). All use temporary directories; nothing touches `client/dictionary/`. Test data is inline (the bytes of `dict_badbopo.csv` are written by the test, not read from the history folder). The behavior tests were prototyped in `$SP/f4spec/` against today's code and the prototype implementation (see Counts).

Test labels: P (pin), S (storage), M (model), E (editor), G (golden trace); `D1`-`D9` remain the decisions.

### P. Pin (`test_dictionary_management_dialog.py`, `DictionaryManagementVirtualListTest`)

- P1 `test_rows_the_editor_does_not_show_are_not_counted`: the `dict_badbopo.csv` bytes; the count column shows `"1"`. Green before and after (D6).

### S. Storage (`test_dictionary_entries.py`, `DictionaryEntryStorageTest`)

Red for all: `ImportError: cannot import name 'PreservedDictionaryRow' from 'dictionaries.entries'` (the module fails to load, one error).

1. S1 `test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order`: a file with `Alpha,⠁,General`, `,⠃,General`, `  ,⠃,General`, `肚子, ㄉㄨˋ|ㄗ˙ ,Bopomofo`, `媽,ㄇㄚ ,Bopomofo`, `,⠃` (two fields), `"q,""x""","a<CRLF>b",Bopomofo`, `Beta,⠃,General` gives `[DictionaryEntry(Alpha), Preserved("", "⠃", "General"), Preserved("  ", "⠃", "General"), Preserved("肚子", " ㄉㄨˋ|ㄗ˙ ", "Bopomofo"), Preserved("媽", "ㄇㄚ ", "Bopomofo"), Preserved("", "⠃", ""), Preserved('q,"x"', "a\r\nb", "Bopomofo"), DictionaryEntry(Beta)]`.
2. S2 `test_save_writes_preserved_rows_unchanged_at_their_place`: saving that list gives the same bytes as the file of S1, except `,⠃` written as `,⠃,`.
3. S3 `test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical`: the `dict_badbopo.csv` bytes, `save_dictionary_entries(path, load_dictionary_rows(path))`, bytes identical (the F-W11 storage regression).
4. S4 `test_round_trip_normalizes_only_the_bom_line_ends_and_quoting`: `BOM + text,braille,type\n"肚子","ㄉ",Bopomofo\n` comes back as `text,braille,type\r\n肚子,ㄉ,Bopomofo\r\n` (an invalid one-symbol sequence, quoted, LF, BOM).
5. S5 `test_round_trip_keeps_the_conversion_rules`: the file of S1; `LoadedDictionaryRules.from_paths(path, client/data/Bopomofo2Braille.csv, processing=normalize_zhuyin_sequence)` before and after the round trip are equal, and contain a rule for `肚子` (prototype: today's OK turns 6 rules into 2).
6. S6 `test_a_preserved_row_is_never_equal_to_an_entry`: `PreservedDictionaryRow("a", "b", "General") != DictionaryEntry("a", "b", "General")` and `[entry].count(preserved) == 0` (guards the model's `list.remove`, D2).

`test_load_filters_empty_and_invalid_bopomofo_rows`, `test_save_load_roundtrip`, the BOM and failure tests stay unchanged.

### M. Model (`test_dictionary_entry_list_model.py`, new class `PreservedRowsTest`; and `LoadSaveTest`)

Red: `AttributeError: 'DictionaryEntryListModel' object has no attribute 'rows'`, or the preserved row shows up in `entries`/`visible_entries`, or no `DuplicateEntryError`.

1. M1 `test_preserved_rows_are_not_entries_and_never_visible`: model `[alpha, kept, beta]` (`kept = Preserved("肚子", "ㄉㄨˋ|ㄗ˙", "Bopomofo")`): `entries == visible_entries == (alpha, beta)`; filters `"ㄉ"` and `"肚"` give `()`; `rows == (alpha, kept, beta)`.
2. M2 `test_remove_and_add_leave_preserved_rows_in_place`: `remove(0)`, `add(gamma)`: `rows == (kept, beta, gamma)`.
3. M3 `test_replace_leaves_preserved_rows_in_place`: `replace(0, delta)`: `rows == (delta, kept, beta)`.
4. M4 `test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate`: `add(DictionaryEntry("肚子", "ㄉㄨˋㄗ˙", "Bopomofo"))` and `replace(1, <same>)` raise `DuplicateEntryError("肚子")`; `rows` unchanged.
5. M5 `LoadSaveTest.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place`: load the file of S1, save to a new path: bytes as in S2.

### E. Editor (`test_dictionary_entries_dialog.py`)

- **Flip** `test_unchanged_dictionary_is_rewritten_in_normalized_form` to `test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form`: same input; expected `HEADER + "Alpha,⠁,General\r\n,⠃,General\r\nZhuyin,invalid,Bopomofo\r\nBeta,⠃,General\r\n"`. The `# KNOWN BUG (P2-2 spec, Q2)` marker stays, its comment narrowed to what remains (whitespace stripped, unknown type rewritten as `General`; skipped rows kept since F-4). Red: the old output.
- E1 `test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical`: `open_editor(data=<dict_badbopo bytes>)`; `rows() == [["臺北", "⠞⠺", UNICODE_BRAILLE]]`; `press_ok()` is `True`; the file bytes equal the input (F-W11 regression at the GUI boundary).
- E2 `test_deleting_every_shown_row_keeps_the_hidden_rows`: select 0, Delete, `rows() == []`, OK: `HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n"`.
- E3 `test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message`: script `("肚子", "ㄉㄨˋㄗ˙", "Bopomofo")`, Add: log exactly `[["AddSymbolDialog", None], ["MessageBox", _duplicate_message("肚子"), ERROR_TITLE, ERROR_FLAGS]]`; OK leaves the file byte-identical.
- `test_loads_only_rows_accepted_by_the_editor` unchanged.

### G. Golden trace (`DictionaryEntriesTraceTest`), fixture unchanged

`TRACE_CSV` contains the blank-text row `,⠃,General` and the invalid Bopomofo row `zz,ab,Bopomofo`. The fixture was recorded on the pre-P2-2 editor, which deleted both on OK, so every sequence's final `csv` lacks them. With F-4 the replay's last step differs in exactly that: prototype result, all 40 sequences fail at the `ok` step only, and with the amended oracle below all 40 pass, i.e. the 1,040 per-action observations (logs, rows, selection, filter) and the `ok` step's log and state are unchanged, and no recorded action ever adds `zz` or a blank source text, so D5 does not show up in the trace.

The fixture is **not** regenerated (sha256 stays `f493da52…6c2cf`; the module docstring says never regenerate to make a change pass). Instead `test_replay_matches_every_recorded_step` amends its oracle for the last step only: a module constant `_TRACE_KEPT_ROWS = (",⠃,General", "zz,ab,Bopomofo")` (written with `\u2803` in the source, like `TRACE_CSV`) with a comment (recorded before F-4, when OK dropped them); before comparing, the replay splits the actual `csv` on `"\r\n"`, asserts that the lines equal to a kept row are exactly `_TRACE_KEPT_ROWS` in that order (each once, blank-text row first), removes them and joins the rest with `"\r\n"`; then every step is compared with `assertEqual` as today. Line-wise, not substring: `ab,⠃,General` ends with `,⠃,General` (a substring version failed 6 seeds in the prototype). Exact positions are pinned by S and M, not by the trace. `write_trace_fixture` is not changed. Red: before the fix, the new assertion fails for all 40 seeds (the kept rows are missing).

### Counts

New: P 1, S 6, M 5, E 3 = 15; the flip replaces one test; the trace change adds none. Expected `Ran 1226`, `FAILED (errors=1, skipped=5)` (the F-W6 error), with the runtime copied as in Current State. Prototype (`$SP/f4spec/`): with S1-S4, M1-M4, E1-E3, one characterization test of `load_dictionary_entries` and the trace change applied to the worktree (then reverted), `Ran 1223`, only the unflipped Q2 test and F-W6 failing; S5 and S6 run separately, green; on today's code all twelve behavior tests are red as stated.

## Migration Steps (each step one green commit, red first)

1. `test: pin that Dictionary Management counts only the rows the editor shows (F-4)`: P1 (green on today's code). 1212 tests.
2. `fix: keep the dictionary rows the editor does not show when saving (F-4)`: D2/D3 in `entries.py`; tests S1-S6 (red: one `ImportError`). The model still loads entries only, so the editor still drops the rows and the Q2 test still passes. 1218 tests.
3. `fix: keep hidden dictionary rows in place through the entries editor (F-4)`: D4/D5 in `entry_list_model.py`; tests M1-M5, E1-E3, the Q2 flip, the trace oracle change (red: M errors/failures, E1-E3 and the flipped test fail on the old output, the trace fails 40 subtests). 1226 tests.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; stage explicit paths only. No commit touches `client/locales/`, the fixtures, `client/dictionary/`, `client/braille/`, `dialog.py`, `gui.py`, `shared/atomic_write.py` or `conversion/`.

## Acceptance Criteria

1. `cd client && $PY -m unittest discover -s tests`: `Ran 1226`, `FAILED (errors=1, skipped=5)`, the error F-W6 only.
2. Focused: `$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_conversion_text_dictionary_rules tests.test_translation_golden -v` passes.
3. Fixture sha256 unchanged (`git diff <merge-base> -- client/tests/fixtures` empty).
4. msgid scan: `353 sha256 24dbc629…5277c`; `git diff <merge-base> -- client/locales` empty.
5. `git diff <merge-base> --stat -- client` lists only `dictionaries/entries.py`, `dictionaries/entry_list_model.py` and the four test files.
6. `grep -rn "KNOWN BUG (P2-2 spec, Q2)" client/tests` still finds the flipped test (narrowed comment).
7. Mutation check (plan): each mutant is caught: preserved fields stripped; preserved type normalized (`""` written as `General`); preserved rows written at the end; blank-text rows shown as entries; invalid Bopomofo rows shown; preserved rows not written; duplicate check over entries only; `load_dictionary_entries` returning all rows (P1); `PreservedDictionaryRow` made a subclass of / equal to `DictionaryEntry`; `remove` by equality over rows matching a preserved row; trace oracle removing substrings instead of lines.
8. App data: `client/dictionary/` in the main checkout untouched (never used by the tests).

## Windows Verification (packaged build)

Build per `docs/superpowers/history/2026-10-09-03-windows-verification/test.md` section 0.1 in this worktree (runtime and MathCAT copied as in Current State), `D:\dxtest\N-f4\DotExpress.exe`. The 2026-10-09-03 scripts are not edited: a `rerun.py` in the F-4 history folder (`docs/superpowers/history/2026-10-09-NN-f4-keep-invalid-bopomofo-rows/auto/`, `NN` the next free number, `06` if F-3's `05` is merged first) runs them with `D:\dxtest\N\DotExpress.exe` replaced by the F-4 exe and every work folder `D:\dxtest\auto<N>` replaced by `D:\dxtest\auto<N>-f4` in memory (items 25 and 29 attach to item 24's folder, so they all use `auto24-f4`); for item 25 it runs the script only up to `# 29 ACL deny write` (that section uses `(W)`, superseded by `item29.py`, F-W13). Data files from `auto/data/` copied to `D:\dxtest\data\`. Separate venv with `pywinauto`, `psutil`.

| # | Script | Expected after F-4 | Before (N, 2026-10-09-03) |
| --- | --- | --- | --- |
| 23 | `item23.py` (B and N-f4) | `dict23`: B and N-f4 identical, sha256 `ef319c21…`, CRLF, no BOM. `dict_badbopo`: N-f4 `changed: False`, lines 4 -> 4, sha256 `c4324573…`; B 4 -> 2 (F-W11 baseline); manager shows `dict_badbopo` `1` in both | `dict_badbopo` 4 -> 2 in N and B |
| 24 | `item24.py` | unchanged: counts, rows, no BOM after OK, conversion uses the dictionary | same |
| 25-28 | `item25.py` up to item 28 | unchanged (F-2 write path untouched): 25 `[WinError 5]`, file unchanged, no `.tmp`; 26 `[Errno 13]`; 27 replaced, hidden attribute lost; 28 0/10 failures | same |
| 29 | `item29.py` | unchanged: replaced, deny ACE gone; restored | same |
| 35 (new) | `item35.py`, fresh `D:\dxtest\auto35-f4` | import `dict_badbopo`; manager count `1`; select it in Settings, convert `肚子數學` (output O1); editor shows one row; OK: bytes = source (sha256 `c4324573…`), no `.tmp`; convert again: output = O1; editor: Delete `臺北`, OK: `text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n`, count `0`; restart: editor empty, file unchanged. Optional, manual if the script cannot drive the entry dialog: Add `肚子` / `ㄉㄨˋㄗ˙` / Bopomofo shows `來源文字「肚子」已存在。` and the file stays unchanged | B: the first OK leaves 2 lines and the second conversion output differs from O1 |

Item numbers 30-34 are F-3's; renumber 35 if F-3's numbering changes. Item 35 can run on B for the "Before" column.

## Interaction with F-3 (in progress on `fix/f3-dep-atomic-write`)

F-3 changes `client/shared/atomic_write.py` (shared core, `write_bytes_atomically`, `ensure_writable`), `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/gui.py` (Save/Add/Rename handlers, import loop) and `test_atomic_write.py`, `test_document_workspace.py`, `test_workspace_service.py`, `test_gui_document_flows.py`, `case_insensitive_package_files.py`, `windows_file_handles.py`. F-4 changes none of these files (D3: `write_text_atomically` is used as is; F-3 keeps its signature, behavior and 15 tests), so no textual merge conflict is expected in `client/`. Semantic dependency: only `write_text_atomically(path, write, encoding="utf-8", newline="")`, unchanged by F-3. Likely conflicts are limited to documentation: the history folder number and the Windows verification item numbers (F-3 uses 30-34; F-4 uses 35), and any shared `test.md`/review record either task updates. After both merge, expected `Ran 1263` (1211 + F-3's 37 + F-4's 15), `FAILED (errors=1, skipped=7)`; run the dictionary tests and `tests.test_atomic_write` after the second merge.

## Risks

- **Hidden rows the user cannot see** (medium, accepted by option A). The editor gives no hint that a file has preserved rows; the count excludes them. The user fixes them outside the app (Q2).
- **Duplicate refused for an invisible row** (low-medium, D5). The message names the source text but the row is not in the list; the user must edit the CSV. Before F-4 the same add succeeded and silently deleted the old row on OK.
- **Field-exact, not byte-exact** (low, D3). A preserved row written with LF, extra quoting, missing fields or extra columns comes back normalized, as every other row of the file already does on OK.
- **Model change under the golden trace** (low). `_entries` becomes derived; the trace and the 60+ editor tests pin every observable; the trace oracle change is limited to the two named lines of the last step.
- **Performance** (very low). One list comprehension per filter or edit over the file's rows.

## Open Questions for the User (decided 2026-10-09, see "Corrected after planning")

**Q1. Adding an entry whose source text equals a hidden row's.** **Recommended: refuse with the existing duplicate message (D5).** Alternatives: (a) accept and append; the hidden row stays earlier in the file and conversion keeps using it, so the new entry has no effect; (b) let the new entry replace the hidden row in place, which lets the editor delete a hidden row implicitly (contradicts option A's "cannot delete them") and needs a rule for which hidden row is replaced. **Decided: refuse.** **Decided by orchestrator with the recommended default; user may override before merge.**

**Q2. Telling the user that rows are hidden** (for example "2 rows cannot be shown and are kept unchanged" in the editor, or `1 (+2)` in Dictionary Management). **Recommended: not in F-4**; it needs new msgids and `.po`/`.mo` updates and is not needed to stop the loss. Follow-up UX task. **Decided: no notice in F-4** (known defect; follow-up UX task). **Decided by orchestrator with the recommended default; user may override before merge.**

**Q3. Conversion keeps using invalid Bopomofo rows** through R3's fallback (D7). The brief expected them to be ignored by translation; they are not, today or after F-4. **Recommended: keep conversion unchanged in F-4**; ignoring them would change conversion output for existing dictionaries and belongs with P1-6 defect 2 (the swallowed `processing` exception) if wanted. **Decided: conversion unchanged in F-4** (follow-up with P1-6 defect 2). **Decided by orchestrator with the recommended default; user may override before merge.**

## Out of Scope / Follow-ups

- The rest of P2-2 Q2: OK still rewrites an unchanged dictionary, stripping shown rows' text and braille (which can change which source R3 matches), rewriting unknown types as `General`, dropping extra columns, overflow fields, the BOM and blank lines, and normalizing line ends and quoting. Fix: write only when the list changed, or keep shown rows' raw fields too.
- The UX of Q1 and Q2 above; P2-2 Q4-Q6, Q8 (Q4's identity remove also fixes the D4 imprecision, F-4 review M-2); F-W12 (an unreadable dictionary makes Dictionary Management fail silently).
- `manager.py` writers through the atomic helper (F-2 D6).
- Validating dictionary rows for conversion (Q3, P1-6 defect 2).
