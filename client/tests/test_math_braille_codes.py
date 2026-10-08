import unittest

import config
from conversion import math_braille_codes


class MathBrailleCodesTest(unittest.TestCase):
    def test_leaf_module_defines_math_braille_codes(self) -> None:
        self.assertEqual(math_braille_codes.MATH_BRAILLE_TABLES, ("UEB", "Nemeth"))
        self.assertEqual(math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE, "UEB")

    def test_config_re_exports_the_leaf_module_values(self) -> None:
        self.assertIs(config.MATH_BRAILLE_TABLES, math_braille_codes.MATH_BRAILLE_TABLES)
        self.assertIs(config.DEFAULT_MATH_BRAILLE_TABLE, math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE)


if __name__ == "__main__":
    unittest.main()
