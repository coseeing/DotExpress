import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from font_support import SIMBRAILLE_FACE_NAME, get_simbraille_font_path, register_private_font_for_windows


class FontSupportTest(unittest.TestCase):
    def test_get_simbraille_font_path_points_to_data_file(self) -> None:
        path = get_simbraille_font_path(Path('/tmp/app'))
        self.assertEqual(path, Path('/tmp/app/data/SimBraille.ttf'))

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
        called_path, flags, reserved = add_font.call_args.args
        self.assertEqual(Path(called_path), font_path)
        self.assertEqual(flags, 0x10)
        self.assertIsNone(reserved)

    def test_register_private_font_for_windows_returns_false_when_api_adds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            font_path = Path(tmpdir) / 'SimBraille.ttf'
            font_path.write_bytes(b'font')
            add_font = Mock(return_value=0)
            result = register_private_font_for_windows(font_path, platform='win32', add_font_resource_ex=add_font)
        self.assertFalse(result)

    def test_simbraille_face_name_constant(self) -> None:
        self.assertEqual(SIMBRAILLE_FACE_NAME, 'SimBraille')


if __name__ == '__main__':
    unittest.main()
