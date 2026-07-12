from dataclasses import replace
from pathlib import Path
import gettext
import sys
import webbrowser

import wx

import about
from adapters.translation.contracts import TranslationRuntime
from adapters.translation.provider import build_default_translation_runtime
from conversion.jobs import (
	ConversionCompletionPolicy,
	ConversionJobFailure,
	ConversionJobRequest,
	ConversionJobRunner,
	ConversionJobSuccess,
)
from conversion.service import (
	ConversionOutput,
	ConversionRequest,
	convert_text_for_output,
	get_public_error_message,
)
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
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
from documents.controller import DocumentController
from documents.formats import get_format
from documents.session import (
    document_name_exists,
    get_adjacent_document_name,
    format_window_title,
)
from documents.workspace import (
    BatchIssue,
    DEFAULT_DOCUMENT_NAME,
    Document,
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
from documents.export_results import (
    ExportBatchResult,
)
from ui.action_menu import (
    get_document_menu_enabled_state,
    get_document_menu_descriptors,
)
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from config import (
	DEFAULT_TRANSLATION_TABLES,
	set_selected_dictionary,
)
from settings.translation import (
	TranslationSettings,
	load_translation_settings,
	normalize_translation_settings,
	save_translation_settings,
)
from settings.translation_tables import load_translation_tables, save_translation_tables
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
	is_document_cycle_shortcut,
	is_document_delete_shortcut,
	is_document_import_txt_shortcut,
	is_document_rename_shortcut,
	is_section_navigation_shortcut,
)
from ui.section_navigation import (
	BRAILLE_RESULT_SECTION,
	DOCUMENT_LIST_SECTION,
	SOURCE_TEXT_SECTION,
	get_adjacent_section,
)
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from ui.dual_view import DualViewFrame
from ui.translation_menu import get_translation_menu_items
from client_init import start_client_init_background

from dialog import (
	DictionaryManagementDialog,
	DictionaryNameDialog,
	DocumentNameDialog,
	FileIssuesDialog,
	InvalidWorkspaceFilesDialog,
	SpeechSymbolsDialog,
	finalize_dialog_layout,
)
from settings.view import (
	ViewSettings,
	load_view_settings,
	normalize_view_settings,
	save_view_settings,
)
from settings.state import DotExpressSettingsSnapshot
from settings.dialogs import DotExpressSettingsDialog, TranslationSettingsPanel


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
PDF_WILDCARD = "PDF files (*.pdf)|*.pdf"
DOCX_WILDCARD = "Word documents (*.docx)|*.docx"
EPUB_WILDCARD = "EPUB books (*.epub)|*.epub"
BRL_WILDCARD = "Braille files (*.brl)|*.brl"
IMPORT_WILDCARDS = {
	"dep": DEP_WILDCARD,
	"txt": TXT_WILDCARD,
	"pdf": PDF_WILDCARD,
	"docx": DOCX_WILDCARD,
	"epub": EPUB_WILDCARD,
}


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
	_("Dual View"),
	_("Rename"),
	_("Default"),
	_("Braille Font"),
	_("SimBraille"),
	_("Export All"),
	_("DEP"),
	_("TXT"),
	_("PDF"),
	_("DOCX"),
	_("EPUB"),
	_("BRL"),
	_("Delete All"),
	_("Translation"),
	_("No conversion data is available for this document."),
	_("Convert"),
	_("Settings"),
	_("Dictionary Management..."),
	_("Confirm Delete Dictionary"),
	_("Do you want to delete dictionary \"{name}\"?"),
	_("Rename Dictionary"),
	_("Help"),
	_("Coseeing Website"),
	_("About DotExpress"),
	_("CSV files (*.csv)|*.csv"),
	_("DotExpress files (*.dep)|*.dep"),
	_("Text files (*.txt)|*.txt"),
	_("PDF files (*.pdf)|*.pdf"),
	_("Word documents (*.docx)|*.docx"),
	_("EPUB books (*.epub)|*.epub"),
	_("Braille files (*.brl)|*.brl"),
	_("All Supported Files"),
)

