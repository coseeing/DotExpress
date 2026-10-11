import csv
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

from conversion.text import dictionary_rules
from conversion.text.dictionary_rules import (
    DictionaryRulesLoader,
    LoadedDictionaryRules,
    apply_dictionary,
    split_bracket_segments,
)
from dictionaries.entries import DictionaryEntry, load_dictionary_rows
from text.zhuyin import normalize_zhuyin_sequence


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DICTIONARY_HEADER = "text,braille,type\n"
BOPOMOFO_HEADER = "Bopomofo,Braille\n"
TEST_BOPOMOFO = BOPOMOFO_HEADER + "ㄉㄨˋ,⠙⠨\nㄗ˙,⠗⠂\n"


def _identity(text):
    return text


def _split_on_bar(text):
    return text.split("|")


def _raise_value_error(text):
    raise ValueError(f"cannot split {text}")


PROCESSING = {
    "identity": _identity,
    "split on |": _split_on_bar,
    "raises": _raise_value_error,
    "zhuyin": normalize_zhuyin_sequence,
}


class DictionaryCase(NamedTuple):
    name: str
    dictionary: str
    bopomofo: str | None  # None: the real client/data/Bopomofo2Braille.csv
    processing: str
    text: str
    raw: str
    replacement: str


# Expected strings were captured from the unchanged apply_dictionary (P1-6 step 1).
DICTIONARY_CASES = (
    DictionaryCase(
        "@ split aligned per character",
        DICTIONARY_HEADER + "音樂,abc@de,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        "聽音樂",
        r"聽\[音\]\[樂\]",
        r"聽\[abc\]\[de\]",
    ),
    DictionaryCase(
        "part count mismatch collapses to one part",
        DICTIONARY_HEADER + "音樂,a@b@c,Braille/Unicode\n",
        BOPOMOFO_HEADER,
        "identity",
        "音樂",
        r"\[音樂\]",
        r"\[abc\]",
    ),
    DictionaryCase(
        "longest source wins and output is not rescanned",
        DICTIONARY_HEADER + "台,t,\n台灣,wt,\nabc,foo,\no,bar,\n",
        BOPOMOFO_HEADER,
        "identity",
        "台灣台abco",
        r"\[台灣\]\[台\]\[abc\]\[o\]",
        r"\[wt\]\[t\]\[foo\]\[bar\]",
    ),
    DictionaryCase(
        "first duplicate source wins",
        DICTIONARY_HEADER + "台,first,\n台,second,\n",
        BOPOMOFO_HEADER,
        "identity",
        "台",
        r"\[台\]",
        r"\[first\]",
    ),
    DictionaryCase(
        "empty source skipped, missing cell empty, extra cell ignored",
        DICTIONARY_HEADER + ",zz,Braille\n台灣\n灣,⠺,Braille,extra\n",
        BOPOMOFO_HEADER,
        "identity",
        "台灣灣",
        r"\[台灣\]\[灣\]",
        r"\[\]\[⠺\]",
    ),
    DictionaryCase(
        "Bopomofo row with a processing that returns a list",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\n",
        TEST_BOPOMOFO,
        "split on |",
        "肚子",
        r"\[肚\]\[子\]",
        r"\[⠙⠨\]\[⠗⠂\]",
    ),
    DictionaryCase(
        # Was a rule through the fallback (r"\[肚子\]", r"\[⠙⠨⠗⠂\]"); since F-11 (D13) a
        # Bopomofo row the parser rejects is ignored, as the dictionary editor hides it.
        "Bopomofo row with a processing that raises is not a rule",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋㄗ˙,Bopomofo\n",
        TEST_BOPOMOFO,
        "raises",
        "肚子",
        "肚子",
        "肚子",
    ),
    DictionaryCase(
        # F-11 (D13): whitespace-only source texts replaced spaces before (r"\[x\]\[t\]\[y\]").
        "whitespace-only source is not a rule",
        DICTIONARY_HEADER + "  ,x,Braille\n　,y,Braille\n台,t,\n",
        BOPOMOFO_HEADER,
        "identity",
        "  台　",
        r"  \[台\]　",
        r"  \[t\]　",
    ),
    DictionaryCase(
        # F-11 (D13): was the fallback rule r"\[⠙⠌⠐|⠓⠁\]".
        "Bopomofo row the real parser rejects is not a rule",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\n",
        None,
        "zhuyin",
        "肚子",
        "肚子",
        "肚子",
    ),
    DictionaryCase(
        # Rows whose last syllable is first tone and that have their tone space, which the
        # editor shows since F-11 (D14), convert as before. A row without the space was a
        # rule through the fallback (r"\[媽\]", r"\[⠍⠜\]"); the editor hides it, so it is
        # not a rule (decided by the user 2026-10-11).
        "first-tone Bopomofo rows with their tone space convert as before, without it they are not rules",
        DICTIONARY_HEADER + "中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo\n媽,ㄇㄚ,Bopomofo\n",
        None,
        "zhuyin",
        "中心媽",
        r"\[中\]\[心\]媽",
        r"\[⠁⠯⠄\]\[⠑⠹⠄\]媽",
    ),
    DictionaryCase(
        # F-11 (D14, decided by the user 2026-10-11): more whitespace after the last syllable
        # makes the sequence invalid; before, these rows were rules through the fallback.
        "Bopomofo rows with whitespace after the last syllable are not rules",
        DICTIONARY_HEADER + "媽,ㄇㄚ  ,Bopomofo\n肚子,ㄉㄨˋㄗ˙ ,Bopomofo\n",
        None,
        "zhuyin",
        "媽肚子",
        "媽肚子",
        "媽肚子",
    ),
    DictionaryCase(
        # The editor shows the sequence without its leading whitespace, and conversion uses
        # that sequence; the fallback gave r"\[⠄⠍⠜⠄\]" (F-11 D13, D14).
        "Bopomofo row with leading whitespace converts from the sequence without it",
        DICTIONARY_HEADER + "媽, ㄇㄚ ,Bopomofo\n",
        None,
        "zhuyin",
        "媽",
        r"\[媽\]",
        r"\[⠍⠜⠄\]",
    ),
    DictionaryCase(
        "Bopomofo row with the real zhuyin parser and data file",
        DICTIONARY_HEADER + "肚子,ㄉㄨˋㄗ˙,Bopomofo\n音樂,ㄧㄣ ㄩㄝˋ,Bopomofo\n",
        None,
        "zhuyin",
        "肚子聽音樂",
        r"\[肚\]\[子\]聽\[音\]\[樂\]",
        r"\[⠙⠌⠐\]\[⠓⠱⠁\]聽\[⠹⠄\]\[⠦⠐\]",
    ),
    DictionaryCase(
        "input that already contains markers",
        DICTIONARY_HEADER + "灣,w,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        r"\[台\]灣",
        r"\[台\]\[灣\]",
        r"\[台\]\[w\]",
    ),
    DictionaryCase(
        "empty input",
        DICTIONARY_HEADER + "灣,w,Braille\n",
        BOPOMOFO_HEADER,
        "identity",
        "",
        "",
        "",
    ),
    DictionaryCase(
        "header-only dictionary",
        DICTIONARY_HEADER,
        BOPOMOFO_HEADER,
        "identity",
        "台灣",
        "台灣",
        "台灣",
    ),
)

