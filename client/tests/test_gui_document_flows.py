from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def _install_stub_modules() -> None:
    wx = sys.modules.get("wx", types.ModuleType("wx"))

    class _Widget:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, _name):
            def _method(*args, **kwargs):
                return None

            return _method

    class Window(_Widget):
        @staticmethod
        def FindFocus():
            return None

    class Frame(Window):
        pass

    class Dialog(Window):
        pass

    class Accessible(_Widget):
        pass

    class App(_Widget):
        pass

    class Menu(_Widget):
        pass

    class MenuBar(_Widget):
        pass

    class StaticText(Window):
        pass

    class BoxSizer(_Widget):
        pass

    class StaticBoxSizer(_Widget):
        pass

    class StaticBox(_Widget):
        pass

    class Choice(Window):
        pass

    class TextCtrl(Window):
        pass

    class ListCtrl(Window):
        pass

    class SpinCtrl(Window):
        pass

    class CommandEvent(_Widget):
        pass

    class CloseEvent(_Widget):
        pass

    class KeyEvent(_Widget):
        pass

    class MouseEvent(_Widget):
        pass

    class ListEvent(_Widget):
        pass

    class ContextMenuEvent(_Widget):
        pass

    class Font(_Widget):
        pass

    class Colour(tuple):
        def __new__(cls, red=0, green=0, blue=0):
            return tuple.__new__(cls, (red, green, blue))

    class Point(tuple):
        def __new__(cls, x=0, y=0):
            return tuple.__new__(cls, (x, y))

    class _Timer:
        def __init__(self, *_args, **_kwargs):
            self.stopped = False

        def Stop(self):
            self.stopped = True

    class _FileDialog(Dialog):
        def GetPaths(self):
            return []

        def GetPath(self):
            return ""

        def SetFilterIndex(self, _index):
            return None

        def GetFilterIndex(self):
            return 0

    class _DirDialog(Dialog):
        def GetPath(self):
            return ""

    class _MessageDialog(Dialog):
        pass

    wx.Window = Window
    wx.Frame = Frame
    wx.Dialog = Dialog
    wx.Accessible = Accessible
    wx.App = App
    wx.Menu = Menu
    wx.MenuBar = MenuBar
    wx.StaticText = StaticText
    wx.BoxSizer = BoxSizer
    wx.StaticBoxSizer = StaticBoxSizer
    wx.StaticBox = StaticBox
    wx.Choice = Choice
    wx.TextCtrl = TextCtrl
    wx.ListCtrl = ListCtrl
    wx.SpinCtrl = SpinCtrl
    wx.CommandEvent = CommandEvent
    wx.CloseEvent = CloseEvent
    wx.KeyEvent = KeyEvent
    wx.MouseEvent = MouseEvent
    wx.ListEvent = ListEvent
    wx.ContextMenuEvent = ContextMenuEvent
    wx.Font = Font
    wx.Colour = Colour
    wx.Point = Point
    wx.FileDialog = _FileDialog
    wx.DirDialog = _DirDialog
    wx.MessageDialog = _MessageDialog
    wx.CallAfter = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    wx.CallLater = lambda *_args, **_kwargs: _Timer()
    wx.MessageBox = lambda *args, **kwargs: wx.OK
    wx.DefaultPosition = Point()
    wx.DefaultSize = Point()
    wx.__path__ = []
    wx.__getattr__ = lambda name: type(name, (), {})
    wx_html2 = types.ModuleType("wx.html2")
    wx_html2.WebView = type(
        "WebView",
        (),
        {"New": staticmethod(lambda parent: Mock())},
    )
    wx.html2 = wx_html2
    sys.modules["wx.html2"] = wx_html2

    wx_lib = types.ModuleType("wx.lib")
    wx_lib_scrolledpanel = types.ModuleType("wx.lib.scrolledpanel")

    class _ScrolledPanel(Window):
        def SetupScrolling(self, *args, **kwargs):
            pass

        def SetSizer(self, *args, **kwargs):
            pass

        def Fit(self):
            pass

        def Layout(self):
            pass

    wx_lib_scrolledpanel.ScrolledPanel = _ScrolledPanel
    wx_lib.ScrolledPanel = _ScrolledPanel
    wx.lib = wx_lib
    sys.modules["wx.lib"] = wx_lib
    sys.modules["wx.lib.scrolledpanel"] = wx_lib_scrolledpanel

    wx.ID_ANY = -1
    wx.ID_ABOUT = 1
    wx.ID_OK = 2
    wx.OK = 4
    wx.CANCEL = 8
    wx.YES = 1
    wx.NO = 0
    wx.YES_NO = 16
    wx.NO_DEFAULT = 32
    wx.ICON_ERROR = 64
    wx.ICON_INFORMATION = 128
    wx.ICON_WARNING = 256
    wx.DEFAULT_DIALOG_STYLE = 512
    wx.CLOSE_BOX = 1024
    wx.STAY_ON_TOP = 2048
    wx.VERTICAL = 4096
    wx.HORIZONTAL = 8192
    wx.ALL = 16384
    wx.ALIGN_CENTER_HORIZONTAL = 32768
    wx.ALIGN_CENTER_VERTICAL = 65536
    wx.EXPAND = 131072
    wx.LEFT = 262144
    wx.RIGHT = 524288
    wx.BOTTOM = 1048576
    wx.TE_MULTILINE = 2097152
    wx.TE_READONLY = 4194304
    wx.FD_OPEN = 1 << 20
    wx.FD_MULTIPLE = 1 << 21
    wx.FD_SAVE = 1 << 22
    wx.FD_OVERWRITE_PROMPT = 1 << 23
    wx.NOT_FOUND = -1
    wx.ACC_OK = 0

    sys.modules["wx"] = wx

    if "dialog" not in sys.modules:
        dialog = types.ModuleType("dialog")

        class _Dialog:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def ShowModal(self):
                return 0

        for name in (
            "DictionaryManagementDialog",
            "DictionaryNameDialog",
            "DocumentNameDialog",
            "FileIssuesDialog",
            "InvalidWorkspaceFilesDialog",
            "SpeechSymbolsDialog",
            "TranslationSettingsDialog",
            "TranslationTableDialog",
        ):
            setattr(dialog, name, _Dialog)
        dialog.finalize_dialog_layout = lambda *args, **kwargs: None

        sys.modules["dialog"] = dialog

    if "braille.louis_helper" not in sys.modules:
        louis_helper = types.ModuleType("braille.louis_helper")
        louis_helper.initialize = lambda: None
        louis_helper.terminate = lambda: None
        sys.modules["braille.louis_helper"] = louis_helper

    if "mammoth" not in sys.modules:
        mammoth = types.ModuleType("mammoth")
        mammoth.convert_to_html = lambda *args, **kwargs: types.SimpleNamespace(value="")
        sys.modules["mammoth"] = mammoth

    if "lxml" not in sys.modules:
        lxml = types.ModuleType("lxml")
        etree = types.ModuleType("lxml.etree")
        html = types.ModuleType("lxml.html")

        class _QName:
            def __init__(self, element):
                self.localname = getattr(element, "tag", "")

        etree.QName = _QName
        etree.XMLParser = lambda *args, **kwargs: object()
        etree.fromstring = lambda *args, **kwargs: types.SimpleNamespace(xpath=lambda *_a, **_k: [])
        html.fragment_fromstring = lambda *args, **kwargs: types.SimpleNamespace()
        lxml.etree = etree
        lxml.html = html
        sys.modules["lxml"] = lxml
        sys.modules["lxml.etree"] = etree
        sys.modules["lxml.html"] = html

    if "ebooklib" not in sys.modules:
        ebooklib = types.ModuleType("ebooklib")
        epub = types.ModuleType("ebooklib.epub")
        epub.read_epub = lambda *_args, **_kwargs: types.SimpleNamespace(spine=[], get_item_with_id=lambda _item_id: None)
        ebooklib.epub = epub
        sys.modules["ebooklib"] = ebooklib
        sys.modules["ebooklib.epub"] = epub

    if "pymupdf" not in sys.modules:
        pymupdf = types.ModuleType("pymupdf")
        sys.modules["pymupdf"] = pymupdf

    if "pypdf" not in sys.modules:
        pypdf = types.ModuleType("pypdf")
        pypdf.PdfReader = type("PdfReader", (), {})
        sys.modules["pypdf"] = pypdf


