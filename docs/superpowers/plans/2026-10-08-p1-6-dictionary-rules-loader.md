# Dictionary Rules Loader (P1-6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read the user dictionary and `data/Bopomofo2Braille.csv` once per conversion instead of once per plain-text item, without changing any output. `conversion/text/dictionary_rules.py` gains the immutable `LoadedDictionaryRules` (parsed rules plus their compiled tries, built by `from_paths` and applied by `apply`) and the conversion-scoped, lazy `DictionaryRulesLoader`; `pipeline.translate_plain_text_segment` takes an optional `dictionary_rules` loader; `service.translate_with_language_dual_view_segments` creates one loader per call and passes it to every text segment. `apply_dictionary` keeps its signature and becomes a wrapper. The character maps keep their code and get read-count guards. The pytest-style `tests/test_conversion_text_dictionary_rules.py` becomes a `unittest` module. Byte-identical output (golden fixture unchanged); same exception types, messages, stages and timing; no user-facing string changes; `.po`/`.mo` untouched.

**Architecture:** Four commits in the spec's order. Task 1 is the safety net on unchanged production code (converted module, rule matrix, file and header errors, conversion-level error timing and freshness); it cannot be red, so a throwaway mutant runner shows it catches four deliberate breakages. Task 2 splits the trie build from the scan (no new tests; a throwaway check compares the old and new trie code on 5,000 random cases). Tasks 3 and 4 each start with failing tests: Task 3 adds `LoadedDictionaryRules` (red: the class does not exist), Task 4 adds the loader and the wiring (red: the dictionary is opened 12 times for a 12-item text, and a dictionary rewritten during a conversion leaks into later items).

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `dataclasses`, `csv`, `collections.Counter`). wxPython is not installed and not needed: nothing here touches `gui.py` or a dialog. liblouis loads only on Windows; the read-count tests use the fallback translators and the golden test drives the real adapters with fakes.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-6-dictionary-rules-loader-design.md` (authoritative, commit `945becf`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-6-dictionary-rules-loader`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (6, nothing else): production `client/conversion/text/dictionary_rules.py`, `client/conversion/text/pipeline.py`, `client/conversion/service.py`; tests `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_conversion_service.py`. Never touch `client/conversion/output.py`, `client/conversion/text/char_maps.py`, `client/gui.py`, `client/dictionaries/`, `client/locales/`, `scripts/`, `client/braille/` or `client/tests/fixtures/translation_golden.json`.
- Indentation: every touched file uses 4 spaces (no tabs). The patches and file blocks carry the exact characters; run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- The golden fixture is never regenerated. Its sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd` is checked after every task; if `tests.test_translation_golden` fails, the production change is wrong.
- New test text is ASCII except braille cells, Bopomofo, CJK sample text and the BOM (written as the `﻿` escape).
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, and absolute paths are stripped from import errors, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p16impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.4.
- Baseline (re-verified at `945becf`, the spec commit; code identical to `cdae2f1`): `$PY -m unittest discover -s tests` gives `Ran 783 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: acceptance criterion 6's first command checks nothing.** `grep -n "apply_dictionary(" client/conversion` names a directory without `-r`, so grep prints no match and the check passes whatever the code does. The plan runs `grep -rn "apply_dictionary(" client/conversion`, which prints exactly the definition (`client/conversion/text/dictionary_rules.py:249:def apply_dictionary(`). The second command (`grep -n "\.open(" client/conversion/text/dictionary_rules.py`) is fine and prints the two reads inside `from_paths` (lines 152 and 168).
2. **Refinement: test count fixed at 35 new tests (783 -> 818).** Task 1: 17 (the 7 converted functions, 1 rule-matrix test, 3 file-semantics tests, 6 conversion-level tests); Task 2: 0; Task 3: 6; Task 4: 12 (3 loader, 8 read-count, 1 snapshot). The spec said "about 30".
3. **Refinement: two pipeline tests beyond the spec's list.** The spec's Pipeline section states two behaviors that part D does not test: a standalone `translate_plain_text_segment` call (no loader) reads each file once per call, and a passed loader wins over the path arguments. `DictionaryReadCountTest` pins both (`test_standalone_plain_text_segment_opens_each_dictionary_file_once`, `test_plain_text_segment_uses_the_given_loader_instead_of_the_paths`; the latter passes paths that do not exist and checks the loader's dictionary is applied and opened once across two calls).
4. **Refinement: shared conversion fixture.** The A4/A5 tests (`DictionaryErrorTimingTest`) and the D snapshot test (`DictionarySnapshotTest`) in `tests/test_conversion_service.py` share a test-less base class `DictionaryConversionTestCase` (temporary data directory with header-only `BopomofoChar2Braille.csv` and `Bopomofo2Braille.csv`, a dictionary at `dictionary/default.csv`, the module's recording fakes). The tests in `tests/test_conversion_text_dictionary_rules.py` share `DictionaryFilesTestCase` (a temporary directory with `dictionary.csv` and `bopomofo.csv`) and an `OpenRecorder` context manager that records `Path.open` file names.
5. **Refinement: the rule matrix and the error table.** `DICTIONARY_CASES` has 11 cases (the spec's list, with "empty `text` skipped", "no `braille` cell" and "extra cell" in one dictionary, the overlap and no-cascading rules in one dictionary, plus a header-only dictionary). `_error_cases()` has 10 cases; the message is compared for every `ValueError`, while `FileNotFoundError` and `UnicodeDecodeError` are checked by type only (their messages name temporary paths or byte offsets). "Both malformed" uses missing columns in both files and expects the Bopomofo message.
6. **Refinement: Task 4's red step.** The pipeline read-count tests reach the new names through the module (`dictionary_rules.DictionaryRulesLoader`), so the red run shows the real defect (`dictionary.csv` and `Bopomofo2Braille.csv` opened 12 times, `from_paths` called 12 and 24 times, the snapshot `['X', 'Y', 'Y']`) instead of a module import error; only the loader-only tests in `tests/test_conversion_text_dictionary_rules.py` fail at import. `test_math_only_conversion_opens_no_dictionary_file` is already green on the old code: it pins existing behavior that an eager load would break.
7. **Refinement: the Task 2 check is against the old code.** After the split, `_replace_with_trie` is literally `_scan_trie(text, _build_trie(rules))`, so comparing the two in the working tree would be tautological. The throwaway `trie_split_check.py` loads the committed (pre-split) module from `git show HEAD:` and compares its `_replace_with_trie` and `mapping(..., marker=True)` with the new `_replace_with_trie`, `_scan_trie(_build_trie(...))` and `mapping(..., marker=True)` on 5,000 seeded random rule sets and texts that include the marker characters.
8. **Refinement: acceptance criterion 7 (timing).** Measured on this box, `long_document` with a 2,000-row dictionary: 2.25 s before, 0.066 s after (34 times faster), same display text length. Timings vary between machines, so the final check prints only "same display length: True" and "at least 10x faster: True"; the raw timings are kept in `$T/perf_before.txt` and `$T/perf_after.txt` for the handoff note.

Everything else in the spec was re-checked at `945becf`: the read counts per input (`chinese_prose` 3, `english_math` 4, `long_document` 240, `$x$` 0 for both dictionary files; the character maps and the preprocessing script once), every error and timing probe (header-less, BOM, empty, Latin-1, short rows, missing dictionary, missing `Bopomofo2Braille.csv` with and without a dictionary, the `str` Bopomofo path `AttributeError`), the 13 pipeline tests, the 7 pytest-style functions (`NO TESTS RAN` under `unittest`), the P0-3 guard and the line numbers cited in the spec.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `945becf` (`$SP/p16plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 4 the 20 shuffle seeds, the msgid scan and every acceptance criterion passed. The patches in this file are `git diff`s of those commits, split into the red test step and the implementation step; Task 1's rewritten test module is given as a whole file because its diff (the 7 pytest functions turned into methods) is harder to read than the file. Then this file's blocks were run in order on fresh clones (`$SP/p16plan/replay1`, `replay2`, each with a stand-in plan commit) by a harness that compares every "Expected" block with the real output: all 4 commits applied, every expected block (20) matched byte for byte, and the resulting `client/` tree is identical to the dry clone. Final sha256: `client/conversion/text/dictionary_rules.py` `23f6325adbe9a2d31bb9a7a2cdcd70352db0bbc22ef369e638eb622696e2fa32`, `client/conversion/text/pipeline.py` `be7a398b8760d52ad477103b65dec370a4e6c120481631e9bf2bff5723c71d32`, `client/conversion/service.py` `2b814fcbeb8e78dfdf3ee8d3b279598748885c90762bca2a8719dc598d1002ba`, `client/tests/test_conversion_text_dictionary_rules.py` `36aefa0e5001a822244541e9e62b1fc3bb3e08c66e55642ff103bf0cf8785f5c`, `client/tests/test_conversion_text_pipeline.py` `f4597ba768e7d00da69ca83a378d210738b6faff9dcfdda81f3b92b5ade1e6a1`, `client/tests/test_conversion_service.py` `ea017c6f2cea2159eb9a61ee90e134dee114de6755e86d9a74f4d2fe7b1c27c3`; `client/tests/fixtures/translation_golden.json` unchanged at `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`.

## Review Focus

1. **Same output.** `from_paths` is `apply_dictionary`'s parse moved into a classmethod (re-indented, same order, same messages); the only edits are `Path(bopomofo_path)` (the accepted widening), building the Bopomofo trie once (`_build_trie`) and mapping each part with `_scan_trie(part, bopomofo_trie)` instead of `mapping(part, replacements_bopomofo)` (equal, because `mapping` without markers is `_replace_with_trie`, which Task 2 defines as `_scan_trie(_build_trie(...))`). `apply` scans the stored tries; the empty-rules shortcut returns the same strings a scan of an empty trie would. Guards: the 11-case matrix runs through both `apply_dictionary` and `from_paths(...).apply`, the golden fixture is unchanged, and `git diff -w` of Task 3 shows the moved block.
2. **Same errors at the same moment.** The loader is lazy: creating it reads nothing; the first `load()` happens at the first plain-text item, exactly where the first `apply_dictionary` call was. A failed load is not kept. Guards: `DictionaryErrorTimingTest` (stage `translation`, math-only and empty input succeed with a broken dictionary, the preprocessing stage wins, math before the first text is translated first), the 10-case error table through both APIs, and the mutant "dictionary loaded before the first segment" (2 tests fail).
3. **Once per conversion, fresh per conversion.** One loader per `translate_with_language_dual_view_segments` call, no module-level state. Guards: `DictionaryReadCountTest` (each rule file opened once in Unicode and ASCII mode for a 12-item text, `from_paths` once and `_build_trie` three times per conversion, twice for two conversions, never for math-only input), `test_next_conversion_reads_the_rewritten_dictionary`, `test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule`, and `DictionarySnapshotTest` for the intended snapshot change.
4. **Immutability.** `LoadedDictionaryRules` is a frozen dataclass of two tuples; the tries are private, built in `__post_init__`, excluded from `repr` and equality, and only read by `_scan_trie`. Guards: `test_rules_are_immutable_tuples_in_file_order`, `test_apply_reads_no_file_and_builds_no_trie`.
5. **Untouched seams.** `output.py`, `char_maps.py`, `ConversionRequest`, `TranslateSegments`, `map_char` and the `_translate_plain_text_segment` alias are unchanged; `apply_dictionary` keeps the P0-3 guard green and has no production caller left.

## File Map

- Task 1: rewrite `client/tests/test_conversion_text_dictionary_rules.py`; modify `client/tests/test_conversion_service.py`.
- Task 2: modify `client/conversion/text/dictionary_rules.py`.
- Task 3: modify `client/conversion/text/dictionary_rules.py`, `client/tests/test_conversion_text_dictionary_rules.py`.
- Task 4: modify `client/conversion/text/dictionary_rules.py`, `client/conversion/text/pipeline.py`, `client/conversion/service.py`, `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_conversion_service.py`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 783 |
| 1 characterization | 17 (7 converted, 1 matrix, 3 file semantics, 6 conversion) | 800 |
| 2 trie split | 0 | 800 |
| 3 `LoadedDictionaryRules` | 6 | 806 |
| 4 loader and wiring | 12 (3 loader, 8 read count, 1 snapshot) | 818 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case. The fixture sha256 stays `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `dictionary_mutants.py "<mutant>"`: applies one deliberate breakage in memory (the source files are not changed) and runs the Task 1 tests (`tests.test_conversion_text_dictionary_rules` and `tests.test_conversion_service.DictionaryErrorTimingTest`), printing the failure and error counts.
- `trie_split_check.py <rev>`: compares the trie code at `<rev>` with the working tree on 5,000 seeded random cases.
- `dictionary_perf.py <client_dir>`: converts the golden `long_document` with a 2,000-row dictionary three times and prints the best time and the display text length.
- Existing: `$SP/p12/tools/msgid_scan.py` (the P0-5 AST stand-in for xgettext; source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`) and `$SP/shuffle_harness.py <seed>` (runs every test module in a seeded random order, one process).

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
```

Expected (no output from `status`; HEAD is the plan commit):

```text
docs: plan dictionary rules loader
refactor/p1-6-dictionary-rules-loader
```

- [ ] **Step 2: Create the tools.**

```bash
mkdir -p $T/tools
cat > $T/tools/dictionary_mutants.py <<'EOF'
"""Run the P1-6 characterization tests against deliberately broken code (throwaway; from client/).

Usage: python dictionary_mutants.py "<mutant>"
The mutant is applied in memory (the source files are not changed) before the tests are loaded.
"""
import importlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, ".")

MUTANTS = {
    "dictionary reader skips the first row": (
        "conversion.text.dictionary_rules",
        "        raws: list[tuple[str, str]] = []\n",
        "        next(reader, None)\n        raws: list[tuple[str, str]] = []\n",
    ),
    "missing dictionary is not checked": (
        "conversion.text.dictionary_rules",
        "    if not dictionary_path.exists():\n",
        "    if False:\n",
    ),
    "processing errors are not swallowed": (
        "conversion.text.dictionary_rules",
        "                except Exception:\n",
        "                except KeyError:\n",
    ),
    "dictionary loaded before the first segment": (
        "conversion.service",
        "    segments_records = []\n",
        "    __import__('conversion.text.dictionary_rules', fromlist=['x']).apply_dictionary("
        "'', dictionary_path, bopomofo_path, lambda text: text)\n    segments_records = []\n",
    ),
}
TESTS = (
    "tests.test_conversion_text_dictionary_rules",
    "tests.test_conversion_service.DictionaryErrorTimingTest",
)

name = sys.argv[1]
module_name, old, new = MUTANTS[name]
module = importlib.import_module(module_name)
source = Path(module.__file__).read_text(encoding="utf-8")
if source.count(old) != 1:
    raise SystemExit(f"{name}: anchor not found exactly once")
exec(compile(source.replace(old, new), module.__file__, "exec"), module.__dict__)
pipeline = importlib.import_module("conversion.text.pipeline")
rules = importlib.import_module("conversion.text.dictionary_rules")
pipeline.apply_dictionary = rules.apply_dictionary
suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(f"{name}: ran={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}")
EOF
cat > $T/tools/trie_split_check.py <<'EOF'
"""Compare the committed _replace_with_trie/mapping with the working tree's (throwaway, P1-6; from client/).

Usage: python trie_split_check.py <git-rev>
Loads client/conversion/text/dictionary_rules.py at <git-rev> next to the working-tree module and
compares _replace_with_trie, _scan_trie(_build_trie(...)) and mapping(..., marker=True) on seeded
random rules and texts.
"""
import random
import subprocess
import sys

sys.path.insert(0, ".")
from conversion.text import dictionary_rules as new

old_source = subprocess.run(
    ["git", "show", f"{sys.argv[1]}:client/conversion/text/dictionary_rules.py"],
    check=True, capture_output=True, text=True,
).stdout
old = {"__name__": "old_dictionary_rules"}
exec(compile(old_source, "old_dictionary_rules.py", "exec"), old)

rng = random.Random(16)
alphabet = "ab台灣\\[]"
cases = 0
for _ in range(5000):
    rules = [
        ("".join(rng.choice(alphabet) for _ in range(rng.randint(0, 3))), "".join(rng.choice("xyz") for _ in range(rng.randint(0, 2))))
        for _ in range(rng.randint(0, 6))
    ]
    text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
    expected = old["_replace_with_trie"](text, rules)
    assert new._replace_with_trie(text, rules) == expected, (text, rules)
    assert new._scan_trie(text, new._build_trie(rules)) == expected, (text, rules)
    assert new.mapping(text, rules, marker=True) == old["mapping"](text, rules, marker=True), (text, rules)
    cases += 1
print(f"trie split: {cases} random cases identical")
EOF
cat > $T/tools/dictionary_perf.py <<'EOF'
"""Time long_document with a 2,000-row dictionary (throwaway, P1-6).

Usage: python dictionary_perf.py <client_dir>
Run with the client directory as the working directory; prints the best of three runs in seconds.
"""
import csv
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from tests import test_translation_golden as golden
from conversion.service import ConversionRequest, convert_text_with_alignment

with tempfile.TemporaryDirectory() as directory:
    dictionary_path = Path(directory) / "dictionary.csv"
    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "braille", "type"])
        writer.writerow(["台灣", "⠞⠺", "Braille/Unicode"])
        for index in range(1999):
            writer.writerow([f"詞{index:04d}", "⠁⠃", "Braille"])
    request = ConversionRequest(
        raw_text=golden.INPUTS["long_document"],
        output_mode="unicode",
        width=40,
        dictionary_path=dictionary_path,
        data_dir=golden.DATA_DIR,
        translation_tables=dict(golden.TRANSLATION_TABLES),
        lang=golden.LANG,
        charset_maps=dict(golden.DEFAULT_CHARSET_MAPS),
    )
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        output = convert_text_with_alignment(request, runtime=golden._runtime())
        timings.append(time.perf_counter() - start)
    print(f"{min(timings):.3f} {len(output.display_text)}")
EOF
```

- [ ] **Step 3: Record the baseline suite, msgids, read counts and timing.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_conversion_text_dictionary_rules 2>&1 | grep -E '^Ran|^NO TESTS RAN' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | grep -E '^source'
sha256sum tests/fixtures/translation_golden.json
$PY -B $T/tools/dictionary_perf.py . > $T/perf_before.txt
```

Expected (the P2-5 failure; the dictionary-rules module collects nothing under `unittest`; 353 source msgids; the golden sha256):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 783 tests
FAILED (failures=1, skipped=9)
Ran 0 tests
NO TESTS RAN
source msgids: 353
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

---

### Task 1: Characterize dictionary rule loading (spec part A)

**Files:**
- Rewrite: `client/tests/test_conversion_text_dictionary_rules.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Convert the pytest module and add the matrix and file-semantics tests.** The 7 module functions become methods of `ApplyDictionaryTest` with the same assertions (`tmp_path` comes from `DictionaryFilesTestCase.setUp`; the unused `DICTIONARY_MARKER_OPEN` import goes). `DictionaryRulesCasesTest` runs the 11 `DICTIONARY_CASES` through `apply_dictionary` with `subTest`; the expected strings are literals captured from the unchanged code. `DictionaryFileSemanticsTest` pins the missing-dictionary shortcut (no file opened, with and without the Bopomofo file), the read order (Bopomofo file first) and the 10 `_error_cases()`.

```bash
cat > $REPO/client/tests/test_conversion_text_dictionary_rules.py <<'PYEOF'
import csv
import tempfile
import unittest
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

from conversion.text.dictionary_rules import (
    apply_dictionary,
    split_bracket_segments,
)
from text.zhuyin import normalize_zhuyin_sequence


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DICTIONARY_HEADER = "text,braille,type\n"
BOPOMOFO_HEADER = "Bopomofo,Braille\n"
TEST_BOPOMOFO = BOPOMOFO_HEADER + "ㄉㄨˋ,⠙⠨\nㄗ˙,⠗⠂\n"


def _identity(text):
    return text


def _split_on_bar(text):
    return text.split("|")


def _raise_value_error(text):
    raise ValueError(f"cannot split {text}")


PROCESSING = {
    "identity": _identity,
    "split on |": _split_on_bar,
    "raises": _raise_value_error,
    "zhuyin": normalize_zhuyin_sequence,
}


class DictionaryCase(NamedTuple):
    name: str
    dictionary: str
    bopomofo: str | None  # None: the real client/data/Bopomofo2Braille.csv
    processing: str
    text: str
    raw: str
    replacement: str


# Expected strings were captured from the unchanged apply_dictionary (P1-6 step 1).
DICTIONARY_CASES = (
    DictionaryCase(
        "@ split aligned per character",
        DICTIONARY_HEADER + "音樂,abc@de,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        "聽音樂",
        r"聽\[音\]\[樂\]",
        r"聽\[abc\]\[de\]",
    ),
    DictionaryCase(
        "part count mismatch collapses to one part",
        DICTIONARY_HEADER + "音樂,a@b@c,Braille/Unicode\n",
        BOPOMOFO_HEADER,
        "identity",
        "音樂",
        r"\[音樂\]",
        r"\[abc\]",
    ),
    DictionaryCase(
        "longest source wins and output is not rescanned",
        DICTIONARY_HEADER + "台,t,\n台灣,wt,\nabc,foo,\no,bar,\n",
        BOPOMOFO_HEADER,
        "identity",
        "台灣台abco",
        r"\[台灣\]\[台\]\[abc\]\[o\]",
        r"\[wt\]\[t\]\[foo\]\[bar\]",
    ),
    DictionaryCase(
        "first duplicate source wins",
        DICTIONARY_HEADER + "台,first,\n台,second,\n",
        BOPOMOFO_HEADER,
        "identity",
        "台",
        r"\[台\]",
        r"\[first\]",
    ),
    DictionaryCase(
        "empty source skipped, missing cell empty, extra cell ignored",
        DICTIONARY_HEADER + ",zz,Braille\n台灣\n灣,⠺,Braille,extra\n",
        BOPOMOFO_HEADER,
        "identity",
        "台灣灣",
        r"\[台灣\]\[灣\]",
        r"\[\]\[⠺\]",
    ),
    DictionaryCase(
        "Bopomofo row with a processing that returns a list",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\n",
        TEST_BOPOMOFO,
        "split on |",
        "肚子",
        r"\[肚\]\[子\]",
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
        DICTIONARY_HEADER + "肚子,ㄉㄨˋㄗ˙,Bopomofo\n音樂,ㄧㄣ ㄩㄝˋ,Bopomofo\n",
        None,
        "zhuyin",
        "肚子聽音樂",
        r"\[肚\]\[子\]聽\[音\]\[樂\]",
        r"\[⠙⠌⠐\]\[⠓⠱⠁\]聽\[⠹⠄\]\[⠦⠐\]",
    ),
    DictionaryCase(
        "input that already contains markers",
        DICTIONARY_HEADER + "灣,w,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        r"\[台\]灣",
        r"\[台\]\[灣\]",
        r"\[台\]\[w\]",
    ),
    DictionaryCase(
        "empty input",
        DICTIONARY_HEADER + "灣,w,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        "",
        "",
        "",
    ),
    DictionaryCase(
        "header-only dictionary",
        DICTIONARY_HEADER,
        BOPOMOFO_HEADER,
        "identity",
        "台灣",
        "台灣",
        "台灣",
    ),
)

VALID_DICTIONARY = (DICTIONARY_HEADER + "台,t,\n").encode("utf-8")
VALID_BOPOMOFO = BOPOMOFO_HEADER.encode("utf-8")
BOPOMOFO_COLUMNS = "CSV must contain columns: Bopomofo, Braille"
DICTIONARY_COLUMNS = "CSV must contain columns: text, braille, type"
NO_HEADER = "CSV must contain header row."


class ErrorCase(NamedTuple):
    name: str
    dictionary: bytes
    bopomofo: bytes | None  # None: the Bopomofo file does not exist
    error: type
    message: str | None  # None: only the exception type is checked


def _error_cases() -> tuple[ErrorCase, ...]:
    return (
        ErrorCase("Bopomofo file missing", VALID_DICTIONARY, None, FileNotFoundError, None),
        ErrorCase("Bopomofo file empty", VALID_DICTIONARY, b"", ValueError, NO_HEADER),
        ErrorCase("Bopomofo columns missing", VALID_DICTIONARY, b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
        ErrorCase(
            "Bopomofo header with BOM",
            VALID_DICTIONARY,
            "﻿Bopomofo,Braille\n".encode("utf-8"),
            ValueError,
            BOPOMOFO_COLUMNS,
        ),
        ErrorCase("Bopomofo file not UTF-8", VALID_DICTIONARY, b"Bopomofo,Braille\n\xff,x\n", UnicodeDecodeError, None),
        ErrorCase("dictionary empty", b"", VALID_BOPOMOFO, ValueError, NO_HEADER),
        ErrorCase("dictionary columns missing", b"text,braille\n", VALID_BOPOMOFO, ValueError, DICTIONARY_COLUMNS),
        ErrorCase(
            "dictionary header with BOM",
            "﻿text,braille,type\n".encode("utf-8"),
            VALID_BOPOMOFO,
            ValueError,
            DICTIONARY_COLUMNS,
        ),
        ErrorCase("dictionary not UTF-8", b"text,braille,type\n\xe9,x,\n", VALID_BOPOMOFO, UnicodeDecodeError, None),
        ErrorCase("both malformed: Bopomofo first", b"text,braille\n", b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
    )


class OpenRecorder:
    """Record the file name of every pathlib.Path.open call while active."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def __enter__(self) -> "OpenRecorder":
        original_open = Path.open
        names = self.names

        def recording_open(path, *args, **kwargs):
            names.append(path.name)
            return original_open(path, *args, **kwargs)

        self._patcher = patch.object(Path, "open", recording_open)
        self._patcher.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._patcher.stop()


class DictionaryFilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = Path(self._tmpdir.name)
        self.dictionary_path = self.tmp_path / "dictionary.csv"
        self.bopomofo_path = self.tmp_path / "bopomofo.csv"

    def write_case_files(self, case: DictionaryCase) -> Path:
        self.dictionary_path.write_text(case.dictionary, encoding="utf-8")
        if case.bopomofo is None:
            return DATA_DIR / "Bopomofo2Braille.csv"
        self.bopomofo_path.write_text(case.bopomofo, encoding="utf-8")
        return self.bopomofo_path

    def write_error_files(self, case: ErrorCase) -> None:
        self.dictionary_path.write_bytes(case.dictionary)
        self.bopomofo_path.unlink(missing_ok=True)
        if case.bopomofo is not None:
            self.bopomofo_path.write_bytes(case.bopomofo)


class ApplyDictionaryTest(DictionaryFilesTestCase):
    def test_apply_dictionary_does_not_remap_dictionary_output(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "abc", "braille": "foo", "type": ""})
            writer.writerow({"text": "o", "braille": "bar", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "abc",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "foo", "atomic": True},
        ])

    def test_apply_dictionary_aligns_braille_multi_char_segments_with_at_separator(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "音樂", "braille": "abc@de", "type": "Braille"})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "音樂",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["raw"]), [
            {"text": "音", "atomic": True},
            {"text": "樂", "atomic": True},
        ])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "abc", "atomic": True},
            {"text": "de", "atomic": True},
        ])

    def test_apply_dictionary_longer_source_strings_win_over_shorter_overlaps(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "abc", "braille": "short", "type": ""})
            writer.writerow({"text": "abcd", "braille": "long", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "abcd",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "long", "atomic": True},
        ])

    def test_apply_dictionary_uses_longest_trie_match_without_target_prefix_requirement(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "台", "braille": "t", "type": ""})
            writer.writerow({"text": "台灣", "braille": "wt", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "台灣台",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "wt", "atomic": True},
            {"text": "t", "atomic": True},
        ])

    def test_apply_dictionary_bopomofo_branch_calls_processing_and_maps_output(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"
        processed: list[str] = []

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "肚子", "braille": "ㄉㄨˋ", "type": "Bopomofo"})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()
            writer.writerow({"Bopomofo": "ㄉㄨˋ", "Braille": "⠙⠨"})

        def processing(text: str) -> str:
            processed.append(text)
            return text

        result = apply_dictionary(
            "肚子",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=processing,
        )

        self.assertEqual(processed, ["ㄉㄨˋ"])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "⠙⠨", "atomic": True},
        ])

    def test_apply_dictionary_collapses_length_mismatch_to_one_segment(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "音樂", "braille": "abc", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "音樂",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["raw"]), [
            {"text": "音樂", "atomic": True},
        ])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "abc", "atomic": True},
        ])

    def test_split_bracket_segments_treats_unclosed_marker_as_text(self) -> None:
        self.assertEqual(split_bracket_segments(r"\[abc"), [
            {"text": r"\[abc", "atomic": False},
        ])


class DictionaryRulesCasesTest(DictionaryFilesTestCase):
    def test_apply_dictionary_gives_the_recorded_output_for_every_case(self) -> None:
        for case in DICTIONARY_CASES:
            with self.subTest(case=case.name):
                bopomofo_path = self.write_case_files(case)

                result = apply_dictionary(
                    case.text,
                    dictionary_path=self.dictionary_path,
                    bopomofo_path=bopomofo_path,
                    processing=PROCESSING[case.processing],
                )

                self.assertEqual(result, {"raw": case.raw, "replacement": case.replacement})


class DictionaryFileSemanticsTest(DictionaryFilesTestCase):
    def test_missing_dictionary_returns_text_without_opening_the_bopomofo_file(self) -> None:
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        for bopomofo_exists in (True, False):
            with self.subTest(bopomofo_exists=bopomofo_exists):
                if not bopomofo_exists:
                    self.bopomofo_path.unlink()

                with OpenRecorder() as recorder:
                    result = apply_dictionary(
                        "台灣",
                        dictionary_path=self.dictionary_path,
                        bopomofo_path=self.bopomofo_path,
                        processing=_identity,
                    )

                self.assertEqual(result, {"raw": "台灣", "replacement": "台灣"})
                self.assertEqual(recorder.names, [])

    def test_reads_the_bopomofo_file_before_the_dictionary(self) -> None:
        self.dictionary_path.write_bytes(VALID_DICTIONARY)
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)

        with OpenRecorder() as recorder:
            apply_dictionary(
                "台",
                dictionary_path=self.dictionary_path,
                bopomofo_path=self.bopomofo_path,
                processing=_identity,
            )

        self.assertEqual(recorder.names, ["bopomofo.csv", "dictionary.csv"])

    def test_malformed_files_raise_the_recorded_errors(self) -> None:
        for case in _error_cases():
            with self.subTest(case=case.name):
                self.write_error_files(case)

                with self.assertRaises(case.error) as context:
                    apply_dictionary(
                        "台",
                        dictionary_path=self.dictionary_path,
                        bopomofo_path=self.bopomofo_path,
                        processing=_identity,
                    )

                if case.message is not None:
                    self.assertEqual(str(context.exception), case.message)


if __name__ == "__main__":
    unittest.main()
PYEOF
```

- [ ] **Step 2: Add the conversion-level error timing and freshness tests.** `DictionaryErrorTimingTest` (on the test-less base `DictionaryConversionTestCase`) runs the real pipeline with the module's recording fakes.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index a52c56d..1de6e85 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -423,5 +423,103 @@ class ConversionServiceTest(unittest.TestCase):
         self.assertEqual(output.translation_results, ())
         self.assertEqual(output.dual_view_segments, ())
 
+
+class DictionaryConversionTestCase(unittest.TestCase):
+    """Real pipeline over a temporary dictionary and data directory (no tests of its own)."""
+
+    def setUp(self) -> None:
+        self._tmpdir = tempfile.TemporaryDirectory()
+        self.addCleanup(self._tmpdir.cleanup)
+        self.test_dir = Path(self._tmpdir.name)
+        self.data_dir = self.test_dir / "data"
+        self.data_dir.mkdir()
+        (self.data_dir / "BopomofoChar2Braille.csv").write_text("Bopomofo,Braille\n", encoding="utf-8")
+        (self.data_dir / "Bopomofo2Braille.csv").write_text("Bopomofo,Braille\n", encoding="utf-8")
+        self.dictionary_dir = self.test_dir / "dictionary"
+        self.dictionary_dir.mkdir()
+        self.dictionary_path = self.dictionary_dir / "default.csv"
+
+    def _convert(self, raw_text: str, runtime: TranslationRuntime) -> ConversionOutput:
+        request = ConversionRequest(
+            raw_text=raw_text,
+            output_mode="unicode",
+            width=40,
+            dictionary_path=self.dictionary_path,
+            data_dir=self.data_dir,
+            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
+        )
+        return convert_text_with_alignment(request, runtime=runtime)
+
+    def _runtime(self) -> TranslationRuntime:
+        return TranslationRuntime(text_translator=FakeTextTranslator(), math_translator=FakeMathTranslator())
+
+
+class DictionaryErrorTimingTest(DictionaryConversionTestCase):
+    """When a broken or edited dictionary is read, and which stage reports it."""
+
+    def test_headerless_dictionary_fails_text_at_the_translation_stage(self) -> None:
+        self.dictionary_path.write_text("", encoding="utf-8")
+
+        with self.assertRaises(ConversionStageError) as context:
+            self._convert("abc", self._runtime())
+
+        self.assertEqual(context.exception.stage, "translation")
+        self.assertIs(type(context.exception.error), ValueError)
+        self.assertEqual(str(context.exception.error), "CSV must contain header row.")
+
+    def test_headerless_dictionary_does_not_fail_math_only_or_empty_input(self) -> None:
+        self.dictionary_path.write_text("", encoding="utf-8")
+        for raw_text, segment_count in (("$x$", 1), ("", 0)):
+            with self.subTest(raw_text=raw_text):
+                output = self._convert(raw_text, self._runtime())
+
+                self.assertEqual(len(output.dual_view_segments), segment_count)
+
+    def test_failing_preprocessing_script_is_reported_before_a_broken_dictionary(self) -> None:
+        self.dictionary_path.write_text("", encoding="utf-8")
+        (self.dictionary_dir / "preprocessing.py").write_text(
+            "def main(text):\n    raise RuntimeError('script boom')\n",
+            encoding="utf-8",
+        )
+
+        with self.assertRaises(ConversionStageError) as context:
+            self._convert("abc", self._runtime())
+
+        self.assertEqual(context.exception.stage, "text_processing")
+        self.assertEqual(str(context.exception.error), "script boom")
+
+    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
+        self.dictionary_path.write_text("", encoding="utf-8")
+        runtime = self._runtime()
+
+        with self.assertRaises(ConversionStageError) as context:
+            self._convert("$x$abc", runtime)
+
+        self.assertEqual(str(context.exception.error), "CSV must contain header row.")
+        self.assertEqual(runtime.math_translator.calls, [("x", "Nemeth", LANG)])
+
+    def test_next_conversion_reads_the_rewritten_dictionary(self) -> None:
+        texts = []
+        for target in ("X", "Y"):
+            self.dictionary_path.write_text(f"text,braille,type\n甲,{target},Braille\n", encoding="utf-8")
+            runtime = self._runtime()
+            self._convert("甲", runtime)
+            texts.append([call[0] for call in runtime.text_translator.calls])
+
+        self.assertEqual(texts, [["X"], ["Y"]])
+
+    def test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule(self) -> None:
+        self.dictionary_path.write_text("text,braille,type\n甲,X,Braille\n", encoding="utf-8")
+        self._convert("甲", self._runtime())
+        self.dictionary_path.unlink()
+        runtime = self._runtime()
+
+        self._convert("甲", runtime)
+
+        self.assertEqual(runtime.text_translator.calls, [("甲", "zh-tw.ctb", "甲", False)])
+
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 3: Run the new tests on the unchanged code.** Characterization passes by construction.

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_service.DictionaryErrorTimingTest -v 2>&1 | grep -E ' \.\.\. |^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (17 tests):

```text
test_apply_dictionary_aligns_braille_multi_char_segments_with_at_separator (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_aligns_braille_multi_char_segments_with_at_separator) ... ok
test_apply_dictionary_bopomofo_branch_calls_processing_and_maps_output (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_bopomofo_branch_calls_processing_and_maps_output) ... ok
test_apply_dictionary_collapses_length_mismatch_to_one_segment (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_collapses_length_mismatch_to_one_segment) ... ok
test_apply_dictionary_does_not_remap_dictionary_output (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_does_not_remap_dictionary_output) ... ok
test_apply_dictionary_longer_source_strings_win_over_shorter_overlaps (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_longer_source_strings_win_over_shorter_overlaps) ... ok
test_apply_dictionary_uses_longest_trie_match_without_target_prefix_requirement (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_apply_dictionary_uses_longest_trie_match_without_target_prefix_requirement) ... ok
test_split_bracket_segments_treats_unclosed_marker_as_text (tests.test_conversion_text_dictionary_rules.ApplyDictionaryTest.test_split_bracket_segments_treats_unclosed_marker_as_text) ... ok
test_malformed_files_raise_the_recorded_errors (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_malformed_files_raise_the_recorded_errors) ... ok
test_missing_dictionary_returns_text_without_opening_the_bopomofo_file (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_missing_dictionary_returns_text_without_opening_the_bopomofo_file) ... ok
test_reads_the_bopomofo_file_before_the_dictionary (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_reads_the_bopomofo_file_before_the_dictionary) ... ok
test_apply_dictionary_gives_the_recorded_output_for_every_case (tests.test_conversion_text_dictionary_rules.DictionaryRulesCasesTest.test_apply_dictionary_gives_the_recorded_output_for_every_case) ... ok
test_failing_preprocessing_script_is_reported_before_a_broken_dictionary (tests.test_conversion_service.DictionaryErrorTimingTest.test_failing_preprocessing_script_is_reported_before_a_broken_dictionary) ... ok
test_headerless_dictionary_does_not_fail_math_only_or_empty_input (tests.test_conversion_service.DictionaryErrorTimingTest.test_headerless_dictionary_does_not_fail_math_only_or_empty_input) ... ok
test_headerless_dictionary_fails_text_at_the_translation_stage (tests.test_conversion_service.DictionaryErrorTimingTest.test_headerless_dictionary_fails_text_at_the_translation_stage) ... ok
test_math_before_the_first_text_is_translated_before_the_dictionary_error (tests.test_conversion_service.DictionaryErrorTimingTest.test_math_before_the_first_text_is_translated_before_the_dictionary_error) ... ok
test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule (tests.test_conversion_service.DictionaryErrorTimingTest.test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule) ... ok
test_next_conversion_reads_the_rewritten_dictionary (tests.test_conversion_service.DictionaryErrorTimingTest.test_next_conversion_reads_the_rewritten_dictionary) ... ok
Ran 17 tests
OK
```

- [ ] **Step 4: Show that the net can fail.** Each mutant is applied in memory; the source files stay unchanged.

```bash
for mutant in "dictionary reader skips the first row" "missing dictionary is not checked" "processing errors are not swallowed" "dictionary loaded before the first segment"; do
    $PY -B $T/tools/dictionary_mutants.py "$mutant"
done
git -C $REPO status --short
```

Expected (every mutant is caught; only the two test files are modified):

```text
dictionary reader skips the first row: ran=17 failures=14 errors=0
missing dictionary is not checked: ran=17 failures=0 errors=3
processing errors are not swallowed: ran=17 failures=0 errors=1
dictionary loaded before the first segment: ran=17 failures=1 errors=1
 M client/tests/test_conversion_service.py
 M client/tests/test_conversion_text_dictionary_rules.py
```

- [ ] **Step 5: Full suite and fixture.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
```

Expected (783 + 17):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 800 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_text_dictionary_rules.py client/tests/test_conversion_service.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize dictionary rule loading

Convert the pytest-style dictionary rule module to unittest (its 7 tests
never ran) and pin, on the unchanged code, the rule matrix, the file and
header errors, the read order, the missing-dictionary shortcut, and when
a conversion notices a broken or edited dictionary: stage, math-only and
empty input, preprocessing first, math before the first text, and the
next conversion after an edit or a delete.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize dictionary rule loading
```

---

### Task 2: Split the trie build from the scan (spec part B)

**Files:**
- Modify: `client/conversion/text/dictionary_rules.py`

No new tests: the existing tests, Task 1 and the golden fixture cover this move.

- [ ] **Step 1: Split `_replace_with_trie`.** The first loop becomes `_build_trie(replacements) -> _TrieNode` (including "the first duplicate source wins"), the scan becomes `_scan_trie(text, root) -> str`, and `_replace_with_trie` returns `_scan_trie(text, _build_trie(replacements))`, so `mapping()` is unchanged. The loops are moved, not edited.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/text/dictionary_rules.py b/client/conversion/text/dictionary_rules.py
index 08bd2de..8cc3dbe 100644
--- a/client/conversion/text/dictionary_rules.py
+++ b/client/conversion/text/dictionary_rules.py
@@ -24,13 +24,8 @@ class _TrieNode:
     target: str | None = None
 
 
-def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> str:
-    """Replace source text using left-to-right, longest-prefix matching.
-
-    The trie is built from dictionary sources and only the original input is
-    scanned. Emitted targets are never re-scanned, so replacement rules cannot
-    cascade into one another.
-    """
+def _build_trie(replacements: Iterable[tuple[str, str]]) -> _TrieNode:
+    """Build the match trie for (source, target) rules; empty sources are skipped."""
     root = _TrieNode()
     for source, target in replacements:
         if not source:
@@ -46,7 +41,16 @@ def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> st
         # Match the existing replacement order: the first duplicate source wins.
         if node.target is None:
             node.target = target
+    return root
+
 
+def _scan_trie(text: str, root: _TrieNode) -> str:
+    """Replace source text using left-to-right, longest-prefix matching.
+
+    Only the original input is scanned. Emitted targets are never re-scanned,
+    so replacement rules cannot cascade into one another. The trie is only
+    read, never changed, so one trie can serve many scans.
+    """
     result: list[str] = []
     index = 0
     while index < len(text):
@@ -72,6 +76,10 @@ def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> st
     return "".join(result)
 
 
+def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> str:
+    return _scan_trie(text, _build_trie(replacements))
+
+
 def _wrap_atomic_parts(parts: list[str]) -> str:
     return (
         DICTIONARY_MARKER_OPEN
PATCH
```

- [ ] **Step 2: Compare with the committed trie code.**

```bash
$PY -B $T/tools/trie_split_check.py HEAD
```

Expected:

```text
trie split: 5000 random cases identical
```

- [ ] **Step 3: Focused tests, full suite and fixture.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_translation_golden 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 58 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 800 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/conversion/text/dictionary_rules.py
git -C $REPO commit -q -F - <<'EOF'
refactor: split dictionary trie build and scan

Split _replace_with_trie into _build_trie and _scan_trie so that a trie
can be built once and scanned many times. _replace_with_trie and
mapping() keep their behavior; the two loops are moved, not edited.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: split dictionary trie build and scan
```

---

### Task 3: Add `LoadedDictionaryRules` (spec part C)

**Files:**
- Modify: `client/conversion/text/dictionary_rules.py`, `client/tests/test_conversion_text_dictionary_rules.py`

- [ ] **Step 1: Write the failing tests.** `LoadedDictionaryRulesTest`: every `DICTIONARY_CASES` entry through `from_paths(...).apply(...)`; every `_error_cases()` entry from `from_paths`; the missing dictionary gives `LoadedDictionaryRules()` without opening a file; the rule fields are tuples in file order (duplicates kept) and cannot be assigned (`FrozenInstanceError`); three `apply` calls open no file and call `_build_trie` 0 times; empty rules return the text unchanged.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_text_dictionary_rules.py b/client/tests/test_conversion_text_dictionary_rules.py
index c25966b..a6f801d 100644
--- a/client/tests/test_conversion_text_dictionary_rules.py
+++ b/client/tests/test_conversion_text_dictionary_rules.py
@@ -1,11 +1,14 @@
 import csv
 import tempfile
 import unittest
+from dataclasses import FrozenInstanceError
 from pathlib import Path
 from typing import NamedTuple
 from unittest.mock import patch
 
+from conversion.text import dictionary_rules
 from conversion.text.dictionary_rules import (
+    LoadedDictionaryRules,
     apply_dictionary,
     split_bracket_segments,
 )
@@ -479,5 +482,68 @@ class DictionaryFileSemanticsTest(DictionaryFilesTestCase):
                     self.assertEqual(str(context.exception), case.message)
 
 
+class LoadedDictionaryRulesTest(DictionaryFilesTestCase):
+    def test_from_paths_gives_the_recorded_output_for_every_case(self) -> None:
+        for case in DICTIONARY_CASES:
+            with self.subTest(case=case.name):
+                bopomofo_path = self.write_case_files(case)
+
+                rules = LoadedDictionaryRules.from_paths(
+                    self.dictionary_path,
+                    bopomofo_path,
+                    processing=PROCESSING[case.processing],
+                )
+
+                self.assertEqual(rules.apply(case.text), {"raw": case.raw, "replacement": case.replacement})
+
+    def test_from_paths_raises_the_recorded_errors(self) -> None:
+        for case in _error_cases():
+            with self.subTest(case=case.name):
+                self.write_error_files(case)
+
+                with self.assertRaises(case.error) as context:
+                    LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+                if case.message is not None:
+                    self.assertEqual(str(context.exception), case.message)
+
+    def test_missing_dictionary_gives_empty_rules_without_opening_the_bopomofo_file(self) -> None:
+        with OpenRecorder() as recorder:
+            rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        self.assertEqual(rules, LoadedDictionaryRules())
+        self.assertEqual(recorder.names, [])
+
+    def test_rules_are_immutable_tuples_in_file_order(self) -> None:
+        self.dictionary_path.write_text(DICTIONARY_HEADER + "乙,Y,\n甲,X,\n乙,Z,\n", encoding="utf-8")
+        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
+
+        rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        self.assertEqual(rules.raw_rules, (("乙", r"\[乙\]"), ("甲", r"\[甲\]"), ("乙", r"\[乙\]")))
+        self.assertEqual(rules.replacement_rules, (("乙", r"\[Y\]"), ("甲", r"\[X\]"), ("乙", r"\[Z\]")))
+        with self.assertRaises(FrozenInstanceError):
+            rules.raw_rules = ()
+        with self.assertRaises(FrozenInstanceError):
+            rules.replacement_rules = ()
+
+    def test_apply_reads_no_file_and_builds_no_trie(self) -> None:
+        self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
+        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
+        rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        with OpenRecorder() as recorder, patch.object(
+            dictionary_rules, "_build_trie", wraps=dictionary_rules._build_trie
+        ) as build_trie:
+            results = [rules.apply(text) for text in ("甲", "乙甲", "甲甲")]
+
+        self.assertEqual(recorder.names, [])
+        self.assertEqual(build_trie.call_count, 0)
+        self.assertEqual(results[2], {"raw": r"\[甲\]\[甲\]", "replacement": r"\[X\]\[X\]"})
+
+    def test_empty_rules_return_the_text_unchanged(self) -> None:
+        self.assertEqual(LoadedDictionaryRules().apply("台灣"), {"raw": "台灣", "replacement": "台灣"})
+        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//; s/ \(\/[^)]*\)$//'
```

Expected (the module cannot import the class):

```text
ERROR: test_conversion_text_dictionary_rules (unittest.loader._FailedTest.test_conversion_text_dictionary_rules)
ImportError: Failed to import test module: test_conversion_text_dictionary_rules
ImportError: cannot import name 'LoadedDictionaryRules' from 'conversion.text.dictionary_rules'
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Add the class and make `apply_dictionary` a wrapper.** `from_paths` is today's `apply_dictionary` body up to the two `mapping(...)` calls, moved into a classmethod: `Path(dictionary_path)`, missing -> `cls()` without touching the Bopomofo file, then `Path(bopomofo_path)` (accepted widening: a `str` now works), the Bopomofo trie built once, the dictionary rows parsed exactly as before, `cls(tuple(raws), tuple(replacements))`. `apply` scans the two stored tries, with a shortcut for empty rules. `apply_dictionary` keeps its signature and docstring.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/text/dictionary_rules.py b/client/conversion/text/dictionary_rules.py
index 8cc3dbe..11354f2 100644
--- a/client/conversion/text/dictionary_rules.py
+++ b/client/conversion/text/dictionary_rules.py
@@ -116,6 +116,106 @@ def mapping(
     return "".join(result)
 
 
+@dataclass(frozen=True)
+class LoadedDictionaryRules:
+    """Parsed dictionary rules with their match tries, read once and applied many times.
+
+    Immutable: the rule tuples never change and the private tries are built once,
+    in __post_init__, and only read afterwards.
+    """
+
+    raw_rules: tuple[tuple[str, str], ...] = ()
+    replacement_rules: tuple[tuple[str, str], ...] = ()
+    _raw_trie: _TrieNode = field(init=False, repr=False, compare=False)
+    _replacement_trie: _TrieNode = field(init=False, repr=False, compare=False)
+
+    def __post_init__(self) -> None:
+        object.__setattr__(self, "_raw_trie", _build_trie(self.raw_rules))
+        object.__setattr__(self, "_replacement_trie", _build_trie(self.replacement_rules))
+
+    @classmethod
+    def from_paths(
+        cls,
+        dictionary_path: Path | str,
+        bopomofo_path: Path | str,
+        *,
+        processing: Callable[[str], str],
+    ) -> "LoadedDictionaryRules":
+        """Read the dictionary and Bopomofo rule files.
+
+        A missing dictionary gives empty rules without opening the Bopomofo file.
+        """
+        dictionary_path = Path(dictionary_path)
+        if not dictionary_path.exists():
+            return cls()
+
+        with Path(bopomofo_path).open("r", newline="", encoding="utf-8") as f_b:
+            reader = csv.DictReader(f_b)
+            if reader.fieldnames is None:
+                raise ValueError("CSV must contain header row.")
+            if not {"Bopomofo", "Braille"}.issubset(reader.fieldnames):
+                raise ValueError("CSV must contain columns: Bopomofo, Braille")
+
+            replacements_bopomofo: list[tuple[str, str]] = []
+            for row in reader:
+                source = (row.get("Bopomofo") or "")
+                target = (row.get("Braille") or "")
+                if not source:
+                    continue
+                replacements_bopomofo.append((source, target))
+        bopomofo_trie = _build_trie(replacements_bopomofo)
+
+        with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
+            reader = csv.DictReader(f_d)
+            if reader.fieldnames is None:
+                raise ValueError("CSV must contain header row.")
+            if not {"text", "braille", "type"}.issubset(reader.fieldnames):
+                raise ValueError("CSV must contain columns: text, braille, type")
+
+            raws: list[tuple[str, str]] = []
+            replacements: list[tuple[str, str]] = []
+            for row in reader:
+                source = (row.get("text") or "")
+                target = (row.get("braille") or "")
+                if not source:
+                    continue
+
+                type_ = (row.get("type") or "")
+                if type_ == "Bopomofo":
+                    try:
+                        target = processing(target)
+                    except Exception:
+                        pass
+                    if isinstance(target, str):
+                        target_parts = [target]
+                    else:
+                        target_parts = list(target)
+                    replacement_parts = [_scan_trie(part, bopomofo_trie) for part in target_parts]
+                else:
+                    replacement_parts = target.split("@")
+
+                raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
+                raws.append((source, _wrap_atomic_parts(raw_parts)))
+                replacements.append((source, _wrap_atomic_parts(replacement_parts)))
+
+        return cls(tuple(raws), tuple(replacements))
+
+    def apply(self, text: str) -> dict[str, str]:
+        """Return the raw and replacement text; reads no file and builds no trie."""
+        if not self.raw_rules and not self.replacement_rules:
+            return {
+                "raw": text,
+                "replacement": text,
+            }
+        # Both outputs are derived from the same original text. The trie therefore
+        # gives them identical dictionary-match boundaries without relying on marker
+        # wrapping to prevent a second replacement pass.
+        return {
+            "raw": _scan_trie(text, self._raw_trie),
+            "replacement": _scan_trie(text, self._replacement_trie),
+        }
+
+
 def apply_dictionary(
     text: str,
     dictionary_path: Path | str,
@@ -125,71 +225,11 @@ def apply_dictionary(
     """
     支援不同類型字典的轉換。
     """
-    dictionary_path = Path(dictionary_path)
-    if not dictionary_path.exists():
-        return {
-            "raw": text,
-            "replacement": text,
-        }
-
-    with bopomofo_path.open("r", newline="", encoding="utf-8") as f_b:
-        reader = csv.DictReader(f_b)
-        if reader.fieldnames is None:
-            raise ValueError("CSV must contain header row.")
-        if not {"Bopomofo", "Braille"}.issubset(reader.fieldnames):
-            raise ValueError("CSV must contain columns: Bopomofo, Braille")
-
-        replacements_bopomofo: list[tuple[str, str]] = []
-        for row in reader:
-            source = (row.get("Bopomofo") or "")
-            target = (row.get("Braille") or "")
-            if not source:
-                continue
-            replacements_bopomofo.append((source, target))
-
-    with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
-        reader = csv.DictReader(f_d)
-        if reader.fieldnames is None:
-            raise ValueError("CSV must contain header row.")
-        if not {"text", "braille", "type"}.issubset(reader.fieldnames):
-            raise ValueError("CSV must contain columns: text, braille, type")
-
-        raws: list[tuple[str, str]] = []
-        replacements: list[tuple[str, str]] = []
-        for row in reader:
-            source = (row.get("text") or "")
-            target = (row.get("braille") or "")
-            if not source:
-                continue
-
-            type_ = (row.get("type") or "")
-            if type_ == "Bopomofo":
-                try:
-                    target = processing(target)
-                except Exception:
-                    pass
-                if isinstance(target, str):
-                    target_parts = [target]
-                else:
-                    target_parts = list(target)
-                replacement_parts = [mapping(part, replacements_bopomofo) for part in target_parts]
-            else:
-                replacement_parts = target.split("@")
-
-            raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
-            raws.append((source, _wrap_atomic_parts(raw_parts)))
-            replacements.append((source, _wrap_atomic_parts(replacement_parts)))
-
-    # Both outputs are derived from the same original text. The trie therefore
-    # gives them identical dictionary-match boundaries without relying on marker
-    # wrapping to prevent a second replacement pass.
-    raw = mapping(text, raws)
-    replacement = mapping(text, replacements)
-
-    return {
-        "raw": raw,
-        "replacement": replacement,
-    }
+    return LoadedDictionaryRules.from_paths(
+        dictionary_path,
+        bopomofo_path,
+        processing=processing,
+    ).apply(text)
 
 
 def split_bracket_segments(text: str) -> list[BracketSegment]:
PATCH
```

- [ ] **Step 4: Focused tests, full suite and fixture.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_translation_golden tests.test_removed_dead_code 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
git -C $REPO diff -w --stat -- client/conversion
```

Expected (783 + 23; ignoring whitespace, the moved parse shows as a small change):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 69 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 806 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
 client/conversion/text/dictionary_rules.py | 72 +++++++++++++++++++++++-------
 1 file changed, 56 insertions(+), 16 deletions(-)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/text/dictionary_rules.py client/tests/test_conversion_text_dictionary_rules.py
git -C $REPO commit -q -F - <<'EOF'
refactor: add LoadedDictionaryRules

Parse the dictionary and Bopomofo rule files into an immutable value
object that holds the rules and their compiled tries, so the rules can
be read once and applied to many items. apply_dictionary keeps its
signature, output, errors and reads, and becomes a wrapper over
LoadedDictionaryRules.from_paths(...).apply(...).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: add LoadedDictionaryRules
```

---

### Task 4: Load the dictionary rules once per conversion (spec part D)

**Files:**
- Modify: `client/conversion/text/dictionary_rules.py`, `client/conversion/text/pipeline.py`, `client/conversion/service.py`, `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_conversion_service.py`

- [ ] **Step 1: Write the failing tests.** `DictionaryRulesLoaderTest` (constructing reads nothing; three `load()` calls read once and return the same object; a failed load is retried). `DictionaryReadCountTest` in the pipeline module counts `Path.open` by file name for a 12-item mixed zh/en text with inline math (precondition: at least 8 `LoadedDictionaryRules.apply` calls), in Unicode and ASCII mode, plus `from_paths`/`_build_trie` counts, math-only input, `translate_with_language` called directly, two conversions, a standalone `translate_plain_text_segment` call and a passed loader. `DictionarySnapshotTest`: a translator that rewrites the dictionary after its first call; the conversion keeps the first version, the next conversion sees the new one.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index 1de6e85..5bd1fac 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -521,5 +521,28 @@ class DictionaryErrorTimingTest(DictionaryConversionTestCase):
         self.assertEqual(runtime.text_translator.calls, [("甲", "zh-tw.ctb", "甲", False)])
 
 
+class DictionarySnapshotTest(DictionaryConversionTestCase):
+    def test_one_conversion_uses_one_dictionary_snapshot(self) -> None:
+        dictionary_path = self.dictionary_path
+        dictionary_path.write_text("text,braille,type\n甲,X,Braille\n", encoding="utf-8")
+
+        class RewritingTextTranslator(FakeTextTranslator):
+            """Rewrites the dictionary (as an external editor would) after the first item."""
+
+            def translate(self, text, **kwargs):
+                result = super().translate(text, **kwargs)
+                if len(self.calls) == 1:
+                    dictionary_path.write_text("text,braille,type\n甲,Y,Braille\n", encoding="utf-8")
+                return result
+
+        runtime = TranslationRuntime(text_translator=RewritingTextTranslator(), math_translator=FakeMathTranslator())
+        self._convert("甲$x$甲$y$甲", runtime)
+        next_runtime = self._runtime()
+        self._convert("甲$x$甲$y$甲", next_runtime)
+
+        self.assertEqual([call[0] for call in runtime.text_translator.calls if call[2] == "甲"], ["X", "X", "X"])
+        self.assertEqual([call[0] for call in next_runtime.text_translator.calls if call[2] == "甲"], ["Y", "Y", "Y"])
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_conversion_text_dictionary_rules.py b/client/tests/test_conversion_text_dictionary_rules.py
index a6f801d..fda15ba 100644
--- a/client/tests/test_conversion_text_dictionary_rules.py
+++ b/client/tests/test_conversion_text_dictionary_rules.py
@@ -8,6 +8,7 @@ from unittest.mock import patch
 
 from conversion.text import dictionary_rules
 from conversion.text.dictionary_rules import (
+    DictionaryRulesLoader,
     LoadedDictionaryRules,
     apply_dictionary,
     split_bracket_segments,
@@ -545,5 +546,48 @@ class LoadedDictionaryRulesTest(DictionaryFilesTestCase):
         self.assertEqual(LoadedDictionaryRules().apply("台灣"), {"raw": "台灣", "replacement": "台灣"})
         self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})
 
+
+class DictionaryRulesLoaderTest(DictionaryFilesTestCase):
+    def test_constructing_a_loader_reads_nothing(self) -> None:
+        with OpenRecorder() as recorder, patch.object(
+            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
+        ) as from_paths:
+            DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_raise_value_error)
+
+        self.assertEqual(recorder.names, [])
+        self.assertEqual(from_paths.call_count, 0)
+
+    def test_load_reads_the_rules_once_and_returns_the_same_object(self) -> None:
+        self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
+        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
+        loader = DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        with OpenRecorder() as recorder, patch.object(
+            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
+        ) as from_paths:
+            loaded = [loader.load() for _ in range(3)]
+
+        self.assertEqual(from_paths.call_count, 1)
+        self.assertIs(loaded[1], loaded[0])
+        self.assertIs(loaded[2], loaded[0])
+        self.assertEqual(recorder.names, ["bopomofo.csv", "dictionary.csv"])
+        self.assertEqual(loaded[0].apply("甲"), {"raw": r"\[甲\]", "replacement": r"\[X\]"})
+
+    def test_a_failed_load_is_retried_by_the_next_load(self) -> None:
+        self.dictionary_path.write_bytes(b"")
+        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
+        loader = DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        with patch.object(
+            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
+        ) as from_paths:
+            with self.assertRaisesRegex(ValueError, "^CSV must contain header row\\.$"):
+                loader.load()
+            self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
+            rules = loader.load()
+
+        self.assertEqual(from_paths.call_count, 2)
+        self.assertEqual(rules.replacement_rules, (("甲", r"\[X\]"),))
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_conversion_text_pipeline.py b/client/tests/test_conversion_text_pipeline.py
index 18e4e04..7ba0009 100644
--- a/client/tests/test_conversion_text_pipeline.py
+++ b/client/tests/test_conversion_text_pipeline.py
@@ -1,11 +1,16 @@
 import csv
 import tempfile
 import unittest
+from collections import Counter
 from pathlib import Path
+from unittest.mock import patch
 
 from adapters.translation.contracts import TranslationRuntime
+from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
 from config import DEFAULT_CHARSET_MAPS
+from conversion import service
 from conversion.output import ConversionRequest, convert_text_with_alignment
+from conversion.text import dictionary_rules
 from conversion.text.dictionary_rules import apply_dictionary, split_bracket_segments
 from conversion.text.pipeline import (
     TextProcessingError,
@@ -16,6 +21,11 @@ from translate import TranslationResult
 
 
 LANGUAGE_TABLES = {"default": "default.ctb", "en": "en.ctb", "zh": "zh.ctb", "ja": "ja.ctb"}
+DATA_DIR = Path(__file__).resolve().parents[1] / "data"
+READ_COUNT_TABLES = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb", "zh": "zh-tw.ctb", "math": "Nemeth"}
+# Twelve plain-text items for the language detector, around one inline math segment.
+MIXED_TEXT = "台灣 is 美麗 island, 中文 and English 混合 $x+1$ 測試 test 完成 done"
+COUNTED_FILES = ("dictionary.csv", "Bopomofo2Braille.csv", "BopomofoChar2Braille.csv", "Braille2Ascii.csv")
 
 
 class ConversionTextPipelineTest(unittest.TestCase):
@@ -269,3 +279,153 @@ class ConversionTextPipelineTest(unittest.TestCase):
                 )
 
                 self.assertEqual(calls, [("A", "en.ctb"), (" ", "en.ctb"), ("中", table)])
+
+
+class DictionaryReadCountTest(unittest.TestCase):
+    """Each rule file is opened at most once per conversion, however many items the text has."""
+
+    def setUp(self) -> None:
+        self._tmpdir = tempfile.TemporaryDirectory()
+        self.addCleanup(self._tmpdir.cleanup)
+        self.test_dir = Path(self._tmpdir.name)
+        self.dictionary_path = self.test_dir / "dictionary.csv"
+        self.dictionary_path.write_text("text,braille,type\n台灣,⠞⠺,Braille/Unicode\n", encoding="utf-8")
+
+    def _runtime(self) -> TranslationRuntime:
+        return TranslationRuntime(text_translator=FallbackTextTranslator(), math_translator=FallbackMathTranslator())
+
+    def _convert(self, raw_text: str, output_mode: str = "unicode"):
+        request = ConversionRequest(
+            raw_text=raw_text,
+            output_mode=output_mode,
+            width=40,
+            dictionary_path=self.dictionary_path,
+            data_dir=DATA_DIR,
+            translation_tables=dict(READ_COUNT_TABLES),
+            lang="zh_TW",
+            charset_maps=dict(DEFAULT_CHARSET_MAPS),
+        )
+        return service.convert_text_with_alignment(request, runtime=self._runtime())
+
+    def _opened(self, call) -> dict[str, int]:
+        """Run call() and return how often each counted file was opened through Path.open."""
+        counts: Counter[str] = Counter()
+        original_open = Path.open
+
+        def counting_open(path, *args, **kwargs):
+            counts[path.name] += 1
+            return original_open(path, *args, **kwargs)
+
+        with patch.object(Path, "open", counting_open):
+            call()
+        return {name: counts[name] for name in COUNTED_FILES}
+
+    def _count_apply(self):
+        rules_class = dictionary_rules.LoadedDictionaryRules
+        return patch.object(rules_class, "apply", autospec=True, side_effect=rules_class.apply)
+
+    def test_unicode_conversion_opens_each_rule_file_once(self) -> None:
+        with self._count_apply() as apply:
+            opened = self._opened(lambda: self._convert(MIXED_TEXT))
+
+        self.assertGreaterEqual(apply.call_count, 8)
+        self.assertEqual(
+            opened,
+            {"dictionary.csv": 1, "Bopomofo2Braille.csv": 1, "BopomofoChar2Braille.csv": 1, "Braille2Ascii.csv": 0},
+        )
+
+    def test_ascii_conversion_also_opens_the_ascii_map_once(self) -> None:
+        with self._count_apply() as apply:
+            opened = self._opened(lambda: self._convert(MIXED_TEXT, output_mode="ascii"))
+
+        self.assertGreaterEqual(apply.call_count, 8)
+        self.assertEqual(
+            opened,
+            {"dictionary.csv": 1, "Bopomofo2Braille.csv": 1, "BopomofoChar2Braille.csv": 1, "Braille2Ascii.csv": 1},
+        )
+
+    def test_conversion_parses_the_rules_once_and_builds_three_tries(self) -> None:
+        rules_class = dictionary_rules.LoadedDictionaryRules
+        with patch.object(rules_class, "from_paths", wraps=rules_class.from_paths) as from_paths, patch.object(
+            dictionary_rules, "_build_trie", wraps=dictionary_rules._build_trie
+        ) as build_trie:
+            self._convert(MIXED_TEXT)
+
+        self.assertEqual(from_paths.call_count, 1)
+        self.assertEqual(build_trie.call_count, 3)
+
+    def test_math_only_conversion_opens_no_dictionary_file(self) -> None:
+        opened = self._opened(lambda: self._convert("$x+1$"))
+
+        self.assertEqual(opened["dictionary.csv"], 0)
+        self.assertEqual(opened["Bopomofo2Braille.csv"], 0)
+
+    def test_translate_with_language_opens_each_dictionary_file_once(self) -> None:
+        opened = self._opened(
+            lambda: service.translate_with_language(
+                MIXED_TEXT,
+                self.dictionary_path,
+                dict(READ_COUNT_TABLES),
+                DATA_DIR / "Bopomofo2Braille.csv",
+                runtime=self._runtime(),
+                lang="zh_TW",
+                charset_maps=dict(DEFAULT_CHARSET_MAPS),
+            )
+        )
+
+        self.assertEqual(opened["dictionary.csv"], 1)
+        self.assertEqual(opened["Bopomofo2Braille.csv"], 1)
+
+    def test_every_conversion_reads_the_rules_again(self) -> None:
+        rules_class = dictionary_rules.LoadedDictionaryRules
+        with patch.object(rules_class, "from_paths", wraps=rules_class.from_paths) as from_paths:
+            self._convert(MIXED_TEXT)
+            self._convert(MIXED_TEXT)
+
+        self.assertEqual(from_paths.call_count, 2)
+
+    def test_standalone_plain_text_segment_opens_each_dictionary_file_once(self) -> None:
+        with self._count_apply() as apply:
+            opened = self._opened(
+                lambda: translate_plain_text_segment(
+                    "台灣 is 美麗 island, 中文 and English",
+                    self.dictionary_path,
+                    dict(READ_COUNT_TABLES),
+                    DATA_DIR / "Bopomofo2Braille.csv",
+                    runtime=self._runtime(),
+                    lang="zh_TW",
+                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
+                )
+            )
+
+        self.assertGreater(apply.call_count, 1)
+        self.assertEqual(opened["dictionary.csv"], 1)
+        self.assertEqual(opened["Bopomofo2Braille.csv"], 1)
+
+    def test_plain_text_segment_uses_the_given_loader_instead_of_the_paths(self) -> None:
+        loader = dictionary_rules.DictionaryRulesLoader(
+            self.dictionary_path,
+            DATA_DIR / "Bopomofo2Braille.csv",
+            processing=lambda text: text,
+        )
+        results = []
+
+        def translate():
+            results.append(
+                translate_plain_text_segment(
+                    "台灣",
+                    self.test_dir / "missing.csv",
+                    dict(READ_COUNT_TABLES),
+                    self.test_dir / "missing-bopomofo.csv",
+                    runtime=self._runtime(),
+                    lang="zh_TW",
+                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
+                    dictionary_rules=loader,
+                )
+            )
+
+        first = self._opened(translate)
+        second = self._opened(translate)
+
+        self.assertEqual([first["dictionary.csv"], second["dictionary.csv"]], [1, 0])
+        self.assertEqual(["".join(result[0].braille) for result in results], ["⠞⠺", "⠞⠺"])
PATCH
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_pipeline.DictionaryReadCountTest tests.test_conversion_service.DictionarySnapshotTest 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//; s/ \(\/[^)]*\)$//'
```

Expected (the loader does not exist; every read count shows one read per item; the snapshot mixes versions; the math-only test is already green):

```text
ERROR: test_conversion_text_dictionary_rules (unittest.loader._FailedTest.test_conversion_text_dictionary_rules)
ImportError: Failed to import test module: test_conversion_text_dictionary_rules
ImportError: cannot import name 'DictionaryRulesLoader' from 'conversion.text.dictionary_rules'
ERROR: test_plain_text_segment_uses_the_given_loader_instead_of_the_paths (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_plain_text_segment_uses_the_given_loader_instead_of_the_paths)
AttributeError: module 'conversion.text.dictionary_rules' has no attribute 'DictionaryRulesLoader'
FAIL: test_ascii_conversion_also_opens_the_ascii_map_once (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_ascii_conversion_also_opens_the_ascii_map_once)
AssertionError: {'dictionary.csv': 12, 'Bopomofo2Braille.csv': 12, 'BopomofoC[39 chars]': 1} != {'dictionary.csv': 1, 'Bopomofo2Braille.csv': 1, 'BopomofoCha[37 chars]': 1}
FAIL: test_conversion_parses_the_rules_once_and_builds_three_tries (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_conversion_parses_the_rules_once_and_builds_three_tries)
AssertionError: 12 != 1
FAIL: test_every_conversion_reads_the_rules_again (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_every_conversion_reads_the_rules_again)
AssertionError: 24 != 2
FAIL: test_standalone_plain_text_segment_opens_each_dictionary_file_once (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_standalone_plain_text_segment_opens_each_dictionary_file_once)
AssertionError: 6 != 1
FAIL: test_translate_with_language_opens_each_dictionary_file_once (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_translate_with_language_opens_each_dictionary_file_once)
AssertionError: 12 != 1
FAIL: test_unicode_conversion_opens_each_rule_file_once (tests.test_conversion_text_pipeline.DictionaryReadCountTest.test_unicode_conversion_opens_each_rule_file_once)
AssertionError: {'dictionary.csv': 12, 'Bopomofo2Braille.csv': 12, 'BopomofoC[39 chars]': 0} != {'dictionary.csv': 1, 'Bopomofo2Braille.csv': 1, 'BopomofoCha[37 chars]': 0}
FAIL: test_one_conversion_uses_one_dictionary_snapshot (tests.test_conversion_service.DictionarySnapshotTest.test_one_conversion_uses_one_dictionary_snapshot)
AssertionError: Lists differ: ['X', 'Y', 'Y'] != ['X', 'X', 'X']
Ran 10 tests
FAILED (failures=7, errors=2)
```

- [ ] **Step 3: Add the loader and wire it.** `DictionaryRulesLoader` (in `dictionary_rules.py`) stores its arguments and reads on the first `load()`; a failed load is not kept. `pipeline.dictionary_rules_loader(dictionary_path, bopomofo_path)` builds one with `normalize_zhuyin_sequence` (the function-local `text.zhuyin` import moves there). `translate_plain_text_segment` takes `dictionary_rules: DictionaryRulesLoader | None = None` and builds its own when none is passed. `translate_with_language_dual_view_segments` creates one loader after the empty-text return and passes it to every text segment.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/service.py b/client/conversion/service.py
index 3736a53..597c541 100644
--- a/client/conversion/service.py
+++ b/client/conversion/service.py
@@ -11,7 +11,7 @@ from conversion.output import (
 )
 from conversion.plain_text import get_public_error_message
 from conversion.text.math_segments import parse_inline_math_segments, segment_needs_boundary_space
-from conversion.text.pipeline import translate_plain_text_segment
+from conversion.text.pipeline import dictionary_rules_loader, translate_plain_text_segment
 from conversion.wrapping import (
     merge_translation_results,
     wrap_translation_results,
@@ -36,6 +36,9 @@ def translate_with_language_dual_view_segments(
     if text == "":
         return []
 
+    # One loader per call: the rule files are read at the first plain-text item
+    # (never for math-only text) and at most once for the whole conversion.
+    dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)
     segments_records = []
     segments = parse_inline_math_segments(text)
     default_table = translation_tables["default"]
@@ -57,6 +60,7 @@ def translate_with_language_dual_view_segments(
                 runtime=runtime,
                 lang=lang,
                 charset_maps=charset_maps,
+                dictionary_rules=dictionary_rules,
             )
             if isinstance(plain_results, (list, tuple)):
                 for result in plain_results:
diff --git a/client/conversion/text/dictionary_rules.py b/client/conversion/text/dictionary_rules.py
index 11354f2..3659af1 100644
--- a/client/conversion/text/dictionary_rules.py
+++ b/client/conversion/text/dictionary_rules.py
@@ -216,6 +216,36 @@ class LoadedDictionaryRules:
         }
 
 
+class DictionaryRulesLoader:
+    """Loads one conversion's dictionary rules on first use and keeps them for that conversion.
+
+    Creating a loader reads nothing. A failed load is not kept, so the next
+    load() reads the files again. Not thread-safe: one loader serves one
+    conversion on one worker thread, and nothing is cached across conversions.
+    """
+
+    def __init__(
+        self,
+        dictionary_path: Path | str,
+        bopomofo_path: Path | str,
+        *,
+        processing: Callable[[str], str],
+    ) -> None:
+        self._dictionary_path = dictionary_path
+        self._bopomofo_path = bopomofo_path
+        self._processing = processing
+        self._rules: LoadedDictionaryRules | None = None
+
+    def load(self) -> LoadedDictionaryRules:
+        if self._rules is None:
+            self._rules = LoadedDictionaryRules.from_paths(
+                self._dictionary_path,
+                self._bopomofo_path,
+                processing=self._processing,
+            )
+        return self._rules
+
+
 def apply_dictionary(
     text: str,
     dictionary_path: Path | str,
diff --git a/client/conversion/text/pipeline.py b/client/conversion/text/pipeline.py
index 7d125c2..f17c571 100644
--- a/client/conversion/text/pipeline.py
+++ b/client/conversion/text/pipeline.py
@@ -8,7 +8,7 @@ from conversion.preprocessing.literal_braille import (
     is_unicode_braille,
 )
 from .char_maps import map_characters
-from .dictionary_rules import apply_dictionary, split_bracket_segments
+from .dictionary_rules import DictionaryRulesLoader, split_bracket_segments
 
 
 ExecuteScript = Callable[[Path, str], str]
@@ -45,6 +45,13 @@ def preprocess_source_text(
     )
 
 
+def dictionary_rules_loader(dictionary_path: Path, bopomofo_path: Path) -> DictionaryRulesLoader:
+    """Return a loader that reads the two rule files on first use, with the zhuyin parser."""
+    from text.zhuyin import normalize_zhuyin_sequence
+
+    return DictionaryRulesLoader(dictionary_path, bopomofo_path, processing=normalize_zhuyin_sequence)
+
+
 def translate_plain_text_segment(
     text: str,
     dictionary_path: Path,
@@ -54,10 +61,13 @@ def translate_plain_text_segment(
     runtime: TranslationRuntime,
     lang: str,
     charset_maps: dict[str, str],
+    dictionary_rules: DictionaryRulesLoader | None = None,
 ):
-    from text.zhuyin import normalize_zhuyin_sequence
     from languageDetection import LangChangeCommand, LanguageDetector
 
+    if dictionary_rules is None:
+        dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)
+
     language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
     language_detector = LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)
     sequence = list(language_detector.add_detected_language_commands([text]))
@@ -67,12 +77,7 @@ def translate_plain_text_segment(
     translations = []
     for item in sequence:
         if isinstance(item, str):
-            result = apply_dictionary(
-                item,
-                dictionary_path=dictionary_path,
-                bopomofo_path=bopomofo_path,
-                processing=normalize_zhuyin_sequence,
-            )
+            result = dictionary_rules.load().apply(item)
             raw_segments = split_bracket_segments(result["raw"])
             replacement_segments = split_bracket_segments(result["replacement"])
 
PATCH
```

- [ ] **Step 4: Roadmap verification, full suite and fixture.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
```

Expected (783 + 35):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 69 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 818 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/text/dictionary_rules.py client/conversion/text/pipeline.py client/conversion/service.py client/tests/test_conversion_text_dictionary_rules.py client/tests/test_conversion_text_pipeline.py client/tests/test_conversion_service.py
git -C $REPO commit -q -F - <<'EOF'
refactor: load dictionary rules once per conversion

Create one lazy DictionaryRulesLoader per translate_with_language call
and pass it to every plain-text segment, so a conversion opens the
dictionary and Bopomofo2Braille.csv at most once instead of once per
language item. The loader reads at the first plain-text item, as the
old per-item call did, so errors keep their type, stage and timing and
math-only input still reads nothing. Every conversion reads the files
again; an external edit during a conversion now takes effect at the
next conversion instead of mid-document.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: load dictionary rules once per conversion
```

---

### Task 5: Final verification (spec acceptance criteria; no commit)

- [ ] **Step 1: AC1 (verbose module list) and AC2.**

```bash
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service -v 2>&1 | grep -cE ' \.\.\. ok$'
$PY -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service -v 2>&1 | grep -E ' \.\.\. FAIL$|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_translation_golden tests.test_conversion_language_explicit tests.test_removed_dead_code tests.test_conversion_jobs tests.test_conversion_presenter tests.test_main_demo 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (68 passing, the P2-5 failure; AC2 all green):

```text
68
test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math) ... FAIL
Ran 69 tests
FAILED (failures=1)
Ran 44 tests
OK
```

- [ ] **Step 2: AC3 and AC4, fixture and full suite.**

```bash
git -C $REPO diff main -- client/tests/fixtures/translation_golden.json
sha256sum tests/fixtures/translation_golden.json
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (no diff):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 818 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 3: AC4, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 818 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=818 failures=1 errors=0 skipped=9
```

- [ ] **Step 4: AC5-AC8 and the msgid scan.** AC5 is the `DictionaryReadCountTest` run above; this step re-runs it alone.

```bash
echo AC5; $PY -m unittest tests.test_conversion_text_pipeline.DictionaryReadCountTest 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
echo AC6; grep -rn "apply_dictionary(" $REPO/client/conversion | sed "s#$REPO/##"; grep -n "\.open(" $REPO/client/conversion/text/dictionary_rules.py
echo AC7; $PY -B $T/tools/dictionary_perf.py . > $T/perf_after.txt
$PY -c "import sys; b, bl = open(sys.argv[1]).read().split(); a, al = open(sys.argv[2]).read().split(); print('same display length:', bl == al); print('at least 10x faster:', float(b) >= 10 * float(a))" $T/perf_before.txt $T/perf_after.txt
echo AC8; git -C $REPO diff main --stat -- client/locales scripts client/braille client/gui.py client/dictionaries client/conversion/output.py client/conversion/text/char_maps.py
echo msgids; $PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo end
```

Expected (AC6: only the definition, and the two reads inside `from_paths`; nothing after AC8; the msgid set unchanged at 353):

```text
AC5
Ran 8 tests
OK
AC6
client/conversion/text/dictionary_rules.py:249:def apply_dictionary(
152:        with Path(bopomofo_path).open("r", newline="", encoding="utf-8") as f_b:
168:        with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
AC7
same display length: True
at least 10x faster: True
AC8
msgids
source msgids: 353
SOURCE == SAVED
end
```

Report the two timings (`cat $T/perf_before.txt $T/perf_after.txt`: seconds, then display length) in the handoff note; the dry run measured 2.25 s and 0.066 s.

- [ ] **Step 5: The branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -5
git -C $REPO diff --stat HEAD~4 HEAD
```

Expected:

```text
refactor: load dictionary rules once per conversion
refactor: add LoadedDictionaryRules
refactor: split dictionary trie build and scan
test: characterize dictionary rule loading
docs: plan dictionary rules loader
 client/conversion/service.py                       |   6 +-
 client/conversion/text/dictionary_rules.py         | 222 +++++--
 client/conversion/text/pipeline.py                 |  21 +-
 client/tests/test_conversion_service.py            | 121 ++++
 .../tests/test_conversion_text_dictionary_rules.py | 727 ++++++++++++++++-----
 client/tests/test_conversion_text_pipeline.py      | 160 +++++
 6 files changed, 1018 insertions(+), 239 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): on a packaged build, before and after, convert a long mixed zh/en document with inline math using a large user dictionary that has `Braille`, `Braille/Unicode` (`@` split) and `Bopomofo` rows, in Unicode and ASCII output modes; the Braille Result text and the exported BRL must be byte-identical, and the conversion should be visibly faster. Edit the dictionary in Dictionary Management between two conversions and confirm the second conversion uses the edit. Run `tests.test_liblouis_runtime`, `tests.test_translation_language_result` and `tests.test_language_detection_translation` and compare with the baseline (the last two already fail for the reasons recorded in P1-1 and P1-5). No menu, dialog or string changes, so no screenshots and no `generate_pot.bat` run are needed.
