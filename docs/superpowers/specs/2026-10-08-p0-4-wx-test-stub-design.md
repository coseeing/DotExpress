# Shared wx Test Stub (P0-4) Design

## Goal

Move every hand-written fake `wx` in `client/tests/` into one shared module, `client/tests/wx_stub.py`, and make each GUI test module install its stubs in a way that cannot leak into other test modules. This is roadmap task P0-4 (`storage/refactor.md` section 6.1, finding at section 5 "wx stub 測試骨架"). P0-5 and the P1 GUI splits build on it.

This is a test-only refactor. No production file, user-visible string, translation or build input changes. The number of tests and the result of every existing test stay the same, both per module and for the full suite. No assertion gets weaker. The only count change is the new `client/tests/test_wx_stub.py` (16 tests for the shared helper; see Test Strategy).

## Method and Baseline (verified 2026-10-08 on `refactor/p0-4-wx-test-stub`, HEAD `8404088`, P0-1/P0-2/P0-3 merged)

1. `grep -lw wx client/tests/*.py`, then reading every match. Seven modules touch a fake `wx`. Production modules that import `wx` are only `gui.py`, `dialog.py`, `settings/dialogs.py` and `ui/dual_view.py` (`ui/__init__.py` is empty). No other test module imports them.
2. Running each of the 64 test modules alone in its own process, then the full suite with `discover`, then in shuffled module orders. The shuffles used a small harness that copies `discover -s tests`: `client/` and `client/tests/` on `sys.path`, every module imported first through `TestLoader.loadTestsFromName` in the given order (an import-time `SkipTest` becomes one skipped test, as in `discover`), then one suite run. The harness is a throwaway file, not part of the change.
3. Probing `sys.modules` and module globals after importing the modules in `discover` order.

Baseline (venv Python 3.14.4, run from `client/`):