_install_stub_modules()
gui = importlib.import_module("gui")

from documents.workspace import Document
from documents.export_results import ExportBatchResult
from settings.dialogs import TranslationSettingsPanel
from settings.state import DotExpressSettingsSnapshot
from settings.translation import TranslationSettings
from settings.view import ViewSettings


def make_snapshot(
    *,
    translation=TranslationSettings("unicode", 40, "default"),
    tables=None,
    view=ViewSettings(40, "light", "default"),
) -> DotExpressSettingsSnapshot:
    return DotExpressSettingsSnapshot.create(
        translation=translation,
        translation_tables={} if tables is None else tables,
        view=view,
    )


class GuiDocumentFlowsTest(unittest.TestCase):
    def _make_frame(self) -> gui.BrailleFrame:
        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
        frame.translation_runtime = Mock()
        frame._conversion_runner = Mock()
        frame._conversion_runner.is_running.return_value = False
        frame._conversion_runner.start = Mock(return_value=7)
        frame._convert_dialog_timer = Mock()
        frame._convert_dialog = Mock()
        frame._set_conversion_busy = Mock()
        frame._close_converting_dialog = Mock()
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_export_all_result = Mock()
        frame._dual_view_frame = None
        frame._dual_view_results_by_document = {}
        frame._open_document_name = "alpha"
        return frame

    def test_convert_text_for_output_forwards_runtime(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = Mock(width=40, output_mode="unicode")
        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
        frame._build_conversion_request = Mock(return_value=Mock())

        with patch.object(gui, "convert_text_for_output", return_value="braille") as convert_mock:
            result = frame._convert_text_for_output("source")

        self.assertEqual(result, "braille")
        convert_mock.assert_called_once_with(
            frame._build_conversion_request.return_value,
            runtime=frame.translation_runtime,
        )


class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
    def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
        runtime = Mock()
        frame = Mock()

        with (
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertTrue(result)
        frame_class.assert_called_once_with(None, runtime=runtime)
        frame.Show.assert_called_once_with()

    def test_app_exit_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.translation_runtime = runtime

        result = app.OnExit()

        self.assertEqual(result, 0)
        runtime.close.assert_called_once_with()

    def test_start_conversion_builds_request_and_starts_runner(self) -> None:
        frame = self._make_frame()
        frame._build_conversion_request = Mock(return_value=Mock())
        with patch.object(gui.wx, "CallLater", return_value=Mock()) as call_later:
            frame._start_conversion(
                "zh-tw.ctb",
                "source",
                40,
                "unicode",
                Path("dictionary/default.csv"),
            )

        frame._build_conversion_request.assert_called_once_with(
            "source",
            "zh-tw.ctb",
            "unicode",
            40,
            Path("dictionary/default.csv"),
        )
        frame._conversion_runner.start.assert_called_once_with(
            gui.ConversionJobRequest(
                conversion_request=frame._build_conversion_request.return_value,
                completion_policy=gui.ConversionCompletionPolicy(),
            )
        )
        frame._set_conversion_busy.assert_called_once_with(True)
        frame._close_converting_dialog.assert_called_once_with()
        call_later.assert_called_once_with(2000, frame._show_converting_dialog, 7)

    def test_manual_conversion_updates_output_focus_and_shows_completion(self) -> None:
        frame = self._make_frame()
        policy = gui.ConversionCompletionPolicy()
        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._complete_conversion(policy, display_text="braille")

        frame.output_txt.SetValue.assert_called_once_with("braille")
        frame.output_txt.SetFocus.assert_called_once_with()
        message_box.assert_called_once_with(
            gui._("Conversion completed."),
            gui._("Info"),
            gui.wx.OK | gui.wx.ICON_INFORMATION,
            parent=frame,
        )

    def test_export_conversion_calls_success_callback_without_manual_message(self) -> None:
        frame = self._make_frame()
        on_success = Mock()
        policy = gui.ConversionCompletionPolicy(
            on_success=on_success,
            update_output=False,
            show_success=False,
        )

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._complete_conversion(policy, display_text="braille")

        on_success.assert_called_once_with("braille")
        frame.output_txt.SetValue.assert_not_called()
        frame.output_txt.SetFocus.assert_not_called()
        message_box.assert_not_called()

    def test_export_conversion_calls_error_callback_without_showing_worker_error(self) -> None:
        frame = self._make_frame()
        on_error = Mock()
        policy = gui.ConversionCompletionPolicy(
            on_error=on_error,
            update_output=False,
            show_success=False,
        )

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._complete_conversion(policy, error_message="boom")

        on_error.assert_called_once_with("boom")
        message_box.assert_not_called()

    def test_later_job_uses_its_own_policy_after_previous_completion(self) -> None:
        frame = self._make_frame()
        first_policy = gui.ConversionCompletionPolicy(
            on_success=Mock(),
            update_output=False,
            show_success=False,
        )
        second_policy = gui.ConversionCompletionPolicy()
        first_result = gui.ConversionJobSuccess(
            job_id=1,
            conversion_output=gui.ConversionOutput("first", ("old",)),
            completion_policy=first_policy,
        )
        second_result = gui.ConversionJobSuccess(
            job_id=2,
            conversion_output=gui.ConversionOutput("second", ("new",)),
            completion_policy=second_policy,
        )

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._finish_conversion_success(first_result)
            frame._finish_conversion_success(second_result)

        first_policy.on_success.assert_called_once_with("first")
        frame.output_txt.SetValue.assert_called_once_with("second")
        frame.output_txt.SetFocus.assert_called_once_with()
        message_box.assert_called_once_with(
            gui._("Conversion completed."),
            gui._("Info"),
            gui.wx.OK | gui.wx.ICON_INFORMATION,
            parent=frame,
        )

    def test_export_all_continues_after_conversion_failure(self) -> None:
        frame = self._make_frame()
        written: list[tuple[str, str]] = []

        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
            written.append((destination_path.name, document.name))

        def start_export_conversion(document: Document, destination_path: Path, format_key: str, *, on_success=None, on_error=None, on_missing_table=None):
            if document.name == "pending":
                on_error("Translation failed")
            else:
                raise AssertionError("unexpected conversion request")
            return True

        frame._write_export_document = write_export_document
        frame._start_export_conversion = start_export_conversion

        documents = [
            Document("ready-one", "text", "braille-one"),
            Document("pending", "text", None),
            Document("ready-two", "text", "braille-two"),
        ]

        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())

        self.assertEqual(
            written,
            [
                ("ready-one.brl", "ready-one"),
                ("ready-two.brl", "ready-two"),
            ],
        )
        frame._show_export_all_result.assert_called_once()
        result = frame._show_export_all_result.call_args.args[0]
        self.assertFalse(result.all_succeeded)
        self.assertEqual(
            result.summary_values,
            {
                "success_count": 2,
                "failure_count": 1,
                "failures": "pending: Translation failed",
            },
        )

    def test_export_all_shows_one_success_dialog(self) -> None:
        frame = self._make_frame()
        written: list[str] = []

        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
            written.append(destination_path.name)

        frame._write_export_document = write_export_document
        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))

        documents = [
            Document("alpha", "text", "a"),
            Document("beta", "text", "b"),
        ]

        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())

        self.assertEqual(written, ["alpha.brl", "beta.brl"])
        frame._show_export_all_result.assert_called_once()
        result = frame._show_export_all_result.call_args.args[0]
        self.assertTrue(result.all_succeeded)

    def test_open_dual_view_creates_refreshes_and_shows_viewer(self) -> None:
        frame = self._make_frame()
        frame._dual_view_results_by_document["alpha"] = ("segment",)
        viewer = Mock()
        frame._create_dual_view_frame = Mock(return_value=viewer)
        frame._render_dual_view_for_open_document = Mock(return_value="<html>alpha</html>")
        viewer.IsIconized.return_value = False

        frame._show_dual_view()

        frame._create_dual_view_frame.assert_called_once_with()
        viewer.refresh_html.assert_called_once_with("<html>alpha</html>")
        viewer.Show.assert_called_once_with()
        viewer.Raise.assert_called_once_with()

    def test_open_existing_dual_view_reuses_and_refreshes_it(self) -> None:
        frame = self._make_frame()
        viewer = Mock()
        frame._dual_view_frame = viewer
        frame._render_dual_view_for_open_document = Mock(return_value="<html>new</html>")
        viewer.IsIconized.return_value = False

        frame._show_dual_view()

        viewer.refresh_html.assert_called_once_with("<html>new</html>")
        viewer.Show.assert_called_once_with()
        viewer.Raise.assert_called_once_with()

    def test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer(self) -> None:
        frame = self._make_frame()
        policy = gui.ConversionCompletionPolicy(show_success=False)
        frame._dual_view_frame = Mock()
        frame._refresh_dual_view = Mock()
        conversion_output = gui.ConversionOutput("braille", ("segment",))

        with patch.object(gui.wx, "MessageBox"):
            frame._finish_conversion_success(
                gui.ConversionJobSuccess(
                    job_id=1,
                    conversion_output=conversion_output,
                    completion_policy=policy,
                )
            )

        self.assertEqual(frame._dual_view_results_by_document["alpha"], ("segment",))
        frame._refresh_dual_view.assert_called_once_with()

    def test_export_conversion_does_not_replace_dual_view_cache(self) -> None:
        frame = self._make_frame()
        policy = gui.ConversionCompletionPolicy(update_output=False)
        frame._dual_view_results_by_document["alpha"] = ("manual",)
        conversion_output = gui.ConversionOutput("export", ("export-segment",))

        frame._finish_conversion_success(
            gui.ConversionJobSuccess(
                job_id=1,
                conversion_output=conversion_output,
                completion_policy=policy,
            )
        )

        self.assertEqual(frame._dual_view_results_by_document["alpha"], ("manual",))

    def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
        frame = self._make_frame()
        frame.documents = [Document("beta", "new text", "braille")]
        frame._dual_view_frame = Mock()
        frame._refresh_dual_view = Mock()
        frame._load_document_into_editors = Mock()
        frame._refresh_document_list = Mock()
        frame._update_window_title = Mock()

        frame._open_document_by_name("beta")

        frame._refresh_dual_view.assert_called_once_with()

    def test_open_document_moves_input_cursor_to_start(self) -> None:
        frame = self._make_frame()
        frame.documents = [Document("beta", "new text", "braille")]
        frame._refresh_dual_view = Mock()
        frame._refresh_document_list = Mock()
        frame._update_window_title = Mock()
        frame.input_txt = Mock()
        frame.output_txt = Mock()

        frame._open_document_by_name("beta")

        frame.input_txt.SetInsertionPoint.assert_called_once_with(0)
        frame.input_txt.ShowPosition.assert_called_once_with(0)

    def test_char_hook_cycles_forward_to_first_document_from_last(self) -> None:
        frame = self._make_frame()
        frame.documents = [
            Document("alpha", "a", "1"),
            Document("beta", "b", "2"),
            Document("zoo", "z", "3"),
        ]
        frame._open_document_name = "zoo"
        frame._selected_document_name = "zoo"
        frame._save_open_document_with_feedback = Mock(return_value=True)
        frame._open_document_by_name = Mock()
        event = Mock()
        event.GetKeyCode.return_value = 9
        event.ControlDown.return_value = True
        event.ShiftDown.return_value = False

        frame.on_char_hook(event)

        frame._open_document_by_name.assert_called_once_with("alpha")
        event.Skip.assert_not_called()

    def test_char_hook_cycles_backward_to_last_document_from_first(self) -> None:
        frame = self._make_frame()
        frame.documents = [
            Document("alpha", "a", "1"),
            Document("beta", "b", "2"),
            Document("zoo", "z", "3"),
        ]
        frame._open_document_name = "alpha"
        frame._selected_document_name = "alpha"
        frame._save_open_document_with_feedback = Mock(return_value=True)
        frame._open_document_by_name = Mock()
        event = Mock()
        event.GetKeyCode.return_value = 366
        event.ControlDown.return_value = True
        event.ShiftDown.return_value = False

        frame.on_char_hook(event)

        frame._open_document_by_name.assert_called_once_with("zoo")
        event.Skip.assert_not_called()

    def test_activate_raises_visible_non_iconized_viewer_without_taking_focus(self) -> None:
        frame = self._make_frame()
        frame._dual_view_frame = Mock()
        frame._dual_view_frame.IsShown.return_value = True
        frame._dual_view_frame.IsIconized.return_value = False
        event = Mock()
        event.GetActive.return_value = True

        frame.on_frame_activate(event)

        frame._dual_view_frame.raise_without_activating.assert_called_once_with()
        frame._dual_view_frame.Raise.assert_not_called()
        event.Skip.assert_called_once_with()

    def test_rename_and_delete_keep_alignment_cache_consistent(self) -> None:
        frame = self._make_frame()
        frame._dual_view_results_by_document = {"alpha": ("segment",)}

        frame._rename_dual_view_result("alpha", "renamed")
        frame._delete_dual_view_result("renamed")

        self.assertEqual(frame._dual_view_results_by_document, {})

    def test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer(self) -> None:
        frame = self._make_frame()
        frame.documents = [
            Document("alpha", "text-a", "braille-a"),
            Document("beta", "text-b", "braille-b"),
        ]
        frame.workspace_dir = Path("/workspace")
        frame._dual_view_results_by_document = {
            "alpha": ("stale-alpha",),
            "beta": ("fresh-beta",),
            "ghost": ("stale-ghost",),
        }
        frame._save_open_document_with_feedback = Mock(return_value=True)
        frame._show_file_error = Mock()
        frame._refresh_document_list = Mock()
        frame._review_invalid_workspace_files = Mock()
        frame._open_document_by_name = Mock()
        frame._clear_document_editors = Mock()
        frame._refresh_dual_view = Mock()

        alpha_path = Mock()
        alpha_path.exists.return_value = True
        alpha_path.unlink.return_value = None
        beta_path = Mock()
        beta_path.exists.return_value = True
        beta_path.unlink.side_effect = OSError("unlink failed")

        with (
            patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES),
            patch.object(gui, "document_package_path_for_name", side_effect=[alpha_path, beta_path]),
            patch.object(gui, "load_workspace_documents", return_value=([Document("beta", "reloaded", "braille-b")], [])),
        ):
            frame.on_delete_all_documents(None)

        self.assertEqual(frame._dual_view_results_by_document, {"beta": ("fresh-beta",)})
        frame._refresh_dual_view.assert_called_once_with()
        frame._open_document_by_name.assert_called_once_with("beta")

    def test_export_all_shows_one_partial_failure_dialog_with_names(self) -> None:
        frame = self._make_frame()
        written: list[str] = []

        def write_export_document(destination_path: Path, document: Document, format_key: str) -> None:
            if document.name == "write-fail":
                raise OSError("disk full")
            written.append(destination_path.name)

        def start_export_conversion(document: Document, destination_path: Path, format_key: str, *, on_success=None, on_error=None, on_missing_table=None):
            if document.name == "convert-fail":
                on_error("Translation failed")
            else:
                on_success("converted-braille")
            return True

        frame._write_export_document = write_export_document
        frame._start_export_conversion = start_export_conversion

        documents = [
            Document("alpha", "text", "a"),
            Document("convert-fail", "text", None),
            Document("write-fail", "text", "w"),
        ]

        with patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)):
            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())

        self.assertEqual(written, ["alpha.brl"])
        frame._show_export_all_result.assert_called_once()
        result = frame._show_export_all_result.call_args.args[0]
        self.assertFalse(result.all_succeeded)
        self.assertEqual(
            result.summary_values,
            {
                "success_count": 1,
                "failure_count": 2,
                "failures": "convert-fail: Translation failed\nwrite-fail: disk full",
            },
        )

    def test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = Mock()
        frame._write_export_document = Mock()
        missing_table_message = gui._("Please select a translation table first.")

        documents = [
            Document("alpha", "text", None),
            Document("beta", "text", None),
        ]

        with (
            patch.dict(gui.language_map_translate_table, {"default": ""}, clear=True),
            patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            frame._export_next_document(documents, Path("/tmp/export"), "brl", ExportBatchResult())

        frame._write_export_document.assert_not_called()
        message_box.assert_not_called()
        frame._show_export_all_result.assert_called_once()
        result = frame._show_export_all_result.call_args.args[0]
        self.assertFalse(result.all_succeeded)
        self.assertEqual(
            result.summary_values,
            {
                "success_count": 0,
                "failure_count": 2,
                "failures": f"alpha: {missing_table_message}\nbeta: {missing_table_message}",
            },
        )

    def test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = Mock()
        frame._write_export_document = Mock()

        class _AcceptedFileDialog:
            def __init__(self, *_args, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK

            def GetPath(self):
                return "/tmp/exported"

        with (
            patch.dict(gui.language_map_translate_table, {"default": ""}, clear=True),
            patch.object(gui.wx, "FileDialog", _AcceptedFileDialog),
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            frame._export_document_with_dialog(Document("alpha", "text", None), "brl")

        frame._write_export_document.assert_not_called()
        message_box.assert_called_once_with(
            gui._("Please select a translation table first."),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )

    def test_apply_settings_from_dialog_updates_all_live_state(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame._dictionary_names = ["default", "math"]
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        snapshot = make_snapshot(
            translation=TranslationSettings("ascii", 52, "math"),
            tables={"default": "en-ueb-g1.ctb", "math": "Nemeth"},
            view=ViewSettings(18, "dark", "default"),
        )

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            result = frame.apply_settings_from_dialog(snapshot)

        self.assertEqual(frame.translation_settings, snapshot.translation)
        self.assertEqual(frame.view_settings, snapshot.view)
        self.assertEqual(gui.language_map_translate_table, snapshot.translation_tables)
        frame._apply_editor_view_settings.assert_called_once_with(snapshot.view)
        self.assertEqual(result, snapshot)

    def test_open_settings_uses_singleton_dialog(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.get_settings_snapshot = Mock(return_value=make_snapshot())
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.apply_settings_from_dialog = Mock()

        with patch.object(gui.DotExpressSettingsDialog, "show_singleton") as show:
            frame.on_open_settings(None)

        show.assert_called_once()
        self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)


if __name__ == "__main__":
    unittest.main()
