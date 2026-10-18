"""Script Management without wx (F-18): ``text_scripts.presenter.ScriptManagementPresenter``."""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import text_scripts.presenter as presenter_module
from text_scripts.presenter import ScriptManagementPresenter

PRESENTER_PATH = Path(presenter_module.__file__)
UPPER = "def main(text: str) -> str:\n    return text.upper()\n"


class PresenterTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)
		self.script_dir = self.root / "script"
		self.active = ["no-processing"]
		self.set_active_name = Mock(side_effect=lambda name: self.active.__setitem__(0, name))

	def write_script(self, name, source=UPPER):
		self.script_dir.mkdir(parents=True, exist_ok=True)
		path = self.script_dir / f"{name}.py"
		path.write_text(source, encoding="utf-8")
		return path

	def make_presenter(self, *names, active="no-processing"):
		for name in names:
			self.write_script(name)
		self.active[0] = active
		presenter = ScriptManagementPresenter(
			self.script_dir,
			get_active_name=lambda: self.active[0],
			set_active_name=self.set_active_name,
		)
		presenter.refresh(active)
		return presenter

	def files(self):
		return sorted(path.name for path in self.script_dir.iterdir())


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


class PresenterRefreshTest(PresenterTestCase):
	def test_constructor_does_no_io(self):
		ScriptManagementPresenter(self.script_dir, get_active_name=lambda: "no-processing", set_active_name=Mock())

		self.assertFalse(self.script_dir.exists())

	def test_refresh_creates_no_processing_and_lists_it_first(self):
		self.write_script("zeta")
		self.write_script("Alpha")
		presenter = ScriptManagementPresenter(self.script_dir, get_active_name=lambda: "no-processing", set_active_name=Mock())

		selected = presenter.refresh()

		self.assertEqual(selected, "no-processing")
		self.assertEqual(presenter.script_names, ["no-processing", "Alpha", "zeta"])
		self.assertEqual(self.files(), ["Alpha.py", "no-processing.py", "zeta.py"])
		self.assertEqual(presenter.script_dir, self.script_dir)

	def test_refresh_selects_the_preferred_name_if_listed(self):
		presenter = self.make_presenter("upper")

		self.assertEqual(presenter.refresh("upper"), "upper")
		self.assertEqual(presenter.refresh("gone"), "no-processing")

	def test_the_names_are_a_copy_and_a_name_maps_to_its_file(self):
		presenter = self.make_presenter("upper")

		presenter.script_names.append("other")

		self.assertEqual(presenter.script_names, ["no-processing", "upper"])
		self.assertEqual(presenter.script_path("upper"), self.script_dir / "upper.py")
		self.set_active_name.assert_not_called()


if __name__ == "__main__":
	unittest.main()
