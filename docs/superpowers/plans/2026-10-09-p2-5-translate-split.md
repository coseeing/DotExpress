# translate.py Split (P2-5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `client/translate.py` into `conversion/tokenizer.py` (how source characters become tokens), `conversion/line_wrap.py` (how tokens are laid out on lines) and `conversion/alignment.py` (the `TranslationResult` value object and the operations that keep its maps consistent); `translate.py` becomes a one-line re-export. In the same branch: resolve the one failing test as the user decided, make `reclean_braille_endspace` and `reclean_token` linear with byte-identical output, convert `tests/test_translation_result.py` to `unittest` with its five fixture defects fixed, move the translation ports into `conversion/contracts.py` so that `conversion` no longer imports `adapters`, and build three independent safety nets first (the unchanged fake golden, a frozen pre-split oracle with randomized equivalence tests, and a Windows real-liblouis golden with the recorded BRL hashes). No output, string, msgid (353), `.po`/`.mo`, `client/braille/`, `client/locales/`, `scripts/` or `client/dictionary/` change.

**Architecture:** Ten green commits in the spec's migration order (Tasks 1-10), then verification (Tasks 11-12). Tasks 1-4 change tests only, on unchanged production code. Task 5 moves the ports. Tasks 6-7 make the two quadratic passes linear inside `translate.py`, each with a fast path for a well-formed alignment and the original code for anything else. Tasks 8-9 extract the tokenizer and the line wrapper as pure functions that `TranslationResult` delegates to. Task 10 moves the class to `conversion/alignment.py` mechanically (tabs to 4 spaces) and points every production import at it. Every production task is red first.

**Tech Stack:** Python 3.13 standard library (`unittest`, `unittest.mock`, `bisect`, `random`, `hashlib`, `json`, `ast`, `subprocess`). Windows 11, `client\.venv` with wxPython and PyInstaller, the bundled liblouis 3.37.0 DLL and tables, MathCAT under `client\mathcat\`.

**Spec:** `docs/superpowers/specs/2026-10-09-p2-5-translate-split-design.md` (+ `_zh-TW.md`), commit `079d58b`, with the section "Corrected after planning" added in the plan commit. The orchestrator decided the spec's open questions: Q1 yes (linear `reclean_token`, Task 7, included), Q2 out of scope (recorded in the spec as a known pre-existing defect for a later user decision; the real golden pins today's behavior).

## Global Constraints

- Branch: `refactor/p2-5-translate-split` (HEAD is the plan commit on top of `079d58b`). Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (28, nothing else): production `client/translate.py` (tabs until Task 10), `client/conversion/{tokenizer,line_wrap,alignment,contracts}.py` (new, 4 spaces), `client/adapters/translation/contracts.py` (rewritten), and one import line each in `client/adapters/translation/{fallback,liblouis,mathcat}.py`, `client/conversion/{jobs,output,service,wrapping}.py`, `client/conversion/text/pipeline.py`, `client/conversion/preprocessing/literal_braille.py`, `client/gui.py` and `client/ui/conversion_presenter.py`; tests `client/tests/test_translation_result.py` (tabs), `test_conversion_service.py`, `test_translation_result_core.py`, `test_translation_import_isolation.py` (4 spaces), new `test_translation_liblouis_golden.py`, `test_translation_split_equivalence.py`, `test_conversion_tokenizer.py`, `test_conversion_line_wrap.py`, `legacy_translation_result.py` (the oracle, tabs as copied), new fixtures `client/tests/fixtures/translation_liblouis_golden.json` and `client/tests/fixtures/p25_doc.txt`.
- Never touch `client/tests/fixtures/translation_golden.json`, `client/tests/fixtures/dictionary_entries_trace.json`, `client/tests/test_translation_golden.py`, `client/dictionary/` (user data; no test reads it), `client/braille/` (including the generated, git-ignored `liblouis/`, `liblouis.dll`, `louis_helper.py`, and `tables/__init__.py`, CRLF byte for byte), `client/locales/`, `scripts/`, `vendor/`, `include/liblouis`, the untracked `client2/`, `preprocessing/`, `testdata/`. Never run `scripts\sync-nvda.py`.
- The checkout uses `core.autocrlf=true`: the index has LF, the working tree CRLF. **Create files with the Write tool and run the Python edit scripts below; never edit with MSYS `sed -i` (it rewrites CRLF) and never paste Python through a shell heredoc (the agent shell can alter backslash escapes).** The edit scripts read CRLF, assert that each replacement matches exactly once and write CRLF back. New files may be written with LF; git normalizes them (the "LF will be replaced by CRLF" warning is expected).
- Fixtures: `git show HEAD:client/tests/fixtures/translation_golden.json | sha256sum` must print `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd` and the same for `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` after every task. `client/tests/fixtures/translation_liblouis_golden.json` is written once in Task 3 and never regenerated.
- Real liblouis is reached only through `braille.louis_helper` (W-1 guard); the new real-golden module follows the existing pattern.
- No user-visible string changes: the msgid scan prints `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c` before and after.
- After each task, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). Each task also lists the sha256 of the files it changed (`git show HEAD:<path> | sha256sum`). If a value differs, stop and diff the file against the block in this plan.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; use `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. Stage only the files named in the task, explicitly.
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers, exception lines cut to 160 characters and de-duplicated, `Ran` without timing, final status; the client directory is shown as `<client>`, measured seconds in a timing assertion as `<seconds>`).
- Shell (Git Bash). `SP` is your session scratchpad in Git Bash form:
  ```bash
  REPO=/d/workspace/DotExpress
  PY=$REPO/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/D--workspace-DotExpress/<session>/scratchpad
  T=$SP/p25impl
  H=$REPO/docs/superpowers/history/2026-10-09-03-windows-verification
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit.

1. **The oracle is header + marker + verbatim copy.** D11.2 calls `tests/legacy_translation_result.py` a byte copy with a header comment and checks its git blob id; both cannot hold. The file is a five-line comment header ending with the marker line `# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----`, followed by the exact bytes of `git show d4a7aa1:client/translate.py`. `test_oracle_is_the_pre_split_translate_py` LF-normalizes the file, takes the part after the marker and checks that its blob id is `10bd641485327b00cb71a14d4946f01a1788f794`.
2. **The language-blocks patch target moves in Task 8, not Task 10.** Once the tokenizer owns the constants (Task 8), `translate.py` no longer imports `build_language_blocks`, so `patch("translate.build_language_blocks")` raises `AttributeError`. Task 8 changes it to `conversion.tokenizer.build_language_blocks`.
3. **The separator timing test uses 10,000 separators.** The old `reclean_token` is quadratic: 10,000 `」「` pairs take 19 s here, 20,000 would take more than a minute for one red run. The test is `test_inserting_ten_thousand_separators_takes_linear_time` (bound 2 s; linear code 0.01 s). The trim test keeps 40,000 tokens (old code 42 s here, linear 0.02 s).
4. **Real golden shape.** 17 cases: the 8 inputs for each of the two table sets, plus one long document (the `p25_perf.py` paragraph x 400, width 40) with the default tables only (it is Chinese only, so the English table cannot matter). Per case: `text_sha256`, the display text of each run (digest only for the long document), the post-processed tokens in full (digest for the long document), and digests of the merged lists, the post-processed lists and the dual-view segments, plus the segment count. The fixture is about 34 KB; the module runs in 1.7 s after Task 6 (4.9 s before, because of the quadratic trim). A liblouis version other than the recorded `3.37.0` makes `setUpClass` raise an `AssertionError` that says to regenerate only for an intended upgrade (so all 13 tests error with that message). The runtime is built from `create_default_text_translator()` and `create_default_math_translator()` directly (no silent fallback), and both are closed by a class cleanup.
5. **Equivalence tests also compare list identity.** Besides the four lists, the return value and the exception type and message, `outcome()` records which of the four attributes still hold the original list objects, which pins "mutates in place or replaces". A separator-dense unit alphabet is used for half of the `reclean_token` cases and half of the whole-chain cases; with the general alphabet alone fewer than 100 of 4,000 well-formed cases had a separator and none had two. Counts: 4,000 cases per operation (2,000 + 2,000 for `reclean_token`), 2,000 chains; the module runs in 1.3 s.
6. **The fast trim skips the final clamp.** D5 says the clamp loop "runs anyway". On the fast path no start can exceed the new length, so the code does not run it (a comment says why); the stepwise fallback keeps it.
7. **Separator positions are computed eagerly.** D6 describes a lazy generator so that an exception happens at the same pair. `iter_separator_positions` is a generator, but `reclean_token` takes `list(...)` of it first in both paths: the positions depend only on the original tokens and computing them cannot raise for string tokens, so the one-by-one fallback still raises at the same insertion.
8. **Comments in moved code.** The moved bodies keep their Chinese comments verbatim (the files already contain CJK punctuation constants). The `bind_word_tokens` docstring stays on the method. `line_wrap.py` drops the two commented-out lines `# raw_lines = [i for i in raw_lines if i != []]` / `# braille_lines = ...` and adds the English branch comments D4 allows. Task 11 lists every line of the three new modules that is not in `translate.py` at `d4a7aa1` (indentation ignored) for review.
9. **`test_bind_word_tokens_complex` also has a short map** (96 characters, 94 cells and positions). It passes because the regroup never reads past position 82, so it stays as written; the equivalence tests cover too-short maps.
10. **Guards that hold before Task 10.** `test_tokenizer_and_line_wrap_do_not_import_alignment` already passes when added (it is a guard, not the red test). Task 10's red tests are `test_production_modules_do_not_import_translate` (lists six imports), `test_alignment_modules_load_no_config_adapters_or_native_code` and `test_translate_reexports_the_alignment_class`. Until Task 10, `conversion/contracts.py` imports `TranslationResult` from `translate`.
11. **Windows verification step 4.** `D:\dxtest\N` holds only `DotExpress.exe`; the packaged outputs are compared with `$H\baseline\p25_*.brl` (which N and B matched byte for byte).
12. **Counts.** After Task 10: `Ran 1208`, `FAILED (errors=1, skipped=5)` (the F-W6 error only); the spec estimated "about 1200". Per-task counts are in Expected Counts.

## Dry Run

The whole plan was executed red-first on a scratch clone of `079d58b` (`$SP/p25plan/dry`, never the repo) with the git-ignored runtime copied in (`client/braille/liblouis.dll`, `client/braille/liblouis/`, `client/braille/louis_helper.py`, `client/mathcat/`, a copy of `client/dictionary/`, and `include/liblouis/configure.ac` for `test_built_wrapper_loads_bundled_dll`), one commit per task. After Task 10 the full suite, the 20 shuffle seeds (one process each), the acceptance criteria, `p25_baseline.py` (BRL byte-identical to `$H/baseline`), `p25_perf.py`, the separator timing script, the msgid scan, the moved-lines listing and the mutation checks (6 mutants of the old `translate.py` after Task 4, 15 mutants of the split modules after Task 10, all caught) passed. Then this file's blocks were replayed in order on a fresh clone (`$SP/p25plan/replay`) by a harness that writes every `File:` block, applies every `Edit:` block, runs the scripts and commands, and compares outputs: every task's `HEAD:client` tree id matched the dry run's. The packaged-build check (Task 12) was not run in the dry run.

## Review Focus

1. **Byte identity of everything a user sees.** BRL (Unicode and ASCII), the display text, the source wrap, the alignment lists and the dual-view segments must not change for any input. Pinned three ways: the fake golden (unchanged fixture), the oracle equivalence tests (random, including malformed maps), and the real-liblouis golden plus the two recorded BRL hashes (Windows).
2. **The two linear algorithms** (Tasks 6-7) take the fast path only for a checked well-formed alignment (one start per token, one token per cell, non-decreasing starts within the braille); everything else runs the original code. The comments in the code state why the results are identical; the mutation check shows the nets catch a wrong shift, a wrong token index, a replaced list object and a too-lenient well-formedness check.
3. **Mechanical moves** (Tasks 8-10): the moved bodies are the old ones re-indented; Task 11 prints every new line for review.
4. **Import direction**: after Task 5 `conversion` imports nothing from `adapters`; after Task 10 no production module imports `translate`, and `conversion.alignment`, `tokenizer`, `line_wrap`, `contracts` load no `config`, `adapters`, `braille`, `wx`, `dual_view` or MathCAT.

## File Map

- Task 1: `client/tests/test_translation_result.py` (rewritten as `unittest`, tabs).
- Task 2: `client/tests/test_conversion_service.py` (relaxed assertion, one new test).
- Task 3: `client/tests/test_translation_liblouis_golden.py` (new), `client/tests/fixtures/translation_liblouis_golden.json` (generated), `client/tests/fixtures/p25_doc.txt` (copy of the history document).
- Task 4: `client/tests/legacy_translation_result.py` (oracle), `client/tests/test_translation_split_equivalence.py` (new).
- Task 5: `client/tests/test_translation_import_isolation.py`, `client/conversion/contracts.py` (new), `client/adapters/translation/contracts.py`, six one-line import changes.
- Task 6: `client/tests/test_translation_result_core.py` (`LinearTrimTest`), `client/translate.py`.
- Task 7: `client/tests/test_translation_result_core.py` (`LinearSeparatorTest`), `client/translate.py`.
- Task 8: `client/tests/test_conversion_tokenizer.py` (new), `client/conversion/tokenizer.py` (new), `client/translate.py`, `client/tests/test_translation_result_core.py` (patch target).
- Task 9: `client/tests/test_conversion_line_wrap.py` (new), `client/conversion/line_wrap.py` (new), `client/translate.py`.
- Task 10: `client/tests/test_translation_import_isolation.py`, `client/tests/test_translation_result_core.py`, `client/conversion/alignment.py` (new, generated from `translate.py`), `client/translate.py` (re-export), six one-line import changes.

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line |
| --- | --- | --- | --- |
| baseline (`079d58b`) | - | 1143 | `FAILED (failures=1, errors=1, skipped=5)` |
| 1 unittest conversion | 14 (module ran 0 before) | 1157 | `FAILED (failures=1, errors=1, skipped=5)` |
| 2 leading space | 1 | 1158 | `FAILED (errors=1, skipped=5)` |
| 3 real golden | 13 | 1171 | `FAILED (errors=1, skipped=5)` |
| 4 oracle | 8 | 1179 | `FAILED (errors=1, skipped=5)` |
| 5 contracts | 1 | 1180 | `FAILED (errors=1, skipped=5)` |
| 6 linear trim | 3 | 1183 | `FAILED (errors=1, skipped=5)` |
| 7 linear separators | 3 | 1186 | `FAILED (errors=1, skipped=5)` |
| 8 tokenizer | 14 | 1200 | `FAILED (errors=1, skipped=5)` |
| 9 line wrapper | 4 | 1204 | `FAILED (errors=1, skipped=5)` |
| 10 alignment | 4 | 1208 | `FAILED (errors=1, skipped=5)` |

The failure until Task 2 is `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`; the error in every row is `test_case_only_rename_still_renames` (F-W6, out of scope). The 5 skips are platform skips. On Linux the real-golden module is one module-level skip instead of 13 tests.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 with the Write tool (sources in the Appendix):

- `brief.py`: condenses unittest output (Global Constraints).
- `msgid_scan.py <client_dir>`: AST stand-in for `generate-pot.bat` (keywords `_`, `N_`; same file set); prints the msgid count and the sha256 of the sorted set.
- `p25_mutants.py <client_dir> <scratch_dir> <pre|post> [mutant ...]`: copies `client/` (without `.venv`, `log`, `dictionary`, `workspace`, `build`, `dist`, `config.json`, `__pycache__`) to `<scratch_dir>/client`, applies one mutant at a time, runs the P2-5 test modules there and prints which tests caught it. The repo is never changed.
- `shuffle_harness.py <seed>`: every test module in a seeded random order in one process.
- `moved_lines.py`: lines of the three new modules that are not in `translate.py` at `d4a7aa1` (indentation ignored).
- `p25_separator_perf.py <repeat ...>`: times `reclean_token` on dialogue-heavy real `zh-tw.ctb` output.

The Python edit scripts for `translate.py` and the import changes are written to `$T/` in the task that uses them.

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO diff main --stat -- client
```

Expected (`status` lists only the untracked `client2/`, `preprocessing/`, `testdata/`; no diff output):

```text
?? client2/
?? preprocessing/
?? testdata/
docs: plan for splitting translate.py (P2-5)
refactor/p2-5-translate-split
```

- [ ] **Step 2: Create the tools.** `mkdir -p $T/tools`, then write the six Appendix files to `$T/tools/` with the Write tool.

- [ ] **Step 3: Baseline suite, fixtures, msgids, tree.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1143 tests
FAILED (failures=1, errors=1, skipped=5)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
a8aa670c68fd711cf0a19e78a82cc3fcb8e55879
```

### Task 1: Run `test_translation_result` under unittest (D10)

- [ ] **Step 1: Before.** The module has pytest-style functions only.

```bash
$PY -m unittest tests.test_translation_result 2>&1 | tail -1
```

Expected:

```text
NO TESTS RAN
```

