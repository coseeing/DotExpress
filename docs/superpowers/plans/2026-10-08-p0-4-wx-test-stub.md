# Shared wx Test Stub (P0-4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every hand-written fake `wx` in `client/tests/` into `client/tests/wx_stub.py`, and make each of the seven GUI test modules install its stubs through one `StubScope` so nothing leaks into other test modules. Test-only refactor: no production file, string, translation or build input changes.

**Architecture:** `wx_stub.py` holds three widget bases, two auto-module classes, `StubScope` (install, import, restore, leak guard, `activate`/`deactivate` for module fixtures) and one factory per current stub shape, each building fresh objects on every call. Task 1 adds the shared core plus its own tests in a new `client/tests/test_wx_stub.py`. Tasks 2-7 each add one factory (with a factory test in `test_wx_stub.py`) and migrate one test module (two in Task 6), one commit per task. Task 8 is the spec's acceptance run.

**Tech Stack:** Python 3 (`unittest`, `importlib.util`, `contextlib`, `unittest.mock.Mock`). wxPython is not installed; everything runs against the stubs.

**Spec:** `docs/superpowers/specs/2026-10-08-p0-4-wx-test-stub-design.md` (authoritative, except for the corrections below).

## Global Constraints

- Branch: `refactor/p0-4-wx-test-stub`. Never switch to or merge into `main`, never push, never rewrite history.
- Only `client/tests/` changes. No production file, no `.po`/`.mo`/`.pot`, no build script.
- Indentation per file, unchanged: 4 spaces in `wx_stub.py`, `test_wx_stub.py`, `test_gui_document_flows.py`, `test_settings_dialogs.py`, `test_dialog_validation.py`, `test_speech_symbols_dialog.py`; TABS in `test_dual_view_frame.py`, `test_dialog_display.py`, `test_dictionary_management_dialog.py`. The new header lines in the tab files are module level (no indentation) except the two imports inside `with _SCOPE.loading():` in `test_dual_view_frame.py`, which use one TAB.
- Every test method, test class, test name and assertion in the seven modules stays as it is. Only stub-building and install code moves.
- Blocks appended to `wx_stub.py` go after exactly two blank lines; each factory test is a new method at the end of `StubFactoryTest`, after one blank line. Code blocks below are exact (copy them, do not retype).
- Test modules import the helper as `from tests import wx_stub` (never `import wx_stub`; see spec).
- ASCII only in the new files.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Shell variables used below (run every command from `client/` unless stated):
  ```bash
  cd /workspace/DotExpress/client
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  P04=$SP/p04
  ```
  `client/` must contain the git-ignored `log/` directory, as the working tree does today.
