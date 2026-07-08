import csv
import tempfile
import unittest
from pathlib import Path


from conversion.text.char_maps import translate__mapping_char


class TranslationCharMapsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _write_mapping(self, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> Path:
        dictionary_path = self.directory / "mapping.csv"
        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames or ["source", "target"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return dictionary_path

    def test_translate_mapping_char_maps_single_char_rows(self) -> None:
        dictionary_path = self._write_mapping(
            [
                {"source": "a", "target": "x"},
                {"source": "b", "target": "y"},
            ]
        )

        self.assertEqual(
            translate__mapping_char(
                "abc",
                dictionary_path=dictionary_path,
                from_field="source",
                to_field="target",
            ),
            "xyc",
        )

    def test_translate_mapping_char_ignores_multi_char_sources(self) -> None:
        dictionary_path = self._write_mapping(
            [
                {"source": "ab", "target": "x"},
                {"source": "c", "target": "z"},
            ]
        )

        self.assertEqual(
            translate__mapping_char(
                "abc",
                dictionary_path=dictionary_path,
                from_field="source",
                to_field="target",
            ),
            "abz",
        )

    def test_translate_mapping_char_deletes_char_when_target_is_empty(self) -> None:
        dictionary_path = self._write_mapping([{"source": "b", "target": ""}])

        self.assertEqual(
            translate__mapping_char(
                "abc",
                dictionary_path=dictionary_path,
                from_field="source",
                to_field="target",
            ),
            "ac",
        )

    def test_translate_mapping_char_requires_header_row(self) -> None:
        dictionary_path = self.directory / "mapping.csv"
        dictionary_path.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "header row"):
            translate__mapping_char(
                "abc",
                dictionary_path=dictionary_path,
                from_field="source",
                to_field="target",
            )

    def test_translate_mapping_char_requires_requested_columns(self) -> None:
        dictionary_path = self._write_mapping(
            [{"source": "a", "other": "x"}],
            fieldnames=["source", "other"],
        )

        with self.assertRaisesRegex(ValueError, "source, target"):
            translate__mapping_char(
                "abc",
                dictionary_path=dictionary_path,
                from_field="source",
                to_field="target",
            )


if __name__ == "__main__":
    unittest.main()
