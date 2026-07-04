import csv
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _AutoModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        sub_name = f'{self.__name__}.{name}'
        if sub_name not in sys.modules:
            sub = _AutoModule(sub_name)
            sys.modules[sub_name] = sub
        return sys.modules[sub_name]

    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self


_MODULE_UNDER_TEST_NAME = '_speech_symbols_dialog_under_test'
_DIALOG_PATH = Path(__file__).resolve().parents[1] / 'dialog.py'
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
_SCOPED_RESTORE_ROOTS = {
    'Bopomofo',
    'PIL',
    'braille',
    'bs4',
    'dialog',
    'dictionaries',
    'documents',
    'ebooklib',
    'lxml',
    'mammoth',
    'markdown',
    'markdownify',
    'pymupdf',
    'pypdf',
    'translation',
    'wx',
}


def _make_wx_stub() -> _AutoModule:
    wx_stub = _AutoModule('wx')
    wx_stub.Dialog = type('Dialog', (), {})
    wx_stub.ListCtrl = type('ListCtrl', (), {})
    wx_stub.Window = type('Window', (), {})
    wx_stub.CommandEvent = type('CommandEvent', (), {})
    wx_stub.ListEvent = type('ListEvent', (), {})
    wx_stub.NOT_FOUND = -1
    wx_stub.OK = 1
    wx_stub.ICON_ERROR = 2
    wx_stub.MessageBox = lambda *args, **kwargs: None
    return wx_stub


def _restore_module_binding(name: str, existed: bool, module: types.ModuleType | None) -> None:
    if existed:
        sys.modules[name] = module
    else:
        sys.modules.pop(name, None)


def _install_scoped_import_stubs() -> None:
    sys.modules['wx'] = _make_wx_stub()

    for name in ('mammoth', 'pymupdf', 'bs4', 'pypdf', 'markdown', 'markdownify', 'PIL'):
        sys.modules.setdefault(name, _AutoModule(name))

    if 'lxml' not in sys.modules:
        lxml = _AutoModule('lxml')
        lxml.etree = _AutoModule('lxml.etree')
        lxml.html = _AutoModule('lxml.html')
        sys.modules['lxml'] = lxml
        sys.modules['lxml.etree'] = lxml.etree
        sys.modules['lxml.html'] = lxml.html

    if 'ebooklib' not in sys.modules:
        ebooklib = _AutoModule('ebooklib')
        ebooklib.epub = _AutoModule('ebooklib.epub')
        sys.modules['ebooklib'] = ebooklib
        sys.modules['ebooklib.epub'] = ebooklib.epub


def _restore_scoped_modules(previous_modules: dict[str, types.ModuleType]) -> None:
    for name in list(sys.modules):
        if name == _MODULE_UNDER_TEST_NAME:
            del sys.modules[name]
            continue
        if name.split('.')[0] in _SCOPED_RESTORE_ROOTS and name not in previous_modules:
            del sys.modules[name]

    for name, previous in previous_modules.items():
        sys.modules[name] = previous


def _load_dialog_module() -> types.ModuleType:
    previous_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.split('.')[0] in _SCOPED_RESTORE_ROOTS
    }
    try:
        _install_scoped_import_stubs()
        spec = importlib.util.spec_from_file_location(_MODULE_UNDER_TEST_NAME, _DIALOG_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f'Unable to load dialog module from {_DIALOG_PATH}')
        module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_UNDER_TEST_NAME] = module
        spec.loader.exec_module(module)
        return module
    finally:
        _restore_scoped_modules(previous_modules)


dialog = _load_dialog_module()
DictionaryEntry = dialog.DictionaryEntry
CallbackVirtualListCtrl = dialog.CallbackVirtualListCtrl
SpeechSymbolsDialog = dialog.SpeechSymbolsDialog
load_dictionary_entries = dialog.load_dictionary_entries


