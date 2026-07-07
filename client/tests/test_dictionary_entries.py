import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dictionaries.entries import (
	DictionaryEntry,
	load_dictionary_entries,
	normalize_entry_type,
	save_dictionary_entries,
	validate_dictionary_entry,
)


class NormalizeEntryTypeTest(unittest.TestCase):
	def test_unknown_entry_type_falls_back_to_general(self) -> None:
		self.assertEqual(normalize_entry_type("Unknown"), "General")


class DictionaryEntryValidationTest(unittest.TestCase):
	def test_empty_source_text_is_rejected(self) -> None:
		with self.assertRaises(ValueError):
			validate_dictionary_entry(DictionaryEntry("", "\u2801", "General"))

	def test_invalid_unicode_braille_is_rejected(self) -> None:
		with self.assertRaises(ValueError):
			validate_dictionary_entry(DictionaryEntry("Alpha", "abc", "Braille"))

	def test_valid_unicode_braille_is_accepted(self) -> None:
		validate_dictionary_entry(DictionaryEntry("Alpha", "\u2801\u2803", "Braille"))


class DictionaryEntryStorageTest(unittest.TestCase):
	def test_load_filters_empty_and_invalid_bopomofo_rows(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			with path.open("w", newline="", encoding="utf-8") as stream:
				writer = csv.writer(stream)
				writer.writerow(["text", "braille", "type"])
				writer.writerow(["Alpha", "\u2801", "General"])
				writer.writerow(["", "\u2803", "General"])
				writer.writerow(["Zhuyin", "invalid", "Bopomofo"])

			with patch("dictionaries.entries.normalize_zhuyin_sequence", side_effect=ValueError):
				entries = load_dictionary_entries(path)

		self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])

	def test_load_preserves_invalid_braille_rows(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			with path.open("w", newline="", encoding="utf-8") as stream:
				writer = csv.writer(stream)
				writer.writerow(["text", "braille", "type"])
				writer.writerow(["Braille", "abc", "Braille"])

			entries = load_dictionary_entries(path)

		self.assertEqual(entries, [DictionaryEntry("Braille", "abc", "Braille")])

	def test_save_load_roundtrip(self) -> None:
		entries = [
			DictionaryEntry("Alpha", "\u2801", "General"),
			DictionaryEntry("Zhuyin", "\u3105\u02c9", "Bopomofo"),
			DictionaryEntry("Braille", "\u2803\u2811", "Braille"),
		]

		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			save_dictionary_entries(path, entries)
			with patch("dictionaries.entries.normalize_zhuyin_sequence", return_value="\u3105\u02c9"):
				loaded_entries = load_dictionary_entries(path)

		self.assertEqual(loaded_entries, entries)

	def test_save_preserves_entry_type_value(self) -> None:
		entries = [DictionaryEntry("Alpha", "\u2801", "UnexpectedType")]

		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			save_dictionary_entries(path, entries)
			with path.open("r", newline="", encoding="utf-8") as stream:
				rows = list(csv.DictReader(stream))

		self.assertEqual(
			rows,
			[{"text": "Alpha", "braille": "\u2801", "type": "UnexpectedType"}],
		)


if __name__ == "__main__":
	unittest.main()
