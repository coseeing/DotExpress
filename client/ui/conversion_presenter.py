"""Conversion state machine of the main window, without wx.

``ConversionPresenter`` starts conversion jobs, arms the "converting" dialog timer,
toggles the busy state and completes manual and export conversions. It talks to the
frame through ``ConversionView``. Threading is injected: ``call_after`` must defer to a
later UI turn (as ``wx.CallAfter`` does), so the active job is recorded before any
result can be delivered.

One job runs at a time. A job asked for while another one runs or completes waits in a
queue and starts, oldest first, when that completion returns, so no result is dropped
and a completion's message box closes before the next job starts (F-9).
``shutdown`` (the window closes) drops the running and queued jobs: later results are
ignored, and no view method runs after that (F-9).
"""

from __future__ import annotations

import threading
from collections import deque
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
    on_success: Callable[[ConversionOutput], None]
    on_error: Callable[[str], None]


@dataclass(frozen=True)
class _Job:
    request: ConversionRequest
    export: _ExportCallbacks | None  # None: a manual conversion


@dataclass(frozen=True)
class _ActiveJob:
    job_id: int
    job: _Job


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
        # Jobs asked for while another one is active or completing, oldest first (F-9 D4).
        self._queue: deque[_Job] = deque()
        self._completing = False
        self._shut_down = False

    def is_running(self) -> bool:
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
        return self._active is not None or bool(self._queue)

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())

    def convert(self) -> None:
        if self.is_running():
            return
        message = self.missing_table_message()
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        self._submit(self._view.get_source_text(), export=None)

    def convert_for_export(
        self,
        raw_text: str,
        *,
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None:
        # A running job is not replaced: this one waits for it (F-9 D4, was P1-4 defect 2).
        self._submit(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _submit(self, raw_text: str, export: _ExportCallbacks | None) -> None:
        """Start a job now, or queue it while another one is active, completing or queued (F-9 D4).

        A queued job's request is built now, so the settings at the time of the command apply.
        """
        if self._shut_down:
            return
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export))
            return
        self._start(lambda: _Job(self._build_request(raw_text), export))

    def _start(self, make_job: Callable[[], _Job]) -> None:
        self._view.set_conversion_busy(True)
        self._view.close_converting_dialog()
        job = make_job()
        job_id = self._runner.start(job.request)
        self._active = _ActiveJob(job_id, job)
        self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)

    def _finish_completion(self) -> None:
        """End a completion, also one that raised: start the oldest queued job (F-9 D4)."""
        self._completing = False
        if self._queue and not self._shut_down:
            job = self._queue.popleft()
            self._start(lambda: job)

    def shutdown(self) -> None:
        """Drop the running and queued jobs; the window has closed (F-9 D8, P1 review M-10).

        Stops the dialog timer. A result delivered later finds no active job and is
        ignored; no view method is called from now on.
        """
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None
        self._active = None
        self._queue.clear()
        self._shut_down = True

    def _show_converting_dialog(self, job_id: int) -> None:
        if self._shut_down or job_id != self._runner.active_job_id:
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
        active = self._take_active(result.job_id)
        if active is None:
            return
        self._completing = True
        try:
            self._end_job()
            output = result.conversion_output
            if active.job.export is not None:
                active.job.export.on_success(output)
            else:
                self._complete_manual(output)
        finally:
            self._finish_completion()

    def _on_job_failure(self, result: ConversionJobFailure) -> None:
        active = self._take_active(result.job_id)
        if active is None:
            return
        message = format_conversion_error(result.error)
        self._completing = True
        try:
            self._end_job()
            if active.job.export is not None:
                active.job.export.on_error(message)
            else:
                self._view.show_error(message, _("Error"))
        finally:
            self._finish_completion()

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