VALID_DICTIONARY = (DICTIONARY_HEADER + "台,t,\n").encode("utf-8")
VALID_BOPOMOFO = BOPOMOFO_HEADER.encode("utf-8")
BOPOMOFO_COLUMNS = "CSV must contain columns: Bopomofo, Braille"
DICTIONARY_COLUMNS = "CSV must contain columns: text, braille, type"
NO_HEADER = "CSV must contain header row."


class ErrorCase(NamedTuple):
    name: str
    dictionary: bytes
    bopomofo: bytes | None  # None: the Bopomofo file does not exist
    error: type
    message: str | None  # None: only the exception type is checked


def _error_cases() -> tuple[ErrorCase, ...]:
    return (
        ErrorCase("Bopomofo file missing", VALID_DICTIONARY, None, FileNotFoundError, None),
        ErrorCase("Bopomofo file empty", VALID_DICTIONARY, b"", ValueError, NO_HEADER),
        ErrorCase("Bopomofo columns missing", VALID_DICTIONARY, b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
        # F-2: a UTF-8 BOM before the header is ignored now (see
        # test_from_paths_ignores_a_utf8_bom_in_both_files); a file that is only a BOM has no header.
        ErrorCase("Bopomofo file is only a BOM", VALID_DICTIONARY, b"\xef\xbb\xbf", ValueError, NO_HEADER),
        ErrorCase("Bopomofo file not UTF-8", VALID_DICTIONARY, b"Bopomofo,Braille\n\xff,x\n", UnicodeDecodeError, None),
        ErrorCase("dictionary empty", b"", VALID_BOPOMOFO, ValueError, NO_HEADER),
        ErrorCase("dictionary columns missing", b"text,braille\n", VALID_BOPOMOFO, ValueError, DICTIONARY_COLUMNS),
        ErrorCase("dictionary is only a BOM", b"\xef\xbb\xbf", VALID_BOPOMOFO, ValueError, NO_HEADER),
        ErrorCase(
            "dictionary with a doubled BOM",
            b"\xef\xbb\xbf\xef\xbb\xbftext,braille,type\n",
            VALID_BOPOMOFO,
            ValueError,
            DICTIONARY_COLUMNS,
        ),
        ErrorCase("dictionary not UTF-8", b"text,braille,type\n\xe9,x,\n", VALID_BOPOMOFO, UnicodeDecodeError, None),
        ErrorCase("both malformed: Bopomofo first", b"text,braille\n", b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
    )


class OpenRecorder:
    """Record the file name of every pathlib.Path.open call while active."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def __enter__(self) -> "OpenRecorder":
        original_open = Path.open
        names = self.names

        def recording_open(path, *args, **kwargs):
            names.append(path.name)
            return original_open(path, *args, **kwargs)

        self._patcher = patch.object(Path, "open", recording_open)
        self._patcher.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._patcher.stop()


class DictionaryFilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = Path(self._tmpdir.name)
        self.dictionary_path = self.tmp_path / "dictionary.csv"
        self.bopomofo_path = self.tmp_path / "bopomofo.csv"

    def write_case_files(self, case: DictionaryCase) -> Path:
        self.dictionary_path.write_text(case.dictionary, encoding="utf-8")
        if case.bopomofo is None:
            return DATA_DIR / "Bopomofo2Braille.csv"
        self.bopomofo_path.write_text(case.bopomofo, encoding="utf-8")
        return self.bopomofo_path

    def write_error_files(self, case: ErrorCase) -> None:
        self.dictionary_path.write_bytes(case.dictionary)
        self.bopomofo_path.unlink(missing_ok=True)
        if case.bopomofo is not None:
            self.bopomofo_path.write_bytes(case.bopomofo)


class ApplyDictionaryTest(DictionaryFilesTestCase):
    def test_apply_dictionary_does_not_remap_dictionary_output(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "abc", "braille": "foo", "type": ""})
            writer.writerow({"text": "o", "braille": "bar", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "abc",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "foo", "atomic": True},
        ])

    def test_apply_dictionary_aligns_braille_multi_char_segments_with_at_separator(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "音樂", "braille": "abc@de", "type": "Braille"})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "音樂",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["raw"]), [
            {"text": "音", "atomic": True},
            {"text": "樂", "atomic": True},
        ])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "abc", "atomic": True},
            {"text": "de", "atomic": True},
        ])

    def test_apply_dictionary_longer_source_strings_win_over_shorter_overlaps(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "abc", "braille": "short", "type": ""})
            writer.writerow({"text": "abcd", "braille": "long", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "abcd",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "long", "atomic": True},
        ])

    def test_apply_dictionary_uses_longest_trie_match_without_target_prefix_requirement(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "台", "braille": "t", "type": ""})
            writer.writerow({"text": "台灣", "braille": "wt", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "台灣台",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "wt", "atomic": True},
            {"text": "t", "atomic": True},
        ])

    def test_apply_dictionary_bopomofo_branch_calls_processing_and_maps_output(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"
        processed: list[str] = []

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "肚子", "braille": "ㄉㄨˋ", "type": "Bopomofo"})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()
            writer.writerow({"Bopomofo": "ㄉㄨˋ", "Braille": "⠙⠨"})

        def processing(text: str) -> str:
            processed.append(text)
            return text

        result = apply_dictionary(
            "肚子",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=processing,
        )

        self.assertEqual(processed, ["ㄉㄨˋ"])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "⠙⠨", "atomic": True},
        ])

    def test_apply_dictionary_collapses_length_mismatch_to_one_segment(self) -> None:
        tmp_path = self.tmp_path
        dictionary_path = tmp_path / "dictionary.csv"
        bopomofo_path = tmp_path / "bopomofo.csv"

        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "音樂", "braille": "abc", "type": ""})

        with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
            writer.writeheader()

        result = apply_dictionary(
            "音樂",
            dictionary_path=dictionary_path,
            bopomofo_path=bopomofo_path,
            processing=lambda text: text,
        )

        self.assertEqual(split_bracket_segments(result["raw"]), [
            {"text": "音樂", "atomic": True},
        ])
        self.assertEqual(split_bracket_segments(result["replacement"]), [
            {"text": "abc", "atomic": True},
        ])

    def test_split_bracket_segments_treats_unclosed_marker_as_text(self) -> None:
        self.assertEqual(split_bracket_segments(r"\[abc"), [
            {"text": r"\[abc", "atomic": False},
        ])


class DictionaryRulesCasesTest(DictionaryFilesTestCase):
    def test_apply_dictionary_gives_the_recorded_output_for_every_case(self) -> None:
        for case in DICTIONARY_CASES:
            with self.subTest(case=case.name):
                bopomofo_path = self.write_case_files(case)

                result = apply_dictionary(
                    case.text,
                    dictionary_path=self.dictionary_path,
                    bopomofo_path=bopomofo_path,
                    processing=PROCESSING[case.processing],
                )

                self.assertEqual(result, {"raw": case.raw, "replacement": case.replacement})


class DictionaryFileSemanticsTest(DictionaryFilesTestCase):
    def test_missing_dictionary_returns_text_without_opening_the_bopomofo_file(self) -> None:
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        for bopomofo_exists in (True, False):
            with self.subTest(bopomofo_exists=bopomofo_exists):
                if not bopomofo_exists:
                    self.bopomofo_path.unlink()

                with OpenRecorder() as recorder:
                    result = apply_dictionary(
                        "台灣",
                        dictionary_path=self.dictionary_path,
                        bopomofo_path=self.bopomofo_path,
                        processing=_identity,
                    )

                self.assertEqual(result, {"raw": "台灣", "replacement": "台灣"})
                self.assertEqual(recorder.names, [])

    def test_reads_the_bopomofo_file_before_the_dictionary(self) -> None:
        self.dictionary_path.write_bytes(VALID_DICTIONARY)
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)

        with OpenRecorder() as recorder:
            apply_dictionary(
                "台",
                dictionary_path=self.dictionary_path,
                bopomofo_path=self.bopomofo_path,
                processing=_identity,
            )

        self.assertEqual(recorder.names, ["bopomofo.csv", "dictionary.csv"])

    def test_malformed_files_raise_the_recorded_errors(self) -> None:
        for case in _error_cases():
            with self.subTest(case=case.name):
                self.write_error_files(case)

                with self.assertRaises(case.error) as context:
                    apply_dictionary(
                        "台",
                        dictionary_path=self.dictionary_path,
                        bopomofo_path=self.bopomofo_path,
                        processing=_identity,
                    )

                if case.message is not None:
                    self.assertEqual(str(context.exception), case.message)


class LoadedDictionaryRulesTest(DictionaryFilesTestCase):
    def test_from_paths_gives_the_recorded_output_for_every_case(self) -> None:
        for case in DICTIONARY_CASES:
            with self.subTest(case=case.name):
                bopomofo_path = self.write_case_files(case)

                rules = LoadedDictionaryRules.from_paths(
                    self.dictionary_path,
                    bopomofo_path,
                    processing=PROCESSING[case.processing],
                )

                self.assertEqual(rules.apply(case.text), {"raw": case.raw, "replacement": case.replacement})

    def test_from_paths_raises_the_recorded_errors(self) -> None:
        for case in _error_cases():
            with self.subTest(case=case.name):
                self.write_error_files(case)

                with self.assertRaises(case.error) as context:
                    LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)

                if case.message is not None:
                    self.assertEqual(str(context.exception), case.message)

    def test_from_paths_ignores_a_utf8_bom_in_both_files(self) -> None:
        dictionary = DICTIONARY_HEADER + "台,⠞,Braille\n都,ㄉㄨˋ,Bopomofo\n"
        plain_dictionary = self.tmp_path / "plain_dictionary.csv"
        plain_bopomofo = self.tmp_path / "plain_bopomofo.csv"
        plain_dictionary.write_text(dictionary, encoding="utf-8")
        plain_bopomofo.write_text(TEST_BOPOMOFO, encoding="utf-8")
        self.dictionary_path.write_text(dictionary, encoding="utf-8-sig")
        self.bopomofo_path.write_text(TEST_BOPOMOFO, encoding="utf-8-sig")
        self.assertTrue(self.dictionary_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertTrue(self.bopomofo_path.read_bytes().startswith(b"\xef\xbb\xbf"))

        plain = LoadedDictionaryRules.from_paths(plain_dictionary, plain_bopomofo, processing=_identity)
        with_bom = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)

        self.assertNotEqual(plain, LoadedDictionaryRules())
        self.assertEqual(with_bom, plain)
        self.assertEqual(with_bom.apply("台都"), plain.apply("台都"))
        self.assertNotEqual(plain.apply("台都")["replacement"], "台都")

    def test_missing_dictionary_gives_empty_rules_without_opening_the_bopomofo_file(self) -> None:
        with OpenRecorder() as recorder:
            rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)

        self.assertEqual(rules, LoadedDictionaryRules())
        self.assertEqual(recorder.names, [])

    def test_rules_are_immutable_tuples_in_file_order(self) -> None:
        self.dictionary_path.write_text(DICTIONARY_HEADER + "乙,Y,\n甲,X,\n乙,Z,\n", encoding="utf-8")
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)

        rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)

        self.assertEqual(rules.raw_rules, (("乙", r"\[乙\]"), ("甲", r"\[甲\]"), ("乙", r"\[乙\]")))
        self.assertEqual(rules.replacement_rules, (("乙", r"\[Y\]"), ("甲", r"\[X\]"), ("乙", r"\[Z\]")))
        with self.assertRaises(FrozenInstanceError):
            rules.raw_rules = ()
        with self.assertRaises(FrozenInstanceError):
            rules.replacement_rules = ()

    def test_apply_reads_no_file_and_builds_no_trie(self) -> None:
        self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)

        with OpenRecorder() as recorder, patch.object(
            dictionary_rules, "_build_trie", wraps=dictionary_rules._build_trie
        ) as build_trie:
            results = [rules.apply(text) for text in ("甲", "乙甲", "甲甲")]

        self.assertEqual(recorder.names, [])
        self.assertEqual(build_trie.call_count, 0)
        self.assertEqual(results[2], {"raw": r"\[甲\]\[甲\]", "replacement": r"\[X\]\[X\]"})

    def test_empty_rules_return_the_text_unchanged(self) -> None:
        self.assertEqual(LoadedDictionaryRules().apply("台灣"), {"raw": "台灣", "replacement": "台灣"})
        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})


class EditorParityTest(DictionaryFilesTestCase):
    """Conversion ignores exactly the rows the dictionary editor hides (F-11 D13, U6)."""

    # (text, braille, type, whether the editor shows the row): the F-4 cases, the rows of
    # dict_badbopo.csv, whitespace variants, other types, and the first-tone cases of D14.
    ROWS = (
        ("Alpha", "⠁", "General", True),
        ("", "⠃", "General", False),
        ("  ", "⠃", "General", False),
        ("　", "⠃", "Braille", False),
        ("\t", "x", "General", False),
        ("臺北", "⠞⠺", "Braille", True),
        ("肚子", "ㄉㄨˋ|ㄗ˙", "Bopomofo", False),
        ("肚子", " ㄉㄨˋ|ㄗ˙ ", "Bopomofo", False),
        ("數學", "ㄕㄨˋ ㄒㄩㄝˊ", "Bopomofo", False),
        ("肚子", "ㄉㄨˋㄗ˙", "Bopomofo", True),
        ("肚子", " ㄉㄨˋㄗ˙", "Bopomofo", True),
        ("肚子", " ㄉㄨˋㄗ˙ ", "Bopomofo", False),
        ("媽", "ㄇㄚ ", "Bopomofo", True),
        ("媽", " ㄇㄚ ", "Bopomofo", True),
        ("媽", "\u3000ㄇㄚ ", "Bopomofo", True),
        ("媽", "ㄇㄚ", "Bopomofo", False),
        ("媽", " ㄇㄚ", "Bopomofo", False),
        ("媽", "ㄇㄚ  ", "Bopomofo", False),
        ("媽", "ㄇㄚ\t", "Bopomofo", False),
        ("媽", "ㄇㄚ\u3000", "Bopomofo", False),
        ("中心", "ㄓㄨㄥ ㄒㄧㄣ ", "Bopomofo", True),
        ("中心", "ㄓㄨㄥˋㄒㄧㄣ ", "Bopomofo", True),
        ("中心", "ㄓㄨㄥ ㄒㄧㄣ", "Bopomofo", False),
        ("肚子", "ㄉㄨˋㄗ˙ ", "Bopomofo", False),
        ("媽", "ㄇㄚˉ", "Bopomofo", False),
        ("空", "", "Bopomofo", True),
        ("q", "invalid", "bopomofo", True),
        ("q", "invalid", " Bopomofo", True),
        ("q", "invalid", "Unknown", True),
        ("q", "invalid", "", True),
        ('q,"x"', "a\r\nb", "Bopomofo", False),
    )

    def test_a_row_is_a_rule_exactly_when_the_editor_shows_it(self) -> None:
        for text, braille, type_, shown in self.ROWS:
            with self.subTest(text=text, braille=braille, type=type_):
                with self.dictionary_path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["text", "braille", "type"])
                    writer.writerow([text, braille, type_])

                rules = LoadedDictionaryRules.from_paths(
                    self.dictionary_path, DATA_DIR / "Bopomofo2Braille.csv", processing=normalize_zhuyin_sequence
                )

                self.assertEqual(isinstance(load_dictionary_rows(self.dictionary_path)[0], DictionaryEntry), shown)
                self.assertEqual(bool(rules.raw_rules), shown)

    def test_the_parser_is_called_once_on_the_sequence_without_its_leading_whitespace(self) -> None:
        # The editor's rule (F-11 D14, decided by the user 2026-10-11): the trailing
        # whitespace stays, and a sequence that does not parse is not tried again with a
        # tone space or converted from its raw symbols.
        for processing_raises in (False, True):
            with self.subTest(processing_raises=processing_raises):
                calls = []

                def processing(text):
                    calls.append(text)
                    if processing_raises:
                        raise ValueError(text)
                    return text

                self.dictionary_path.write_text(DICTIONARY_HEADER + "肚子, ㄉㄨˋ ,Bopomofo\n", encoding="utf-8")
                self.bopomofo_path.write_text(TEST_BOPOMOFO, encoding="utf-8")

                rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=processing)

                self.assertEqual(calls, ["ㄉㄨˋ "])
                self.assertEqual(bool(rules.raw_rules), not processing_raises)


class DictionaryRulesLoaderTest(DictionaryFilesTestCase):
    def test_constructing_a_loader_reads_nothing(self) -> None:
        with OpenRecorder() as recorder, patch.object(
            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
        ) as from_paths:
            DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_raise_value_error)

        self.assertEqual(recorder.names, [])
        self.assertEqual(from_paths.call_count, 0)

    def test_load_reads_the_rules_once_and_returns_the_same_object(self) -> None:
        self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        loader = DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_identity)

        with OpenRecorder() as recorder, patch.object(
            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
        ) as from_paths:
            loaded = [loader.load() for _ in range(3)]

        self.assertEqual(from_paths.call_count, 1)
        self.assertIs(loaded[1], loaded[0])
        self.assertIs(loaded[2], loaded[0])
        self.assertEqual(recorder.names, ["bopomofo.csv", "dictionary.csv"])
        self.assertEqual(loaded[0].apply("甲"), {"raw": r"\[甲\]", "replacement": r"\[X\]"})

    def test_a_failed_load_is_retried_by_the_next_load(self) -> None:
        self.dictionary_path.write_bytes(b"")
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        loader = DictionaryRulesLoader(self.dictionary_path, self.bopomofo_path, processing=_identity)

        with patch.object(
            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
        ) as from_paths:
            with self.assertRaisesRegex(ValueError, "^CSV must contain header row\\.$"):
                loader.load()
            self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
            rules = loader.load()

        self.assertEqual(from_paths.call_count, 2)
        self.assertEqual(rules.replacement_rules, (("甲", r"\[X\]"),))

if __name__ == "__main__":
    unittest.main()
