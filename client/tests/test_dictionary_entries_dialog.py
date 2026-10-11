"""Tests of the dictionary entries editor (``dialog.DictionaryEntriesDialog``).

The editor is driven only through its wx surface by ``_EditorHarness``: the
module's ``wx`` is a namespace of fake widgets and distinct power-of-two flags,
every widget call goes to one ordered log, the cell text comes from the callback
the dialog hands to its virtual list, and the dictionary is a real CSV file. The
harness never reads or sets the dialog's data attributes, so the same tests pin
the editor before and after its data logic moves into a model (P2-2).

``tests/fixtures/dictionary_entries_trace.json`` is a golden trace recorded from
the pre-P2-2 editor by ``write_trace_fixture()``: 40 seeded sequences of 25
random actions over rows that collide (identical rows, case variants, ``Stra\u00dfe``
and ``STRASSE``). ``DictionaryEntriesTraceTest`` replays it step by step. Never
regenerate it to make a refactor pass.
"""

import csv
import inspect
import json
import os
import random
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from dictionaries.entries import DictionaryEntry, load_dictionary_entries
from dictionaries.entry_list_model import DictionaryEntryListModel
from i18n import _
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
DictionaryEntriesDialog = dialog.DictionaryEntriesDialog
_NATIVE_DIALOG_BASE = dialog.wx.Dialog


# --- black-box harness ------------------------------------------------------

_FLAG_NAMES = (
    "DEFAULT_DIALOG_STYLE",
    "RESIZE_BORDER",
    "VERTICAL",
    "HORIZONTAL",
    "LEFT",
    "RIGHT",
    "TOP",
    "BOTTOM",
    "EXPAND",
    "ALL",
    "LC_REPORT",
    "BORDER_SUNKEN",
    "LC_SINGLE_SEL",
    "LC_VIRTUAL",
    "OK",
    "CANCEL",
    "APPLY",
    "CLOSE",
    "ICON_ERROR",
)
FLAGS = types.SimpleNamespace(**{name: 1 << bit for bit, name in enumerate(_FLAG_NAMES)})
_EVENT_NAMES = (
    "EVT_TEXT",
    "EVT_BUTTON",
    "EVT_LIST_ITEM_SELECTED",
    "EVT_LIST_ITEM_DESELECTED",
    "EVT_LIST_ITEM_ACTIVATED",
)
ID_OK = 5100
ID_CANCEL = 5101

# zh_TW texts the editor shows (i18n always loads the bundled zh_TW catalog).
TITLE = "\u81ea\u8a02\u5b57\u5178\u7ba1\u7406\u5668"  # Custom Dictionary Manager
DIALOG_STYLE = FLAGS.DEFAULT_DIALOG_STYLE | FLAGS.RESIZE_BORDER
LIST_STYLE = FLAGS.LC_REPORT | FLAGS.BORDER_SUNKEN | FLAGS.LC_SINGLE_SEL | FLAGS.LC_VIRTUAL
ERROR_FLAGS = FLAGS.OK | FLAGS.ICON_ERROR
ERROR_TITLE = "\u932f\u8aa4"  # Error
ADD = "\u65b0\u589e"  # Add
EDIT = "\u7de8\u8f2f"  # Edit
DELETE = "\u522a\u9664"  # Delete
GENERAL = "\u4e00\u822c"  # General
BOPOMOFO = "\u6ce8\u97f3"  # Bopomofo
UNICODE_BRAILLE = "Unicode \u9ede\u5b57"  # Unicode Braille
HEADER = "text,braille,type\r\n"
# dict_badbopo.csv of the Windows verification (F-W11): one Braille row and two Bopomofo
# rows whose sequences do not parse, which the editor does not show; UTF-8, CRLF.
BADBOPO_HIDDEN_ROWS = (
    "\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
    "\u6578\u5b78,\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca,Bopomofo\r\n"
)
DICT_BADBOPO = (HEADER + "\u81fa\u5317,\u281e\u283a,Braille\r\n" + BADBOPO_HIDDEN_ROWS).encode("utf-8")
TAIPEI_CELLS = ["\u81fa\u5317", "\u281e\u283a", UNICODE_BRAILLE]


def _duplicate_message(identifier: str) -> str:
    """zh_TW of 'Source text "{identifier}" already exists.'"""
    return "\u4f86\u6e90\u6587\u5b57\u300c" + identifier + "\u300d\u5df2\u5b58\u5728\u3002"


def _entry_fields(entry: DictionaryEntry | None) -> list[str] | None:
    if entry is None:
        return None
    return [entry.text, entry.braille, entry.entry_type]


class _Event:
    def __init__(self, harness: '_EditorHarness') -> None:
        self._harness = harness
        self.skipped = False

    def Skip(self) -> None:
        self.skipped = True
        self._harness.record("Skip")


class _FakeControl:
    """Fake widget: records ``Bind`` and can fire the bound handlers."""

    def __init__(self, harness: '_EditorHarness', name: str) -> None:
        self._harness = harness
        self.name = name
        self.bindings: list[tuple[str, object]] = []

    def Bind(self, event: str, handler) -> None:
        self._harness.record("Bind", self.name, event)
        self.bindings.append((event, handler))

    def fire(self, event_type: str) -> bool:
        """Call every handler bound to ``event_type``; return whether one called ``Skip``."""
        event = _Event(self._harness)
        for bound_event, handler in list(self.bindings):
            if bound_event == event_type:
                handler(event)
        return event.skipped


class _FakeTextCtrl(_FakeControl):
    def __init__(self, harness: '_EditorHarness') -> None:
        super().__init__(harness, "TextCtrl")
        self.value = ""

    def GetValue(self) -> str:
        return self.value

    def ChangeValue(self, value: str) -> None:
        self._harness.record("ChangeValue", value)
        self.value = value

    def SetValue(self, value: str) -> None:
        """Like wx, ``SetValue`` also sends ``EVT_TEXT`` (``ChangeValue`` does not)."""
        self._harness.record("SetValue", value)
        self.value = value
        self.fire("EVT_TEXT")


class _FakeButton(_FakeControl):
    def __init__(self, harness: '_EditorHarness', name: str, label: str) -> None:
        super().__init__(harness, name)
        self.label = label
        self.enabled = True

    def Enable(self, enable: bool = True) -> None:
        self._harness.record("Enable", self.label, bool(enable))
        self.enabled = bool(enable)

    def SetLabel(self, label: str) -> None:
        self._harness.record("SetLabel", self.name, label)
        self.label = label


