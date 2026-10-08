# Explicit Conversion Language (P1-1) Design

## Goal

Stop the conversion stack from reading the conversion language and the charset-to-language map from the global `config` module. The UI layer (`BrailleFrame`, or `main.py` for the CLI demo) reads both values, puts them on the `ConversionRequest`, and every layer below receives them as arguments. This is roadmap task P1-1 in `storage/refactor.md` (section 6.2), covering finding D-1 (section 3.5, DIP).

Concretely:

- `ConversionRequest` gains `lang` and `charset_maps`.
- `LanguageDetector` takes `default_lang` and `charset_maps` in its constructor.
- `MathCATAdapter.get_braille_for_mathml(..., language=...)` takes the language explicitly, and so does the math translation chain that calls it.
- `braille/tables/__init__.py` `getDefaultTableForCurLang` takes `lang`.
- `conversion/text/pipeline.py`, `languageDetection/__init__.py`, `conversion/mathcat_adapter.py` and `braille/tables/__init__.py` no longer import `config`.

This is a behavior-preserving refactor. For the same `config.json`, `TEXT2BRAILLE_LANG` value and input text, the app produces the same braille as before. No user-facing string changes.

## Current State (verified 2026-10-08 on `refactor/p1-1-explicit-language`, HEAD `7f0d127`, P0-1..P0-6 merged)

Indentation: `languageDetection/__init__.py`, `conversion/mathcat_adapter.py`, `conversion/math_service.py`, `braille/tables/__init__.py` and `gui.py` use tabs. `conversion/text/pipeline.py`, `conversion/output.py`, `conversion/service.py`, `adapters/translation/*.py`, `main.py` and most tests use 4 spaces. The Windows-only tests `test_language_detection_translation.py` and `test_translation_language_result.py` use tabs.

### How the values are produced (`client/config.py`)

- `get_lang()` (line 141) returns, in order: `_runtime_lang` (set only by `set_lang`), the `TEXT2BRAILLE_LANG` environment variable, the top-level `"language"` key of `config.json`, else `"zh_TW"`. It reads `config.json` on every call. The value is returned as stored (`"zh_TW"`, `"zh-TW"` and `"en"` are all possible).
- `get_charset_maps()` (line 152) reads `language_detection.charset_maps` from `config.json` on every call and merges it over `DEFAULT_CHARSET_MAPS`. The three keys (`latinCharactersLanguage`, `CJKCharactersLanguage`, `arabicCharactersLanguage`) are always present in the result.
- `set_lang()` (line 160) has no production caller. Only `tests/test_mathcat_adapter.py` uses it.
- Nothing in the UI writes `"language"` or `charset_maps`. The settings dialog (`settings/dialogs.py`) has no language control; its only language-related controls are the per-language translation tables, which already travel on `ConversionRequest.translation_tables`. So the two values change mid-session only if someone hand-edits `config.json` (or a test calls `set_lang`). `TEXT2BRAILLE_LANG` is read from the process environment and never changes inside the app.

### Every read of the language or charset map (`grep -rn "get_lang\|get_charset_maps\|TEXT2BRAILLE_LANG\|set_lang" client --include=*.py`)

