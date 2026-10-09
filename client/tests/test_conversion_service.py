import csv
import tempfile
import unittest
from pathlib import Path

from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from config import DEFAULT_CHARSET_MAPS
from conversion.output import DualViewSegment
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    convert_text_with_alignment,
    get_public_error_message,
    translate_with_language,
    translate_with_language_segments,
)
from translate import TranslationResult


LANG = "zh_TW"
CHARSET_MAPS = dict(DEFAULT_CHARSET_MAPS)


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

    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
        self.calls.append((source, braille_code, language))
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
            output_mode="unicode",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
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
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
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
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
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
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        with self.assertRaises(ConversionStageError) as context:
            convert_text_with_alignment(request, map_char=lambda text, **kwargs: text, runtime=self._runtime())

        self.assertEqual(context.exception.stage, "text_processing")
        self.assertEqual(str(context.exception.error), "script boom")

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
            "計算$1+2$的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual(result.raw, ["計算", " ", "1+2", " ", "的值"])
        self.assertEqual("".join(result.braille), "T[計算]⠀M[1+2]⠀T[的值]")
        self.assertEqual(result.raw_to_braille_pos, [0, 5, 6, 12, 13])
        self.assertEqual(result.braille_to_raw_pos, [0] * 5 + [1] + [2] * 6 + [3] + [4] * 5)

    def test_translate_with_language_segments_preserves_math_and_text_boundaries(self) -> None:
        runtime = self._runtime()

        results = translate_with_language_segments(
            "ab$x+1$",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual([result.raw for result in results], [["ab"], [" "], ["x+1"]])
        self.assertEqual(["".join(result.braille) for result in results], ["T[ab]", "⠀", "M[x+1]"])

    def test_translate_with_language_uses_default_table_for_boundary_space(self) -> None:
        runtime = self._runtime()

        translate_with_language_segments(
            "ab$x+1$",
            self.dictionary_path,
            {"default": "default.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertIn((" ", "default.ctb", " ", False), runtime.text_translator.calls)

    def test_nonstandard_punctuation_is_passed_to_normal_translation(self) -> None:
        text_translator = FakeTextTranslator()
        runtime = self._runtime(text_translator=text_translator)

        results = translate_with_language_segments(
            "甲「乙」",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual([result.raw for result in results], [["甲「乙」"]])
        self.assertEqual([call[0] for call in text_translator.calls], ["甲「乙」"])

    def test_unicode_braille_dictionary_replacement_bypasses_text_translation(self) -> None:
        self._write_csv(
            self.dictionary_path,
            ["text", "braille", "type"],
            [{"text": "台灣", "braille": "⠞⠺", "type": "Braille/Unicode"}],
        )
        text_translator = FakeTextTranslator()
        runtime = self._runtime(text_translator=text_translator)

        results = translate_with_language_segments(
            "台灣",
            self.dictionary_path,
            {"default": "table.ctb"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual([result.raw for result in results], [["台灣"]])
        self.assertEqual(["".join(result.braille) for result in results], ["⠞⠺"])
        self.assertEqual(text_translator.calls, [])

    def test_translate_with_language_does_not_duplicate_existing_spaces_around_math(self) -> None:
        from conversion import service
        runtime = self._runtime()
        result = service.translate_with_language(
            "計算 $1+2$ 的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        # Each source space appears once in the text and once in the braille (the fake
        # translates a lone " " to one blank cell); how the tokens split is pinned below.
        self.assertEqual("".join(result.raw), "計算 1+2 的值")
        self.assertEqual("".join(result.braille), "T[計算 ]M[1+2]⠀T[的值]")

    def test_leading_space_of_a_text_segment_is_its_own_token_and_segment(self) -> None:
        text_translator = FakeTextTranslator()
        result = translate_with_language(
            "計算 $1+2$ 的值",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=self._runtime(text_translator=text_translator),
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        request = ConversionRequest(
            raw_text="計算 $1+2$ 的值",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(result.raw, ["計算 ", "1+2", " ", "的值"])
        self.assertEqual([call[0] for call in text_translator.calls], ["計算 ", " ", "的值"])
        self.assertEqual(
            [(segment.source_kind, segment.result.raw) for segment in output.dual_view_segments],
            [("text", ["計算 "]), ("math", ["1+2"]), ("text", [" "]), ("text", ["的值"])],
        )

    def test_translate_with_language_propagates_math_conversion_failures(self) -> None:
        from conversion import service
        runtime = self._runtime(math_translator=FakeMathTranslator(error=ValueError("math failed")))
        with self.assertRaisesRegex(ValueError, "math failed"):
            service.translate_with_language(
                "計算$1+2$的值",
                self.dictionary_path,
                {"default": "zh-tw.ctb", "math": "Nemeth"},
                self.bopomofo_path,
                runtime=runtime,
                lang=LANG,
                charset_maps=CHARSET_MAPS,
            )

    def test_translate_with_language_passes_selected_math_braille_code(self) -> None:
        from conversion import service
        math_translator = FakeMathTranslator()
        runtime = self._runtime(math_translator=math_translator)
        service.translate_with_language(
            "計算$1$",
            self.dictionary_path,
            {"default": "zh-tw.ctb", "math": "UEB"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual(math_translator.calls, [("1", "UEB", "zh_TW")])

    def test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment(self) -> None:
        from conversion import service
        runtime = self._runtime()
        result = service.translate_with_language(
            "價格\\$100",
            self.dictionary_path,
            {"default": "zh-tw.ctb"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        self.assertEqual(result.raw, ["價格\\$100"])
        self.assertEqual("".join(result.braille), "T[價格\\$100]")

    def test_dual_view_segments_exposes_text_source_kind(self) -> None:
        request = ConversionRequest(
            raw_text="hello",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(len(output.dual_view_segments), 1)
        self.assertEqual(output.dual_view_segments[0].source_kind, "text")
        self.assertIs(output.translation_results[0], output.dual_view_segments[0].result)

    def test_dual_view_segments_exposes_math_source_kind(self) -> None:
        request = ConversionRequest(
            raw_text="a$x$b",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(
            [seg.source_kind for seg in output.dual_view_segments],
            ["text", "text", "math", "text", "text"],
        )

    def test_dual_view_segments_boundary_space_is_text(self) -> None:
        request = ConversionRequest(
            raw_text="計算$1+2$的值",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(
            [seg.source_kind for seg in output.dual_view_segments],
            ["text", "text", "math", "text", "text"],
        )

    def test_translate_with_language_segments_still_returns_plain_results(self) -> None:
        runtime = self._runtime()
        results = translate_with_language_segments(
            "ab$x+1$",
            self.dictionary_path,
            {"default": "table.ctb", "math": "Nemeth"},
            self.bopomofo_path,
            runtime=runtime,
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        for result in results:
            self.assertIsInstance(result, TranslationResult)

    def test_dual_view_segments_empty_convert_has_empty_tuple(self) -> None:
        request = ConversionRequest(
            raw_text="",
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.test_dir,
            translation_tables={"default": "zh-tw.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        output = convert_text_with_alignment(request, runtime=self._runtime())

        self.assertEqual(output.display_text, "")
        self.assertEqual(output.translation_results, ())
        self.assertEqual(output.dual_view_segments, ())


class DictionaryConversionTestCase(unittest.TestCase):
    """Real pipeline over a temporary dictionary and data directory (no tests of its own)."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.test_dir = Path(self._tmpdir.name)
        self.data_dir = self.test_dir / "data"
        self.data_dir.mkdir()
        (self.data_dir / "BopomofoChar2Braille.csv").write_text("Bopomofo,Braille\n", encoding="utf-8")
        (self.data_dir / "Bopomofo2Braille.csv").write_text("Bopomofo,Braille\n", encoding="utf-8")
        self.dictionary_dir = self.test_dir / "dictionary"
        self.dictionary_dir.mkdir()
        self.dictionary_path = self.dictionary_dir / "default.csv"

    def _convert(self, raw_text: str, runtime: TranslationRuntime) -> ConversionOutput:
        request = ConversionRequest(
            raw_text=raw_text,
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.data_dir,
            translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        return convert_text_with_alignment(request, runtime=runtime)

    def _runtime(self) -> TranslationRuntime:
        return TranslationRuntime(text_translator=FakeTextTranslator(), math_translator=FakeMathTranslator())


class DictionaryErrorTimingTest(DictionaryConversionTestCase):
    """When a broken or edited dictionary is read, and which stage reports it."""

    def test_headerless_dictionary_fails_text_at_the_translation_stage(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")

        with self.assertRaises(ConversionStageError) as context:
            self._convert("abc", self._runtime())

        self.assertEqual(context.exception.stage, "translation")
        self.assertIs(type(context.exception.error), ValueError)
        self.assertEqual(str(context.exception.error), "CSV must contain header row.")

    def test_headerless_dictionary_does_not_fail_math_only_or_empty_input(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        for raw_text, segment_count in (("$x$", 1), ("", 0)):
            with self.subTest(raw_text=raw_text):
                output = self._convert(raw_text, self._runtime())

                self.assertEqual(len(output.dual_view_segments), segment_count)

    def test_failing_preprocessing_script_is_reported_before_a_broken_dictionary(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        (self.dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    raise RuntimeError('script boom')\n",
            encoding="utf-8",
        )

        with self.assertRaises(ConversionStageError) as context:
            self._convert("abc", self._runtime())

        self.assertEqual(context.exception.stage, "text_processing")
        self.assertEqual(str(context.exception.error), "script boom")

    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        runtime = self._runtime()

        with self.assertRaises(ConversionStageError) as context:
            self._convert("$x$abc", runtime)

        self.assertEqual(str(context.exception.error), "CSV must contain header row.")
        self.assertEqual(runtime.math_translator.calls, [("x", "Nemeth", LANG)])

    def test_next_conversion_reads_the_rewritten_dictionary(self) -> None:
        texts = []
        for target in ("X", "Y"):
            self.dictionary_path.write_text(f"text,braille,type\n甲,{target},Braille\n", encoding="utf-8")
            runtime = self._runtime()
            self._convert("甲", runtime)
            texts.append([call[0] for call in runtime.text_translator.calls])

        self.assertEqual(texts, [["X"], ["Y"]])

    def test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule(self) -> None:
        self.dictionary_path.write_text("text,braille,type\n甲,X,Braille\n", encoding="utf-8")
        self._convert("甲", self._runtime())
        self.dictionary_path.unlink()
        runtime = self._runtime()

        self._convert("甲", runtime)

        self.assertEqual(runtime.text_translator.calls, [("甲", "zh-tw.ctb", "甲", False)])


class DictionarySnapshotTest(DictionaryConversionTestCase):
    def test_one_conversion_uses_one_dictionary_snapshot(self) -> None:
        dictionary_path = self.dictionary_path
        dictionary_path.write_text("text,braille,type\n甲,X,Braille\n", encoding="utf-8")

        class RewritingTextTranslator(FakeTextTranslator):
            """Rewrites the dictionary (as an external editor would) after the first item."""

            def translate(self, text, **kwargs):
                result = super().translate(text, **kwargs)
                if len(self.calls) == 1:
                    dictionary_path.write_text("text,braille,type\n甲,Y,Braille\n", encoding="utf-8")
                return result

        runtime = TranslationRuntime(text_translator=RewritingTextTranslator(), math_translator=FakeMathTranslator())
        self._convert("甲$x$甲$y$甲", runtime)
        next_runtime = self._runtime()
        self._convert("甲$x$甲$y$甲", next_runtime)

        self.assertEqual([call[0] for call in runtime.text_translator.calls if call[2] == "甲"], ["X", "X", "X"])
        self.assertEqual([call[0] for call in next_runtime.text_translator.calls if call[2] == "甲"], ["Y", "Y", "Y"])


if __name__ == "__main__":
    unittest.main()
