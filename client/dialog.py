from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import gettext
import sys
from typing import List

import wx
from Bopomofo import normalize_zhuyin_sequence
from dictionaries.actions import get_action_availability, resolve_dictionary_selection
from dictionaries.manager import (
	DEFAULT_DICTIONARY_NAME,
	MAX_DICTIONARY_NAME_LENGTH,
	dictionary_path_for_name,
	list_dictionary_names,
	normalize_dictionary_name,
)
from documents.workspace import normalize_document_name


def resource_path(relative_path: str) -> Path:
	if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
		base_path = Path(sys._MEIPASS)
	else:
		base_path = Path(__file__).resolve().parent
	return base_path / relative_path


LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ["zh_TW"]
_translation = gettext.translation(
	LOCALE_DOMAIN,
	localedir=str(resource_path("locales")),
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


def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
	dialog.SetSizerAndFit(sizer)
	if dialog.GetParent() is not None:
		dialog.CentreOnParent()
	else:
		dialog.Centre()


def _normalize_dialog_name(
	candidate: str,
	normalizer: Callable[[str], str],
	empty_message: str,
	length_message: str,
	invalid_message: str,
	reserved_message: str | None = None,
) -> tuple[str | None, str | None]:
	if not candidate or not candidate.strip():
		return None, empty_message
	if any(ord(char) < 32 for char in candidate):
		return None, invalid_message
	if candidate.endswith((" ", ".")):
		return None, invalid_message
	normalized_candidate = candidate.strip()
	if len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:
		return None, length_message
	try:
		return normalizer(normalized_candidate), None
	except ValueError as exc:
		if reserved_message and normalized_candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
			return None, reserved_message
		if "exceed" in str(exc):
			return None, length_message
		return None, invalid_message


@dataclass
class DictionaryEntry:
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE


def normalize_entry_type(entry_type: str | None) -> str:
	if entry_type in ENTRY_TYPE_LABELS:
		return str(entry_type)
	return DEFAULT_ENTRY_TYPE


def load_dictionary_entries(dictionary_path: Path) -> List[DictionaryEntry]:
	if not dictionary_path.exists():
		return []

	entries: List[DictionaryEntry] = []
	with dictionary_path.open("r", newline="", encoding="utf-8") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			text = (row.get("text") or "").strip()
			if not text:
				continue
			braille = (row.get("braille") or "").strip()
			entry_type = normalize_entry_type(row.get("type"))
			if entry_type == "Bopomofo":
				try:
					normalize_zhuyin_sequence(braille)
				except Exception:
					continue
			entries.append(DictionaryEntry(text=text, braille=braille, entry_type=entry_type))
	return entries


class AddSymbolDialog(wx.Dialog):
	"""Dialog to create or edit a dictionary entry."""

	def __init__(self, parent: wx.Window | None, entry: DictionaryEntry | None = None):
		title = _("Edit Dictionary Entry") if entry else _("Add Dictionary Entry")
		super().__init__(parent, title=title)

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
		grid.AddGrowableCol(1, 1)

		source_label = wx.StaticText(self, label=_("Source Text"))
		self.identifier_ctrl = wx.TextCtrl(self)
		braille_label = wx.StaticText(self, label=_("Braille"))
		self.braille_ctrl = wx.TextCtrl(self)
		type_label = wx.StaticText(self, label=_("Type"))
		self.type_choice = wx.Choice(self, choices=[label for _key, label in ENTRY_TYPE_OPTIONS])

		grid.Add(source_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.identifier_ctrl, 1, wx.EXPAND)
		grid.Add(braille_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.braille_ctrl, 1, wx.EXPAND)
		grid.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.type_choice, 1, wx.EXPAND)

		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

		finalize_dialog_layout(self, main_sizer)
		self._apply_initial_values(entry)
		self.identifier_ctrl.SetFocus()

	def get_identifier(self) -> str:
		return self.identifier_ctrl.GetValue().strip()

	def get_braille(self) -> str:
		return self.braille_ctrl.GetValue().strip()

	def get_entry_type(self) -> str:
		selection = self.type_choice.GetSelection()
		if selection == wx.NOT_FOUND:
			return DEFAULT_ENTRY_TYPE
		key = ENTRY_TYPE_OPTIONS[selection][0]
		return key if key in ENTRY_TYPE_LABELS else DEFAULT_ENTRY_TYPE

	def get_entry(self) -> DictionaryEntry:
		return DictionaryEntry(
			text=self.get_identifier(),
			braille=self.get_braille(),
			entry_type=self.get_entry_type(),
		)

	def _apply_initial_values(self, entry: DictionaryEntry | None) -> None:
		if entry:
			self.identifier_ctrl.SetValue(entry.text)
			self.braille_ctrl.SetValue(entry.braille)
			self._select_entry_type(entry.entry_type)
		else:
			self._select_entry_type(DEFAULT_ENTRY_TYPE)

	def _select_entry_type(self, entry_type: str) -> None:
		index = next((idx for idx, (key, _label) in enumerate(ENTRY_TYPE_OPTIONS) if key == entry_type), None)
		if index is None:
			index = 0
		self.type_choice.SetSelection(index)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
			identifier = self.get_identifier()
		except RuntimeError:
			event.Skip()
			return

		if not identifier:
			wx.MessageBox(_("Please enter the source text."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			try:
				self.identifier_ctrl.SetFocus()
			except RuntimeError:
				pass
			return

		braille = self.get_braille()
		entry_type = self.get_entry_type()
		if entry_type == "Bopomofo":
			try:
				normalize_zhuyin_sequence(braille)
			except Exception:
				wx.MessageBox(_("Please enter the a valid Bopomofo sequence."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
				try:
					self.braille_ctrl.SetFocus()
				except RuntimeError:
					pass
				return
		elif entry_type == "Braille":
			for b in braille:
				if not BRAILLE_UNICODE_PATTERNS_START <= ord(b) < BRAILLE_UNICODE_PATTERNS_START + 256:
					wx.MessageBox(_("Please enter the a valid Unicode Braille sequence."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
					try:
						self.braille_ctrl.SetFocus()
					except RuntimeError:
						pass
					return

		event.Skip()

	def __enter__(self) -> "AddSymbolDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class DictionaryNameDialog(wx.Dialog):
	"""Dialog for creating a new dictionary file name."""

	def __init__(self, parent: wx.Window | None, initial_name: str = ""):
		super().__init__(parent, title=_("Add Dictionary"))

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
		grid.AddGrowableCol(1, 1)

		name_label = wx.StaticText(self, label=_("Dictionary Name"))
		self.name_ctrl = wx.TextCtrl(self)
		grid.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.name_ctrl, 1, wx.EXPAND)
		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

		finalize_dialog_layout(self, main_sizer)
		self._apply_initial_name(initial_name)

	def get_dictionary_name(self) -> str:
		return self.name_ctrl.GetValue().strip()

	def _apply_initial_name(self, initial_name: str) -> None:
		self.name_ctrl.SetValue(initial_name)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		candidate = self.name_ctrl.GetValue()
		normalized_candidate, message = _normalize_dialog_name(
			candidate,
			normalize_dictionary_name,
			_("Please enter the dictionary name."),
			_("Dictionary name must be 1 to 32 characters."),
			_("Dictionary name is not a valid Windows file name."),
			_('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
		)
		if message:
			wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			self.name_ctrl.SetFocus()
			return
		self.name_ctrl.SetValue(normalized_candidate)
		event.Skip()

	def _validate_name(self, candidate: str) -> str | None:
		_normalized, message = _normalize_dialog_name(
			candidate,
			normalize_dictionary_name,
			_("Please enter the dictionary name."),
			_("Dictionary name must be 1 to 32 characters."),
			_("Dictionary name is not a valid Windows file name."),
			_('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
		)
		return message

	def __enter__(self) -> "DictionaryNameDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class DocumentNameDialog(wx.Dialog):
	"""Dialog for creating or renaming a document."""

	def __init__(self, parent: wx.Window | None, title: str, initial_name: str = ""):
		super().__init__(parent, title=title)

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
		grid.AddGrowableCol(1, 1)

		name_label = wx.StaticText(self, label=_("Document Name"))
		self.name_ctrl = wx.TextCtrl(self)
		self.name_ctrl.SetValue(initial_name)
		grid.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.name_ctrl, 1, wx.EXPAND)
		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

		finalize_dialog_layout(self, main_sizer)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def get_document_name(self) -> str:
		return self.name_ctrl.GetValue().strip()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		candidate = self.name_ctrl.GetValue()
		normalized_candidate, message = _normalize_dialog_name(
			candidate,
			normalize_document_name,
			_("Please enter the document name."),
			_("Document name must be 1 to 32 characters."),
			_("Document name is not a valid Windows file name."),
		)
		if message:
			wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			self.name_ctrl.SetFocus()
			return
		self.name_ctrl.SetValue(normalized_candidate)
		event.Skip()

	def _validate_name(self, candidate: str) -> str | None:
		_normalized, message = _normalize_dialog_name(
			candidate,
			normalize_document_name,
			_("Please enter the document name."),
			_("Document name must be 1 to 32 characters."),
			_("Document name is not a valid Windows file name."),
		)
		return message

	def __enter__(self) -> "DocumentNameDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class InvalidWorkspaceFilesDialog(wx.Dialog):
	"""Dialog shown when startup finds invalid DEP files in the workspace."""

	def __init__(self, parent: wx.Window | None, invalid_paths: list[Path]):
		super().__init__(parent, title=_("Invalid Workspace Files"))
		self._delete_invalid_files = False
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		message = wx.StaticText(self, label=_("The following workspace files are invalid. Do you want to delete them or keep them?"))
		main_sizer.Add(message, 0, wx.EXPAND | wx.ALL, 12)
		self.list_box = wx.ListBox(self, choices=[path.name for path in invalid_paths])
		main_sizer.Add(self.list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		delete_btn = wx.Button(self, label=_("Delete Invalid Files"))
		keep_btn = wx.Button(self, label=_("Keep Invalid Files"))
		button_sizer.Add(delete_btn, 0, wx.RIGHT, 8)
		button_sizer.Add(keep_btn, 0)
		main_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		delete_btn.Bind(wx.EVT_BUTTON, self._on_delete)
		keep_btn.Bind(wx.EVT_BUTTON, self._on_keep)
		finalize_dialog_layout(self, main_sizer)
		self.SetMinSize((420, 280))

	def should_delete_invalid_files(self) -> bool:
		return self._delete_invalid_files

	def _on_delete(self, _event: wx.CommandEvent) -> None:
		self._delete_invalid_files = True
		self.EndModal(wx.ID_OK)

	def _on_keep(self, _event: wx.CommandEvent) -> None:
		self._delete_invalid_files = False
		self.EndModal(wx.ID_CANCEL)

	def __enter__(self) -> "InvalidWorkspaceFilesDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class FileIssuesDialog(wx.Dialog):
	"""Dialog shown when a batch operation skips one or more files."""

	def __init__(self, parent: wx.Window | None, title: str, message: str, issues: list[str]):
		super().__init__(parent, title=title)
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(wx.StaticText(self, label=message), 0, wx.EXPAND | wx.ALL, 12)
		self.list_box = wx.ListBox(self, choices=issues)
		main_sizer.Add(self.list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		button_sizer = self.CreateButtonSizer(wx.OK)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		finalize_dialog_layout(self, main_sizer)
		self.SetMinSize((520, 320))

	def __enter__(self) -> "FileIssuesDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class CallbackVirtualListCtrl(wx.ListCtrl):
	"""Virtual list that asks its owner for visible dictionary cell text."""

	def __init__(
		self,
		parent: wx.Window,
		get_item_text: Callable[[int, int], str],
		**kwargs,
	):
		super().__init__(parent, **kwargs)
		self._get_item_text = get_item_text

	def OnGetItemText(self, item: int, column: int) -> str:
		return self._get_item_text(item, column)


DictionaryEntryListCtrl = CallbackVirtualListCtrl


class SpeechSymbolsDialog(wx.Dialog):
	"""Dialog for editing custom dictionary mappings stored on disk."""

	def __init__(self, parent: wx.Window | None, dictionary_path: Path | None = None):
		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
		self.entries: List[DictionaryEntry] = self._load_entries()
		self.filtered_entries: List[DictionaryEntry] = list(self.entries)
		self._build_ui()
		self.filter_entries()
		self._update_button_states()

	def __enter__(self) -> "SpeechSymbolsDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		filter_label = wx.StaticText(self, label=_("Filter by:"))
		main_sizer.Add(filter_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		self.filter_ctrl = wx.TextCtrl(self)
		self.filter_ctrl.Bind(wx.EVT_TEXT, self._on_filter_changed)
		main_sizer.Add(self.filter_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		list_label = wx.StaticText(self, label=_("Dictionary entries"))
		main_sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

		self.list_ctrl = CallbackVirtualListCtrl(
			self,
			self._get_item_text,
			style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
		)
		self.list_ctrl.InsertColumn(0, _("Source Text"), width=200)
		self.list_ctrl.InsertColumn(1, _("Braille"), width=230)
		self.list_ctrl.InsertColumn(2, _("Type"), width=120)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 8)

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label=_("Add"))
		self.edit_button = wx.Button(self, label=_("Edit"))
		self.remove_button = wx.Button(self, label=_("Delete"))
		button_sizer.Add(self.add_button, 0, wx.RIGHT, 8)
		button_sizer.Add(self.edit_button, 0, wx.RIGHT, 8)
		button_sizer.Add(self.remove_button, 0)
		main_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		self.add_button.Bind(wx.EVT_BUTTON, self._on_add_clicked)
		self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit_clicked)
		self.remove_button.Bind(wx.EVT_BUTTON, self._on_remove_clicked)

		button_bar = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_bar:
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
			ok_button = self.FindWindowById(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

		finalize_dialog_layout(self, main_sizer)

	def _load_entries(self) -> List[DictionaryEntry]:
		return load_dictionary_entries(self.dictionary_path)

	def _get_item_text(self, item: int, column: int) -> str:
		entry = self.filtered_entries[item]
		if column == 0:
			return entry.text
		if column == 1:
			return entry.braille
		if column == 2:
			return ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)
		raise ValueError(f"Unknown column: {column}")

	def _entry_matches_filter(self, entry: DictionaryEntry, filter_text: str) -> bool:
		normalized_filter = filter_text.casefold()
		return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

	def filter_entries(
		self,
		filter_text: str | None = None,
		preferred_entry: DictionaryEntry | None = None,
		fallback_index: int = 0,
	) -> None:
		previous_entry = preferred_entry or self._get_selected_entry()
		if filter_text is None:
			filter_text = self.filter_ctrl.GetValue()

		if filter_text:
			self.filtered_entries = [
				entry for entry in self.entries if self._entry_matches_filter(entry, filter_text)
			]
		else:
			self.filtered_entries = list(self.entries)

		self.list_ctrl.SetItemCount(len(self.filtered_entries))
		self.list_ctrl.Refresh()
		if not self.filtered_entries:
			self._clear_selection()
			self._update_button_states()
			return

		new_index = min(fallback_index, len(self.filtered_entries) - 1)
		if previous_entry is not None:
			try:
				new_index = self.filtered_entries.index(previous_entry)
			except ValueError:
				pass
		self._select_index(new_index)

	def _on_filter_changed(self, event: wx.CommandEvent) -> None:
		self.filter_entries(self.filter_ctrl.GetValue())
		event.Skip()

	def _update_button_states(self) -> None:
		has_selection = self._get_selected_index() is not None
		self.edit_button.Enable(has_selection)
		self.remove_button.Enable(has_selection)

	def _get_selected_index(self) -> int | None:
		index = self.list_ctrl.GetFirstSelected()
		if index == wx.NOT_FOUND or index < 0 or index >= len(self.filtered_entries):
			return None
		return index

	def _get_selected_entry(self) -> DictionaryEntry | None:
		index = self._get_selected_index()
		return self.filtered_entries[index] if index is not None else None

	def _clear_selection(self) -> None:
		index = self.list_ctrl.GetFirstSelected()
		if index != wx.NOT_FOUND:
			self.list_ctrl.Select(index, False)

	def _select_index(self, index: int) -> None:
		if index < 0 or index >= len(self.filtered_entries):
			self._clear_selection()
			self._update_button_states()
			return
		self._clear_selection()
		self.list_ctrl.Select(index)
		self.list_ctrl.Focus(index)
		self._update_button_states()

	def _on_selection_changed(self, event: wx.ListEvent) -> None:
		self._update_button_states()
		event.Skip()

	def _on_item_activated(self, _event: wx.ListEvent) -> None:
		self._edit_selected()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
		new_entry = self._open_entry_dialog()
		if new_entry is None:
			return
		if self._identifier_exists(new_entry.text):
			wx.MessageBox(
				_('Source text "{identifier}" already exists.').format(identifier=new_entry.text),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		self.entries.append(new_entry)
		filter_text = self.filter_ctrl.GetValue()
		if filter_text and not self._entry_matches_filter(new_entry, filter_text):
			self.filter_ctrl.ChangeValue("")
			filter_text = ""
		self.filter_entries(filter_text, preferred_entry=new_entry)

	def _on_edit_clicked(self, _event: wx.CommandEvent) -> None:
		self._edit_selected()

	def _edit_selected(self) -> None:
		visible_index = self._get_selected_index()
		current_entry = self._get_selected_entry()
		if visible_index is None or current_entry is None:
			return
		updated_entry = self._open_entry_dialog(current_entry)
		if updated_entry is None:
			return
		if self._identifier_exists(updated_entry.text, exclude_entry=current_entry):
			wx.MessageBox(
				_('Source text "{identifier}" already exists.').format(identifier=updated_entry.text),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		full_index = next(
			index for index, entry in enumerate(self.entries) if entry is current_entry
		)
		self.entries[full_index] = updated_entry
		self.filter_entries(
			self.filter_ctrl.GetValue(),
			preferred_entry=updated_entry,
			fallback_index=visible_index,
		)

	def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
		visible_index = self._get_selected_index()
		current_entry = self._get_selected_entry()
		if visible_index is None or current_entry is None:
			return
		self.entries.remove(current_entry)
		self.filter_entries(
			self.filter_ctrl.GetValue(),
			fallback_index=visible_index,
		)

	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
		with AddSymbolDialog(self, entry) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_entry()

	def _identifier_exists(
		self,
		identifier: str,
		exclude_entry: DictionaryEntry | None = None,
	) -> bool:
		return any(
			entry.text == identifier and entry is not exclude_entry
			for entry in self.entries
		)

	def _normalize_type(self, entry_type: str | None) -> str:
		return normalize_entry_type(entry_type)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
			self._save_entries()
		except IOError as exc:
			wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()

	def _save_entries(self) -> None:
		self.dictionary_path.parent.mkdir(parents=True, exist_ok=True)
		with self.dictionary_path.open("w", newline="", encoding="utf-8") as fp:
			writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
			writer.writeheader()
			for entry in self.entries:
				writer.writerow({"text": entry.text, "braille": entry.braille, "type": entry.entry_type})


class DictionaryManagementDialog(wx.Dialog):
	"""Dialog that stages dictionary lifecycle actions through callbacks."""

	def __init__(
		self,
		parent: wx.Window | None,
		dictionary_names: list[str],
		selected_name: str,
		dictionary_dir: Path,
		on_add: Callable[[wx.Window | None], str | None],
		on_delete: Callable[[wx.Window | None, str], str | None],
		on_rename: Callable[[wx.Window | None, str], str | None],
		on_import: Callable[[wx.Window | None], str | None],
		on_export: Callable[[wx.Window | None, str], None],
	):
		super().__init__(
			parent,
			title=_("Dictionary Management"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
		)
		self.dictionary_dir = Path(dictionary_dir)
		self._dictionary_names = list(dictionary_names)
		self._selected_name = selected_name
		self._dictionary_counts: dict[str, int] = {}
		self._on_add = on_add
		self._on_delete = on_delete
		self._on_rename = on_rename
		self._on_import = on_import
		self._on_export = on_export
		self.edit_dictionary_name: str | None = None
		self._build_ui()
		self.refresh_dictionaries(self._dictionary_names, selected_name)

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		self.list_ctrl = CallbackVirtualListCtrl(
			self,
			self._get_item_text,
			style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
		)
		self.list_ctrl.InsertColumn(0, _("Dictionary"))
		self.list_ctrl.InsertColumn(1, _("Entries"))
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_SIZE, self._on_list_size)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 12)

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label=_("Add"))
		self.delete_button = wx.Button(self, label=_("Delete"))
		self.rename_button = wx.Button(self, label=_("Rename"))
		self.edit_button = wx.Button(self, label=_("Edit"))
		self.import_button = wx.Button(self, label=_("Import"))
		self.export_button = wx.Button(self, label=_("Export"))
		for button in (
			self.add_button,
			self.delete_button,
			self.rename_button,
			self.edit_button,
			self.import_button,
			self.export_button,
		):
			button_sizer.Add(button, 0, wx.RIGHT, 8)
		main_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

		button_bar = self.CreateButtonSizer(wx.CLOSE)
		if button_bar:
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

		self.add_button.Bind(wx.EVT_BUTTON, self._on_add_clicked)
		self.delete_button.Bind(wx.EVT_BUTTON, self._on_delete_clicked)
		self.rename_button.Bind(wx.EVT_BUTTON, self._on_rename_clicked)
		self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit)
		self.import_button.Bind(wx.EVT_BUTTON, self._on_import_clicked)
		self.export_button.Bind(wx.EVT_BUTTON, self._on_export_clicked)

		finalize_dialog_layout(self, main_sizer)
		self._resize_columns()

	def _get_item_text(self, item: int, column: int) -> str:
		name = self._dictionary_names[item]
		if column == 0:
			return name
		if column == 1:
			return str(self._dictionary_counts.get(name, 0))
		raise ValueError(f"Unknown column: {column}")

	def _load_dictionary_counts(self) -> None:
		self._dictionary_counts = {
			name: len(load_dictionary_entries(dictionary_path_for_name(name, self.dictionary_dir)))
			for name in self._dictionary_names
		}

	def refresh_dictionaries(
		self,
		dictionary_names: list[str],
		preferred_name: str | None,
	) -> None:
		self._dictionary_names = list(dictionary_names)
		self._load_dictionary_counts()
		self.list_ctrl.SetItemCount(len(self._dictionary_names))
		self.list_ctrl.Refresh()
		selected = resolve_dictionary_selection(self._dictionary_names, preferred_name)
		self._selected_name = selected
		if selected in self._dictionary_names:
			index = self._dictionary_names.index(selected)
			self.list_ctrl.Select(index)
			self.list_ctrl.Focus(index)
		self._resize_columns()
		self._update_button_states()

	def _resize_columns(self) -> None:
		available_width = max(0, self.list_ctrl.GetClientSize().width)
		if available_width == 0:
			return
		count_text_width = self.list_ctrl.GetTextExtent(_("Entries"))[0]
		count_width = min(available_width, max(96, count_text_width + 32))
		name_width = max(0, available_width - count_width)
		self.list_ctrl.SetColumnWidth(0, name_width)
		self.list_ctrl.SetColumnWidth(1, count_width)

	def _on_list_size(self, event: wx.SizeEvent) -> None:
		self._resize_columns()
		event.Skip()

	def _get_selected_name(self) -> str | None:
		index = self.list_ctrl.GetFirstSelected()
		if index == wx.NOT_FOUND:
			return None
		if index >= len(self._dictionary_names):
			return None
		return self._dictionary_names[index]

	def _update_button_states(self) -> None:
		selected_name = self._get_selected_name() or self._selected_name or ""
		availability = get_action_availability(self._dictionary_names, selected_name)
		self.add_button.Enable(True)
		self.import_button.Enable(True)
		self.delete_button.Enable(availability.delete)
		self.rename_button.Enable(availability.rename)
		self.edit_button.Enable(availability.edit)
		self.export_button.Enable(availability.export)

	def _on_selection_changed(self, event: wx.ListEvent) -> None:
		selected_name = self._get_selected_name()
		if selected_name is not None:
			self._selected_name = selected_name
		self._update_button_states()
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
		preferred_name = self._on_add(self)
		if preferred_name is not None:
			self._refresh_from_disk(preferred_name)

	def _on_delete_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._on_delete(self, selected)
			if preferred_name is not None:
				self._refresh_from_disk(preferred_name)

	def _on_rename_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._on_rename(self, selected)
			if preferred_name is not None:
				self._refresh_from_disk(preferred_name)

	def _on_import_clicked(self, _event: wx.CommandEvent) -> None:
		preferred_name = self._on_import(self)
		if preferred_name is not None:
			self._refresh_from_disk(preferred_name)

	def _on_export_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			self._on_export(self, selected)

	def _on_edit(self, _event: wx.Event) -> None:
		selected = self._get_selected_name()
		if selected is None:
			return
		self.edit_dictionary_name = selected
		self.EndModal(wx.ID_EDIT)

	def _refresh_from_disk(self, preferred_name: str | None) -> None:
		self.refresh_dictionaries(list_dictionary_names(self.dictionary_dir), preferred_name)

	def __enter__(self) -> "DictionaryManagementDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()
