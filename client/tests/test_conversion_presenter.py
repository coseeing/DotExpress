from __future__ import annotations

import ast
import unittest
from pathlib import Path

from ui.conversion_presenter import (
    CONVERTING_DIALOG_DELAY_MS,
    ConversionPresenter,
    format_conversion_error,
    missing_default_table_message,
)
import csv

from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from conversion.text import dictionary_rules
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import big5_decode_error

# F-12 (D4): a conversion that cannot read the selected dictionary, as the user sees it.
NOT_UTF8 = "檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。"
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"
HEADER_NOT_RECOGNIZED = "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
BIG5_DICTIONARY_FAILED = f"轉譯失敗：無法讀取字典「big5dict」。{NOT_UTF8}"


def _read_error(*args, **kwargs) -> Exception:
    """A DictionaryRulesReadError, looked up when the test runs."""
    return dictionary_rules.DictionaryRulesReadError(*args, **kwargs)


def _big5_dictionary_failure() -> ConversionStageError:
    return ConversionStageError("translation", _read_error(Path("dictionary/big5dict.csv"), big5_decode_error()))

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"
LOGGER = "dotexpress.gui"


def setUpModule() -> None:
    # A discarded result is logged to gui.log (F-9 D3); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class RecordingConversionView:
    """Implements ``ConversionView``; every call lands in the shared event list."""

    def __init__(self, events: list, source_text: str = ""):
        self.events = events
        self.source_text = source_text
        self.save_result = True

    def get_source_text(self) -> str:
        self.events.append(("get_source_text",))
        return self.source_text

    def set_conversion_busy(self, busy: bool) -> None:
        self.events.append(("busy", busy))

    def show_converting_dialog(self) -> None:
        self.events.append(("show_converting_dialog",))

    def close_converting_dialog(self) -> None:
        self.events.append(("close_converting_dialog",))

    def show_conversion_output(self, text: str) -> None:
        self.events.append(("show_conversion_output", text))

    def refresh_dual_view(self) -> None:
        self.events.append(("refresh_dual_view",))

    def show_info(self, message: str, caption: str) -> None:
        self.events.append(("show_info", message, caption))

    def show_error(self, message: str, caption: str) -> None:
        self.events.append(("show_error", message, caption))

    def save_converted_document(self, document: Document) -> bool:
        self.events.append(("save_converted_document", document))
        return self.save_result

    def focus_source_editor(self) -> None:
        self.events.append(("focus_source_editor",))


class ConversionPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list = []
        self.view = RecordingConversionView(self.events, "source")
        self.documents = DocumentController(
            documents=[Document("alpha", "old", None), Document("beta", "b", "⠃")],
            open_name="alpha",
            selected_name="alpha",
        )
        self.tables = {"default": "zh-tw.ctb"}
        self.calls = DeferredCalls(self.events)
        self.timers = FakeTimers(self.events)
        self.thread_factory = make_thread_factory()
        self.threads = self.thread_factory.threads
        self.runtime = object()
        self.outputs: dict = {}
        self.requests: list = []

    def _build_request(self, raw_text: str) -> ConversionRequest:
        self.events.append(("build_request", raw_text))
        return ConversionRequest(
            raw_text=raw_text,
            output_mode="unicode",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables=dict(self.tables),
            lang="zh_TW",
            charset_maps={},
        )

    def _convert(self, request, *, runtime):
        self.assertIs(runtime, self.runtime)
        self.requests.append(request)
        self.events.append(("convert", request.raw_text))
        outcome = self.outputs[request.raw_text]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def _presenter(self, *, call_after=None) -> ConversionPresenter:
        return ConversionPresenter(
            self.view,
            self.documents,
            runtime=self.runtime,
            build_request=self._build_request,
            get_translation_tables=lambda: self.tables,
            call_after=self.calls if call_after is None else call_after,
            call_later=self.timers,
            thread_factory=self.thread_factory,
            converter=self._convert,
        )

    def _take(self) -> list:
        taken = list(self.events)
        self.events.clear()
        return taken

    def _export_callbacks(self) -> dict:
        return {
            "on_success": lambda output: self.events.append(("on_success", output.display_text)),
            "on_error": lambda message: self.events.append(("on_error", message)),
        }

    def _end(self, timer_number: int = 1) -> list:
        return [("timer.Stop", timer_number), ("close_converting_dialog",), ("busy", False)]

    def _switch_to(self, name: str) -> None:
        """Switch documents as the frame does: store the open document's editor text, then open ``name``."""
        open_document = self.documents.get_document(self.documents.open_document_name)
        if open_document is not None:
            self.documents.replace_document(Document(open_document.name, self.view.source_text, open_document.braille))
        document = self.documents.open_document(name)
        self.view.source_text = document.text if document is not None else ""

    def _saved_to(self, name: str) -> tuple:
        return (
            "show_info",
            _('Conversion completed. The result was saved to document "{name}".').format(name=name),
            _("Info"),
        )

    # --- module helpers ------------------------------------------------------

    def test_module_imports_neither_wx_nor_gui(self) -> None:
        tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])

        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)

    def test_missing_default_table_message_reports_only_unset_default(self) -> None:
        self.assertIsNone(missing_default_table_message({"default": "zh-tw.ctb"}))
        for tables in ({}, {"default": ""}, {"default": None}):
            with self.subTest(tables=tables):
                self.assertEqual(
                    missing_default_table_message(tables),
                    _("Please select a translation table first."),
                )

    def test_format_conversion_error_by_stage(self) -> None:
        for stage, template in (
            ("ascii", "ASCII conversion failed: {error}"),
            ("text_processing", "Text processing failed: {error}"),
            ("translation", "Translation failed: {error}"),
            ("other", "Translation failed: {error}"),
        ):
            with self.subTest(stage=stage):
                self.assertEqual(
                    format_conversion_error(ConversionStageError(stage, RuntimeError("script boom"))),
                    _(template).format(error="script boom"),
                )

    def test_format_conversion_error_public_texts(self) -> None:
        # The two public fallback texts are msgids since F-12 (D2; were English, P1-4 defect 4).
        for raw, public in (
            ("", "發生不明的錯誤。"),
            ("Can't translate: tables zh-tw.ctb inbuf=12", "選取的轉譯表無法轉譯這段文字。"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    format_conversion_error(ConversionStageError("translation", RuntimeError(raw))),
                    _("Translation failed: {error}").format(error=public),
                )

    def test_format_conversion_error_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4): one line, as it is also a line of the Export All summary.
        path = Path("dictionary/d.csv")
        field_error = csv.Error("field larger than field limit (131072)")
        missing = FileNotFoundError(2, "No such file or directory", str(path))
        cases = (
            ("not UTF-8", _read_error(path, big5_decode_error()), NOT_UTF8),
            ("cannot be opened", _read_error(path, PermissionError(13, "Permission denied")), CANNOT_OPEN),
            (
                "not a valid CSV file",
                _read_error(path, field_error),
                f"檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{field_error}",
            ),
            ("another error", _read_error(path, missing), f"無法讀取檔案：{missing}"),
            (
                "a header that is not recognized",
                _read_error(path, ValueError("CSV must contain header row."), header_not_recognized=True),
                HEADER_NOT_RECOGNIZED,
            ),
        )
        for label, error, reason in cases:
            with self.subTest(label):
                message = format_conversion_error(ConversionStageError("translation", error))

                self.assertEqual(message, f"轉譯失敗：無法讀取字典「d」。{reason}")
                self.assertNotIn("\n", message)

    # --- convert -------------------------------------------------------------

    def test_convert_reads_source_text_then_starts_job_and_timer(self) -> None:
        presenter = self._presenter()

        presenter.convert()

        self.assertEqual(
            self._take(),
            [
                ("get_source_text",),
                ("busy", True),
                ("close_converting_dialog",),
                ("build_request", "source"),
                ("call_later", CONVERTING_DIALOG_DELAY_MS, (1,)),
            ],
        )
        self.assertEqual(CONVERTING_DIALOG_DELAY_MS, 2000)
        self.assertEqual([(thread.daemon, thread.started) for thread in self.threads], [(True, True)])
        self.assertTrue(presenter.is_running())
        self.assertEqual(self.requests, [])

    def test_convert_without_default_table_shows_info_only(self) -> None:
        self.tables = {"default": ""}
        presenter = self._presenter()

        presenter.convert()

        self.assertEqual(
            self._take(),
            [("show_info", _("Please select a translation table first."), _("Info"))],
        )
        self.assertEqual(self.threads, [])

    def test_convert_while_running_returns_before_table_check(self) -> None:
        presenter = self._presenter()
        presenter.convert()
        self._take()
        self.tables = {}

        presenter.convert()

        self.assertEqual(self._take(), [])
        self.assertEqual(len(self.threads), 1)

    def test_is_running_and_missing_table_message_read_live_state(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()

        self.assertFalse(presenter.is_running())
        self.assertIsNone(presenter.missing_table_message())
        self.tables = {"default": None}
        self.assertEqual(presenter.missing_table_message(), _("Please select a translation table first."))
        self.tables = {"default": "zh-tw.ctb"}
        presenter.convert()
        self.assertTrue(presenter.is_running())
        self.threads[0].run()
        # Running until the result is delivered, not until the worker ends (F-9 D5).
        self.assertTrue(presenter.is_running())
        self.calls.run_next()
        self.assertFalse(presenter.is_running())

    # --- converting dialog timer ----------------------------------------------

    def test_timer_shows_dialog_only_for_the_running_active_job(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()
        presenter.convert()
        self._take()

        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [("show_converting_dialog",)])

        self.threads[0].run()
        self._take()
        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [])

        self.calls.run_next()
        presenter.convert()
        self._take()
        self.timers.timers[0].fire()
        self.assertEqual(self._take(), [])
        self.timers.timers[1].fire()
        self.assertEqual(self._take(), [("show_converting_dialog",)])

    # --- manual completion ----------------------------------------------------

    def test_manual_success_updates_output_document_cache_then_reports(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self.assertEqual(self._take()[-2:], [("convert", "source"), ("call_after",)])

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "source", "⠎"), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})
        self.assertFalse(presenter.is_running())

    def test_manual_success_without_open_document_touches_no_document(self) -> None:
        self.documents.open_name = None
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {})

    def test_manual_success_with_open_name_missing_from_list_still_writes_cache(self) -> None:
        self.documents.open_name = "ghost"
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"ghost": ("segment",)})

    # --- the document that started the conversion (F-9 D1-D3) -------------------

    def test_result_goes_to_the_document_that_started_the_conversion(self) -> None:
        # Was P1-4 defect 1: the result went to the document open at completion.
        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        # After the box the focus goes to beta's source editor: the switch left it in the
        # read-only Braille Result editor, as the source editor was disabled (F-9 review M-6).
        self.assertEqual(
            self._take(),
            self._end()
            + [("save_converted_document", Document("alpha", "source", "⠎")), self._saved_to("alpha")]
            + [("focus_source_editor",)],
        )
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", "⠃"))
        self.assertEqual(self.documents.open_document_name, "beta")

    def test_result_for_the_open_document_follows_todays_path(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self._switch_to("alpha")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "source", "⠎"), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})

    def test_failed_save_of_the_originating_document_shows_no_completion_message(self) -> None:
        # The view has shown the save error; the next queued job still starts.
        self.outputs.update({"source": ConversionOutput("⠎", (), ("segment",)), "doc text": ConversionOutput("⠙", ())})
        self.view.save_result = False
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self._switch_to("beta")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("save_converted_document", Document("alpha", "source", "⠎")), ("focus_source_editor",)]
            + [("busy", True), ("close_converting_dialog",), ("call_later", CONVERTING_DIALOG_DELAY_MS, (2,))],
        )
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})

    def _assert_discarded(self, presenter: ConversionPresenter, reason: str) -> None:
        """Deliver the running job's result and check that it was dropped with one log line."""
        self.threads[-1].run()
        self._take()
        documents_before = list(self.documents.documents)
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.calls.run_next()

        self.assertEqual(self._take(), self._end(len(self.timers.timers)))
        self.assertEqual([record.getMessage() for record in logs.records], [f"Discarded a conversion result: {reason}"])
        self.assertEqual(self.documents.documents, documents_before)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertFalse(presenter.is_running())

    def test_result_for_a_document_that_is_gone_is_discarded_and_logged(self) -> None:
        # None of these can happen while a job runs today (the list and the File menu are
        # disabled); the result is not guessed onto another document (F-9 D3, O2).
        for case, remove in (
            ("deleted", lambda: self.documents.delete_document("alpha")),
            ("renamed", lambda: self.documents.rename_document("alpha", "gamma")),
            ("delete all", lambda: self.documents.delete_all_documents()),
        ):
            with self.subTest(case=case):
                self.setUp()
                self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
                presenter = self._presenter()
                presenter.convert()
                self._switch_to("beta")
                remove()

                self._assert_discarded(presenter, 'document "alpha" no longer exists')

    def test_result_for_a_changed_text_is_discarded_and_logged(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self.documents.replace_document(Document("alpha", "another text", None))

        self._assert_discarded(presenter, 'the text of document "alpha" changed')

    def test_result_without_a_starting_document(self) -> None:
        # No document open at the start: today's output-only path if none is open at the end;
        # if one was opened meanwhile, the result is discarded rather than given to it.
        self.documents.open_name = None
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )

        presenter.convert()
        self.documents.open_document("beta")
        self._assert_discarded(presenter, 'document "beta" was opened during a conversion without a document')

    def test_manual_failure_shows_error_after_busy_off(self) -> None:
        self.outputs["source"] = ConversionStageError("text_processing", RuntimeError("script boom"))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("show_error", _("Text processing failed: {error}").format(error="script boom"), _("Error"))],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {})

    def test_manual_failure_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4).
        self.outputs["source"] = _big5_dictionary_failure()
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end() + [("show_error", BIG5_DICTIONARY_FAILED, "錯誤")])

    def _failed_after(self, switch) -> list:
        """Convert alpha, run ``switch`` while the job runs, deliver a failure; the events after it."""
        self.outputs["source"] = ConversionStageError("translation", RuntimeError("boom"))
        presenter = self._presenter()
        presenter.convert()
        switch()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        return self._take()

    def test_a_failure_after_switching_names_the_document(self) -> None:
        # F-12 (D7, F-9 review M-9): the box would otherwise seem to be about the open document.
        # F-13 (D1): after the box the focus goes to the open document's source editor.
        events = self._failed_after(lambda: self._switch_to("beta"))

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)],
        )

    def test_a_failure_after_an_import_opened_another_document_names_it_and_focuses(self) -> None:
        # F-13 (D1): an import during the job opens the imported document, as a switch does.
        def import_and_open() -> None:
            self.documents.add_document(Document("imported", "i", None))
            self._switch_to("imported")

        events = self._failed_after(import_and_open)

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)],
        )

    def test_the_focus_after_a_failure_comes_before_the_queued_job_starts(self) -> None:
        # F-13 (D1): the focus call is part of the completion; the queued export starts after it.
        self.outputs.update(
            {"source": ConversionStageError("translation", RuntimeError("boom")), "doc text": ConversionOutput("export", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)]
            + self._started(2),
        )

    def _not_named(self) -> list:
        return self._end() + [("show_error", _("Translation failed: {error}").format(error="boom"), _("Error"))]

    def test_a_failure_of_the_open_document_is_not_named(self) -> None:
        self.assertEqual(self._failed_after(lambda: None), self._not_named())

    def test_a_failure_after_switching_away_and_back_is_not_named(self) -> None:
        events = self._failed_after(lambda: (self._switch_to("beta"), self._switch_to("alpha")))

        self.assertEqual(events, self._not_named())

    def test_a_failure_without_a_starting_document_is_not_named(self) -> None:
        # No document to name, also when one was opened during the conversion.
        self.documents.open_name = None

        events = self._failed_after(lambda: self.documents.open_document("alpha"))

        self.assertEqual(events, self._not_named())

    # --- export completion ----------------------------------------------------

    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
        self.tables = {}
        presenter = self._presenter()

        presenter.convert_for_export("doc text", **self._export_callbacks())

        self.assertEqual(
            self._take(),
            [
                ("busy", True),
                ("close_converting_dialog",),
                ("build_request", "doc text"),
                ("call_later", 2000, (1,)),
            ],
        )
        self.assertEqual(len(self.threads), 1)

    def test_export_success_calls_only_on_success(self) -> None:
        self.documents.set_dual_view_results("alpha", ("manual",))
        self.outputs["doc text"] = ConversionOutput("⠙", ("result",), ("export-segment",))
        presenter = self._presenter()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end() + [("on_success", "⠙")])
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("manual",)})

    def test_export_success_receives_the_conversion_output(self) -> None:
        # F-9 D6: the export gets the whole output, so a pending document's HTML export can use
        # the fresh dual-view segments.
        output = ConversionOutput("⠙", ("result",), ("export-segment",))
        self.outputs["doc text"] = output
        received: list = []
        presenter = self._presenter()
        presenter.convert_for_export("doc text", on_success=received.append, on_error=self.fail)
        self.threads[0].run()

        self.calls.run_next()

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], output)

    def test_export_failure_calls_only_on_error(self) -> None:
        self.outputs["doc text"] = ConversionStageError("ascii", RuntimeError("bad map"))
        presenter = self._presenter()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("on_error", _("ASCII conversion failed: {error}").format(error="bad map"))],
        )

    def test_export_failure_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4): a single export shows it, and Export All lists it after the document's name.
        self.outputs["doc text"] = _big5_dictionary_failure()
        presenter = self._presenter()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end() + [("on_error", BIG5_DICTIONARY_FAILED)])

    def test_later_job_uses_its_own_completion(self) -> None:
        self.outputs.update({"doc text": ConversionOutput("first", ()), "source": ConversionOutput("second", ())})
        presenter = self._presenter()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self.calls.run_next()
        presenter.convert()
        self.threads[1].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end(2)
            + [
                ("show_conversion_output", "second"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )

    def _started(self, timer_number: int) -> list:
        return [("busy", True), ("close_converting_dialog",), ("call_later", CONVERTING_DIALOG_DELAY_MS, (timer_number,))]

    def test_export_requested_while_a_conversion_runs_waits_for_it(self) -> None:
        # Was the P1-4 KNOWN BUG (defect 2): the export superseded the manual conversion, whose
        # result was dropped. Now it waits (F-9 D4); its request is built when it is asked for.
        self.outputs.update({"source": ConversionOutput("manual", ()), "doc text": ConversionOutput("export", ())})
        presenter = self._presenter()
        presenter.convert()
        self._take()

        presenter.convert_for_export("doc text", **self._export_callbacks())

        self.assertEqual(self._take(), [("build_request", "doc text")])
        self.assertEqual(len(self.threads), 1)

        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "manual"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ]
            + self._started(2),
        )
        self.assertTrue(self.timers.timers[0].stopped)

        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "doc text"), ("call_after",)])
        self.calls.run_next()

        self.assertEqual(self._take(), self._end(2) + [("on_success", "export")])
        self.assertFalse(presenter.is_running())

    def test_queued_jobs_run_in_request_order(self) -> None:
        texts = ("first", "a", "b", "c")
        self.outputs.update({text: ConversionOutput(text.upper(), ()) for text in texts})
        presenter = self._presenter()
        for text in texts:
            presenter.convert_for_export(text, **self._export_callbacks())

        for index in range(len(texts)):
            self.threads[index].run()
            self.calls.run_next()

        self.assertEqual(
            [event for event in self.events if event[0] in ("convert", "on_success")],
            [("convert", "first"), ("on_success", "FIRST"), ("convert", "a"), ("on_success", "A")]
            + [("convert", "b"), ("on_success", "B"), ("convert", "c"), ("on_success", "C")],
        )
        self.assertEqual([timer.stopped for timer in self.timers.timers], [True, True, True, True])
        self.assertFalse(presenter.is_running())

    def test_queue_drains_after_a_failed_completion(self) -> None:
        self.outputs.update(
            {"source": ConversionStageError("translation", RuntimeError("boom")), "doc text": ConversionOutput("export", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("show_error", _("Translation failed: {error}").format(error="boom"), _("Error"))]
            + self._started(2),
        )

    def test_request_during_a_completion_waits_until_it_returns(self) -> None:
        # An Export All step's CallAfter runs inside the modal box of a completion: it queues,
        # so a second box never opens on top of the first (F-9 D4).
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        presenter = self._presenter()

        def first_done(output) -> None:
            self.events.append(("on_success", output.display_text))
            presenter.convert_for_export("second", **self._export_callbacks())
            self.events.append(("callback returns",))

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("on_success", "1"), ("build_request", "second"), ("callback returns",)] + self._started(2),
        )

    def test_queue_drains_when_a_completion_raises(self) -> None:
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        presenter = self._presenter()

        def first_done(_output) -> None:
            raise RuntimeError("callback boom")

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        presenter.convert_for_export("second", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        with self.assertRaisesRegex(RuntimeError, "callback boom"):
            self.calls.run_next()

        self.assertEqual(self._take(), self._end() + self._started(2))
        self.assertTrue(presenter.is_running())

    def test_request_during_a_failed_completion_waits_until_it_returns(self) -> None:
        # F-9 review M-1: the failure completion queues a request made inside it, as the success
        # completion does, so its error box closes before the next job starts.
        self.outputs.update(
            {"first": ConversionStageError("translation", RuntimeError("boom")), "second": ConversionOutput("2", ())}
        )
        presenter = self._presenter()

        def first_failed(message) -> None:
            self.events.append(("on_error", message))
            presenter.convert_for_export("second", **self._export_callbacks())
            self.events.append(("callback returns",))

        presenter.convert_for_export("first", on_success=self.fail, on_error=first_failed)
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("on_error", _("Translation failed: {error}").format(error="boom"))]
            + [("build_request", "second"), ("callback returns",)]
            + self._started(2),
        )

    def test_queue_drains_when_a_failed_completion_raises(self) -> None:
        # F-9 review M-2: the failure completion drains in its finally too; otherwise the queued
        # job would never start and every later close would be vetoed.
        self.outputs.update(
            {"first": ConversionStageError("translation", RuntimeError("boom")), "second": ConversionOutput("2", ())}
        )
        presenter = self._presenter()

        def first_failed(_message) -> None:
            raise RuntimeError("callback boom")

        presenter.convert_for_export("first", on_success=self.fail, on_error=first_failed)
        presenter.convert_for_export("second", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        with self.assertRaisesRegex(RuntimeError, "callback boom"):
            self.calls.run_next()

        self.assertEqual(self._take(), self._end() + self._started(2))
        self.threads[1].run()
        self.calls.run_next()
        self.assertEqual(self._take(), [("convert", "second"), ("call_after",)] + self._end(2) + [("on_success", "2")])
        self.assertFalse(presenter.is_running())

    def test_queued_manual_job_keeps_its_target(self) -> None:
        # F-9 review M-3: a manual Convert asked for during a completion (is_running() is False
        # then) is queued with the document open at that time, and its result goes there.
        self.outputs.update({"first": ConversionOutput("1", ()), "source": ConversionOutput("⠎", (), ("segment",))})
        presenter = self._presenter()

        def first_done(output) -> None:
            self.events.append(("on_success", output.display_text))
            presenter.convert()

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("on_success", "1"), ("get_source_text",), ("build_request", "source")] + self._started(2),
        )

        self._switch_to("beta")
        self.threads[1].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end(2)
            + [("save_converted_document", Document("alpha", "source", "⠎")), self._saved_to("alpha")]
            + [("focus_source_editor",)],
        )
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", "⠃"))
        self.assertFalse(presenter.is_running())

    def test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap(self) -> None:
        self.outputs.update(
            {"source": ConversionOutput("⠎", ()), "first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        # The worker has ended; its result is not delivered yet.
        presenter.convert()

        self.assertEqual(self._take(), [])
        self.assertEqual(len(self.threads), 1)
        self.calls.run_next()
        self._take()

        def first_done(output) -> None:
            self.events.append(("on_success", output.display_text))
            # "second" is queued.
            presenter.convert()

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        presenter.convert_for_export("second", **self._export_callbacks())
        self.threads[1].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end(2) + [("on_success", "1")] + self._started(3))
        self.assertEqual(len(self.threads), 3)

    def test_is_running_covers_the_delivery_gap_and_the_queue(self) -> None:
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        seen: list = []
        presenter = self._presenter()
        for text in ("first", "second"):
            presenter.convert_for_export(
                text,
                on_success=lambda _output, text=text: seen.append((text, presenter.is_running())),
                on_error=self.fail,
            )

        self.threads[0].run()
        self.assertTrue(presenter.is_running())
        self.calls.run_next()
        self.threads[1].run()
        self.assertTrue(presenter.is_running())
        self.calls.run_next()

        # Queued: running; a completion with an empty queue: not running.
        self.assertEqual(seen, [("first", True), ("second", False)])
        self.assertFalse(presenter.is_running())

    def test_shutdown_drops_the_running_and_queued_jobs(self) -> None:
        # The window has closed (F-9 D8, P1 review M-10): nothing may reach the view any more.
        self.outputs.update({"source": ConversionOutput("⠎", ()), "doc text": ConversionOutput("⠙", ())})
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self._take()

        presenter.shutdown()

        self.assertEqual(self._take(), [("timer.Stop", 1)])
        self.assertFalse(presenter.is_running())
        self.timers.timers[0].fire()
        self.threads[0].run()
        self.calls.run_next()
        presenter.convert_for_export("late", **self._export_callbacks())

        self.assertEqual(self._take(), [("convert", "source"), ("call_after",)])
        self.assertEqual(len(self.threads), 1)
        self.assertFalse(presenter.is_running())

    # --- the conversion thread at exit (F-13 D3) ------------------------------

    def test_worker_alive_is_false_before_a_job(self) -> None:
        self.assertFalse(self._presenter().worker_alive())

    def test_worker_alive_while_the_thread_runs_also_after_shutdown(self) -> None:
        # BrailleApp.OnExit does not free liblouis while the thread may be inside it. After the
        # window closed (shutdown), is_running is false, but the thread still runs.
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()
        presenter.convert()

        self.assertTrue(presenter.worker_alive())
        presenter.shutdown()
        self.assertFalse(presenter.is_running())
        self.assertTrue(presenter.worker_alive())

    def test_worker_alive_is_false_once_the_thread_has_ended(self) -> None:
        # The result may not be delivered yet (its CallAfter is pending), or not at all after
        # a shutdown: the thread has ended either way.
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()
        presenter.convert()
        presenter.shutdown()

        self.threads[0].run()

        self.assertFalse(presenter.worker_alive())
        self.calls.run_next()
        self.assertFalse(presenter.worker_alive())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
        presenter.convert()
        self._take()

        self.threads[0].run()

        self.assertEqual(
            self._take(),
            [("convert", "source")]
            + self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )


if __name__ == "__main__":
    unittest.main()
