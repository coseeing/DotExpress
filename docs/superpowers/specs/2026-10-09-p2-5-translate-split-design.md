# translate.py Split (P2-5) Design

## Goal

Roadmap task P2-5 (`docs/superpowers/history/2026-10-09-02-handoff/refactor-review.md` section 6.3, finding S-2, the rest of D-3) splits `client/translate.py` into three modules with one job each:

- `client/conversion/tokenizer.py`: how source characters are grouped into tokens (punctuation classes, contracted-token spans, word-token spans, where a separator space goes between a closing and an opening punctuation mark).
- `client/conversion/line_wrap.py`: how tokens are laid out on lines of a given width.
- `client/conversion/alignment.py`: the `TranslationResult` value object (source tokens, braille cells and the two position maps) and the operations that keep the maps consistent (merge, regroup, insert, trim).

`client/translate.py` stays as a one-line re-export so existing imports keep working. `conversion/wrapping.py` keeps its two functions and signatures.

In the same task, on the same branch:

1. **The failing test** `test_translate_with_language_does_not_duplicate_existing_spaces_around_math` is resolved as the user decided: the assertion compares the joined source text and the joined braille, and a new characterization test pins that the leading space of a text segment is its own token and its own dual-view segment.
2. **`reclean_braille_endspace` becomes linear** (P1-5 known defect 3). Output must be byte-identical.
3. **Prerequisites** (HANDOFF section 4.3): `tests/test_translation_result.py` is converted to `unittest` and its 5 failures are adjudicated (verdicts below: all five are fixture defects, none is a production bug); `adapters/translation/contracts.py` moves its ports into `conversion/contracts.py` and `adapters` joins `HIGHER_LAYERS` (P2 review M-1).
4. **Safety net before any production change**: the existing fake-helper golden stays byte-identical; a frozen copy of today's `translate.py` serves as a test oracle for randomized equivalence tests (runs everywhere); a new Windows-only golden pins real liblouis and MathCAT output (Chinese, English UEB grade 1 and 2, Japanese, math, punctuation, widths 1-40) and the recorded `p25_*.brl` hashes, and skips where liblouis is absent.
5. **Proposed addition (decided: included, see Open Questions):** `reclean_token` becomes linear too. Found while writing this spec: on dialogue-heavy Chinese text it is quadratic and much slower than the trim (322 s for 99,200 characters with 9,600 separators, real liblouis). Byte-identical, same safety net, its own commit, droppable without touching the other steps.

This is a behavior-preserving refactor except for the test expectation in item 1, which pins today's behavior. For any input the braille text (Unicode and ASCII), the BRL bytes, the source-text wrap, every alignment list and every dual-view segment and HTML are byte-identical to `main` at `d4a7aa1`. No user-facing string changes; no `.po`/`.mo` change.

Corrected after planning: the plan `docs/superpowers/plans/2026-10-09-p2-5-translate-split.md` (section "Spec Corrections and Refinements") fixed three facts (the oracle cannot be a byte copy and carry a header; the language-blocks patch target must move when the tokenizer is extracted, not at the class move; the separator timing test size) and refined the safety net, two implementation details and the counts. The section "Corrected after planning" below lists every change against the first version (commit `079d58b`); where a later section disagrees with that list, the list wins.

## Corrected after planning (2026-10-09)

1. **Q1 and Q2 are decided** (orchestrator, 2026-10-09): Q1 yes, migration step 7 (D6, linear `reclean_token`) is part of P2-5. Q2 is out of scope: P2-5 only pins today's behavior; the mid-word break with UEB grade 2 stays a known pre-existing defect (Known Defects 1) for a later user decision.
2. **The oracle is header + marker + verbatim copy (D11.2).** `tests/legacy_translation_result.py` is a five-line comment header ending with the marker line `# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----`, followed by the exact bytes of `git show d4a7aa1:client/translate.py`. The oracle test LF-normalizes the file and checks that the part after the marker has the blob id `10bd641485327b00cb71a14d4946f01a1788f794` (a byte copy with a header would have a different blob id).
3. **The `build_language_blocks` patch target moves in step 8, not step 10 (D7, Test Plan F).** Once the tokenizer owns the constants, `translate.py` no longer imports `build_language_blocks`, so `patch("translate.build_language_blocks")` raises `AttributeError`; step 8 changes it to `conversion.tokenizer.build_language_blocks`.
4. **Separator timing test: 10,000 separators (Test Plan E).** The old `reclean_token` takes 19 s for 10,000 `」「` pairs on the Windows machine and would take more than a minute for 20,000; the test is `test_inserting_ten_thousand_separators_takes_linear_time` (bound 2 s; linear 0.01 s). The trim test keeps 40,000 tokens (old code 42 s there, not 37 s; linear 0.02 s).
5. **Real golden shape (D11.3).** 17 cases: the 8 inputs for each table set and one long document (the `p25_perf.py` paragraph x 400, width 40) with the default tables only, since it is Chinese only. Per case: the input's sha256, the display text per run (digest only for the long document), the post-processed tokens (digest for the long document), the digests of the merged lists, the post-processed lists and the dual-view segments, and the segment count. The fixture is about 34 KB; the module runs in 1.7 s after step 6 (4.9 s before). A liblouis version other than the recorded `3.37.0` makes `setUpClass` raise an `AssertionError` that says to regenerate only for an intended upgrade. The runtime comes from `create_default_text_translator()` and `create_default_math_translator()` directly and is closed by a class cleanup.
6. **Equivalence tests (D11.2)** also compare which of the four attributes still hold the original list objects ("mutates in place or replaces"). Half of the `reclean_token` cases and half of the whole-chain cases use a separator-dense unit alphabet (with the general one, fewer than 100 of 4,000 well-formed cases had a separator and none had two). 4,000 cases per operation, 2,000 chains; the module runs in 1.3 s.
7. **The fast trim does not run the final clamp loop (D5).** On the fast path no start can exceed the new length, so it is skipped (a comment says why); the stepwise fallback keeps it.
8. **Separator positions are taken eagerly (D6).** `reclean_token` computes `list(iter_separator_positions(...))` before choosing a path. The positions depend only on the original tokens and computing them cannot raise for string tokens, so the one-by-one fallback still raises at the same insertion.
9. **Moved code keeps its comments (D1).** The moved bodies keep their Chinese comments verbatim; the `bind_word_tokens` docstring stays on the method. `line_wrap.py` drops the two commented-out lines at the end of `wrap` and adds the English branch comments D4 allows.
10. **Fixture defects (D10).** `test_bind_word_tokens_complex` also has a short map (96 characters, 94 cells and positions); it passes because the regroup never reads past position 82 and stays as written.
11. **Guards (Test Plan F).** `test_tokenizer_and_line_wrap_do_not_import_alignment` passes when it is added (a guard, not a red test). Until step 10, `conversion/contracts.py` imports `TranslationResult` from `translate`.
12. **Windows verification 4.** `D:\dxtest\N` holds only `DotExpress.exe`; the packaged outputs are compared with `docs/superpowers/history/2026-10-09-03-windows-verification/baseline/p25_*.brl`, which N and B matched byte for byte.
13. **Counts.** After step 10: `Ran 1208`, `FAILED (errors=1, skipped=5)` on Windows (F-W6 only). Per commit: 1157, 1158, 1171, 1179, 1180, 1183, 1186, 1200, 1204, 1208. The real-golden module has 13 tests; the equivalence module 8; the tokenizer module 14; the line-wrap module 4.
14. **The packaged build keeps the `translate` shim (D7; added after the P2-5 review, finding I-1).** Once no production module imports `translate`, PyInstaller leaves it out of the exe, and a user preprocessing script that imports it would fail only in the packaged app. `scripts/build-dotexpress.bat` passes `--hidden-import translate` (the git-ignored `client/DotExpress.spec` it regenerates then lists `hiddenimports=['translate']`), and `test_packaged_build_keeps_the_translate_shim` checks the batch file. This is the only `scripts/` and packaging change; it overrides those words in "What Stays Identical" and acceptance criterion 7.

