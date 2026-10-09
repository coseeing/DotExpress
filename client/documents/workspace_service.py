"""Workspace disk operations of the document flows, with the matching controller update.

No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
The order of memory and disk effects is part of the contract: save updates memory
before writing, and Delete All reports a failure before it reloads the workspace.
A package is always written through a temporary file in the workspace, so a failed
save leaves it as it was. Every rename stages the new package and moves the old one
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from documents.controller import DocumentController
from documents.session import DeleteDocumentDecision
from documents.workspace import (
    BatchIssue,
    Document,
    PackageFiles,
    batch_import_documents,
    document_package_path_for_name,
    ensure_workspace_directory,
    load_workspace_documents,
    move_document_package,
    prepare_document_for_save,
    save_document_package,
)


@dataclass(frozen=True)
class ImportResult:
    saved: list[Document]
    issues: list[BatchIssue]


@dataclass(frozen=True)
class DeleteAllResult:
    completed: bool
    invalid_paths: list[Path]


class DocumentWorkspaceService:
    def __init__(
        self,
        controller: DocumentController,
        workspace_dir: Path,
        *,
        package_files: PackageFiles | None = None,
    ) -> None:
        self._controller = controller
        self._workspace_dir = Path(workspace_dir)
        self._package_files = package_files or PackageFiles()

    @property
    def workspace_dir(self) -> Path:
        return self._workspace_dir

    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        self._controller.load_documents(documents)
        return invalid_paths

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                on_error(exc)

    def save_open_document(self, *, text: str, braille: str) -> Document | None:
        document = self._controller.get_document(self._controller.open_document_name)
        if document is None:
            return None
        updated_document = prepare_document_for_save(document, text=text, braille=braille)
        self._controller.replace_document(updated_document)
        save_document_package(self.package_path(updated_document.name), updated_document)
        return updated_document

    def create_document(self, document: Document) -> None:
        save_document_package(self.package_path(document.name), document)
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
        documents, load_issues = batch_import_documents(
            list(paths),
            format_key=format_key,
            existing_names=set(self._controller.document_names),
        )
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
        for document in documents:
            package_path = self.package_path(document.name)
            try:
                save_document_package(package_path, document)
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=str(exc)))
                continue
            saved.append(document)
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)

    def rename_document(self, source_name: str, new_name: str) -> Document | None:
        if source_name == new_name:
            raise ValueError("A document cannot be renamed to its own name.")
        source = self._controller.get_document(source_name)
        if source is None:
            return None
        move_document_package(
            self.package_path(source_name),
            self.package_path(new_name),
            Document(new_name, source.text, source.braille),
            files=self._package_files,
        )
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
        package_path = self.package_path(name)
        if package_path.exists():
            package_path.unlink()
        return self._controller.delete_document(name)

    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
        for document in self._controller.documents_snapshot():
            package_path = self.package_path(document.name)
            try:
                if package_path.exists():
                    package_path.unlink()
            except OSError as exc:
                on_error(exc)
                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
                self._controller.restore_documents_after_delete_all_failure(remaining_documents)
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
