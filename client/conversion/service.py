from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from config import DEFAULT_MATH_BRAILLE_TABLE
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


@dataclass(frozen=True)
class ConversionOutput:
	display_text: str
	translation_results: tuple[object, ...]


class ConversionStageError(Exception):
	def __init__(self, stage: str, error: Exception):
		super().__init__(str(error))
		self.stage = stage
		self.error = error


MapChar = Callable[..., str]
WrapBoth = Callable[..., tuple[str, str]]


def _append_text_segment(segments: list[dict[str, str]], text: str) -> None:
	if not text:
		return
	if segments and segments[-1]["type"] == "text":
		segments[-1]["text"] += text
	else:
		segments.append({"type": "text", "text": text})


def parse_inline_math_segments(text: str) -> list[dict[str, str]]:
	segments: list[dict[str, str]] = []
	current: list[str] = []
	in_math = False

	for index, char in enumerate(text):
		is_escaped_dollar = char == "$" and index > 0 and text[index - 1] == "\\"
		if char == "$" and not is_escaped_dollar:
			if in_math:
				segments.append({"type": "math", "text": "".join(current)})
				current = []
				in_math = False
			else:
				_append_text_segment(segments, "".join(current))
				current = []
				in_math = True
			continue
		current.append(char)

	if in_math:
		_append_text_segment(segments, "$" + "".join(current))
	else:
		_append_text_segment(segments, "".join(current))

	return segments


def build_literal_translation_result(text: str):
	from translate import TranslationResult

	braille = list(text)
	return TranslationResult([text], braille, [0] * len(braille), [0])


def _segment_needs_boundary_space(left_segment: dict[str, str], right_segment: dict[str, str]) -> bool:
	if left_segment["type"] != "math" and right_segment["type"] != "math":
		return False
	left_text = left_segment["text"]
	right_text = right_segment["text"]
	return bool(
		left_text
		and right_text
		and not left_text[-1].isspace()
		and not right_text[0].isspace()
	)


def get_public_error_message(error: Exception) -> str:
	message = str(error)
	if not message:
		return "An unknown error occurred."
	if "Can't translate: tables" in message and "inbuf" in message:
		return "The selected translation table could not translate this text."
	return message


def _translate_plain_text_segment(
	table_file: str,
	text: str,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
	*,
	runtime: TranslationRuntime,
):
	from Bopomofo import normalize_zhuyin_sequence
	from languageDetection import LangChangeCommand, LanguageDetector
	from utils import apply_dictionary, split_bracket_segments

	language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
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
				translations.append(
					runtime.text_translator.translate(
						replacement_segment["text"],
						table=translate_table,
						raw=raw_segment["text"],
						single_token=replacement_segment["atomic"],
					)
				)
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
					translations.append(
						runtime.text_translator.translate(
							" ",
							table=previous_translate_table,
							raw=" ",
						)
					)

	assert translations, "No translatable text segments were found."
	return translations


def merge_translation_results(translations):
	from translate import TranslationResult

	if not translations:
		return TranslationResult([], [], [], [])
	merged = TranslationResult([], [], [], [])
	for segment in translations:
		merged = merged + segment
	return merged


def translate_with_language_segments(
	table_file: str,
	text: str,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
	*,
	runtime: TranslationRuntime,
):
	if text == "":
		return []

	translations = []
	segments = parse_inline_math_segments(text)
	math_braille_code = translation_tables.get("math", DEFAULT_MATH_BRAILLE_TABLE)
	for index, segment in enumerate(segments):
		if index > 0 and _segment_needs_boundary_space(segments[index - 1], segment):
			translations.append(
				runtime.text_translator.translate(
					" ",
					table=table_file,
					raw=" ",
				)
			)
		if segment["type"] == "text":
			plain_results = _translate_plain_text_segment(
				table_file,
				segment["text"],
				dictionary_path,
				translation_tables,
				bopomofo_path,
				runtime=runtime,
			)
			if isinstance(plain_results, (list, tuple)):
				translations.extend(plain_results)
			else:
				translations.append(plain_results)
		else:
			translations.append(
				runtime.math_translator.translate(
					segment["text"],
					braille_code=math_braille_code,
				)
			)
	return translations


def translate_with_language(
	table_file: str,
	text: str,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
	*,
	runtime: TranslationRuntime,
):
	return merge_translation_results(
		translate_with_language_segments(
			table_file,
			text,
			dictionary_path,
			translation_tables,
			bopomofo_path,
			runtime=runtime,
		)
	)


def _wrap_translation_results(translations, width: int) -> tuple[str, str]:
	translation_result = merge_translation_results(translations)
	translation_result.reclean_braille_endspace()
	translation_result.bind_word_tokens()
	translation_result.reclean_token()
	return translation_result.wrap(width)


def convert_text_with_alignment(
	request: ConversionRequest,
	*,
	map_char: MapChar = translate__mapping_char,
	runtime: TranslationRuntime,
) -> ConversionOutput:
	if request.raw_text == "":
		return ConversionOutput("", ())
	try:
		text = map_char(
			request.raw_text,
			dictionary_path=request.data_dir / "BopomofoChar2Braille.csv",
			from_field="Bopomofo",
			to_field="Braille",
		)
		translations = translate_with_language_segments(
			request.table_file,
			text,
			request.dictionary_path,
			request.translation_tables,
			request.data_dir / "Bopomofo2Braille.csv",
			runtime=runtime,
		)
		braille_wrapped, _text_wrapped = _wrap_translation_results(translations, request.width)
	except Exception as error:
		raise ConversionStageError("translation", error) from error

	display_text = braille_wrapped
	if request.output_mode == "ascii":
		try:
			display_text = map_char(
				braille_wrapped,
				dictionary_path=request.data_dir / "Braille2Ascii.csv",
				from_field="Braille",
				to_field="Ascii",
			)
		except Exception as error:
			raise ConversionStageError("ascii", error) from error
	return ConversionOutput(display_text, tuple(translations))


def translate_and_wrap_both(
	*,
	table_file: str,
	text: str,
	width: int,
	dictionary_path: Path,
	translation_tables: dict[str, str],
	bopomofo_path: Path,
	runtime: TranslationRuntime,
) -> tuple[str, str]:
	translation_result = translate_with_language(
		table_file,
		text,
		dictionary_path,
		translation_tables,
		bopomofo_path,
		runtime=runtime,
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
	runtime: TranslationRuntime,
) -> str:
	if request.raw_text == "":
		return ""
	if wrap_both is translate_and_wrap_both:
		return convert_text_with_alignment(request, map_char=map_char, runtime=runtime).display_text
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
			runtime=runtime,
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
