import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.service import (
    ConversionRequest,
    ConversionStageError,
    ConversionOutput,
    convert_text_for_output,
    convert_text_with_alignment,
    get_public_error_message,
    parse_inline_math_segments,
    translate_with_language,
    translate_with_language_segments,
)


class ConversionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple] = []
        self.request = ConversionRequest(
            raw_text="abc",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
        )

    def _map_char(self, text: str, *, dictionary_path: Path, from_field: str, to_field: str) -> str:
        self.calls.append(("map", text, dictionary_path, from_field, to_field))
        if from_field == "Bopomofo":
            return f"mapped:{text}"
        if from_field == "Braille":
            return f"ascii:{text}"
        raise AssertionError(f"unexpected mapping fields: {from_field} -> {to_field}")

    def _wrap(self, *, table_file, text, width, dictionary_path, translation_tables, bopomofo_path, runtime):
        self.calls.append(("wrap", table_file, text, width, dictionary_path, translation_tables, bopomofo_path, runtime))
        return "braille-output", "source-output"

    def _fallback_runtime(self) -> TranslationRuntime:
        return TranslationRuntime(
            text_translator=FallbackTextTranslator(),
            math_translator=FallbackMathTranslator(),
        )

    def _runtime(self, text_translator=None, math_translator=None) -> TranslationRuntime:
        return TranslationRuntime(
            text_translator=text_translator or Mock(),
            math_translator=math_translator or Mock(),
        )

    def _fake_translate_module(self) -> ModuleType:
        fake_module = ModuleType("translate")

        class FakeTranslationResult:
            def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
                self.raw = raw
                self.braille = braille
                self.braille_to_raw_pos = braille_to_raw_pos
                self.raw_to_braille_pos = raw_to_braille_pos

            def __add__(self, other):
                raw_offset = len(self.raw)
                braille_offset = len(self.braille)
                return FakeTranslationResult(
                    self.raw + other.raw,
                    self.braille + other.braille,
                    list(self.braille_to_raw_pos) + [pos + raw_offset for pos in other.braille_to_raw_pos],
                    list(self.raw_to_braille_pos) + [pos + braille_offset for pos in other.raw_to_braille_pos],
                )

        fake_module.TranslationResult = FakeTranslationResult
        fake_module.translate = lambda *_args, **_kwargs: None
        fake_module.translate_as_single_token = lambda *_args, **_kwargs: None
        return fake_module

    def _mutating_translate_module(self) -> ModuleType:
        fake_module = ModuleType("translate")

        class MutatingTranslationResult:
            def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
                self.raw = raw
                self.braille = braille
                self.braille_to_raw_pos = braille_to_raw_pos
                self.raw_to_braille_pos = raw_to_braille_pos

            def __add__(self, other):
                raw_offset = len(self.raw)
                braille_offset = len(self.braille)
                return MutatingTranslationResult(
                    self.raw + other.raw,
                    self.braille + other.braille,
                    list(self.braille_to_raw_pos) + [pos + raw_offset for pos in other.braille_to_raw_pos],
                    list(self.raw_to_braille_pos) + [pos + braille_offset for pos in other.raw_to_braille_pos],
                )

            def reclean_braille_endspace(self):
                return None

            def bind_word_tokens(self):
                self.raw = ["".join(self.raw)]
                self.raw_to_braille_pos = [0]
                self.braille_to_raw_pos = [0] * len(self.braille)

            def reclean_token(self):
                return None

            def wrap(self, _width):
                return "".join(self.braille), "".join(self.raw)

        fake_module.TranslationResult = MutatingTranslationResult
        return fake_module

    def _translation_result(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
        from translate import TranslationResult

        return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)

    def test_convert_text_for_output_returns_empty_string_for_empty_input(self) -> None:
        request = ConversionRequest(
            raw_text="",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
        )

        result = convert_text_for_output(
            request,
            map_char=self._map_char,
            wrap_both=self._wrap,
            runtime=self._fallback_runtime(),
        )

        self.assertEqual(result, "")

    def test_convert_text_for_output_returns_unicode_braille_output(self) -> None:
        result = convert_text_for_output(
            self.request,
            map_char=self._map_char,
            wrap_both=self._wrap,
            runtime=self._fallback_runtime(),
        )

        self.assertEqual(result, "braille-output")

    def test_convert_text_for_output_maps_braille_to_ascii_when_requested(self) -> None:
        request = ConversionRequest(
            raw_text="abc",
            table_file="zh-tw.ctb",
            output_mode="ascii",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
        )

        result = convert_text_for_output(
            request,
            map_char=self._map_char,
            wrap_both=self._wrap,
            runtime=self._fallback_runtime(),
        )

        self.assertEqual(result, "ascii:braille-output")

    def test_convert_text_for_output_propagates_translation_failures(self) -> None:
        def failing_wrap(**_kwargs):
            raise ValueError("translation boom")

        with self.assertRaisesRegex(ConversionStageError, "translation boom") as context:
            convert_text_for_output(
                self.request,
                map_char=self._map_char,
                wrap_both=failing_wrap,
                runtime=self._fallback_runtime(),
            )
        self.assertEqual(context.exception.stage, "translation")
        self.assertIsInstance(context.exception.error, ValueError)

    def test_convert_text_for_output_propagates_ascii_failures(self) -> None:
        def failing_map(text: str, *, dictionary_path: Path, from_field: str, to_field: str) -> str:
            if from_field == "Braille":
                raise ValueError("ascii boom")
            return self._map_char(text, dictionary_path=dictionary_path, from_field=from_field, to_field=to_field)

        request = ConversionRequest(
            raw_text="abc",
            table_file="zh-tw.ctb",
            output_mode="ascii",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
        )

        with self.assertRaisesRegex(ConversionStageError, "ascii boom") as context:
            convert_text_for_output(
                request,
                map_char=failing_map,
                wrap_both=self._wrap,
                runtime=self._fallback_runtime(),
            )
        self.assertEqual(context.exception.stage, "ascii")
        self.assertIsInstance(context.exception.error, ValueError)

    def test_get_public_error_message_hides_liblouis_internal_translate_details(self) -> None:
        error = RuntimeError(
            "Can't translate: tables ['D:\\workspace\\DotExpress\\client\\louis\\tables\\en-ueb-g1.ctb'], "
            "inbuf b'a\\x00\\x00\\x00', typeform None, cursorPos c_long(0), mode 4"
        )

        self.assertEqual(get_public_error_message(error), "The selected translation table could not translate this text.")

    def test_get_public_error_message_preserves_regular_errors(self) -> None:
        self.assertEqual(get_public_error_message(ValueError("missing dictionary")), "missing dictionary")

    def test_get_public_error_message_replaces_empty_error_text(self) -> None:
        self.assertEqual(get_public_error_message(ValueError("")), "An unknown error occurred.")

    def test_parse_inline_math_segments_splits_multiple_math_ranges(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2$和$3+4$"),
            [
                {"type": "text", "text": "計算"},
                {"type": "math", "text": "1+2"},
                {"type": "text", "text": "和"},
                {"type": "math", "text": "3+4"},
            ],
        )

    def test_parse_inline_math_segments_keeps_escaped_dollar_inside_math(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("$1+\\$2$"),
            [{"type": "math", "text": "1+\\$2"}],
        )

    def test_parse_inline_math_segments_treats_unmatched_opening_dollar_as_text(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2"),
            [{"type": "text", "text": "計算$1+2"}],
        )

    def test_parse_inline_math_segments_keeps_escaped_dollar_outside_math(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("價格\\$100"),
            [{"type": "text", "text": "價格\\$100"}],
        )

    def test_translate_with_language_merges_text_and_math_segments_in_order(self) -> None:
        from conversion import service

        runtime = self._runtime(
            text_translator=Mock(),
            math_translator=Mock(),
        )
        runtime.text_translator.translate.return_value = self._translation_result([" "], ["⠀"], [0], [0])
        runtime.math_translator.translate.return_value = self._translation_result(
            ["1+2"],
            list("M[1+2]"),
            [0] * 6,
            [0],
        )

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path, *, runtime):
            from translate import TranslationResult

            braille = list(f"T[{text}]")
            return [TranslationResult([text], braille, [0] * len(braille), [0])]

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            result = service.translate_with_language(
                "zh-tw.ctb",
                "計算$1+2$的值",
                Path("dictionary/default.csv"),
                {"default": "zh-tw.ctb", "math": "Nemeth"},
                Path("data/Bopomofo2Braille.csv"),
                runtime=runtime,
            )

        self.assertEqual(result.raw, ["計算", " ", "1+2", " ", "的值"])
        self.assertEqual("".join(result.braille), "T[計算]⠀M[1+2]⠀T[的值]")
        self.assertEqual(result.raw_to_braille_pos, [0, 5, 6, 12, 13])
        self.assertEqual(result.braille_to_raw_pos, [0] * 5 + [1] + [2] * 6 + [3] + [4] * 5)

    def test_translate_with_language_segments_preserves_math_and_text_boundaries(self) -> None:
        from conversion import service

        text_result = self._translation_result(list("ab"), list("⠁⠃"), [0, 1], [0, 1])
        space_result = self._translation_result([" "], ["⠀"], [0], [0])
        math_result = self._translation_result(["x+1"], list("⠭⠬⠼⠁"), [0, 0, 0, 0], [0])
        runtime = self._runtime(text_translator=Mock(), math_translator=Mock())
        runtime.text_translator.translate.return_value = space_result
        runtime.math_translator.translate.return_value = math_result

        with patch.object(service, "_translate_plain_text_segment", return_value=[text_result]):
            results = translate_with_language_segments(
                "table.ctb",
                "ab$x+1$",
                Path("dictionary.csv"),
                {"default": "table.ctb", "math": "Nemeth"},
                Path("bopomofo.csv"),
                runtime=runtime,
            )

        self.assertEqual(results, [text_result, space_result, math_result])

    def test_convert_text_with_alignment_keeps_segments_unbound(self) -> None:
        segment = self._translation_result(list("word"), list("⠺⠕⠗⠙"), [0, 1, 2, 3], [0, 1, 2, 3])
        request = self.request

        with (
            patch("conversion.service.translate_with_language_segments", return_value=[segment]),
            patch("conversion.service._wrap_translation_results", return_value=("⠺⠕⠗⠙", "source-output")),
        ):
            result = convert_text_with_alignment(
                request,
                map_char=self._map_char,
                runtime=self._fallback_runtime(),
            )

        self.assertIsInstance(result, ConversionOutput)
        self.assertEqual(result.display_text, "⠺⠕⠗⠙")
        self.assertEqual(result.translation_results[0].raw, list("word"))
        self.assertEqual(result.translation_results[0].raw_to_braille_pos, [0, 1, 2, 3])

    def test_convert_text_with_alignment_preserves_character_alignment_for_single_segment_wrap(self) -> None:
        from translate import TranslationResult

        segment = TranslationResult(
            list("word"),
            list("⠺⠕⠗⠙"),
            [0, 1, 2, 3],
            [0, 1, 2, 3],
        )

        with (
            patch("conversion.service.translate_with_language_segments", return_value=[segment]),
            patch("conversion.service._wrap_translation_results", return_value=("⠺⠕⠗⠙", "word")),
        ):
            result = convert_text_with_alignment(
                self.request,
                map_char=self._map_char,
                runtime=self._fallback_runtime(),
            )

        self.assertEqual(result.display_text, "⠺⠕⠗⠙")
        self.assertEqual(result.translation_results[0].raw, list("word"))
        self.assertEqual(result.translation_results[0].raw_to_braille_pos, [0, 1, 2, 3])

    def test_translate_with_language_does_not_duplicate_existing_spaces_around_math(self) -> None:
        from conversion import service
        runtime = self._runtime(text_translator=Mock(), math_translator=Mock())
        runtime.math_translator.translate.return_value = self._translation_result(
            ["1+2"],
            list("⠼⠁⠬⠃"),
            [0, 0, 0, 0],
            [0],
        )

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path, *, runtime):
            from translate import TranslationResult

            braille = list(text)
            return [TranslationResult([text], braille, [0] * len(braille), [0])]

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            result = service.translate_with_language(
                "zh-tw.ctb",
                "計算 $1+2$ 的值",
                Path("dictionary/default.csv"),
                {"default": "zh-tw.ctb", "math": "Nemeth"},
                Path("data/Bopomofo2Braille.csv"),
                runtime=runtime,
            )

        self.assertEqual(result.raw, ["計算 ", "1+2", " 的值"])
        self.assertEqual("".join(result.braille), "計算 ⠼⠁⠬⠃ 的值")

    def test_math_translation_table_options_list_ueb_before_nemeth(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "settings" / "dialogs.py"
        ).read_text(encoding="utf-8")

        self.assertLess(source.index('TableOption(file_name="UEB"'), source.index('TableOption(file_name="Nemeth"'))

    def test_translate_with_language_propagates_math_conversion_failures(self) -> None:
        from conversion import service
        runtime = self._runtime(text_translator=Mock(), math_translator=Mock())
        runtime.math_translator.translate.side_effect = ValueError("math failed")

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path, *, runtime):
            from translate import TranslationResult

            braille = list(text)
            return [TranslationResult([text], braille, [0] * len(braille), [0])]

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            with self.assertRaisesRegex(ValueError, "math failed"):
                service.translate_with_language(
                    "zh-tw.ctb",
                    "計算$1+2$的值",
                    Path("dictionary/default.csv"),
                    {"default": "zh-tw.ctb", "math": "Nemeth"},
                    Path("data/Bopomofo2Braille.csv"),
                    runtime=runtime,
                )

    def test_translate_with_language_passes_selected_math_braille_code(self) -> None:
        from conversion import service
        runtime = self._runtime(text_translator=Mock(), math_translator=Mock())
        runtime.text_translator.translate.return_value = self._translation_result([" "], ["⠀"], [0], [0])
        runtime.math_translator.translate.return_value = self._translation_result(
            ["1"],
            list("⠼⠁"),
            [0, 0],
            [0],
        )

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path, *, runtime):
            from translate import TranslationResult

            braille = list(text)
            return [TranslationResult([text], braille, [0] * len(braille), [0])]

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            service.translate_with_language(
                "zh-tw.ctb",
                "計算$1$",
                Path("dictionary/default.csv"),
                {"default": "zh-tw.ctb", "math": "UEB"},
                Path("data/Bopomofo2Braille.csv"),
                runtime=runtime,
            )

        runtime.math_translator.translate.assert_called_once_with("1", braille_code="UEB")

    def test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment(self) -> None:
        from conversion import service
        runtime = self._runtime(text_translator=Mock(), math_translator=Mock())

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path, *, runtime):
            from translate import TranslationResult

            braille = list(text)
            return [TranslationResult([text], braille, [0] * len(braille), [0])]

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            result = service.translate_with_language(
                "zh-tw.ctb",
                "價格\\$100",
                Path("dictionary/default.csv"),
                {"default": "zh-tw.ctb"},
                Path("data/Bopomofo2Braille.csv"),
                runtime=runtime,
            )

        self.assertEqual(result.raw, ["價格\\$100"])
        self.assertEqual("".join(result.braille), "價格\\$100")

if __name__ == "__main__":
    unittest.main()
