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
