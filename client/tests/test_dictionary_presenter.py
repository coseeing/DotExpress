import ast
import tempfile
import unittest
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock, patch

from dictionaries import presenter as presenter_module
from dictionaries.presenter import DictionaryManagementPresenter
from i18n import _


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


if __name__ == "__main__":
	unittest.main()
