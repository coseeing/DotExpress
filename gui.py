from pathlib import Path
import gettext
import sys
import threading

import wx

import louisHelper
from action_menu import (
	build_actions_button_label,
	get_actions_menu_position,
	get_dictionary_action_labels,
)
from config import (
	DEFAULT_CONVERSION_WIDTH,
	DEFAULT_OUTPUT_MODE,
	DEFAULT_TRANSLATION_TABLES,
	DEFAULT_VIEW_FONT_SIZE,
	DEFAULT_VIEW_SCHEME,
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

from Bopomofo import normalize_zhuyin_sequence
from dialog import DictionaryNameDialog, SpeechSymbolsDialog, TranslationTableDialog
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

		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		controls_box = wx.BoxSizer(wx.VERTICAL)
		self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
		self._view_schemes = [("light", _("Light")), ("dark", _("Dark"))]

		initial_output_mode = self._normalize_output_mode(get_output_mode(DEFAULT_OUTPUT_MODE))
		initial_width = self._clamp_conversion_width(get_conversion_width(DEFAULT_CONVERSION_WIDTH))
		initial_font_size = self._clamp_view_font_size(get_view_font_size(DEFAULT_VIEW_FONT_SIZE))
		initial_scheme = self._normalize_view_scheme(get_view_scheme(DEFAULT_VIEW_SCHEME))

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

		view_row.Add(font_size_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.font_size_spin, 0, wx.RIGHT, 12)
		view_row.Add(scheme_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.scheme_choice, 0)
		view_row.AddStretchSpacer()

		controls_box.Add(conversion_group, 0, wx.EXPAND)
		controls_box.Add(view_group, 0, wx.EXPAND | wx.TOP, 8)
		vbox.Add(controls_box, 0, wx.EXPAND | wx.ALL, 8)

		self.input_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		self._set_control_accessible_name(self.input_txt, _("Source Text"))
		vbox.Add(self.input_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		self.output_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
		self._set_control_accessible_name(self.output_txt, _("Braille"))
		vbox.Add(self.output_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		panel.SetSizer(vbox)

		self._set_output_mode_selection(initial_output_mode)
		self._set_scheme_selection(initial_scheme)
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
		self.Bind(wx.EVT_CLOSE, self._on_close)

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

	def _apply_editor_font_size(self, font_size: int):
		for control in (self.input_txt, self.output_txt):
			font = control.GetFont()
			font.SetPointSize(font_size)
			control.SetFont(font)

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

	def on_font_size_change(self, _evt):
		font_size = self._clamp_view_font_size(self.font_size_spin.GetValue())
		if self.font_size_spin.GetValue() != font_size:
			self.font_size_spin.SetValue(font_size)
		self._apply_editor_view_settings(font_size, self._get_selected_scheme())
		set_view_font_size(font_size)

	def on_scheme_change(self, _evt):
		scheme = self._normalize_view_scheme(self._get_selected_scheme())
		self._apply_editor_view_settings(self._clamp_view_font_size(self.font_size_spin.GetValue()), scheme)
		set_view_scheme(scheme)

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
