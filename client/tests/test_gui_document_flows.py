from __future__ import annotations

import errno
import importlib
import inspect
import json
import os
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, DEFAULT, Mock, call, patch

from tests import wx_stub
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.full_disk import full_disk
from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
from tests.windows_file_handles import make_read_only

_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view", "ui.message_box"),
)
with _SCOPE.loading():
    gui = importlib.import_module("gui")
    from settings.dialogs import TranslationSettingsPanel


def setUpModule() -> None:
    _SCOPE.activate()
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


tearDownModule = _SCOPE.deactivate

import app_paths
import config
import i18n
from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from documents.export_results import ExportBatchResult
from settings.state import DotExpressSettingsSnapshot
from settings.translation import TranslationSettings
from settings.view import ViewSettings
from conversion.math_service import latex_to_mathml
from conversion.output import DualViewSegment
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from dictionaries.read_problems import describe_unreadable_dictionary
from tests.unreadable_dictionary_files import big5_decode_error

# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
    """Application paths under ``root``, with the given folders replaced (P2-6)."""
    return replace(app_paths.build_application_paths(root), **folders)


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


def text_file_bytes(text: str) -> bytes:
    """Bytes ``Path.write_text(text, encoding="utf-8")`` writes: newlines become ``os.linesep`` (W-2)."""
    return text.replace("\n", os.linesep).encode("utf-8")


class GuiDocumentFlowsTest(unittest.TestCase):
    def _make_frame(self, documents=(Document("alpha", "source", None),), open_name="alpha") -> gui.BrailleFrame:
        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
        frame.translation_runtime = Mock()
        frame._paths = make_paths()
        frame._config_store = Mock(spec=gui.ConfigStore)
        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
        frame._conversion_presenter.is_running.return_value = False
        frame._convert_dialog = Mock()
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._export_coordinator = Mock(spec=gui.ExportCoordinator)
        frame._dual_view_frame = None
        frame._document_controller = DocumentController(documents=list(documents), open_name=open_name)
        frame._workspace_service = DocumentWorkspaceService(frame._document_controller, Path("unused-workspace"))
        frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
        return frame

    def test_sync_document_menu_state_before_document_list_exists(self) -> None:
        frame = self._make_frame(documents=())
        menu_items = {
            "open": Mock(),
            "delete": Mock(),
            "delete_all": Mock(),
            "add": Mock(),
            "rename": Mock(),
            "import": Mock(),
            "export": Mock(),
            "export_all": Mock(),
        }

        frame._sync_document_menu_state(menu_items)

        self.assertNotIn("document_list", frame.__dict__)
        menu_items["open"].Enable.assert_called_once_with(False)
        menu_items["delete"].Enable.assert_called_once_with(False)
        menu_items["delete_all"].Enable.assert_called_once_with(False)
        menu_items["add"].Enable.assert_called_once_with(True)
        menu_items["rename"].Enable.assert_called_once_with(False)
        menu_items["import"].Enable.assert_called_once_with(True)
        menu_items["export"].Enable.assert_called_once_with(False)
        menu_items["export_all"].Enable.assert_called_once_with(False)

    def test_open_dual_view_creates_refreshes_and_shows_viewer(self) -> None:
        frame = self._make_frame()
        frame._document_controller.set_dual_view_results("alpha", ("segment",))
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

        write_html.assert_called_once_with("<html>dual</html>", frame._paths.dual_view)
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


class DocumentControllerOwnershipTest(unittest.TestCase):
    STARTUP_STEPS = (
        "_initialize_state",
        "_create_main_layout",
        "_initialize_conversion_state",
        "_apply_initial_settings",
        "_bind_events",
        "_load_startup_documents",
    )

    def test_frame_creates_its_controller_before_building_the_menu_bar(self) -> None:
        seen = []

        def initialize_frame(frame) -> None:
            seen.append(frame.__dict__.get("_document_controller"))

        with (
            patch.object(gui.BrailleFrame, "_initialize_frame", autospec=True, side_effect=initialize_frame),
            patch.multiple(gui.BrailleFrame, **{name: DEFAULT for name in self.STARTUP_STEPS}),
        ):
            frame = gui.BrailleFrame(None, runtime=Mock(), paths=make_paths(), config_store=Mock())

        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], gui.DocumentController)
        self.assertIs(frame._document_controller, seen[0])
        self.assertEqual(seen[0].documents, [])

    def test_initialize_state_keeps_the_frame_controller(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        controller = DocumentController(documents=[Document("alpha", "a", "1")], open_name="alpha")
        frame._document_controller = controller
        frame._register_output_font = Mock(return_value=False)
        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
        frame._config_store = Mock(spec=gui.ConfigStore)
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value={}),
        ):
            frame._initialize_state()

        self.assertIs(frame._document_controller, controller)
        self.assertEqual(controller.document_names, ["alpha"])
        self.assertEqual(controller.open_document_name, "alpha")

    def test_frame_requires_paths_and_config_store(self) -> None:
        parameters = inspect.signature(gui.BrailleFrame.__init__).parameters

        for name in ("runtime", "paths", "config_store"):
            with self.subTest(name=name):
                self.assertIn(name, parameters)
                self.assertIs(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)
                self.assertIs(parameters[name].default, inspect.Parameter.empty)


class FrameWorkspaceServiceDelegationTest(unittest.TestCase):
    """The frame hands workspace IO to its service and keeps the dialogs and UI updates."""

    UI_STEPS = (
        "_refresh_document_list",
        "_open_document_by_name",
        "_update_window_title",
        "_refresh_dual_view",
        "_clear_document_editors",
        "_ensure_open_document_exists",
        "_review_invalid_workspace_files",
        "_show_file_issues_dialog",
    )

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace = Path(temp_dir.name)

    def _make_frame(self, documents=(), open_name=None, selected_name=None) -> gui.BrailleFrame:
        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
        frame._document_controller = DocumentController(
            documents=list(documents),
            open_name=open_name,
            selected_name=selected_name,
        )
        frame._workspace_service = Mock()
        frame._workspace_service.workspace_dir = self.workspace
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
        frame._save_open_document_with_feedback = Mock(return_value=True)
        frame.ui = Mock()
        for name in self.UI_STEPS:
            setattr(frame, name, getattr(frame.ui, name))
        return frame

    def test_initialize_state_creates_service_for_frame_controller(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame._document_controller = DocumentController()
        frame._register_output_font = Mock(return_value=False)
        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=self.workspace)
        frame._config_store = Mock(spec=gui.ConfigStore)
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value={}),
        ):
            frame._initialize_state()

        service = frame._workspace_service
        self.assertEqual(service.workspace_dir, self.workspace)
        service.create_document(Document("beta", "", ""))
        self.assertEqual(frame._document_controller.document_names, ["beta"])
        self.assertTrue((self.workspace / "beta.dep").is_file())

    def test_startup_loads_through_service_and_reviews_returned_paths(self) -> None:
        frame = self._make_frame()
        invalid_paths = [self.workspace / "bad.dep"]
        frame._workspace_service.load_documents.return_value = invalid_paths

        frame._load_workspace_documents_at_startup()

        frame._workspace_service.load_documents.assert_called_once_with()
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._refresh_document_list(),
                call._review_invalid_workspace_files(invalid_paths),
                call._ensure_open_document_exists(),
                call._update_window_title(),
            ],
        )

    def test_save_open_document_passes_editor_text_to_service(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha")
        frame.input_txt.GetValue.return_value = "edited"
        frame.output_txt.GetValue.return_value = "edited braille"

        frame._save_open_document()

        frame._workspace_service.save_open_document.assert_called_once_with(text="edited", braille="edited braille")

    def test_create_document_adds_through_service_then_opens_it(self) -> None:
        frame = self._make_frame()

        self.assertTrue(frame._create_document("beta", focus_input=True))

        frame._workspace_service.create_document.assert_called_once_with(Document("beta", "", ""))
        self.assertEqual(
            frame.ui.mock_calls,
            [call._refresh_document_list("beta"), call._open_document_by_name("beta")],
        )
        frame.input_txt.SetFocus.assert_called_once_with()

    def test_create_document_failure_shows_error_and_stops(self) -> None:
        frame = self._make_frame()
        error = OSError("disk full")
        frame._workspace_service.create_document.side_effect = error

        self.assertFalse(frame._create_document("beta"))

        frame._show_file_error.assert_called_once_with(gui._("Failed to save document: {error}"), error)
        self.assertEqual(frame.ui.mock_calls, [])

    def test_invalid_file_review_deletes_through_service_and_reports_errors(self) -> None:
        frame = self._make_frame()
        invalid_paths = [self.workspace / "bad.dep", self.workspace / "worse.dep"]
        error = OSError("locked")
        frame._workspace_service.delete_invalid_files.side_effect = lambda paths, on_error: on_error(error)
        dialog = Mock()
        dialog.__enter__ = Mock(return_value=dialog)
        dialog.__exit__ = Mock(return_value=False)
        dialog.should_delete_invalid_files.return_value = True

        with patch.object(gui, "InvalidWorkspaceFilesDialog", Mock(return_value=dialog)) as dialog_class:
            gui.BrailleFrame._review_invalid_workspace_files(frame, invalid_paths)

        dialog_class.assert_called_once_with(frame, invalid_paths)
        frame._workspace_service.delete_invalid_files.assert_called_once_with(invalid_paths, on_error=ANY)
        frame._show_file_error.assert_called_once_with(gui._("Failed to delete invalid workspace file: {error}"), error)

    def test_import_hands_chosen_files_to_service_and_shows_its_result(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha")
        issue = BatchIssue(path=Path("x.txt"), reason="bad")
        frame._workspace_service.import_files.return_value = ImportResult(
            saved=[Document("beta", "b", None)],
            issues=[issue],
        )
        dialog = Mock()
        dialog.__enter__ = Mock(return_value=dialog)
        dialog.__exit__ = Mock(return_value=False)
        dialog.ShowModal.return_value = gui.wx.ID_OK
        dialog.GetFilterIndex.return_value = gui.ALL_SUPPORTED_FILTER_INDEX
        dialog.GetPaths.return_value = [str(self.workspace / "beta.txt")]

        with patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)):
            frame.on_import_document(None)

        frame._workspace_service.import_files.assert_called_once_with(
            [self.workspace / "beta.txt"],
            format_key=gui.get_import_filters()[gui.ALL_SUPPORTED_FILTER_INDEX].key,
        )
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._open_document_by_name("beta"),
                call._show_file_issues_dialog(
                    gui._("Import Issues"),
                    gui._("Some files were skipped during import."),
                    [issue],
                ),
            ],
        )

    def _patch_name_dialog(self, name: str):
        dialog = Mock()
        dialog.__enter__ = Mock(return_value=dialog)
        dialog.__exit__ = Mock(return_value=False)
        dialog.ShowModal.return_value = gui.wx.ID_OK
        dialog.get_document_name.return_value = name
        return patch.object(gui, "DocumentNameDialog", Mock(return_value=dialog))

    def test_rename_goes_through_service_then_refreshes(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        frame._workspace_service.rename_document.return_value = Document("gamma", "a", "1")

        with self._patch_name_dialog("gamma"):
            frame.on_rename_document(None)

        frame._workspace_service.rename_document.assert_called_once_with("alpha", "gamma")
        self.assertEqual(
            frame.ui.mock_calls,
            [call._refresh_document_list("gamma"), call._update_window_title(), call._refresh_dual_view()],
        )
        frame._show_file_error.assert_not_called()

    def test_rename_failure_from_service_shows_save_error(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        error = OSError("locked")
        frame._workspace_service.rename_document.side_effect = error

        with self._patch_name_dialog("gamma"):
            frame.on_rename_document(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to save document: {error}"), error)
        self.assertEqual(frame.ui.mock_calls, [])

    def test_delete_goes_through_service_then_refreshes(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
        frame._workspace_service.delete_document.side_effect = frame._document_controller.delete_document

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._workspace_service.delete_document.assert_called_once_with("beta")
        self.assertEqual(frame.ui.mock_calls, [call._refresh_document_list("alpha"), call._refresh_dual_view()])
        frame._show_file_error.assert_not_called()

    def test_delete_failure_from_service_shows_delete_error(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
        error = OSError("locked")
        frame._workspace_service.delete_document.side_effect = error

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        self.assertEqual(frame.ui.mock_calls, [])
        self.assertEqual(frame._document_controller.documents, documents)

    def test_delete_all_success_goes_through_service(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        controller = frame._document_controller

        def delete_all_documents(*, on_error):
            controller.delete_all_documents()
            return DeleteAllResult(completed=True, invalid_paths=[])

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._workspace_service.delete_all_documents.assert_called_once_with(on_error=ANY)
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._update_window_title(),
                call._refresh_document_list(),
                call._clear_document_editors(),
                call._ensure_open_document_exists(),
                call._refresh_dual_view(),
            ],
        )

    def test_delete_all_failure_reviews_paths_from_service(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        controller = frame._document_controller
        error = OSError("locked")
        invalid_paths = [self.workspace / "alpha.dep"]

        def delete_all_documents(*, on_error):
            on_error(error)
            controller.restore_documents_after_delete_all_failure([])
            return DeleteAllResult(completed=False, invalid_paths=invalid_paths)

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._refresh_document_list(),
                call._review_invalid_workspace_files(invalid_paths),
                call._clear_document_editors(),
                call._refresh_dual_view(),
            ],
        )


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
            patch.object(gui, "message_box") as message_box,
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
        paths = make_paths(Path("C:/DotExpress"))

        with (
            patch.object(gui, "build_application_paths", return_value=paths),
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html"),
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertTrue(result)
        frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=ANY)
        frame.Show.assert_called_once_with()

    def test_app_validates_application_data_before_building_runtime(self) -> None:
        runtime = Mock()
        frame = Mock()
        order: list[str] = []

        with (
            patch.object(gui, "build_application_paths", return_value=make_paths(Path("C:/DotExpress"))),
            patch.object(
                gui,
                "prepare_application_directories",
                side_effect=lambda paths: (order.append("paths"), paths)[1],
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
            patch.object(gui, "message_box") as message_box,
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
        app.paths = make_paths(Path("C:/DotExpress"))
        app.translation_runtime = None

        with patch.object(gui, "cleanup_dual_view_html"):
            self.assertEqual(app.OnExit(), 0)

    def test_app_exit_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.paths = make_paths(Path("C:/DotExpress"))
        app.translation_runtime = runtime

        with patch.object(gui, "cleanup_dual_view_html"):
            result = app.OnExit()

        self.assertEqual(result, 0)
        runtime.close.assert_called_once_with()

    def test_app_cleans_stale_dual_view_html_after_path_validation(self) -> None:
        paths = make_paths(Path("C:/DotExpress"))
        runtime = Mock()
        frame = Mock()

        with (
            patch.object(gui, "build_application_paths", return_value=paths),
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
        paths = make_paths(Path("C:/DotExpress"))
        cause = PermissionError("locked")

        with (
            patch.object(gui, "build_application_paths", return_value=paths),
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "message_box") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertFalse(result)
        build_runtime.assert_not_called()
        self.assertIn(str(paths.dual_view), message_box.call_args.args[0])

    def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.paths = make_paths(Path("C:/DotExpress"))
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

    def _startup_recorders(self, order: list, prepare_error: Exception | None = None) -> dict:
        """P2-6: recording fakes for every startup step; each accepts any arguments."""

        def prepare(*args, **kwargs):
            order.append("prepare")
            if prepare_error is not None:
                raise prepare_error
            return args[0] if args else Mock(dual_view=Path("C:/DotExpress/dual_view"))

        def record(step, result=None):
            def fake(*args, **kwargs):
                order.append(step)
                return result

            return fake

        frame = Mock()
        frame.Show.side_effect = record("show")
        return {
            "prepare_application_directories": prepare,
            "cleanup_dual_view_html": record("cleanup"),
            "build_default_translation_runtime": record("runtime", Mock()),
            "BrailleFrame": record("frame", frame),
            "start_client_init_background": record("client_init"),
        }

    def test_app_startup_runs_steps_in_contract_order(self) -> None:
        order: list[str] = []

        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertTrue(result)
        self.assertEqual(order, ["prepare", "cleanup", "runtime", "frame", "show", "client_init"])
        message_box.assert_not_called()

    def test_app_stops_before_cleanup_when_validation_fails(self) -> None:
        order: list[str] = []
        error = gui.ApplicationDataError(Path("C:/Program Files/DotExpress/dictionary"), PermissionError("denied"))

        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order, prepare_error=error).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertFalse(result)
        self.assertEqual(order, ["prepare"])
        message_box.assert_called_once()
        self.assertIn(str(error.path), message_box.call_args.args[0])

    def test_app_passes_the_validated_paths_and_one_store(self) -> None:
        paths = make_paths(Path("C:/DotExpress"))
        runtime = Mock()
        frame = Mock()
        order: list[str] = []
        stores: list = []
        store_class = gui.ConfigStore

        def build_store(path):
            order.append("store")
            stores.append(store_class(path))
            return stores[-1]

        with (
            patch.object(gui, "build_application_paths", return_value=paths) as build_paths,
            patch.object(
                gui,
                "prepare_application_directories",
                side_effect=lambda validated: (order.append("prepare"), validated)[1],
            ) as prepare,
            patch.object(gui, "cleanup_dual_view_html", side_effect=lambda folder: order.append("cleanup")) as cleanup,
            patch.object(gui, "ConfigStore", side_effect=build_store),
            patch.object(
                gui,
                "build_default_translation_runtime",
                side_effect=lambda: (order.append("runtime"), runtime)[1],
            ),
            patch.object(gui, "BrailleFrame", return_value=frame) as frame_class,
            patch.object(gui, "start_client_init_background") as start_client_init,
        ):
            app = gui.BrailleApp()
            self.assertTrue(app.OnInit())

        build_paths.assert_called_once_with()
        self.assertIs(prepare.call_args.args[0], paths)
        self.assertIs(app.paths, paths)
        cleanup.assert_called_once_with(paths.dual_view)
        self.assertEqual(order, ["prepare", "cleanup", "store", "runtime"])
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0].path, paths.config)
        frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=stores[0])
        self.assertIs(frame_class.call_args.kwargs["paths"], paths)
        start_client_init.assert_called_once_with(stores[0])

    def test_app_exit_cleans_the_validated_dual_view_folder(self) -> None:
        app = gui.BrailleApp()
        app.paths = make_paths(Path("C:/DotExpress"))
        app.translation_runtime = Mock()

        with patch.object(gui, "cleanup_dual_view_html") as cleanup:
            self.assertEqual(app.OnExit(), 0)

        cleanup.assert_called_once_with(Path("C:/DotExpress/dual_view"))
        app.translation_runtime.close.assert_called_once_with()

    def test_open_document_refreshes_viewer_but_text_edit_does_not(self) -> None:
        frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
        frame._dual_view_frame = Mock()
        frame._refresh_dual_view = Mock()
        frame._load_document_into_editors = Mock()
        frame._refresh_document_list = Mock()
        frame._update_window_title = Mock()

        frame._open_document_by_name("beta")

        frame._refresh_dual_view.assert_called_once_with()

    def test_open_document_moves_input_cursor_to_start(self) -> None:
        frame = self._make_frame(documents=(Document("beta", "new text", "braille"),))
        frame._refresh_dual_view = Mock()
        frame._refresh_document_list = Mock()
        frame._update_window_title = Mock()
        frame.input_txt = Mock()
        frame.output_txt = Mock()

        frame._open_document_by_name("beta")

        frame.input_txt.SetInsertionPoint.assert_called_once_with(0)
        frame.input_txt.ShowPosition.assert_called_once_with(0)

    def test_char_hook_cycles_forward_to_first_document_from_last(self) -> None:
        frame = self._make_frame(
            documents=(
                Document("alpha", "a", "1"),
                Document("beta", "b", "2"),
                Document("zoo", "z", "3"),
            ),
            open_name="zoo",
        )
        frame._document_controller.select_document("zoo")
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
        frame = self._make_frame(
            documents=(
                Document("alpha", "a", "1"),
                Document("beta", "b", "2"),
                Document("zoo", "z", "3"),
            ),
            open_name="alpha",
        )
        frame._document_controller.select_document("alpha")
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
        frame = self._make_frame(
            documents=(
                Document("alpha", "text-a", "braille-a"),
                Document("beta", "text-b", "braille-b"),
            ),
        )
        frame._document_controller.set_dual_view_results("alpha", ("stale-alpha",))
        frame._document_controller.set_dual_view_results("beta", ("fresh-beta",))
        frame._document_controller.set_dual_view_results("ghost", ("stale-ghost",))
        frame._save_open_document_with_feedback = Mock(return_value=True)
        frame._show_file_error = Mock()
        frame._refresh_document_list = Mock()
        frame._review_invalid_workspace_files = Mock()
        frame._open_document_by_name = Mock()
        frame._clear_document_editors = Mock()
        frame._refresh_dual_view = Mock()
        error = OSError("unlink failed")
        controller = frame._document_controller

        def delete_all_documents(*, on_error):
            # Stub service: alpha's package is deleted, beta's unlink fails, the reload finds beta.
            on_error(error)
            controller.restore_documents_after_delete_all_failure([Document("beta", "reloaded", "braille-b")])
            return DeleteAllResult(completed=False, invalid_paths=[])

        frame._workspace_service = Mock()
        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        frame._review_invalid_workspace_files.assert_called_once_with([])
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": ("fresh-beta",)})
        frame._refresh_dual_view.assert_called_once_with()
        frame._open_document_by_name.assert_called_once_with("beta")

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
        frame._document_controller = DocumentController()
        frame._register_output_font = Mock(return_value=False)
        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
        frame._config_store = Mock(spec=gui.ConfigStore)
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(
                gui,
                "load_translation_settings",
                return_value=TranslationSettings("unicode", 40, "default"),
            ),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value=loaded_tables) as load_tables,
        ):
            frame._initialize_state()
        return frame, load_tables

    def test_initialize_state_loads_translation_tables_into_frame(self) -> None:
        loaded_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        frame, load_tables = self._initialize_state_with_loaded_tables(loaded_tables)

        self.assertEqual(frame.translation_tables, loaded_tables)
        load_tables.assert_called_once_with(frame._config_store)

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
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}

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
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual(request.translation_tables, snapshot.translation_tables)

    def test_conversion_request_reads_language_settings_per_request(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "test-default.ctb"}
        first_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
        second_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "ja"}

        frame._config_store.get_lang.side_effect = ["en", "zh_TW"]
        frame._config_store.get_charset_maps.side_effect = [first_maps, second_maps]

        first = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
        second = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual((first.lang, first.charset_maps), ("en", first_maps))
        self.assertEqual((second.lang, second.charset_maps), ("zh_TW", second_maps))
        self.assertEqual(frame._config_store.get_lang.call_count, 2)
        self.assertEqual(frame._config_store.get_charset_maps.call_count, 2)

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

    def test_save_open_document_saves_prepared_document(self) -> None:
        frame = self._make_frame(documents=(Document("alpha", "source", "old braille"),))
        frame.input_txt.GetValue.return_value = "edited"
        frame.output_txt.GetValue.return_value = "edited braille"

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            frame._workspace_service = DocumentWorkspaceService(frame._document_controller, workspace)
            frame._save_open_document()
            saved = load_document_package(workspace / "alpha.dep")

        expected = Document("alpha", "edited", "edited braille")
        self.assertEqual(frame._document_controller.get_document("alpha"), expected)
        self.assertEqual(saved, expected)

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

    def _open_management(self, frame, result, edit_name, editor_error=None):
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "DictionaryEntriesDialog", side_effect=editor_error) as editor_class,
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

    def test_editor_that_cannot_read_its_dictionary_shows_the_reason(self) -> None:
        # F-6 (D6): the file went bad between the check in Dictionary Management and the editor.
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = big5_decode_error()

        with (
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [f'Cannot read dictionary "alpha.csv": UnicodeDecodeError: {error}'],
        )
        self.assertIsNone(logs.records[0].exc_info)

    def test_editor_failure_that_is_unexpected_is_logged_with_its_traceback(self) -> None:
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = RuntimeError("injected")

        with (
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ['Unexpected error while reading dictionary "alpha.csv"'],
        )
        self.assertIs(logs.records[0].exc_info[1], error)

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
            frame._document_controller = DocumentController()
            frame._register_output_font = Mock(return_value=False)
            frame._paths = make_paths(dictionary=dictionary_dir, workspace=Path("workspace"))
            frame._config_store = Mock(spec=gui.ConfigStore)
            with (
                patch.object(
                    gui,
                    "load_translation_settings",
                    return_value=TranslationSettings("unicode", 40, "alpha"),
                ) as load_settings,
                patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
                patch.object(gui, "load_translation_tables", return_value={}),
            ):
                frame._initialize_state()
            presenter = frame._dictionary_presenter
            view = Mock()
            view.confirm.return_value = True

            selected = presenter.delete(view, "alpha")

            remaining = sorted(path.name for path in dictionary_dir.iterdir())

        self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
        self.assertEqual(presenter.dictionary_dir, dictionary_dir)
        load_settings.assert_called_once_with(frame._config_store, ["alpha", "default"])
        self.assertEqual(selected, "default")
        self.assertEqual(remaining, ["default.csv"])
        frame._config_store.set_selected_dictionary.assert_called_once_with("default")
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
        for name in ("dictionary_path_for_name", "DictionaryManagementDialog", "DictionaryEntriesDialog"):
            with self.subTest(kept=name):
                self.assertTrue(hasattr(gui, name))
        for name in ("_get_selected_dictionary_path", "_show_file_error"):
            with self.subTest(kept=name):
                self.assertTrue(hasattr(gui.BrailleFrame, name))


