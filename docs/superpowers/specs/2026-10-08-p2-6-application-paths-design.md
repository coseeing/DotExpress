# Application Paths Injection (P2-6) Design

## Goal

Stop resolving application data locations through module-level defaults. This is roadmap task P2-6 in `storage/refactor.md` (section 6.3), finding D-7 ("`app_paths` is called service-locator style by every module"), plus the P1 phase review's M-1 (`conversion/presenter.py` makes the `conversion` package depend back on `documents`).

After this task:

- `BrailleApp.OnInit` is the single composition root. It builds one `ApplicationPaths`, validates **that** object, cleans **its** `dual_view/`, builds one `config.ConfigStore(paths.config)` and passes both to `BrailleFrame` (and the store to client init). The frame no longer asks any module for a directory.
- `config.py` has a `ConfigStore` class that owns the config file path. `CONFIG_PATH` and the module-level config IO functions are gone.
- The five `app_paths.get_*_directory(path=None)`/`get_config_path` helpers are gone, and every `dictionary_dir`/`workspace_dir`/`directory` parameter in `dictionaries/manager.py`, `dictionaries/name_prompt.py`, `documents/workspace.py` and `dual_view/files.py` is required.
- `log.py` keeps resolving its directory implicitly (decision D10 explains why), through one private helper.
- `ConversionPresenter` moves from `conversion/presenter.py` to `ui/conversion_presenter.py`, and a guard test keeps `conversion` from importing `documents`, `ui`, `gui` and the other higher layers.

This is a pure refactor. Every file lands where it lands today, the startup check order and error dialog are the same, the bytes written to `config.json` are the same, the log files and messages are the same, nothing new is shown or spoken, and no msgid changes (353, same set). The golden fixtures `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`) do not change. No user-visible change is needed, so nothing is escalated.

## Contract kept from 2026-07-20

`docs/superpowers/specs/2026-07-20-external-dual-view-and-app-data-paths-design.md` is the path contract. This task changes who holds the paths, not the contract:

- Root: `Path(sys.executable).resolve().parent` when frozen (PyInstaller `--onefile`, so this is the folder holding `DotExpress.exe`, not the `_MEIPASS` unpack folder), otherwise the `client/` folder. `get_application_root()` is not touched.
- Layout: `<root>/config.json`, `dictionary/`, `workspace/`, `log/`, `dual_view/`. `build_application_paths()` is not touched.
- Startup order: validate the root and every managed folder (mkdir + probe file), then append-open an existing `config.json`, then remove leftover `dual-view-*.html`, and only then build the translation runtime and the main frame. Any failure shows the localized "cannot write to its application data directory" error with the failing path and stops before the runtime. No fallback location.
- Loggers: importing a module creates no folder and opens no file (`FileHandler(delay=True)`); log files live under `<root>/log/`.
- Shutdown: remove owned `dual-view-*.html`; a failure is logged and the runtime is still closed.
- Read-only bundled resources (`i18n.resource_path`, `braille/tables/__tables.py`, `conversion/mathcat_adapter.py`, `main.BASE_DIR / "data"`) are not application data and stay outside `ApplicationPaths`.

## Current State (verified 2026-10-08 on `refactor/p2-6-application-paths`, HEAD `f1ff5b3`, P0-*, P1-*, P2-1..P2-4 merged)

