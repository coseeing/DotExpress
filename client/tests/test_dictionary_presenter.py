import ast
import csv
import tempfile
import unittest
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock, patch

import dictionaries.presenter as presenter_module
from dictionaries.entries import load_dictionary_entries
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_dictionary_read_error
from i18n import _
from tests.unreadable_dictionary_files import BIG5, FIELD_LIMIT, LATE_BIG5


PRESENTER_PATH = Path(presenter_module.__file__)
HEADER = "text,braille,type\n"


class FakeView:
	"""Records every view call in order and answers from scripted values."""

	def __init__(self, *, names=(), confirm=True, import_path=None, export_path=None):
		self.calls = []
		self._names = list(names)
		self._confirm = confirm
		self._import_path = import_path
		self._export_path = export_path

	def prompt_dictionary_name(self, title, initial_name):
		self.calls.append(("prompt", title, initial_name))
		return self._names.pop(0)

	def show_info(self, message):
		self.calls.append(("info", message))

	def show_error(self, message):
		self.calls.append(("error", message))

	def confirm(self, message, caption):
		self.calls.append(("confirm", message, caption))
		return self._confirm

	def choose_import_path(self, title):
		self.calls.append(("choose_import", title))
		return self._import_path

	def choose_export_path(self, title, default_file):
		self.calls.append(("choose_export", title, default_file))
		return self._export_path


class PresenterTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)
		self.dictionary_dir = self.root / "dictionaries"
		self.active = ["default"]
		self.set_active_name = Mock(side_effect=lambda name: self.active.__setitem__(0, name))

	def write_dictionary(self, name, content=HEADER):
		self.dictionary_dir.mkdir(parents=True, exist_ok=True)
		path = self.dictionary_dir / f"{name}.csv"
		path.write_text(content, encoding="utf-8")
		return path

	def make_presenter(self, *names, active="default"):
		for name in names:
			self.write_dictionary(name)
		self.active[0] = active
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: self.active[0],
			set_active_name=self.set_active_name,
		)
		presenter.refresh(active)
		return presenter

	def files(self):
		return sorted(path.stem for path in self.dictionary_dir.glob("*.csv"))


class PresenterModuleTest(unittest.TestCase):
	def test_presenter_module_does_not_import_wx(self):
		tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name.split(".")[0] for alias in node.names)
			elif isinstance(node, ast.ImportFrom) and node.module:
				imported.add(node.module.split(".")[0])

		self.assertNotIn("wx", imported)

	def test_view_and_actions_are_protocols(self):
		for name in ("DictionaryManagementView", "DictionaryManagementActions"):
			with self.subTest(name=name):
				self.assertIn(Protocol, getattr(presenter_module, name).__bases__)

	def test_presenter_provides_every_action(self):
		for name in (
			"dictionary_names",
			"dictionary_path",
			"add",
			"delete",
			"rename",
			"import_from_file",
			"export_to_file",
		):
			with self.subTest(name=name):
				self.assertTrue(hasattr(presenter_module.DictionaryManagementActions, name))
				self.assertTrue(hasattr(DictionaryManagementPresenter, name))


