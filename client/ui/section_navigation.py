DOCUMENT_LIST_SECTION = "document_list"
SOURCE_TEXT_SECTION = "source_text"
BRAILLE_RESULT_SECTION = "braille_result"

SECTION_ORDER = [
    DOCUMENT_LIST_SECTION,
    SOURCE_TEXT_SECTION,
    BRAILLE_RESULT_SECTION,
]


def get_adjacent_section(current_section: str, step: int) -> str:
    index = SECTION_ORDER.index(current_section)
    return SECTION_ORDER[(index + step) % len(SECTION_ORDER)]
