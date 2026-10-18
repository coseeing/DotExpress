import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from adapters.translation.contracts import TranslationRuntime
from conversion.service import ConversionRequest, convert_text_with_alignment
from tests.script_support import no_processing_script_path
from translate import TranslationResult


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


class RecordingTextTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, text, *, table, raw, single_token=False):
        self.calls.append((text, table))
        braille = list(f"T[{text}]")
        return TranslationResult([raw], braille, [0] * len(braille), [0])


class RecordingMathTranslator:
    def __init__(self) -> None:
        self.calls = []

    def translate(self, source, *, braille_code, language):
        self.calls.append((source, braille_code, language))
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
        original_runtime_lang = config._runtime_lang
        self.addCleanup(setattr, config, "_runtime_lang", original_runtime_lang)

    def _write_csv(self, path: Path, fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    def _request(self, raw_text: str, *, lang: str) -> ConversionRequest:
        return ConversionRequest(
            raw_text=raw_text,
            output_mode="unicode",
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=self.data_dir,
            translation_tables=dict(TABLES),
            lang=lang,
            charset_maps=dict(config.DEFAULT_CHARSET_MAPS),
            script_path=no_processing_script_path(),
        )

    def _convert(self, request: ConversionRequest, *, env_lang: str):
        text_translator = RecordingTextTranslator()
        math_translator = RecordingMathTranslator()
        config._runtime_lang = "ko"
        with patch.dict(os.environ, {config.LANG_ENV: env_lang}), patch.object(
            config.ConfigStore, "get_lang", side_effect=AssertionError("ConfigStore.get_lang must not be read")
        ), patch.object(
            config.ConfigStore, "get_charset_maps", side_effect=AssertionError("ConfigStore.get_charset_maps must not be read")
        ):
            output = convert_text_with_alignment(
                request,
                map_char=lambda text, **_kwargs: text,
                runtime=TranslationRuntime(text_translator=text_translator, math_translator=math_translator),
            )
        return output, text_translator.calls, math_translator.calls

    def test_same_request_gives_same_output_in_any_environment(self) -> None:
        request = self._request(MIXED_TEXT, lang="en")

        first = self._convert(request, env_lang="zh_TW")
        second = self._convert(request, env_lang="ja")

        for output, text_calls, math_calls in (first, second):
            self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
            self.assertEqual(text_calls, MIXED_TEXT_CALLS)
            self.assertEqual(math_calls, [("1", "Nemeth", "en")])
        self.assertEqual(first[0].display_text, second[0].display_text)

    def test_non_detecting_text_follows_request_language(self) -> None:
        for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
            with self.subTest(lang=lang):
                _output, text_calls, _math_calls = self._convert(
                    self._request("\u2192", lang=lang),
                    env_lang="ja",
                )

                self.assertEqual(text_calls, [("\u2192", table)])


if __name__ == "__main__":
    unittest.main()
