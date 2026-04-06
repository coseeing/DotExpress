import tempfile
import unittest
from pathlib import Path

from document_workspace import (
    BatchIssue,
    Document,
    batch_import_documents_from_folder,
    batch_export_documents_to_folder,
    choose_selection_after_delete,
    ensure_workspace_directory,
    export_document_brl,
    load_document_package,
    load_text_document,
    load_workspace_documents,
    normalize_document_name,
    prepare_document_for_save,
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

    def test_save_and_load_document_package_preserves_pending_braille_state(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        ensure_workspace_directory(self.workspace_dir)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_document_package_can_skip_pending_metadata_for_exports(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        ensure_workspace_directory(self.workspace_dir)
        save_document_package(package_path, document, include_pending_metadata=False)

        import zipfile

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["lesson1.brl", "lesson1.txt"])

    def test_load_document_package_rejects_mismatched_internal_names(self) -> None:
        ensure_workspace_directory(self.workspace_dir)
        package_path = self.workspace_dir / "lesson1.dep"
        save_document_package(package_path, Document(name="math", text="source", braille="braille"))
        with self.assertRaises(ValueError):
            load_document_package(package_path)

    def test_load_text_document_uses_stem_and_sets_pending_braille(self) -> None:
        source_path = self.workspace_dir / "lesson1.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="lesson1", text="hello", braille=None))

    def test_export_document_brl_writes_plain_braille_text(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        output_path = self.workspace_dir / "lesson1.brl"
        export_document_brl(output_path, document)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "⠇⠑⠎⠎")

    def test_batch_import_documents_from_folder_imports_txt_only_and_reports_duplicates(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "alpha.txt").write_text("A", encoding="utf-8")
        (source_dir / "beta.txt").write_text("B", encoding="utf-8")
        (source_dir / "alpha.dep").write_text("ignored", encoding="utf-8")

        documents, issues = batch_import_documents_from_folder(
            source_dir,
            format_key="txt",
            existing_names={"beta"},
        )

        self.assertEqual(documents, [Document(name="alpha", text="A", braille=None)])
        self.assertEqual(
            issues,
            [BatchIssue(path=source_dir / "beta.txt", reason='Document "beta" already exists.')],
        )

    def test_batch_import_documents_from_folder_reports_invalid_dep(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "bad.dep").write_text("not-a-zip", encoding="utf-8")

        documents, issues = batch_import_documents_from_folder(source_dir, format_key="dep", existing_names=set())

        self.assertEqual(documents, [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].path, source_dir / "bad.dep")

    def test_batch_export_documents_to_folder_reports_existing_conflicts(self) -> None:
        export_dir = Path(self._tmpdir.name) / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "lesson1.brl").write_text("old", encoding="utf-8")

        conflicts = batch_export_documents_to_folder(
            export_dir,
            [
                Document(name="lesson1", text="a", braille="⠁"),
                Document(name="lesson2", text="b", braille="⠃"),
            ],
            format_key="brl",
            overwrite=False,
        )

        self.assertEqual(conflicts, [export_dir / "lesson1.brl"])
        self.assertFalse((export_dir / "lesson2.brl").exists())

    def test_batch_export_documents_to_folder_writes_all_documents_when_overwrite_allowed(self) -> None:
        export_dir = Path(self._tmpdir.name) / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "lesson1.brl").write_text("old", encoding="utf-8")

        conflicts = batch_export_documents_to_folder(
            export_dir,
            [
                Document(name="lesson1", text="a", braille="⠁"),
                Document(name="lesson2", text="b", braille="⠃"),
            ],
            format_key="brl",
            overwrite=True,
        )

        self.assertEqual(conflicts, [])
        self.assertEqual((export_dir / "lesson1.brl").read_text(encoding="utf-8"), "⠁")
        self.assertEqual((export_dir / "lesson2.brl").read_text(encoding="utf-8"), "⠃")

    def test_prepare_document_for_save_auto_converts_pending_braille(self) -> None:
        document = Document(name="lesson1", text="old", braille=None)

        prepared, auto_error = prepare_document_for_save(
            document,
            text="new text",
            braille="",
            auto_convert=lambda text: f"converted:{text}",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="converted:new text"))
        self.assertIsNone(auto_error)

    def test_prepare_document_for_save_stores_empty_string_when_auto_convert_fails(self) -> None:
        document = Document(name="lesson1", text="old", braille=None)

        prepared, auto_error = prepare_document_for_save(
            document,
            text="new text",
            braille="",
            auto_convert=lambda _text: (_ for _ in ()).throw(ValueError("boom")),
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille=""))
        self.assertIsInstance(auto_error, ValueError)

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