## Open Questions for the User (decided 2026-10-09, see above)

- **Q1. Make `reclean_token` linear in P2-5 (D6)?** Not in the brief, but the same kind of fix as the decided trim and on the same code path. **Decided: yes**, migration step 7.
- **Q2 (finding, not part of P2-5).** With English set to UEB grade 2, every word that contains a part-word contraction is cut into several tokens (`brown` -> `br`, `ow`, `n`; see Known Defects 1 for the full extent), so the line wrapper can break a word in the middle without a hyphen: at width 8, `The quick br` / `own fox`. Grade 1 (the default) is not affected. Fixing it changes braille layout, so it is a user decision and a separate task. **Decided: out of scope**; P2-5 pins today's behavior in the Windows golden, and the defect stays open for a later user decision (Known Defects 1).

## Inputs Already Decided

- The failing test is resolved in P2-5 by relaxing the assertion to the joined raw/braille text and adding a characterization test that pins the space as its own segment. Evidence: `docs/superpowers/history/2026-10-09-03-windows-verification/results.md` section 3 A-B (real liblouis gives raw `['計','算',' ','1+2',' ','的','值']`; `" 的值"` translated in one call and in two calls gives identical cells).
- `reclean_braille_endspace` is made linear with byte-identical output (results.md section 3 C-D: 13 trims in `p25_doc.txt`; 28.55 s of 28.92 s wrap time for 83,200 characters, versus 4.17 s of translation).
- Real liblouis is reached only through `braille.louis_helper` (results.md F-W1, W-1 guard).

## Current State (verified 2026-10-09 on `main` `d4a7aa1`)

### `client/translate.py` (537 lines, tabs)

| Lines | Member | Role |
| --- | --- | --- |
| 11-14 | `_CJK_LANGUAGE_BLOCKS` | read-only CJK block table (P1-5) |
| 17-35 | class attributes | 12 punctuation `frozenset`s, `lang_blocks`, `__hash__ = None` |
| 37-70 | `__init__`, `concat`, `__add__`, `__eq__` | value object and linear merge (P1-5) |
| 72-114 | `bind_contracted_tokens` | merge source characters that share one braille start (called by the liblouis adapter) |
| 116-317 | `bind_word_tokens` | three passes over the units (ASCII runs, CJK singles, trailing-punctuation chains, leading-punctuation chains), then rebuild both maps at token level |
| 319-367 | `insert_token` | insert one token and its cells, rebuild all four lists |
| 369-391 | `reclean_token` | insert `" "` + blank cell between a token ending in `RIGHT_PUNCT` and one starting with `LEFT_PUNCT` |
| 393-444 | `reclean_braille_endspace` | trim trailing blank cells of every token (keep at least one cell) |
| 446-537 | `wrap` | lay tokens out on lines of `width` cells, return `(braille, source)` |

`bind_word_tokens` builds `ASCII_ALNUM`, `TRAIL_PUNCT` and `LEAD_PUNCT` on every call; `wrap` builds `RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL` and `set(" ")` on every token.

Callers: `conversion/wrapping.py` (`concat`, then `reclean_braille_endspace`, `bind_word_tokens`, `reclean_token`, `wrap` as methods), `adapters/translation/liblouis.py` (`bind_contracted_tokens`). Constructors: the liblouis, MathCAT and fallback adapters, `conversion/preprocessing/literal_braille.py`. Type users: `adapters/translation/contracts.py`. No production code reads the punctuation sets or `lang_blocks` outside `translate.py`. The Windows history scripts `p25_baseline.py` and `p25_perf.py` import `translate` and monkeypatch `TranslationResult.reclean_braille_endspace` to count trims and time them.

The raw-text half of `wrap`'s result is never shown: `conversion/output.py:80` discards it (`_text_wrapped`). Only the golden test records it. The braille half is what users see and export.

### Import graph today