- Baseline (spec, re-verified at `8a89d5e`): `$PY -m unittest discover -s tests` gives `Ran 450 tests`, `FAILED (failures=1, skipped=7)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. The recorded baseline files are in `$P04/baseline/` (`alone_<module>.txt`: sorted `-v` lines of each wx module run alone; `full_seed<N>.json`: per-seed outcomes of the full-suite shuffle harness) and `$P04/baseline_discover_verbose.txt` (sorted `... ` lines of `discover -v`). `diff <($PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | sort) $P04/baseline_discover_verbose.txt` printed nothing at `8a89d5e`.

## Spec Corrections (decided in this plan)

1. **New tests for `wx_stub.py` (deliberate deviation, requested by the coordinator).** The spec's "Out of scope" excludes a `test_wx_stub.py` and its Test Strategy says there is no red-green step, so that all counts stay identical. This plan adds `client/tests/test_wx_stub.py` with 16 tests (10 for the shared core in Task 1, then one factory test per Task 2-7) so every task starts from a failing test. Consequences, made precise:
   - Criterion 1 (per module) is unchanged: each of the seven modules alone gives the same test ids and outcomes as `$P04/baseline/alone_<module>.txt`, counts 5 / 8 / 8 / 6 / 61 / 27 / 21.
   - Criterion 2 becomes: `discover` gives `Ran 466 tests` (450 + 16), `FAILED (failures=1, skipped=7)`; the sorted `... ` lines **without** the `(test_wx_stub.` lines are byte-identical to `$P04/baseline_discover_verbose.txt`; exactly 16 lines contain `(test_wx_stub.`, all `... ok`. Intermediate totals are in "Expected Counts".
   - Criterion 5 becomes: the shuffle harness runs with `--exclude test_wx_stub`, so each seed produces exactly the baseline permutation of the 64 baseline modules (450 tests) and can be compared with `full_seed<N>.json`. An extra run of seeds 1-20 **with** `test_wx_stub` (466 tests) must show no failure or error in `test_wx_stub` or the seven modules.
   - The new module has no wx-bound production import and leaves `sys.modules` unchanged (leak probe, Task 8).
2. **Ordered pairs: two fail today, not one.** The spec says that of the 42 ordered pairs of the seven modules, "exactly the first pair above fails". Re-running all 42 at `8a89d5e` gives two failing pairs: `tests.test_gui_document_flows tests.test_dialog_validation` (`FAILED (errors=18)`) and `tests.test_gui_document_flows tests.test_dual_view_frame` (`FAILED (errors=1)`, `test_initial_geometry_matches_parent`, same cause as the spec's three-module command). The 40-seed numbers (17 break `test_dialog_validation`, 20 break `test_dual_view_frame`, none break the other five) reproduce exactly. Criterion 4 is unaffected (all 42 must pass afterwards); Task 3 uses the second pair as an extra red check.
3. **Clarifications the spec leaves open (not factual errors):**
   - `activate()` re-installs the recorded stub modules (including dotted children such as speech's auto-registered `wx.*` submodules seen at load time), the isolated modules and their parent-package attributes, but **not** the private module-under-test names (`_speech_symbols_dialog_under_test`, `_dialog_display_test`). Today those names are absent while the tests run, and `DialogModuleIsolationTest` asserts `_MODULE_UNDER_TEST_NAME` is not in `sys.modules` after a nested load, which would fail if `activate()` had installed it.
   - Isolated parent attributes are restored to their exact prior state: if the parent package had no such attribute before `loading()` (or did not exist), the attribute is deleted from the parent afterwards, so `from settings import dialogs` cannot return a stale copy.
   - The display loader gets the same shape as the speech one: `wx_stub.load_display_dialog()` returns `(module, scope)`.
   - The leak guard raises `wx_stub.StubLeakError` (an `AssertionError` subclass) naming `<module>.<global>` pairs, after the restore and eviction steps.
   - The auto-module classes (`AutoClassModule`, `AutoSubmoduleModule`) land in Task 1 with the core, because `test_wx_stub.py` tests them there; each factory lands with the module that uses it, so "`wx_stub.py` grows only by what that commit's module needs" still holds per task.

Everything else in the spec was re-checked at `8a89d5e`: the inventory line ranges (`test_gui_document_flows` 12-319, `test_settings_dialogs` 10-291, `test_dual_view_frame` 7-53, `test_dialog_validation` 6-12, `test_dialog_display` 9-46, `test_speech_symbols_dialog` 13-121), the per-module counts and the 117/136 totals, both failing order commands, the leak list (probe below: validation leaves `dialog`/`wx`, dual view leaves `ui.dual_view`/`wx`/`wx.html2`, gui leaves nine names, settings leaves non-package `braille`/`braille.tables`, the dictionary run leaves `wx.ID_EDIT`), the double import of `tests.test_speech_symbols_dialog` under `discover`, the 24-line criterion 9 grep, and that only `gui.py`, `dialog.py`, `settings/dialogs.py` and `ui/dual_view.py` import `wx`.

## Review Focus

1. `StubScope` restores exactly: managed `sys.modules` names and isolated parent attributes after `loading()` and after `deactivate()`. Tests: `StubScopeTest` in `test_wx_stub.py`; leak probe (Task 8, Step 5).
2. While a module's tests run, string `patch` targets and function-level imports reach the copy bound at load (R2). Tests: unchanged `test_settings_dialogs` / `test_dual_view_frame`; bind probe (Task 8, Step 6).
3. Each factory reproduces its old stub exactly (constants, widget base, module `__getattr__`, submodule wiring). Tests: `StubFactoryTest` plus the unchanged migrated modules with identical per-test outcomes.
4. The speech loader keeps `DialogModuleIsolationTest`'s contract. Test: `test_loader_uses_real_dialog_module_without_leaking_stubs` (unchanged).

## File Map

- Create `client/tests/wx_stub.py` (Task 1 core; factories appended in Tasks 2-7).
- Create `client/tests/test_wx_stub.py` (Task 1; one factory test added in each of Tasks 2-7).
- Modify `client/tests/test_dialog_validation.py` (Task 2), `test_dual_view_frame.py` (Task 3), `test_gui_document_flows.py` (Task 4), `test_settings_dialogs.py` (Task 5), `test_speech_symbols_dialog.py` and `test_dictionary_management_dialog.py` (Task 6), `test_dialog_display.py` (Task 7).

Line numbers are at `8a89d5e`; locate code by the quoted text.

## Throwaway Tooling (not committed)

All in the scratchpad, outside the repo. Sources are in the Appendix; if `$P04/tools/` is missing, recreate the files from there.

- `$P04/order_run.py` (from the spec author) runs test modules in a given import order in one process, like `discover`. `$P04/tools/order_run.py` is the same file plus `--exclude m1,m2` (applied before `--seed` shuffles).
- `$P04/tools/seed_check.py pairs | gui A B | full A B | full-new A B`: criterion 4 and 5 checks; exits non-zero on any bad case.
- `$P04/tools/leak_probe.py <module>`: criterion 6 (R1/R3) in a fresh process; prints `NO LEAKS` or each changed key.
- `$P04/tools/bind_probe.py [--seed N]`: criterion 7 (R2); loads all modules first and runs one probe test inside each of `test_settings_dialogs`, `test_dual_view_frame`, `test_gui_document_flows`.

Per-task identical-results check (`<module>` is the module migrated in the task; `<N>` the expected total from the table below):

```bash
$PY -m unittest tests.<module> -v 2>&1 | grep ' \.\.\. ' | sort | diff - $P04/baseline/alone_<module>.txt && echo ALONE-IDENTICAL
$PY -m unittest discover -s tests -v > $P04/run.txt 2>&1; grep -E '^Ran|^FAILED|^OK' $P04/run.txt
grep ' \.\.\. ' $P04/run.txt | sort | grep -v '(test_wx_stub\.' | diff - $P04/baseline_discover_verbose.txt && echo DISCOVER-IDENTICAL
grep -c '(test_wx_stub\..*\.\.\. ok$' $P04/run.txt
```

Expected: `ALONE-IDENTICAL`, `Ran <N> tests`, `FAILED (failures=1, skipped=7)`, `DISCOVER-IDENTICAL`, and the `test_wx_stub` count from the table.

## Expected Counts

| After task | `test_wx_stub` | `discover` `Ran` | criterion 9 grep lines |
| --- | --- | --- | --- |
| baseline | - | 450 | 24 |
| 1 core | 10 | 460 | 24 |
| 2 dialog validation | 11 | 461 | 23 |
| 3 dual view frame | 12 | 462 | 18 |
| 4 gui document flows | 13 | 463 | 10 |
| 5 settings dialogs | 14 | 464 | 3 |
| 6 speech + dictionary | 15 | 465 | 1 |
| 7 dialog display | 16 | 466 | 0 |

Every row: `FAILED (failures=1, skipped=7)`, the one failure being the P2-5 case. The criterion 9 grep (run from the repo root) is:

```bash
grep -nE 'class _Widget|class _AutoModule|def _install_stub_modules|def _make_wx_stub|__getattr__ = lambda|__path__ = \[\]|ModuleType\("wx' client/tests/test_*.py | wc -l
```

---

### Task 1: Shared core and its tests

**Files:**
- Create: `client/tests/wx_stub.py`
- Create: `client/tests/test_wx_stub.py`

**Interfaces:** `NoOpAttributes`, `Widget`, `RecordingWidget`, `AutoClassModule`, `AutoSubmoduleModule`, `StubLeakError`, `evict_nothing`, `evict_everything`, `DIALOG_PATH`, `StubScope(stubs, isolate=(), evict=evict_nothing)` with `loading()`, `load_file(name, path)`, `activate()`, `deactivate()`, `stubs`, `loaded`. No existing file changes.

- [ ] **Step 1: Write the failing tests.** Create `client/tests/test_wx_stub.py`:

```python
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

from tests import wx_stub

_FAKE_WX = "_wxstub_fake_wx"
_PREFIX = "_wxstub_"


class _TempModulesMixin:
    """Writes throwaway modules named ``_wxstub_*`` and removes every trace afterwards."""

    def setUp(self) -> None:
        super().setUp()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        sys.path.insert(0, temp_dir.name)
        self.addCleanup(sys.path.remove, temp_dir.name)
        self.addCleanup(self._forget_temp_modules)

    @staticmethod
    def _forget_temp_modules() -> None:
        for name in [name for name in sys.modules if name.startswith(_PREFIX)]:
            del sys.modules[name]

    def write_module(self, relative_path: str, source: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        importlib.invalidate_caches()

    def write_consumer_package(self) -> None:
        self.write_module("_wxstub_pkg/__init__.py", "")
        self.write_module("_wxstub_pkg/consumer.py", f"import {_FAKE_WX} as wx\n")


class WidgetBaseTest(unittest.TestCase):
    def test_widget_masks_missing_attributes_and_ignores_bind(self) -> None:
        parent = object()
        widget = wx_stub.Widget(parent, label="Label", size=(1, 2))

        self.assertIs(widget.parent, parent)
        self.assertEqual(widget.label, "Label")
        self.assertEqual(widget.size, (1, 2))
        self.assertTrue(callable(widget.title))
        self.assertIsNone(widget.AnyMissingMethod(1, key=2))
        self.assertIsNone(widget.Bind("event", "handler"))
        self.assertFalse(hasattr(wx_stub.Widget, "bound_events"))

    def test_recording_widget_records_events_focus_and_visibility(self) -> None:
        widget = wx_stub.RecordingWidget(None, title="Title")

        widget.Bind("event", "handler")
        widget.Hide()
        widget.SetFocus()

        self.assertEqual(widget.title, "Title")
        self.assertEqual(widget.bound_events, {"event": "handler"})
        self.assertFalse(widget.visible)
        self.assertTrue(widget.HasFocus())
        self.assertIsNone(widget.AnyMissingMethod())


class AutoModuleTest(unittest.TestCase):
    def test_auto_class_module_caches_one_new_class_per_name(self) -> None:
        module = wx_stub.AutoClassModule(_FAKE_WX)

        first = module.Anything

        self.assertIsInstance(first, type)
        self.assertIs(module.Anything, first)
        with self.assertRaises(AttributeError):
            module.__missing_dunder__

    def test_auto_submodule_module_registers_submodules_and_absorbs_or(self) -> None:
        self.addCleanup(sys.modules.pop, f"{_FAKE_WX}.Flag", None)
        module = wx_stub.AutoSubmoduleModule(_FAKE_WX)

        flag = module.Flag

        self.assertIs(sys.modules[f"{_FAKE_WX}.Flag"], flag)
        self.assertIs(module.Flag, flag)
        self.assertIs(flag | 1, flag)
        self.assertIs(1 | flag, flag)


class StubScopeTest(_TempModulesMixin, unittest.TestCase):
    def test_loading_installs_stubs_then_leaves_no_trace(self) -> None:
        self.write_consumer_package()
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))

        with scope.loading():
            import _wxstub_pkg.consumer as consumer

        self.assertIs(consumer.wx, fake_wx)
        self.assertNotIn(_FAKE_WX, sys.modules)
        self.assertNotIn("_wxstub_pkg.consumer", sys.modules)
        self.assertIn("_wxstub_pkg", sys.modules)
        self.assertNotIn("consumer", vars(sys.modules["_wxstub_pkg"]))
        self.assertIs(scope.loaded["_wxstub_pkg.consumer"], consumer)
        self.assertIs(scope.loaded[_FAKE_WX], fake_wx)

    def test_loading_restores_previous_modules_and_parent_attribute(self) -> None:
        self.write_consumer_package()
        previous_wx = types.ModuleType(_FAKE_WX)
        sys.modules[_FAKE_WX] = previous_wx
        import _wxstub_pkg.consumer as previous_consumer
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))

        with scope.loading():
            import _wxstub_pkg.consumer as consumer

        self.assertIsNot(consumer, previous_consumer)
        self.assertIs(consumer.wx, fake_wx)
        self.assertIs(sys.modules[_FAKE_WX], previous_wx)
        self.assertIs(sys.modules["_wxstub_pkg.consumer"], previous_consumer)
        self.assertIs(sys.modules["_wxstub_pkg"].consumer, previous_consumer)

    def test_activate_reinstalls_loaded_modules_and_deactivate_restores(self) -> None:
        self.write_consumer_package()
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))
        with scope.loading():
            import _wxstub_pkg.consumer as consumer
        package = sys.modules["_wxstub_pkg"]

        scope.activate()
        try:
            self.assertIs(sys.modules[_FAKE_WX], fake_wx)
            self.assertIs(sys.modules["_wxstub_pkg.consumer"], consumer)
            self.assertIs(package.consumer, consumer)
            sys.modules[f"{_FAKE_WX}.CreatedAtRunTime"] = types.ModuleType("child")
        finally:
            scope.deactivate()

        self.assertNotIn(_FAKE_WX, sys.modules)
        self.assertNotIn(f"{_FAKE_WX}.CreatedAtRunTime", sys.modules)
        self.assertNotIn("_wxstub_pkg.consumer", sys.modules)
        self.assertNotIn("consumer", vars(package))

    def test_leak_guard_names_module_that_keeps_a_stub(self) -> None:
        self.write_module("_wxstub_leaky.py", f"import {_FAKE_WX} as wx\n")
        scope = wx_stub.StubScope({_FAKE_WX: types.ModuleType(_FAKE_WX)})

        with self.assertRaises(wx_stub.StubLeakError) as caught:
            with scope.loading():
                import _wxstub_leaky  # noqa: F401

        self.assertIn("_wxstub_leaky.wx", str(caught.exception))
        self.assertNotIn(_FAKE_WX, sys.modules)

    def test_eviction_policy_controls_other_new_modules(self) -> None:
        self.write_module("_wxstub_kept.py", "VALUE = 1\n")
        self.write_module("_wxstub_evicted.py", "VALUE = 2\n")

        with wx_stub.StubScope({}).loading():
            import _wxstub_kept  # noqa: F401
        with wx_stub.StubScope({}, evict=wx_stub.evict_everything).loading():
            import _wxstub_evicted  # noqa: F401

        self.assertIn("_wxstub_kept", sys.modules)
        self.assertNotIn("_wxstub_evicted", sys.modules)

    def test_load_file_runs_a_private_module_and_removes_it(self) -> None:
        self.write_module("_wxstub_source.py", f"import {_FAKE_WX} as wx\nVALUE = 3\n")
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx})

        with scope.loading():
            module = scope.load_file("_wxstub_private", self.root / "_wxstub_source.py")

        self.assertEqual(module.VALUE, 3)
        self.assertIs(module.wx, fake_wx)
        self.assertNotIn("_wxstub_private", sys.modules)
        self.assertNotIn("_wxstub_private", scope.loaded)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and see them fail.**

Run: `$PY -m unittest tests.test_wx_stub`
Expected: `Ran 1 test`, `FAILED (errors=1)`; the error is `ImportError: cannot import name 'wx_stub' from 'tests' (unknown location)`.

- [ ] **Step 3: Write the core.** Create `client/tests/wx_stub.py`. `Mock` is imported now but first used in Task 3, and `DIALOG_PATH` is first used in Task 6; keep both so later tasks only append.

