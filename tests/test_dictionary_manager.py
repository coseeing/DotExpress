import csv
import tempfile
import unittest
from pathlib import Path

from dictionary_manager import (
    DEFAULT_DICTIONARY_NAME,
    DEFAULT_HEADER,
    choose_selection_after_delete,
    create_dictionary,
    dictionary_path_for_name,
    ensure_default_dictionary,
    export_dictionary,
    import_dictionary,
    list_dictionary_names,
    normalize_dictionary_name,
    rename_dictionary,
    resolve_selected_dictionary,
)


class DictionaryManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dictionary_dir = Path(self._tmpdir.name) / "dictionary"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_ensure_default_dictionary_creates_folder_and_header(self) -> None:
        default_path = ensure_default_dictionary(self.dictionary_dir)

        self.assertEqual(default_path, self.dictionary_dir / f"{DEFAULT_DICTIONARY_NAME}.csv")
        self.assertTrue(default_path.exists())
        with default_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            self.assertEqual(next(reader), DEFAULT_HEADER)
            self.assertEqual(list(reader), [])

    def test_list_dictionary_names_uses_case_insensitive_sorting(self) -> None:
        self.dictionary_dir.mkdir()
        for name in ["Beta", "alpha", "中"]:
            create_dictionary(self.dictionary_dir, name)

        self.assertEqual(list_dictionary_names(self.dictionary_dir), ["alpha", "Beta", "中"])

    def test_normalize_dictionary_name_accepts_unicode_and_trims_whitespace(self) -> None:
        self.assertEqual(normalize_dictionary_name("  中文12  "), "中文12")

    def test_normalize_dictionary_name_rejects_reserved_or_invalid_names(self) -> None:
        invalid_values = [
            "",
            " ",
            ".",
            "a/b",
            r"a\\b",
            "this-name-is-way-too-long",
            DEFAULT_DICTIONARY_NAME,
        ]

        for value in invalid_values:
            with self.assertRaises(ValueError):
                normalize_dictionary_name(value)

    def test_choose_selection_after_delete_prefers_previous_item(self) -> None:
        names = ["alpha", "math", "zoo"]

        self.assertEqual(choose_selection_after_delete(names, "math"), "alpha")

    def test_choose_selection_after_delete_uses_next_when_first_removed(self) -> None:
        names = ["alpha", "math", "zoo"]

        self.assertEqual(choose_selection_after_delete(names, "alpha"), "math")

    def test_resolve_selected_dictionary_falls_back_to_default_for_missing_saved_value(self) -> None:
        names = ["default", "math"]

        self.assertEqual(resolve_selected_dictionary(names, "missing"), DEFAULT_DICTIONARY_NAME)
        self.assertEqual(resolve_selected_dictionary(names, "math"), "math")

    def test_export_dictionary_copies_selected_dictionary_to_destination(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["term", "braille", "General"])

        export_path = Path(self._tmpdir.name) / "export.csv"

        result = export_dictionary(self.dictionary_dir, "math", export_path)

        self.assertEqual(result, export_path)
        self.assertEqual(export_path.read_text(encoding="utf-8"), source_path.read_text(encoding="utf-8"))

    def test_import_dictionary_copies_valid_csv_into_managed_dictionary(self) -> None:
        source_path = Path(self._tmpdir.name) / "source.csv"
        with source_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(DEFAULT_HEADER)
            writer.writerow(["term", "braille", "General"])

        imported_path = import_dictionary(self.dictionary_dir, source_path, "science")

        self.assertEqual(imported_path, self.dictionary_dir / "science.csv")
        self.assertEqual(imported_path.read_text(encoding="utf-8"), source_path.read_text(encoding="utf-8"))

    def test_import_dictionary_rejects_invalid_header(self) -> None:
        source_path = Path(self._tmpdir.name) / "invalid.csv"
        with source_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["wrong", "header"])

        with self.assertRaises(ValueError):
            import_dictionary(self.dictionary_dir, source_path, "science")

    def test_rename_dictionary_renames_file_and_preserves_contents(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["term", "braille", "General"])

        renamed_path = rename_dictionary(self.dictionary_dir, "math", "science")

        self.assertEqual(renamed_path, dictionary_path_for_name("science", self.dictionary_dir))
        self.assertFalse(source_path.exists())
        self.assertTrue(renamed_path.exists())
        self.assertIn("term,braille,General", renamed_path.read_text(encoding="utf-8"))

    def test_rename_dictionary_rejects_existing_destination(self) -> None:
        create_dictionary(self.dictionary_dir, "math")
        create_dictionary(self.dictionary_dir, "science")

        with self.assertRaises(FileExistsError):
            rename_dictionary(self.dictionary_dir, "math", "science")


if __name__ == "__main__":
    unittest.main()
