import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from conversion.text.dictionary_rules import LoadedDictionaryRules
from dictionaries import entries as entries_module
from dictionaries.entries import (
	DictionaryEntry,
	PreservedDictionaryRow,
	load_dictionary_entries,
	load_dictionary_rows,
	normalize_entry_type,
	save_dictionary_entries,
	validate_dictionary_entry,
)
from tests.unreadable_dictionary_files import FIELD_LIMIT, LATE_BIG5
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
# whitespace-only source text, an invalid Bopomofo sequence with spaces around it, a row
# with a missing field, and a quoted row whose fields hold a comma, quotes and a line
# break. The first-tone sequence was hidden too, because the editor stripped its tone
# space; since F-11 (D14) it is an entry that keeps it.
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
	DictionaryEntry("\u5abd", "\u3107\u311a ", "Bopomofo"),
	PreservedDictionaryRow("", "\u2803", ""),
	PreservedDictionaryRow('q,"x"', "a\r\nb", "Bopomofo"),
	DictionaryEntry("Beta", "\u2803", "General"),
]
# What saving MIXED_ROWS writes: the same bytes, except that the row with a missing
# field gets its empty third field.
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))
BOM = b"\xef\xbb\xbf"
# A dictionary kept in Excel (F-11 D5): a BOM, a column of notes between the required
# ones, CRLF. The writer keeps all three.
EXTRA_CSV = BOM + (
	"text,note,braille,type\r\n"
	"Alpha,first,\u2801,General\r\n"
	"Beta,,\u2803,General\r\n"
).encode("utf-8")
# Records the loader reads differently from a plain table (F-11 D6, probe 5): a blank
# line, a quoted field over two lines, a short row, an overflow field, a whitespace-only
# line.
ODD_RECORDS_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	"\r\n"
	",\u2803,General\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"short\r\n"
	"Beta,\u2803,General,overflow\r\n"
	" \r\n"
	"\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
).encode("utf-8")
# Records of empty fields around an entry and a blank line: csv.DictReader reads each as a
# row (F-11 D6; review M-2 b).
EMPTY_FIELDS_CSV = b"text,braille,type\r\n,,\r\nAlpha,x,General\r\n\r\n,,,\r\n"
# A column named twice: csv.DictReader reads the last position, so the second row has no
# source text.
TWICE_CSV = "text,braille,type,text\r\nAlpha,\u2801,General,Alpha2\r\nBeta,\u2803,General\r\n".encode("utf-8")


def _dictreader_rows(path: Path) -> list:
	"""The loader before F-11 (csv.DictReader), verbatim: the oracle of the parity tests."""
	if not path.exists():
		return []

	rows = []
	with path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if entries_module._is_editable(entry):
				if entry.entry_type == "Bopomofo":
					# F-11 (D14): a final first-tone syllable keeps its tone space.
					entry.braille = entries_module.canonical_bopomofo(entry.braille)
				rows.append(entry)
			else:
				rows.append(
					PreservedDictionaryRow(
						text=row.get("text") or "",
						braille=row.get("braille") or "",
						entry_type=row.get("type") or "",
					)
				)
	return rows


def _values(rows) -> list:
	return [(type(row).__name__, row.text, row.braille, row.entry_type) for row in rows]


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

	def test_bopomofo_with_a_final_first_tone_is_accepted_without_its_tone_space(self) -> None:
		# F-11 (D14): the entry dialog strips the space; the sequence is valid with it.
		rejected = []
		for braille in ("\u3107\u311a", "\u3107\u311a ", "\u3113\u3128\u3125 \u3112\u3127\u3123", "\u3107\u311a\u02c9", "\u3109\u3128\u02cb|\u3117\u02d9"):
			try:
				validate_dictionary_entry(DictionaryEntry("\u5abd", braille, "Bopomofo"))
			except ValueError as error:
				rejected.append((braille, str(error)))

		message = "\u8acb\u8f38\u5165\u6709\u6548\u7684\u6ce8\u97f3\u5e8f\u5217\u3002"
		self.assertEqual(rejected, [("\u3107\u311a\u02c9", message), ("\u3109\u3128\u02cb|\u3117\u02d9", message)])


