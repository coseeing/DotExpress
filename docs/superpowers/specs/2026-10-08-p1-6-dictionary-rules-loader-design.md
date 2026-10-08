# Dictionary Rules Loader (P1-6) Design

## Goal

Read the user dictionary and the Bopomofo rule file once per conversion instead of once per language segment, without changing any output. This is roadmap task P1-6 in `storage/refactor.md` (section 6.2), covering the first two bullets of section 5.6 and the Repository row of section 4.3:

- `dictionary_rules.apply_dictionary` opens and parses two CSVs (the selected dictionary and `data/Bopomofo2Braille.csv`) on every call, and `pipeline.translate_plain_text_segment` calls it once for every plain-text item the language detector yields. A mixed zh/en document re-reads the dictionary N times.
- `char_maps._load_char_mapping` reads `data/BopomofoChar2Braille.csv` and `data/Braille2Ascii.csv` on every conversion.

Concretely:

- `conversion/text/dictionary_rules.py` gains `LoadedDictionaryRules`, an immutable value object holding the parsed raw and replacement rules (and their compiled match tries), built by `LoadedDictionaryRules.from_paths(dictionary_path, bopomofo_path, *, processing)` and applied with `.apply(text)`.
- A conversion-scoped `DictionaryRulesLoader` builds it on first use and returns the same object afterwards. `conversion/service.translate_with_language_dual_view_segments` creates one loader per call and passes it to every `translate_plain_text_segment` call, so a conversion reads each dictionary file at most once.
- `apply_dictionary` keeps its signature and output and becomes a thin wrapper over `from_paths(...).apply(...)`.
- The character maps already read each file at most once per conversion; they keep their code and get read-count guards.
- The pytest-style `tests/test_conversion_text_dictionary_rules.py`, which `unittest` never runs today, becomes a `unittest` module.

