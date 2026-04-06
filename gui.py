from pathlib import Path
import gettext
import sys
import threading
import zipfile

import wx

import louisHelper
from action_menu import (
	build_actions_button_label,
	get_actions_menu_position,
	get_dictionary_action_labels,
	get_document_action_labels,
	get_document_export_format_labels,
	get_document_import_format_labels,
)
from config import (
	DEFAULT_CONVERSION_WIDTH,
	DEFAULT_OUTPUT_MODE,
	DEFAULT_TRANSLATION_TABLES,
	DEFAULT_VIEW_FONT_SIZE,
	DEFAULT_VIEW_SCHEME,
	DEFAULT_BRAILLE_FONT,
	get_braille_font,
	get_conversion_width,
	get_output_mode,
	get_selected_dictionary,
	get_translation_tables,
	get_view_font_size,
	get_view_scheme,
	set_conversion_width,
	set_output_mode,
	set_selected_dictionary,
	set_translation_tables,
	set_view_font_size,
	set_view_scheme,
	set_braille_font,
)
from dictionary_manager import (
	DEFAULT_DICTIONARY_NAME,
	choose_selection_after_delete,
	create_dictionary,
	delete_dictionary,
	dictionary_path_for_name,
	ensure_default_dictionary,
	export_dictionary,
	get_dictionary_directory,
	import_dictionary,
	list_dictionary_names,
	resolve_selected_dictionary,
)
from document_workspace import (
	BatchIssue,
	Document,
	batch_export_documents_to_folder,
	batch_import_documents_from_folder,
	choose_selection_after_delete as choose_document_selection_after_delete,
	document_package_path_for_name,
	ensure_workspace_directory,
	export_document_brl,
	get_workspace_directory,
	load_document_package,
	load_text_document,
	load_workspace_documents,
	normalize_document_name,
	prepare_document_for_save,
	save_document_package,
)
from font_support import SIMBRAILLE_FACE_NAME, get_simbraille_font_path, register_private_font_for_windows
from input_shortcuts import is_convert_shortcut
from input_shortcuts import (
	get_font_size_step_from_wheel,
	is_brl_export_shortcut,
	is_convert_shortcut,
	is_document_rename_shortcut,
)

from Bopomofo import normalize_zhuyin_sequence
from dialog import DictionaryNameDialog, DocumentNameDialog, FileIssuesDialog, InvalidWorkspaceFilesDialog, SpeechSymbolsDialog, TranslationTableDialog
from languageDetection import LangChangeCommand, LanguageDetector
from translate import translate, translate_as_single_token, TranslationResult
from utils import apply_dictionary, split_bracket_segments, translate__mapping_char


CONVERSION_WIDTH_MIN = 10
CONVERSION_WIDTH_MAX = 200
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
	_("Open"),
	_("Rename"),
	_("Default"),
	_("Braille Font"),
	_("SimBraille"),
	_("Batch Import"),
	_("Batch Export"),
	_("DEP"),
	_("TXT"),
	_("BRL"),
	_("Delete All"),
)

language_map_translate_table = get_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()



def translate_with_language(table_file: str, text: str, dictionary_path: Path) -> TranslationResult:
	language = [k for k, v in language_map_translate_table.items() if k != "default" and v != ""]
	language_detector = LanguageDetector(language)
	sequence = list(language_detector.add_detected_language_commands([text]))
	bopomofo_path = Path(resource_path("data/Bopomofo2Braille.csv"))

	translate_table = language_map_translate_table["default"]
	translations = []
	for item in sequence:
		if isinstance(item, str):
			result = apply_dictionary(
				item,
				dictionary_path=dictionary_path,
				bopomofo_path=bopomofo_path,
				processing=normalize_zhuyin_sequence,
			)
			raw_segments = split_bracket_segments(result["raw"])
			replacement_segments = split_bracket_segments(result["replacement"])

			for raw_segment, replacement_segment in zip(raw_segments, replacement_segments):
				if raw_segment["atomic"] != replacement_segment["atomic"]:
					raise ValueError("atomic not match")
				if replacement_segment["atomic"]:
					translations.append(translate_as_single_token(translate_table, replacement_segment["text"], raw_segment["text"]))
				else:
					translations.append(translate(translate_table, replacement_segment["text"], raw_segment["text"]))
		elif isinstance(item, LangChangeCommand):
			previous_translate_table = translate_table
			lang = item.lang.split("_")[0]
			try:
				translate_table = language_map_translate_table[lang]
				if translate_table == "":
					translate_table = language_map_translate_table["default"]
			except KeyError:
				translate_table = language_map_translate_table["default"]
			if translate_table != previous_translate_table:
				raw = translations[-1].raw if translations else None
				if raw and not raw[-1].isspace():
					translations.append(translate(previous_translate_table, " ", " "))

	assert translations, "No translatable text segments were found."
	merged = translations[0]
	for segment in translations[1:]:
		merged = merged + segment

	return merged



