import csv
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from dictionaries.presenter import DictionaryManagementView
from tests import wx_stub


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate


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


class _FakeActions:
	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""

	def __init__(self, dictionary_dir, names, results=None):
		self.dictionary_dir = Path(dictionary_dir)
		self.dictionary_names = list(names)
		self.results = dict(results or {})
		self.calls = []

	def dictionary_path(self, name):
		return self.dictionary_dir / f"{name}.csv"

	def add(self, view):
		self.calls.append(("add", view))
		return self.results.get("add")

	def delete(self, view, name):
		self.calls.append(("delete", view, name))
		return self.results.get("delete")

	def rename(self, view, name):
		self.calls.append(("rename", view, name))
		return self.results.get("rename")

	def import_from_file(self, view):
		self.calls.append(("import", view))
		return self.results.get("import")

	def export_to_file(self, view, name):
		self.calls.append(("export", view, name))
		return self.results.get("export")


def _make_dialog(dictionary_dir, names, actions=None):
	target = object.__new__(DictionaryManagementDialog)
	target._actions = actions if actions is not None else _FakeActions(dictionary_dir, names)
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

	def test_refresh_after_action_takes_names_from_actions_not_disk(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "new.csv"
			path.write_text("text,braille,type\n", encoding="utf-8")
			actions = _FakeActions(temp_dir, ["listed"], results={"add": "listed"})
			target = _make_dialog(temp_dir, ["old"], actions)

			target._on_add_clicked(None)

		self.assertEqual(target._dictionary_names, ["listed"])
		self.assertEqual(target._dictionary_counts, {"listed": 0})
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


class DictionaryManagementActionsWiringTest(unittest.TestCase):
	def test_constructor_takes_actions_and_selected_name(self):
		parameters = list(inspect.signature(DictionaryManagementDialog.__init__).parameters)

		self.assertEqual(parameters, ["self", "parent", "actions", "selected_name"])
		self.assertFalse(hasattr(dialog, "list_dictionary_names"))

	def test_constructor_lists_names_from_actions(self):
		actions = _FakeActions(".", ["alpha", "beta"])
		with (
			patch.object(dialog.wx.Dialog, "__init__", lambda self, *args, **kwargs: None),
			patch.object(DictionaryManagementDialog, "_build_ui"),
			patch.object(DictionaryManagementDialog, "refresh_dictionaries") as refresh,
		):
			target = DictionaryManagementDialog(None, actions, "beta")

		self.assertIs(target._actions, actions)
		self.assertIsNone(target.edit_dictionary_name)
		self.assertFalse(hasattr(target, "dictionary_dir"))
		refresh.assert_called_once_with(["alpha", "beta"], "beta")

	def test_add_and_import_pass_dialog_and_refresh_with_result(self):
		for action, handler in (("add", "_on_add_clicked"), ("import", "_on_import_clicked")):
			with self.subTest(action=action):
				actions = _FakeActions(".", ["alpha", "beta"], results={action: "beta"})
				target = _make_dialog(".", ["alpha"], actions)

				getattr(target, handler)(None)

				self.assertEqual(actions.calls, [(action, target)])
				self.assertEqual(target._dictionary_names, ["alpha", "beta"])
				self.assertEqual(target.list_ctrl.selected, 1)
				self.assertEqual(target.list_ctrl.focused, 1)

	def test_delete_and_rename_pass_selection_and_refresh_with_result(self):
		for action, handler in (("delete", "_on_delete_clicked"), ("rename", "_on_rename_clicked")):
			with self.subTest(action=action):
				actions = _FakeActions(".", ["default", "gamma"], results={action: "gamma"})
				target = _make_dialog(".", ["alpha", "default"], actions)
				target.list_ctrl.selected = 0

				getattr(target, handler)(None)

				self.assertEqual(actions.calls, [(action, target, "alpha")])
				self.assertEqual(target._dictionary_names, ["default", "gamma"])
				self.assertEqual(target.list_ctrl.selected, 1)

	def test_none_result_leaves_list_untouched(self):
		for action, handler in (
			("add", "_on_add_clicked"),
			("delete", "_on_delete_clicked"),
			("rename", "_on_rename_clicked"),
			("import", "_on_import_clicked"),
		):
			with self.subTest(action=action):
				actions = _FakeActions(".", ["other"])
				target = _make_dialog(".", ["alpha"], actions)
				target.list_ctrl.selected = 0

				getattr(target, handler)(None)

				self.assertEqual(len(actions.calls), 1)
				self.assertEqual(target._dictionary_names, ["alpha"])
				self.assertEqual(target.list_ctrl.refresh_count, 0)

	def test_selection_actions_do_nothing_without_selection(self):
		for handler in ("_on_delete_clicked", "_on_rename_clicked", "_on_export_clicked"):
			with self.subTest(handler=handler):
				actions = _FakeActions(".", ["alpha"], results={"delete": "alpha", "rename": "alpha"})
				target = _make_dialog(".", ["alpha"], actions)
				target.list_ctrl.selected = dialog.wx.NOT_FOUND

				getattr(target, handler)(None)

				self.assertEqual(actions.calls, [])

	def test_export_passes_selection_and_never_refreshes(self):
		actions = _FakeActions(".", ["other"], results={"export": "other"})
		target = _make_dialog(".", ["alpha"], actions)
		target.list_ctrl.selected = 0

		target._on_export_clicked(None)

		self.assertEqual(actions.calls, [("export", target, "alpha")])
		self.assertEqual(target._dictionary_names, ["alpha"])
		self.assertEqual(target.list_ctrl.refresh_count, 0)

	def test_counts_are_read_through_actions_dictionary_path(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			listed = Path(temp_dir) / "listed"
			listed.mkdir()
			(listed / "alpha.csv").write_text("text,braille,type\nAlpha,\u2801,General\n", encoding="utf-8")
			target = _make_dialog(temp_dir, ["alpha"], _FakeActions(listed, ["alpha"]))

			target.refresh_dictionaries(["alpha"], "alpha")

		self.assertEqual(target._get_item_text(0, 1), "1")


class DictionaryManagementViewTest(unittest.TestCase):
	def setUp(self):
		self.target = _make_dialog(".", ["alpha"])
		self.wx = dialog.wx

	def _name_dialog(self, result, name="typed"):
		name_dialog = MagicMock()
		name_dialog.__enter__.return_value = name_dialog
		name_dialog.ShowModal.return_value = result
		name_dialog.get_dictionary_name.return_value = name
		return name_dialog

	def _file_dialog_class(self, result, path="/data/words.csv"):
		file_dialog = MagicMock()
		file_dialog.ShowModal.return_value = result
		file_dialog.GetPath.return_value = path
		file_dialog_class = MagicMock()
		file_dialog_class.return_value.__enter__.return_value = file_dialog
		return file_dialog_class, file_dialog

	def test_prompt_dictionary_name_returns_entered_name(self):
		name_dialog = self._name_dialog(self.wx.ID_OK, "beta")

		with patch.object(dialog, "DictionaryNameDialog", return_value=name_dialog) as name_dialog_class:
			result = self.target.prompt_dictionary_name("Title", "alpha")

		self.assertEqual(result, "beta")
		name_dialog_class.assert_called_once_with(self.target, initial_name="alpha")
		name_dialog.SetTitle.assert_called_once_with("Title")
		name_dialog.ShowModal.assert_called_once_with()
		name_dialog.__exit__.assert_called_once()

	def test_prompt_dictionary_name_cancel_returns_none(self):
		name_dialog = self._name_dialog(self.wx.ID_CANCEL)

		with patch.object(dialog, "DictionaryNameDialog", return_value=name_dialog):
			result = self.target.prompt_dictionary_name("Title", "")

		self.assertIsNone(result)
		name_dialog.get_dictionary_name.assert_not_called()
		name_dialog.__exit__.assert_called_once()

	def test_show_info_uses_information_box_on_dialog(self):
		with patch.object(self.wx, "MessageBox") as message_box:
			self.target.show_info("message")

		message_box.assert_called_once_with(
			"message",
			dialog._("Info"),
			self.wx.OK | self.wx.ICON_INFORMATION,
			parent=self.target,
		)

	def test_show_error_uses_error_box_on_dialog(self):
		with patch.object(self.wx, "MessageBox") as message_box:
			self.target.show_error("message")

		message_box.assert_called_once_with(
			"message",
			dialog._("Error"),
			self.wx.OK | self.wx.ICON_ERROR,
			parent=self.target,
		)

	def test_confirm_uses_warning_yes_no_box_with_no_default(self):
		for answer, expected in ((self.wx.YES, True), (self.wx.NO, False)):
			with self.subTest(answer=answer):
				with patch.object(self.wx, "MessageBox", return_value=answer) as message_box:
					result = self.target.confirm("message", "caption")

				self.assertIs(result, expected)
				message_box.assert_called_once_with(
					"message",
					"caption",
					self.wx.YES_NO | self.wx.NO_DEFAULT | self.wx.ICON_WARNING,
					parent=self.target,
				)

	def test_choose_import_path_opens_csv_file_dialog(self):
		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_OK)

		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
			result = self.target.choose_import_path("Import")

		self.assertEqual(result, Path("/data/words.csv"))
		file_dialog_class.assert_called_once_with(
			self.target,
			"Import",
			wildcard=dialog._("CSV files (*.csv)|*.csv"),
			style=self.wx.FD_OPEN,
		)
		file_dialog_class.return_value.__exit__.assert_called_once()

	def test_choose_import_path_cancel_returns_none(self):
		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_CANCEL)

		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
			result = self.target.choose_import_path("Import")

		self.assertIsNone(result)
		file_dialog.GetPath.assert_not_called()

	def test_choose_export_path_opens_save_dialog_with_default_file(self):
		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_OK, "/data/out.csv")

		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
			result = self.target.choose_export_path("Export", "alpha.csv")

		self.assertEqual(result, Path("/data/out.csv"))
		file_dialog_class.assert_called_once_with(
			self.target,
			"Export",
			defaultFile="alpha.csv",
			wildcard=dialog._("CSV files (*.csv)|*.csv"),
			style=self.wx.FD_SAVE | self.wx.FD_OVERWRITE_PROMPT,
		)
		file_dialog_class.return_value.__exit__.assert_called_once()

	def test_choose_export_path_cancel_returns_none(self):
		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_CANCEL)

		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
			result = self.target.choose_export_path("Export", "alpha.csv")

		self.assertIsNone(result)
		file_dialog.GetPath.assert_not_called()

	def test_dialog_provides_every_view_method(self):
		for name in (
			"prompt_dictionary_name",
			"show_info",
			"show_error",
			"confirm",
			"choose_import_path",
			"choose_export_path",
		):
			with self.subTest(name=name):
				self.assertTrue(hasattr(DictionaryManagementView, name))
				self.assertTrue(callable(vars(DictionaryManagementDialog).get(name)), name)


if __name__ == "__main__":
	unittest.main()
