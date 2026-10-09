import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from conversion.text.dictionary_rules import LoadedDictionaryRules
from dictionaries.entries import (
	DictionaryEntry,
	PreservedDictionaryRow,
	load_dictionary_entries,
	load_dictionary_rows,
	normalize_entry_type,
	save_dictionary_entries,
	validate_dictionary_entry,
)
from text.zhuyin import normalize_zhuyin_sequence

BOPOMOFO_DATA = Path(__file__).resolve().parents[1] / "data" / "Bopomofo2Braille.csv"

# dict_badbopo.csv of the Windows verification (F-W11): one Braille row and two Bopomofo
# rows whose sequences do not parse; UTF-8 without a BOM, CRLF.
DICT_BADBOPO = (
	"text,braille,type\r\n"
	"\u81fa\u5317,\u281e\u283a,Braille\r\n"
	"\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
	"\u6578\u5b78,\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca,Bopomofo\r\n"
).encode("utf-8")
DICT_BADBOPO_SHA256 = "c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4"

# Every kind of row the editor does not show, between two entries (F-4): a blank and a
# whitespace-only source text, an invalid Bopomofo sequence with spaces around it, a
# first-tone sequence whose tone space the editor would strip, a row with a missing
# field, and a quoted row whose fields hold a comma, quotes and a line break.
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	",\u2803,General\r\n"
	"  ,\u2803,General\r\n"
	"\u809a\u5b50, \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n"
	"\u5abd,\u3107\u311a ,Bopomofo\r\n"
	",\u2803\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")
MIXED_ROWS = [
	DictionaryEntry("Alpha", "\u2801", "General"),
	PreservedDictionaryRow("", "\u2803", "General"),
	PreservedDictionaryRow("  ", "\u2803", "General"),
	PreservedDictionaryRow("\u809a\u5b50", " \u3109\u3128\u02cb|\u3117\u02d9 ", "Bopomofo"),
	PreservedDictionaryRow("\u5abd", "\u3107\u311a ", "Bopomofo"),
	PreservedDictionaryRow("", "\u2803", ""),
	PreservedDictionaryRow('q,"x"', "a\r\nb", "Bopomofo"),
	DictionaryEntry("Beta", "\u2803", "General"),
]
# What saving MIXED_ROWS writes: the same bytes, except that the row with a missing
# field gets its empty third field.
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))


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

	def test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)

			rows = load_dictionary_rows(path)

		self.assertEqual(rows, MIXED_ROWS)

	def test_save_writes_preserved_rows_unchanged_at_their_place(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"

			save_dictionary_entries(path, MIXED_ROWS)

			data = path.read_bytes()

		self.assertEqual(data, MIXED_CSV_SAVED)

	def test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical(self) -> None:
		# F-W11: the editor's OK used to delete the two Bopomofo rows (4 lines -> 2).
		self.assertEqual(hashlib.sha256(DICT_BADBOPO).hexdigest(), DICT_BADBOPO_SHA256)
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "dict_badbopo.csv"
			path.write_bytes(DICT_BADBOPO)

			save_dictionary_entries(path, load_dictionary_rows(path))

			data = path.read_bytes()

		self.assertEqual(data, DICT_BADBOPO)

	def test_round_trip_normalizes_only_the_bom_line_ends_and_quoting(self) -> None:
		# An invalid one-symbol sequence, quoted, with LF line ends and a BOM.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(b"\xef\xbb\xbf" + 'text,braille,type\n"\u809a\u5b50","\u3109",Bopomofo\n'.encode("utf-8"))

			save_dictionary_entries(path, load_dictionary_rows(path))

			data = path.read_bytes()

		self.assertEqual(data, "text,braille,type\r\n\u809a\u5b50,\u3109,Bopomofo\r\n".encode("utf-8"))

	def test_round_trip_keeps_the_conversion_rules(self) -> None:
		# Conversion also uses the rows the editor hides (an invalid Bopomofo sequence
		# falls back to its raw symbols), so a load/save round trip must not change them.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)
			before = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

			save_dictionary_entries(path, load_dictionary_rows(path))

			after = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

		self.assertEqual(after, before)
		self.assertIn("\u809a\u5b50", [source for source, _replacement in before.replacement_rules])

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
		entry = DictionaryEntry("Alpha", "\u2801", "General")

		self.assertNotEqual(preserved, entry)
		self.assertNotEqual(entry, preserved)
		self.assertEqual([entry].count(preserved), 0)


if __name__ == "__main__":
	unittest.main()
