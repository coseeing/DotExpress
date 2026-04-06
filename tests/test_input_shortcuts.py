import unittest

from input_shortcuts import (
    is_brl_export_shortcut,
    is_convert_shortcut,
    is_document_delete_shortcut,
    is_document_rename_shortcut,
    get_font_size_step_from_wheel,
)


class InputShortcutsTest(unittest.TestCase):
    def test_ctrl_enter_uses_main_enter(self) -> None:
        self.assertTrue(is_convert_shortcut(key_code=13, control_down=True))

    def test_ctrl_enter_uses_numpad_enter(self) -> None:
        self.assertTrue(is_convert_shortcut(key_code=370, control_down=True))

    def test_plain_enter_is_not_convert_shortcut(self) -> None:
        self.assertFalse(is_convert_shortcut(key_code=13, control_down=False))

    def test_other_keys_do_not_trigger_convert(self) -> None:
        self.assertFalse(is_convert_shortcut(key_code=65, control_down=True))

    def test_ctrl_s_triggers_brl_export_shortcut(self) -> None:
        self.assertTrue(is_brl_export_shortcut(key_code=83, control_down=True))

    def test_plain_s_does_not_trigger_brl_export_shortcut(self) -> None:
        self.assertFalse(is_brl_export_shortcut(key_code=83, control_down=False))

    def test_f2_triggers_document_rename_shortcut(self) -> None:
        self.assertTrue(is_document_rename_shortcut(key_code=341))

    def test_other_keys_do_not_trigger_document_rename_shortcut(self) -> None:
        self.assertFalse(is_document_rename_shortcut(key_code=13))

    def test_delete_triggers_document_delete_shortcut(self) -> None:
        self.assertTrue(is_document_delete_shortcut(key_code=127))

    def test_other_keys_do_not_trigger_document_delete_shortcut(self) -> None:
        self.assertFalse(is_document_delete_shortcut(key_code=13))

    def test_ctrl_wheel_up_increases_font_size(self) -> None:
        self.assertEqual(get_font_size_step_from_wheel(wheel_rotation=120, control_down=True), 1)

    def test_ctrl_wheel_down_decreases_font_size(self) -> None:
        self.assertEqual(get_font_size_step_from_wheel(wheel_rotation=-120, control_down=True), -1)

    def test_wheel_without_ctrl_does_not_change_font_size(self) -> None:
        self.assertEqual(get_font_size_step_from_wheel(wheel_rotation=120, control_down=False), 0)

    def test_zero_wheel_rotation_does_not_change_font_size(self) -> None:
        self.assertEqual(get_font_size_step_from_wheel(wheel_rotation=0, control_down=True), 0)


if __name__ == "__main__":
    unittest.main()