Indentation: `gui.py` and `dictionaries/name_prompt.py` use tabs. `app_paths.py`, `config.py`, `log.py`, `main.py`, `client_init.py`, `settings/*.py`, `dictionaries/manager.py`, `documents/*.py`, `dual_view/files.py`, `conversion/presenter.py` and all touched test modules use 4 spaces.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1043 tests`, `FAILED (failures=1, skipped=9)`; the failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. Shuffle seeds 1 and 2 give the same single failure. Msgid scan (`cd /workspace/DotExpress && $PY $SP/p12/tools/msgid_scan.py client`) reports `source msgids: 353`. After the suite, `client/config.json` and `client/workspace/` do not exist (no test writes real app data). (`$PY` = `$SP/venv/bin/python`, `$SP` = the session scratchpad.)

The line numbers in `storage/refactor.md` predate P0-P2-4. These are the current ones.

### `app_paths.py`

- `ApplicationPaths` (11-22): frozen dataclass `root, config, dictionary, workspace, log, dual_view` and `writable_directories`.
- `get_application_root()` (32-35), `build_application_paths(root=None)` (38-47).
- `get_config_path`, `get_dictionary_directory`, `get_workspace_directory`, `get_log_directory`, `get_dual_view_directory` (50-67): each `return Path(path) if path is not None else build_application_paths().<field>`.
- `prepare_application_directories(paths=None, *, probe_factory)` (70-89): `paths or build_application_paths()`; wraps every `OSError` in `ApplicationDataError`.

### Who resolves a path by default

| Caller | What it does today |
| --- | --- |
| `config.py:15` | `CONFIG_PATH = str(get_config_path())`, fixed at import. `_load_from_file` (63-82) and `_save_to_file` (85-98) read the global at call time. |
| `log.py:17` | `get_log_directory() / name` inside `get_logger`, evaluated when each module creates its logger at import. |
| `gui.py:138` | `self.dictionary_dir = get_dictionary_directory()` (imported through `dictionaries.manager`, `gui.py:17`). |
| `gui.py:147` | `DocumentWorkspaceService(controller, get_workspace_directory())` (imported through `documents.workspace`, `gui.py:30`). |
| `gui.py:334` | `write_dual_view_html(html)` with the default folder. |
| `gui.py:1074` | `OnExit`: `cleanup_dual_view_html()` with the default folder. |
| `gui.py:1056` | `OnInit`: `paths = prepare_application_directories()`, then `cleanup_dual_view_html(paths.dual_view)`; `paths` is then dropped. |
| `main.py:23` | demo: `get_dictionary_directory() / "default.csv"`. |
| `dictionaries/manager.py:15-101` | `dictionary_path_for_name`, `ensure_default_dictionary`, `list_dictionary_names` default `dictionary_dir=None`; `create/import/rename/export/delete_dictionary` take `Path | None`; all go through `get_dictionary_directory(dictionary_dir)`. |
| `dictionaries/name_prompt.py:33-42` | `rename_dictionary_after_name_prompt(dictionary_dir: Path | None, ...)`. |
| `documents/workspace.py:37-48, 132` | `ensure_workspace_directory`, `document_package_path_for_name`, `load_workspace_documents` default `workspace_dir=None`. |
| `dual_view/files.py:17-36` | `write_dual_view_html(content, directory=None, *, token_factory)`, `cleanup_dual_view_html(directory=None)`. |

Every production caller except the ones listed above already passes an explicit folder (`DictionaryManagementPresenter`, `DocumentWorkspaceService`, `conversion/output.py:62`). Every test passes an explicit folder too, except `tests/test_app_paths.py:106-115`, which calls the defaults on purpose.

### Who reads `config.py`

- `settings/translation.py` (`get/set_output_mode`, `get/set_conversion_width`, `get/set_selected_dictionary`), `settings/view.py` (`get_view_font_size`, `get_view_scheme`, `get_braille_font`, `set_view_settings`), `settings/translation_tables.py` (`get/set_translation_tables`). Only `gui.py` calls their `load_*`/`save_*` (`gui.py:145, 146, 151, 422-424, 557`).
- `gui.py:433` `set_selected_dictionary`, `gui.py:530-531` `get_lang()`/`get_charset_maps()` once per conversion request (the P1-1 read pattern).
- `client_init.py:14, 147-149`: `run_client_init` defaults `client_id_provider=get_or_create_client_id`, `locale_provider=get_lang`; both run inside the background worker (`start_client_init_background`, 160-173).
- `main.py:5, 30-31` demo.
- `conversion/service.py`, `conversion/math_service.py` and many tests import only constants (`DEFAULT_*`, `*_KEY`, `LANG_ENV`).
- `set_lang` (159-165) has no production caller; `_runtime_lang` (47) is therefore always `None` in the app. `tests/test_conversion_language_explicit.py:63-89` sets `config._runtime_lang = "ko"` and patches `config.get_lang`/`config.get_charset_maps` to raise, to prove conversion never reads config.
- P0-1 behavior: a save to a missing file injects `{"language_detection": {"charset_maps": DEFAULT_CHARSET_MAPS}}` first (88-93); read failures log one `WARNING` per path per distinct failure signature (`_logged_load_failures`, 50, keyed by path string); every save failure logs an `ERROR`; a log handler that cannot open its file never raises (`_log_current_exception`, 53-60); all IO catches stay `except Exception`.

### Loggers created at import

`config.py:11`, `client_init.py:17`, `gui.py:103`, `ui/dual_view.py:13`, `adapters/translation/provider.py:13`, `conversion/math_service.py:10`. All of them exist before `OnInit` runs.

### Startup (`gui.py:1053-1080`)

`OnInit`: `prepare_application_directories()` -> `cleanup_dual_view_html(paths.dual_view)` -> (on `ApplicationDataError`: dialog, `return False`; on other `OSError`: `ApplicationDataError(paths.dual_view, cause)`, dialog, `return False`) -> `build_default_translation_runtime()` -> `BrailleFrame(None, runtime=...)` -> `Show()` -> `start_client_init_background()` -> `True`. `OnExit`: `cleanup_dual_view_html()` (logged on `OSError`), then `runtime.close()`. wx calls `OnExit` only after `OnInit` returned `True`.

If `prepare_application_directories` itself ever raised a plain `OSError`, the `except OSError` branch would hit an unbound `paths` (`storage/refactor.md` 5.3). Today it cannot, because `prepare_application_directories` wraps every `OSError`.

### M-1: `conversion` -> `documents`

`conversion/presenter.py:31-32` imports `documents.controller.DocumentController` and `documents.workspace.Document`; `documents/formats.py:8` imports `conversion.math_service`. No module-level cycle, but the packages depend on each other. No other `conversion` module imports `documents`, `ui`, `gui`, `dialog`, `settings`, `dictionaries` or `dual_view` (AST scan, including function-level imports). `ConversionPresenter` is imported by `gui.py:14`, `tests/test_conversion_presenter.py:7` (its AST guard reads `PRESENTER_PATH`), `tests/test_export_coordinator.py:11`; `documents/export_coordinator.py:40` and `gui.py:965` name it in a docstring and a comment.

### Tests that patch paths or `CONFIG_PATH`

- `CONFIG_PATH` reassigned in `setUp`: `tests/test_config.py` (3 classes), `tests/test_view_settings.py`, `tests/test_translation_tables.py`, `tests/test_translation_settings.py`; read back in `tests/test_app_paths.py:113`.
- `patch.object(gui, "get_dictionary_directory" | "get_workspace_directory")`: four `_initialize_state` tests in `tests/test_gui_document_flows.py` (`test_initialize_state_keeps_the_frame_controller`, `test_initialize_state_creates_service_for_frame_controller`, `_initialize_state_with_loaded_tables`, `test_initialize_state_wires_presenter_to_active_dictionary`).
- `patch.object(gui, "prepare_application_directories")`: five `BrailleAppLifecycleTest` tests; `test_app_validates_application_data_before_building_runtime` uses a zero-argument `side_effect`. Three `OnExit` tests patch `gui.cleanup_dual_view_html`, one asserts the failure is logged.
- `patch.object(gui, "get_lang"/"get_charset_maps"/"set_selected_dictionary"/"save_view_settings"/...)`: `test_conversion_request_copies_frame_translation_tables`, `test_initialize_state_wires_presenter_to_active_dictionary`, the six P2-4 `ViewFontSizeSyncCharacterizationTest` tests (`save.assert_called_once_with(expected)`), two `apply_settings_from_dialog` tests.
- `test_dual_view_menu_opens_rendered_html_with_main_window_size` asserts `write_html.assert_called_once_with("<html>dual</html>")`.
- `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` keeps `"get_dictionary_directory"` in its "kept" list (P0-6 guard).
- `DocumentControllerOwnershipTest.test_frame_creates_its_controller_before_building_the_menu_bar` constructs `gui.BrailleFrame(None, runtime=Mock())`.
- `tests/test_log.py` patches `log.get_logger`'s `get_log_directory`; `tests/test_main_demo.py` patches `main.get_dictionary_directory`, `main.get_lang`, `main.get_charset_maps`.

## Design

### Decision summary

| # | Decision | Why |
| --- | --- | --- |
| D1 | `BrailleApp.OnInit` is the composition root: `paths = build_application_paths()`, `self.paths = paths`, then the unchanged `try` (validate `paths`, clean `paths.dual_view`), then `config_store = ConfigStore(paths.config)`, runtime, `BrailleFrame(None, runtime=..., paths=paths, config_store=config_store)`, `Show()`, `start_client_init_background(config_store)`. | One object is validated and used everywhere, which is what D-7 asks for. `build_application_paths()` and `ConfigStore(...)` do no IO, so the observable order (validate, clean, runtime, frame, show, client init) is the 2026-07-20 order. Binding `paths` before the `try` also removes the unbound-name hazard in the `except OSError` branch without changing any reachable path. |
| D2 | `config.ConfigStore(path)` with one public method per current module function, same names, parameters, defaults, return values and file format. The constructor stores `Path(path)` and does no IO. Every getter still re-reads the file; nothing is cached. | Smallest faithful move of the module functions. P1-1 relies on `get_lang`/`get_charset_maps` being read once per conversion request, which stays true. The S-5 repository shape (`load`/`save`/`update`, batching `save_translation_settings` into one write, narrowing the catches) is a separate change and is out of scope (P0-1 deferred it). |
| D3 | `_logged_load_failures`, `logger` and `_log_current_exception` stay module-level in `config.py`; the throttle stays keyed by `str(path)`. | The P0-1 rule is "one warning per path per distinct failure per process". Keying the shared dict by path keeps that true no matter how many stores point at the same file (the app, the demo, tests). Tests keep patching `config.logger` and clearing `config._logged_load_failures`. |
| D4 | `_runtime_lang` stays module-level; `set_lang(lang, persist=False)` becomes `ConfigStore.set_lang` with the same body; `get_lang` keeps the order runtime override, `TEXT2BRAILLE_LANG`, file `"language"`, `"zh_TW"`. | The override is process state, not path state. Removing `set_lang`/`_runtime_lang` is S-5 work (P0-1 recorded it) and would also change the guard in `tests/test_conversion_language_explicit.py`. |
| D5 | `CONFIG_PATH` and every module-level `get_*`/`set_*` config function are deleted, no aliases, no default store. | A default store would keep exactly the module-global path this task removes, and would let tests patch one config source while code reads another. All production callers are within reach: `gui.py`, `main.py` (both composition roots), `client_init.py` and the three `settings` modules, each a one-parameter change. |
| D6 | The settings functions take the store first: `load_translation_settings(store, dictionary_names)`, `save_translation_settings(store, settings)`, `load_view_settings(store)`, `save_view_settings(store, settings)`, `load_translation_tables(store)`, `save_translation_tables(store, tables)`. Bodies call the same store methods in the same order (three writes for translation settings, one for view, one for tables). | Resource-first matches `create_dictionary(dictionary_dir, name)`. Same writes in the same order means the same `config.json` bytes, including the first-save `language_detection` injection. `settings/__init__.py` re-exports the same names. |
| D7 | `start_client_init_background(config_store, *, run_client_init=run_client_init, thread_factory=threading.Thread)`. The worker calls `run_client_init(client_id_provider=config_store.get_or_create_client_id, locale_provider=config_store.get_lang)`. In `run_client_init` those two providers become required keyword-only parameters. `client_init.py` no longer imports `config`. | The client id and locale are still read (and the id still created and saved) inside the worker thread, as today. Exceptions are still swallowed by the worker. |
| D8 | `BrailleFrame.__init__(self, *args, runtime, paths, config_store, **kwargs)`: all three keyword-only and required. The frame stores `self._paths` and `self._config_store` next to `translation_runtime`, before `_initialize_frame()`. `self.dictionary_dir` stays (set from `self._paths.dictionary`). | Mirrors the existing `runtime` injection the review points to. `dictionary_dir` is read by `on_open_text_processing`, `_get_selected_dictionary_path` and 14 test sites; keeping it avoids churn without adding a second source of truth. |
| D9 | `app_paths` keeps `ApplicationPaths`, `ApplicationDataError`, `get_application_root`, `build_application_paths(root=None)` and `prepare_application_directories(paths, *, probe_factory)`, with `paths` now required. The five `get_*` helpers are deleted. | `build_application_paths()` with no root means "resolve the real root". It is the one legitimate implicit call, and a guard limits it to `gui.py`, `main.py` and `log.py`. |
| D10 | `log.py` keeps implicit resolution, through a private `_log_directory()` that returns `build_application_paths().log`. It is evaluated inside `get_logger`, as `get_log_directory()` is today. | Six modules create their logger at import, before any composition root exists. Injecting the folder would mean re-pointing handlers after `OnInit` or creating loggers lazily, which changes when and where log files are bound, which is what the 2026-07-20 contract pins. Because the resolver is the same function `OnInit` uses, the handler folder equals the validated `paths.log`; a test pins that. |
| D11 | Every directory parameter in `dictionaries/manager.py`, `dictionaries/name_prompt.py`, `documents/workspace.py` and `dual_view/files.py` becomes required and typed `Path` (call sites may still pass `str`; bodies use `Path(x)`). `write_dual_view_html(content, directory, *, token_factory=...)` keeps `directory` second and positional. | `Path(x)` is what `get_*_directory(x)` returned for any non-`None` `x`, so results are identical. No production or test caller passes `None`. |
| D12 | `main.run_demo` is its own composition root: `paths = build_application_paths()`, `config_store = ConfigStore(paths.config)`, dictionary `paths.dictionary / "default.csv"`, `lang=config_store.get_lang()`, `charset_maps=config_store.get_charset_maps()`. It still does not validate folders. | Same files and same reads as today. The demo never ran the startup check and still does not. |
| D13 | M-1: `git mv client/conversion/presenter.py client/ui/conversion_presenter.py`. The module body does not change (its docstring may mention its new home). No re-export left in `conversion/`. An AST guard forbids `conversion/**` from importing `documents`, `ui`, `gui`, `dialog`, `settings`, `dictionaries` and `dual_view`. | The presenter is the main window's conversion coordinator (busy state, converting-dialog timer, translated messages, writing results into `DocumentController`), so it belongs on the UI side, like the wx-free `ui/menu_builder.py` and `ui/action_menu.py`, which already import `documents`. Not a new `app/` package: it would hold one module, and `server/app` already uses that name. Not `documents/`: that would widen `documents` -> `conversion` with jobs, service and runtime. Not a Protocol inversion inside `conversion/`: the dependency would go away but the coordinator would stay in a domain package. A shim would keep the edge M-1 is about. The AST check also catches function-level imports, which a `sys.modules` check would miss. |

### `app_paths.py` (4 spaces)

- Delete `get_config_path`, `get_dictionary_directory`, `get_workspace_directory`, `get_log_directory`, `get_dual_view_directory`.
- `prepare_application_directories(paths: ApplicationPaths, *, probe_factory=tempfile.TemporaryFile)`; the body uses `paths` directly. Nothing else changes.

### `config.py` (4 spaces)

Kept at module level: the imports minus `get_config_path`, `logger`, every constant (`DEFAULT_*`, `*_SECTION`, `*_KEY`, `LANG_ENV`, `DEFAULT_FALLBACK`, `DEFAULT_CHARSET_MAPS`, the re-exported math names), `_runtime_lang`, `_logged_load_failures`, `_log_current_exception`, `_coerce_int`, `_get_section`.

New:

```python
class ConfigStore:
    """config.json at one path. Each getter re-reads the file; nothing is cached."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict: ...          # body of _load_from_file; key = str(self._path)
    def _save(self, data: dict) -> None: ...  # body of _save_to_file, incl. the first-save injection
    def _set_section_value(self, section, key, value) -> None: ...
    def _get_dict_setting(self, section, key, default) -> dict: ...

    def get_lang(self) -> str: ...
    def get_charset_maps(self) -> dict[str, str]: ...
    def set_lang(self, lang: str, persist: bool = False) -> None: ...   # sets module _runtime_lang
    def get_translation_tables(self) -> dict: ...
    def set_translation_tables(self, tables: dict[str, str]) -> None: ...
    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str: ...
    def set_output_mode(self, output_mode: str) -> None: ...
    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int: ...
    def set_conversion_width(self, width: int) -> None: ...
    def get_selected_dictionary(self, default: str = "default") -> str: ...
    def set_selected_dictionary(self, dictionary_name: str) -> None: ...
    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int: ...
    def get_view_scheme(self, default: str = DEFAULT_VIEW_SCHEME) -> str: ...
    def get_braille_font(self, default: str = DEFAULT_BRAILLE_FONT) -> str: ...
    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> None: ...
    def get_or_create_client_id(self) -> str: ...
```

Each method body is the current function body with `_load_from_file()`/`_save_to_file()`/`CONFIG_PATH` replaced by `self._load()`/`self._save()`/`self._path`. `_save` still uses `os.path.exists`, `os.makedirs(os.path.dirname(...), exist_ok=True)`, `json.dump(data, f, ensure_ascii=False, indent=2)`, and passes `str(self._path)` to the log calls, so the messages are character-for-character the same. The class lives in `config.py` (the roadmap names `config.ConfigStore`); `settings/options.py`'s note about the `config` -> `settings` import cycle stays true.

### `log.py` (4 spaces)

```python
from app_paths import build_application_paths


def _log_directory() -> Path:
    return build_application_paths().log
```

`get_logger` uses `_log_directory() / Path(filename).name`. Signature, `delay=True`, levels, formatter and `propagate = False` do not change.

### `gui.py` (tabs)

- Imports: `from app_paths import ApplicationDataError, ApplicationPaths, build_application_paths, prepare_application_directories`; `from config import ConfigStore, DEFAULT_TRANSLATION_TABLES`; `from dictionaries.manager import dictionary_path_for_name`; drop `get_workspace_directory`, `get_lang`, `get_charset_maps`, `set_selected_dictionary`; `from ui.conversion_presenter import ConversionPresenter` (step 5).
- `BrailleFrame.__init__` per D8.
- `_initialize_state`: `self.dictionary_dir = self._paths.dictionary`; `load_translation_settings(self._config_store, names)`; `load_translation_tables(self._config_store)`; `DocumentWorkspaceService(self._document_controller, self._paths.workspace)`; `load_view_settings(self._config_store)`. Same order as today.
- `_open_dual_view_in_browser`: `write_dual_view_html(self._render_dual_view_for_open_document(), self._paths.dual_view)`.
- `apply_settings_from_dialog` and `_set_view_font_size`: `save_*(self._config_store, ...)`, same order.
- `_set_active_dictionary`: `self._config_store.set_selected_dictionary(selected_name)`.
- `_build_conversion_request`: `lang=self._config_store.get_lang()`, `charset_maps=self._config_store.get_charset_maps()`.
- `BrailleApp.OnInit` per D1. The two `except` branches and `_show_application_data_error` do not change.
- `BrailleApp.OnExit`: `paths = getattr(self, "paths", None)`; when not `None`, `cleanup_dual_view_html(paths.dual_view)` inside the same `try`/`except OSError`/`logger.exception("Failed to clean up dual-view HTML")`; then the runtime is closed as today. In the product `self.paths` is always set (wx only calls `OnExit` after a successful `OnInit`); the `None` case exists only for tests that call `OnExit` on a bare app.
- The `# --- ConversionView (conversion/presenter.py)` comment points at `ui/conversion_presenter.py`.

### Other modules

- `settings/translation.py`, `settings/view.py`, `settings/translation_tables.py`: per D6; import `ConfigStore` for the annotation and keep importing the constants.
- `client_init.py`: per D7.
- `main.py`: per D12; imports `build_application_paths` and `ConfigStore`.
- `dictionaries/manager.py`, `dictionaries/name_prompt.py`, `documents/workspace.py`, `dual_view/files.py`: per D11; drop the `app_paths` imports.
- `documents/export_coordinator.py:40`: the docstring names `ui.conversion_presenter.ConversionPresenter`.

## What Stays Identical

Every file location (root, `config.json`, the four folders, log files, dual-view HTML names). The startup sequence, which checks run, what stops startup and the error dialog text. Shutdown cleanup and its log line. The exact `config.json` content after every setter, including the first-save `language_detection` injection, key order, `ensure_ascii=False` and `indent=2`. Load and save logging, its level, message, `exc_info`, throttling, and that a broken log folder never raises. What `get_lang` returns in every case. When the client id is created and from which thread. How often the config file is read per conversion. The msgid set and the fixtures. No visible or spoken change, so no screenshot is needed.

## Test Plan

### A. Characterization on current code (step 1)

These pass on today's code. Each group reaches the code under test through one small test helper. Steps 3-4 change only the helpers, never the assertions. The helpers point everything at a temporary root: on today's code by patching `app_paths.get_application_root` (which redirects every `get_*_directory()` call, because they resolve the root at call time) and `config.CONFIG_PATH` (fixed at import); after the switch by building `build_application_paths(root)` and `ConfigStore(root / "config.json")` and passing them in.

1. `tests/test_gui_document_flows.py`, new class `ApplicationPathsWiringCharacterizationTest`:
   - `_initialize_state` on a frame from `object.__new__` (real `DictionaryManagementPresenter`, real settings loaders, `_register_output_font` mocked): `frame.dictionary_dir == root / "dictionary"`, `root/dictionary/default.csv` exists, `frame._workspace_service.workspace_dir == root / "workspace"`, and settings pre-written to `root/config.json` are loaded (output mode, width, selected dictionary, view settings, tables).
   - `_set_active_dictionary("default")` on a fresh root writes `root/config.json` whose first key is `language_detection` and whose `conversion.selected_dictionary` is `"default"`.
   - `_open_dual_view_in_browser` with `open_html_in_browser` patched writes one `dual-view-*.html` under `root/dual_view` and passes that path to the browser helper.
   - `_build_conversion_request` with `TEXT2BRAILLE_LANG` removed from the environment and `{"language": "en", "language_detection": {"charset_maps": {...}}}` in `root/config.json`: `request.lang == "en"` and the charset maps merge as today. Two requests read the file twice (a counting wrapper around `open` for the config path, installed by the helper), so nothing is cached.
2. Same file, `BrailleAppLifecycleTest` gains `test_app_startup_runs_steps_in_contract_order`: recording fakes for `prepare_application_directories`, `cleanup_dual_view_html`, `build_default_translation_runtime`, `BrailleFrame` (its `Show`) and `start_client_init_background` give `["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`. And `test_app_stops_before_cleanup_when_validation_fails`: on `ApplicationDataError` there is no cleanup, runtime, frame or client init. The fakes accept any arguments, so the test survives the new signatures.
3. `tests/test_client_init.py`, new `ClientInitConfigCharacterizationTest`: with a synchronous `thread_factory` and a fake `opener`, starting background client init against an empty root creates a UUID client id, saves it in `root/config.json`, and sends it; a second start sends the same id; `"language": "ja"` in the file is sent as `locale`. The helper wraps today's `start_client_init_background(run_client_init=partial(run_client_init, opener=fake))` (with `CONFIG_PATH` patched) and later `start_client_init_background(ConfigStore(...), run_client_init=partial(...))`.
4. `tests/test_log.py`: `test_default_log_directory_follows_the_application_root`: with `app_paths.get_application_root` patched to a temp root, a new logger's `baseFilename` is `root/log/<name>`, `root/log` is not created, and it equals `build_application_paths().log / <name>` under the same patch. Survives unchanged.
5. `tests/test_main_demo.py`: `test_demo_reads_dictionary_and_language_from_the_application_root`: with the root patched and `{"language": "en"}` in `root/config.json`, the request's `dictionary_path` is `root/dictionary/default.csv` and `lang == "en"`.
6. `tests/test_config.py`, new `ConfigLanguageOverrideCharacterizationTest`: `set_lang("ja")` makes `get_lang()` return `"ja"` over `TEXT2BRAILLE_LANG` and the file, without writing the file; `set_lang("en", persist=True)` writes top-level `"language": "en"` with the first-save injection. Restores `_runtime_lang` with `addCleanup`. Reached through a `make_store(path)` helper (step 1: an adapter object whose methods patch `config.CONFIG_PATH` around the module function; step 2 on: `config.ConfigStore(path)`).

A throwaway mutant runner (not committed) applies one-edit breakages to a copy of `client/` (frame dictionary folder from `Path.cwd()`, dual-view HTML written to the workspace folder, cleanup before validation, runtime before cleanup, client id read on the UI thread, `language_detection` injection dropped, `get_lang` cached, logger folder resolved from `Path.cwd()`) and shows part A catches each. The plan lists the exact mutants.

### B. `ConfigStore` (step 2, additive)

`tests/test_config.py` gains `ConfigStoreTest`:
- The constructor creates no file or folder and logs nothing (`patch.object(config, "logger")`, `mock_calls == []`), for a path whose parent does not exist.
- `store.path == Path(given)` for `str` and `Path` input.
- Two stores on the same corrupt file log one warning in total; stores on two corrupt files log one each (D3).
- A store and the module functions (still present in step 2) produce byte-identical `config.json` for the same sequence of setters from a missing file.

In step 2 the module functions become one-line delegates to `ConfigStore(CONFIG_PATH)` built at call time, so every existing `CONFIG_PATH` test still runs unchanged against the store code.

### C. Switch and guards (steps 3-5)

- Step 3 moves `tests/test_config.py`, `test_view_settings.py`, `test_translation_tables.py`, `test_translation_settings.py` from `CONFIG_PATH` reassignment to `self.store = config.ConfigStore(tmp / "config.json")` and store or settings calls; assertions on file content stay. `test_conversion_language_explicit.py` patches `config.ConfigStore.get_lang` and `config.ConfigStore.get_charset_maps` to raise (same guard, any store). Frame factories in `test_gui_document_flows.py` set `frame._paths` and `frame._config_store` (a real store on a temp root where a test writes, `Mock(spec=config.ConfigStore)` elsewhere); assertions that named a patched module function name the store instead (for example `save.assert_called_once_with(frame._config_store, expected)`, `frame._config_store.set_selected_dictionary.assert_called_once_with("default")`, `write_html.assert_called_once_with("<html>dual</html>", frame._paths.dual_view)`). `BrailleAppLifecycleTest` patches `gui.build_application_paths` to return temp-root paths; the zero-argument `side_effect` takes `paths`; `frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=ANY)`; `OnExit` tests set `app.paths`.
- New in step 3: `test_app_passes_the_validated_paths_and_one_store`: the object given to `prepare_application_directories` is the one given to `BrailleFrame` and stored as `app.paths`; one `ConfigStore` with `path == paths.config` reaches both the frame and `start_client_init_background`; the store is built after cleanup and before the runtime. `test_app_exit_cleans_the_validated_dual_view_folder`. `test_frame_requires_paths_and_config_store` (keyword-only, no default, via `inspect.signature`).
- Step 4 guards, written as allow-lists so they never spell a removed name (P2-4 lesson):
  - `tests/test_app_paths.py` `ApplicationPathsApiTest`: the public functions of `app_paths` are exactly `{"get_application_root", "build_application_paths", "prepare_application_directories"}`; `prepare_application_directories`'s `paths` has no default.
  - Same class: for each function listed in D11, `inspect.signature` shows the folder parameter with no default.
  - Same class: an AST scan of `client/**/*.py` (excluding `tests/`, `.venv/`, `braille/liblouis/`, `__pycache__`) finds calls of `build_application_paths` with no arguments only in `gui.py`, `main.py` and `log.py`.
  - `test_consumers_use_the_common_application_root` is rewritten to `build_application_paths(root)` and checks the store and the frame helpers built from it.
  - `tests/test_config.py` `ConfigModuleShapeTest`: no module attribute of `config` starts with `get_` or `set_`, and the names containing `PATH` are none.
  - `tests/test_translation_import_isolation.py`: `test_client_init_does_not_import_config` (subprocess, like its neighbors).
  - `tests/test_gui_document_flows.py`: `"get_dictionary_directory"` leaves the "kept" list of `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` (intentional guard change, called out in the commit message).
  - `tests/test_log.py`: the existing test patches `log._log_directory`.
- Step 5 (M-1): `tests/test_conversion_presenter.py` imports from `ui.conversion_presenter` and its `PRESENTER_PATH` points at `client/ui/conversion_presenter.py` (the wx/gui/dialog AST guard stays); `tests/test_export_coordinator.py` import updated. New `tests/test_translation_import_isolation.py::test_conversion_package_imports_no_higher_layer`: AST over every `client/conversion/**/*.py`, top-level name of every `import`/`from` (absolute, any nesting) not in `{"documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}`. Red before the move (it names `conversion/presenter.py`), green after.

The plan fixes the exact new-test count.

## Migration Steps (each step one green commit)

1. `test: characterize application paths wiring` (part A, helpers on today's seams).
2. `refactor: add config store behind the config functions` (`ConfigStore`, module functions delegate per call, part B).
3. `refactor: inject application paths and config store at startup` (`OnInit`, `BrailleFrame`, settings modules, `client_init`, `main`; config tests to the store API; part A helpers switched; step 3 tests).
4. `refactor: remove implicit application path defaults` (delete the `app_paths` helpers, the `None` defaults, `CONFIG_PATH` and the module config functions; `log._log_directory`; step 4 guards).
5. `refactor: move conversion presenter to ui` (D13, its guard).

## Acceptance Criteria

1. Roadmap verification on Linux: `cd client && $PY -m unittest tests.test_app_paths tests.test_config tests.test_gui_document_flows -v` passes. Also green: `tests.test_log tests.test_main_demo tests.test_client_init tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_conversion_presenter tests.test_export_coordinator tests.test_translation_import_isolation tests.test_dictionary_manager tests.test_dictionary_name_prompt tests.test_document_workspace tests.test_workspace_service tests.test_dual_view_files tests.test_removed_dead_code tests.test_i18n tests.test_wx_stub`.
2. Full suite: `Ran` = 1043 + the new tests, `failures=1` (the P2-5 case only), `errors=0`, `skipped=9`.
3. Shuffle harness: `cd client && for s in $(seq 0 19); do $PY $SP/shuffle_harness.py $s; done` gives exactly one failure for every seed, the P2-5 case. `test_config`, `test_gui_document_flows` and `test_app_paths` pass alone and in both orders of each pair.
4. Msgid scan from the repo root reports `source msgids: 353`, the same set as `main`. `git diff main --stat -- client/locales` is empty.
5. Both fixture sha256 values above are unchanged and `git diff main -- client/tests/fixtures` is empty.
6. Greps (all `--include=*.py --exclude-dir=.venv`, over `client`): `CONFIG_PATH` prints nothing; `get_config_path\|get_dictionary_directory\|get_workspace_directory\|get_log_directory\|get_dual_view_directory` prints nothing; `grep -rnE "(_dir|directory|paths): (Path|ApplicationPaths) \| None" client/app_paths.py client/dictionaries client/documents/workspace.py client/dual_view/files.py` prints nothing (the only remaining optional root, `build_application_paths(root: Path | None = None)`, does not match; today it prints 15 lines); `conversion.presenter\|conversion/presenter` prints nothing; `grep -rn "documents" client/conversion --include=*.py` prints no import line; `client/conversion/presenter.py` does not exist.
7. After the full suite, `client/config.json` and `client/workspace/` still do not exist.
8. `git diff main --stat` touches only the modules named in this spec, the test modules named in the Test Plan and the two spec files plus the plan.

## Risks

- **Large test edit in `test_gui_document_flows.py`.** About 30 sites move from patched module functions to frame attributes. Mitigation: part A pins the behavior through helpers first; `Mock(spec=config.ConfigStore)` makes a misspelled store method fail.
- **A frame built with `object.__new__` and no `_config_store`.** Any test that reaches a save or a conversion request without setting it gets `AttributeError`. Both frame factories set it; the full suite and shuffles cover it.
- **Stub-scope class identity.** Scopes with `evict_everything` can re-import `config`, giving a second `ConfigStore` class and a second `_logged_load_failures`. Production code does no `isinstance` on `ConfigStore`; tests patch the class they imported. Covered by the shuffles.
- **Two config readers on two threads.** The UI and the client-init worker share one store. The store holds only an immutable path, so sharing is as safe as today's module functions. The pre-existing read-modify-write race between `get_or_create_client_id` and a UI save is unchanged (not fixed, see quirks).
- **Hidden caller of a deleted name.** Out-of-repo scripts that import `config.get_lang` or `app_paths.get_*` would break. Repo-wide grep shows none (`server/` does not import client modules; the `import config` in `scripts/sync-nvda.py` is NVDA's module, which that script strips).
- **PyInstaller.** The moved presenter is reached by a static import from `gui.py`, so `--onefile` picks it up. Not buildable here (Windows debt).

## Known quirks kept (pinned or recorded, not fixed)

1. In development mode `client/dual_view/` is both the `dual_view` Python package and the dual-view HTML folder. Cleanup only removes `dual-view-*.html`, so source files are safe. Part A item 1 writes into a temp root and does not touch it.
2. `get_or_create_client_id` (worker thread) and UI saves both read-modify-write `config.json` without a lock; a save landing between them can drop one side's change. Pre-existing, not pinned (timing-dependent).
3. `set_lang` has no production caller and `_runtime_lang` is always `None` in the app. Kept for S-5.
4. `save_translation_settings` still writes the file three times. Kept for S-5.

## Windows verification debt

Not runnable on this Linux box: build with `scripts\build-dotexpress.bat` and run the exe from a writable folder: `config.json`, `dictionary\`, `workspace\`, `log\` and `dual_view\` appear next to `DotExpress.exe` as before; settings, the selected dictionary and documents survive a restart; Dual View opens and its HTML is removed on exit; client init still reports (server log or `log\init.log` on failure). Run it from a read-only folder (for example under `Program Files` without elevation): the same localized startup error with the failing path, and no runtime starts. Run `python gui.py` from `client\` and from another working folder: the same `client\` root is used.

## Out of Scope

- The S-5 repository shape (`load`/`save`/`update`), batching writes, narrowing `except Exception`, and removing `set_lang`/`_runtime_lang`.
- Injecting the log folder into loggers (D10), and P2-7's logging work in `braille/`.
- Moving `documents/export_coordinator.py` or `documents/workspace_service.py`, and renaming `tests/test_conversion_presenter.py`.
- Separating the development-mode `dual_view/` data folder from the package (quirk 1), and any change to the 2026-07-20 contract.
- Splitting `tests/test_gui_document_flows.py` (P1 review M-2).
- Updating historical specs, plans and `storage/refactor.md` that mention the old names.
