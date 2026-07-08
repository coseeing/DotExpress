import csv
import tempfile
import unittest
from pathlib import Path

from adapters.translation.contracts import TranslationRuntime
from conversion.output import ConversionRequest, convert_text_for_output, convert_text_with_alignment
from conversion.text.dictionary_rules import split_bracket_segments
from conversion.text.pipeline import apply_plain_text_rules, preprocess_source_text


class ConversionTextPipelineTest(unittest.TestCase):
    def _write_csv(self, directory: Path, name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> Path:
        path = directory / name
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def _runtime(self) -> TranslationRuntime:
        class Translator:
            def translate(self, *_args, **_kwargs):
                raise AssertionError("runtime translator should not be used")

        return TranslationRuntime(text_translator=Translator(), math_translator=Translator())

    def test_preprocess_source_text_applies_bopomofo_char_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            data_dir = directory / "data"
            data_dir.mkdir()
            self._write_csv(
                data_dir,
                "BopomofoChar2Braille.csv",
                ["Bopomofo", "Braille"],
                [{"Bopomofo": "ㄅ", "Braille": "⠃"}],
            )

            self.assertEqual(preprocess_source_text("ㄅ", data_dir=data_dir), "⠃")

    def test_apply_plain_text_rules_returns_bracketed_raw_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            dictionary_path = self._write_csv(
                directory,
                "dictionary.csv",
                ["text", "braille", "type"],
                [{"text": "abc", "braille": "foo", "type": ""}],
            )
            bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])

            result = apply_plain_text_rules(
                "abc",
                dictionary_path=dictionary_path,
                bopomofo_path=bopomofo_path,
                processing=lambda text: text,
            )

            self.assertEqual(set(result), {"raw", "replacement"})
            self.assertEqual(split_bracket_segments(result["raw"]), [{"text": "abc", "atomic": True}])
            self.assertEqual(split_bracket_segments(result["replacement"]), [{"text": "foo", "atomic": True}])

    def test_atomic_flags_remain_paired_before_runtime_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            dictionary_path = self._write_csv(
                directory,
                "dictionary.csv",
                ["text", "braille", "type"],
                [{"text": "音樂", "braille": "abc@de", "type": ""}],
            )
            bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])

            result = apply_plain_text_rules(
                "音樂",
                dictionary_path=dictionary_path,
                bopomofo_path=bopomofo_path,
                processing=lambda text: text,
            )

            raw_segments = split_bracket_segments(result["raw"])
            replacement_segments = split_bracket_segments(result["replacement"])
            self.assertEqual(
                [segment["atomic"] for segment in raw_segments],
                [segment["atomic"] for segment in replacement_segments],
            )

    def test_both_output_entry_points_share_source_preprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            data_dir = directory / "data"
            data_dir.mkdir()
            dictionary_path = self._write_csv(directory, "dictionary.csv", ["text", "braille", "type"], [])
            self._write_csv(
                data_dir,
                "BopomofoChar2Braille.csv",
                ["Bopomofo", "Braille"],
                [{"Bopomofo": "ㄅ", "Braille": "⠃"}],
            )
            self._write_csv(data_dir, "Bopomofo2Braille.csv", ["Bopomofo", "Braille"], [])
            self._write_csv(data_dir, "Braille2Ascii.csv", ["Braille", "Ascii"], [{"Braille": "⠁", "Ascii": "a"}])

            request = ConversionRequest(
                raw_text="ㄅ",
                table_file="zh-tw.ctb",
                output_mode="unicode",
                width=40,
                dictionary_path=dictionary_path,
                data_dir=data_dir,
                translation_tables={"default": "zh-tw.ctb"},
            )

            runtime = self._runtime()
            map_calls: list[str] = []

            def map_char(text: str, *, dictionary_path: Path, from_field: str, to_field: str) -> str:
                map_calls.append(text)
                return f"mapped:{text}"

            alignment_result = convert_text_with_alignment(
                request,
                translate_segments=lambda *args, **kwargs: [],
                wrap_translation_results=lambda translations, width: ("wrapped", "source"),
                map_char=map_char,
                runtime=runtime,
            )
            output_result = convert_text_for_output(
                request,
                convert_with_alignment=lambda *args, **kwargs: alignment_result,
                default_wrap_both=lambda **kwargs: ("wrapped", "source"),
                wrap_both=lambda **kwargs: ("wrapped", "source"),
                map_char=map_char,
                runtime=runtime,
            )

            self.assertIsNotNone(alignment_result)
            self.assertEqual(output_result, "wrapped")
            self.assertEqual(map_calls, ["ㄅ", "ㄅ"])
