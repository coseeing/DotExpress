"""The wx dialogs of Script Management (F-18 D7, D8, D9), against the wx stubs.

``ScriptManagementDialog`` is built without its native window (``object.__new__``) and fake
list, reason and button widgets, as ``test_dictionary_management_dialog`` builds its twin;
``ScriptEditorDialog`` is built for real against a namespace of fake widgets and distinct
power-of-two flags.
"""

import os
import tempfile
import types
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from i18n import _
from tests import wx_stub
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import hold_open

dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
LOGGER = "dotexpress.gui"


def setUpModule():
	_DIALOG_SCOPE.activate()
	# A script that cannot be read is logged to dotexpress.gui (gui.log).
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


tearDownModule = _DIALOG_SCOPE.deactivate

UPPER = b"def main(text: str) -> str:\n    return text.upper()\n"
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"


class _FakeListCtrl:
	def __init__(self, width: int = 500):
		self.item_count = 0
		self.selected = -1
		self.focused = -1
		self.width = width
		self.column_widths = {}
		self.calls = []

	def SetItemCount(self, count):
		self.item_count = count

	def Refresh(self):
		pass

	def GetFirstSelected(self):
		return self.selected

	def Select(self, index, on=True):
		self.selected = index if on else -1

	def Focus(self, index):
		self.focused = index

	def SetFocus(self):
		self.calls.append("SetFocus")

	def GetClientSize(self):
		return types.SimpleNamespace(width=self.width)

	def GetTextExtent(self, text):
		return (len(text) * 8, 16)

	def SetColumnWidth(self, column, width):
		self.column_widths[column] = width


class _FakeControl:
	"""The reason label or field: records what the dialog does."""

	def __init__(self):
		self.shown = False
		self.value = ""
		self.calls = []

	def Show(self, show=True):
		self.shown = show

	def ChangeValue(self, value):
		self.value = value

	def SelectAll(self):
		self.calls.append("SelectAll")


class _FakeActions:
	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""

	def __init__(self, script_dir, names, results=None):
		self.script_dir = Path(script_dir)
		self.script_names = list(names)
		self.results = dict(results or {})
		self.calls = []

	def script_path(self, name):
		return self.script_dir / f"{name}.py"

	def _record(self, action, *args):
		self.calls.append((action, *args))
		return self.results.get(action)

	def add(self, view):
		return self._record("add", view)

	def edit(self, view, name):
		return self._record("edit", view, name)

	def delete(self, view, name):
		return self._record("delete", view, name)

	def rename(self, view, name):
		return self._record("rename", view, name)

	def import_from_file(self, view):
		return self._record("import", view)

	def export_to_file(self, view, name):
		return self._record("export", view, name)


class ManagementTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.script_dir = Path(temp_dir.name)

	def write(self, name, data=UPPER):
		path = self.script_dir / f"{name}.py"
		path.write_bytes(data)
		return path

	def make_dialog(self, names, actions=None):
		target = object.__new__(dialog.ScriptManagementDialog)
		target._actions = actions if actions is not None else _FakeActions(self.script_dir, names)
		target._script_names = list(names)
		target._script_checks = {}
		target._selected_name = names[0] if names else ""
		target.list_ctrl = _FakeListCtrl()
		for name in ("add", "delete", "rename", "edit", "import", "export"):
			setattr(target, f"{name}_button", Mock())
		target.problem_label = _FakeControl()
		target.problem_ctrl = _FakeControl()
		target.Layout = Mock()
		return target

	def rows(self, target):
		return [[target._get_item_text(row, column) for column in (0, 1)] for row in range(target.list_ctrl.item_count)]

	def select(self, target, index):
		target.list_ctrl.selected = index
		target._on_selection_changed(Mock())


