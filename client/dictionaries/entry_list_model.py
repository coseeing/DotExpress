"""wx-free model of the dictionary entries editor (the "Custom Dictionary Manager" in ``dialog.py``).

The model owns every row of the file in file order, the filter text and the
visible (filtered) list. The dialog owns the widgets and the selected row: it
passes the selected visible index into each call and renders the returned
``EntryListUpdate``. Nothing here imports wx or i18n; the dialog shows the
messages.

Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed: they keep their place in the file and ``save``
writes them back unchanged (F-4). ``entries`` and the visible list hold the
entries only.

Comparison rules, kept from the pre-P2-2 dialog (a file may hold identical rows):

* the selection is restored by equality: the first visible entry equal to the
  previous one wins;
* ``replace`` swaps the full-list item that *is* the visible entry (identity);
* ``remove`` removes the first full-list entry *equal* to the visible one;
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  row, entries hidden by the filter and preserved rows included, and excludes
  the edited entry by identity.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from dictionaries.entries import (
	ENTRY_TYPE_LABELS,
	DictionaryEntry,
	DictionaryRow,
	load_dictionary_rows,
	save_dictionary_entries,
)


class DuplicateEntryError(ValueError):
	"""Another entry already has this source text; nothing was changed."""

	def __init__(self, identifier: str) -> None:
		super().__init__(identifier)
		self.identifier = identifier


@dataclass(frozen=True)
class EntryListUpdate:
	"""What the view renders after a change."""

	selection: int | None  # visible row to select and focus; None: clear the selection
	filter_cleared: bool = False  # add only: the filter was reset to "" because the new entry did not match


class DictionaryEntryListModel:
	"""Full list, filter and visible list of one dictionary CSV."""

	def __init__(self, rows: Iterable[DictionaryRow] = ()) -> None:
		self._rows: list[DictionaryRow] = list(rows)
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read every row of ``path`` with ``load_dictionary_rows``; errors propagate."""
		return cls(load_dictionary_rows(path))

	def save(self, path: Path) -> None:
		"""Write every row (preserved rows unchanged, in place); errors propagate."""
		save_dictionary_entries(path, self._rows)

	@property
	def _entries(self) -> list[DictionaryEntry]:
		return [row for row in self._rows if isinstance(row, DictionaryEntry)]

	@property
	def rows(self) -> tuple[DictionaryRow, ...]:
		"""Every row of the file in file order, preserved rows included."""
		return tuple(self._rows)

	@property
	def entries(self) -> tuple[DictionaryEntry, ...]:
		return tuple(self._entries)

	@property
	def visible_entries(self) -> tuple[DictionaryEntry, ...]:
		return tuple(self._visible)

	@property
	def filter_text(self) -> str:
		return self._filter_text

	@property
	def visible_count(self) -> int:
		return len(self._visible)

	def visible_entry(self, index: int | None) -> DictionaryEntry | None:
		if index is None or index < 0 or index >= len(self._visible):
			return None
		return self._visible[index]

	def cell_text(self, row: int, column: int) -> str:
		entry = self._visible[row]
		if column == 0:
			return entry.text
		if column == 1:
			return entry.braille
		if column == 2:
			return ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)
		raise ValueError(f"Unknown column: {column}")

	@staticmethod
	def matches(entry: DictionaryEntry, filter_text: str) -> bool:
		normalized_filter = filter_text.casefold()
		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool:
		return any(row.text == text and row is not exclude_entry for row in self._rows)

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate:
		preferred_entry = self.visible_entry(selected_index)
		self._filter_text = filter_text
		self._refilter()
		return EntryListUpdate(self._selection_after(preferred_entry, 0))

	def add(self, entry: DictionaryEntry) -> EntryListUpdate:
		if self.source_text_exists(entry.text):
			raise DuplicateEntryError(entry.text)
		self._rows.append(entry)
		filter_cleared = bool(self._filter_text) and not self.matches(entry, self._filter_text)
		if filter_cleared:
			self._filter_text = ""
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, 0), filter_cleared=filter_cleared)

	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		if self.source_text_exists(entry.text, exclude_entry=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index))

	def remove(self, visible_index: int) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		self._rows.remove(current_entry)
		self._refilter()
		return EntryListUpdate(self._selection_after(current_entry, visible_index))

	def _visible_at(self, index: int) -> DictionaryEntry:
		if index < 0 or index >= len(self._visible):
			raise IndexError(f"visible index out of range: {index}")
		return self._visible[index]

	def _refilter(self) -> None:
		if self._filter_text:
			self._visible = [entry for entry in self._entries if self.matches(entry, self._filter_text)]
		else:
			self._visible = list(self._entries)

	def _selection_after(self, preferred_entry: DictionaryEntry | None, fallback_index: int) -> int | None:
		if not self._visible:
			return None
		index = min(fallback_index, len(self._visible) - 1)
		if preferred_entry is not None:
			try:
				index = self._visible.index(preferred_entry)
			except ValueError:
				pass
		return index
