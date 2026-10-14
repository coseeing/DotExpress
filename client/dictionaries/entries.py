from __future__ import annotations

import codecs
import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from i18n import N_, _
from shared.atomic_write import write_text_atomically
from text.zhuyin import normalize_zhuyin_sequence


# (key, msgid): the labels are translated when they are shown (F-14 D3).
ENTRY_TYPE_OPTIONS: list[tuple[str, str]] = [
	("General", N_("General")),
	("Bopomofo", N_("Bopomofo")),
	("Braille", N_("Unicode Braille")),
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

	@property
	def header_recognized(self) -> bool:
		"""Whether the header names a ``text`` column, or no row is hidden.

		Under a header without one (``Text,Braille,Type``, a blank first line) every row
		reads as having no source text; such rows must never be removed as hidden rows
		(F-11 review M-1).
		"""
		return "text" in self.layout.header or not any(isinstance(row, PreservedDictionaryRow) for row in self.rows)


def normalize_entry_type(entry_type: str | None) -> str:
	if entry_type in ENTRY_TYPE_LABELS:
		return str(entry_type)
	return DEFAULT_ENTRY_TYPE


def entry_type_label(entry_type: str) -> str:
	"""The translated label of a known entry type; any other value unchanged (F-14 D3)."""
	label = ENTRY_TYPE_LABELS.get(entry_type)
	return entry_type if label is None else _(label)


def entry_type_choices() -> list[str]:
	"""The translated labels of the entry types, in option order (F-14 D3)."""
	return [_(label) for _key, label in ENTRY_TYPE_OPTIONS]


def canonical_bopomofo(braille: str) -> str | None:
	"""The Bopomofo sequence the editor shows and saves for ``braille``; None if it does not parse.

	Only leading whitespace is stripped: the parser marks a first tone with a trailing
	space, so trailing whitespace is part of the sequence and must parse as it is. Nothing
	is appended (F-11 D14, decided by the user 2026-10-11).
	"""
	sequence = braille.lstrip()
	try:
		normalize_zhuyin_sequence(sequence)
	except Exception:
		return None
	return sequence


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
	normalized_type = normalize_entry_type(entry_type)
	entry = DictionaryEntry(
		text=text.strip(),
		# A Bopomofo sequence keeps its trailing whitespace (F-11 D14).
		braille=braille.lstrip() if normalized_type == "Bopomofo" else braille.strip(),
		entry_type=normalized_type,
		fields=tuple(record),
	)
	if not _is_editable(entry):
		return PreservedDictionaryRow(text=text, braille=braille, entry_type=entry_type, line=line, fields=tuple(record))
	return entry


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses
	as it is once its leading whitespace is gone (F-11 D14)."""
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
	a new row has them empty (F-11 D5). An appended column goes between the header's
	fields and the overflow fields, which move right (F-11 review M-5). UTF-8, CRLF,
	minimal quoting.
	"""
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)
	header = list(layout.header)
	header.extend(name for name in REQUIRED_COLUMNS if name not in header)
	# Without a header (the default layout), a record's first fields are text, braille, type.
	read_columns = len(layout.header) if layout.header else len(header)
	positions = [_column(header, name) for name in REQUIRED_COLUMNS]

	def _write(fp) -> None:
		writer = csv.writer(fp)
		writer.writerow(header)
		for row in rows:
			fields = list(row.fields[:read_columns])
			fields += [""] * (len(header) - len(fields))
			fields += row.fields[read_columns:]
			for position, value in zip(positions, (row.text, row.braille, row.entry_type)):
				fields[position] = value
			writer.writerow(fields)

	# utf-8-sig writes the BOM first.
	encoding = "utf-8-sig" if layout.has_bom else "utf-8"
	write_text_atomically(dictionary_path, _write, encoding=encoding, newline="")
