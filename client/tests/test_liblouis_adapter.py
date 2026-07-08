import unittest

from adapters.translation.liblouis import LiblouisTextTranslator


class FakeLouisHelper:
    def __init__(self) -> None:
        self.translate_calls = []
        self.terminated = False

    def translate(self, tables, text, *, mode):
        self.translate_calls.append((tables, text, mode))
        return ([1, 3], [0, 1], [0, 1], None)

    def terminate(self) -> None:
        self.terminated = True


class LiblouisTextTranslatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = FakeLouisHelper()
        self.adapter = LiblouisTextTranslator(
            helper=self.helper,
            tables_dir="/tables",
        )

    def test_regular_translation_preserves_native_mapping(self) -> None:
        result = self.adapter.translate(
            "ab",
            table="en.ctb",
            raw="ab",
        )

        self.assertEqual(self.helper.translate_calls, [(["/tables/en.ctb"], "ab", 4)])
        self.assertEqual(result.raw, ["a", "b"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 1])
        self.assertEqual(result.raw_to_braille_pos, [0, 1])

    def test_single_token_maps_every_cell_to_source_token(self) -> None:
        result = self.adapter.translate(
            "replacement",
            table="zh-tw.ctb",
            raw="原文",
            single_token=True,
        )

        self.assertEqual(result.raw, ["原文"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 0])
        self.assertEqual(result.raw_to_braille_pos, [0])


if __name__ == "__main__":
    unittest.main()
