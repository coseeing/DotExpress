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


# --- factory: test_dialog_validation ----------------------------------------


def dialog_validation_stubs():
    """Plain ``wx`` with four classes; any other attribute raises AttributeError."""
    wx = types.ModuleType("wx")
    wx.Dialog = _new_class("Dialog")
    wx.ListCtrl = _new_class("ListCtrl")
    wx.Window = _new_class("Window")
    wx.CommandEvent = _new_class("CommandEvent")
    return {"wx": wx}


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
