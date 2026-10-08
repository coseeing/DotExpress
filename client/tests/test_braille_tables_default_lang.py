import unittest
from unittest.mock import patch

import braille.tables as tables


class DefaultTableForLanguageTest(unittest.TestCase):
    def test_output_table_follows_language(self) -> None:
        self.assertNotIn("ja_JP", tables._outputTableForLangs)
        for lang, expected in (
            ("zh_TW", "zh-tw.ctb"),
            ("ja_JP", "ja-kantenji.utb"),
            ("xx", tables.DEFAULT_TABLE),
        ):
            with self.subTest(lang=lang), patch("braille.tables.config.get_lang", return_value=lang):
                self.assertEqual(tables.getDefaultTableForCurLang(tables.TableType.OUTPUT), expected)


if __name__ == "__main__":
    unittest.main()
