from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
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


@dataclass
class DictionaryEntry:
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE


@dataclass(frozen=True)
class PreservedDictionaryRow:
	"""A row the editor does not show: a blank source text, or a Bopomofo row whose
	sequence does not parse (F-4).

	Kept as read (fields not stripped, a missing field as "") and written back
	unchanged at its place in the file. Never equal to a ``DictionaryEntry``
	(dataclass equality requires the same class).
	"""

	text: str
	braille: str
	entry_type: str


DictionaryRow = DictionaryEntry | PreservedDictionaryRow


def normalize_entry_type(entry_type: str | None) -> str:
	if entry_type in ENTRY_TYPE_LABELS:
		return str(entry_type)
	return DEFAULT_ENTRY_TYPE


def validate_dictionary_entry(entry: DictionaryEntry) -> None:
	if not entry.text.strip():
		raise ValueError(_("Please enter the source text."))
	if normalize_entry_type(entry.entry_type) == "Bopomofo":
		try:
			normalize_zhuyin_sequence(entry.braille)
		except Exception as exc:
			raise ValueError(_("Please enter the a valid Bopomofo sequence.")) from exc
	elif normalize_entry_type(entry.entry_type) == "Braille":
		for braille_character in entry.braille:
			if not BRAILLE_UNICODE_PATTERNS_START <= ord(braille_character) < BRAILLE_UNICODE_PATTERNS_START + 256:
				raise ValueError(_("Please enter the a valid Unicode Braille sequence."))


def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]:
	"""Every data row of the file in file order: an entry, or a row the editor keeps hidden."""
	if not dictionary_path.exists():
		return []

	rows: list[DictionaryRow] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if _is_editable(entry):
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


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses."""
	if not entry.text:
		return False
	if entry.entry_type == "Bopomofo":
		try:
			normalize_zhuyin_sequence(entry.braille)
		except Exception:
			return False
	return True


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
	"""The rows the editor shows and Dictionary Management counts."""
	return [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]


def save_dictionary_entries(dictionary_path: Path, rows: Iterable[DictionaryRow]) -> None:
	"""Replace the file atomically; on an error it is unchanged."""
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)

	def _write(fp) -> None:
		writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		for row in rows:
			writer.writerow(
				{
					"text": row.text,
					"braille": row.braille,
					"type": row.entry_type,
				}
			)

	write_text_atomically(dictionary_path, _write, encoding="utf-8", newline="")
