import csv
import tempfile
import unittest
from pathlib import Path

from Bopomofo import normalize_zhuyin_sequence
from utils import apply_dictionary, split_bracket_segments


class ApplyDictionaryAlignmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_bopomofo_multi_char_entry_aligns_raw_and_replacement_segments(self) -> None:
        dictionary_path = self.tmp_path / "dictionary.csv"
        with dictionary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
            writer.writeheader()
            writer.writerow({"text": "肚子", "braille": "ㄉㄨˋㄗ˙", "type": "Bopomofo"})

        result = apply_dictionary(
            "肚子",
            dictionary_path=dictionary_path,
            bopomofo_path=Path("data/Bopomofo2Braille.csv"),
            processing=normalize_zhuyin_sequence,
        )

        self.assertEqual(
            split_bracket_segments(result["raw"]),
            [
                {"text": "肚", "atomic": True},
                {"text": "子", "atomic": True},
            ],
        )
        self.assertEqual(
            len(split_bracket_segments(result["raw"])),
            len(split_bracket_segments(result["replacement"])),
        )

    def test_braille_multi_char_entry_aligns_with_at_separator(self) -> None:
        dictionary_path = self.tmp_path / "dictionary.csv"
        bopomofo_path = self.tmp_path / "bopomofo.csv"

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

        self.assertEqual(
            split_bracket_segments(result["raw"]),
            [
                {"text": "音", "atomic": True},
                {"text": "樂", "atomic": True},
            ],
        )
        self.assertEqual(
            split_bracket_segments(result["replacement"]),
            [
                {"text": "abc", "atomic": True},
                {"text": "de", "atomic": True},
            ],
        )


if __name__ == "__main__":
    unittest.main()