| Location | Read | When it is evaluated |
| --- | --- | --- |
| `conversion/text/pipeline.py:4, 64` | `config.get_lang().replace("-", "_").split("_", 1)[0]` picks the starting translation table. | Once per plain-text segment, on the worker thread. |
| `languageDetection/__init__.py:6, 183` | `defaultLang = config.get_lang()` in `add_detected_language_commands`. | When the generator starts, once per segment. |
| `languageDetection/__init__.py:340` | `config.get_charset_maps()[configKey]` in `find_language_for_charset`. | Every time a character switches into a Latin or CJK Unified Ideographs block that the current language does not cover. Each call re-reads `config.json`. |
| `languageDetection/__init__.py:349, 357` | `pref = config.get_lang()` inside a `try/except Exception` in `_preferred_full_lang` (docstring mentions it too). | On every language switch. |
| `conversion/mathcat_adapter.py:9, 72` | `get_lang().replace("_", "-").lower()` in `_configure_runtime`, then `SetPreference("Language", ...)` and the speech-style lookup. Line 9 also imports `DEFAULT_MATH_BRAILLE_TABLE` and `MATH_BRAILLE_TABLES` from `config`. | Every math segment, on the worker thread (Windows only; MathCAT is not loaded elsewhere). |
| `braille/tables/__init__.py:25, 117` | `config.get_lang()` in `getDefaultTableForCurLang`. | Never: the function has no caller in the repository. The `import config` at line 25 still runs whenever `braille.tables` is imported (settings dialog, liblouis provider). |
| `client_init.py:14, 149` | `get_lang` as the locale provider for server init. | Out of scope (D-1 calls it legitimate). Unchanged. |
| `tests/test_language_detection_char_langinfo.py:18-49`, `tests/test_conversion_text_pipeline.py:141`, `tests/test_mathcat_adapter.py:48-53` | Patch `languageDetection.config.*`, `conversion.text.pipeline.config.get_lang`, or call `config.set_lang`. | Tests. |

Consequences today:

- One conversion can read `config.json` many times and could, in theory, mix two languages if the file changes mid-job.
- `ConversionRequest` (`conversion/output.py:12-18`) is not self-contained: the same request yields different braille under a different `TEXT2BRAILLE_LANG` or `config.json`.
- Tests that do not patch the global (for example `tests/test_language_detection_unicode_braille.py` and most of `tests/test_conversion_service.py`) depend on the developer's real environment and `config.json`.

### Call chains that need the values

- **Text:** `gui._build_conversion_request` (`gui.py:697-705`) or `main.run_demo` (`main.py:19-29`) -> `ConversionRequest` -> `ConversionJobRunner` (worker thread) -> `conversion.service.convert_text_with_alignment` -> `conversion.output.convert_text_with_alignment` -> `translate_segments(...)` (`output.py:63`) -> `service.translate_with_language_dual_view_segments` -> `pipeline.translate_plain_text_segment` -> `LanguageDetector`.
- **Math:** `service.translate_with_language_dual_view_segments` -> `runtime.math_translator.translate(source, braille_code=...)` (`service.py:63`) -> `MathCATMathTranslator.translate` (`adapters/translation/mathcat.py:12`) -> `math_service.translate_math_segment` -> `mathml_to_nemeth_braille` -> `MathCATAdapter.get_braille_for_mathml`. `FallbackMathTranslator` (`adapters/translation/fallback.py:30`) implements the same protocol (`MathSegmentTranslator` in `adapters/translation/contracts.py:25`).
- Also calling `translate_with_language*`: `tests/test_conversion_service.py` (about 10 calls) and the Windows-only `tests/test_translation_language_result.py`. That Windows-only test already passes an extra positional argument (`"zh-tw.ctb"`) that the current signature does not accept, so it raises `TypeError` today.
- `LanguageDetector(...)` is constructed in `pipeline.py:61` and in tests only. `ConversionRequest(...)` is constructed in `gui.py:698`, `main.py:19` and tests (`test_conversion_service.py` x8, `test_conversion_text_pipeline.py`, `test_conversion_jobs.py`).
- `dual_view/model.py` uses only `latex_to_mathml` (no language). `documents/` exports go through `BrailleFrame._start_conversion`, so they use the same request builder.

### Files that must not be edited

`braille/tables/__tables.py` and `braille/liblouis/` are NVDA-derived or vendored. `scripts/sync-nvda.py` writes only under `vendor/nvda/`; it does not regenerate `client/braille/tables/__init__.py`, so that first-party glue file can be edited.

### Baseline

