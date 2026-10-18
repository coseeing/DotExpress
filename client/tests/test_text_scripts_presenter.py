"""Script Management without wx (F-18): ``text_scripts.presenter.ScriptManagementPresenter``."""

import ast
import os
import tempfile
import unittest
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock, patch

import text_scripts.presenter as presenter_module
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT
from tests.file_log_isolation import isolate_file_logs
from text_scripts.presenter import ScriptManagementPresenter

PRESENTER_PATH = Path(presenter_module.__file__)
UPPER = "def main(text: str) -> str:\n    return text.upper()\n"


def setUpModule():
	# An Edit of a script that cannot be read logs to dotexpress.gui (gui.log).
	unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


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
		path.write_bytes(source.encode("utf-8"))
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

	def test_view_and_actions_are_protocols(self):
		for name in ("ScriptManagementView", "ScriptManagementActions"):
			with self.subTest(name=name):
				self.assertIn(Protocol, getattr(presenter_module, name).__bases__)

	def test_presenter_provides_every_action(self):
		for name in ("script_names", "script_path", "add", "edit", "delete", "rename", "import_from_file", "export_to_file"):
			with self.subTest(name=name):
				self.assertTrue(hasattr(presenter_module.ScriptManagementActions, name))
				self.assertTrue(hasattr(ScriptManagementPresenter, name))


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


class FakeView:
	"""Records every view call in order and answers from scripted values.

	``edits`` holds one entry per editor: the texts saved in turn (a failed save is recorded
	with its error), or a function that gets ``save``.
	"""

	def __init__(self, *, names=(), confirm=True, import_path=None, export_path=None, edits=()):
		self.calls = []
		self._names = list(names)
		self._confirm = confirm
		self._import_path = import_path
		self._export_path = export_path
		self._edits = list(edits)

	def prompt_script_name(self, title, initial_name):
		self.calls.append(("prompt", title, initial_name))
		return self._names.pop(0)

	def edit_script(self, title, source, save):
		self.calls.append(("edit", title, source))
		edit = self._edits.pop(0)
		if callable(edit):
			edit(save)
			return
		for text in edit:
			try:
				save(text)
			except (OSError, SyntaxError, ValueError) as error:
				self.calls.append(("save failed", type(error).__name__, str(error)))
			else:
				self.calls.append(("saved", text))

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


SHOUT = "def main(text):\n    return text.upper() + '!'\n"
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")
NOT_UTF8_REASON = "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"


class PresenterAddTest(PresenterTestCase):
	def test_add_asks_a_name_then_opens_the_template_and_writes_nothing_without_a_save(self):
		# F-18 (D8.1): Cancel in the editor creates nothing.
		presenter = self.make_presenter()
		view = FakeView(names=["upper"], edits=[[]])

		self.assertIsNone(presenter.add(view))

		self.assertEqual(view.calls, [("prompt", "新增腳本", ""), ("edit", "upper", NO_PROCESSING_SCRIPT)])
		self.assertEqual(self.files(), ["no-processing.py"])
		self.assertEqual(presenter.script_names, ["no-processing"])

	def test_the_first_save_creates_the_file_and_the_next_one_replaces_it(self):
		presenter = self.make_presenter()
		view = FakeView(names=[" upper"], edits=[[UPPER, SHOUT]])

		self.assertEqual(presenter.add(view), "upper")

		self.assertEqual(view.calls[1:], [("edit", "upper", NO_PROCESSING_SCRIPT), ("saved", UPPER), ("saved", SHOUT)])
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), SHOUT)
		self.assertEqual(presenter.script_names, ["no-processing", "upper"])
		self.set_active_name.assert_not_called()

	def test_an_invalid_save_writes_nothing(self):
		presenter = self.make_presenter()
		view = FakeView(names=["upper"], edits=[["def main(a, b):\n    return a\n", UPPER]])

		presenter.add(view)

		self.assertEqual(
			view.calls[2],
			("save failed", "ValueError", "main must define exactly one positional parameter and no other parameters."),
		)
		self.assertEqual(view.calls[3], ("saved", UPPER))
		self.assertEqual(self.files(), ["no-processing.py", "upper.py"])

	def test_a_taken_name_asks_again(self):
		presenter = self.make_presenter("upper")
		view = FakeView(names=["Upper", "shout"], edits=[[]])

		presenter.add(view)

		self.assertEqual(
			view.calls,
			[
				("prompt", "新增腳本", ""),
				("error", "腳本「Upper」已存在。"),
				("prompt", "新增腳本", "Upper"),
				("edit", "shout", NO_PROCESSING_SCRIPT),
			],
		)

	def test_a_file_written_meanwhile_fails_the_first_save_and_is_kept(self):
		presenter = self.make_presenter()

		def edit(save):
			self.write_script("upper", "KEEP")
			with self.assertRaises(FileExistsError) as raised:
				save(UPPER)
			self.assertEqual(str(raised.exception), "腳本「upper」已存在。")

		self.assertIsNone(presenter.add(FakeView(names=["upper"], edits=[edit])))
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), "KEEP")

	def test_a_cancelled_name_opens_no_editor(self):
		presenter = self.make_presenter()
		view = FakeView(names=[None])

		self.assertIsNone(presenter.add(view))
		self.assertEqual(view.calls, [("prompt", "新增腳本", "")])