```python
"""Shared fake ``wx`` modules for the GUI tests, and the scope that installs them.

wxPython is not installed in the test environment, so the GUI tests import the
production modules (``gui``, ``dialog``, ``settings.dialogs``, ``ui.dual_view``)
against hand-written stubs. Every stub lives here:

* Widget bases (``NoOpAttributes``, ``Widget``, ``RecordingWidget``) and the two
  auto modules (``AutoClassModule``, ``AutoSubmoduleModule``).
* One factory per consumer (``*_stubs()``). Each call builds fresh module
  objects, classes, mocks and constants, and each factory mirrors exactly the
  stub its test module used before P0-4. The profiles disagree on purpose
  (constant values, recording versus ignoring widgets); converging them is a
  separate, behavior-changing task.
* ``StubScope``, which installs a factory's modules, imports the code under test
  and restores ``sys.modules`` so nothing leaks into other test modules.

Masking: ``NoOpAttributes.__getattr__`` turns every missing instance attribute
into a no-op function returning ``None``. ``hasattr(widget, anything)`` is
therefore always true. Check absence on classes, never on stub instances.

Import this module as ``from tests import wx_stub`` (run tests from ``client/``).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

DIALOG_PATH = Path(__file__).resolve().parents[1] / "dialog.py"

_MISSING = object()


# --- widget bases -----------------------------------------------------------


class NoOpAttributes:
    """Masking base: any missing attribute is a no-op function returning None."""

    def __getattr__(self, _name):
        def _method(*args, **kwargs):
            return None

        return _method


class Widget(NoOpAttributes):
    """Widget base of the gui-frame profile: ``Bind`` ignores its arguments."""

    def __init__(self, *args, **kwargs):
        self.parent = args[0] if args else None
        self.label = kwargs.get("label", "")
        self.title = kwargs.get("title", getattr(self, "title", ""))
        self.name = ""
        self.size = kwargs.get("size")
        self.min_size = None
        self.sizer = None

    def SetLabel(self, label):
        self.label = label

    def SetName(self, name):
        self.name = name

    def GetName(self):
        return self.name

    def Bind(self, _event, _handler):
        return None

    def SetSize(self, size):
        self.size = size

    def SetMinSize(self, size):
        self.min_size = size

    def SetSizer(self, sizer):
        self.sizer = sizer


class RecordingWidget(Widget):
    """Widget base of the settings-dialog profile: records events, focus, visibility."""

    def __init__(self, *args, **kwargs):
        Widget.__init__(self, *args, **kwargs)
        self.bound_events = {}
        self.focused = False
        self.visible = True

    def Bind(self, event, handler):
        self.bound_events[event] = handler

    def Show(self):
        self.visible = True

    def Hide(self):
        self.visible = False

    def SetFocus(self):
        self.focused = True

    def HasFocus(self):
        return self.focused


def _new_class(name):
    return type(name, (), {})


# --- auto modules -----------------------------------------------------------


class AutoClassModule(types.ModuleType):
    """A missing attribute becomes a new class, cached on the module."""

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        value = type(name, (), {})
        setattr(self, name, value)
        return value


class AutoSubmoduleModule(types.ModuleType):
    """A missing attribute becomes a submodule registered in ``sys.modules``.

    The submodules absorb ``|`` so flag expressions such as ``wx.A | wx.B`` work.
    """

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        sub_name = f"{self.__name__}.{name}"
        if sub_name not in sys.modules:
            sub = AutoSubmoduleModule(sub_name)
            sys.modules[sub_name] = sub
        return sys.modules[sub_name]

    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self


# --- scope ------------------------------------------------------------------


class StubLeakError(AssertionError):
    """A module imported inside a StubScope kept a reference to a stub module."""


def evict_nothing(_name):
    return False


def evict_everything(_name):
    return True


class StubScope:
    """Install stub modules, import the code under test, then restore ``sys.modules``.

    Managed names are the stub names and their dotted children, the ``isolate``
    names (wx-bound production modules imported fresh inside the scope) and the
    private names given to ``load_file``. ``evict`` decides which other modules
    first imported inside ``loading()`` are removed afterwards.
    """

    def __init__(self, stubs, isolate=(), evict=evict_nothing):
        self.stubs = dict(stubs)
        self.isolate = tuple(isolate)
        self.evict = evict
        self.private = set()
        self.loaded = {}
        self.loaded_attrs = {}
        self._load_snapshot = None
        self._activate_snapshot = None

    def _is_under_stub(self, name):
        return any(name == stub or name.startswith(stub + ".") for stub in self.stubs)

    def _is_managed(self, name):
        return self._is_under_stub(name) or name in self.isolate or name in self.private

    @staticmethod
    def _parent_and_child(name):
        parent_name, _, child = name.rpartition(".")
        return parent_name, child

    def _parent_attrs(self):
        attrs = {}
        for name in self.isolate:
            parent_name, child = self._parent_and_child(name)
            parent = sys.modules.get(parent_name) if parent_name else None
            attrs[name] = _MISSING if parent is None else vars(parent).get(child, _MISSING)
        return attrs

    def _snapshot(self):
        modules = {name: module for name, module in sys.modules.items() if self._is_managed(name)}
        return modules, self._parent_attrs()

    def _restore(self, snapshot):
        modules, attrs = snapshot
        for name in [name for name in sys.modules if self._is_managed(name)]:
            if name not in modules:
                del sys.modules[name]
        sys.modules.update(modules)
        for name, value in attrs.items():
            parent_name, child = self._parent_and_child(name)
            parent = sys.modules.get(parent_name) if parent_name else None
            if parent is None:
                continue
            if value is _MISSING:
                vars(parent).pop(child, None)
            else:
                setattr(parent, child, value)

    @contextmanager
    def loading(self):
        """Context manager for the test module's module-level imports."""
        before = set(sys.modules)
        self._load_snapshot = self._snapshot()
        for name in self.isolate:
            sys.modules.pop(name, None)
        sys.modules.update(self.stubs)
        try:
            yield self
        except BaseException:
            self._restore(self._load_snapshot)
            raise
        self.loaded = {
            name: module
            for name, module in sys.modules.items()
            if self._is_managed(name) and name not in self.private
        }
        self.loaded_attrs = self._parent_attrs()
        self._restore(self._load_snapshot)
        new_names = set(sys.modules) - before
        for name in new_names:
            if not self._is_managed(name) and self.evict(name):
                del sys.modules[name]
        self._check_leaks(new_names)

    def load_file(self, name, path):
        """Inside ``loading()``: execute ``path`` as a module named ``name``."""
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load {name} from {path}")
        if name in sys.modules and name not in self.private:
            self._load_snapshot[0][name] = sys.modules[name]
        self.private.add(name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def _check_leaks(self, new_names):
        stub_ids = {id(module) for module in self.stubs.values()}
        stub_ids.update(id(module) for name, module in self.loaded.items() if self._is_under_stub(name))
        offenders = []
        for name in sorted(new_names):
            module = sys.modules.get(name)
            if module is None:
                continue
            for attr, value in list(getattr(module, "__dict__", {}).items()):
                if id(value) in stub_ids:
                    offenders.append(f"{name}.{attr}")
        if offenders:
            raise StubLeakError(
                "modules first imported inside a StubScope still reference stub modules: "
                + ", ".join(offenders)
                + ". Add the importing production module to the scope's isolate names."
            )

    def activate(self):
        """``setUpModule``: re-install the modules recorded at the end of ``loading()``."""
        self._activate_snapshot = self._snapshot()
        sys.modules.update(self.loaded)
        for name, value in self.loaded_attrs.items():
            parent_name, child = self._parent_and_child(name)
            parent = sys.modules.get(parent_name) if parent_name else None
            if parent is not None and value is not _MISSING:
                setattr(parent, child, value)

    def deactivate(self):
        """``tearDownModule``: restore what ``activate()`` replaced and drop new stub children."""
        snapshot, self._activate_snapshot = self._activate_snapshot, None
        if snapshot is not None:
            self._restore(snapshot)
```

- [ ] **Step 4: Run the new tests.**

Run: `$PY -m unittest tests.test_wx_stub -v`
Expected: `Ran 10 tests`, `OK`.

- [ ] **Step 5: Check that the tests bite (do not commit these edits).** Each mutation below must turn the run red; undo it right after (`cp` from a backup or revert the one line by hand; do not use `git checkout` on an uncommitted new file):
  - In `StubScope._restore`, replace the body of the final `for name, value in attrs.items():` loop with `continue` -> `FAILED (failures=3)`.
  - In `_check_leaks`, change `if offenders:` to `if False:` -> `FAILED (failures=1)` (`test_leak_guard_names_module_that_keeps_a_stub`).
  - In `deactivate`, change `if snapshot is not None:` to `if False:` -> `FAILED (failures=1)`.

- [ ] **Step 6: Full suite unchanged apart from the new tests.** Run the per-task identical-results check with `discover` only (no module was migrated): `Ran 460 tests`, `FAILED (failures=1, skipped=7)`, `DISCOVER-IDENTICAL`, 10 `test_wx_stub` lines. Also `$PY $P04/tools/leak_probe.py test_wx_stub` -> `NO LEAKS`.

- [ ] **Step 7: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py
git commit -m "test: add shared wx stub core" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Migrate `test_dialog_validation`

**Files:**
- Modify: `client/tests/wx_stub.py` (append `dialog_validation_stubs`)
- Modify: `client/tests/test_wx_stub.py` (add `StubFactoryTest`)
- Modify: `client/tests/test_dialog_validation.py:1-14`

- [ ] **Step 1: Red checks (record the output).**
  - `$PY -m unittest tests.test_gui_document_flows tests.test_dialog_validation` -> `FAILED (errors=18)`.
  - `$PY $P04/tools/leak_probe.py test_dialog_validation` -> `sys.modules['dialog'] changed` and `sys.modules['wx'] changed`, after load and after run.

- [ ] **Step 2: Add the failing factory test.** In `client/tests/test_wx_stub.py`, insert this class above `if __name__ == "__main__":` (two blank lines before and after it):

```python
class StubFactoryTest(unittest.TestCase):
    def assert_fresh(self, factory, names: list[str]) -> dict:
        first = factory()
        second = factory()

        self.assertEqual(sorted(first), sorted(names))
        for name in names:
            self.assertIsInstance(first[name], types.ModuleType)
            self.assertIsNot(first[name], second[name])
        self.assertIsNot(first["wx"].Window, second["wx"].Window)
        return first

    def test_dialog_validation_stubs_are_fresh_plain_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.dialog_validation_stubs, ["wx"])["wx"]

        self.assertIs(type(wx), types.ModuleType)
        self.assertEqual(
            sorted(name for name in vars(wx) if not name.startswith("__")),
            ["CommandEvent", "Dialog", "ListCtrl", "Window"],
        )
        self.assertFalse(hasattr(wx, "OK"))
```

Run: `$PY -m unittest tests.test_wx_stub`
Expected: `Ran 11 tests`, `FAILED (errors=1)`, `AttributeError: module 'tests.wx_stub' has no attribute 'dialog_validation_stubs'`.

- [ ] **Step 3: Append the factory** to the end of `client/tests/wx_stub.py`:

```python
# --- factory: test_dialog_validation ----------------------------------------


def dialog_validation_stubs():
    """Plain ``wx`` with four classes; any other attribute raises AttributeError."""
    wx = types.ModuleType("wx")
    wx.Dialog = _new_class("Dialog")
    wx.ListCtrl = _new_class("ListCtrl")
    wx.Window = _new_class("Window")
    wx.CommandEvent = _new_class("CommandEvent")
    return {"wx": wx}
```

- [ ] **Step 4: Migrate the module.** In `client/tests/test_dialog_validation.py`, replace lines 1-14 (from `import sys` through `from dialog import DictionaryNameDialog, DocumentNameDialog`) with:

```python
import unittest

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog",))
with _SCOPE.loading():
    from dialog import DictionaryNameDialog, DocumentNameDialog

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate
```

The rest of the file (from `class _TextCtrl:`) stays byte-identical.

