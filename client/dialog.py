from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx
from dictionaries.actions import get_action_availability, resolve_dictionary_selection
from dictionaries.entries import (
	DEFAULT_ENTRY_TYPE,
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	validate_dictionary_entry,
)
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
from dictionaries.manager import (
	DEFAULT_DICTIONARY_NAME,
	normalize_dictionary_name,
)
from dictionaries.presenter import DictionaryManagementActions
from dictionaries.read_problems import (
	DictionaryCount,
	describe_dictionary_read_error,
	describe_unreadable_dictionary,
	read_dictionary_count,
)
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")


def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
	dialog.SetSizerAndFit(sizer)
	if dialog.GetParent() is not None:
		dialog.CentreOnParent()
	else:
		dialog.Centre()


def localize_standard_buttons(
	dialog: wx.Dialog,
	flags: int,
	button_sizer: wx.StdDialogButtonSizer | None = None,
) -> None:
	"""Apply application translations to wxPython's standard dialog buttons.

	Only the dialog's own children are searched (F-W9): a search of every top-level
	window could find another dialog's button with the same id and relabel that one.
	"""
	button_labels = (
		(wx.OK, wx.ID_OK, _("OK"), "GetAffirmativeButton"),
		(wx.CANCEL, wx.ID_CANCEL, _("Cancel"), "GetCancelButton"),
		(wx.APPLY, wx.ID_APPLY, _("Apply"), "GetApplyButton"),
		(wx.CLOSE, wx.ID_CLOSE, _("Close"), "GetCloseButton"),
	)
	for flag, button_id, label, sizer_button_getter in button_labels:
		if flags & flag:
			button = dialog.FindWindow(button_id)
			if button is None and button_sizer is not None:
				getter = getattr(button_sizer, sizer_button_getter, None)
				if getter is not None:
					button = getter()
			if button is not None:
				button.SetLabel(label)


class AddSymbolDialog(ContextManagedDialog, wx.Dialog):
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

		button_sizer = wx.StdDialogButtonSizer()
		ok_button = wx.Button(self, wx.ID_OK, _("OK"))
		cancel_button = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
		button_sizer.AddButton(ok_button)
		button_sizer.AddButton(cancel_button)
		button_sizer.Realize()
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
			entry = self.get_entry()
		except RuntimeError:
			event.Skip()
			return

		try:
			validate_dictionary_entry(entry)
		except ValueError as exc:
			message_box(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			try:
				if not entry.text:
					self.identifier_ctrl.SetFocus()
				else:
					self.braille_ctrl.SetFocus()
			except RuntimeError:
				pass
			return

		event.Skip()


class _NameDialog(NameDialogBase, wx.Dialog):
	"""Name dialog base: shows a name error in an information message box."""

	def _show_name_error(self, message: str) -> None:
		message_box(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)


class DictionaryNameDialog(_NameDialog):
	"""Dialog for creating a new dictionary file name."""

	normalize_name = staticmethod(normalize_dictionary_name)
	name_messages = NameDialogMessages(
		empty=N_("Please enter the dictionary name."),
		too_long=N_("Dictionary name must be 1 to 32 characters."),
		invalid=N_("Dictionary name is not a valid Windows file name."),
		reserved=N_('Dictionary name "{name}" is reserved.'),
		reserved_name=DEFAULT_DICTIONARY_NAME,
	)

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
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_sizer)
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


class DocumentNameDialog(_NameDialog):
	"""Dialog for creating or renaming a document."""

	normalize_name = staticmethod(normalize_document_name)
	name_messages = NameDialogMessages(
		empty=N_("Please enter the document name."),
		too_long=N_("Document name must be 1 to 32 characters."),
		invalid=N_("Document name is not a valid Windows file name."),
	)

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
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_sizer)
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

		finalize_dialog_layout(self, main_sizer)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def get_document_name(self) -> str:
		return self.name_ctrl.GetValue().strip()


class InvalidWorkspaceFilesDialog(ContextManagedDialog, wx.Dialog):
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