class ScriptListTest(ManagementTestCase):
	def test_no_processing_is_shown_translated_and_ready_without_reading_its_file(self):
		# F-18 (D4): conversion never reads no-processing.py, so its bytes do not matter.
		self.write("no-processing", b"def main(:\n")
		target = self.make_dialog(["no-processing"])

		with patch.object(dialog, "read_script_status", wraps=dialog.read_script_status) as read:
			target.refresh_scripts(["no-processing"], "no-processing")

		read.assert_not_called()
		self.assertEqual(self.rows(target), [["不處理", "可使用"]])
		self.assertFalse(target.problem_ctrl.shown)

	def test_each_script_shows_its_status(self):
		# F-18 (D7, O6): Ready, Unreadable, Not Valid.
		self.write("upper")
		self.write("cp950", NOT_UTF8)
		self.write("bad", b"def main(:\n")
		self.write("two", b"def main(a, b):\n    return a\n")
		names = ["no-processing", "bad", "cp950", "two", "upper"]
		target = self.make_dialog(names)

		with self.assertLogs(LOGGER, "ERROR") as logs:
			target.refresh_scripts(names, "no-processing")

		self.assertEqual(
			self.rows(target),
			[["不處理", "可使用"], ["bad", "格式不正確"], ["cp950", "無法讀取"], ["two", "格式不正確"], ["upper", "可使用"]],
		)
		# Only the read error is logged; invalid code is the user's content.
		self.assertEqual(len(logs.records), 1)
		self.assertIn('"cp950.py"', logs.output[0])

	def test_the_reason_row_says_why_and_selects_its_text(self):
		self.write("upper")
		self.write("two", b"def main(a, b):\n    return a\n")
		self.write("cp950", NOT_UTF8)
		names = ["no-processing", "cp950", "two", "upper"]
		target = self.make_dialog(names)
		with self.assertLogs(LOGGER, "ERROR"):
			target.refresh_scripts(names, "two")

		self.assertEqual(target.problem_ctrl.value, "main 必須恰好定義一個位置參數，且不得有其他參數。")
		self.assertEqual((target.problem_label.shown, target.problem_ctrl.shown), (True, True))
		self.assertEqual(target.problem_ctrl.calls, ["SelectAll"])

		self.select(target, 1)
		self.assertEqual(target.problem_ctrl.value, "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。")

		self.select(target, 3)
		self.assertEqual((target.problem_ctrl.value, target.problem_ctrl.shown, target.problem_label.shown), ("", False, False))

	def test_the_active_script_is_selected_and_focused(self):
		self.write("alpha")
		self.write("upper")
		names = ["no-processing", "alpha", "upper"]
		target = self.make_dialog(names)

		target.refresh_scripts(names, "upper")

		self.assertEqual((target.list_ctrl.selected, target.list_ctrl.focused), (2, 2))

		target.refresh_scripts(names, "gone")
		self.assertEqual(target.list_ctrl.selected, 0)

	@unittest.skipUnless(os.name == "nt", "Windows sharing modes")
	def test_a_locked_and_a_broken_script_do_not_stop_the_dialog(self):
		# F-18 (D-G): the GUI item 160 case.
		locked = self.write("locked")
		self.write("broken", b"def main(text)\n    return text\n")
		hold_open(self, locked, 0)
		names = ["no-processing", "broken", "locked"]
		target = self.make_dialog(names)

		with self.assertLogs(LOGGER, "ERROR"):
			target.refresh_scripts(names, "locked")

		self.assertEqual(self.rows(target), [["不處理", "可使用"], ["broken", "格式不正確"], ["locked", "無法讀取"]])
		self.assertEqual(target.problem_ctrl.value, CANNOT_OPEN)


class ScriptButtonsTest(ManagementTestCase):
	def enabled(self, target):
		return {
			name: getattr(target, f"{name}_button").Enable.call_args.args[0]
			for name in ("add", "delete", "rename", "edit", "import", "export")
		}

	def test_no_processing_can_only_be_exported_and_a_user_script_everything(self):
		# F-18 (D7): Edit too is disabled for No Processing.
		self.write("upper")
		names = ["no-processing", "upper"]
		target = self.make_dialog(names)

		target.refresh_scripts(names, "no-processing")
		self.assertEqual(
			self.enabled(target),
			{"add": True, "delete": False, "rename": False, "edit": False, "import": True, "export": True},
		)

		self.select(target, 1)
		self.assertEqual(
			self.enabled(target),
			{"add": True, "delete": True, "rename": True, "edit": True, "import": True, "export": True},
		)


