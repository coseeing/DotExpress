from __future__ import annotations

from dataclasses import dataclass, field


EXPORT_COMPLETE_TITLE = "Export Complete"
EXPORT_COMPLETE_WITH_ERRORS_TITLE = "Export Complete with Errors"
EXPORT_ALL_SUCCESS_MESSAGE = "All documents were exported successfully."
EXPORT_ALL_PARTIAL_MESSAGE = (
    "Exported documents: {success_count}\n"
    "Failed documents: {failure_count}\n"
    "\n"
    "{failures}"
)


@dataclass(frozen=True)
class ExportFailure:
    document_name: str
    reason: str


@dataclass
class ExportBatchResult:
    successful_names: list[str] = field(default_factory=list)
    failures: list[ExportFailure] = field(default_factory=list)

    def add_success(self, document_name: str) -> None:
        self.successful_names.append(document_name)

    def add_failure(self, document_name: str, reason: str) -> None:
        self.failures.append(ExportFailure(document_name, reason))

    @property
    def all_succeeded(self) -> bool:
        return not self.failures

    @property
    def summary_title(self) -> str:
        return EXPORT_COMPLETE_TITLE if self.all_succeeded else EXPORT_COMPLETE_WITH_ERRORS_TITLE

    @property
    def summary_template(self) -> str:
        return EXPORT_ALL_SUCCESS_MESSAGE if self.all_succeeded else EXPORT_ALL_PARTIAL_MESSAGE

    @property
    def summary_values(self) -> dict[str, int | str]:
        if self.all_succeeded:
            return {}
        return {
            "success_count": len(self.successful_names),
            "failure_count": len(self.failures),
            "failures": "\n".join(f"{item.document_name}: {item.reason}" for item in self.failures),
        }


BatchExportResult = ExportBatchResult
