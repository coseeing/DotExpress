import tempfile
import unittest
from pathlib import Path

from documents.importers.epub_importer import import_epub


class EpubImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "book.epub"
        self.path.write_bytes(b"epub")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_rejects_wrong_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, r"must use the \.epub extension"):
            import_epub(self.path.with_suffix(".zip"))


if __name__ == "__main__":
    unittest.main()