- Full suite at HEAD `7f0d127` (Linux venv): 554 tests, `failures=1` (the known P2-5 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`), `skipped=7`.
- On Linux, the roadmap's focused command aborts at load time: `tests.test_language_detection_translation` raises `unittest.SkipTest` at import and loading it by name stops the run. Linux verification must leave out the two Windows-only modules (see Acceptance Criteria).

## Design

### Values and names

| Layer | Name | Type | Meaning |
| --- | --- | --- | --- |
| `ConversionRequest` | `lang` | `str` | The raw value `config.get_lang()` returned, unnormalized (`"zh_TW"`, `"zh-TW"`, `"en"`, ...). |
| `ConversionRequest` | `charset_maps` | `dict[str, str]` | The full merged map `config.get_charset_maps()` returned. |
| text pipeline, service functions | `lang`, `charset_maps` | same | Passed through unchanged. |
| `LanguageDetector` | `default_lang`, `charset_maps` | same | Same values. |
| math chain | `language` | `str` | Same raw value as `lang`. |

The raw value is passed down unchanged and each consumer normalizes it exactly as it does today (pipeline: `replace("-", "_").split("_", 1)[0]`; MathCAT: `replace("_", "-").lower()`; detector: uses it as is). Normalizing once at the top would be cleaner, but it could change detector output for a `"zh-TW"`-style value, so it is out of scope.

All new parameters are **required** (no default). A default would be a hidden fallback language, which is exactly what D-1 removes. Every caller is in this repository and is updated in the same change.

### Where the values are read, and when

`BrailleFrame._build_conversion_request` reads both values **once per conversion request**, on the UI thread, and puts them on the request:

```python
return ConversionRequest(
	...,
	translation_tables=self.translation_tables.copy(),
	lang=get_lang(),
	charset_maps=get_charset_maps(),
)
```

`gui.py` adds `get_charset_maps` and `get_lang` to its existing `from config import (...)` block.

Why per request and not once at frame start-up:

- **It preserves current behavior exactly.** Today a hand-edit of `config.json` (`"language"` or `charset_maps`) while the app is running affects the next conversion. Reading once at start-up would quietly require a restart. The roadmap phrase "BrailleFrame reads it once and passes it in" is satisfied: there is one read point per conversion, in `BrailleFrame`, instead of many scattered reads on the worker thread.
- **Settings propagation needs no new code.** The settings dialog has no language control. Translation-table changes already reach the next request through `self.translation_tables` (P0-2). If a language control is added later, the next request picks it up automatically, because the request builder reads the current value.
- **Cost is negligible:** two small JSON reads per conversion on the UI thread, instead of (today) one or more per segment and per language switch on the worker thread.
- `TEXT2BRAILLE_LANG` keeps its meaning and precedence because `config.get_lang()` itself is unchanged.

`get_charset_maps()` returns a new dict on every call, so each request owns its own map and nothing aliases frame or config state.

`main.run_demo` (CLI demo) does the same: it calls `get_lang()` and `get_charset_maps()` once while building its request. `main.py` adds both to its existing `config` import.

### Threading

The request is a frozen dataclass built on the UI thread. The worker thread only reads `request.lang` and `request.charset_maps`. A settings change or a `config.json` edit during a running job does not affect that job, which is stricter than today (today a mid-job edit can change later segments of the same job). `LanguageDetector` copies `charset_maps` with `dict(...)` so it never shares the request's dict. Nothing below the request mutates either value.

The shared `MathCATAdapter` already re-applies all preferences (including `Language`) on every call, so passing the language per call keeps that guarantee.

### `ConversionRequest` (`conversion/output.py`)

```python
@dataclass(frozen=True)
class ConversionRequest:
    raw_text: str
    output_mode: str
    width: int
    dictionary_path: Path
    data_dir: Path
    translation_tables: dict[str, str]
    lang: str
    charset_maps: dict[str, str]
```

`convert_text_with_alignment` passes them on as keywords:

```python
translations = translate_segments(
    text,
    request.dictionary_path,
    request.translation_tables,
    request.data_dir / "Bopomofo2Braille.csv",
    runtime=runtime,
    lang=request.lang,
    charset_maps=request.charset_maps,
)
```

`output.py` still does not import `config`.

### Service functions (`conversion/service.py`)

Add keyword-only `lang: str, charset_maps: dict[str, str]` after `runtime` to `translate_with_language_dual_view_segments`, `translate_with_language_segments`, `translate_with_language` and the inner `translate_segments_with_dual_view` closure in `convert_text_with_alignment`. They forward the values:

- to `_translate_plain_text_segment(..., runtime=runtime, lang=lang, charset_maps=charset_maps)`;
- to `runtime.math_translator.translate(segment["text"], braille_code=math_braille_code, language=lang)`.

The boundary-space translation (`runtime.text_translator.translate(" ", table=default_table, ...)`) does not use the language and is unchanged. `service.py` keeps `from config import DEFAULT_MATH_BRAILLE_TABLE` (not part of this task).

### Text pipeline (`conversion/text/pipeline.py`)

```python
def translate_plain_text_segment(
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
    lang: str,
    charset_maps: dict[str, str],
):
    ...
    language_detector = LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)
    sequence = list(language_detector.add_detected_language_commands([text]))

    default_lang = lang.replace("-", "_").split("_", 1)[0]