class _FakeListCtrl:
    def __init__(self) -> None:
        self.item_count = 0
        self.selected = -1
        self.focused = -1
        self.refresh_count = 0

    def GetFirstSelected(self) -> int:
        return self.selected

    def SetItemCount(self, count: int) -> None:
        self.item_count = count
        if self.selected >= count:
            self.selected = -1

    def GetItemCount(self) -> int:
        return self.item_count

    def Select(self, index: int, on: bool = True) -> None:
        if on:
            self.selected = index
        elif self.selected == index:
            self.selected = -1

    def Focus(self, index: int) -> None:
        self.focused = index

    def Refresh(self) -> None:
        self.refresh_count += 1


class _FakeTextCtrl:
    def __init__(self, value: str = '') -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value

    def ChangeValue(self, value: str) -> None:
        self.value = value


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = True
        self.bindings: list[tuple[object, object]] = []

    def Enable(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def Bind(self, event: object, handler: object) -> None:
        self.bindings.append((event, handler))


class _FakeSizer:
    def Add(self, *_args, **_kwargs) -> None:
        pass


class _FakeControl:
    def __init__(self, *_args, **_kwargs) -> None:
        self.bindings: list[tuple[object, object]] = []

    def Bind(self, event: object, handler: object) -> None:
        self.bindings.append((event, handler))


class _FakeBuildListCtrl(_FakeControl):
    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()
        self.columns: list[tuple[int, str, int | None]] = []

    def InsertColumn(self, index: int, label: str, width: int | None = None) -> None:
        self.columns.append((index, label, width))


class _FakeEvent:
    def __init__(self) -> None:
        self.skipped = False

    def Skip(self) -> None:
        self.skipped = True


def _make_dialog(entries: list[DictionaryEntry]) -> SpeechSymbolsDialog:
    dialog = object.__new__(SpeechSymbolsDialog)
    dialog.entries = list(entries)
    dialog.filtered_entries = list(entries)
    dialog.filter_ctrl = _FakeTextCtrl()
    dialog.list_ctrl = _FakeListCtrl()
    dialog.list_ctrl.SetItemCount(len(entries))
    dialog.edit_button = _FakeButton()
    dialog.remove_button = _FakeButton()
    if entries:
        dialog.list_ctrl.Select(0)
    dialog._update_button_states()
    return dialog


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

            with patch.object(dialog, "normalize_zhuyin_sequence", side_effect=ValueError):
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

        self.assertTrue(hasattr(loaded_dialog, 'DictionaryEntry'))
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


class SpeechSymbolsDialogFilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.alpha = DictionaryEntry('Alpha', '\u2801', 'General')
        self.beta = DictionaryEntry('Beta', 'Needle', 'Bopomofo')
        self.dialog = _make_dialog([self.alpha, self.beta])

    def test_empty_filter_shows_all_entries(self) -> None:
        self.dialog.filter_entries('')

        self.assertEqual(self.dialog.filtered_entries, [self.alpha, self.beta])
        self.assertEqual(self.dialog.list_ctrl.item_count, 2)

    def test_filter_matches_source_text_case_insensitively(self) -> None:
        self.dialog.filter_entries('ALP')

        self.assertEqual(self.dialog.filtered_entries, [self.alpha])

    def test_filter_matches_braille_case_insensitively(self) -> None:
        self.dialog.filter_entries('NEED')

        self.assertEqual(self.dialog.filtered_entries, [self.beta])

    def test_filter_does_not_match_entry_type(self) -> None:
        self.dialog.filter_entries('bopomofo')

        self.assertEqual(self.dialog.filtered_entries, [])

    def test_item_text_uses_visible_entry_and_localized_type_label(self) -> None:
        self.dialog.filtered_entries = [self.beta]

        self.assertEqual(self.dialog._get_item_text(0, 0), 'Beta')
        self.assertEqual(self.dialog._get_item_text(0, 1), 'Needle')
        self.assertEqual(self.dialog._get_item_text(0, 2), '\u6ce8\u97f3')

    def test_filter_preserves_selected_entry_when_it_remains_visible(self) -> None:
        self.dialog.list_ctrl.Select(1)

        self.dialog.filter_entries("e")

        self.assertIs(self.dialog.filtered_entries[self.dialog.list_ctrl.selected], self.beta)
        self.assertTrue(self.dialog.edit_button.enabled)
        self.assertTrue(self.dialog.remove_button.enabled)

    def test_filter_falls_back_to_first_entry_when_selection_is_hidden(self) -> None:
        self.dialog.list_ctrl.Select(1)

        self.dialog.filter_entries("alp")

        self.assertEqual(self.dialog.list_ctrl.selected, 0)
        self.assertIs(self.dialog.filtered_entries[0], self.alpha)

    def test_empty_result_clears_selection_and_disables_edit_and_delete(self) -> None:
        self.dialog.filter_entries("missing")

        self.assertEqual(self.dialog.list_ctrl.selected, -1)
        self.assertFalse(self.dialog.edit_button.enabled)
        self.assertFalse(self.dialog.remove_button.enabled)

    def test_filter_event_applies_current_text_and_is_skipped(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("alp")
        event = _FakeEvent()

        self.dialog._on_filter_changed(event)

        self.assertEqual(self.dialog.filtered_entries, [self.alpha])
        self.assertTrue(event.skipped)


class SpeechSymbolsDialogBuildUiTest(unittest.TestCase):
    def test_build_ui_binds_item_activation_to_edit_handler(self) -> None:
        list_ctrls: list[_FakeBuildListCtrl] = []

        class _FakeWx:
            VERTICAL = object()
            HORIZONTAL = object()
            LEFT = 1
            RIGHT = 2
            TOP = 4
            BOTTOM = 8
            ALL = 16
            EXPAND = 32
            LC_REPORT = 64
            BORDER_SUNKEN = 128
            LC_SINGLE_SEL = 256
            LC_VIRTUAL = 512
            OK = 1024
            CANCEL = 2048
            EVT_TEXT = object()
            EVT_LIST_ITEM_SELECTED = object()
            EVT_LIST_ITEM_DESELECTED = object()
            EVT_LIST_ITEM_ACTIVATED = object()
            EVT_BUTTON = object()
            ID_OK = 1

            @staticmethod
            def BoxSizer(_orientation: object) -> _FakeSizer:
                return _FakeSizer()

            @staticmethod
            def StaticText(*_args, **_kwargs) -> object:
                return object()

            @staticmethod
            def TextCtrl(*_args, **_kwargs) -> _FakeControl:
                return _FakeControl()

            @staticmethod
            def Button(*_args, **_kwargs) -> _FakeButton:
                return _FakeButton()

        def _fake_list_ctrl_factory(*_args, **_kwargs) -> _FakeBuildListCtrl:
            list_ctrl = _FakeBuildListCtrl()
            list_ctrls.append(list_ctrl)
            return list_ctrl

        speech_dialog = object.__new__(SpeechSymbolsDialog)
        speech_dialog.CreateButtonSizer = lambda _flags: None
        speech_dialog.FindWindowById = lambda _window_id: None

        with patch.object(dialog, 'wx', _FakeWx), patch.object(
            dialog,
            'CallbackVirtualListCtrl',
            side_effect=_fake_list_ctrl_factory,
        ), patch.object(dialog, 'finalize_dialog_layout'):
            speech_dialog._build_ui()

        self.assertEqual(
            list_ctrls[0].bindings,
            [
                (_FakeWx.EVT_LIST_ITEM_SELECTED, speech_dialog._on_selection_changed),
                (_FakeWx.EVT_LIST_ITEM_DESELECTED, speech_dialog._on_selection_changed),
                (_FakeWx.EVT_LIST_ITEM_ACTIVATED, speech_dialog._on_item_activated),
            ],
        )


class SpeechSymbolsDialogMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.alpha = DictionaryEntry("Alpha", "\u2801", "General")
        self.beta = DictionaryEntry("Beta", "\u2803", "General")
        self.dialog = _make_dialog([self.alpha, self.beta])

    def test_add_matching_entry_keeps_filter_and_selects_new_entry(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("alp")
        self.dialog.filter_entries("alp")
        added = DictionaryEntry("Alphabet", "\u2801\u2803", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: added

        self.dialog._on_add_clicked(None)

        self.assertEqual(self.dialog.filter_ctrl.GetValue(), "alp")
        self.assertEqual(self.dialog.filtered_entries, [self.alpha, added])
        self.assertIs(
            self.dialog.filtered_entries[self.dialog.list_ctrl.selected],
            added,
        )

    def test_add_nonmatching_entry_clears_filter_and_selects_new_entry(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("alp")
        self.dialog.filter_entries("alp")
        added = DictionaryEntry("Gamma", "\u281b", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: added

        self.dialog._on_add_clicked(None)

        self.assertEqual(self.dialog.filter_ctrl.GetValue(), "")
        self.assertEqual(self.dialog.filtered_entries, [self.alpha, self.beta, added])
        self.assertIs(
            self.dialog.filtered_entries[self.dialog.list_ctrl.selected],
            added,
        )

    def test_edit_visible_entry_updates_full_list_and_preserves_selection(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("bet")
        self.dialog.filter_entries("bet")
        updated = DictionaryEntry("Better", "\u2803\u2801", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: updated

        self.dialog._edit_selected()

        self.assertEqual(self.dialog.entries, [self.alpha, updated])
        self.assertEqual(self.dialog.filtered_entries, [updated])
        self.assertIs(self.dialog.filtered_entries[self.dialog.list_ctrl.selected], updated)

    def test_edit_entry_that_stops_matching_removes_it_from_visible_list(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("bet")
        self.dialog.filter_entries("bet")
        updated = DictionaryEntry("Gamma", "\u281b", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: updated

        self.dialog._edit_selected()

        self.assertEqual(self.dialog.entries, [self.alpha, updated])
        self.assertEqual(self.dialog.filtered_entries, [])
        self.assertEqual(self.dialog.list_ctrl.selected, -1)
        self.assertFalse(self.dialog.edit_button.enabled)
        self.assertFalse(self.dialog.remove_button.enabled)

    def test_delete_filtered_entry_selects_nearest_remaining_entry(self) -> None:
        alpine = DictionaryEntry("Alpine", "\u2801\u2807", "General")
        self.dialog.entries.append(alpine)
        self.dialog.filter_ctrl.ChangeValue("a")
        self.dialog.filter_entries("a")
        self.dialog.list_ctrl.Select(1)

        self.dialog._on_remove_clicked(None)

        self.assertEqual(self.dialog.entries, [self.alpha, alpine])
        self.assertEqual(self.dialog.filtered_entries, [self.alpha, alpine])
        self.assertEqual(self.dialog.list_ctrl.selected, 1)
        self.assertIs(self.dialog.filtered_entries[1], alpine)

    def test_save_writes_all_entries_not_only_filtered_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dictionary.csv"
            self.dialog.dictionary_path = path
            self.dialog.filter_entries("alp")

            self.dialog._save_entries()

            with path.open("r", newline="", encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
        self.assertEqual(
            rows,
            [
                {"text": "Alpha", "braille": "\u2801", "type": "General"},
                {"text": "Beta", "braille": "\u2803", "type": "General"},
            ],
        )

    @patch.object(dialog.wx, 'MessageBox')
    def test_edit_rejects_duplicate_source_text_outside_filter(
        self,
        message_box,
    ) -> None:
        self.dialog.filter_ctrl.ChangeValue("bet")
        self.dialog.filter_entries("bet")
        self.dialog._open_entry_dialog = lambda _entry=None: DictionaryEntry(
            "Alpha",
            "\u2803",
            "General",
        )

        self.dialog._edit_selected()

        self.assertEqual(self.dialog.entries, [self.alpha, self.beta])
        message_box.assert_called_once()


if __name__ == '__main__':
    unittest.main()
