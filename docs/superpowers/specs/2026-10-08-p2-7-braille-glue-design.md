# Braille Glue Cleanup (P2-7) Design

## Goal

Roadmap task P2-7 in `storage/refactor.md` (section 6.3), finding D-6 ("first-party `braille/` glue calls `logging.basicConfig` at import"), plus two items handed over by the P1 phase review (`docs/superpowers/history/2026-10-08-02-refactor-p1/review_task.md`, section "P2-7") and the P2-6 handoff note about test logs.

After this task:

- Importing `braille.tables` or `braille.louis_helper` no longer configures the root logger. Both modules log through `logging.getLogger(__name__)`.
- `braille.tables.get_table_directory(source)` is the public way to ask for a table source's folder. `louis_helper` no longer reads `braille_tables._tablesDirs`.
- The translation runtime provider creates the `MathCATAdapter`, passes it down the math chain, and closes it when the runtime closes. The module-level `_SHARED_ADAPTER` / `get_shared_mathcat_adapter()` singleton is gone.
- `getDefaultTableForCurLang(tableType, lang)` is kept on purpose (decision D4).
- The unit test suite no longer appends to the real `client/log/*.log` files.

This is a refactor. Nothing new is shown or spoken, no msgid changes (353, same set), conversion output is the same, the golden fixtures do not change, the files in `<root>/log/` get the same records, and NVDA-derived files that DotExpress does not own (`client/braille/tables/__tables.py`, `client/braille/liblouis/__init__.py`, everything in `vendor/nvda/` except the adapted helper) are not touched. The only observable difference is on the console of a **source run** (the packaged app is built with `--noconsole` and has no console): see D2.

Corrected after planning: the plan `docs/superpowers/plans/2026-10-08-p2-7-braille-glue.md` (section "Spec Corrections and Refinements") fixed three facts (criterion 9's grep also matches three tracked lines on purpose: D5's `return _tablesDirs.get(source)`, the `_adapt_helper` marker in `scripts/sync-nvda.py` and NVDA's verbatim `vendor/nvda/liblouis/python/louisHelper.py`; `tests/test_dual_view_frame.py` uses tabs, not 4 spaces; `TranslationRuntime.close()` is `contracts.py:35-40`) and refined the design (24 new client tests and 2 new scripts tests, the existing `MathCATError` provider test reused through `adapter_factory=`, a test that pins the default adapter factory, a context-manager characterization helper, `MathCATAdapter.close()` idempotent without an early return, D9's `except BaseException`, D11 through `unittest.addModuleCleanup`, criterion 7 in a fresh clone, the regenerated helper equal to the prototype); those changes are folded in below.

## Key Finding: `louis_helper.py` Is Generated

The roadmap lists `client/braille/louis_helper.py` as a file to edit, and `storage/refactor.md` section 7 item 6 says to check first whether `scripts\sync-nvda.py` overwrites it, and to change an adapter layer instead if it does. It does:

- `client/braille/louis_helper.py` is **not tracked**. `client/.gitignore:13` ignores it, `scripts/clean-liblouis.bat:44` and `sconstruct` `_remove_liblouis_artifacts` delete it, and `readme.md` ("The generated runtime outputs are ...") says it must not be hand-edited.
- It is produced in two steps. `scripts/sync-nvda.py` `_adapt_helper()` (lines 144-200) rewrites NVDA's `include/nvda/source/louisHelper.py` with a fixed list of string replacements and writes the result to the tracked file `vendor/nvda/liblouis/runtime/louis_helper.py`. Then `scons install` (`scripts\install.bat`) copies it through `vendor/nvda/liblouis/dist/` to `client/braille/louis_helper.py` (`sconstruct` lines 94-109).
- Checked on this checkout: `_adapt_helper(include/nvda/source/louisHelper.py)` is byte-identical to `vendor/nvda/liblouis/runtime/louis_helper.py` and to the local `client/braille/louis_helper.py`.
- The `logging.basicConfig(...)` call and the `braille_tables._tablesDirs.get(...)` line are both inserted by `_adapt_helper` (the replacement for `"from logHandler import log\n"` at line 166 and the one at line 175). NVDA's source has neither.

So the change goes where DotExpress owns the code: the replacement strings in `_adapt_helper`. NVDA's file is not modified. The tracked snapshot `vendor/nvda/liblouis/runtime/louis_helper.py` is regenerated with `_adapt_helper` alone (decision D3), and the ignored `client/braille/louis_helper.py` is refreshed by the normal Windows build (`scripts\install.bat`). That last step cannot run here (Windows debt).