`conversion/{jobs,output,service,text/pipeline}.py`, `gui.py` and `ui/conversion_presenter.py` import `TranslationRuntime` from `adapters.translation.contracts` (P2 review M-1: `conversion` depends on `adapters`). `adapters/translation/contracts.py` holds `RuntimeUnavailableError` (raised and caught only by `adapters/translation/provider.py`), the two translator `Protocol`s and the `TranslationRuntime` dataclass, and imports `translate`. `tests/test_translation_import_isolation.py:8` `HIGHER_LAYERS` does not contain `adapters`, so the AST guard does not see the reverse edge.

### Test safety net today

- Full suite on this machine (`cd client && .venv/Scripts/python.exe -m unittest discover -s tests`): `Ran 1143`, `failures=1` (the P2-5 test), `errors=1` (`test_case_only_rename_still_renames`, F-W6, out of scope), `skipped=5` (platform skips).
- `tests/test_translation_golden.py` + `fixtures/translation_golden.json`: fake liblouis helper, 5 short inputs x 5 runs + a 360-segment document. Covers Chinese, English with contractions, math, full-width pairs, literal braille, widths 1/10/24/40. No Japanese, no Korean, no em-dash, no half-width bracket chains next to words. Fixture sha256 (`git show HEAD:<path> | sha256sum`, because `core.autocrlf=true`): `translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.
- `tests/test_translation_result_core.py`: 21 tests (value object, merge, constants). `test_construction_does_not_build_language_blocks` patches `translate.build_language_blocks`.
- `tests/test_translation_result.py`: 13 pytest-style functions, `NO TESTS RAN` under `unittest`; called directly 8 pass, 5 fail (next section).
- Windows-only, real liblouis: `test_translation_language_result.py` (1 test), `test_language_detection_translation.py` (1), `test_liblouis_runtime.py` (5). None pins wrap or token output for realistic text.

### The 5 failures of `test_translation_result.py`

Probed by calling each function directly and then with corrected fixtures (scratch scripts, not committed).

| Test | Failure | Cause | Verdict |
| --- | --- | --- | --- |
| `test_bind_word_tokens_lead_punct` | `IndexError` at `translate.py:297` (`old_r2b[c_start]`) | fixture has 5 source characters but 4 cells and 4 `raw_to_braille_pos` entries | **fixture defect.** No producer builds such a result (liblouis returns one input position per character; MathCAT, literal braille and the fallback build equal lengths; `concat` and the regroups preserve them). With 5 cells and 5 positions the code returns exactly the expected `['「嶼', '我', '共', '視']`. |
| `test_bind_word_tokens_lead_punct_continue` | same `IndexError` | 6 characters, 5 cells and positions | **fixture defect**, same reasoning; with 6/6 the expected `['「「嶼', '我', '共', '視']` is returned. |
| `test_end_right_end_sentence_blank2` | missing `" "` after `」` before the hard newline | every braille cell in the fixture is `BLANK`; `wrap` adds the separator after full-width closing or sentence-ending punctuation only when the token's braille does not already end in a blank cell (`translate.py:509-515`) | **fixture defect.** With non-blank cells the code returns exactly the expected string. |
| `test_end_right_end_sentence_blank3` | missing `" "` between `」` and `『` | same all-`BLANK` fixture | **fixture defect**; with non-blank cells the expected `"「嶼我」 『共視』"` is returned. |
| `test_remove_start_line_blank` | `"...an \nI see"` instead of `"...an\nI see"` | the first token has 39 characters and is given 39 cells, so the space token fits at the end of line 1 (39 + 1 = 40) and never reaches the start of line 2 | **fixture defect** (arithmetic). With 40 cells for the first token the space starts line 2, is dropped, and the expected string is returned. The as-written case is correct behavior (a space that fits at the line end stays there). |

Consequence for the passing `test_end_right_end_sentence_blank`: it also uses all-`BLANK` cells, so it pins the "token already ends in a blank cell, add nothing" branch. It stays as it is, documented as such; `..._blank2` with non-blank cells pins the other branch. The two expectations are consistent once the fixtures say what they test.

### Performance

- `reclean_braille_endspace` deletes from the middle of two lists and shifts every later `raw_to_braille_pos` entry per trimmed token: O(trims x length). Windows: 83,200 characters of real `zh-tw.ctb` output, 28.55 s (results.md section 3 D); worst case 10,000 trims 2.3 s.
- **New finding:** `reclean_token` calls `insert_token` per separator, and `insert_token` rebuilds all four lists: O(separators x length). Real liblouis, text `他說：「你好嗎？」「我很好，謝謝。」（甲）（乙）大家都笑了。` repeated: 6,200 characters (600 separators) 0.35 s, 24,800 (2,400) 11.6 s, 99,200 (9,600) 322 s. Dialogue (`」「`) and enumerations (`）（`) make this realistic for novels and textbooks.
- Prototypes of both linear versions (scratch only): trim 0.053 s and whole wrap 0.50 s for the 83,200-character case; 48,000 separators 0.064 s. Both matched the frozen code on the fake golden, on the `p25` BRL bytes, on the dialogue text at widths 1/7/10/24/40, and on 30,000 + 40,000 random cases including malformed alignments. On every real output observed the alignment is well formed (fast path), never the fallback.

## Design

### D1. Module layout and dependencies

```
conversion/tokenizer.py   -> languageDetection.unicode_blocks, string, types
conversion/line_wrap.py   -> conversion.tokenizer (constants only)
conversion/alignment.py   -> conversion.tokenizer, conversion.line_wrap
conversion/contracts.py   -> conversion.alignment
translate.py              -> conversion.alignment            (re-export only)
```

No cycle; `tokenizer` and `line_wrap` never import `alignment`. None of them imports `config`, `braille`, `adapters`, `wx` or `dual_view`. New files use 4 spaces, like the rest of `conversion/`; moved bodies are re-indented from tabs mechanically and otherwise unchanged except where this section says so.

The module is named `tokenizer`, not the roadmap's `tokenize`: a file named like the standard library's `tokenize` breaks `traceback`/`linecache` whenever `conversion/` lands on `sys.path` (for example `python conversion/line_wrap.py`).

### D2. `TranslationResult` keeps its whole method API

`TranslationResult` (in `conversion/alignment.py`) keeps `__init__`, `concat`, `__add__`, `__eq__`, `__hash__ = None`, the 12 punctuation class attributes and `lang_blocks` (the same objects as the tokenizer's constants), and the methods `bind_contracted_tokens`, `bind_word_tokens`, `insert_token`, `reclean_token`, `reclean_braille_endspace` and `wrap` with unchanged signatures, return values and mutation behavior. The tokenizing and wrapping methods become thin delegates. `conversion/wrapping.py` keeps calling them as methods.

Reasons: every caller, test and the two Windows history scripts (which monkeypatch `TranslationResult.reclean_braille_endspace` and are rerun for verification) keep working unchanged; the class stays the single place that mutates the four lists.

### D3. `conversion/tokenizer.py`

- Constants: the 12 punctuation `frozenset`s (same names and members as today), `CJK_LANGUAGE_BLOCKS` (today's `_CJK_LANGUAGE_BLOCKS`), and the per-call sets hoisted to module level with the same members: `ASCII_ALNUM = frozenset(string.ascii_letters + string.digits)`, `TRAIL_PUNCT = RIGHT_PUNCT | MIDDLE_SENTENCE_PUNCT | END_SENTENCE_PUNCT`, `LEAD_PUNCT = LEFT_PUNCT | frozenset("—")`.
- `is_cjk_word_char(ch, lang_blocks) -> bool`: today's nested function.
- `contracted_token_spans(raw_to_braille_pos) -> list[tuple[int, int]]`: the span loop of `bind_contracted_tokens` (lines 85-97).
- `word_token_spans(units, lang_blocks=CJK_LANGUAGE_BLOCKS) -> list[tuple[int, int]]`: passes 1-3 of `bind_word_tokens` (lines 159-285), returning the final spans. The token text of a span is always `"".join(units[start:end])`: pass 1 joins runs or takes one unit, passes 2 and 3 only concatenate adjacent tokens in order.
- `iter_separator_positions(tokens)`: a generator over today's pair check (`prev and curr and prev[-1] in RIGHT_PUNCT and curr[0] in LEFT_PUNCT`), yielding each index `i` (`1 <= i < len(tokens)`) before which `reclean_token` inserts a separator. Today's loop skips the inserted token, so it checks exactly the original adjacent pairs, each once, in order; the generator does the same.

Pure functions, no `TranslationResult` import. `language_has_all` building a set per call (P1-5 known defect 4) is out of scope.

### D4. `conversion/line_wrap.py`

`wrap_tokens(tokens, braille, raw_to_braille_pos, width) -> tuple[str, str]`: the body of `wrap` with `self.raw`, `self.braille`, `self.raw_to_braille_pos` replaced by the parameters, `self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL` replaced by the module constant `SEPARATED_AFTER_PUNCT` and `set(" ")` by `SPACE_ONLY = frozenset(" ")` (identical membership). Reads its inputs, never mutates them. The only other change allowed: parentheses that make the existing `and`/`or` precedence explicit in the two conditions of the hard-newline branch, and English comments that explain the branches (including why the second condition differs from the first). `TranslationResult.wrap(width)` returns `wrap_tokens(self.raw, self.braille, self.raw_to_braille_pos, width)`.

### D5. `conversion/alignment.py`

- `TranslationResult` as in D2, moved from `translate.py`.
- `_regroup(spans)` (private method): `raw = ["".join(old_raw[s:e]) ...]`, `raw_to_braille_pos = [old_r2b[s] ...]`, `braille_to_raw_pos = [char_to_token[c] if 0 <= c < len(old_raw) else 0 for c in old_b2r]`. Both regroups today use exactly these expressions (lines 99-114 and 296-317), including the `IndexError` when `raw_to_braille_pos` is shorter than the spans need.
- `bind_contracted_tokens`: unchanged guard (`if not self.raw or len(self.raw) != len(self.raw_to_braille_pos): return`), then `self._regroup(contracted_token_spans(self.raw_to_braille_pos))`.
- `bind_word_tokens`: computes `word_token_spans(self.raw, self.lang_blocks)` first, then today's guard (`not r2b or not raw or len(b2r) != len(braille)`: return), then `_regroup`. Same order as today. `self.lang_blocks` is still read through the instance.
- `insert_token`: body unchanged.
- `reclean_braille_endspace` (linear, item 2):
  - Same early returns as today (empty `raw`/`braille`, empty maps).
  - **Fast path** when the alignment is well formed: `len(raw_to_braille_pos) == len(raw)`, `len(braille_to_raw_pos) == len(braille)`, and `0 <= raw_to_braille_pos[0] <= ... <= raw_to_braille_pos[-1] <= len(braille)`. One pass over the tokens with a running count `removed` of deleted cells: for token `t` with original span `[start, end)` (`end` is the next start or `len(braille)`), the new start is `start - removed`; the kept cells are `braille[start:new_end]` where `new_end` drops trailing blank cells while more than one cell remains; cells before the first start are kept. The three lists are replaced in place with slice assignment (`lst[:] = new`), so they stay the same objects, as with today's `del`.
  - Why it is identical: today's loop shifts every later start by the same amount, so at token `t` both its start and its end are the original values minus the cells removed so far; with non-decreasing starts every earlier deletion lies before the current start, so the current cells are the original cells at the same offset. Hence the same tokens are trimmed by the same amounts. The final clamp loop cannot fire on this path (the removals after token `t` fit inside `[start_t, len)`), so the fast path skips it (Corrected after planning 7); the fallback keeps it.
  - **Fallback**: any other alignment runs today's loop unchanged (private `_reclean_braille_endspace_stepwise`). Non-monotonic or mismatched maps make deletions overlap later spans, which only a step-by-step simulation reproduces; they never occur in real output, so the fallback costs nothing in practice and keeps byte identity for every input, including the same exceptions.
- `reclean_token` (D6).

### D6. `reclean_token` in one pass (proposed, Q1)

Without D6, `reclean_token` loops `for offset, index in enumerate(iter_separator_positions(list(self.raw))): self.insert_token(index + offset, " ", blank)`, which is today's loop restated (positions read from a snapshot of the original tokens, lazily, so any exception happens at the same pair).

With D6, when there is at least one separator and the alignment is well formed (same test as the trim), the four lists are rebuilt once. For separator positions `i_0 < ... < i_{k-1}` (original token indices):

- `raw`: `" "` before each original token `i_m`.
- `raw_to_braille_pos`: original token `j` starts at `r2b[j] + #{m : i_m <= j}`; separator `m` starts at `r2b[i_m] + m`.
- `braille`: one blank cell before original cell `r2b[i_m]` for each `m`, in order (cells at the same position keep separator order; positions equal to `len(braille)` append at the end).
- `braille_to_raw_pos`: separator cell `m` maps to `i_m + m`; an original cell at position `b` with value `t` maps to `t + min(#{m : r2b[i_m] <= b}, #{m : i_m <= t})`.