This is a behavior-preserving refactor. For any input, the braille text, the ASCII output, the alignment and the dual-view segments are byte-identical to `main` at `cdae2f1`. The P1-5 golden fixture `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) must not change. No user-facing string changes.

Not in this task: one `LanguageDetector` per segment (section 5.6, third bullet), the preprocessing script read (once per conversion already), the `_translate_plain_text_segment` monkeypatch alias (section 5.5), the function-local imports in `pipeline.py`, caching anything across conversions, and changing CSV encoding or validation rules (for example accepting a BOM).

## Current State (verified 2026-10-08 on `refactor/p1-6-dictionary-rules-loader`, HEAD `cdae2f1`, P0-1..P0-6 and P1-1..P1-5 merged)

Indentation: every file touched here (`conversion/text/*.py`, `conversion/service.py`, `conversion/output.py` and the test modules named below) uses 4 spaces.

### Call path and who reads what

`ConversionPresenter._start` builds the `ConversionRequest` on the UI thread (`gui._build_conversion_request`: `dictionary_path = dictionary_path_for_name(selected_dictionary, dictionary_dir)`, `data_dir = resource_path("data")`). The path is frozen in the request; no file is opened on the UI thread. `ConversionJobRunner._run_job` then calls `conversion.service.convert_text_with_alignment(request, runtime=...)` on a daemon worker thread, and every file read below happens on that thread. A `ConversionStageError` is delivered to the UI with `call_after`; any other exception is not caught by the runner.

| Step (worker thread) | Code | File read | Reads per conversion today |
| --- | --- | --- | --- |
| Preprocessing script | `output.convert_text_with_alignment` -> `pipeline.preprocess_source_text` -> `execute_preprocessing_script` | `<dictionary dir>/preprocessing.py` | 1 |
| Bopomofo character map | `preprocess_source_text` -> `map_char(..., data_dir / "BopomofoChar2Braille.csv")` (`char_maps._load_char_mapping`, lines 5-30) | `BopomofoChar2Braille.csv` | 1 |
| Dictionary rules | `service.translate_with_language_dual_view_segments` (lines 26-73) -> per text segment `_translate_plain_text_segment` (line 52) -> per language item `apply_dictionary` (`pipeline.py:70`, `dictionary_rules.py:111-184`) | selected dictionary CSV and `Bopomofo2Braille.csv` | once per plain-text item each |
| ASCII output | `output.convert_text_with_alignment`, only when `output_mode == "ascii"`, after wrapping | `Braille2Ascii.csv` | 0 or 1 |

Measured with a counting `Path.open` wrapper on the golden inputs (real `client/data`, the golden one-row dictionary):

| Input | preprocessing.py | BopomofoChar2Braille | Bopomofo2Braille | dictionary | Braille2Ascii (ascii mode) |
| --- | --- | --- | --- | --- | --- |
| `chinese_prose` (3 segments) | 1 | 1 | 3 | 3 | 1 |
| `english_math` (6 segments) | 1 | 1 | 4 | 4 | 1 |
| `long_document` (360 segments) | 1 | 1 | 240 | 240 | 1 |
| `$x$` (math only) | 1 | 1 | 0 | 0 | - |

Cost: converting `long_document` takes 0.11 s with the one-row dictionary and 2.24 s with a 2,000-row dictionary on this box. Under a profiler, CSV parsing is about 40% of the dictionary time and building the match tries (`_replace_with_trie` builds a fresh trie for every call, and `apply_dictionary` builds one more per `Bopomofo`-type row) about 35%. Both scale with segments times rows.

So the character maps are already read once per conversion; the dictionary and `Bopomofo2Braille.csv` are the hot spot.

### Parse and validation semantics of `apply_dictionary` (characterized by probes; all must stay)

- `dictionary_path` is wrapped in `Path(...)`; if it does not exist, the function returns `{"raw": text, "replacement": text}` and **does not open `Bopomofo2Braille.csv`** (a missing or broken Bopomofo file is then not an error).
- Otherwise it reads `Bopomofo2Braille.csv` first, then the dictionary, both with `open("r", newline="", encoding="utf-8")` and `csv.DictReader`.
- Errors, in this order: Bopomofo file missing -> `FileNotFoundError`; no header (empty file) -> `ValueError("CSV must contain header row.")`; missing columns -> `ValueError("CSV must contain columns: Bopomofo, Braille")`, then the same for the dictionary with `text, braille, type`. Invalid UTF-8 -> `UnicodeDecodeError`. A UTF-8 BOM is not stripped, so a BOM-prefixed header fails the column check (`ValueError`).
- Rows: an empty source (`text` or `Bopomofo`) is skipped; a missing cell reads as `""` (a dictionary row with no `braille` gives an empty atomic replacement `\[\]`); extra cells are ignored; rule order is file order and the first duplicate source wins (trie).
- `type == "Bopomofo"`: `processing(target)` (production: `text.zhuyin.normalize_zhuyin_sequence`, pure, returns a list) splits the target; if it raises, the exception is swallowed and the whole target is one part. Each part is mapped through the Bopomofo rules. Any other type splits the target on `@`. Parts are aligned per source character when the counts match, otherwise collapsed to one part, and wrapped in `\[...\]`.
- `bopomofo_path` is used as `bopomofo_path.open(...)` without `Path(...)`, so a `str` raises `AttributeError`. Every caller passes a `Path`.

### Error timing at the conversion level (all must stay)

- Every dictionary error surfaces as `ConversionStageError("translation", error)` (the `translate_segments` try block in `output.py`).
- The preprocessing script runs first: a failing script gives stage `text_processing` even if the dictionary is broken.
- The dictionary is opened only when the first plain-text item is translated. Empty input returns before anything is read; **math-only input never reads the dictionary, so a malformed dictionary (or a missing `Bopomofo2Braille.csv`) does not fail it** (probed: `$x$` with a header-less dictionary converts fine).
- Math segments before the first text segment are translated before the dictionary error is raised.

### Can the files change during or between conversions?

- **Between conversions:** yes, and the next conversion must see it. The Dictionary Management dialog and the dictionary entries dialog write the CSV; the selected dictionary is saved in settings and resolved into `request.dictionary_path` when the next request is built. Nothing caches parsed rules today.
- **During a conversion through the app:** no. `set_conversion_busy(True)` disables the File and Translation menus (Dictionary Management lives under Translation), the document list (and so its Actions popup) and the input editor until the job ends. No keyboard shortcut opens a dictionary dialog. The selected dictionary path is frozen in the request.
- **During a conversion from outside:** possible (an external editor saving the CSV). Today later segments then see the new file, so one document can be converted with two dictionary versions.
- **Concurrent conversions:** `convert_for_export` supersedes a running job without stopping it (P1-4 known defect 2), so two worker threads can run conversions at once. They share no state today.

### Tests today

- `tests/test_conversion_text_dictionary_rules.py` holds 7 pytest-style module functions; `python -m unittest tests.test_conversion_text_dictionary_rules` prints `NO TESTS RAN`, and pytest is not installed or a project dependency. Called directly, all 7 pass.
- `tests/test_conversion_text_pipeline.py` (13 tests) and `tests/test_conversion_text_char_maps.py` call `apply_dictionary`, `translate_plain_text_segment` and `translate__mapping_char` with path arguments. Nothing counts reads.
- `tests/test_removed_dead_code.py` asserts that `char_maps.translate__mapping_char` and `dictionary_rules.apply_dictionary` exist (P0-3 kept them on purpose).
- The golden fixture uses a one-row `Braille/Unicode` dictionary only; it has no `Bopomofo` or `@` rows, so it does not cover the Bopomofo branch.
- Baseline: full suite (Linux venv, alphabetical) 783 tests, `failures=1` (the known P2-5 test), `errors=0`, `skipped=9`.

## Design

### `LoadedDictionaryRules` (`conversion/text/dictionary_rules.py`)

```python
@dataclass(frozen=True)
class LoadedDictionaryRules:
    raw_rules: tuple[tuple[str, str], ...] = ()
    replacement_rules: tuple[tuple[str, str], ...] = ()
    _raw_trie: _TrieNode = field(init=False, repr=False, compare=False)
    _replacement_trie: _TrieNode = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_raw_trie", _build_trie(self.raw_rules))
        object.__setattr__(self, "_replacement_trie", _build_trie(self.replacement_rules))

    @classmethod
    def from_paths(cls, dictionary_path, bopomofo_path, *, processing) -> "LoadedDictionaryRules": ...

    def apply(self, text: str) -> dict[str, str]: ...
```

- `from_paths` is the body of today's `apply_dictionary` up to the two `mapping(...)` calls, unchanged in order and messages: `Path(dictionary_path)`; missing -> `cls()` without touching the Bopomofo file; else parse `Bopomofo2Braille.csv`, build its trie once, parse the dictionary row by row exactly as today, mapping each `Bopomofo` part with that one trie. It returns `cls(tuple(raws), tuple(replacements))`.
- `apply(text)` returns `{"raw": _scan_trie(text, self._raw_trie), "replacement": _scan_trie(text, self._replacement_trie)}`. With no rules (missing or header-only dictionary) it returns `{"raw": text, "replacement": text}` without scanning. Scanning with an empty trie returns the text unchanged, so this shortcut gives the same strings either way.
- Immutable: frozen, tuple fields, no setters. The tries are private, built once in `__post_init__` and never mutated after that. Sharing an instance between threads would be safe, but nothing shares one.
- `processing` is a required keyword argument (no default), so this module still does not import `text.zhuyin`.
- Accepted widening: `from_paths` also wraps `bopomofo_path` in `Path(...)`, so a `str` works instead of raising `AttributeError`. No caller passes a `str`.

### Trie build and scan split

`_replace_with_trie(text, replacements)` is split into `_build_trie(replacements) -> _TrieNode` (the first loop, including "the first duplicate source wins") and `_scan_trie(text, root) -> str` (the longest-prefix scan). `_replace_with_trie` becomes `return _scan_trie(text, _build_trie(replacements))`, so `mapping()` (public, signature unchanged) behaves exactly as before. The two loops are moved, not edited.

### `apply_dictionary` stays

```python
def apply_dictionary(text, dictionary_path, bopomofo_path, processing):
    return LoadedDictionaryRules.from_paths(dictionary_path, bopomofo_path, processing=processing).apply(text)
```

Same signature, return type, errors and reads (one of each file per call). After this task no production code calls it; it stays for the existing tests and the P0-3 guard in `tests/test_removed_dead_code.py`, which therefore does not change.

### `DictionaryRulesLoader` (conversion-scoped, lazy, at most once)

```python
class DictionaryRulesLoader:
    """Loads one conversion's dictionary rules on first use and keeps them for that conversion."""

    def __init__(self, dictionary_path, bopomofo_path, *, processing) -> None: ...  # stores arguments, reads nothing

    def load(self) -> LoadedDictionaryRules:
        if self._rules is None:
            self._rules = LoadedDictionaryRules.from_paths(
                self._dictionary_path, self._bopomofo_path, processing=self._processing
            )
        return self._rules
```

- Lazy on purpose. Loading eagerly at the start of `convert_text_with_alignment` (the roadmap's wording) would change error behavior: a broken dictionary would fail math-only input that converts today, and a broken dictionary plus a broken preprocessing script would report the wrong stage. Loading eagerly just before translation would still fail math-only input. Lazy loading reads at the same moment as today's first `apply_dictionary` call, so the exception type, message, stage and timing are unchanged.
- A failed load is not memoized: `self._rules` stays `None` and the exception propagates (and aborts the conversion, as today).
- Not thread-safe by design: one loader serves one conversion on one worker thread. No module-level state, no cache across conversions, so every conversion re-reads the files and sees edits made before it started.

### Pipeline (`conversion/text/pipeline.py`)

```python
def dictionary_rules_loader(dictionary_path, bopomofo_path) -> DictionaryRulesLoader:
    from text.zhuyin import normalize_zhuyin_sequence
    return DictionaryRulesLoader(dictionary_path, bopomofo_path, processing=normalize_zhuyin_sequence)


def translate_plain_text_segment(
    text, dictionary_path, translation_tables, bopomofo_path, *,
    runtime, lang, charset_maps,
    dictionary_rules: DictionaryRulesLoader | None = None,
):
    if dictionary_rules is None:
        dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)
    ...
            result = dictionary_rules.load().apply(item)
```

- The new keyword is optional, so the existing direct callers and tests (path arguments only) keep working; a standalone call now reads each file at most once per call instead of once per item.
- When a loader is passed, it wins and the path arguments are not read again. The service builds the loader from the same two paths, so they always agree.
- The function-local `text.zhuyin` import moves from `translate_plain_text_segment` into `dictionary_rules_loader` and stays function-local; `LanguageDetector` handling is unchanged.

### Service (`conversion/service.py`) is the once-per-conversion boundary

`translate_with_language_dual_view_segments` keeps its signature. After the `text == ""` early return it creates `dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)` and passes `dictionary_rules=dictionary_rules` to every `_translate_plain_text_segment` call.

- `convert_text_with_alignment` calls it exactly once per conversion, and `translate_with_language` and `translate_with_language_segments` go through it too, so every public entry point reads the dictionary at most once per call.
- Why here and not in `output.convert_text_with_alignment` (the roadmap's wording): it is the single function every text-translation path goes through, and `output.py`'s `TranslateSegments` contract, `ConversionRequest` and the `map_char` seam stay unchanged. Loading in `output.py` would need a new argument through `translate_segments`, the service's inner adapter and the test fakes, plus a fallback for the public `translate_with_language*` functions anyway.
- Creating the loader reads nothing, so math-only input still reads no dictionary.

### Character maps: no production change

`BopomofoChar2Braille.csv` and `Braille2Ascii.csv` are each read at most once per conversion today, at points with their own error semantics (`BopomofoChar2Braille` after the user script, inside the generic `translation` handler; `Braille2Ascii` only in ASCII mode, after wrapping, as stage `ascii`). Moving them into the loader would either move those reads (changing when and in which stage they fail) or repeat the lazy machinery for no read-count gain, and it would break the `map_char` injection seam that four tests use. `char_maps.py` and `output.py` therefore do not change; read-count guards pin the current once-per-conversion behavior.

### What changes in behavior (intended, documented)

- **One dictionary snapshot per conversion.** If an external program rewrites the dictionary or `Bopomofo2Braille.csv` while a conversion is running, the whole conversion now uses the version read at its first plain-text item, instead of mixing versions. Through the app this cannot happen (the menus are disabled while busy). The next conversion reads the new file.
- `processing` runs once per `Bopomofo` row per conversion instead of once per row per item. It is pure, so outputs are the same.

## What Stays Identical

- Braille output (Unicode and ASCII), the source-text wrap, the alignment lists and the dual-view segments for every input; the golden fixture is unchanged.
- Signatures and return types of `apply_dictionary`, `mapping`, `split_bracket_segments`, `translate_plain_text_segment` (plus one optional keyword), `translate_with_language*`, both `convert_text_with_alignment`, `preprocess_source_text`, `translate__mapping_char` and `map_characters`; `ConversionRequest`, `ConversionOutput` and `TranslateSegments`.
- Exception types, messages and stages for every malformed or missing file, and the moment they are raised.
- Reads stay on the conversion worker thread; the UI thread still only resolves paths.
- `dictionaries/manager.py`, `gui.py`, `ConversionJobRunner` and the conversion presenter do not change. No string, menu, dialog, `.po`/`.mo`, packaging, liblouis DLL or table change.

## Test Plan

All new tests are `unittest` and use 4 spaces. Characterization tests (part A) are written against unchanged production code and pass before any production change. Expected strings are literal values captured from unchanged code, never computed by the code under test.

### A. Characterization (step 1, before any production change)

1. **Convert `tests/test_conversion_text_dictionary_rules.py` to `unittest`**: the 7 functions become methods of `ApplyDictionaryTest` with the same assertions (`tmp_path` becomes a `TemporaryDirectory` in `setUp`). They now run: 7 tests that were silently skipped before.
2. **Rule matrix** (same module, class `DictionaryRulesCasesTest`): a module-level table `DICTIONARY_CASES` of (dictionary rows, Bopomofo rows, input, expected `raw`, expected `replacement`) covering: `Braille` row with `@` split and aligned parts; length mismatch collapsed to one part; overlapping sources (longest wins, no cascading); duplicate source (first wins); a row with an empty `text` (skipped), a row with no `braille` cell (`\[\]`), a row with an extra cell; a `Bopomofo` row with a `processing` that returns a list, one that raises, and one with the real `normalize_zhuyin_sequence` and the real `client/data/Bopomofo2Braille.csv`; input containing `\[` and `\]` literally; empty input. One test runs every case through `apply_dictionary` with `subTest`.
3. **File and header semantics** (class `DictionaryFileSemanticsTest`): missing dictionary -> identity and `Bopomofo2Braille.csv` never opened (counted, and also with that file absent); missing `Bopomofo2Braille.csv` with an existing dictionary -> `FileNotFoundError`; empty file, missing columns and BOM header -> the exact `ValueError` messages for each file; invalid UTF-8 -> `UnicodeDecodeError`; both files malformed -> the Bopomofo message (order). A test helper `_error_cases()` returns this table so step 3 can reuse it.
4. **Conversion-level error timing** (`tests/test_conversion_service.py`, class `DictionaryErrorTimingTest`, real pipeline, recording fake runtime like the module's existing tests): header-less dictionary with text -> `ConversionStageError` stage `translation` with the `ValueError`; the same dictionary with `$x$` and with `""` -> success; a failing preprocessing script plus a broken dictionary -> stage `text_processing`; a math segment before the first text segment is translated before the error (math translator called once).
5. **Fresh between conversions** (same class): convert, rewrite the dictionary with a different rule, convert again -> the second output uses the new rule; delete the dictionary, convert again -> no dictionary applied.

### B. Trie split (step 2)

No new tests: the existing tests, part A and the golden fixture cover it. A throwaway check in the step (not committed) confirms `_scan_trie(text, _build_trie(rules)) == _replace_with_trie(text, rules)` for the part A matrix.

### C. `LoadedDictionaryRules` (step 3, `tests/test_conversion_text_dictionary_rules.py`, class `LoadedDictionaryRulesTest`)

- Every `DICTIONARY_CASES` entry through `LoadedDictionaryRules.from_paths(...).apply(input)` gives the same literal expectations.
- Every `_error_cases()` entry raises the same exception type and message from `from_paths`, and the missing-dictionary case returns `LoadedDictionaryRules()` without opening the Bopomofo file.
- The instance is immutable: assigning `raw_rules` raises `FrozenInstanceError`; both rule fields are tuples of `(str, str)` in file order.
- `apply` reads no file and builds no trie: with `Path.open` and `_build_trie` patched to count, three `apply` calls on one instance cause 0 opens and 0 builds.
- `LoadedDictionaryRules().apply(text)` returns `{"raw": text, "replacement": text}`.

### D. Loader and read counts (step 4)

- `DictionaryRulesLoaderTest` (`tests/test_conversion_text_dictionary_rules.py`): constructing a loader opens nothing; three `load()` calls call `from_paths` once and return the same object; a `load()` that raises is retried by the next `load()` (2 calls).
- `DictionaryReadCountTest` (`tests/test_conversion_text_pipeline.py`), counting `pathlib.Path.open` by file name (`dictionary_rules.py` and `char_maps.py` both open through `Path.open`; the test asserts the counted names include the dictionary, so a switch to another open function fails loudly instead of passing with zero reads):
  - A mixed zh/en text with inline math that yields at least 8 plain-text items (asserted as a precondition by counting `LoadedDictionaryRules.apply` calls): in `unicode` mode the dictionary, `Bopomofo2Braille.csv` and `BopomofoChar2Braille.csv` are each opened exactly once and `Braille2Ascii.csv` never; in `ascii` mode `Braille2Ascii.csv` once. On the old code the first two are opened once per item, so this test is red before step 4.
  - `LoadedDictionaryRules.from_paths` is called once per conversion and `_build_trie` three times (Bopomofo, raw, replacement), independent of the number of items.
  - Math-only input opens neither the dictionary nor `Bopomofo2Braille.csv`.
  - `translate_with_language(...)` called directly opens each dictionary file once.
  - Two consecutive conversions call `from_paths` twice (no cross-conversion cache).
- `DictionarySnapshotTest` (`tests/test_conversion_service.py`): a fake text translator rewrites the dictionary file after its first call; every later item in the same conversion still uses the first version, and the next conversion uses the new one. This documents the intended snapshot change and is red on the old code.

### E. Unchanged tests

The 13 pipeline tests, the char-map tests, `test_conversion_service`, `test_conversion_language_explicit`, `test_removed_dead_code` and the golden test pass at every step without edits (other than the converted module in A1).

## Migration Steps (each step is one green commit; the plan details them)

1. `test: characterize dictionary rule loading` (part A; also converts the pytest module). Characterization cannot be red; the plan adds a throwaway mutation check (for example, the dictionary reader skipping the first row, or `apply_dictionary` not checking existence) showing the new tests catch it.
2. `refactor: split dictionary trie build and scan` (part B).
3. `refactor: add LoadedDictionaryRules` (`from_paths`, `apply`, `apply_dictionary` as wrapper; part C, red first because the class does not exist).
4. `refactor: load dictionary rules once per conversion` (`DictionaryRulesLoader`, `dictionary_rules_loader`, the pipeline keyword, the service wiring; part D, red first on the read counts and the snapshot test).

The golden fixture is never regenerated in this task.

## Acceptance Criteria

1. Roadmap verification passes on Linux: `cd client && python -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service -v`, with only the known P2-5 failure. `tests.test_conversion_text_dictionary_rules` now reports tests instead of `NO TESTS RAN`.
2. Also green: `tests.test_translation_golden tests.test_conversion_language_explicit tests.test_removed_dead_code tests.test_conversion_jobs tests.test_conversion_presenter tests.test_main_demo`.
3. `git diff main -- client/tests/fixtures/translation_golden.json` is empty and its sha256 is still `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`; `tests.test_translation_golden` passes at every commit of this task.
4. Full suite (alphabetical): 783 + new tests (about 30, including the 7 converted ones; the plan fixes the number), `failures=1` (P2-5 only), `errors=0`, `skipped=9`. The shuffled-module harness (seeds 0-19) shows the same single failure for every seed.
5. Read-count guards (part D) pass: per conversion each of the dictionary, `Bopomofo2Braille.csv`, `BopomofoChar2Braille.csv` and (ASCII mode) `Braille2Ascii.csv` is opened at most once.
6. `grep -n "apply_dictionary(" client/conversion` shows only its definition; `grep -n "\.open(" client/conversion/text/dictionary_rules.py` shows only reads inside `from_paths`.
7. Measured (reported, not a test): `long_document` with a 2,000-row dictionary converts in well under the 2.24 s baseline on this box (the plan's scratch script prints before and after).
8. `git diff main --stat -- client/locales scripts client/braille client/gui.py client/dictionaries client/conversion/output.py client/conversion/text/char_maps.py` is empty.

## Risks

- **Error timing drift** (medium impact, low likelihood). An eager load would fail math-only conversions with a broken dictionary. Mitigation: the lazy loader and the A4 tests.
- **Parse drift** (high impact, low likelihood). `from_paths` must keep the read order, skipping rules, `processing` fallback and messages. Mitigation: the code is moved, not rewritten; the A2/A3 tables run against both APIs; the golden fixture covers the whole pipeline.
- **Shared trie between items** (low). One trie object now serves every item of a conversion; a scan only reads it. `_scan_trie` must not mutate nodes (it does not today), and the Bopomofo trie is used only inside `from_paths`.
- **Snapshot semantics** (low). Externally edited files are read once per conversion instead of per item. Documented; the next conversion picks the change up; the app cannot edit during a conversion.
- **Concurrent conversions** (low). A superseded export job and a new job each have their own loader; there is no module-level cache to race on.
- **Read-count guard brittleness** (low). It counts `Path.open`; the guard asserts the dictionary was seen at least once, so a change of open function fails loudly rather than passing vacuously.
- **Windows-only paths** (low, unverifiable here). Reading is pure Python, but a packaged build with real liblouis and real user dictionaries should be checked; see the verification debt.

## Known defects found during this investigation (not fixed here)

1. A dictionary saved with a UTF-8 BOM (as some Windows editors do) fails with "CSV must contain columns: text, braille, type", and so do the data files. `dictionaries.manager.validate_dictionary_csv` (import) has the same behavior. Accepting `utf-8-sig` would be a behavior change; a separate task should decide it together with import validation.
2. A broken `Bopomofo2Braille.csv` is only reported when a dictionary file exists and the input has plain text, and `apply_dictionary` silently ignores `processing` failures (the whole Bopomofo target becomes one part). Both are kept.
3. `LanguageDetector` is still built once per text segment (section 5.6, third bullet), and the preprocessing script is still compiled per conversion; neither is in the P1-6 row.

## Windows verification debt

- On a packaged build, before and after: convert a long mixed zh/en document with inline math using a large user dictionary that has `Braille`, `Braille/Unicode` (`@` split) and `Bopomofo` rows, in Unicode and ASCII output modes; the Braille Result text and the exported BRL must be byte-identical, and the conversion should be visibly faster.
- Edit the dictionary in Dictionary Management between two conversions and confirm the second conversion uses the edit.
- Run the Windows-only modules (`tests.test_liblouis_runtime`, `tests.test_translation_language_result`, `tests.test_language_detection_translation`) and compare with the baseline (the last two already fail for reasons recorded in P1-1 and P1-5).
- No menu, dialog or string changes, so no screenshots and no `generate_pot.bat` run are needed.

## Out of Scope

- Caching parsed rules across conversions (would need airtight invalidation on edits, renames, deletes and selection changes; the per-conversion read is cheap once it is no longer per item).
- Loading the character maps through the loader, changing `map_char`, `ConversionRequest` or `TranslateSegments`.
- `LanguageDetector` reuse, the preprocessing script, the `_translate_plain_text_segment` alias and the other module aliases in `service.py` (section 5.5), and moving pipeline imports to module level.
- BOM handling and any other change to CSV validation (known defect 1).
- `ApplicationPaths` (P2-6), the P2-5 tokenizer work and its failing test, and indentation (P2-8).