A second finding (pre-existing, not fixed): **a full `sync-nvda.py` run is not idempotent.** Running `synchronize()` into a scratch root that links the real `include/` gives the same files as `vendor/nvda/` except `vendor/nvda/liblouis/build/sconscript`, which commits `9aa8355` and `1bd19d7` edited by hand after the last sync (`buildDir`, `workDir`, `buildInputsDir`). A full sync would revert those edits, even though `AGENTS.md` and `readme.md` say to rerun it before rebuilding. This task must not run the full sync. It is listed as a follow-up.

## Current State (verified 2026-10-08 on `refactor/p2-7-braille-glue`, HEAD `5764ad3`, P0-*, P1-*, P2-1..P2-4 and P2-6 merged)

`$SP` is the session scratchpad and `$PY` is `$SP/venv/bin/python`.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1071 tests`, `FAILED (failures=1, skipped=9)`. The failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. `$PY $SP/shuffle_harness.py 1` gives the same. From the repo root, `$PY -m unittest discover -s scripts/tests` gives `Ran 25 tests ... OK`. `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`. Fixture sha256: `client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.

Note for whoever greps: the shell `grep` in this environment skips ignored files, so it does not see `client/braille/louis_helper.py`. Use `command grep`.

### Who configures logging

| Where | What |
| --- | --- |
| `client/braille/tables/__init__.py:24-31` (tabs, **CRLF**) | `import logging`, `log = logging` (the module itself, not a logger), `log.basicConfig(level=INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt=...)`. Runs on first import. `addTable` (127-165) calls `log.warning(...)` twice, so these are module-level `logging.warning` calls, which run `basicConfig()` again on their own if the root has no handler. |
| `client/braille/louis_helper.py:19-26` (generated, tabs, LF) | `log = logging.getLogger(__name__)` then the same `logging.basicConfig(...)`. |
| `client/log.py:11-32` | `get_logger(name, filename, level)`: one `FileHandler(<root>/log/<file>, delay=True)` per logger, explicit level, `propagate = False`. |
| Users of `get_logger` | `config.py:13` (`config.log`), `client_init.py:16` (`init.log`), `gui.py:97` (`gui.log`), `ui/dual_view.py:13` (`dual_view.log`), `adapters/translation/provider.py:13` (`translation.log`), `conversion/math_service.py:10` (`math.log`). |

No other module in `client/`, `server/` or `scripts/` calls `basicConfig` or touches the root logger (`command grep -rn basicConfig`, `logging.getLogger`). The tests never configure the root logger.

Measured on Linux: before `import braille.tables` the root logger has no handler and level `WARNING`; after it, one `StreamHandler(<stderr>)` and level `INFO`. Importing it emits no warning (no duplicate language entries in `__tables.py`).

What the root handler is used for today: every `get_logger` logger has `propagate = False`, so none of the app's log files depend on it. The only records that reach the root are from loggers DotExpress does not configure: `braille.louis_helper`, the `logging.warning` calls in `braille.tables`, and third-party libraries. In the app, `settings/dialogs.py:10` imports `braille.tables` while `gui.py` is imported, so the root is configured before `OnInit`. The packaged app is built with `--noconsole` (`scripts/build-dotexpress.bat`), so `sys.stderr` is `None` and the root handler's output is dropped. Only a source run (`python gui.py` in a console) prints it.

`louis_helper._isDebug()` is `log.isEnabledFor(logging.DEBUG)`. With `basicConfig` the effective level is `INFO`; without it, `WARNING`. Both are above `DEBUG`, so the liblouis log callback and the resolver's debug lines stay off either way.

### `braille/tables/__init__.py` (tabs, CRLF, 251 lines, every line ends in `\r\n`)

- `TABLES_DIR` (34), `DEFAULT_TABLE` (39), `TableSource`, `TableType`.
- `_tablesDirs` (57-61): `ChainMap({TableSource.BUILTIN: TABLES_DIR})`, rebound at 229 to `_tablesDirs.new_child()`. `terminate()` (248-251) clears the child maps. DotExpress never calls `braille.tables.initialize()`/`terminate()`.
- `getDefaultTableForCurLang(tableType, lang)` (104-124): P1-1 made `lang` a parameter. No caller in the repository. `tests/test_braille_tables_default_lang.py` pins it. `addTable` fills `_inputTableForLangs`/`_outputTableForLangs`, which only this function reads.
- `getTable` (168-175), `listTables` (178-185; used by `settings/dialogs.py:543`).
- Upstream NVDA (`include/nvda/source/brailleTables/__init__.py`) has no public accessor for `_tablesDirs` either.
- `sync-nvda.py` does not generate this file or `__tables.py`.

### `louis_helper` table resolution (generated file, lines as in the current output)