class ScriptHandlersTest(ManagementTestCase):
	def setUp(self):
		super().setUp()
		for name in ("upper", "shout"):
			self.write(name)
		self.names = ["no-processing", "shout", "upper"]

	def test_edit_runs_the_action_then_refreshes_and_focuses_the_list(self):
		# F-18 (D8.2, O4): the dialog stays open; the status is read again.
		actions = _FakeActions(self.script_dir, self.names, {"edit": "upper"})
		target = self.make_dialog(self.names, actions)
		target.refresh_scripts(self.names, "upper")
		self.write("upper", b"def main(:\n")

		target._on_edit_clicked(Mock())

		self.assertEqual(actions.calls, [("edit", target, "upper")])
		self.assertEqual(self.rows(target)[2], ["upper", "格式不正確"])
		self.assertEqual(target.list_ctrl.calls, ["SetFocus"])

	def test_add_delete_rename_and_import_refresh_with_the_name_they_return(self):
		for action, handler, selected in (
			("add", "_on_add_clicked", None),
			("delete", "_on_delete_clicked", "upper"),
			("rename", "_on_rename_clicked", "upper"),
			("import", "_on_import_clicked", None),
		):
			with self.subTest(action=action):
				actions = _FakeActions(self.script_dir, self.names, {action: "shout"})
				target = self.make_dialog(self.names, actions)
				target.refresh_scripts(self.names, "upper")

				getattr(target, handler)(Mock())

				expected = (action, target, selected) if selected else (action, target)
				self.assertEqual(actions.calls, [expected])
				self.assertEqual(target.list_ctrl.selected, 1)
				self.assertEqual(target.list_ctrl.calls, ["SetFocus"] if action == "add" else [])

	def test_nothing_is_refreshed_when_an_action_returns_none_and_export_returns_nothing(self):
		actions = _FakeActions(self.script_dir, self.names)
		target = self.make_dialog(self.names, actions)
		target.refresh_scripts(self.names, "upper")
		target.refresh_scripts = Mock()

		for handler in ("_on_add_clicked", "_on_edit_clicked", "_on_delete_clicked", "_on_rename_clicked", "_on_import_clicked", "_on_export_clicked"):
			getattr(target, handler)(Mock())

		target.refresh_scripts.assert_not_called()
		self.assertEqual(actions.calls[-1], ("export", target, "upper"))


class ScriptViewTest(ManagementTestCase):
	def test_delete_asks_in_a_system_yes_no_box_with_no_as_default(self):
		target = self.make_dialog(["no-processing"])
		with patch.object(dialog, "message_box", return_value=dialog.wx.YES) as box:
			self.assertTrue(target.confirm("要刪除腳本「upper」嗎？", "確認刪除腳本"))

		box.assert_called_once_with(
			"要刪除腳本「upper」嗎？",
			"確認刪除腳本",
			dialog.wx.YES_NO | dialog.wx.NO_DEFAULT | dialog.wx.ICON_WARNING,
			parent=target,
		)

	def test_boxes_belong_to_the_dialog(self):
		target = self.make_dialog(["no-processing"])
		with patch.object(dialog, "message_box") as box:
			target.show_error("e")
			target.show_info("i")

		self.assertEqual(
			[call.args + (call.kwargs["parent"],) for call in box.call_args_list],
			[
				("e", "錯誤", dialog.wx.OK | dialog.wx.ICON_ERROR, target),
				("i", "資訊", dialog.wx.OK | dialog.wx.ICON_INFORMATION, target),
			],
		)

	def test_the_file_dialogs_offer_python_files(self):
		target = self.make_dialog(["no-processing"])
		created = []

		class FileDialog:
			def __init__(self, *args, **kwargs):
				created.append((args, kwargs))

			def __enter__(self):
				return self

			def __exit__(self, *_exc):
				return False

			def ShowModal(self):
				return dialog.wx.ID_OK

			def GetPath(self):
				return "C:/in/upper.py"

		with patch.object(dialog.wx, "FileDialog", FileDialog, create=True):
			self.assertEqual(target.choose_import_path("匯入腳本"), Path("C:/in/upper.py"))
			self.assertEqual(target.choose_export_path("匯出腳本", "upper.py"), Path("C:/in/upper.py"))

		self.assertEqual(
			created,
			[
				((target, "匯入腳本"), {"wildcard": "Python 檔案 (*.py)|*.py", "style": dialog.wx.FD_OPEN}),
				(
					(target, "匯出腳本"),
					{
						"defaultFile": "upper.py",
						"wildcard": "Python 檔案 (*.py)|*.py",
						"style": dialog.wx.FD_SAVE | dialog.wx.FD_OVERWRITE_PROMPT,
					},
				),
			],
		)

	def test_the_name_prompt_and_the_editor_open_over_the_dialog(self):
		target = self.make_dialog(["no-processing"])
		name_dialog = Mock()
		name_dialog.__enter__ = Mock(return_value=name_dialog)
		name_dialog.__exit__ = Mock(return_value=False)
		name_dialog.ShowModal.return_value = dialog.wx.ID_OK
		name_dialog.get_script_name.return_value = "upper"
		editor = Mock()
		editor.__enter__ = Mock(return_value=editor)
		editor.__exit__ = Mock(return_value=False)
		save = Mock()

		with (
			patch.object(dialog, "ScriptNameDialog", return_value=name_dialog) as name_class,
			patch.object(dialog, "ScriptEditorDialog", return_value=editor) as editor_class,
		):
			self.assertEqual(target.prompt_script_name("新增腳本", "x"), "upper")
			self.assertIsNone(target.edit_script("upper", "source", save))

		name_class.assert_called_once_with(target, "新增腳本", initial_name="x")
		editor_class.assert_called_once_with(target, script_name="upper", source="source", save=save)
		editor.ShowModal.assert_called_once_with()