- [ ] **Step 2: Rewrite the module** (tabs, as today). Same names and expectations; the five fixtures are corrected as in the spec's verdict table, each with a one-line comment; `test_end_right_end_sentence_blank` keeps its fixture and states the branch it pins; one new test pins the original `test_remove_start_line_blank` fixture.

File: `client/tests/test_translation_result.py`

````python
import unittest

from translate import TranslationResult


BLANK = chr(0x2800)


class BindContractedTokensTest(unittest.TestCase):
	def test_bind_contracted_tokens_merges_source_characters_with_one_braille_cell(self) -> None:
		result = TranslationResult(
			list("A the test"),
			["⠠", "⠁", BLANK, "⠮", BLANK, "⠞", "⠑", "⠌"],
			[0, 0, 1, 2, 5, 6, 7, 8],
			[0, 2, 3, 3, 3, 4, 5, 6, 7, 7],
		)

		result.bind_contracted_tokens()

		self.assertEqual(result.raw, ["A", " ", "the", " ", "t", "e", "st"])
		self.assertEqual(result.braille_to_raw_pos, [0, 0, 1, 2, 3, 4, 5, 6])
		self.assertEqual(result.raw_to_braille_pos, [0, 2, 3, 4, 5, 6, 7])


class BindWordTokensTest(unittest.TestCase):
	def test_bind_word_tokens_lead_punct(self) -> None:
		"""開頭字元測試"""
		# One cell and one position per source character, as every producer builds them.
		result = TranslationResult(
			list("「嶼我共視"),
			["⠁", "⠂", "⠃", "⠄", "⠅"],
			[0, 1, 2, 3, 4],
			[0, 1, 2, 3, 4],
		)
		result.bind_word_tokens()
		self.assertEqual(result.raw, [
			"「嶼",
			"我",
			"共",
			"視",
		])

	def test_bind_word_tokens_lead_punct_continue(self) -> None:
		"""連續開頭字元測試"""
		# One cell and one position per source character, as every producer builds them.
		result = TranslationResult(
			list("「「嶼我共視"),
			["⠁", "⠂", "⠃", "⠄", "⠅", "⠆"],
			[0, 1, 2, 3, 4, 5],
			[0, 1, 2, 3, 4, 5],
		)
		result.bind_word_tokens()
		self.assertEqual(result.raw, [
			"「「嶼",
			"我",
			"共",
			"視",
		])

	def test_bind_word_tokens_tail_punct(self) -> None:
		"""尾隨字元測試"""
		result = TranslationResult(
			list("嶼我共視」"),
			["⠁", "⠂", "⠃", "⠄", "⠅"],
			[0, 1, 2, 3, 4],
			[0, 1, 2, 3, 4],
		)
		result.bind_word_tokens()
		self.assertEqual(result.raw, [
			"嶼",
			"我",
			"共",
			"視」",
		])

	def test_bind_word_tokens_tail_punct_continue(self) -> None:
		"""連續尾隨字元測試"""
		result = TranslationResult(
			list("嶼我共視。」"),
			["⠁", "⠂", "⠃", "⠄", "⠅", "⠆"],
			[0, 1, 2, 3, 4, 5],
			[0, 1, 2, 3, 4, 5],
		)
		result.bind_word_tokens()
		self.assertEqual(result.raw, [
			"嶼",
			"我",
			"共",
			"視。」",
		])

	def test_bind_word_tokens_complex(self) -> None:
		result = TranslationResult(
			list("Hello,. We are Coseeing. Coseeing is a community dedicated to championing digital accessibility."),
			["⠁"] * 94,
			list(range(94)),
			list(range(94)),
		)
		result.bind_word_tokens()
		self.assertEqual(result.raw, [
			"Hello,.",
			" ",
			"We",
			" ",
			"are",
			" ",
			"Coseeing.",
			" ",
			"Coseeing",
			" ",
			"is",
			" ",
			"a",
			" ",
			"community",
			" ",
			"dedicated",
			" ",
			"to",
			" ",
			"championing",
			" ",
			"digital",
			" ",
			"accessibility.",
		])


class RecleanTokenTest(unittest.TestCase):
	def test_bind_word_tokens_left_right_continue(self) -> None:
		"""右符號後接左符號插入空格"""
		result = TranslationResult(
			["「", "嶼", "我", "」", "「", "共", "視", "」"],
			["⠁", "⠂", "⠃", "⠄", "⠅", "⠆", "⠇", "⠈"],
			[0, 1, 2, 3, 4, 5, 6, 7],
			[0, 1, 2, 3, 4, 5, 6, 7],
		)
		result.reclean_token()
		self.assertEqual(result.raw, [
			"「",
			"嶼",
			"我",
			"」",
			" ",
			"「",
			"共",
			"視",
			"」",
		])

	def test_bind_word_tokens_left_right_continue2(self) -> None:
		"""右符號後接左符號插入空格"""
		result = TranslationResult(
			["『嶼", "我』", "「共", "視」"],
			["⠁", "⠂", "⠃", "⠄"],
			[0, 0, 1, 2],
			[0, 2, 3, 4],
		)
		result.reclean_token()
		self.assertEqual(result.raw, [
			"『嶼",
			"我』",
			" ",
			"「共",
			"視」",
		])


class WrapTest(unittest.TestCase):
	def test_end_right_end_sentence_blank(self) -> None:
		"""右符號/句尾符號加空白: pins the branch where the token's braille already ends
		in a blank cell, so wrap adds no separator (every cell here is blank)."""
		result = TranslationResult(
			["「嶼我共視是一個關心數位無障礙」", "\n", "「嶼我共視是一個關心數位無障礙」"],
			[BLANK] * 40,
			[0] * 40,
			[0, 20, 20],
		)
		self.assertEqual(result.wrap(40)[1], "「嶼我共視是一個關心數位無障礙」\n「嶼我共視是一個關心數位無障礙」")

	def test_end_right_end_sentence_blank2(self) -> None:
		"""右符號/句尾符號加空白"""
		# Non-blank cells: a token whose braille ends in a blank cell gets no separator.
		result = TranslationResult(
			["「嶼我共視 是個關心數位無障礙」", "\n", "「嶼我共視 是個關心數位無障礙」"],
			["⠁"] * 38,
			[0] * 38,
			[0, 19, 19],
		)
		self.assertEqual(result.wrap(40)[1], "「嶼我共視 是個關心數位無障礙」 \n「嶼我共視 是個關心數位無障礙」")

	def test_end_right_end_sentence_blank3(self) -> None:
		"""右符號/句尾符號加空白"""
		# Non-blank cells: a token whose braille ends in a blank cell gets no separator.
		result = TranslationResult(
			["「嶼我」", "『共視』"],
			["⠁"] * 8,
			[0] * 8,
			[0, 4],
		)
		self.assertEqual(result.wrap(40)[1], "「嶼我」 『共視』")

	def test_remove_start_line_blank(self) -> None:
		"""行中的空格在排版後如果在行首需移除"""
		# The first token fills the line (40 cells), so the space starts line 2.
		result = TranslationResult(
			["Coseeing is a community dedicated to an", " ", "I see"],
			[BLANK] * 46,
			[0] * 46,
			[0, 40, 41],
		)
		self.assertEqual(result.wrap(40)[1], "Coseeing is a community dedicated to an\nI see")

	def test_space_that_fits_at_the_line_end_stays_there(self) -> None:
		# The original fixture of test_remove_start_line_blank: 39 + 1 cells fill line 1.
		result = TranslationResult(
			["Coseeing is a community dedicated to an", " ", "I see"],
			[BLANK] * 45,
			[0] * 45,
			[0, 39, 40],
		)
		self.assertEqual(result.wrap(40)[1], "Coseeing is a community dedicated to an \nI see")

	def test_remove_start_line_blank2(self) -> None:
		"""行首的空格在排版後必定在行首，但不能移除"""
		result = TranslationResult(
			[" ", " ", " ", "Coseeing is a community dedicated to", " ", "I see"],
			[BLANK] * 45,
			[0] * 45,
			[0, 1, 2, 3, 40, 41],
		)
		self.assertEqual(result.wrap(40)[1], "   Coseeing is a community dedicated to\nI see")


if __name__ == "__main__":
	unittest.main()
````

- [ ] **Step 3: Run the module and the suite.**

```bash
$PY -m unittest tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 14 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1157 tests
FAILED (failures=1, errors=1, skipped=5)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_translation_result.py
git -C $REPO commit -q -m "test: run test_translation_result under unittest" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO show HEAD:client/tests/test_translation_result.py | sha256sum
```

Expected:

```text
76d5229449ef1c22a0589d08975967e0403934f8
ca35c1ee39c683d3de96d159cd23d7d2ed5bb3074adb95800bb990090a710a63 *-
```

### Task 2: Pin the leading space of a text segment (D9)

- [ ] **Step 1: Red is the known failure.**

```bash
$PY -m unittest tests.test_conversion_service 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_langu
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 27 tests
FAILED (failures=1)
```

- [ ] **Step 2: Relax the assertion and add the characterization test** (4 spaces).

Edit: `client/tests/test_conversion_service.py`

```python
        self.assertEqual(result.raw, ["計算 ", "1+2", " 的值"])
        self.assertEqual("".join(result.braille), "T[計算 ]M[1+2]T[ 的值]")
```

```python
        # Each source space appears once in the text and once in the braille (the fake
        # translates a lone " " to one blank cell); how the tokens split is pinned below.
        self.assertEqual("".join(result.raw), "計算 1+2 的值")
        self.assertEqual("".join(result.braille), "T[計算 ]M[1+2]⠀T[的值]")

    def test_leading_space_of_a_text_segment_is_its_own_token_and_segment(self) -> None:
        text_translator = FakeTextTranslator()
        result = translate_with_language(
            "計算 $1+2$ 的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=self._runtime(text_translator=text_translator),
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        request = ConversionRequest(
            raw_text="計算 $1+2$ 的值",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(result.raw, ["計算 ", "1+2", " ", "的值"])
        self.assertEqual([call[0] for call in text_translator.calls], ["計算 ", " ", "的值"])
        self.assertEqual(
            [(segment.source_kind, segment.result.raw) for segment in output.dual_view_segments],
            [("text", ["計算 "]), ("math", ["1+2"]), ("text", [" "]), ("text", ["的值"])],
        )
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_conversion_service 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 28 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1158 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_service.py
git -C $REPO commit -q -m "test: pin the leading space of a text segment" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO show HEAD:client/tests/test_conversion_service.py | sha256sum
```

Expected:

```text
01b2a49718fb75ff2f26b54db889a0ca555c7cd0
b597d5a3084904777fb5476f9937e315853ece5911e2f834365f3e359e7d27a1 *-
```

### Task 3: Pin real liblouis output on Windows (D11.3)

The fixture is written here, once, from unchanged production code.

- [ ] **Step 1: Copy the history document into the fixtures.**

```bash
git -C $REPO show HEAD:docs/superpowers/history/2026-10-09-03-windows-verification/p25_doc.txt > tests/fixtures/p25_doc.txt
sha256sum tests/fixtures/p25_doc.txt
```

Expected:

```text
d287af567962262be7fce5a624d698b844a0c231a225be49abc114fe5c5fa4a2 *tests/fixtures/p25_doc.txt
```

- [ ] **Step 2: Write the test module** (4 spaces).

File: `client/tests/test_translation_liblouis_golden.py`

````python
"""Golden characterization of the translation and wrap output with the real
liblouis and MathCAT (Windows only).

The fixture was written once from the unchanged production code (P2-5, step 3)
and must not be regenerated by a refactor. Regenerate it only for an intended
output change or a liblouis upgrade, on Windows, from client/:

    python -m tests.test_translation_liblouis_golden --write
"""
import ctypes
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


if not hasattr(ctypes, "WINFUNCTYPE"):
    raise unittest.SkipTest("liblouis bindings require WINFUNCTYPE on this platform")

# Probe through the helper: it adds the bundled DLL's directory first. A bare
# braille.liblouis import loads System32's older liblouis.dll on Windows 11 (W-1).
try:
    from braille import louis_helper
except Exception as exc:
    raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc

from adapters.translation.contracts import RuntimeUnavailableError, TranslationRuntime
from adapters.translation.provider import create_default_math_translator, create_default_text_translator
from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
from conversion.service import ConversionRequest, convert_text_with_alignment, translate_with_language
from conversion.wrapping import merge_translation_results


CLIENT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = CLIENT_DIR / "data"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURES_DIR / "translation_liblouis_golden.json"
P25_DOCUMENT_PATH = FIXTURES_DIR / "p25_doc.txt"
LANG = "zh_TW"
TABLE_SETS = {
    "default": dict(DEFAULT_TRANSLATION_TABLES),
    "ueb_g2": {**DEFAULT_TRANSLATION_TABLES, "en": "en-ueb-g2.ctb"},
}
INPUTS = {
    "zh_prose": "我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動。",
    "en_prose": "The quick brown fox jumps over the lazy dog, and then it rests. Testing, (one) [two]!",
    "ja_prose": "日本語の文章：これは点字翻訳のテストです。カタカナも含む。",
    "math_mix": "請計算 $\\frac{1}{2} + \\frac{2}{5}$ 的值，並說明 the reason why 你這樣做。",
    "spaced_math": "計算 $1+2$ 的值",
    "punctuation": "「引號」與（括號）（甲）（乙）『雙』——破折號，以及 \"English quotes\"、[a] {b}。",
    "spaces_lines": "  前置空白的中文行\n結尾有空白的行   \n第一章　緒論",
    "numbers": "價格是新臺幣 1,234 元（約 USD 40），請於 2026/10/09 前回覆。",
}
RUNS = (("unicode", 1), ("unicode", 10), ("unicode", 24), ("unicode", 40), ("ascii", 40))
# The p25_perf.py paragraph: dense full-width punctuation, so many trimmed tokens.
LONG_PARAGRAPH = "第一章　緒論。請說明你的理由，並且（如果可以）提供範例。這是一段用來測試效能的中文段落，包含標點符號。\n"
LONG_REPEAT = 400
LONG_RUNS = (("unicode", 40),)
# BRL bytes of tests/fixtures/p25_doc.txt from the Windows verification baseline
# (docs/superpowers/history/2026-10-09-03-windows-verification/results.md section 3 C).
P25_DOCUMENT_SHA256 = "d287af567962262be7fce5a624d698b844a0c231a225be49abc114fe5c5fa4a2"
P25_BRL_SHA256 = {
    "unicode": "365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c",
    "ascii": "95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64",
}


def build_runtime() -> TranslationRuntime:
    text_translator = create_default_text_translator()
    try:
        math_translator = create_default_math_translator()
    except BaseException:
        text_translator.close()
        raise
    return TranslationRuntime(
        text_translator=text_translator,
        math_translator=math_translator,
        close_callbacks=(text_translator.close, math_translator.close),
    )


def _lists(result) -> dict[str, list]:
    return {
        "raw": list(result.raw),
        "braille": list(result.braille),
        "braille_to_raw_pos": list(result.braille_to_raw_pos),
        "raw_to_braille_pos": list(result.raw_to_braille_pos),
    }


def _digest(value) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _request(text: str, output_mode: str, width: int, tables: dict, dictionary_path: Path) -> ConversionRequest:
    return ConversionRequest(
        raw_text=text,
        output_mode=output_mode,
        width=width,
        dictionary_path=dictionary_path,
        data_dir=DATA_DIR,
        translation_tables=dict(tables),
        lang=LANG,
        charset_maps=dict(DEFAULT_CHARSET_MAPS),
    )


def snapshot_run(runtime, text: str, output_mode: str, width: int, tables: dict, dictionary_path: Path) -> tuple[str, dict]:
    """Return (display text, width-independent conversion snapshot)."""
    output = convert_text_with_alignment(_request(text, output_mode, width, tables, dictionary_path), runtime=runtime)
    results = list(output.translation_results)
    merged = merge_translation_results(results)
    post_processed = merge_translation_results(results)
    post_processed.reclean_braille_endspace()
    post_processed.bind_word_tokens()
    post_processed.reclean_token()
    # Read after the wrap and the post-processing: they must not mutate the segments.
    segments = [
        {"source_kind": segment.source_kind, **_lists(segment.result)}
        for segment in output.dual_view_segments
    ]
    conversion = {
        "tokens": list(post_processed.raw),
        "merged_sha256": _digest(_lists(merged)),
        "post_processed_sha256": _digest(_lists(post_processed)),
        "dual_view_segments_sha256": _digest(segments),
        "dual_view_segment_count": len(segments),
    }
    return output.display_text, conversion


