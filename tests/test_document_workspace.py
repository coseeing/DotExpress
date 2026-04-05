import tempfile
import unittest
from pathlib import Path

from document_workspace import (
    Document,
    choose_selection_after_delete,
    ensure_workspace_directory,
    load_document_package,
    load_workspace_documents,
    normalize_document_name,
    save_document_package,
)


class DocumentWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self._tmpdir.name) / "workspace"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_ensure_workspace_directory_creates_folder(self) -> None:
        workspace = ensure_workspace_directory(self.workspace_dir)
        self.assertEqual(workspace, self.workspace_dir)
        self.assertTrue(self.workspace_dir.exists())
        self.assertTrue(self.workspace_dir.is_dir())

    def test_normalize_document_name_accepts_unicode_trims_and_allows_default(self) -> None:
        self.assertEqual(normalize_document_name("  default中文12  "), "default中文12")
        self.assertEqual(normalize_document_name(" default "), "default")

    def test_normalize_document_name_rejects_invalid_names(self) -> None:
        for value in ["", " ", ".", "a/b", r"a\\b", "this-name-is-way-too-long"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_document_name(value)

    def test_save_and_load_document_package_roundtrip(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        package_path = self.workspace_dir / "lesson1.dep"
        ensure_workspace_directory(self.workspace_dir)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_load_document_package_rejects_mismatched_internal_names(self) -> None:
        ensure_workspace_directory(self.workspace_dir)
        package_path = self.workspace_dir / "lesson1.dep"
        save_document_package(package_path, Document(name="math", text="source", braille="braille"))
        with self.assertRaises(ValueError):
            load_document_package(package_path)

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        ensure_workspace_directory(self.workspace_dir)
        save_document_package(self.workspace_dir / "Beta.dep", Document(name="Beta", text="b", braille="1"))
        save_document_package(self.workspace_dir / "alpha.dep", Document(name="alpha", text="a", braille="2"))
        save_document_package(self.workspace_dir / "bad.dep", Document(name="other", text="x", braille="3"))
        documents, invalid_paths = load_workspace_documents(self.workspace_dir)
        self.assertEqual([document.name for document in documents], ["alpha", "Beta"])
        self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])

    def test_choose_selection_after_delete_prefers_previous_item(self) -> None:
        names = ["alpha", "math", "zoo"]
        self.assertEqual(choose_selection_after_delete(names, "math"), "alpha")

    def test_choose_selection_after_delete_uses_next_when_first_removed(self) -> None:
        names = ["alpha", "math", "zoo"]
        self.assertEqual(choose_selection_after_delete(names, "alpha"), "math")


if __name__ == "__main__":
    unittest.main()
