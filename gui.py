from pathlib import Path
import gettext
import sys
import threading

import wx

import louisHelper

from Bopomofo import normalize_zhuyin_sequence
from dialog import SpeechSymbolsDialog, TranslationTableDialog
from languageDetection import LangChangeCommand, LanguageDetector
from translate import translate, translate_as_single_token, TranslationResult
from utils import apply_dictionary, split_bracket_segments, translate__mapping_char, translate__mapping_string


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


language_map_translate_table = {
	"default": "zh-tw.ctb",
	"en": "en-ueb-g1.ctb",
	"zh": "zh-tw.ctb",
	"ja": "ja-rokutenkanji.utb",
}

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
	# text, braille, braille_to_raw_pos, raw_to_braille_pos = translate(table_file, text)
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

		# Top controls: label, table selection, convert button
		top_box = wx.BoxSizer(wx.HORIZONTAL)
		self.table_btn = wx.Button(panel, label=_("Translation Tables..."))
		output_lbl = wx.StaticText(panel, label=_("Output Format"))
		self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
		self.output_choice = wx.Choice(panel, choices=[label for _, label in self._output_modes])
		width_lbl = wx.StaticText(panel, label=_("Width"))
		self.width_spin = wx.SpinCtrl(panel, min=10, max=200, initial=40)
		self.dictionary_btn = wx.Button(panel, label=_("Dictionary"))
		self.convert_btn = wx.Button(panel, label=_("Convert"))

		top_box.Add(self.table_btn, 0, wx.RIGHT, 8)
		top_box.Add(output_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		top_box.Add(self.output_choice, 0, wx.RIGHT, 8)
		top_box.Add(width_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
		top_box.Add(self.width_spin, 0, wx.RIGHT, 8)
		top_box.Add(self.dictionary_btn, 0)
		top_box.Add(self.convert_btn, 0, wx.LEFT, 8)

		# self.dictionary_btn.Disable()

		vbox.Add(top_box, 0, wx.EXPAND | wx.ALL, 8)

		# Middle: input multiline editor
		self.input_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
		vbox.Add(self.input_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		# Bottom: output multiline editor (read-only)
		self.output_txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
		vbox.Add(self.output_txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		panel.SetSizer(vbox)

		self.output_choice.SetSelection(0)
		self._convert_thread = None
		self._convert_dialog = None
		self._convert_dialog_timer = None
		self._convert_job_id = 0

		self.table_btn.Bind(wx.EVT_BUTTON, self.on_open_table_dialog)
		self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
		self.dictionary_btn.Bind(wx.EVT_BUTTON, self.on_open_dictionary)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def on_open_table_dialog(self, _evt):
		with TranslationTableDialog(self, language_map_translate_table) as dialog:
			if dialog.ShowModal() == wx.ID_OK:
				selections = dialog.get_selected_tables()
				language_map_translate_table.update(selections)

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

		output_mode = self._output_modes[selection][0]

		raw_text = self.input_txt.GetValue()
		width = self.width_spin.GetValue()
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
		# Initialize liblouis integration (logging + resolver)
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