```

Remove `import config` (line 4). Nothing else in the function changes.

### `LanguageDetector` (`languageDetection/__init__.py`)

```python
def __init__(self, availableLanguages, *, default_lang: str, charset_maps: Mapping[str, str], char_langinfo=None):
	self.default_lang = default_lang
	self.charset_maps = dict(charset_maps)
	...
```

- `add_detected_language_commands`: `defaultLang = self.default_lang`. Keep the NVDA-style commented-out `# defaultLang = getSynth().language` line.
- `find_language_for_charset`: `lang = self.charset_maps.get(configKey)`; return it if it is truthy, else fall through to `return langs[0]`. Today `config.get_charset_maps()` always contains every key, so `[configKey]` never raises. With an injected map, a caller could pass a partial map. Falling through to the existing "no configured language" path is the natural meaning of a missing entry and avoids a `KeyError` deep inside detection. Production behavior does not change, because the app always passes the full merged map.
- `_preferred_full_lang`: step 2 uses `pref = self.default_lang` and drops the `try/except Exception` (it guarded config file I/O, which no longer happens here). Update the docstring line that names `config.get_lang()`.
- Remove `import config` (line 6). The NVDA comment `# import config` at line 10 may stay; acceptance checks look only at real import statements.
- Keep the rest as is: camelCase names, NVDA comments and the algorithm (refactor.md section 7, item 1). Add `Mapping` to the `typing` import.

`default_lang` and `charset_maps` are keyword-only, so the existing positional `availableLanguages` and the optional `char_langinfo` keep their meaning.

### Math chain

- `adapters/translation/contracts.py`: `MathSegmentTranslator.translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult`.
- `adapters/translation/fallback.py`: `FallbackMathTranslator.translate(self, source, *, braille_code, language)`. It ignores `language`, as it already ignores `braille_code`.
- `adapters/translation/mathcat.py`: `MathCATMathTranslator.translate(self, source, *, braille_code, language)` calls `self._translate_math(source, braille_code=braille_code, language=language)`.
- `conversion/math_service.py`:
  - `mathml_to_nemeth_braille(mathml_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language: str)` calls `get_shared_mathcat_adapter().get_braille_for_mathml(mathml_text, braille_code=braille_code, language=language)`.
  - `translate_math_segment(latex_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language: str)` forwards `language`. The log message and `MathConversionError` wrapping stay unchanged.
  - `math_service.py` keeps `from config import DEFAULT_MATH_BRAILLE_TABLE`. It is not one of the four modules this task cleans.
- `conversion/mathcat_adapter.py`:
  - `get_braille_for_mathml(self, mathml_text: str, braille_code: str | None = None, *, language: str) -> str` calls `self._configure_runtime(libmathcat, braille_code, language)`.
  - `_configure_runtime(self, libmathcat, braille_code: str | None, language: str)` starts with `mathcat_language = language.replace("_", "-").lower()` and otherwise works as today (same preference order, same speech-style lookup).
  - Remove `from config import ...` (line 9). The two constants it needs come from a new leaf module (next item).
