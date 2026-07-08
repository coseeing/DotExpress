import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from documents.workspace import (
    BatchIssue,
    Document,
    batch_import_documents,
    batch_export_documents_to_folder,
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

    def test_normalize_document_name_accepts_unicode_trims_and_allows_default(self) -> None:
        self.assertEqual(normalize_document_name("  default中文12"), "default中文12")
        self.assertEqual(normalize_document_name(" default"), "default")
        self.assertEqual(normalize_document_name("1.1"), "1.1")
        self.assertEqual(normalize_document_name("name\u3000"), "name")

    def test_normalize_document_name_rejects_windows_invalid_names(self) -> None:
        invalid_values = [
            "",
            " ",
            ".",
            "..",
            " name ",
            "a.",
            "name ",
            "name\t",
            "a. ",
            "a<b",
            "a>b",
            "a:b",
            'a"b',
            "a/b",
            r"a\\b",
            "a|b",
            "a?b",
            "a*b",
            f"a{chr(1)}b",
            "CON",
            "prn",
            "AUX",
            "nul",
            "COM1",
            "com9",
            "LPT1",
            "lpt9",
            "a" * 33,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_document_name(value)

    def test_normalize_document_name_accepts_32_characters(self) -> None:
        self.assertEqual(normalize_document_name("a" * 32), "a" * 32)

    def test_save_and_load_document_package_roundtrip(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_and_load_document_package_preserves_pending_braille_state(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_and_load_document_package_roundtrip_with_dotted_name(self) -> None:
        document = Document(name="1.1", text="source", braille="braille")
        package_path = self.workspace_dir / "1.1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)

        import zipfile

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["1.1.brl", "1.1.txt"])

        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_document_package_can_skip_pending_metadata_for_exports(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document, include_pending_metadata=False)

        import zipfile

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["lesson1.brl", "lesson1.txt"])

    def test_load_document_package_rejects_mismatched_internal_names(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
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

    def test_load_text_document_handles_dotted_document_name(self) -> None:
        source_path = self.workspace_dir / "1.1.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="1.1", text="hello", braille=None))

    def test_load_text_document_accepts_32_character_stem(self) -> None:
        source_path = self.workspace_dir / f"{'a' * 32}.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="a" * 32, text="hello", braille=None))

    def test_export_document_brl_writes_plain_braille_text(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        output_path = self.workspace_dir / "lesson1.brl"
        export_document_brl(output_path, document)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "⠇⠑⠎⠎")

    def test_batch_import_documents_imports_txt_only_and_reports_duplicates(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "alpha.txt").write_text("A", encoding="utf-8")
        (source_dir / "beta.txt").write_text("B", encoding="utf-8")
        (source_dir / "alpha.dep").write_text("ignored", encoding="utf-8")

        documents, issues = batch_import_documents(
            [source_dir / "alpha.txt", source_dir / "beta.txt", source_dir / "alpha.dep"],
            format_key="txt",
            existing_names={"beta"},
        )

        self.assertEqual(documents, [Document(name="alpha", text="A", braille=None)])
        self.assertEqual(
            issues,
            [
                BatchIssue(path=source_dir / "alpha.dep", reason="Text document must use the .txt extension."),
                BatchIssue(path=source_dir / "beta.txt", reason='Document "beta" already exists.'),
            ],
        )

    def test_batch_import_documents_dispatches_semantic_importer(self) -> None:
        source = Path(self._tmpdir.name) / "lesson.docx"
        loader = Mock(return_value=Document("lesson", "# Heading\n", None))
        with patch.dict("documents.workspace.IMPORT_LOADERS", {"docx": loader}, clear=False):
            documents, issues = batch_import_documents([source], format_key="docx", existing_names=set())

        self.assertEqual(documents, [Document("lesson", "# Heading\n", None)])
        self.assertEqual(issues, [])
        loader.assert_called_once_with(source)

    def test_batch_import_documents_all_detects_each_supported_extension(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            source_dir / "alpha.txt",
            source_dir / "beta.dep",
            source_dir / "gamma.pdf",
            source_dir / "delta.docx",
            source_dir / "epsilon.epub",
        ]
        loaders = {
            "txt": Mock(return_value=Document("alpha", "A", None)),
            "dep": Mock(return_value=Document("beta", "B", "⠃")),
            "pdf": Mock(return_value=Document("gamma", "G", None)),
            "docx": Mock(return_value=Document("delta", "D", None)),
            "epub": Mock(return_value=Document("epsilon", "E", None)),
        }

        with patch.dict("documents.workspace.IMPORT_LOADERS", loaders, clear=False):
            documents, issues = batch_import_documents(paths, format_key="all", existing_names=set())

        self.assertEqual(
            documents,
            [
                Document("alpha", "A", None),
                Document("beta", "B", "⠃"),
                Document("delta", "D", None),
                Document("epsilon", "E", None),
                Document("gamma", "G", None),
            ],
        )
        self.assertEqual(issues, [])
        for path in paths:
            loaders[path.suffix.lstrip(".")].assert_called_once_with(path)

    def test_batch_import_documents_rejects_unknown_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported import format"):
            batch_import_documents([], format_key="rtf", existing_names=set())

    def test_batch_import_documents_reports_invalid_dep(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "bad.dep").write_text("not-a-zip", encoding="utf-8")

        documents, issues = batch_import_documents([source_dir / "bad.dep"], format_key="dep", existing_names=set())

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

    def test_batch_export_documents_to_folder_writes_dep_packages_without_pending_metadata(self) -> None:
        export_dir = Path(self._tmpdir.name) / "export"
        export_dir.mkdir(parents=True, exist_ok=True)

        conflicts = batch_export_documents_to_folder(
            export_dir,
            [Document(name="lesson1", text="a", braille=None)],
            format_key="dep",
            overwrite=True,
        )

        self.assertEqual(conflicts, [])

        import zipfile

        with zipfile.ZipFile(export_dir / "lesson1.dep", "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["lesson1.brl", "lesson1.txt"])

    def test_prepare_document_for_save_preserves_pending_braille_without_auto_conversion(self) -> None:
        document = Document(name="lesson1", text="old", braille=None)

        prepared, auto_error = prepare_document_for_save(
            document,
            text="new text",
            braille="⠞⠑⠎⠞",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille=None))
        self.assertIsNone(auto_error)

    def test_prepare_document_for_save_keeps_existing_braille_without_auto_conversion(self) -> None:
        document = Document(name="lesson1", text="old", braille="⠃⠗⠇")

        prepared, auto_error = prepare_document_for_save(
            document,
            text="new text",
            braille="⠃⠗⠇",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="⠃⠗⠇"))
        self.assertIsNone(auto_error)

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(self.workspace_dir / "Beta.dep", Document(name="Beta", text="b", braille="1"))
        save_document_package(self.workspace_dir / "alpha.dep", Document(name="alpha", text="a", braille="2"))
        save_document_package(self.workspace_dir / "bad.dep", Document(name="other", text="x", braille="3"))
        documents, invalid_paths = load_workspace_documents(self.workspace_dir)
        self.assertEqual([document.name for document in documents], ["alpha", "Beta"])
        self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])

if __name__ == "__main__":
    unittest.main()
