import tempfile
import unittest
from pathlib import Path

from dual_view.files import cleanup_dual_view_html, write_dual_view_html


class DualViewFilesTest(unittest.TestCase):
    def test_write_creates_unique_utf8_owned_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dual_view"
            tokens = iter(("first", "second"))

            first = write_dual_view_html("雙視一", target, token_factory=lambda: next(tokens))
            second = write_dual_view_html("雙視二", target, token_factory=lambda: next(tokens))

            self.assertEqual(first, target / "dual-view-first.html")
            self.assertEqual(second, target / "dual-view-second.html")
            self.assertEqual(first.read_text(encoding="utf-8"), "雙視一")
            self.assertEqual(second.read_text(encoding="utf-8"), "雙視二")

    def test_cleanup_removes_only_owned_html_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dual_view"
            target.mkdir()
            owned = target / "dual-view-stale.html"
            unrelated_html = target / "notes.html"
            unrelated_file = target / "dual-view-not-html.txt"
            owned.write_text("old", encoding="utf-8")
            unrelated_html.write_text("keep", encoding="utf-8")
            unrelated_file.write_text("keep", encoding="utf-8")

            cleanup_dual_view_html(target)

            self.assertFalse(owned.exists())
            self.assertTrue(unrelated_html.exists())
            self.assertTrue(unrelated_file.exists())

    def test_cleanup_accepts_a_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cleanup_dual_view_html(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
