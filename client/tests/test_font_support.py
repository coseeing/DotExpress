import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ui.font_support import register_private_font_for_windows


class FontSupportTest(unittest.TestCase):
    def test_register_private_font_for_windows_returns_false_for_missing_file(self) -> None:
        result = register_private_font_for_windows(Path('/tmp/missing.ttf'), platform='win32')
        self.assertFalse(result)

    def test_register_private_font_for_windows_skips_non_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            font_path = Path(tmpdir) / 'SimBraille.ttf'
            font_path.write_bytes(b'font')
            add_font = Mock(return_value=1)
            result = register_private_font_for_windows(font_path, platform='linux', add_font_resource_ex=add_font)
        self.assertFalse(result)
        add_font.assert_not_called()

    def test_register_private_font_for_windows_uses_gdi_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            font_path = Path(tmpdir) / 'SimBraille.ttf'
            font_path.write_bytes(b'font')
            add_font = Mock(return_value=1)
            result = register_private_font_for_windows(font_path, platform='win32', add_font_resource_ex=add_font)
        self.assertTrue(result)
        add_font.assert_called_once()

    def test_register_private_font_for_windows_returns_false_when_api_adds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            font_path = Path(tmpdir) / 'SimBraille.ttf'
            font_path.write_bytes(b'font')
            add_font = Mock(return_value=0)
            result = register_private_font_for_windows(font_path, platform='win32', add_font_resource_ex=add_font)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