class PresenterEditTest(PresenterTestCase):
	def test_edit_opens_the_text_of_the_file_and_saves_it(self):
		presenter = self.make_presenter("upper", active="upper")
		(self.script_dir / "upper.py").write_bytes(b"\xef\xbb\xbf" + UPPER.encode("utf-8"))
		view = FakeView(edits=[[SHOUT]])

		self.assertEqual(presenter.edit(view, "upper"), "upper")

		self.assertEqual(view.calls, [("edit", "upper", UPPER), ("saved", SHOUT)])
		self.assertEqual((self.script_dir / "upper.py").read_bytes(), SHOUT.encode("utf-8"))
		self.set_active_name.assert_not_called()

	def test_an_invalid_script_opens_so_that_it_can_be_fixed(self):
		presenter = self.make_presenter()
		self.write_script("bad", "def main(:\n")
		presenter.refresh()
		view = FakeView(edits=[[]])

		presenter.edit(view, "bad")

		self.assertEqual(view.calls, [("edit", "bad", "def main(:\n")])

	def test_a_script_that_cannot_be_read_is_explained_and_not_opened(self):
		presenter = self.make_presenter()
		(self.script_dir / "cp950.py").write_bytes(NOT_UTF8)
		view = FakeView()

		with self.assertLogs("dotexpress.gui", "ERROR"):
			self.assertEqual(presenter.edit(view, "cp950"), "cp950")

		self.assertEqual(view.calls, [("error", f"無法讀取腳本「cp950」。\n\n{NOT_UTF8_REASON}")])

	def test_no_processing_is_not_edited(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.edit(view, "no-processing"))
		self.assertEqual(view.calls, [])


class PresenterDeleteTest(PresenterTestCase):
	def test_delete_asks_first_and_selects_the_script_above(self):
		presenter = self.make_presenter("alpha", "beta", "gamma")
		view = FakeView(confirm=True)

		self.assertEqual(presenter.delete(view, "beta"), "alpha")

		self.assertEqual(view.calls, [("confirm", "要刪除腳本「beta」嗎？", "確認刪除腳本")])
		self.assertEqual(self.files(), ["alpha.py", "gamma.py", "no-processing.py"])
		self.set_active_name.assert_not_called()

	def test_no_keeps_the_file(self):
		presenter = self.make_presenter("alpha")

		self.assertIsNone(presenter.delete(FakeView(confirm=False), "alpha"))
		self.assertEqual(self.files(), ["alpha.py", "no-processing.py"])

	def test_deleting_the_active_script_makes_no_processing_active(self):
		# F-18 (O5): not the neighbour, which would start running another script.
		presenter = self.make_presenter("alpha", "beta", active="beta")

		self.assertEqual(presenter.delete(FakeView(), "beta"), "alpha")

		self.set_active_name.assert_called_once_with("no-processing")
		self.assertEqual(self.active, ["no-processing"])

	def test_the_first_user_script_selects_no_processing_after_its_delete(self):
		presenter = self.make_presenter("alpha", active="alpha")

		self.assertEqual(presenter.delete(FakeView(), "alpha"), "no-processing")
		self.assertEqual(self.active, ["no-processing"])

	def test_a_failed_delete_is_reported(self):
		presenter = self.make_presenter("alpha", active="alpha")
		error = PermissionError(13, "Permission denied")

		with patch.object(presenter_module, "delete_script", side_effect=error):
			view = FakeView()
			self.assertIsNone(presenter.delete(view, "alpha"))

		self.assertEqual(view.calls[-1], ("error", "無法刪除腳本：[Errno 13] Permission denied"))
		self.set_active_name.assert_not_called()

	def test_no_processing_is_not_deleted(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.delete(view, "no-processing"))
		self.assertEqual(view.calls, [])