class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
    """Pins today's menu and export behavior; must pass unchanged through P1-2."""

    _make_frame = GuiDocumentFlowsTest._make_frame

    DOCUMENT_HANDLER_NAMES = (
        "on_open_document",
        "on_delete_document",
        "on_delete_all_documents",
        "on_add_document",
        "on_rename_document",
        "on_import_document",
        "on_export_document",
        "on_export_all_documents",
    )

    def _make_menu_frame(self):
        frame = self._make_frame(documents=())
        frame.handler_calls = Mock()
        for name in self.DOCUMENT_HANDLER_NAMES:
            setattr(frame, name, getattr(frame.handler_calls, name))
        return frame

    def _patch_menus(self, recorder: MenuRecorder):
        return (
            patch.object(gui.wx, "Menu", recorder.new_menu),
            patch.object(gui.wx, "EVT_MENU", "EVT_MENU", create=True),
            patch.object(gui, "_", fake_translate),
        )

    def _make_export_frame(self):
        frame = self._make_frame()
        frame._export_coordinator = gui.ExportCoordinator(
            frame,
            frame._document_controller,
            frame._conversion_presenter,
            call_after=lambda fn, *args, **kwargs: fn(*args, **kwargs),
        )
        return frame

    def _select_first_of(self, frame, *names: str) -> None:
        frame._document_controller.load_documents([Document(name, "text", None) for name in names])
        frame.document_list = Mock()
        frame.document_list.GetFirstSelected.return_value = 0

    def test_file_menu_build_log(self) -> None:
        frame = self._make_menu_frame()
        recorder = MenuRecorder()
        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)

        with menu_patch, event_patch, translate_patch:
            menu, _items = frame._create_document_menu()

        self.assertIs(menu, recorder.menus[0])
        self.assertEqual(
            recorder.log,
            DOCUMENT_MENU_BUILD_LOG + enable_log(False, False, False, True, False, True, False, False),
        )

    def test_menu_handlers_dispatch_to_frame_methods(self) -> None:
        frame = self._make_menu_frame()
        recorder = MenuRecorder()
        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
        with menu_patch, event_patch, translate_patch:
            frame._create_document_menu()
        event = object()
        expected = [
            ("menu0:T[Open]", call.on_open_document(event)),
            ("menu0:T[Delete]", call.on_delete_document(event)),
            ("menu0:T[Delete All]", call.on_delete_all_documents(event)),
            ("menu0:T[Add]", call.on_add_document(event)),
            ("menu0:T[Rename]", call.on_rename_document(event)),
            ("menu0:T[Import]", call.on_import_document(event)),
            ("menu1:T[Package DEP]", call.on_export_document("dep")),
            ("menu1:T[Braille BRL]", call.on_export_document("brl")),
            ("menu1:T[Dual View HTML]", call.on_export_document("html")),
            ("menu2:T[Package DEP]", call.on_export_all_documents("dep")),
            ("menu2:T[Braille BRL]", call.on_export_all_documents("brl")),
            ("menu2:T[Dual View HTML]", call.on_export_all_documents("html")),
        ]

        self.assertEqual([item for _menu, item, _handler in recorder.binds], [item for item, _call in expected])
        for (menu_name, item_name, handler), (_item, expected_call) in zip(recorder.binds, expected):
            with self.subTest(item=item_name):
                frame.handler_calls.reset_mock()
                handler(event)
                self.assertEqual(menu_name, "menu0")
                self.assertEqual(frame.handler_calls.mock_calls, [expected_call])

    def test_menu_enabled_states_follow_selection_and_documents(self) -> None:
        frame = self._make_menu_frame()
        recorder = MenuRecorder()
        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
        with menu_patch, event_patch, translate_patch:
            _menu, items = frame._create_document_menu()
        frame._document_menu_items = items

        self.assertEqual(
            recorder.log[len(DOCUMENT_MENU_BUILD_LOG):],
            enable_log(False, False, False, True, False, True, False, False),
        )

        recorder.log.clear()
        self._select_first_of(frame, "alpha")
        frame._sync_document_menu_state()

        self.assertEqual(recorder.log, enable_log(True, True, True, True, True, True, True, True))

    def test_context_menu_on_item_selects_it_and_pops_up_below_it(self) -> None:
        frame = self._make_menu_frame()
        self._select_first_of(frame, "alpha")
        frame._document_controller.select_document(None)
        recorder = MenuRecorder()
        document_list = frame.document_list
        document_list.ScreenToClient.return_value = gui.wx.Point(5, 6)
        document_list.HitTest.return_value = (0, 0)
        document_list.GetItemRect.return_value = SimpleNamespace(x=10, y=20, height=5)
        document_list.GetItemCount.return_value = 1
        document_list.PopupMenu.side_effect = lambda menu, position: recorder.log.append(("PopupMenu", menu.name, position))
        event = Mock()
        event.GetPosition.return_value = gui.wx.Point(100, 200)
        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)

        with menu_patch, event_patch, translate_patch:
            frame.on_document_context_menu(event)

        self.assertEqual(
            recorder.log,
            DOCUMENT_MENU_BUILD_LOG
            + enable_log(True, True, True, True, True, True, True, True)
            + [("PopupMenu", "menu0", (10, 25)), ("menu0", "Destroy")],
        )
        document_list.ScreenToClient.assert_called_once_with(gui.wx.Point(100, 200))
        document_list.HitTest.assert_called_once_with(gui.wx.Point(5, 6))
        document_list.Select.assert_called_once_with(0)
        document_list.Focus.assert_called_once_with(0)
        self.assertEqual(frame._document_controller.selected_document_name, "alpha")

    def test_keyboard_context_menu_without_selection_clears_it(self) -> None:
        frame = self._make_menu_frame()
        self._select_first_of(frame, "alpha", "beta")
        frame._document_controller.select_document("alpha")
        frame._document_menu_items = {}
        recorder = MenuRecorder()
        document_list = frame.document_list
        document_list.GetFirstSelected.return_value = gui.wx.NOT_FOUND
        document_list.HitTest.return_value = (gui.wx.NOT_FOUND, 0)
        document_list.PopupMenu.side_effect = lambda menu, position: recorder.log.append(("PopupMenu", menu.name, position))
        event = Mock()
        event.GetPosition.return_value = gui.wx.DefaultPosition
        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)

        with menu_patch, event_patch, translate_patch:
            frame.on_document_context_menu(event)

        self.assertEqual(
            recorder.log,
            DOCUMENT_MENU_BUILD_LOG
            + enable_log(False, False, True, True, False, True, False, True)
            + [("PopupMenu", "menu0", (0, 0)), ("menu0", "Destroy")],
        )
        self.assertIsInstance(recorder.log[-2][2], gui.wx.Point)
        document_list.ScreenToClient.assert_not_called()
        document_list.Select.assert_not_called()
        document_list.GetItemRect.assert_not_called()
        self.assertIsNone(frame._document_controller.selected_document_name)

    def test_menu_bar_menus_items_and_handlers(self) -> None:
        frame = self._make_menu_frame()
        for name in (
            "on_convert",
            "on_open_dual_view",
            "on_open_text_processing",
            "on_open_dictionary_management",
            "on_open_settings",
            "on_open_coseeing_website",
            "on_about",
        ):
            setattr(frame, name, getattr(frame.handler_calls, name))
        recorder = MenuRecorder()
        frame.Bind = Mock(side_effect=lambda event, handler, item: recorder.log.append(("frame", "Bind", event, handler, item.name)))

        class RecordedMenuBar:
            def Append(self, menu, title):
                recorder.log.append(("menubar", "Append", menu.name, title))

        menu_patch, event_patch, translate_patch = self._patch_menus(recorder)
        with menu_patch, event_patch, translate_patch, patch.object(gui.wx, "MenuBar", RecordedMenuBar):
            menu_bar = frame._create_menu_bar()

        self.assertIsInstance(menu_bar, RecordedMenuBar)
        self.assertEqual(
            recorder.log,
            DOCUMENT_MENU_BUILD_LOG
            + enable_log(False, False, False, True, False, True, False, False)
            + [
                ("menubar", "Append", "menu0", "T[File]"),
                ("new", "menu3"),
                ("menu3", "Append", -1, "T[Convert]"),
                ("frame", "Bind", "EVT_MENU", frame.on_convert, "menu3:T[Convert]"),
                ("menu3", "Append", -1, "T[Dual View]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dual_view, "menu3:T[Dual View]"),
                ("menu3", "Append", -1, "T[Text Processing]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_text_processing, "menu3:T[Text Processing]"),
                ("menu3", "Append", -1, "T[Dictionary Management...]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dictionary_management, "menu3:T[Dictionary Management...]"),
                ("menu3", "Append", -1, "T[Settings]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_settings, "menu3:T[Settings]"),
                ("menubar", "Append", "menu3", "T[Translation]"),
                ("new", "menu4"),
                ("menu4", "Append", -1, "T[Coseeing Website]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_coseeing_website, "menu4:T[Coseeing Website]"),
                ("menu4", "Append", 1, "T[About]"),
                ("frame", "Bind", "EVT_MENU", frame.on_about, "menu4:T[About]"),
                ("menubar", "Append", "menu4", "T[Help]"),
            ],
        )

    def test_export_dialog_title_default_file_wildcard_and_style(self) -> None:
        dialogs = []

        class RecordedFileDialog:
            def __init__(self, *args, **kwargs):
                dialogs.append((args, kwargs))

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.CANCEL

        expected_wildcards = {
            "dep": "T[DotExpress files (*.dep)|*.dep]",
            "brl": "T[Braille files (*.brl)|*.brl]",
            "html": "T[HTML files (*.html)|*.html]",
        }
        for key, wildcard in expected_wildcards.items():
            with self.subTest(format_key=key):
                frame = self._make_export_frame()
                frame._export_coordinator.write_document = Mock()
                dialogs.clear()
                with patch.object(gui.wx, "FileDialog", RecordedFileDialog), patch.object(gui, "_", fake_translate):
                    frame._export_coordinator.export_document(Document("alpha", "t", "b"), key)

                self.assertEqual(
                    dialogs,
                    [
                        (
                            (frame, "T[Export Document]"),
                            {
                                "defaultFile": f"alpha.{key}",
                                "wildcard": wildcard,
                                "style": gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
                            },
                        )
                    ],
                )
                frame._export_coordinator.write_document.assert_not_called()
                frame._conversion_presenter.convert_for_export.assert_not_called()

    def test_export_dialog_corrects_only_a_wrong_extension(self) -> None:
        for chosen, written in (("/tmp/x/out.TXT", "/tmp/x/out.brl"), ("/tmp/x/out.BRL", "/tmp/x/out.BRL")):
            with self.subTest(chosen=chosen):
                frame = self._make_export_frame()
                frame._export_coordinator.write_document = Mock()
                dialog = Mock()
                dialog.__enter__ = Mock(return_value=dialog)
                dialog.__exit__ = Mock(return_value=False)
                dialog.ShowModal.return_value = gui.wx.ID_OK
                dialog.GetPath.return_value = chosen
                document = Document("alpha", "t", "b")
                with (
                    patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)),
                    patch.object(gui, "message_box", Mock()) as message_box,
                ):
                    frame._export_coordinator.export_document(document, "brl")

                frame._export_coordinator.write_document.assert_called_once_with(Path(written), document, "brl")
                message_box.assert_called_once()

    def test_real_writers_produce_today_bytes(self) -> None:
        frame = self._make_export_frame()
        results = (
            DualViewSegment(
                result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
                source_kind="text",
            ),
        )
        frame._document_controller.set_dual_view_results("alpha", results)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            frame._export_coordinator.write_document(root / "alpha.dep", Document("alpha", "text", None), "dep")
            with zipfile.ZipFile(root / "alpha.dep") as archive:
                members = {name: archive.read(name).decode("utf-8") for name in archive.namelist()}
            self.assertEqual(members, {"alpha.txt": "text", "alpha.brl": ""})

            frame._export_coordinator.write_document(root / "nested" / "alpha.brl", Document("alpha", "text", "⠁⠃"), "brl")
            self.assertEqual((root / "nested" / "alpha.brl").read_bytes(), "⠁⠃".encode("utf-8"))

            frame._export_coordinator.write_document(root / "alpha.html", Document("alpha", "text", "b"), "html")
            cached_html = render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml))
            self.assertEqual((root / "alpha.html").read_bytes(), text_file_bytes(cached_html))
            self.assertIn('<span class="source">a</span>', cached_html)

            frame._export_coordinator.write_document(root / "beta.html", Document("beta", "text", "b"), "html")
            empty_html = render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml))
            self.assertEqual((root / "beta.html").read_bytes(), text_file_bytes(empty_html))
            self.assertNotEqual(cached_html, empty_html)

            with self.assertRaises(OSError):
                frame._export_coordinator.write_document(root / "missing" / "alpha.html", Document("alpha", "text", "b"), "html")
            self.assertFalse((root / "missing").exists())

    def test_dual_view_and_html_export_render_math_with_real_mathml(self) -> None:
        frame = self._make_export_frame()
        results = (
            DualViewSegment(
                result=SimpleNamespace(raw=["x^2"], braille=["⠭", "⠘", "⠆"], braille_to_raw_pos=[0, 0, 0], raw_to_braille_pos=[0]),
                source_kind="math",
            ),
        )
        frame._document_controller.set_dual_view_results("alpha", results)
        expected = render_dual_view_html(
            build_dual_view_model(results, mathml_converter=latex_to_mathml),
            empty_message=gui._("No conversion data is available for this document."),
        )

        window_html = frame._render_dual_view_for_open_document()

        self.assertEqual(window_html, expected)
        self.assertIn(latex_to_mathml("x^2"), window_html)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alpha.html"
            frame._export_coordinator.write_document(path, Document("alpha", "text", "b"), "html")
            self.assertEqual(path.read_bytes(), text_file_bytes(expected))

    def test_export_all_html_uses_each_document_cache(self) -> None:
        frame = self._make_export_frame()
        results = (
            DualViewSegment(
                result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
                source_kind="text",
            ),
        )
        frame._document_controller.set_dual_view_results("alpha", results)
        frame._conversion_presenter.convert_for_export.side_effect = AssertionError("conversion should not run")
        documents = [Document("alpha", "text", "a"), Document("beta", "text", "b")]
        frame._document_controller.documents = documents
        frame.show_info = Mock()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame.choose_export_directory = Mock(return_value=root)
            frame._export_coordinator.export_all("html")

            self.assertEqual(
                (root / "alpha.html").read_text(encoding="utf-8"),
                render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml)),
            )
            self.assertEqual(
                (root / "beta.html").read_text(encoding="utf-8"),
                render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml)),
            )
        frame.show_info.assert_called_once_with(
            gui._(ExportBatchResult().summary_template),
            gui._(ExportBatchResult().summary_title),
        )

    def test_ctrl_s_in_output_editor_exports_open_document_as_brl(self) -> None:
        frame = self._make_frame()
        steps = Mock()
        frame._save_open_document_with_feedback = steps.save
        steps.save.return_value = True
        frame._export_coordinator = steps.coordinator
        frame.output_txt = steps.output_txt
        event = Mock()
        event.GetKeyCode.return_value = 83
        event.ControlDown.return_value = True

        frame.on_output_text_key_down(event)

        self.assertEqual(
            steps.mock_calls,
            [
                call.save(),
                call.coordinator.export_document(frame._document_controller.get_document("alpha"), "brl"),
                call.output_txt.SetFocus(),
            ],
        )
        event.Skip.assert_not_called()