def snapshot_case(runtime, text: str, tables: dict, runs, dictionary_path: Path, *, digest_only: bool) -> dict:
    case = {"text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "runs": {}}
    for output_mode, width in runs:
        display_text, conversion = snapshot_run(runtime, text, output_mode, width, tables, dictionary_path)
        if digest_only:
            display_text = hashlib.sha256(display_text.encode("utf-8")).hexdigest()
            conversion["tokens"] = _digest(conversion["tokens"])
        case["runs"][f"{output_mode}-{width}"] = display_text
        case.setdefault("conversion", conversion)
        if case["conversion"] != conversion:
            raise AssertionError(f"conversion depends on {output_mode}-{width}")
    return case


def case_names() -> list[str]:
    # The long document is Chinese only, so the English table does not matter for it.
    return [f"{table_set}/{name}" for table_set in TABLE_SETS for name in INPUTS] + ["default/long_document"]


def snapshot_named_case(runtime, case_name: str, dictionary_path: Path) -> dict:
    table_set, name = case_name.split("/")
    if name == "long_document":
        return snapshot_case(
            runtime, LONG_PARAGRAPH * LONG_REPEAT, TABLE_SETS[table_set], LONG_RUNS, dictionary_path, digest_only=True
        )
    return snapshot_case(runtime, INPUTS[name], TABLE_SETS[table_set], RUNS, dictionary_path, digest_only=False)


def write_fixture() -> None:
    runtime = build_runtime()
    try:
        with tempfile.TemporaryDirectory() as directory:
            dictionary_path = Path(directory) / "default.csv"
            fixture = {
                "liblouis_version": louis_helper.louis.version(),
                "cases": {name: snapshot_named_case(runtime, name, dictionary_path) for name in case_names()},
            }
    finally:
        runtime.close()
    FIXTURE_PATH.write_text(json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE_PATH.name}: {len(fixture['cases'])} cases, liblouis {fixture['liblouis_version']}")


class LiblouisGoldenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        version = louis_helper.louis.version()
        if version != cls.fixture["liblouis_version"]:
            raise AssertionError(
                f"liblouis {version} differs from the fixture's {cls.fixture['liblouis_version']}; "
                "regenerate the fixture only for an intended liblouis upgrade"
            )
        try:
            cls.runtime = build_runtime()
        except RuntimeUnavailableError as error:
            raise unittest.SkipTest(f"real translation runtime unavailable: {error}") from error
        cls.addClassCleanup(cls.runtime.close)
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        # No dictionary file and no preprocessing script in this directory.
        cls.dictionary_path = Path(directory.name) / "default.csv"

    def assert_input(self, name: str) -> None:
        for case_name in (case for case in case_names() if case.endswith(f"/{name}")):
            with self.subTest(case=case_name):
                actual = snapshot_named_case(self.runtime, case_name, self.dictionary_path)
                expected = self.fixture["cases"][case_name]
                self.assertEqual(actual["text_sha256"], expected["text_sha256"])
                self.assertEqual(sorted(actual["runs"]), sorted(expected["runs"]))
                for run in sorted(expected["runs"]):
                    self.assertEqual(actual["runs"][run], expected["runs"][run], run)
                for key in sorted(expected["conversion"]):
                    self.assertEqual(actual["conversion"][key], expected["conversion"][key], key)
                self.assertEqual(sorted(actual["conversion"]), sorted(expected["conversion"]))

    def test_fixture_covers_every_case(self) -> None:
        self.assertEqual(sorted(self.fixture["cases"]), sorted(case_names()))

    def test_zh_prose(self) -> None:
        self.assert_input("zh_prose")

    def test_en_prose(self) -> None:
        self.assert_input("en_prose")

    def test_ja_prose(self) -> None:
        self.assert_input("ja_prose")

    def test_math_mix(self) -> None:
        self.assert_input("math_mix")

    def test_spaced_math(self) -> None:
        self.assert_input("spaced_math")

    def test_punctuation(self) -> None:
        self.assert_input("punctuation")

    def test_spaces_lines(self) -> None:
        self.assert_input("spaces_lines")

    def test_numbers(self) -> None:
        self.assert_input("numbers")

    def test_long_document(self) -> None:
        self.assert_input("long_document")

    def test_p25_document_matches_the_recorded_brl(self) -> None:
        document = P25_DOCUMENT_PATH.read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(document.encode("utf-8")).hexdigest(), P25_DOCUMENT_SHA256)
        for output_mode, expected in P25_BRL_SHA256.items():
            with self.subTest(output_mode=output_mode):
                output = convert_text_with_alignment(
                    _request(document, output_mode, 40, DEFAULT_TRANSLATION_TABLES, self.dictionary_path),
                    runtime=self.runtime,
                )
                # The BRL export writes the display text with Windows line ends.
                brl = output.display_text.replace("\n", "\r\n").encode("utf-8")
                self.assertEqual(hashlib.sha256(brl).hexdigest(), expected)

    def test_one_call_equals_split_calls(self) -> None:
        translator = self.runtime.text_translator
        cases = ((" 的值", (" ", "的值")), ("  中文", ("  ", "中文")), ("計算 ", ("計算", " ")))
        for whole, parts in cases:
            with self.subTest(text=whole):
                one = translator.translate(whole, table="zh-tw.ctb", raw=whole)
                split = [translator.translate(part, table="zh-tw.ctb", raw=part) for part in parts]
                self.assertEqual(
                    "".join(one.braille),
                    "".join("".join(result.braille) for result in split),
                )

    def test_leading_space_is_its_own_token_with_real_liblouis(self) -> None:
        text = "計算 $1+2$ 的值"
        result = translate_with_language(
            text,
            self.dictionary_path,
            dict(DEFAULT_TRANSLATION_TABLES),
            DATA_DIR / "Bopomofo2Braille.csv",
            runtime=self.runtime,
            lang=LANG,
            charset_maps=dict(DEFAULT_CHARSET_MAPS),
        )
        output = convert_text_with_alignment(
            _request(text, "unicode", 40, DEFAULT_TRANSLATION_TABLES, self.dictionary_path),
            runtime=self.runtime,
        )

        self.assertEqual(result.raw, ["計", "算", " ", "1+2", " ", "的", "值"])
        self.assertEqual("".join(result.braille), "⠅⠡⠐⠑⠻⠐⠀⠼⠁⠐⠖⠼⠃⠀⠙⠮⠁⠁⠱⠂")
        self.assertEqual(
            [(segment.source_kind, list(segment.result.raw)) for segment in output.dual_view_segments],
            [("text", ["計", "算", " "]), ("math", ["1+2"]), ("text", [" "]), ("text", ["的", "值"])],
        )


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write_fixture()
    else:
        unittest.main()
````

- [ ] **Step 3: Red: no fixture yet.**

```bash
$PY -m unittest tests.test_translation_liblouis_golden 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: setUpClass (tests.test_translation_liblouis_golden.LiblouisGoldenTest)
FileNotFoundError: [Errno 2] No such file or directory: '<client>\\tests\\fixtures\\translation_liblouis_golden.json'
Ran 0 tests
FAILED (errors=1)
```

- [ ] **Step 4: Write the fixture twice and check that it is deterministic.**

```bash
$PY -m tests.test_translation_liblouis_golden --write && sha256sum tests/fixtures/translation_liblouis_golden.json
$PY -m tests.test_translation_liblouis_golden --write && sha256sum tests/fixtures/translation_liblouis_golden.json
```

Expected (both lines identical; on this machine with liblouis 3.37.0 and the bundled MathCAT). `write_text` writes Windows line ends; git stores the file with LF, so Step 6 prints a different sha256 for the committed blob.

```text
wrote translation_liblouis_golden.json: 17 cases, liblouis 3.37.0
b699a0802d6b7068996469a9de31ac614b19e2d94427999f59b17e7d83c62cd4 *tests/fixtures/translation_liblouis_golden.json
wrote translation_liblouis_golden.json: 17 cases, liblouis 3.37.0
b699a0802d6b7068996469a9de31ac614b19e2d94427999f59b17e7d83c62cd4 *tests/fixtures/translation_liblouis_golden.json
```

- [ ] **Step 5: Green, nothing skipped.**

```bash
$PY -m unittest tests.test_translation_liblouis_golden -v 2>&1 | grep -c " ok$"
$PY -m unittest tests.test_translation_liblouis_golden 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
13
Ran 13 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1171 tests
FAILED (errors=1, skipped=5)
```