class PresenterRenameTest(PresenterTestCase):
	def test_renaming_the_active_script_makes_the_new_name_active(self):
		presenter = self.make_presenter("upper", active="upper")
		view = FakeView(names=["shout"])

		self.assertEqual(presenter.rename(view, "upper"), "shout")

		self.assertEqual(view.calls, [("prompt", "重新命名腳本", "upper")])
		self.assertEqual(self.files(), ["no-processing.py", "shout.py"])
		self.set_active_name.assert_called_once_with("shout")

	def test_renaming_another_script_keeps_the_active_one(self):
		presenter = self.make_presenter("upper", "alpha", active="alpha")

		self.assertEqual(presenter.rename(FakeView(names=["shout"]), "upper"), "shout")
		self.set_active_name.assert_not_called()

	def test_a_taken_name_asks_again_and_the_same_name_changes_nothing(self):
		presenter = self.make_presenter("upper", "shout", active="upper")
		view = FakeView(names=["shout", "upper"])

		self.assertEqual(presenter.rename(view, "upper"), "upper")

		self.assertEqual(view.calls[1], ("error", "腳本「shout」已存在。"))
		self.assertEqual(self.files(), ["no-processing.py", "shout.py", "upper.py"])
		self.set_active_name.assert_not_called()

	@unittest.skipUnless(os.name == "nt", "case-insensitive file names")
	def test_a_case_only_rename_follows_the_active_script(self):
		presenter = self.make_presenter("upper", active="upper")

		self.assertEqual(presenter.rename(FakeView(names=["Upper"]), "upper"), "Upper")
		self.assertEqual(self.active, ["Upper"])

	def test_a_failed_rename_is_reported(self):
		presenter = self.make_presenter("upper", active="upper")

		with patch.object(presenter_module, "rename_script", side_effect=PermissionError(13, "Permission denied")):
			view = FakeView(names=["shout"])
			self.assertIsNone(presenter.rename(view, "upper"))

		self.assertEqual(view.calls[-1], ("error", "儲存腳本失敗：[Errno 13] Permission denied"))
		self.set_active_name.assert_not_called()