- New `conversion/math_braille_codes.py` (no imports):

  ```python
  MATH_BRAILLE_TABLES = ("UEB", "Nemeth")
  DEFAULT_MATH_BRAILLE_TABLE = "UEB"
  ```

  `mathcat_adapter.py` imports both from it. `config.py` replaces its two literal definitions with `from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)`, so `config.MATH_BRAILLE_TABLES`, `config.DEFAULT_MATH_BRAILLE_TABLE` and the existing `from config import DEFAULT_MATH_BRAILLE_TABLE` in `service.py` and `math_service.py` keep working with equal values. `conversion/__init__.py` is empty, so `config` importing this leaf adds no import side effects and no cycle. P2-3 can later decide where the settings options read these from.

  Alternatives rejected: keeping the constants in `config` (then `mathcat_adapter` still imports `config`); moving them into `mathcat_adapter.py` (then `config` would import the MathCAT glue module); duplicating them (two sources of truth).

### `braille/tables/__init__.py`

```python
def getDefaultTableForCurLang(tableType: TableType, lang: str) -> str:
	"""Gets the file name of the default braille table for C{lang}.
	DotExpress: the caller passes the language; upstream NVDA reads languageHandler.getLanguage().
	...
	"""
```

The body replaces `lang = config.get_lang()` with the parameter and is otherwise unchanged (exact match, then the base code before `_`, then `DEFAULT_TABLE`). The NVDA name is kept so the file stays easy to compare with upstream; the docstring explains the change. The function still has no caller in the app. Remove `import config` (line 25). The upstream comment `# import config` at line 18 stays. `logging.basicConfig` and the other glue are left for P2-7.

### Callers that need updating

| Caller | Change |
| --- | --- |
| `gui.py` `_build_conversion_request` | Adds `lang=get_lang()` and `charset_maps=get_charset_maps()`; imports both from `config`. |
| `main.py` `run_demo` | Same two fields; imports both from `config`. |
| `tests/test_conversion_jobs.py` | Its `ConversionRequest(...)` gets `lang` and `charset_maps`. |
| `tests/test_language_detection_translation.py` (Windows-only) | `LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=<defaults>)`. `"zh_TW"` is what the test effectively used before (the `get_lang()` fallback when nothing is set). |
| `tests/test_translation_language_result.py` (Windows-only) | Calls `translate_with_language(text, dictionary_path, DEFAULT_TRANSLATION_TABLES, bopomofo_path, runtime=runtime, lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)`. The call must be rewritten for the new keywords anyway. In the same edit, drop the stray leading `"zh-tw.ctb"` positional, which makes the test raise `TypeError` today. This is a minimal fix needed to make the call match the signature; it cannot be run on Linux. |

`client_init.py` keeps using `config.get_lang` for its locale report.

## What Stays Identical

- For a given `config.json`, environment and input: the language commands the detector emits, the translation table chosen for each segment, the boundary spaces, the MathCAT `Language`/`SpeechStyle`/`BrailleCode` preferences, and therefore the braille output and the dual-view segments.
- `config.get_lang()` precedence (`set_lang` override, `TEXT2BRAILLE_LANG`, `config.json` `"language"`, `"zh_TW"`) and `config.get_charset_maps()` merging.
- A mid-session `config.json` edit still affects the next conversion.
- `config.MATH_BRAILLE_TABLES` and `config.DEFAULT_MATH_BRAILLE_TABLE` still exist with the same values.
- `client_init.py`, `settings/*`, `conversion/jobs.py`, `dual_view/*`, `documents/*`, `braille/tables/__tables.py` and `braille/liblouis/` are untouched.
- No `.po`/`.mo` change.

Intentional differences, none visible in normal use:

- All segments in one conversion use the same language snapshot (today a `config.json` edit during a running job could affect later segments).
- `LanguageDetector` with a partial `charset_maps` falls back to the first language for the block instead of raising `KeyError` (unreachable from the app).
- Importing `braille.tables`, `languageDetection`, `conversion.text.pipeline`, `conversion.output` or `conversion.mathcat_adapter` no longer imports `config` (and so no longer creates its logger).