- [ ] **Step 5: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 11 tests`, `OK`.
  - Per-task identical-results check with `<module>` = `test_dialog_validation`, `Ran 461 tests`, 11 `test_wx_stub` lines.
  - `$PY -m unittest tests.test_gui_document_flows tests.test_dialog_validation` -> `Ran 69 tests`, `OK`.
  - `$PY $P04/tools/leak_probe.py test_dialog_validation` -> `NO LEAKS`.
  - Criterion 9 grep -> 23.

- [ ] **Step 6: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_dialog_validation.py
git commit -m "refactor: use shared wx stub in dialog validation tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Migrate `test_dual_view_frame`

**Files:**
- Modify: `client/tests/wx_stub.py` (append `_DualViewWidget`, `dual_view_stubs`)
- Modify: `client/tests/test_wx_stub.py` (add one method to `StubFactoryTest`)
- Modify: `client/tests/test_dual_view_frame.py:1-56` (TABS)

- [ ] **Step 1: Red checks.**
  - `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame` -> `FAILED (failures=1, errors=1)`.
  - `$PY -m unittest tests.test_gui_document_flows tests.test_dual_view_frame` -> `FAILED (errors=1)`.
  - `$PY $P04/tools/leak_probe.py test_dual_view_frame` -> `ui.dual_view`, `wx`, `wx.html2` changed.

- [ ] **Step 2: Add the failing factory test.** Append this method to `StubFactoryTest` (after the last method of the class):

```python
    def test_dual_view_stubs_are_fresh_with_recording_frame(self) -> None:
        stubs = self.assert_fresh(wx_stub.dual_view_stubs, ["wx", "wx.html2"])
        wx = stubs["wx"]
        calls = []

        frame = wx.Frame("parent", size=(1, 2))
        wx.CallAfter(lambda: calls.append("called"))

        self.assertEqual(frame.init_args, ("parent",))
        self.assertEqual(frame.init_kwargs, {"size": (1, 2)})
        self.assertEqual(calls, ["called"])
        self.assertFalse(hasattr(wx.Window, "FindFocus"))
        self.assertIs(wx.html2, stubs["wx.html2"])
        self.assertEqual((wx.VERTICAL, wx.EXPAND), (1, 2))
        self.assertIsNot(wx.AnyName, wx.AnyName)
```

Run: `$PY -m unittest tests.test_wx_stub` -> `Ran 12 tests`, `FAILED (errors=1)`, `AttributeError: ... no attribute 'dual_view_stubs'`.

- [ ] **Step 3: Append the factory** to `client/tests/wx_stub.py`:

```python
# --- factory: test_dual_view_frame ------------------------------------------


class _DualViewWidget(NoOpAttributes):
    def __init__(self, *args, **kwargs):
        pass


def dual_view_stubs():
    """Minimal ``wx`` + ``wx.html2``: recording ``Frame``, no ``Window.FindFocus``."""
    wx = types.ModuleType("wx")

    class Window(_DualViewWidget):
        pass

    class Frame(Window):
        def __init__(self, *args, **kwargs):
            self.init_args = args
            self.init_kwargs = kwargs

    class BoxSizer(_DualViewWidget):
        pass

    wx.Window = Window
    wx.Frame = Frame
    wx.BoxSizer = BoxSizer
    wx.__path__ = []
    wx.VERTICAL = 1
    wx.EXPAND = 2
    wx.EVT_CLOSE = object()
    wx.CallAfter = lambda callback: callback()
    wx.__getattr__ = _new_class

    wx_html2 = types.ModuleType("wx.html2")
    wx_html2.WebView = type(
        "WebView",
        (),
        {"New": staticmethod(lambda parent: Mock())},
    )
    wx.html2 = wx_html2
    return {"wx": wx, "wx.html2": wx_html2}
```

- [ ] **Step 4: Migrate the module.** In `client/tests/test_dual_view_frame.py`, replace lines 1-56 (from `import types` through `import ui.dual_view as dual_view`) with the block below. The two indented imports use one TAB. `sys` and `types` are no longer used in this file (the `patch("ui.dual_view.sys.platform", ...)` strings do not need them).

```python
import unittest
from unittest.mock import Mock, patch

from tests import wx_stub

_STUBS = wx_stub.dual_view_stubs()
_SCOPE = wx_stub.StubScope(_STUBS, isolate=("ui.dual_view",))
wx = _STUBS["wx"]
with _SCOPE.loading():
	from ui.dual_view import DualViewFrame
	import ui.dual_view as dual_view

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate
```

- [ ] **Step 5: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 12 tests`, `OK`.
  - Per-task identical-results check with `<module>` = `test_dual_view_frame`, `Ran 462 tests`, 12 `test_wx_stub` lines.
  - Both Step 1 order commands -> `Ran 94 tests`, `OK` and `Ran 67 tests`, `OK`.
  - `$PY $P04/tools/leak_probe.py test_dual_view_frame` -> `NO LEAKS`.
  - `$PY $P04/tools/seed_check.py gui 1 40` -> `40 checked, 0 bad` (all seven-module order failures were in the two modules migrated so far).
  - Criterion 9 grep -> 18.

- [ ] **Step 6: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_dual_view_frame.py
git commit -m "refactor: use shared wx stub in dual view frame tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Migrate `test_gui_document_flows`

**Files:**
- Modify: `client/tests/wx_stub.py` (append `_GUI_DIALOG_NAMES`, `gui_frame_stubs`)
- Modify: `client/tests/test_wx_stub.py` (add one method)
- Modify: `client/tests/test_gui_document_flows.py:3-322` and `:326`