class _FakeListCtrl(_FakeControl):
    """Virtual list: keeps the item count, the selected and the focused row.

    Like the pre-P2-2 fake, shrinking the item count below the selected row
    drops the selection; programmatic ``Select`` sends no event.
    """

    def __init__(self, harness: '_EditorHarness', get_item_text) -> None:
        super().__init__(harness, "ListCtrl")
        self.get_item_text = get_item_text
        self.item_count = 0
        self.selected = -1
        self.focused = -1

    def InsertColumn(self, index: int, label: str, width: int = -1) -> None:
        self._harness.record("InsertColumn", index, label, width)

    def SetItemCount(self, count: int) -> None:
        self._harness.record("SetItemCount", count)
        self.item_count = count
        if self.selected >= count:
            self.selected = -1

    def Refresh(self) -> None:
        self._harness.record("Refresh")

    def GetFirstSelected(self) -> int:
        return self.selected

    def Select(self, index: int, on: bool = True) -> None:
        self._harness.record("Select", index, bool(on))
        if on:
            self.selected = index
        elif self.selected == index:
            self.selected = -1

    def Focus(self, index: int) -> None:
        self._harness.record("Focus", index)
        self.focused = index


class _FakeSizer:
    def Add(self, *_args, **_kwargs) -> None:
        pass


class _ScriptedEntryDialog:
    def __init__(self, result: int, entry: DictionaryEntry | None) -> None:
        self._result = result
        self._entry = entry

    def __enter__(self) -> '_ScriptedEntryDialog':
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def ShowModal(self) -> int:
        return self._result

    def get_entry(self) -> DictionaryEntry | None:
        return self._entry


def _skip_fsync(_descriptor: int) -> None:
    """Stand-in for ``os.fsync`` while an editor is open; see ``_EditorHarness.open``."""


class _EditorHarness:
    """Build the real editor against fake widgets and drive it like a user."""

    def __init__(self, path: Path, on_base_init=None) -> None:
        self.path = path
        self.parent = object()
        self.on_base_init = on_base_init
        self.base_parent = None
        self.log: list[list] = []
        self.buttons: dict[str, _FakeButton] = {}
        self.filter: _FakeTextCtrl | None = None
        self.list: _FakeListCtrl | None = None
        self.ok_button = _FakeButton(self, "ok", "OK")
        self.cancel_button = _FakeButton(self, "cancel", "Cancel")
        # The standard buttons of an older top-level window, such as an open Settings dialog (F-W9).
        self.other_dialog_buttons: dict[int, _FakeButton] = {}
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.message_box_parents: list[object] = []
        self.dialog = None
        self._stack = ExitStack()
        self.wx = types.SimpleNamespace(
            **vars(FLAGS),
            **{name: name for name in _EVENT_NAMES},
            ID_OK=ID_OK,
            ID_CANCEL=ID_CANCEL,
            ID_APPLY=5102,
            ID_CLOSE=5103,
            NOT_FOUND=-1,
            BoxSizer=lambda _orientation: _FakeSizer(),
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
            Button=self._button,
        )

    # construction

    def __enter__(self) -> '_EditorHarness':
        return self.open()

    def __exit__(self, *_exc) -> None:
        self.close()

    def open(self) -> '_EditorHarness':
        stack = self._stack
        try:
            stack.enter_context(patch.object(_NATIVE_DIALOG_BASE, "__init__", self._base_init_function()))
            stack.enter_context(patch.object(dialog, "wx", self.wx))
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            stack.enter_context(patch.object(dialog, "message_box", self._message_box))
            # Editor tests check the dialog and the saved bytes, not durability: every OK
            # would otherwise wait for a real fsync (40 in the trace replay alone).
            # tests.test_atomic_write keeps the real fsync.
            stack.enter_context(patch("os.fsync", _skip_fsync))
            editor = object.__new__(DictionaryEntriesDialog)
            editor.CreateButtonSizer = self._create_button_sizer
            editor.FindWindow = self._find_own_window
            editor.FindWindowById = self._find_window_by_id
            editor.SetSizerAndFit = lambda _sizer: self.record("SetSizerAndFit")
            editor.GetParent = lambda: self.parent
            editor.CentreOnParent = lambda: self.record("CentreOnParent")
            editor.Centre = lambda: self.record("Centre")
            editor.Destroy = lambda: self.record("Destroy")
            self.dialog = editor
            editor.__init__(self.parent, dictionary_path=self.path)
        except BaseException:
            stack.close()
            raise
        return self

    def close(self) -> None:
        self._stack.close()

    def _base_init_function(self):
        harness = self

        def base_init(_dialog, parent, title=None, style=None):
            harness.record("Dialog.__init__", title, style)
            harness.base_parent = parent
            if harness.on_base_init is not None:
                harness.on_base_init()

        return base_init

    def _static_text(self, _parent, label: str = "") -> object:
        self.record("StaticText", label)
        return object()

    def _text_ctrl(self, _parent) -> _FakeTextCtrl:
        self.record("TextCtrl")
        self.filter = _FakeTextCtrl(self)
        return self.filter

    def _button(self, _parent, label: str = "") -> _FakeButton:
        self.record("Button", label)
        button = _FakeButton(self, label, label)
        self.buttons[label] = button
        return button

    def _list_ctrl(self, _parent, get_item_text, style=None) -> _FakeListCtrl:
        self.record("ListCtrl", style)
        self.list = _FakeListCtrl(self, get_item_text)
        return self.list

    def _create_button_sizer(self, flags: int) -> _FakeSizer:
        self.record("CreateButtonSizer", flags)
        return _FakeSizer()

    def _find_own_window(self, window_id: int) -> _FakeButton | None:
        """``wxWindow::FindWindow``: the editor and its children only."""
        return {ID_OK: self.ok_button, ID_CANCEL: self.cancel_button}.get(window_id)

    def _find_window_by_id(self, window_id: int) -> _FakeButton | None:
        """``wx.Window.FindWindowById`` without a parent: every top-level window, oldest first."""
        return self.other_dialog_buttons.get(window_id) or self._find_own_window(window_id)

    def _message_box(self, message: str, caption: str, style: int, parent=None) -> int:
        self.record("MessageBox", message, caption, style)
        self.message_box_parents.append(parent)
        return FLAGS.OK

    def _entry_dialog(self, parent, entry: DictionaryEntry | None = None) -> _ScriptedEntryDialog:
        self.record("AddSymbolDialog", _entry_fields(entry))
        self.entry_dialog_parents.append(parent)
        if not self.script:
            raise AssertionError("the entry dialog opened without a scripted result")
        result, scripted = self.script.pop(0)
        return _ScriptedEntryDialog(result, scripted)

    # recording

    def record(self, *event) -> None:
        self.log.append(list(event))

    def take_log(self) -> list[list]:
        log, self.log = self.log, []
        return log

    # user actions

    def script_entry(self, text: str, braille: str, entry_type: str = "General") -> None:
        """The next entry dialog returns ``ID_OK`` with this entry."""
        self.script.append((ID_OK, DictionaryEntry(text, braille, entry_type)))

    def script_cancel(self) -> None:
        self.script.append((ID_CANCEL, None))

    def type_filter(self, text: str) -> bool:
        self.filter.value = text
        return self.filter.fire("EVT_TEXT")

    def select(self, index: int) -> bool:
        self.list.selected = index
        return self.list.fire("EVT_LIST_ITEM_SELECTED")

    def deselect(self) -> bool:
        self.list.selected = -1
        return self.list.fire("EVT_LIST_ITEM_DESELECTED")

    def click(self, label: str) -> bool:
        """Press the button whose (translated) label is ``_(label)``."""
        return self.buttons[_(label)].fire("EVT_BUTTON")

    def activate(self) -> bool:
        return self.list.fire("EVT_LIST_ITEM_ACTIVATED")

    def press_ok(self) -> bool:
        return self.ok_button.fire("EVT_BUTTON")

    # observations

    def cell(self, row: int, column: int) -> str:
        return self.list.get_item_text(row, column)

    def rows(self) -> list[list[str]]:
        return [[self.cell(row, column) for column in range(3)] for row in range(self.list.item_count)]

    def selected_row(self) -> list[str] | None:
        if self.list.selected < 0:
            return None
        return [self.cell(self.list.selected, column) for column in range(3)]

    def state(self) -> dict:
        return {
            "rows": self.rows(),
            "selected": self.list.selected,
            "focused": self.list.focused,
            "edit": self.buttons[EDIT].enabled,
            "delete": self.buttons[DELETE].enabled,
            "filter": self.filter.value,
        }

    def saved_csv(self) -> str | None:
        if not self.path.is_file():
            return None
        return self.path.read_bytes().decode("utf-8")


