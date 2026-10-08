from __future__ import annotations

import importlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from tests import wx_stub

_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view"),
)
with _SCOPE.loading():
    gui = importlib.import_module("gui")
    from settings.dialogs import TranslationSettingsPanel

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

from documents.workspace import Document
from documents.export_results import ExportBatchResult
from settings.state import DotExpressSettingsSnapshot
from settings.translation import TranslationSettings
from settings.view import ViewSettings
from documents.formats import get_format


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
        frame._documents_by_name = {"alpha": Document("alpha", "source", None)}
        frame._get_document_by_name = lambda name: frame._documents_by_name.get(name)
        frame._replace_document = lambda document: frame._documents_by_name.__setitem__(document.name, document)
        frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
        return frame

    def test_write_export_document_uses_registry_writer(self) -> None:
        frame = self._make_frame()
        document = Document("alpha", "text", "braille")
        writer = Mock()
        descriptor = replace(get_format("dep"), writer=writer)

        with patch.object(gui, "get_format", return_value=descriptor) as get_format_mock:
            frame._write_export_document(Path("/tmp/custom.dep"), document, "dep")

        get_format_mock.assert_called_once_with("dep")
        writer.assert_called_once_with(Path("/tmp/custom.dep"), document)

    def test_write_html_export_document_passes_cached_dual_view_results(self) -> None:
        frame = self._make_frame()
        document = Document("alpha", "text", "braille")
        cached_results = (Mock(),)
        frame._dual_view_results_by_document["alpha"] = cached_results
        writer = Mock()
        descriptor = replace(get_format("html"), writer=writer)

        with patch.object(gui, "get_format", return_value=descriptor):
            frame._write_export_document(Path("/tmp/custom.html"), document, "html")

        writer.assert_called_once_with(
            Path("/tmp/custom.html"),
            document,
            dual_view_results=cached_results,
        )

    def test_write_export_document_rejects_non_exportable_format(self) -> None:
        frame = self._make_frame()
        document = Document("alpha", "text", "braille")
        descriptor = replace(get_format("txt"), writer=Mock())

        with patch.object(gui, "get_format", return_value=descriptor):
            with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
                frame._write_export_document(Path("/tmp/custom.txt"), document, "txt")

    def test_export_next_document_uses_registry_extension(self) -> None:
        frame = self._make_frame()
        written: list[Path] = []
        document = Document("alpha", "text", "braille")
        descriptor = replace(get_format("brl"), extension=".braille")

        def write_export_document(destination_path: Path, export_document: Document, format_key: str) -> None:
            written.append(destination_path)

        frame._write_export_document = write_export_document
        frame._start_export_conversion = Mock(side_effect=AssertionError("conversion should not run"))

        with (
            patch.object(gui, "get_format", return_value=descriptor) as get_format_mock,
            patch.object(gui.wx, "CallAfter", side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs)),
        ):
            frame._export_next_document([document], Path("/tmp/export"), "brl", ExportBatchResult())

        self.assertEqual(written, [Path("/tmp/export/alpha.braille")])
        get_format_mock.assert_called_once_with("brl")

    def test_sync_document_menu_state_before_document_list_exists(self) -> None:
        frame = self._make_frame()
        menu_items = {
            "Open": Mock(),
            "Delete": Mock(),
            "Delete All": Mock(),
            "Add": Mock(),
            "Rename": Mock(),
            "Import": Mock(),
            "Export": Mock(),
            "Export All": Mock(),
        }

        frame._sync_document_menu_state(menu_items)

        self.assertNotIn("document_list", frame.__dict__)
        menu_items["Open"].Enable.assert_called_once_with(False)
        menu_items["Delete"].Enable.assert_called_once_with(False)
        menu_items["Delete All"].Enable.assert_called_once_with(False)
        menu_items["Add"].Enable.assert_called_once_with(True)
        menu_items["Rename"].Enable.assert_called_once_with(False)
        menu_items["Import"].Enable.assert_called_once_with(True)
        menu_items["Export"].Enable.assert_called_once_with(False)
        menu_items["Export All"].Enable.assert_called_once_with(False)

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

    def test_dual_view_menu_opens_rendered_html_with_main_window_size(self) -> None:
        frame = self._make_frame()
        frame.GetSize = Mock(return_value=(1024, 768))
        frame._render_dual_view_for_open_document = Mock(return_value="<html>dual</html>")
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        with (
            patch.object(gui, "write_dual_view_html", return_value=html_path) as write_html,
            patch.object(gui, "open_html_in_browser") as open_browser,
        ):
            frame.on_open_dual_view(None)

        write_html.assert_called_once_with("<html>dual</html>")
        open_browser.assert_called_once_with(html_path, (1024, 768))

    def test_dual_view_menu_reports_write_or_launch_failure(self) -> None:
        frame = self._make_frame()
        frame.GetSize = Mock(return_value=(900, 600))
        frame._render_dual_view_for_open_document = Mock(return_value="<html>dual</html>")
        frame._show_file_error = Mock()
        error = OSError("browser failed")

        with (
            patch.object(gui, "write_dual_view_html", side_effect=error),
            patch.object(gui.logger, "exception") as log_exception,
        ):
            frame.on_open_dual_view(None)

        log_exception.assert_called_once_with("Failed to open dual view")
        frame._show_file_error.assert_called_once_with(gui._("Failed to open dual view: {error}"), error)


