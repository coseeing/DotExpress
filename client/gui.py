from pathlib import Path
import gettext
import sys
import threading
import webbrowser

import wx

import about
from braille import louis_helper
from conversion.service import ConversionRequest, ConversionStageError, convert_text_for_output, get_public_error_message
from dictionaries.actions import is_default_dictionary
from dictionaries.manager import (
	create_dictionary,
	delete_dictionary,
	dictionary_path_for_name,
	ensure_default_dictionary,
	export_dictionary,
	get_dictionary_directory,
	import_dictionary,
	list_dictionary_names,
	rename_dictionary,
)
from documents.session import (
	document_name_exists,
	find_document,
	get_document_names,
	plan_delete_document,
	plan_open_document,
	rename_document_in_list,
	replace_document,
)
from documents.workspace import (
	BatchIssue,
	DEFAULT_DOCUMENT_NAME,
	Document,
	batch_export_documents_to_folder,
	batch_import_documents,
	create_default_document,
	document_package_path_for_name,
	ensure_workspace_directory,
	export_document_brl,
	get_workspace_directory,
	load_workspace_documents,
	normalize_document_name,
	prepare_document_for_save,
	save_document_package,
)
from ui.action_menu import (
	get_document_export_format_labels,
	get_document_import_format_labels,
	get_document_menu_enabled_state,
	get_document_menu_items,
)
from config import (
	DEFAULT_TRANSLATION_TABLES,
	DEFAULT_VIEW_FONT_SIZE,
	DEFAULT_VIEW_SCHEME,
	DEFAULT_BRAILLE_FONT,
	get_braille_font,
	get_translation_tables,
	get_view_font_size,
	get_view_scheme,
	set_selected_dictionary,
	set_translation_tables,
	set_view_font_size,
	set_view_scheme,
	set_braille_font,
)
from translation.settings import (
	TranslationSettings,
	load_translation_settings,
	normalize_translation_settings,
	save_translation_settings,
)
from translation.dictionary_state import (
	plan_dictionary_state_after_add,
	plan_dictionary_state_after_delete,
	plan_dictionary_state_after_rename,
	resolve_management_selection,
)
from ui.font_support import SIMBRAILLE_FACE_NAME, get_simbraille_font_path, register_private_font_for_windows
from ui.shortcuts import (
	get_font_size_step_from_wheel,
	is_brl_export_shortcut,
	is_convert_shortcut,
	is_document_delete_shortcut,
	is_document_import_txt_shortcut,
	is_document_rename_shortcut,
	is_section_navigation_shortcut,
)
from ui.section_navigation import (
	BRAILLE_RESULT_SECTION,
	DOCUMENT_LIST_SECTION,
	SOURCE_TEXT_SECTION,
	VIEW_SECTION,
	get_adjacent_section,
)
from ui.translation_menu import get_translation_menu_items
from client_init import start_client_init_background

from dialog import (
	DictionaryManagementDialog,
	DictionaryNameDialog,
	DocumentNameDialog,
	FileIssuesDialog,
	InvalidWorkspaceFilesDialog,
	SpeechSymbolsDialog,
	TranslationSettingsDialog,
	TranslationTableDialog,
)


VIEW_FONT_SIZE_MIN = 8
VIEW_FONT_SIZE_MAX = 48
VIEW_SCHEMES = {
	"light": {
		"background": wx.Colour(255, 255, 255),
		"foreground": wx.Colour(0, 0, 0),
	},
	"dark": {
		"background": wx.Colour(0, 0, 0),
		"foreground": wx.Colour(255, 255, 255),
	},
}
CSV_WILDCARD = "CSV files (*.csv)|*.csv"
DEP_WILDCARD = "DotExpress files (*.dep)|*.dep"
TXT_WILDCARD = "Text files (*.txt)|*.txt"
BRL_WILDCARD = "Braille files (*.brl)|*.brl"


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

# Keep dynamic context-menu labels discoverable to gettext extraction.
_MENU_TRANSLATION_MARKERS = (
	_("Add"),
	_("Edit"),
	_("Delete"),
	_("Import"),
	_("Export"),
	_("Open"),
	_("Rename"),
	_("Default"),
	_("Braille Font"),
	_("SimBraille"),
	_("Export All"),
	_("DEP"),
	_("TXT"),
	_("BRL"),
	_("Delete All"),
	_("Translation"),
	_("Convert"),
	_("Translation Settings..."),
	_("Translation Tables Setting..."),
	_("Dictionary Management..."),
	_("Confirm Delete Dictionary"),
	_("Do you want to delete dictionary \"{name}\"?"),
	_("Rename Dictionary"),
	_("Help"),
	_("Coseeing Website"),
	_("About DotExpress"),
)

language_map_translate_table = get_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()


class ConvertingDialog(wx.Dialog):
	def __init__(self, parent: wx.Window):
		style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP
		super().__init__(parent, title=_("Info"), style=style)

		message = wx.StaticText(self, label=_("converting"))
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(message, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 20)
		self.SetSizerAndFit(sizer)
		self.CentreOnParent()
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _on_close(self, evt: wx.CloseEvent):
		if evt.CanVeto():
			evt.Veto()


class NamedControlAccessible(wx.Accessible):
	def __init__(self, window: wx.Window, name: str, description: str = ""):
		super().__init__(window)
		self._name = name
		self._description = description

	def GetName(self, childId):
		return (wx.ACC_OK, self._name)

	def GetDescription(self, childId):
		return (wx.ACC_OK, self._description)


class BrailleFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._initialize_frame()
		initial_settings = self._initialize_state()
		self._create_main_layout(initial_settings)
		self._initialize_conversion_state()
		self._apply_initial_settings(initial_settings)
		self._bind_events()
		self._load_startup_documents()

	def _initialize_frame(self) -> None:
		self.SetTitle(_("DotExpress"))
		self.SetSize((900, 600))
		self.SetMenuBar(self._create_menu_bar())

	def _initialize_state(self) -> dict[str, str | int]:
		self.dictionary_dir = get_dictionary_directory()
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names = list_dictionary_names(self.dictionary_dir)
		self.translation_settings = load_translation_settings(self._dictionary_names)
		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		self.workspace_dir = get_workspace_directory()
		self.documents: list[Document] = []
		self._simbraille_font_available = self._register_output_font()
		self._selected_document_name: str | None = None
		self._open_document_name: str | None = None

		self._view_schemes = [("light", _("Light")), ("dark", _("Dark"))]
		self._braille_font_options = [("default", _("Default")), ("simbraille", _("SimBraille"))]

		return {
			"font_size": self._clamp_view_font_size(get_view_font_size(DEFAULT_VIEW_FONT_SIZE)),
			"scheme": self._normalize_view_scheme(get_view_scheme(DEFAULT_VIEW_SCHEME)),
			"braille_font": self._normalize_braille_font(get_braille_font(DEFAULT_BRAILLE_FONT)),
		}

	def _create_main_layout(self, initial_settings: dict[str, str | int]) -> None:
		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		content_box = wx.BoxSizer(wx.HORIZONTAL)
		content_box.Add(self._create_document_list(panel), 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 8)
		content_box.Add(self._create_editor_area(panel, int(initial_settings["font_size"])), 1, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 8)
		vbox.Add(content_box, 1, wx.EXPAND)

		panel.SetSizer(vbox)

	def _create_document_list(self, panel: wx.Window) -> wx.BoxSizer:
		documents_box = wx.BoxSizer(wx.VERTICAL)
		documents_label = wx.StaticText(panel, label=_("Documents"))
		self.document_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL)
		self.document_list.InsertColumn(0, _("Document Name"), width=220)
		self.document_list.SetMinSize((240, -1))
		self._set_control_accessible_name(
			self.document_list,
			_("Document List"),
			_("Press the Applications key to open the menu."),
		)
		documents_box.Add(documents_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		documents_box.Add(self.document_list, 1, wx.EXPAND | wx.ALL, 8)
		return documents_box

	def _create_editor_area(self, panel: wx.Window, initial_font_size: int) -> wx.BoxSizer:
		view_group, view_box, view_row = self._create_labeled_group(panel, _("View"))
		font_size_lbl = wx.StaticText(view_box, label=_("Font Size"))
		self.font_size_spin = wx.SpinCtrl(
			view_box,
			min=VIEW_FONT_SIZE_MIN,
			max=VIEW_FONT_SIZE_MAX,
			initial=initial_font_size,
		)
		scheme_lbl = wx.StaticText(view_box, label=_("Scheme"))
		self.scheme_choice = wx.Choice(view_box, choices=[label for _, label in self._view_schemes])
		braille_font_lbl = wx.StaticText(view_box, label=_("Braille Font"))
		self.braille_font_choice = wx.Choice(view_box, choices=[label for _, label in self._braille_font_options])

		view_row.Add(font_size_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.font_size_spin, 0, wx.RIGHT, 12)
		view_row.Add(scheme_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.scheme_choice, 0, wx.RIGHT, 12)
		view_row.Add(braille_font_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.braille_font_choice, 0)
		view_row.AddStretchSpacer()

		editors_box = wx.BoxSizer(wx.VERTICAL)
		editors_box.Add(view_group, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
		self.input_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		self._set_control_accessible_name(self.input_txt, _("Source Text"))
		editors_box.Add(self.input_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		self.output_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
		self._default_output_font = self.output_txt.GetFont()
		self._set_control_accessible_name(self.output_txt, _("Braille Result"))
		editors_box.Add(self.output_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
		return editors_box

	def _initialize_conversion_state(self) -> None:
		self._convert_thread = None
		self._convert_dialog = None
		self._convert_dialog_timer = None
		self._convert_job_id = 0

	def _apply_initial_settings(self, initial_settings: dict[str, str | int]) -> None:
		initial_font_size = int(initial_settings["font_size"])
		initial_scheme = str(initial_settings["scheme"])
		initial_braille_font = str(initial_settings["braille_font"])

		self._set_scheme_selection(initial_scheme)
		self._set_braille_font_selection(initial_braille_font)
		self.font_size_spin.SetValue(initial_font_size)
		self._apply_editor_view_settings(initial_font_size, initial_scheme)

	def _bind_events(self) -> None:
		self.font_size_spin.Bind(wx.EVT_SPINCTRL, self.on_font_size_change)
		self.font_size_spin.Bind(wx.EVT_TEXT, self.on_font_size_change)
		self.scheme_choice.Bind(wx.EVT_CHOICE, self.on_scheme_change)
		self.braille_font_choice.Bind(wx.EVT_CHOICE, self.on_braille_font_change)
		self.input_txt.Bind(wx.EVT_KEY_DOWN, self.on_input_text_key_down)
		self.input_txt.Bind(wx.EVT_MOUSEWHEEL, self.on_editor_mousewheel)
		self.output_txt.Bind(wx.EVT_KEY_DOWN, self.on_output_text_key_down)
		self.output_txt.Bind(wx.EVT_MOUSEWHEEL, self.on_editor_mousewheel)
		self.document_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_document_selection_changed)
		self.document_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_document_selection_changed)
		self.document_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_document_activated)
		self.document_list.Bind(wx.EVT_KEY_DOWN, self.on_document_list_key_down)
		self.document_list.Bind(wx.EVT_CONTEXT_MENU, self.on_document_context_menu)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _load_startup_documents(self) -> None:
		self._clear_document_editors()
		self._load_workspace_documents_at_startup()
		self.input_txt.SetFocus()

	def _create_menu_bar(self) -> wx.MenuBar:
		menu_bar = wx.MenuBar()
		file_menu, self._document_menu_items = self._create_document_menu()
		menu_bar.Append(file_menu, _("File"))

		translation_menu = wx.Menu()
		translation_handlers = {
			"convert": self.on_convert,
			"settings": self.on_open_translation_settings,
			"tables": self.on_open_table_dialog,
			"dictionaries": self.on_open_dictionary_management,
		}
		for key, label in get_translation_menu_items():
			item = translation_menu.Append(wx.ID_ANY, _(label))
			self.Bind(wx.EVT_MENU, translation_handlers[key], item)
		menu_bar.Append(translation_menu, _("Translation"))

		help_menu = wx.Menu()

		website_item = help_menu.Append(wx.ID_ANY, _("Coseeing Website"))
		self.Bind(wx.EVT_MENU, self.on_open_coseeing_website, website_item)

		about_item = help_menu.Append(wx.ID_ABOUT, _("About"))
		self.Bind(wx.EVT_MENU, self.on_about, about_item)

		menu_bar.Append(help_menu, _("Help"))
		return menu_bar

	def _create_document_menu(self) -> tuple[wx.Menu, dict[str, wx.MenuItem]]:
		menu = wx.Menu()
		menu_items: dict[str, wx.MenuItem] = {}
		for item in get_document_menu_items():
			item_type = item[0]
			label = item[1]
			if item_type == "command":
				menu_items[label] = menu.Append(wx.ID_ANY, _(label))
			elif label == "Import":
				submenu = wx.Menu()
				menu_items[label] = menu.AppendSubMenu(submenu, _(label))
				for format_label in get_document_import_format_labels():
					submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
					submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_import_document(fmt),
						submenu_item,
					)
			elif label == "Export":
				submenu = wx.Menu()
				menu_items[label] = menu.AppendSubMenu(submenu, _(label))
				for format_label in get_document_export_format_labels():
					submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
					submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_export_document(fmt),
						submenu_item,
					)
			elif label == "Export All":
				submenu = wx.Menu()
				menu_items[label] = menu.AppendSubMenu(submenu, _(label))
				for format_label in get_document_export_format_labels():
					submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
					submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_export_all_documents(fmt),
						submenu_item,
					)
		self._bind_document_menu_handlers(menu, menu_items)
		self._sync_document_menu_state(menu_items)
		return menu, menu_items

	def _bind_document_menu_handlers(self, menu: wx.Menu, menu_items: dict[str, wx.MenuItem]) -> None:
		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["Open"])
		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["Delete"])
		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["Delete All"])
		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["Add"])
		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["Rename"])

	def _sync_document_menu_state(self, menu_items: dict[str, wx.MenuItem] | None = None) -> None:
		target_items = menu_items if menu_items is not None else getattr(self, "_document_menu_items", None)
		if not target_items or not hasattr(self, "documents") or not hasattr(self, "_selected_document_name"):
			return
		menu_state = get_document_menu_enabled_state(
			has_selection=self._get_selected_document() is not None,
			has_documents=bool(self.documents),
		)
		for label, enabled in menu_state.items():
			menu_item = target_items.get(label)
			if menu_item is not None:
				menu_item.Enable(enabled)

	def _set_control_accessible_name(
		self,
		control: wx.Window,
		name: str,
		description: str = "",
	) -> None:
		control.SetName(name)
		control.SetAccessible(NamedControlAccessible(control, name, description))

	def _create_labeled_group(self, parent: wx.Window, label: str) -> tuple[wx.StaticBoxSizer, wx.StaticBox, wx.BoxSizer]:
		group = wx.StaticBoxSizer(wx.VERTICAL, parent, label=label)
		box = group.GetStaticBox()
		row = wx.BoxSizer(wx.HORIZONTAL)
		group.Add(row, 0, wx.EXPAND | wx.ALL, 8)
		return group, box, row

	def _get_section_controls(self) -> dict[str, tuple[wx.Window, ...]]:
		return {
			DOCUMENT_LIST_SECTION: (self.document_list,),
			VIEW_SECTION: (
				self.font_size_spin,
				self.scheme_choice,
				self.braille_font_choice,
			),
			SOURCE_TEXT_SECTION: (self.input_txt,),
			BRAILLE_RESULT_SECTION: (self.output_txt,),
		}

	def _get_current_section_name(self) -> str | None:
		focus = wx.Window.FindFocus()
		if focus is None:
			return None
		for section_name, controls in self._get_section_controls().items():
			for control in controls:
				if focus == control or control.IsDescendant(focus):
					return section_name
		return None

	def _focus_section(self, section_name: str) -> None:
		target = self._get_section_controls()[section_name][0]
		target.SetFocus()

	def _clamp_view_font_size(self, font_size: int) -> int:
		return max(VIEW_FONT_SIZE_MIN, min(VIEW_FONT_SIZE_MAX, font_size))

	def _normalize_view_scheme(self, scheme: str) -> str:
		return scheme if scheme in VIEW_SCHEMES else DEFAULT_VIEW_SCHEME

	def _set_scheme_selection(self, scheme: str):
		for index, (scheme_key, _label) in enumerate(self._view_schemes):
			if scheme_key == scheme:
				self.scheme_choice.SetSelection(index)
				return
		self.scheme_choice.SetSelection(0)

	def _get_selected_scheme(self) -> str:
		selection = self.scheme_choice.GetSelection()
		if selection == wx.NOT_FOUND:
			return DEFAULT_VIEW_SCHEME
		return self._view_schemes[selection][0]

	def _normalize_braille_font(self, braille_font: str) -> str:
		valid_fonts = {font_key for font_key, _label in self._braille_font_options}
		return braille_font if braille_font in valid_fonts else DEFAULT_BRAILLE_FONT

	def _set_braille_font_selection(self, braille_font: str):
		for index, (font_key, _label) in enumerate(self._braille_font_options):
			if font_key == braille_font:
				self.braille_font_choice.SetSelection(index)
				return
		self.braille_font_choice.SetSelection(0)

	def _get_selected_braille_font(self) -> str:
		selection = self.braille_font_choice.GetSelection()
		if selection == wx.NOT_FOUND:
			return DEFAULT_BRAILLE_FONT
		return self._braille_font_options[selection][0]

	def _register_output_font(self) -> bool:
		return register_private_font_for_windows(get_simbraille_font_path(resource_path(".")))

	def _apply_editor_font_size(self, font_size: int):
		input_font = self.input_txt.GetFont()
		input_font.SetPointSize(font_size)
		self.input_txt.SetFont(input_font)

		output_font = wx.Font(self._default_output_font)
		output_font.SetPointSize(font_size)
		selected_braille_font = self._normalize_braille_font(self._get_selected_braille_font())
		if selected_braille_font == "simbraille" and (self._simbraille_font_available or sys.platform == "win32"):
			output_font.SetFaceName(SIMBRAILLE_FACE_NAME)
		self.output_txt.SetFont(output_font)

	def _apply_editor_scheme(self, scheme: str):
		scheme_colors = VIEW_SCHEMES[self._normalize_view_scheme(scheme)]
		for control in (self.input_txt, self.output_txt):
			control.SetBackgroundColour(scheme_colors["background"])
			control.SetForegroundColour(scheme_colors["foreground"])
			control.Refresh()

	def _apply_editor_view_settings(self, font_size: int, scheme: str):
		self._apply_editor_font_size(font_size)
		self._apply_editor_scheme(scheme)
		self.Layout()

	def _refresh_dictionary_names(self, preferred_name: str | None = None) -> str:
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names[:] = list_dictionary_names(self.dictionary_dir)
		selected_name = resolve_management_selection(self._dictionary_names, preferred_name)
		return selected_name

	def get_dictionary_names_for_dialog(self) -> list[str]:
		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		return list(self._dictionary_names)

	def _set_active_dictionary(self, selected_name: str) -> None:
		self.translation_settings = TranslationSettings(
			output_mode=self.translation_settings.output_mode,
			width=self.translation_settings.width,
			selected_dictionary=selected_name,
		)
		set_selected_dictionary(selected_name)

	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _get_csv_wildcard(self) -> str:
		return _(CSV_WILDCARD)

	def _show_file_error(self, message: str, error: Exception, parent: wx.Window | None = None) -> None:
		wx.MessageBox(
			message.format(error=error),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=parent or self,
		)

	def _get_dep_wildcard(self) -> str:
		return _(DEP_WILDCARD)

	def _get_document_names(self) -> list[str]:
		return get_document_names(self.documents)

	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
		try:
			webbrowser.open(about.url)
		except Exception as exc:
			self._show_file_error(_("Failed to open website: {error}"), exc)

	def on_about(self, _evt: wx.CommandEvent) -> None:
		with wx.MessageDialog(
			self,
			about.aboutMessage,
			_("About DotExpress"),
			wx.OK | wx.ICON_INFORMATION,
		) as dialog:
			dialog.ShowModal()

	def _sort_documents(self) -> None:
		self.documents.sort(key=lambda document: (document.name.casefold(), document.name))

	def _get_document_by_name(self, name: str | None) -> Document | None:
		return find_document(self.documents, name)

	def _replace_document(self, updated_document: Document) -> None:
		replace_document(self.documents, updated_document)

	def _document_name_exists(self, name: str, exclude_name: str | None = None) -> bool:
		return document_name_exists(self.documents, name, exclude_name=exclude_name)

	def _clear_document_selection(self) -> None:
		selection = self.document_list.GetFirstSelected()
		while selection != wx.NOT_FOUND:
			self.document_list.Select(selection, on=0)
			selection = self.document_list.GetFirstSelected()
		self._selected_document_name = None
		self._sync_document_menu_state()

	def _refresh_document_list(self, preferred_name: str | None = None) -> None:
		self._sort_documents()
		self.document_list.DeleteAllItems()
		for document in self.documents:
			self.document_list.InsertItem(self.document_list.GetItemCount(), document.name)
		if not self.documents:
			self._selected_document_name = None
			self._sync_document_menu_state()
			return
		selected_name = preferred_name if preferred_name in self._get_document_names() else self.documents[0].name
		self._selected_document_name = selected_name
		for index, document in enumerate(self.documents):
			if document.name == selected_name:
				self.document_list.Select(index)
				self.document_list.Focus(index)
				break
		self._sync_document_menu_state()

	def _clear_document_editors(self) -> None:
		self.input_txt.SetValue("")
		self.output_txt.SetValue("")

	def _load_document_into_editors(self, document: Document) -> None:
		self.input_txt.SetValue(document.text)
		self.output_txt.SetValue(document.braille or "")

	def _get_txt_wildcard(self) -> str:
		return _(TXT_WILDCARD)

	def _get_brl_wildcard(self) -> str:
		return _(BRL_WILDCARD)

	def _build_conversion_request(self, raw_text: str, table_file: str, output_mode: str, width: int, dictionary_path: Path) -> ConversionRequest:
		return ConversionRequest(
			raw_text=raw_text,
			table_file=table_file,
			output_mode=output_mode,
			width=width,
			dictionary_path=dictionary_path,
			data_dir=resource_path("data"),
			translation_tables=language_map_translate_table.copy(),
		)

	def _convert_text_for_output(self, raw_text: str) -> str:
		if raw_text == "":
			return ""
		table_file = language_map_translate_table.get("default")
		if not table_file:
			raise ValueError(_("Please select a translation table first."))
		settings = self.translation_settings
		dictionary_path = self._get_selected_dictionary_path()
		return convert_text_for_output(
			self._build_conversion_request(
				raw_text,
				table_file,
				settings.output_mode,
				settings.width,
				dictionary_path,
			)
		)

	def _format_batch_issue_lines(self, issues: list[BatchIssue]) -> list[str]:
		return [f"{issue.path.name}: {issue.reason}" for issue in issues]

	def _show_file_issues_dialog(self, title: str, message: str, issues: list[BatchIssue]) -> None:
		if not issues:
			return
		with FileIssuesDialog(self, title=title, message=message, issues=self._format_batch_issue_lines(issues)) as dialog:
			dialog.ShowModal()

	def _confirm_overwrite_all(self, conflicts: list[Path]) -> bool:
		if not conflicts:
			return True
		message = _(
			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
		)
		return (
			wx.MessageBox(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
		)

	def _prepare_document_for_export(self, document: Document) -> tuple[Document, Exception | None]:
		return prepare_document_for_save(
			document,
			text=document.text,
			braille=document.braille or "",
			auto_convert=self._convert_text_for_output,
		)

	def _export_document_with_dialog(self, document: Document, format_key: str) -> None:
		export_document, auto_error = self._prepare_document_for_export(document)
		default_file = f"{document.name}.dep" if format_key == "dep" else f"{document.name}.brl"
		wildcard = self._get_dep_wildcard() if format_key == "dep" else self._get_brl_wildcard()
		with wx.FileDialog(
			self,
			_("Export Document"),
			defaultFile=default_file,
			wildcard=wildcard,
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			destination_path = Path(file_dialog.GetPath())
		target_suffix = ".dep" if format_key == "dep" else ".brl"
		if destination_path.suffix.casefold() != target_suffix:
			destination_path = destination_path.with_suffix(target_suffix)
		try:
			if format_key == "dep":
				save_document_package(destination_path, export_document, include_pending_metadata=False)
			else:
				export_document_brl(destination_path, export_document)
		except OSError as exc:
			self._show_file_error(_("Failed to export document: {error}"), exc)
			return
		if auto_error is not None:
			wx.MessageBox(
				_("Automatic conversion failed while exporting. The document was exported with empty braille output.\n\n{error}").format(error=auto_error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)

	def _set_view_font_size(self, font_size: int) -> None:
		font_size = self._clamp_view_font_size(font_size)
		if self.font_size_spin.GetValue() != font_size:
			self.font_size_spin.SetValue(font_size)
		self._apply_editor_view_settings(font_size, self._get_selected_scheme())
		set_view_font_size(font_size)

	def _open_document_by_name(self, name: str | None) -> None:
		decision = plan_open_document(self.documents, name)
		if decision.document is None:
			self._open_document_name = decision.open_name
			self._selected_document_name = decision.selected_name
			self._clear_document_editors()
			return
		self._open_document_name = decision.open_name
		self._selected_document_name = decision.selected_name
		self._load_document_into_editors(decision.document)
		self._refresh_document_list(decision.selected_name)

	def _save_open_document(self) -> Exception | None:
		if not self._open_document_name:
			return None
		document = self._get_document_by_name(self._open_document_name)
		if document is None:
			return None
		updated_document, auto_error = prepare_document_for_save(
			document,
			text=self.input_txt.GetValue(),
			braille=self.output_txt.GetValue(),
			auto_convert=self._convert_text_for_output,
		)
		if document.braille is None:
			self.output_txt.SetValue(updated_document.braille or "")
		self._replace_document(updated_document)
		save_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)
		return auto_error

	def _save_open_document_with_feedback(self) -> bool:
		try:
			auto_error = self._save_open_document()
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return False
		if auto_error is not None:
			wx.MessageBox(
				_("Automatic conversion failed while saving. The document was saved with empty braille output.\n\n{error}").format(error=auto_error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
		return True

	def _review_invalid_workspace_files(self, invalid_paths: list[Path]) -> None:
		if not invalid_paths:
			return
		with InvalidWorkspaceFilesDialog(self, invalid_paths) as dialog:
			dialog.ShowModal()
			delete_invalid = dialog.should_delete_invalid_files()
		if not delete_invalid:
			return
		for invalid_path in invalid_paths:
			try:
				invalid_path.unlink(missing_ok=True)
			except OSError as exc:
				self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc)

	def _create_document(
		self,
		document_name: str,
		text: str = "",
		braille: str | None = "",
		*,
		focus_input: bool = False,
	) -> bool:
		document = Document(name=document_name, text=text, braille=braille)
		try:
			save_document_package(document_package_path_for_name(document.name, self.workspace_dir), document)
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return False
		self.documents.append(document)
		self._refresh_document_list(document.name)
		self._open_document_by_name(document.name)
		if focus_input:
			self.input_txt.SetFocus()
		return True

	def _prompt_for_document_name(
		self,
		title: str,
		initial_name: str = "",
		exclude_name: str | None = None,
	) -> str | None:
		prefill_name = initial_name
		while True:
			with DocumentNameDialog(self, title=title, initial_name=prefill_name) as dialog:
				if dialog.ShowModal() != wx.ID_OK:
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			if self._document_name_exists(document_name, exclude_name=exclude_name):
				wx.MessageBox(
					_('Document "{name}" already exists.').format(name=document_name),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=self,
				)
				prefill_name = document_name
				continue
			return document_name

	def _create_default_document(self) -> bool:
		default_document = create_default_document()
		return self._create_document(
			DEFAULT_DOCUMENT_NAME,
			default_document.text,
			default_document.braille,
			focus_input=True,
		)

	def _ensure_open_document_exists(self) -> None:
		if self.documents:
			self._open_document_by_name(self.documents[0].name)
			return
		self._create_default_document()

	def _persist_documents(self, documents: list[Document]) -> tuple[list[Document], list[BatchIssue]]:
		saved_documents: list[Document] = []
		issues: list[BatchIssue] = []
		for document in documents:
			try:
				save_document_package(document_package_path_for_name(document.name, self.workspace_dir), document)
			except OSError as exc:
				issues.append(BatchIssue(path=document_package_path_for_name(document.name, self.workspace_dir), reason=str(exc)))
				continue
			saved_documents.append(document)
		return saved_documents, issues

	def _load_workspace_documents_at_startup(self) -> None:
		self.workspace_dir = ensure_workspace_directory(self.workspace_dir)
		self.documents, invalid_paths = load_workspace_documents(self.workspace_dir)
		self._refresh_document_list()
		self._review_invalid_workspace_files(invalid_paths)
		self._ensure_open_document_exists()

	def _get_selected_document_name(self) -> str | None:
		selection = self.document_list.GetFirstSelected()
		if selection == wx.NOT_FOUND or selection >= len(self.documents):
			return self._selected_document_name
		return self.documents[selection].name

	def _get_selected_document(self) -> Document | None:
		return self._get_document_by_name(self._get_selected_document_name())

	def on_document_selection_changed(self, event: wx.ListEvent) -> None:
		selection = self.document_list.GetFirstSelected()
		if selection == wx.NOT_FOUND or selection >= len(self.documents):
			self._selected_document_name = None
		else:
			self._selected_document_name = self.documents[selection].name
		self._sync_document_menu_state()
		event.Skip()

	def on_document_activated(self, _event: wx.ListEvent) -> None:
		self.on_open_document(None)

	def on_document_context_menu(self, event: wx.ContextMenuEvent) -> None:
		position = event.GetPosition()
		client_position = self.document_list.ScreenToClient(position) if position != wx.DefaultPosition else wx.Point(0, 0)
		item_index, _flags = self.document_list.HitTest(client_position)
		selected_index = self.document_list.GetFirstSelected()
		if item_index != wx.NOT_FOUND and item_index < len(self.documents):
			self.document_list.Select(item_index)
			self.document_list.Focus(item_index)
			self._selected_document_name = self.documents[item_index].name
		elif position == wx.DefaultPosition and selected_index != wx.NOT_FOUND:
			item_index = selected_index
		else:
			self._clear_document_selection()
		rect = self.document_list.GetItemRect(item_index) if item_index != wx.NOT_FOUND and item_index < self.document_list.GetItemCount() else None
		menu = wx.Menu()
		menu_items: dict[str, wx.MenuItem] = {}
		import_submenu = wx.Menu()
		export_submenu = wx.Menu()
		export_all_submenu = wx.Menu()
		for item in get_document_menu_items():
			item_type = item[0]
			label = item[1]
			if item_type == "command":
				menu_items[label] = menu.Append(wx.ID_ANY, _(label))
			elif label == "Import":
				menu_items[label] = menu.AppendSubMenu(import_submenu, _(label))
				for format_label in get_document_import_format_labels():
					submenu_item = import_submenu.Append(wx.ID_ANY, _(format_label))
					import_submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_import_document(fmt),
						submenu_item,
					)
			elif label == "Export":
				menu_items[label] = menu.AppendSubMenu(export_submenu, _(label))
				for format_label in get_document_export_format_labels():
					submenu_item = export_submenu.Append(wx.ID_ANY, _(format_label))
					export_submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_export_document(fmt),
						submenu_item,
					)
			elif label == "Export All":
				menu_items[label] = menu.AppendSubMenu(export_all_submenu, _(label))
				for format_label in get_document_export_format_labels():
					submenu_item = export_all_submenu.Append(wx.ID_ANY, _(format_label))
					export_all_submenu.Bind(
						wx.EVT_MENU,
						lambda _evt, fmt=format_label.lower(): self.on_export_all_documents(fmt),
						submenu_item,
					)
		self._bind_document_menu_handlers(menu, menu_items)
		self._sync_document_menu_state(menu_items)
		popup_position = (rect.x, rect.y + rect.height) if rect is not None else client_position
		self.document_list.PopupMenu(menu, popup_position)
		menu.Destroy()

	def on_open_document(self, _evt) -> None:
		selected_name = self._get_selected_document_name()
		if not selected_name:
			return
		if not self._save_open_document_with_feedback():
			return
		self._open_document_by_name(selected_name)
		self.input_txt.SetFocus()

	def on_add_document(self, _evt) -> None:
		if not self._save_open_document_with_feedback():
			return
		document_name = self._prompt_for_document_name(_("Add Document"))
		if document_name is None:
			return
		self._create_document(document_name)

	def on_rename_document(self, _evt) -> None:
		selected_name = self._get_selected_document_name()
		selected_document = self._get_document_by_name(selected_name)
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		selected_document = self._get_document_by_name(selected_name)
		if selected_document is None:
			return
		new_name = self._prompt_for_document_name(
			_("Rename Document"),
			initial_name=selected_document.name,
			exclude_name=selected_document.name,
		)
		if new_name is None or new_name == selected_document.name:
			return
		try:
			renamed_document = Document(name=new_name, text=selected_document.text, braille=selected_document.braille)
			save_document_package(document_package_path_for_name(renamed_document.name, self.workspace_dir), renamed_document)
			old_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
			if old_path.exists():
				old_path.unlink()
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return
		renamed_document = rename_document_in_list(self.documents, selected_document.name, new_name)
		if renamed_document is None:
			return
		if self._open_document_name == selected_document.name:
			self._open_document_name = renamed_document.name
		self._refresh_document_list(renamed_document.name)

	def on_delete_document(self, _evt) -> None:
		selected_document = self._get_selected_document()
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = wx.MessageBox(
			_('Do you want to delete document "{name}"?').format(name=selected_document.name),
			_("Confirm Delete Document"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			parent=self,
		)
		if confirmation != wx.YES:
			return
		delete_decision = plan_delete_document(self.documents, selected_document.name, self._open_document_name)
		try:
			package_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
			if package_path.exists():
				package_path.unlink()
		except OSError as exc:
			self._show_file_error(_("Failed to delete document: {error}"), exc)
			return
		self.documents = [document for document in self.documents if document.name != selected_document.name]
		if delete_decision.was_open:
			self._open_document_name = None
		self._refresh_document_list(delete_decision.preferred_name)
		if self.documents:
			if delete_decision.was_open and delete_decision.preferred_name:
				self._open_document_by_name(delete_decision.preferred_name)
		else:
			self._clear_document_editors()
			self._ensure_open_document_exists()

	def on_delete_all_documents(self, _evt) -> None:
		if not self.documents:
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = wx.MessageBox(
			_("Delete All will remove all documents. Do you want to continue?"),
			_("Confirm Delete All"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			parent=self,
		)
		if confirmation != wx.YES:
			return
		for document in list(self.documents):
			try:
				package_path = document_package_path_for_name(document.name, self.workspace_dir)
				if package_path.exists():
					package_path.unlink()
			except OSError as exc:
				self._show_file_error(_("Failed to delete document: {error}"), exc)
				remaining_documents, invalid_paths = load_workspace_documents(self.workspace_dir)
				self.documents = remaining_documents
				self._refresh_document_list()
				self._review_invalid_workspace_files(invalid_paths)
				if self.documents:
					self._open_document_by_name(self.documents[0].name)
				else:
					self._clear_document_editors()
				return
		self.documents = []
		self._selected_document_name = None
		self._open_document_name = None
		self._refresh_document_list()
		self._clear_document_editors()
		self._ensure_open_document_exists()

	def on_import_document(self, format_key: str) -> None:
		if not self._save_open_document_with_feedback():
			return
		title = _("Import Document")
		wildcard = self._get_dep_wildcard() if format_key == "dep" else self._get_txt_wildcard()
		with wx.FileDialog(self, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_MULTIPLE) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			source_paths = [Path(path) for path in file_dialog.GetPaths()]
		documents, issues = batch_import_documents(
			source_paths,
			format_key=format_key,
			existing_names=set(self._get_document_names()),
		)
		saved_documents, save_issues = self._persist_documents(documents)
		self.documents.extend(saved_documents)
		if len(saved_documents) == 1:
			self._open_document_by_name(saved_documents[0].name)
		else:
			self._refresh_document_list(self._open_document_name or self._selected_document_name)
		self._show_file_issues_dialog(
			_("Import Issues"),
			_("Some files were skipped during import."),
			issues + save_issues,
		)

	def on_export_document(self, format_key: str) -> None:
		selected_document = self._get_selected_document()
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		selected_document = self._get_selected_document() or selected_document
		self._export_document_with_dialog(selected_document, format_key)

	def on_export_all_documents(self, format_key: str) -> None:
		if not self.documents:
			return
		if not self._save_open_document_with_feedback():
			return
		with wx.DirDialog(self, _("Export All Documents")) as dir_dialog:
			if dir_dialog.ShowModal() != wx.ID_OK:
				return
			destination_dir = Path(dir_dialog.GetPath())
		conflicts = batch_export_documents_to_folder(destination_dir, self.documents, format_key=format_key, overwrite=False)
		if conflicts and not self._confirm_overwrite_all(conflicts):
			return
		export_documents: list[Document] = []
		issues: list[BatchIssue] = []
		for document in self.documents:
			export_document, auto_error = self._prepare_document_for_export(document)
			export_documents.append(export_document)
			if auto_error is not None:
				issues.append(BatchIssue(path=Path(f"{document.name}.{format_key}"), reason=str(auto_error)))
		try:
			batch_export_documents_to_folder(destination_dir, export_documents, format_key=format_key, overwrite=True)
		except OSError as exc:
			self._show_file_error(_("Failed to export document: {error}"), exc)
			return
		self._show_file_issues_dialog(
			_("Export All Issues"),
			_("Some documents were exported with empty braille output because automatic conversion failed."),
			issues,
		)

	def on_font_size_change(self, _evt):
		self._set_view_font_size(self.font_size_spin.GetValue())

	def on_scheme_change(self, _evt):
		scheme = self._normalize_view_scheme(self._get_selected_scheme())
		self._apply_editor_view_settings(self._clamp_view_font_size(self.font_size_spin.GetValue()), scheme)
		set_view_scheme(scheme)

	def on_braille_font_change(self, _evt):
		braille_font = self._normalize_braille_font(self._get_selected_braille_font())
		self._apply_editor_view_settings(self._clamp_view_font_size(self.font_size_spin.GetValue()), self._get_selected_scheme())
		set_braille_font(braille_font)

	def on_input_text_key_down(self, event: wx.KeyEvent) -> None:
		if is_convert_shortcut(event.GetKeyCode(), event.ControlDown()):
			self.on_convert(None)
			return
		event.Skip()

	def on_output_text_key_down(self, event: wx.KeyEvent) -> None:
		if is_brl_export_shortcut(event.GetKeyCode(), event.ControlDown()):
			if self._save_open_document_with_feedback():
				document = self._get_document_by_name(self._open_document_name)
				if document is not None:
					self._export_document_with_dialog(document, "brl")
			self.output_txt.SetFocus()
			return
		event.Skip()

	def on_document_list_key_down(self, event: wx.KeyEvent) -> None:
		if is_document_rename_shortcut(event.GetKeyCode()):
			self.on_rename_document(None)
			return
		if is_document_delete_shortcut(event.GetKeyCode()):
			self.on_delete_document(None)
			return
		event.Skip()

	def on_char_hook(self, event: wx.KeyEvent) -> None:
		if is_document_import_txt_shortcut(event.GetKeyCode(), event.AltDown()):
			self.on_import_document("txt")
			return
		step = is_section_navigation_shortcut(event.GetKeyCode(), event.ShiftDown())
		if step == 0:
			event.Skip()
			return
		current_section = self._get_current_section_name()
		if current_section is None:
			target_section = DOCUMENT_LIST_SECTION if step > 0 else BRAILLE_RESULT_SECTION
		else:
			target_section = get_adjacent_section(current_section, step)
		self._focus_section(target_section)

	def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
		step = get_font_size_step_from_wheel(event.GetWheelRotation(), event.ControlDown())
		if step == 0:
			event.Skip()
			return
		self._set_view_font_size(self.font_size_spin.GetValue() + step)

	def on_open_translation_settings(self, _evt) -> None:
		dictionary_names = self.get_dictionary_names_for_dialog()
		staged_settings = normalize_translation_settings(self.translation_settings, dictionary_names)
		with TranslationSettingsDialog(self, staged_settings, dictionary_names) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			self.translation_settings = normalize_translation_settings(dialog.get_settings(), dictionary_names)
			self._set_active_dictionary(self.translation_settings.selected_dictionary)
			save_translation_settings(self.translation_settings)

	def on_open_dictionary_management(self, _evt) -> None:
		selected_name = self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		with DictionaryManagementDialog(
			self,
			self._dictionary_names,
			selected_name,
			self.add_dictionary,
			self.delete_dictionary_from_dialog,
			self.rename_dictionary_from_dialog,
			self.import_dictionary_from_dialog,
			self.export_dictionary_from_dialog,
		) as dialog:
			result = dialog.ShowModal()
			edit_name = dialog.edit_dictionary_name

		if result != wx.ID_EDIT or edit_name is None:
			return
		dictionary_path = dictionary_path_for_name(edit_name, self.dictionary_dir)
		with SpeechSymbolsDialog(self, dictionary_path=dictionary_path) as editor:
			editor.ShowModal()

	def on_open_table_dialog(self, _evt):
		with TranslationTableDialog(self, language_map_translate_table) as dialog:
			if dialog.ShowModal() == wx.ID_OK:
				selections = dialog.get_selected_tables()
				language_map_translate_table.update(selections)
				set_translation_tables(language_map_translate_table)

	def add_dictionary(self, parent: wx.Window | None) -> str | None:
		dialog_parent = parent or self
		with DictionaryNameDialog(dialog_parent) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			dictionary_name = dialog.get_dictionary_name()

		try:
			path = create_dictionary(self.dictionary_dir, dictionary_name)
		except FileExistsError:
			wx.MessageBox(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=dialog_parent,
			)
			return None
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
			return None

		update = plan_dictionary_state_after_add(
			self.translation_settings.selected_dictionary,
			self.get_dictionary_names_for_dialog(),
			path.stem,
		)
		return update.management_selected_name

	def delete_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> str | None:
		dialog_parent = parent or self
		if is_default_dictionary(selected_name):
			wx.MessageBox(
				_("The default dictionary cannot be deleted."),
				_("Info"),
				wx.OK | wx.ICON_INFORMATION,
				parent=dialog_parent,
			)
			return None

		if (
			wx.MessageBox(
				_('Do you want to delete dictionary "{name}"?').format(name=selected_name),
				_("Confirm Delete Dictionary"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
				parent=dialog_parent,
			)
			!= wx.YES
		):
			return None

		previous_names = list(self._dictionary_names)
		current_active_name = self.translation_settings.selected_dictionary
		try:
			delete_dictionary(self.dictionary_dir, selected_name)
		except OSError as exc:
			self._show_file_error(_("Failed to delete dictionary: {error}"), exc, parent=dialog_parent)
			return None
		self._refresh_dictionary_names(selected_name)
		update = plan_dictionary_state_after_delete(
			current_active_name,
			selected_name,
			previous_names,
		)
		if update.active_selected_name != current_active_name:
			self._set_active_dictionary(update.active_selected_name)
		return update.management_selected_name

	def rename_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> str | None:
		dialog_parent = parent or self
		if is_default_dictionary(selected_name):
			return None
		with DictionaryNameDialog(dialog_parent) as dialog:
			dialog.SetTitle(_("Rename Dictionary"))
			dialog.name_ctrl.SetValue(selected_name)
			dialog.name_ctrl.SetFocus()
			dialog.name_ctrl.SelectAll()
			if dialog.ShowModal() != wx.ID_OK:
				return None
			dictionary_name = dialog.get_dictionary_name()

		try:
			path = rename_dictionary(self.dictionary_dir, selected_name, dictionary_name)
		except FileExistsError:
			wx.MessageBox(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=dialog_parent,
			)
			return None
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
			return None
		except OSError as exc:
			self._show_file_error(_("Failed to save dictionary: {error}"), exc, parent=dialog_parent)
			return None

		current_active_name = self.translation_settings.selected_dictionary
		self._refresh_dictionary_names(path.stem)
		update = plan_dictionary_state_after_rename(
			current_active_name,
			selected_name,
			path.stem,
			self.get_dictionary_names_for_dialog(),
		)
		if update.active_selected_name != current_active_name:
			self._set_active_dictionary(update.active_selected_name)
		return update.management_selected_name

	def import_dictionary_from_dialog(self, parent: wx.Window | None) -> str | None:
		dialog_parent = parent or self
		with wx.FileDialog(
			dialog_parent,
			_("Import Dictionary"),
			wildcard=self._get_csv_wildcard(),
			style=wx.FD_OPEN,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			source_path = Path(file_dialog.GetPath())

		with DictionaryNameDialog(dialog_parent) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			dictionary_name = dialog.get_dictionary_name()

		try:
			path = import_dictionary(self.dictionary_dir, source_path, dictionary_name)
		except FileExistsError:
			wx.MessageBox(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=dialog_parent,
			)
			return None
		except ValueError:
			wx.MessageBox(
				_("Imported file must contain text, braille, and type headers."),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=dialog_parent,
			)
			return None
		except OSError as exc:
			self._show_file_error(_("Failed to import dictionary: {error}"), exc, parent=dialog_parent)
			return None

		update = plan_dictionary_state_after_add(
			self.translation_settings.selected_dictionary,
			self.get_dictionary_names_for_dialog(),
			path.stem,
		)
		return update.management_selected_name

	def export_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> None:
		dialog_parent = parent or self
		if not self._dictionary_names:
			return
		with wx.FileDialog(
			dialog_parent,
			_("Export Dictionary"),
			defaultFile=f"{selected_name}.csv",
			wildcard=self._get_csv_wildcard(),
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			destination_path = Path(file_dialog.GetPath())

		try:
			export_dictionary(self.dictionary_dir, selected_name, destination_path)
		except OSError as exc:
			self._show_file_error(_("Failed to export dictionary: {error}"), exc, parent=dialog_parent)

	def on_convert(self, _evt):
		if self._convert_thread and self._convert_thread.is_alive():
			return

		table_file = language_map_translate_table.get("default")
		if not table_file:
			wx.MessageBox(
				_("Please select a translation table first."),
				_("Info"),
				wx.OK | wx.ICON_INFORMATION,
				parent=self,
			)
			return
		raw_text = self.input_txt.GetValue()
		settings = self.translation_settings
		self._start_conversion(
			table_file,
			raw_text,
			settings.width,
			settings.output_mode,
			self._get_selected_dictionary_path(),
		)

	def _on_close(self, evt: wx.CloseEvent):
		if self._convert_thread and self._convert_thread.is_alive() and evt.CanVeto():
			evt.Veto()
			return
		if not self._save_open_document_with_feedback():
			if evt.CanVeto():
				evt.Veto()
			return
		self._close_converting_dialog()
		evt.Skip()

	def _set_conversion_busy(self, busy: bool):
		menu_bar = self.GetMenuBar()
		if menu_bar is not None:
			for menu_label in (_("File"), _("Translation")):
				menu_index = menu_bar.FindMenu(menu_label)
				if menu_index != wx.NOT_FOUND:
					menu_bar.EnableTop(menu_index, not busy)
		self.document_list.Enable(not busy)
		self.input_txt.Enable(not busy)

	def _start_conversion(self, table_file: str, raw_text: str, width: int, output_mode: str, dictionary_path: Path):
		self._convert_job_id += 1
		job_id = self._convert_job_id
		self._set_conversion_busy(True)
		self._close_converting_dialog()
		self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)
		self._convert_thread = threading.Thread(
			target=self._run_conversion,
			args=(job_id, table_file, raw_text, width, output_mode, dictionary_path),
			daemon=True,
		)
		self._convert_thread.start()

	def _run_conversion(self, job_id: int, table_file: str, raw_text: str, width: int, output_mode: str, dictionary_path: Path):
		try:
			display_text = convert_text_for_output(
				self._build_conversion_request(raw_text, table_file, output_mode, width, dictionary_path)
			)
		except ConversionStageError as e:
			message_template = _("ASCII conversion failed: {error}") if e.stage == "ascii" else _("Translation failed: {error}")
			wx.CallAfter(
				self._finish_conversion,
				job_id,
				error_message=message_template.format(error=get_public_error_message(e.error)),
			)
			return

		wx.CallAfter(self._finish_conversion, job_id, display_text=display_text)

	def _show_converting_dialog(self, job_id: int):
		if job_id != self._convert_job_id:
			return
		if not (self._convert_thread and self._convert_thread.is_alive()):
			return
		if self._convert_dialog is not None:
			return
		self._convert_dialog = ConvertingDialog(self)
		self._convert_dialog.Show()
		self._convert_dialog.Raise()

	def _close_converting_dialog(self):
		if self._convert_dialog is None:
			return
		dialog = self._convert_dialog
		self._convert_dialog = None
		dialog.Unbind(wx.EVT_CLOSE)
		dialog.Destroy()

	def _finish_conversion(self, job_id: int, display_text: str | None = None, error_message: str | None = None):
		if job_id != self._convert_job_id:
			return
		if self._convert_dialog_timer is not None:
			self._convert_dialog_timer.Stop()
			self._convert_dialog_timer = None
		self._close_converting_dialog()
		self._convert_thread = None
		self._set_conversion_busy(False)

		if error_message is not None:
			wx.MessageBox(
				error_message,
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return

		self.output_txt.SetValue(display_text or "")
		self.output_txt.SetFocus()
		wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)


class BrailleApp(wx.App):
	def OnInit(self):
		louis_helper.initialize()
		self.frame = BrailleFrame(None)
		self.frame.Show()
		start_client_init_background()
		return True

	def OnExit(self):
		louis_helper.terminate()
		return 0


if __name__ == "__main__":
	app = BrailleApp()
	app.MainLoop()