def _listing(directory: Path) -> list[str]:
    return sorted(child.name for child in directory.iterdir())


def _write_rows(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["text", "braille", "type"])
        writer.writerows(rows)


class _EditorTestCase(unittest.TestCase):
    def make_path(self, name: str = "dictionary.csv") -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name) / name

    def open_editor(self, rows=(), *, path=None, data=None, on_base_init=None, keep_log=False) -> _EditorHarness:
        """Write ``rows`` (or the raw ``data``) to a new CSV and open the editor on it.

        ``rows=None`` leaves the file missing. The construction log is dropped
        unless ``keep_log`` is set.
        """
        if path is None:
            path = self.make_path()
            if data is not None:
                path.write_bytes(data)
            elif rows is not None:
                _write_rows(path, rows)
        harness = _EditorHarness(path, on_base_init=on_base_init)
        harness.open()
        self.addCleanup(harness.close)
        if not keep_log:
            harness.take_log()
        return harness


ALPHA = ["Alpha", "\u2801", "General"]
BETA = ["Beta", "\u2803", "General"]
ALPHA_CELLS = ["Alpha", "\u2801", GENERAL]
BETA_CELLS = ["Beta", "\u2803", GENERAL]


# --- kept tests (unchanged) -------------------------------------------------


class CallbackVirtualListCtrlTest(unittest.TestCase):
    def test_get_item_text_delegates_to_callback(self) -> None:
        control = object.__new__(CallbackVirtualListCtrl)
        control._get_item_text = lambda item, column: f"{item}:{column}"

        self.assertEqual(control.OnGetItemText(4, 2), "4:2")


class DictionaryEntryLoadingTest(unittest.TestCase):
    def test_loads_only_rows_accepted_by_the_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["text", "braille", "type"])
                writer.writerow(["Alpha", "\u2801", "General"])
                writer.writerow(["", "\u2803", "General"])
                writer.writerow(["Zhuyin", "invalid", "Bopomofo"])

            with patch("dictionaries.entries.normalize_zhuyin_sequence", side_effect=ValueError):
                entries = load_dictionary_entries(path)

        self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])

    def test_missing_dictionary_returns_empty_list(self) -> None:
        self.assertEqual(load_dictionary_entries(Path("missing.csv")), [])


class DialogModuleIsolationTest(unittest.TestCase):
    def test_loader_uses_real_dialog_module_without_leaking_stubs(self) -> None:
        had_dialog = 'dialog' in sys.modules
        previous_dialog = sys.modules.get('dialog')
        had_wx = 'wx' in sys.modules
        previous_wx = sys.modules.get('wx')
        stub_dialog = types.ModuleType('dialog')
        sentinel_wx = types.ModuleType('wx')
        sentinel_wx.sentinel = 'preexisting-wx'
        sys.modules['dialog'] = stub_dialog
        sys.modules['wx'] = sentinel_wx
        self.addCleanup(_restore_module_binding, 'dialog', had_dialog, previous_dialog)
        self.addCleanup(_restore_module_binding, 'wx', had_wx, previous_wx)
        before = {name: sys.modules.get(name) for name in _SCOPED_STUB_MODULES}

        loaded_dialog = _load_dialog_module()

        self.assertIs(sys.modules['dialog'], stub_dialog)
        self.assertIs(sys.modules['wx'], sentinel_wx)
        self.assertIsNot(loaded_dialog.wx, sentinel_wx)
        self.assertTrue(hasattr(loaded_dialog.wx, 'Dialog'))
        self.assertEqual(loaded_dialog.wx.NOT_FOUND, -1)
        self.assertNotIn(_MODULE_UNDER_TEST_NAME, sys.modules)
        for name in _SCOPED_STUB_MODULES:
            self.assertIs(sys.modules.get(name), before[name])

        self.doCleanups()

        self.assertIs(sys.modules.get('dialog'), previous_dialog)
        self.assertIs(sys.modules.get('wx'), previous_wx)


# --- pre-P2-2 tests, rewritten onto the harness (same assertions) -----------