def translate_and_wrap_both(table_file: str, text: str, width: int, dictionary_path: Path) -> tuple[str, str]:
	"""Translate and wrap, returning both braille and original text lines."""
	translation_result = translate_with_language(table_file, text, dictionary_path)
	translation_result.reclean_braille_endspace()
	translation_result.bind_word_tokens()
	translation_result.reclean_token()
	text, braille = translation_result.wrap(width)
	return text, braille


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
	def __init__(self, window: wx.Window, name: str):
		super().__init__(window)
		self._name = name

	def GetName(self, childId):
		return (wx.ACC_OK, self._name)


class BrailleFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.SetTitle(_("DotExpress"))
		self.SetSize((900, 600))

		self.dictionary_dir = get_dictionary_directory()
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names: list[str] = []
		self._saved_dictionary_name = get_selected_dictionary(DEFAULT_DICTIONARY_NAME)
		self.workspace_dir = get_workspace_directory()
		self.documents: list[Document] = []
		self._simbraille_font_available = self._register_output_font()
		self._selected_document_name: str | None = None
		self._open_document_name: str | None = None

		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		controls_box = wx.BoxSizer(wx.VERTICAL)
		self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
		self._view_schemes = [("light", _("Light")), ("dark", _("Dark"))]
		self._braille_font_options = [("default", _("Default")), ("simbraille", _("SimBraille"))]

		initial_output_mode = self._normalize_output_mode(get_output_mode(DEFAULT_OUTPUT_MODE))
		initial_width = self._clamp_conversion_width(get_conversion_width(DEFAULT_CONVERSION_WIDTH))
		initial_font_size = self._clamp_view_font_size(get_view_font_size(DEFAULT_VIEW_FONT_SIZE))
		initial_scheme = self._normalize_view_scheme(get_view_scheme(DEFAULT_VIEW_SCHEME))
		initial_braille_font = self._normalize_braille_font(get_braille_font(DEFAULT_BRAILLE_FONT))

		conversion_group, conversion_box, conversion_row = self._create_labeled_group(panel, _("Conversion"))
		self.table_btn = wx.Button(conversion_box, label=_("Translation Tables..."))
		output_lbl = wx.StaticText(conversion_box, label=_("Output Format"))
		self.output_choice = wx.Choice(conversion_box, choices=[label for _, label in self._output_modes])
		width_lbl = wx.StaticText(conversion_box, label=_("Width"))
		self.width_spin = wx.SpinCtrl(
			conversion_box,
			min=CONVERSION_WIDTH_MIN,
			max=CONVERSION_WIDTH_MAX,
			initial=initial_width,
		)
		dictionary_lbl = wx.StaticText(conversion_box, label=_("Dictionary"))
		self.dictionary_choice = wx.Choice(conversion_box)
		self.dictionary_choice.SetMinSize((160, -1))
		self.actions_btn = wx.Button(conversion_box, label=build_actions_button_label(_("Actions")))
		self.convert_btn = wx.Button(conversion_box, label=_("Convert"))

		conversion_row.Add(self.table_btn, 0, wx.RIGHT, 8)
		conversion_row.Add(output_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		conversion_row.Add(self.output_choice, 0, wx.RIGHT, 8)
		conversion_row.Add(width_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		conversion_row.Add(self.width_spin, 0, wx.RIGHT, 8)
		conversion_row.Add(dictionary_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		conversion_row.Add(self.dictionary_choice, 0, wx.RIGHT, 8)
		conversion_row.Add(self.actions_btn, 0, wx.RIGHT, 8)
		conversion_row.Add(self.convert_btn, 0)

		controls_box.Add(conversion_group, 0, wx.EXPAND)
		vbox.Add(controls_box, 0, wx.EXPAND | wx.ALL, 8)

		content_box = wx.BoxSizer(wx.HORIZONTAL)
		documents_box = wx.BoxSizer(wx.VERTICAL)
		documents_label = wx.StaticText(panel, label=_("Documents"))
		self.document_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL)
		self.document_list.InsertColumn(0, _("Document Name"), width=220)
		self.document_list.SetMinSize((240, -1))
		self._set_control_accessible_name(self.document_list, _("Document List"))
		documents_box.Add(documents_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		documents_box.Add(self.document_list, 1, wx.EXPAND | wx.ALL, 8)

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
		self._set_control_accessible_name(self.output_txt, _("Braille"))
		editors_box.Add(self.output_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		content_box.Add(documents_box, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 8)
		content_box.Add(editors_box, 1, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 8)
		vbox.Add(content_box, 1, wx.EXPAND)

		panel.SetSizer(vbox)

		self._set_output_mode_selection(initial_output_mode)
		self._set_scheme_selection(initial_scheme)
		self._set_braille_font_selection(initial_braille_font)
		self.width_spin.SetValue(initial_width)
		self.font_size_spin.SetValue(initial_font_size)
		self._convert_thread = None
		self._convert_dialog = None
		self._convert_dialog_timer = None
		self._convert_job_id = 0

		self._refresh_dictionary_choice(self._saved_dictionary_name)
		self._apply_editor_view_settings(initial_font_size, initial_scheme)

		self.table_btn.Bind(wx.EVT_BUTTON, self.on_open_table_dialog)
		self.output_choice.Bind(wx.EVT_CHOICE, self.on_output_mode_change)
		self.width_spin.Bind(wx.EVT_SPINCTRL, self.on_width_change)
		self.width_spin.Bind(wx.EVT_TEXT, self.on_width_change)
		self.dictionary_choice.Bind(wx.EVT_CHOICE, self.on_dictionary_change)
		self.actions_btn.Bind(wx.EVT_BUTTON, self.on_open_dictionary_actions)
		self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
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
		self.Bind(wx.EVT_CLOSE, self._on_close)

		self._clear_document_editors()
		self._load_workspace_documents_at_startup()

	def _set_control_accessible_name(self, control: wx.Window, name: str) -> None:
		control.SetName(name)
		control.SetAccessible(NamedControlAccessible(control, name))

	def _create_labeled_group(self, parent: wx.Window, label: str) -> tuple[wx.StaticBoxSizer, wx.StaticBox, wx.BoxSizer]:
		group = wx.StaticBoxSizer(wx.VERTICAL, parent, label=label)
		box = group.GetStaticBox()
		row = wx.BoxSizer(wx.HORIZONTAL)
		group.Add(row, 0, wx.EXPAND | wx.ALL, 8)
		return group, box, row

	def _clamp_conversion_width(self, width: int) -> int:
		return max(CONVERSION_WIDTH_MIN, min(CONVERSION_WIDTH_MAX, width))

	def _clamp_view_font_size(self, font_size: int) -> int:
		return max(VIEW_FONT_SIZE_MIN, min(VIEW_FONT_SIZE_MAX, font_size))

	def _normalize_output_mode(self, output_mode: str) -> str:
		valid_modes = {mode for mode, _label in self._output_modes}
		return output_mode if output_mode in valid_modes else DEFAULT_OUTPUT_MODE

	def _normalize_view_scheme(self, scheme: str) -> str:
		return scheme if scheme in VIEW_SCHEMES else DEFAULT_VIEW_SCHEME

	def _set_output_mode_selection(self, output_mode: str):
		for index, (mode, _label) in enumerate(self._output_modes):
			if mode == output_mode:
				self.output_choice.SetSelection(index)
				return
		self.output_choice.SetSelection(0)

	def _get_selected_output_mode(self) -> str:
		selection = self.output_choice.GetSelection()
		if selection == wx.NOT_FOUND:
			return DEFAULT_OUTPUT_MODE
		return self._output_modes[selection][0]

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

	def _refresh_dictionary_choice(self, preferred_name: str | None = None) -> None:
		ensure_default_dictionary(self.dictionary_dir)
		self._dictionary_names = list_dictionary_names(self.dictionary_dir)
		selected_name = resolve_selected_dictionary(self._dictionary_names, preferred_name)
		self.dictionary_choice.Clear()
		if self._dictionary_names:
			self.dictionary_choice.AppendItems(self._dictionary_names)
			self.dictionary_choice.SetSelection(self._dictionary_names.index(selected_name))
		set_selected_dictionary(selected_name)

	def _get_selected_dictionary_name(self) -> str:
		selection = self.dictionary_choice.GetSelection()
		if selection == wx.NOT_FOUND or selection >= len(self._dictionary_names):
			return DEFAULT_DICTIONARY_NAME
		return self._dictionary_names[selection]

	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self._get_selected_dictionary_name(), self.dictionary_dir)

	def _get_csv_wildcard(self) -> str:
		return _(CSV_WILDCARD)

	def _show_file_error(self, message: str, error: Exception) -> None:
		wx.MessageBox(
			message.format(error=error),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=self,
		)

	def _get_dep_wildcard(self) -> str:
		return _(DEP_WILDCARD)

	def _get_document_names(self) -> list[str]:
		return [document.name for document in self.documents]

	def _sort_documents(self) -> None:
		self.documents.sort(key=lambda document: (document.name.casefold(), document.name))

	def _get_document_by_name(self, name: str | None) -> Document | None:
		if not name:
			return None
		for document in self.documents:
			if document.name == name:
				return document
		return None

	def _replace_document(self, updated_document: Document) -> None:
		for index, document in enumerate(self.documents):
			if document.name == updated_document.name:
				self.documents[index] = updated_document
				return

	def _document_name_exists(self, name: str, exclude_name: str | None = None) -> bool:
		return any(document.name == name and document.name != exclude_name for document in self.documents)

	def _clear_document_selection(self) -> None:
		selection = self.document_list.GetFirstSelected()
		while selection != wx.NOT_FOUND:
			self.document_list.Select(selection, on=0)
			selection = self.document_list.GetFirstSelected()
		self._selected_document_name = None

	def _refresh_document_list(self, preferred_name: str | None = None) -> None:
		self._sort_documents()
		self.document_list.DeleteAllItems()
		for document in self.documents:
			self.document_list.InsertItem(self.document_list.GetItemCount(), document.name)
		if not self.documents:
			self._selected_document_name = None
			return
		selected_name = preferred_name if preferred_name in self._get_document_names() else self.documents[0].name
		self._selected_document_name = selected_name
		for index, document in enumerate(self.documents):
			if document.name == selected_name:
				self.document_list.Select(index)
				self.document_list.Focus(index)
				break

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

	def _convert_text_for_output(self, raw_text: str) -> str:
		table_file = language_map_translate_table.get("default")
		if not table_file:
			raise ValueError(_("Please select a translation table first."))
		output_mode = self._get_selected_output_mode()
		width = self._clamp_conversion_width(self.width_spin.GetValue())
		dictionary_path = self._get_selected_dictionary_path()
		text = translate__mapping_char(
			raw_text,
			dictionary_path=resource_path("data/BopomofoChar2Braille.csv"),
			from_field="Bopomofo",
			to_field="Braille",
		)
		braille_wrapped, _text_wrapped = translate_and_wrap_both(table_file, text, width, dictionary_path)
		if output_mode == "ascii":
			return translate__mapping_char(
				braille_wrapped,
				dictionary_path=resource_path("data/Braille2Ascii.csv"),
				from_field="Braille",
				to_field="Ascii",
			)
		return braille_wrapped

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
		document = self._get_document_by_name(name)
		if document is None:
			self._open_document_name = None
			self._clear_document_editors()
			return
		self._open_document_name = document.name
		self._selected_document_name = document.name
		self._load_document_into_editors(document)
		self._refresh_document_list(document.name)

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

	def _create_document(self, document_name: str, text: str = "", braille: str | None = "") -> bool:
		document = Document(name=document_name, text=text, braille=braille)
		try:
			save_document_package(document_package_path_for_name(document.name, self.workspace_dir), document)
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return False
		self.documents.append(document)
		self._refresh_document_list(document.name)
		self._open_document_by_name(document.name)
		return True

	def _prompt_for_document_name(
		self,
		title: str,
		initial_name: str = "",
		exclude_name: str | None = None,
		required: bool = False,
	) -> str | None:
		prefill_name = initial_name
		while True:
			with DocumentNameDialog(self, title=title, initial_name=prefill_name) as dialog:
				if dialog.ShowModal() != wx.ID_OK:
					if required:
						wx.MessageBox(
							_("At least one document is required."),
							_("Info"),
							wx.OK | wx.ICON_INFORMATION,
							parent=self,
						)
						continue
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

	def _ensure_open_document_exists(self) -> None:
		if self.documents:
			self._open_document_by_name(self.documents[0].name)
			return
		while True:
			document_name = self._prompt_for_document_name(_("Add Document"), required=True)
			if document_name and self._create_document(document_name):
				return

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
		batch_import_submenu = wx.Menu()
		export_submenu = wx.Menu()
		batch_export_submenu = wx.Menu()
		format_items: dict[str, wx.MenuItem] = {}
		for label in get_document_action_labels():
			if label == "Import":
				menu_items[label] = menu.AppendSubMenu(import_submenu, _(label))
				for format_label in get_document_import_format_labels():
					format_items[f"import:{format_label.lower()}"] = import_submenu.Append(wx.ID_ANY, _(format_label))
			elif label == "Batch Import":
				menu_items[label] = menu.AppendSubMenu(batch_import_submenu, _(label))
				for format_label in get_document_import_format_labels():
					format_items[f"batch-import:{format_label.lower()}"] = batch_import_submenu.Append(wx.ID_ANY, _(format_label))
			elif label == "Export":
				menu_items[label] = menu.AppendSubMenu(export_submenu, _(label))
				for format_label in get_document_export_format_labels():
					format_items[f"export:{format_label.lower()}"] = export_submenu.Append(wx.ID_ANY, _(format_label))
			elif label == "Batch Export":
				menu_items[label] = menu.AppendSubMenu(batch_export_submenu, _(label))
				for format_label in get_document_export_format_labels():
					format_items[f"batch-export:{format_label.lower()}"] = batch_export_submenu.Append(wx.ID_ANY, _(format_label))
			else:
				menu_items[label] = menu.Append(wx.ID_ANY, _(label))
		has_selection = self._get_selected_document() is not None
		has_documents = bool(self.documents)
		menu_items["Open"].Enable(has_selection)
		menu_items["Delete"].Enable(has_selection)
		menu_items["Delete All"].Enable(has_documents)
		menu_items["Rename"].Enable(has_selection)
		menu_items["Export"].Enable(has_selection)
		menu_items["Batch Export"].Enable(has_documents)
		menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["Open"])
		menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["Delete"])
		menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["Delete All"])
		menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["Add"])
		menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["Rename"])
		for key, item in format_items.items():
			action, format_key = key.split(":")
			if action == "import":
				menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_import_document(fmt), item)
			elif action == "batch-import":
				menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_batch_import_documents(fmt), item)
			elif action == "export":
				menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_document(fmt), item)
			elif action == "batch-export":
				menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_batch_export_documents(fmt), item)
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
		renamed_document = Document(name=new_name, text=selected_document.text, braille=selected_document.braille)
		try:
			save_document_package(document_package_path_for_name(renamed_document.name, self.workspace_dir), renamed_document)
			old_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
			if old_path.exists():
				old_path.unlink()
		except OSError as exc:
			self._show_file_error(_("Failed to save document: {error}"), exc)
			return
		for index, document in enumerate(self.documents):
			if document.name == selected_document.name:
				self.documents[index] = renamed_document
				break
		if self._open_document_name == selected_document.name:
			self._open_document_name = renamed_document.name
		self._refresh_document_list(renamed_document.name)

	def on_delete_document(self, _evt) -> None:
		selected_document = self._get_selected_document()
		if selected_document is None:
			return
		if not self._save_open_document_with_feedback():
			return
		preferred_name = choose_document_selection_after_delete(self._get_document_names(), selected_document.name)
		was_open = self._open_document_name == selected_document.name
		try:
			package_path = document_package_path_for_name(selected_document.name, self.workspace_dir)
			if package_path.exists():
				package_path.unlink()
		except OSError as exc:
			self._show_file_error(_("Failed to delete document: {error}"), exc)
			return
		self.documents = [document for document in self.documents if document.name != selected_document.name]
		if was_open:
			self._open_document_name = None
		self._refresh_document_list(preferred_name)
		if self.documents:
			if was_open and preferred_name:
				self._open_document_by_name(preferred_name)
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
		with wx.FileDialog(self, title, wildcard=wildcard, style=wx.FD_OPEN) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			source_path = Path(file_dialog.GetPath())
		try:
			loaded_document = load_document_package(source_path) if format_key == "dep" else load_text_document(source_path)
		except (ValueError, zipfile.BadZipFile):
			wx.MessageBox(
				_("Imported file must be a valid DotExpress DEP package.") if format_key == "dep" else _("Imported file must be a valid text document."),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		except OSError as exc:
			self._show_file_error(_("Failed to import document: {error}"), exc)
			return
		document_name = self._prompt_for_document_name(title, initial_name=loaded_document.name)
		if document_name is None:
			return
		self._create_document(document_name, loaded_document.text, loaded_document.braille)

	def on_batch_import_documents(self, format_key: str) -> None:
		if not self._save_open_document_with_feedback():
			return
		with wx.DirDialog(self, _("Batch Import Documents")) as dir_dialog:
			if dir_dialog.ShowModal() != wx.ID_OK:
				return
			source_dir = Path(dir_dialog.GetPath())
		documents, issues = batch_import_documents_from_folder(
			source_dir,
			format_key=format_key,
			existing_names=set(self._get_document_names()),
		)
		saved_documents, save_issues = self._persist_documents(documents)
		self.documents.extend(saved_documents)
		self._refresh_document_list(self._open_document_name or self._selected_document_name)
		self._show_file_issues_dialog(
			_("Batch Import Issues"),
			_("Some files were skipped during batch import."),
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

	def on_batch_export_documents(self, format_key: str) -> None:
		if not self.documents:
			return
		if not self._save_open_document_with_feedback():
			return
		with wx.DirDialog(self, _("Batch Export Documents")) as dir_dialog:
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
			_("Batch Export Issues"),
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
		event.Skip()

	def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
		step = get_font_size_step_from_wheel(event.GetWheelRotation(), event.ControlDown())
		if step == 0:
			event.Skip()
			return
		self._set_view_font_size(self.font_size_spin.GetValue() + step)

	def on_output_mode_change(self, _evt):
		set_output_mode(self._get_selected_output_mode())

	def on_width_change(self, _evt):
		width = self._clamp_conversion_width(self.width_spin.GetValue())
		if self.width_spin.GetValue() != width:
			self.width_spin.SetValue(width)
		set_conversion_width(width)

	def on_dictionary_change(self, _evt):
		set_selected_dictionary(self._get_selected_dictionary_name())

	def on_open_table_dialog(self, _evt):
		with TranslationTableDialog(self, language_map_translate_table) as dialog:
			if dialog.ShowModal() == wx.ID_OK:
				selections = dialog.get_selected_tables()
				language_map_translate_table.update(selections)
				set_translation_tables(language_map_translate_table)

	def on_open_dictionary_actions(self, _evt):
		menu = wx.Menu()
		menu_items: dict[str, wx.MenuItem] = {}
		for label in get_dictionary_action_labels():
			menu_items[label] = menu.Append(wx.ID_ANY, _(label))

		has_selection = bool(self._dictionary_names)
		selected_name = self._get_selected_dictionary_name()
		menu_items["Edit"].Enable(has_selection)
		menu_items["Delete"].Enable(has_selection and selected_name.casefold() != DEFAULT_DICTIONARY_NAME.casefold())
		menu_items["Export"].Enable(has_selection)

		menu.Bind(wx.EVT_MENU, self.on_edit_dictionary, menu_items["Edit"])
		menu.Bind(wx.EVT_MENU, self.on_delete_dictionary, menu_items["Delete"])
		menu.Bind(wx.EVT_MENU, self.on_add_dictionary, menu_items["Add"])
		menu.Bind(wx.EVT_MENU, self.on_import_dictionary, menu_items["Import"])
		menu.Bind(wx.EVT_MENU, self.on_export_dictionary, menu_items["Export"])
		self.actions_btn.PopupMenu(menu, get_actions_menu_position(self.actions_btn.GetSize()))
		menu.Destroy()

	def on_add_dictionary(self, _evt):
		with DictionaryNameDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			dictionary_name = dialog.get_dictionary_name()

		try:
			path = create_dictionary(self.dictionary_dir, dictionary_name)
		except FileExistsError:
			wx.MessageBox(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			return

		self._refresh_dictionary_choice(path.stem)

	def on_edit_dictionary(self, _evt):
		if not self._dictionary_names:
			return
		with SpeechSymbolsDialog(self, dictionary_path=self._get_selected_dictionary_path()) as dialog:
			dialog.ShowModal()

	def on_delete_dictionary(self, _evt):
		selected_name = self._get_selected_dictionary_name()
		if selected_name.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
			wx.MessageBox(
				_("The default dictionary cannot be deleted."),
				_("Info"),
				wx.OK | wx.ICON_INFORMATION,
				parent=self,
			)
			return

		preferred_name = choose_selection_after_delete(self._dictionary_names, selected_name)
		delete_dictionary(self.dictionary_dir, selected_name)
		self._refresh_dictionary_choice(preferred_name)

	def on_import_dictionary(self, _evt):
		with wx.FileDialog(
			self,
			_("Import Dictionary"),
			wildcard=self._get_csv_wildcard(),
			style=wx.FD_OPEN,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return
			source_path = Path(file_dialog.GetPath())

		with DictionaryNameDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			dictionary_name = dialog.get_dictionary_name()

		try:
			path = import_dictionary(self.dictionary_dir, source_path, dictionary_name)
		except FileExistsError:
			wx.MessageBox(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		except ValueError:
			wx.MessageBox(
				_("Imported file must contain text, braille, and type headers."),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		except OSError as exc:
			self._show_file_error(_("Failed to import dictionary: {error}"), exc)
			return

		self._refresh_dictionary_choice(path.stem)

	def on_export_dictionary(self, _evt):
		if not self._dictionary_names:
			return
		selected_name = self._get_selected_dictionary_name()
		with wx.FileDialog(
			self,
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
			self._show_file_error(_("Failed to export dictionary: {error}"), exc)

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

		selection = self.output_choice.GetSelection()
		if selection == wx.NOT_FOUND:
			wx.MessageBox(
				_("Please select the output format first."),
				_("Info"),
				wx.OK | wx.ICON_INFORMATION,
				parent=self,
			)
			return

		output_mode = self._get_selected_output_mode()
		raw_text = self.input_txt.GetValue()
		width = self._clamp_conversion_width(self.width_spin.GetValue())
		self._start_conversion(table_file, raw_text, width, output_mode, self._get_selected_dictionary_path())

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
		for control in (
			self.table_btn,
			self.output_choice,
			self.width_spin,
			self.dictionary_choice,
			self.actions_btn,
			self.convert_btn,
			self.document_list,
			self.input_txt,
		):
			control.Enable(not busy)

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
			text = translate__mapping_char(
				raw_text,
				dictionary_path=resource_path("data/BopomofoChar2Braille.csv"),
				from_field="Bopomofo",
				to_field="Braille",
			)
			braille_wrapped, _text_wrapped = translate_and_wrap_both(table_file, text, width, dictionary_path)
		except Exception as e:
			wx.CallAfter(
				self._finish_conversion,
				job_id,
				error_message=_("Translation failed: {error}").format(error=e),
			)
			return

		display_text = braille_wrapped
		if output_mode == "ascii":
			try:
				display_text = translate__mapping_char(
					braille_wrapped,
					dictionary_path=resource_path("data/Braille2Ascii.csv"),
					from_field="Braille",
					to_field="Ascii",
				)
			except Exception as e:
				wx.CallAfter(
					self._finish_conversion,
					job_id,
					error_message=_("ASCII conversion failed: {error}").format(error=e),
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
		louisHelper.initialize()
		self.frame = BrailleFrame(None)
		self.frame.Show()
		return True

	def OnExit(self):
		louisHelper.terminate()
		return 0


if __name__ == "__main__":
	app = BrailleApp()
	app.MainLoop()
