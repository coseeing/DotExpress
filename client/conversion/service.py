from adapters.translation.contracts import TranslationRuntime
from config import DEFAULT_MATH_BRAILLE_TABLE
from conversion.text.char_maps import translate__mapping_char
from conversion.output import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    MapChar,
    WrapBoth,
    convert_text_for_output as _convert_text_for_output,
    convert_text_with_alignment as _convert_text_with_alignment,
)
from conversion.plain_text import get_public_error_message
from conversion.preprocessing.literal_braille import (
    LiteralBrailleToken,
    build_literal_translation_result,
    preprocess_punctuation,
)
from conversion.text.math_segments import parse_inline_math_segments, segment_needs_boundary_space
from conversion.text.pipeline import translate_plain_text_segment
from conversion.wrapping import (
    merge_translation_results,
    translate_and_wrap_both as _translate_and_wrap_both,
    wrap_translation_results,
)
from dual_view.model import DualViewSegment


_translate_plain_text_segment = translate_plain_text_segment
_segment_needs_boundary_space = segment_needs_boundary_space
_wrap_translation_results = wrap_translation_results


def translate_with_language_dual_view_segments(
    table_file: str,
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
    math_braille_code = translation_tables.get("math", DEFAULT_MATH_BRAILLE_TABLE)
    for index, segment in enumerate(segments):
        if index > 0 and _segment_needs_boundary_space(segments[index - 1], segment):
            result = runtime.text_translator.translate(
                " ",
                table=table_file,
                raw=" ",
            )
            segments_records.append(DualViewSegment(result=result, source_kind="text"))
        if segment["type"] == "text":
            for punctuation_token in preprocess_punctuation(segment["text"]):
                if isinstance(punctuation_token, LiteralBrailleToken):
                    segments_records.append(
                        DualViewSegment(
                            result=build_literal_translation_result(
                                punctuation_token.source_text,
                                punctuation_token.braille_text,
                            ),
                            source_kind="text",
                        )
                    )
                    continue

                plain_results = _translate_plain_text_segment(
                    table_file,
                    punctuation_token.text,
                    dictionary_path,
                    translation_tables,
                    bopomofo_path,
                    runtime=runtime,
                )
                if isinstance(plain_results, (list, tuple)):
                    for res in plain_results:
                        segments_records.append(DualViewSegment(result=res, source_kind="text"))
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
    table_file: str,
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
            table_file,
            text,
            dictionary_path,
            translation_tables,
            bopomofo_path,
            runtime=runtime,
        )
    ]


def translate_with_language(
    table_file: str,
    text: str,
    dictionary_path,
    translation_tables: dict[str, str],
    bopomofo_path,
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


def convert_text_with_alignment(
    request: ConversionRequest,
    *,
    map_char: MapChar = translate__mapping_char,
    runtime: TranslationRuntime,
) -> ConversionOutput:
    captured_segments: list[DualViewSegment] = []

    def translate_segments_with_dual_view(
        table_file, text, dictionary_path, translation_tables, bopomofo_path, *, runtime
    ):
        segments = translate_with_language_dual_view_segments(
            table_file,
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


def translate_and_wrap_both(
    *,
    table_file: str,
    text: str,
    width: int,
    dictionary_path,
    translation_tables: dict[str, str],
    bopomofo_path,
    runtime: TranslationRuntime,
) -> tuple[str, str]:
    return _translate_and_wrap_both(
        table_file=table_file,
        text=text,
        width=width,
        dictionary_path=dictionary_path,
        translation_tables=translation_tables,
        bopomofo_path=bopomofo_path,
        runtime=runtime,
        translate_with_language=translate_with_language,
    )


def convert_text_for_output(
    request: ConversionRequest,
    *,
    map_char: MapChar = translate__mapping_char,
    wrap_both: WrapBoth = translate_and_wrap_both,
    runtime: TranslationRuntime,
) -> str:
    return _convert_text_for_output(
        request,
        convert_with_alignment=convert_text_with_alignment,
        default_wrap_both=translate_and_wrap_both,
        wrap_both=wrap_both,
        map_char=map_char,
        runtime=runtime,
    )
