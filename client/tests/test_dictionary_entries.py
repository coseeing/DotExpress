import csv
import tempfile
import unittest
from pathlib import Path

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

	def test_load_ignores_a_utf8_bom(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")

			entries = load_dictionary_entries(path)

		self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])

	def test_save_load_roundtrip(self) -> None:
		entries = [
			DictionaryEntry("Alpha", "\u2801", "General"),
			DictionaryEntry("Zhuyin", "ㄉㄨˋ", "Bopomofo"),
			DictionaryEntry("Braille", "\u2803\u2811", "Braille"),
		]

		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			save_dictionary_entries(path, entries)
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

	def test_save_writes_utf8_without_a_bom(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			save_dictionary_entries(path, [DictionaryEntry("Alpha", "\u2801", "General")])

			data = path.read_bytes()

		self.assertEqual(data, b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")

	def test_save_failure_leaves_the_existing_file_unchanged(self) -> None:
		# Regression record of the P2-2 Q3 data loss (fixed by F-2): the file used to be
		# truncated before the failing row was written.
		original = b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\nBeta,\xe2\xa0\x83,General\r\n"
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(original)

			with self.assertRaises(UnicodeEncodeError):
				save_dictionary_entries(
					path,
					[DictionaryEntry("Alpha", "\u2801", "General"), DictionaryEntry("\ud800", "\u2803", "General")],
				)

			data = path.read_bytes()
			listing = sorted(child.name for child in Path(temp_dir).iterdir())

		self.assertEqual(data, original)
		self.assertEqual(listing, ["sample.csv"])


if __name__ == "__main__":
	unittest.main()
