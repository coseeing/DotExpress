import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from config import DEFAULT_CHARSET_MAPS
from conversion import service
from conversion.output import ConversionRequest, convert_text_with_alignment
from conversion.text import dictionary_rules
from conversion.text.dictionary_rules import apply_dictionary, split_bracket_segments
from conversion.text.pipeline import (
    TextProcessingError,
    preprocess_source_text,
    translate_plain_text_segment,
)
from translate import TranslationResult


LANGUAGE_TABLES = {"default": "default.ctb", "en": "en.ctb", "zh": "zh.ctb", "ja": "ja.ctb"}
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
READ_COUNT_TABLES = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb", "zh": "zh-tw.ctb", "math": "Nemeth"}
# Twelve plain-text items for the language detector, around one inline math segment.
MIXED_TEXT = "台灣 is 美麗 island, 中文 and English 混合 $x+1$ 測試 test 完成 done"
COUNTED_FILES = ("dictionary.csv", "Bopomofo2Braille.csv", "BopomofoChar2Braille.csv", "Braille2Ascii.csv")


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

    def _recording_runtime(self, calls: list) -> TranslationRuntime:
        class Translator:
            def translate(self, text, *, table, raw, single_token=False):
                calls.append((text, table))
                return TranslationResult(raw, text, list(range(len(text))), list(range(len(raw))))

        return TranslationRuntime(text_translator=Translator(), math_translator=Translator())

    def _plain_text_paths(self, directory: Path) -> tuple[Path, Path]:
        dictionary_path = self._write_csv(directory, "dictionary.csv", ["text", "braille", "type"], [])
        bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])
        return dictionary_path, bopomofo_path

    def test_preprocess_source_text_runs_user_script_before_bopomofo_mapping(self) -> None:
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

            events = []

            def execute_script(path: Path, text: str) -> str:
                events.append(("script", path, text))
                return text.replace("B", "ㄅ")

            def map_char(text: str, **kwargs) -> str:
                events.append(("map", text))
                return "⠃"

            result = preprocess_source_text(
                "B",
                data_dir=data_dir,
                script_path=directory / "upper.py",
                execute_script=execute_script,
                map_char=map_char,
            )

            self.assertEqual(result, "⠃")
            self.assertEqual(
                events,
                [
                    ("script", directory / "upper.py", "B"),
                    ("map", "ㄅ"),
                ],
            )

    def test_no_processing_runs_no_script_and_still_maps_characters(self) -> None:
        # F-18 (D4): script_path None is No Processing.
        def execute_script(_path: Path, _text: str) -> str:
            raise AssertionError("No Processing must not run a script")

        events = []

        def map_char(text: str, **kwargs) -> str:
            events.append(("map", text, kwargs["dictionary_path"]))
            return "mapped"

        result = preprocess_source_text(
            "B",
            data_dir=Path("data"),
            script_path=None,
            execute_script=execute_script,
            map_char=map_char,
        )

        self.assertEqual(result, "mapped")
        self.assertEqual(events, [("map", "B", Path("data") / "BopomofoChar2Braille.csv")])

    def test_preprocess_source_text_preserves_script_exception(self) -> None:
        error = RuntimeError("script boom")

        def execute_script(_path: Path, _text: str) -> str:
            raise error

        with self.assertRaises(TextProcessingError) as context:
            preprocess_source_text(
                "source",
                data_dir=Path("data"),
                script_path=Path("script/upper.py"),
                execute_script=execute_script,
            )

        self.assertIs(context.exception.error, error)

    def test_preprocess_source_text_normalizes_system_exit(self) -> None:
        def execute_script(_path: Path, _text: str) -> str:
            raise SystemExit("requested exit")

        with self.assertRaises(TextProcessingError) as context:
            preprocess_source_text(
                "source",
                data_dir=Path("data"),
                script_path=Path("script/upper.py"),
                execute_script=execute_script,
            )

        self.assertIsInstance(context.exception.error, RuntimeError)
        self.assertEqual(str(context.exception.error), "SystemExit: requested exit")

    def test_apply_dictionary_returns_bracketed_raw_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            dictionary_path = self._write_csv(
                directory,
                "dictionary.csv",
                ["text", "braille", "type"],
                [{"text": "abc", "braille": "foo", "type": ""}],
            )
            bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])

            result = apply_dictionary(
                "abc",
                dictionary_path=dictionary_path,
                bopomofo_path=bopomofo_path,
                processing=lambda text: text,
            )

            self.assertEqual(set(result), {"raw", "replacement"})
            self.assertEqual(split_bracket_segments(result["raw"]), [{"text": "abc", "atomic": True}])
            self.assertEqual(split_bracket_segments(result["replacement"]), [{"text": "foo", "atomic": True}])

    def test_plain_text_translation_uses_current_language_when_no_language_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            dictionary_path = self._write_csv(directory, "dictionary.csv", ["text", "braille", "type"], [])
            bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])
            calls = []

            class Translator:
                def translate(self, text, *, table, raw, single_token=False):
                    calls.append(table)
                    return TranslationResult(raw, text, list(range(len(text))), list(range(len(raw))))

            runtime = TranslationRuntime(text_translator=Translator(), math_translator=Translator())

            translate_plain_text_segment(
                "Hello",
                dictionary_path,
                {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"},
                bopomofo_path,
                runtime=runtime,
                lang="en",
                charset_maps=dict(DEFAULT_CHARSET_MAPS),
            )

            self.assertEqual(calls, ["en-ueb-g1.ctb"])

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

            result = apply_dictionary(
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

    def test_alignment_output_entry_applies_source_preprocessing_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            data_dir = directory / "data"
            dictionary_dir = directory / "dictionary"
            data_dir.mkdir()
            dictionary_dir.mkdir()
            dictionary_path = self._write_csv(dictionary_dir, "default.csv", ["text", "braille", "type"], [])
            script_path = directory / "script" / "processed.py"
            script_path.parent.mkdir()
            script_path.write_text(
                "def main(text):\n    return text.replace('raw', 'processed')\n",
                encoding="utf-8",
            )
            self._write_csv(data_dir, "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"], [])
            self._write_csv(data_dir, "Bopomofo2Braille.csv", ["Bopomofo", "Braille"], [])

            request = ConversionRequest(
                raw_text="raw",
                output_mode="unicode",
                width=40,
                dictionary_path=dictionary_path,
                data_dir=data_dir,
                translation_tables={"default": "table.ctb"},
                lang="en",
                charset_maps=dict(DEFAULT_CHARSET_MAPS),
                script_path=script_path,
            )

            translated_texts = []
            result = convert_text_with_alignment(
                request,
                translate_segments=lambda text, *_args, **_kwargs: translated_texts.append(text) or [],
                wrap_translation_results=lambda translations, width: ("wrapped", "processed"),
                map_char=lambda text, **kwargs: text,
                runtime=self._runtime(),
            )

            self.assertEqual(result.display_text, "wrapped")
            self.assertEqual(translated_texts, ["processed"])

    def test_non_detecting_text_uses_current_language_table(self) -> None:
        for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as tmpdir:
                dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
                calls = []

                translate_plain_text_segment(
                    "\u2192",
                    dictionary_path,
                    LANGUAGE_TABLES,
                    bopomofo_path,
                    runtime=self._recording_runtime(calls),
                    lang=lang,
                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
                )

                self.assertEqual(calls, [("\u2192", table)])

    def test_cjk_charset_map_selects_table_for_cjk_text(self) -> None:
        for cjk_language, table in (("zh", "zh.ctb"), ("ja", "ja.ctb")):
            charset_maps = {
                "latinCharactersLanguage": "en",
                "CJKCharactersLanguage": cjk_language,
                "arabicCharactersLanguage": "ar",
            }
            with self.subTest(cjk_language=cjk_language), tempfile.TemporaryDirectory() as tmpdir:
                dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
                calls = []

                translate_plain_text_segment(
                    "A中",
                    dictionary_path,
                    LANGUAGE_TABLES,
                    bopomofo_path,
                    runtime=self._recording_runtime(calls),
                    lang="en",
                    charset_maps=charset_maps,
                )

                self.assertEqual(calls, [("A", "en.ctb"), (" ", "en.ctb"), ("中", table)])


class DictionaryReadCountTest(unittest.TestCase):
    """Each rule file is opened at most once per conversion, however many items the text has."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.test_dir = Path(self._tmpdir.name)
        self.dictionary_path = self.test_dir / "dictionary.csv"
        self.dictionary_path.write_text("text,braille,type\n台灣,⠞⠺,Braille/Unicode\n", encoding="utf-8")

    def _runtime(self) -> TranslationRuntime:
        return TranslationRuntime(text_translator=FallbackTextTranslator(), math_translator=FallbackMathTranslator())

    def _convert(self, raw_text: str, output_mode: str = "unicode"):
        request = ConversionRequest(
            raw_text=raw_text,
            output_mode=output_mode,
            width=40,
            dictionary_path=self.dictionary_path,
            data_dir=DATA_DIR,
            translation_tables=dict(READ_COUNT_TABLES),
            lang="zh_TW",
            charset_maps=dict(DEFAULT_CHARSET_MAPS),
        )
        return service.convert_text_with_alignment(request, runtime=self._runtime())

    def _opened(self, call) -> dict[str, int]:
        """Run call() and return how often each counted file was opened through Path.open."""
        counts: Counter[str] = Counter()
        original_open = Path.open

        def counting_open(path, *args, **kwargs):
            counts[path.name] += 1
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", counting_open):
            call()
        return {name: counts[name] for name in COUNTED_FILES}

    def _count_apply(self):
        rules_class = dictionary_rules.LoadedDictionaryRules
        return patch.object(rules_class, "apply", autospec=True, side_effect=rules_class.apply)

    def test_unicode_conversion_opens_each_rule_file_once(self) -> None:
        with self._count_apply() as apply:
            opened = self._opened(lambda: self._convert(MIXED_TEXT))

        self.assertGreaterEqual(apply.call_count, 8)
        self.assertEqual(
            opened,
            {"dictionary.csv": 1, "Bopomofo2Braille.csv": 1, "BopomofoChar2Braille.csv": 1, "Braille2Ascii.csv": 0},
        )

    def test_ascii_conversion_also_opens_the_ascii_map_once(self) -> None:
        with self._count_apply() as apply:
            opened = self._opened(lambda: self._convert(MIXED_TEXT, output_mode="ascii"))

        self.assertGreaterEqual(apply.call_count, 8)
        self.assertEqual(
            opened,
            {"dictionary.csv": 1, "Bopomofo2Braille.csv": 1, "BopomofoChar2Braille.csv": 1, "Braille2Ascii.csv": 1},
        )

    def test_conversion_parses_the_rules_once_and_builds_three_tries(self) -> None:
        rules_class = dictionary_rules.LoadedDictionaryRules
        with patch.object(rules_class, "from_paths", wraps=rules_class.from_paths) as from_paths, patch.object(
            dictionary_rules, "_build_trie", wraps=dictionary_rules._build_trie
        ) as build_trie:
            self._convert(MIXED_TEXT)

        self.assertEqual(from_paths.call_count, 1)
        self.assertEqual(build_trie.call_count, 3)

    def test_math_only_conversion_opens_no_dictionary_file(self) -> None:
        opened = self._opened(lambda: self._convert("$x+1$"))

        self.assertEqual(opened["dictionary.csv"], 0)
        self.assertEqual(opened["Bopomofo2Braille.csv"], 0)

    def test_translate_with_language_opens_each_dictionary_file_once(self) -> None:
        opened = self._opened(
            lambda: service.translate_with_language(
                MIXED_TEXT,
                self.dictionary_path,
                dict(READ_COUNT_TABLES),
                DATA_DIR / "Bopomofo2Braille.csv",
                runtime=self._runtime(),
                lang="zh_TW",
                charset_maps=dict(DEFAULT_CHARSET_MAPS),
            )
        )

        self.assertEqual(opened["dictionary.csv"], 1)
        self.assertEqual(opened["Bopomofo2Braille.csv"], 1)

    def test_every_conversion_reads_the_rules_again(self) -> None:
        rules_class = dictionary_rules.LoadedDictionaryRules
        with patch.object(rules_class, "from_paths", wraps=rules_class.from_paths) as from_paths:
            self._convert(MIXED_TEXT)
            self._convert(MIXED_TEXT)

        self.assertEqual(from_paths.call_count, 2)

    def test_standalone_plain_text_segment_opens_each_dictionary_file_once(self) -> None:
        with self._count_apply() as apply:
            opened = self._opened(
                lambda: translate_plain_text_segment(
                    "台灣 is 美麗 island, 中文 and English",
                    self.dictionary_path,
                    dict(READ_COUNT_TABLES),
                    DATA_DIR / "Bopomofo2Braille.csv",
                    runtime=self._runtime(),
                    lang="zh_TW",
                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
                )
            )

        self.assertGreater(apply.call_count, 1)
        self.assertEqual(opened["dictionary.csv"], 1)
        self.assertEqual(opened["Bopomofo2Braille.csv"], 1)

    def test_plain_text_segment_uses_the_given_loader_instead_of_the_paths(self) -> None:
        loader = dictionary_rules.DictionaryRulesLoader(
            self.dictionary_path,
            DATA_DIR / "Bopomofo2Braille.csv",
            processing=lambda text: text,
        )
        results = []

        def translate():
            results.append(
                translate_plain_text_segment(
                    "台灣",
                    self.test_dir / "missing.csv",
                    dict(READ_COUNT_TABLES),
                    self.test_dir / "missing-bopomofo.csv",
                    runtime=self._runtime(),
                    lang="zh_TW",
                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
                    dictionary_rules=loader,
                )
            )

        first = self._opened(translate)
        second = self._opened(translate)

        self.assertEqual([first["dictionary.csv"], second["dictionary.csv"]], [1, 0])
        self.assertEqual(["".join(result[0].braille) for result in results], ["⠞⠺", "⠞⠺"])
