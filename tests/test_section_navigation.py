import unittest

from section_navigation import (
    DOCUMENT_LIST_SECTION,
    SECTION_ORDER,
    BRAILLE_RESULT_SECTION,
    CONVERSION_SECTION,
    SOURCE_TEXT_SECTION,
    VIEW_SECTION,
    get_adjacent_section,
)


class SectionNavigationTest(unittest.TestCase):
    def test_section_order_matches_expected_cycle(self) -> None:
        self.assertEqual(
            SECTION_ORDER,
            [
                CONVERSION_SECTION,
                DOCUMENT_LIST_SECTION,
                VIEW_SECTION,
                SOURCE_TEXT_SECTION,
                BRAILLE_RESULT_SECTION,
            ],
        )

    def test_get_adjacent_section_moves_forward(self) -> None:
        self.assertEqual(get_adjacent_section(CONVERSION_SECTION, step=1), DOCUMENT_LIST_SECTION)

    def test_get_adjacent_section_wraps_forward(self) -> None:
        self.assertEqual(get_adjacent_section(BRAILLE_RESULT_SECTION, step=1), CONVERSION_SECTION)

    def test_get_adjacent_section_moves_backward(self) -> None:
        self.assertEqual(get_adjacent_section(BRAILLE_RESULT_SECTION, step=-1), SOURCE_TEXT_SECTION)

    def test_get_adjacent_section_wraps_backward(self) -> None:
        self.assertEqual(get_adjacent_section(CONVERSION_SECTION, step=-1), BRAILLE_RESULT_SECTION)


if __name__ == "__main__":
    unittest.main()
