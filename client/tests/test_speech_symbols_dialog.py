import csv
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


if 'wx' not in sys.modules:
    wx_stub = _AutoModule('wx')
    wx_stub.Dialog = type('Dialog', (), {})
    wx_stub.ListCtrl = type('ListCtrl', (), {})
    wx_stub.Window = type('Window', (), {})
    wx_stub.CommandEvent = type('CommandEvent', (), {})
    wx_stub.ListEvent = type('ListEvent', (), {})
    wx_stub.NOT_FOUND = -1
    sys.modules['wx'] = wx_stub

for _name in ('mammoth', 'pymupdf', 'bs4', 'pypdf', 'markdown', 'markdownify', 'PIL'):
    sys.modules.setdefault(_name, _AutoModule(_name))

_lxml = _AutoModule('lxml')
_lxml.etree = _AutoModule('lxml.etree')
_lxml.html = _AutoModule('lxml.html')
sys.modules.setdefault('lxml', _lxml)
sys.modules.setdefault('lxml.etree', _lxml.etree)
sys.modules.setdefault('lxml.html', _lxml.html)

_ebooklib = _AutoModule('ebooklib')
_ebooklib.epub = _AutoModule('ebooklib.epub')
sys.modules.setdefault('ebooklib', _ebooklib)
sys.modules.setdefault('ebooklib.epub', _ebooklib.epub)


from dialog import (
    DictionaryEntry,
    DictionaryEntryListCtrl,
    SpeechSymbolsDialog,
)


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

    def Enable(self, enabled: bool = True) -> None:
        self.enabled = enabled


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


class DictionaryEntryListCtrlTest(unittest.TestCase):
    def test_get_item_text_delegates_to_callback(self) -> None:
        control = object.__new__(DictionaryEntryListCtrl)
        control._get_item_text = lambda item, column: f'{item}:{column}'

        self.assertEqual(control.OnGetItemText(4, 2), '4:2')


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

    @patch("dialog.wx.MessageBox")
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