class PresenterRefreshTest(PresenterTestCase):
	def test_constructor_does_no_io(self):
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: "default",
			set_active_name=self.set_active_name,
		)

		self.assertFalse(self.dictionary_dir.exists())
		self.assertEqual(presenter.dictionary_names, [])
		self.assertEqual(presenter.dictionary_dir, self.dictionary_dir)

	def test_refresh_creates_default_dictionary_and_selects_it(self):
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: "default",
			set_active_name=self.set_active_name,
		)

		selected = presenter.refresh()

		self.assertEqual(selected, "default")
		self.assertEqual(presenter.dictionary_names, ["default"])
		self.assertEqual((self.dictionary_dir / "default.csv").read_text(encoding="utf-8").splitlines(), ["text,braille,type"])

	def test_refresh_lists_names_case_insensitively_and_keeps_preferred_name(self):
		presenter = self.make_presenter("beta", "Alpha")

		selected = presenter.refresh("beta")

		self.assertEqual(selected, "beta")
		self.assertEqual(presenter.dictionary_names, ["Alpha", "beta", "default"])

	def test_refresh_falls_back_to_default_for_unknown_name(self):
		presenter = self.make_presenter("alpha")

		self.assertEqual(presenter.refresh("missing"), "default")
		self.assertEqual(presenter.refresh(None), "default")

	def test_refresh_picks_up_files_added_on_disk(self):
		presenter = self.make_presenter()
		self.write_dictionary("later")

		self.assertEqual(presenter.dictionary_names, ["default"])
		presenter.refresh()
		self.assertEqual(presenter.dictionary_names, ["default", "later"])

	def test_dictionary_names_returns_a_copy(self):
		presenter = self.make_presenter("alpha")

		names = presenter.dictionary_names
		names.append("intruder")

		self.assertIsNot(presenter.dictionary_names, presenter.dictionary_names)
		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])

	def test_dictionary_path_uses_dictionary_directory(self):
		presenter = self.make_presenter()

		self.assertEqual(presenter.dictionary_path("alpha"), self.dictionary_dir / "alpha.csv")
		self.set_active_name.assert_not_called()


class PresenterAddTest(PresenterTestCase):
	def test_add_creates_dictionary_and_selects_it(self):
		presenter = self.make_presenter()
		view = FakeView(names=["alpha"])

		result = presenter.add(view)

		self.assertEqual(result, "alpha")
		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
		self.assertEqual(self.files(), ["alpha", "default"])
		self.assertEqual((self.dictionary_dir / "alpha.csv").read_text(encoding="utf-8").splitlines(), ["text,braille,type"])
		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])
		self.set_active_name.assert_not_called()

	def test_add_cancel_creates_nothing(self):
		presenter = self.make_presenter()
		view = FakeView(names=[None])

		result = presenter.add(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
		self.assertEqual(self.files(), ["default"])
		self.assertEqual(presenter.dictionary_names, ["default"])

	def test_add_duplicate_shows_error_and_prompts_again_with_typed_name(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(names=[" alpha", "beta"])

		result = presenter.add(view)

		self.assertEqual(result, "beta")
		self.assertEqual(
			view.calls,
			[
				("prompt", _("Add Dictionary"), ""),
				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
				("prompt", _("Add Dictionary"), " alpha"),
			],
		)
		self.assertEqual(self.files(), ["alpha", "beta", "default"])
		self.assertEqual(presenter.dictionary_names, ["alpha", "beta", "default"])

	def test_add_invalid_name_shows_untranslated_info(self):
		presenter = self.make_presenter()
		view = FakeView(names=["Default"])

		result = presenter.add(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[("prompt", _("Add Dictionary"), ""), ("info", "Name 'Default' is reserved.")],
		)
		self.assertEqual(self.files(), ["default"])

	def test_add_does_not_catch_os_error(self):
		presenter = self.make_presenter()
		view = FakeView(names=["alpha"])

		with patch.object(presenter_module, "create_dictionary", side_effect=PermissionError("denied")):
			with self.assertRaises(PermissionError):
				presenter.add(view)

		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
		self.assertEqual(presenter.dictionary_names, ["default"])

	def test_add_never_changes_active_dictionary(self):
		presenter = self.make_presenter(active="missing")
		view = FakeView(names=["alpha"])

		result = presenter.add(view)

		self.assertEqual(result, "alpha")
		self.assertEqual(self.active, ["missing"])
		self.set_active_name.assert_not_called()


class PresenterDeleteTest(PresenterTestCase):
	def confirm_call(self, name):
		return (
			"confirm",
			_('Do you want to delete dictionary "{name}"?').format(name=name),
			_("Confirm Delete Dictionary"),
		)

	def test_delete_default_shows_info_without_confirmation(self):
		presenter = self.make_presenter("alpha")
		view = FakeView()

		result = presenter.delete(view, "default")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [("info", _("The default dictionary cannot be deleted."))])
		self.assertEqual(self.files(), ["alpha", "default"])

	def test_delete_declined_keeps_file(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(confirm=False)

		result = presenter.delete(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.confirm_call("alpha")])
		self.assertEqual(self.files(), ["alpha", "default"])
		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])

	def test_delete_inactive_dictionary_keeps_active_name(self):
		presenter = self.make_presenter("alpha", "beta", active="beta")
		view = FakeView()

		result = presenter.delete(view, "alpha")

		self.assertEqual(result, "default")
		self.assertEqual(view.calls, [self.confirm_call("alpha")])
		self.assertEqual(self.files(), ["beta", "default"])
		self.assertEqual(presenter.dictionary_names, ["beta", "default"])
		self.assertEqual(self.active, ["beta"])
		self.set_active_name.assert_not_called()

	def test_delete_active_dictionary_activates_planned_fallback(self):
		presenter = self.make_presenter("alpha", "beta", active="beta")
		view = FakeView()

		result = presenter.delete(view, "beta")

		self.assertEqual(result, "default")
		self.assertEqual(view.calls, [self.confirm_call("beta")])
		self.assertEqual(self.files(), ["alpha", "default"])
		self.set_active_name.assert_called_once_with("alpha")
		self.assertEqual(self.active, ["alpha"])

	def test_delete_os_error_shows_error_and_changes_nothing(self):
		presenter = self.make_presenter("alpha", active="alpha")
		view = FakeView()

		with patch.object(presenter_module, "delete_dictionary", side_effect=PermissionError("denied")):
			result = presenter.delete(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.confirm_call("alpha"),
				("error", _("Failed to delete dictionary: {error}").format(error="denied")),
			],
		)
		self.assertEqual(self.files(), ["alpha", "default"])
		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])
		self.set_active_name.assert_not_called()

	def test_delete_does_not_catch_value_error_for_padded_default_name(self):
		presenter = self.make_presenter(" default")
		view = FakeView()

		with self.assertRaises(ValueError):
			presenter.delete(view, " default")

		self.assertEqual(view.calls, [self.confirm_call(" default")])
		self.assertEqual(self.files(), [" default", "default"])
		self.set_active_name.assert_not_called()