- `python -m unittest discover -s tests` gives `Ran 450 tests`, `FAILED (failures=1, skipped=7)`. The one failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`.
- Each module alone: every module passes except that same P2-5 failure, and the per-module counts add up to 450.
- The seven wx modules alone (`python -m unittest tests.<module>`), all `OK`: `test_dialog_display` 5, `test_dialog_validation` 8, `test_dictionary_management_dialog` 8, `test_dual_view_frame` 6, `test_gui_document_flows` 61, `test_settings_dialogs` 27, `test_speech_symbols_dialog` 21. Together: 136.
- The roadmap command `python -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog -v` gives `Ran 117 tests`, `OK`.

## Current State

### Inventory

| Module (indent) | Stub lines | How it builds `wx` | When and how it installs | Other stubs | Looks up wx-bound modules by name at run time? |
| --- | --- | --- | --- | --- | --- |
| `test_gui_document_flows` (4 sp) | 12-319 | `_install_stub_modules()`. **Reuses** `sys.modules.get("wx")` if present and mutates it. Full widget set (below). | At import. Installs `wx`, `wx.html2`, `wx.lib`, `wx.lib.scrolledpanel`. Never restores. Then imports `gui` and `settings.dialogs`. | `dialog` stub and `braille.louis_helper` stub, **only if absent** | No. Uses `patch.object(gui, ...)` and `patch.object(gui.wx, ...)` only. |
| `test_settings_dialogs` (4 sp) | 10-291 | `_install_stub_modules()`. Always a **fresh** module. Recording widget set (below). | At import. Replaces `wx`, `wx.lib`, `wx.lib.scrolledpanel` unconditionally. Never restores. `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` (565) calls it again for a fresh `wx` and restores only the 3 wx names. | `braille` and `braille.tables`, replaced **unconditionally** (the `braille` stub is not a package: no `__path__`) | Yes: 15 function-level `from settings.dialogs import ...`, `import settings.dialogs as dialogs_module`, and 8 `patch("settings.dialogs. ...")` string targets. |
| `test_dual_view_frame` (tabs) | 7-53 | Reuses and mutates `sys.modules.get("wx")`. Own minimal `_Widget` (no-op `__init__`), `Frame` that records `init_args`/`init_kwargs`, `BoxSizer`, `Window` **without** `FindFocus`. | At import. Installs `wx`, `wx.html2`. Never restores. Imports `ui.dual_view`. | none | Yes: `patch("ui.dual_view. ...")` (3), and `patch.object(wx.Window, "FindFocus", create=True)` on its own `wx`. |
| `test_dialog_validation` (4 sp) | 6-12 | Plain `ModuleType` with `Dialog`, `ListCtrl`, `Window`, `CommandEvent` only. Missing attributes raise `AttributeError`. | At import, **only if `wx` is absent**. Then `from dialog import ...` caches the real `dialog` module in `sys.modules`. Never restores. | none | No. |
| `test_dialog_display` (tabs) | 9-46 | `_AutoModule`: a missing attribute becomes a new class, cached on the module. Constants `NOT_FOUND`=-1, `ID_OK`/`ID_CANCEL`/`ID_APPLY`/`ID_CLOSE` = 1/2/3/4, `OK`/`CANCEL`/`APPLY`/`CLOSE` = 4/8/16/32. | Scoped: snapshots all of `sys.modules`, loads `dialog.py` as `_dialog_display_test`, then removes **every** new module and restores the snapshot. Already isolated. | none | No. |
| `test_speech_symbols_dialog` (4 sp) | 13-121 | Another `_AutoModule`: a missing attribute becomes a **submodule** registered as `sys.modules["wx.<name>"]`, with `__or__`/`__ror__` returning itself. Constants `NOT_FOUND`=-1, `OK`=1, `ICON_ERROR`=2, `MessageBox` no-op, classes `Dialog`, `ListCtrl`, `Window`, `CommandEvent`, `ListEvent`. | Scoped: loads `dialog.py` as `_speech_symbols_dialog_under_test`, removes new modules under `_SCOPED_RESTORE_ROOTS` (`wx`, `dialog`, `dictionaries`, `documents`, `braille`, `translation`, `Bopomofo`, and the document-format libraries), restores the rest. `DialogModuleIsolationTest` tests this loader. | none | No. |
| `test_dictionary_management_dialog` (tabs) | none | Imports `dialog` from `tests.test_speech_symbols_dialog`. | Under `discover` this executes `test_speech_symbols_dialog.py` a second time, as `tests.test_speech_symbols_dialog`. | none | No. |

### Field-by-field differences between the widget stubs

`test_gui_document_flows` (G), `test_settings_dialogs` (S) and `test_dual_view_frame` (D) all use a widget base whose `__getattr__` returns a no-op function that returns `None`. P0-2 and P0-3 already hit the consequence: `hasattr(widget, anything)` is always true, reading a missing attribute gives a function instead of `AttributeError`, and calling a missing method silently returns `None`. Even `title` defaults to that function, because `__init__` does `kwargs.get("title", getattr(self, "title", ""))` before `title` exists. Many G tests rely on this masking (for example `_make_frame` leaves frame methods unset). Beyond that, the stubs disagree:

- **Base fields and methods.** G: `parent`, `label`, `title`, `name`, `size`, `min_size`, `sizer`; `SetLabel`, `SetName`, `GetName`, `SetSize`, `SetMinSize`, `SetSizer`; `Bind` ignores its arguments. S has all of that plus `bound_events`, `focused`, `visible`; its `Bind` records `bound_events[event] = handler`, and it adds `Show`/`Hide` (set `visible`), `SetFocus` (sets `focused`) and `HasFocus` (returns it). Under G those four fall through to `__getattr__` (`HasFocus()` returns `None`, not a bool). D's base has only `__getattr__` and an `__init__` that ignores its arguments.
- **Classes.** G only: `App`, `Menu`, `MenuBar`, `StaticBoxSizer`, `StaticBox`, the events `CommandEvent`/`CloseEvent`/`KeyEvent`/`MouseEvent`/`ListEvent`/`ContextMenuEvent`, `Font` (a widget with `SetFamily`), `Colour` and `Point` (tuple subclasses), `FileDialog`/`DirDialog`/`MessageDialog`, `CallLater` returning a `_Timer`, `wx.html2.WebView.New` returning a `Mock`. S only: `Sizer` with a recorded `children` list (`BoxSizer`, `GridBagSizer`, `FlexGridSizer` derive from it). Both, but different: `Choice` (G all `__getattr__`; S `GetSelection` returns -1), `SpinCtrl` and `TextCtrl` (S hold a value; G's `TextCtrl` holds only a `Font`; S's font is a plain `_Font` that records `family`), `ListCtrl` (G plain; S records columns, items, selection, focus and exposes `ItemCount`), `Accessible` (G a plain widget; S `__init__(window=None)` sets only `self.Window` and skips the base `__init__`), `ScrolledPanel` (G a `Window` whose `SetupScrolling`/`SetSizer`/`Fit`/`Layout` do nothing, exposed as `wx.lib.ScrolledPanel`; S a plain `Panel`, exposed as `wx.lib.scrolledpanel`).
- **Module attributes.** Same in both: `__path__ = []`, module `__getattr__` returning a **new** class `type(name, (), {})` on every access (D too), `CallAfter` calling through with arguments, `PyDeadObjectError`, `ID_ANY`=-1, `NOT_FOUND`=-1, `OK`=4, `ICON_ERROR`=512, `ACC_OK`=0, `ROLE_SYSTEM_PROPERTYPAGE`=38, `FONTFAMILY_TELETYPE`=1. Different values: `ID_OK` (G 2, S 5100), `VERTICAL` (4096 / 1), `HORIZONTAL` (8192 / 2), `ALL` (16384 / 16), `EXPAND` (131072 / 32), `LEFT`, `RIGHT`, `BOTTOM`, `ALIGN_RIGHT`, `ALIGN_CENTER_VERTICAL`, `TE_MULTILINE`, `TE_RICH2`, `TE_DONTWRAP`, `RESIZE_BORDER`, `DEFAULT_DIALOG_STYLE`. `DefaultPosition`/`DefaultSize` are `Point()` in G and `(0, 0)` in S. `MessageBox` is a lambda returning `wx.OK` in G and one shared `Mock()` in S. `EVT_*` names are ints in S and fresh classes per access in G. G alone has `YES`, `NO`, `YES_NO`, `NO_DEFAULT`, `CANCEL`, `ICON_INFORMATION`, `ICON_WARNING`, `FD_*`, `STAY_ON_TOP`, `CLOSE_BOX`, `ID_ABOUT`, `ALIGN_CENTER_HORIZONTAL`; S alone has `ID_CANCEL`, `ID_APPLY`, `APPLY`, `LC_*`, `SP_*`, `WXK_TAB`, `BORDER_SUNKEN`, `ALIGN_CENTER`, `TOP`. D: `VERTICAL`=1, `EXPAND`=2, `EVT_CLOSE = object()`, and `CallAfter(callback)` that takes **no** extra arguments.

The three `dialog.py` loaders (validation, display, speech) also differ in what a missing attribute does: `AttributeError` (validation), a cached new class (display), or an auto-registered submodule that absorbs `|` (speech). Their constants conflict too (`OK` is 4 in display and 1 in speech).

### Leaks and order dependence today

Only `test_dialog_display` and `test_speech_symbols_dialog` clean up after themselves. Because `discover` imports **all** modules before it runs any test, the other stubs mix at import time. Probing `sys.modules` after importing the seven modules in `discover` order shows:

- `test_dialog_validation` creates a minimal `wx` and leaves it, plus the real `dialog` bound to it, in `sys.modules`. `test_dual_view_frame` and then `test_gui_document_flows` reuse and mutate that same `wx` object.
- So under `discover`, `gui` imports the **real** `dialog` (validation left it; G's `dialog` stub is skipped because the name exists), `gui`'s `DualViewFrame` inherits D's recording `Frame`, and `wx.EVT_CLOSE` is D's `object()`. Run alone, `gui` gets G's `dialog` stub and G's `Frame`.
- `test_settings_dialogs` then replaces `sys.modules["wx"]`, but `settings.dialogs` is already cached and bound to the shared G object. So under `discover` the settings tests run against `settings.dialogs` built on **G's** widgets, while the test module's own `wx` name is S's object. They pass anyway because the constants they compare (`OK | ICON_ERROR`, `ACC_OK`, `ROLE_SYSTEM_PROPERTYPAGE`) happen to match.
- After all imports, `sys.modules` still holds `wx`, `wx.html2`, `wx.lib`, `wx.lib.scrolledpanel`, `dialog`, `gui`, `settings.dialogs`, `ui.dual_view`, G's `braille.louis_helper` stub, and S's non-package `braille` and `braille.tables` stubs. Every later module runs with them.
- At run time, `test_dictionary_management_dialog` leaves `sys.modules["wx.ID_EDIT"]` behind (an auto-submodule created by the speech-style `wx` when the test reads `dialog.wx.ID_EDIT`).

Alphabetical order happens to make all of this pass. Other orders fail today:

- `python -m unittest tests.test_gui_document_flows tests.test_dialog_validation`: `FAILED (errors=18)` (8 tests, counted with subtests). `test_dialog_validation` imports G's `dialog` stub, so `DictionaryNameDialog` is `_Dialog` with no `_validate_name`.
- `python -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame`: `FAILED (failures=1, errors=1)`. `ui.dual_view` is already bound to G's `wx`, so `test_initial_geometry_matches_parent` gets G's `Frame` (no `init_kwargs`, `'function' object is not subscriptable`), and `test_raise_without_activating_restores_focus_on_other_platforms` patches `FindFocus` on a `wx` that `ui.dual_view` does not use.
- 42 ordered pairs of the seven modules: two fail, the first pair above and `python -m unittest tests.test_gui_document_flows tests.test_dual_view_frame` (`FAILED (errors=1)`, `test_initial_geometry_matches_parent`, same cause as the three-module command above). (Corrected: an earlier draft said only the first pair fails; re-running all 42 at `8a89d5e` gives two.) 40 seeded shuffles of the seven modules: 17 break `test_dialog_validation`, 20 break `test_dual_view_frame`. No shuffle broke the other five modules.
- 20 seeded shuffles of the full suite: besides the two modules above, only `test_conversion_service` fails (8 errors) when `test_translation_result_core` runs before it. That one is not about wx: `test_translation_result_core` pops and re-imports `translate`, so `TranslationResult` exists twice (`python -m unittest tests.test_translation_result_core tests.test_conversion_service` reproduces it with no wx module involved). It is out of scope here.

### Does any test rely on a leaked stub?

No test needs a leak to pass. Every module passes alone (where nothing leaks in), and the per-module counts add up to the `discover` count. But several modules **run against** leaked objects under `discover` today (`gui` with the real `dialog` and D's `Frame`, the settings tests with G's `settings.dialogs`, every later module with the stubbed `braille`). After this change each module always runs against its own stubs, as it does alone. That is the reference behavior this spec preserves. The mixtures `discover` creates today are accidental, and this change removes them.

## Design

### Decision: per-module stub factories plus a scope helper, not one shared fake module

Alternatives considered:

1. **One fake `wx` module (or one `install()`) shared by every test module.** Rejected. The stubs conflict in constant values (`ID_OK` is 2, 5100 or 1; `VERTICAL` is 4096 or 1; `OK` is 4 or 1), in widget behavior (recording versus ignoring `Bind`/`SetFocus`/`HasFocus`, value-holding versus `None`-returning `Choice`/`SpinCtrl`/`TextCtrl`/`ListCtrl`) and in missing-attribute semantics. Merging them changes what tests run against. They might still pass, but that is a behavior change to prove test by test, not a refactor. A shared singleton also cannot give `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` the fresh `wx` it builds today, and it would keep everything bound to one object, which is exactly the leak.
2. **Keep stubs local and only add cleanup.** Rejected. It fixes the leaks but leaves about 650 lines of stub code spread over test modules, which is what the roadmap asks to remove.
3. **Chosen: `client/tests/wx_stub.py` holds every stub as a factory that builds fresh objects on each call (one factory per current stub shape, written once from shared parts), plus one scope helper that installs a set of stub modules, imports the code under test, and restores `sys.modules`.** Each test module keeps exactly the stubs it has today, and none of them can reach another module.

Converging the profiles (one constant table, one widget set) is a possible follow-up once this lands. It is a behavior change and is out of scope.

### Contents of `client/tests/wx_stub.py`

4-space indentation, ASCII, standard library only (plus `unittest.mock.Mock`, which the stubs use today). The name does not match `test*.py`, so `discover` never collects it. It defines no `TestCase`. Test modules import it as `from tests import wx_stub`. That works both for `python -m unittest tests.<module>` and for `python -m unittest discover -s tests` run from `client/`, which is the documented working directory, and `test_dictionary_management_dialog` already imports through `tests.` today. A bare `import wx_stub` would fail under `tests.<module>` and could load a second copy under `discover`.

Names below show intent. The plan may adjust spelling but not behavior.

1. **Widget bases** (module level, never mutated):
   - `NoOpAttributes`: only the `__getattr__` that returns a no-op function returning `None`. Documented as intentional masking, with the consequences listed above and the rule P0-3 adopted: check absence on classes, never on stub instances.
   - `Widget(NoOpAttributes)`: exactly G's `_Widget` (fields, methods, `Bind` ignores).
   - `RecordingWidget(Widget)`: exactly S's `_Widget`. It calls `Widget.__init__`, then sets `bound_events`, `focused`, `visible`, and overrides `Bind`, `Show`, `Hide`, `SetFocus`, `HasFocus`.
2. **Stub factories.** Each call returns a new `dict[str, ModuleType]` keyed by `sys.modules` name, with every installed class, `Mock` and constant created fresh. Each one reproduces today's stub exactly: the same classes and methods, the same constant values, the same module `__getattr__`, the same submodule wiring.
   - `gui_frame_stubs()` for `test_gui_document_flows`: `wx`, `wx.html2`, `wx.lib`, `wx.lib.scrolledpanel`, plus the `dialog` stub (`_Dialog` for the 8 dialog names, plus `finalize_dialog_layout`) and the `braille.louis_helper` stub. Both are now installed **always**, which is what happens when the module runs alone.
   - `settings_dialog_stubs()` for `test_settings_dialogs`: `wx`, `wx.lib`, `wx.lib.scrolledpanel`, `braille`, `braille.tables` (`listTables` returns `[]`).
   - `dual_view_stubs()` for `test_dual_view_frame`: `wx`, `wx.html2`, with D's own no-op base (not `Widget`), its recording `Frame`, `CallAfter(callback)`, and no `FindFocus`.
   - `dialog_validation_stubs()`: the plain four-class `wx`.
   - `dialog_display_stubs()`: display's class-caching auto module with its constants.
   - `speech_dialog_stubs()`: speech's submodule-registering auto module with its constants and `|` support.
   - The two auto-module classes move here unchanged, named for what they do (for example `AutoClassModule` and `AutoSubmoduleModule`).
3. **`StubScope`**, the one install-and-restore mechanism:
   - Built with the stub dict, the names to isolate (wx-bound production modules this test module imports fresh, for example `("gui", "settings.dialogs", "ui.dual_view")`), and an optional eviction policy for other modules first imported inside the scope. The default policy evicts nothing beyond the managed names (see R1). Display passes "every new module" and speech passes its current root set, so their behavior stays exactly as it is.
   - `loading()` is a context manager for module-level imports. It snapshots the managed names and the matching parent-package attributes, removes the isolated names so they import fresh, installs the stubs, and runs the body. On exit it records the resulting module objects, restores the snapshot (`sys.modules` entries and parent-package attributes such as `settings.dialogs` and `ui.dual_view`), applies the eviction policy, and runs the leak guard (R4).
   - A helper to load a file under a private module name inside `loading()` (what display and speech do with `spec_from_file_location` today). Private names are removed again when `loading()` exits.
   - `activate()` / `deactivate()` for `setUpModule` / `tearDownModule`. `activate` re-installs the recorded stub modules (including dotted children such as speech's auto-registered `wx.*` submodules seen at load time), the isolated modules and their parent-package attributes, but **not** the private module-under-test names (`_speech_symbols_dialog_under_test`, `_dialog_display_test`): those are absent while the tests run today, and `DialogModuleIsolationTest` asserts `_MODULE_UNDER_TEST_NAME` is not in `sys.modules` after a nested load. `deactivate` restores what was there before and removes any new `sys.modules` key under a stub name (for example `wx.ID_EDIT`).
   - The speech-style `dialog.py` loader (speech stubs, private name `_speech_symbols_dialog_under_test`, speech eviction roots) lives here as one function, so `test_speech_symbols_dialog` and `test_dictionary_management_dialog` share it. It gives the caller both the loaded module and the scope, so each of the two modules can use that scope's `activate`/`deactivate` as its module fixtures (needed for R3: `test_dictionary_management_dialog` creates `wx.ID_EDIT` at run time). The display loader has the same shape: `load_display_dialog()` also returns `(module, scope)`.

### Isolation contract

- **R1, load leaves no trace.** Importing a migrated test module leaves `sys.modules` unchanged for every managed name (stub names and their dotted children, isolated names, private module-under-test names) and leaves the parent-package attributes of isolated modules unchanged. "Unchanged" is exact: if the parent package had no such attribute before `loading()`, the attribute is deleted afterwards, so `from settings import dialogs` cannot return a stale copy. Pure modules first imported during the load may stay cached, as they would after any normal import. With the display and speech policies, they are evicted as today.
- **R2, run-time lookups see the load-time objects.** While a migrated module's tests run, every name its tests resolve through `sys.modules` (string `patch` targets, function-level imports, `import a.b as c`, which reads the parent-package attribute) resolves to the same module objects its module-level code bound at load. `test_settings_dialogs` and `test_dual_view_frame` need this. All seven modules get `setUpModule = scope.activate` and `tearDownModule = scope.deactivate` for uniformity, which is harmless for the others.
- **R3, run leaves no trace.** After a migrated module's tests finish, managed names and parent-package attributes are back to their state before `setUpModule`, and no new key under a stub name remains.
- **R4, leak guard.** When `loading()` exits, after the restore and eviction steps, it raises `StubLeakError` (an `AssertionError` subclass) naming the offending `<module>.<global>` pairs if any module that stays in `sys.modules` and was first imported inside the scope has a module global that is one of the scope's stub module objects. This catches a future production module that starts importing `wx` without being added to `isolate`. Today the guard passes: only `gui.py`, `dialog.py`, `settings/dialogs.py` and `ui/dual_view.py` import `wx`, and only `settings/dialogs.py` imports `braille.tables` at module level (`adapters/translation/provider.py` imports `braille` lazily inside a function).

### Per-module migration

| Module | Factory | `isolate` | Module-level code kept in the test module |
| --- | --- | --- | --- |
| `test_gui_document_flows` | `gui_frame_stubs()` | `gui`, `settings.dialogs`, `ui.dual_view` | Inside `loading()`: `gui = importlib.import_module("gui")` and `from settings.dialogs import TranslationSettingsPanel`, because both must bind G's stubs. Pure imports (`documents.*`, `settings.state`, ...) stay outside. `_make_frame` and every test stay unchanged. |
| `test_settings_dialogs` | `settings_dialog_stubs()` | `settings.dialogs` | Inside `loading()`: `import wx` and the `from settings.dialogs import ...` block. `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` still builds a fresh settings stub set mid-test, installs it in `sys.modules`, patches `dialogs_module` with it, and restores, as it does today. `tearDownModule` cleans up whatever it leaves (today it leaves the re-stubbed `braille`). |
| `test_dual_view_frame` | `dual_view_stubs()` | `ui.dual_view` | Inside `loading()`: `from ui.dual_view import DualViewFrame` and `import ui.dual_view as dual_view`. The module-level name `wx` points at the stub `wx` from the factory, because the tests patch `wx.Window`. |
| `test_dialog_validation` | `dialog_validation_stubs()` | `dialog` | Inside `loading()`: `from dialog import DictionaryNameDialog, DocumentNameDialog`. The stub is now always installed (today: only when `wx` is absent, which is the case when it runs alone). |
| `test_dialog_display` | `dialog_display_stubs()` | none (private name `_dialog_display_test`) | `dialog_module` loaded through the scope's private-name loader with the "evict every new module" policy. |
| `test_speech_symbols_dialog` | `speech_dialog_stubs()` | none (private name `_speech_symbols_dialog_under_test`) | `_load_dialog_module()` stays as a thin wrapper around the shared speech loader, so `DialogModuleIsolationTest` keeps testing the same contract with the same assertions. `_SCOPED_STUB_MODULES` stays available to that test. |
| `test_dictionary_management_dialog` | shared speech loader | none | `dialog = <shared speech loader>()` replaces `from tests.test_speech_symbols_dialog import dialog`. It gets an identical, separately loaded copy, as it already does under `discover`. `discover` no longer executes the speech test module twice. |

Every test method, class, name and assertion stays as it is. Only the stub-building and install code moves. Indentation stays per file (tabs in `test_dual_view_frame`, `test_dialog_display` and `test_dictionary_management_dialog`; 4 spaces elsewhere).

### Behavior preserved on purpose

- The masking `__getattr__` on G, S and D widgets, and the per-access new-class module `__getattr__`.
- Every constant value per profile, including the conflicting ones.
- S's single shared `MessageBox` `Mock` per factory call (built once per module load, as today).
- Speech's auto-submodule registration in `sys.modules` during a module's run. R3 now removes those keys at teardown.
- `test_settings_dialogs`' mid-test fresh build.
- Reprs change slightly: classes built by the module `__getattr__` and the factories get `__module__ == "tests.wx_stub"` instead of the test module name. No test asserts `__module__`, `__qualname__` or a stub repr (checked by grep).

### Out of scope

- Converging the profiles, or a strict mode without the masking `__getattr__`. Possible follow-ups. Each is a behavior change for the tests.
- The non-wx order dependence between `test_translation_result_core` and `test_conversion_service` (`translate` re-import).
- The P2-5 failure.
- Adding `client/tests/__init__.py`. It would rename every module under `discover` and change test ids.
- New test modules or methods in the seven migrated modules. (Corrected: an earlier draft also excluded a `test_wx_stub.py` so that all counts stay identical. The plan adds `client/tests/test_wx_stub.py` on purpose, so that every task starts from a failing test; see Test Strategy.)
- Any production code.

## Test Strategy

This change moves test scaffolding and adds no production behavior. (Corrected: an earlier draft said there is no red-green step and no new test.) `wx_stub.py` gets its own tests in `client/tests/test_wx_stub.py`: 10 for the shared core (widget bases, auto modules, `StubScope`), written first, then one factory test per migration commit, 16 in total. Each starts red. The migrated modules remain the main evidence that every factory reproduces its old stub. Safety comes from recording the baseline before touching anything and comparing after each step:

1. Before the first commit, record per-test outcomes (`-v` output, sorted) for each of the seven modules alone and for `discover`, and the per-seed outcomes of the shuffle harness (seven-module shuffles and full-suite shuffles, fixed seeds).
2. Add the shared core (widget bases, both auto-module classes, `StubScope`) and its tests in a first commit. Then migrate one module per commit, starting with `test_dialog_validation` (smallest), then `test_dual_view_frame`, `test_gui_document_flows`, `test_settings_dialogs`, `test_speech_symbols_dialog` together with `test_dictionary_management_dialog`, and `test_dialog_display`. `wx_stub.py` grows only by what that commit's module needs (its factory). After each commit, the module alone and the full `discover` run must match the recorded outcomes exactly, apart from the added `test_wx_stub` lines.
3. After the last commit, run the order checks and the binding and leak probes in the acceptance criteria.

## Acceptance Criteria

All commands run from `client/` with the venv Python (`$PY`).

1. **Per module, identical.** For each of the seven modules, `$PY -m unittest tests.<module> -v` lists the same test ids with the same outcomes as the baseline, with counts 5 / 8 / 8 / 6 / 61 / 27 / 21, all `OK`.
2. **Full suite, identical.** `$PY -m unittest discover -s tests -v`: `Ran 466 tests` (450 + 16 in `test_wx_stub`), `FAILED (failures=1, skipped=7)`. The sorted list of `<test id> ... <outcome>` lines without the `(test_wx_stub.` lines is identical to the baseline, and exactly 16 lines contain `(test_wx_stub.`, all `... ok`. The only failure is the P2-5 case. (Corrected: an earlier draft expected `Ran 450 tests`, before `test_wx_stub.py` was added.)
3. **Roadmap command.** `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog -v` gives `Ran 117 tests`, `OK`. All seven modules together in one command give `Ran 136 tests`, `OK`.
4. **Order independence (seven modules).** These pass, and failed before:
   - `$PY -m unittest tests.test_gui_document_flows tests.test_dialog_validation` gives `Ran 69 tests`, `OK`.
   - `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame` gives `Ran 94 tests`, `OK`.
   - `$PY -m unittest tests.test_gui_document_flows tests.test_dual_view_frame` gives `Ran 67 tests`, `OK`.

   With the shuffle harness, all 42 ordered pairs and at least 200 seeded permutations of the seven modules (seeds 1-200) give 136 tests and no failure or error. Running all 5040 permutations is optional (about 25 minutes sequentially).
5. **Order independence (full suite).** For harness seeds 1-20 over the 64 baseline modules (`test_wx_stub` excluded before shuffling, so each seed gives the baseline permutation): 450 tests every time, no failure or error in any of the seven modules, and the failures outside them identical to the same seed's baseline. Those are only the `test_conversion_service` cases that the out-of-scope `translate` re-import or P2-5 causes. An extra run of seeds 1-20 over all 65 modules (466 tests) shows no failure or error in `test_wx_stub` or the seven modules. (Corrected: `test_wx_stub` is excluded from the baseline comparison because adding a module changes every seeded permutation.)
6. **No leak (R1/R3).** A throwaway probe imports each migrated module on its own (in a fresh process) and checks that `sys.modules` has no `wx`, `wx.*`, `dialog`, `gui`, `settings.dialogs`, `ui.dual_view` or `braille.louis_helper` key that was not there before, and that `braille`, if present, is the real package. After running that module's suite, the same holds. The same probe run on `test_wx_stub` also reports no change.
7. **Binding (R2).** A throwaway probe, run inside each of `test_settings_dialogs` and `test_dual_view_frame` under `discover` (all modules loaded first), confirms while their tests run that `sys.modules["settings.dialogs"]` (or `sys.modules["ui.dual_view"]`) and the matching parent-package attribute are the module the test module bound at load, and that its `wx` is the module's own stub. This matters because `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` could still pass against a stale module.
8. **Leak guard works.** Temporarily dropping `"ui.dual_view"` from `test_gui_document_flows`' `isolate` makes its import fail with the guard's message. Revert afterwards. Do not commit this.
9. **No stub code left in test modules.** Run from the repo root: `grep -nE 'class _Widget|class _AutoModule|def _install_stub_modules|def _make_wx_stub|__getattr__ = lambda|__path__ = \[\]|ModuleType\("wx' client/tests/test_*.py`. Today it matches 24 lines across six modules. After the change it prints nothing, and every fake-`wx` construction is in `client/tests/wx_stub.py`. The pattern does not match `DialogModuleIsolationTest`'s `sentinel_wx = types.ModuleType('wx')` (single quotes). That line is test data, not a stub, and stays.
10. `git diff main --stat` touches only `client/tests/` (the seven modules, `wx_stub.py` and `test_wx_stub.py`) and these spec/plan docs. No production file and no `.po`/`.mo` change.
11. One commit for the shared core, then one module migration per commit (the speech and dictionary modules together). After each commit, criteria 1 and 2 hold for the modules migrated so far.

## Risks

- **Stale parent-package attributes** (medium). `import settings.dialogs as x` and `from settings import dialogs` read the `settings.dialogs` attribute, not `sys.modules`. If the scope restored `sys.modules` but not the attribute, a later module could get another module's copy and still pass. R1/R2/R3 cover the attributes explicitly, and criterion 7 checks them.
- **Hidden reliance on cross-module objects** (low). Ruled out by running each module alone (all pass, counts add up) and by the order checks. Under `discover`, `gui` will use G's `dialog` stub instead of the real `dialog`, and the settings tests will use S's widgets instead of G's. Both are the stand-alone behavior that passes today.
- **Profile drift** (low). Later tests may add widgets to one profile only. The module docstring says each factory mirrors one consumer and that converging is a separate change.
- **Windows-only behavior** (cannot verify here). Today S's non-package `braille` stub and G's `braille.louis_helper` stub stay in `sys.modules` for the rest of a `discover` run. On Windows, `test_liblouis_runtime.setUpClass` (`from braille import liblouis, louis_helper`) runs after all modules are loaded, so it may currently get G's stub `louis_helper`. After this change it gets the real modules. Test counts do not change, but Windows results for those Windows-only tests could change, presumably from error to pass. This Linux host cannot run them. The handoff must say so and ask for `py -m unittest discover -s tests` on Windows before and after.
- **pytest** (low). Not installed here. pytest honors `setUpModule`/`tearDownModule` and imports modules before running, like `discover`, but this is unverified.
- **Scope beyond the roadmap row** (judgment call). The row lists four modules. This spec also migrates `test_dialog_validation`, `test_dual_view_frame` and `test_dialog_display`. The first two are the modules leaks break today, and the third is the last hand-written fake `wx`. Leaving them out would keep three stub copies and the order failures.