class PresenterImportTest(PresenterTestCase):
	def source(self, name, data):
		folder = self.root / "source"
		folder.mkdir(exist_ok=True)
		path = folder / name
		path.write_bytes(data)
		return path

	def test_import_asks_a_name_from_the_file_and_copies_its_bytes(self):
		presenter = self.make_presenter("alpha", active="alpha")
		data = b"\xef\xbb\xbf" + UPPER.replace("\n", "\r\n").encode("utf-8")
		view = FakeView(names=["upper2"], import_path=self.source("upper2.py", data))

		self.assertEqual(presenter.import_from_file(view), "upper2")

		self.assertEqual(view.calls, [("choose_import", "匯入腳本"), ("prompt", "新增腳本", "upper2")])
		self.assertEqual((self.script_dir / "upper2.py").read_bytes(), data)
		self.set_active_name.assert_not_called()

	def test_a_cancelled_file_dialog_does_nothing(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.import_from_file(view))
		self.assertEqual(view.calls, [("choose_import", "匯入腳本")])

	def test_a_file_that_is_not_python_is_refused_before_a_name_is_asked(self):
		# F-18 review M-2: no name box for a file that cannot be imported whatever its name.
		presenter = self.make_presenter()
		view = FakeView(names=["notes"], import_path=self.source("notes.txt", UPPER.encode("utf-8")))

		self.assertIsNone(presenter.import_from_file(view))

		self.assertEqual(view.calls, [("choose_import", "匯入腳本"), ("error", "匯入腳本失敗：只能匯入 Python 檔案（.py）。")])
		self.assertEqual(self.files(), ["no-processing.py"])

	def test_the_suffix_check_ignores_case(self):
		presenter = self.make_presenter()
		view = FakeView(names=["upper"], import_path=self.source("UPPER.PY", UPPER.encode("utf-8")))

		self.assertEqual(presenter.import_from_file(view), "upper")

		self.assertEqual(view.calls, [("choose_import", "匯入腳本"), ("prompt", "新增腳本", "UPPER")])

	def test_each_error_is_reported_and_nothing_is_copied(self):
		cases = (
			("x.txt", UPPER.encode("utf-8"), "匯入腳本失敗：只能匯入 Python 檔案（.py）。"),
			("cp950.py", NOT_UTF8, f"匯入腳本失敗：{NOT_UTF8_REASON}"),
			("int.py", b"def main(x: int):\n    return x\n", "匯入腳本失敗：main 的參數只能標註為 str，或不加標註。"),
			("two.py", b"def main(a, b):\n    return a\n", "匯入腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。"),
		)
		for name, data, message in cases:
			with self.subTest(name=name):
				presenter = self.make_presenter()
				view = FakeView(names=[Path(name).stem], import_path=self.source(name, data))

				self.assertIsNone(presenter.import_from_file(view))

				self.assertEqual(view.calls[-1], ("error", message))
				self.assertEqual(self.files(), ["no-processing.py"])

	def test_a_syntax_error_is_shown_as_python_gives_it(self):
		presenter = self.make_presenter()
		source = self.source("bad.py", b"def main(:\n")
		with self.assertRaises(SyntaxError) as raised:
			compile("def main(:\n", str(source), "exec")

		view = FakeView(names=["bad"], import_path=source)
		presenter.import_from_file(view)

		self.assertEqual(view.calls[-1], ("error", f"匯入腳本失敗：{raised.exception}"))
		self.assertEqual(self.files(), ["no-processing.py"])

	def test_a_source_that_cannot_be_opened_gets_the_reason(self):
		presenter = self.make_presenter()
		source = self.source("upper.py", UPPER.encode("utf-8"))
		view = FakeView(names=["upper"], import_path=source)

		with patch.object(Path, "read_bytes", side_effect=PermissionError(13, "denied")):
			presenter.import_from_file(view)

		self.assertEqual(
			view.calls[-1],
			("error", "匯入腳本失敗：無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"),
		)

	def test_a_taken_name_asks_again(self):
		presenter = self.make_presenter("upper")
		view = FakeView(names=["upper", "upper2"], import_path=self.source("upper.py", SHOUT.encode("utf-8")))

		self.assertEqual(presenter.import_from_file(view), "upper2")

		self.assertEqual(view.calls[2:4], [("error", "腳本「upper」已存在。"), ("prompt", "新增腳本", "upper")])
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), UPPER)


class PresenterExportTest(PresenterTestCase):
	def test_export_suggests_the_file_name_and_copies(self):
		for name, expected in (("upper", UPPER.encode("utf-8")), ("no-processing", NO_PROCESSING_SCRIPT.encode("utf-8"))):
			with self.subTest(name=name):
				presenter = self.make_presenter("upper")
				destination = self.root / f"out-{name}.py"
				view = FakeView(export_path=destination)

				self.assertIsNone(presenter.export_to_file(view, name))

				self.assertEqual(view.calls, [("choose_export", "匯出腳本", f"{name}.py")])
				self.assertEqual(destination.read_bytes(), expected)

	def test_a_cancelled_or_failed_export(self):
		presenter = self.make_presenter("upper")
		view = FakeView()
		presenter.export_to_file(view, "upper")
		self.assertEqual(view.calls, [("choose_export", "匯出腳本", "upper.py")])

		folder = self.root / "folder.py"
		folder.mkdir()
		view = FakeView(export_path=folder)
		presenter.export_to_file(view, "upper")
		self.assertEqual(view.calls[-1][0], "error")
		self.assertTrue(view.calls[-1][1].startswith("匯出腳本失敗：[Errno "))


if __name__ == "__main__":
	unittest.main()