## Test Plan

Write the characterization tests first, on the current code, so the expected values come from today's behavior. Then change the code and update only the call shapes.

### Updated tests

- `tests/test_language_detection_char_langinfo.py`: replace every `patch("languageDetection.config.get_lang", return_value="en")` with `default_lang="en"` and `charset_maps=<default map>` in the constructor. `test_charset_map_is_loaded_from_config` becomes `test_charset_map_comes_from_constructor` and passes the `CJKCharactersLanguage: "ja"` map to the constructor. Expected sequences do not change.
- `tests/test_language_detection_unicode_braille.py`: pass `default_lang="zh_TW"` and the default map (the values it implicitly used before).
- `tests/test_conversion_text_pipeline.py`: `test_plain_text_translation_uses_current_language_when_no_language_command` passes `lang="en"` and the default map instead of patching. `test_alignment_output_entry_applies_source_preprocessing_once` adds the two request fields.
- `tests/test_conversion_service.py`: every `ConversionRequest(...)` gets `lang="zh_TW"` and the default map. Every `translate_with_language*` call gets `lang="zh_TW", charset_maps=<default map>` (use module-level `LANG`/`CHARSET_MAPS` constants). `FakeMathTranslator.translate` takes `language` and records `(source, braille_code, language)`. `test_translate_with_language_passes_selected_math_braille_code` expects `[("1", "UEB", "zh_TW")]`. The known P2-5 failure stays as it is.
- `tests/test_mathcat_adapter.py`: remove the `config` import and the `setUp`/`tearDown` that call `config.set_lang`; pass `language="zh_TW"` to every `get_braille_for_mathml` call. Expected preferences do not change (`("SetPreference", "Language", "zh-tw")`).
- `tests/test_math_service.py`: `translate_math_segment(r"\frac{2}{", language="zh_TW")`.
- `tests/test_math_translation_adapter.py`: the fake `translate_math` takes `language`; calls pass `language=...`; the recorded call includes it.
- `tests/test_translation_fallback.py`: `FallbackMathTranslator().translate(..., braille_code="Nemeth", language="zh_TW")`.
- `tests/test_conversion_jobs.py`, `tests/test_language_detection_translation.py`, `tests/test_translation_language_result.py`: as in the caller table above.
- `tests/test_gui_document_flows.py`: the two existing `_build_conversion_request` tests (`test_conversion_request_copies_frame_translation_tables`, `test_applied_settings_tables_reach_next_conversion_request`) patch `gui.get_lang` and `gui.get_charset_maps`, so they no longer read the developer's real `config.json`.

### New tests

