import csv
import tempfile
import unittest
from pathlib import Path

from shared import name_validation
from dictionaries.entries import DictionaryEntry, load_dictionary_entries
from dictionaries.manager import (
    DEFAULT_DICTIONARY_NAME,
    DEFAULT_HEADER,
    create_dictionary,
    dictionary_path_for_name,
    ensure_default_dictionary,
    export_dictionary,
    import_dictionary,
    list_dictionary_names,
    normalize_dictionary_name,
    rename_dictionary,
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
        self.assertEqual(normalize_dictionary_name("  中文12"), "中文12")
        self.assertEqual(normalize_dictionary_name("1.1"), "1.1")
        self.assertEqual(normalize_dictionary_name("name\u3000"), "name")

    def test_normalize_dictionary_name_rejects_windows_invalid_names(self) -> None:
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
            DEFAULT_DICTIONARY_NAME,
            "a" * 33,
        ]

        for value in invalid_values:
            with self.assertRaises(ValueError):
                normalize_dictionary_name(value)

    def test_normalize_dictionary_name_accepts_32_characters(self) -> None:
        self.assertEqual(normalize_dictionary_name("a" * 32), "a" * 32)

    def test_normalize_dictionary_name_raises_typed_errors(self) -> None:
        cases = (
            ("", "empty"),
            ("CON", "invalid"),
            ("name.", "invalid"),
            ("a" * 33, "too_long"),
            (" Default", "reserved"),
            ("a\ud800", "invalid"),
        )
        for value, code in cases:
            with self.subTest(value=value):
                with self.assertRaises(name_validation.NameValidationError) as caught:
                    normalize_dictionary_name(value)
                self.assertEqual(caught.exception.code, code)

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

    def test_import_dictionary_allows_periods_in_dictionary_name(self) -> None:
        source_path = Path(self._tmpdir.name) / "source.csv"
        with source_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(DEFAULT_HEADER)
            writer.writerow(["term", "braille", "General"])

        imported_path = import_dictionary(self.dictionary_dir, source_path, "1.1")

        self.assertEqual(imported_path, self.dictionary_dir / "1.1.csv")
        self.assertEqual(imported_path.read_text(encoding="utf-8"), source_path.read_text(encoding="utf-8"))

    def test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes(self) -> None:
        source_path = Path(self._tmpdir.name) / "excel.csv"
        data = b"\xef\xbb\xbftext,braille,type\r\nterm,\xe2\xa0\x81,General\r\n"
        source_path.write_bytes(data)

        imported_path = import_dictionary(self.dictionary_dir, source_path, "excel")

        self.assertEqual(imported_path, self.dictionary_dir / "excel.csv")
        self.assertEqual(imported_path.read_bytes(), data)
        self.assertEqual(load_dictionary_entries(imported_path), [DictionaryEntry("term", "\u2801", "General")])

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