`_resolveTableInner(tables, base)` (49-81): for each name, if `base` is `None` it tries `braille_tables.getTable(name)` and `braille_tables._tablesDirs.get(registeredTable.source)` (65), on `LookupError` it falls back; with a `base` it searches `dirname(base)` first; then `TABLES_DIR`. `_resolveTable` (86-124) is the ctypes callback. `initialize()` (143-151) registers the log callback, `LOG_DEBUG` and the resolver; `terminate()` (154-162) undoes them and calls `lou_free()`.

In production, `LiblouisTextTranslator.translate` (`adapters/translation/liblouis.py:28`) always passes a full path (`os.path.join(tables_dir, table)`). `getTable(full path)` raises `KeyError`, so the registered-source branch is reached only for bare names: `tests/test_liblouis_runtime.py` (`_resolveTableInner(["en-ueb-g2.ctb"])`, `louis.translateString(["zh-tw.ctb"], ...)`). Included tables come through the `base` branch.

On Linux, `import braille.liblouis` raises `AttributeError` (the bundled DLL is not loadable), so the real helper cannot be imported here. Loading `vendor/nvda/liblouis/runtime/louis_helper.py` with a fake `braille.liblouis` module (the `LOG_*` constants, `LogCallback = ctypes.CFUNCTYPE(None, c_int, c_char_p)`, `fileSystemEncoding`) works: on this checkout it adds the root `StreamHandler` at `INFO` and resolves a registered table into its source directory. The new tests use this (prototype checked).

### MathCAT lifecycle

| Where | What |
| --- | --- |
| `conversion/mathcat_adapter.py:20-100` (tabs) | `@dataclass MathCATAdapter(resource_root, _libmathcat=None, _dll_directory_handle=None)`. `initialize()` loads `libmathcat_py.pyd`: `os.add_dll_directory(resource_root)` once (handle kept, never closed), `importlib` load, `sys.modules.setdefault("libmathcat_py", module)`. `get_braille_for_mathml(mathml, braille_code=None, *, language)` reapplies rules and preferences on every call and wraps any non-`MathCATError` in `MathCATError`. No `close()`. |
| `conversion/mathcat_adapter.py:103-110` | `_SHARED_ADAPTER` and `get_shared_mathcat_adapter()`: process-wide lazy singleton built from `get_default_mathcat_resource_root()` (16-17, `client/mathcat/assets`, a read-only bundled resource). |
| `conversion/math_service.py:40-52` (tabs) | `mathml_to_nemeth_braille(mathml, braille_code=DEFAULT, *, language)` imports `get_shared_mathcat_adapter` inside the function and calls the singleton. |
| `conversion/math_service.py:55-73` | `translate_math_segment(latex, braille_code=DEFAULT, *, language)`: `latex_to_mathml` then `mathml_to_nemeth_braille`; any exception is logged to `math.log` and raised as `MathConversionError`. |
| `adapters/translation/mathcat.py` (4 spaces) | `MathCATMathTranslator(*, translate_math)`: calls `translate_math(source, braille_code=, language=)` and builds a single-token `TranslationResult`. No `close()`. |
| `adapters/translation/provider.py:85-100` (4 spaces) | `create_default_math_translator(*, platform=None)`: non-`win32` -> `RuntimeUnavailableError`; else imports, `get_shared_mathcat_adapter().initialize()`, maps `ImportError`/`OSError`/`MathCATError` to `RuntimeUnavailableError`, returns `MathCATMathTranslator(translate_math=translate_math_segment)`. |
| `adapters/translation/provider.py:16-18, 30-60` | `build_translation_runtime` adds `translator.close` as a close callback when the translator has a callable `close`. Today only `LiblouisTextTranslator.close` (`helper.terminate()`) qualifies. |
| `adapters/translation/contracts.py:35-40` | `TranslationRuntime.close()`: idempotent, runs callbacks in reverse order. |
| `gui.py:1086-1096` | `OnExit`: dual-view cleanup, then `runtime.close()`. `main.py:18-39` (demo) closes its runtime in `finally`. |

So the shared adapter is created on Windows when the runtime is built, used by every math conversion, never closed, and its DLL directory stays registered for the life of the process. Callers of the singleton: `provider.py:9, 96`, `math_service.py:46-48`, `tests/test_translation_runtime_provider.py:253` (patches `provider.get_shared_mathcat_adapter`), `tests/test_math_service.py:31` (patches `conversion.mathcat_adapter.get_shared_mathcat_adapter`). Callers of `translate_math_segment`/`mathml_to_nemeth_braille`: the provider and `tests/test_math_service.py` only. `MathCATMathTranslator(translate_math=...)` is also built by `tests/test_math_translation_adapter.py` and `tests/test_translation_golden.py:125`.

### Tests that write real log files

Each test module was run alone while watching `client/log/*.log` sizes. Exactly four append to real files:

| Module | File | Logger |
| --- | --- | --- |
| `tests/test_client_init.py` | `init.log` | `dotexpress.client_init` |
| `tests/test_dual_view_frame.py` | `dual_view.log` | `dotexpress.dual_view` |
| `tests/test_math_service.py` | `math.log` | `dotexpress.math` |
| `tests/test_translation_runtime_provider.py` | `translation.log` | `dotexpress.translation` |

The handlers bind to `<client>/log/` when each module creates its logger at import (P2-6 D10). `client/log/` is git-ignored, so nothing shows in `git status`, but the files grow on every run (math.log is 1.9 MB here).

## Decisions

| # | Decision | Why |
| --- | --- | --- |
| D1 | `braille/tables/__init__.py`: replace `log = logging` + `log.basicConfig(...)` with `log = logging.getLogger(__name__)`. Every other line stays. | `log = logging` made `log.warning` the module-level function, which calls `basicConfig()` itself when the root has no handler. Dropping only the explicit call would move the root setup to the first duplicate-language warning instead of removing it. A named logger keeps the same `log.warning(...)` call sites and messages. |
| D2 | Neither glue module configures logging. No replacement handler is added (no `get_logger("dotexpress.liblouis", "liblouis.log")`). | The app's log files come only from `get_logger` loggers with `propagate = False`, so they are unchanged. The packaged app has no console, so it is unchanged. In a source run, records that reach the root now go to Python's last-resort handler: `WARNING` and above still print to stderr, but without the timestamp format, and `INFO` records from third-party libraries no longer print. `_isDebug()` stays `False` (effective level `WARNING` instead of `INFO`). Adding a `liblouis.log` file would create a new file in `<root>/log/` and change what the app writes, which is not this task. If one is wanted later, `louis_helper` already logs through `braille.louis_helper`, so a handler can be attached there without touching the glue. |
| D3 | The `louis_helper` change is made in `scripts/sync-nvda.py` `_adapt_helper()`: (a) the replacement for `"from logHandler import log\n"` drops the `logging.basicConfig(...)` block and keeps `import logging`, `log = logging.getLogger(__name__)`, `BASE_DIR`, `WINFUNCTYPE`; (b) the replacement for `"path = brailleTables._tablesDirs.get(registeredTable.source)\n"` becomes `"path = braille_tables.get_table_directory(registeredTable.source)\n"`. Then `vendor/nvda/liblouis/runtime/louis_helper.py` is rewritten as `_adapt_helper(Path("include/nvda/source/louisHelper.py").read_text(encoding="utf-8"))`, UTF-8 with `\n` line endings, exactly as `synchronize()` writes it. Nothing else in `vendor/` changes (`SOURCE.json` lists the same files and commit). The ignored `client/braille/louis_helper.py` is not edited by hand; `scripts\install.bat` refreshes it on Windows. | The helper is a generated file (see Key Finding); a hand edit would be lost at the next `clean-liblouis`/`install`, and `client/braille/louis_helper.py` cannot be committed. The adaptation table is DotExpress's own adapter layer over NVDA's file, which is what `storage/refactor.md` section 7 item 6 asks for. The helper is regenerated alone because a full sync would also revert the hand-edited `build/sconscript` (pre-existing drift). Regenerating with the same function guarantees the snapshot equals what a sync would write for that file; a test pins it. |
| D4 | Keep `getDefaultTableForCurLang(tableType, lang)` and its test. Add one docstring line saying it is kept for parity with NVDA `brailleTables` and has no DotExpress caller. | Deleting it leaves `addTable`'s `inputForLangs`/`outputForLangs` (passed by the non-editable `__tables.py`) filling two dicts that nothing reads, and widens the diff from upstream for no runtime gain. Wiring it in (for example as the default table for a language) would change which table a user gets, which is a behavior change outside this task. Recorded so later reviews do not reopen it. |
| D5 | Add `get_table_directory(source: str) -> str \| None` to `braille/tables/__init__.py`, right after `getTable`/`listTables`. Body: `return _tablesDirs.get(source)`, reading the module global at call time. snake_case, as the roadmap names it and `AGENTS.md` asks for new functions; the NVDA-style camelCase names stay. | Same result as the old private access for every source, including after `terminate()` (the builtin parent map survives) and with child maps added later. `louis_helper` only needs the directory, not the map. |
| D6 | `MathCATAdapter.close()`: idempotent without an early return. It sets a `_closed` flag (new dataclass field, default `False`), takes `_dll_directory_handle` and sets it to `None` before closing it, and drops `_libmathcat`, so a second call finds nothing to close (an `if self._closed: return` guard would be dead code). After `close()`, `initialize()` and `get_braille_for_mathml()` raise `MathCATError("MathCAT adapter is closed")` without loading anything: a private `_ensure_open()` runs first in `initialize()` and before the `try` in `get_braille_for_mathml()`. `sys.modules["libmathcat_py"]` is left alone (an extension module cannot be unloaded). | Gives the runtime something real to release: the DLL search-path entry added with `os.add_dll_directory`. The closed check sits in the two public methods (not in `_load_libmathcat`), so the existing test subclass that overrides `_load_libmathcat` exercises it. Failing loudly after close stops a late caller from quietly adding the DLL directory again. |
| D7 | Delete `_SHARED_ADAPTER` and `get_shared_mathcat_adapter()`. `mathml_to_nemeth_braille(mathml, braille_code=DEFAULT, *, language, mathcat)` and `translate_math_segment(latex, braille_code=DEFAULT, *, language, mathcat)` take the adapter as a required keyword (any object with `get_braille_for_mathml(mathml, braille_code=..., *, language=...)`; annotated `MathCATAdapter` under `TYPE_CHECKING`). `math_service` no longer imports `conversion.mathcat_adapter` at run time. | With the provider owning the adapter, a hidden singleton would be a second owner nobody closes. The only production caller is the provider. `math_service` stays free of native loading (the import-isolation test still passes). |
| D8 | `MathCATMathTranslator(*, translate_math, close=None)`. `close()` calls the callback when one was given, otherwise does nothing. `translate()` is unchanged. | Existing constructions (`test_math_translation_adapter.py`, the golden test) keep working unchanged. `build_translation_runtime` already turns a callable `close` into a close callback, so no provider plumbing changes. |
| D9 | `create_default_math_translator(*, platform=None, adapter_factory=None)`. With no factory it uses a private `_create_mathcat_adapter()` that returns `MathCATAdapter(resource_root=get_default_mathcat_resource_root())`. Order: platform check; imports (`MathCATMathTranslator`, `translate_math_segment`); `adapter = adapter_factory()`; `adapter.initialize()`; if `initialize()` raises anything, `adapter.close()` runs and the exception continues (an `except BaseException:` that closes and re-raises, inside the existing `try`, where the factory call also sits, as the singleton lookup did; `ImportError`/`OSError`/`MathCATError` still become `RuntimeUnavailableError`, other errors still propagate as today). On success it returns `MathCATMathTranslator(translate_math=functools.partial(translate_math_segment, mathcat=adapter), close=adapter.close)`. | One adapter per runtime, created, initialized and closed by the same owner. A failed load no longer leaves its DLL directory registered. Error mapping and fallback logging are unchanged. `adapter_factory` replaces the patch of `provider.get_shared_mathcat_adapter` in tests. |
| D10 | Shutdown order follows `TranslationRuntime.close()`: callbacks run in reverse registration order, so the MathCAT adapter is closed first, then liblouis `terminate()`. Nothing else changes in `OnExit` or the demo. | The two runtimes are independent; this is the order the contract already defines. Today the math side has no callback. |
| D11 | Test log isolation: a new test helper module `client/tests/file_log_isolation.py` with one function that, for the given logger names, swaps each logger's handlers for a `logging.NullHandler`, sets `propagate = False`, and on cleanup puts back the exact previous handlers and `propagate`. It works whether or not the logger exists yet. `isolate_file_logs(*names)` returns the restore function; each of the four modules above registers it from its `setUpModule` with `unittest.addModuleCleanup` (which runs after `tearDownModule`, also when `setUpModule` fails part-way), so each one restores state when it finishes. `tests/test_dual_view_frame.py`'s `setUpModule = _SCOPE.activate` becomes a function that activates the scope, then isolates `dotexpress.dual_view`. The helper is imported as `tests.file_log_isolation` (the form `tests.wx_stub` uses), so it works under `discover`, `python -m unittest tests.x` and the shuffle harness. No production module changes. | Test-only, so the app is unchanged. It belongs here because it is the other half of the logging cleanup the P2-6 handoff assigned to P2-7. Swapping handlers (rather than patching `log._log_directory`) works because the handlers were already bound at import, and it survives `StubScope` eviction: a re-imported module calls `get_logger` again, finds a handler, and keeps it. Tests that assert on log calls (`patch.object(dual_view.logger, "debug")`, `RecordingLogger`) keep working because they replace the logger or its methods, not the handlers. This commit is independent and can be dropped on its own if a reviewer wants it elsewhere. |