1. **Same request, different environment** (new `tests/test_conversion_language_explicit.py`): build one `ConversionRequest(lang="en", charset_maps=<default map>, ...)` with mixed text and inline math (for example `"Hello 中文 $1$"`). Run `conversion.service.convert_text_with_alignment` with recording fake text and math translators, injected `map_char`, and temporary data and dictionary files (same setup as `test_conversion_service.py`). Run it twice: once with `TEXT2BRAILLE_LANG=zh_TW` and once with `TEXT2BRAILLE_LANG=ja` (`patch.dict(os.environ, ...)`, and `config._runtime_lang` set to a third value and restored). Both runs patch `config.get_lang` and `config.get_charset_maps` with `side_effect=AssertionError`. Assert: equal `display_text`, equal recorded text-translator `(text, table)` calls, equal math calls, and every math call has `language == "en"`.
2. **The request language is honored** (same file): the text `"→"` (its block maps to `None` in `languageDetection.blocks.BLOCKS`, so it is a non-detecting character and the detector emits no language change; it is not Unicode braille, so it still goes through the runtime translator) is translated with the `en` table when `lang="en"` and with the `zh` table when `lang="zh_TW"`, given tables `{"default": ..., "en": ..., "zh": ..., "ja": ...}`. Digits and ASCII punctuation are not suitable: under `zh_TW` they switch to `en`. Characterization on the current code (detector with `config.get_lang` patched): `"→"` yields `["→"]` under both `en` and `zh_TW`; `"1+1"` yields `["1+1"]` under `en` but `["en", "1+1"]` under `zh_TW`.
3. **The request `charset_maps` is honored** (`tests/test_conversion_text_pipeline.py`): with tables `{"default": ..., "en": ..., "zh": ..., "ja": ...}`, `lang="en"`, text `"A中"`: `CJKCharactersLanguage: "zh"` translates `中` with the `zh` table; `CJKCharactersLanguage: "ja"` translates it with the `ja` table.
4. **Detector uses `default_lang` for the preferred full language** (`tests/test_language_detection_char_langinfo.py`): `LanguageDetector(["en", "zh"], default_lang="zh_HK", charset_maps=<default map>)` on `[LangChangeCommand("en"), "中"]` emits `["en", "zh_HK", "中"]` (step 2 of `_preferred_full_lang`; confirmed on the current code with `config.get_lang` patched to `"zh_HK"`). Also: `LanguageDetector(["en", "zh", "ja"], ...)` on `"Hello 中文 "` emits `["Hello ", "zh", "中文 "]` with `default_lang="en"` and `["en", "Hello ", "zh_TW", "中文 "]` with `default_lang="zh_TW"` (also confirmed on the current code).
5. **Detector with a partial map** (same file): `charset_maps={}` with `default_lang="zh_TW"`, available `["en", "zh_TW"]`, text `"中A"` does not raise and emits `["中", "en", "A"]` (the first language for Basic Latin; the full default map gives the same sequence today). Do not use a CJK character for this case: `blockLanguages` for CJK blocks is built by iterating a `set`, so `langs[0]` depends on hash randomization.
6. **Detector constructor is explicit** (same file): `LanguageDetector(["en"])` raises `TypeError`.
7. **MathCAT language is per call** (`tests/test_mathcat_adapter.py`): `get_braille_for_mathml(..., language="en_US")` sets `("SetPreference", "Language", "en-us")`; two calls on one adapter with `"zh_TW"` then `"en"` each set their own language. `get_braille_for_mathml("<math/>")` without `language` raises `TypeError`.
8. **Math service forwards the language** (`tests/test_math_service.py`): with `conversion.mathcat_adapter.get_shared_mathcat_adapter` patched to a recording fake, `translate_math_segment("1", braille_code="Nemeth", language="en")` calls `get_braille_for_mathml(<mathml>, braille_code="Nemeth", language="en")`.
9. **`getDefaultTableForCurLang` takes `lang`** (new `tests/test_braille_tables_default_lang.py`): for `TableType.OUTPUT`, `"zh_TW"` -> `"zh-tw.ctb"`, `"ja_JP"` -> `"ja-kantenji.utb"` (base-code fallback), `"xx"` -> `DEFAULT_TABLE`. These values come from the registry in `__tables.py` (checked on Linux). If the registry changes upstream, the test should read the expected value from `_outputTableForLangs` instead of hard-coding it.
10. **No `config` import in the cleaned modules** (`tests/test_translation_import_isolation.py`, new test in the existing class): a subprocess runs `import languageDetection, conversion.text.pipeline, conversion.output, conversion.mathcat_adapter, braille.tables` and asserts `"config" not in sys.modules`. This catches transitive imports as well as direct ones.
11. **Frame reads the language per request** (`tests/test_gui_document_flows.py`): with `gui.get_lang` returning `"en"` and `gui.get_charset_maps` returning a map, `_build_conversion_request(...)` carries both. A second request after the patched return values change carries the new values (a mid-session change reaches the next conversion). Two requests do not share the same `charset_maps` object.
12. **CLI demo reads the language once** (new small test, for example `tests/test_main_demo.py`): with `main.build_default_translation_runtime`, `main.convert_text_with_alignment`, `main.get_lang` and `main.get_charset_maps` patched, `run_demo("x")` builds a request with the patched `lang`/`charset_maps`, prints the output and closes the runtime.

New tests must not depend on the developer's `config.json` or environment.

## Acceptance Criteria

