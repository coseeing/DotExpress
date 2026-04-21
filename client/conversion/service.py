from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from utils import translate__mapping_char


@dataclass(frozen=True)
class ConversionRequest:
	raw_text: str
	table_file: str
	output_mode: str
	width: int
	dictionary_path: Path
	data_dir: Path
	translation_tables: dict[str, str]


class ConversionStageError(Exception):
	def __init__(self, stage: str, error: Exception):
		super().__init__(str(error))
		self.stage = stage
		self.error = error


MapChar = Callable[..., str]
WrapBoth = Callable[..., tuple[str, str]]


def get_public_error_message(error: Exception) -> str:
	message = str(error)
	if "Can't translate: tables" in message and "inbuf" in message:
		return "The selected translation table could not translate this text."
	return message


def translate_with_language(
	table_file: str,
	text: str,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
):
	from Bopomofo import normalize_zhuyin_sequence
	from languageDetection import LangChangeCommand, LanguageDetector
	from translate import TranslationResult, translate, translate_as_single_token
	from utils import apply_dictionary, split_bracket_segments

	if text == "":
		return TranslationResult([], [], [], [])
	language = [key for key, value in translation_tables.items() if key != "default" and value != ""]
	language_detector = LanguageDetector(language)
	sequence = list(language_detector.add_detected_language_commands([text]))

	translate_table = translation_tables["default"]
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
				translate_table = translation_tables[lang]
				if translate_table == "":
					translate_table = translation_tables["default"]
			except KeyError:
				translate_table = translation_tables["default"]
			if translate_table != previous_translate_table:
				raw = translations[-1].raw if translations else None
				if raw and not raw[-1].isspace():
					translations.append(translate(previous_translate_table, " ", " "))

	assert translations, "No translatable text segments were found."
	merged = translations[0]
	for segment in translations[1:]:
		merged = merged + segment

	return merged


def translate_and_wrap_both(
	*,
	table_file: str,
	text: str,
	width: int,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
) -> tuple[str, str]:
	translation_result = translate_with_language(
		table_file,
		text,
		dictionary_path,
		translation_tables,
		bopomofo_path,
	)
	translation_result.reclean_braille_endspace()
	translation_result.bind_word_tokens()
	translation_result.reclean_token()
	braille_wrapped, text_wrapped = translation_result.wrap(width)
	return braille_wrapped, text_wrapped


def convert_text_for_output(
	request: ConversionRequest,
	*,
	map_char: MapChar = translate__mapping_char,
	wrap_both: WrapBoth = translate_and_wrap_both,
) -> str:
	if request.raw_text == "":
		return ""
	try:
		text = map_char(
			request.raw_text,
			dictionary_path=request.data_dir / "BopomofoChar2Braille.csv",
			from_field="Bopomofo",
			to_field="Braille",
		)
		braille_wrapped, _text_wrapped = wrap_both(
			table_file=request.table_file,
			text=text,
			width=request.width,
			dictionary_path=request.dictionary_path,
			translation_tables=request.translation_tables,
			bopomofo_path=request.data_dir / "Bopomofo2Braille.csv",
		)
	except Exception as error:
		raise ConversionStageError("translation", error) from error
	if request.output_mode == "ascii":
		try:
			return map_char(
				braille_wrapped,
				dictionary_path=request.data_dir / "Braille2Ascii.csv",
				from_field="Braille",
				to_field="Ascii",
			)
		except Exception as error:
			raise ConversionStageError("ascii", error) from error
	return braille_wrapped