The fixture pins Q2: `ueb_g2/en_prose` has the tokens `'br', 'ow', 'n'` and `'ov', 'er'`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/tests/test_translation_liblouis_golden.py client/tests/fixtures/translation_liblouis_golden.json client/tests/fixtures/p25_doc.txt
git -C $REPO commit -q -m "test: pin real liblouis output on Windows" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in tests/fixtures/p25_doc.txt tests/fixtures/translation_liblouis_golden.json tests/test_translation_liblouis_golden.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
5b2cff83f800c252691ca191e80c1f12035678e5
d287af567962262be7fce5a624d698b844a0c231a225be49abc114fe5c5fa4a2 *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
c6ef015c179889c4b5cf6b3a7b41dc0fd2d9c584a6ca14aef72acd57b8ece214 *-
```

Task 11 checks that the fixtures never change after this commit.

### Task 4: Add the pre-split oracle and equivalence tests (D11.2)

- [ ] **Step 1: Write the oracle** (header + marker + the verbatim old file).

File: `$T/oracle_header.txt`

```text
# Frozen pre-split reference for tests/test_translation_split_equivalence.py (P2-5).
# Everything after the marker line below is a verbatim copy of client/translate.py
# at d4a7aa1 (git blob 10bd641485327b00cb71a14d4946f01a1788f794). Never edit this
# file: the equivalence tests check that blob id.
# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----
```

```bash
{ cat $T/oracle_header.txt; git -C $REPO show d4a7aa1:client/translate.py; } > tests/legacy_translation_result.py
head -6 tests/legacy_translation_result.py
```

Expected:

```text
# Frozen pre-split reference for tests/test_translation_split_equivalence.py (P2-5).
# Everything after the marker line below is a verbatim copy of client/translate.py
# at d4a7aa1 (git blob 10bd641485327b00cb71a14d4946f01a1788f794). Never edit this
# file: the equivalence tests check that blob id.
# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----
import string
```

(`oracle_header.txt` must end with a newline after the marker line.)

- [ ] **Step 2: Write the equivalence tests** (4 spaces).

File: `client/tests/test_translation_split_equivalence.py`

````python
"""Equivalence of the production TranslationResult with the pre-split translate.py (P2-5).

Each operation runs on identical seeded random starting states through the frozen
oracle (tests/legacy_translation_result.py) and through the production class. The
four lists, which of them are still the original list objects, the return value and
the type and message of any exception must match. Most cases have a well-formed
alignment, as every producer builds; a fixed share is malformed (shuffled, too long,
too short or out-of-range maps, arbitrary braille_to_raw_pos values) so that the
fallback paths run too.
"""
import hashlib
import random
import unittest
from pathlib import Path

from tests import legacy_translation_result as legacy
from translate import TranslationResult


ORACLE_PATH = Path(__file__).resolve().parent / "legacy_translation_result.py"
ORACLE_MARKER = "# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----\n"
ORACLE_BLOB = "10bd641485327b00cb71a14d4946f01a1788f794"
FIELDS = ("raw", "braille", "braille_to_raw_pos", "raw_to_braille_pos")
BLANK = chr(0x2800)
CELLS = (BLANK, BLANK, "⠁", "⠃")
PUNCTUATION = sorted(
    set().union(*(getattr(legacy.TranslationResult, name) for name in (
        "LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT",
    )))
    | {"—"}
)
UNIT_KINDS = (
    (6, lambda rng: rng.choice("abcXYZ019")),
    (2, lambda rng: "".join(rng.choice("abc12") for _ in range(rng.randint(2, 4)))),
    (2, lambda rng: rng.choice(("the", "1+2", "台灣", "ing"))),
    (5, lambda rng: rng.choice("中文我嶼視台")),
    (2, lambda rng: rng.choice("かなカナ")),
    (1, lambda rng: rng.choice("한글")),
    (1, lambda rng: rng.choice("ㄅㄆㄇ")),
    (7, lambda rng: rng.choice(PUNCTUATION)),
    (3, lambda rng: " "),
    (1, lambda rng: "　"),
    (2, lambda rng: "\n"),
    (1, lambda rng: rng.choice("#+=")),
)
RIGHT = sorted(legacy.TranslationResult.RIGHT_PUNCT)
LEFT = sorted(legacy.TranslationResult.LEFT_PUNCT)
# Dense right/left punctuation, so that reclean_token inserts several separators.
SEPARATOR_UNIT_KINDS = (
    (4, lambda rng: rng.choice(RIGHT)),
    (4, lambda rng: rng.choice(LEFT)),
    (2, lambda rng: rng.choice("視我a1") + rng.choice(RIGHT)),
    (2, lambda rng: rng.choice(LEFT) + rng.choice("共嶼b2")),
    (3, lambda rng: rng.choice("中文ab")),
    (1, lambda rng: " "),
    (1, lambda rng: "\n"),
)


def random_units(rng: random.Random, max_units: int, kinds=UNIT_KINDS) -> list[str]:
    weights = [weight for weight, _make in kinds]
    makers = [make for _weight, make in kinds]
    units = [rng.choices(makers, weights)[0](rng) for _ in range(rng.randint(0, max_units))]
    if units and rng.random() < 0.03:
        units[rng.randrange(len(units))] = ""
    return units


def random_state(rng: random.Random, max_units: int = 14, kinds=UNIT_KINDS) -> tuple[list, list, list, list]:
    """Return (raw, braille, braille_to_raw_pos, raw_to_braille_pos)."""
    raw = random_units(rng, max_units, kinds)
    braille, b2r, r2b = [], [], []
    for index, _unit in enumerate(raw):
        r2b.append(len(braille))
        for _cell in range(rng.choice((0, 1, 1, 2, 2, 3, 4))):
            braille.append(rng.choice(CELLS))
            b2r.append(index)
    if rng.random() < 0.25:
        malform(rng, raw, braille, b2r, r2b)
    return raw, braille, b2r, r2b


def malform(rng: random.Random, raw: list, braille: list, b2r: list, r2b: list) -> None:
    kind = rng.randrange(6)
    if kind == 0:
        rng.shuffle(r2b)
    elif kind == 1:
        r2b.append(rng.randint(0, len(braille)))
    elif kind == 2 and r2b:
        r2b.pop()
    elif kind == 3 and r2b:
        r2b[rng.randrange(len(r2b))] = rng.randint(-3, len(braille) + 3)
    elif kind == 4:
        b2r[:] = [rng.randint(-2, len(raw) + 2) for _ in b2r]
    elif b2r:
        del b2r[rng.randrange(len(b2r))]


def build_pair(state) -> tuple[legacy.TranslationResult, TranslationResult]:
    return (
        legacy.TranslationResult(*[list(values) for values in state]),
        TranslationResult(*[list(values) for values in state]),
    )


def outcome(result, operation) -> tuple:
    before = {name: getattr(result, name) for name in FIELDS}
    try:
        value = ("returned", operation(result))
    except Exception as error:
        value = ("raised", type(error).__name__, str(error))
    lists = tuple(list(getattr(result, name)) for name in FIELDS)
    kept = tuple(getattr(result, name) is before[name] for name in FIELDS)
    return value, lists, kept


class OracleTest(unittest.TestCase):
    def test_oracle_is_the_pre_split_translate_py(self) -> None:
        text = ORACLE_PATH.read_text(encoding="utf-8")
        _header, marker, body = text.partition(ORACLE_MARKER)
        data = body.encode("utf-8")

        self.assertEqual(marker, ORACLE_MARKER)
        self.assertEqual(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), ORACLE_BLOB)
        self.assertIsNot(legacy.TranslationResult, TranslationResult)


class SplitEquivalenceTest(unittest.TestCase):
    def assert_equivalent(self, seed: int, cases: int, operation, kinds=UNIT_KINDS) -> None:
        rng = random.Random(seed)
        paths = {"returned": 0, "raised": 0}
        for case in range(cases):
            state = random_state(rng, 14, kinds)
            arguments = operation.arguments(rng, state) if hasattr(operation, "arguments") else ()
            oracle, production = build_pair(state)
            expected = outcome(oracle, lambda result: operation(result, *arguments))
            actual = outcome(production, lambda result: operation(result, *arguments))
            paths[expected[0][0]] += 1
            if actual != expected:
                self.fail(f"seed {seed} case {case}: {state!r} {arguments!r}\nexpected {expected!r}\nactual   {actual!r}")
        self.assertGreater(paths["returned"], cases // 2)

    def test_bind_contracted_tokens_matches_the_oracle(self) -> None:
        self.assert_equivalent(101, 4000, lambda result: result.bind_contracted_tokens())

    def test_bind_word_tokens_matches_the_oracle(self) -> None:
        self.assert_equivalent(102, 4000, lambda result: result.bind_word_tokens())

    def test_insert_token_matches_the_oracle(self) -> None:
        def insert(result, index, text, braille):
            return result.insert_token(index, text, braille)

        def arguments(rng, state):
            raw = state[0]
            index = rng.randint(-1, len(raw) + 1)
            braille = "".join(rng.choice(CELLS) for _ in range(rng.randint(0, 3)))
            return index, rng.choice((" ", "x", "「")), braille if rng.random() < 0.5 else list(braille)

        insert.arguments = arguments
        self.assert_equivalent(103, 4000, insert)

    def test_reclean_token_matches_the_oracle(self) -> None:
        self.assert_equivalent(104, 2000, lambda result: result.reclean_token())
        self.assert_equivalent(108, 2000, lambda result: result.reclean_token(), SEPARATOR_UNIT_KINDS)

    def test_reclean_braille_endspace_matches_the_oracle(self) -> None:
        self.assert_equivalent(105, 4000, lambda result: result.reclean_braille_endspace())

    def test_wrap_matches_the_oracle(self) -> None:
        def wrap(result, width):
            return result.wrap(width)

        wrap.arguments = lambda rng, state: (rng.choice((rng.randint(1, 45), rng.randint(1, 6), 0, None)),)
        self.assert_equivalent(106, 4000, wrap)

    def test_whole_post_processing_matches_the_oracle(self) -> None:
        rng = random.Random(107)
        for case in range(2000):
            kinds = SEPARATOR_UNIT_KINDS if case % 2 else UNIT_KINDS
            states = [random_state(rng, 8, kinds) for _ in range(rng.randint(1, 3))]
            width = rng.randint(1, 45)
            pairs = [build_pair(state) for state in states]
            expected = self.post_process(legacy.TranslationResult, [oracle for oracle, _production in pairs], width)
            actual = self.post_process(TranslationResult, [production for _oracle, production in pairs], width)
            if actual != expected:
                self.fail(f"case {case}: {states!r} width {width}\nexpected {expected!r}\nactual   {actual!r}")

    @staticmethod
    def post_process(cls, results, width) -> tuple:
        merged = cls.concat(results)
        steps = []
        for name in ("reclean_braille_endspace", "bind_word_tokens", "reclean_token"):
            steps.append(outcome(merged, lambda result: getattr(result, name)()))
        steps.append(outcome(merged, lambda result: result.wrap(width)))
        return tuple(steps)


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 3: Green by construction.**

```bash
$PY -m unittest tests.test_translation_split_equivalence 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 8 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1179 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 4: Mutation check of the nets on the old code** (the spec's "throwaway mutation check"; about one minute).

```bash
$PY $T/tools/p25_mutants.py $REPO/client $T/mut pre
```

Expected (every mutant caught by its operation's equivalence test):

```text
contracted-merges-on-less-or-equal: 1 caught: test_translation_split_equivalence.test_bind_contracted_tokens_matches_the_oracle
word-lead-drops-em-dash: 3 caught: test_translation_liblouis_golden.test_punctuation, test_translation_split_equivalence.test_bind_word_tokens_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
insert-shifts-only-later-tokens: 6 caught: test_translation_golden.test_long_document, test_translation_golden.test_spaced_math_punctuation, test_translation_liblouis_golden.test_punctuation, test_translation_split_equivalence.test_insert_token_matches_the_oracle, test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
separator-only-before-full-width: 2 caught: test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
trim-may-empty-a-token: 5 caught: test_translation_liblouis_golden.test_long_document, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_spaces_lines, test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
wrap-drops-leading-spaces: 7 caught: test_translation_golden.test_dictionary_literal, test_translation_golden.test_long_document, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_spaces_lines, test_translation_result.test_remove_start_line_blank2, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle, test_translation_split_equivalence.test_wrap_matches_the_oracle
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/legacy_translation_result.py client/tests/test_translation_split_equivalence.py
git -C $REPO commit -q -m "test: add the pre-split oracle and equivalence tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in tests/legacy_translation_result.py tests/test_translation_split_equivalence.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
04baa5b799e556e28633d17ac313117554b92f68
f8a7d229f29a01399cc0aa00bf4a220d8e2f7fa01c3d983468d3745181f80b43 *-
43ba56b7509d879a0b5d91dbeef277272825fb0be45f1c0a77dd11e1ef5bbd42 *-
```

### Task 5: Move the translation ports into conversion (D8)

- [ ] **Step 1: Red: `adapters` becomes a higher layer of `conversion`, and the adapter contracts must re-export the conversion ports.**

Edit: `client/tests/test_translation_import_isolation.py`

```python
HIGHER_LAYERS = {"documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}
```

```python
HIGHER_LAYERS = {"adapters", "documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}
```

Edit: `client/tests/test_translation_import_isolation.py`

```python
    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
```

```python
    def test_adapter_contracts_reexport_the_conversion_ports(self) -> None:
        import adapters.translation
        import adapters.translation.contracts
        import conversion.contracts

        for name in ("BrailleTextTranslator", "MathSegmentTranslator", "TranslationRuntime"):
            with self.subTest(name=name):
                port = getattr(conversion.contracts, name)
                self.assertEqual(port.__module__, "conversion.contracts")
                self.assertIs(getattr(adapters.translation.contracts, name), port)
                self.assertIs(getattr(adapters.translation, name), port)
        error = adapters.translation.contracts.RuntimeUnavailableError
        self.assertEqual(error.__module__, "adapters.translation.contracts")
        self.assertIs(adapters.translation.RuntimeUnavailableError, error)
        self.assertFalse(hasattr(conversion.contracts, "RuntimeUnavailableError"))

    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
```

```bash
$PY -m unittest tests.test_translation_import_isolation 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_translation_import_isolation 2>&1 | grep "^-  *\['\|^-  *'"
```

Expected:

```text
ERROR: test_adapter_contracts_reexport_the_conversion_ports (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_adapter_contracts_reexp
ModuleNotFoundError: No module named 'conversion.contracts'
FAIL: test_conversion_package_imports_no_higher_layer (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_conversion_package_imports_no
AssertionError: Lists differ: ['conversion/jobs.py:5 adapters.translatio[187 chars]cts'] != []
Ran 7 tests
FAILED (failures=1, errors=1)
- ['conversion/jobs.py:5 adapters.translation.contracts',
-  'conversion/output.py:5 adapters.translation.contracts',
-  'conversion/service.py:1 adapters.translation.contracts',
-  'conversion/text/pipeline.py:4 adapters.translation.contracts']
```

- [ ] **Step 2: Create `conversion/contracts.py`** (the three ports moved verbatim; until Task 10 it imports `translate`).

File: `client/conversion/contracts.py`

````python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from translate import TranslationResult


class BrailleTextTranslator(Protocol):
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult: ...


class MathSegmentTranslator(Protocol):
    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult: ...


@dataclass
class TranslationRuntime:
    text_translator: BrailleTextTranslator
    math_translator: MathSegmentTranslator
    close_callbacks: tuple[Callable[[], None], ...] = ()
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for callback in reversed(self.close_callbacks):
            callback()
````

- [ ] **Step 3: Replace `adapters/translation/contracts.py`** (keeps `RuntimeUnavailableError`, re-exports the ports).

File: `client/adapters/translation/contracts.py`

````python
from __future__ import annotations

# The translation ports belong to their consumer, the conversion package; they are
# re-exported here so that adapters.translation keeps its names.
from conversion.contracts import BrailleTextTranslator, MathSegmentTranslator, TranslationRuntime


class RuntimeUnavailableError(RuntimeError):
    pass


__all__ = [
    "BrailleTextTranslator",
    "MathSegmentTranslator",
    "RuntimeUnavailableError",
    "TranslationRuntime",
]
````

- [ ] **Step 4: Point the six consumers at `conversion.contracts`.**

File: `$T/step5_imports.py`

````python
"""P2-5 Task 5: the six consumers import TranslationRuntime from conversion.contracts.

Run from client/. One exact line replacement per file; keeps CRLF.
"""
from pathlib import Path

old = b"from adapters.translation.contracts import TranslationRuntime\r\n"
new = b"from conversion.contracts import TranslationRuntime\r\n"
for name in (
    "conversion/jobs.py",
    "conversion/output.py",
    "conversion/service.py",
    "conversion/text/pipeline.py",
    "gui.py",
    "ui/conversion_presenter.py",
):
    path = Path(name)
    data = path.read_bytes()
    assert data.count(old) == 1, name
    path.write_bytes(data.replace(old, new))
print("6 imports now use conversion.contracts")
````

```bash
$PY $T/step5_imports.py
git -C $REPO grep -n "adapters" -- client/conversion
$PY -m unittest tests.test_translation_import_isolation 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (no `git grep` output):

```text
6 imports now use conversion.contracts
Ran 7 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1180 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/contracts.py client/adapters/translation/contracts.py client/conversion/jobs.py client/conversion/output.py client/conversion/service.py client/conversion/text/pipeline.py client/gui.py client/ui/conversion_presenter.py client/tests/test_translation_import_isolation.py
git -C $REPO commit -q -m "refactor: move the translation ports into conversion" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in adapters/translation/contracts.py conversion/contracts.py conversion/jobs.py conversion/output.py conversion/service.py conversion/text/pipeline.py gui.py tests/test_translation_import_isolation.py ui/conversion_presenter.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
fd6dd3b6917d441d5dcd2bb79399cc27c2313327
6ddda835b50a3fc85328ad1e5f1dd6a87a68fcd503888143dc67f4a67f91c6a5 *-
c01be859e35c284422882d02a2b5db8d0dc17b0639e70fc7671320621bb18246 *-
eb667a487a59b401734ebc88cd41f7f4be44a44b441878a861710ecdb6f8550d *-
4d4adf6e17cbaa791ef02aa2343c163ee21f372f15c323704487d85bfc9ef273 *-
a964d1e8c55b376505be16a2b55910380580db46a26ea232699d10c7ccea9434 *-
f41dd52fbd799dcd25a37e0c0c00b0f5a8d0bb679949408f563e8a0c403a1c15 *-
dfc0dac21fdf8173c9a1402ab39f6810e355f25d8f11257d3c3e8e10ca641c50 *-
9e7f6d143f5dcc50470cf3600a48337c1b0da09a85f903240505ee685f4dbc29 *-
ef58ebe72d2c04537860296b251111e90ab6304dfebac4f3389c82187c7b4582 *-
```

### Task 6: Trim trailing blank cells in one pass (D5, P1-5 known defect 3)

- [ ] **Step 1: Red: `LinearTrimTest`** (4 spaces; appended after `LinearMergeTest`).

Edit: `client/tests/test_translation_result_core.py`

```python
        self.assertLess(elapsed, 5.0)

if __name__ == "__main__":
```

```python
        self.assertLess(elapsed, 5.0)


class LinearTrimTest(unittest.TestCase):
    def test_trimming_forty_thousand_tokens_takes_linear_time(self) -> None:
        count = 40_000
        result = TranslationResult(
            ["中"] * count,
            ["⠁", "⠀"] * count,
            [index for index in range(count) for _cell in range(2)],
            [2 * index for index in range(count)],
        )

        started = time.perf_counter()
        result.reclean_braille_endspace()
        elapsed = time.perf_counter() - started

        self.assertEqual(
            lists_of(result),
            (["中"] * count, ["⠁"] * count, list(range(count)), list(range(count))),
        )
        self.assertLess(elapsed, 2.0)

    def test_trim_keeps_the_list_objects(self) -> None:
        result = TranslationResult(["中", "文", "字"], ["⠁", "⠀", "⠀", "⠃", "⠉", "⠀"], [0, 0, 0, 1, 2, 2], [0, 3, 4])
        before = lists_of(result)

        result.reclean_braille_endspace()

        self.assertEqual(lists_of(result), (["中", "文", "字"], ["⠁", "⠃", "⠉"], [0, 1, 2], [0, 1, 2]))
        for name, original in zip(FIELDS, before):
            self.assertIs(getattr(result, name), original, name)

    def test_malformed_alignment_uses_the_stepwise_trim(self) -> None:
        stepwise = TranslationResult._reclean_braille_endspace_stepwise
        well_formed = TranslationResult(["中", "文"], ["⠁", "⠀", "⠃", "⠀"], [0, 0, 1, 1], [0, 2])
        shuffled = TranslationResult(["中", "文"], ["⠁", "⠀", "⠃", "⠀"], [0, 0, 1, 1], [2, 0])

        with patch.object(TranslationResult, "_reclean_braille_endspace_stepwise", autospec=True, side_effect=stepwise) as fallback:
            well_formed.reclean_braille_endspace()
            fallback.assert_not_called()
            shuffled.reclean_braille_endspace()

        fallback.assert_called_once_with(shuffled)
        self.assertEqual(well_formed.braille, ["⠁", "⠃"])


if __name__ == "__main__":
```

```bash
$PY -m unittest tests.test_translation_result_core 2>&1 | $PY $T/tools/brief.py
```

Expected (the old trim needs about 40 s here):

```text
ERROR: test_malformed_alignment_uses_the_stepwise_trim (tests.test_translation_result_core.LinearTrimTest.test_malformed_alignment_uses_the_stepwise_trim)
AttributeError: type object 'TranslationResult' has no attribute '_reclean_braille_endspace_stepwise'. Did you mean: 'reclean_braille_endspace'?
FAIL: test_trimming_forty_thousand_tokens_takes_linear_time (tests.test_translation_result_core.LinearTrimTest.test_trimming_forty_thousand_tokens_takes_linear_
AssertionError: <seconds> not less than 2.0
Ran 24 tests
FAILED (failures=1, errors=1)
```

- [ ] **Step 2: Green: the one-pass trim with the stepwise fallback.**

File: `$T/step6_edit.py`

````python
"""P2-5 Task 6: trim trailing blank cells in one pass (client/translate.py).

Run from client/. Exact replacements (each must match once); keeps tabs and CRLF.
"""
from pathlib import Path

path = Path("translate.py")
text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")

old_helper_anchor = "\n\nclass TranslationResult:\n"
new_helper = '''

def _is_well_formed_alignment(raw, braille, braille_to_raw_pos, raw_to_braille_pos):
\t"""True when there is one start per token and one token per cell, and the token
\tstarts never decrease and stay within the braille, as every producer builds them."""
\tif len(raw_to_braille_pos) != len(raw) or len(braille_to_raw_pos) != len(braille):
\t\treturn False
\tprevious = 0
\tfor start in raw_to_braille_pos:
\t\tif start < previous:
\t\t\treturn False
\t\tprevious = start
\treturn previous <= len(braille)


class TranslationResult:
'''
assert text.count(old_helper_anchor) == 1
text = text.replace(old_helper_anchor, new_helper, 1)

old_head = '''\t\tif not self.braille_to_raw_pos or not self.raw_to_braille_pos:
\t\t\treturn

\t\tblank = chr(0x2800)
\t\tn_tokens = len(self.raw)
'''
new_head = '''\t\tif not self.braille_to_raw_pos or not self.raw_to_braille_pos:
\t\t\treturn
\t\tif not _is_well_formed_alignment(self.raw, self.braille, self.braille_to_raw_pos, self.raw_to_braille_pos):
\t\t\tself._reclean_braille_endspace_stepwise()
\t\t\treturn

\t\t# One pass. Every earlier trim lies before the current token (the starts never
\t\t# decrease) and shifts its start and end by the same amount, so the step-by-step
\t\t# loop sees each token's original cells: the same tokens lose the same cells.
\t\tblank = chr(0x2800)
\t\tbraille = self.braille
\t\tbraille_to_raw_pos = self.braille_to_raw_pos
\t\traw_to_braille_pos = self.raw_to_braille_pos
\t\tbraille_len = len(braille)
\t\tfirst_start = raw_to_braille_pos[0]
\t\tnew_braille = braille[:first_start]
\t\tnew_braille_to_raw_pos = braille_to_raw_pos[:first_start]
\t\tnew_raw_to_braille_pos = []
\t\tremoved = 0
\t\tfor t_idx, start in enumerate(raw_to_braille_pos):
\t\t\tend = raw_to_braille_pos[t_idx + 1] if t_idx + 1 < len(raw_to_braille_pos) else braille_len
\t\t\tnew_raw_to_braille_pos.append(start - removed)
\t\t\tnew_end = end
\t\t\twhile new_end - start > 1 and braille[new_end - 1] == blank:
\t\t\t\tnew_end -= 1
\t\t\tnew_braille.extend(braille[start:new_end])
\t\t\tnew_braille_to_raw_pos.extend(braille_to_raw_pos[start:new_end])
\t\t\tremoved += end - new_end
\t\t# Replace the contents, not the lists, as the step-by-step deletions do. No start
\t\t# can exceed the new length here, so the stepwise loop's final clamp is not needed.
\t\tbraille[:] = new_braille
\t\tbraille_to_raw_pos[:] = new_braille_to_raw_pos
\t\traw_to_braille_pos[:] = new_raw_to_braille_pos

\tdef _reclean_braille_endspace_stepwise(self):
\t\t"""The original trim, one token at a time; kept for malformed alignments, whose
\t\tdeletions can overlap later tokens."""
\t\tblank = chr(0x2800)
\t\tn_tokens = len(self.raw)
'''
assert text.count(old_head) == 1
text = text.replace(old_head, new_head, 1)
path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
print("translate.py: one-pass trim")
````

```bash
$PY $T/step6_edit.py
$PY -m unittest tests.test_translation_result_core tests.test_translation_split_equivalence tests.test_translation_golden tests.test_translation_liblouis_golden tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
translate.py: one-pass trim
Ran 66 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1183 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 3: Commit.**

```bash
git -C $REPO add client/translate.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -m "perf: trim trailing blank cells in one pass" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in tests/test_translation_result_core.py translate.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
704f05cc42afb314eef460211d9e2ab564edc055
e3ffafc89acd7349ed2ab210ac003cd3719ef03cb4e89f84e49233bcace30ebc *-
56d0458e3b8455e6d87822ef4edfeaee4c224ac468fed72b061da31765169642 *-
```

### Task 7: Insert punctuation separators in one pass (D6, Q1 = yes)

- [ ] **Step 1: Red: `LinearSeparatorTest`** (appended after `LinearTrimTest`).

Edit: `client/tests/test_translation_result_core.py`

```python
        fallback.assert_called_once_with(shuffled)
        self.assertEqual(well_formed.braille, ["⠁", "⠃"])
```

```python
        fallback.assert_called_once_with(shuffled)
        self.assertEqual(well_formed.braille, ["⠁", "⠃"])


class LinearSeparatorTest(unittest.TestCase):
    def test_inserting_ten_thousand_separators_takes_linear_time(self) -> None:
        count = 10_000
        result = TranslationResult(["」", "「"] * count, ["⠁"] * (2 * count), list(range(2 * count)), list(range(2 * count)))

        started = time.perf_counter()
        result.reclean_token()
        elapsed = time.perf_counter() - started

        self.assertEqual(
            lists_of(result),
            (["」", " ", "「"] * count, ["⠁", "⠀", "⠁"] * count, list(range(3 * count)), list(range(3 * count))),
        )
        self.assertLess(elapsed, 2.0)

    def test_well_formed_alignment_never_calls_insert_token(self) -> None:
        result = TranslationResult(["我」", "「共", "）", "（", "乙"], ["⠁", "⠂", "⠃", "⠄", "⠅", "⠆"], [0, 0, 1, 2, 3, 4], [0, 2, 3, 4, 5])

        with patch.object(TranslationResult, "insert_token", side_effect=AssertionError("one by one")):
            result.reclean_token()

        self.assertEqual(
            lists_of(result),
            (
                ["我」", " ", "「共", "）", " ", "（", "乙"],
                ["⠁", "⠂", "⠀", "⠃", "⠄", "⠀", "⠅", "⠆"],
                [0, 0, 1, 2, 3, 4, 5, 6],
                [0, 2, 3, 4, 5, 6, 7],
            ),
        )

    def test_malformed_alignment_inserts_one_by_one(self) -> None:
        insert_token = TranslationResult.insert_token
        result = TranslationResult(["我」", "「共", "）", "（"], ["⠁", "⠂", "⠃", "⠄"], [0, 1, 2], [0, 1, 2, 3])

        with patch.object(TranslationResult, "insert_token", autospec=True, side_effect=insert_token) as insert:
            result.reclean_token()

        self.assertEqual([call.args[1:] for call in insert.call_args_list], [(1, " ", "⠀"), (4, " ", "⠀")])
        self.assertEqual(result.raw, ["我」", " ", "「共", "）", " ", "（"])
```

```bash
$PY -m unittest tests.test_translation_result_core 2>&1 | $PY $T/tools/brief.py
```

Expected (the old loop needs about 20 s here):

```text
FAIL: test_inserting_ten_thousand_separators_takes_linear_time (tests.test_translation_result_core.LinearSeparatorTest.test_inserting_ten_thousand_separators_ta
AssertionError: <seconds> not less than 2.0
FAIL: test_well_formed_alignment_never_calls_insert_token (tests.test_translation_result_core.LinearSeparatorTest.test_well_formed_alignment_never_calls_insert_
AssertionError: one by one
Ran 27 tests
FAILED (failures=2)
```

- [ ] **Step 2: Green: separators inserted in one pass, one by one for malformed maps.**

File: `$T/step7_edit.py`

````python
"""P2-5 Task 7: insert punctuation separators in one pass (client/translate.py).

Run from client/. Exact replacements (each must match once); keeps tabs and CRLF.
"""
from pathlib import Path

path = Path("translate.py")
text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")

old_import = "import string\nfrom types import MappingProxyType\n"
new_import = "import string\nfrom bisect import bisect_right\nfrom types import MappingProxyType\n"
assert text.count(old_import) == 1
text = text.replace(old_import, new_import, 1)

old_body = '''\t\tblank_cell = chr(0x2800)
\t\ti = 1
\t\t# 以 while 迴圈處理，因為過程會動態插入 token、改變長度
\t\twhile i < len(self.raw):
\t\t\tprev_tok = self.raw[i - 1]
\t\t\tcurr_tok = self.raw[i]

\t\t\t# 防禦：空字串不處理
\t\t\tif prev_tok and curr_tok:
\t\t\t\tprev_last = prev_tok[-1]
\t\t\t\tcurr_first = curr_tok[0]

\t\t\t\tif (prev_last in self.RIGHT_PUNCT) and (curr_first in self.LEFT_PUNCT):
\t\t\t\t\t# 插入空白 token 與點字空格
\t\t\t\t\tself.insert_token(i, " ", blank_cell)
\t\t\t\t\ti += 1  # 跳過剛插入的空白

\t\t\ti += 1
'''
new_body = '''\t\tblank_cell = chr(0x2800)
\t\t# The original token indices before which a separator goes. The original loop
\t\t# skipped every inserted separator, so it checked exactly these adjacent pairs.
\t\tpositions = []
\t\tfor i in range(1, len(self.raw)):
\t\t\tprev_tok = self.raw[i - 1]
\t\t\tcurr_tok = self.raw[i]
\t\t\t# 防禦：空字串不處理
\t\t\tif prev_tok and curr_tok and prev_tok[-1] in self.RIGHT_PUNCT and curr_tok[0] in self.LEFT_PUNCT:
\t\t\t\tpositions.append(i)
\t\tif not positions:
\t\t\treturn
\t\tif not _is_well_formed_alignment(self.raw, self.braille, self.braille_to_raw_pos, self.raw_to_braille_pos):
\t\t\t# Malformed maps: insert one by one, exactly as before.
\t\t\tfor offset, index in enumerate(positions):
\t\t\t\tself.insert_token(index + offset, " ", blank_cell)
\t\t\treturn

\t\t# One pass: the lists that inserting the separators one by one would give.
\t\t# Separator m goes before original token positions[m], at token index
\t\t# positions[m] + m and braille index raw_to_braille_pos[positions[m]] + m.
\t\traw_to_braille_pos = self.raw_to_braille_pos
\t\tcount = len(positions)
\t\tnew_raw: list[str] = []
\t\tnew_raw_to_braille_pos: list[int] = []
\t\tinserted = 0
\t\tfor t_idx, token in enumerate(self.raw):
\t\t\tif inserted < count and positions[inserted] == t_idx:
\t\t\t\tnew_raw.append(" ")
\t\t\t\tnew_raw_to_braille_pos.append(raw_to_braille_pos[t_idx] + inserted)
\t\t\t\tinserted += 1
\t\t\tnew_raw.append(token)
\t\t\tnew_raw_to_braille_pos.append(raw_to_braille_pos[t_idx] + inserted)

\t\tseparator_cells = [raw_to_braille_pos[index] for index in positions]
\t\tnew_braille: list[str] = []
\t\tnew_braille_to_raw_pos: list[int] = []
\t\tinserted = 0
\t\tfor b_idx, cell in enumerate(self.braille):
\t\t\twhile inserted < count and separator_cells[inserted] <= b_idx:
\t\t\t\tnew_braille.append(blank_cell)
\t\t\t\tnew_braille_to_raw_pos.append(positions[inserted] + inserted)
\t\t\t\tinserted += 1
\t\t\t# One by one, a cell's token index grows at each separator inserted at or
\t\t\t# before the cell, until the first separator that lies after that token.
\t\t\ttoken_idx = self.braille_to_raw_pos[b_idx]
\t\t\tnew_braille.append(cell)
\t\t\tnew_braille_to_raw_pos.append(token_idx + min(inserted, bisect_right(positions, token_idx)))
\t\twhile inserted < count:
\t\t\tnew_braille.append(blank_cell)
\t\t\tnew_braille_to_raw_pos.append(positions[inserted] + inserted)
\t\t\tinserted += 1

\t\tself.raw = new_raw
\t\tself.braille = new_braille
\t\tself.raw_to_braille_pos = new_raw_to_braille_pos
\t\tself.braille_to_raw_pos = new_braille_to_raw_pos
'''
assert text.count(old_body) == 1
text = text.replace(old_body, new_body, 1)
path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
print("translate.py: one-pass separators")
````

```bash
$PY $T/step7_edit.py
$PY -m unittest tests.test_translation_result_core tests.test_translation_split_equivalence tests.test_translation_golden tests.test_translation_liblouis_golden tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
translate.py: one-pass separators
Ran 69 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1186 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 3: Commit.**

```bash
git -C $REPO add client/translate.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -m "perf: insert punctuation separators in one pass" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in tests/test_translation_result_core.py translate.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
7b36829fbbda7322adc9ec6782021657348d3925
d5120c88457e9549298999bf4c09c948c8dd5846d7a7bee0778c2b5c23211bac *-
b2f901fd4ae7987c36b3112a2f26b082561acfa0a5a5a37610bf698c26792f2c *-
```

### Task 8: Extract the tokenizer (D3)

- [ ] **Step 1: Red: the tokenizer tests** (4 spaces).

File: `client/tests/test_conversion_tokenizer.py`

````python
import unittest

from conversion import tokenizer
from translate import TranslationResult


def word_tokens(text: str) -> list[str]:
    units = list(text)
    return ["".join(units[start:end]) for start, end in tokenizer.word_token_spans(units)]


class ContractedTokenSpansTest(unittest.TestCase):
    def test_characters_with_one_braille_start_form_one_span(self) -> None:
        self.assertEqual(
            tokenizer.contracted_token_spans([0, 2, 3, 3, 3, 4, 5, 6, 7, 7]),
            [(0, 1), (1, 2), (2, 5), (5, 6), (6, 7), (7, 8), (8, 10)],
        )

    def test_no_positions_give_no_spans(self) -> None:
        self.assertEqual(tokenizer.contracted_token_spans([]), [])


class WordTokenSpansTest(unittest.TestCase):
    def test_ascii_letters_and_digits_form_one_token(self) -> None:
        self.assertEqual(word_tokens("Cos 2026 a1"), ["Cos", " ", "2026", " ", "a1"])

    def test_each_cjk_character_is_its_own_token(self) -> None:
        self.assertEqual(word_tokens("我們かな한글"), ["我", "們", "か", "な", "한", "글"])

    def test_a_newline_is_its_own_token(self) -> None:
        self.assertEqual(word_tokens("a\n\nb"), ["a", "\n", "\n", "b"])

    def test_a_trailing_punctuation_chain_joins_the_previous_word(self) -> None:
        self.assertEqual(word_tokens("共視。」"), ["共", "視。」"])
        self.assertEqual(word_tokens("Hello,."), ["Hello,."])

    def test_a_leading_punctuation_chain_joins_the_next_word(self) -> None:
        self.assertEqual(word_tokens("「「嶼我"), ["「「嶼", "我"])
        self.assertEqual(word_tokens("(one)"), ["(one)"])

    def test_a_leading_mark_before_a_space_or_newline_stays_alone(self) -> None:
        self.assertEqual(word_tokens("「 我"), ["「", " ", "我"])
        self.assertEqual(word_tokens("「　我"), ["「", "　", "我"])
        self.assertEqual(word_tokens("「\n我"), ["「", "\n", "我"])
        self.assertEqual(word_tokens("我「"), ["我", "「"])

    def test_an_em_dash_leads_the_next_word(self) -> None:
        self.assertEqual(word_tokens("——破折"), ["——破", "折"])

    def test_without_language_blocks_cjk_characters_take_no_punctuation(self) -> None:
        units = list("「嶼」")
        self.assertEqual(tokenizer.word_token_spans(units, {}), [(0, 1), (1, 2), (2, 3)])


class SeparatorPositionsTest(unittest.TestCase):
    def test_a_separator_goes_between_closing_and_opening_marks(self) -> None:
        tokens = ["我」", "「共", "）", "（", "乙", "]", "["]
        self.assertEqual(list(tokenizer.iter_separator_positions(tokens)), [1, 3, 6])

    def test_empty_tokens_and_other_pairs_get_no_separator(self) -> None:
        self.assertEqual(list(tokenizer.iter_separator_positions(["」", "", "「", "「", "」"])), [])
        self.assertEqual(list(tokenizer.iter_separator_positions([])), [])
        self.assertEqual(list(tokenizer.iter_separator_positions(["」"])), [])


class SharedConstantsTest(unittest.TestCase):
    def test_translation_result_exposes_the_tokenizer_constants(self) -> None:
        names = (
            "LEFT_PUNCT_HALF", "RIGHT_PUNCT_HALF", "MIDDLE_SENTENCE_PUNCT_HALF", "END_SENTENCE_PUNCT_HALF",
            "LEFT_PUNCT_FULL", "RIGHT_PUNCT_FULL", "MIDDLE_SENTENCE_PUNCT_FULL", "END_SENTENCE_PUNCT_FULL",
            "LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(TranslationResult, name), getattr(tokenizer, name))
        self.assertIs(TranslationResult.lang_blocks, tokenizer.CJK_LANGUAGE_BLOCKS)

    def test_hoisted_sets_keep_their_members(self) -> None:
        self.assertEqual(tokenizer.ASCII_ALNUM, frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
        self.assertEqual(
            tokenizer.TRAIL_PUNCT,
            tokenizer.RIGHT_PUNCT | tokenizer.MIDDLE_SENTENCE_PUNCT | tokenizer.END_SENTENCE_PUNCT,
        )
        self.assertEqual(tokenizer.LEAD_PUNCT, tokenizer.LEFT_PUNCT | {"—"})


if __name__ == "__main__":
    unittest.main()
````

```bash
$PY -m unittest tests.test_conversion_tokenizer 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_conversion_tokenizer (unittest.loader._FailedTest.test_conversion_tokenizer)
ImportError: Failed to import test module: test_conversion_tokenizer
ImportError: cannot import name 'tokenizer' from 'conversion' (<client>\conversion\__init__.py)
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 2: Create `conversion/tokenizer.py`** (4 spaces; the constants, the hoisted per-call sets and the three span/position functions; moved bodies keep their comments).

File: `client/conversion/tokenizer.py`

````python
"""How source characters are grouped into tokens.

Pure functions over token lists and position maps; TranslationResult
(conversion.alignment) applies the spans they return to its four lists.
"""
import string
from types import MappingProxyType

from languageDetection.unicode_blocks import (
    build_language_blocks,
    language_has_all,
)


LEFT_PUNCT_HALF = frozenset("([{")
RIGHT_PUNCT_HALF = frozenset(")]}")
MIDDLE_SENTENCE_PUNCT_HALF = frozenset(",;:%")
END_SENTENCE_PUNCT_HALF = frozenset(".!?")

LEFT_PUNCT_FULL = frozenset("‘“「『〈《【〔〖（")
RIGHT_PUNCT_FULL = frozenset("’”」』〉》】〕〗）")
MIDDLE_SENTENCE_PUNCT_FULL = frozenset("，；：、％")
END_SENTENCE_PUNCT_FULL = frozenset("。！？")

LEFT_PUNCT = LEFT_PUNCT_HALF | LEFT_PUNCT_FULL
RIGHT_PUNCT = RIGHT_PUNCT_HALF | RIGHT_PUNCT_FULL
MIDDLE_SENTENCE_PUNCT = MIDDLE_SENTENCE_PUNCT_HALF | MIDDLE_SENTENCE_PUNCT_FULL
END_SENTENCE_PUNCT = END_SENTENCE_PUNCT_HALF | END_SENTENCE_PUNCT_FULL

CJK_LANGUAGE_BLOCKS = MappingProxyType({
    language: tuple(blocks)
    for language, blocks in build_language_blocks(("ja", "zh", "ko")).items()
})

# ---- ASCII 英數集合（可合併成詞）----
ASCII_ALNUM = frozenset(string.ascii_letters + string.digits)
# 會併到「前一個字母 token」的尾隨標點（避免出現在行首）
TRAIL_PUNCT = RIGHT_PUNCT | MIDDLE_SENTENCE_PUNCT | END_SENTENCE_PUNCT
# 會併到「後一個字母 token」的開頭標點（避免出現在行尾）
LEAD_PUNCT = LEFT_PUNCT | frozenset("—")


def is_cjk_word_char(ch: str, lang_blocks) -> bool:
    """CJK/kana/Bopomofo/Hangul letters: one token each, but they can take punctuation."""
    if not lang_blocks:
        return False
    for _lang in ("ja", "zh", "ko"):
        if language_has_all(_lang, ch, lang_blocks):
            return True
    return False


def contracted_token_spans(raw_to_braille_pos) -> list[tuple[int, int]]:
    """Spans of adjacent source characters that share one braille-cell start."""
    token_spans: list[tuple[int, int]] = []
    start = 0
    while start < len(raw_to_braille_pos):
        end = start + 1
        while (
            end < len(raw_to_braille_pos)
            and raw_to_braille_pos[end] == raw_to_braille_pos[start]
        ):
            end += 1
        token_spans.append((start, end))
        start = end
    return token_spans


def word_token_spans(units, lang_blocks=CJK_LANGUAGE_BLOCKS) -> list[tuple[int, int]]:
    """Spans of word-level tokens over units (see TranslationResult.bind_word_tokens).

    The token text of a span (start, end) is always "".join(units[start:end]).
    """
    chars = units  # list[str]（每元素一字元）
    n_chars = len(chars)

    # ---- Pass 1：產生基礎 tokens ----
    # 規則：
    #   - 連續 ASCII 英數 → 合併為一個 token
    #   - CJK/假名/注音/韓文 → 單字一 token（不合併）
    #   - 其他（空白/標點/符號…）→ 單字一 token
    #   - '\n' → 獨立 token
    tokens: list[str] = []
    token_char_spans: list[tuple[int, int]] = []  # (char_start, char_end_exclusive)

    i = 0
    while i < n_chars:
        ch = chars[i]
        if ch == "\n":
            tokens.append("\n")
            token_char_spans.append((i, i + 1))
            i += 1
            continue

        if ch in ASCII_ALNUM:
            j = i + 1
            while j < n_chars and chars[j] in ASCII_ALNUM:
                j += 1
            tokens.append("".join(chars[i:j]))
            token_char_spans.append((i, j))
            i = j
            continue

        if is_cjk_word_char(ch, lang_blocks):
            tokens.append(ch)
            token_char_spans.append((i, i + 1))
            i += 1
            continue

        # 其他：空白/標點/符號等，單字元 token
        tokens.append(ch)
        token_char_spans.append((i, i + 1))
        i += 1

    # ---- 定義「字母 token」：可被尾隨/開頭標點綁定的 token ----
    #   A) 含任一 ASCII_ALNUM 的 ASCII 詞
    #   B) 長度為 1 且為 CJK 字母字元
    def is_word_token(tok: str) -> bool:
        if any(c in ASCII_ALNUM for c in tok):
            return True
        return len(tok) == 1 and is_cjk_word_char(tok, lang_blocks)

    # ---- Pass 2：尾隨標點鏈併入前一個字母 token ----
    merged_tokens: list[str] = []
    merged_spans: list[tuple[int, int]] = []
    t = 0
    while t < len(tokens):
        tok = tokens[t]
        span_start, span_end = token_char_spans[t]

        if is_word_token(tok):
            u = t
            trailing_text = ""
            trailing_end = span_end
            # 貪婪吸收連續尾隨標點
            while (
                u + 1 < len(tokens)
                and len(tokens[u + 1]) == 1
                and tokens[u + 1] in TRAIL_PUNCT
            ):
                u += 1
                trailing_text += tokens[u]
                trailing_end = token_char_spans[u][1]
            if trailing_text:
                tok = tok + trailing_text
                span_end = trailing_end
                t = u  # 跳過吃掉的尾隨標點

        merged_tokens.append(tok)
        merged_spans.append((span_start, span_end))
        t += 1

    tokens = merged_tokens
    token_char_spans = merged_spans

    # ---- Pass 3：開頭標點鏈併到下一個字母 token ----
    # 不與 '\n' 或空白（含全形空白等 .isspace()）綁定
    merged_tokens2: list[str] = []
    merged_spans2: list[tuple[int, int]] = []
    t = 0
    while t < len(tokens):
        tok = tokens[t]
        span_start, span_end = token_char_spans[t]

        if len(tok) == 1 and tok in LEAD_PUNCT and t + 1 < len(tokens):
            u = t
            lead_text = tok
            lead_start = span_start
            lead_end = span_end

            # 收集連續的開頭標點
            while (
                u + 1 < len(tokens)
                and len(tokens[u + 1]) == 1
                and tokens[u + 1] in LEAD_PUNCT
            ):
                u += 1
                lead_text += tokens[u]
                lead_end = token_char_spans[u][1]

            # 嘗試與下一個可綁定的「字母 token」合併
            if u + 1 < len(tokens):
                next_tok = tokens[u + 1]
                if next_tok != "\n" and not (len(next_tok) == 1 and next_tok.isspace()):
                    if is_word_token(next_tok):
                        merged_tokens2.append(lead_text + next_tok)
                        merged_spans2.append((lead_start, token_char_spans[u + 1][1]))
                        t = u + 2
                        continue

            # 無法綁定則保留開頭標點鏈
            merged_tokens2.append(lead_text)
            merged_spans2.append((lead_start, lead_end))
            t = u + 1
            continue

        # 其他情況原樣輸出
        merged_tokens2.append(tok)
        merged_spans2.append((span_start, span_end))
        t += 1

    return merged_spans2


def iter_separator_positions(tokens):
    """Yield each index i (1 <= i < len(tokens)) before which a separator space goes:
    tokens[i - 1] ends with a closing and tokens[i] starts with an opening mark."""
    for i in range(1, len(tokens)):
        prev_tok = tokens[i - 1]
        curr_tok = tokens[i]
        # 防禦：空字串不處理
        if prev_tok and curr_tok and prev_tok[-1] in RIGHT_PUNCT and curr_tok[0] in LEFT_PUNCT:
            yield i
````

- [ ] **Step 3: `TranslationResult` uses it** (constants are the tokenizer's objects; `_regroup` replaces the two map rebuilds; `reclean_token` reads `iter_separator_positions`), and the language-blocks patch target moves (Correction 2).

File: `$T/step8_edit.py`

````python
"""P2-5 Task 8: translate.py uses conversion.tokenizer.

Run from client/. Exact replacements (each must match once); keeps tabs and CRLF.
"""
from pathlib import Path

path = Path("translate.py")
text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def replace_once(old, new):
    global text
    assert text.count(old) == 1, old[:80]
    text = text.replace(old, new, 1)


def replace_between(start, stop, new):
    global text
    assert text.count(start) == 1 and text.count(stop) == 1, start
    i, j = text.index(start), text.index(stop)
    text = text[:i] + new + text[j:]


replace_between("import string\n", "def _is_well_formed_alignment", '''from bisect import bisect_right

from conversion import tokenizer
from conversion.tokenizer import contracted_token_spans, iter_separator_positions, word_token_spans


''')
replace_between("\tLEFT_PUNCT_HALF = ", "\t__hash__ = None\n", '''\t# The same objects as the tokenizer's constants.
\tLEFT_PUNCT_HALF = tokenizer.LEFT_PUNCT_HALF
\tRIGHT_PUNCT_HALF = tokenizer.RIGHT_PUNCT_HALF
\tMIDDLE_SENTENCE_PUNCT_HALF = tokenizer.MIDDLE_SENTENCE_PUNCT_HALF
\tEND_SENTENCE_PUNCT_HALF = tokenizer.END_SENTENCE_PUNCT_HALF

\tLEFT_PUNCT_FULL = tokenizer.LEFT_PUNCT_FULL
\tRIGHT_PUNCT_FULL = tokenizer.RIGHT_PUNCT_FULL
\tMIDDLE_SENTENCE_PUNCT_FULL = tokenizer.MIDDLE_SENTENCE_PUNCT_FULL
\tEND_SENTENCE_PUNCT_FULL = tokenizer.END_SENTENCE_PUNCT_FULL

\tLEFT_PUNCT = tokenizer.LEFT_PUNCT
\tRIGHT_PUNCT = tokenizer.RIGHT_PUNCT
\tMIDDLE_SENTENCE_PUNCT = tokenizer.MIDDLE_SENTENCE_PUNCT
\tEND_SENTENCE_PUNCT = tokenizer.END_SENTENCE_PUNCT

\tlang_blocks = tokenizer.CJK_LANGUAGE_BLOCKS

''')
replace_between("\t\tif not self.raw or len(self.raw) != len(self.raw_to_braille_pos):\n\t\t\treturn\n", "\tdef bind_word_tokens(self):\n", '''\t\tif not self.raw or len(self.raw) != len(self.raw_to_braille_pos):
\t\t\treturn
\t\tself._regroup(contracted_token_spans(self.raw_to_braille_pos))

''')
replace_between("\t\t# 取得語系對應 blocks\n", "\tdef insert_token(", '''\t\tspans = word_token_spans(self.raw, self.lang_blocks)

\t\t# 防禦：長度不一致時維持原狀（避免 IndexError）
\t\tif not self.raw_to_braille_pos or not self.raw or len(self.braille_to_raw_pos) != len(self.braille):
\t\t\treturn
\t\tself._regroup(spans)

\tdef _regroup(self, spans):
\t\t"""Rebuild the four lists for tokens made of the given spans of the current tokens."""
\t\told_raw = self.raw
\t\told_r2b = self.raw_to_braille_pos

\t\t# token → braille 起始（取 token 第一個字元的起點）
\t\tnew_raw_to_braille_pos = [old_r2b[span_start] for span_start, _span_end in spans]

\t\t# 字元索引 → token 索引
\t\tchar_to_token = [0] * len(old_raw)
\t\tfor token_index, (span_start, span_end) in enumerate(spans):
\t\t\tfor char_index in range(span_start, span_end):
\t\t\t\tchar_to_token[char_index] = token_index

\t\t# braille 索引 → token 索引（從舊的字元級映射轉換）
\t\tnew_braille_to_raw_pos = [
\t\t\tchar_to_token[char_index]
\t\t\tif 0 <= char_index < len(old_raw)
\t\t\telse 0
\t\t\tfor char_index in self.braille_to_raw_pos
\t\t]

\t\tself.raw = ["".join(old_raw[span_start:span_end]) for span_start, span_end in spans]
\t\tself.raw_to_braille_pos = new_raw_to_braille_pos
\t\tself.braille_to_raw_pos = new_braille_to_raw_pos

''')
replace_between("\t\t# The original token indices before which a separator goes.", "\t\tif not positions:\n", '''\t\t# The original token indices before which a separator goes. The original loop
\t\t# skipped every inserted separator, so it checked exactly these adjacent pairs.
\t\tpositions = list(iter_separator_positions(self.raw))
''')
path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
print("translate.py: tokenizer extracted")
````

Edit: `client/tests/test_translation_result_core.py`

```python
        with patch("translate.build_language_blocks", side_effect=AssertionError("built per instance")) as build:
```

```python
        with patch("conversion.tokenizer.build_language_blocks", side_effect=AssertionError("built per instance")) as build:
```

```bash
$PY $T/step8_edit.py
$PY -m unittest tests.test_conversion_tokenizer tests.test_translation_result_core tests.test_translation_split_equivalence tests.test_translation_golden tests.test_translation_liblouis_golden tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
translate.py: tokenizer extracted
Ran 83 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1200 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/conversion/tokenizer.py client/tests/test_conversion_tokenizer.py client/translate.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -m "refactor: extract the tokenizer" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in conversion/tokenizer.py tests/test_conversion_tokenizer.py tests/test_translation_result_core.py translate.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
12b5b9d4b012b915c37cf6d691aff6ef3d815945
0b2c9ae1f28522cf4be1c2208b56a355101e17f3cb337164a566371b736a6d97 *-
321820c695824d0a2e703369cb139e10f09cdeddc769ab18aeeb21f847cd2f61 *-
6694d2e13be77185ea8a7fe2d28016fee1aa142c9ff75f4fd05b6916e946de57 *-
40d73f2844e0b8610f7a71f74bd5645653bbe05aeee9ccf6bad25301f198df57 *-
```

### Task 9: Extract the line wrapper (D4)

- [ ] **Step 1: Red: the line-wrap tests** (4 spaces; they compare `wrap_tokens` with the oracle's `wrap`).

File: `client/tests/test_conversion_line_wrap.py`

````python
import copy
import unittest

from conversion import line_wrap, tokenizer
from tests import legacy_translation_result as legacy


BLANK = chr(0x2800)
# The WrapTest fixtures of tests/test_translation_result.py: (tokens, braille, raw_to_braille_pos).
WRAP_CASES = (
    (["「嶼我共視是一個關心數位無障礙」", "\n", "「嶼我共視是一個關心數位無障礙」"], [BLANK] * 40, [0, 20, 20]),
    (["「嶼我共視 是個關心數位無障礙」", "\n", "「嶼我共視 是個關心數位無障礙」"], ["⠁"] * 38, [0, 19, 19]),
    (["「嶼我」", "『共視』"], ["⠁"] * 8, [0, 4]),
    (["Coseeing is a community dedicated to an", " ", "I see"], [BLANK] * 46, [0, 40, 41]),
    (["Coseeing is a community dedicated to an", " ", "I see"], [BLANK] * 45, [0, 39, 40]),
    ([" ", " ", " ", "Coseeing is a community dedicated to", " ", "I see"], [BLANK] * 45, [0, 1, 2, 3, 40, 41]),
    (["中。", "\n", "\n", "文", " ", "字"], ["⠁", "⠂", BLANK, BLANK, "⠃", BLANK, "⠄"], [0, 2, 3, 4, 5, 6]),
)


class WrapTokensTest(unittest.TestCase):
    def test_wrap_tokens_matches_the_pre_split_wrap(self) -> None:
        for index, (tokens, braille, raw_to_braille_pos) in enumerate(WRAP_CASES):
            for width in (1, 2, 5, 10, 39, 40, 41):
                with self.subTest(case=index, width=width):
                    oracle = legacy.TranslationResult(list(tokens), list(braille), [0] * len(braille), list(raw_to_braille_pos))
                    self.assertEqual(
                        line_wrap.wrap_tokens(tokens, braille, raw_to_braille_pos, width),
                        oracle.wrap(width),
                    )

    def test_a_full_width_closing_mark_gets_a_separator(self) -> None:
        self.assertEqual(
            line_wrap.wrap_tokens(["「嶼我」", "『共視』"], ["⠁"] * 8, [0, 4], 40),
            ("⠁⠁⠁⠁⠀⠁⠁⠁⠁" + BLANK * 31, "「嶼我」 『共視』"),
        )

    def test_wrap_tokens_does_not_mutate_its_inputs(self) -> None:
        for tokens, braille, raw_to_braille_pos in WRAP_CASES:
            arguments = (list(tokens), list(braille), list(raw_to_braille_pos))
            before = copy.deepcopy(arguments)

            line_wrap.wrap_tokens(*arguments, 10)

            self.assertEqual(arguments, before)

    def test_separator_and_space_sets(self) -> None:
        self.assertEqual(line_wrap.SEPARATED_AFTER_PUNCT, tokenizer.RIGHT_PUNCT_FULL | tokenizer.END_SENTENCE_PUNCT_FULL)
        self.assertIsInstance(line_wrap.SEPARATED_AFTER_PUNCT, frozenset)
        self.assertEqual(line_wrap.SPACE_ONLY, frozenset(" "))


if __name__ == "__main__":
    unittest.main()
````

```bash
$PY -m unittest tests.test_conversion_line_wrap 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_conversion_line_wrap (unittest.loader._FailedTest.test_conversion_line_wrap)
ImportError: Failed to import test module: test_conversion_line_wrap
ImportError: cannot import name 'line_wrap' from 'conversion' (<client>\conversion\__init__.py)
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 2: Create `conversion/line_wrap.py`** (the body of `wrap` with the parameters for `self`, the two module sets, explicit parentheses and English branch comments).

File: `client/conversion/line_wrap.py`

````python
"""How tokens are laid out on lines of a given width."""
from conversion.tokenizer import END_SENTENCE_PUNCT_FULL, RIGHT_PUNCT_FULL


# A token ending in one of these marks is followed by a separator space when the
# next token is not a space and the token's braille does not already end blank.
SEPARATED_AFTER_PUNCT = RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL
SPACE_ONLY = frozenset(" ")


def wrap_tokens(tokens, braille, raw_to_braille_pos, width) -> tuple[str, str]:
    """Lay the tokens out on lines of width braille cells.

    Token i owns the cells braille[raw_to_braille_pos[i]:raw_to_braille_pos[i + 1]]
    (the last token owns the rest). Returns (braille text, source text), lines joined
    by "\\n"; every braille line is padded with blank cells to the full width. The
    inputs are only read.
    """
    blank = chr(0x2800)
    width = max(1, int(width or 1))
    current_len = 0

    raw_lines: list[list[str]] = []
    current_raw_parts: list[str] = []

    braille_lines: list[list[str]] = []
    current_braille_parts: list[str] = []

    raw_len = len(tokens)

    # line_start_blank 是為了分辨是原文就在開頭的空白與後續因點字規則需要而插入的空白
    # (line_start_blank tells spaces that start a source line, which are kept, from a
    # space that only starts a wrapped line, which is dropped.)
    line_start_blank = True
    full_line_break = False

    for i, token in enumerate(tokens):
        # Treat explicit newline in source as a hard line break.
        if token == "\n":
            # Pad a partly filled line, or an empty line that a newline started (not
            # the empty line left behind when the previous token filled a line).
            if (current_len < width and current_len > 0) or (current_len == 0 and not full_line_break):
                current_raw_parts.append("")
                current_braille_parts.append(blank * (width - current_len))

            # 不能與上面條件相同，要移除 current_len < width 因為這樣如果單一 token 超過寬度雖然會爆版，但仍能顯示
            # (Not the same condition as above: without current_len < width, a line that
            # one over-long token overflows is still ended here, so the token is shown.)
            if current_len > 0 or (current_len == 0 and not full_line_break):
                raw_lines.append(current_raw_parts)
                braille_lines.append(current_braille_parts)
                current_raw_parts = []
                current_braille_parts = []
                current_len = 0

            line_start_blank = True
            full_line_break = False
            continue
        elif token == " ":
            # A space at the start of a wrapped line is dropped.
            if current_len == 0 and not line_start_blank:
                continue

        if token != " ":
            line_start_blank = False

        full_line_break = False
        start = raw_to_braille_pos[i]
        end = raw_to_braille_pos[i + 1] if i + 1 < raw_len else len(braille)
        seg_len = end - start

        # The token does not fit: pad and end the current line first.
        if current_len + seg_len > width and current_len > 0:
            current_raw_parts.append("")
            current_braille_parts.append(blank * (width - current_len))
            raw_lines.append(current_raw_parts)
            braille_lines.append(current_braille_parts)
            current_raw_parts = []
            current_braille_parts = []
            current_len = 0

        if seg_len:
            current_raw_parts.append(token)
            current_braille_parts.append("".join(braille[start:end]))
            current_len += seg_len

        if current_len < width:
            next_token = tokens[i + 1] if i + 1 < len(tokens) else None
            if (
                token[-1] in SEPARATED_AFTER_PUNCT
                and next_token is not None
                and next_token not in SPACE_ONLY
                and current_braille_parts[-1][-1] != blank
            ):
                current_raw_parts[-1] += " "
                current_braille_parts[-1] += blank
                current_len += len(blank)

        if current_len == width:
            raw_lines.append(current_raw_parts)
            braille_lines.append(current_braille_parts)
            current_raw_parts = []
            current_braille_parts = []
            current_len = 0
            full_line_break = True

    if current_len > 0 or not braille_lines:
        current_raw_parts.append("")
        current_braille_parts.append(blank * (width - current_len))
        raw_lines.append(current_raw_parts)
        braille_lines.append(current_braille_parts)

    braille_lines_str = ["".join(item) for item in braille_lines]
    raw_lines_str = ["".join(item) for item in raw_lines]

    return "\n".join(braille_lines_str), "\n".join(raw_lines_str)
````

- [ ] **Step 3: `TranslationResult.wrap` delegates.**

File: `$T/step9_edit.py`

````python
"""P2-5 Task 9: TranslationResult.wrap delegates to conversion.line_wrap.

Run from client/. Exact replacements (each must match once); keeps tabs and CRLF.
"""
from pathlib import Path

path = Path("translate.py")
text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")

old_import = "from conversion import tokenizer\n"
new_import = "from conversion import tokenizer\nfrom conversion.line_wrap import wrap_tokens\n"
assert text.count(old_import) == 1
text = text.replace(old_import, new_import, 1)

start = text.index("\tdef wrap(self, width: int) -> tuple[str, str]:\n")
assert text.endswith('\t\treturn "\\n".join(braille_lines_str), "\\n".join(raw_lines_str)\n')
text = text[:start] + '''\tdef wrap(self, width: int) -> tuple[str, str]:
\t\treturn wrap_tokens(self.raw, self.braille, self.raw_to_braille_pos, width)
'''
path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
print("translate.py: line wrapper extracted")
````

```bash
$PY $T/step9_edit.py
$PY -m unittest tests.test_conversion_line_wrap tests.test_conversion_tokenizer tests.test_translation_result_core tests.test_translation_split_equivalence tests.test_translation_golden tests.test_translation_liblouis_golden tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
translate.py: line wrapper extracted
Ran 87 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1204 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/conversion/line_wrap.py client/tests/test_conversion_line_wrap.py client/translate.py
git -C $REPO commit -q -m "refactor: extract the line wrapper" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in conversion/line_wrap.py tests/test_conversion_line_wrap.py translate.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
204a689e26ddd79bdc44c6ddcc62b069e8f82384
0976c167614cd8ef76b043eacb7630b9092bde1b8c6d1186eb0a77c2c510bb53 *-
b31fbace90696345e1d04931462266361aa46b0275ceacad1e914ffc3126640b *-
5df64c12ceb20ca5e73e8170fe361b1d384872981aff5af99fd42b2349d25c5c *-
```

### Task 10: Move `TranslationResult` to `conversion.alignment` (D1, D2, D7)

- [ ] **Step 1: Red: the import guards and the re-export test.**

Edit: `client/tests/test_translation_import_isolation.py`

```python
    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
```

```python
    def test_production_modules_do_not_import_translate(self) -> None:
        found = []
        for path in sorted(CLIENT_DIR.rglob("*.py")):
            relative = path.relative_to(CLIENT_DIR)
            if {"tests", ".venv", "__pycache__"} & set(relative.parts) or relative.parts[:2] == ("braille", "liblouis"):
                continue
            if relative.as_posix() == "translate.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                if "translate" in names:
                    found.append(f"{relative.as_posix()}:{node.lineno}")

        self.assertEqual(found, [], "import TranslationResult from conversion.alignment")

    def test_alignment_modules_load_no_config_adapters_or_native_code(self) -> None:
        script = """
import sys
import conversion.alignment
import conversion.tokenizer
import conversion.line_wrap
import conversion.contracts
forbidden = ("config", "adapters", "braille", "wx", "dual_view", "libmathcat_py")
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
)
assert not loaded, f"loaded: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_tokenizer_and_line_wrap_do_not_import_alignment(self) -> None:
        script = """
import sys
import conversion.tokenizer
import conversion.line_wrap
loaded = sorted(name for name in sys.modules if name in {"conversion.alignment", "translate"})
assert not loaded, f"loaded: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
```

Edit: `client/tests/test_translation_result_core.py`

```python
        )


class SharedConstantsTest(unittest.TestCase):
```

```python
        )

    def test_translate_reexports_the_alignment_class(self) -> None:
        import conversion.alignment
        import translate

        self.assertIs(translate.TranslationResult, conversion.alignment.TranslationResult)
        self.assertEqual(TranslationResult.__module__, "conversion.alignment")
        self.assertEqual(translate.__all__, ["TranslationResult"])


class SharedConstantsTest(unittest.TestCase):
```

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_translation_result_core 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_translation_import_isolation 2>&1 | grep "^-  *\['\|^-  *'"
```

Expected:

```text
ERROR: test_translate_reexports_the_alignment_class (tests.test_translation_result_core.TranslationResultCoreTest.test_translate_reexports_the_alignment_class)
ModuleNotFoundError: No module named 'conversion.alignment'
FAIL: test_alignment_modules_load_no_config_adapters_or_native_code (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_alignment_modul
AssertionError: 1 != 0 : Traceback (most recent call last):
FAIL: test_production_modules_do_not_import_translate (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_production_modules_do_not_imp
AssertionError: Lists differ: ['adapters/translation/fallback.py:1', 'ad[172 chars]y:1'] != []
Ran 38 tests
FAILED (failures=2, errors=1)
- ['adapters/translation/fallback.py:1',
-  'adapters/translation/liblouis.py:6',
-  'adapters/translation/mathcat.py:5',
-  'conversion/contracts.py:6',
-  'conversion/preprocessing/literal_braille.py:1',
-  'conversion/wrapping.py:1'] : import TranslationResult from conversion.alignment
```

- [ ] **Step 2: Move the class** (mechanical: each leading tab becomes 4 spaces; `translate.py` becomes the re-export; the six production imports use `conversion.alignment`).

File: `$T/step10_move.py`

````python
"""P2-5 Task 10: move TranslationResult from translate.py to conversion/alignment.py.

Run from client/. Re-indents each leading tab to 4 spaces (whitespace-only lines become
empty), adds a module docstring, leaves translate.py as a re-export and points the six
production imports at conversion.alignment. Nothing else changes.
"""
from pathlib import Path

HEADER = (
    "from bisect import bisect_right\n"
    "\n"
    "from conversion import tokenizer\n"
    "from conversion.line_wrap import wrap_tokens\n"
    "from conversion.tokenizer import contracted_token_spans, iter_separator_positions, word_token_spans"
)
DOCSTRING = (
    '"""The TranslationResult value object: source tokens, braille cells and the two\n'
    "position maps between them, and the operations that keep the maps consistent.\n"
    '"""\n'
)

source = Path("translate.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
header_end = source.index("\n\n\ndef _is_well_formed_alignment(")
assert source[:header_end] == HEADER, source[:header_end]

lines = []
for line in source[header_end:].split("\n"):
    stripped = line.lstrip("\t")
    converted = "    " * (len(line) - len(stripped)) + stripped
    lines.append(converted if converted.strip() else "")
Path("conversion/alignment.py").write_text(DOCSTRING + HEADER + "\n".join(lines), encoding="utf-8", newline="\n")

Path("translate.py").write_text(
    'from conversion.alignment import TranslationResult\n\n__all__ = ["TranslationResult"]\n',
    encoding="utf-8",
    newline="\n",
)

old = b"from translate import TranslationResult"
new = b"from conversion.alignment import TranslationResult"
for name in (
    "adapters/translation/fallback.py",
    "adapters/translation/liblouis.py",
    "adapters/translation/mathcat.py",
    "conversion/contracts.py",
    "conversion/preprocessing/literal_braille.py",
    "conversion/wrapping.py",
):
    path = Path(name)
    data = path.read_bytes()
    assert data.count(old) == 1, name
    path.write_bytes(data.replace(old, new))
print("moved TranslationResult to conversion/alignment.py")
````

```bash
$PY $T/step10_move.py
grep -cP "\t| +$" conversion/alignment.py
$PY -m unittest tests.test_translation_import_isolation tests.test_translation_result_core tests.test_conversion_line_wrap tests.test_conversion_tokenizer tests.test_translation_split_equivalence tests.test_translation_golden tests.test_translation_liblouis_golden tests.test_translation_result 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (no tab and no trailing blank in `alignment.py`):

```text
moved TranslationResult to conversion/alignment.py
0
Ran 98 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1208 tests
FAILED (errors=1, skipped=5)
```

The resulting `client/translate.py`:

```python
from conversion.alignment import TranslationResult

__all__ = ["TranslationResult"]
```

- [ ] **Step 3: Commit.**

```bash
git -C $REPO add client/conversion/alignment.py client/translate.py client/adapters/translation/fallback.py client/adapters/translation/liblouis.py client/adapters/translation/mathcat.py client/conversion/contracts.py client/conversion/preprocessing/literal_braille.py client/conversion/wrapping.py client/tests/test_translation_import_isolation.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -m "refactor: move TranslationResult to conversion.alignment" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
for f in adapters/translation/fallback.py adapters/translation/liblouis.py adapters/translation/mathcat.py conversion/alignment.py conversion/contracts.py conversion/preprocessing/literal_braille.py conversion/wrapping.py tests/test_translation_import_isolation.py tests/test_translation_result_core.py translate.py; do git -C $REPO show HEAD:client/$f | sha256sum; done
```

Expected:

```text
ae851a78fd2f56882577bf992619717331b01f07
a6609d819a33afa736134f86a3fd10c053cffb3a9607de38ff44df7a43243771 *-
59361476a36d5cd63ba779fc43cbaacf3e180d06e8a98c99788809aa42aa4126 *-
6e7115078c07583df0264b4e9c490d633105d2fd66b5aeb7682a9382c50cc954 *-
701dc9718645df3ea383fce11382ecf5284d0573fc7b2e0ba252cd385c1dca08 *-
7f102e55f2f0882ef9146d4f2fa8069bfcf026fa4d645cd45528c52c9cc10672 *-
e1696009f5dcd23eef5542e09aac2fae4a577ad2eade18a229a0c045cb40826b *-
c18de6c7de0d663d4377d052b7b066067ce79e73d734b718a13a6468fb0da0fc *-
7cbc8be1d5bcb46de719066d4348fb11045dba6b3d67950a2e066d4d4c89dc59 *-
3f18632fd9f8436cf3c2c11ec17b56ec02a6c4479d2bee4f5464fb9eaecfd1f1 *-
b78a3e69d3e5e18281e9f5a1a51fac05b158905c749c593f250fd3be0250c80b *-
```

### Task 11: Verification (no commit)

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1208 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 2: Criterion 2, the P2-5 modules; the real golden runs all 13 tests.**

```bash
MODS="tests.test_translation_result tests.test_translation_result_core tests.test_translation_golden tests.test_translation_split_equivalence tests.test_translation_liblouis_golden tests.test_conversion_tokenizer tests.test_conversion_line_wrap tests.test_conversion_service tests.test_translation_import_isolation"
$PY -m unittest $MODS 2>&1 | $PY $T/tools/brief.py
$PY -m unittest $MODS -v 2>&1 | grep -c "test_translation_liblouis_golden.LiblouisGoldenTest.* ok$"
```

Expected:

```text
Ran 126 tests
OK
13
```

- [ ] **Step 3: Criterion 3, Windows-only modules unchanged.**

```bash
$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 7 tests
OK
```

- [ ] **Step 4: Criterion 4, fixtures.**

```bash
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
STEP3=$(git -C $REPO log --format=%H -1 --grep="^test: pin real liblouis output on Windows")
git -C $REPO diff $STEP3 HEAD --stat -- client/tests/fixtures/
```

Expected (no diff output):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
```

- [ ] **Step 5: Criterion 5, shuffled module order, seeds 0-19, one process each** (about 3 minutes).

```bash
for s in $(seq 0 19); do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
     20 ran=1208 failures=0 errors=1 skipped=5 ['test_case_only_rename_still_renames']
```

- [ ] **Step 6: Criteria 6 and 7, imports and untouched trees** (no output from any command).

```bash
git -C $REPO grep -nE "^[[:space:]]*(from translate import|import translate$)" -- client ':!client/tests' ':!client/translate.py'
git -C $REPO grep -n "adapters" -- client/conversion
git -C $REPO diff main --stat -- client/locales client/braille scripts client/dictionary client/tests/fixtures/translation_golden.json client/tests/fixtures/dictionary_entries_trace.json client/tests/test_translation_golden.py
```

- [ ] **Step 7: Criterion 8, mutation check of the split modules** (15 mutants, about 4 minutes).

```bash
$PY $T/tools/p25_mutants.py $REPO/client $T/mut post; echo "exit $?"
```

Expected:

```text
contracted-merges-on-less-or-equal: 1 caught: test_translation_split_equivalence.test_bind_contracted_tokens_matches_the_oracle
word-lead-drops-em-dash: 5 caught: test_conversion_tokenizer.test_an_em_dash_leads_the_next_word, test_conversion_tokenizer.test_hoisted_sets_keep_their_members, test_translation_liblouis_golden.test_punctuation, test_translation_split_equivalence.test_bind_word_tokens_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
word-trailing-span-ends-early: 20 caught: test_conversion_tokenizer.test_a_leading_punctuation_chain_joins_the_next_word, test_conversion_tokenizer.test_a_trailing_punctuation_chain_joins_the_previous_word, test_translation_golden.test_chinese_prose, test_translation_golden.test_english_math, test_translation_golden.test_escaped_dollar_fraction, test_translation_golden.test_long_document, test_translation_golden.test_spaced_math_punctuation, test_translation_liblouis_golden.test_en_prose, test_translation_liblouis_golden.test_ja_prose, test_translation_liblouis_golden.test_long_document, test_translation_liblouis_golden.test_math_mix, test_translation_liblouis_golden.test_numbers, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_punctuation, test_translation_liblouis_golden.test_zh_prose, test_translation_result.test_bind_word_tokens_complex, test_translation_result.test_bind_word_tokens_tail_punct, test_translation_result.test_bind_word_tokens_tail_punct_continue, test_translation_split_equivalence.test_bind_word_tokens_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
separator-only-before-full-width: 3 caught: test_conversion_tokenizer.test_a_separator_goes_between_closing_and_opening_marks, test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
regroup-maps-stray-cells-to-token-one: 3 caught: test_translation_split_equivalence.test_bind_contracted_tokens_matches_the_oracle, test_translation_split_equivalence.test_bind_word_tokens_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
insert-shifts-only-later-tokens: 3 caught: test_translation_split_equivalence.test_insert_token_matches_the_oracle, test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
well-formed-check-accepts-decreasing-starts: 4 caught: test_translation_result_core.test_malformed_alignment_uses_the_stepwise_trim, test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
well-formed-check-accepts-starts-past-the-end: 2 caught: test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
separator-fast-path-ignores-token-order: 2 caught: test_translation_split_equivalence.test_reclean_token_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
trim-may-empty-a-token: 18 caught: test_translation_golden.test_chinese_prose, test_translation_golden.test_dictionary_literal, test_translation_golden.test_english_math, test_translation_golden.test_escaped_dollar_fraction, test_translation_golden.test_long_document, test_translation_golden.test_spaced_math_punctuation, test_translation_liblouis_golden.test_en_prose, test_translation_liblouis_golden.test_ja_prose, test_translation_liblouis_golden.test_long_document, test_translation_liblouis_golden.test_math_mix, test_translation_liblouis_golden.test_numbers, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_punctuation, test_translation_liblouis_golden.test_spaced_math, test_translation_liblouis_golden.test_spaces_lines, test_translation_liblouis_golden.test_zh_prose, test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
trim-forgets-the-shift: 17 caught: test_translation_golden.test_chinese_prose, test_translation_golden.test_english_math, test_translation_golden.test_escaped_dollar_fraction, test_translation_golden.test_long_document, test_translation_golden.test_spaced_math_punctuation, test_translation_liblouis_golden.test_ja_prose, test_translation_liblouis_golden.test_long_document, test_translation_liblouis_golden.test_math_mix, test_translation_liblouis_golden.test_numbers, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_punctuation, test_translation_liblouis_golden.test_spaces_lines, test_translation_liblouis_golden.test_zh_prose, test_translation_result_core.test_trim_keeps_the_list_objects, test_translation_result_core.test_trimming_forty_thousand_tokens_takes_linear_time, test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
trim-replaces-the-lists: 3 caught: test_translation_result_core.test_trim_keeps_the_list_objects, test_translation_split_equivalence.test_reclean_braille_endspace_matches_the_oracle, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle
wrap-drops-leading-spaces: 8 caught: test_conversion_line_wrap.test_wrap_tokens_matches_the_pre_split_wrap, test_translation_golden.test_dictionary_literal, test_translation_golden.test_long_document, test_translation_liblouis_golden.test_p25_document_matches_the_recorded_brl, test_translation_liblouis_golden.test_spaces_lines, test_translation_result.test_remove_start_line_blank2, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle, test_translation_split_equivalence.test_wrap_matches_the_oracle
wrap-separates-after-half-width-marks: 3 caught: test_conversion_line_wrap.test_separator_and_space_sets, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle, test_translation_split_equivalence.test_wrap_matches_the_oracle
wrap-pads-after-a-full-line: 5 caught: test_conversion_line_wrap.test_wrap_tokens_matches_the_pre_split_wrap, test_translation_golden.test_dictionary_literal, test_translation_liblouis_golden.test_spaces_lines, test_translation_split_equivalence.test_whole_post_processing_matches_the_oracle, test_translation_split_equivalence.test_wrap_matches_the_oracle
exit 0
```

- [ ] **Step 8: msgids unchanged, and review the moved lines.**

```bash
$PY -I $T/tools/msgid_scan.py $REPO/client
$PY $T/tools/moved_lines.py | grep "^=="
```

Expected:

```text
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
== conversion/tokenizer.py: 179 lines, 30 not in translate.py@d4a7aa1
== conversion/line_wrap.py: 95 lines, 33 not in translate.py@d4a7aa1
== conversion/alignment.py: 292 lines, 112 not in translate.py@d4a7aa1
```

Then read the full `$PY $T/tools/moved_lines.py` output: every listed line must be one of the intended changes (module docstrings and imports, the hoisted constants, the span and position functions' signatures, returns and docstrings, the parameterized lines of `wrap_tokens`, `_is_well_formed_alignment`, the two fast paths and their comments, `_regroup`, `_reclean_braille_endspace_stepwise`'s header, the delegations).

- [ ] **Step 9: Windows verification 2, source-run baseline** (from the repo root).

```bash
cd $REPO
$PY $H/p25_baseline.py $T/p25out 2>&1 | grep -v "trimmed:"
cmp $T/p25out/p25_unicode.brl $H/baseline/p25_unicode.brl && cmp $T/p25out/p25_ascii.brl $H/baseline/p25_ascii.brl && echo "BRL identical"
cd $REPO/client
```

Expected:

```text
== A. liblouis one call vs split calls (zh-tw.ctb, mode=4)
' 的值': one='⠀⠙⠮⠁⠁⠱⠂' split='⠀⠙⠮⠁⠁⠱⠂' identical=True b2r=[0, 1, 1, 1, 2, 2, 2] r2b=[0, 1, 4]
'  中文': one='⠀⠀⠁⠯⠄⠿⠂' split='⠀⠀⠁⠯⠄⠿⠂' identical=True b2r=[0, 1, 2, 2, 2, 3, 3] r2b=[0, 1, 2, 5]
'計算 ': one='⠅⠡⠐⠑⠻⠐⠀' split='⠅⠡⠐⠑⠻⠐⠀' identical=True b2r=[0, 0, 0, 1, 1, 1, 2] r2b=[0, 3, 6]

== B. P2-5 failing-test input through the real pipeline
raw tokens: ['計', '算', ' ', '1+2', ' ', '的', '值']
braille: ⠅⠡⠐⠑⠻⠐⠀⠼⠁⠐⠖⠼⠃⠀⠙⠮⠁⠁⠱⠂

== C. long mixed document (p25_doc.txt, width 40)
mode=unicode sha256=365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c trims=13 cells_removed=13
mode=ascii sha256=95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64 trims=13 cells_removed=13
BRL identical
```

- [ ] **Step 10: Windows verification 3, performance** (timings vary; the bounds are what matters).

```bash
cd $REPO
$PY $H/p25_perf.py $T/p25out 100 400 1600
cd $REPO/client
$PY $T/tools/p25_separator_perf.py 200 800 3200
```

Expected in the dry run (bounds: `reclean` at 83,200 characters below 0.2 s, was 28.55 s; `wrap` below 2 s, was 28.92 s; `reclean_token` at 99,200 characters below 1 s, was 322 s):

```text
chars=   5200 translate=  0.40s wrap=  0.02s reclean=  0.00s
chars=  20800 translate=  1.01s wrap=  0.08s reclean=  0.01s
chars=  83200 translate=  4.19s wrap=  0.45s reclean=  0.06s
chars=6200 separators=600 reclean_token=0.01s
chars=24800 separators=2400 reclean_token=0.02s
chars=99200 separators=9600 reclean_token=0.08s
```

### Task 12: Packaged build (Windows verification 4; no commit)

- [ ] **Step 1: Build** (PowerShell, from the repo root; a few minutes).

```powershell
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
& .\scripts\build-dotexpress.bat
New-Item -ItemType Directory -Force D:\dxtest\P25 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\P25\DotExpress.exe
(Get-FileHash D:\dxtest\P25\DotExpress.exe).Hash
```

`client\build\`, `client\dist\` and `client\DotExpress.spec` are git-ignored; `git status --short` stays as in Task 0.

- [ ] **Step 2: Import, convert and export BRL through the real GUI** (`auto/item7.py`, with the pywinauto 0.6.9 + psutil venv; this session's is `$SP/uia`, otherwise create one with `python -m venv` and `pip install pywinauto==0.6.9 psutil`). The work directory must be new: `dx.launch` deletes it first.

```bash
$SP/uia/Scripts/python.exe $H/auto/item7.py 'D:\dxtest\P25\DotExpress.exe' 'D:\dxtest\auto7-p25' "$(cygpath -w $H/p25_doc.txt)"
sha256sum /d/dxtest/auto7-p25/p25_unicode.brl /d/dxtest/auto7-p25/p25_ascii.brl
cmp /d/dxtest/auto7-p25/p25_unicode.brl $H/baseline/p25_unicode.brl && cmp /d/dxtest/auto7-p25/p25_ascii.brl $H/baseline/p25_ascii.brl && echo "packaged BRL identical"
```

Expected:

```text
365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c */d/dxtest/auto7-p25/p25_unicode.brl
95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64 */d/dxtest/auto7-p25/p25_ascii.brl
packaged BRL identical
```

- [ ] **Step 3 (optional, spec item 5): Dual View HTML.** Export Dual View HTML for `p25_doc.txt` from `D:\dxtest\P25\DotExpress.exe` and from `D:\dxtest\N\DotExpress.exe` (the `main` build) with the same automation style and compare the bytes.

- [ ] **Step 4: Record the results** in the report to the user (counts, hashes, timings, any deviation). Do not mark manual items done that were not run.

## Appendix: Throwaway Tool Sources

`$T/tools/brief.py`:

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers, exception lines (cut to 160 characters, each printed
once), the "Ran" line without its timing and the final OK/FAILED line, so that outputs
can be compared with the plan. The client directory (also in its repr form with doubled
backslashes) is shown as <client>, measured seconds in a timing assertion as <seconds>.
"""
import re
import sys
from pathlib import Path

CLIENT = str(Path.cwd())
CLIENT_REPR = CLIENT.replace("\\", "\\\\")
seen = set()
for line in sys.stdin:
    line = line.rstrip("\n").replace(CLIENT_REPR, "<client>").replace(CLIENT, "<client>")
    line = re.sub(r"^AssertionError: [0-9.]+ not less than", "AssertionError: <seconds> not less than", line)
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception): ", line):
        if line not in seen:
            seen.add(line)
            print(line[:160])
    elif line.startswith("Ran "):
        print(re.sub(r" in [0-9.]+s$", "", line))
    elif line.startswith(("OK", "FAILED")):
        print(line)
````

`$T/tools/msgid_scan.py`:

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

`$T/tools/p25_mutants.py`:

````python
"""Run the P2-5 nets against deliberately broken code (throwaway, not committed).

Usage: python p25_mutants.py <client_dir> <scratch_dir> <pre|post> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/,
build/, dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run.
For each mutant it edits one production file of the copy (one exact, unique
replacement), runs the P2-5 test modules there, prints which tests caught it and
restores the file. The repository is never changed. "pre" mutants target
client/translate.py as it is after Task 4; "post" mutants target the split modules
after Task 10. Exit status 1 if a mutant is not caught or its pattern is not unique.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

PRE = {
    "contracted-merges-on-less-or-equal": ("translate.py", "and old_raw_to_braille[end] == old_raw_to_braille[start]", "and old_raw_to_braille[end] <= old_raw_to_braille[start]"),
    "word-lead-drops-em-dash": ("translate.py", 'LEAD_PUNCT = set(self.LEFT_PUNCT) | set("—")', "LEAD_PUNCT = set(self.LEFT_PUNCT)"),
    "insert-shifts-only-later-tokens": ("translate.py", "right = [(t + 1) if t >= idx else t for t in old_b2r[b_ins:]]", "right = [(t + 1) if t > idx else t for t in old_b2r[b_ins:]]"),
    "separator-only-before-full-width": ("translate.py", "(curr_first in self.LEFT_PUNCT)", "(curr_first in self.LEFT_PUNCT_FULL)"),
    "trim-may-empty-a-token": ("translate.py", "while new_end - start > 1 and self.braille[new_end - 1] == blank:", "while new_end - start > 0 and self.braille[new_end - 1] == blank:"),
    "wrap-drops-leading-spaces": ("translate.py", "if current_len == 0 and not line_start_blank:", "if current_len == 0:"),
}
POST = {
    "contracted-merges-on-less-or-equal": ("conversion/tokenizer.py", "and raw_to_braille_pos[end] == raw_to_braille_pos[start]", "and raw_to_braille_pos[end] <= raw_to_braille_pos[start]"),
    "word-lead-drops-em-dash": ("conversion/tokenizer.py", 'LEAD_PUNCT = LEFT_PUNCT | frozenset("—")', "LEAD_PUNCT = LEFT_PUNCT"),
    "word-trailing-span-ends-early": ("conversion/tokenizer.py", "trailing_end = token_char_spans[u][1]", "trailing_end = token_char_spans[u][0]"),
    "separator-only-before-full-width": ("conversion/tokenizer.py", "curr_tok[0] in LEFT_PUNCT:", "curr_tok[0] in LEFT_PUNCT_FULL:"),
    "regroup-maps-stray-cells-to-token-one": ("conversion/alignment.py", "            else 0\n", "            else 1\n"),
    "insert-shifts-only-later-tokens": ("conversion/alignment.py", "right = [(t + 1) if t >= idx else t for t in old_b2r[b_ins:]]", "right = [(t + 1) if t > idx else t for t in old_b2r[b_ins:]]"),
    "well-formed-check-accepts-decreasing-starts": ("conversion/alignment.py", "        if start < previous:\n", "        if False:\n"),
    "well-formed-check-accepts-starts-past-the-end": ("conversion/alignment.py", "    return previous <= len(braille)\n", "    return True\n"),
    "separator-fast-path-ignores-token-order": ("conversion/alignment.py", "token_idx + min(inserted, bisect_right(positions, token_idx))", "token_idx + inserted"),
    "trim-may-empty-a-token": ("conversion/alignment.py", "while new_end - start > 1 and braille[new_end - 1] == blank:", "while new_end - start > 0 and braille[new_end - 1] == blank:"),
    "trim-forgets-the-shift": ("conversion/alignment.py", "new_raw_to_braille_pos.append(start - removed)", "new_raw_to_braille_pos.append(start)"),
    "trim-replaces-the-lists": ("conversion/alignment.py", "braille[:] = new_braille", "self.braille = new_braille"),
    "wrap-drops-leading-spaces": ("conversion/line_wrap.py", "if current_len == 0 and not line_start_blank:", "if current_len == 0:"),
    "wrap-separates-after-half-width-marks": ("conversion/line_wrap.py", "SEPARATED_AFTER_PUNCT = RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL", 'SEPARATED_AFTER_PUNCT = RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL | frozenset(")]}")'),
    "wrap-pads-after-a-full-line": ("conversion/line_wrap.py", "or (current_len == 0 and not full_line_break):\n                current_raw_parts", "or current_len == 0:\n                current_raw_parts"),
}
MODULES = (
    "tests.test_translation_split_equivalence",
    "tests.test_translation_liblouis_golden",
    "tests.test_translation_golden",
    "tests.test_translation_result",
    "tests.test_translation_result_core",
    "tests.test_conversion_tokenizer",
    "tests.test_conversion_line_wrap",
)
IGNORE = shutil.ignore_patterns(".venv", "log", "dictionary", "workspace", "build", "dist", "config.json", "__pycache__")
FAILED = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", re.M)


def main() -> int:
    client_dir, scratch_dir, table_name, *selected = sys.argv[1:]
    table = {"pre": PRE, "post": POST}[table_name]
    copy = Path(scratch_dir) / "client"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(client_dir, copy, ignore=IGNORE)
    modules = [name for name in MODULES if (copy / (name.replace(".", "/") + ".py")).exists()]
    status = 0
    for mutant in selected or list(table):
        relative, old, new = table[mutant]
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
                [sys.executable, "-m", "unittest", *modules],
                cwd=copy, capture_output=True, text=True, encoding="utf-8",
            )
        finally:
            path.write_bytes(original)
        names = sorted({f"{where.split('.')[1]}.{test}" for test, where in FAILED.findall(completed.stderr)})
        print(f"{mutant}: {len(names)} caught: {', '.join(names) if names else 'NONE'}")
        if not names:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
````

`$T/tools/shuffle_harness.py`:

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

`$T/tools/moved_lines.py`:

````python
"""List the lines of the split modules that are not in translate.py at d4a7aa1 (throwaway).

Usage (from client/): python moved_lines.py
Compares stripped, non-blank lines (indentation ignored, so tabs vs 4 spaces do not
matter) of conversion/alignment.py, conversion/tokenizer.py and conversion/line_wrap.py
with client/translate.py at d4a7aa1 and prints every line of the new modules that the
old file does not contain, per module. The reviewer checks that each printed line is
one of the changes the plan intends (new helpers, delegation, the linear paths,
module constants, comments and docstrings).
"""
import subprocess

old = subprocess.run(
    ["git", "show", "d4a7aa1:client/translate.py"], check=True, capture_output=True, encoding="utf-8"
).stdout
old_lines = {line.strip() for line in old.splitlines() if line.strip()}
for name in ("conversion/tokenizer.py", "conversion/line_wrap.py", "conversion/alignment.py"):
    with open(name, encoding="utf-8") as handle:
        new_lines = [line.strip() for line in handle if line.strip()]
    added = [line for line in new_lines if line not in old_lines]
    print(f"== {name}: {len(new_lines)} lines, {len(added)} not in translate.py@d4a7aa1")
    for line in added:
        print(f"  {line}")
````

`$T/tools/p25_separator_perf.py`:

````python
"""Time reclean_token on dialogue-heavy real zh-tw.ctb output (throwaway, Windows).

Usage (from client/): python p25_separator_perf.py 200 800 3200
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from braille import louis_helper  # noqa: F401  load the bundled DLL first
from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
from conversion import wrapping
from conversion.service import translate_with_language_segments

PARAGRAPH = "他說：「你好嗎？」「我很好，謝謝。」（甲）（乙）大家都笑了。\n"

runtime = build_default_translation_runtime()
try:
    for repeat in (int(arg) for arg in sys.argv[1:]):
        text = PARAGRAPH * repeat
        segments = translate_with_language_segments(
            text, Path("no-such-dir/default.csv"), dict(DEFAULT_TRANSLATION_TABLES), Path("data/Bopomofo2Braille.csv"),
            runtime=runtime, lang="zh_TW", charset_maps=dict(DEFAULT_CHARSET_MAPS),
        )
        merged = wrapping.merge_translation_results(segments)
        merged.reclean_braille_endspace()
        merged.bind_word_tokens()
        before = len(merged.raw)
        started = time.perf_counter()
        merged.reclean_token()
        elapsed = time.perf_counter() - started
        print(f"chars={len(text)} separators={len(merged.raw) - before} reclean_token={elapsed:.2f}s")
finally:
    runtime.close()
````