class PresenterRenameTest(PresenterTestCase):
	def prompt_call(self, initial_name):
		return ("prompt", _("Rename Dictionary"), initial_name)

	def test_rename_default_does_nothing(self):
		presenter = self.make_presenter()
		view = FakeView()

		result = presenter.rename(view, "default")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [])
		self.assertEqual(self.files(), ["default"])

	def test_rename_cancel_keeps_file(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(names=[None])

		result = presenter.rename(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["alpha", "default"])

	def test_rename_inactive_dictionary_keeps_active_name(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(names=["gamma"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "gamma")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["default", "gamma"])
		self.assertEqual(presenter.dictionary_names, ["default", "gamma"])
		self.set_active_name.assert_not_called()

	def test_rename_active_dictionary_activates_new_name(self):
		presenter = self.make_presenter("alpha", active="alpha")
		view = FakeView(names=["gamma"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "gamma")
		self.assertEqual(self.files(), ["default", "gamma"])
		self.set_active_name.assert_called_once_with("gamma")
		self.assertEqual(self.active, ["gamma"])

	def test_rename_to_same_name_changes_nothing(self):
		presenter = self.make_presenter("alpha", active="alpha")
		view = FakeView(names=["alpha"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "alpha")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["alpha", "default"])
		self.set_active_name.assert_not_called()

	def test_rename_case_only_change_renames_file(self):
		presenter = self.make_presenter("alpha")
		if (self.dictionary_dir / "ALPHA.csv").exists():
			self.skipTest("case-insensitive file system: a case-only rename is reported as a duplicate")
		view = FakeView(names=["Alpha"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "Alpha")
		self.assertEqual(view.calls, [self.prompt_call("alpha")])
		self.assertEqual(self.files(), ["Alpha", "default"])

	def test_rename_duplicate_shows_error_and_prompts_again_with_typed_name(self):
		presenter = self.make_presenter("alpha", "beta")
		view = FakeView(names=["beta", "gamma"])

		result = presenter.rename(view, "alpha")

		self.assertEqual(result, "gamma")
		self.assertEqual(
			view.calls,
			[
				self.prompt_call("alpha"),
				("error", _('Dictionary "{name}" already exists.').format(name="beta")),
				self.prompt_call("beta"),
			],
		)
		self.assertEqual(self.files(), ["beta", "default", "gamma"])

	def test_rename_invalid_name_shows_untranslated_info(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(names=["bad|name"])

		result = presenter.rename(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.prompt_call("alpha"), ("info", "Name contains invalid characters.")])
		self.assertEqual(self.files(), ["alpha", "default"])

	def test_rename_os_error_shows_save_error(self):
		presenter = self.make_presenter("alpha", active="alpha")
		view = FakeView(names=["gamma"])

		with patch.object(presenter_module, "rename_dictionary_after_name_prompt", side_effect=PermissionError("denied")):
			result = presenter.rename(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.prompt_call("alpha"),
				("error", _("Failed to save dictionary: {error}").format(error="denied")),
			],
		)
		self.assertEqual(self.files(), ["alpha", "default"])
		self.set_active_name.assert_not_called()


class PresenterImportTest(PresenterTestCase):
	HEADER_ERROR = "Imported file must contain text, braille, and type headers."

	def write_source(self, name, content=HEADER + "Alpha,\u2801,General\n"):
		source_dir = self.root / "source"
		source_dir.mkdir(exist_ok=True)
		path = source_dir / f"{name}.csv"
		path.write_text(content, encoding="utf-8")
		return path

	def write_source_bytes(self, name, data):
		source_dir = self.root / "source"
		source_dir.mkdir(exist_ok=True)
		path = source_dir / f"{name}.csv"
		path.write_bytes(data)
		return path

	def read_error_call(self, source):
		"""The error box for a source that cannot be read as a dictionary (F-6 D9)."""
		with self.assertRaises((UnicodeDecodeError, csv.Error)) as caught:
			load_dictionary_entries(source)
		reason = describe_dictionary_read_error(caught.exception)
		return ("error", _("Failed to import dictionary: {error}").format(error=reason))

	def choose_call(self):
		return ("choose_import", _("Import Dictionary"))

	def prompt_call(self, initial_name):
		return ("prompt", _("Add Dictionary"), initial_name)

	def test_import_cancelled_file_dialog_does_not_prompt(self):
		presenter = self.make_presenter()
		view = FakeView(import_path=None)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call()])
		self.assertEqual(self.files(), ["default"])

	def test_import_copies_source_under_prompted_name(self):
		source = self.write_source("words")
		presenter = self.make_presenter(active="missing")
		view = FakeView(names=["words"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertEqual(result, "words")
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("words")])
		self.assertEqual(self.files(), ["default", "words"])
		self.assertEqual((self.dictionary_dir / "words.csv").read_bytes(), source.read_bytes())
		self.assertEqual(presenter.dictionary_names, ["default", "words"])
		self.assertEqual(self.active, ["missing"])
		self.set_active_name.assert_not_called()

	def test_import_duplicate_shows_error_and_prompts_again_with_typed_name(self):
		source = self.write_source("alpha")
		presenter = self.make_presenter("alpha")
		view = FakeView(names=["alpha", "beta"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertEqual(result, "beta")
		self.assertEqual(
			view.calls,
			[
				self.choose_call(),
				self.prompt_call("alpha"),
				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
				self.prompt_call("alpha"),
			],
		)
		self.assertEqual(self.files(), ["alpha", "beta", "default"])

	def test_import_reports_duplicate_name_before_checking_headers(self):
		source = self.write_source("alpha", content="a,b\n")
		presenter = self.make_presenter("alpha")
		view = FakeView(names=["alpha", None], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.choose_call(),
				self.prompt_call("alpha"),
				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
				self.prompt_call("alpha"),
			],
		)
		self.assertEqual(self.files(), ["alpha", "default"])

	def test_import_without_headers_shows_header_error(self):
		source = self.write_source("bad", content="a,b\n")
		presenter = self.make_presenter()
		view = FakeView(names=["bad"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[self.choose_call(), self.prompt_call("bad"), ("error", _(self.HEADER_ERROR))],
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_invalid_name_shows_header_error(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
		view = FakeView(names=["bad|name"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[self.choose_call(), self.prompt_call("words"), ("error", _(self.HEADER_ERROR))],
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_missing_source_shows_import_error(self):
		source = self.root / "source" / "gone.csv"
		with self.assertRaises(FileNotFoundError) as missing:
			source.open("r", newline="", encoding="utf-8")
		presenter = self.make_presenter()
		view = FakeView(names=["gone"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.choose_call(),
				self.prompt_call("gone"),
				("error", _("Failed to import dictionary: {error}").format(error=missing.exception)),
			],
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_big5_shows_the_not_utf8_reason(self):
		# Before F-6 this showed the header message, which named the wrong problem.
		source = self.write_source_bytes("big5", BIG5)
		presenter = self.make_presenter()
		view = FakeView(names=["big5"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("big5"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_late_big5_is_refused(self):
		# Before F-6 the header check passed and the file was copied; Dictionary Management
		# then could not count it.
		source = self.write_source_bytes("late", LATE_BIG5)
		presenter = self.make_presenter()
		view = FakeView(names=["late"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("late"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_invalid_csv_shows_the_reason(self):
		source = self.write_source_bytes("long", FIELD_LIMIT)
		presenter = self.make_presenter()
		view = FakeView(names=["long"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("long"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_cancelled_name_prompt_imports_nothing(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
		view = FakeView(names=[None], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("words")])
		self.assertEqual(self.files(), ["default"])


class PresenterExportTest(PresenterTestCase):
	def choose_call(self, default_file):
		return ("choose_export", _("Export Dictionary"), default_file)

	def test_export_with_empty_list_does_nothing(self):
		self.write_dictionary("alpha")
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: "default",
			set_active_name=self.set_active_name,
		)
		view = FakeView(export_path=self.root / "copy.csv")

		result = presenter.export_to_file(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [])
		self.assertFalse((self.root / "copy.csv").exists())

	def test_export_cancelled_writes_nothing(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(export_path=None)

		result = presenter.export_to_file(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call("alpha.csv")])
		self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["dictionaries"])

	def test_export_copies_dictionary_to_chosen_path(self):
		presenter = self.make_presenter()
		source = self.write_dictionary("alpha", HEADER + "Alpha,\u2801,General\n")
		destination = self.root / "copy.csv"
		view = FakeView(export_path=destination)

		result = presenter.export_to_file(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call("alpha.csv")])
		self.assertEqual(destination.read_bytes(), source.read_bytes())
		self.assertEqual(presenter.dictionary_names, ["default"])

	def test_export_os_error_shows_error(self):
		presenter = self.make_presenter("alpha")
		view = FakeView(export_path=self.root / "copy.csv")

		with patch.object(presenter_module, "export_dictionary", side_effect=PermissionError("denied")):
			result = presenter.export_to_file(view, "alpha")

		self.assertIsNone(result)
		self.assertEqual(
			view.calls,
			[
				self.choose_call("alpha.csv"),
				("error", _("Failed to export dictionary: {error}").format(error="denied")),
			],
		)


if __name__ == "__main__":
	unittest.main()
