from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import gettext
import sys
from typing import List

import wx
from braille.tables import listTables
from Bopomofo import normalize_zhuyin_sequence
from dictionaries.actions import get_action_availability, resolve_dictionary_selection
from dictionaries.manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name
from documents.workspace import normalize_document_name
from translation.settings import MAX_CONVERSION_WIDTH, MIN_CONVERSION_WIDTH, TranslationSettings


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
WINDOWS_FILE_NAME_ERROR = "請輸入有效的 Windows 檔名。"


def _normalize_dialog_name(
	candidate: str,
	normalizer: Callable[[str], str],
	empty_message: str,
	length_message: str,
	reserved_message: str | None = None,
) -> tuple[str | None, str | None]:
	candidate = candidate.strip()
	if not candidate:
		return None, empty_message
	if len(candidate) > MAX_DICTIONARY_NAME_LENGTH:
		return None, length_message
	try:
		return normalizer(candidate), None
	except ValueError as exc:
		if reserved_message and candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
			return None, reserved_message
		if "exceed" in str(exc):
			return None, length_message
		return None, WINDOWS_FILE_NAME_ERROR


@dataclass
class DictionaryEntry:
	text: str
	braille: str
	entry_type: str = DEFAULT_ENTRY_TYPE


@dataclass(frozen=True)
class TableOption:
	file_name: str
	display_name: str


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

		self.SetSizerAndFit(main_sizer)
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

		self.SetSizerAndFit(main_sizer)
		self._apply_initial_name(initial_name)

	def get_dictionary_name(self) -> str:
		return self.name_ctrl.GetValue().strip()

	def _apply_initial_name(self, initial_name: str) -> None:
		self.name_ctrl.SetValue(initial_name)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		candidate = self.get_dictionary_name()
		normalized_candidate, message = _normalize_dialog_name(
			candidate,
			normalize_dictionary_name,
			_("Please enter the dictionary name."),
			_("Dictionary name must be 1 to 32 characters."),
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

		self.SetSizerAndFit(main_sizer)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def get_document_name(self) -> str:
		return self.name_ctrl.GetValue().strip()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		candidate = self.get_document_name()
		normalized_candidate, message = _normalize_dialog_name(
			candidate,
			normalize_document_name,
			_("Please enter the document name."),
			_("Document name must be 1 to 32 characters."),
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
		self.SetSizerAndFit(main_sizer)
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
		self.SetSizerAndFit(main_sizer)
		self.SetMinSize((520, 320))

	def __enter__(self) -> "FileIssuesDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class SpeechSymbolsDialog(wx.Dialog):
	"""Dialog for editing custom dictionary mappings stored on disk."""

	def __init__(self, parent: wx.Window | None, dictionary_path: Path | None = None):
		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
		self.entries: List[DictionaryEntry] = self._load_entries()
		self._build_ui()
		self._populate_list()
		self._update_button_states()

	def __enter__(self) -> "SpeechSymbolsDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		list_label = wx.StaticText(self, label=_("Dictionary entries"))
		main_sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

		self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL)
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

		self.SetSizer(main_sizer)
		self.SetMinSize((560, 440))
		self.Layout()

	def _load_entries(self) -> List[DictionaryEntry]:
		if not self.dictionary_path.exists():
			return []

		entries: List[DictionaryEntry] = []
		with self.dictionary_path.open("r", newline="", encoding="utf-8") as fp:
			reader = csv.DictReader(fp)
			for row in reader:
				text = (row.get("text") or "").strip()
				if not text:
					continue
				braille = (row.get("braille") or "").strip()
				entry_type = self._normalize_type(row.get("type"))
				if entry_type == "Bopomofo":
					try:
						normalize_zhuyin_sequence(braille)
					except Exception:
						continue

				entries.append(DictionaryEntry(text=text, braille=braille, entry_type=entry_type))
		return entries

	def _populate_list(self) -> None:
		self.list_ctrl.DeleteAllItems()
		for entry in self.entries:
			index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), entry.text)
			self.list_ctrl.SetItem(index, 1, entry.braille)
			self.list_ctrl.SetItem(index, 2, ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type))

	def _update_button_states(self) -> None:
		has_selection = self.list_ctrl.GetFirstSelected() != wx.NOT_FOUND
		self.edit_button.Enable(has_selection)
		self.remove_button.Enable(has_selection)

	def _get_selected_index(self) -> int | None:
		index = self.list_ctrl.GetFirstSelected()
		return index if index != wx.NOT_FOUND else None

	def _select_index(self, index: int) -> None:
		if index < 0 or index >= self.list_ctrl.GetItemCount():
			return
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
		self._populate_list()
		self._select_index(len(self.entries) - 1)

	def _on_edit_clicked(self, _event: wx.CommandEvent) -> None:
		self._edit_selected()

	def _edit_selected(self) -> None:
		index = self._get_selected_index()
		if index is None:
			return
		current_entry = self.entries[index]
		updated_entry = self._open_entry_dialog(current_entry)
		if updated_entry is None:
			return
		if self._identifier_exists(updated_entry.text, exclude_index=index):
			wx.MessageBox(
				_('Source text "{identifier}" already exists.').format(identifier=updated_entry.text),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		self.entries[index] = updated_entry
		self._populate_list()
		self._select_index(index)

	def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
		index = self._get_selected_index()
		if index is None:
			return
		del self.entries[index]
		self._populate_list()
		if self.entries:
			self._select_index(min(index, len(self.entries) - 1))
		else:
			self._update_button_states()

	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
		with AddSymbolDialog(self, entry) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_entry()

	def _identifier_exists(self, identifier: str, exclude_index: int | None = None) -> bool:
		return any(entry.text == identifier and idx != exclude_index for idx, entry in enumerate(self.entries))

	def _normalize_type(self, entry_type: str | None) -> str:
		if entry_type in ENTRY_TYPE_LABELS:
			return str(entry_type)
		return DEFAULT_ENTRY_TYPE

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


class TranslationSettingsDialog(wx.Dialog):
	"""Dialog that stages translation settings changes."""

	_OUTPUT_MODES: list[tuple[str, str]] = [
		("unicode", _("Unicode")),
		("ascii", _("ASCII")),
	]

	def __init__(
		self,
		parent: wx.Window | None,
		settings: TranslationSettings,
		dictionary_names: list[str],
	):
		super().__init__(parent, title=_("Translation Settings"))
		self._initial_settings = settings
		self._dictionary_names = list(dictionary_names)

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(3, 2, 8, 8)

		output_label = wx.StaticText(self, label=_("Braille Type"))
		self.output_choice = wx.Choice(self, choices=[label for _key, label in self._OUTPUT_MODES])
		grid.Add(output_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.output_choice, 1, wx.EXPAND)

		width_label = wx.StaticText(self, label=_("Width"))
		self.width_spin = wx.SpinCtrl(
			self,
			min=MIN_CONVERSION_WIDTH,
			max=MAX_CONVERSION_WIDTH,
			initial=max(MIN_CONVERSION_WIDTH, min(MAX_CONVERSION_WIDTH, settings.width)),
		)
		grid.Add(width_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.width_spin, 1, wx.EXPAND)

		dictionary_label = wx.StaticText(self, label=_("Dictionary"))
		self.dictionary_choice = wx.Choice(self, choices=self._dictionary_names)
		grid.Add(dictionary_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.dictionary_choice, 1, wx.EXPAND)
		grid.AddGrowableCol(1, 1)

		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

		self.SetSizerAndFit(main_sizer)
		self._select_output_mode(settings.output_mode)
		self._select_dictionary(settings.selected_dictionary)

	def get_settings(self) -> TranslationSettings:
		output_index = self.output_choice.GetSelection()
		dictionary_index = self.dictionary_choice.GetSelection()
		output_mode = (
			self._OUTPUT_MODES[output_index][0]
			if output_index != wx.NOT_FOUND
			else self._initial_settings.output_mode
		)
		selected_dictionary = (
			self._dictionary_names[dictionary_index]
			if dictionary_index != wx.NOT_FOUND and self._dictionary_names
			else self._initial_settings.selected_dictionary
		)
		return TranslationSettings(
			output_mode=output_mode,
			width=self.width_spin.GetValue(),
			selected_dictionary=selected_dictionary,
		)

	def _select_output_mode(self, output_mode: str) -> None:
		index = next((idx for idx, (key, _label) in enumerate(self._OUTPUT_MODES) if key == output_mode), 0)
		self.output_choice.SetSelection(index)

	def _select_dictionary(self, dictionary_name: str) -> None:
		if not self._dictionary_names:
			self.dictionary_choice.SetSelection(wx.NOT_FOUND)
			self.dictionary_choice.Disable()
			return

		index = next((idx for idx, name in enumerate(self._dictionary_names) if name == dictionary_name), 0)
		self.dictionary_choice.SetSelection(index)

	def __enter__(self) -> "TranslationSettingsDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class DictionaryManagementDialog(wx.Dialog):
	"""Dialog that stages dictionary lifecycle actions through callbacks."""

	def __init__(
		self,
		parent: wx.Window | None,
		dictionary_names: list[str],
		selected_name: str,
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
		self._dictionary_names = dictionary_names
		self._selected_name = selected_name
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
		self.list_ctrl = wx.ListCtrl(
			self,
			style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL,
		)
		self.list_ctrl.InsertColumn(0, _("Dictionary"), width=360)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)
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

		self.SetSizer(main_sizer)
		self.SetMinSize((650, 400))
		self.Layout()

	def refresh_dictionaries(
		self,
		dictionary_names: list[str],
		preferred_name: str | None,
	) -> None:
		self._dictionary_names = dictionary_names
		self.list_ctrl.DeleteAllItems()
		for name in self._dictionary_names:
			self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), name)
		selected = resolve_dictionary_selection(self._dictionary_names, preferred_name)
		self._selected_name = selected
		if selected in self._dictionary_names:
			index = self._dictionary_names.index(selected)
			self.list_ctrl.Select(index)
			self.list_ctrl.Focus(index)
		self._update_button_states()

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
			self.refresh_dictionaries(self._dictionary_names, preferred_name)

	def _on_delete_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._on_delete(self, selected)
			if preferred_name is not None:
				self.refresh_dictionaries(self._dictionary_names, preferred_name)

	def _on_rename_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._on_rename(self, selected)
			if preferred_name is not None:
				self.refresh_dictionaries(self._dictionary_names, preferred_name)

	def _on_import_clicked(self, _event: wx.CommandEvent) -> None:
		preferred_name = self._on_import(self)
		if preferred_name is not None:
			self.refresh_dictionaries(self._dictionary_names, preferred_name)

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

	def __enter__(self) -> "DictionaryManagementDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class TranslationTableDialog(wx.Dialog):
	"""Dialog that allows configuring translation tables for each supported language."""

	_CHOICE_SPECS = [
		("default", _("Default Translation Table"), None),
		("en", _("English Translation Table"), "en"),
		("zh", _("Chinese Translation Table"), "zh"),
		("ja", _("Japanese Translation Table"), "ja"),
		("math", _("Math Translation Table"), None),
	]

	def __init__(self, parent: wx.Window | None, language_map: dict[str, str]):
		super().__init__(parent, title=_("Translation Tables Setting"))
		self.language_map = language_map
		self.table_options: List[TableOption] = self._load_table_options()
		self._choice_controls: dict[str, wx.Choice] = {}
		self._options_by_key: dict[str, List[TableOption]] = {}
		self._build_ui()
		self._apply_initial_selection()

	def get_selected_tables(self) -> dict[str, str]:
		results: dict[str, str] = {}
		for key, _label, _lang_code in self._CHOICE_SPECS:
			option = self._get_selected_option(key)
			if option:
				results[key] = option.file_name
		return results

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(len(self._CHOICE_SPECS), 2, 8, 8)

		for key, label, lang_code in self._CHOICE_SPECS:
			static_lbl = wx.StaticText(self, label=label)
			options = self._options_for_key(key, lang_code)
			if key not in {"default", "math"}:
				options = [TableOption(file_name="", display_name=_("None selected"))] + options
			choice = wx.Choice(self)
			choice.AppendItems([option.display_name for option in options])
			self._choice_controls[key] = choice
			self._options_by_key[key] = options

			grid.Add(static_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
			grid.Add(choice, 1, wx.EXPAND)

			if not options:
				choice.Disable()

		grid.AddGrowableCol(1, 1)
		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

		self.SetSizerAndFit(main_sizer)

	def _apply_initial_selection(self) -> None:
		for key, _label, _code in self._CHOICE_SPECS:
			self._select_choice_value(key, self.language_map.get(key))

	def _select_choice_value(self, key: str, file_name: str | None) -> None:
		choice = self._choice_controls[key]
		options = self._options_by_key[key]
		if not options:
			choice.SetSelection(wx.NOT_FOUND)
			return

		index = next((idx for idx, option in enumerate(options) if option.file_name == file_name), None)
		if index is None:
			index = 0
		choice.SetSelection(index)

	def _get_selected_option(self, key: str) -> TableOption | None:
		choice = self._choice_controls.get(key)
		if not choice:
			return None
		selection = choice.GetSelection()
		if selection == wx.NOT_FOUND:
			return None
		options = self._options_by_key.get(key, [])
		if selection >= len(options):
			return None
		return options[selection]

	def _options_for_lang(self, lang_code: str | None) -> List[TableOption]:
		if lang_code is None:
			return self.table_options
		prefix = lang_code.lower()
		return [option for option in self.table_options if option.file_name.lower().startswith(prefix)]

	def _options_for_key(self, key: str, lang_code: str | None) -> List[TableOption]:
		if key == "math":
			return [
				TableOption(file_name="UEB", display_name="UEB"),
				TableOption(file_name="Nemeth", display_name="Nemeth"),
			]
		return self._options_for_lang(lang_code)

	def _load_table_options(self) -> List[TableOption]:
		tables = [table for table in listTables() if getattr(table, "output", False)]
		options = [
			TableOption(
				file_name=table.fileName,
				display_name=_(table.displayName),
			)
			for table in tables
		]
		return sorted(options, key=lambda option: option.display_name.lower())

	def __enter__(self) -> "TranslationTableDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()