class _FakeEditor:
    def __init__(self, name: str, events: list, value: str = ""):
        self.name = name
        self.events = events
        self.value = value

    def SetValue(self, value: str) -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value

    def SetFocus(self) -> None:
        self.events.append(("focus", self.name))

    def SetInsertionPoint(self, _position: int) -> None:
        pass

    def ShowPosition(self, _position: int) -> None:
        pass


class _FakeDocumentList:
    def __init__(self, names: list[str], selected_index: int):
        self.items = list(names)
        self.selected = selected_index

    def DeleteAllItems(self) -> None:
        self.items = []
        self.selected = gui.wx.NOT_FOUND

    def InsertItem(self, index: int, label: str) -> None:
        self.items.insert(index, label)

    def GetItemCount(self) -> int:
        return len(self.items)

    def Select(self, index: int, on: int = 1) -> None:
        self.selected = index if on else gui.wx.NOT_FOUND

    def Focus(self, _index: int) -> None:
        pass

    def GetFirstSelected(self) -> int:
        return self.selected


class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that moving the file named ``source_name``, or onto
    the file named ``destination_name``, raises."""

    def __init__(self, *, source_name: str | None = None, destination_name: str | None = None) -> None:
        self.source_name = source_name
        self.destination_name = destination_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name or Path(destination).name == self.destination_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)


class _FailingWritePackageFiles(PackageFiles):
    """The real file operations, except that writing the staged package raises ``ValueError`` (a bug)."""

    def write(self, path: Path, document: Document) -> None:
        raise ValueError("injected")


class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
    """Pins today's document flows: disk effects, dialogs, state; must pass unchanged through P1-3.

    Faults come from the file system: a directory at ``<ws>/<name>.dep`` makes the package
    write and the unlink fail with an ``OSError`` and is loaded as an invalid package.
    """

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"
        self.events: list = []
        self.answers: list = []
        self.dialog_answers: list = []
        # One-shot callbacks, each run by one MessageDialog while it is open (F-7, M-5).
        self.dialog_hooks: list = []
        self.names: list = []
        self.delete_invalid = False
        self.import_paths: list[str] = []
        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
        for patcher in (
            patch.object(gui, "message_box", self._message_box),
            patch.object(gui.wx, "MessageDialog", self._message_dialog_class()),
            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
            patch.object(gui, "FileIssuesDialog", self._issues_dialog_class()),
            patch.object(gui.wx, "FileDialog", self._import_dialog_class()),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    # --- fakes -------------------------------------------------------------

    def _message_box(self, message, caption, style, parent=None):
        self.events.append(("MessageBox", message, caption, style, parent))
        return self.answers.pop(0) if self.answers else gui.wx.OK

    def _message_dialog_class(self):
        """``wx.MessageDialog``: records the shown dialog, answers from ``dialog_answers`` (default Cancel)."""
        test = self

        class FakeMessageDialog:
            def __init__(self, parent, message, caption, style):
                self.shown = [message, caption, style, None, None, parent]

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def SetExtendedMessage(self, extended):
                self.shown[3] = extended

            def SetYesNoCancelLabels(self, yes, no, cancel):
                self.shown[4] = (yes, no, cancel)
                return True

            def ShowModal(self):
                test.events.append(("MessageDialog", *self.shown))
                hook = test.dialog_hooks.pop(0) if test.dialog_hooks else None
                if hook is not None:
                    hook()
                return test.dialog_answers.pop(0) if test.dialog_answers else gui.wx.ID_CANCEL

        return FakeMessageDialog

    def _name_dialog_class(self):
        test = self

        class FakeDocumentNameDialog:
            def __init__(self, parent, title, initial_name=""):
                test.events.append(("DocumentNameDialog", title, initial_name))
                self.name = test.names.pop(0)

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK if self.name is not None else gui.wx.CANCEL

            def get_document_name(self):
                return self.name

        return FakeDocumentNameDialog

    def _invalid_files_dialog_class(self):
        test = self

        class FakeInvalidWorkspaceFilesDialog:
            def __init__(self, parent, invalid_paths):
                test.events.append(("InvalidWorkspaceFilesDialog", list(invalid_paths)))

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK

            def should_delete_invalid_files(self):
                return test.delete_invalid

        return FakeInvalidWorkspaceFilesDialog

    def _issues_dialog_class(self):
        test = self

        class FakeFileIssuesDialog:
            def __init__(self, parent, title, message, issues):
                test.events.append(("FileIssuesDialog", title, message, list(issues)))

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK

        return FakeFileIssuesDialog

    def _import_dialog_class(self):
        test = self

        class FakeImportDialog:
            def __init__(self, parent, title, wildcard="", style=0):
                test.events.append(("FileDialog", title, style))

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def SetFilterIndex(self, index):
                pass

            def ShowModal(self):
                return gui.wx.ID_OK

            def GetFilterIndex(self):
                return test.import_filter_index

            def GetPaths(self):
                return list(test.import_paths)

        return FakeImportDialog

    # --- helpers -----------------------------------------------------------

    def _make_workspace_frame(self, documents=(), open_name=None, selected_name=None) -> gui.BrailleFrame:
        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
        documents = list(documents)
        frame._document_controller = DocumentController(
            documents=documents,
            open_name=open_name,
            selected_name=selected_name,
        )
        frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)
        open_document = next((document for document in documents if document.name == open_name), None)
        frame.input_txt = _FakeEditor("input", self.events, open_document.text if open_document else "")
        frame.output_txt = _FakeEditor("output", self.events, (open_document.braille or "") if open_document else "")
        names = [document.name for document in documents]
        frame.document_list = _FakeDocumentList(
            names,
            names.index(selected_name) if selected_name in names else gui.wx.NOT_FOUND,
        )
        frame.SetTitle = lambda title: self.events.append(("title", title))
        frame._dual_view_frame = None
        frame._document_menu_items = {}
        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
        frame._conversion_presenter.is_running.return_value = False
        frame.close_converting_dialog = Mock()
        return frame

    def _write_packages(self, *documents: Document) -> None:
        for document in documents:
            save_document_package(self.workspace / f"{document.name}.dep", document)

    def _block(self, name: str) -> Path:
        """Make ``<ws>/<name>.dep`` a non-empty directory: writes and unlinks of it fail."""
        path = self.workspace / f"{name}.dep"
        (path / "keep").mkdir(parents=True)
        return path

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace.iterdir())

    def _package(self, name: str) -> Document:
        return load_document_package(self.workspace / f"{name}.dep")

    def _members(self, name: str) -> list[str]:
        with zipfile.ZipFile(self.workspace / f"{name}.dep") as archive:
            return sorted(archive.namelist())

    def _state(self, frame) -> tuple:
        controller = frame._document_controller
        return (
            list(controller.documents),
            controller.open_name,
            controller.selected_name,
            dict(controller.dual_view_results_by_document),
        )

    def _assert_error_box(self, event, template: str, path_name: str, frame) -> None:
        kind, message, caption, style, parent = event
        self.assertEqual(kind, "MessageBox")
        self.assertTrue(message.startswith(gui._(template).partition("{error}")[0]), message)
        self.assertIn(path_name, message)
        self.assertEqual(caption, gui._("Error"))
        self.assertEqual(style, gui.wx.OK | gui.wx.ICON_ERROR)
        self.assertIs(parent, frame)

    def _confirm(self, message: str, title: str, frame) -> tuple:
        return (
            "MessageBox",
            message,
            title,
            gui.wx.YES_NO | gui.wx.NO_DEFAULT | gui.wx.ICON_WARNING,
            frame,
        )

    # --- Add and default document ------------------------------------------

    def test_add_saves_open_document_then_creates_and_opens_new_document(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("a edited")
        self.names = ["beta"]

        frame.on_add_document(None)

        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(self._package("beta"), Document("beta", "", ""))
        self.assertEqual(self._members("beta"), ["beta.brl", "beta.txt"])
        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual(frame._document_controller.open_name, "beta")
        self.assertEqual(frame._document_controller.selected_name, "beta")
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))
        self.assertEqual(frame.document_list.items, ["alpha", "beta"])
        self.assertEqual(frame.document_list.selected, 1)
        self.assertEqual(
            self.events,
            [("DocumentNameDialog", gui._("Add Document"), ""), ("title", "beta - DotExpress")],
        )

    def test_add_duplicate_name_reprompts_with_that_name(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.names = ["alpha", "beta"]

        frame.on_add_document(None)

        self.assertEqual(
            self.events[:3],
            [
                ("DocumentNameDialog", gui._("Add Document"), ""),
                (
                    "MessageBox",
                    gui._('Document "{name}" already exists.').format(name="alpha"),
                    gui._("Error"),
                    gui.wx.OK | gui.wx.ICON_ERROR,
                    frame,
                ),
                ("DocumentNameDialog", gui._("Add Document"), "alpha"),
            ],
        )
        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_add_write_failure_shows_error_and_keeps_state(self) -> None:
        # F-8 (D1): a folder at beta.dep would now make the name taken, so the write of
        # beta fails on a full disk instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["beta"]

        with full_disk(self.workspace, pattern=r"^\.beta\.dep\."):
            frame.on_add_document(None)

        self.assertEqual(len(self.events), 2)
        self.assertEqual(
            self.events[1],
            (
                "MessageBox",
                gui._("Failed to save document: {error}").format(error=f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"),
                gui._("Error"),
                gui.wx.OK | gui.wx.ICON_ERROR,
                frame,
            ),
        )
        self.assertEqual(self._state(frame), before)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))

    def test_add_failure_that_is_not_an_os_error_shows_the_message(self) -> None:
        # F-3 (D9): every Exception from creating the package is reported.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["beta"]

        with patch.object(frame._workspace_service, "create_document", side_effect=ValueError("boom")):
            frame.on_add_document(None)

        self.assertEqual(
            self.events,
            [
                ("DocumentNameDialog", gui._("Add Document"), ""),
                (
                    "MessageBox",
                    gui._("Failed to save document: {error}").format(error="boom"),
                    gui._("Error"),
                    gui.wx.OK | gui.wx.ICON_ERROR,
                    frame,
                ),
            ],
        )
        self.assertEqual(self._state(frame), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_default_document_is_pending_opened_and_focused(self) -> None:
        frame = self._make_workspace_frame()

        frame._ensure_open_document_exists()

        self.assertEqual(self._listing(), ["new.dep"])
        self.assertEqual(self._package("new"), Document("new", "", None))
        self.assertEqual(self._members("new"), ["new.brl", "new.meta.json", "new.txt"])
        self.assertEqual(frame._document_controller.document_names, ["new"])
        self.assertEqual(frame._document_controller.open_name, "new")
        self.assertEqual(self.events, [("title", "new - DotExpress"), ("focus", "input")])

    # --- startup -----------------------------------------------------------

    def test_startup_with_missing_workspace_creates_it_and_default_document(self) -> None:
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(self._listing(), ["new.dep"])
        self.assertEqual(frame._document_controller.document_names, ["new"])
        self.assertEqual(frame._document_controller.open_name, "new")
        self.assertEqual(
            self.events,
            [("title", "new - DotExpress"), ("focus", "input"), ("title", "new - DotExpress")],
        )

    def test_startup_reviews_invalid_packages_and_opens_first_valid_one(self) -> None:
        self._write_packages(Document("good", "g", "1"))
        (self.workspace / "bad.dep").write_bytes(b"not a zip")
        self.delete_invalid = True
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(
            self.events,
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "bad.dep"]),
                ("title", "good - DotExpress"),
                ("title", "good - DotExpress"),
            ],
        )
        self.assertEqual(self._listing(), ["good.dep"])
        self.assertEqual(frame._document_controller.document_names, ["good"])
        self.assertEqual(frame._document_controller.open_name, "good")
        self.assertEqual(frame.input_txt.value, "g")

    def test_startup_invalid_file_delete_error_continues_with_next_file(self) -> None:
        self._block("a-blocked")
        (self.workspace / "b-corrupt.dep").write_bytes(b"not a zip")
        self._write_packages(Document("good", "g", "1"))
        self.delete_invalid = True
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(
            self.events[0],
            ("InvalidWorkspaceFilesDialog", [self.workspace / "a-blocked.dep", self.workspace / "b-corrupt.dep"]),
        )
        self._assert_error_box(self.events[1], "Failed to delete invalid workspace file: {error}", "a-blocked.dep", frame)
        self.assertEqual(self.events[2:], [("title", "good - DotExpress"), ("title", "good - DotExpress")])
        self.assertEqual(self._listing(), ["a-blocked.dep", "good.dep"])

    def test_startup_ignores_leftover_temporary_files(self) -> None:
        # F-3 (D13): temporary files a crash can leave next to the packages are neither
        # listed nor offered for deletion; they stay on disk untouched.
        self._write_packages(Document("good", "g", "1"))
        leftovers = [".good.dep.0123456789abcdef.tmp", ".good.dep.k2j1abcd.tmp"]
        for name in leftovers:
            (self.workspace / name).write_bytes(b"not a zip")
        self.delete_invalid = True
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(self.events, [("title", "good - DotExpress"), ("title", "good - DotExpress")])
        self.assertEqual(self._listing(), sorted(leftovers + ["good.dep"]))
        self.assertEqual(frame._document_controller.document_names, ["good"])

    def test_startup_with_only_a_kept_invalid_new_package_creates_new_2(self) -> None:
        # F-8 (D2): the default document takes a free name; the kept new.dep stays as it is.
        self.workspace.mkdir()
        (self.workspace / "new.dep").write_bytes(b"not a zip")
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(
            self.events,
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "new.dep"]),
                ("title", "new (2) - DotExpress"),
                ("focus", "input"),
                ("title", "new (2) - DotExpress"),
            ],
        )
        self.assertEqual(self._listing(), ["new (2).dep", "new.dep"])
        self.assertEqual((self.workspace / "new.dep").read_bytes(), b"not a zip")
        self.assertEqual(self._package("new (2)"), Document("new (2)", "", None))
        self.assertEqual(frame._document_controller.document_names, ["new (2)"])
        self.assertEqual(frame._document_controller.open_name, "new (2)")

    # --- save --------------------------------------------------------------

    def test_save_open_document_keeps_pending_document_pending(self) -> None:
        alpha = Document("alpha", "a", None)
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("edited")
        frame.output_txt.SetValue("ignored braille")

        self.assertTrue(frame._save_open_document_with_feedback())

        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", None)])
        self.assertEqual(self._package("alpha"), Document("alpha", "edited", None))
        self.assertIn("alpha.meta.json", self._members("alpha"))
        self.assertEqual(self.events, [])

    def test_save_failure_reports_error_after_updating_memory(self) -> None:
        self._block("alpha")
        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("edited")
        frame.output_txt.SetValue("edited braille")

        self.assertFalse(frame._save_open_document_with_feedback())

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "alpha.dep", frame)
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", "edited braille")])

    def test_close_save_failure_cancel_vetoes(self) -> None:
        # F-5 (D6): the dialog replaces the error box; Cancel keeps the window open.
        self._block("alpha")
        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        event = Mock()
        event.CanVeto.return_value = True
        self.dialog_answers = [gui.wx.ID_CANCEL]

        frame._on_close(event)

        self.assertEqual([item[0] for item in self.events], ["MessageDialog"])
        expected = self._close_dialog(frame, "")
        self.assertTrue(self.events[0][1].startswith(expected[1]), self.events[0][1])
        self.assertIn("alpha.dep", self.events[0][1])
        self.assertEqual(self.events[0][2:], expected[2:])
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()

    def test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package(self) -> None:
        # F-3 (D9): a bug in the writer (simulated: writestr raises ValueError). The message
        # appears instead of an escaping exception; the package keeps its bytes and memory
        # keeps the edit.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x edited")

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            self.assertFalse(frame._save_open_document_with_feedback())

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "x edited", "1")])

    def test_pasted_lone_surrogate_is_saved_as_replacement_character(self) -> None:
        # F-5 (D4, D5): the save succeeds without a message; memory and the package hold
        # U+FFFD, and the editor keeps what the user pasted until the document is reopened.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x\ud800")

        self.assertTrue(frame._save_open_document_with_feedback())

        self.assertEqual(self.events, [])
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "x�", "1")])
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_save_reads_both_editors_through_the_replacement(self) -> None:
        # F-7 (M-7): the frame reads the editors through replace_lone_surrogates; F-5's
        # replacement in the documents layer stays as the second line of defense.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a" + LONE_SURROGATE)
        frame.output_txt.SetValue("1" + LONE_SURROGATE)
        service = frame._workspace_service

        with patch.object(service, "save_open_document", wraps=service.save_open_document) as save:
            frame._save_open_document()

        save.assert_called_once_with(text="a�", braille="1�")
        self.assertEqual(frame.input_txt.value, "a" + LONE_SURROGATE)
        self.assertEqual(frame.output_txt.value, "1" + LONE_SURROGATE)
        self.assertEqual(self._package("alpha"), Document("alpha", "a�", "1�"))

    def test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why. F-5 (D6, D9): the traceback is logged at each attempt and
        # the dialog offers a way out (here Cancel: the close is vetoed).
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("edited")
        event = Mock()
        event.CanVeto.return_value = True
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with (
            patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")),
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "injected")
        self._assert_logged_with_traceback(logs, ValueError)
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- save only when changed (F-5) ----------------------------------------

    def _start_with_alpha_and_beta(self) -> gui.BrailleFrame:
        """Packages alpha ("a", "1") and beta ("b", "2") loaded at startup; alpha is open."""
        self._write_packages(Document("alpha", "a", "1"), Document("beta", "b", "2"))
        frame = self._make_workspace_frame()
        frame._load_workspace_documents_at_startup()
        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.events.clear()
        return frame

    def _disk(self, name: str = "alpha") -> tuple[bytes, int]:
        path = self.workspace / f"{name}.dep"
        return path.read_bytes(), path.stat().st_mtime_ns

    def _vetoable_close(self) -> Mock:
        event = Mock()
        event.CanVeto.return_value = True
        return event

    def test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next(self) -> None:
        # F-W10: before F-5 the unchanged document was rewritten, the write failed, and the
        # error box blocked the switch.
        frame = self._start_with_alpha_and_beta()
        before = self._disk()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._open_adjacent_document(1)

        replace.assert_not_called()
        self.assertEqual(frame._document_controller.open_name, "beta")
        self.assertEqual(frame.input_txt.value, "b")
        self.assertEqual([item for item in self.events if item[0] != "title"], [("focus", "input")])
        self.assertEqual(self._disk(), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_unchanged_read_only_document_blocks_neither_switch_nor_close(self) -> None:
        frame = self._start_with_alpha_and_beta()
        make_read_only(self, self.workspace / "alpha.dep")
        before = self._disk()
        event = self._vetoable_close()

        frame._open_adjacent_document(1)
        frame._open_adjacent_document(1)
        frame._on_close(event)

        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.assertEqual([item[0] for item in self.events if item[0] not in ("title", "focus")], [])
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    def test_switch_from_a_changed_document_whose_save_fails_still_blocks(self) -> None:
        # Decision C: an action whose save really writes and fails is still blocked.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._open_adjacent_document(1)

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_with_an_unchanged_document_whose_save_would_fail_closes(self) -> None:
        frame = self._start_with_alpha_and_beta()
        before = self._disk()
        event = self._vetoable_close()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(event)

        replace.assert_not_called()
        self.assertEqual(self.events, [])
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        frame.close_converting_dialog.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    # --- close after a failed save (F-5) -------------------------------------

    def _close_dialog(self, frame, error: str) -> tuple:
        """The event of the dialog that a failed save on Close shows (D7)."""
        return (
            "MessageDialog",
            gui._("Failed to save document: {error}").format(error=error),
            gui._("Cannot Save Document"),
            gui.wx.YES_NO | gui.wx.CANCEL | gui.wx.YES_DEFAULT | gui.wx.ICON_ERROR,
            gui._(
                "Changes made since the last successful save have not been saved. "
                "If you close without saving, these changes will be lost."
            ),
            (gui._("&Retry"), gui._("Close &Without Saving"), gui._("Cancel")),
            frame,
        )

    def _assert_close_dialogs(self, frame, *errors: str) -> None:
        """The only events are one close dialog per error text, in this order."""
        self.assertEqual([item[0] for item in self.events], ["MessageDialog"] * len(errors))
        self.assertEqual(self.events, [self._close_dialog(frame, error) for error in errors])

    def test_close_save_failure_asks_and_cancel_keeps_the_window_open(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_retry_after_the_cause_is_gone_saves_and_closes(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_YES]

        with patch("os.replace", wraps=os.replace, side_effect=[PermissionError(errno.EACCES, "injected"), DEFAULT]):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_close_retry_that_fails_again_asks_again(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_YES, gui.wx.ID_CANCEL]
        errors = [PermissionError(errno.EACCES, "first"), PermissionError(errno.EACCES, "second")]

        with patch("os.replace", side_effect=errors):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] first", "[Errno 13] second")
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        self.assertEqual(self._disk(), before)

    def test_close_without_saving_closes_and_keeps_the_last_saved_package(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        viewer = Mock()
        frame._dual_view_frame = viewer
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_NO]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 1)
        frame.close_converting_dialog.assert_called_once_with()
        viewer.Destroy.assert_called_once_with()
        self.assertIsNone(frame._dual_view_frame)
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- a close that arrives while the close dialog is open (F-7, M-5) ------

    def test_close_reentered_while_the_close_dialog_is_open_is_vetoed(self) -> None:
        # Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs, and
        # wx delivers another close event to the frame. The open dialog decides.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        outer = self._vetoable_close()
        inner = self._vetoable_close()
        self.dialog_hooks = [lambda: frame._on_close(inner)]
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(outer)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 1)
        inner.Veto.assert_called_once_with()
        inner.Skip.assert_not_called()
        outer.Veto.assert_called_once_with()
        outer.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_reentered_that_cannot_be_vetoed_closes_once(self) -> None:
        # Defensive: wx 3.2 ends a session without a close event, and DotExpress never forces a
        # close. A nested close that cannot be vetoed runs F-5 D8 once, and the outer close
        # stops when its dialog returns, whatever the answer.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        viewer = Mock()
        frame._dual_view_frame = viewer
        before = self._disk()
        outer = self._vetoable_close()
        inner = Mock()
        inner.CanVeto.return_value = False
        self.dialog_hooks = [lambda: frame._on_close(inner)]
        self.dialog_answers = [gui.wx.ID_YES]

        with (
            patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace,
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            frame._on_close(outer)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 2)
        self.assertEqual([record.getMessage() for record in logs.records], ["Failed to save the open document while closing"])
        frame.close_converting_dialog.assert_called_once_with()
        viewer.Destroy.assert_called_once_with()
        inner.Veto.assert_not_called()
        inner.Skip.assert_called_once_with()
        outer.Veto.assert_not_called()
        outer.Skip.assert_not_called()
        self.assertEqual(self._disk(), before)

    def test_close_works_again_after_a_vetoed_close(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        first = self._vetoable_close()
        second = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._on_close(first)
        frame._on_close(second)

        first.Veto.assert_called_once_with()
        second.Veto.assert_not_called()
        second.Skip.assert_called_once_with()
        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))

    def test_close_flag_is_reset_when_the_close_raises(self) -> None:
        frame = self._start_with_alpha_and_beta()
        event = self._vetoable_close()

        with (
            patch.object(frame, "_save_open_document_before_close", side_effect=RuntimeError("injected")),
            self.assertRaisesRegex(RuntimeError, "injected"),
        ):
            frame._on_close(event)

        # The wx stub answers every missing attribute, so read the frame's own attributes.
        self.assertIs(vars(frame).get("_closing"), False)

    def test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes(self) -> None:
        # D8: Windows is ending the session; nobody could answer a dialog.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = Mock()
        event.CanVeto.return_value = False
        error = PermissionError(errno.EACCES, "injected")

        with patch("os.replace", side_effect=error), self.assertLogs(gui.logger, level="ERROR") as logs:
            frame._on_close(event)

        self.assertEqual([item[0] for item in self.events], [])
        self.assertEqual([record.getMessage() for record in logs.records], ["Failed to save the open document while closing"])
        self.assertIs(logs.records[0].exc_info[1], error)
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    def test_close_dialog_strings_are_translated(self) -> None:
        translation = i18n.load_translation()
        expected = {
            "Cannot Save Document": "無法儲存文件",
            "Changes made since the last successful save have not been saved. "
            "If you close without saving, these changes will be lost.": (
                "上次成功儲存之後的修改尚未儲存。"
                "如果不儲存就關閉，這些修改將會遺失。"
            ),
            "&Retry": "重試(&R)",
            "Close &Without Saving": "不儲存就關閉(&W)",
            "Cancel": "取消",
            "Failed to save document: {error}": "儲存文件失敗：{error}",
        }

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    # --- rename ------------------------------------------------------------

    def test_rename_writes_new_package_deletes_old_and_moves_state(self) -> None:
        alpha = Document("alpha", "a", None)
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="alpha")
        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",), "beta": ("seg-b",)})
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", None))
        self.assertIn("gamma.meta.json", self._members("gamma"))
        self.assertEqual(
            self._state(frame),
            (
                [Document("beta", "b", "2"), Document("gamma", "a", None)],
                "gamma",
                "gamma",
                {"gamma": ("seg-a",), "beta": ("seg-b",)},
            ),
        )
        self.assertEqual(frame.document_list.items, ["beta", "gamma"])
        self.assertEqual(frame.document_list.selected, 1)
        self.assertEqual(
            self.events,
            [("DocumentNameDialog", gui._("Rename Document"), "alpha"), ("title", "gamma - DotExpress")],
        )

    def test_rename_with_missing_old_package_writes_new_one(self) -> None:
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "b", "2"))
        self.assertEqual(frame._document_controller.document_names, ["alpha", "gamma"])
        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.assertEqual(frame._document_controller.selected_name, "gamma")

    def test_rename_write_failure_keeps_old_package_and_state(self) -> None:
        # F-8 (D1): a folder at gamma.dep would now make the name taken, so installing
        # gamma.dep fails instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingReplacePackageFiles(destination_name="gamma.dep"),
        )
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "gamma.dep", frame)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), alpha)
        self.assertEqual(self._state(frame), before)

    def test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state(self) -> None:
        # Was the KNOWN BUG test of P1-3 known defect 3 (the new package was written, the
        # old one could not be removed, and both stayed on disk while memory kept only
        # the old name), fixed by F-3: the old package is moved aside before the new one
        # is installed, so a failure there leaves only the old package.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        beta_bytes = (self.workspace / "beta.dep").read_bytes()
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingReplacePackageFiles(source_name="beta.dep"),
        )
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0], ("DocumentNameDialog", gui._("Rename Document"), "beta"))
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual((self.workspace / "beta.dep").read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_rename_of_a_read_only_package_is_refused_with_the_save_message(self) -> None:
        # F-3 (D7, Q2): the same [Errno 13] text Save gives; before F-3 a regular rename
        # failed with [WinError 5] after writing gamma.dep, so both packages stayed.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        beta_path = self.workspace / "beta.dep"
        beta_bytes = beta_path.read_bytes()
        make_read_only(self, beta_path)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertIn(f"[Errno 13] Permission denied: {str(beta_path)!r}", self.events[1][1])
        self.assertEqual(beta_path.read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    def _rename_frame_whose_staged_write_fails(self) -> gui.BrailleFrame:
        """alpha open, beta selected; writing the staged package of a rename raises ``ValueError``."""
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingWritePackageFiles(),
        )
        self.names = ["gamma"]
        return frame

    def test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state(self) -> None:
        # F-3 (D9): renaming the non-open beta while the staged write raises (a bug).
        frame = self._rename_frame_whose_staged_write_fails()
        beta_bytes = (self.workspace / "beta.dep").read_bytes()
        before = self._state(frame)

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "beta.dep").read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    # --- logging at the save boundary (F-3 review M-3) ----------------------

    def _assert_logged_with_traceback(self, logs, error_type: type[BaseException]) -> None:
        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.levelname, "ERROR")
        self.assertIs(record.exc_info[0], error_type)
        self.assertIn("Traceback (most recent call last)", logs.output[0])

    def test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        # The packaged build has no console: gui.log is the only trace of an
        # unexpected error behind the "Failed to save document" box.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x edited")

        with (
            patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")),
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            self.assertFalse(frame._save_open_document_with_feedback())

        self._assert_logged_with_traceback(logs, ValueError)
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)

    def test_add_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.names = ["beta"]

        with (
            patch.object(frame._workspace_service, "create_document", side_effect=ValueError("boom")),
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            frame.on_add_document(None)

        self._assert_logged_with_traceback(logs, ValueError)
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "boom", frame)

    def test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        frame = self._rename_frame_whose_staged_write_fails()

        with self.assertLogs(gui.logger, level="ERROR") as logs:
            frame.on_rename_document(None)

        self._assert_logged_with_traceback(logs, ValueError)
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "injected", frame)

    def test_save_failure_from_an_os_error_is_not_logged(self) -> None:
        # Locked, read-only or full disks are expected; the message box already
        # names the path and the system error, so gui.log stays free of them.
        self._block("alpha")
        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("edited")

        with self.assertNoLogs(gui.logger):
            self.assertFalse(frame._save_open_document_with_feedback())

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "alpha.dep", frame)

    def test_rename_cancelled_or_unchanged_does_nothing(self) -> None:
        for answer in (None, "alpha"):
            with self.subTest(answer=answer):
                self.events.clear()
                alpha = Document("alpha", "a", "1")
                self._write_packages(alpha)
                frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
                before = self._state(frame)
                self.names = [answer]

                frame.on_rename_document(None)

                self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "alpha")])
                self.assertEqual(self._listing(), ["alpha.dep"])
                self.assertEqual(self._state(frame), before)

    def _rename_alpha_case_only(self, package_files=None):
        alpha = Document("Alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="Alpha", selected_name="Alpha")
        if package_files is not None:
            frame._workspace_service = DocumentWorkspaceService(
                frame._document_controller,
                self.workspace,
                package_files=package_files,
            )
        self.names = ["alpha"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
        self.assertEqual(frame._document_controller.document_names, ["alpha"])
        self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "Alpha"), ("title", "alpha - DotExpress")])

    def test_case_only_rename_keeps_the_document(self) -> None:
        # Replaces the KNOWN BUG test of P1-3 known defect 1 (data loss: the case-only
        # rename deleted the package on a case-insensitive file system), fixed by F-1.
        # Runs on the host's real file system: case-insensitive on Windows and macOS.
        self._rename_alpha_case_only()

    def test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document(self) -> None:
        # F-1: the same rename on the case-insensitive file model, so Linux covers it too.
        self._rename_alpha_case_only(CaseInsensitivePackageFiles())

    def _duplicate_name_events(self, title: str, initial_name: str, typed_name: str, frame) -> list:
        return [
            ("DocumentNameDialog", gui._(title), initial_name),
            (
                "MessageBox",
                gui._('Document "{name}" already exists.').format(name=typed_name),
                gui._("Error"),
                gui.wx.OK | gui.wx.ICON_ERROR,
                frame,
            ),
            ("DocumentNameDialog", gui._(title), typed_name),
        ]

    def test_add_case_variant_is_refused_as_a_duplicate(self) -> None:
        # Replaces the KNOWN BUG test of P1-3 known defect 2 (data loss: Add "Alpha"
        # overwrote alpha.dep on a case-insensitive file system), fixed by F-1. Names are
        # compared with casefold() on every platform, so this runs on any file system.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.names = ["Alpha", None]

        frame.on_add_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "Alpha", frame))
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), alpha)
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
        self.assertEqual(frame._document_controller.document_names, ["alpha"])

    def test_rename_to_a_case_variant_of_another_document_is_refused(self) -> None:
        # F-1: renaming beta to "Alpha" while alpha exists overwrote alpha.dep on a
        # case-insensitive file system; it is now refused like an exact duplicate.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.names = ["Alpha", None]

        frame.on_rename_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Rename Document", "beta", "Alpha", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(self._package("alpha"), alpha)
        self.assertEqual(self._package("beta"), beta)
        self.assertEqual(self._state(frame), before)

    def _frame_with_a_kept_invalid_bad_package(self):
        """alpha listed and open, bad.dep invalid and kept at startup (F-8, M-1)."""
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        (self.workspace / "bad.dep").write_bytes(b"not a zip")
        return self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")

    def test_add_of_a_name_whose_package_is_on_disk_asks_again(self) -> None:
        frame = self._frame_with_a_kept_invalid_bad_package()
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        before = self._state(frame)
        self.names = ["bad", None]

        frame.on_add_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    def test_rename_to_a_name_whose_package_is_on_disk_asks_again(self) -> None:
        frame = self._frame_with_a_kept_invalid_bad_package()
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        before = self._state(frame)
        self.names = ["bad", None]

        frame.on_rename_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Rename Document", "alpha", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    # --- delete ------------------------------------------------------------

    def test_delete_open_middle_document_opens_previous_neighbour(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("gamma", "c", "3")]
        self._write_packages(*documents)
        frame = self._make_workspace_frame(documents, open_name="beta", selected_name="beta")
        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",), "beta": ("seg-b",)})
        self.answers = [gui.wx.YES]

        frame.on_delete_document(None)

        self.assertEqual(
            self.events,
            [
                self._confirm(
                    gui._('Do you want to delete document "{name}"?').format(name="beta"),
                    gui._("Confirm Delete Document"),
                    frame,
                ),
                ("title", "alpha - DotExpress"),
            ],
        )
        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(
            self._state(frame),
            ([documents[0], documents[2]], "alpha", "alpha", {"alpha": ("seg-a",)}),
        )
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))

    def test_delete_selected_document_that_is_not_open_keeps_editors(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(*documents)
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="beta")
        self.answers = [gui.wx.YES]

        frame.on_delete_document(None)

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._state(frame), ([documents[0]], "alpha", "alpha", {}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
        self.assertEqual(len(self.events), 1)

    def test_delete_last_document_creates_default_document(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.answers = [gui.wx.YES]

        frame.on_delete_document(None)

        self.assertEqual(self._listing(), ["new.dep"])
        self.assertEqual(self._package("new"), Document("new", "", None))
        self.assertEqual(self._state(frame), ([Document("new", "", None)], "new", "new", {}))
        self.assertEqual(
            self.events[1:],
            [("title", "DotExpress"), ("title", "new - DotExpress"), ("focus", "input")],
        )

    def test_delete_answered_no_changes_nothing(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.answers = [gui.wx.NO]

        frame.on_delete_document(None)

        self.assertEqual(len(self.events), 1)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._state(frame), before)

    def test_delete_unlink_failure_shows_error_and_keeps_state(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(documents[0])
        self._block("beta")
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.answers = [gui.wx.YES]

        frame.on_delete_document(None)

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(self._state(frame), before)

    # --- Delete All --------------------------------------------------------

    def test_delete_all_success_removes_packages_and_creates_default_document(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(*documents)
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
        frame._document_controller.dual_view_results_by_document.update({"alpha": ("seg-a",)})
        self.answers = [gui.wx.YES]

        frame.on_delete_all_documents(None)

        self.assertEqual(
            self.events,
            [
                self._confirm(
                    gui._("Delete All will remove all documents. Do you want to continue?"),
                    gui._("Confirm Delete All"),
                    frame,
                ),
                ("title", "DotExpress"),
                ("title", "new - DotExpress"),
                ("focus", "input"),
            ],
        )
        self.assertEqual(self._listing(), ["new.dep"])
        self.assertEqual(self._state(frame), ([Document("new", "", None)], "new", "new", {}))

    def test_delete_all_failure_reports_then_reloads_and_reviews(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("gamma", "c", "3")]
        self._write_packages(documents[0], documents[2])
        self._block("beta")
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
        frame._document_controller.dual_view_results_by_document.update(
            {"alpha": ("seg-a",), "beta": ("seg-b",), "gamma": ("seg-c",)}
        )
        self.answers = [gui.wx.YES]

        frame.on_delete_all_documents(None)

        self.assertEqual(len(self.events), 4)
        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
        self.assertEqual(
            self.events[2:],
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]),
                ("title", "gamma - DotExpress"),
            ],
        )
        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep"])
        self.assertEqual(self._state(frame), ([documents[2]], "gamma", "gamma", {"gamma": ("seg-c",)}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("c", "3"))

    def test_delete_all_failure_without_valid_document_clears_editors_only(self) -> None:
        # KNOWN BUG (P1-3 spec, known defect 4), pinned as it is today, NOT desired
        # behavior: the rollback leaves no valid document, so only the editors are
        # cleared (no title update, no default document). A later fix task flips this.
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(documents[0])
        self._block("beta")
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
        self.answers = [gui.wx.YES]

        frame.on_delete_all_documents(None)

        self.assertEqual(len(self.events), 3)
        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
        self.assertEqual(self.events[2], ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]))
        self.assertEqual(self._listing(), ["beta.dep"])
        self.assertEqual(self._state(frame), ([], None, None, {}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))

    def test_delete_all_without_documents_does_nothing(self) -> None:
        frame = self._make_workspace_frame()
        frame._save_open_document_with_feedback = Mock()

        frame.on_delete_all_documents(None)

        frame._save_open_document_with_feedback.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertFalse(self.workspace.exists())

    # --- import ------------------------------------------------------------

    def _write_sources(self, **texts: str) -> list[str]:
        source_dir = self.root / "sources"
        source_dir.mkdir(exist_ok=True)
        paths = []
        for stem, text in texts.items():
            path = source_dir / f"{stem}.txt"
            path.write_text(text, encoding="utf-8")
            paths.append(str(path))
        return paths

    def test_import_two_files_adds_them_and_keeps_open_document(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.import_paths = self._write_sources(delta="d", beta="b")

        frame.on_import_document(None)

        self.assertEqual(self.events, [("FileDialog", gui._("Import Document"), gui.wx.FD_OPEN | gui.wx.FD_MULTIPLE)])
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep", "delta.dep"])
        self.assertEqual(self._package("delta"), Document("delta", "d", None))
        self.assertEqual(
            self._state(frame),
            ([alpha, Document("beta", "b", None), Document("delta", "d", None)], "alpha", "alpha", {}),
        )
        self.assertEqual(frame.document_list.items, ["alpha", "beta", "delta"])

    def test_import_one_file_opens_it(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.import_paths = self._write_sources(beta="b")

        frame.on_import_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(frame._document_controller.open_name, "beta")
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("b", ""))
        self.assertEqual(self.events[1:], [("title", "beta - DotExpress")])

    def test_import_reports_load_issues_before_save_issues(self) -> None:
        # F-8 (D1): a folder at delta.dep would now make the name taken (a load issue),
        # so the save of delta fails on a full disk instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.import_paths = self._write_sources(Alpha="dup", beta="b", delta="d")

        with full_disk(self.workspace, pattern=r"^\.delta\.dep\."):
            frame.on_import_document(None)

        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual(frame._document_controller.open_name, "beta")
        kind, title, message, lines = self.events[-1]
        self.assertEqual((kind, title, message), ("FileIssuesDialog", gui._("Import Issues"), gui._("Some files were skipped during import.")))
        self.assertEqual(
            lines,
            [
                'Alpha.txt: Document "Alpha" already exists.',
                f"delta.dep: [Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}",
            ],
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- selection ---------------------------------------------------------

    def test_selection_change_maps_index_to_name(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
        for index, expected in ((1, "beta"), (gui.wx.NOT_FOUND, None), (2, None), (0, "alpha")):
            with self.subTest(index=index):
                frame.document_list.selected = index
                event = Mock()

                frame.on_document_selection_changed(event)

                self.assertEqual(frame._document_controller.selected_name, expected)
                event.Skip.assert_called_once_with()



def _dual_view_segment(raw: str, braille: str) -> DualViewSegment:
    return DualViewSegment(
        result=SimpleNamespace(raw=[raw], braille=[braille], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
        source_kind="text",
    )


class _RecordingEditor(_FakeEditor):
    def SetValue(self, value: str) -> None:
        self.events.append(("set", self.name, value))
        super().SetValue(value)

    def Enable(self, enable: bool = True) -> None:
        self.events.append(("enable", self.name, enable))


class _RecordingDocumentList(_FakeDocumentList):
    def __init__(self, events: list, names: list[str], selected_index: int):
        super().__init__(names, selected_index)
        self.events = events

    def Enable(self, enable: bool = True) -> None:
        self.events.append(("enable", "list", enable))


class _RecordingMenuBar:
    def __init__(self, events: list):
        self.events = events
        self.titles = [gui._("File"), gui._("Translation"), gui._("Help")]

    def FindMenu(self, title: str) -> int:
        self.events.append(("FindMenu", title))
        return self.titles.index(title) if title in self.titles else gui.wx.NOT_FOUND

    def EnableTop(self, index: int, enable: bool) -> None:
        self.events.append(("EnableTop", index, enable))


class _RecordingViewer:
    """Stands for the open Dual View window."""

    def __init__(self, events: list):
        self.events = events
        self.html = None

    def refresh_html(self, html: str) -> None:
        self.html = html
        self.events.append(("dual_view.refresh",))

    def Destroy(self) -> None:
        self.events.append(("dual_view.Destroy",))


class _KeyEvent:
    def __init__(self, key_code: int, *, control: bool = True, shift: bool = False):
        self.key_code = key_code
        self.control = control
        self.shift = shift
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self.key_code

    def ControlDown(self) -> bool:
        return self.control

    def ShiftDown(self) -> bool:
        return self.shift

    def Skip(self) -> None:
        self.skipped = True


class _CloseEvent:
    def __init__(self, events: list, can_veto: bool):
        self.events = events
        self.can_veto = can_veto

    def CanVeto(self) -> bool:
        return self.can_veto

    def Veto(self) -> None:
        self.events.append(("close.Veto",))

    def Skip(self) -> None:
        self.events.append(("close.Skip",))


class ConversionExportFlowsCharacterizationTest(unittest.TestCase):
    """Pins today's conversion and export flows turn by turn; must pass unchanged through P1-4.

    ``wx.CallAfter`` is a ``DeferredCalls`` queue, ``wx.CallLater`` a ``FakeTimers`` recorder and
    every worker a ``FakeThread``. A test drives a public entry point (the click or menu turn),
    then steps the worker (``thread.run()``), each later UI turn (``calls.run_next()``) and the
    timers (``fire()``), and checks the ordered ``self.events`` log after each step.
    Only ``_wire_conversion`` may change during P1-4.
    """

    TABLES = {"default": "zh-tw.ctb", "math": "nemeth.ctb"}
    LANG = "zh_TW"
    CHARSET_MAPS = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
    CTRL_S = 83
    CTRL_TAB = 9

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"
        self.export_dir = self.root / "export"
        self.export_dir.mkdir()
        self.events: list = []
        self.answers: list = []
        self.export_paths: list = []
        self.export_dirs: list = []
        self.outputs: dict = {}
        self.requests: list = []
        self.runtime = object()
        self.calls = DeferredCalls(self.events)
        self.timers = FakeTimers(self.events)
        self.thread_factory = make_thread_factory()
        self.threads = self.thread_factory.threads
        self.menu_bar = _RecordingMenuBar(self.events)
        for patcher in (
            patch.object(gui, "message_box", self._message_box),
            patch.object(gui.wx, "FileDialog", self._file_dialog_class()),
            patch.object(gui.wx, "DirDialog", self._dir_dialog_class()),
            patch.object(gui.wx, "CallAfter", self.calls),
            patch.object(gui.wx, "CallLater", self.timers),
            patch.object(gui.wx, "EVT_CLOSE", "EVT_CLOSE"),
            patch.object(gui, "ConvertingDialog", self._converting_dialog_class()),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    # --- fakes -------------------------------------------------------------

    def _message_box(self, message, caption, style, parent=None):
        self.events.append(("MessageBox", message, caption, style, parent))
        return self.answers.pop(0) if self.answers else gui.wx.OK

    def _file_dialog_class(self):
        test = self

        class FakeExportFileDialog:
            def __init__(self, parent, title, defaultFile="", wildcard="", style=0):
                test.events.append(("FileDialog", parent, title, defaultFile, wildcard, style))
                self.path = test.export_paths.pop(0)

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK if self.path is not None else gui.wx.CANCEL

            def GetPath(self):
                return str(self.path)

        return FakeExportFileDialog

    def _dir_dialog_class(self):
        test = self

        class FakeDirDialog:
            def __init__(self, parent, title):
                test.events.append(("DirDialog", parent, title))
                self.path = test.export_dirs.pop(0)

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def ShowModal(self):
                return gui.wx.ID_OK if self.path is not None else gui.wx.CANCEL

            def GetPath(self):
                return str(self.path)

        return FakeDirDialog

    def _converting_dialog_class(self):
        test = self

        class FakeConvertingDialog:
            def __init__(self, parent):
                test.events.append(("ConvertingDialog", parent))

            def Show(self):
                test.events.append(("dialog.Show",))

            def Raise(self):
                test.events.append(("dialog.Raise",))

            def Unbind(self, event):
                test.events.append(("dialog.Unbind", event))

            def Destroy(self):
                test.events.append(("dialog.Destroy",))

        return FakeConvertingDialog

    def _convert(self, request, *, runtime):
        self.assertIs(runtime, self.runtime)
        self.requests.append(request)
        self.events.append(("convert", request.raw_text))
        outcome = self.outputs[request.raw_text]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    # --- helpers -----------------------------------------------------------

    def _wire_conversion(self, frame) -> None:
        """Today's conversion wiring with the fakes. The only helper that changes during P1-4."""
        frame._convert_dialog = None
        frame._conversion_presenter = gui.ConversionPresenter(
            frame,
            frame._document_controller,
            runtime=frame.translation_runtime,
            build_request=frame._build_conversion_request_for_text,
            get_translation_tables=lambda: frame.translation_tables,
            call_after=self.calls,
            call_later=self.timers,
            thread_factory=self.thread_factory,
            converter=self._convert,
        )
        frame._export_coordinator = gui.ExportCoordinator(
            frame,
            frame._document_controller,
            frame._conversion_presenter,
            call_after=self.calls,
        )

    def _make_frame(self, documents, open_name=None, selected_name=None) -> gui.BrailleFrame:
        frame = gui.BrailleFrame.__new__(gui.BrailleFrame)
        documents = list(documents)
        selected_name = selected_name or open_name
        controller = DocumentController(documents=documents, open_name=open_name, selected_name=selected_name)
        frame._document_controller = controller
        frame._workspace_service = DocumentWorkspaceService(controller, self.workspace)
        open_document = controller.get_document(open_name)
        frame.input_txt = _RecordingEditor("input", self.events, open_document.text if open_document else "")
        frame.output_txt = _RecordingEditor(
            "output", self.events, (open_document.braille or "") if open_document else ""
        )
        names = [document.name for document in documents]
        frame.document_list = _RecordingDocumentList(
            self.events,
            names,
            names.index(selected_name) if selected_name in names else gui.wx.NOT_FOUND,
        )
        frame.SetTitle = lambda title: self.events.append(("title", title))
        frame.GetMenuBar = lambda: self.menu_bar
        frame._dual_view_frame = _RecordingViewer(self.events)
        frame._document_menu_items = {}
        frame.translation_runtime = self.runtime
        frame.translation_tables = dict(self.TABLES)
        frame.translation_settings = TranslationSettings("ascii", 32, "default")
        frame.dictionary_dir = self.root / "dictionary"
        frame._config_store = Mock(spec=gui.ConfigStore)
        frame._config_store.get_lang.return_value = self.LANG
        frame._config_store.get_charset_maps.return_value = dict(self.CHARSET_MAPS)
        self._wire_conversion(frame)
        return frame

    def _take(self) -> list:
        taken = list(self.events)
        self.events.clear()
        return taken

    def _busy(self, busy: bool) -> list:
        return [
            ("FindMenu", gui._("File")),
            ("EnableTop", 0, not busy),
            ("FindMenu", gui._("Translation")),
            ("EnableTop", 1, not busy),
            ("enable", "list", not busy),
            ("enable", "input", not busy),
        ]

    def _box(self, frame, message: str, caption: str, flags: int) -> tuple:
        return ("MessageBox", message, caption, flags, frame)

    def _info(self, frame, message: str, caption: str | None = None) -> tuple:
        caption = gui._("Info") if caption is None else caption
        return self._box(frame, message, caption, gui.wx.OK | gui.wx.ICON_INFORMATION)

    def _error(self, frame, message: str) -> tuple:
        return self._box(frame, message, gui._("Error"), gui.wx.OK | gui.wx.ICON_ERROR)

    def _completed(self, frame) -> tuple:
        return self._info(frame, gui._("Conversion completed."))

    def _exported(self, frame) -> tuple:
        return self._info(frame, gui._("The document was exported successfully."), gui._("Export Complete"))

    def _export_dialog(self, frame, default_file: str) -> tuple:
        return (
            "FileDialog",
            frame,
            gui._("Export Document"),
            default_file,
            gui._("Braille files (*.brl)|*.brl"),
            gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
        )

    def _overwrite_question(self, frame) -> tuple:
        return self._box(
            frame,
            gui._(
                "The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
            ),
            gui._("Confirm Overwrite"),
            gui.wx.YES_NO | gui.wx.ICON_WARNING,
        )

    def _os_error_text(self, path: Path) -> str:
        """``str(exc)`` of writing to ``path`` (a directory), as the BRL writer raises it."""
        try:
            path.write_text("", encoding="utf-8")
        except OSError as exc:
            return str(exc)
        self.fail(f"{path} is writable")

    def _request(self, raw_text: str) -> ConversionRequest:
        return ConversionRequest(
            raw_text=raw_text,
            output_mode="ascii",
            width=32,
            dictionary_path=self.root / "dictionary" / "default.csv",
            data_dir=gui.resource_path("data"),
            translation_tables=self.TABLES,
            lang=self.LANG,
            charset_maps=self.CHARSET_MAPS,
        )

    # --- manual conversion ---------------------------------------------------

    def test_manual_conversion_success_turn_by_turn(self) -> None:
        segment = _dual_view_segment("a", "⠁")
        frame = self._make_frame([Document("alpha", "old text", None), Document("beta", "b", "⠃")], "alpha")
        frame.input_txt.value = "edited text"
        self.outputs["edited text"] = ConversionOutput("⠑⠙", ("result",), (segment,))

        frame.on_convert(None)

        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])
        self.assertEqual([(thread.daemon, thread.started) for thread in self.threads], [(True, True)])
        self.assertEqual(self.requests, [])

        self.threads[0].run()

        self.assertEqual(self._take(), [("convert", "edited text"), ("call_after",)])
        self.assertEqual(self.requests, [self._request("edited text")])
        self.assertIsNot(self.requests[0].translation_tables, frame.translation_tables)
        self.assertEqual(frame.output_txt.value, "")

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("timer.Stop", 1)]
            + self._busy(False)
            + [
                ("set", "output", "⠑⠙"),
                ("focus", "output"),
                ("dual_view.refresh",),
                self._completed(frame),
            ],
        )
        controller = frame._document_controller
        self.assertEqual(controller.documents, [Document("alpha", "edited text", "⠑⠙"), Document("beta", "b", "⠃")])
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
        self.assertIn('<span class="source">a</span>', frame._dual_view_frame.html)
        self.assertEqual(self.calls.pending, [])
        self.assertFalse(self.workspace.exists())

    def test_manual_conversion_without_open_document_updates_output_only(self) -> None:
        frame = self._make_frame([Document("alpha", "a", None)], open_name=None, selected_name="alpha")
        frame.input_txt.value = "loose text"
        self.outputs["loose text"] = ConversionOutput("⠇", ("result",), (_dual_view_segment("l", "⠇"),))

        frame.on_convert(None)
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠇"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
        )
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "a", None)])
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})

    def test_manual_conversion_stores_replaced_text(self) -> None:
        # F-7 (M-7): the conversion, its dual-view segments and the open document's text get
        # U+FFFD; the source editor keeps what the user pasted.
        frame = self._make_frame([Document("alpha", "a", None)], "alpha")
        frame.input_txt.value = "A" + LONE_SURROGATE + "B"
        segment = _dual_view_segment("A�B", "⠁")
        self.outputs["A�B"] = ConversionOutput("⠁", ("result",), (segment,))

        frame.on_convert(None)
        self.threads[0].run()

        self.assertEqual([request.raw_text for request in self.requests], ["A�B"])
        self.calls.run_next()
        controller = frame._document_controller
        self.assertEqual(controller.documents, [Document("alpha", "A�B", "⠁")])
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
        self.assertEqual(frame.input_txt.value, "A" + LONE_SURROGATE + "B")
        self.assertEqual([event for event in self.events if event[:2] == ("set", "input")], [])

    def test_conversion_failure_messages_by_stage_and_public_text(self) -> None:
        cases = (
            (ConversionStageError("ascii", RuntimeError("bad map")), gui._("ASCII conversion failed: {error}"), "bad map"),
            (
                ConversionStageError("text_processing", RuntimeError("script boom")),
                gui._("Text processing failed: {error}"),
                "script boom",
            ),
            (ConversionStageError("translation", RuntimeError("boom")), gui._("Translation failed: {error}"), "boom"),
            (ConversionStageError("other", RuntimeError("odd")), gui._("Translation failed: {error}"), "odd"),
            # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
            (
                ConversionStageError("translation", RuntimeError("")),
                gui._("Translation failed: {error}"),
                "An unknown error occurred.",
            ),
            (
                ConversionStageError("translation", RuntimeError("Can't translate: tables zh-tw.ctb inbuf=12")),
                gui._("Translation failed: {error}"),
                "The selected translation table could not translate this text.",
            ),
        )
        for error, template, error_text in cases:
            with self.subTest(stage=error.stage, error=str(error)):
                self.events.clear()
                self.threads.clear()
                self.timers.timers.clear()
                segment = _dual_view_segment("o", "⠕")
                frame = self._make_frame([Document("alpha", "source", "⠕")], "alpha")
                frame._document_controller.set_dual_view_results("alpha", (segment,))
                self.outputs["source"] = error

                frame.on_convert(None)
                self.threads[0].run()
                self._take()
                self.calls.run_next()

                self.assertEqual(
                    self._take(),
                    [("timer.Stop", 1)] + self._busy(False) + [self._error(frame, template.format(error=error_text))],
                )
                self.assertEqual(frame.output_txt.value, "⠕")
                self.assertEqual(frame._document_controller.documents, [Document("alpha", "source", "⠕")])
                self.assertEqual(frame._document_controller.dual_view_results_by_document, {"alpha": (segment,)})

    def test_convert_while_running_does_nothing(self) -> None:
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        self.outputs["source"] = ConversionOutput("⠎", ())

        frame.on_convert(None)
        self._take()
        frame.on_convert(None)
        frame.on_input_text_key_down(_KeyEvent(13))

        self.assertEqual(self._take(), [])
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(len(self.timers.timers), 1)

    def test_convert_without_default_table_shows_info_only(self) -> None:
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        frame.translation_tables = {"default": "", "math": "nemeth.ctb"}

        frame.on_convert(None)

        self.assertEqual(self._take(), [self._info(frame, gui._("Please select a translation table first."))])
        self.assertEqual(self.threads, [])
        self.assertEqual(self.timers.timers, [])

    def test_converting_dialog_appears_once_and_closes_on_completion(self) -> None:
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        self.outputs["source"] = ConversionOutput("⠎", ())
        frame.on_convert(None)
        self._take()

        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [("ConvertingDialog", frame), ("dialog.Show",), ("dialog.Raise",)])
        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [])

        self.threads[0].run()
        self._take()
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [("timer.Stop", 1), ("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",)]
            + self._busy(False)
            + [("set", "output", "⠎"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
        )

        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [])

    def test_converting_dialog_timer_of_an_earlier_job_does_nothing(self) -> None:
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        self.outputs["source"] = ConversionOutput("⠎", ())
        frame.on_convert(None)
        self.threads[0].run()
        self.calls.run_next()
        frame.on_convert(None)
        self._take()

        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [])
        self.timers.timers[1].fire()
        self.assertEqual(self._take(), [("ConvertingDialog", frame), ("dialog.Show",), ("dialog.Raise",)])

    def test_close_while_running_vetoes_or_saves_and_closes(self) -> None:
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        frame.input_txt.value = "edited"
        self.outputs["edited"] = ConversionOutput("⠑", ())
        frame.on_convert(None)
        self.timers.timers[0].fire()
        self._take()

        frame._on_close(_CloseEvent(self.events, can_veto=True))

        self.assertEqual(self._take(), [("close.Veto",)])
        self.assertFalse(self.workspace.exists())

        frame._on_close(_CloseEvent(self.events, can_veto=False))

        self.assertEqual(
            self._take(),
            [("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",), ("dual_view.Destroy",), ("close.Skip",)],
        )
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
        self.assertIsNone(frame._dual_view_frame)

    # --- single export -------------------------------------------------------

    def test_single_export_with_braille_writes_and_reports(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "⠁⠃")], "alpha")
        target = self.export_dir / "alpha.brl"
        self.export_paths.append(target)

        frame.on_export_document("brl")

        self.assertEqual(self._take(), [self._export_dialog(frame, "alpha.brl"), self._exported(frame)])
        self.assertEqual(target.read_bytes(), "⠁⠃".encode("utf-8"))
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "a", "⠁⠃"))
        self.assertEqual(self.threads, [])

    def test_single_export_write_error_and_extension_correction(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "⠁")], "alpha")
        blocked = self.export_dir / "blocked.brl"
        blocked.mkdir()
        reason = self._os_error_text(blocked)
        self.export_paths.extend([blocked, self.export_dir / "renamed.TXT"])

        frame.on_export_document("brl")

        self.assertEqual(
            self._take(),
            [
                self._export_dialog(frame, "alpha.brl"),
                self._error(frame, gui._("Failed to export document: {error}").format(error=reason)),
            ],
        )

        frame.on_export_document("brl")

        self.assertEqual(self._take(), [self._export_dialog(frame, "alpha.brl"), self._exported(frame)])
        self.assertEqual((self.export_dir / "renamed.brl").read_text(encoding="utf-8"), "⠁")
        self.assertFalse((self.export_dir / "renamed.TXT").exists())

    def test_single_export_of_pending_document_converts_its_text_then_writes(self) -> None:
        frame = self._make_frame(
            [Document("alpha", "alpha text", "⠁"), Document("beta", "beta text", None)],
            open_name="alpha",
            selected_name="beta",
        )
        frame.input_txt.value = "alpha editor"
        frame._document_controller.set_dual_view_results("beta", ("cached",))
        target = self.export_dir / "beta.brl"
        self.export_paths.append(target)
        self.outputs["beta text"] = ConversionOutput("⠃⠃", ("result",), (_dual_view_segment("b", "⠃"),))

        frame.on_export_document("brl")

        self.assertEqual(
            self._take(),
            [self._export_dialog(frame, "beta.brl")] + self._busy(True) + [("call_later", 2000, (1,))],
        )
        self.assertFalse(target.exists())

        self.threads[0].run()
        self.assertEqual(self._take(), [("convert", "beta text"), ("call_after",)])
        self.assertEqual(self.requests, [self._request("beta text")])

        self.calls.run_next()

        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._exported(frame)])
        self.assertEqual(target.read_text(encoding="utf-8"), "⠃⠃")
        self.assertEqual(frame.output_txt.value, "⠁")
        self.assertEqual(
            frame._document_controller.documents,
            [Document("alpha", "alpha editor", "⠁"), Document("beta", "beta text", None)],
        )
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": ("cached",)})

    def test_single_export_of_pending_document_reports_conversion_or_table_error(self) -> None:
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        target = self.export_dir / "alpha.brl"
        self.export_paths.extend([target, target])
        self.outputs["alpha text"] = ConversionStageError("translation", RuntimeError("boom"))

        frame.on_export_document("brl")
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("timer.Stop", 1)]
            + self._busy(False)
            + [self._error(frame, gui._("Translation failed: {error}").format(error="boom"))],
        )
        self.assertFalse(target.exists())

        frame.translation_tables = {"default": ""}
        frame.on_export_document("brl")

        self.assertEqual(
            self._take(),
            [self._export_dialog(frame, "alpha.brl"), self._error(frame, gui._("Please select a translation table first."))],
        )
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(len(self.timers.timers), 1)
        self.assertFalse(target.exists())

    # --- Export All ----------------------------------------------------------

    def test_export_all_mixed_documents_turn_by_turn(self) -> None:
        documents = [
            Document("d1-ready", "t1", "⠁"),
            Document("d2-pending", "t2", None),
            Document("d3-ready", "t3", "⠉"),
            Document("d4-write-fail", "t4", "⠙"),
            Document("d5-convert-fail", "t5", None),
            Document("d6-pending", "t6", None),
        ]
        frame = self._make_frame(documents, "d1-ready")
        blocked = self.export_dir / "d4-write-fail.brl"
        blocked.mkdir()
        write_reason = self._os_error_text(blocked)
        self.export_dirs.append(self.export_dir)
        self.answers.append(gui.wx.YES)
        self.outputs.update(
            t2=ConversionOutput("⠃", ()),
            t5=ConversionStageError("translation", RuntimeError("t5 boom")),
            t6=ConversionOutput("⠋", ()),
        )

        def written() -> dict:
            return {path.name: path.read_text(encoding="utf-8") for path in self.export_dir.glob("*.brl") if path.is_file()}

        frame.on_export_all_documents("brl")

        self.assertEqual(
            self._take(),
            [
                ("DirDialog", frame, gui._("Export All Documents")),
                self._overwrite_question(frame),
                ("call_after",),
            ],
        )
        self.assertEqual(written(), {"d1-ready.brl": "⠁"})

        self.calls.run_next()
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])
        self.threads[0].run()
        self.assertEqual(self._take(), [("convert", "t2"), ("call_after",)])
        self.assertEqual(written(), {"d1-ready.brl": "⠁"})
        self.calls.run_next()
        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [("call_after",)])
        self.assertEqual(written(), {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃"})

        self.calls.run_next()
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()
        self.assertEqual(self._take(), [("call_after",)])
        self.assertEqual(written(), {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃", "d3-ready.brl": "⠉"})

        self.calls.run_next()
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (2,))])
        self.threads[1].run()
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [("convert", "t5"), ("call_after",), ("timer.Stop", 2)] + self._busy(False) + [("call_after",)],
        )

        self.calls.run_next()
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (3,))])
        self.threads[2].run()
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [("convert", "t6"), ("call_after",), ("timer.Stop", 3)] + self._busy(False) + [("call_after",)],
        )

        self.calls.run_next()
        # KNOWN BUG (P1-4 spec, defect 4): the partial-export summary is not translated.
        summary = (
            "Exported documents: 4\n"
            "Failed documents: 2\n"
            "\n"
            f"d4-write-fail: {write_reason}\n"
            f"d5-convert-fail: {gui._('Translation failed: {error}').format(error='t5 boom')}"
        )
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.calls.pending, [])
        self.assertEqual(
            written(),
            {"d1-ready.brl": "⠁", "d2-pending.brl": "⠃", "d3-ready.brl": "⠉", "d6-pending.brl": "⠋"},
        )
        self.assertEqual(frame._document_controller.documents, documents)
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
        self.assertEqual(frame.output_txt.value, "⠁")

    def test_export_all_ready_documents_shows_one_information_summary(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")], "alpha")
        self.export_dirs.append(self.export_dir)

        frame.on_export_all_documents("brl")
        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
        self.calls.run_next()
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        # KNOWN BUG (P1-4 spec, defect 4): the message is not a msgid; only the caption is translated.
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl", "beta.brl"])

    def test_export_all_without_default_table_collects_failures_turn_by_turn(self) -> None:
        frame = self._make_frame([Document("p1", "t1", None), Document("p2", "t2", None)], "p1")
        frame.translation_tables = {}
        self.export_dirs.append(self.export_dir)
        message = gui._("Please select a translation table first.")

        frame.on_export_all_documents("brl")
        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
        self.calls.run_next()
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        summary = f"Exported documents: 0\nFailed documents: 2\n\np1: {message}\np2: {message}"
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.threads, [])
        self.assertEqual(list(self.export_dir.iterdir()), [])

    def test_export_all_folder_and_overwrite_dialogs(self) -> None:
        frame = self._make_frame([Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")], "alpha")

        self.export_dirs.append(None)
        frame.on_export_all_documents("brl")
        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents"))])

        self.export_dirs.append(self.export_dir)
        frame.on_export_all_documents("brl")
        self.assertEqual(self._take(), [("DirDialog", frame, gui._("Export All Documents")), ("call_after",)])
        self.calls.run_all()
        self.events.clear()

        (self.export_dir / "alpha.brl").write_text("old", encoding="utf-8")
        (self.export_dir / "beta.brl").unlink()
        self.export_dirs.append(self.export_dir)
        self.answers.append(gui.wx.NO)
        frame.on_export_all_documents("brl")
        self.assertEqual(
            self._take(),
            [("DirDialog", frame, gui._("Export All Documents")), self._overwrite_question(frame)],
        )
        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl"])
        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "old")

        self.export_dirs.append(self.export_dir)
        self.answers.append(gui.wx.YES)
        frame.on_export_all_documents("brl")
        self.calls.run_all()
        self.assertEqual(
            self._take(),
            [
                ("DirDialog", frame, gui._("Export All Documents")),
                self._overwrite_question(frame),
                ("call_after",),
                ("call_after",),
                self._info(frame, "All documents were exported successfully.", gui._("Export Complete")),
            ],
        )
        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "⠁")
        self.assertEqual((self.export_dir / "beta.brl").read_text(encoding="utf-8"), "⠃")

    # --- re-entrancy (known defects 1 and 2) ----------------------------------

    def test_ctrl_s_during_manual_conversion_supersedes_it(self) -> None:
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        target = self.export_dir / "alpha.brl"
        self.export_paths.append(target)
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ())

        frame.on_convert(None)
        self._take()
        event = _KeyEvent(self.CTRL_S)
        frame.on_output_text_key_down(event)

        # KNOWN BUG (P1-4 spec, defect 2): the export conversion starts without a running check.
        self.assertEqual(
            self._take(),
            [self._export_dialog(frame, "alpha.brl")]
            + self._busy(True)
            + [("call_later", 2000, (2,)), ("focus", "output")],
        )
        self.assertFalse(event.skipped)
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))

        self.threads[0].run()
        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "alpha text"), ("call_after",), ("convert", "alpha text"), ("call_after",)])

        self.calls.run_next()
        self.assertEqual(self._take(), [])

        self.calls.run_next()
        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [self._exported(frame)])
        self.assertEqual(target.read_text(encoding="utf-8"), "⠁⠁")
        self.assertFalse(self.timers.timers[0].stopped)
        self.assertEqual(frame.output_txt.value, "")
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])

    def test_ctrl_tab_during_manual_conversion_sends_result_to_new_document(self) -> None:
        segment = _dual_view_segment("a", "⠁")
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (segment,))

        frame.on_convert(None)
        self._take()
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))

        self.assertEqual(
            self._take(),
            [
                ("set", "input", "beta text"),
                ("set", "output", "⠃"),
                ("title", gui._(gui.format_window_title("beta"))),
                ("dual_view.refresh",),
                ("focus", "input"),
            ],
        )
        self.assertEqual(frame._document_controller.open_document_name, "beta")

        self.threads[0].run()
        self.calls.run_next()

        # KNOWN BUG (P1-4 spec, defect 1): alpha's result lands in beta, the document open now.
        self.assertEqual(
            self._take(),
            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠁⠁"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
        )
        self.assertEqual(
            frame._document_controller.documents,
            [Document("alpha", "alpha text", None), Document("beta", "beta text", "⠁⠁")],
        )
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": (segment,)})

    def test_convert_between_export_all_steps_is_superseded(self) -> None:
        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
        frame.input_txt.value = "manual text"
        self.export_dirs.append(self.export_dir)
        self.outputs.update({"manual text": ConversionOutput("⠍", ()), "t2": ConversionOutput("⠃", ())})

        frame.on_export_all_documents("brl")
        self._take()
        frame.on_convert(None)
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])

        self.calls.run_next()
        # KNOWN BUG (P1-4 spec, defect 2): the next pending step starts a second job; the manual one is dropped.
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (2,))])

        self.threads[0].run()
        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "manual text"), ("call_after",), ("convert", "t2"), ("call_after",)])
        self.calls.run_next()
        self.assertEqual(self._take(), [])
        self.calls.run_next()
        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [("call_after",)])
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(frame.output_txt.value, "⠁")
        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")



