import unittest

from documents.session import (
    DeleteDocumentDecision,
    plan_delete_document,
)
from documents.workspace import Document


class DocumentSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            Document(name="alpha", text="a", braille="1"),
            Document(name="math", text="m", braille="2"),
            Document(name="zoo", text="z", braille="3"),
        ]

    def test_plan_delete_document_prefers_previous_selection_and_tracks_open_document(self) -> None:
        self.assertEqual(
            plan_delete_document(self.documents, "math", open_name="math"),
            DeleteDocumentDecision(preferred_name="alpha", was_open=True),
        )

    def test_plan_delete_document_uses_next_selection_when_first_removed(self) -> None:
        self.assertEqual(
            plan_delete_document(self.documents, "alpha", open_name="zoo"),
            DeleteDocumentDecision(preferred_name="math", was_open=False),
        )


if __name__ == "__main__":
    unittest.main()
