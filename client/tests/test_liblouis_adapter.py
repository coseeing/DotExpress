import unittest
from unittest.mock import Mock

from adapters.translation.liblouis import LiblouisTextTranslator


class LiblouisTextTranslatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = Mock()
        self.helper.translate.return_value = ([1, 3], [0, 1], [0, 1], None)
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

        self.helper.translate.assert_called_once_with(
            ["/tables/en.ctb"],
            "ab",
            mode=4,
        )
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
