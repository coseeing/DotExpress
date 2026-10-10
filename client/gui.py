from dataclasses import replace
from pathlib import Path
import sys
import webbrowser

import wx

import about
from i18n import _, resource_path
from app_paths import ApplicationDataError, ApplicationPaths, build_application_paths, prepare_application_directories
from conversion.contracts import TranslationRuntime
from adapters.translation.provider import build_default_translation_runtime
from conversion.math_service import latex_to_mathml
from conversion.service import ConversionRequest
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.manager import dictionary_path_for_name
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_unreadable_dictionary, log_dictionary_read_error
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
from documents.formats import DocumentFormatDescriptor, build_export_wildcard, get_format
from documents.session import (
    format_window_title,
)
from documents.workspace import (
    BatchIssue,
    DEFAULT_DOCUMENT_NAME,
    Document,
    create_default_document,
    normalize_document_name,
    replace_lone_surrogates,
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
from ui.conversion_presenter import ConversionPresenter
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from ui.menu_builder import apply_document_menu_state, build_document_menu
from ui.message_box import message_box
from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
from settings.translation import (
	TranslationSettings,
	load_translation_settings,
	normalize_translation_settings,
	save_translation_settings,
)
from settings.translation_tables import load_translation_tables, save_translation_tables
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
from dual_view.browser import open_html_in_browser
from dual_view.files import cleanup_dual_view_html, write_dual_view_html
from dual_view.model import build_dual_view_model
from log import get_logger
from ui.dual_view import DualViewFrame
from ui.translation_menu import get_translation_menu_items
from client_init import start_client_init_background

from dialog import (
	ConvertingDialog,
	DictionaryEntriesDialog,
	DictionaryManagementDialog,
	DocumentNameDialog,
	FileIssuesDialog,
	InvalidWorkspaceFilesDialog,
)
from settings.view import (
	ViewSettings,
	load_view_settings,
	normalize_view_settings,
	save_view_settings,
)
from settings.state import DotExpressSettingsSnapshot
from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog, TranslationSettingsPanel
from settings.options import BRAILLE_FONT_SIMBRAILLE, VIEW_SCHEME_OPTIONS


VIEW_SCHEMES = {
	option.value: {
		"background": wx.Colour(*option.background),
		"foreground": wx.Colour(*option.foreground),
	}
	for option in VIEW_SCHEME_OPTIONS
}

logger = get_logger("dotexpress.gui", "gui.log")


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
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False

	def __init__(
		self,
		*args,
		runtime: TranslationRuntime,
		paths: ApplicationPaths,
		config_store: ConfigStore,
		**kwargs,
	):
		super().__init__(*args, **kwargs)
		self.translation_runtime = runtime
		self._paths = paths
		self._config_store = config_store
		self._document_controller = DocumentController()

		self._initialize_frame()
		initial_settings = self._initialize_state()
		self._create_main_layout(initial_settings)
		self._initialize_conversion_state()
		self._apply_initial_settings(initial_settings)
		self._bind_events()
		self._load_startup_documents()

	def _initialize_frame(self) -> None:
		self.SetSize((900, 600))
		self.SetMenuBar(self._create_menu_bar())

	def _initialize_state(self) -> ViewSettings:
		self.dictionary_dir = self._paths.dictionary
		self._dictionary_presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: self.translation_settings.selected_dictionary,
			set_active_name=self._set_active_dictionary,
		)
		self._dictionary_presenter.refresh()
		self.translation_settings = load_translation_settings(
			self._config_store,
			self._dictionary_presenter.dictionary_names,
		)
		self.translation_tables = load_translation_tables(self._config_store) or DEFAULT_TRANSLATION_TABLES.copy()
		self._workspace_service = DocumentWorkspaceService(self._document_controller, self._paths.workspace)
		self._simbraille_font_available = self._register_output_font()
		self._dual_view_frame: DualViewFrame | None = None

		self.view_settings = load_view_settings(self._config_store)
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
		self._convert_dialog = None
		self._conversion_presenter = ConversionPresenter(
			self,
			self._document_controller,
			runtime=self.translation_runtime,
			build_request=self._build_conversion_request_for_text,
			get_translation_tables=lambda: self.translation_tables,
			call_after=wx.CallAfter,
			call_later=wx.CallLater,
		)
		self._export_coordinator = ExportCoordinator(
			self,
			self._document_controller,
			self._conversion_presenter,
			call_after=wx.CallAfter,
		)

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
			"text_processing": self.on_open_text_processing,
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
		menu_items = self._append_document_menu(menu)
		self._sync_document_menu_state(menu_items)
		return menu, menu_items

	def _document_menu_handlers(self) -> dict[str, object]:
		return {
			"open": self.on_open_document,
			"delete": self.on_delete_document,
			"delete_all": self.on_delete_all_documents,
			"add": self.on_add_document,
			"rename": self.on_rename_document,
			"import": self.on_import_document,
			"export": self.on_export_document,
			"export_all": self.on_export_all_documents,
		}

	def _append_document_menu(self, menu: wx.Menu) -> dict[str, wx.MenuItem]:
		return build_document_menu(
			menu,
			self._document_menu_handlers(),
			translate=_,
			new_menu=wx.Menu,
			menu_event=wx.EVT_MENU,
			item_id=wx.ID_ANY,
		)

	def _sync_document_menu_state(self, menu_items: dict[str, wx.MenuItem] | None = None) -> None:
		target_items = menu_items if menu_items is not None else getattr(self, "_document_menu_items", None)
		if not target_items:
			return
		selected_document = self._get_selected_document() if "document_list" in self.__dict__ else None
		menu_state = get_document_menu_enabled_state(
			has_selection=selected_document is not None,
			has_documents=self._document_controller.has_documents,
		)
		apply_document_menu_state(target_items, menu_state)

	def _update_window_title(self) -> None:
		self.SetTitle(_(format_window_title(self._document_controller.open_document_name)))

	def _create_dual_view_frame(self) -> DualViewFrame:
		return DualViewFrame(self, title=_("Dual View"), on_closed=self._on_dual_view_closed)

	def _on_dual_view_closed(self, viewer: DualViewFrame) -> None:
		if self._dual_view_frame is viewer:
			self._dual_view_frame = None

	def _render_dual_view_for_open_document(self) -> str:
		controller = self._document_controller
		results = controller.get_dual_view_results(controller.open_document_name)
		return render_dual_view_html(
			build_dual_view_model(results, mathml_converter=latex_to_mathml),
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

	def _open_dual_view_in_browser(self) -> None:
		try:
			html_path = write_dual_view_html(self._render_dual_view_for_open_document(), self._paths.dual_view)
			width, height = self.GetSize()
			open_html_in_browser(html_path, (width, height))
		except Exception as error:
			logger.exception("Failed to open dual view")
			self._show_file_error(_("Failed to open dual view: {error}"), error)

	def _set_control_accessible_name(
		self,
		control: wx.Window,
		name: str,
		description: str = "",
	) -> None:
		control.SetName(name)
		control.SetAccessible(NamedControlAccessible(control, name, description))

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
			settings.braille_font == BRAILLE_FONT_SIMBRAILLE
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

	def get_dictionary_names_for_dialog(self) -> list[str]:
		self._dictionary_presenter.refresh(self.translation_settings.selected_dictionary)
		return self._dictionary_presenter.dictionary_names

	def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		return DotExpressSettingsSnapshot.create(
			normalize_translation_settings(self.translation_settings, dictionary_names),
			self.translation_tables,
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
		self.translation_tables = tables
		self._apply_editor_view_settings(view)

		save_translation_settings(self._config_store, translation)
		save_translation_tables(self._config_store, tables)
		save_view_settings(self._config_store, view)
		return DotExpressSettingsSnapshot.create(translation, tables, view)

	def _set_active_dictionary(self, selected_name: str) -> None:
		self.translation_settings = TranslationSettings(
			output_mode=self.translation_settings.output_mode,
			width=self.translation_settings.width,
			selected_dictionary=selected_name,
		)
		self._config_store.set_selected_dictionary(selected_name)

	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _show_file_error(self, message: str, error: Exception) -> None:
		message_box(
			message.format(error=error),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=self,
		)

	def _log_unexpected_save_error(self, error: Exception) -> None:
		"""Log the traceback of a failed document save if it is not an ``OSError``.

		An ``OSError`` (locked, read-only, disk full) is expected and the message
		names it fully. Anything else means a bug or bad data in memory, and the
		packaged build has no console, so its traceback goes to ``gui.log``.
		"""
		if not isinstance(error, OSError):
			logger.error("Unexpected error while saving a document", exc_info=error)

	def _show_document_save_error(self, error: Exception) -> None:
		"""Report a failed document save; log the traceback if it is not an ``OSError``."""
		self._log_unexpected_save_error(error)
		self._show_file_error(_("Failed to save document: {error}"), error)

	def _ask_after_close_save_failure(self, error: Exception) -> int:
		"""Ask what Close does after a failed save (F-5 D7).

		``wx.ID_YES``: retry; ``wx.ID_NO``: close without saving; anything else: cancel.
		A Windows task dialog: Retry is the default, Esc and the close box cancel.
		"""
		with wx.MessageDialog(
			self,
			_("Failed to save document: {error}").format(error=error),
			_("Cannot Save Document"),
			wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,
		) as dialog:
			dialog.SetExtendedMessage(
				_("Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost.")
			)
			dialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))
			return dialog.ShowModal()

	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
		try:
			webbrowser.open(about.url)
		except Exception as exc:
			self._show_file_error(_("Failed to open website: {error}"), exc)

	def on_about(self, _evt: wx.CommandEvent) -> None:
		message_box(about.aboutMessage, _("About DotExpress"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def on_open_dual_view(self, _evt) -> None:
		self._open_dual_view_in_browser()

	def on_open_text_processing(self, _event) -> None:
		try:
			TextProcessingDialog.show_singleton(
				parent=self,
				script_path=preprocessing_script_path(self.dictionary_dir),
			)
		except OSError as error:
			message_box(
				_("Unable to open text processing script: {error}").format(error=error),
				_("Text Processing"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)

	def on_frame_activate(self, event: wx.ActivateEvent) -> None:
		viewer = self._dual_view_frame
		if event.GetActive() and viewer is not None and viewer.IsShown() and not viewer.IsIconized():
			viewer.raise_without_activating()
		event.Skip()

	def _clear_document_selection(self) -> None:
		selection = self.document_list.GetFirstSelected()
		while selection != wx.NOT_FOUND:
			self.document_list.Select(selection, on=0)
			selection = self.document_list.GetFirstSelected()
		self._document_controller.select_document(None)
		self._sync_document_menu_state()

	def _refresh_document_list(self, preferred_name: str | None = None) -> None:
		controller = self._document_controller
		controller.sort_documents()
		self.document_list.DeleteAllItems()
		names = controller.document_names
		for name in names:
			self.document_list.InsertItem(self.document_list.GetItemCount(), name)
		if not names:
			controller.select_document(None)
			self._sync_document_menu_state()
			return
		selected_name = preferred_name if preferred_name in names else names[0]
		controller.select_document(selected_name)
		index = names.index(selected_name)
		self.document_list.Select(index)
		self.document_list.Focus(index)
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

	def _build_conversion_request(self, raw_text: str, output_mode: str, width: int, dictionary_path: Path) -> ConversionRequest:
		return ConversionRequest(
			raw_text=raw_text,
			output_mode=output_mode,
			width=width,
			dictionary_path=dictionary_path,
			data_dir=resource_path("data"),
			translation_tables=self.translation_tables.copy(),
			lang=self._config_store.get_lang(),
			charset_maps=self._config_store.get_charset_maps(),
		)

	def _build_conversion_request_for_text(self, raw_text: str) -> ConversionRequest:
		settings = self.translation_settings
		return self._build_conversion_request(
			raw_text,
			settings.output_mode,
			settings.width,
			self._get_selected_dictionary_path(),
		)

	def _format_batch_issue_lines(self, issues: list[BatchIssue]) -> list[str]:
		return [f"{issue.path.name}: {issue.reason}" for issue in issues]

	def _show_file_issues_dialog(self, title: str, message: str, issues: list[BatchIssue]) -> None:
		if not issues:
			return
		with FileIssuesDialog(self, title=title, message=message, issues=self._format_batch_issue_lines(issues)) as dialog:
			dialog.ShowModal()

	def _set_view_font_size(self, font_size: int) -> None:
		self.view_settings = normalize_view_settings(
			replace(self.view_settings, font_size=font_size)
		)
		self._apply_editor_view_settings(self.view_settings)
		save_view_settings(self._config_store, self.view_settings)
		settings_dialog = DotExpressSettingsDialog.open_instance()
		if settings_dialog is not None:
			settings_dialog.sync_font_size(self.view_settings.font_size)

	def _open_document_by_name(self, name: str | None) -> None:
		document = self._document_controller.open_document(name)
		if document is None:
			self._clear_document_editors()
			self._update_window_title()
			self._refresh_dual_view()
			return
		self._load_document_into_editors(document)
		self._reset_input_cursor_to_start()
		self._refresh_document_list(self._document_controller.selected_document_name)
		self._update_window_title()
		self._refresh_dual_view()

	def _open_adjacent_document(self, step: int) -> None:
		target_name = self._document_controller.adjacent_document_name(step)
		if not target_name:
			return
		if not self._save_open_document_with_feedback():
			return
		self._open_document_by_name(target_name)
		self.input_txt.SetFocus()

	def _editor_text(self, control: wx.TextCtrl) -> str:
		"""The control's text with each lone surrogate replaced by U+FFFD (F-7, M-7); the control is not changed."""
		return replace_lone_surrogates(control.GetValue())

	def _save_open_document(self) -> None:
		self._workspace_service.save_open_document(
			text=self._editor_text(self.input_txt),
			braille=self._editor_text(self.output_txt),
		)

	def _save_open_document_with_feedback(self) -> bool:
		try:
			self._save_open_document()
		except Exception as exc:
			self._show_document_save_error(exc)
			return False
		return True

	def _save_open_document_before_close(self, can_veto: bool) -> bool:
		"""Save before closing; ``True`` if the frame may close (F-5 D6, D8).

		A failed save asks: Retry saves again, Close without saving drops the edits
		since the last good save (the package keeps that save), Cancel keeps the
		frame open. A close that cannot be vetoed only logs the failure.
		"""
		while True:
			try:
				self._save_open_document()
				return True
			except Exception as error:
				if not can_veto:
					logger.error("Failed to save the open document while closing", exc_info=error)
					return True
				self._log_unexpected_save_error(error)
				answer = self._ask_after_close_save_failure(error)
				if self._close_finished:
					# A nested close that could not be vetoed closed the frame meanwhile (F-7, M-5).
					return True
				if answer == wx.ID_YES:
					continue
				return answer == wx.ID_NO

	def _review_invalid_workspace_files(self, invalid_paths: list[Path]) -> None:
		if not invalid_paths:
			return
		with InvalidWorkspaceFilesDialog(self, invalid_paths) as dialog:
			dialog.ShowModal()
			delete_invalid = dialog.should_delete_invalid_files()
		if not delete_invalid:
			return
		self._workspace_service.delete_invalid_files(
			invalid_paths,
			on_error=lambda exc: self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc),
		)

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
			self._workspace_service.create_document(document)
		except Exception as exc:
			self._show_document_save_error(exc)
			return False
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
			# A package on disk that is not listed (kept invalid at startup) counts too (F-8).
			if self._document_controller.document_name_exists(
				document_name, exclude_name=exclude_name
			) or self._workspace_service.package_name_taken(document_name, exclude_name=exclude_name):
				message_box(
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
			# "new (2)", "new (3)", ... when a package that is not listed holds "new" (F-8).
			self._workspace_service.free_document_name(DEFAULT_DOCUMENT_NAME),
			default_document.text,
			default_document.braille,
			focus_input=True,
		)

	def _ensure_open_document_exists(self) -> None:
		first_name = self._document_controller.first_document_name
		if first_name is not None:
			self._open_document_by_name(first_name)
			return
		self._create_default_document()

	def _load_workspace_documents_at_startup(self) -> None:
		invalid_paths = self._workspace_service.load_documents()
		self._refresh_document_list()
		self._review_invalid_workspace_files(invalid_paths)
		self._ensure_open_document_exists()
		self._update_window_title()

	def _get_selected_document_name(self) -> str | None:
		controller = self._document_controller
		if "document_list" not in self.__dict__:
			return controller.selected_document_name
		name = controller.document_name_at(self.document_list.GetFirstSelected())
		return name if name is not None else controller.selected_document_name

	def _get_selected_document(self) -> Document | None:
		return self._document_controller.get_document(self._get_selected_document_name())

	def on_document_selection_changed(self, event: wx.ListEvent) -> None:
		controller = self._document_controller
		controller.select_document(controller.document_name_at(self.document_list.GetFirstSelected()))
		self._sync_document_menu_state()
		event.Skip()

	def on_document_activated(self, _event: wx.ListEvent) -> None:
		self.on_open_document(None)

	def on_document_context_menu(self, event: wx.ContextMenuEvent) -> None:
		position = event.GetPosition()
		client_position = self.document_list.ScreenToClient(position) if position != wx.DefaultPosition else wx.Point(0, 0)
		item_index, _flags = self.document_list.HitTest(client_position)
		selected_index = self.document_list.GetFirstSelected()
		item_name = self._document_controller.document_name_at(item_index)
		if item_name is not None:
			self.document_list.Select(item_index)
			self.document_list.Focus(item_index)
			self._document_controller.select_document(item_name)
		elif position == wx.DefaultPosition and selected_index != wx.NOT_FOUND:
			item_index = selected_index
		else:
			self._clear_document_selection()
		rect = self.document_list.GetItemRect(item_index) if item_index != wx.NOT_FOUND and item_index < self.document_list.GetItemCount() else None
		menu = wx.Menu()
		menu_items = self._append_document_menu(menu)
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
		selected_document = self._document_controller.get_document(selected_name)
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		selected_document = self._document_controller.get_document(selected_name)
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
			renamed_document = self._workspace_service.rename_document(selected_document.name, new_name)
		except Exception as exc:
			self._show_document_save_error(exc)
			return
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
		confirmation = message_box(
			_('Do you want to delete document "{name}"?').format(name=selected_document.name),
			_("Confirm Delete Document"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			parent=self,
		)
		if confirmation != wx.YES:
			return
		try:
			delete_decision = self._workspace_service.delete_document(selected_document.name)
		except OSError as exc:
			self._show_file_error(_("Failed to delete document: {error}"), exc)
			return
		self._refresh_document_list(self._document_controller.selected_document_name)
		if self._document_controller.has_documents:
			open_name = self._document_controller.open_document_name
			if delete_decision.was_open and open_name:
				self._open_document_by_name(open_name)
		else:
			self._update_window_title()
			self._clear_document_editors()
			self._ensure_open_document_exists()
		self._refresh_dual_view()

	def on_delete_all_documents(self, _evt) -> None:
		if not self._document_controller.has_documents:
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = message_box(
			_("Delete All will remove all documents. Do you want to continue?"),
			_("Confirm Delete All"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
			parent=self,
		)
		if confirmation != wx.YES:
			return
		result = self._workspace_service.delete_all_documents(
			on_error=lambda exc: self._show_file_error(_("Failed to delete document: {error}"), exc),
		)
		if not result.completed:
			self._refresh_document_list()
			self._review_invalid_workspace_files(result.invalid_paths)
			if self._document_controller.has_documents:
				self._open_document_by_name(self._document_controller.first_document_name)
			else:
				self._clear_document_editors()
			self._refresh_dual_view()
			return
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
		result = self._workspace_service.import_files(source_paths, format_key=format_key)
		if len(result.saved) == 1:
			self._open_document_by_name(result.saved[0].name)
		else:
			controller = self._document_controller
			self._refresh_document_list(controller.open_document_name or controller.selected_document_name)
		self._show_file_issues_dialog(
			_("Import Issues"),
			_("Some files were skipped during import."),
			result.issues,
		)

	def on_export_document(self, format_key: str) -> None:
		selected_document = self._get_selected_document()
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		selected_document = self._get_selected_document() or selected_document
		self._export_coordinator.export_document(selected_document, format_key)

	def on_export_all_documents(self, format_key: str) -> None:
		if not self._document_controller.has_documents:
			return
		if not self._save_open_document_with_feedback():
			return
		self._export_coordinator.export_all(format_key)

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
				controller = self._document_controller
				document = controller.get_document(controller.open_document_name)
				if document is not None:
					self._export_coordinator.export_document(document, get_format("brl").key)
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
		selected_name = self._dictionary_presenter.refresh(self.translation_settings.selected_dictionary)
		with DictionaryManagementDialog(self, self._dictionary_presenter, selected_name) as dialog:
			result = dialog.ShowModal()
			edit_name = dialog.edit_dictionary_name

		if result != wx.ID_EDIT or edit_name is None:
			return
		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
		try:
			editor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path)
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			message_box(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		with editor as entries_dialog:
			entries_dialog.ShowModal()

	def on_convert(self, _evt):
		self._conversion_presenter.convert()

	def _on_close(self, evt: wx.CloseEvent):
		if self._closing:
			self._on_close_reentered(evt)
			return
		self._closing = True
		try:
			self._close(evt)
		finally:
			self._closing = False

	def _close(self, evt: wx.CloseEvent) -> None:
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		may_close = self._save_open_document_before_close(evt.CanVeto())
		if self._close_finished:
			# A nested close that could not be vetoed already closed the frame (M-5).
			return
		if not may_close:
			evt.Veto()
			return
		self._finish_close(evt)

	def _on_close_reentered(self, evt: wx.CloseEvent) -> None:
		"""A close event while another close is still asking (F-7, M-5).

		Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs.
		A close that can be vetoed is vetoed: the open dialog decides. One that cannot
		follows F-5 D8: one save attempt, a logged failure, and the frame closes.
		"""
		if evt.CanVeto():
			evt.Veto()
			return
		self._save_open_document_before_close(False)
		self._finish_close(evt)

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
			self._dual_view_frame = None
			viewer.Destroy()
		evt.Skip()

	# --- ConversionView (ui/conversion_presenter.py) ------------------------

	def get_source_text(self) -> str:
		return self._editor_text(self.input_txt)

	def set_conversion_busy(self, busy: bool) -> None:
		menu_bar = self.GetMenuBar()
		if menu_bar is not None:
			for menu_label in (_("File"), _("Translation")):
				menu_index = menu_bar.FindMenu(menu_label)
				if menu_index != wx.NOT_FOUND:
					menu_bar.EnableTop(menu_index, not busy)
		self.document_list.Enable(not busy)
		self.input_txt.Enable(not busy)

	def show_converting_dialog(self) -> None:
		if self._convert_dialog is not None:
			return
		self._convert_dialog = ConvertingDialog(self)
		self._convert_dialog.Show()
		self._convert_dialog.Raise()

	def close_converting_dialog(self) -> None:
		if self._convert_dialog is None:
			return
		dialog = self._convert_dialog
		self._convert_dialog = None
		dialog.Unbind(wx.EVT_CLOSE)
		dialog.Destroy()

	def show_conversion_output(self, text: str) -> None:
		self.output_txt.SetValue(text)
		self.output_txt.SetFocus()

	def refresh_dual_view(self) -> None:
		self._refresh_dual_view()

	def show_info(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_ERROR, parent=self)

	# --- ExportView (documents/export_coordinator.py) -----------------------

	def show_warning(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_WARNING, parent=self)

	def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None:
		wildcard = build_export_wildcard(descriptor, _)
		with wx.FileDialog(
			self,
			_("Export Document"),
			defaultFile=default_file,
			wildcard=wildcard,
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())

	def choose_export_directory(self) -> Path | None:
		with wx.DirDialog(self, _("Export All Documents")) as dir_dialog:
			if dir_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(dir_dialog.GetPath())

	def confirm_overwrite_all(self, conflicts: list[Path]) -> bool:
		if not conflicts:
			return True
		message = _(
			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
		)
		return (
			message_box(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
		)

def _show_application_data_error(error: ApplicationDataError) -> None:
	message_box(
		_(
			"DotExpress cannot write to its application data directory:\n"
			"{path}\n\nChoose a writable installation or execution location.\n\n{error}"
		).format(path=error.path, error=error.cause),
		_("Startup Error"),
		wx.OK | wx.ICON_ERROR,
	)


class BrailleApp(wx.App):
	def OnInit(self):
		paths = build_application_paths()
		self.paths = paths
		try:
			prepare_application_directories(paths)
			cleanup_dual_view_html(paths.dual_view)
		except ApplicationDataError as error:
			_show_application_data_error(error)
			return False
		except OSError as cause:
			error = ApplicationDataError(paths.dual_view, cause)
			_show_application_data_error(error)
			return False

		config_store = ConfigStore(paths.config)
		self.translation_runtime = build_default_translation_runtime()
		self.frame = BrailleFrame(
			None,
			runtime=self.translation_runtime,
			paths=paths,
			config_store=config_store,
		)
		self.frame.Show()
		start_client_init_background(config_store)
		return True

	def OnExit(self):
		paths = getattr(self, "paths", None)
		if paths is not None:
			try:
				cleanup_dual_view_html(paths.dual_view)
			except OSError:
				logger.exception("Failed to clean up dual-view HTML")
		runtime = getattr(self, "translation_runtime", None)
		if runtime is not None:
			runtime.close()
		return 0


if __name__ == "__main__":
	app = BrailleApp()
	app.MainLoop()
