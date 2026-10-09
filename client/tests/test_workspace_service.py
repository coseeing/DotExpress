from __future__ import annotations

import ast
import errno
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import documents.workspace_service as workspace_service
from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"


class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that one ``replace`` raises ``PermissionError``.

    It fails when the source is named ``source_name`` (moving the old package aside) or
    the destination is named ``destination_name`` (installing the new package). Names
    are compared as strings: ``Path`` equality ignores case on Windows. The error names
    both paths, as a failed rename does (spec D8).
    """

    def __init__(self, *, source_name: str | None = None, destination_name: str | None = None) -> None:
        self.source_name = source_name
        self.destination_name = destination_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name or Path(destination).name == self.destination_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)


class _FailingRemovePackageFiles(PackageFiles):
    """The real file operations, except that ``remove`` raises ``PermissionError``."""

    def remove(self, path: Path) -> None:
        raise PermissionError(errno.EACCES, "injected", str(path))


class _RecordingPackageFiles(PackageFiles):
    """The real file operations, recording the source and destination name of every ``replace``."""

    def __init__(self) -> None:
        self.replaced: list[tuple[str, str]] = []

    def replace(self, source: Path, destination: Path) -> None:
        super().replace(source, destination)
        self.replaced.append((Path(source).name, Path(destination).name))


class _RecordingCaseInsensitivePackageFiles(CaseInsensitivePackageFiles):
    """The case-insensitive model, recording the destination name of every ``replace``."""

    def __init__(self) -> None:
        super().__init__()
        self.replaced_onto: list[str] = []

    def replace(self, source: Path, destination: Path) -> None:
        super().replace(source, destination)
        self.replaced_onto.append(Path(destination).name)


class DocumentWorkspaceServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"

    def _service(self, documents=(), *, package_files=None, **state) -> DocumentWorkspaceService:
        self.controller = DocumentController(documents=list(documents), **state)
        if package_files is None:
            return DocumentWorkspaceService(self.controller, self.workspace)
        return DocumentWorkspaceService(self.controller, self.workspace, package_files=package_files)

    def _write(self, *documents: Document) -> None:
        for document in documents:
            save_document_package(self.workspace / f"{document.name}.dep", document)

    def _block(self, name: str) -> Path:
        """A non-empty directory at ``<ws>/<name>.dep``: writing or unlinking it raises ``OSError``."""
        path = self.workspace / f"{name}.dep"
        (path / "keep").mkdir(parents=True)
        return path

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace.iterdir())

    def _package(self, name: str) -> Document:
        return load_document_package(self.workspace / f"{name}.dep")

    def _members(self, name: str) -> list[str]:
        with zipfile.ZipFile(self.workspace / f"{name}.dep") as archive:
            return sorted(archive.namelist())

    def _state(self) -> tuple:
        return (
            list(self.controller.documents),
            self.controller.open_name,
            self.controller.selected_name,
            dict(self.controller.dual_view_results_by_document),
        )

    # --- basics ------------------------------------------------------------

    def test_workspace_dir_and_package_path(self) -> None:
        service = self._service()

        self.assertEqual(service.workspace_dir, self.workspace)
        self.assertEqual(service.package_path("alpha"), self.workspace / "alpha.dep")
        self.assertFalse(self.workspace.exists())

    def test_module_imports_neither_wx_nor_gui(self) -> None:
        tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])

        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)

    # --- load and invalid files ------------------------------------------

    def test_load_documents_creates_directory_and_loads_sorted_documents(self) -> None:
        service = self._service(
            [Document("old", "o", "1")],
            open_name="old",
            selected_name="old",
            dual_view_results_by_document={"old": ("segment",)},
        )

        self.assertEqual(service.load_documents(), [])
        self.assertTrue(self.workspace.is_dir())
        self.assertEqual(self._state(), ([], None, None, {}))

        self._write(Document("beta", "b", "2"), Document("Alpha", "a", None))
        (self.workspace / "bad.dep").write_bytes(b"not a zip")

        invalid_paths = service.load_documents()

        self.assertEqual(invalid_paths, [self.workspace / "bad.dep"])
        self.assertEqual(self.controller.documents, [Document("Alpha", "a", None), Document("beta", "b", "2")])

    def test_delete_invalid_files_reports_each_error_and_continues(self) -> None:
        blocked = self._block("a-blocked")
        corrupt = self.workspace / "b-corrupt.dep"
        corrupt.write_bytes(b"not a zip")
        missing = self.workspace / "c-missing.dep"
        errors: list[OSError] = []

        self._service().delete_invalid_files([blocked, corrupt, missing], on_error=errors.append)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], OSError)
        self.assertIn("a-blocked.dep", str(errors[0]))
        self.assertEqual(self._listing(), ["a-blocked.dep"])

    # --- save --------------------------------------------------------------

    def test_save_open_document_updates_memory_and_disk(self) -> None:
        service = self._service([Document("alpha", "a", "1"), Document("beta", "b", None)], open_name="alpha")

        saved = service.save_open_document(text="edited", braille="edited braille")

        self.assertEqual(saved, Document("alpha", "edited", "edited braille"))
        self.assertEqual(self.controller.get_document("alpha"), saved)
        self.assertEqual(self._package("alpha"), saved)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_open_document_keeps_pending_braille_pending(self) -> None:
        service = self._service([Document("alpha", "a", None)], open_name="alpha")

        saved = service.save_open_document(text="edited", braille="ignored")

        self.assertEqual(saved, Document("alpha", "edited", None))
        self.assertEqual(self._package("alpha"), Document("alpha", "edited", None))
        self.assertIn("alpha.meta.json", self._members("alpha"))

    def test_save_without_open_document_does_nothing(self) -> None:
        for state in ({}, {"open_name": "ghost"}):
            with self.subTest(state=state):
                service = self._service([Document("alpha", "a", "1")], **state)

                self.assertIsNone(service.save_open_document(text="edited", braille="b"))
                self.assertEqual(self.controller.documents, [Document("alpha", "a", "1")])
                self.assertFalse(self.workspace.exists())

    def test_save_failure_propagates_after_memory_update(self) -> None:
        self._block("alpha")
        service = self._service([Document("alpha", "a", "1")], open_name="alpha")

        with self.assertRaises(OSError):
            service.save_open_document(text="edited", braille="edited braille")

        self.assertEqual(self.controller.documents, [Document("alpha", "edited", "edited braille")])

    def test_save_failure_keeps_the_package_and_updates_memory(self) -> None:
        # Memory is updated first (the documented contract); the package keeps its bytes.
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service([Document("alpha", "a", "1")], open_name="alpha")

        with self.assertRaises(UnicodeEncodeError):
            service.save_open_document(text="\ud800", braille="1")

        self.assertEqual(self.controller.documents, [Document("alpha", "\ud800", "1")])
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- create ------------------------------------------------------------

    def test_create_document_writes_then_adds(self) -> None:
        service = self._service([Document("zoo", "z", "1")])

        service.create_document(Document("alpha", "", ""))
        service.create_document(Document("new", "", None))

        self.assertEqual(self.controller.document_names, ["zoo", "alpha", "new"])
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
        self.assertEqual(self._members("new"), ["new.brl", "new.meta.json", "new.txt"])

    def test_create_document_failure_adds_nothing(self) -> None:
        self._block("alpha")
        service = self._service()

        with self.assertRaises(OSError):
            service.create_document(Document("alpha", "", ""))

        self.assertEqual(self.controller.documents, [])

    # --- import ------------------------------------------------------------

    def _sources(self, **texts: str) -> list[Path]:
        source_dir = self.root / "sources"
        source_dir.mkdir(exist_ok=True)
        paths = []
        for stem, text in texts.items():
            path = source_dir / f"{stem}.txt"
            path.write_text(text, encoding="utf-8")
            paths.append(path)
        return paths

    def test_import_files_saves_and_adds_in_order(self) -> None:
        service = self._service([Document("zoo", "z", "1")])

        result = service.import_files(self._sources(delta="d", beta="b"), format_key="all")

        expected = [Document("beta", "b", None), Document("delta", "d", None)]
        self.assertEqual(result, ImportResult(saved=expected, issues=[]))
        self.assertEqual(self.controller.document_names, ["zoo", "beta", "delta"])
        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])

    def test_import_files_lists_load_issues_before_save_issues(self) -> None:
        self._block("delta")
        service = self._service([Document("alpha", "a", "1")])
        sources = self._sources(Alpha="dup", beta="b", delta="d")

        result = service.import_files(sources, format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason='Document "Alpha" already exists.'))
        self.assertEqual(result.issues[1].path, self.workspace / "delta.dep")
        self.assertIn("delta.dep", result.issues[1].reason)

    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
        # F-3 (D9): an error that is not an OSError becomes an issue too; before, it
        # escaped after beta.dep was written, and beta never reached the list.
        service = self._service([Document("zoo", "z", "1")])
        real_save = workspace_service.save_document_package
        error = UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogates not allowed")

        def save(path, document, **kwargs):
            if document.name == "delta":
                raise error
            return real_save(path, document, **kwargs)

        with patch.object(workspace_service, "save_document_package", side_effect=save):
            result = service.import_files(self._sources(beta="b", delta="d"), format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "delta.dep", reason=str(error))])
        self.assertEqual(self.controller.document_names, ["zoo", "beta"])
        self.assertEqual(self._listing(), ["beta.dep"])

    def test_import_files_rejects_unknown_format(self) -> None:
        service = self._service()

        with self.assertRaisesRegex(ValueError, 'Unsupported import format: "nope"'):
            service.import_files(self._sources(beta="b"), format_key="nope")

        self.assertEqual(self.controller.documents, [])

    # --- rename ------------------------------------------------------------

    def test_rename_writes_new_package_deletes_old_and_updates_controller(self) -> None:
        self._write(Document("alpha", "a", None))
        service = self._service(
            [Document("alpha", "a", None), Document("beta", "b", "2")],
            open_name="alpha",
            selected_name="alpha",
            dual_view_results_by_document={"alpha": ("segment",)},
        )

        renamed = service.rename_document("alpha", "gamma")

        self.assertEqual(renamed, Document("gamma", "a", None))
        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", None))
        self.assertEqual(
            self._state(),
            ([Document("gamma", "a", None), Document("beta", "b", "2")], "gamma", "gamma", {"gamma": ("segment",)}),
        )

    def test_rename_with_missing_old_package(self) -> None:
        service = self._service([Document("alpha", "a", "1")])

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))
        self.assertEqual(self._listing(), ["gamma.dep"])

    def test_rename_write_failure_propagates_and_keeps_state(self) -> None:
        self._write(Document("alpha", "a", "1"))
        self._block("gamma")
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with self.assertRaises(OSError):
            service.rename_document("alpha", "gamma")

        # gamma.dep is the blocking folder; the staged package and the aside file are gone.
        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    def test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state(self) -> None:
        # Was the KNOWN BUG test of P1-3 known defect 3 (the new package was written next
        # to the old one, the old one could not be removed, and both stayed on disk),
        # fixed by F-3: the old package is moved aside before the new one is installed.
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingReplacePackageFiles(source_name="alpha.dep"),
            open_name="alpha",
            selected_name="alpha",
        )
        before = self._state()

        with self.assertRaises(PermissionError) as raised:
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertIn("alpha.dep", str(raised.exception))
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_regular_rename_install_failure_puts_the_old_package_back(self) -> None:
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingReplacePackageFiles(destination_name="gamma.dep"),
            open_name="alpha",
            selected_name="alpha",
        )
        before = self._state()

        with self.assertRaises(PermissionError):
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_rename_of_an_unwritable_package_is_refused(self) -> None:
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.workspace / 'alpha.dep')!r}",
        )
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package(self) -> None:
        # The rename is complete once the new package is installed; an aside file that
        # cannot be removed stays as a .tmp the workspace never loads (F-1 behavior).
        self._write(Document("alpha", "a", "1"))
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingRemovePackageFiles(),
            open_name="alpha",
            selected_name="alpha",
        )

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))

        listing = self._listing()
        self.assertEqual(len(listing), 2, listing)
        self.assertRegex(listing[0], r"^\.alpha\.dep\..+\.tmp$")
        self.assertEqual(listing[1], "gamma.dep")
        self.assertEqual(self.controller.document_names, ["gamma"])
        reloaded = DocumentController()
        self.assertEqual(DocumentWorkspaceService(reloaded, self.workspace).load_documents(), [])
        self.assertEqual(reloaded.documents, [Document("gamma", "a", "1")])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_rename_of_a_package_held_open_by_another_program(self) -> None:
        # Moving the package aside needs delete sharing. Without it (a zip tool, an
        # editor) the rename fails and exactly the old package stays; before F-3 the new
        # package was left next to it. With it (an antivirus scanner) the rename completes.
        for label, share in SHARE_MODES:
            with self.subTest(share=label):
                self.workspace = self.root / label.replace("+", "-")
                self._write(Document("alpha", "a", "1"))
                alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
                service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
                before = self._state()
                release = hold_open(self, self.workspace / "alpha.dep", share)
                try:
                    if share & SHARE_DELETE:
                        service.rename_document("alpha", "gamma")
                    else:
                        with self.assertRaises(PermissionError) as raised:
                            service.rename_document("alpha", "gamma")
                finally:
                    release()

                if share & SHARE_DELETE:
                    self.assertEqual(self._listing(), ["gamma.dep"])
                    self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
                    self.assertEqual(self.controller.document_names, ["gamma"])
                else:
                    self.assertEqual(self._listing(), ["alpha.dep"])
                    self.assertEqual(raised.exception.winerror, 32)
                    self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
                    self.assertEqual(self._state(), before)

    def _assert_case_only_rename(self, service: DocumentWorkspaceService) -> None:
        self.assertEqual(service.rename_document("Alpha", "alpha"), Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._package("beta"), Document("beta", "b", "2"))
        self.assertEqual(
            self._state(),
            ([Document("alpha", "a", "1"), Document("beta", "b", "2")], "alpha", "alpha", {"alpha": ("segment",)}),
        )

    def _case_only_service(self, package_files=None) -> DocumentWorkspaceService:
        self._write(Document("Alpha", "a", "1"), Document("beta", "b", "2"))
        return self._service(
            [Document("Alpha", "a", "1"), Document("beta", "b", "2")],
            package_files=package_files,
            open_name="Alpha",
            selected_name="Alpha",
            dual_view_results_by_document={"Alpha": ("segment",)},
        )

    def test_case_only_rename_moves_the_package_and_updates_the_controller(self) -> None:
        self._assert_case_only_rename(self._case_only_service())

    def test_case_only_rename_on_a_case_insensitive_file_model(self) -> None:
        # F-1: the Linux stand-in for Windows and macOS (P1-3 known defect 1 lost the package).
        self._assert_case_only_rename(self._case_only_service(CaseInsensitivePackageFiles()))

    def test_case_only_rename_on_a_case_insensitive_file_model_survives_a_reload(self) -> None:
        # F-1 end to end: the service's real case-only rename on the model, then a fresh
        # load of the workspace (the next start). On Linux the old rename path never calls
        # package_files, so the test also checks that the model installed alpha.dep.
        files = _RecordingCaseInsensitivePackageFiles()
        service = self._case_only_service(files)

        service.rename_document("Alpha", "alpha")

        self.assertIn("alpha.dep", files.replaced_onto)
        reloaded = DocumentController()
        invalid_paths = DocumentWorkspaceService(reloaded, self.workspace).load_documents()
        self.assertEqual(invalid_paths, [])
        self.assertEqual(reloaded.documents, [Document("alpha", "a", "1"), Document("beta", "b", "2")])
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])

    def test_case_only_rename_install_failure_propagates_and_keeps_state(self) -> None:
        service = self._case_only_service(_FailingReplacePackageFiles(destination_name="alpha.dep"))
        alpha_bytes = (self.workspace / "Alpha.dep").read_bytes()
        before = self._state()

        with self.assertRaises(OSError):
            service.rename_document("Alpha", "alpha")

        self.assertEqual(self._listing(), ["Alpha.dep", "beta.dep"])
        self.assertEqual((self.workspace / "Alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_regular_rename_moves_the_old_package_aside_before_installing(self) -> None:
        # F-3 (D5): replaces the F-1 (D6) guard that kept regular renames on the old
        # write-then-unlink sequence. The old package leaves its name before the new one
        # takes its own, so nothing is removed under a name that can alias the new one.
        self._write(Document("alpha", "a", "1"))
        files = _RecordingPackageFiles()
        service = self._service([Document("alpha", "a", "1")], package_files=files)

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))

        self.assertEqual(len(files.replaced), 2, files.replaced)
        (moved, aside), (staged, installed) = files.replaced
        self.assertEqual(moved, "alpha.dep")
        self.assertRegex(aside, r"^\.alpha\.dep\..+\.tmp$")
        self.assertRegex(staged, r"^\.gamma\.dep\..+\.tmp$")
        self.assertEqual(installed, "gamma.dep")
        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))

    def test_rename_unknown_source_does_nothing(self) -> None:
        service = self._service([Document("alpha", "a", "1")])

        self.assertIsNone(service.rename_document("ghost", "gamma"))
        self.assertFalse(self.workspace.exists())

    def test_rename_to_the_same_name_is_refused(self) -> None:
        self._write(Document("alpha", "a", "1"))
        service = self._service([Document("alpha", "a", "1")])

        with self.assertRaises(ValueError):
            service.rename_document("alpha", "alpha")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))

    # --- delete ------------------------------------------------------------

    def test_delete_document_unlinks_and_applies_decision(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("zoo", "z", "3")]
        self._write(*documents)
        service = self._service(
            documents,
            open_name="beta",
            selected_name="beta",
            dual_view_results_by_document={"alpha": ("keep",), "beta": ("drop",)},
        )

        decision = service.delete_document("beta")

        self.assertEqual((decision.preferred_name, decision.was_open), ("alpha", True))
        self.assertEqual(self._listing(), ["alpha.dep", "zoo.dep"])
        self.assertEqual(self._state(), ([documents[0], documents[2]], "alpha", "alpha", {"alpha": ("keep",)}))

    def test_delete_document_with_missing_package(self) -> None:
        service = self._service([Document("alpha", "a", "1")])

        service.delete_document("alpha")

        self.assertEqual(self.controller.documents, [])
        self.assertFalse(self.workspace.exists())

    def test_delete_document_unlink_failure_keeps_state(self) -> None:
        self._block("alpha")
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with self.assertRaises(OSError):
            service.delete_document("alpha")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._state(), before)

    # --- Delete All --------------------------------------------------------

    def test_delete_all_success_clears_disk_and_controller(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write(*documents)
        errors: list[OSError] = []
        service = self._service(
            documents,
            open_name="alpha",
            selected_name="beta",
            dual_view_results_by_document={"alpha": ("segment",)},
        )

        result = service.delete_all_documents(on_error=errors.append)

        self.assertEqual(result, DeleteAllResult(completed=True, invalid_paths=[]))
        self.assertEqual(errors, [])
        self.assertEqual(self._listing(), [])
        self.assertEqual(self._state(), ([], None, None, {}))

    def test_delete_all_failure_reports_before_reload_and_restores_from_disk(self) -> None:
        documents = [
            Document("alpha", "a", "1"),
            Document("beta", "b", "2"),
            Document("gamma", "c", "3"),
            Document("zoo", "z", "4"),
        ]
        self._write(documents[0], documents[2], Document("zoo", "z on disk", "4"))
        self._block("beta")
        seen: list[tuple] = []
        errors: list[OSError] = []

        def on_error(error: OSError) -> None:
            errors.append(error)
            seen.append((self._listing(), self.controller.document_names))

        service = self._service(
            documents,
            open_name="alpha",
            selected_name="zoo",
            dual_view_results_by_document={"alpha": ("a",), "beta": ("b",), "zoo": ("z",), "ghost": ("g",)},
        )

        result = service.delete_all_documents(on_error=on_error)

        self.assertEqual(result, DeleteAllResult(completed=False, invalid_paths=[self.workspace / "beta.dep"]))
        self.assertEqual(len(errors), 1)
        self.assertIn("beta.dep", str(errors[0]))
        self.assertEqual(seen, [(["beta.dep", "gamma.dep", "zoo.dep"], ["alpha", "beta", "gamma", "zoo"])])
        self.assertEqual(self._listing(), ["beta.dep", "gamma.dep", "zoo.dep"])
        self.assertEqual(
            self._state(),
            ([documents[2], Document("zoo", "z on disk", "4")], None, "zoo", {"zoo": ("z",)}),
        )

    def test_delete_all_reload_error_propagates_after_on_error(self) -> None:
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write(documents[0])
        self._block("beta")
        calls: list[str] = []
        service = self._service(documents)

        def on_error(_error: OSError) -> None:
            calls.append("on_error")
            # Make the reload fail: the workspace directory is replaced by a file.
            for path in sorted(self.workspace.rglob("*"), reverse=True):
                path.rmdir() if path.is_dir() else path.unlink()
            self.workspace.rmdir()
            self.workspace.write_text("", encoding="utf-8")

        with self.assertRaises(OSError):
            service.delete_all_documents(on_error=on_error)

        self.assertEqual(calls, ["on_error"])
        self.assertEqual(self.controller.documents, documents)


if __name__ == "__main__":
    unittest.main()
