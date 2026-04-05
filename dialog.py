from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import gettext
import sys
from typing import List

import wx
from brailleTables import listTables
from Bopomofo import normalize_zhuyin_sequence
from dictionary_manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name


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

	def __init__(self, parent: wx.Window | None):
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
		self.name_ctrl.SetFocus()

	def get_dictionary_name(self) -> str:
		return self.name_ctrl.GetValue().strip()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		candidate = self.get_dictionary_name()
		message = self._validate_name(candidate)
		if message:
			wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			self.name_ctrl.SetFocus()
			return
		self.name_ctrl.SetValue(normalize_dictionary_name(candidate))
		event.Skip()

	def _validate_name(self, candidate: str) -> str | None:
		if not candidate:
			return _("Please enter the dictionary name.")
		if len(candidate) > MAX_DICTIONARY_NAME_LENGTH:
			return _("Dictionary name must be 1 to 16 characters.")
		if any(char in candidate for char in (".", "/", "\\")):
			return _('Dictionary name cannot contain ".", "/", or "\\".')
		if candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
			return _('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME)
		return None

	def __enter__(self) -> "DictionaryNameDialog":
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


class TranslationTableDialog(wx.Dialog):
	"""Dialog that allows configuring translation tables for each supported language."""

	_CHOICE_SPECS = [
		("default", _("Default Translation Table"), None),
		("en", _("English Translation Table"), "en"),
		("zh", _("Chinese Translation Table"), "zh"),
		("ja", _("Japanese Translation Table"), "ja"),
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
			options = self._options_for_lang(lang_code)
			if key != "default":
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

	def _load_table_options(self) -> List[TableOption]:
		tables = [table for table in listTables() if getattr(table, "output", False)]
		options = [
			TableOption(
				file_name=table.fileName,
				display_name=table.displayName,
			)
			for table in tables
		]
		return sorted(options, key=lambda option: option.display_name.lower())

	def __enter__(self) -> "TranslationTableDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()
