# DotExpress Platform Translation Adapters Design

## Summary

DotExpress currently loads the bundled Windows liblouis runtime while importing `braille.louis_helper`, and initializes it directly from `gui.py`. Math translation loads the Windows MathCAT `.pyd` and dependent DLLs on demand. These native dependencies prevent the complete conversion flow from being imported and tested reliably on unsupported platforms.

This design isolates text and math translation behind small adapters. Windows continues to use liblouis and MathCAT. If either capability is unavailable, only that capability falls back to a deterministic character-level translation: every non-space, non-newline source character becomes `⣿`, each source space becomes the braille blank `⠀` (`U+2800`), and newlines remain newlines.

The change preserves the current conversion orchestration, wrapping, language detection, dictionary processing, and native Windows output. It does not introduce plugin discovery, a dependency-injection framework, or new native backends.

## Current Problems

The platform boundary is spread across these paths:

- `client/braille/louis_helper.py` imports and loads the bundled liblouis runtime at module import time.
- `client/translate.py` imports `braille.louis_helper` at module import time.
- `client/gui.py` imports, initializes, and terminates `braille.louis_helper`.
- `client/conversion/mathcat_adapter.py` loads `libmathcat_py.pyd` and related DLLs.
- `client/conversion/service.py` calls concrete text and math translation functions.

This causes four concrete problems:

1. Importing otherwise platform-neutral conversion modules can load Windows binaries.
2. Text and math cannot independently degrade when only one native runtime is unavailable.
3. Non-Windows tests cannot exercise conversion, wrapping, and dual-view alignment end to end.
4. A future backend would require more platform checks in services or GUI code.

Two other Windows-specific behaviors are already isolated and degradable:

- `client/ui/font_support.py` guards `AddFontResourceExW` and returns `False` off Windows.
- `client/ui/dual_view.py` uses `SetWindowPos(..., SWP_NOACTIVATE, ...)` only on Windows and restores focus after `Raise()` elsewhere.

They are not part of the translation adapter hierarchy and require no redesign in this change.

## Goals

- Keep native runtime imports, loading, initialization, and shutdown inside translation adapters.
- Let text and math capability selection happen independently.
- Make conversion entry points depend on a `TranslationRuntime`, not Windows modules.
- Preserve current native Windows translation and error behavior.
- Provide deterministic fallback results with valid `TranslationResult` mappings.
- Exercise conversion, wrapping, and dual view on unsupported platforms.
- Leave an explicit extension point for future Linux or macOS adapters.

## Non-Goals

- Implementing real Linux or macOS liblouis or MathCAT backends.
- Adding backend discovery, a registry, user-selectable backends, or a DI container.
- Rewriting `TranslationResult`, language detection, dictionary processing, wrapping, or dual view.
- Silently falling back after a native adapter successfully initializes but later fails to translate.
- Making non-Windows focus behavior identical to the Windows `SWP_NOACTIVATE` behavior.
- Refactoring unrelated GUI, document, or settings code.

## Evaluated Approaches

### A. Add Platform Checks to Existing Functions

Add `sys.platform` branches to `translate.py`, `math_service.py`, and conversion functions.

This has low initial churn, but spreads platform and fallback policy through the application. It also keeps module imports coupled to native implementations.

### B. Add Translation Adapters and a Small Runtime Provider

Define separate text and math protocols, implement native and fallback strategies, and centralize capability selection in one provider.

This creates a testable boundary while preserving the current orchestration and result model. It adds only the abstractions required by the two existing native integrations.

### C. Rebuild Translation as a Plugin System

Replace the result model and conversion pipeline and add backend discovery and dependency injection.

This exceeds the stated requirement and increases regression risk before multiple real backends exist.

### Decision

Use approach B. It is the smallest design that removes native imports from platform-neutral modules, supports independent text/math fallback, and allows explicit test injection.

## Design Principles

- Adapter wraps liblouis and MathCAT calling conventions.
- Strategy makes native and fallback implementations interchangeable.
- A small provider constructs and selects the two strategies.
- SRP separates native loading, conversion orchestration, and result behavior.
- OCP allows a future backend without changing `conversion/service.py`.
- LSP requires every implementation to return a valid `TranslationResult`.
- ISP keeps text and math contracts separate.
- DIP makes conversion depend on protocols and a runtime bundle.

## Required File Structure

```text
client/
├── adapters/
│   ├── __init__.py
│   └── translation/
│       ├── __init__.py
│       ├── contracts.py
│       ├── fallback.py
│       ├── liblouis.py
│       ├── mathcat.py
│       └── provider.py
├── conversion/
│   ├── math_service.py
│   └── service.py
├── gui.py
└── translate.py
```

Responsibilities:

- `contracts.py`: protocols, `RuntimeUnavailableError`, and `TranslationRuntime`.
- `fallback.py`: deterministic text and math fallback adapters.
- `liblouis.py`: lazy import, lifecycle, and calls to `braille.louis_helper`.
- `mathcat.py`: MathCAT capability initialization and math result construction.
- `provider.py`: independent construction and fallback selection.
- `conversion/service.py`: segment parsing, dictionary/language orchestration, result composition, and wrapping.
- `translate.py`: `TranslationResult` and its result/mapping operations only.
- `gui.py`: application assembly; obtains, passes, and closes one runtime.

## Contracts

### Text Translation

```python
class BrailleTextTranslator(Protocol):
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        ...
```

`text` is post-dictionary input sent to a native backend. `raw` is the source represented in alignment output. `single_token=True` preserves the existing atomic-dictionary behavior.

The native adapter reproduces the current `translate()` and `translate_as_single_token()` behavior. The fallback adapter generates output from `raw`, not replacement `text`, because dictionary replacement may change length and degraded output must remain one cell per source character.

### Math Translation

```python
class MathSegmentTranslator(Protocol):
    def translate(
        self,
        source: str,
        *,
        braille_code: str,
    ) -> TranslationResult:
        ...
```

The MathCAT adapter preserves current behavior: the complete math source is one raw token and every native braille cell maps to that token. The fallback math adapter returns one raw token per source character and one-to-one arrays so every unsupported math character remains alignable.

### Runtime Bundle

```python
@dataclass
class TranslationRuntime:
    text_translator: BrailleTextTranslator
    math_translator: MathSegmentTranslator
    close_callbacks: tuple[Callable[[], None], ...] = ()

    def close(self) -> None:
        ...
```

`close()` is idempotent and closes only native adapters that initialized successfully.

## Runtime Selection

Text and math capability are selected independently:

| Text | Math | Text adapter | Math adapter |
| --- | --- | --- | --- |
| Available | Available | liblouis | MathCAT |
| Available | Unavailable | liblouis | fallback |
| Unavailable | Available | fallback | MathCAT |
| Unavailable | Unavailable | fallback | fallback |

Native factories normalize known loading failures into `RuntimeUnavailableError`. Unsupported platform, missing binary, missing dependent DLL, and an import failure caused by the native package are capability-unavailable conditions.

The provider catches only `RuntimeUnavailableError`. Unexpected defects propagate instead of being disguised as unsupported capability.

Capability probing is eager during application assembly:

- The liblouis adapter imports `braille.louis_helper` inside its factory and calls `initialize()`.
- The MathCAT adapter loads the `.pyd` and dependent DLLs during its factory initialization.
- Importing `translate`, `conversion.service`, or `gui` does not initialize either native runtime.

## Fallback Contract

For source string `source` of length `n`:

- Every character other than a space or newline becomes `⣿`.
- Every source space becomes `⠀` (`U+2800`).
- Every newline remains `\n`.
- `raw == list(source)`.
- `braille` contains one output character per source character.
- `raw_to_braille_pos == list(range(n))`.
- `braille_to_raw_pos == list(range(n))`.
- Empty input returns `TranslationResult([], [], [], [])`.

Examples:

| Input | Output |
| --- | --- |
| `我們這一家` | `⣿⣿⣿⣿⣿` |
| `我 們` | `⣿⠀⣿` |
| `1+2` | `⣿⣿⣿` |
| `a\nb` | `⣿\n⣿` |

The fallback is an explicit degraded mode. It exists to preserve application flow and alignment, not to claim semantically correct braille.

`single_token=True` does not collapse fallback mapping. Character-level fallback alignment takes precedence because unsupported-platform testing is its purpose.

## Data Flow

```text
BrailleApp.OnInit
    |
    +--> build_translation_runtime()
             |
             +--> native text or fallback
             `--> native math or fallback
    |
    `--> BrailleFrame(runtime)
             |
             `--> convert_text_with_alignment(..., runtime=runtime)
                      |
                      +--> dictionary and language segmentation
                      +--> runtime.text_translator.translate(...)
                      +--> runtime.math_translator.translate(...)
                      `--> compose, wrap, dual-view results

BrailleApp.OnExit --> runtime.close()
```

Tests inject a `TranslationRuntime` containing fallback or fake adapters. They do not mutate global `sys.platform` to control service behavior.

## Error Handling

### Capability Unavailable

This occurs only while constructing a native adapter. A native factory raises `RuntimeUnavailableError`, and the provider selects fallback for that capability. The other capability remains independent.

### Translation Failure

The native adapter initialized, but a translation call fails for an input, table, LaTeX expression, or runtime state. The error propagates through the existing `ConversionStageError("translation", error)` path. It does not silently switch to fallback.

This distinction prevents real Windows regressions from appearing as successful degraded output.

## UI Platform Behavior

### Font Registration