- [ ] **Step 1: Red checks.**
  - `$PY $P04/tools/leak_probe.py test_gui_document_flows` -> nine changed names (`braille.louis_helper`, `dialog`, `gui`, `settings.dialogs`, `ui.dual_view`, `wx`, `wx.html2`, `wx.lib`, `wx.lib.scrolledpanel`), after load and after run.
  - `$PY $P04/tools/bind_probe.py` -> `test_settings_dialogs -> AssertionError: ... settings.dialogs.wx is not this module's stub wx` (the settings tests run against the `settings.dialogs` that gui's stubs built). The other two probes print `OK`.

- [ ] **Step 2: Add the failing factory test** (append to `StubFactoryTest`):

```python
    def test_gui_frame_stubs_are_fresh_with_ignoring_widgets(self) -> None:
        stubs = self.assert_fresh(
            wx_stub.gui_frame_stubs,
            ["braille.louis_helper", "dialog", "wx", "wx.html2", "wx.lib", "wx.lib.scrolledpanel"],
        )
        wx = stubs["wx"]

        self.assertTrue(issubclass(wx.Window, wx_stub.Widget))
        self.assertFalse(issubclass(wx.Window, wx_stub.RecordingWidget))
        self.assertEqual((wx.ID_OK, wx.OK, wx.VERTICAL), (2, 4, 4096))
        self.assertEqual(wx.MessageBox("text"), wx.OK)
        self.assertIs(wx.lib, stubs["wx.lib"])
        self.assertIs(stubs["wx.lib.scrolledpanel"].ScrolledPanel, wx.lib.ScrolledPanel)
        self.assertIsNot(wx.EVT_CLOSE, wx.EVT_CLOSE)
        self.assertEqual(stubs["dialog"].DictionaryNameDialog().ShowModal(), 0)
        self.assertIsNone(stubs["braille.louis_helper"].initialize())
```

Run: `$PY -m unittest tests.test_wx_stub` -> `Ran 13 tests`, `FAILED (errors=1)`, `AttributeError: ... no attribute 'gui_frame_stubs'`.

- [ ] **Step 3: Append the factory** to `client/tests/wx_stub.py`. It is the old `_install_stub_modules()` body with three intended differences: a fresh `wx` module instead of `sys.modules.get("wx", ...)`, the `dialog` and `braille.louis_helper` stubs built unconditionally (what happens when the module runs alone), and nothing written to `sys.modules` (the scope installs the returned dict).

```python
# --- factory: test_gui_document_flows ---------------------------------------


_GUI_DIALOG_NAMES = (
    "DictionaryManagementDialog",
    "DictionaryNameDialog",
    "DocumentNameDialog",
    "FileIssuesDialog",
    "InvalidWorkspaceFilesDialog",
    "SpeechSymbolsDialog",
    "TranslationSettingsDialog",
    "TranslationTableDialog",
)


def gui_frame_stubs():
    """Full widget set for ``gui``: ``wx``, ``wx.html2``, ``wx.lib``, ``dialog``, ``braille.louis_helper``."""
    wx = types.ModuleType("wx")

    class Window(Widget):
        @staticmethod
        def FindFocus():
            return None

    class Frame(Window):
        pass

    class Panel(Window):
        pass

    class Dialog(Window):
        pass

    class Accessible(Widget):
        pass

    class App(Widget):
        pass

    class Menu(Widget):
        pass

    class MenuBar(Widget):
        pass

    class StaticText(Window):
        pass

    class Button(Window):
        pass

    class BoxSizer(Widget):
        pass

    class StaticBoxSizer(Widget):
        pass

    class StaticBox(Widget):
        pass

    class Choice(Window):
        pass

    class TextCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._font = Font()

        def GetFont(self):
            return self._font

        def SetFont(self, font):
            self._font = font

    class ListCtrl(Window):
        pass

    class SpinCtrl(Window):
        pass

    class CommandEvent(Widget):
        pass

    class CloseEvent(Widget):
        pass

    class KeyEvent(Widget):
        pass

    class MouseEvent(Widget):
        pass

    class ListEvent(Widget):
        pass

    class ContextMenuEvent(Widget):
        pass

    class Font(Widget):
        def SetFamily(self, _family):
            return None

    class Colour(tuple):
        def __new__(cls, red=0, green=0, blue=0):
            return tuple.__new__(cls, (red, green, blue))

    class Point(tuple):
        def __new__(cls, x=0, y=0):
            return tuple.__new__(cls, (x, y))

    class _Timer:
        def __init__(self, *_args, **_kwargs):
            self.stopped = False

        def Stop(self):
            self.stopped = True

    class _FileDialog(Dialog):
        def GetPaths(self):
            return []

        def GetPath(self):
            return ""

        def SetFilterIndex(self, _index):
            return None

        def GetFilterIndex(self):
            return 0

    class _DirDialog(Dialog):
        def GetPath(self):
            return ""

    class _MessageDialog(Dialog):
        pass

    wx.Window = Window
    wx.Frame = Frame
    wx.Panel = Panel
    wx.Dialog = Dialog
    wx.Accessible = Accessible
    wx.App = App
    wx.Menu = Menu
    wx.MenuBar = MenuBar
    wx.StaticText = StaticText
    wx.Button = Button
    wx.BoxSizer = BoxSizer
    wx.StaticBoxSizer = StaticBoxSizer
    wx.StaticBox = StaticBox
    wx.Choice = Choice
    wx.TextCtrl = TextCtrl
    wx.ListCtrl = ListCtrl
    wx.SpinCtrl = SpinCtrl
    wx.CommandEvent = CommandEvent
    wx.CloseEvent = CloseEvent
    wx.KeyEvent = KeyEvent
    wx.MouseEvent = MouseEvent
    wx.ListEvent = ListEvent
    wx.ContextMenuEvent = ContextMenuEvent
    wx.Font = Font
    wx.Colour = Colour
    wx.Point = Point
    wx.FileDialog = _FileDialog
    wx.DirDialog = _DirDialog
    wx.MessageDialog = _MessageDialog
    wx.CallAfter = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    wx.CallLater = lambda *_args, **_kwargs: _Timer()
    wx.MessageBox = lambda *args, **kwargs: wx.OK
    wx.DefaultPosition = Point()
    wx.DefaultSize = Point()
    wx.__path__ = []
    wx.__getattr__ = _new_class
    wx_html2 = types.ModuleType("wx.html2")
    wx_html2.WebView = type(
        "WebView",
        (),
        {"New": staticmethod(lambda parent: Mock())},
    )
    wx.html2 = wx_html2

    wx_lib = types.ModuleType("wx.lib")
    wx_lib_scrolledpanel = types.ModuleType("wx.lib.scrolledpanel")

    class _ScrolledPanel(Window):
        def SetupScrolling(self, *args, **kwargs):
            pass

        def SetSizer(self, *args, **kwargs):
            pass

        def Fit(self):
            pass

        def Layout(self):
            pass

    wx_lib_scrolledpanel.ScrolledPanel = _ScrolledPanel
    wx_lib.ScrolledPanel = _ScrolledPanel
    wx.lib = wx_lib

    wx.ID_ANY = -1
    wx.ID_ABOUT = 1
    wx.ID_OK = 2
    wx.OK = 4
    wx.CANCEL = 8
    wx.YES = 1
    wx.NO = 0
    wx.YES_NO = 16
    wx.NO_DEFAULT = 32
    wx.ICON_ERROR = 512
    wx.ICON_INFORMATION = 128
    wx.ICON_WARNING = 256
    wx.DEFAULT_DIALOG_STYLE = 512
    wx.RESIZE_BORDER = 256
    wx.CLOSE_BOX = 1024
    wx.STAY_ON_TOP = 2048
    wx.VERTICAL = 4096
    wx.HORIZONTAL = 8192
    wx.ALL = 16384
    wx.ALIGN_RIGHT = 32768
    wx.ALIGN_CENTER_HORIZONTAL = 32768
    wx.ALIGN_CENTER_VERTICAL = 65536
    wx.EXPAND = 131072
    wx.LEFT = 262144
    wx.RIGHT = 524288
    wx.BOTTOM = 1048576
    wx.TE_MULTILINE = 2097152
    wx.TE_READONLY = 4194304
    wx.TE_RICH2 = 1 << 25
    wx.TE_DONTWRAP = 1 << 26
    wx.FONTFAMILY_TELETYPE = 1
    wx.FD_OPEN = 1 << 20
    wx.FD_MULTIPLE = 1 << 21
    wx.FD_SAVE = 1 << 22
    wx.FD_OVERWRITE_PROMPT = 1 << 23
    wx.NOT_FOUND = -1
    wx.ACC_OK = 0
    wx.ROLE_SYSTEM_PROPERTYPAGE = 38

    class PyDeadObjectError(RuntimeError):
        pass

    wx.PyDeadObjectError = PyDeadObjectError

    dialog = types.ModuleType("dialog")

    class _Dialog:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ShowModal(self):
            return 0

    for name in _GUI_DIALOG_NAMES:
        setattr(dialog, name, _Dialog)
    dialog.finalize_dialog_layout = lambda *args, **kwargs: None

    louis_helper = types.ModuleType("braille.louis_helper")
    louis_helper.initialize = lambda: None
    louis_helper.terminate = lambda: None

    return {
        "wx": wx,
        "wx.html2": wx_html2,
        "wx.lib": wx_lib,
        "wx.lib.scrolledpanel": wx_lib_scrolledpanel,
        "dialog": dialog,
        "braille.louis_helper": louis_helper,
    }
```

- [ ] **Step 4: Migrate the module.** In `client/tests/test_gui_document_flows.py`:
  1. Replace lines 3-322 (from `import importlib` through `gui = importlib.import_module("gui")`) with:

```python
import importlib
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from tests import wx_stub

_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view"),
)
with _SCOPE.loading():
    gui = importlib.import_module("gui")
    from settings.dialogs import TranslationSettingsPanel

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate
```

  2. Delete the now-duplicate line `from settings.dialogs import TranslationSettingsPanel` from the import block that follows (old line 326, between `from documents.export_results import ExportBatchResult` and `from settings.state import DotExpressSettingsSnapshot`). Leave the other imports in that block, and everything below, unchanged. `sys` and `types` are no longer used in this file.

- [ ] **Step 5: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 13 tests`, `OK`.
  - Per-task identical-results check with `<module>` = `test_gui_document_flows`, `Ran 463 tests`, 13 `test_wx_stub` lines.
  - `$PY $P04/tools/leak_probe.py test_gui_document_flows` -> `NO LEAKS`.
  - `$PY $P04/tools/bind_probe.py` -> all three probes `OK`, `ran=466 failures=1 errors=0` (463 + 3 probes; the failure is P2-5).
  - Leak guard smoke check (criterion 8, do not commit): `sed -i 's/isolate=("gui", "settings.dialogs", "ui.dual_view"),/isolate=("gui", "settings.dialogs"),/' tests/test_gui_document_flows.py`, then `$PY -m unittest tests.test_gui_document_flows 2>&1 | grep StubLeakError:` -> `tests.wx_stub.StubLeakError: modules first imported inside a StubScope still reference stub modules: ui.dual_view.wx. Add the importing production module to the scope's isolate names.` Undo with the reverse `sed -i 's/isolate=("gui", "settings.dialogs"),/isolate=("gui", "settings.dialogs", "ui.dual_view"),/' tests/test_gui_document_flows.py` and confirm `git diff` still shows only the Step 4 change. Do **not** use `git checkout -- tests/test_gui_document_flows.py` here: it would also discard the uncommitted migration (this happened in the dry run).
  - Criterion 9 grep -> 10.

- [ ] **Step 6: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_gui_document_flows.py
git commit -m "refactor: use shared wx stub in gui document flow tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Migrate `test_settings_dialogs`

**Files:**
- Modify: `client/tests/wx_stub.py` (append `settings_dialog_stubs`)
- Modify: `client/tests/test_wx_stub.py` (add one method)
- Modify: `client/tests/test_settings_dialogs.py:3-300` and `:574` (inside `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name`)

- [ ] **Step 1: Red check.** `$PY $P04/tools/leak_probe.py test_settings_dialogs` -> `settings.dialogs`, `wx`, `wx.lib`, `wx.lib.scrolledpanel` changed and `sys.modules['braille'] is a stub`, `sys.modules['braille.tables'] is a stub`, after load and after run.

- [ ] **Step 2: Add the failing factory test** (append to `StubFactoryTest`):

```python
    def test_settings_dialog_stubs_are_fresh_with_recording_widgets(self) -> None:
        names = ["braille", "braille.tables", "wx", "wx.lib", "wx.lib.scrolledpanel"]
        stubs = self.assert_fresh(wx_stub.settings_dialog_stubs, names)
        other = wx_stub.settings_dialog_stubs()
        wx = stubs["wx"]

        self.assertTrue(issubclass(wx.Window, wx_stub.RecordingWidget))
        self.assertEqual((wx.ID_OK, wx.OK, wx.VERTICAL), (5100, 4, 1))
        self.assertIsNot(wx.MessageBox, other["wx"].MessageBox)
        self.assertIs(wx.lib.scrolledpanel, stubs["wx.lib.scrolledpanel"])
        self.assertFalse(hasattr(stubs["braille"], "__path__"))
        self.assertEqual(stubs["braille.tables"].listTables(), [])
```

Run: `$PY -m unittest tests.test_wx_stub` -> `Ran 14 tests`, `FAILED (errors=1)`, `AttributeError: ... no attribute 'settings_dialog_stubs'`.

- [ ] **Step 3: Append the factory** to `client/tests/wx_stub.py`. It is the old `_install_stub_modules()` body with `_Widget` replaced by `RecordingWidget` (same fields and methods) and nothing written to `sys.modules`.

```python
# --- factory: test_settings_dialogs -----------------------------------------


def settings_dialog_stubs():
    """Recording widget set for ``settings.dialogs``: ``wx``, ``wx.lib``, and a non-package ``braille``."""
    wx = types.ModuleType("wx")

    class Window(RecordingWidget):
        @staticmethod
        def FindFocus():
            return None

    class Panel(Window):
        pass

    class Dialog(Window):
        pass

    class Frame(Window):
        pass

    class StaticText(Window):
        pass

    class Button(Window):
        pass

    class Choice(Window):
        def GetSelection(self):
            return -1

        def SetSelection(self, index):
            pass

        def AppendItems(self, items):
            pass

        def Append(self, item):
            pass

        def Disable(self):
            pass

        def Enable(self, state=True):
            pass

    class SpinCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._value = kwargs.get("initial", 0)

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

    class _Font:
        def __init__(self):
            self.family = None

        def SetFamily(self, family):
            self.family = family

    class TextCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._value = kwargs.get("value", "")
            self._font = _Font()

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

        def GetFont(self):
            return self._font

        def SetFont(self, font):
            self._font = font

    class Sizer(RecordingWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.children = []

        def Add(self, *args, **kwargs):
            self.children.append((args, kwargs))

    class BoxSizer(Sizer):
        pass

    class GridBagSizer(Sizer):
        def AddGrowableRow(self, idx, proportion=1):
            pass

        def AddGrowableCol(self, idx, proportion=1):
            pass

    class FlexGridSizer(Sizer):
        def AddGrowableCol(self, idx, proportion=1):
            pass

    class ListCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.style = kwargs.get("style", 0)
            self.columns = []
            self.items = []
            self.selected_index = -1
            self.focused_index = -1

        @property
        def ItemCount(self):
            return len(self.items)

        def InsertColumn(self, index, label):
            self.columns.insert(index, label)

        def Append(self, item):
            self.items.append(item)

        def Select(self, index):
            self.selected_index = index

        def GetFirstSelected(self):
            return self.selected_index

        def Focus(self, index):
            self.focused_index = index
            self.focused = True

        def GetItemCount(self):
            return len(self.items)

        def GetItemText(self, index):
            return self.items[index][0]

    class Accessible(RecordingWidget):
        def __init__(self, window=None):
            self.Window = window

    wx.Window = Window
    wx.Panel = Panel
    wx.Dialog = Dialog
    wx.Frame = Frame
    wx.StaticText = StaticText
    wx.Button = Button
    wx.Choice = Choice
    wx.SpinCtrl = SpinCtrl
    wx.TextCtrl = TextCtrl
    wx.Sizer = Sizer
    wx.BoxSizer = BoxSizer
    wx.GridBagSizer = GridBagSizer
    wx.FlexGridSizer = FlexGridSizer
    wx.ListCtrl = ListCtrl
    wx.Accessible = Accessible

    braille = types.ModuleType("braille")
    braille_tables = types.ModuleType("braille.tables")
    braille_tables.listTables = lambda: []
    braille.tables = braille_tables

    wx_lib = types.ModuleType("wx.lib")
    wx_lib_scrolledpanel = types.ModuleType("wx.lib.scrolledpanel")

    class ScrolledPanel(Panel):
        pass

    wx_lib_scrolledpanel.ScrolledPanel = ScrolledPanel
    wx.lib = wx_lib
    wx_lib.scrolledpanel = wx_lib_scrolledpanel

    wx.CallAfter = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    wx.DefaultPosition = (0, 0)
    wx.DefaultSize = (0, 0)
    wx.__path__ = []
    wx.__getattr__ = _new_class

    wx.ID_OK = 5100
    wx.ID_CANCEL = 5101
    wx.ID_APPLY = 5102
    wx.ID_ANY = -1
    wx.OK = 0x0004
    wx.ICON_ERROR = 0x0200
    wx.APPLY = 5102
    wx.RESIZE_BORDER = 0x0040
    wx.DEFAULT_DIALOG_STYLE = 0x0010
    wx.BORDER_SUNKEN = 0x0008
    wx.LC_SINGLE_SEL = 0x0020
    wx.LC_REPORT = 0x0010
    wx.LC_NO_HEADER = 0x4000
    wx.ACC_OK = 0
    wx.ROLE_SYSTEM_PROPERTYPAGE = 38
    wx.EVT_LIST_ITEM_FOCUSED = 100
    wx.EVT_LIST_ITEM_SELECTED = 101
    wx.EVT_CHAR_HOOK = 102
    wx.EVT_CLOSE = 103
    wx.EVT_BUTTON = 104
    wx.NOT_FOUND = -1
    wx.ALL = 0x0010
    wx.EXPAND = 0x0020
    wx.VERTICAL = 0x0001
    wx.HORIZONTAL = 0x0002
    wx.ALIGN_RIGHT = 0x0200
    wx.ALIGN_CENTER = 0x0100
    wx.ALIGN_CENTER_VERTICAL = 0x0200
    wx.LEFT = 0x0040
    wx.RIGHT = 0x0080
    wx.TOP = 0x0100
    wx.BOTTOM = 0x0200
    wx.SP_WRAP = 0x0001
    wx.SP_ARROW_KEYS = 0x0002
    wx.EVT_SPINCTRL = 110
    wx.EVT_TEXT = 111
    wx.WXK_TAB = 9
    wx.TE_MULTILINE = 0x0004
    wx.TE_RICH2 = 0x8000
    wx.TE_DONTWRAP = 0x40000000
    wx.FONTFAMILY_TELETYPE = 1

    class PyDeadObjectError(RuntimeError):
        pass

    wx.PyDeadObjectError = PyDeadObjectError
    wx.MessageBox = Mock()

    return {
        "wx": wx,
        "wx.lib": wx_lib,
        "wx.lib.scrolledpanel": wx_lib_scrolledpanel,
        "braille": braille,
        "braille.tables": braille_tables,
    }
```

- [ ] **Step 4: Migrate the module.** In `client/tests/test_settings_dialogs.py`:
  1. Replace lines 3-300 (from `import sys` through the `)` that closes `from settings.dialogs import (`) with the block below. `sys` stays (the layout test uses it); `types` goes.

```python
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.settings_dialog_stubs(), isolate=("settings.dialogs",))
with _SCOPE.loading():
    import wx

    from settings.dialogs import (
        MultiCategorySettingsDialog,
        SettingsPanel,
        SettingsPanelAccessible,
    )

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate
```

  2. In `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name`, replace the single line `        _install_stub_modules()` with `        sys.modules.update(wx_stub.settings_dialog_stubs())`. Everything else in that test (the `saved_modules` save/pop, `fresh_wx = sys.modules["wx"]`, the patches and the `finally` that restores only the three wx names) stays as it is. The re-stubbed `braille`/`braille.tables` it leaves behind are now removed by `tearDownModule`.

- [ ] **Step 5: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 14 tests`, `OK`.
  - Per-task identical-results check with `<module>` = `test_settings_dialogs`, `Ran 464 tests`, 14 `test_wx_stub` lines.
  - `$PY $P04/tools/leak_probe.py test_settings_dialogs` -> `NO LEAKS`.
  - `$PY $P04/tools/bind_probe.py` -> all three probes `OK`.
  - Criterion 9 grep -> 3.

- [ ] **Step 6: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_settings_dialogs.py
git commit -m "refactor: use shared wx stub in settings dialog tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Share the speech dialog loader (`test_speech_symbols_dialog` + `test_dictionary_management_dialog`)

**Files:**
- Modify: `client/tests/wx_stub.py` (append `SPEECH_DIALOG_MODULE_NAME`, `SPEECH_RESTORE_ROOTS`, `speech_dialog_stubs`, `evict_speech_roots`, `load_speech_dialog`)
- Modify: `client/tests/test_wx_stub.py` (add one method)
- Modify: `client/tests/test_speech_symbols_dialog.py:1-125`
- Modify: `client/tests/test_dictionary_management_dialog.py:7` (TABS file; the new lines are module level)

- [ ] **Step 1: Red checks.**
  - `$PY $P04/tools/leak_probe.py test_dictionary_management_dialog` -> `after run: sys.modules['wx.ID_EDIT'] changed`.
  - `$PY -c "import sys, unittest; unittest.main(module=None, argv=['u', 'discover', '-s', 'tests'], exit=False); print(sorted(k for k in sys.modules if k.startswith('tests.test_')))" 2>&1 | tail -1` -> `['tests.test_speech_symbols_dialog']` (the speech module is executed twice under `discover`).

- [ ] **Step 2: Add the failing factory test** (append to `StubFactoryTest`):

```python
    def test_speech_dialog_stubs_are_fresh_submodule_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.speech_dialog_stubs, ["wx"])["wx"]

        self.assertIsInstance(wx, wx_stub.AutoSubmoduleModule)
        self.assertEqual((wx.NOT_FOUND, wx.OK, wx.ICON_ERROR), (-1, 1, 2))
        self.assertIsNone(wx.MessageBox("text"))
