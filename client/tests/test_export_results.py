import unittest

from documents.export_results import (
    EXPORT_ALL_PARTIAL_MESSAGE,
    EXPORT_ALL_SUCCESS_MESSAGE,
    EXPORT_COMPLETE_TITLE,
    EXPORT_COMPLETE_WITH_ERRORS_TITLE,
    ExportBatchResult,
)


class ExportBatchResultTest(unittest.TestCase):
    def test_all_success_summary(self) -> None:
        result = ExportBatchResult()
        result.add_success("alpha")
        result.add_success("beta")

        self.assertTrue(result.all_succeeded)
        self.assertEqual(result.summary_title, EXPORT_COMPLETE_TITLE)
        self.assertEqual(result.summary_template, EXPORT_ALL_SUCCESS_MESSAGE)
        self.assertEqual(result.summary_values, {})

    def test_partial_failure_summary_lists_names_and_reasons(self) -> None:
        result = ExportBatchResult()
        result.add_success("alpha")
        result.add_failure("beta", "Translation failed")
        result.add_failure("gamma", "Permission denied")

        self.assertFalse(result.all_succeeded)
        self.assertEqual(result.summary_title, EXPORT_COMPLETE_WITH_ERRORS_TITLE)
        self.assertEqual(result.summary_template, EXPORT_ALL_PARTIAL_MESSAGE)
        self.assertEqual(
            result.summary_values,
            {
                "success_count": 1,
                "failure_count": 2,
                "failures": "beta: Translation failed\ngamma: Permission denied",
            },
        )


if __name__ == "__main__":
    unittest.main()