Keep `register_private_font_for_windows()` unchanged. It already skips unsupported platforms and does not block translation initialization.

### Dual-View Window

Keep the Windows no-activation optimization and current cross-platform focus restoration. Non-Windows acceptance requires that dual view open, close, and render fallback alignment; exact focus semantics need not match Windows.

## Testing Strategy

### Result Characterization

- Move liblouis-independent `TranslationResult` tests out of runtime-gated modules.
- Lock down addition, empty results, and character-level mapping before adapter migration.

### Fallback Unit Tests

- CJK, ASCII, numbers, and punctuation become `⣿`.
- Spaces become `⠀`; newlines remain `\n`.
- Mixed and empty input produce exact arrays.
- Text fallback uses `raw` when dictionary replacement length differs.
- Text fallback remains character-level with `single_token=True`.
- Math fallback follows the same character-level contract.

### Native Adapter Tests

- liblouis adapter forwards table, text, and mode and reproduces normal and single-token mappings.
- liblouis initialization and close happen once.
- MathCAT adapter passes the selected braille code and returns the current single-token mapping.
- Known load failures become `RuntimeUnavailableError`.
- Translation failures remain translation errors.

### Provider Tests

- Cover all four native/fallback combinations with injected factories.
- Verify only `RuntimeUnavailableError` causes fallback.
- Verify runtime close callbacks include only initialized native adapters and are idempotent.

### Conversion Integration Tests

- Pure text conversion completes with full fallback.
- Text containing math completes with full fallback.
- Native/fake text and fallback math can be mixed.
- Fallback results pass through wrapping.
- `convert_text_with_alignment()` returns character mappings usable by dual view.
- Importing `translate`, `conversion.service`, and `gui` does not load native modules.

### Existing Platform Tests

- Retain Windows-only liblouis and MathCAT runtime tests.
- Keep font and dual-view platform behavior tests.
- Cross-platform fallback tests must never be skipped for absent Windows binaries.

## Migration Order

1. Characterize the current result contract.
2. Define protocols, runtime bundle, and capability error.
3. Implement fallback adapters.
4. Move liblouis calls out of `translate.py`.
5. Wrap MathCAT conversion as a result-producing adapter.
6. Add independent provider selection and lifecycle.
7. Inject the runtime through conversion entry points.
8. Assemble and close the runtime in `BrailleApp`.
9. Add cross-platform conversion and dual-view coverage.
10. Run focused cross-platform tests and retain Windows regression commands for a Windows environment.

## Compatibility

- Windows selects liblouis and MathCAT by default and preserves current native output.
- Existing conversion function names remain, but conversion entry points receive an explicit `runtime` keyword argument.
- `TranslationResult` keeps its public behavior.
- Language detection, dictionary replacement, math delimiters, boundary spaces, wrapping, and ASCII output remain service responsibilities.
- Existing `font_support.py` and `dual_view.py` platform guards remain unchanged.

## Risks and Mitigations

### Native Loading Still Happens During Import

Moving classes without removing top-level imports would preserve the failure.

Mitigation: add import-isolation tests and remove `braille.louis_helper` imports from `translate.py` and `gui.py`.

### Dictionary Replacement Breaks Fallback Alignment

Post-dictionary text can differ in length from source text.

Mitigation: the text contract carries both `text` and `raw`; fallback always maps `raw`.

### Math Mapping Contradicts Character-Level Fallback

Current MathCAT output maps a whole expression as one token.

Mitigation: preserve that native behavior, but explicitly require character-level mapping for fallback math.

### Broad Exception Handling Hides Defects

Treating every initialization exception as unavailable could hide programming errors.

Mitigation: native factories normalize only known load failures, and the provider catches only `RuntimeUnavailableError`.

### Runtime Lifecycle Is Duplicated

Keeping `gui.py` calls to `louis_helper.initialize()` while adapters also initialize it could double-register callbacks.

Mitigation: the runtime owns lifecycle exclusively; GUI only calls `runtime.close()`.

## Acceptance Criteria

- `translate.py`, `conversion.service`, and `gui.py` import without initializing liblouis or MathCAT.
- Non-Windows platforms can run text and math conversion through fallback adapters.
- Unsupported text and math capabilities are selected independently.
- Every unsupported non-space/non-newline character becomes `⣿`.
- Source spaces become `⠀`, and newlines remain newlines.
- Fallback position arrays exactly match the character-level contract.
- Dictionary replacement cannot change fallback result length or source alignment.
- Fallback conversion passes through wrapping and dual-view model generation.
- `conversion/service.py` contains no OS detection or native binary loading.
- Native translation failure is reported, not silently degraded.
- Windows continues using existing liblouis and MathCAT behavior.
- Font registration and no-focus window behavior remain separate optional UI enhancements.
- No plugin system, DI container, or unrelated refactor is introduced.