Why it is identical: separator `m` is inserted at token index `i_m + m` and cell `r2b[i_m] + m`; with non-decreasing starts an original cell is at or after that cell exactly when `b >= r2b[i_m]`; today's update adds one to a value `v` at step `m` only if the cell is at or after the insertion and `v >= i_m + m`, and once that comparison fails it keeps failing (its margin drops by at least one per step), which gives the `min`. With no separator nothing changes (same list objects, as today); with at least one, all four lists are new objects, as today (`insert_token` rebinds them). Malformed alignments use the loop above.

### D7. `translate.py` becomes a re-export

```python
from conversion.alignment import TranslationResult

__all__ = ["TranslationResult"]
```

Kept for tests, the Windows history scripts and anything outside the repository that imports `translate`, including user preprocessing scripts, which `conversion/preprocessing/user_script.py` runs inside the packaged app. No production module imports it, so PyInstaller would leave it out of the frozen build; `scripts/build-dotexpress.bat` passes `--hidden-import translate` to keep it there (Corrected after planning 14). Production modules import `conversion.alignment` (adapters, `conversion/wrapping.py`, `conversion/preprocessing/literal_braille.py`, `conversion/contracts.py`); a guard keeps it that way. `test_import_does_not_import_liblouis_helper` still holds (`translate` has `TranslationResult`, no `translate`, no `translate_as_single_token`, loads no native module). `SharedConstantsTest.test_construction_does_not_build_language_blocks` patches `conversion.tokenizer.build_language_blocks` instead of `translate.build_language_blocks` (the attribute no longer exists on the shim).