## Design per File

### `client/braille/tables/__init__.py` (tabs, CRLF; edit byte-carefully)

- Lines 24-31 become `import logging`, a blank line, `log = logging.getLogger(__name__)` (D1). Keep the blank lines around them as they are.
- Add `get_table_directory` (D5) with a short docstring.
- Add the D4 line to the `getDefaultTableForCurLang` docstring.
- Every line keeps `\r\n`. The diff must show only these lines. Check: `$PY -c "d=open('client/braille/tables/__init__.py','rb').read(); assert d.count(b'\n')==d.count(b'\r\n')"`.

### `scripts/sync-nvda.py` (4 spaces)

Only the two replacement strings in `_adapt_helper` (D3). The marker check and the replacement loop are unchanged, so a future NVDA source that lacks a marker still fails loudly.

### `vendor/nvda/liblouis/runtime/louis_helper.py` (generated, tabs, LF)

Regenerated as in D3. Expected diff (prototyped in the scratchpad): the five-line `logging.basicConfig(...)` block (lines 22-26) disappears and the old line 65 (new line 60) reads `path = braille_tables.get_table_directory(registeredTable.source)`. Nothing else. The regenerated file equals the prototype (`$SP/p27spec/helper_new.py`).

### `conversion/mathcat_adapter.py` (tabs)

