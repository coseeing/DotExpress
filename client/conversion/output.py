from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from conversion.preprocessing.user_script import preprocessing_script_path
from conversion.text.char_maps import translate__mapping_char
from conversion.text.pipeline import TextProcessingError, preprocess_source_text


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
    dual_view_segments: tuple[object, ...] = ()


class ConversionStageError(Exception):
    def __init__(self, stage: str, error: Exception):
        super().__init__(str(error))
        self.stage = stage
        self.error = error


MapChar = Callable[..., str]
TranslateSegments = Callable[..., list[object]]
WrapTranslationResults = Callable[[list[object], int], tuple[str, str]]


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
        text = preprocess_source_text(
            request.raw_text,
            data_dir=request.data_dir,
            preprocessing_path=preprocessing_script_path(request.dictionary_path.parent),
            map_char=map_char,
        )
    except TextProcessingError as error:
        raise ConversionStageError("text_processing", error.error) from error
    except Exception as error:
        raise ConversionStageError("translation", error) from error

    try:
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
