import unittest

from ui.section_navigation import (
    BRAILLE_RESULT_SECTION,
    DOCUMENT_LIST_SECTION,
    SOURCE_TEXT_SECTION,
    VIEW_SECTION,
    get_adjacent_section,
)


class SectionNavigationTest(unittest.TestCase):
    def test_get_adjacent_section_moves_forward(self) -> None:
        self.assertEqual(get_adjacent_section(DOCUMENT_LIST_SECTION, step=1), VIEW_SECTION)

    def test_get_adjacent_section_wraps_forward(self) -> None:
        self.assertEqual(get_adjacent_section(BRAILLE_RESULT_SECTION, step=1), DOCUMENT_LIST_SECTION)

    def test_get_adjacent_section_moves_backward(self) -> None:
        self.assertEqual(get_adjacent_section(BRAILLE_RESULT_SECTION, step=-1), SOURCE_TEXT_SECTION)

    def test_get_adjacent_section_wraps_backward(self) -> None:
        self.assertEqual(get_adjacent_section(DOCUMENT_LIST_SECTION, step=-1), BRAILLE_RESULT_SECTION)


if __name__ == "__main__":
    unittest.main()
