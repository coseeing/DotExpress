"""Workspace disk operations of the document flows, with the matching controller update.

No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
The order of memory and disk effects is part of the contract: save updates memory
before writing, and Delete All reports a failure before it reloads the workspace.
A package is always written through a temporary file in the workspace, so a failed
save leaves it as it was. Every rename stages the new package and moves the old one
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
Save writes only when the document differs from what was last written to or loaded
from its package; that record changes only after a successful write, so a failed save
is retried by the next one. ``save_open_document`` saves the open document from the
editors; ``save_document`` saves any listed document, such as a conversion result for
a document that is no longer open (F-9).
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
temporary file, and reports its name once; it never replaces a file. It then removes
the temporary files it did not use that hold no package or a package whose content a
document on disk holds; one that holds the only copy of its text stays.
U+0000, which the Windows editors cannot hold, reaches the controller as U+FFFD when
packages are loaded and files imported; the count is kept per document until the
frame takes it to tell the user, and a loaded package is recorded as read, so the
first save of such a document writes the replaced text.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import stat

from documents.controller import DocumentController
from documents.session import DeleteDocumentDecision
from documents.workspace import (
    BatchIssue,
    DEP_EXTENSION,
    Document,
    PackageFiles,
    _displayable,
    _encodable,
    batch_import_documents,
    document_package_path_for_name,
    ensure_workspace_directory,
    load_workspace_documents,
    move_document_package,
    prepare_document_for_save,
    recover_interrupted_packages,
    save_document_package,
)
from i18n import _


@dataclass(frozen=True)
class ImportResult:
    saved: list[Document]
    issues: list[BatchIssue]


@dataclass(frozen=True)
class DeleteAllResult:
    completed: bool
    invalid_paths: list[Path]


@dataclass(frozen=True)
class _SavedPackage:
    """What was last written to or loaded from a package, and the package's fingerprint then."""

    document: Document
    fingerprint: tuple[int, int] | None


def _package_fingerprint(path: Path) -> tuple[int, int] | None:
    """``(st_size, st_mtime_ns)`` of the regular file at ``path``, or ``None`` if there is none."""
    try:
        status = os.stat(path)
    except OSError:
        return None
    if not stat.S_ISREG(status.st_mode):
        return None
    return status.st_size, status.st_mtime_ns