class DictionaryEntriesDialogFilterTest(_EditorTestCase):
    def setUp(self) -> None:
        # Beta is added through the entry dialog: the loader drops a Bopomofo row
        # whose braille is not a zhuyin sequence. Row 0 is selected, as before.
        self.harness = self.open_editor([ALPHA])
        self.harness.script_entry("Beta", "Needle", "Bopomofo")
        self.harness.click("Add")
        self.harness.select(0)
        self.alpha = ALPHA_CELLS
        self.beta = ["Beta", "Needle", BOPOMOFO]

    def test_empty_filter_shows_all_entries(self) -> None:
        self.harness.type_filter('')

        self.assertEqual(self.harness.rows(), [self.alpha, self.beta])
        self.assertEqual(self.harness.list.item_count, 2)

    def test_filter_matches_source_text_case_insensitively(self) -> None:
        self.harness.type_filter('ALP')

        self.assertEqual(self.harness.rows(), [self.alpha])

    def test_filter_matches_braille_case_insensitively(self) -> None:
        self.harness.type_filter('NEED')

        self.assertEqual(self.harness.rows(), [self.beta])

    def test_filter_does_not_match_entry_type(self) -> None:
        self.harness.type_filter('bopomofo')

        self.assertEqual(self.harness.rows(), [])

    def test_item_text_uses_visible_entry_and_localized_type_label(self) -> None:
        self.harness.type_filter('bet')

        self.assertEqual(self.harness.cell(0, 0), 'Beta')
        self.assertEqual(self.harness.cell(0, 1), 'Needle')
        self.assertEqual(self.harness.cell(0, 2), '\u6ce8\u97f3')

    def test_filter_preserves_selected_entry_when_it_remains_visible(self) -> None:
        self.harness.select(1)

        self.harness.type_filter("e")

        self.assertEqual(self.harness.selected_row(), self.beta)
        self.assertTrue(self.harness.buttons[EDIT].enabled)
        self.assertTrue(self.harness.buttons[DELETE].enabled)

    def test_filter_falls_back_to_first_entry_when_selection_is_hidden(self) -> None:
        self.harness.select(1)

        self.harness.type_filter("alp")

        self.assertEqual(self.harness.list.selected, 0)
        self.assertEqual(self.harness.rows()[0], self.alpha)

    def test_empty_result_clears_selection_and_disables_edit_and_delete(self) -> None:
        self.harness.type_filter("missing")

        self.assertEqual(self.harness.list.selected, -1)
        self.assertFalse(self.harness.buttons[EDIT].enabled)
        self.assertFalse(self.harness.buttons[DELETE].enabled)

    def test_filter_event_applies_current_text_and_is_skipped(self) -> None:
        skipped = self.harness.type_filter("alp")

        self.assertEqual(self.harness.rows(), [self.alpha])
        self.assertTrue(skipped)


class DictionaryEntriesDialogBuildUiTest(_EditorTestCase):
    def test_build_ui_binds_item_activation_to_edit_handler(self) -> None:
        harness = self.open_editor([ALPHA])
        editor = harness.dialog

        self.assertEqual(
            harness.list.bindings,
            [
                ("EVT_LIST_ITEM_SELECTED", editor._on_selection_changed),
                ("EVT_LIST_ITEM_DESELECTED", editor._on_selection_changed),
                ("EVT_LIST_ITEM_ACTIVATED", editor._on_item_activated),
            ],
        )


class DictionaryEntriesDialogMutationTest(_EditorTestCase):
    def setUp(self) -> None:
        self.harness = self.open_editor([ALPHA, BETA])

    def test_add_matching_entry_keeps_filter_and_selects_new_entry(self) -> None:
        self.harness.type_filter("alp")
        self.harness.script_entry("Alphabet", "\u2801\u2803")

        self.harness.click("Add")

        added = ["Alphabet", "\u2801\u2803", GENERAL]
        self.assertEqual(self.harness.filter.GetValue(), "alp")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, added])
        self.assertEqual(self.harness.selected_row(), added)

    def test_add_nonmatching_entry_clears_filter_and_selects_new_entry(self) -> None:
        self.harness.type_filter("alp")
        self.harness.script_entry("Gamma", "\u281b")

        self.harness.click("Add")

        added = ["Gamma", "\u281b", GENERAL]
        self.assertEqual(self.harness.filter.GetValue(), "")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, BETA_CELLS, added])
        self.assertEqual(self.harness.selected_row(), added)

    def test_edit_visible_entry_updates_full_list_and_preserves_selection(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Better", "\u2803\u2801")

        self.harness.click("Edit")

        updated = ["Better", "\u2803\u2801", GENERAL]
        self.assertEqual(self.harness.rows(), [updated])
        self.assertEqual(self.harness.selected_row(), updated)
        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, updated])

    def test_edit_entry_that_stops_matching_removes_it_from_visible_list(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Gamma", "\u281b")

        self.harness.click("Edit")

        self.assertEqual(self.harness.rows(), [])
        self.assertEqual(self.harness.list.selected, -1)
        self.assertFalse(self.harness.buttons[EDIT].enabled)
        self.assertFalse(self.harness.buttons[DELETE].enabled)
        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, ["Gamma", "\u281b", GENERAL]])

    def test_delete_filtered_entry_selects_nearest_remaining_entry(self) -> None:
        harness = self.harness
        harness.script_entry("Alpine", "\u2801\u2807")
        harness.click("Add")
        alpine = ["Alpine", "\u2801\u2807", GENERAL]
        harness.type_filter("a")
        harness.select(1)

        harness.click("Delete")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, alpine])
        self.assertEqual(harness.list.selected, 1)
        self.assertEqual(harness.rows()[1], alpine)
        harness.type_filter("")
        self.assertEqual(harness.rows(), [ALPHA_CELLS, alpine])

    def test_save_writes_all_entries_not_only_filtered_entries(self) -> None:
        self.harness.type_filter("alp")

        self.assertTrue(self.harness.press_ok())

        with self.harness.path.open("r", newline="", encoding="utf-8") as fp:
            rows = list(csv.DictReader(fp))
        self.assertEqual(
            rows,
            [
                {"text": "Alpha", "braille": "\u2801", "type": "General"},
                {"text": "Beta", "braille": "\u2803", "type": "General"},
            ],
        )

    def test_edit_rejects_duplicate_source_text_outside_filter(self) -> None:
        self.harness.type_filter("bet")
        self.harness.script_entry("Alpha", "\u2803")
        self.harness.take_log()

        self.harness.click("Edit")

        self.harness.type_filter("")
        self.assertEqual(self.harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        message_boxes = [event for event in self.harness.take_log() if event[0] == "MessageBox"]
        self.assertEqual(len(message_boxes), 1)


# --- new characterization (P2-2 part A) -------------------------------------


class DictionaryEntriesDialogConstructionTest(_EditorTestCase):
    def test_construction_log_is_exact(self) -> None:
        harness = self.open_editor([ALPHA, BETA], keep_log=True)

        self.assertEqual(
            harness.take_log(),
            [
                ["Dialog.__init__", TITLE, DIALOG_STYLE],
                ["StaticText", "\u7be9\u9078\u689d\u4ef6\uff1a"],
                ["TextCtrl"],
                ["Bind", "TextCtrl", "EVT_TEXT"],
                ["StaticText", "\u5b57\u5178\u9805\u76ee"],
                ["ListCtrl", LIST_STYLE],
                ["InsertColumn", 0, "\u4f86\u6e90\u6587\u5b57", 200],
                ["InsertColumn", 1, "\u9ede\u5b57", 230],
                ["InsertColumn", 2, "\u985e\u578b", 120],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_SELECTED"],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_DESELECTED"],
                ["Bind", "ListCtrl", "EVT_LIST_ITEM_ACTIVATED"],
                ["Button", ADD],
                ["Button", EDIT],
                ["Button", DELETE],
                ["Bind", ADD, "EVT_BUTTON"],
                ["Bind", EDIT, "EVT_BUTTON"],
                ["Bind", DELETE, "EVT_BUTTON"],
                ["CreateButtonSizer", FLAGS.OK | FLAGS.CANCEL],
                ["SetLabel", "ok", "\u78ba\u5b9a"],
                ["SetLabel", "cancel", "\u53d6\u6d88"],
                ["Bind", "ok", "EVT_BUTTON"],
                ["SetSizerAndFit"],
                ["CentreOnParent"],
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertIs(harness.base_parent, harness.parent)

    def test_native_dialog_exists_before_the_dictionary_is_read(self) -> None:
        path = self.make_path()

        harness = self.open_editor(path=path, on_base_init=lambda: _write_rows(path, [ALPHA]))

        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_empty_dictionary_shows_no_rows_and_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([], keep_log=True)

        self.assertEqual(
            harness.take_log()[-6:],
            [
                ["SetItemCount", 0],
                ["Refresh"],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
            ],
        )
        self.assertEqual(harness.state(), {
            "rows": [], "selected": -1, "focused": -1, "edit": False, "delete": False, "filter": "",
        })

    def test_missing_dictionary_opens_empty_without_creating_the_file(self) -> None:
        harness = self.open_editor(None)

        self.assertEqual(harness.rows(), [])
        self.assertFalse(harness.path.exists())

    def test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog(self) -> None:
        # KNOWN BUG (P2-2 spec, Q8), pinned as it is today, NOT desired: the load error
        # escapes the constructor after the native dialog was created; nothing destroys it.
        path = self.make_path()
        path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")
        harness = _EditorHarness(path)

        with self.assertRaises(UnicodeDecodeError):
            harness.open()

        self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])

    def test_bom_dictionary_opens_with_its_rows_and_ok_after_a_change_keeps_the_bom(self) -> None:
        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
        # "\ufefftext", the editor showed no rows and OK wrote the header only. Since F-11
        # (D5) the BOM is kept (F-2 to F-9 wrote the file without it).
        harness = self.open_editor(data=b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
        harness.script_entry(*BETA)
        harness.click("Add")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), "\ufeff" + HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_ok_after_a_change_keeps_the_header_and_the_extra_columns(self) -> None:
        # F-11 (D5): "note" was dropped. The edited row keeps its note (O5), the new one has none.
        data = "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803,General\r\n".encode("utf-8")
        harness = self.open_editor(data=data)
        harness.select(1)
        harness.script_entry("Beta", "\u2803\u2803")
        harness.click("Edit")
        harness.script_entry("Gamma", "\u281b", "Braille")
        harness.click("Add")

        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,second,\u2803\u2803,General\r\nGamma,,\u281b,Braille\r\n",
        )

    def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
        harness = self.open_editor([ALPHA])

        self.assertEqual([event for event, _handler in harness.ok_button.bindings], ["EVT_BUTTON"])
        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: Cancel has no
        # handler of its own, so it discards every edit without asking.
        self.assertEqual(harness.cancel_button.bindings, [])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")

    def test_entries_dialog_binds_ok_to_its_own_button(self) -> None:
        # F-7 (F-W9): while the Settings or Text Processing dialog is open, a global lookup of
        # ID_OK finds that dialog's OK. The editor's own OK then closed without saving.
        path = self.make_path()
        _write_rows(path, [ALPHA])
        harness = _EditorHarness(path)
        other_ok = _FakeButton(harness, "other ok", "OK")
        other_cancel = _FakeButton(harness, "other cancel", "Cancel")
        harness.other_dialog_buttons = {ID_OK: other_ok, ID_CANCEL: other_cancel}
        harness.open()
        self.addCleanup(harness.close)
        harness.script_entry(*BETA)
        harness.click("Add")

        self.assertTrue(harness.press_ok())
        self.assertEqual(load_dictionary_entries(path), [DictionaryEntry(*ALPHA), DictionaryEntry(*BETA)])
        self.assertEqual((harness.ok_button.label, harness.cancel_button.label), (_("OK"), _("Cancel")))
        self.assertEqual([event for event, _handler in other_ok.bindings], [])
        self.assertEqual((other_ok.label, other_cancel.label), ("OK", "Cancel"))


