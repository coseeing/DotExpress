from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from documents.workspace import (
    Document,
    load_document_package,
    load_workspace_documents,
    move_document_package,
    save_document_package,
)
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles


class CaseInsensitivePackageFilesTest(unittest.TestCase):
    """The case-insensitive file model (F-1): the old failures it reproduces and the new move."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)

    def _workspace(self, name: str = "workspace") -> Path:
        directory = self.root / name
        directory.mkdir()
        return directory

    @staticmethod
    def _listing(directory: Path) -> list[str]:
        return sorted(path.name for path in directory.iterdir())

    @staticmethod
    def _members(path: Path) -> list[str]:
        with zipfile.ZipFile(path) as archive:
            return sorted(archive.namelist())

    def test_writing_a_case_variant_rewrites_the_existing_entry_and_keeps_its_spelling(self) -> None:
        # The P1-3 known defect 2 mechanism: Add "Alpha" next to "alpha".
        workspace = self._workspace()
        save_document_package(workspace / "alpha.dep", Document("alpha", "a", "1"))

        CaseInsensitivePackageFiles().write(workspace / "Alpha.dep", Document("Alpha", "A", "2"))

        self.assertEqual(self._listing(workspace), ["alpha.dep"])
        self.assertEqual(self._members(workspace / "alpha.dep"), ["Alpha.brl", "Alpha.txt"])
        self.assertEqual(load_workspace_documents(workspace), ([], [workspace / "alpha.dep"]))

    def test_the_old_rename_sequence_deletes_a_case_only_renamed_package(self) -> None:
        # The P1-3 known defect 1 scenario: write the new package, then unlink the old one.
        workspace = self._workspace()
        save_document_package(workspace / "Alpha.dep", Document("Alpha", "a", "1"))
        files = CaseInsensitivePackageFiles()

        files.write(workspace / "alpha.dep", Document("alpha", "a", "1"))
        if files.exists(workspace / "Alpha.dep"):
            files.remove(workspace / "Alpha.dep")

        self.assertEqual(self._listing(workspace), [])

    def test_replace_resolves_case_variants(self) -> None:
        for keeps in (True, False):
            with self.subTest(replace_keeps_existing_spelling=keeps):
                files = CaseInsensitivePackageFiles(replace_keeps_existing_spelling=keeps)
                own = self._workspace(f"own-{keeps}")
                save_document_package(own / "Alpha.dep", Document("Alpha", "a", "1"))
                alpha_bytes = (own / "Alpha.dep").read_bytes()

                files.replace(own / "Alpha.dep", own / "alpha.dep")

                self.assertEqual(self._listing(own), ["alpha.dep"])
                self.assertEqual((own / "alpha.dep").read_bytes(), alpha_bytes)

                other = self._workspace(f"other-{keeps}")
                save_document_package(other / "alpha.dep", Document("alpha", "a", "1"))
                save_document_package(other / "beta.dep", Document("beta", "b", "2"))
                beta_bytes = (other / "beta.dep").read_bytes()

                files.replace(other / "beta.dep", other / "ALPHA.dep")

                self.assertEqual(self._listing(other), ["alpha.dep" if keeps else "ALPHA.dep"])
                self.assertEqual((other / self._listing(other)[0]).read_bytes(), beta_bytes)

    def test_move_document_package_keeps_a_case_only_renamed_package(self) -> None:
        for keeps in (True, False):
            with self.subTest(replace_keeps_existing_spelling=keeps):
                workspace = self._workspace(f"workspace-{keeps}")
                save_document_package(workspace / "Alpha.dep", Document("Alpha", "a", "1"))

                move_document_package(
                    workspace / "Alpha.dep",
                    workspace / "alpha.dep",
                    Document("alpha", "a", "1"),
                    files=CaseInsensitivePackageFiles(replace_keeps_existing_spelling=keeps),
                )

                self.assertEqual(self._listing(workspace), ["alpha.dep"])
                self.assertEqual(self._members(workspace / "alpha.dep"), ["alpha.brl", "alpha.txt"])
                self.assertEqual(load_document_package(workspace / "alpha.dep"), Document("alpha", "a", "1"))


if __name__ == "__main__":
    unittest.main()
