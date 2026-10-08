import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from adapters.translation.contracts import TranslationRuntime
from conversion.service import ConversionRequest, convert_text_with_alignment


TABLES = {
    "default": "default.ctb",
    "en": "en.ctb",
    "zh": "zh.ctb",
    "ja": "ja.ctb",
    "math": "Nemeth",
}
MIXED_TEXT = "Hello 中文 $1$"
MIXED_TEXT_BRAILLE = "T[Hello ]T[ ]T[中文 ]M[1]"
MIXED_TEXT_CALLS = [
    ("Hello ", "en.ctb"),
    (" ", "en.ctb"),
    ("中文 ", "zh.ctb"),
]


# The fakes import TranslationResult per call: tests.test_translation_result_core
# re-imports `translate`, and the wrapping step only accepts the current class.
class RecordingTextTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, text, *, table, raw, single_token=False):
        from translate import TranslationResult

        self.calls.append((text, table))
        braille = list(f"T[{text}]")
        return TranslationResult([raw], braille, [0] * len(braille), [0])


class RecordingMathTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, source, *, braille_code, language):
        from translate import TranslationResult

        self.calls.append((source, braille_code))
        braille = list(f"M[{source}]")
        return TranslationResult([source], braille, [0] * len(braille), [0])


class ConversionLanguageTest(unittest.TestCase):
    def setUp(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        directory = Path(tmpdir.name)
        self.data_dir = directory / "data"
        dictionary_dir = directory / "dictionary"
        self.data_dir.mkdir()
        dictionary_dir.mkdir()
        self.dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(self.dictionary_path, ["text", "braille", "type"])
        self._write_csv(self.data_dir / "Bopomofo2Braille.csv", ["Bopomofo", "Braille"])
        self._write_csv(self.data_dir / "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"])

    def _write_csv(self, path: Path, fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    def _convert(self, raw_text: str):
        text_translator = RecordingTextTranslator()
        math_translator = RecordingMathTranslator()
        request = ConversionRequest(
            raw_text=raw_text,
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.data_dir,
            translation_tables=dict(TABLES),
        )
        output = convert_text_with_alignment(
            request,
            map_char=lambda text, **_kwargs: text,
            runtime=TranslationRuntime(text_translator=text_translator, math_translator=math_translator),
        )
        return output, text_translator.calls, math_translator.calls

    def test_mixed_text_translation_for_english(self) -> None:
        with patch.object(config, "get_lang", return_value="en"), patch.object(
            config, "get_charset_maps", return_value=dict(config.DEFAULT_CHARSET_MAPS)
        ):
            output, text_calls, math_calls = self._convert(MIXED_TEXT)

        self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
        self.assertEqual(text_calls, MIXED_TEXT_CALLS)
        self.assertEqual(math_calls, [("1", "Nemeth")])

    def test_non_detecting_text_follows_language(self) -> None:
        for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
            with self.subTest(lang=lang):
                with patch.object(config, "get_lang", return_value=lang):
                    _output, text_calls, _math_calls = self._convert("\u2192")

                self.assertEqual(text_calls, [("\u2192", table)])


if __name__ == "__main__":
    unittest.main()