class DictionaryEntriesDialogCellTextTest(_EditorTestCase):
    def test_cells_show_text_braille_and_the_translated_type_label(self) -> None:
        harness = self.open_editor([
            ["Alpha", "\u2801", "General"],
            ["\u3109\u311a\u02cb", "\u3109\u311a\u02cb", "Bopomofo"],
            ["Gamma", "\u281b", "Braille"],
        ])

        self.assertEqual(
            harness.rows(),
            [
                ["Alpha", "\u2801", GENERAL],
                ["\u3109\u311a\u02cb", "\u3109\u311a\u02cb", BOPOMOFO],
                ["Gamma", "\u281b", UNICODE_BRAILLE],
            ],
        )

    def test_unknown_column_raises_value_error(self) -> None:
        harness = self.open_editor([ALPHA])

        with self.assertRaises(ValueError) as caught:
            harness.cell(0, 3)

        self.assertEqual(str(caught.exception), "Unknown column: 3")


class DictionaryEntriesDialogFilterBehaviorTest(_EditorTestCase):
    def test_filter_uses_casefold_not_lower(self) -> None:
        harness = self.open_editor([["Stra\u00dfe", "\u280e", "General"], ["STRASSE", "", "General"]])

        harness.type_filter("STRASSE")
        self.assertEqual([row[0] for row in harness.rows()], ["Stra\u00dfe", "STRASSE"])
        harness.type_filter("\u00df")
        self.assertEqual([row[0] for row in harness.rows()], ["Stra\u00dfe", "STRASSE"])

    def test_whitespace_filter_is_literal(self) -> None:
        harness = self.open_editor([["New York", "\u281d", "General"], ALPHA])

        harness.type_filter(" ")

        self.assertEqual([row[0] for row in harness.rows()], ["New York"])

    def test_filter_does_not_match_the_type_label(self) -> None:
        harness = self.open_editor([ALPHA, BETA])

        harness.type_filter(GENERAL)

        self.assertEqual(harness.rows(), [])

    def test_selection_is_kept_by_equality_so_identical_rows_select_the_first(self) -> None:
        harness = self.open_editor([["a", "\u2801", "General"], ["b", "\u2803", "General"], ["a", "\u2801", "General"]])
        harness.select(2)

        harness.type_filter("a")

        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], ["a", "\u2801", GENERAL]])
        self.assertEqual(harness.list.selected, 0)

    def test_previous_selection_is_read_from_the_old_visible_list(self) -> None:
        harness = self.open_editor([["b1", "\u2803", "General"], ["a1", "\u2801", "General"], ["a2", "\u2801", "General"]])
        harness.select(2)

        harness.type_filter("a")

        self.assertEqual(harness.selected_row(), ["a2", "\u2801", GENERAL])
        self.assertEqual(harness.list.selected, 1)

    def test_filter_log_with_a_kept_selection_is_exact(self) -> None:
        harness = self.open_editor([ALPHA, BETA, ["Alpine", "\u2801\u2807", "General"]])
        harness.select(2)
        harness.take_log()

        harness.type_filter("alp")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Skip"],
            ],
        )
        self.assertEqual(harness.state()["focused"], 1)

    def test_empty_result_log_disables_edit_and_delete(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.take_log()

        harness.type_filter("zzz")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 0],
                ["Refresh"],
                ["Enable", EDIT, False],
                ["Enable", DELETE, False],
                ["Skip"],
            ],
        )

    def test_filter_that_keeps_the_selected_row_index_deselects_it_first(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.take_log()

        harness.type_filter("a")

        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
                ["Skip"],
            ],
        )


