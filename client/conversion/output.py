from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from conversion.text.char_maps import translate__mapping_char
from conversion.text.pipeline import preprocess_source_text


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
TranslateSegments = Callable[..., list[object]]
WrapTranslationResults = Callable[[list[object], int], tuple[str, str]]
ConvertWithAlignment = Callable[..., ConversionOutput]


def convert_text_with_alignment(
    request: ConversionRequest,
    *,
    translate_segments: TranslateSegments,
    wrap_translation_results: WrapTranslationResults,
    map_char: MapChar = translate__mapping_char,
    runtime: TranslationRuntime,
) -> ConversionOutput:
    if request.raw_text == "":
        return ConversionOutput("", ())
    try:
        text = preprocess_source_text(request.raw_text, data_dir=request.data_dir, map_char=map_char)
        translations = translate_segments(
            request.table_file,
            text,
            request.dictionary_path,
            request.translation_tables,
            request.data_dir / "Bopomofo2Braille.csv",
            runtime=runtime,
        )
        braille_wrapped, _text_wrapped = wrap_translation_results(translations, request.width)
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


def convert_text_for_output(
    request: ConversionRequest,
    *,
    convert_with_alignment: ConvertWithAlignment,
    default_wrap_both: WrapBoth,
    wrap_both: WrapBoth,
    map_char: MapChar = translate__mapping_char,
    runtime: TranslationRuntime,
) -> str:
    if request.raw_text == "":
        return ""
    if wrap_both is default_wrap_both:
        return convert_with_alignment(request, map_char=map_char, runtime=runtime).display_text
    try:
        text = preprocess_source_text(request.raw_text, data_dir=request.data_dir, map_char=map_char)
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
