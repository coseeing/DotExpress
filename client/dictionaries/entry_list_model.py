"""wx-free model of the dictionary entries editor (the "Custom Dictionary Manager" in ``dialog.py``).

The model owns every row of the file in file order, the filter text and the
visible (filtered) list. The dialog owns the widgets and the selected row: it
passes the selected visible index into each call and renders the returned
``EntryListUpdate``. Nothing here imports wx or i18n; the dialog shows the
messages.

Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed, and their source texts are not duplicates (F-11
D2). ``hidden_rows`` lists them for the dialog, which asks before saving;
``save`` writes the entries only, so it removes them from the file (F-11 D1;
F-4 wrote them back). ``entries`` and the visible list hold the entries only.
``save`` writes with the layout of the loaded file (its BOM and header); a
replaced entry takes over the fields of the row it replaces, so its extra
columns are kept (F-11 D5).

Comparison rules (a file may hold identical rows):

* ``replace`` and ``remove`` act on the full-list item that *is* the visible
  entry (identity; ``remove`` took the first *equal* one before F-11, P2-2 Q4);
* after ``add`` and ``replace`` the new entry is selected by identity; after
  ``remove`` and a filter change the selection is restored by equality, the
  first visible entry equal to the previous one winning (as the golden trace
  records);
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  entry, entries hidden by the filter included, preserved rows not (F-11 D2),
  and excludes the edited entry by identity; an edit that keeps the edited
  entry's own text is never a duplicate (F-11 D9).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from dictionaries.entries import (
	ENTRY_TYPE_LABELS,
	DictionaryEntry,
	DictionaryLayout,
	DictionaryRow,
	PreservedDictionaryRow,
	load_dictionary_file,
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

	def __init__(self, rows: Iterable[DictionaryRow] = (), layout: DictionaryLayout = DictionaryLayout()) -> None:
		self._rows: list[DictionaryRow] = list(rows)
		self._layout = layout
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read every row of ``path`` and its layout with ``load_dictionary_file``; errors propagate."""
		loaded = load_dictionary_file(path)
		return cls(loaded.rows, loaded.layout)

	def save(self, path: Path) -> None:
		"""Write the entries with the layout of the loaded file; errors propagate.

		The hidden rows are not written (F-11 D1); after a successful write the model
		holds the entries only. After an error the hidden rows are still there.
		"""
		entries = self._entries
		save_dictionary_entries(path, entries, self._layout)
		self._rows = list(entries)

	@property
	def hidden_rows(self) -> tuple[PreservedDictionaryRow, ...]:
		"""The rows the editor does not show, in file order (F-11 D1)."""
		return tuple(row for row in self._rows if isinstance(row, PreservedDictionaryRow))

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
		"""Whether an entry other than ``exclude_entry`` has exactly this source text.

		Preserved rows do not count: OK lists them before removing them (F-11 D1, D2).
		"""
		return any(entry.text == text and entry is not exclude_entry for entry in self._entries)

	def is_duplicate(self, text: str, editing: DictionaryEntry | None = None) -> bool:
		"""Whether adding (``editing`` None) or editing ``editing`` to ``text`` duplicates a row.

		An edit that keeps the entry's own text adds no duplicate, even when an identical
		row exists (F-11 D9).
		"""
		if editing is not None and text == editing.text:
			return False
		return self.source_text_exists(text, exclude_entry=editing)

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
		return EntryListUpdate(self._selection_after(entry, 0, by_identity=True), filter_cleared=filter_cleared)

	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		if self.is_duplicate(entry.text, editing=current_entry):
			raise DuplicateEntryError(entry.text)
		full_index = self._full_index(current_entry)
		entry.fields = current_entry.fields
		self._rows[full_index] = entry
		self._refilter()
		return EntryListUpdate(self._selection_after(entry, visible_index, by_identity=True))

	def remove(self, visible_index: int) -> EntryListUpdate:
		current_entry = self._visible_at(visible_index)
		del self._rows[self._full_index(current_entry)]
		self._refilter()
		return EntryListUpdate(self._selection_after(current_entry, visible_index))

	def _full_index(self, entry: DictionaryEntry) -> int:
		"""The full-list position of the row that *is* ``entry`` (F-11 D9)."""
		return next(index for index, candidate in enumerate(self._rows) if candidate is entry)

	def _visible_at(self, index: int) -> DictionaryEntry:
		if index < 0 or index >= len(self._visible):
			raise IndexError(f"visible index out of range: {index}")
		return self._visible[index]

	def _refilter(self) -> None:
		if self._filter_text:
			self._visible = [entry for entry in self._entries if self.matches(entry, self._filter_text)]
		else:
			self._visible = list(self._entries)

	def _selection_after(
		self,
		preferred_entry: DictionaryEntry | None,
		fallback_index: int,
		*,
		by_identity: bool = False,
	) -> int | None:
		if not self._visible:
			return None
		index = min(fallback_index, len(self._visible) - 1)
		if preferred_entry is not None:
			if by_identity:
				index = next((position for position, entry in enumerate(self._visible) if entry is preferred_entry), index)
			else:
				try:
					index = self._visible.index(preferred_entry)
				except ValueError:
					pass
		return index
