from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import documents.export_coordinator as coordinator_module
from ui.conversion_presenter import ConversionPresenter
from conversion.output import DualViewSegment
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
from documents.formats import ExportContext, get_format
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs

COORDINATOR_PATH = Path(__file__).resolve().parents[1] / "documents" / "export_coordinator.py"
MISSING_TABLE = "missing table"
LOGGER = "dotexpress.gui"
# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)
# The Export All summary as the user sees it (F-12 D1; it was English, P1-4 defect 4).
ALL_EXPORTED = "所有文件皆已成功匯出。"
EXPORTED_WITH_ERRORS = "匯出完成，但有錯誤"


def setUpModule() -> None:
    # The coordinator logs unexpected export errors to gui.log (F-7); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


def _segment(raw: str, braille: str) -> DualViewSegment:
    """One dual-view segment showing ``raw`` above ``braille``."""
    return DualViewSegment(
        result=SimpleNamespace(raw=[raw], braille=[braille], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
        source_kind="text",
    )


def _writer_failing_for(name: str, error: Exception):
    """The BRL writer, except that it raises ``error`` for the document called ``name``."""
    write_brl = get_format("brl").writer

    def writer(path, document, context):
        if document.name == name:
            raise error
        return write_brl(path, document, context)

    return writer


class RecordingExportView:
    """Implements ``ExportView`` (and ``ConversionView`` for the integration test)."""

    def __init__(self, events: list):
        self.events = events
        self.paths: list = []
        self.directories: list = []
        self.overwrite_answers: list = []

    def choose_export_path(self, default_file, descriptor):
        self.events.append(("choose_export_path", default_file, descriptor.key))
        return self.paths.pop(0)

    def choose_export_directory(self):
        self.events.append(("choose_export_directory",))
        return self.directories.pop(0)

    def confirm_overwrite_all(self, conflicts):
        self.events.append(("confirm_overwrite_all", [path.name for path in conflicts]))
        return self.overwrite_answers.pop(0)

    def show_info(self, message, caption):
        self.events.append(("show_info", message, caption))

    def show_warning(self, message, caption):
        self.events.append(("show_warning", message, caption))

    def show_error(self, message, caption):
        self.events.append(("show_error", message, caption))

    # ConversionView, used only with a real ConversionPresenter
    def get_source_text(self):
        return ""

    def set_conversion_busy(self, busy):
        self.events.append(("busy", busy))

    def show_converting_dialog(self):
        self.events.append(("show_converting_dialog",))

    def close_converting_dialog(self):
        self.events.append(("close_converting_dialog",))

    def show_conversion_output(self, text):
        self.events.append(("show_conversion_output", text))

    def refresh_dual_view(self):
        self.events.append(("refresh_dual_view",))


class FakeExportConversions:
    """Implements ``ExportConversions``; the test calls the stored callbacks."""

    def __init__(self, events: list):
        self.events = events
        self.missing_message: str | None = None
        self.started: list = []

    def missing_table_message(self):
        self.events.append(("missing_table_message",))
        return self.missing_message

    def convert_for_export(self, raw_text, *, on_success, on_error):
        self.events.append(("convert_for_export", raw_text))
        self.started.append((on_success, on_error))


class ExportCoordinatorTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.events: list = []
        self.view = RecordingExportView(self.events)
        self.conversions = FakeExportConversions(self.events)
        self.calls = DeferredCalls(self.events)
        self.documents = DocumentController(documents=[Document("alpha", "a", "⠁"), Document("beta", "b", None)])
        self.coordinator = ExportCoordinator(self.view, self.documents, self.conversions, call_after=self.calls)

    def _take(self) -> list:
        taken = list(self.events)
        self.events.clear()
        return taken

    def _written(self) -> dict:
        return {path.name: path.read_text(encoding="utf-8") for path in sorted(self.root.glob("*.brl")) if path.is_file()}

    def _exported(self) -> tuple:
        return ("show_info", _("The document was exported successfully."), _("Export Complete"))

    def _all_exported(self) -> tuple:
        return ("show_info", ALL_EXPORTED, "匯出完成")

    def _os_error_text(self, path: Path) -> str:
        try:
            path.write_text("", encoding="utf-8")
        except OSError as exc:
            return str(exc)
        self.fail(f"{path} is writable")

    def test_module_imports_neither_wx_nor_gui(self) -> None:
        tree = ast.parse(COORDINATOR_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])

        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)

    def test_importing_binds_no_log_file(self) -> None:
        # The gui.log handler is bound when the first error is logged (as in F-6 review M-6), so a
        # test that imports the coordinator without isolating the logger cannot write to log/.
        script = (
            "import logging\n"
            "import documents.export_coordinator\n"
            "handlers = logging.getLogger('dotexpress.gui').handlers\n"
            "assert handlers == [], handlers\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=COORDINATOR_PATH.parents[1],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    # --- write_document --------------------------------------------------------

    def test_write_document_uses_registry_writer(self) -> None:
        document = Document("alpha", "text", "braille")
        writer = Mock()
        descriptor = replace(get_format("dep"), writer=writer)

        with patch.object(coordinator_module, "get_format", return_value=descriptor) as get_format_mock:
            self.coordinator.write_document(Path("/tmp/custom.dep"), document, "dep")

        get_format_mock.assert_called_once_with("dep")
        writer.assert_called_once_with(Path("/tmp/custom.dep"), document, ExportContext())

    def test_write_document_passes_cached_results_to_every_writer(self) -> None:
        document = Document("alpha", "text", "braille")
        cached_results = (Mock(),)
        self.documents.set_dual_view_results("alpha", cached_results)
        for key in ("dep", "brl", "html"):
            with self.subTest(format_key=key):
                writer = Mock()
                descriptor = replace(get_format(key), writer=writer)
                with patch.object(coordinator_module, "get_format", return_value=descriptor):
                    self.coordinator.write_document(Path(f"/tmp/custom.{key}"), document, key)

                writer.assert_called_once_with(
                    Path(f"/tmp/custom.{key}"),
                    document,
                    ExportContext(dual_view_results=cached_results),
                )

    def test_write_document_reads_the_cache_of_the_written_document(self) -> None:
        self.documents.set_dual_view_results("alpha", ("alpha-cache",))
        writer = Mock()
        descriptor = replace(get_format("html"), writer=writer)

        with patch.object(coordinator_module, "get_format", return_value=descriptor):
            self.coordinator.write_document(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), "html")

        writer.assert_called_once_with(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), ExportContext())

    def test_write_document_uses_the_given_results_instead_of_the_cache(self) -> None:
        # F-9 D6: None reads the cache, as before; a tuple, even an empty one, is used as it is.
        self.documents.set_dual_view_results("alpha", ("alpha-cache",))
        document = Document("alpha", "text", "braille")
        for given, expected in ((None, ("alpha-cache",)), ((), ()), (("fresh",), ("fresh",))):
            with self.subTest(given=given):
                writer = Mock()
                descriptor = replace(get_format("html"), writer=writer)
                with patch.object(coordinator_module, "get_format", return_value=descriptor):
                    self.coordinator.write_document(Path("/tmp/alpha.html"), document, "html", dual_view_results=given)

                writer.assert_called_once_with(Path("/tmp/alpha.html"), document, ExportContext(dual_view_results=expected))

        self.coordinator.write_document(self.root / "alpha.html", document, "html", dual_view_results=())
        # The page's text in zh_TW, as the in-app Dual View shows it (F-12 D8).
        self.assertIn("此文件沒有可顯示的轉換資料。", (self.root / "alpha.html").read_text(encoding="utf-8"))

    def test_write_document_rejects_non_exportable_format(self) -> None:
        descriptor = replace(get_format("txt"), writer=Mock())

        with patch.object(coordinator_module, "get_format", return_value=descriptor):
            with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
                self.coordinator.write_document(Path("/tmp/custom.txt"), Document("alpha", "t", "b"), "txt")

        descriptor.writer.assert_not_called()

    # --- export_document ---------------------------------------------------------

    def test_export_document_passes_default_file_and_descriptor_and_stops_on_cancel(self) -> None:
        self.view.paths.append(None)

        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(self._take(), [("choose_export_path", "alpha.brl", "brl")])
        self.assertEqual(self._written(), {})

    def test_export_document_with_braille_writes_and_reports(self) -> None:
        self.view.paths.append(self.root / "alpha.brl")

        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(self._take(), [("choose_export_path", "alpha.brl", "brl"), self._exported()])
        self.assertEqual(self._written(), {"alpha.brl": "⠁"})

    def test_export_document_corrects_only_a_wrong_extension(self) -> None:
        for chosen, written in (("out.TXT", "out.brl"), ("out.BRL", "out.BRL")):
            with self.subTest(chosen=chosen):
                self.coordinator.write_document = Mock()
                self.view.paths.append(self.root / chosen)

                self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

                self.coordinator.write_document.assert_called_once_with(
                    self.root / written, Document("alpha", "a", "⠁"), "brl"
                )

    def test_export_document_write_error_shows_one_error(self) -> None:
        blocked = self.root / "blocked.brl"
        blocked.mkdir()
        reason = self._os_error_text(blocked)
        self.view.paths.append(blocked)

        self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(
            self._take(),
            [
                ("choose_export_path", "alpha.brl", "brl"),
                ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
            ],
        )

    def test_single_export_error_that_is_not_an_os_error_shows_the_failure_message(self) -> None:
        # F-7: before, the exception left the menu handler; the packaged build showed nothing.
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("alpha", error))
        self.view.paths.append(self.root / "alpha.brl")

        with (
            patch.object(coordinator_module, "get_format", return_value=descriptor),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(
            self._take(),
            [
                ("choose_export_path", "alpha.brl", "brl"),
                ("show_error", _("Failed to export document: {error}").format(error="injected"), _("Error")),
            ],
        )
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_single_export_os_error_is_not_logged(self) -> None:
        blocked = self.root / "blocked.brl"
        blocked.mkdir()
        reason = self._os_error_text(blocked)
        self.view.paths.append(blocked)

        with self.assertNoLogs(LOGGER, level="ERROR"):
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(
            self._take()[-1],
            ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
        )

    def test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure(self) -> None:
        # The M-7 trigger: the dual-view segments carry the source text, and UTF-8 cannot
        # encode a lone surrogate. The frame now replaces it before converting (F-7 D5).
        result = SimpleNamespace(
            raw=["A" + LONE_SURROGATE + "B"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]
        )
        self.documents.set_dual_view_results("alpha", (DualViewSegment(result=result, source_kind="text"),))
        self.view.paths.append(self.root / "alpha.html")

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "html")

        kind, message, caption = self._take()[-1]
        self.assertEqual((kind, caption), ("show_error", _("Error")))
        self.assertTrue(message.startswith(_("Failed to export document: {error}").format(error="")), message)
        self.assertIn("surrogates not allowed", message)
        self.assertIsInstance(logs.records[0].exc_info[1], UnicodeEncodeError)

    def test_pending_export_failure_after_conversion_is_reported(self) -> None:
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("beta", error))
        self.view.paths.append(self.root / "beta.brl")

        with patch.object(coordinator_module, "get_format", return_value=descriptor):
            self.coordinator.export_document(Document("beta", "b", None), "brl")
            self._take()
            on_success, _on_error = self.conversions.started[0]
            with self.assertLogs(LOGGER, level="ERROR") as logs:
                on_success(ConversionOutput("⠃⠃", ()))

        self.assertEqual(
            self._take(),
            [("show_error", _("Failed to export document: {error}").format(error="injected"), _("Error"))],
        )
        self.assertIs(logs.records[0].exc_info[1], error)
        self.assertEqual(self._written(), {})

    def test_export_document_pending_converts_document_text_then_writes(self) -> None:
        self.view.paths.append(self.root / "beta.brl")

        self.coordinator.export_document(Document("beta", "b", None), "brl")

        self.assertEqual(
            self._take(),
            [("choose_export_path", "beta.brl", "brl"), ("missing_table_message",), ("convert_for_export", "b")],
        )
        self.assertEqual(self._written(), {})

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃⠃", ()))

        self.assertEqual(self._take(), [self._exported()])
        self.assertEqual(self._written(), {"beta.brl": "⠃⠃"})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

    def test_export_document_pending_conversion_error_shows_it(self) -> None:
        # The exported document is the open one: the message is not named (F-12 D7).
        self.documents.open_document("beta")
        self.view.paths.append(self.root / "beta.brl")
        self.coordinator.export_document(Document("beta", "b", None), "brl")
        self._take()

        _on_success, on_error = self.conversions.started[0]
        on_error("boom")

        self.assertEqual(self._take(), [("show_error", "boom", _("Error"))])
        self.assertEqual(self._written(), {})

    def test_a_failed_export_of_a_document_that_is_not_open_names_it(self) -> None:
        # F-12 (D7): the open document at delivery decides, not the one at the request.
        cases = (
            ("another document open", "alpha", "alpha", True),
            ("opened during the conversion", "alpha", "beta", False),
            ("switched away during the conversion", "beta", "alpha", True),
        )
        for label, open_at_request, open_at_delivery, named in cases:
            with self.subTest(label):
                self.events.clear()
                self.conversions.started.clear()
                self.documents.open_document(open_at_request)
                self.view.paths.append(self.root / "beta.brl")
                self.coordinator.export_document(Document("beta", "b", None), "brl")
                self._take()
                self.documents.open_document(open_at_delivery)

                _on_success, on_error = self.conversions.started[0]
                on_error("轉譯失敗：boom")

                message = "無法轉換文件「beta」。\n\n轉譯失敗：boom" if named else "轉譯失敗：boom"
                self.assertEqual(self._take(), [("show_error", message, _("Error"))])

    def test_export_document_pending_without_table_shows_error_only(self) -> None:
        self.conversions.missing_message = MISSING_TABLE
        self.view.paths.append(self.root / "beta.brl")

        self.coordinator.export_document(Document("beta", "b", None), "brl")

        self.assertEqual(
            self._take(),
            [
                ("choose_export_path", "beta.brl", "brl"),
                ("missing_table_message",),
                ("show_error", MISSING_TABLE, _("Error")),
            ],
        )
        self.assertEqual(self.conversions.started, [])

    def test_html_export_of_a_pending_document_uses_its_conversion(self) -> None:
        # Was P1-4 defect 3 (task.md #11): the cache, empty for a pending document, gave the
        # "No conversion data" page (F-9 D6).
        self.view.paths.append(self.root / "beta.html")
        self.coordinator.export_document(Document("beta", "b", None), "html")
        self._take()

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃", ("result",), (_segment("fresh-b", "⠃"),)))

        self.assertEqual(self._take(), [self._exported()])
        html = (self.root / "beta.html").read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-b</span>', html)
        self.assertNotIn("此文件沒有可顯示的轉換資料。", html)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

    # --- export_all ----------------------------------------------------------------

    def test_export_all_folder_cancel_does_nothing(self) -> None:
        self.view.directories.append(None)

        self.coordinator.export_all("brl")

        self.assertEqual(self._take(), [("choose_export_directory",)])
        self.assertEqual(self.calls.pending, [])

    def test_export_all_takes_the_snapshot_after_the_folder_dialog(self) -> None:
        self.documents.documents = [Document("alpha", "a", "⠁")]

        def choose_export_directory():
            self.events.append(("choose_export_directory",))
            self.documents.add_document(Document("gamma", "g", "⠛"))
            return self.root

        self.view.choose_export_directory = choose_export_directory

        self.coordinator.export_all("brl")
        self.calls.run_all()

        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})

    def test_export_all_asks_about_conflicts_only_when_needed(self) -> None:
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("gamma", "g", "⠛")]
        self.view.directories.extend([self.root, self.root, self.root])
        self.view.overwrite_answers.extend([False, True])

        self.coordinator.export_all("brl")
        self.calls.run_all()
        self.assertEqual(
            self._take(),
            [("choose_export_directory",), ("call_after",), ("call_after",), self._all_exported()],
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})

        (self.root / "alpha.brl").write_text("old", encoding="utf-8")
        (self.root / "gamma.brl").unlink()
        self.coordinator.export_all("brl")
        self.assertEqual(self._take(), [("choose_export_directory",), ("confirm_overwrite_all", ["alpha.brl"])])
        self.assertEqual(self._written(), {"alpha.brl": "old"})

        self.coordinator.export_all("brl")
        self.calls.run_all()
        self.assertEqual(
            self._take(),
            [
                ("choose_export_directory",),
                ("confirm_overwrite_all", ["alpha.brl"]),
                ("call_after",),
                ("call_after",),
                self._all_exported(),
            ],
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})

    def test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn(self) -> None:
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", None), Document("gamma", "g", "⠛")]
        self.view.directories.append(self.root)

        self.coordinator.export_all("brl")
        self.assertEqual(self._take(), [("choose_export_directory",), ("call_after",)])
        self.assertEqual(self._written(), {"alpha.brl": "⠁"})

        self.calls.run_next()
        self.assertEqual(self._take(), [("missing_table_message",), ("convert_for_export", "b")])
        self.assertEqual(self.calls.pending, [])

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃", ()))
        self.assertEqual(self._take(), [("call_after",)])
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃"})

        self.calls.run_next()
        self.assertEqual(self._take(), [("call_after",)])
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃", "gamma.brl": "⠛"})

        self.calls.run_next()
        self.assertEqual(self._take(), [self._all_exported()])
        self.assertEqual(self.calls.pending, [])

    def test_export_all_reads_the_format_for_conflicts_each_step_and_each_write(self) -> None:
        self.documents.documents = [Document("alpha", "a", "⠁")]
        self.view.directories.append(self.root)
        descriptor = replace(get_format("brl"), extension=".braille")

        with patch.object(coordinator_module, "get_format", return_value=descriptor) as get_format_mock:
            self.coordinator.export_all("brl")
            self.calls.run_all()

        self.assertEqual(get_format_mock.call_args_list, [call("brl"), call("brl"), call("brl")])
        self.assertEqual((self.root / "alpha.braille").read_text(encoding="utf-8"), "⠁")

    def test_export_all_partial_failure_summary_lists_each_failure(self) -> None:
        blocked = self.root / "write-fail.brl"
        blocked.mkdir()
        reason = self._os_error_text(blocked)
        self.documents.documents = [
            Document("alpha", "a", "⠁"),
            Document("convert-fail", "c", None),
            Document("write-fail", "w", "⠺"),
        ]
        self.view.directories.append(self.root)
        self.view.overwrite_answers.append(True)

        self.coordinator.export_all("brl")
        self.calls.run_next()
        _on_success, on_error = self.conversions.started[0]
        on_error("Translation failed")
        self.calls.run_all()

        self.assertEqual(
            self._take()[-1],
            (
                "show_warning",
                f"成功匯出的文件：1\n匯出失敗的文件：2\n\nconvert-fail: Translation failed\nwrite-fail: {reason}",
                EXPORTED_WITH_ERRORS,
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁"})

    def test_export_all_missing_table_accumulates_failures_without_per_file_messages(self) -> None:
        self.conversions.missing_message = MISSING_TABLE
        self.documents.documents = [Document("alpha", "a", None), Document("beta", "b", None)]
        self.view.directories.append(self.root)

        self.coordinator.export_all("brl")
        self.assertEqual(
            self._take(),
            [("choose_export_directory",), ("missing_table_message",), ("call_after",)],
        )
        self.calls.run_next()
        self.assertEqual(self._take(), [("missing_table_message",), ("call_after",)])
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [
                (
                    "show_warning",
                    f"成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: {MISSING_TABLE}\nbeta: {MISSING_TABLE}",
                    EXPORTED_WITH_ERRORS,
                )
            ],
        )
        self.assertEqual(self.conversions.started, [])

    def test_export_all_writer_value_error_is_listed_and_the_chain_goes_on(self) -> None:
        # Was the P1-4 KNOWN BUG (defect 7), fixed by F-7: the error escaped, the chain stopped
        # and no summary was shown.
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")]
        self.view.directories.append(self.root)

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.coordinator.export_all("txt")
            self.calls.run_all()

        reason = 'Unsupported export format: "txt".'
        self.assertEqual(
            self._take(),
            [
                ("choose_export_directory",),
                ("call_after",),
                ("call_after",),
                (
                    "show_warning",
                    f"成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: {reason}\nbeta: {reason}",
                    EXPORTED_WITH_ERRORS,
                ),
            ],
        )
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(self.calls.pending, [])

    def test_export_all_goes_on_after_an_error_that_is_not_an_os_error(self) -> None:
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("beta", error))
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃"), Document("gamma", "g", "⠛")]
        self.view.directories.append(self.root)

        with (
            patch.object(coordinator_module, "get_format", return_value=descriptor),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            self.coordinator.export_all("brl")
            self.calls.run_all()

        self.assertEqual(
            self._take()[-1],
            (
                "show_warning",
                "成功匯出的文件：2\n匯出失敗的文件：1\n\nbeta: injected",
                EXPORTED_WITH_ERRORS,
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_export_all_html_uses_each_pending_documents_conversion(self) -> None:
        # F-9 D6: each pending document gets its own fresh segments; a converted one keeps its cache.
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", None), Document("gamma", "g", None)]
        self.documents.set_dual_view_results("alpha", (_segment("cached-a", "⠁"),))
        self.view.directories.append(self.root)

        self.coordinator.export_all("html")
        self.calls.run_next()
        self.conversions.started[0][0](ConversionOutput("⠃", (), (_segment("fresh-b", "⠃"),)))
        self.calls.run_next()
        self.conversions.started[1][0](ConversionOutput("⠛", (), (_segment("fresh-g", "⠛"),)))
        self.calls.run_next()

        self.assertEqual(self._take()[-1], self._all_exported())
        for name, source in (("alpha", "cached-a"), ("beta", "fresh-b"), ("gamma", "fresh-g")):
            with self.subTest(name=name):
                html = (self.root / f"{name}.html").read_text(encoding="utf-8")
                self.assertIn(f'<span class="source">{source}</span>', html)
                self.assertNotIn("此文件沒有可顯示的轉換資料。", html)
        self.assertEqual(list(self.documents.dual_view_results_by_document), ["alpha"])


class ExportThroughConversionPresenterTest(unittest.TestCase):
    def test_export_all_with_a_real_presenter_turn_by_turn(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        events: list = []
        view = RecordingExportView(events)
        view.directories.append(root)
        documents = DocumentController(
            documents=[Document("ready", "r", "⠗"), Document("pending", "p", None), Document("broken", "x", None)],
        )
        documents.set_dual_view_results("pending", ("cached",))
        outcomes = {
            "p": ConversionOutput("⠏", ("result",), ("fresh",)),
            "x": ConversionStageError("translation", RuntimeError("bad")),
        }

        def converter(request, *, runtime):
            events.append(("convert", request.raw_text))
            outcome = outcomes[request.raw_text]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        calls = DeferredCalls(events)
        timers = FakeTimers(events)
        thread_factory = make_thread_factory()
        presenter = ConversionPresenter(
            view,
            documents,
            runtime=object(),
            build_request=lambda raw_text: ConversionRequest(
                raw_text, "unicode", 40, Path("d.csv"), Path("data"), {"default": "t"}, "zh_TW", {}
            ),
            get_translation_tables=lambda: {"default": "t"},
            call_after=calls,
            call_later=timers,
            thread_factory=thread_factory,
            converter=converter,
        )
        coordinator = ExportCoordinator(view, documents, presenter, call_after=calls)

        coordinator.export_all("brl")
        calls.run_next()
        thread_factory.threads[0].run()
        calls.run_next()
        calls.run_next()
        thread_factory.threads[1].run()
        calls.run_next()
        calls.run_next()

        busy_on = [("busy", True), ("close_converting_dialog",)]
        busy_off = [("close_converting_dialog",), ("busy", False)]
        self.assertEqual(
            events,
            [("choose_export_directory",), ("call_after",)]
            + busy_on
            + [("call_later", 2000, (1,)), ("convert", "p"), ("call_after",), ("timer.Stop", 1)]
            + busy_off
            + [("call_after",)]
            + busy_on
            + [("call_later", 2000, (2,)), ("convert", "x"), ("call_after",), ("timer.Stop", 2)]
            + busy_off
            + [
                ("call_after",),
                (
                    "show_warning",
                    "成功匯出的文件：2\n匯出失敗的文件：1\n\nbroken: "
                    + _("Translation failed: {error}").format(error="bad"),
                    EXPORTED_WITH_ERRORS,
                ),
            ],
        )
        self.assertEqual((root / "pending.brl").read_text(encoding="utf-8"), "⠏")
        self.assertEqual(documents.dual_view_results_by_document, {"pending": ("cached",)})
        self.assertEqual(calls.pending, [])


if __name__ == "__main__":
    unittest.main()