def _displayable_documents(documents: Iterable[Document]) -> tuple[list[Document], dict[str, int]]:
    """``documents`` with U+0000 replaced (F-8 D12), and the count of each name that had any."""
    shown: list[Document] = []
    counts: dict[str, int] = {}
    for document in documents:
        displayable, count = _displayable(document)
        shown.append(displayable)
        if count:
            counts[document.name] = count
    return shown, counts


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
        self._saved: dict[str, _SavedPackage] = {}
        self._recovered_names: list[str] = []
        # Document name -> how many U+0000 were replaced, until the frame reports it (F-8 D12).
        self._nul_pending: dict[str, int] = {}

    @property
    def workspace_dir(self) -> Path:
        return self._workspace_dir

    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def package_name_taken(self, name: str, *, exclude_name: str | None = None) -> bool:
        """Whether something is on disk at ``name``'s package path (F-8 D1).

        A listed package, one that is not listed, a folder or a broken link all count; on
        a case-insensitive file system any spelling does. ``exclude_name`` is a Rename's
        own document: a name equal to it ignoring case is never taken.
        """
        if exclude_name is not None and name.casefold() == exclude_name.casefold():
            return False
        return os.path.lexists(self.package_path(name))

    def free_document_name(self, base: str) -> str:
        """``base`` if no document and no package has it, else ``"base (2)"``, ``"base (3)"``... (F-8 D2)."""
        name = base
        number = 1
        while self._controller.document_name_exists(name) or self.package_name_taken(name):
            number += 1
            name = f"{base} ({number})"
        return name

    def _remember(self, document: Document) -> None:
        """Record ``document`` as its package holds it now, right after a write or a load."""
        fingerprint = _package_fingerprint(self.package_path(document.name))
        self._saved[document.name] = _SavedPackage(_encodable(document), fingerprint)

    def _is_saved(self, document: Document) -> bool:
        """Whether the package already holds ``document`` (F-5 D2); when in doubt, ``False``."""
        record = self._saved.get(document.name)
        if record is None or record.document != document:
            return False
        fingerprint = _package_fingerprint(self.package_path(document.name))
        return fingerprint is not None and fingerprint == record.fingerprint

    def _reset_saved(self, documents: Iterable[Document]) -> None:
        self._saved = {}
        for document in documents:
            self._remember(document)

    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        recovered = recover_interrupted_packages(self._workspace_dir, documents)
        self._recovered_names = [document.name for document in recovered]
        documents = sorted([*documents, *recovered], key=lambda document: (document.name.casefold(), document.name))
        displayable, self._nul_pending = _displayable_documents(documents)
        self._controller.load_documents(displayable)
        # Recorded as read: the replaced text differs, so the first save writes it.
        self._reset_saved(documents)
        return invalid_paths

    def take_recovered_document_names(self) -> list[str]:
        """The documents the last ``load_documents`` put back from temporary files, once (F-8 D4)."""
        names, self._recovered_names = self._recovered_names, []
        return names

    def take_replaced_character_count(self, name: str) -> int:
        """How many U+0000 of ``name`` were replaced and not yet reported; 0 from then on (F-8 D12)."""
        return self._nul_pending.pop(name, 0)

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
        # A pending document's braille stays pending here: the editor shows none (F-5).
        return self.save_document(prepare_document_for_save(document, text=text, braille=braille))

    def save_document(self, document: Document) -> Document | None:
        """Put ``document`` in memory, then write its package unless it already holds it (F-9 D1).

        ``None`` if no listed document has its name. The braille is kept as given, also for
        a document that was pending. Raises like ``save_document_package``; memory has the
        new document then, and the next save of it retries the write.
        """
        if self._controller.get_document(document.name) is None:
            return None
        updated_document = _encodable(document)
        self._controller.replace_document(updated_document)
        if self._is_saved(updated_document):
            return updated_document
        save_document_package(self.package_path(updated_document.name), updated_document)
        self._remember(updated_document)
        return updated_document

    def create_document(self, document: Document) -> None:
        package_path = self.package_path(document.name)
        if os.path.lexists(package_path):
            # Created after the name was checked, or never listed (F-8 D1): not replaced.
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))
        save_document_package(package_path, document)
        self._remember(document)
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
        on_disk = {path.stem for path in self._workspace_dir.glob(f"*{DEP_EXTENSION}")}
        documents, load_issues = batch_import_documents(
            list(paths),
            format_key=format_key,
            existing_names=set(self._controller.document_names) | on_disk,
        )
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
        for document in documents:
            # The replaced text is what gets saved (F-8 D12).
            document, count = _displayable(document)
            package_path = self.package_path(document.name)
            try:
                if os.path.lexists(package_path):
                    # Created after the names were checked (F-8 D1): not replaced.
                    raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))
                save_document_package(package_path, document)
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=_("Failed to save document: {error}").format(error=exc)))
                continue
            self._remember(document)
            saved.append(document)
            if count:
                self._nul_pending[document.name] = count
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)

    def rename_document(self, source_name: str, new_name: str) -> Document | None:
        if source_name == new_name:
            raise ValueError("A document cannot be renamed to its own name.")
        source = self._controller.get_document(source_name)
        if source is None:
            return None
        renamed = Document(new_name, source.text, source.braille)
        move_document_package(
            self.package_path(source_name),
            self.package_path(new_name),
            renamed,
            files=self._package_files,
        )
        self._saved.pop(source_name, None)
        self._remember(renamed)
        if source_name in self._nul_pending:
            self._nul_pending[new_name] = self._nul_pending.pop(source_name)
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
        package_path = self.package_path(name)
        if package_path.exists():
            package_path.unlink()
        self._saved.pop(name, None)
        self._nul_pending.pop(name, None)
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
                displayable, _counts = _displayable_documents(remaining_documents)
                self._controller.restore_documents_after_delete_all_failure(displayable)
                self._reset_saved(remaining_documents)
                # Only documents that were still to be reported are reported later.
                remaining = {document.name for document in remaining_documents}
                self._nul_pending = {name: count for name, count in self._nul_pending.items() if name in remaining}
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._saved = {}
        self._nul_pending = {}
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
