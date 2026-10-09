"""Conversion state machine of the main window, without wx.

``ConversionPresenter`` starts conversion jobs, arms the "converting" dialog timer,
toggles the busy state and completes manual and export conversions. It talks to the
frame through ``ConversionView``. Threading is injected: ``call_after`` must defer to a
later UI turn (as ``wx.CallAfter`` does), so the active job is recorded before any
result can be delivered.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from conversion.contracts import TranslationRuntime
from conversion.jobs import (
    ConversionJobFailure,
    ConversionJobRunner,
    ConversionJobSuccess,
    ThreadFactory,
)
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    convert_text_with_alignment,
    get_public_error_message,
)
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _

CONVERTING_DIALOG_DELAY_MS = 2000


class Timer(Protocol):
    def Stop(self) -> object: ...


CallAfter = Callable[..., object]
CallLater = Callable[..., Timer]


class ConversionView(Protocol):
    def get_source_text(self) -> str: ...

    def set_conversion_busy(self, busy: bool) -> None: ...

    def show_converting_dialog(self) -> None: ...

    def close_converting_dialog(self) -> None: ...

    def show_conversion_output(self, text: str) -> None: ...

    def refresh_dual_view(self) -> None: ...

    def show_info(self, message: str, caption: str) -> None: ...

    def show_error(self, message: str, caption: str) -> None: ...


@dataclass(frozen=True)
class _ExportCallbacks:
    on_success: Callable[[str], None]
    on_error: Callable[[str], None]


@dataclass(frozen=True)
class _ActiveJob:
    job_id: int
    export: _ExportCallbacks | None  # None: a manual conversion


def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None:
    if translation_tables.get("default"):
        return None
    return _("Please select a translation table first.")


def format_conversion_error(error: ConversionStageError) -> str:
    message_templates = {
        "ascii": _("ASCII conversion failed: {error}"),
        "text_processing": _("Text processing failed: {error}"),
    }
    message_template = message_templates.get(error.stage, _("Translation failed: {error}"))
    error_text = _(get_public_error_message(error.error))
    return message_template.format(error=error_text)


class ConversionPresenter:
    def __init__(
        self,
        view: ConversionView,
        documents: DocumentController,
        *,
        runtime: TranslationRuntime,
        build_request: Callable[[str], ConversionRequest],
        get_translation_tables: Callable[[], Mapping[str, object]],
        call_after: CallAfter,
        call_later: CallLater,
        thread_factory: ThreadFactory = threading.Thread,
        converter: Callable[..., ConversionOutput] = convert_text_with_alignment,
    ) -> None:
        self._view = view
        self._documents = documents
        self._build_request = build_request
        self._get_translation_tables = get_translation_tables
        self._call_later = call_later
        self._runner = ConversionJobRunner(
            runtime=runtime,
            on_success=self._on_job_success,
            on_failure=self._on_job_failure,
            call_after=call_after,
            converter=converter,
            thread_factory=thread_factory,
        )
        self._active: _ActiveJob | None = None
        self._timer: Timer | None = None

    def is_running(self) -> bool:
        return self._runner.is_running()

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())

    def convert(self) -> None:
        if self.is_running():
            return
        message = self.missing_table_message()
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        self._start(self._view.get_source_text(), export=None)

    def convert_for_export(
        self,
        raw_text: str,
        *,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        # No running check, as before (P1-4 spec, known defect 2): a running job is superseded.
        self._start(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _start(self, raw_text: str, export: _ExportCallbacks | None) -> None:
        self._view.set_conversion_busy(True)
        self._view.close_converting_dialog()
        request = self._build_request(raw_text)
        job_id = self._runner.start(request)
        self._active = _ActiveJob(job_id, export)
        self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)

    def _show_converting_dialog(self, job_id: int) -> None:
        if job_id != self._runner.active_job_id:
            return
        if not self._runner.is_running():
            return
        self._view.show_converting_dialog()

    def _take_active(self, job_id: int) -> _ActiveJob | None:
        job = self._active
        if job is None or job.job_id != job_id:
            return None
        self._active = None
        return job

    def _end_job(self) -> None:
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None
        self._view.close_converting_dialog()
        self._view.set_conversion_busy(False)

    def _on_job_success(self, result: ConversionJobSuccess) -> None:
        job = self._take_active(result.job_id)
        if job is None:
            return
        self._end_job()
        output = result.conversion_output
        if job.export is not None:
            job.export.on_success(output.display_text)
            return
        self._complete_manual(output)

    def _on_job_failure(self, result: ConversionJobFailure) -> None:
        job = self._take_active(result.job_id)
        if job is None:
            return
        message = format_conversion_error(result.error)
        self._end_job()
        if job.export is not None:
            job.export.on_error(message)
            return
        self._view.show_error(message, _("Error"))

    def _complete_manual(self, output: ConversionOutput) -> None:
        braille = output.display_text
        self._view.show_conversion_output(braille)
        # The result goes to the document open now, as before (P1-4 spec, known defect 1).
        open_name = self._documents.open_document_name
        if open_name:
            document = self._documents.get_document(open_name)
            if document is not None:
                self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))
            self._documents.set_dual_view_results(open_name, output.dual_view_segments)
        self._view.refresh_dual_view()
        self._view.show_info(_("Conversion completed."), _("Info"))
