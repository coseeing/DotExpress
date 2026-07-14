import csv
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from dual_view.model import DualViewSegment
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    convert_text_for_output,
    convert_text_with_alignment,
    get_public_error_message,
    translate_with_language,
    translate_with_language_segments,
)
from conversion.preprocessing.literal_braille import build_literal_translation_result
from conversion.wrapping import wrap_translation_results
from translate import TranslationResult


class FakeTextTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, text: str, *, table: str, raw: str, single_token: bool = False) -> TranslationResult:
        self.calls.append((text, table, raw, single_token))
        if text == " ":
            return TranslationResult([" "], ["⠀"], [0], [0])
        braille = list(f"T[{text}]")
        return TranslationResult([raw] if single_token else [raw], braille, [0] * len(braille), [0])


class FakeMathTranslator:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = []
        self.error = error

    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        self.calls.append((source, braille_code))
        if self.error is not None:
            raise self.error
        braille = list(f"M[{source}]")
        return TranslationResult([source], braille, [0] * len(braille), [0])


class ConversionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.test_dir = Path(self._tmpdir.name)
        self.dictionary_path = self.test_dir / "dictionary.csv"
        self.bopomofo_path = self.test_dir / "Bopomofo2Braille.csv"
        self._write_csv(self.dictionary_path, ["text", "braille", "type"], [])
        self._write_csv(self.bopomofo_path, ["Bopomofo", "Braille"], [])
        self._write_csv(self.test_dir / "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"], [])
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

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

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
            text_translator=text_translator or FakeTextTranslator(),
            math_translator=math_translator or FakeMathTranslator(),
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

    def test_empty_source_does_not_read_or_execute_preprocessing_script(self) -> None:
        dictionary_dir = self.test_dir / "dictionary"
        dictionary_dir.mkdir()
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "raise RuntimeError('must not run')\ndef main(text):\n    return text\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="",
            table_file="table.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
        )

        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(output, ConversionOutput("", (), ()))

    def test_conversion_uses_processed_text_for_translation_and_dual_view(self) -> None:
        dictionary_dir = self.test_dir / "dictionary"
        dictionary_dir.mkdir()
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    return text.replace('raw', 'processed')\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="raw",
            table_file="table.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
        )
        runtime = self._runtime()

        output = convert_text_with_alignment(request, map_char=lambda text, **kwargs: text, runtime=runtime)

        self.assertEqual(output.dual_view_segments[0].result.raw, ["processed"])

    def test_conversion_reports_text_processing_stage(self) -> None:
        dictionary_dir = self.test_dir / "dictionary"
        dictionary_dir.mkdir(exist_ok=True)
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    raise RuntimeError('script boom')\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="raw",
            table_file="table.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
        )

        with self.assertRaises(ConversionStageError) as context:
            convert_text_with_alignment(request, map_char=lambda text, **kwargs: text, runtime=self._runtime())

        self.assertEqual(context.exception.stage, "text_processing")
        self.assertEqual(str(context.exception.error), "script boom")

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

    def test_translate_with_language_merges_text_and_math_segments_in_order(self) -> None:
        from conversion import service

        runtime = self._runtime()
        result = service.translate_with_language(
            "zh-tw.ctb",
            "計算$1+2$的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual(result.raw, ["計算", " ", "1+2", " ", "的值"])
        self.assertEqual("".join(result.braille), "T[計算]⠀M[1+2]⠀T[的值]")
        self.assertEqual(result.raw_to_braille_pos, [0, 5, 6, 12, 13])
        self.assertEqual(result.braille_to_raw_pos, [0] * 5 + [1] + [2] * 6 + [3] + [4] * 5)

    def test_translate_with_language_segments_preserves_math_and_text_boundaries(self) -> None:
        runtime = self._runtime()

        results = translate_with_language_segments(
            "table.ctb",
            "ab$x+1$",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual([result.raw for result in results], [["ab"], [" "], ["x+1"]])
        self.assertEqual(["".join(result.braille) for result in results], ["T[ab]", "⠀", "M[x+1]"])

    def test_literal_punctuation_bypasses_text_translation_and_preserves_source_token(self) -> None:
        text_translator = FakeTextTranslator()
        runtime = self._runtime(text_translator=text_translator)

        results = translate_with_language_segments(
            "table.ctb",
            "A「B」",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual([result.raw for result in results], [["A"], ["「"], ["B"], ["」"]])
        self.assertEqual("".join("".join(result.braille) for result in results), "T[A]⠠⠦T[B]⠠⠴")
        self.assertEqual([call[0] for call in text_translator.calls], ["A", "B"])

    def test_unicode_braille_dictionary_replacement_bypasses_text_translation(self) -> None:
        self._write_csv(
            self.dictionary_path,
            ["text", "braille", "type"],
            [{"text": "台灣", "braille": "⠞⠺", "type": "Braille/Unicode"}],
        )
        text_translator = FakeTextTranslator()
        runtime = self._runtime(text_translator=text_translator)

        results = translate_with_language_segments(
            "table.ctb",
            "台灣",
            self.dictionary_path,
            {"default": "table.ctb"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual([result.raw for result in results], [["台灣"]])
        self.assertEqual(["".join(result.braille) for result in results], ["⠞⠺"])
        self.assertEqual(text_translator.calls, [])

    def test_literal_punctuation_participates_in_existing_wrap_with_its_braille_width(self) -> None:
        literal = build_literal_translation_result("——", "⠐⠠⠤")
        text = self._translation_result(["A"], ["⠁"], [0], [0])

        braille, source = wrap_translation_results([literal, text], width=4)

        self.assertEqual(braille, "⠐⠠⠤⠁")
        self.assertEqual(source, "——A")

    def test_translate_with_language_does_not_duplicate_existing_spaces_around_math(self) -> None:
        from conversion import service
        runtime = self._runtime()
        result = service.translate_with_language(
            "zh-tw.ctb",
            "計算 $1+2$ 的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual(result.raw, ["計算 ", "1+2", " 的值"])
        self.assertEqual("".join(result.braille), "T[計算 ]M[1+2]T[ 的值]")

    def test_translate_with_language_propagates_math_conversion_failures(self) -> None:
        from conversion import service
        runtime = self._runtime(math_translator=FakeMathTranslator(error=ValueError("math failed")))
        with self.assertRaisesRegex(ValueError, "math failed"):
            service.translate_with_language(
                "zh-tw.ctb",
                "計算$1+2$的值",
                self.dictionary_path,
                {"default": "zh-tw.ctb", "math": "Nemeth"},
                self.bopomofo_path,
                runtime=runtime,
            )

    def test_translate_with_language_passes_selected_math_braille_code(self) -> None:
        from conversion import service
        math_translator = FakeMathTranslator()
        runtime = self._runtime(math_translator=math_translator)
        service.translate_with_language(
            "zh-tw.ctb",
            "計算$1$",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "UEB"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual(math_translator.calls, [("1", "UEB")])

    def test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment(self) -> None:
        from conversion import service
        runtime = self._runtime()
        result = service.translate_with_language(
            "zh-tw.ctb",
            "價格\\$100",
            self.dictionary_path,
            {"default": "zh-tw.ctb"},
            self.bopomofo_path,
            runtime=runtime,
        )

        self.assertEqual(result.raw, ["價格\\$100"])
        self.assertEqual("".join(result.braille), "T[價格\\$100]")

    def test_dual_view_segments_exposes_text_source_kind(self) -> None:
        request = ConversionRequest(
            raw_text="hello",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb"},
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(len(output.dual_view_segments), 1)
        self.assertEqual(output.dual_view_segments[0].source_kind, "text")
        self.assertIs(output.translation_results[0], output.dual_view_segments[0].result)

    def test_dual_view_segments_exposes_math_source_kind(self) -> None:
        request = ConversionRequest(
            raw_text="a$x$b",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(
            [seg.source_kind for seg in output.dual_view_segments],
            ["text", "text", "math", "text", "text"],
        )

    def test_dual_view_segments_boundary_space_is_text(self) -> None:
        request = ConversionRequest(
            raw_text="計算$1+2$的值",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(
            [seg.source_kind for seg in output.dual_view_segments],
            ["text", "text", "math", "text", "text"],
        )

    def test_translate_with_language_segments_still_returns_plain_results(self) -> None:
        runtime = self._runtime()
        results = translate_with_language_segments(
            "table.ctb",
            "ab$x+1$",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
        )

        for result in results:
            self.assertIsInstance(result, TranslationResult)

    def test_dual_view_segments_empty_convert_has_empty_tuple(self) -> None:
        request = ConversionRequest(
            raw_text="",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb"},
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(output.display_text, "")
        self.assertEqual(output.translation_results, ())
        self.assertEqual(output.dual_view_segments, ())

if __name__ == "__main__":
    unittest.main()
