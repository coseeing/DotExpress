from adapters.translation.contracts import TranslationRuntime
from config import DEFAULT_MATH_BRAILLE_TABLE
from conversion.text.char_maps import translate__mapping_char
from conversion.output import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    MapChar,
    convert_text_with_alignment as _convert_text_with_alignment,
)
from conversion.plain_text import get_public_error_message
from conversion.text.math_segments import parse_inline_math_segments, segment_needs_boundary_space
from conversion.text.pipeline import translate_plain_text_segment
from conversion.wrapping import (
    merge_translation_results,
    wrap_translation_results,
)
from dual_view.model import DualViewSegment


_translate_plain_text_segment = translate_plain_text_segment
_segment_needs_boundary_space = segment_needs_boundary_space
_wrap_translation_results = wrap_translation_results


def translate_with_language_dual_view_segments(
    text: str,
    dictionary_path,
    translation_tables: dict[str, str],
    bopomofo_path,
    *,
    runtime: TranslationRuntime,
) -> list[DualViewSegment]:
    if text == "":
        return []

    segments_records = []
    segments = parse_inline_math_segments(text)
    default_table = translation_tables["default"]
    math_braille_code = translation_tables.get("math", DEFAULT_MATH_BRAILLE_TABLE)
    for index, segment in enumerate(segments):
        if index > 0 and _segment_needs_boundary_space(segments[index - 1], segment):
            result = runtime.text_translator.translate(
                " ",
                table=default_table,
                raw=" ",
            )
            segments_records.append(DualViewSegment(result=result, source_kind="text"))
        if segment["type"] == "text":
            plain_results = _translate_plain_text_segment(
                segment["text"],
                dictionary_path,
                translation_tables,
                bopomofo_path,
                runtime=runtime,
            )
            if isinstance(plain_results, (list, tuple)):
                for result in plain_results:
                    segments_records.append(DualViewSegment(result=result, source_kind="text"))
            else:
                segments_records.append(DualViewSegment(result=plain_results, source_kind="text"))
        else:
            result = runtime.math_translator.translate(
                segment["text"],
                braille_code=math_braille_code,
            )
            segments_records.append(DualViewSegment(result=result, source_kind="math"))
    return segments_records


def translate_with_language_segments(
    text: str,
    dictionary_path,
    translation_tables: dict[str, str],
    bopomofo_path,
    *,
    runtime: TranslationRuntime,
):
    return [
        segment.result
        for segment in translate_with_language_dual_view_segments(
            text,
            dictionary_path,
            translation_tables,
            bopomofo_path,
            runtime=runtime,
        )
    ]


def translate_with_language(
    text: str,
    dictionary_path,
    translation_tables: dict[str, str],
    bopomofo_path,
    *,
    runtime: TranslationRuntime,
):
    return merge_translation_results(
        translate_with_language_segments(
            text,
            dictionary_path,
            translation_tables,
            bopomofo_path,
            runtime=runtime,
        )
    )


def convert_text_with_alignment(
    request: ConversionRequest,
    *,
    map_char: MapChar = translate__mapping_char,
    runtime: TranslationRuntime,
) -> ConversionOutput:
    captured_segments: list[DualViewSegment] = []

    def translate_segments_with_dual_view(
        text, dictionary_path, translation_tables, bopomofo_path, *, runtime
    ):
        segments = translate_with_language_dual_view_segments(
            text,
            dictionary_path,
            translation_tables,
            bopomofo_path,
            runtime=runtime,
        )
        captured_segments.extend(segments)
        return [s.result for s in segments]

    output = _convert_text_with_alignment(
        request,
        translate_segments=translate_segments_with_dual_view,
        wrap_translation_results=_wrap_translation_results,
        map_char=map_char,
        runtime=runtime,
    )

    return ConversionOutput(output.display_text, output.translation_results, tuple(captured_segments))