language_map_translate_table = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()


def _prompt_for_dictionary_name(parent: wx.Window | None, *, title: str, initial_name: str = "") -> str | None:
	with DictionaryNameDialog(parent, initial_name=initial_name) as dialog:
		dialog.SetTitle(title)
		if dialog.ShowModal() != wx.ID_OK:
			return None
		return dialog.get_dictionary_name()


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
	def __init__(self, *args, runtime: TranslationRuntime, **kwargs):
		super().__init__(*args, **kwargs)
		self.translation_runtime = runtime

		self._initialize_frame()
		initial_settings = self._initialize_state()
		self._create_main_layout(initial_settings)
		self._initialize_conversion_state()
		self._apply_initial_settings(initial_settings)
		self._bind_events()
		self._load_startup_documents()

	def _get_document_controller(self) -> DocumentController:
		controller = self.__dict__.get("_document_controller")
		if controller is None:
			controller = DocumentController()
			self._document_controller = controller
		return controller

	@property
	def documents(self) -> list[Document]:
		return self._get_document_controller().documents

	@documents.setter
	def documents(self, value: list[Document]) -> None:
		self._get_document_controller().documents = value

	@property
	def _open_document_name(self) -> str | None:
		return self._get_document_controller().open_name

	@_open_document_name.setter
	def _open_document_name(self, value: str | None) -> None:
		self._get_document_controller().open_name = value

	@property
	def _selected_document_name(self) -> str | None:
		return self._get_document_controller().selected_name

	@_selected_document_name.setter
	def _selected_document_name(self, value: str | None) -> None:
		self._get_document_controller().selected_name = value

	@property
	def _dual_view_results_by_document(self) -> dict[str, tuple[object, ...]]:
		return self._get_document_controller().dual_view_results_by_document

	@_dual_view_results_by_document.setter
	def _dual_view_results_by_document(self, value: dict[str, tuple[object, ...]]) -> None:
		self._get_document_controller().dual_view_results_by_document = value

	def _initialize_frame(self) -> None:
		self.SetSize((900, 600))
		self.SetMenuBar(self._create_menu_bar())

	def _initialize_state(self) -> ViewSettings:
		self.dictionary_dir = get_dictionary_directory()
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names = list_dictionary_names(self.dictionary_dir)
		self.translation_settings = load_translation_settings(self._dictionary_names)
		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		self.workspace_dir = get_workspace_directory()
		self._document_controller = DocumentController()
		self.documents = []
		self._simbraille_font_available = self._register_output_font()
		self._selected_document_name = None
		self._open_document_name = None
		self._dual_view_frame: DualViewFrame | None = None
		self._dual_view_results_by_document = {}

		self.view_settings = load_view_settings()
		return self.view_settings

	def _create_main_layout(self, initial_settings: ViewSettings) -> None:
		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		content_box = wx.BoxSizer(wx.HORIZONTAL)
		content_box.Add(self._create_document_list(panel), 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 8)
		content_box.Add(self._create_editor_area(panel), 1, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 8)
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

	def _create_editor_area(self, panel: wx.Window) -> wx.BoxSizer:
		editors_box = wx.BoxSizer(wx.VERTICAL)
		self.input_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		self._set_control_accessible_name(self.input_txt, _("Source Text"))
		editors_box.Add(self.input_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		self.output_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
		self._default_output_font = self.output_txt.GetFont()
		self._set_control_accessible_name(self.output_txt, _("Braille Result"))
		editors_box.Add(self.output_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
		return editors_box

	def _initialize_conversion_state(self) -> None:
		self._conversion_runner = ConversionJobRunner(
			runtime=self.translation_runtime,
			on_success=self._finish_conversion_success,
			on_failure=self._finish_conversion_failure,
			call_after=wx.CallAfter,
		)
		self._convert_dialog = None
		self._convert_dialog_timer = None

	def _apply_initial_settings(self, initial_settings: ViewSettings) -> None:
		self._apply_editor_view_settings(initial_settings)

	def _bind_events(self) -> None:
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
		self.Bind(wx.EVT_ACTIVATE, self.on_frame_activate)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _load_startup_documents(self) -> None:
		self._clear_document_editors()
		self._load_workspace_documents_at_startup()
		self._update_window_title()
		self.input_txt.SetFocus()

	def _create_menu_bar(self) -> wx.MenuBar:
		menu_bar = wx.MenuBar()
		file_menu, self._document_menu_items = self._create_document_menu()
		menu_bar.Append(file_menu, _("File"))

		translation_menu = wx.Menu()
		translation_handlers = {
			"convert": self.on_convert,
			"dual_view": self.on_open_dual_view,
			"settings": self.on_open_settings,
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
		menu_items, submenu_items = self._append_document_menu_items(menu)
		self._bind_document_menu_handlers(menu, menu_items, submenu_items)
		self._sync_document_menu_state(menu_items)
		return menu, menu_items

	def _append_document_menu_items(
		self,
		menu: wx.Menu,
	) -> tuple[dict[str, wx.MenuItem], dict[str, dict[str, wx.MenuItem]]]:
		menu_items: dict[str, wx.MenuItem] = {}
		submenu_items: dict[str, dict[str, wx.MenuItem]] = {}
		for item in get_document_menu_descriptors():
			if item.kind == "command":
				menu_items[item.label] = menu.Append(wx.ID_ANY, _(item.label))
				continue
			submenu = wx.Menu()
			menu_items[item.label] = menu.AppendSubMenu(submenu, _(item.label))
			submenu_items[item.action] = {}
			for format_label in item.formats:
				submenu_item = submenu.Append(wx.ID_ANY, _(format_label))
				submenu_items[item.action][format_label.casefold()] = submenu_item
		return menu_items, submenu_items

	def _bind_document_menu_handlers(
		self,
		menu: wx.Menu,
		menu_items: dict[str, wx.MenuItem],
		submenu_items: dict[str, dict[str, wx.MenuItem]],
	) -> None:
		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["Open"])
		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["Delete"])
		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["Delete All"])
		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["Add"])
		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["Rename"])
		menu.Bind(wx.EVT_MENU, self.on_import_document, menu_items["Import"])
		for format_key, submenu_item in submenu_items.get("export", {}).items():
			menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_document(fmt), submenu_item)
		for format_key, submenu_item in submenu_items.get("export_all", {}).items():
			menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_all_documents(fmt), submenu_item)

	def _sync_document_menu_state(self, menu_items: dict[str, wx.MenuItem] | None = None) -> None:
		target_items = menu_items if menu_items is not None else getattr(self, "_document_menu_items", None)
		if not target_items or not hasattr(self, "documents") or not hasattr(self, "_selected_document_name"):
			return
		selected_document = self._get_selected_document() if "document_list" in self.__dict__ else None
		menu_state = get_document_menu_enabled_state(
			has_selection=selected_document is not None,
			has_documents=bool(self.documents),
		)
		for label, enabled in menu_state.items():
			menu_item = target_items.get(label)
			if menu_item is not None:
				menu_item.Enable(enabled)

	def _update_window_title(self) -> None:
		self.SetTitle(_(format_window_title(self._open_document_name)))

	def _create_dual_view_frame(self) -> DualViewFrame:
		return DualViewFrame(self, title=_("Dual View"), on_closed=self._on_dual_view_closed)

	def _on_dual_view_closed(self, viewer: DualViewFrame) -> None:
		if self._dual_view_frame is viewer:
			self._dual_view_frame = None

	def _render_dual_view_for_open_document(self) -> str:
		results = self._dual_view_results_by_document.get(self._open_document_name or "", ())
		return render_dual_view_html(
			build_dual_view_model(results),
			empty_message=_("No conversion data is available for this document."),
		)

	def _refresh_dual_view(self) -> None:
		if self._dual_view_frame is not None:
			self._dual_view_frame.refresh_html(self._render_dual_view_for_open_document())

	def _show_dual_view(self) -> None:
		if self._dual_view_frame is None:
			self._dual_view_frame = self._create_dual_view_frame()
		self._refresh_dual_view()
		self._dual_view_frame.Show()
		if self._dual_view_frame.IsIconized():
			self._dual_view_frame.Iconize(False)
		self._dual_view_frame.Raise()

	def _rename_dual_view_result(self, old_name: str, new_name: str) -> None:
		if old_name in self._dual_view_results_by_document:
			self._dual_view_results_by_document[new_name] = self._dual_view_results_by_document.pop(old_name)

	def _delete_dual_view_result(self, name: str) -> None:
		self._dual_view_results_by_document.pop(name, None)

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

	def _register_output_font(self) -> bool:
		return register_private_font_for_windows(get_simbraille_font_path(resource_path(".")))

	def _apply_editor_view_settings(self, settings: ViewSettings) -> None:
		settings = normalize_view_settings(settings)
		input_font = self.input_txt.GetFont()
		input_font.SetPointSize(settings.font_size)
		self.input_txt.SetFont(input_font)

		output_font = wx.Font(self._default_output_font)
		output_font.SetPointSize(settings.font_size)
		if (
			settings.braille_font == "simbraille"
			and (self._simbraille_font_available or sys.platform == "win32")
		):
			output_font.SetFaceName(SIMBRAILLE_FACE_NAME)
		self.output_txt.SetFont(output_font)

		colors = VIEW_SCHEMES[settings.scheme]
		for control in (self.input_txt, self.output_txt):
			control.SetBackgroundColour(colors["background"])
			control.SetForegroundColour(colors["foreground"])
			control.Refresh()
		self.Layout()

	def _refresh_dictionary_names(self, preferred_name: str | None = None) -> str:
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names[:] = list_dictionary_names(self.dictionary_dir)
		selected_name = resolve_management_selection(self._dictionary_names, preferred_name)
		return selected_name

	def get_dictionary_names_for_dialog(self) -> list[str]:
		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		return list(self._dictionary_names)

	def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		return DotExpressSettingsSnapshot.create(
			normalize_translation_settings(self.translation_settings, dictionary_names),
			language_map_translate_table,
			normalize_view_settings(self.view_settings),
		)

	def apply_settings_from_dialog(
		self,
		snapshot: DotExpressSettingsSnapshot,
	) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		translation = normalize_translation_settings(snapshot.translation, dictionary_names)
		view = normalize_view_settings(snapshot.view)
		tables = dict(snapshot.translation_tables)

		self.translation_settings = translation
		self.view_settings = view
		language_map_translate_table.clear()
		language_map_translate_table.update(tables)
		self._apply_editor_view_settings(view)

		save_translation_settings(translation)
		save_translation_tables(tables)
		save_view_settings(view)
		return DotExpressSettingsSnapshot.create(translation, tables, view)

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
		return self._get_document_controller().document_names

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

	def on_open_dual_view(self, _evt) -> None:
		self._show_dual_view()

	def on_frame_activate(self, event: wx.ActivateEvent) -> None:
		viewer = self._dual_view_frame
		if event.GetActive() and viewer is not None and viewer.IsShown() and not viewer.IsIconized():
			viewer.raise_without_activating()
		event.Skip()

	def _sort_documents(self) -> None:
		self._get_document_controller().sort_documents()

	def _get_document_by_name(self, name: str | None) -> Document | None:
		return self._get_document_controller().get_document(name)

	def _replace_document(self, updated_document: Document) -> None:
		self._get_document_controller().replace_document(updated_document)

	def _document_name_exists(self, name: str, exclude_name: str | None = None) -> bool:
		return document_name_exists(self._get_document_controller().documents, name, exclude_name=exclude_name)

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
		documents = self.documents
		for document in documents:
			self.document_list.InsertItem(self.document_list.GetItemCount(), document.name)
		if not documents:
			self._selected_document_name = None
			self._sync_document_menu_state()
			return
		selected_name = preferred_name if preferred_name in self._get_document_names() else documents[0].name
		self._selected_document_name = selected_name
		for index, document in enumerate(documents):
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

	def _reset_input_cursor_to_start(self) -> None:
		self.input_txt.SetInsertionPoint(0)
		self.input_txt.ShowPosition(0)

	def _get_txt_wildcard(self) -> str:
		return _(TXT_WILDCARD)

	def _get_import_wildcard(self, format_key: str) -> str:
		descriptor = get_format(format_key)
		return _(f"{descriptor.wildcard_label} (*{descriptor.extension})|*{descriptor.extension}")

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
			),
			runtime=self.translation_runtime,
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

	def _export_document_with_dialog(self, document: Document, format_key: str) -> None:
		descriptor = get_format(format_key)
		default_file = f"{document.name}{descriptor.extension}"
		wildcard = self._get_dep_wildcard() if descriptor.key == "dep" else self._get_brl_wildcard()
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
		target_suffix = descriptor.extension
		if destination_path.suffix.casefold() != target_suffix:
			destination_path = destination_path.with_suffix(target_suffix)
		if document.braille is None:
			self._start_export_conversion(
				document,
				destination_path,
				format_key,
				on_success=lambda braille: self._continue_single_export(
					Document(document.name, document.text, braille),
					destination_path,
					format_key,
				),
				on_error=lambda message: wx.MessageBox(
					message,
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=self,
				),
			)
			return
		self._continue_single_export(document, destination_path, format_key)

	def _set_view_font_size(self, font_size: int) -> None:
		self.view_settings = normalize_view_settings(
			replace(self.view_settings, font_size=font_size)
		)
		self._apply_editor_view_settings(self.view_settings)
		save_view_settings(self.view_settings)
		DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)

	def _open_document_by_name(self, name: str | None) -> None:
		document = self._get_document_controller().open_document(name)
		if document is None:
			self._clear_document_editors()
			self._update_window_title()
			self._refresh_dual_view()
			return
		self._load_document_into_editors(document)
		self._reset_input_cursor_to_start()
		self._refresh_document_list(self._selected_document_name)
		self._update_window_title()
		self._refresh_dual_view()

	def _open_adjacent_document(self, step: int) -> None:
		target_name = get_adjacent_document_name(
			self.documents,
			self._open_document_name or self._selected_document_name,
			step,
		)
		if not target_name:
			return
		if not self._save_open_document_with_feedback():
			return
		self._open_document_by_name(target_name)
		self.input_txt.SetFocus()

	def _save_open_document(self) -> None:
		if not self._open_document_name:
			return
		document = self._get_document_by_name(self._open_document_name)
		if document is None:
			return
		updated_document, _ = prepare_document_for_save(
			document,
			text=self.input_txt.GetValue(),
			braille=self.output_txt.GetValue(),
		)
		self._replace_document(updated_document)
		save_document_package(document_package_path_for_name(updated_document.name, self.workspace_dir), updated_document)

	def _save_open_document_with_feedback(self) -> bool:
		try:
			self._save_open_document()
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return False
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
		documents = self.documents
		if documents:
			self._open_document_by_name(documents[0].name)
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
		documents, invalid_paths = load_workspace_documents(self.workspace_dir)
		self.documents = documents
		self._refresh_document_list()
		self._review_invalid_workspace_files(invalid_paths)
		self._ensure_open_document_exists()
		self._update_window_title()

	def _get_selected_document_name(self) -> str | None:
		if "document_list" not in self.__dict__:
			return self._selected_document_name
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
		menu_items, submenu_items = self._append_document_menu_items(menu)
		self._bind_document_menu_handlers(menu, menu_items, submenu_items)
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
		renamed_document = self._document_controller.rename_document(selected_document.name, new_name)
		if renamed_document is None:
			return
		self._refresh_document_list(renamed_document.name)
		self._update_window_title()
		self._refresh_dual_view()

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
		try:
			package_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
			if package_path.exists():
				package_path.unlink()
		except OSError as exc:
			self._show_file_error(_("Failed to delete document: {error}"), exc)
			return
		delete_decision = self._document_controller.delete_document(selected_document.name)
		self._refresh_document_list(self._selected_document_name)
		if self.documents:
			if delete_decision.was_open and self._open_document_name:
				self._open_document_by_name(self._open_document_name)
		else:
			self._update_window_title()
			self._clear_document_editors()
			self._ensure_open_document_exists()
		self._refresh_dual_view()

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
				self._document_controller.restore_documents_after_delete_all_failure(remaining_documents)
				self._refresh_document_list()
				self._review_invalid_workspace_files(invalid_paths)
				if self.documents:
					self._open_document_by_name(self.documents[0].name)
				else:
					self._clear_document_editors()
				self._refresh_dual_view()
				return
		self._document_controller.delete_all_documents()
		self._update_window_title()
		self._refresh_document_list()
		self._clear_document_editors()
		self._ensure_open_document_exists()
		self._refresh_dual_view()

	def on_import_document(self, _evt) -> None:
		if not self._save_open_document_with_feedback():
			return
		with wx.FileDialog(
			self,
			_("Import Document"),
			wildcard=build_import_wildcard(_),
			style=wx.FD_OPEN | wx.FD_MULTIPLE,
		) as file_dialog:
			file_dialog.SetFilterIndex(ALL_SUPPORTED_FILTER_INDEX)
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			filter_index = file_dialog.GetFilterIndex()
			import_filters = get_import_filters()
			if filter_index < 0 or filter_index >= len(import_filters):
				filter_index = ALL_SUPPORTED_FILTER_INDEX
			format_key = import_filters[filter_index].key
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
		suffix = get_format(format_key).extension
		conflicts = [destination_dir / f"{document.name}{suffix}" for document in self.documents if (destination_dir / f"{document.name}{suffix}").exists()]
		if conflicts and not self._confirm_overwrite_all(conflicts):
			return
		self._export_next_document(list(self.documents), destination_dir, format_key, ExportBatchResult())

	def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
		step = get_font_size_step_from_wheel(event.GetWheelRotation(), event.ControlDown())
		if step == 0:
			event.Skip()
			return
		self._set_view_font_size(self.view_settings.font_size + step)

	def on_open_settings(self, _event) -> None:
		DotExpressSettingsDialog.show_singleton(
			parent=self,
			snapshot=self.get_settings_snapshot(),
			dictionary_names=self.get_dictionary_names_for_dialog(),
			commit=self.apply_settings_from_dialog,
			initial_category=TranslationSettingsPanel,
		)

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
					self._export_document_with_dialog(document, get_format("brl").key)
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
		if is_document_import_txt_shortcut(event.GetKeyCode(), event.ControlDown()):
			self.on_import_document(None)
			return
		document_cycle_step = is_document_cycle_shortcut(
			event.GetKeyCode(),
			event.ControlDown(),
			event.ShiftDown(),
		)
		if document_cycle_step != 0:
			self._open_adjacent_document(document_cycle_step)
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

	def on_open_dictionary_management(self, _evt) -> None:
		selected_name = self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
		with DictionaryManagementDialog(
			self,
			self._dictionary_names,
			selected_name,
			self.dictionary_dir,
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

	def add_dictionary(self, parent: wx.Window | None) -> str | None:
		dialog_parent = parent or self
		try:
			path = prompt_dictionary_name_until_success(
				"",
				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
					dialog_parent,
					title=_("Add Dictionary"),
					initial_name=initial_name,
				),
				on_submit=lambda dictionary_name: create_dictionary(self.dictionary_dir, dictionary_name),
				on_duplicate=lambda dictionary_name: wx.MessageBox(
					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=dialog_parent,
				),
			)
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
			return None
		if path is None:
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
		try:
			path = prompt_dictionary_name_until_success(
				selected_name,
				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
					dialog_parent,
					title=_("Rename Dictionary"),
					initial_name=initial_name,
				),
				on_submit=lambda dictionary_name: rename_dictionary_after_name_prompt(
					self.dictionary_dir,
					selected_name,
					dictionary_name,
				),
				on_duplicate=lambda dictionary_name: wx.MessageBox(
					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=dialog_parent,
				),
			)
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
			return None
		except OSError as exc:
			self._show_file_error(_("Failed to save dictionary: {error}"), exc, parent=dialog_parent)
			return None
		if path is None:
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

		try:
			path = prompt_dictionary_name_until_success(
				source_path.stem,
				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
					dialog_parent,
					title=_("Add Dictionary"),
					initial_name=initial_name,
				),
				on_submit=lambda dictionary_name: import_dictionary(self.dictionary_dir, source_path, dictionary_name),
				on_duplicate=lambda dictionary_name: wx.MessageBox(
					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=dialog_parent,
				),
			)
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
		if path is None:
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

	def _write_export_document(self, destination_path: Path, document: Document, format_key: str) -> None:
		descriptor = get_format(format_key)
		if not descriptor.exportable or descriptor.writer is None:
			raise ValueError(f'Unsupported export format: "{format_key}".')
		descriptor.writer(destination_path, document)

	def _continue_single_export(self, document: Document, destination_path: Path, format_key: str) -> None:
		try:
			self._write_export_document(destination_path, document, format_key)
		except OSError as exc:
			self._show_file_error(_("Failed to export document: {error}"), exc)
			return
		wx.MessageBox(
			_("The document was exported successfully."),
			_("Export Complete"),
			wx.OK | wx.ICON_INFORMATION,
			parent=self,
		)

	def _start_export_conversion(
		self,
		document: Document,
		destination_path: Path,
		format_key: str,
		*,
		on_success=None,
		on_error=None,
		on_missing_table=None,
	) -> bool:
		table_file = language_map_translate_table.get("default")
		if not table_file:
			message = _("Please select a translation table first.")
			if on_missing_table is not None:
				on_missing_table(message)
			elif on_error is not None:
				on_error(message)
			return False
		settings = self.translation_settings
		self._start_conversion(
			table_file,
			document.text,
			settings.width,
			settings.output_mode,
			self._get_selected_dictionary_path(),
			on_success=on_success,
			on_error=on_error,
			update_output=False,
			show_success=False,
		)
		return True

	def _export_next_document(
		self,
		remaining: list[Document],
		destination_dir: Path,
		format_key: str,
		result: ExportBatchResult,
	) -> None:
		if not remaining:
			self._show_export_all_result(result)
			return

		descriptor = get_format(format_key)
		document = remaining[0]
		rest = remaining[1:]
		destination_path = destination_dir / f"{document.name}{descriptor.extension}"

		def continue_batch() -> None:
			wx.CallAfter(self._export_next_document, rest, destination_dir, format_key, result)

		def write_document(export_document: Document) -> None:
			try:
				self._write_export_document(destination_path, export_document, format_key)
			except OSError as exc:
				result.add_failure(document.name, str(exc))
			else:
				result.add_success(document.name)
			continue_batch()

		if document.braille is not None:
			write_document(document)
			return

		def conversion_failed(message: str) -> None:
			result.add_failure(document.name, message)
			continue_batch()

		self._start_export_conversion(
			document,
			destination_path,
			format_key,
			on_success=lambda braille: write_document(Document(document.name, document.text, braille)),
			on_error=conversion_failed,
			on_missing_table=conversion_failed,
		)

	def _show_export_all_result(self, result: ExportBatchResult) -> None:
		style = wx.OK | (wx.ICON_INFORMATION if result.all_succeeded else wx.ICON_WARNING)
		message = _(result.summary_template).format(**result.summary_values)
		wx.MessageBox(
			message,
			_(result.summary_title),
			style,
			parent=self,
		)

	def on_convert(self, _evt):
		if self._conversion_runner.is_running():
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
		if self._conversion_runner.is_running() and evt.CanVeto():
			evt.Veto()
			return
		if not self._save_open_document_with_feedback():
			if evt.CanVeto():
				evt.Veto()
			return
		self._close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
			self._dual_view_frame = None
			viewer.Destroy()
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

	def _start_conversion(
		self,
		table_file: str,
		raw_text: str,
		width: int,
		output_mode: str,
		dictionary_path: Path,
		*,
		on_success=None,
		on_error=None,
		update_output: bool = True,
		show_success: bool = True,
	):
		self._set_conversion_busy(True)
		self._close_converting_dialog()
		policy = ConversionCompletionPolicy(
			on_success=on_success,
			on_error=on_error,
			update_output=update_output,
			show_success=show_success,
		)
		job_id = self._conversion_runner.start(
			ConversionJobRequest(
				conversion_request=self._build_conversion_request(
					raw_text,
					table_file,
					output_mode,
					width,
					dictionary_path,
				),
				completion_policy=policy,
			)
		)
		self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)

	def _show_converting_dialog(self, job_id: int):
		if job_id != self._conversion_runner.active_job_id:
			return
		if not self._conversion_runner.is_running():
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

	def _complete_conversion(
		self,
		policy: ConversionCompletionPolicy,
		conversion_output: ConversionOutput | None = None,
		error_message: str | None = None,
		display_text: str | None = None,
	):
		if self._convert_dialog_timer is not None:
			self._convert_dialog_timer.Stop()
			self._convert_dialog_timer = None
		self._close_converting_dialog()
		self._set_conversion_busy(False)
		on_success = policy.on_success
		on_error = policy.on_error
		update_output = policy.update_output
		show_success = policy.show_success

		if error_message is not None:
			if on_error is not None:
				on_error(error_message)
			else:
				wx.MessageBox(
					error_message,
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=self,
				)
			return

		output = conversion_output or ConversionOutput(display_text or "", ())
		converted_braille = output.display_text
		if update_output:
			self.output_txt.SetValue(converted_braille)
			self.output_txt.SetFocus()
			if self._open_document_name:
				document = self._get_document_by_name(self._open_document_name)
				if document is not None:
					self._replace_document(
						Document(
							document.name,
							self.input_txt.GetValue(),
							converted_braille,
						)
					)
				self._dual_view_results_by_document[self._open_document_name] = output.dual_view_segments
			self._refresh_dual_view()
		if on_success is not None:
			on_success(converted_braille)
		if show_success:
			wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def _finish_conversion_success(self, result: ConversionJobSuccess) -> None:
		self._complete_conversion(result.completion_policy, conversion_output=result.conversion_output)

	def _finish_conversion_failure(self, result: ConversionJobFailure) -> None:
		message_template = _("ASCII conversion failed: {error}") if result.error.stage == "ascii" else _("Translation failed: {error}")
		self._complete_conversion(
			result.completion_policy,
			error_message=message_template.format(error=get_public_error_message(result.error.error)),
		)


class BrailleApp(wx.App):
	def OnInit(self):
		self.translation_runtime = build_default_translation_runtime()
		self.frame = BrailleFrame(None, runtime=self.translation_runtime)
		self.frame.Show()
		start_client_init_background()
		return True

	def OnExit(self):
		self.translation_runtime.close()
		return 0


if __name__ == "__main__":
	app = BrailleApp()
	app.MainLoop()
