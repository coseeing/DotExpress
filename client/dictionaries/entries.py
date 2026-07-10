from __future__ import annotations

import csv
from dataclasses import dataclass
import gettext
from pathlib import Path

from text.zhuyin import normalize_zhuyin_sequence


def _resource_path(relative_path: str) -> Path:
	return Path(__file__).resolve().parents[1] / relative_path


LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ["zh_TW"]
_translation = gettext.translation(
	LOCALE_DOMAIN,
	localedir=str(_resource_path("locales")),
	languages=LOCALE_LANGUAGES,
	fallback=True,
)
_ = _translation.gettext


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


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
	if not dictionary_path.exists():
		return []

	entries: list[DictionaryEntry] = []
	with dictionary_path.open("r", newline="", encoding="utf-8") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if not entry.text:
				continue
			if entry.entry_type == "Bopomofo":
				try:
					normalize_zhuyin_sequence(entry.braille)
				except Exception:
					continue
			entries.append(entry)
	return entries


def save_dictionary_entries(dictionary_path: Path, entries: list[DictionaryEntry]) -> None:
	dictionary_path.parent.mkdir(parents=True, exist_ok=True)
	with dictionary_path.open("w", newline="", encoding="utf-8") as fp:
		writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		for entry in entries:
			writer.writerow(
				{
					"text": entry.text,
					"braille": entry.braille,
					"type": entry.entry_type,
				}
			)