1. `grep -nE '^[[:space:]]*(import config\b|from config import)' client/conversion/text/pipeline.py client/languageDetection/__init__.py client/conversion/mathcat_adapter.py client/braille/tables/__init__.py` prints nothing.
2. `grep -rnE 'get_lang|get_charset_maps' client --include=*.py | grep -v '^client/tests/'` lists only `config.py` (definitions), `client_init.py`, `gui.py` (import and `_build_conversion_request`) and `main.py` (import and `run_demo`).
3. `grep -rnE 'languageDetection\.config|pipeline\.config|config\.set_lang' client/tests` prints nothing.
4. `git diff main --stat -- client/braille/tables/__tables.py client/braille/liblouis` is empty.
5. Focused verification (Linux; leaves out the two Windows-only modules, which abort a by-name run on Linux) passes with only the known P2-5 failure:
   `cd client && python3 -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation tests.test_math_service tests.test_math_translation_adapter tests.test_translation_fallback tests.test_conversion_jobs tests.test_translation_runtime_provider tests.test_conversion_language_explicit tests.test_braille_tables_default_lang tests.test_main_demo tests.test_gui_document_flows -v`
6. Full suite: `cd client && python3 -m unittest discover -s tests -p "test_*.py"` reports `failures=1` (only the known P2-5 failure), `errors=0`, `skipped=7`, with 554 tests plus the new ones.
7. No changes under `client/locales/`.
8. On Windows (cannot be run on this Linux host; tracked as verification debt): the roadmap command `python -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_translation tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation -v`, plus `tests.test_translation_language_result`, `tests.test_liblouis_runtime` and `tests.test_translation_runtime_provider`; and a manual check that converting mixed Chinese/English/math text in the app gives the same braille as before the change, with `TEXT2BRAILLE_LANG` unset and with `TEXT2BRAILLE_LANG=en`.

## Risks

- **Language-sensitive detection** (medium): the detector's output depends on `default_lang` in three places. The characterization-first test order and passing the raw `get_lang()` value unchanged keep the results identical. Any normalization of `lang` is deliberately left out.
- **Windows-only paths cannot be run here** (medium): MathCAT (`libmathcat_py.pyd`) and liblouis only load on Windows. The MathCAT `Language` preference is computed from the same string with the same expression as before, and fake-library tests pin the call sequence. The Windows-only tests are updated but cannot be run on Linux.
- **Signature churn** (low): all new parameters are required keywords, so a missed caller fails loudly with `TypeError` instead of silently using a default. Grep in the acceptance criteria covers production callers; the full suite covers tests.
- **`config` importing `conversion.math_braille_codes`** (low): this adds a dependency from `config` to a leaf module with no imports. It cannot form a cycle. Under the wx test stubs (`tests/wx_stub.py` `StubScope`), `config` is not stubbed; re-importing the leaf after eviction is harmless. Run `tests.test_gui_document_flows` alone and with the full suite.
- **gui tests reading the real config** (low): new and updated gui tests patch `gui.get_lang`/`gui.get_charset_maps`. Other gui tests that mock `_build_conversion_request` are unaffected.
- **Overlap with later tasks** (low): P1-6 (dictionary repository) also changes `translate_plain_text_segment`'s signature; it adds to the keyword parameters added here. P2-3 may move the math options; the leaf module gives it a config-free place to read from. P2-7 changes `braille/tables/__init__.py` logging and `MathCATAdapter` injection; it keeps the explicit `language` parameter.

## Out of Scope

- Adding a language control to the settings dialog, or persisting `lang` through `set_lang`.
- Normalizing the language string at the source.
- Changing `client_init.py`'s locale provider.
- Removing `config` imports from `conversion/service.py` or `conversion/math_service.py` (they import only the math-table constant).
- Removing `logging.basicConfig` or other P2-7 cleanups in `braille/`.
- Building the language detector once per conversion instead of once per segment (P1-6 territory).
- Editing NVDA-derived or vendored files (`braille/tables/__tables.py`, `braille/liblouis/`).