class CanonicalBopomofoTest(unittest.TestCase):
	"""The Bopomofo sequence the editor shows and saves (F-11 D14, spec O1 (b))."""

	def test_a_final_first_tone_syllable_keeps_its_tone_space(self) -> None:
		cases = (
			("\u3107\u311a", "\u3107\u311a "),
			("\u3107\u311a ", "\u3107\u311a "),
			("  \u3107\u311a  ", "\u3107\u311a "),
			("\u3107\u311a\u3000", "\u3107\u311a "),
			("\u3113\u3128\u3125 \u3112\u3127\u3123", "\u3113\u3128\u3125 \u3112\u3127\u3123 "),
			("\u3109\u3128\u02cb\u3117\u02d9", "\u3109\u3128\u02cb\u3117\u02d9"),
			(" \u3109\u3128\u02cb\u3117\u02d9 ", "\u3109\u3128\u02cb\u3117\u02d9"),
			("", ""),
			("\u3109\u3128\u02cb|\u3117\u02d9", None),
			("\u3107\u311a\u02c9", None),
			("\u3107\u311a  \u3107\u311a", None),
			("invalid", None),
		)
		for braille, expected in cases:
			with self.subTest(braille=braille):
				self.assertEqual(entries_module.canonical_bopomofo(braille), expected)

	def test_loader_shows_a_row_whose_last_syllable_is_first_tone(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "tone1.csv"
			path.write_bytes("text,braille,type\r\n\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n\u5abd, \u3107\u311a,Bopomofo\r\n".encode("utf-8"))

			rows = load_dictionary_rows(path)
			loaded = entries_module.load_dictionary_file(path)
			save_dictionary_entries(path, loaded.rows, loaded.layout)
			saved = path.read_bytes()

		self.assertEqual(rows, [DictionaryEntry("\u4e2d\u5fc3", "\u3113\u3128\u3125 \u3112\u3127\u3123 ", "Bopomofo"), DictionaryEntry("\u5abd", "\u3107\u311a ", "Bopomofo")])
		self.assertEqual(saved, "text,braille,type\r\n\u4e2d\u5fc3,\u3113\u3128\u3125 \u3112\u3127\u3123 ,Bopomofo\r\n\u5abd,\u3107\u311a ,Bopomofo\r\n".encode("utf-8"))


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
		# A load/save round trip must not change the conversion rules. Since F-11 (D13)
		# conversion ignores the rows the editor hides, as the hidden invalid sequence.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)
			before = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

			save_dictionary_entries(path, load_dictionary_rows(path))

			after = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

		self.assertEqual(after, before)
		self.assertEqual([source for source, _replacement in before.replacement_rules], ["Alpha", "\u5abd", "Beta"])

	def test_rows_carry_their_record_and_entries_still_compare_by_value(self) -> None:
		# F-11 (D6): the record's fields and the start line are kept, outside equality.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)

			rows = load_dictionary_rows(path)

		self.assertEqual(rows, MIXED_ROWS)
		self.assertEqual(rows[0].fields, ("Alpha", "\u2801", "General"))
		self.assertEqual(rows[5].fields, ("", "\u2803"))
		self.assertEqual(rows[6].fields, ('q,"x"', "a\r\nb", "Bopomofo"))
		self.assertEqual([row.line for row in rows if isinstance(row, PreservedDictionaryRow)], [3, 4, 5, 7, 8])
		self.assertEqual(DictionaryEntry("Alpha", "\u2801", "General", ("x",)), DictionaryEntry("Alpha", "\u2801", "General"))
		self.assertNotIn("fields", repr(rows[0]))

	def test_a_preserved_row_tells_why_the_editor_hides_it(self) -> None:
		# F-11 (D1): the box on OK gives the reason of each row.
		cases = (
			(PreservedDictionaryRow("", "\u2803", "General"), "no_source_text"),
			(PreservedDictionaryRow(" \u3000", "\u2803", "General"), "no_source_text"),
			(PreservedDictionaryRow("\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9", "Bopomofo"), "invalid_bopomofo"),
		)
		for row, reason in cases:
			with self.subTest(row=row):
				self.assertEqual(row.reason, reason)

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
		entry = DictionaryEntry("Alpha", "\u2801", "General")

		self.assertNotEqual(preserved, entry)
		self.assertNotEqual(entry, preserved)
		self.assertEqual([entry].count(preserved), 0)


class DictionaryLayoutTest(unittest.TestCase):
	"""The loader records what the writer keeps of the file (F-11 D5, D6)."""

	def load(self, data: bytes | None):
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			if data is not None:
				path.write_bytes(data)
			return entries_module.load_dictionary_file(path)

	def test_layout_records_the_bom_and_the_header_as_read(self) -> None:
		cases = (
			("no BOM", b"text,braille,type\r\nAlpha,x,General\r\n", False, ("text", "braille", "type")),
			("BOM and an extra column", EXTRA_CSV, True, ("text", "note", "braille", "type")),
			("a column named twice", TWICE_CSV, False, ("text", "braille", "type", "text")),
			("no type column", b"text,braille\r\nAlpha,x\r\n", False, ("text", "braille")),
			("an empty file", b"", False, ()),
			("only a BOM", BOM, True, ()),
			("a blank first line", b"\r\ntext,braille,type\r\n", False, ()),
		)
		for name, data, has_bom, header in cases:
			with self.subTest(name):
				self.assertEqual(self.load(data).layout, entries_module.DictionaryLayout(has_bom, header))

	def test_a_missing_file_has_no_rows_and_the_default_layout(self) -> None:
		loaded = self.load(None)

		self.assertEqual(loaded.rows, ())
		self.assertEqual(loaded.layout, entries_module.DictionaryLayout(False, ()))

	def test_hidden_rows_record_the_line_on_which_their_record_starts(self) -> None:
		# The header is line 1; a blank line is skipped but counted; a quoted field over two
		# lines makes the next record start two lines later (probe 5).
		rows = self.load(ODD_RECORDS_CSV).rows

		self.assertEqual(
			[(row.line, row.text) for row in rows if isinstance(row, PreservedDictionaryRow)],
			[(4, ""), (5, 'q,"x"'), (9, " "), (10, "\u809a\u5b50")],
		)

	def test_a_record_of_empty_fields_is_a_hidden_row_on_its_line(self) -> None:
		# csv.DictReader gives ",," a row whose fields are "" (review M-2 b); only a blank line is skipped.
		rows = self.load(EMPTY_FIELDS_CSV).rows

		self.assertEqual(len(rows), 3)
		self.assertEqual(
			[(row.line, row.fields) for row in rows if isinstance(row, PreservedDictionaryRow)],
			[(2, ("", "", "")), (5, ("", "", "", ""))],
		)

	def test_rows_keep_every_field_of_their_record(self) -> None:
		rows = self.load(ODD_RECORDS_CSV).rows

		self.assertEqual(
			[row.fields for row in rows],
			[
				("Alpha", "\u2801", "General"),
				("", "\u2803", "General"),
				('q,"x"', "a\r\nb", "Bopomofo"),
				("short",),
				("Beta", "\u2803", "General", "overflow"),
				(" ",),
				("\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9", "Bopomofo"),
			],
		)

	def test_values_and_classes_equal_those_of_dictreader(self) -> None:
		# A column named twice takes the value of its last position, a missing field is "",
		# blank records are skipped, the first record is the header even when it is blank.
		corpora = {
			"MIXED_CSV": MIXED_CSV,
			"DICT_BADBOPO": DICT_BADBOPO,
			"EXTRA_CSV": EXTRA_CSV,
			"ODD_RECORDS_CSV": ODD_RECORDS_CSV,
			"TWICE_CSV": TWICE_CSV,
			"blank first line": b"\r\ntext,braille,type\r\nAlpha,x,General\r\n",
			"LF and quotes": 'text,braille,type\n"Alpha",\u2801,General\nZhuyin,invalid,Bopomofo\n'.encode("utf-8"),
			"no type column": b"text,braille\r\nAlpha,x\r\n",
			"empty": b"",
			"records of empty fields": EMPTY_FIELDS_CSV,
		}
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			for name, data in corpora.items():
				with self.subTest(name):
					path.write_bytes(data)

					self.assertEqual(_values(load_dictionary_rows(path)), _values(_dictreader_rows(path)))

	def test_read_errors_equal_those_of_dictreader(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			for name, data in (("late Big5", LATE_BIG5), ("field limit", FIELD_LIMIT)):
				with self.subTest(name):
					path.write_bytes(data)
					with self.assertRaises(Exception) as expected:
						_dictreader_rows(path)

					with self.assertRaises(type(expected.exception)) as actual:
						load_dictionary_rows(path)

					self.assertEqual(str(actual.exception), str(expected.exception))


class DictionaryWriterLayoutTest(unittest.TestCase):
	"""The writer keeps the BOM, the header and the extra fields of the file (F-11 D5)."""

	def save(self, rows, layout=None) -> bytes:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			if layout is None:
				save_dictionary_entries(path, rows)
			else:
				save_dictionary_entries(path, rows, layout)
			return path.read_bytes()

	def round_trip(self, data: bytes) -> bytes:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(data)
			loaded = entries_module.load_dictionary_file(path)
			save_dictionary_entries(path, loaded.rows, loaded.layout)
			return path.read_bytes()

	def test_bom_is_kept_and_never_added(self) -> None:
		alpha = DictionaryEntry("Alpha", "\u2801", "General")
		with_bom = self.save([alpha], entries_module.DictionaryLayout(True, ("text", "braille", "type")))
		without = self.save([alpha], entries_module.DictionaryLayout(False, ("text", "braille", "type")))

		self.assertEqual(with_bom, BOM + "text,braille,type\r\nAlpha,\u2801,General\r\n".encode("utf-8"))
		self.assertEqual(without, "text,braille,type\r\nAlpha,\u2801,General\r\n".encode("utf-8"))

	def test_an_unchanged_file_with_a_bom_and_an_extra_column_is_written_back_byte_for_byte(self) -> None:
		self.assertEqual(self.round_trip(EXTRA_CSV), EXTRA_CSV)

	def test_header_order_is_kept_and_missing_required_columns_are_appended(self) -> None:
		layout = entries_module.DictionaryLayout(False, ("type", "note", "text"))

		data = self.save([DictionaryEntry("Alpha", "\u2801", "Braille")], layout)

		self.assertEqual(data, "type,note,text,braille\r\nBraille,,Alpha,\u2801\r\n".encode("utf-8"))

	def test_rows_keep_extra_and_overflow_fields_and_are_stripped_and_normalized(self) -> None:
		data = (
			"text,note,braille,type\r\n"
			" Alpha ,first,  \u2801 ,Custom,overflow\r\n"
			"short\r\n"
		).encode("utf-8")

		self.assertEqual(
			self.round_trip(data),
			"text,note,braille,type\r\nAlpha,first,\u2801,General,overflow\r\nshort,,,General\r\n".encode("utf-8"),
		)

	def test_a_new_row_has_empty_extra_fields_and_an_edited_row_keeps_them(self) -> None:
		layout = entries_module.DictionaryLayout(False, ("text", "note", "braille", "type"))
		edited = DictionaryEntry("Alpine", "\u2801\u2807", "General", ("Alpha", "first", "\u2801", "General"))
		new = DictionaryEntry("Gamma", "\u281b", "Braille")

		data = self.save([edited, new], layout)

		self.assertEqual(
			data,
			"text,note,braille,type\r\nAlpine,first,\u2801\u2807,General\r\nGamma,,\u281b,Braille\r\n".encode("utf-8"),
		)

	def test_a_column_named_twice_gets_the_value_at_its_last_position(self) -> None:
		# DictReader reads the last position, so the writer writes there; the other keeps its value.
		layout = entries_module.DictionaryLayout(False, ("text", "braille", "type", "text"))
		entry = DictionaryEntry("Zeta", "\u2801", "General", ("Alpha", "\u2801", "General", "Alpha2"))

		data = self.save([entry], layout)

		self.assertEqual(data, "text,braille,type,text\r\nAlpha,\u2801,General,Zeta\r\n".encode("utf-8"))

	def test_hidden_rows_are_written_with_their_fields(self) -> None:
		# Until the editor removes them (F-11 D1), the rows it hides keep their whole record.
		data = "text,note,braille,type\r\n,kept,\u2803,General\r\n".encode("utf-8")

		self.assertEqual(self.round_trip(data), data)

	def test_default_layout_gives_the_bytes_of_the_writer_before_f11(self) -> None:
		entries = [DictionaryEntry("Alpha", "\u2801", "General"), DictionaryEntry("q,\"x\"", "a b", "Braille")]

		self.assertEqual(
			self.save(entries),
			'text,braille,type\r\nAlpha,\u2801,General\r\n"q,""x""",a b,Braille\r\n'.encode("utf-8"),
		)
		self.assertEqual(self.save(entries, entries_module.DictionaryLayout()), self.save(entries))


if __name__ == "__main__":
	unittest.main()