### D8. Contracts move into `conversion` (P2 review M-1)

- New `conversion/contracts.py` (4 spaces): `BrailleTextTranslator`, `MathSegmentTranslator` and `TranslationRuntime`, moved verbatim; it imports `TranslationResult` from `conversion.alignment`.
- `adapters/translation/contracts.py` keeps `RuntimeUnavailableError` (an adapter concern: only `provider.py` raises and catches it) and re-exports the three ports from `conversion.contracts`, so `adapters.translation` and every test that imports from there keep working with the same objects.
- `conversion/{jobs,output,service,text/pipeline}.py`, `gui.py` and `ui/conversion_presenter.py` import `TranslationRuntime` from `conversion.contracts`.
- `tests/test_translation_import_isolation.py`: `HIGHER_LAYERS` gains `"adapters"`. Direction afterwards: `adapters -> conversion` only. The ports belong to the consumer, which is the usual place for a `Protocol`.
- Rejected alternative: documenting `adapters.translation.contracts` as part of `conversion`. After D7 the adapters import `conversion.alignment`, so the package graph would become `adapters <-> conversion`.

### D9. The failing test (decided)

`tests/test_conversion_service.py`:

- `test_translate_with_language_does_not_duplicate_existing_spaces_around_math` keeps its name and input and asserts `"".join(result.raw) == "計算 1+2 的值"` and `"".join(result.braille) == "T[計算 ]M[1+2]⠀T[的值]"` (the fake translates a lone `" "` to one blank cell). Each space of the source appears once in the text and maps to exactly one place in the braille: no space is duplicated.
- New `test_leading_space_of_a_text_segment_is_its_own_token_and_segment`: same input; `result.raw == ["計算 ", "1+2", " ", "的值"]`; the text translator is called with `"計算 "`, `" "`, `"的值"` in that order; the dual-view segments are `[("text", ["計算 "]), ("math", ["1+2"]), ("text", [" "]), ("text", ["的值"])]` as `(source_kind, raw)`.
- Windows golden (D11) pins the same shape with real liblouis: merged raw `['計','算',' ','1+2',' ','的','值']`, braille `⠅⠡⠐⠑⠻⠐⠀⠼⠁⠐⠖⠼⠃⠀⠙⠮⠁⠁⠱⠂`, segments `text ['計','算',' ']`, `math ['1+2']`, `text [' ']`, `text ['的','值']`; and `zh-tw.ctb` gives identical cells for `" 的值"`, `"  中文"`, `"計算 "` in one call and split as in results.md section 3 A.

The only visible effect of the split (an extra whitespace-only dual-view segment) is accepted as today's behavior.

### D10. `test_translation_result.py` becomes `unittest`

Same file, tabs kept, classes `BindContractedTokensTest`, `BindWordTokensTest`, `RecleanTokenTest`, `WrapTest`. All 13 functions become methods with unchanged names and expectations; the five fixtures are corrected as in the verdict table (5/5 and 6/6 cells and positions; non-blank cells `⠁` for `..._blank2` and `..._blank3`; 46 cells and `[0, 40, 41]` for `test_remove_start_line_blank`), each with a one-line comment saying why. `test_end_right_end_sentence_blank` stays as written with a docstring saying it pins the blank-cell branch. One new test, `test_space_that_fits_at_the_line_end_stays_there`, pins the original `test_remove_start_line_blank` fixture and today's result `"...an \nI see"`. All 14 pass on unchanged code.