D6 and D7: add `_closed`, `close()`, the closed checks; delete the singleton. `get_default_mathcat_resource_root()` stays.

### `conversion/math_service.py` (tabs)

D7: the `mathcat` keyword on both functions; `mathml_to_nemeth_braille` calls `mathcat.get_braille_for_mathml(mathml_text, braille_code=braille_code, language=language)`. `translate_math_segment`'s logging and `MathConversionError` behavior do not change.

### `adapters/translation/mathcat.py` (4 spaces)

D8.

### `adapters/translation/provider.py` (4 spaces)

D9. The top-level import becomes `from conversion.mathcat_adapter import MathCATAdapter, MathCATError, get_default_mathcat_resource_root` (still no native loading at import). `create_default_text_translator` is not touched.

### Tests (4 spaces, except `tests/test_dual_view_frame.py`, which uses tabs)

See the Test Plan.

## Migration (characterization first)

Each step is one green commit. The plan fixes the exact split.

1. **Characterize** (green before any production change):
   - A new `client/tests/test_braille_glue.py` loads `vendor/nvda/liblouis/runtime/louis_helper.py` with a fake `braille.liblouis` (as in Current State; restores `sys.modules`, the `braille.liblouis` attribute and the root logger's handlers and level afterwards). It pins `_resolveTableInner`: a registered table resolves into its source's directory (driven by patching `braille.tables._tables` and `braille.tables._tablesDirs`, which both the old and the new helper read through), an unregistered name falls back to `TABLES_DIR` (patched to a temp dir), a `base` makes the search start in `dirname(base)`, and a missing table raises `LookupError` naming the folders searched.
   - `tests/test_translation_runtime_provider.py` gets a test that builds the default math translator with `platform="win32"` around a recording fake adapter, through one local helper, `default_math_translator(adapter)`. It is a context manager, because today `translate_math_segment` looks the singleton up on every call, so the patches must stay active while the test translates. Today the helper patches `provider.get_shared_mathcat_adapter` and `conversion.mathcat_adapter.get_shared_mathcat_adapter`; in step 4 only the helper body changes to `adapter_factory=`. It pins: `initialize()` once before any translation; `translate("1", braille_code="Nemeth", language="en")` calls `get_braille_for_mathml(latex_to_mathml("1"), braille_code="Nemeth", language="en")` and returns the fake's cells as one token.
2. **`braille.tables`** (D1, D4, D5) with its new tests.
3. **Helper adaptation** (D3): `sync-nvda.py`, the regenerated snapshot, the new `scripts/tests` and client tests.
4. **MathCAT injection** (D6-D10): adapter, math service, translator, provider and their tests. `tests/test_math_service.py` and `tests/test_translation_runtime_provider.py:248-255` change on purpose (they patched the deleted singleton) and pass `mathcat=`/`adapter_factory=` instead.
5. **Test log isolation** (D11).

## Test Plan

24 new client tests and 2 new scripts tests (client 1071 -> 1095, scripts 25 -> 27): step 1 adds 5, step 2 adds 4, step 3 adds 3 client and 2 scripts tests, step 4 adds 10, step 5 adds 2. All run on Linux unless marked. Throwaway mutant runs (not committed) show the tests catch 6 breakages of today's code (step 1), 4 of the snapshot and the directory lookup (step 3) and 7 of the new MathCAT lifecycle (step 4); the plan lists them.

**Characterization (step 1)**: the four resolver tests and the default-math-translator wiring test above.

**`braille.tables` (step 2)**, in `tests/test_braille_glue.py`:
- In a fresh interpreter (`subprocess`, like `test_translation_import_isolation.py`): after `import braille.tables`, `logging.root.handlers == []`, `logging.root.level == logging.WARNING`, and `braille.tables.log is logging.getLogger("braille.tables")`. Red before step 2.
- `get_table_directory(TableSource.BUILTIN) == TABLES_DIR`; an unknown source gives `None`; with `_tablesDirs` patched to a chain that has a child map, a source from the child map is found.
- `tests/test_braille_tables_default_lang.py` stays as is.

**Helper (step 3)**:
- `scripts/tests/test_sync_nvda_liblouis.py`: after `synchronize()` on the fixture, the adapted helper contains no `basicConfig`, contains `braille_tables.get_table_directory(registeredTable.source)` and no `_tablesDirs`. Red before step 3.
- A new scripts test: `_adapt_helper(<repo>/include/nvda/source/louisHelper.py)` equals `<repo>/vendor/nvda/liblouis/runtime/louis_helper.py` byte for byte. Skipped when the `include/nvda` submodule is not checked out. This already holds before the change and keeps the snapshot honest afterwards.
- `client/tests/test_braille_glue.py`, in a fresh interpreter: loading the vendor helper as `braille.louis_helper` with the fake `braille.liblouis` leaves the root logger with no handler at `WARNING`, `helper.log is logging.getLogger("braille.louis_helper")`, and `helper._isDebug()` is `False`. Red before step 3.
- AST check on the vendor helper and `braille/tables/__init__.py`: no call to an attribute named `basicConfig`, and the helper has no `_tablesDirs` attribute access.

**MathCAT (step 4)**:
- `tests/test_mathcat_adapter.py`: `close()` closes a fake DLL-directory handle exactly once even when called twice, and clears `_libmathcat`; after `close()`, `initialize()` and `get_braille_for_mathml()` raise `MathCATError` and `_load_libmathcat` is not called; `close()` on an adapter that was never initialized does not fail.
- `tests/test_math_translation_adapter.py`: `close()` calls the given callback; without one it is a no-op.
- `tests/test_translation_runtime_provider.py`: two calls to `create_default_math_translator(platform="win32", adapter_factory=...)` use two different adapters (no singleton); `runtime.close()` on a runtime built from the default factories (both injected) closes the MathCAT adapter once and before the text helper's `terminate()`; the existing `test_default_math_factory_normalizes_native_runtime_errors` passes, through `adapter_factory=`, a recording adapter whose `initialize()` raises `MathCATError`, and now also checks that adapter is closed once while the caller gets `RuntimeUnavailableError`; an adapter raising `ValueError` is closed and the `ValueError` propagates; `_create_mathcat_adapter()` returns a fresh `MathCATAdapter` on the bundled resource root on each call and is used when no factory is given.
- `tests/test_math_service.py`: the two existing tests pass a fake `mathcat=` instead of patching the singleton; one new test that `mathml_to_nemeth_braille` calls the given adapter with `braille_code` and `language`.

**Log isolation (step 5)**: a test for the helper (handlers and `propagate` put back exactly; works for a logger name that has no handlers yet); the four modules use it. Acceptance criterion 6 checks the effect.

## Acceptance Criteria

Run from the paths shown; `$SP`/`$PY` as above.

1. `cd client && $PY -m unittest discover -s tests`: only the known P2-5 failure; test count = 1071 + 24 = 1095; skips unchanged (9).
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`: every seed reports only the P2-5 failure.
3. From the repo root, `$PY -m unittest discover -s scripts/tests`: all pass (25 + 2 = 27).
4. From the repo root, `$PY $SP/p12/tools/msgid_scan.py client` reports `source msgids: 353`, same set.
5. Both fixture sha256 values are unchanged.
6. App data: the P2-6 snapshot (`$SP/p26impl/snap.sh`: `config.json`/`workspace/` existence, sha256 of every file under `dictionary/`, non-source entries of `dual_view/`, names in `log/`) is identical before and after criteria 1-2, **and** the sha256 of every file in `client/log/` is identical before and after (new: the suite no longer appends).
7. `git diff main --stat -- client/braille/tables/__tables.py vendor/nvda/liblouis/SOURCE.json vendor/nvda/liblouis/build vendor/nvda/liblouis/python vendor/nvda/mathcat` is empty, and the sha256 of the ignored `client/braille/liblouis/__init__.py` and `client/braille/louis_helper.py` are unchanged (record them before step 1). In a fresh clone the two ignored files are absent (only `scripts\install.bat` creates them); compare with what was recorded before step 1 either way.
8. `client/braille/tables/__init__.py` still has `\r\n` on every line, and `git diff main -- client/braille/tables/__init__.py` shows only the D1, D4 and D5 lines.
9. `command grep -rn "basicConfig\|_tablesDirs\.get\|get_shared_mathcat_adapter\|_SHARED_ADAPTER" client scripts vendor --include=*.py --exclude-dir=.venv` finds exactly: three tracked lines that match `_tablesDirs\.get` for good (`client/braille/tables/__init__.py`'s `return _tablesDirs.get(source)`, the body D5 prescribes; the NVDA-side marker `brailleTables._tablesDirs.get(...)` in `scripts/sync-nvda.py`, which `_adapt_helper` must still find in NVDA's source; and NVDA's verbatim copy `vendor/nvda/liblouis/python/louisHelper.py:53`, which criterion 7 forbids touching), test text that names `basicConfig` on purpose (`client/tests/test_braille_glue.py`, `scripts/tests/test_sync_nvda_liblouis.py`), and the two lines of the ignored, not-yet-reinstalled `client/braille/louis_helper.py` (until the Windows install refreshes it; absent in a fresh clone). Nothing matches `get_shared_mathcat_adapter` or `_SHARED_ADAPTER`.
10. `git diff main --stat` touches only: `client/braille/tables/__init__.py`, `scripts/sync-nvda.py`, `vendor/nvda/liblouis/runtime/louis_helper.py`, `client/conversion/mathcat_adapter.py`, `client/conversion/math_service.py`, `client/adapters/translation/mathcat.py`, `client/adapters/translation/provider.py`, the test modules named in the Test Plan (plus `client/tests/file_log_isolation.py` and the four modules from D11), `scripts/tests/test_sync_nvda_liblouis.py`, the new `scripts/tests/test_vendor_helper_snapshot.py`, and the spec and plan files.

## Windows Verification Debt (cannot run here)

- Refresh the generated helper: `scripts\install.bat` (or `scripts\clean-rebuild-dotexpress.bat`), then confirm `client\braille\louis_helper.py` equals `vendor\nvda\liblouis\runtime\louis_helper.py` (`fc /b`). Do not run `py scripts\sync-nvda.py` for this (it would revert `build/sconscript`).
- `cd client && python -m unittest tests.test_liblouis_runtime tests.test_translation_runtime_provider tests.test_mathcat_adapter tests.test_braille_glue -v` (the roadmap's command plus the adapter and glue tests). `test_table_resolver_finds_bundled_table` and `test_chinese_default_table_translates` go through `get_table_directory`.
- Source run (`python gui.py` in a console): the app starts, converts a document with Chinese, English and math, and exits without a traceback; the console no longer shows timestamped `INFO` lines from the root logger (expected, D2).
- Packaged build: convert the same document, compare the BRL output with a build from `main` (byte-identical), exit, and check `log\translation.log` has no new fallback warning and `log\math.log` no new error.
- Exit while a math conversion is running: no crash (the MathCAT adapter is now closed first; see Risks).

## Risks

- **Stale generated helper on a Windows checkout.** Until `scripts\install.bat` runs, `client\braille\louis_helper.py` is the old one: it still calls `basicConfig` and reads `_tablesDirs`. That keeps working, because `_tablesDirs` stays (it is still the store behind `get_table_directory`). The new helper needs the new `braille.tables`; both land in this branch, `braille.tables` first.
- **Packaging.** `client/braille/louis_helper.py` is collected by PyInstaller from the working copy, so a packaged build made without reinstalling ships the old helper. Same mitigation: install before packaging (`clean-rebuild-dotexpress.bat` does both).
- **Source-run console output changes** (D2). Only developer consoles are affected; documented.
- **Closing MathCAT while a conversion runs.** If `OnExit` ran while a worker thread was inside MathCAT, the closed adapter would make that segment fail with `MathConversionError` (logged to `math.log`) instead of finishing. The same race already exists for liblouis `terminate()`, and this task does not change when `OnExit` runs. Not checkable here; listed in the Windows debt.
- **Removing the DLL directory at close.** `libmathcat_py.pyd` and its dependencies are loaded by then, so removing the search-path entry does not unload them. Only checkable on Windows.
- **Resolver regression.** Production passes full table paths, so the changed line runs only for bare table names. The Linux tests drive the generated helper's resolver directly with a fake liblouis; the Windows runtime tests cover the real DLL.
- **Root-logger state in the test process.** The step-1 resolver tests load the old helper, which calls `basicConfig`; they restore the root logger's handlers and level. The red/green root checks run in a subprocess so earlier tests cannot mask them.

## Out of Scope / Follow-ups

- `sync-nvda.py` full run reverts the hand-edited `vendor/nvda/liblouis/build/sconscript` (`9aa8355`, `1bd19d7`). Fix by moving those edits into `_adapt_sconscript`, or by documenting that the sconscript is no longer synced.
- `louis_helper._resolveTable` calls `log.exception()` with no message (NVDA's logger accepts that, the stdlib one raises `TypeError`). It only matters when a table cannot be resolved; the callback returns `NULL` either way. Fix in `_adapt_helper` (for example `log.exception("Could not resolve braille tables")`) in a separate task.
- `__tables.py` `localedir` points at the missing `client/braille/locales` (P0 M-5, P2-3 showed no visible effect). Unchanged.
- An optional `liblouis.log` file through `log.get_logger` (D2): a product decision.
