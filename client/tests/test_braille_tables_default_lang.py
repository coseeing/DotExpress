import unittest

import braille.tables as tables


class DefaultTableForLanguageTest(unittest.TestCase):
    def test_output_table_follows_language(self) -> None:
        self.assertNotIn("ja_JP", tables._outputTableForLangs)
        for lang, expected in (
            ("zh_TW", "zh-tw.ctb"),
            ("ja_JP", "ja-kantenji.utb"),
            ("xx", tables.DEFAULT_TABLE),
        ):
            with self.subTest(lang=lang):
                self.assertEqual(tables.getDefaultTableForCurLang(tables.TableType.OUTPUT, lang), expected)

    def test_language_is_required(self) -> None:
        with self.assertRaises(TypeError):
            tables.getDefaultTableForCurLang(tables.TableType.OUTPUT)


if __name__ == "__main__":
    unittest.main()
