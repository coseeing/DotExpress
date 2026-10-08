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
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"


class RecordingConversionView:
    """Implements ``ConversionView``; every call lands in the shared event list."""

    def __init__(self, events: list, source_text: str = ""):
        self.events = events
        self.source_text = source_text

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
            "on_success": lambda braille: self.events.append(("on_success", braille)),
            "on_error": lambda message: self.events.append(("on_error", message)),
        }

    def _end(self, timer_number: int = 1) -> list:
        return [("timer.Stop", timer_number), ("close_converting_dialog",), ("busy", False)]

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
        # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
        for raw, public in (
            ("", "An unknown error occurred."),
            ("Can't translate: tables zh-tw.ctb inbuf=12", "The selected translation table could not translate this text."),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    format_conversion_error(ConversionStageError("translation", RuntimeError(raw))),
                    _("Translation failed: {error}").format(error=public),
                )

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

    def test_superseded_job_delivers_nothing(self) -> None:
        self.outputs.update({"source": ConversionOutput("manual", ()), "doc text": ConversionOutput("export", ())})
        presenter = self._presenter()
        presenter.convert()
        # KNOWN BUG (P1-4 spec, defect 2): convert_for_export does not check for a running job.
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self.threads[1].run()
        self._take()

        self.calls.run_next()
        self.assertEqual(self._take(), [])

        self.calls.run_next()
        self.assertEqual(self._take(), self._end(2) + [("on_success", "export")])
        self.assertFalse(self.timers.timers[0].stopped)

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