```

Run: `$PY -m unittest tests.test_wx_stub` -> `Ran 15 tests`, `FAILED (errors=1)`, `AttributeError: ... no attribute 'speech_dialog_stubs'`.

- [ ] **Step 3: Append the factory and loader** to `client/tests/wx_stub.py`. `SPEECH_RESTORE_ROOTS` is the old `_SCOPED_RESTORE_ROOTS` set; `evict_speech_roots` plus the scope's managed-name restore reproduce the old `_restore_scoped_modules`.

```python
# --- factory and loader: test_speech_symbols_dialog, test_dictionary_management_dialog


SPEECH_DIALOG_MODULE_NAME = "_speech_symbols_dialog_under_test"
SPEECH_RESTORE_ROOTS = frozenset(
    {
        "Bopomofo",
        "PIL",
        "braille",
        "bs4",
        "dialog",
        "dictionaries",
        "documents",
        "ebooklib",
        "lxml",
        "mammoth",
        "markdown",
        "markdownify",
        "pymupdf",
        "pypdf",
        "translation",
        "wx",
    }
)


def speech_dialog_stubs():
    """Submodule-registering ``wx`` for ``dialog.py`` (``OK`` = 1, flags absorb ``|``)."""
    wx = AutoSubmoduleModule("wx")
    wx.Dialog = _new_class("Dialog")
    wx.ListCtrl = _new_class("ListCtrl")
    wx.Window = _new_class("Window")
    wx.CommandEvent = _new_class("CommandEvent")
    wx.ListEvent = _new_class("ListEvent")
    wx.NOT_FOUND = -1
    wx.OK = 1
    wx.ICON_ERROR = 2
    wx.MessageBox = lambda *args, **kwargs: None
    return {"wx": wx}


def evict_speech_roots(name):
    return name.split(".")[0] in SPEECH_RESTORE_ROOTS


def load_speech_dialog():
    """Load ``dialog.py`` as ``SPEECH_DIALOG_MODULE_NAME``; return ``(module, scope)``."""
    scope = StubScope(speech_dialog_stubs(), evict=evict_speech_roots)
    with scope.loading():
        module = scope.load_file(SPEECH_DIALOG_MODULE_NAME, DIALOG_PATH)
    return module, scope
```

- [ ] **Step 4: Migrate `test_speech_symbols_dialog.py`.** Replace lines 1-125 (from `import csv` through `SpeechSymbolsDialog = dialog.SpeechSymbolsDialog`) with the block below. `_SCOPED_STUB_MODULES` (test data for `DialogModuleIsolationTest`) and `_restore_module_binding` are kept verbatim; `_AutoModule`, `_DIALOG_PATH`, `_SCOPED_RESTORE_ROOTS`, `_make_wx_stub`, `_install_scoped_import_stubs`, `_restore_scoped_modules` and the `importlib.util` import go. Everything from `class _FakeListCtrl:` on stays byte-identical.

```python
import csv
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from dictionaries.entries import DictionaryEntry, load_dictionary_entries
from tests import wx_stub


_MODULE_UNDER_TEST_NAME = wx_stub.SPEECH_DIALOG_MODULE_NAME
_SCOPED_STUB_MODULES = (
    'wx',
    'mammoth',
    'pymupdf',
    'bs4',
    'pypdf',
    'markdown',
    'markdownify',
    'PIL',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'ebooklib',
    'ebooklib.epub',
)


def _restore_module_binding(name: str, existed: bool, module: types.ModuleType | None) -> None:
    if existed:
        sys.modules[name] = module
    else:
        sys.modules.pop(name, None)


