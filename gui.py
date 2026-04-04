from pathlib import Path
import gettext
import sys
import threading

import wx

import louisHelper
from config import (
	DEFAULT_CONVERSION_WIDTH,
	DEFAULT_OUTPUT_MODE,
	DEFAULT_TRANSLATION_TABLES,
	DEFAULT_VIEW_FONT_SIZE,
	DEFAULT_VIEW_SCHEME,
	get_conversion_width,
	get_output_mode,
	get_translation_tables,
	get_view_font_size,
	get_view_scheme,
	set_conversion_width,
	set_output_mode,
	set_translation_tables,
	set_view_font_size,
	set_view_scheme,
)

from Bopomofo import normalize_zhuyin_sequence
from dialog import SpeechSymbolsDialog, TranslationTableDialog
from languageDetection import LangChangeCommand, LanguageDetector
from translate import translate, translate_as_single_token, TranslationResult
from utils import apply_dictionary, split_bracket_segments, translate__mapping_char, translate__mapping_string


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

language_map_translate_table2 = {
	"default": "zh-tw.ctb",
	"en": "",
	"zh": "",
	"ja": "",
}


def translate_with_language(table_file: str, text: str) -> TranslationResult:
	language = [k for k, v in language_map_translate_table.items() if k != 'default' and v != '']
	language_detector = LanguageDetector(language)
	sequence = language_detector.add_detected_language_commands([text])
	sequence = list(sequence)
	dictionary_path = Path("data/dictionary.csv")
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


def translate_and_wrap_both(table_file: str, text: str, width: int) -> tuple[str, str]:
	"""Translate and wrap, returning both braille and original text lines.
	"""
	translation_result = translate_with_language(table_file, text)
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


class BrailleFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.SetTitle(_("DotExpress"))
		self.SetSize((800, 600))

		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		controls_box = wx.BoxSizer(wx.VERTICAL)
		label_min_width = 90
		self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
		self._view_schemes = [("light", _("Light")), ("dark", _("Dark"))]

		initial_output_mode = self._normalize_output_mode(get_output_mode(DEFAULT_OUTPUT_MODE))
		initial_width = self._clamp_conversion_width(get_conversion_width(DEFAULT_CONVERSION_WIDTH))
		initial_font_size = self._clamp_view_font_size(get_view_font_size(DEFAULT_VIEW_FONT_SIZE))
		initial_scheme = self._normalize_view_scheme(get_view_scheme(DEFAULT_VIEW_SCHEME))

		conversion_row = wx.BoxSizer(wx.HORIZONTAL)
		conversion_lbl = wx.StaticText(panel, label=_("Conversion"))
		conversion_lbl.SetMinSize((label_min_width, -1))
		self.table_btn = wx.Button(panel, label=_("Translation Tables..."))
		output_lbl = wx.StaticText(panel, label=_("Output Format"))
		self.output_choice = wx.Choice(panel, choices=[label for _, label in self._output_modes])
		width_lbl = wx.StaticText(panel, label=_("Width"))
		self.width_spin = wx.SpinCtrl(panel, min=CONVERSION_WIDTH_MIN, max=CONVERSION_WIDTH_MAX, initial=initial_width)
		self.dictionary_btn = wx.Button(panel, label=_("Dictionary"))
		self.convert_btn = wx.Button(panel, label=_("Convert"))

		conversion_row.Add(conversion_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		conversion_row.Add(self.table_btn, 0, wx.RIGHT, 8)
		conversion_row.Add(output_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		conversion_row.Add(self.output_choice, 0, wx.RIGHT, 8)
		conversion_row.Add(width_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		conversion_row.Add(self.width_spin, 0, wx.RIGHT, 8)
		conversion_row.Add(self.dictionary_btn, 0)
		conversion_row.Add(self.convert_btn, 0, wx.LEFT, 8)

		view_row = wx.BoxSizer(wx.HORIZONTAL)
		view_lbl = wx.StaticText(panel, label=_("View"))
		view_lbl.SetMinSize((label_min_width, -1))
		font_size_lbl = wx.StaticText(panel, label=_("Font Size"))
		self.font_size_spin = wx.SpinCtrl(
			panel,
			min=VIEW_FONT_SIZE_MIN,
			max=VIEW_FONT_SIZE_MAX,
			initial=initial_font_size,
		)
		scheme_lbl = wx.StaticText(panel, label=_("Scheme"))
		self.scheme_choice = wx.Choice(panel, choices=[label for _, label in self._view_schemes])

		view_row.Add(view_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		view_row.Add(font_size_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.font_size_spin, 0, wx.RIGHT, 12)
		view_row.Add(scheme_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		view_row.Add(self.scheme_choice, 0)
		view_row.AddStretchSpacer()

		controls_box.Add(conversion_row, 0, wx.EXPAND)
		controls_box.Add(view_row, 0, wx.EXPAND | wx.TOP, 8)
		vbox.Add(controls_box, 0, wx.EXPAND | wx.ALL, 8)

		self.input_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		vbox.Add(self.input_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		self.output_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
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

		self._apply_editor_view_settings(initial_font_size, initial_scheme)

		self.table_btn.Bind(wx.EVT_BUTTON, self.on_open_table_dialog)
		self.output_choice.Bind(wx.EVT_CHOICE, self.on_output_mode_change)
		self.width_spin.Bind(wx.EVT_SPINCTRL, self.on_width_change)
		self.width_spin.Bind(wx.EVT_TEXT, self.on_width_change)
		self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
		self.dictionary_btn.Bind(wx.EVT_BUTTON, self.on_open_dictionary)
		self.font_size_spin.Bind(wx.EVT_SPINCTRL, self.on_font_size_change)
		self.font_size_spin.Bind(wx.EVT_TEXT, self.on_font_size_change)
		self.scheme_choice.Bind(wx.EVT_CHOICE, self.on_scheme_change)
		self.Bind(wx.EVT_CLOSE, self._on_close)

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

	def on_open_table_dialog(self, _evt):
		with TranslationTableDialog(self, language_map_translate_table) as dialog:
			if dialog.ShowModal() == wx.ID_OK:
				selections = dialog.get_selected_tables()
				language_map_translate_table.update(selections)
				set_translation_tables(language_map_translate_table)

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
		self._start_conversion(table_file, raw_text, width, output_mode)

	def on_open_dictionary(self, _evt):
		with SpeechSymbolsDialog(self) as dialog:
			dialog.ShowModal()

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
			self.dictionary_btn,
			self.convert_btn,
			self.input_txt,
		):
			control.Enable(not busy)

	def _start_conversion(self, table_file: str, raw_text: str, width: int, output_mode: str):
		self._convert_job_id += 1
		job_id = self._convert_job_id
		self._set_conversion_busy(True)
		self._close_converting_dialog()
		self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)
		self._convert_thread = threading.Thread(
			target=self._run_conversion,
			args=(job_id, table_file, raw_text, width, output_mode),
			daemon=True,
		)
		self._convert_thread.start()

	def _run_conversion(self, job_id: int, table_file: str, raw_text: str, width: int, output_mode: str):
		try:
			text = translate__mapping_char(
				raw_text,
				dictionary_path=resource_path("data/BopomofoChar2Braille.csv"),
				from_field="Bopomofo",
				to_field="Braille",
			)
			braille_wrapped, _text_wrapped = translate_and_wrap_both(table_file, text, width)
		except Exception as e:
			raise e
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