class FrameConversionDelegationTest(unittest.TestCase):
    """The frame wires the conversion presenter and hands it the conversion commands."""

    def _make_frame(self) -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame._document_controller = DocumentController()
        frame.translation_runtime = Mock()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        return frame

    def test_initialize_conversion_state_wires_presenter_with_wx_scheduling(self) -> None:
        frame = self._make_frame()

        with patch.object(gui, "ConversionPresenter") as presenter_class:
            frame._initialize_conversion_state()

        presenter_class.assert_called_once_with(
            frame,
            frame._document_controller,
            runtime=frame.translation_runtime,
            build_request=frame._build_conversion_request_for_text,
            get_translation_tables=ANY,
            call_after=gui.wx.CallAfter,
            call_later=gui.wx.CallLater,
        )
        self.assertIs(frame._conversion_presenter, presenter_class.return_value)
        self.assertIsNone(frame._convert_dialog)
        get_tables = presenter_class.call_args.kwargs["get_translation_tables"]
        self.assertIs(get_tables(), frame.translation_tables)
        frame.translation_tables = {"default": "en-ueb-g1.ctb"}
        self.assertIs(get_tables(), frame.translation_tables)

    def test_build_conversion_request_for_text_reads_current_settings(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = TranslationSettings("ascii", 32, "math")
        frame.dictionary_dir = Path("dictionaries")
        frame._config_store = Mock(spec=gui.ConfigStore)
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}

        request = frame._build_conversion_request_for_text("text")

        self.assertEqual(
            request,
            ConversionRequest(
                raw_text="text",
                output_mode="ascii",
                width=32,
                dictionary_path=Path("dictionaries/math.csv"),
                data_dir=gui.resource_path("data"),
                translation_tables={"default": "zh-tw.ctb"},
                lang="zh_TW",
                charset_maps={"CJKCharactersLanguage": "zh"},
            ),
        )

    def test_convert_command_and_ctrl_enter_delegate_to_presenter(self) -> None:
        frame = self._make_frame()
        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)
        event = Mock()
        event.GetKeyCode.return_value = 13
        event.ControlDown.return_value = True

        frame.on_convert(None)
        frame.on_input_text_key_down(event)

        self.assertEqual(frame._conversion_presenter.mock_calls, [call.convert(), call.convert()])
        event.Skip.assert_not_called()

    def test_close_asks_presenter_before_saving(self) -> None:
        frame = self._make_frame()
        steps = Mock()
        frame._conversion_presenter = steps.presenter
        frame._save_open_document = steps.save
        frame.close_converting_dialog = steps.close_converting_dialog
        frame._dual_view_frame = None
        event = steps.event

        steps.presenter.is_running.return_value = True
        event.CanVeto.return_value = True
        frame._on_close(event)
        self.assertEqual(steps.mock_calls, [call.presenter.is_running(), call.event.CanVeto(), call.event.Veto()])

        steps.reset_mock()
        steps.presenter.is_running.return_value = False
        frame._on_close(event)
        self.assertEqual(
            steps.mock_calls,
            [
                call.presenter.is_running(),
                call.event.CanVeto(),
                call.save(),
                call.close_converting_dialog(),
                call.event.Skip(),
            ],
        )