def _load_dialog_module() -> types.ModuleType:
    module, _scope = wx_stub.load_speech_dialog()
    return module


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate
CallbackVirtualListCtrl = dialog.CallbackVirtualListCtrl
SpeechSymbolsDialog = dialog.SpeechSymbolsDialog
```

- [ ] **Step 5: Migrate `test_dictionary_management_dialog.py`.** Replace line 7, `from tests.test_speech_symbols_dialog import dialog`, with:

```python
from tests import wx_stub


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate
```

- [ ] **Step 6: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 15 tests`, `OK`.
  - Per-task identical-results check twice, `<module>` = `test_speech_symbols_dialog` and `test_dictionary_management_dialog`; `discover` gives `Ran 465 tests`, 15 `test_wx_stub` lines.
  - `$PY $P04/tools/leak_probe.py test_speech_symbols_dialog` and `... test_dictionary_management_dialog` -> `NO LEAKS` each.
  - The Step 1 `discover` one-liner -> `[]`.
  - Criterion 9 grep -> 1 (only `client/tests/test_dialog_display.py:10:class _AutoModule(types.ModuleType):`).

- [ ] **Step 7: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_speech_symbols_dialog.py client/tests/test_dictionary_management_dialog.py
git commit -m "refactor: share speech dialog loader through wx stub" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Migrate `test_dialog_display`

**Files:**
- Modify: `client/tests/wx_stub.py` (append `DISPLAY_DIALOG_MODULE_NAME`, `dialog_display_stubs`, `load_display_dialog`)
- Modify: `client/tests/test_wx_stub.py` (add one method)
- Modify: `client/tests/test_dialog_display.py:1-48` (TABS file; the new lines are module level)

- [ ] **Step 1: Red check.** Criterion 9 grep (without `| wc -l`) prints exactly `client/tests/test_dialog_display.py:10:class _AutoModule(types.ModuleType):`.

- [ ] **Step 2: Add the failing factory test** (append to `StubFactoryTest`):

```python
    def test_dialog_display_stubs_are_fresh_class_caching_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.dialog_display_stubs, ["wx"])["wx"]

        self.assertIsInstance(wx, wx_stub.AutoClassModule)
        self.assertEqual((wx.ID_OK, wx.ID_CLOSE, wx.OK, wx.CLOSE), (1, 4, 4, 32))
        self.assertIs(wx.AnyName, wx.AnyName)
```

Run: `$PY -m unittest tests.test_wx_stub` -> `Ran 16 tests`, `FAILED (errors=1)`, `AttributeError: ... no attribute 'dialog_display_stubs'`.

- [ ] **Step 3: Append the factory and loader** to `client/tests/wx_stub.py`. `evict_everything` reproduces the old "remove every module first imported during the load" cleanup.

```python
# --- factory and loader: test_dialog_display --------------------------------


DISPLAY_DIALOG_MODULE_NAME = "_dialog_display_test"


def dialog_display_stubs():
    """Class-caching ``wx`` for ``dialog.py`` (``OK`` = 4, ``ID_OK`` = 1)."""
    wx = AutoClassModule("wx")
    wx.Dialog = _new_class("Dialog")
    wx.ListCtrl = _new_class("ListCtrl")
    wx.Window = _new_class("Window")
    wx.NOT_FOUND = -1
    wx.ID_OK = 1
    wx.ID_CANCEL = 2
    wx.ID_APPLY = 3
    wx.ID_CLOSE = 4
    wx.OK = 4
    wx.CANCEL = 8
    wx.APPLY = 16
    wx.CLOSE = 32
    return {"wx": wx}


def load_display_dialog():
    """Load ``dialog.py`` as ``DISPLAY_DIALOG_MODULE_NAME``; return ``(module, scope)``."""
    scope = StubScope(dialog_display_stubs(), evict=evict_everything)
    with scope.loading():
        module = scope.load_file(DISPLAY_DIALOG_MODULE_NAME, DIALOG_PATH)
    return module, scope
```

- [ ] **Step 4: Migrate the module.** In `client/tests/test_dialog_display.py`, replace lines 1-48 (from `import importlib.util` through `dialog_module = _load_dialog_module()`) with the block below; keep the two blank lines before `class FinalizeDialogLayoutTest(unittest.TestCase):`.

```python
import unittest
from unittest.mock import Mock

from tests import wx_stub


dialog_module, _DIALOG_SCOPE = wx_stub.load_display_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate
```

- [ ] **Step 5: Verify.**
  - `$PY -m unittest tests.test_wx_stub` -> `Ran 16 tests`, `OK`.
  - Per-task identical-results check with `<module>` = `test_dialog_display`, `Ran 466 tests`, 16 `test_wx_stub` lines.
  - `$PY $P04/tools/leak_probe.py test_dialog_display` -> `NO LEAKS`.
  - Criterion 9 grep -> 0 (the grep itself prints nothing and exits 1).

- [ ] **Step 6: Commit.**

```bash
git add client/tests/wx_stub.py client/tests/test_wx_stub.py client/tests/test_dialog_display.py
git commit -m "refactor: use shared wx stub in dialog display tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Final verification (spec acceptance criteria; no commit unless something had to be fixed)

- [ ] **Step 1: Criterion 1, per module.**

```bash
for m in test_dialog_display test_dialog_validation test_dictionary_management_dialog test_dual_view_frame test_gui_document_flows test_settings_dialogs test_speech_symbols_dialog; do
  $PY -m unittest tests.$m -v > $P04/final_$m.txt 2>&1
  echo "$m $(grep '^Ran' $P04/final_$m.txt) $(tail -1 $P04/final_$m.txt)"
  grep ' \.\.\. ' $P04/final_$m.txt | sort | diff - $P04/baseline/alone_$m.txt && echo "  IDENTICAL"
done
```

Expected: counts 5 / 8 / 8 / 6 / 61 / 27 / 21, each `OK` and `IDENTICAL`.

- [ ] **Step 2: Criterion 2 (corrected), full suite.** The per-task identical-results `discover` lines: `Ran 466 tests`, `FAILED (failures=1, skipped=7)`, `DISCOVER-IDENTICAL`, 16 `test_wx_stub` lines all `ok`; the only `FAIL` line is the P2-5 case. Also `$PY -m unittest tests.test_wx_stub` -> `Ran 16 tests`, `OK`.

- [ ] **Step 3: Criteria 3 and 4, fixed commands.**

```bash
$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog -v 2>&1 | tail -3   # Ran 117 tests, OK
$PY -m unittest tests.test_dialog_display tests.test_dialog_validation tests.test_dictionary_management_dialog tests.test_dual_view_frame tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog 2>&1 | tail -3   # Ran 136 tests, OK
$PY -m unittest tests.test_gui_document_flows tests.test_dialog_validation 2>&1 | tail -3   # Ran 69 tests, OK
$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame 2>&1 | tail -3   # Ran 94 tests, OK
$PY -m unittest tests.test_gui_document_flows tests.test_dual_view_frame 2>&1 | tail -3   # Ran 67 tests, OK
```

- [ ] **Step 4: Criteria 4 and 5 (corrected), shuffles.**

```bash
$PY $P04/tools/seed_check.py pairs          # pairs: 42 checked, 0 bad
$PY $P04/tools/seed_check.py gui 1 200      # gui seeds 1-200: 200 checked, 0 bad
$PY $P04/tools/seed_check.py full 1 20      # full seeds 1-20: 20 checked, 0 bad   (450 tests, baseline permutation, outside failures == baseline)
$PY $P04/tools/seed_check.py full-new 1 20  # full-new seeds 1-20: 20 checked, 0 bad   (466 tests incl. test_wx_stub)
```

About 80 seconds in total. Optional: all 5040 seven-module permutations (about 25 minutes).

- [ ] **Step 5: Criterion 6, no leak.**

```bash
for m in test_dialog_display test_dialog_validation test_dictionary_management_dialog test_dual_view_frame test_gui_document_flows test_settings_dialogs test_speech_symbols_dialog test_wx_stub; do $PY $P04/tools/leak_probe.py $m; done
```

Expected: each prints its count with `failures=0 errors=0`, then `NO LEAKS`.

- [ ] **Step 6: Criterion 7, binding.** `$PY $P04/tools/bind_probe.py` -> three `-> OK` lines, `ran=469 failures=1 errors=0`. Repeat with `--seed 3`, `--seed 7`, `--seed 11`: three `-> OK` lines each (`errors=8` on seeds 7 and 11 are the out-of-scope `translate` re-import in `test_conversion_service`, not a probe).

- [ ] **Step 7: Criterion 8, leak guard.** Repeat the Task 4 Step 5 smoke check (drop `"ui.dual_view"` from `isolate`, expect the `StubLeakError` line, restore with the reverse `sed`). Now that everything is committed, `git checkout -- client/tests/test_gui_document_flows.py` is also a safe undo. `git status --short` must be clean afterwards.

- [ ] **Step 8: Criterion 9.** From the repo root, the criterion 9 grep without `| wc -l` prints nothing (exit status 1). `client/tests/test_speech_symbols_dialog.py` still contains `sentinel_wx = types.ModuleType('wx')` (test data, single quotes, not matched).

- [ ] **Step 9: Criteria 10 and 11.** From the repo root: `git diff main --stat` lists only the nine `client/tests/` files from the File Map plus the P0-4 spec, its zh-TW translation and this plan. `git log --oneline main..HEAD` shows the spec and plan commits followed by the seven task commits in order. Criteria 1 and 2 were checked after each commit in Tasks 1-7.

- [ ] **Step 10: Handoff notes (put these in the final reply / PR).**
  - Windows-only: today `discover` leaves gui's stub `braille.louis_helper` and settings' non-package `braille` in `sys.modules`; after this change `test_liblouis_runtime` (Windows only) gets the real modules. Counts cannot change, but Windows results for those tests may (presumably from error to pass). This Linux host cannot run them; ask for `py -m unittest discover -s tests` from `client\` on Windows before and after the branch.
  - pytest is not installed here; it honors `setUpModule`/`tearDownModule`, but that is unverified.
  - The 16 new tests are the only count change (Spec Correction 1).

## Dry Run Record

Executed on 2026-10-08 against a scratch clone (`$SP/p04dry`, branch `refactor/p0-4-wx-test-stub` at `8a89d5e`, `client/log/` created), never in the repository. A second scratch worktree at `8a89d5e` (`$SP/p04base`) re-ran the "before" numbers.

- Baseline in the clone: `discover` `Ran 450`, `FAILED (failures=1, skipped=7)`, sorted lines identical to `$P04/baseline_discover_verbose.txt`. Criterion 9 grep: 24 lines (validation 1, dual view 5, gui 8, settings 7, speech 2, display 1).
- Before numbers at `8a89d5e`: `seed_check.py pairs` -> 2 bad (Spec Correction 2); `gui 1 40` -> 25 bad (17 validation, 20 dual view, 0 others); `full 1 5` -> 1 bad; double import of `tests.test_speech_symbols_dialog` confirmed.
- Every red check in Tasks 1-7 failed exactly as written above; every green check passed: each task's module alone `IDENTICAL`, `discover` 460 / 461 / 462 / 463 / 464 / 465 / 466 with `DISCOVER-IDENTICAL` and 10-16 `test_wx_stub` lines; leak probe `NO LEAKS` for each migrated module from its task on. The three mutations in Task 1 Step 5 gave `failures=3`, `failures=1`, `failures=1`.
- After Task 4 the settings bind probe already passes (its failure came from gui's leaked `settings.dialogs`); after Task 5 its leak probe is clean too.
- Task 8 in the clone: Steps 1-9 exactly as expected (`pairs` 0 bad, `gui 1 200` 0 bad, `full 1 20` 0 bad, `full-new 1 20` 0 bad, about 81 s; bind probe `ran=469 failures=1 errors=0`; `git diff origin/main --stat`: 9 test files + 2 spec files before the plan existed).
- Replay of this plan text: a second clone (`$SP/p04dry2`) was built only from this file, by extracting its `python` code blocks and applying them at the stated line ranges, task by task with a commit after each. Every red output (Task 1 `ImportError: cannot import name 'wx_stub' from 'tests' (unknown location)`; Tasks 2-7 the stated `AttributeError`, `Ran 11`-`16`, `FAILED (errors=1)`) and every green check (module alone `IDENTICAL`, leak probe `NO LEAKS`, `discover` 460-466 `DISCOVER-IDENTICAL`, criterion 9 grep 24 / 23 / 18 / 10 / 3 / 1 / 0) matched, and the resulting `client/tests/` tree was identical (`diff -r`) to the first dry run. Task 8 Steps 3-6 were re-run on that tree with the same results. The replay caught one transcription error in an earlier draft (the `test_settings_dialogs` header block missed its `tearDownModule` line); it is fixed here.
- One mistake during the dry run, fixed in this plan: undoing the criterion 8 edit with `git checkout` before the Task 4 commit discarded the whole uncommitted migration. Task 4 now undoes it with the reverse `sed`.

## Appendix: Throwaway Tool Sources

Create under `$P04/tools/` only if missing. `$P04/tools/order_run.py` is `$P04/order_run.py` with these lines inserted directly before `if "--seed" in args:` (and `--exclude m1,m2` added to the usage line):

```python
if "--exclude" in args:
    excluded = set(args[args.index("--exclude") + 1].split(","))
    mods = [m for m in mods if m not in excluded]