class ScriptNameDialogTest(unittest.TestCase):
	def make(self, text):
		target = object.__new__(dialog.ScriptNameDialog)
		target.name_ctrl = Mock()
		target.name_ctrl.GetValue.return_value = text
		return target

	def test_each_refused_name_gets_its_message(self):
		cases = (
			("", "請輸入腳本名稱。"),
			("x" * 33, "腳本名稱長度需為 1 到 32 個字元。"),
			("a/b", "腳本名稱不是有效的 Windows 檔名。"),
			# F-18 (D4): the name as typed, not one fixed reserved name.
			(" 不處理", "腳本名稱「不處理」為保留名稱。"),
			("No-Processing", "腳本名稱「No-Processing」為保留名稱。"),
			("no processing", "腳本名稱「no processing」為保留名稱。"),
		)
		for text, message in cases:
			with self.subTest(text=text):
				target = self.make(text)
				event = Mock()
				with patch.object(dialog, "message_box") as box:
					target._on_ok(event)

				box.assert_called_once_with(message, "資訊", dialog.wx.OK | dialog.wx.ICON_INFORMATION, parent=target)
				event.Skip.assert_not_called()

	def test_a_valid_name_is_written_back_without_spaces(self):
		target = self.make(" 大寫")
		event = Mock()

		target._on_ok(event)

		target.name_ctrl.SetValue.assert_called_once_with("大寫")
		event.Skip.assert_called_once_with()


# --- the editor ----------------------------------------------------------------


FLAG_NAMES = (
	"DEFAULT_DIALOG_STYLE",
	"RESIZE_BORDER",
	"TE_MULTILINE",
	"TE_RICH2",
	"TE_DONTWRAP",
	"EXPAND",
	"ALL",
	"LEFT",
	"RIGHT",
	"BOTTOM",
	"OK",
	"CANCEL",
	"APPLY",
	"CLOSE",
	"ICON_ERROR",
	"VERTICAL",
	"TOP",
)
FLAGS = types.SimpleNamespace(**{name: 1 << index for index, name in enumerate(FLAG_NAMES)})
ID_OK, ID_CANCEL, ID_APPLY, ID_CLOSE = 5100, 5101, 5102, 5103


class _Event:
	def __init__(self):
		self.skipped = False

	def Skip(self):
		self.skipped = True


class _FakeButton:
	def __init__(self, harness, button_id):
		self.harness = harness
		self.id = button_id
		self.label = None
		self.handlers = []

	def SetLabel(self, label):
		self.label = label

	def Bind(self, _event, handler):
		self.handlers.append(handler)

	def click(self):
		event = _Event()
		for handler in self.handlers:
			handler(event)
		return event.skipped


class _FakeEditor:
	"""Multi-line text control; like wxMSW it hands back its line ends as \\n."""

	def __init__(self, harness, value):
		self.harness = harness
		self.value = value.replace("\r\n", "\n")
		self.name = None
		self.font = Mock()
		self.insertion_point = None

	def GetValue(self):
		return self.value

	def SetName(self, name):
		self.name = name

	def GetFont(self):
		return self.font

	def SetFont(self, font):
		self.harness.log.append(("SetFont", font.SetFamily.call_args.args))

	def SetInsertionPoint(self, position):
		self.insertion_point = position

	def SetFocus(self):
		self.harness.log.append(("SetFocus", "editor"))
		self.harness.focus = self