class FrameViewMethodsTest(unittest.TestCase):
    """The frame's small wx methods behind the presenter view protocols."""

    def _make_frame(self, menu_bar=None) -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame.steps = Mock()
        frame.input_txt = frame.steps.input_txt
        frame.output_txt = frame.steps.output_txt
        frame.document_list = frame.steps.document_list
        frame.GetMenuBar = lambda: menu_bar
        frame._convert_dialog = None
        return frame

    def test_get_source_text_reads_the_source_editor(self) -> None:
        frame = self._make_frame()
        frame.input_txt.GetValue.return_value = "source"

        self.assertEqual(frame.get_source_text(), "source")

    def test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor(self) -> None:
        # F-7 (M-7): no SetValue, so the caret stays where it is and NVDA does not re-read.
        frame = self._make_frame()
        frame.input_txt.GetValue.return_value = "A" + LONE_SURROGATE + "B"

        self.assertEqual(frame.get_source_text(), "A�B")
        self.assertEqual(frame.steps.mock_calls, [call.input_txt.GetValue()])

    def test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source(self) -> None:
        menu_bar = Mock()
        menu_bar.FindMenu.side_effect = lambda title: {gui._("File"): 0, gui._("Translation"): 1}.get(
            title, gui.wx.NOT_FOUND
        )
        frame = self._make_frame(menu_bar)
        frame.steps.attach_mock(menu_bar, "menu_bar")

        for busy in (True, False):
            with self.subTest(busy=busy):
                frame.steps.reset_mock()
                frame.set_conversion_busy(busy)
                self.assertEqual(
                    frame.steps.mock_calls,
                    [
                        call.menu_bar.FindMenu(gui._("File")),
                        call.menu_bar.EnableTop(0, not busy),
                        call.menu_bar.FindMenu(gui._("Translation")),
                        call.menu_bar.EnableTop(1, not busy),
                        call.document_list.Enable(not busy),
                        call.input_txt.Enable(not busy),
                    ],
                )

    def test_set_conversion_busy_without_menu_bar_or_menus_still_toggles_controls(self) -> None:
        missing = Mock()
        missing.FindMenu.return_value = gui.wx.NOT_FOUND
        for menu_bar in (None, missing):
            with self.subTest(menu_bar=menu_bar):
                frame = self._make_frame(menu_bar)
                frame.set_conversion_busy(True)
                self.assertEqual(
                    frame.steps.mock_calls,
                    [call.document_list.Enable(False), call.input_txt.Enable(False)],
                )
        missing.EnableTop.assert_not_called()

    def test_converting_dialog_is_shown_once_and_closed_once(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "ConvertingDialog") as dialog_class, patch.object(gui.wx, "EVT_CLOSE", "EVT_CLOSE"):
            frame.show_converting_dialog()
            frame.show_converting_dialog()
            dialog = dialog_class.return_value
            self.assertEqual(dialog_class.call_args_list, [call(frame)])
            self.assertEqual(dialog.mock_calls, [call.Show(), call.Raise()])

            frame.close_converting_dialog()
            frame.close_converting_dialog()

        self.assertEqual(dialog.mock_calls, [call.Show(), call.Raise(), call.Unbind("EVT_CLOSE"), call.Destroy()])
        self.assertIsNone(frame._convert_dialog)

    def test_show_conversion_output_sets_then_focuses_braille_result(self) -> None:
        frame = self._make_frame()

        frame.show_conversion_output("⠃")

        self.assertEqual(frame.steps.mock_calls, [call.output_txt.SetValue("⠃"), call.output_txt.SetFocus()])

    def test_refresh_dual_view_uses_the_frame_refresh(self) -> None:
        frame = self._make_frame()
        frame._refresh_dual_view = Mock()

        frame.refresh_dual_view()

        frame._refresh_dual_view.assert_called_once_with()

    def test_message_methods_use_one_message_box_each(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame.show_info("info text", "Info caption")
            frame.show_error("error text", "Error caption")

        self.assertEqual(
            message_box.call_args_list,
            [
                call("info text", "Info caption", gui.wx.OK | gui.wx.ICON_INFORMATION, parent=frame),
                call("error text", "Error caption", gui.wx.OK | gui.wx.ICON_ERROR, parent=frame),
            ],
        )

    def test_about_box_uses_the_helper(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame.on_about(None)

        message_box.assert_called_once_with(
            gui.about.aboutMessage, gui._("About DotExpress"), gui.wx.OK | gui.wx.ICON_INFORMATION, parent=frame
        )

    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame._show_file_error("Failed: {error}", OSError("disk full"))

        message_box.assert_called_once_with(
            "Failed: disk full", gui._("Error"), gui.wx.OK | gui.wx.ICON_ERROR, parent=frame
        )
        self.assertEqual(
            list(inspect.signature(gui.BrailleFrame._show_file_error).parameters),
            ["self", "message", "error"],
        )



class FrameExportDelegationTest(unittest.TestCase):
    """The frame wires the export coordinator; the entry points keep their guards and save first."""

    def _make_frame(self, documents=(Document("alpha", "a", None), Document("beta", "b", "⠃"))) -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame._document_controller = DocumentController(documents=list(documents), open_name="alpha")
        frame.steps = Mock()
        frame._export_coordinator = frame.steps.coordinator
        frame._save_open_document_with_feedback = frame.steps.save
        frame.output_txt = frame.steps.output_txt
        frame.steps.save.return_value = True
        return frame

    def test_initialize_conversion_state_wires_coordinator_to_presenter(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame._document_controller = DocumentController()
        frame.translation_runtime = Mock()

        with patch.object(gui, "ConversionPresenter") as presenter_class, patch.object(
            gui, "ExportCoordinator"
        ) as coordinator_class:
            frame._initialize_conversion_state()

        coordinator_class.assert_called_once_with(
            frame,
            frame._document_controller,
            presenter_class.return_value,
            call_after=gui.wx.CallAfter,
        )
        self.assertIs(frame._export_coordinator, coordinator_class.return_value)

    def test_export_menu_saves_then_exports_the_reread_selection(self) -> None:
        frame = self._make_frame()
        frame._get_selected_document = Mock(
            side_effect=[Document("beta", "b", "⠃"), Document("beta", "b2", "⠃⠃")]
        )

        frame.on_export_document("html")

        self.assertEqual(
            frame.steps.mock_calls,
            [call.save(), call.coordinator.export_document(Document("beta", "b2", "⠃⠃"), "html")],
        )

    def test_export_menu_without_selection_or_with_failed_save_does_nothing_more(self) -> None:
        frame = self._make_frame()
        frame._get_selected_document = Mock(return_value=None)
        frame.on_export_document("brl")
        self.assertEqual(frame.steps.mock_calls, [])

        frame._get_selected_document = Mock(return_value=Document("beta", "b", "⠃"))
        frame.steps.save.return_value = False
        frame.on_export_document("brl")
        self.assertEqual(frame.steps.mock_calls, [call.save()])

    def test_export_all_menu_keeps_guards_and_save_first(self) -> None:
        frame = self._make_frame(documents=())
        frame.on_export_all_documents("dep")
        self.assertEqual(frame.steps.mock_calls, [])

        frame = self._make_frame()
        frame.steps.save.return_value = False
        frame.on_export_all_documents("dep")
        self.assertEqual(frame.steps.mock_calls, [call.save()])

        frame.steps.reset_mock()
        frame.steps.save.return_value = True
        frame.on_export_all_documents("dep")
        self.assertEqual(frame.steps.mock_calls, [call.save(), call.coordinator.export_all("dep")])

    def test_ctrl_s_without_open_document_or_with_failed_save_only_refocuses(self) -> None:
        event = Mock()
        event.GetKeyCode.return_value = 83
        event.ControlDown.return_value = True
        frame = self._make_frame()
        frame._document_controller.open_name = None
        frame.on_output_text_key_down(event)
        self.assertEqual(frame.steps.mock_calls, [call.save(), call.output_txt.SetFocus()])

        frame = self._make_frame()
        frame.steps.save.return_value = False
        frame.on_output_text_key_down(event)
        self.assertEqual(frame.steps.mock_calls, [call.save(), call.output_txt.SetFocus()])
        event.Skip.assert_not_called()


class FrameExportViewMethodsTest(unittest.TestCase):
    """The frame's dialogs behind ``ExportView``."""

    def _dialog(self, result, path: str = ""):
        dialog = Mock()
        dialog.__enter__ = Mock(return_value=dialog)
        dialog.__exit__ = Mock(return_value=False)
        dialog.ShowModal.return_value = result
        dialog.GetPath.return_value = path
        return dialog

    def test_choose_export_path_shows_the_save_dialog(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        for result, expected in ((gui.wx.ID_OK, Path("/tmp/out.brl")), (gui.wx.CANCEL, None)):
            with self.subTest(result=result):
                dialog_class = Mock(return_value=self._dialog(result, "/tmp/out.brl"))
                with patch.object(gui.wx, "FileDialog", dialog_class), patch.object(gui, "_", fake_translate):
                    chosen = frame.choose_export_path("alpha.brl", gui.get_format("brl"))

                self.assertEqual(chosen, expected)
                dialog_class.assert_called_once_with(
                    frame,
                    "T[Export Document]",
                    defaultFile="alpha.brl",
                    wildcard="T[Braille files (*.brl)|*.brl]",
                    style=gui.wx.FD_SAVE | gui.wx.FD_OVERWRITE_PROMPT,
                )

    def test_choose_export_directory_shows_the_folder_dialog(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        for result, expected in ((gui.wx.ID_OK, Path("/tmp/folder")), (gui.wx.CANCEL, None)):
            with self.subTest(result=result):
                dialog_class = Mock(return_value=self._dialog(result, "/tmp/folder"))
                with patch.object(gui.wx, "DirDialog", dialog_class):
                    chosen = frame.choose_export_directory()

                self.assertEqual(chosen, expected)
                dialog_class.assert_called_once_with(frame, gui._("Export All Documents"))

    def test_confirm_overwrite_all_asks_only_for_conflicts(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui, "message_box") as message_box:
            self.assertTrue(frame.confirm_overwrite_all([]))
            message_box.assert_not_called()
            for answer, expected in ((gui.wx.YES, True), (gui.wx.NO, False)):
                with self.subTest(answer=answer):
                    message_box.reset_mock()
                    message_box.return_value = answer
                    self.assertIs(frame.confirm_overwrite_all([Path("/tmp/alpha.brl")]), expected)
                    message_box.assert_called_once_with(
                        gui._(
                            "The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
                        ),
                        gui._("Confirm Overwrite"),
                        gui.wx.YES_NO | gui.wx.ICON_WARNING,
                        parent=frame,
                    )

    def test_show_warning_uses_the_warning_icon(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui, "message_box") as message_box:
            frame.show_warning("warning text", "Warning caption")

        message_box.assert_called_once_with(
            "warning text", "Warning caption", gui.wx.OK | gui.wx.ICON_WARNING, parent=frame
        )


class _RecordingFont:
    """``wx.Font`` stand-in: the font it copies and the calls made on it."""

    def __init__(self, base):
        self.base = base
        self.calls = []

    def SetPointSize(self, size):
        self.calls.append(("SetPointSize", size))

    def SetFaceName(self, name):
        self.calls.append(("SetFaceName", name))


class EditorViewSettingsCharacterizationTest(unittest.TestCase):
    """P2-3 characterization: the editor colours of each scheme and the SimBraille face rule."""

    LIGHT = ((255, 255, 255), (0, 0, 0))
    DARK = ((0, 0, 0), (255, 255, 255))

    def test_view_schemes_give_each_scheme_its_editor_colours(self) -> None:
        self.assertEqual(
            gui.VIEW_SCHEMES,
            {
                "light": {"background": (255, 255, 255), "foreground": (0, 0, 0)},
                "dark": {"background": (0, 0, 0), "foreground": (255, 255, 255)},
            },
        )
        self.assertEqual(list(gui.VIEW_SCHEMES), ["light", "dark"])
        for colours in gui.VIEW_SCHEMES.values():
            self.assertEqual(list(colours), ["background", "foreground"])
            for colour in colours.values():
                self.assertIsInstance(colour, gui.wx.Colour)

    def test_apply_editor_view_settings_sets_size_colours_and_the_simbraille_face(self) -> None:
        cases = (
            # settings, font registered, platform, expected size, colours, SimBraille face
            (ViewSettings(14, "light", "simbraille"), True, "linux", 14, self.LIGHT, True),
            (ViewSettings(14, "dark", "simbraille"), False, "linux", 14, self.DARK, False),
            (ViewSettings(14, "dark", "simbraille"), False, "win32", 14, self.DARK, True),
            (ViewSettings(20, "light", "default"), True, "win32", 20, self.LIGHT, False),
            (ViewSettings(99, "sepia", "serif"), True, "linux", 48, self.LIGHT, True),
        )
        for settings, registered, platform, size, (background, foreground), face in cases:
            with self.subTest(settings=settings, registered=registered, platform=platform):
                frame = object.__new__(gui.BrailleFrame)
                frame.steps = Mock()
                frame.input_txt = frame.steps.input_txt
                frame.output_txt = frame.steps.output_txt
                frame.Layout = frame.steps.Layout
                frame._default_output_font = "default-output-font"
                frame._simbraille_font_available = registered
                with (
                    patch.object(gui.wx, "Font", _RecordingFont),
                    patch.object(gui, "sys", SimpleNamespace(platform=platform)),
                ):
                    frame._apply_editor_view_settings(settings)

                output_font = frame.output_txt.SetFont.call_args.args[0]
                self.assertEqual(output_font.base, "default-output-font")
                self.assertEqual(
                    output_font.calls,
                    [("SetPointSize", size)] + ([("SetFaceName", "SimBraille")] if face else []),
                )
                frame.input_txt.GetFont.return_value.SetPointSize.assert_called_once_with(size)
                self.assertEqual(
                    [entry for entry in frame.steps.mock_calls if entry[0].endswith(("Colour", "Refresh", "Layout"))],
                    [
                        call.input_txt.SetBackgroundColour(background),
                        call.input_txt.SetForegroundColour(foreground),
                        call.input_txt.Refresh(),
                        call.output_txt.SetBackgroundColour(background),
                        call.output_txt.SetForegroundColour(foreground),
                        call.output_txt.Refresh(),
                        call.Layout(),
                    ],
                )



class ViewFontSizeSyncCharacterizationTest(unittest.TestCase):
    """P2-4 characterization: Ctrl+wheel in an editor and the open settings dialog's font size."""

    FRAME_VIEW = ViewSettings(12, "dark", "default")
    DIALOG_VIEW = ViewSettings(12, "light", "simbraille")

    def make_frame(self, view=FRAME_VIEW) -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame.view_settings = view
        frame._apply_editor_view_settings = Mock()
        frame._config_store = Mock(spec=gui.ConfigStore)
        return frame

    def make_dialog(self):
        dialog = object.__new__(gui.DotExpressSettingsDialog)
        dialog.snapshot = make_snapshot(view=self.DIALOG_VIEW)
        dialog.panel_instances = {}
        dialog.Destroy = Mock()
        dialog.window_calls = Mock()
        for name in ("Iconize", "Raise", "SetFocus", "Show"):
            setattr(dialog, name, getattr(dialog.window_calls, name))
        return dialog

    @staticmethod
    def wheel(rotation, control_down=True):
        return SimpleNamespace(
            GetWheelRotation=lambda: rotation,
            ControlDown=lambda: control_down,
            Skip=Mock(),
        )

    @staticmethod
    def open_dialog(dialog):
        return patch.object(gui.DotExpressSettingsDialog, "_instance", dialog)

    def test_ctrl_wheel_saves_then_syncs_only_the_font_size_into_the_open_dialog(self) -> None:
        frame = self.make_frame()
        dialog = self.make_dialog()
        dialog_size_when_saved = []
        event = self.wheel(120)

        with (
            self.open_dialog(dialog),
            patch.object(
                gui,
                "save_view_settings",
                side_effect=lambda _store, _view: dialog_size_when_saved.append(dialog.snapshot.view.font_size),
            ) as save,
        ):
            frame.on_editor_mousewheel(event)

        expected = ViewSettings(13, "dark", "default")
        self.assertEqual(frame.view_settings, expected)
        frame._apply_editor_view_settings.assert_called_once_with(expected)
        save.assert_called_once_with(frame._config_store, expected)
        self.assertEqual(dialog_size_when_saved, [12])
        self.assertEqual(dialog.snapshot, make_snapshot(view=ViewSettings(13, "light", "simbraille")))
        self.assertEqual(dialog.window_calls.mock_calls, [])  # the editor keeps the focus
        event.Skip.assert_not_called()

    def test_a_clamped_step_still_saves_and_syncs_the_clamped_size(self) -> None:
        for start, rotation in ((8, -120), (48, 120)):
            with self.subTest(start=start, rotation=rotation):
                frame = self.make_frame(ViewSettings(start, "dark", "default"))
                dialog = self.make_dialog()
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
                    frame.on_editor_mousewheel(self.wheel(rotation))

                # KNOWN QUIRK (P2-4 spec, 1): the size did not change, but it is saved and synced again.
                expected = ViewSettings(start, "dark", "default")
                self.assertEqual(frame.view_settings, expected)
                frame._apply_editor_view_settings.assert_called_once_with(expected)
                save.assert_called_once_with(frame._config_store, expected)
                self.assertEqual(dialog.snapshot.view, ViewSettings(start, "light", "simbraille"))

    def test_a_wheel_without_a_step_is_skipped_and_changes_nothing(self) -> None:
        for rotation, control_down in ((120, False), (-120, False), (0, True)):
            with self.subTest(rotation=rotation, control_down=control_down):
                frame = self.make_frame()
                dialog = self.make_dialog()
                event = self.wheel(rotation, control_down)
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
                    frame.on_editor_mousewheel(event)

                event.Skip.assert_called_once_with()
                self.assertEqual(frame.view_settings, self.FRAME_VIEW)
                frame._apply_editor_view_settings.assert_not_called()
                save.assert_not_called()
                self.assertEqual(dialog.snapshot.view, self.DIALOG_VIEW)

    def test_without_an_open_dialog_the_editors_and_the_config_still_change(self) -> None:
        frame = self.make_frame()
        with self.open_dialog(None), patch.object(gui, "save_view_settings") as save:
            frame.on_editor_mousewheel(self.wheel(-120))

        expected = ViewSettings(11, "dark", "default")
        self.assertEqual(frame.view_settings, expected)
        frame._apply_editor_view_settings.assert_called_once_with(expected)
        save.assert_called_once_with(frame._config_store, expected)

    def test_a_cancelled_dialog_is_no_longer_synced(self) -> None:
        frame = self.make_frame()
        dialog = self.make_dialog()
        with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
            frame.on_editor_mousewheel(self.wheel(120))
            dialog.on_cancel()
            self.assertIsNone(gui.DotExpressSettingsDialog._instance)
            frame.on_editor_mousewheel(self.wheel(120))

        dialog.Destroy.assert_called_once_with()
        self.assertEqual(frame.view_settings, ViewSettings(14, "dark", "default"))
        self.assertEqual(
            save.call_args_list,
            [
                call(frame._config_store, ViewSettings(13, "dark", "default")),
                call(frame._config_store, ViewSettings(14, "dark", "default")),
            ],
        )
        self.assertEqual(dialog.snapshot.view, ViewSettings(13, "light", "simbraille"))

    def test_an_open_text_processing_dialog_is_left_alone(self) -> None:
        frame = self.make_frame()
        text_dialog = Mock()
        with (
            patch.object(gui.TextProcessingDialog, "_instance", text_dialog),
            self.open_dialog(None),
            patch.object(gui, "save_view_settings") as save,
        ):
            frame.on_editor_mousewheel(self.wheel(120))

        save.assert_called_once_with(frame._config_store, ViewSettings(13, "dark", "default"))
        self.assertEqual(text_dialog.mock_calls, [])


class ApplicationPathsWiringCharacterizationTest(unittest.TestCase):
    """P2-6 characterization: the frame keeps all of its application data under one root.

    Every test gets its frame from ``make_frame``, the only part that changes when the
    application paths and the config store are injected (P2-6 steps 3 and 4).
    """

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name) / "application"
        self.root.mkdir()
        self.config_path = self.root / "config.json"

    def make_frame(self) -> gui.BrailleFrame:
        """A bare frame whose application data lives under ``self.root``.

        The frame gets paths built from the root and one config store for them. The real
        application root points at an empty decoy folder, so anything still resolved
        implicitly misses ``self.root`` and never reaches ``client/``.
        """
        decoy = self.root.parent / "decoy"
        patcher = patch.object(app_paths, "get_application_root", return_value=decoy)
        patcher.start()
        self.addCleanup(patcher.stop)
        frame = object.__new__(gui.BrailleFrame)
        frame._paths = app_paths.build_application_paths(self.root)
        frame._config_store = config.ConfigStore(frame._paths.config)
        return frame

    def write_config(self, data: dict) -> None:
        self.config_path.write_text(json.dumps(data), encoding="utf-8")

    def root_entries(self) -> list[str]:
        return sorted(path.name for path in self.root.iterdir())

    def test_initialize_state_keeps_dictionaries_workspace_and_settings_under_the_root(self) -> None:
        self.write_config(
            {
                "conversion": {
                    "output_mode": "ascii",
                    "width": 52,
                    "selected_dictionary": "alpha",
                    "translation_tables": {"default": "en-ueb-g1.ctb"},
                },
                "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
            }
        )
        (self.root / "dictionary").mkdir()
        (self.root / "dictionary" / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
        frame = self.make_frame()
        frame._document_controller = DocumentController()
        frame._register_output_font = Mock(return_value=False)

        view = frame._initialize_state()

        self.assertEqual(frame.dictionary_dir, self.root / "dictionary")
        self.assertEqual(frame._dictionary_presenter.dictionary_dir, self.root / "dictionary")
        self.assertTrue((self.root / "dictionary" / "default.csv").is_file())
        self.assertEqual(frame._workspace_service.workspace_dir, self.root / "workspace")
        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "alpha"))
        self.assertEqual(frame.translation_tables, {**gui.DEFAULT_TRANSLATION_TABLES, "default": "en-ueb-g1.ctb"})
        self.assertEqual(view, ViewSettings(18, "dark", "default"))
        self.assertIs(frame.view_settings, view)
        self.assertEqual(self.root_entries(), ["config.json", "dictionary"])

    def test_selecting_a_dictionary_writes_the_config_file_under_the_root(self) -> None:
        frame = self.make_frame()
        frame.translation_settings = TranslationSettings("ascii", 52, "alpha")

        frame._set_active_dictionary("點字")

        expected = {
            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
            "conversion": {"selected_dictionary": "點字"},
        }
        self.assertEqual(
            self.config_path.read_text(encoding="utf-8"),
            json.dumps(expected, ensure_ascii=False, indent=2),
        )
        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "點字"))
        self.assertEqual(self.root_entries(), ["config.json"])

    def test_dual_view_html_is_written_under_the_root(self) -> None:
        frame = self.make_frame()
        frame.GetSize = Mock(return_value=(800, 600))
        frame._render_dual_view_for_open_document = Mock(return_value="<html>雙視</html>")
        frame._show_file_error = Mock()

        with patch.object(gui, "open_html_in_browser") as open_browser:
            frame.on_open_dual_view(None)

        written = sorted((self.root / "dual_view").glob("dual-view-*.html"))
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0].read_text(encoding="utf-8"), "<html>雙視</html>")
        open_browser.assert_called_once_with(written[0], (800, 600))
        frame._show_file_error.assert_not_called()
        self.assertEqual(self.root_entries(), ["dual_view"])

    def test_each_conversion_request_reads_the_language_settings_from_the_root_config(self) -> None:
        frame = self.make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        reads: list[str] = []
        real_open = open

        def counting_open(file, mode="r", *args, **kwargs):
            if str(file) == str(self.config_path) and "r" in mode:
                reads.append(str(file))
            return real_open(file, mode, *args, **kwargs)

        self.write_config({"language": "en", "language_detection": {"charset_maps": {"latinCharactersLanguage": "fr"}}})
        with (
            patch.dict(os.environ),
            patch.object(config, "_runtime_lang", None),
            patch("builtins.open", counting_open),
        ):
            os.environ.pop(config.LANG_ENV, None)
            first = frame._build_conversion_request("x", "unicode", 40, Path("d.csv"))
            reads_after_first = len(reads)
            self.write_config({"language": "ja"})
            second = frame._build_conversion_request("x", "unicode", 40, Path("d.csv"))

        self.assertEqual(first.lang, "en")
        self.assertEqual(first.charset_maps, {**config.DEFAULT_CHARSET_MAPS, "latinCharactersLanguage": "fr"})
        self.assertEqual(second.lang, "ja")
        self.assertEqual(second.charset_maps, config.DEFAULT_CHARSET_MAPS)
        self.assertEqual((reads_after_first, len(reads)), (2, 4))
        self.assertEqual(self.root_entries(), ["config.json"])


if __name__ == "__main__":
    unittest.main()
