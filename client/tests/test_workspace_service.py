from __future__ import annotations

import ast
import tempfile
import unittest
import zipfile
from pathlib import Path

from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"


class DocumentWorkspaceServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"

    def _service(self, documents=(), **state) -> DocumentWorkspaceService:
        self.controller = DocumentController(documents=list(documents), **state)
        return DocumentWorkspaceService(self.controller, self.workspace)

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

        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    def test_rename_unlink_failure_propagates_and_leaves_both_packages(self) -> None:
        # KNOWN BUG (P1-3 spec, known defect 3), pinned as it is today, NOT desired
        # behavior: the new package stays on disk next to the old one while the
        # controller keeps only the old name. A later fix task flips this.
        self._block("alpha")
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with self.assertRaises(OSError):
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
        self.assertEqual(self._state(), before)

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
