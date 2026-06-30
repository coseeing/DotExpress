import unittest

from ui.import_dialog import (
    get_default_import_filter_index,
    get_import_filter_labels,
    get_import_wildcard_text,
)


class ImportDialogTest(unittest.TestCase):
    def test_import_filter_labels_are_ordered_with_all_supported_last(self) -> None:
        self.assertEqual(
            get_import_filter_labels(),
            ["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"],
        )

    def test_import_wildcard_text_matches_the_required_filter_order(self) -> None:
        self.assertEqual(
            get_import_wildcard_text(),
            (
                "DEP (*.dep)|*.dep|"
                "DOCX (*.docx)|*.docx|"
                "EPUB (*.epub)|*.epub|"
                "PDF (*.pdf)|*.pdf|"
                "TXT (*.txt)|*.txt|"
                "All Supported Files (*.dep;*.docx;*.epub;*.pdf;*.txt)|*.dep;*.docx;*.epub;*.pdf;*.txt"
            ),
        )

    def test_default_import_filter_index_points_to_all_supported_files(self) -> None:
        self.assertEqual(get_default_import_filter_index(), 5)


if __name__ == "__main__":
    unittest.main()
