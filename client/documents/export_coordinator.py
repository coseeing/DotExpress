"""Export flows of the main window, without wx.

``ExportCoordinator`` owns single export (choose a path, fix the extension, convert
first if the document is pending, write, report) and the Export All chain (choose a
folder, check conflicts, then one document per UI turn through ``call_after``, then
one summary). The view owns its dialogs and their texts; the coordinator owns the
outcome messages. The first Export All step runs in the caller's turn.

A pending document is written with its fresh conversion, dual-view segments included
(F-9); the export changes neither the document nor the dual-view cache.

Every write failure is reported: an ``OSError`` by its message, anything else also with
its traceback in ``gui.log`` (F-7).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from conversion.output import ConversionOutput
from documents.controller import DocumentController
from documents.export_results import ExportBatchResult
from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
from documents.workspace import Document
from i18n import _
from log import get_logger

CallAfter = Callable[..., object]


class ExportView(Protocol):
    def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None: ...

    def choose_export_directory(self) -> Path | None: ...

    def confirm_overwrite_all(self, conflicts: list[Path]) -> bool: ...

    def show_info(self, message: str, caption: str) -> None: ...

    def show_warning(self, message: str, caption: str) -> None: ...

    def show_error(self, message: str, caption: str) -> None: ...


class ExportConversions(Protocol):
    """Satisfied by ``ui.conversion_presenter.ConversionPresenter``."""

    def missing_table_message(self) -> str | None: ...

    def convert_for_export(
        self,
        raw_text: str,
        *,
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None: ...


class ExportCoordinator:
    def __init__(
        self,
        view: ExportView,
        documents: DocumentController,
        conversions: ExportConversions,
        *,
        call_after: CallAfter,
    ) -> None:
        self._view = view
        self._documents = documents
        self._conversions = conversions
        self._call_after = call_after

    def write_document(
        self,
        destination_path: Path,
        document: Document,
        format_key: str,
        *,
        dual_view_results: tuple[object, ...] | None = None,
    ) -> None:
        """Write ``document``; ``dual_view_results`` ``None`` means the document's cached ones (F-9 D6)."""
        descriptor = get_format(format_key)
        if not descriptor.exportable or descriptor.writer is None:
            raise ValueError(f'Unsupported export format: "{format_key}".')
        if dual_view_results is None:
            dual_view_results = self._documents.get_dual_view_results(document.name)
        context = ExportContext(dual_view_results=dual_view_results)
        descriptor.writer(destination_path, document, context)

    def export_document(self, document: Document, format_key: str) -> None:
        descriptor = get_format(format_key)
        destination_path = self._view.choose_export_path(f"{document.name}{descriptor.extension}", descriptor)
        if destination_path is None:
            return
        target_suffix = descriptor.extension
        if destination_path.suffix.casefold() != target_suffix:
            destination_path = destination_path.with_suffix(target_suffix)
        if document.braille is None:
            message = self._conversions.missing_table_message()
            if message is not None:
                self._view.show_error(message, _("Error"))
                return
            self._conversions.convert_for_export(
                document.text,
                on_success=lambda output: self._write_single(
                    Document(document.name, document.text, output.display_text),
                    destination_path,
                    format_key,
                    dual_view_results=output.dual_view_segments,
                ),
                on_error=lambda message: self._view.show_error(message, _("Error")),
            )
            return
        self._write_single(document, destination_path, format_key)

    def _log_unexpected_export_error(self, error: Exception) -> None:
        """Log the traceback of a failed export if it is not an ``OSError`` (F-7).

        An ``OSError`` (locked, read-only, disk full) is expected and the message names it
        fully. Anything else is a bug or text the writer cannot encode, and the packaged
        build has no console. The logger is bound here, not at import, so importing this
        module adds no file handler (as in F-6 review M-6).
        """
        if not isinstance(error, OSError):
            get_logger("dotexpress.gui", "gui.log").error("Unexpected error while exporting a document", exc_info=error)

    def _write_single(self, document: Document, destination_path: Path, format_key: str, **results: object) -> None:
        """Write and report one export; ``results`` is a pending export's ``dual_view_results`` (F-9 D6)."""
        try:
            self.write_document(destination_path, document, format_key, **results)
        except Exception as exc:
            self._log_unexpected_export_error(exc)
            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
            return
        self._view.show_info(_("The document was exported successfully."), _("Export Complete"))

    def export_all(self, format_key: str) -> None:
        destination_dir = self._view.choose_export_directory()
        if destination_dir is None:
            return
        suffix = get_format(format_key).extension
        documents = self._documents.documents_snapshot()
        conflicts = [
            destination_dir / f"{document.name}{suffix}"
            for document in documents
            if (destination_dir / f"{document.name}{suffix}").exists()
        ]
        if conflicts and not self._view.confirm_overwrite_all(conflicts):
            return
        self._export_next(documents, destination_dir, format_key, ExportBatchResult())

    def _export_next(
        self,
        remaining: list[Document],
        destination_dir: Path,
        format_key: str,
        result: ExportBatchResult,
    ) -> None:
        if not remaining:
            self._show_batch_result(result)
            return

        descriptor = get_format(format_key)
        document = remaining[0]
        rest = remaining[1:]
        destination_path = destination_dir / f"{document.name}{descriptor.extension}"

        def continue_batch() -> None:
            self._call_after(self._export_next, rest, destination_dir, format_key, result)

        def write_document(export_document: Document, **results: object) -> None:
            try:
                self.write_document(destination_path, export_document, format_key, **results)
            except Exception as exc:
                self._log_unexpected_export_error(exc)
                result.add_failure(document.name, str(exc))
            else:
                result.add_success(document.name)
            continue_batch()

        if document.braille is not None:
            write_document(document)
            return

        def conversion_failed(message: str) -> None:
            result.add_failure(document.name, message)
            continue_batch()

        message = self._conversions.missing_table_message()
        if message is not None:
            conversion_failed(message)
            return
        self._conversions.convert_for_export(
            document.text,
            on_success=lambda output: write_document(
                Document(document.name, document.text, output.display_text),
                dual_view_results=output.dual_view_segments,
            ),
            on_error=conversion_failed,
        )

    def _show_batch_result(self, result: ExportBatchResult) -> None:
        message = _(result.summary_template).format(**result.summary_values)
        caption = _(result.summary_title)
        if result.all_succeeded:
            self._view.show_info(message, caption)
        else:
            self._view.show_warning(message, caption)