```

`$P04/tools/seed_check.py`:

```python
"""Order checks (acceptance criteria 4 and 5). Run from client/ with the venv Python.
  seed_check.py pairs            all 42 ordered pairs of the seven wx modules
  seed_check.py gui A B          seven-module shuffles, seeds A..B
  seed_check.py full A B         full-suite shuffles over the 64 baseline modules (test_wx_stub
                                 excluded so each seed gives the baseline permutation), compared
                                 with p04/baseline/full_seed<N>.json
  seed_check.py full-new A B     full-suite shuffles including test_wx_stub (no baseline to compare)"""
import itertools
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "order_run.py")
BASELINE = os.path.join(HERE, "..", "baseline")
GUI = ["test_dialog_display", "test_dialog_validation", "test_dictionary_management_dialog",
       "test_dual_view_frame", "test_gui_document_flows", "test_settings_dialogs", "test_speech_symbols_dialog"]
COUNTS = {"test_dialog_display": 5, "test_dialog_validation": 8, "test_dictionary_management_dialog": 8,
          "test_dual_view_frame": 6, "test_gui_document_flows": 61, "test_settings_dialogs": 27,
          "test_speech_symbols_dialog": 21}


def run(*args):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        path = handle.name
    subprocess.run([sys.executable, RUNNER, "--json", path, *args], check=True, stdout=subprocess.DEVNULL)
    with open(path) as handle:
        data = json.load(handle)
    os.unlink(path)
    bad = {test: outcome for test, outcome in data["outcome"].items() if outcome != "SKIP"}
    return data["run"], bad


def in_gui(test_id):
    return test_id.split(".")[0] in GUI or test_id.split(".")[0] == "test_wx_stub"


mode = sys.argv[1]
problems = 0
if mode == "pairs":
    for first, second in itertools.permutations(GUI, 2):
        ran, bad = run("--order", f"{first},{second}")
        if ran != COUNTS[first] + COUNTS[second] or bad:
            problems += 1
            print("BAD", first, second, ran, bad)
    print(f"pairs: 42 checked, {problems} bad")
else:
    low, high = int(sys.argv[2]), int(sys.argv[3])
    for seed in range(low, high + 1):
        if mode == "gui":
            ran, bad = run("--gui-only", "--seed", str(seed))
            ok = ran == 136 and not bad
        elif mode == "full":
            ran, bad = run("--exclude", "test_wx_stub", "--seed", str(seed))
            with open(os.path.join(BASELINE, f"full_seed{seed}.json")) as handle:
                base = json.load(handle)
            base_bad = {t: o for t, o in base["outcome"].items() if o != "SKIP" and not in_gui(t)}
            ok = ran == 450 and not any(in_gui(t) for t in bad) and {t: o for t, o in bad.items()} == base_bad
        else:
            ran, bad = run("--seed", str(seed))
            ok = ran == 466 and not any(in_gui(t) for t in bad)
        if not ok:
            problems += 1
            print("BAD seed", seed, ran, bad)
    print(f"{mode} seeds {low}-{high}: {high - low + 1} checked, {problems} bad")
sys.exit(1 if problems else 0)
```

`$P04/tools/leak_probe.py`:

```python
"""R1/R3 probe (acceptance criterion 6). Run from client/: leak_probe.py <test module name>.
Imports tests.<module> in this fresh process, then runs its suite, and reports any
managed sys.modules key or isolated parent attribute that differs from before."""
import importlib
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
name = sys.argv[1]
ISOLATED = {"settings.dialogs": ("settings", "dialogs"), "ui.dual_view": ("ui", "dual_view")}
WATCHED = {"dialog", "gui", "settings.dialogs", "ui.dual_view", "braille.louis_helper",
           "_speech_symbols_dialog_under_test", "_dialog_display_test"}


def watched(key):
    return key == "wx" or key.startswith("wx.") or key in WATCHED


def snapshot():
    return {key: module for key, module in sys.modules.items() if watched(key)}


def problems(before, label):
    found = []
    now = snapshot()
    for key in sorted(set(before) | set(now)):
        if before.get(key) is not now.get(key):
            found.append(f"{label}: sys.modules[{key!r}] changed")
    for key in ("braille", "braille.tables"):
        module = sys.modules.get(key)
        if module is not None and not getattr(module, "__file__", None):
            found.append(f"{label}: sys.modules[{key!r}] is a stub")
    for key, (parent_name, child) in ISOLATED.items():
        parent = sys.modules.get(parent_name)
        if parent is not None and vars(parent).get(child) is not sys.modules.get(key):
            found.append(f"{label}: {parent_name}.{child} does not match sys.modules[{key!r}]")
    return found


before = snapshot()
module = importlib.import_module("tests." + name)
found = problems(before, "after load")
result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(
    unittest.defaultTestLoader.loadTestsFromModule(module)
)
found += problems(before, "after run")
print(f"{name}: ran={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}")
print("\n".join(found) if found else "NO LEAKS")
```

`$P04/tools/bind_probe.py`:

```python
"""R2 probe (acceptance criterion 7). Run from client/: bind_probe.py [--seed N].
Loads every tests/test_*.py module first (as discover does; shuffled with --seed),
appends one probe test to test_settings_dialogs, test_dual_view_frame and
test_gui_document_flows so it runs inside that module's setUpModule/tearDownModule,
then runs the whole suite and prints each probe's result."""
import glob
import os
import random
import sys
import unittest

client = os.getcwd()
sys.path.insert(0, client)
sys.path.insert(0, os.path.join(client, "tests"))
modules = sorted(os.path.basename(path)[:-3] for path in glob.glob(os.path.join(client, "tests", "test_*.py")))
if "--seed" in sys.argv:
    random.Random(int(sys.argv[sys.argv.index("--seed") + 1])).shuffle(modules)


def check_settings(case, module):
    bound = module.MultiCategorySettingsDialog._build_layout.__globals__
    current = sys.modules["settings.dialogs"]
    case.assertIs(current.__dict__, bound, "sys.modules['settings.dialogs'] is not the module bound at load")
    case.assertIs(vars(sys.modules["settings"]).get("dialogs"), current, "settings.dialogs attribute is stale")
    case.assertIs(bound["wx"], module.wx, "settings.dialogs.wx is not this module's stub wx")


def check_dual_view(case, module):
    bound = module.DualViewFrame.refresh_html.__globals__
    current = sys.modules["ui.dual_view"]
    case.assertIs(current.__dict__, bound, "sys.modules['ui.dual_view'] is not the module bound at load")
    case.assertIs(module.dual_view, current, "dual_view name is not sys.modules['ui.dual_view']")
    case.assertIs(vars(sys.modules["ui"]).get("dual_view"), current, "ui.dual_view attribute is stale")
    case.assertIs(bound["wx"], module.wx, "ui.dual_view.wx is not this module's stub wx")


def check_gui(case, module):
    case.assertIs(sys.modules["gui"], module.gui, "sys.modules['gui'] is not the module bound at load")
    settings_globals = module.TranslationSettingsPanel.__init__.__globals__
    case.assertIs(sys.modules["settings.dialogs"].__dict__, settings_globals, "settings.dialogs is not gui's copy")
    case.assertIs(settings_globals["wx"], module.gui.wx, "gui and settings.dialogs use different wx stubs")


CHECKS = {
    "test_settings_dialogs": check_settings,
    "test_dual_view_frame": check_dual_view,
    "test_gui_document_flows": check_gui,
}
loader = unittest.TestLoader()
suite = unittest.TestSuite()
probes = []
for name in modules:
    try:
        suite.addTests(loader.loadTestsFromName(name))
    except unittest.SkipTest as error:
        suite.addTest(unittest.loader._make_skipped_test(name, error, unittest.TestSuite))
        continue
    if name in CHECKS:
        check = CHECKS[name]
        probe_class = type(
            "BindingProbe",
            (unittest.TestCase,),
            {"__module__": name, "test_binding": lambda self, check=check, name=name: check(self, sys.modules[name])},
        )
        probe = probe_class("test_binding")
        probes.append(probe)
        suite.addTest(probe)
result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
problems = {test.id(): text.strip().splitlines()[-1] for test, text in result.failures + result.errors}
for probe in probes:
    print(probe.id().split(".")[0], "->", problems.get(probe.id(), "OK"))
print(f"ran={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}")
```
