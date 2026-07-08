from __future__ import annotations

from documents.session import (
    DeleteDocumentDecision,
    plan_delete_document,
    plan_open_document,
    rename_document_in_list,
    replace_document,
)
from documents.workspace import Document


class DocumentController:
    def __init__(
        self,
        *,
        documents: list[Document] | None = None,
        open_name: str | None = None,
        selected_name: str | None = None,
        dual_view_results_by_document: dict[str, tuple[object, ...]] | None = None,
    ) -> None:
        self.documents = documents if documents is not None else []
        self.open_name = open_name
        self.selected_name = selected_name
        self.dual_view_results_by_document = (
            dual_view_results_by_document if dual_view_results_by_document is not None else {}
        )

    @property
    def document_names(self) -> list[str]:
        return [document.name for document in self.documents]

    @property
    def open_document_name(self) -> str | None:
        return self.open_name

    @property
    def selected_document_name(self) -> str | None:
        return self.selected_name

    def get_document(self, name: str | None) -> Document | None:
        if not name:
            return None
        for document in self.documents:
            if document.name == name:
                return document
        return None

    def sort_documents(self) -> None:
        self.documents.sort(key=lambda document: (document.name.casefold(), document.name))

    def set_state(
        self,
        *,
        documents: list[Document],
        open_name: str | None,
        selected_name: str | None,
        dual_view_results_by_document: dict[str, tuple[object, ...]],
    ) -> None:
        self.documents = documents
        self.open_name = open_name
        self.selected_name = selected_name
        self.dual_view_results_by_document = dual_view_results_by_document

    def open_document(self, name: str | None) -> Document | None:
        decision = plan_open_document(self.documents, name)
        self.open_name = decision.open_name
        self.selected_name = decision.selected_name
        return decision.document

    def replace_document(self, updated_document: Document) -> bool:
        return replace_document(self.documents, updated_document)

    def rename_document(self, source_name: str, new_name: str) -> Document | None:
        renamed_document = rename_document_in_list(self.documents, source_name, new_name)
        if renamed_document is None:
            return None
        if self.open_name == source_name:
            self.open_name = renamed_document.name
        if self.selected_name == source_name:
            self.selected_name = renamed_document.name
        if source_name in self.dual_view_results_by_document:
            self.dual_view_results_by_document[new_name] = self.dual_view_results_by_document.pop(source_name)
        return renamed_document

    def delete_document(self, name: str) -> DeleteDocumentDecision:
        decision = plan_delete_document(self.documents, name, self.open_name)
        self.documents[:] = [document for document in self.documents if document.name != name]
        self.dual_view_results_by_document.pop(name, None)
        if not self.documents:
            self.open_name = None
            self.selected_name = None
            return decision
        if decision.was_open:
            self.open_name = decision.preferred_name
        if self.selected_name == name:
            self.selected_name = decision.preferred_name
        return decision

    def delete_all_documents(self) -> None:
        self.documents.clear()
        self.open_name = None
        self.selected_name = None
        self.dual_view_results_by_document.clear()

    def restore_documents_after_delete_all_failure(self, remaining_documents: list[Document]) -> None:
        self.documents = remaining_documents
        remaining_document_names = {document.name for document in remaining_documents}
        self.dual_view_results_by_document = {
            name: results
            for name, results in self.dual_view_results_by_document.items()
            if name in remaining_document_names
        }
        if self.open_name not in remaining_document_names:
            self.open_name = None
        if self.selected_name not in remaining_document_names:
            self.selected_name = None
