import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from tests.test_speech_symbols_dialog import dialog


DictionaryManagementDialog = dialog.DictionaryManagementDialog


class _FakeListCtrl:
	def __init__(self, width: int = 500):
		self.item_count = 0
		self.selected = -1
		self.focused = -1
		self.refresh_count = 0
		self.width = width
		self.column_widths: dict[int, int] = {}

	def SetItemCount(self, count):
		self.item_count = count

	def Refresh(self):
		self.refresh_count += 1

	def GetFirstSelected(self):
		return self.selected

	def Select(self, index, on=True):
		self.selected = index if on else -1

	def Focus(self, index):
		self.focused = index

	def GetClientSize(self):
		return type("Size", (), {"width": self.width})()

	def GetTextExtent(self, text):
		return (len(text) * 8, 16)

	def SetColumnWidth(self, column, width):
		self.column_widths[column] = width


def _make_dialog(dictionary_dir, names):
	target = object.__new__(DictionaryManagementDialog)
	target.dictionary_dir = Path(dictionary_dir)
	target._dictionary_names = list(names)
	target._dictionary_counts = {}
	target._selected_name = names[0] if names else ""
	target.list_ctrl = _FakeListCtrl()
	target.add_button = Mock()
	target.delete_button = Mock()
	target.rename_button = Mock()
	target.edit_button = Mock()
	target.import_button = Mock()
	target.export_button = Mock()
	target.EndModal = Mock()
	return target


class DictionaryManagementVirtualListTest(unittest.TestCase):
	def test_refresh_sets_virtual_count_and_valid_entry_counts(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "alpha.csv"
			with path.open("w", newline="", encoding="utf-8") as stream:
				writer = csv.writer(stream)
				writer.writerow(["text", "braille", "type"])
				writer.writerow(["Alpha", "\u2801", "General"])
				writer.writerow(["", "\u2803", "General"])
			target = _make_dialog(temp_dir, ["alpha"])

			target.refresh_dictionaries(["alpha"], "alpha")

		self.assertEqual(target.list_ctrl.item_count, 1)
		self.assertEqual(target.list_ctrl.refresh_count, 1)
		self.assertEqual(target._get_item_text(0, 0), "alpha")
		self.assertEqual(target._get_item_text(0, 1), "1")
		self.assertEqual(target.list_ctrl.selected, 0)

	def test_missing_dictionary_has_zero_entries(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			target = _make_dialog(temp_dir, ["missing"])

			target.refresh_dictionaries(["missing"], "missing")

		self.assertEqual(target._get_item_text(0, 1), "0")

	def test_disk_refresh_discovers_new_dictionary_files(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "new.csv"
			path.write_text("text,braille,type\n", encoding="utf-8")
			target = _make_dialog(temp_dir, ["old"])

			target._refresh_from_disk("new")

		self.assertEqual(target._dictionary_names, ["new"])
		self.assertEqual(target.list_ctrl.selected, 0)

	def test_unknown_column_is_rejected(self):
		target = _make_dialog(".", ["alpha"])
		target._dictionary_counts = {"alpha": 1}

		with self.assertRaisesRegex(ValueError, "Unknown column"):
			target._get_item_text(0, 2)


class DictionaryManagementInteractionTest(unittest.TestCase):
	def test_refresh_restores_preferred_selection(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			target = _make_dialog(temp_dir, ["alpha", "beta"])

			target.refresh_dictionaries(["alpha", "beta"], "beta")

		self.assertEqual(target.list_ctrl.selected, 1)
		self.assertEqual(target.list_ctrl.focused, 1)

	def test_column_widths_fill_available_client_width(self):
		target = _make_dialog(".", ["alpha"])
		target.list_ctrl.width = 600

		target._resize_columns()

		self.assertEqual(sum(target.list_ctrl.column_widths.values()), 600)
		self.assertGreater(target.list_ctrl.column_widths[0], target.list_ctrl.column_widths[1])

	def test_resize_event_recalculates_columns_and_continues_propagation(self):
		target = _make_dialog(".", ["alpha"])
		target._resize_columns = Mock()
		event = Mock()

		target._on_list_size(event)

		target._resize_columns.assert_called_once_with()
		event.Skip.assert_called_once_with()

	def test_only_explicit_edit_handler_sets_edit_result(self):
		target = _make_dialog(".", ["alpha"])
		target.list_ctrl.selected = 0

		target._on_edit(None)

		self.assertEqual(target.edit_dictionary_name, "alpha")
		target.EndModal.assert_called_once_with(dialog.wx.ID_EDIT)


if __name__ == "__main__":
	unittest.main()