class _EditorHarness:
	"""Builds the real ``ScriptEditorDialog`` against fake widgets and drives it."""

	def __init__(self, test, source="def main(text):\n    return text\n", save=None):
		self.log = []
		self.saved = []
		self.confirm_answers = []
		self.focus = None
		self.buttons = {button_id: _FakeButton(self, button_id) for button_id in (ID_OK, ID_CANCEL, ID_APPLY)}
		self.save = save if save is not None else self.saved.append
		stack = ExitStack()
		test.addCleanup(stack.close)
		wx = types.SimpleNamespace(
			**vars(FLAGS),
			ID_OK=ID_OK,
			ID_CANCEL=ID_CANCEL,
			ID_APPLY=ID_APPLY,
			ID_CLOSE=ID_CLOSE,
			EVT_BUTTON="EVT_BUTTON",
			FONTFAMILY_TELETYPE="TELETYPE",
			Window=types.SimpleNamespace(FindFocus=lambda: self.focus),
			BoxSizer=lambda _orientation: Mock(),
			StaticText=lambda _parent, label="": self.log.append(("StaticText", label)),
			TextCtrl=self._text_ctrl,
		)
		harness = self

		def base_init(_dialog, parent, title=None, style=None):
			harness.log.append(("Dialog.__init__", parent, title, style))

		# The stub's wx.Dialog under the editor; looked up here, so that the module loads before the class exists.
		native_base = next(base for base in dialog.ScriptEditorDialog.__mro__ if base.__name__ == "Dialog")
		stack.enter_context(patch.object(native_base, "__init__", base_init, create=True))
		stack.enter_context(patch.object(dialog, "wx", wx))
		stack.enter_context(patch.object(dialog, "message_box", self._message_box))
		stack.enter_context(patch.object(dialog, "confirm_box", self._confirm_box))
		editor = object.__new__(dialog.ScriptEditorDialog)
		editor.CreateButtonSizer = lambda flags: self.log.append(("CreateButtonSizer", flags)) or Mock()
		editor.FindWindow = self.buttons.get
		editor.SetSizer = lambda _sizer: None
		editor.SetMinSize = lambda size: self.log.append(("SetMinSize", size))
		editor.SetSize = lambda size: self.log.append(("SetSize", size))
		editor.CentreOnParent = lambda: None
		editor.IsDescendant = lambda window: window is editor.__dict__.get("editor")
		editor.Destroy = lambda: self.log.append(("Destroy",))
		self.dialog = editor
		editor.__init__("parent", script_name="upper", source=source, save=self._save)
		# What the construction did; the log then records only what the test drives.
		self.built = list(self.log)
		self.log.clear()

	def _text_ctrl(self, _parent, value="", style=None):
		self.log.append(("TextCtrl", value, style))
		self.editor = _FakeEditor(self, value)
		return self.editor

	def _save(self, text):
		self.log.append(("save", text))
		self.save(text)

	def _message_box(self, message, caption, style, parent=None):
		self.log.append(("MessageBox", message, caption, style, parent))
		self.focus = "box button"

	def _confirm_box(self, message, caption, ok_label, cancel_label, parent=None):
		self.log.append(("ConfirmBox", message, caption, ok_label, cancel_label, parent))
		self.focus = "box button"
		return self.confirm_answers.pop(0)

	def type(self, text):
		self.editor.value = text


class ScriptEditorBuildTest(unittest.TestCase):
	def test_the_title_is_the_name_and_the_code_is_in_a_named_monospace_editor(self):
		# F-18 (D9, O9): the title names the script, so the editor is 「Python 程式碼」.
		source = "def main(text):\r\n    return text\r\n"
		harness = _EditorHarness(self, source=source)

		self.assertEqual(harness.built[0], ("Dialog.__init__", "parent", "upper", FLAGS.DEFAULT_DIALOG_STYLE | FLAGS.RESIZE_BORDER))
		# The label right before the editor is its accessible name, as the reason row's label in
		# Dictionary Management is (F-6 D3); SetName alone does not reach UIA (GUI item 149).
		self.assertEqual(harness.built[1], ("StaticText", "Python 程式碼"))
		self.assertEqual(harness.built[2], ("TextCtrl", source, FLAGS.TE_MULTILINE | FLAGS.TE_RICH2 | FLAGS.TE_DONTWRAP))
		self.assertIn(("SetFont", ("TELETYPE",)), harness.built)
		self.assertIn(("CreateButtonSizer", FLAGS.OK | FLAGS.CANCEL | FLAGS.APPLY), harness.built)
		self.assertEqual(harness.built[-3:], [("SetMinSize", (520, 300)), ("SetSize", (720, 440)), ("SetFocus", "editor")])
		self.assertEqual(harness.editor.name, "Python 程式碼")
		self.assertEqual(harness.editor.insertion_point, 0)
		self.assertEqual([button.label for button in harness.buttons.values()], ["確定", "取消", "套用"])