### D11. Safety net

1. **Fake golden unchanged.** `tests/test_translation_golden.py` and its fixture are not edited at all; the fixture sha256 stays `e67d95a1…211ccd` at every commit.
2. **Frozen oracle + equivalence tests (all platforms).** `tests/legacy_translation_result.py` is a byte copy of `client/translate.py` at `d4a7aa1` (git blob `10bd641485327b00cb71a14d4946f01a1788f794`) with a header comment saying it is the pre-split reference and must never change. `tests/test_translation_split_equivalence.py` (4 spaces) checks the copy's git blob id (LF-normalized, so `autocrlf` does not matter), then runs seeded random cases through the oracle and through the production class from identical starting states and compares the four lists, return values, and the type and message of any exception, for: `bind_contracted_tokens`, `bind_word_tokens`, `insert_token` (random index), `reclean_token`, `reclean_braille_endspace`, `wrap` (widths 1-45), and the whole chain `concat` -> trim -> `bind_word_tokens` -> `reclean_token` -> `wrap` on 1-3 results. Generator: units drawn from ASCII letters and digits (single and runs), multi-character units (`the`, `1+2`, `台灣`), Han, kana, Hangul, Bopomofo, every member of the 12 punctuation sets and `—`, `" "`, `"　"`, `"\n"`, rarely `""`; 0-4 cells per unit from blank and two non-blank cells; well-formed maps most of the time, and in a fixed share of cases shuffled, too long, too short or out-of-range maps and arbitrary `braille_to_raw_pos` values (so the fallbacks run). Fixed seeds; the case counts are chosen so that the module runs in under 3 s. Limit (P2-5 review M-2): the oracle freezes only `translate.py`; it imports the current `languageDetection.unicode_blocks` (`build_language_blocks`, `language_has_all`), so a later change there changes the oracle and production together and the equivalence tests cannot see it. Only the fake and real goldens would.
3. **Windows real-liblouis golden.** `tests/test_translation_liblouis_golden.py` (4 spaces) with `tests/fixtures/translation_liblouis_golden.json`:
   - Skip rule: module-level `SkipTest` when `ctypes` has no `WINFUNCTYPE` or `from braille import louis_helper` fails (the W-1 pattern; no direct `braille.liblouis` import). `setUpClass` builds `TranslationRuntime` from `create_default_text_translator()` and `create_default_math_translator()` and raises `SkipTest` with the reason if either raises `RuntimeUnavailableError` (no silent fallback to the character fallback). Linux and CI skip; this Windows machine must run it (acceptance criterion).
   - Settings: a temporary directory with no dictionary file (no rules, no preprocessing script), `lang="zh_TW"`, `DEFAULT_CHARSET_MAPS`, two table sets: `DEFAULT_TRANSLATION_TABLES` and the same with `"en": "en-ueb-g2.ctb"`.
   - Inputs: `zh_prose` (Chinese with an English word, `，`, `；`, `。`), `en_prose` (`The quick brown fox ... rests. Testing, (one) [two]!`), `ja_prose` (kanji, hiragana, katakana, `：`, `。`), `math_mix` (fraction, sum, Chinese and English), `spaced_math` (`計算 $1+2$ 的值`), `punctuation` (`「」（）（甲）（乙）『』——`, ASCII quotes, `、`, `[a] {b}`), `spaces_lines` (leading spaces, trailing spaces, full-width space, newlines), `numbers` (`1,234`, `USD 40`, `2026/10/09`, `（）`). Runs: Unicode at widths 1, 10, 24, 40 and ASCII at 40, per table set.
   - Stored per input and table set: `display_text` per run in full; the post-processed tokens (after trim, `bind_word_tokens`, `reclean_token`) in full; the SHA-256 of the canonical JSON of the merged lists, of the post-processed lists and of the dual-view segments (read after the wrap). A long case (the `p25_perf.py` paragraph x 400, width 40) stores only digests. The fixture records `louis_helper.louis.version()` (`3.37.0`); a different version fails first with a message saying to regenerate only for an intended liblouis upgrade. Measured on the prototype: 96 entries, about 15 KB, 0.4 s, identical in two processes.
   - Written once, on unchanged production code, with `python -m tests.test_translation_liblouis_golden --write` from `client/` on Windows; never regenerated by this task.
   - Fixed tests in the same module: `test_p25_document_matches_the_recorded_brl` (the bytes of `tests/fixtures/p25_doc.txt`, a copy of the history document, read with `read_text(encoding="utf-8")`; Unicode and ASCII at width 40 with default tables; BRL bytes = `display_text` with `\r\n` line ends, UTF-8; sha256 `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c` and `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64` from results.md section 3 C, written into the test, not the fixture; the test also checks the document's text sha256 so a changed copy is caught), `test_one_call_equals_split_calls` and `test_leading_space_is_its_own_token_with_real_liblouis` (D9).

## What Stays Identical (behavior invariants)

- Braille output in Unicode and ASCII mode, the BRL and every other export, the source-text wrap, the merged and post-processed alignment lists, every dual-view segment and the dual-view HTML (window and export), for any input, table set and width.
- The exceptions raised for malformed alignments (same type and message, same point), because malformed input takes the original code paths.
- `TranslationResult`'s attributes, constants (same members, still `frozenset`s, `lang_blocks` still a read-only mapping), methods, signatures, return values and which lists a method mutates in place or replaces.
- `conversion.wrapping.merge_translation_results` / `wrap_translation_results`, `conversion.service.*`, `conversion.output.*` signatures and behavior; the `adapters.translation` package exports.
- `client/tests/fixtures/translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd` and `client/tests/fixtures/dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`).
- The recorded BRL hashes: Unicode `365d28a9…f9d683c`, ASCII `95b9a1a6…2538bc64`, from source runs and from the packaged build.
- No string, menu, dialog, `.po`/`.mo`, `client/braille/`, `client/locales/`, `scripts/` or packaging change. `client/dictionary/` is never read or written by any test.

