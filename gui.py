from pathlib import Path
import gettext
import sys

import wx

import louisHelper
from brailleTables import listTables, TableType, getDefaultTableForCurLang

from dialog import SpeechSymbolsDialog
from languageDetection import LangChangeCommand, LanguageDetector
from translate import translate, TranslationResult
from utils import translate__mapping_char, translate__mapping_string


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


language_detector = LanguageDetector(["en", "zh", "ja"])

language_map_translate_table = {
	"default": "zh-tw.ctb",
	"en": "en-ueb-g1.ctb",
	"zh": "zh-tw.ctb",
	"ja": "ja-rokutenkanji.utb",
}


def translate_with_language(table_file: str, text: str) -> TranslationResult:
	sequence = language_detector.add_detected_language_commands([text])

	translate_table = language_map_translate_table["default"]
	translations = []
	for item in sequence:
		if isinstance(item, str):
			translations.append(translate(translate_table, item))
		elif isinstance(item, LangChangeCommand):
			previous_translate_table = translate_table
			try:
				translate_table = language_map_translate_table[item.lang]
			except KeyError:
				translate_table = language_map_translate_table["default"]
			if translate_table != previous_translate_table:
				raw = translations[-1].raw if translations else None
				if raw and not raw[-1].isspace():
					translations.append(translate(previous_translate_table, " "))

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


class BrailleFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.SetTitle(_("DotExpress"))
		self.SetSize((800, 600))

		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		# Top controls: label, table selection, convert button
		top_box = wx.BoxSizer(wx.HORIZONTAL)
		lbl = wx.StaticText(panel, label=_("Translation Table"))
		self.table_choice = wx.Choice(panel)
		output_lbl = wx.StaticText(panel, label=_("Output Format"))
		self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
		self.output_choice = wx.Choice(panel, choices=[label for _, label in self._output_modes])
		width_lbl = wx.StaticText(panel, label=_("Width"))
		self.width_spin = wx.SpinCtrl(panel, min=10, max=200, initial=40)
		self.dictionary_btn = wx.Button(panel, label=_("Dictionary"))
		self.convert_btn = wx.Button(panel, label=_("Convert"))

		top_box.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
		top_box.Add(self.table_choice, 1, wx.RIGHT, 8)
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

		# Populate tables and bind events
		self._tables = [t for t in listTables() if t.output]
		self._display_to_file = [t.fileName for t in self._tables]
		self.table_choice.AppendItems([t.displayName for t in self._tables])
		self.output_choice.SetSelection(0)

		# Select default table for current language if available
		try:
			default_file = getDefaultTableForCurLang(TableType.OUTPUT)
			if default_file in self._display_to_file:
				self.table_choice.SetSelection(self._display_to_file.index(default_file))
			else:
				self.table_choice.SetSelection(0 if self._display_to_file else wx.NOT_FOUND)
		except Exception:
			self.table_choice.SetSelection(0 if self._display_to_file else wx.NOT_FOUND)

		self.convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)
		self.dictionary_btn.Bind(wx.EVT_BUTTON, self.on_open_dictionary)

	def on_convert(self, _evt):
		if self.table_choice.GetSelection() == wx.NOT_FOUND:
			wx.MessageBox(
				_("Please select a translation table first."),
				_("Info"),
				wx.OK | wx.ICON_INFORMATION,
				parent=self,
			)
			return
		table_file = self._display_to_file[self.table_choice.GetSelection()]
		raw_text = self.input_txt.GetValue()
		width = self.width_spin.GetValue()
		text = raw_text

		text = translate__mapping_char(
			text,
			dictionary_path=resource_path("data/BopomofoChar2Braille.csv"),
			from_field="Bopomofo",
			to_field="Braille",
		)
		text = translate__mapping_string(
			text,
			dictionary_path=Path("data/dictionary.csv"),
			from_field="text",
			to_field="braille",
		)
		text = translate__mapping_string(
			text,
			dictionary_path=resource_path("data/Bopomofo2Braille.csv"),
			from_field="Bopomofo",
			to_field="Braille",
		)

		try:
			braille_wrapped, text_wrapped = translate_and_wrap_both(table_file, text, width)
		except Exception as e:
			wx.MessageBox(
				_("Translation failed: {error}").format(error=e),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
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
				wx.MessageBox(
					_("ASCII conversion failed: {error}").format(error=e),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=self,
				)
				return

		self.output_txt.SetValue(display_text)
		wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
		# Update input area to visually match line wrapping by braille width
		# self.input_txt.SetValue(text_wrapped)

	def on_open_dictionary(self, _evt):
		with SpeechSymbolsDialog(self) as dialog:
			dialog.ShowModal()


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