class ScriptEditorSaveTest(unittest.TestCase):
	def test_apply_saves_the_text_and_keeps_the_dialog_open(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text.upper()\n")

		self.assertFalse(harness.buttons[ID_APPLY].click())

		self.assertEqual(harness.saved, ["def main(text):\n    return text.upper()\n"])
		self.assertEqual(harness.log, [("save", "def main(text):\n    return text.upper()\n")])

	def test_a_failed_save_is_explained_and_the_focus_goes_back_to_the_code(self):
		cases = (
			(
				ValueError("main must define exactly one positional parameter and no other parameters."),
				"儲存腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。",
			),
			(SyntaxError("invalid syntax", ("upper.py", 1, 10, "def main(:\n")), "儲存腳本失敗：invalid syntax (upper.py, line 1)"),
			(FileExistsError("腳本「upper」已存在。"), "儲存腳本失敗：腳本「upper」已存在。"),
			(PermissionError(13, "Permission denied"), "儲存腳本失敗：[Errno 13] Permission denied"),
		)
		for error, message in cases:
			with self.subTest(error=type(error).__name__):
				harness = _EditorHarness(self, save=Mock(side_effect=error))
				harness.type("changed")

				self.assertFalse(harness.buttons[ID_OK].click())

				self.assertEqual(
					harness.log,
					[
						("save", "changed"),
						("MessageBox", message, "錯誤", FLAGS.OK | FLAGS.ICON_ERROR, harness.dialog),
						("SetFocus", "editor"),
					],
				)

	def test_ok_closes_after_a_successful_save(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text\n# changed\n")

		self.assertTrue(harness.buttons[ID_OK].click())
		self.assertEqual(harness.saved, ["def main(text):\n    return text\n# changed\n"])


class ScriptEditorCancelTest(unittest.TestCase):
	QUESTION = (
		"ConfirmBox",
		"要放棄對腳本「upper」所做的變更嗎？",
		"尚未儲存的變更",
		"放棄變更",
		"返回編輯",
	)

	def test_cancel_without_a_change_closes_without_asking_or_saving(self):
		# The template of an Add, unchanged, is no change either.
		for source in ("def main(input: str) -> str:\n    return input\n", "def main(text):\r\n    return text\r\n"):
			with self.subTest(source=source):
				harness = _EditorHarness(self, source=source)

				self.assertTrue(harness.buttons[ID_CANCEL].click())
				self.assertEqual(harness.log, [])

	def test_back_to_editing_keeps_the_dialog_and_the_focus(self):
		harness = _EditorHarness(self)
		harness.type("changed")
		harness.confirm_answers.append(False)

		self.assertFalse(harness.buttons[ID_CANCEL].click())

		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog), ("SetFocus", "editor")])
		self.assertEqual(harness.editor.value, "changed")

	def test_discard_changes_closes_without_saving(self):
		harness = _EditorHarness(self)
		harness.type("changed")
		harness.confirm_answers.append(True)

		self.assertTrue(harness.buttons[ID_CANCEL].click())

		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog)])
		self.assertEqual(harness.saved, [])

	def test_after_a_successful_apply_cancel_closes_without_asking(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text.upper()\n")
		harness.buttons[ID_APPLY].click()
		harness.log.clear()

		self.assertTrue(harness.buttons[ID_CANCEL].click())
		self.assertEqual(harness.log, [])

	def test_after_a_failed_apply_cancel_still_asks(self):
		harness = _EditorHarness(self, save=Mock(side_effect=SyntaxError("bad")))
		harness.type("def main(:\n")
		harness.buttons[ID_APPLY].click()
		harness.log.clear()
		harness.focus = harness.editor
		harness.confirm_answers.append(True)

		self.assertTrue(harness.buttons[ID_CANCEL].click())
		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog)])


if __name__ == "__main__":
	unittest.main()
