import tempfile
import unittest
from pathlib import Path

from documents.importers.docx_importer import import_docx


class DocxImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "lesson.docx"
        self.path.write_bytes(b"docx")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_rejects_wrong_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, r"must use the \.docx extension"):
            import_docx(self.path.with_suffix(".doc"))


if __name__ == "__main__":
    unittest.main()
