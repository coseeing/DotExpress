import unittest
from pathlib import Path

from conversion.service import (
    ConversionRequest,
    ConversionStageError,
    convert_text_for_output,
    get_public_error_message,
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

    def _wrap(self, *, table_file, text, width, dictionary_path, translation_tables, bopomofo_path):
        self.calls.append(("wrap", table_file, text, width, dictionary_path, translation_tables, bopomofo_path))
        return "braille-output", "source-output"

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

        result = convert_text_for_output(request, map_char=self._map_char, wrap_both=self._wrap)

        self.assertEqual(result, "")

    def test_convert_text_for_output_returns_unicode_braille_output(self) -> None:
        result = convert_text_for_output(self.request, map_char=self._map_char, wrap_both=self._wrap)

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

        result = convert_text_for_output(request, map_char=self._map_char, wrap_both=self._wrap)

        self.assertEqual(result, "ascii:braille-output")

    def test_convert_text_for_output_propagates_translation_failures(self) -> None:
        def failing_wrap(**_kwargs):
            raise ValueError("translation boom")

        with self.assertRaisesRegex(ConversionStageError, "translation boom") as context:
            convert_text_for_output(self.request, map_char=self._map_char, wrap_both=failing_wrap)
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
            convert_text_for_output(request, map_char=failing_map, wrap_both=self._wrap)
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

if __name__ == "__main__":
    unittest.main()