class FileIssuesDialog(ContextManagedDialog, wx.Dialog):
	"""Dialog shown when a batch operation skips one or more files."""

	def __init__(self, parent: wx.Window | None, title: str, message: str, issues: list[str]):
		super().__init__(parent, title=title)
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(wx.StaticText(self, label=message), 0, wx.EXPAND | wx.ALL, 12)
		self.list_box = wx.ListBox(self, choices=issues)
		main_sizer.Add(self.list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		button_sizer = self.CreateButtonSizer(wx.OK)
		if button_sizer:
			localize_standard_buttons(self, wx.OK, button_sizer)
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		finalize_dialog_layout(self, main_sizer)
		self.SetMinSize((520, 320))


class ConvertingDialog(wx.Dialog):
	def __init__(self, parent: wx.Window):
		style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP
		super().__init__(parent, title=_("Info"), style=style)

		message = wx.StaticText(self, label=_("converting"))
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(message, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 20)
		finalize_dialog_layout(self, sizer)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _on_close(self, evt: wx.CloseEvent):
		if evt.CanVeto():
			evt.Veto()


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


class DictionaryEntriesDialog(ContextManagedDialog, wx.Dialog):
	"""Dialog for editing custom dictionary mappings stored on disk.

	Supervising controller: the widgets and the selected row live here, the
	entries and the filter in ``DictionaryEntryListModel``.
	"""

	def __init__(self, parent: wx.Window | None, dictionary_path: Path):
		super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = Path(dictionary_path)
		self._model = DictionaryEntryListModel.load(self.dictionary_path)
		self._build_ui()
		self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
		self._update_button_states()

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
			self._model.cell_text,
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
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_bar)
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
			ok_button = self.FindWindow(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

		finalize_dialog_layout(self, main_sizer)

	def _render(self, update: EntryListUpdate) -> None:
		self.list_ctrl.SetItemCount(self._model.visible_count)
		self.list_ctrl.Refresh()
		if update.selection is None:
			self._clear_selection()
			self._update_button_states()
			return
		self._select_index(update.selection)

	def _on_filter_changed(self, event: wx.CommandEvent) -> None:
		self._render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))
		event.Skip()

	def _update_button_states(self) -> None:
		has_selection = self._get_selected_index() is not None
		self.edit_button.Enable(has_selection)
		self.remove_button.Enable(has_selection)

	def _get_selected_index(self) -> int | None:
		index = self.list_ctrl.GetFirstSelected()
		if index == wx.NOT_FOUND or index < 0 or index >= self._model.visible_count:
			return None
		return index

	def _clear_selection(self) -> None:
		index = self.list_ctrl.GetFirstSelected()
		if index != wx.NOT_FOUND:
			self.list_ctrl.Select(index, False)

	def _select_index(self, index: int) -> None:
		if index < 0 or index >= self._model.visible_count:
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
		try:
			update = self._model.add(new_entry)
		except DuplicateEntryError as error:
			self._show_duplicate_error(error.identifier)
			return
		if update.filter_cleared:
			self.filter_ctrl.ChangeValue("")
		self._render(update)

	def _on_edit_clicked(self, _event: wx.CommandEvent) -> None:
		self._edit_selected()

	def _edit_selected(self) -> None:
		visible_index = self._get_selected_index()
		current_entry = self._model.visible_entry(visible_index)
		if visible_index is None or current_entry is None:
			return
		updated_entry = self._open_entry_dialog(current_entry)
		if updated_entry is None:
			return
		try:
			update = self._model.replace(visible_index, updated_entry)
		except DuplicateEntryError as error:
			self._show_duplicate_error(error.identifier)
			return
		self._render(update)

	def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
		visible_index = self._get_selected_index()
		if visible_index is None:
			return
		self._render(self._model.remove(visible_index))

	def _open_entry_dialog(self, entry: DictionaryEntry | None = None) -> DictionaryEntry | None:
		with AddSymbolDialog(self, entry) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_entry()

	def _show_duplicate_error(self, identifier: str) -> None:
		message_box(
			_('Source text "{identifier}" already exists.').format(identifier=identifier),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=self,
		)

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
			self._model.save(self.dictionary_path)
		except Exception as exc:
			message_box(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()


class DictionaryManagementDialog(ContextManagedDialog, wx.Dialog):
	"""Passive view of dictionary management: runs ``actions`` and implements ``DictionaryManagementView``."""

	def __init__(
		self,
		parent: wx.Window | None,
		actions: DictionaryManagementActions,
		selected_name: str,
	):
		super().__init__(
			parent,
			title=_("Dictionary Management"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
		)
		self._actions = actions
		self._dictionary_names = list(actions.dictionary_names)
		self._selected_name = selected_name
		self._dictionary_counts: dict[str, int] = {}
		# F-6: the dictionaries that could not be read, with the error (their count is not known).
		self._dictionary_read_errors: dict[str, Exception] = {}
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

		# F-6 (D3): why the selected dictionary cannot be read. Created right after the list, so
		# it is the next Tab stop and the label is the field's accessible name. Multi-line,
		# because wxMSW leaves a read-only single-line field out of the Tab order. Hidden
		# before the layout is fitted, so the dialog keeps its size; shown only while a
		# dictionary that cannot be read is selected.
		self.read_problem_label = wx.StaticText(self, label=_("Why this dictionary cannot be read:"))
		self.read_problem_ctrl = wx.TextCtrl(
			self,
			style=wx.TE_MULTILINE | wx.TE_READONLY,
			size=(-1, self.GetCharHeight() * 4),
		)
		main_sizer.Add(self.read_problem_label, 0, wx.LEFT | wx.RIGHT, 12)
		main_sizer.Add(self.read_problem_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		self.read_problem_label.Hide()
		self.read_problem_ctrl.Hide()
		self.read_problem_ctrl.Bind(wx.EVT_SET_FOCUS, self._on_read_problem_focus)

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
			localize_standard_buttons(self, wx.CLOSE, button_bar)
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
			if name in self._dictionary_read_errors:
				return _("Unreadable")
			return str(self._dictionary_counts.get(name, 0))
		raise ValueError(f"Unknown column: {column}")

	def _load_dictionary_counts(self) -> None:
		"""Read every dictionary on its own; one that cannot be read is kept with its error (F-6)."""
		self._dictionary_counts = {}
		self._dictionary_read_errors = {}
		for name in self._dictionary_names:
			self._store_count(name, read_dictionary_count(self._actions.dictionary_path(name)))

	def _store_count(self, name: str, count: DictionaryCount) -> None:
		if count.error is None:
			self._dictionary_counts[name] = count.entries
			self._dictionary_read_errors.pop(name, None)
		else:
			self._dictionary_counts.pop(name, None)
			self._dictionary_read_errors[name] = count.error

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
		self._update_read_problem()

	def _update_read_problem(self) -> None:
		"""Show why the selected dictionary cannot be read, or hide the reason row (F-6 D3).

		The text is selected, so a screen reader reads all of it when the field gets focus,
		not only its first line.
		"""
		error = self._dictionary_read_errors.get(self._get_selected_name())
		if error is None:
			self.read_problem_ctrl.ChangeValue("")
		else:
			self.read_problem_ctrl.ChangeValue(describe_dictionary_read_error(error))
			self.read_problem_ctrl.SelectAll()
		self.read_problem_label.Show(error is not None)
		self.read_problem_ctrl.Show(error is not None)
		self.Layout()

	def _on_read_problem_focus(self, event: wx.FocusEvent) -> None:
		# Select all again, so the reason is read in full after an arrow key moved the caret.
		self.read_problem_ctrl.SelectAll()
		event.Skip()

	def _resize_columns(self) -> None:
		available_width = max(0, self.list_ctrl.GetClientSize().width)
		if available_width == 0:
			return
		count_text_width = max(self.list_ctrl.GetTextExtent(label)[0] for label in (_("Entries"), _("Unreadable")))
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
		self._update_read_problem()
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
		preferred_name = self._actions.add(self)
		if preferred_name is not None:
			self._refresh_from_actions(preferred_name)

	def _on_delete_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._actions.delete(self, selected)
			if preferred_name is not None:
				self._refresh_from_actions(preferred_name)

	def _on_rename_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			preferred_name = self._actions.rename(self, selected)
			if preferred_name is not None:
				self._refresh_from_actions(preferred_name)

	def _on_import_clicked(self, _event: wx.CommandEvent) -> None:
		preferred_name = self._actions.import_from_file(self)
		if preferred_name is not None:
			self._refresh_from_actions(preferred_name)

	def _on_export_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			self._actions.export_to_file(self, selected)

	def _on_edit(self, _event: wx.Event) -> None:
		selected = self._get_selected_name()
		if selected is None:
			return
		# F-6 (D5): read the file again. A file fixed meanwhile opens; one that cannot be read
		# is explained here, and the dialog stays open.
		count = read_dictionary_count(self._actions.dictionary_path(selected))
		self._store_count(selected, count)
		self.list_ctrl.Refresh()
		self._update_read_problem()
		if count.error is not None:
			self.show_error(describe_unreadable_dictionary(selected, count.error))
			return
		self.edit_dictionary_name = selected
		self.EndModal(wx.ID_EDIT)

	def _refresh_from_actions(self, preferred_name: str | None) -> None:
		self.refresh_dictionaries(self._actions.dictionary_names, preferred_name)

	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None:
		with DictionaryNameDialog(self, initial_name=initial_name) as name_dialog:
			name_dialog.SetTitle(title)
			if name_dialog.ShowModal() != wx.ID_OK:
				return None
			return name_dialog.get_dictionary_name()

	def show_info(self, message: str) -> None:
		message_box(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str) -> None:
		message_box(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)

	def confirm(self, message: str, caption: str) -> bool:
		return message_box(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES

	def choose_import_path(self, title: str) -> Path | None:
		with wx.FileDialog(
			self,
			title,
			wildcard=_(CSV_WILDCARD),
			style=wx.FD_OPEN,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())

	def choose_export_path(self, title: str, default_file: str) -> Path | None:
		with wx.FileDialog(
			self,
			title,
			defaultFile=default_file,
			wildcard=_(CSV_WILDCARD),
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())