class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
    def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.dictionary_dir = Path("dictionary")
        with patch.object(gui.TextProcessingDialog, "show_singleton") as show:
            frame.on_open_text_processing(None)
        show.assert_called_once_with(
            parent=frame,
            script_path=Path("dictionary/preprocessing.py"),
        )

    def test_open_text_processing_reports_read_error(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.dictionary_dir = Path("dictionary")
        with (
            patch.object(gui.TextProcessingDialog, "show_singleton", side_effect=OSError("denied")),
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            frame.on_open_text_processing(None)
        message_box.assert_called_once_with(
            gui._("Unable to open text processing script: {error}").format(error="denied"),
            gui._("Text Processing"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )

    def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
        runtime = Mock()
        frame = Mock()

        with (
            patch.object(
                gui,
                "prepare_application_directories",
                return_value=Mock(dual_view=Path("C:/DotExpress/dual_view")),
            ),
            patch.object(gui, "cleanup_dual_view_html"),
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertTrue(result)
        frame_class.assert_called_once_with(None, runtime=runtime)
        frame.Show.assert_called_once_with()

    def test_app_validates_application_data_before_building_runtime(self) -> None:
        runtime = Mock()
        frame = Mock()
        order: list[str] = []

        with (
            patch.object(
                gui,
                "prepare_application_directories",
                side_effect=lambda: (order.append("paths"), Mock(dual_view=Path("C:/DotExpress/dual_view")))[1],
            ),
            patch.object(gui, "cleanup_dual_view_html"),
            patch.object(gui, "build_default_translation_runtime", side_effect=lambda: (order.append("runtime"), runtime)[1]),
            patch.object(gui, "BrailleFrame", side_effect=lambda *args, **kwargs: (order.append("frame"), frame)[1]),
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertTrue(result)
        self.assertEqual(order, ["paths", "runtime", "frame"])

    def test_app_reports_unwritable_path_and_stops_before_runtime(self) -> None:
        error = gui.ApplicationDataError(Path("C:/Program Files/DotExpress/log"), PermissionError("denied"))

        with (
            patch.object(gui, "prepare_application_directories", side_effect=error),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "BrailleFrame") as frame_class,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertFalse(result)
        build_runtime.assert_not_called()
        frame_class.assert_not_called()
        message_box.assert_called_once_with(
            gui._(
                "DotExpress cannot write to its application data directory:\n"
                "{path}\n\nChoose a writable installation or execution location.\n\n{error}"
            ).format(path=error.path, error=error.cause),
            gui._("Startup Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
        )

    def test_app_exit_without_initialized_runtime_is_safe(self) -> None:
        app = gui.BrailleApp()
        app.translation_runtime = None

        with patch.object(gui, "cleanup_dual_view_html"):
            self.assertEqual(app.OnExit(), 0)

    def test_app_exit_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.translation_runtime = runtime

        with patch.object(gui, "cleanup_dual_view_html"):
            result = app.OnExit()

        self.assertEqual(result, 0)
        runtime.close.assert_called_once_with()

    def test_app_cleans_stale_dual_view_html_after_path_validation(self) -> None:
        paths = Mock()
        paths.dual_view = Path("C:/DotExpress/dual_view")
        runtime = Mock()
        frame = Mock()

        with (
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html") as cleanup,
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame),
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            self.assertTrue(app.OnInit())

        cleanup.assert_called_once_with(paths.dual_view)

    def test_app_reports_startup_cleanup_failure_before_runtime(self) -> None:
        paths = Mock()
        paths.dual_view = Path("C:/DotExpress/dual_view")
        cause = PermissionError("locked")

        with (
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertFalse(result)
        build_runtime.assert_not_called()
        self.assertIn(str(paths.dual_view), message_box.call_args.args[0])

    def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.translation_runtime = runtime
        error = OSError("locked")

        with (
            patch.object(gui, "cleanup_dual_view_html", side_effect=error),
            patch.object(gui.logger, "exception") as log_exception,
        ):
            result = app.OnExit()

        self.assertEqual(result, 0)
        log_exception.assert_called_once_with("Failed to clean up dual-view HTML")
        runtime.close.assert_called_once_with()

    def test_start_conversion_builds_request_and_starts_runner(self) -> None:
        frame = self._make_frame()
        frame._build_conversion_request = Mock(return_value=Mock())
        with patch.object(gui.wx, "CallLater", return_value=Mock()) as call_later:
            frame._start_conversion(
                "source",
                40,
                "unicode",
                Path("dictionary/default.csv"),
            )

        frame._build_conversion_request.assert_called_once_with(
            "source",
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
        frame.input_txt.GetValue.return_value = "source"
        policy = gui.ConversionCompletionPolicy()
        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._complete_conversion(policy, display_text="braille")

        frame.output_txt.SetValue.assert_called_once_with("braille")
        frame.output_txt.SetFocus.assert_called_once_with()
        self.assertEqual(frame._documents_by_name["alpha"].braille, "braille")
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

    def test_text_processing_failure_uses_its_own_message(self) -> None:
        frame = self._make_frame()
        result = gui.ConversionJobFailure(
            job_id=1,
            error=gui.ConversionStageError("text_processing", RuntimeError("script boom")),
            completion_policy=gui.ConversionCompletionPolicy(),
        )
        frame._complete_conversion = Mock()

        frame._finish_conversion_failure(result)

        frame._complete_conversion.assert_called_once_with(
            result.completion_policy,
            error_message=gui._("Text processing failed: {error}").format(error="script boom"),
        )

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

    def test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer(self) -> None:
        frame = self._make_frame()
        policy = gui.ConversionCompletionPolicy(show_success=False)
        frame._dual_view_frame = Mock()
        frame._refresh_dual_view = Mock()
        conversion_output = gui.ConversionOutput("braille", ("segment",), dual_view_segments=("segment",))

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

        frame.translation_tables = {"default": ""}
        with (
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

        frame.translation_tables = {"default": ""}
        with (
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
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        snapshot = make_snapshot(
            translation=TranslationSettings("ascii", 52, "math"),
            tables={"default": "en-ueb-g1.ctb", "math": "Nemeth"},
            view=ViewSettings(18, "dark", "default"),
        )
        previous_tables = {"default": "zh-tw.ctb"}
        frame.translation_tables = previous_tables

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            result = frame.apply_settings_from_dialog(snapshot)

        self.assertEqual(frame.translation_settings, snapshot.translation)
        self.assertEqual(frame.view_settings, snapshot.view)
        self.assertEqual(frame.translation_tables, snapshot.translation_tables)
        self.assertIsNot(frame.translation_tables, snapshot.translation_tables)
        self.assertIsNot(result.translation_tables, frame.translation_tables)
        self.assertEqual(previous_tables, {"default": "zh-tw.ctb"})
        frame._apply_editor_view_settings.assert_called_once_with(snapshot.view)
        self.assertEqual(result, snapshot)

    def _initialize_state_with_loaded_tables(self, loaded_tables: dict[str, str]):
        frame = object.__new__(gui.BrailleFrame)
        frame._register_output_font = Mock(return_value=False)
        with (
            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(
                gui,
                "load_translation_settings",
                return_value=TranslationSettings("unicode", 40, "default"),
            ),
            patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value=loaded_tables) as load_tables,
        ):
            frame._initialize_state()
        return frame, load_tables

    def test_initialize_state_loads_translation_tables_into_frame(self) -> None:
        loaded_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        frame, load_tables = self._initialize_state_with_loaded_tables(loaded_tables)

        self.assertEqual(frame.translation_tables, loaded_tables)
        load_tables.assert_called_once_with()

    def test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty(self) -> None:
        frame, _load_tables = self._initialize_state_with_loaded_tables({})

        self.assertEqual(frame.translation_tables, gui.DEFAULT_TRANSLATION_TABLES)
        self.assertIsNot(frame.translation_tables, gui.DEFAULT_TRANSLATION_TABLES)

    def test_settings_snapshot_reads_frame_translation_tables(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = TranslationSettings("unicode", 40, "default")
        frame.view_settings = ViewSettings(40, "light", "default")
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        snapshot = frame.get_settings_snapshot()

        self.assertEqual(
            snapshot.translation_tables,
            {"default": "test-default.ctb", "math": "test-math.ctb"},
        )
        self.assertIsNot(snapshot.translation_tables, frame.translation_tables)

    def test_conversion_request_copies_frame_translation_tables(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual(
            request.translation_tables,
            {"default": "test-default.ctb", "math": "test-math.ctb"},
        )
        self.assertIsNot(request.translation_tables, frame.translation_tables)

    def test_applied_settings_tables_reach_next_conversion_request(self) -> None:
        frame = self._make_frame()
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            frame.apply_settings_from_dialog(snapshot)
        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual(request.translation_tables, snapshot.translation_tables)

    def test_convert_without_default_table_shows_info_and_does_not_convert(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": ""}
        frame._start_conversion = Mock()

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.on_convert(None)

        message_box.assert_called_once_with(
            gui._("Please select a translation table first."),
            gui._("Info"),
            gui.wx.OK | gui.wx.ICON_INFORMATION,
            parent=frame,
        )
        frame._start_conversion.assert_not_called()

    def test_convert_with_default_table_starts_conversion_without_message(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        frame.translation_settings = TranslationSettings("ascii", 32, "default")
        frame.input_txt.GetValue.return_value = "source"
        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
        frame._start_conversion = Mock()

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.on_convert(None)

        frame._start_conversion.assert_called_once_with(
            "source",
            32,
            "ascii",
            Path("dictionary/default.csv"),
        )
        message_box.assert_not_called()

    def test_export_conversion_with_default_table_starts_background_conversion(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        frame.translation_settings = TranslationSettings("ascii", 32, "default")
        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
        frame._start_conversion = Mock()
        on_success = Mock()
        on_error = Mock()
        on_missing_table = Mock()

        started = frame._start_export_conversion(
            Document("alpha", "text", None),
            Path("/tmp/export/alpha.brl"),
            "brl",
            on_success=on_success,
            on_error=on_error,
            on_missing_table=on_missing_table,
        )

        self.assertTrue(started)
        frame._start_conversion.assert_called_once_with(
            "text",
            32,
            "ascii",
            Path("dictionary/default.csv"),
            on_success=on_success,
            on_error=on_error,
            update_output=False,
            show_success=False,
        )
        on_missing_table.assert_not_called()
        on_error.assert_not_called()

    def test_missing_default_table_message_reports_only_unset_default(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}

        self.assertIsNone(frame._missing_default_table_message())

        for tables in ({}, {"default": ""}, {"default": None}):
            with self.subTest(tables=tables):
                frame.translation_tables = tables
                self.assertEqual(
                    frame._missing_default_table_message(),
                    gui._("Please select a translation table first."),
                )

    def test_translation_tables_are_not_module_state(self) -> None:
        self.assertFalse(hasattr(gui, "language_map_translate_table"))

    def test_dead_frame_helpers_are_removed(self) -> None:
        for name in ("IMPORT_WILDCARDS", "TXT_WILDCARD", "PDF_WILDCARD", "DOCX_WILDCARD", "EPUB_WILDCARD"):
            with self.subTest(module_attribute=name):
                self.assertFalse(hasattr(gui, name))
        # Check the class, not a frame instance: the wx stub's __getattr__ makes
        # every missing instance attribute look present.
        for name in (
            "_create_labeled_group",
            "_get_import_wildcard",
            "_get_txt_wildcard",
            "_rename_dual_view_result",
            "_delete_dual_view_result",
        ):
            with self.subTest(frame_attribute=name):
                self.assertFalse(hasattr(gui.BrailleFrame, name))
        self.assertTrue(hasattr(gui, "DEP_WILDCARD"))
        self.assertTrue(hasattr(gui.BrailleFrame, "_get_brl_wildcard"))

    def test_save_open_document_saves_prepared_document(self) -> None:
        frame = self._make_frame()
        frame._documents_by_name = {"alpha": Document("alpha", "source", "old braille")}
        frame.workspace_dir = Path("workspace")
        frame.input_txt.GetValue.return_value = "edited"
        frame.output_txt.GetValue.return_value = "edited braille"

        with patch.object(gui, "save_document_package") as save_package:
            frame._save_open_document()

        expected = Document("alpha", "edited", "edited braille")
        self.assertEqual(frame._documents_by_name["alpha"], expected)
        save_package.assert_called_once_with(
            gui.document_package_path_for_name("alpha", Path("workspace")),
            expected,
        )

    def test_open_settings_uses_singleton_dialog(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.get_settings_snapshot = Mock(return_value=make_snapshot())
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.apply_settings_from_dialog = Mock()

        with patch.object(gui.DotExpressSettingsDialog, "show_singleton") as show:
            frame.on_open_settings(None)

        show.assert_called_once()
        self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)


class DictionaryManagementFrameTest(unittest.TestCase):
    def _make_frame(self, active: str = "default") -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame.translation_settings = TranslationSettings("unicode", 40, active)
        frame._dictionary_presenter = Mock()
        return frame

    def _open_management(self, frame, result, edit_name):
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "SpeechSymbolsDialog") as editor_class,
        ):
            dialog = dialog_class.return_value.__enter__.return_value
            dialog.ShowModal.return_value = result
            dialog.edit_dictionary_name = edit_name
            frame.on_open_dictionary_management(None)
        return dialog_class, editor_class

    def test_open_management_passes_presenter_and_refreshed_selection(self) -> None:
        frame = self._make_frame("alpha")
        presenter = frame._dictionary_presenter
        presenter.refresh.return_value = "alpha"

        dialog_class, editor_class = self._open_management(frame, gui.wx.ID_OK, None)

        presenter.refresh.assert_called_once_with("alpha")
        dialog_class.assert_called_once_with(frame, presenter, "alpha")
        dialog_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()
        editor_class.assert_not_called()

    def test_edit_result_opens_speech_symbols_for_presenter_path(self) -> None:
        frame = self._make_frame()
        presenter = frame._dictionary_presenter
        presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")

        _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha")

        presenter.dictionary_path.assert_called_once_with("alpha")
        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_other_results_open_no_editor(self) -> None:
        for result, edit_name in ((gui.wx.ID_OK, "alpha"), (gui.wx.ID_EDIT, None)):
            with self.subTest(result=result, edit_name=edit_name):
                frame = self._make_frame()

                _dialog_class, editor_class = self._open_management(frame, result, edit_name)

                editor_class.assert_not_called()
                frame._dictionary_presenter.dictionary_path.assert_not_called()

    def test_dictionary_names_for_dialog_refreshes_with_active_name(self) -> None:
        frame = self._make_frame("alpha")
        frame._dictionary_presenter.dictionary_names = ["alpha", "default"]

        names = frame.get_dictionary_names_for_dialog()

        self.assertEqual(names, ["alpha", "default"])
        frame._dictionary_presenter.refresh.assert_called_once_with("alpha")

    def test_initialize_state_wires_presenter_to_active_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dictionary_dir = Path(temp_dir)
            (dictionary_dir / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
            frame = object.__new__(gui.BrailleFrame)
            frame._register_output_font = Mock(return_value=False)
            with (
                patch.object(gui, "get_dictionary_directory", return_value=dictionary_dir),
                patch.object(
                    gui,
                    "load_translation_settings",
                    return_value=TranslationSettings("unicode", 40, "alpha"),
                ) as load_settings,
                patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
                patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
                patch.object(gui, "load_translation_tables", return_value={}),
            ):
                frame._initialize_state()
            presenter = frame._dictionary_presenter
            view = Mock()
            view.confirm.return_value = True

            with patch.object(gui, "set_selected_dictionary") as set_selected:
                selected = presenter.delete(view, "alpha")

            remaining = sorted(path.name for path in dictionary_dir.iterdir())

        self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
        self.assertEqual(presenter.dictionary_dir, dictionary_dir)
        load_settings.assert_called_once_with(["alpha", "default"])
        self.assertEqual(selected, "default")
        self.assertEqual(remaining, ["default.csv"])
        set_selected.assert_called_once_with("default")
        self.assertEqual(frame.translation_settings, TranslationSettings("unicode", 40, "default"))

    def test_frame_dictionary_callbacks_are_removed(self) -> None:
        # Check the class: the wx stub makes every missing instance attribute look present.
        for name in (
            "_refresh_dictionary_names",
            "add_dictionary",
            "delete_dictionary_from_dialog",
            "rename_dictionary_from_dialog",
            "import_dictionary_from_dialog",
            "export_dictionary_from_dialog",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(gui.BrailleFrame, name))
        self.assertTrue(hasattr(gui.BrailleFrame, "_set_active_dictionary"))
        self.assertTrue(hasattr(gui.BrailleFrame, "get_dictionary_names_for_dialog"))

    def test_dictionary_dialog_helpers_and_imports_are_removed_from_gui(self) -> None:
        for name in (
            "_prompt_for_dictionary_name",
            "CSV_WILDCARD",
            "DictionaryNameDialog",
            "create_dictionary",
            "delete_dictionary",
            "ensure_default_dictionary",
            "export_dictionary",
            "import_dictionary",
            "is_default_dictionary",
            "list_dictionary_names",
            "plan_dictionary_state_after_add",
            "plan_dictionary_state_after_delete",
            "plan_dictionary_state_after_rename",
            "prompt_dictionary_name_until_success",
            "rename_dictionary_after_name_prompt",
            "resolve_management_selection",
        ):
            with self.subTest(module_attribute=name):
                self.assertFalse(hasattr(gui, name))
        self.assertFalse(hasattr(gui.BrailleFrame, "_get_csv_wildcard"))
        for name in ("dictionary_path_for_name", "get_dictionary_directory", "DictionaryManagementDialog", "SpeechSymbolsDialog"):
            with self.subTest(kept=name):
                self.assertTrue(hasattr(gui, name))
        for name in ("_get_selected_dictionary_path", "_show_file_error"):
            with self.subTest(kept=name):
                self.assertTrue(hasattr(gui.BrailleFrame, name))


if __name__ == "__main__":
    unittest.main()