class DictionaryEntriesDialogAddTest(_EditorTestCase):
    def test_cancel_changes_nothing(self) -> None:
        harness = self.open_editor([ALPHA])
        before = harness.state()
        harness.script_cancel()

        harness.click("Add")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", None]])
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_duplicate_of_a_hidden_entry_is_rejected_with_the_exact_message(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("bet")
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u281b", "Braille")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry
        # is discarded; the entry dialog is not opened again.
        self.assertEqual(harness.state(), before)
        self.assertEqual(harness.script, [])

    def test_case_different_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.script_entry("alpha", "\u2801")

        harness.click("Add")

        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["alpha", "\u2801", GENERAL]])

    def test_new_entry_is_appended_at_the_end_selected_and_focused(self) -> None:
        harness = self.open_editor([BETA, ALPHA])
        harness.script_entry("Aardvark", "\u2801\u2801")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["SetItemCount", 3],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 2, True],
                ["Focus", 2],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [BETA_CELLS, ALPHA_CELLS, ["Aardvark", "\u2801\u2801", GENERAL]])
        self.assertEqual((harness.list.selected, harness.list.focused), (2, 2))

    def test_nonmatching_filter_is_cleared_with_change_value_before_the_list_update(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("alp")
        harness.take_log()
        harness.script_entry("Gamma", "\u281b")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", None],
                ["ChangeValue", ""],
                ["SetItemCount", 3],
                ["Refresh"],
                ["Select", 0, False],
                ["Select", 2, True],
                ["Focus", 2],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )

    def test_matching_filter_is_kept_without_touching_the_filter_box(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.type_filter("alp")
        harness.take_log()
        harness.script_entry("Alpine", "\u2801\u2807")

        harness.click("Add")

        log = harness.take_log()
        self.assertNotIn("ChangeValue", [event[0] for event in log])
        self.assertNotIn("SetValue", [event[0] for event in log])
        self.assertEqual(harness.filter.value, "alp")
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Alpine", "\u2801\u2807", GENERAL]])


class DictionaryEntriesDialogEditTest(_EditorTestCase):
    def test_edit_button_opens_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.take_log()
        harness.script_cancel()

        harness.click("Edit")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", BETA]])
        self.assertEqual(harness.entry_dialog_parents, [harness.dialog])

    def test_activation_edits_the_selected_entry(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        harness.take_log()
        harness.script_entry("Bravo", "\u2803\u2817")

        harness.activate()

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", BETA],
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, False],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Bravo", "\u2803\u2817", GENERAL]])

    def test_no_selection_opens_nothing(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.deselect()
        harness.take_log()

        harness.click("Edit")
        harness.activate()

        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.entry_dialog_parents, [])

    def test_cancel_changes_nothing(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        before = harness.state()
        harness.script_cancel()

        harness.click("Edit")

        self.assertEqual(harness.take_log(), [["AddSymbolDialog", ALPHA]])
        self.assertEqual(harness.state(), before)

    def test_same_source_text_is_accepted(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.script_entry("Alpha", "\u2801\u2801", "Braille")

        harness.click("Edit")

        self.assertEqual(harness.rows(), [["Alpha", "\u2801\u2801", UNICODE_BRAILLE], BETA_CELLS])
        self.assertEqual(harness.list.selected, 0)

    def test_duplicate_is_rejected_with_the_exact_message_and_nothing_changes(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)
        before = harness.state()
        harness.take_log()
        harness.script_entry("Alpha", "\u2803")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", BETA],
                ["MessageBox", _duplicate_message("Alpha"), ERROR_TITLE, ERROR_FLAGS],
            ],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
        self.assertEqual(harness.state(), before)

    def test_identical_rows_edit_of_the_selected_row_can_keep_its_text(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made its own text
        # a duplicate. Fixed by F-11 (D9, O6).
        harness = self.open_editor([["a", "\u2801", "General"], BETA, ["a", "\u2801", "General"]])
        harness.select(2)
        harness.take_log()
        harness.script_entry("a", "\u2803")

        harness.click("Edit")

        self.assertNotIn("MessageBox", [event[0] for event in harness.take_log()])
        self.assertEqual(harness.rows(), [["a", "\u2801", GENERAL], BETA_CELLS, ["a", "\u2803", GENERAL]])
        self.assertEqual(harness.list.selected, 2)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "a,\u2801,General\r\nBeta,\u2803,General\r\na,\u2803,General\r\n",
        )

    def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
        harness = self.open_editor([ALPHA, ["Alpine", "\u2801\u2807", "General"], BETA])
        harness.type_filter("alp")
        harness.select(1)
        harness.take_log()
        harness.script_entry("Gamma", "\u281b")

        harness.click("Edit")

        self.assertEqual(
            harness.take_log(),
            [
                ["AddSymbolDialog", ["Alpine", "\u2801\u2807", "General"]],
                ["SetItemCount", 1],
                ["Refresh"],
                ["Select", 0, True],
                ["Focus", 0],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.filter.value, "alp")
        self.assertEqual(harness.rows(), [ALPHA_CELLS])


class DictionaryEntriesDialogDeleteTest(_EditorTestCase):
    def test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index(self) -> None:
        harness = self.open_editor([ALPHA, BETA, ["Gamma", "\u281b", "General"]])
        harness.select(1)
        harness.take_log()

        harness.click("Delete")

        # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: no confirmation.
        self.assertEqual(
            harness.take_log(),
            [
                ["SetItemCount", 2],
                ["Refresh"],
                ["Select", 1, False],
                ["Select", 1, True],
                ["Focus", 1],
                ["Enable", EDIT, True],
                ["Enable", DELETE, True],
            ],
        )
        self.assertEqual(harness.rows(), [ALPHA_CELLS, ["Gamma", "\u281b", GENERAL]])

    def test_deleting_the_last_row_selects_the_new_last_row(self) -> None:
        harness = self.open_editor([ALPHA, BETA])
        harness.select(1)

        harness.click("Delete")

        self.assertEqual(harness.rows(), [ALPHA_CELLS])
        self.assertEqual((harness.list.selected, harness.list.focused), (0, 0))

    def test_deleting_the_only_row_clears_the_selection(self) -> None:
        harness = self.open_editor([ALPHA])

        harness.click("Delete")

        self.assertEqual(harness.state(), {
            "rows": [], "selected": -1, "focused": 0, "edit": False, "delete": False, "filter": "",
        })

    def test_no_selection_deletes_nothing(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.deselect()
        harness.take_log()

        harness.click("Delete")

        self.assertEqual(harness.take_log(), [])
        self.assertEqual(harness.rows(), [ALPHA_CELLS])

    def test_identical_rows_delete_removes_the_selected_row(self) -> None:
        # Was the P2-2 Q4 KNOWN BUG (second half): the first equal row went, not the selected
        # one. Fixed by F-11 (D9); the remaining equal row gets the selection, as before.
        data = (HEADER + "a,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\na,\u2801,General,fourth\r\n")
        harness = self.open_editor(data=data.replace(HEADER, "text,braille,type,note\r\n").encode("utf-8"))
        harness.select(3)

        harness.click("Delete")

        self.assertEqual(
            harness.rows(),
            [["a", "\u2801", GENERAL], BETA_CELLS, ["a", "\u2801", UNICODE_BRAILLE]],
        )
        self.assertEqual(harness.list.selected, 0)
        self.assertTrue(harness.press_ok())
        self.assertEqual(
            harness.saved_csv(),
            "text,braille,type,note\r\na,\u2801,General,first\r\nBeta,\u2803,General,\r\na,\u2801,Braille,\r\n",
        )


class DictionaryEntriesDialogOkTest(_EditorTestCase):
    def test_fsync_is_skipped_only_while_the_editor_is_open(self) -> None:
        real_fsync = os.fsync
        harness = self.open_editor([ALPHA])

        self.assertIs(os.fsync, _skip_fsync)
        harness.close()
        self.assertIs(os.fsync, real_fsync)

    def test_ok_saves_the_full_list_in_order_and_closes(self) -> None:
        harness = self.open_editor([BETA, ALPHA])
        harness.script_entry("Gamma", "\u281b", "Braille")
        harness.click("Add")
        harness.type_filter("gam")
        harness.take_log()

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.take_log(), [["Skip"]])
        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Beta,\u2803,General\r\nAlpha,\u2801,General\r\nGamma,\u281b,Braille\r\n",
        )

    def test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form(self) -> None:
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file, stripping the shown rows and writing an unknown type as
        # General. Since F-4 the rows the editor does not show (blank source text,
        # invalid Bopomofo) are written back unchanged at their place.
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
            ",\u2803,General\n"
            "Zhuyin,invalid,Bopomofo\n"
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)

        self.assertTrue(harness.press_ok())

        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Alpha,\u2801,General\r\n,\u2803,General\r\nZhuyin,invalid,Bopomofo\r\nBeta,\u2803,General\r\n",
        )

    def test_missing_parent_directory_is_created(self) -> None:
        path = self.make_path("nested") / "deeper" / "dictionary.csv"
        harness = self.open_editor(path=path)
        harness.script_entry("Alpha", "\u2801")
        harness.click("Add")

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\n")

    def test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds(self) -> None:
        harness = self.open_editor([ALPHA])
        harness.script_entry("Beta", "\u2803")
        harness.click("Add")
        harness.path.unlink()
        harness.path.mkdir()
        harness.take_log()

        skipped = harness.press_ok()

        self.assertFalse(skipped)
        log = harness.take_log()
        self.assertEqual([[kind, title, flags] for kind, _message, title, flags in log], [["MessageBox", ERROR_TITLE, ERROR_FLAGS]])
        # Installing the temporary file onto the directory fails; the error text differs
        # between Linux and Windows, but both name the dictionary last (F-2 spec D5).
        message = log[0][1]
        self.assertTrue(message.startswith("\u5132\u5b58\u5931\u6557\uff1a"), message)
        self.assertTrue(message.endswith(" -> " + repr(str(harness.path))), message)
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
        self.assertTrue(harness.path.is_dir())
        harness.path.rmdir()
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds(self) -> None:
        harness = self.open_editor([ALPHA])
        original = harness.path.read_bytes()
        harness.script_entry("Beta", "\u2803")
        harness.click("Add")
        harness.take_log()

        with patch("os.replace", side_effect=PermissionError(13, "denied")):
            skipped = harness.press_ok()

        self.assertFalse(skipped)
        self.assertEqual(
            harness.take_log(),
            [["MessageBox", "\u5132\u5b58\u5931\u6557\uff1a[Errno 13] denied", ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.path.read_bytes(), original)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_dictionary_without_write_access_shows_the_message_and_keeps_the_file(self) -> None:
        # A read-only dictionary failed in the old in-place open("w"); the atomic save
        # keeps that verdict and its message instead of renaming over the file.
        harness = self.open_editor([ALPHA])
        original = harness.path.read_bytes()
        harness.script_entry("Beta", "\u2803")
        harness.click("Add")
        harness.take_log()

        with patch("os.access", return_value=False):
            skipped = harness.press_ok()

        self.assertFalse(skipped)
        self.assertEqual(
            harness.take_log(),
            [[
                "MessageBox",
                "\u5132\u5b58\u5931\u6557\uff1a[Errno 13] Permission denied: " + repr(str(harness.path)),
                ERROR_TITLE,
                ERROR_FLAGS,
            ]],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        self.assertEqual(harness.path.read_bytes(), original)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")

    def test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged(self) -> None:
        # Was the P2-2 Q3/Q7 KNOWN BUG (data loss), fixed by F-2: a non-OSError escaped
        # the OK handler without a message and the file was left truncated before the
        # failing row. The same edit is kept as the regression scenario.
        harness = self.open_editor([ALPHA, BETA])
        original = harness.path.read_bytes()
        harness.script_entry("\ud800", "\u2801")
        harness.click("Edit")
        harness.take_log()

        skipped = harness.press_ok()

        self.assertFalse(skipped)
        self.assertEqual(
            harness.take_log(),
            [[
                "MessageBox",
                "\u5132\u5b58\u5931\u6557\uff1a'utf-8' codec can't encode character '\\ud800' in position 0: surrogates not allowed",
                ERROR_TITLE,
                ERROR_FLAGS,
            ]],
        )
        self.assertEqual(harness.message_box_parents, [harness.dialog])
        self.assertEqual(harness.path.read_bytes(), original)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
        self.assertEqual(harness.rows(), [["\ud800", "\u2801", GENERAL], BETA_CELLS])


# --- the dialog delegates to the model (P2-2 part C) -------------------------


class DictionaryEntriesDialogHiddenRowsTest(_EditorTestCase):
    """Rows the editor cannot show are kept, hidden, through OK (F-4, F-W11)."""

    def test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical(self) -> None:
        # F-W11: OK used to delete the two Bopomofo rows the editor cannot show (4 lines -> 2).
        harness = self.open_editor(data=DICT_BADBOPO)

        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])

    def test_deleting_every_shown_row_keeps_the_hidden_rows(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.select(0)
        harness.click("Delete")

        self.assertEqual(harness.rows(), [])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + BADBOPO_HIDDEN_ROWS)

    def test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.script_entry("\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", "Bopomofo")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [["AddSymbolDialog", None], ["MessageBox", _duplicate_message("\u809a\u5b50"), ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)


class DictionaryEntriesDialogModelTest(_EditorTestCase):
    def test_dictionary_path_is_required(self) -> None:
        parameter = inspect.signature(DictionaryEntriesDialog.__init__).parameters["dictionary_path"]

        self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_model_is_loaded_from_the_dictionary_path(self) -> None:
        harness = self.open_editor([ALPHA, BETA])

        self.assertIsInstance(harness.dialog._model, DictionaryEntryListModel)
        self.assertEqual(harness.dialog._model.entries, (DictionaryEntry(*ALPHA), DictionaryEntry(*BETA)))
        self.assertEqual(harness.dialog.dictionary_path, harness.path)


# --- golden trace -----------------------------------------------------------

TRACE_PATH = Path(__file__).resolve().parent / "fixtures" / "dictionary_entries_trace.json"
TRACE_SEQUENCES = 40
TRACE_ACTIONS = 25
TRACE_CSV = (
    "text,braille,type\r\n"
    "a,\u2801,General\r\n"
    " Ab , SS ,General\r\n"
    "a,\u2801,General\r\n"
    ",\u2803,General\r\n"
    "Stra\u00dfe,\u280e,Braille\r\n"
    "STRASSE,,Unknown\r\n"
    "zz,ab,Bopomofo\r\n"
)
_TRACE_TEXTS = ("a", "A", "ab", "Ab", "Stra\u00dfe", "STRASSE", "b", "ss")
_TRACE_BRAILLE = ("\u2801", "ab", "", "SS", "\u2803")
_TRACE_TYPES = ("General", "Bopomofo", "Braille")
_TRACE_FILTERS = ("", "", "a", "A", "b", "ab", "ss", "STRASSE", "\u00df", " ", "\u2801", "x", "General")
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")
# The two TRACE_CSV rows the editor does not show (blank source text, invalid Bopomofo).
# The fixture was recorded before F-4, when OK dropped them; since F-4 OK writes them
# back unchanged, so the replay checks them and removes them before comparing.
_TRACE_KEPT_ROWS = (",\u2803,General", "zz,ab,Bopomofo")


def _random_trace_action(rng: random.Random, harness: _EditorHarness, index: int) -> list:
    kind = rng.choice(_TRACE_KINDS)
    if kind == "filter":
        return ["filter", rng.choice(_TRACE_FILTERS)]
    if kind == "select":
        count = harness.list.item_count
        return ["select", rng.randrange(count)] if count else ["deselect"]
    if kind in ("deselect", "delete"):
        return [kind]
    if rng.random() < 0.2:
        return [kind, None]
    text = f"n{index}" if rng.random() < 0.3 else rng.choice(_TRACE_TEXTS)
    return [kind, [text, rng.choice(_TRACE_BRAILLE), rng.choice(_TRACE_TYPES)]]


def _perform_trace_action(harness: _EditorHarness, action: list) -> None:
    kind = action[0]
    if kind == "filter":
        harness.type_filter(action[1])
    elif kind == "select":
        harness.select(action[1])
    elif kind == "deselect":
        harness.deselect()
    elif kind == "delete":
        harness.click("Delete")
    else:
        if action[1] is None:
            harness.script_cancel()
        else:
            harness.script_entry(*action[1])
        if kind == "add":
            harness.click("Add")
        elif kind == "edit":
            harness.click("Edit")
        else:
            harness.activate()
        harness.script.clear()


def _run_trace_sequence(path: Path, next_action) -> list[dict]:
    """Open the editor on ``TRACE_CSV``, run 25 actions and OK; return every step's observations.

    A step's ``state`` has no ``rows`` when the visible rows did not change
    since the previous step (keeps the fixture small).
    """
    path.write_bytes(TRACE_CSV.encode("utf-8"))
    with _EditorHarness(path) as harness:
        steps = [{"action": ["open"], "log": harness.take_log(), "state": harness.state()}]
        for index in range(TRACE_ACTIONS):
            action = next_action(harness, index)
            _perform_trace_action(harness, action)
            steps.append({"action": action, "log": harness.take_log(), "state": harness.state()})
        harness.press_ok()
        steps.append({
            "action": ["ok"],
            "log": harness.take_log(),
            "state": harness.state(),
            "csv": harness.saved_csv(),
        })
    previous_rows = None
    for step in steps:
        rows = step["state"]["rows"]
        if rows == previous_rows:
            del step["state"]["rows"]
        previous_rows = rows
    return steps


def write_trace_fixture(path: Path = TRACE_PATH) -> None:
    """Record the golden trace. Run once, on the pre-P2-2 editor; never to make a test pass."""
    sequences = []
    _DIALOG_SCOPE.activate()
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for seed in range(TRACE_SEQUENCES):
                rng = random.Random(seed)
                sequences.append(_run_trace_sequence(
                    Path(temp_dir) / f"trace{seed}.csv",
                    lambda harness, index, rng=rng: _random_trace_action(rng, harness, index),
                ))
    finally:
        _DIALOG_SCOPE.deactivate()
    lines = ["["]
    for seed, steps in enumerate(sequences):
        lines.append("[")
        lines.append(",\n".join(json.dumps(step, ensure_ascii=False, separators=(",", ":")) for step in steps))
        lines.append("]," if seed < len(sequences) - 1 else "]")
    lines.append("]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


class DictionaryEntriesTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sequences = json.loads(TRACE_PATH.read_text(encoding="utf-8"))

    def test_fixture_has_40_sequences_of_27_steps(self) -> None:
        self.assertEqual(len(self.sequences), TRACE_SEQUENCES)
        for steps in self.sequences:
            self.assertEqual([step["action"][0] for step in steps[::26]], ["open", "ok"])
            self.assertEqual(len(steps), TRACE_ACTIONS + 2)

    def test_replay_matches_every_recorded_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for seed, expected in enumerate(self.sequences):
                with self.subTest(seed=seed):
                    actual = _run_trace_sequence(
                        Path(temp_dir) / f"trace{seed}.csv",
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                    )
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first kept row.
                    lines = actual[-1]["csv"].split("\r\n")
                    self.assertEqual([line for line in lines if line in _TRACE_KEPT_ROWS], list(_TRACE_KEPT_ROWS))
                    actual[-1]["csv"] = "\r\n".join(line for line in lines if line not in _TRACE_KEPT_ROWS)
                    for index, (got, want) in enumerate(zip(actual, expected)):
                        self.assertEqual(got, want, f"seed {seed}, step {index}: {want['action']}")


if __name__ == '__main__':
    unittest.main()
