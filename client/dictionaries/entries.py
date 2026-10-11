from __future__ import annotations

import codecs
import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from i18n import _
from shared.atomic_write import write_text_atomically
from text.zhuyin import normalize_zhuyin_sequence


ENTRY_TYPE_OPTIONS: list[tuple[str, str]] = [
	("General", _("General")),
	("Bopomofo", _("Bopomofo")),
	("Braille", _("Unicode Braille")),
]
ENTRY_TYPE_LABELS = {key: label for key, label in ENTRY_TYPE_OPTIONS}
DEFAULT_ENTRY_TYPE = ENTRY_TYPE_OPTIONS[0][0]
BRAILLE_UNICODE_PATTERNS_START = 0x2800
# The columns every dictionary has; the writer adds the ones a header lacks (F-11 D5).
REQUIRED_COLUMNS = ("text", "braille", "type")


@dataclass
class DictionaryEntry:
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE
	# Every field of the record the entry was read from, extra columns included; the
	# writer starts from them (F-11 D5). Empty for a new entry. Not part of equality.
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)


@dataclass(frozen=True)
class PreservedDictionaryRow:
	"""A row the editor does not show: a blank source text, or a Bopomofo row whose
	sequence does not parse (F-4).

	Kept as read (fields not stripped, a missing field as "") and written back
	unchanged at its place in the file. Never equal to a ``DictionaryEntry``
	(dataclass equality requires the same class). ``line`` is the file line on which
	its record starts, the header being line 1, and ``fields`` the record as read
	(F-11 D1, D6); neither takes part in equality.
	"""

	text: str
	braille: str
	entry_type: str
	line: int = field(default=0, compare=False)
	fields: tuple[str, ...] = field(default=(), compare=False, repr=False)

	@property
	def reason(self) -> str:
		"""Why the editor hides the row: ``"no_source_text"`` or ``"invalid_bopomofo"`` (F-11 D1)."""
		return "no_source_text" if not self.text.strip() else "invalid_bopomofo"


DictionaryRow = DictionaryEntry | PreservedDictionaryRow


@dataclass(frozen=True)
class DictionaryLayout:
	"""What the writer keeps of a dictionary file: its UTF-8 BOM and its header record (F-11 D5)."""

	has_bom: bool = False
	header: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedDictionary:
	rows: tuple[DictionaryRow, ...]
	layout: DictionaryLayout


def normalize_entry_type(entry_type: str | None) -> str:
	if entry_type in ENTRY_TYPE_LABELS:
		return str(entry_type)
	return DEFAULT_ENTRY_TYPE


def canonical_bopomofo(braille: str) -> str | None:
	"""The Bopomofo sequence the editor shows and saves for ``braille``; None if it does not parse.

	Surrounding whitespace is stripped, as from every field, except the tone space of a
	final first-tone syllable: the parser marks a first tone with a space, so a sequence
	that only parses with that space gets it back (F-11 D14).
	"""
	sequence = braille.strip()
	for candidate in (sequence, sequence + " "):
		try:
			normalize_zhuyin_sequence(candidate)
		except Exception:
			continue
		return candidate
	return None


def validate_dictionary_entry(entry: DictionaryEntry) -> None:
	if not entry.text.strip():
		raise ValueError(_("Please enter the source text."))
	if normalize_entry_type(entry.entry_type) == "Bopomofo":
		if canonical_bopomofo(entry.braille) is None:
			raise ValueError(_("Please enter the a valid Bopomofo sequence."))
	elif normalize_entry_type(entry.entry_type) == "Braille":
		for braille_character in entry.braille:
			if not BRAILLE_UNICODE_PATTERNS_START <= ord(braille_character) < BRAILLE_UNICODE_PATTERNS_START + 256:
				raise ValueError(_("Please enter the a valid Unicode Braille sequence."))


def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]:
	"""Every data row of the file in file order: an entry, or a row the editor keeps hidden."""
	return list(load_dictionary_file(dictionary_path).rows)


def load_dictionary_file(dictionary_path: Path) -> LoadedDictionary:
	"""The rows of ``load_dictionary_rows`` and the layout of the file (F-11 D6).

	The values are the ones ``csv.DictReader`` gives: the first record is the header
	(even a blank one), blank records are skipped, a missing field is "" and a column
	named twice takes the value of its last position. A missing file has no rows and
	the default layout. Read errors propagate.
	"""
	if not dictionary_path.exists():
		return LoadedDictionary((), DictionaryLayout())

	with dictionary_path.open("rb") as raw:
		has_bom = raw.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8
	header: list[str] | None = None
	rows: list[DictionaryRow] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.reader(fp)
		next_line = 1
		for record in reader:
			# A record starts on the line after the previous one ends; a quoted field can
			# span lines, and a blank line is a record of its own.
			line, next_line = next_line, reader.line_num + 1
			if header is None:
				header = record
			elif record:
				rows.append(_read_row(header, record, line))
	return LoadedDictionary(tuple(rows), DictionaryLayout(has_bom, tuple(header or ())))


def _column(header: list[str], name: str) -> int | None:
	"""The position ``csv.DictReader`` reads ``name`` from: its last one in the header."""
	positions = [index for index, column in enumerate(header) if column == name]
	return positions[-1] if positions else None


def _read_row(header: list[str], record: list[str], line: int) -> DictionaryRow:
	text, braille, entry_type = (
		record[index] if index is not None and index < len(record) else ""
		for index in (_column(header, name) for name in REQUIRED_COLUMNS)
	)
	entry = DictionaryEntry(
		text=text.strip(),
		braille=braille.strip(),
		entry_type=normalize_entry_type(entry_type),
		fields=tuple(record),
	)
	if not _is_editable(entry):
		return PreservedDictionaryRow(text=text, braille=braille, entry_type=entry_type, line=line, fields=tuple(record))
	if entry.entry_type == "Bopomofo":
		entry.braille = canonical_bopomofo(entry.braille)
	return entry


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses
	(once a final first-tone syllable has its tone space back, F-11 D14)."""
	if not entry.text:
		return False
	return entry.entry_type != "Bopomofo" or canonical_bopomofo(entry.braille) is not None


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
	"""The rows the editor shows and Dictionary Management counts."""
	return [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]


def save_dictionary_entries(
	dictionary_path: Path,
	rows: Iterable[DictionaryRow],
	layout: DictionaryLayout = DictionaryLayout(),
) -> None:
	"""Replace the file atomically; on an error it is unchanged.

	The file gets the BOM of ``layout`` and its header, with the required columns it
	lacks appended (``text,braille,type`` without a header). Each row is its record as
	read, padded to the header, with its text, braille and type in their columns (the
	last position of a column named twice): extra columns and overflow fields are kept,
	a new row has them empty (F-11 D5). UTF-8, CRLF, minimal quoting.
	"""
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)
	header = list(layout.header)
	header.extend(name for name in REQUIRED_COLUMNS if name not in header)
	positions = [_column(header, name) for name in REQUIRED_COLUMNS]

	def _write(fp) -> None:
		writer = csv.writer(fp)
		writer.writerow(header)
		for row in rows:
			fields = list(row.fields) + [""] * (len(header) - len(row.fields))
			for position, value in zip(positions, (row.text, row.braille, row.entry_type)):
				fields[position] = value
			writer.writerow(fields)

	# utf-8-sig writes the BOM first.
	encoding = "utf-8-sig" if layout.has_bom else "utf-8"
	write_text_atomically(dictionary_path, _write, encoding=encoding, newline="")