## Migration Steps (one branch `refactor/p2-5-translate-split`; each step one green commit)

Steps 1-4 change tests only and are made on unchanged production code; steps 5-10 change production code, red first.

1. `test: run test_translation_result under unittest` (D10). 14 tests, all green.
2. `test: pin the leading space of a text segment` (D9 Linux part). The known failure turns green; full suite: only the F-W6 error left on Windows.
3. `test: pin real liblouis output on Windows` (D11.3). Fixture written here, on Windows, from unchanged code.
4. `test: add the pre-split oracle and equivalence tests` (D11.2). Green by construction; a throwaway mutation check (plan) shows each equivalence test fails for a deliberate in-memory change of the corresponding production method.
5. `refactor: move the translation ports into conversion` (D8). Red: `"adapters"` added to `HIGHER_LAYERS` lists the four `conversion` imports.
6. `perf: trim trailing blank cells in one pass` (D5, item 2). Red: the timing test.
7. `perf: insert punctuation separators in one pass` (D6). Red: the timing test. **Q1 decided yes: included.**
8. `refactor: extract the tokenizer` (D3). Red: `tests/test_conversion_tokenizer.py` (`ModuleNotFoundError`).
9. `refactor: extract the line wrapper` (D4). Red: `tests/test_conversion_line_wrap.py`.
10. `refactor: move TranslationResult to conversion.alignment` (D1, D2, D7). Red: the import guards of part F.

Steps 6 and 7 change `translate.py` in place; step 10 moves the result. Each step keeps the fake golden, the equivalence tests and (on Windows) the real golden green. Every commit message ends with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Test Plan

All tests are `unittest`; new files use 4 spaces, edited files keep their indentation.

### A. Converted tests (step 1)

`tests/test_translation_result.py` per D10: 14 tests.

### B. Failing test resolution (step 2)

`tests/test_conversion_service.py`: the relaxed test and `test_leading_space_of_a_text_segment_is_its_own_token_and_segment` (D9). +1 test.

### C. Windows real-liblouis golden (step 3)

`tests/test_translation_liblouis_golden.py` per D11.3: one test per input (8, table sets and runs as subtests), `test_long_document`, `test_fixture_covers_every_case`, `test_p25_document_matches_the_recorded_brl`, `test_one_call_equals_split_calls`, `test_leading_space_is_its_own_token_with_real_liblouis`. 13 tests on Windows; one module skip elsewhere.

### D. Equivalence (step 4)

`tests/test_translation_split_equivalence.py` per D11.2: `test_oracle_is_the_pre_split_translate_py` plus one test per operation (6) and `test_whole_post_processing_matches_the_oracle`. 8 tests.

### E. Performance guards (steps 6, 7) in `tests/test_translation_result_core.py`

- `LinearTrimTest`: `test_trimming_forty_thousand_tokens_takes_linear_time` (each token one non-blank and one blank cell; result equals a reference computed by plain slicing; bound 2 s; prototype 0.015 s, today about 37 s here), `test_trim_keeps_the_list_objects` (identity of the three lists before and after), `test_malformed_alignment_uses_the_stepwise_trim` (patch the private fallback with a wrapper: called for a shuffled map, not called for a well-formed one).
- `LinearSeparatorTest` (Q1 = yes): `test_inserting_ten_thousand_separators_takes_linear_time` (`」「` pairs, 10,000 separators, see Corrected after planning 4; reference built independently; bound 2 s), `test_well_formed_alignment_never_calls_insert_token` (`insert_token` patched with `side_effect=AssertionError`), `test_malformed_alignment_inserts_one_by_one`.

The timing bounds are backstops; the structural tests and part D are the binding checks.

### F. Structure guards (steps 5, 8-10)

- `tests/test_translation_import_isolation.py`: `HIGHER_LAYERS` with `"adapters"` (step 5); `test_adapter_contracts_reexport_the_conversion_ports` (the three names are the same objects; `RuntimeUnavailableError` is defined in adapters) (step 5); `test_production_modules_do_not_import_translate` (AST over `client/**/*.py` except `tests/`, `.venv/`, `translate.py`) (step 10); `test_alignment_modules_load_no_config_adapters_or_native_code` (subprocess: `import conversion.alignment, conversion.tokenizer, conversion.line_wrap, conversion.contracts` loads no `config`, `adapters*`, `braille*`, `wx*`, `dual_view*`, `libmathcat_py`) (step 10); `test_tokenizer_and_line_wrap_do_not_import_alignment` (subprocess) (step 10).
- `tests/test_conversion_tokenizer.py` (step 8): contracted spans; word spans for an ASCII run, a CJK single, a newline, a trailing chain (`視。」`), a leading chain (`「「嶼`), a leading mark next to a space or newline staying alone, the em-dash; separator positions on `」「`, `）（`, empty tokens; the constants are the objects `TranslationResult` exposes.
- `tests/test_conversion_line_wrap.py` (step 9): `wrap_tokens` equals `TranslationResult.wrap` on the `WrapTest` fixtures and does not mutate its inputs.
- `tests/test_translation_result_core.py`: the patch target of `test_construction_does_not_build_language_blocks` moves to `conversion.tokenizer.build_language_blocks` (step 10); `test_translate_reexports_the_alignment_class` (`translate.TranslationResult is conversion.alignment.TranslationResult`) (step 10).

### Expected counts (Windows, plan to confirm)

Baseline `Ran 1143`, `failures=1, errors=1, skipped=5`. After step 10 with Q1 = yes, about 1200 tests: `failures=0`, `errors=1` (F-W6 only), `skipped=5`. On Linux the real-liblouis module adds one module-level skip.

## Acceptance Criteria

Run from `client/` with `$PY = .venv/Scripts/python.exe` and `PYTHONIOENCODING=utf-8`.

1. `$PY -m unittest discover -s tests`: no failure; the only error is `test_case_only_rename_still_renames` (F-W6).
2. Roadmap command, corrected: `$PY -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_translation_golden tests.test_translation_split_equivalence tests.test_translation_liblouis_golden tests.test_conversion_tokenizer tests.test_conversion_line_wrap tests.test_conversion_service tests.test_translation_import_isolation -v` passes, and on this Windows machine `tests.test_translation_liblouis_golden` reports its 13 tests as run, none skipped.
3. Windows-only modules: `$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v` gives the same results as before the task.
4. `git show HEAD:client/tests/fixtures/translation_golden.json | sha256sum` and the same for `dictionary_entries_trace.json` print the two values above; `git diff <step-3 commit> HEAD -- client/tests/fixtures/translation_liblouis_golden.json` is empty.
5. Seeded module-order shuffle of the full suite, seeds 0-19 (a scratch harness as in earlier phases): every seed has the same counts and only the F-W6 error.
6. `git grep -nE "^[[:space:]]*(from translate import|import translate$)" -- client ':!client/tests' ':!client/translate.py'` prints nothing; `git grep -n "adapters" -- client/conversion` prints nothing.
7. `git diff main --stat -- client/locales client/braille scripts client/dictionary` is empty.
8. Mutation check (plan): each operation's equivalence test and the real golden catch a deliberate change of that operation; the timing tests fail on the pre-change code.

## Windows Verification (automatable; run after implementation)

From the repo root, on the finished branch. `$PY = client\.venv\Scripts\python.exe`; `$H = docs\superpowers\history\2026-10-09-03-windows-verification`.

1. Source-run tests: acceptance criteria 1-3 (the real golden runs, not skips).
2. Source-run baseline: `$PY $H\p25_baseline.py <out>`. Expected: section A `identical=True` three times; section B raw `['計', '算', ' ', '1+2', ' ', '的', '值']` and the braille above; section C sha256 `365d28a9…` (unicode) and `95b9a1a6…` (ascii), `trims=13 cells_removed=13` in both modes; `fc /b <out>\p25_unicode.brl $H\baseline\p25_unicode.brl` and the same for ASCII: no differences. (The script's monkeypatch of `translate.TranslationResult.reclean_braille_endspace` still works because of D2 and D7.)
3. Performance: `$PY $H\p25_perf.py <out> 100 400 1600`. Expected: `reclean` at 83,200 characters below 0.2 s (was 28.55 s; prototype 0.053 s), `wrap` below 2 s (was 28.92 s). With Q1 = yes, also time `reclean_token` on the dialogue paragraph of section "Performance" x 3,200 (a small script in the plan): below 1 s (was 322 s).
4. Packaged build: `scripts\build-dotexpress.bat`, copy `client\dist\DotExpress.exe` to a fresh folder, and run `$H\auto\item7.py <exe> <work dir> $H\p25_doc.txt` from the pywinauto venv (as in `auto-results.md`). Expected: `p25_unicode.brl` sha256 `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c`, `p25_ascii.brl` `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64`, and byte-identical to `D:\dxtest\N`'s outputs.
5. Optional, same automation style: export Dual View HTML for `p25_doc.txt` from the new build and from the `main` build and compare bytes (the fake golden already pins the HTML; this adds real MathCAT/MathML).

No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run.

## Risks

- **Hidden output drift in the move** (high impact, low likelihood). Mitigation: three independent nets (fake golden, oracle equivalence with malformed cases, real Windows golden plus the BRL hashes), and the move happens after the perf steps so each diff is small.
- **The linear algorithms differ on some input** (high impact, low likelihood). Mitigation: fast path only on a checked well-formed alignment, original code otherwise; proof sketches in D5/D6; random equivalence including malformed maps and arbitrary `braille_to_raw_pos` values; the prototypes already matched 70,000 random cases and all real outputs.
- **Re-indentation mistakes** (medium, low). Mitigation: the equivalence tests exercise every moved branch; the plan adds a whitespace-insensitive comparison of moved bodies against `d4a7aa1`.
- **Real golden depends on the liblouis build** (low). It records the version and fails with a clear message after an upgrade; regenerating it is then the documented step, like the AGENTS.md liblouis upgrade checklist.
- **`StubScope` eviction creating a second `TranslationResult` class** (low). Same situation as `translate` today: a module is evicted only if first imported inside a scope, together with everything that imported it there. Criterion 5 covers it.
- **Timing guards on slow machines** (low). Bounds are about 100 times the prototype time and far below the old time.

## Known Defects Found (not fixed here)

1. UEB grade 2 words with contractions can be broken across lines (Q2). Pre-existing, unchanged by P2-5 and pinned by the real golden (`ueb_g2/en_prose` tokens `br`, `ow`, `n`); fixing it changes braille layout and waits for a user decision in a separate task. Extent (P2-5 review M-8): every word that contains a part-word contraction is cut, not only `brown`; in `ueb_g2/en_prose` `brown`, `over`, `then`, `rests.` and `Testing,` become `br`, `ow`, `n`; `ov`, `er`; `the`, `n`; `re`, `st`, `s.`; `Te`, `st`, `ing,` (whole-word contractions such as `the` and `and` stay whole), and trailing punctuation stays with the last piece (`s.`, `ing,`). Likely cause (reasoned from the code, not verified by a fix): `bind_contracted_tokens` turns the characters that share one braille start into one multi-character unit, and pass 1 of `word_token_spans` joins only single-character `ASCII_ALNUM` units, so the pieces of the word are never joined again.
2. `wrap` raises `IndexError` on an empty source token (`token[-1]`), and `bind_word_tokens` on a `raw_to_braille_pos` shorter than `raw`. No producer creates either; kept as is and covered by the equivalence tests.
3. `language_has_all` builds a set per character (P1-5 known defect 4).
4. Root `AGENTS.md` "Key Modules" still describes the old top-level layout (`translate.py`, `utils.py`, ...).

## Out of Scope

- Any change to tokenization or wrap rules, including Q2 and merging consecutive text dual-view segments.
- `LanguageDetector` per-segment construction and the pipeline's function-local imports (P1-6 defect 3).
- Splitting `bind_word_tokens` further, typing `DualViewSegment.result`, P2-8 indentation of other files.
