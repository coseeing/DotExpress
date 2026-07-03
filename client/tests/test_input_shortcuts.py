import unittest

from ui.shortcuts import (
    is_brl_export_shortcut,
    is_convert_shortcut,
    is_document_cycle_shortcut,
    is_document_delete_shortcut,
    is_document_rename_shortcut,
    is_document_import_txt_shortcut,
    is_section_navigation_shortcut,
    get_font_size_step_from_wheel,
)


class InputShortcutsTest(unittest.TestCase):
    def test_keyboard_shortcuts_match_expected_keys(self) -> None:
        cases = [
            ("convert main enter", is_convert_shortcut, {"key_code": 13, "control_down": True}, True),
            ("convert numpad enter", is_convert_shortcut, {"key_code": 370, "control_down": True}, True),
            ("convert plain enter", is_convert_shortcut, {"key_code": 13, "control_down": False}, False),
            ("brl export ctrl s", is_brl_export_shortcut, {"key_code": 83, "control_down": True}, True),
            ("brl export plain s", is_brl_export_shortcut, {"key_code": 83, "control_down": False}, False),
            ("rename f2", is_document_rename_shortcut, {"key_code": 341}, True),
            ("rename other key", is_document_rename_shortcut, {"key_code": 13}, False),
            ("delete", is_document_delete_shortcut, {"key_code": 127}, True),
            ("delete other key", is_document_delete_shortcut, {"key_code": 13}, False),
            ("ctrl o txt import", is_document_import_txt_shortcut, {"key_code": 79, "control_down": True}, True),
            ("plain o txt import", is_document_import_txt_shortcut, {"key_code": 79, "control_down": False}, False),
            ("ctrl other key txt import", is_document_import_txt_shortcut, {"key_code": 80, "control_down": True}, False),
        ]

        for label, shortcut, kwargs, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(shortcut(**kwargs), expected)

    def test_document_cycle_shortcut_direction(self) -> None:
        cases = [
            ("ctrl tab forward", {"key_code": 9, "control_down": True, "shift_down": False}, 1),
            ("ctrl shift tab backward", {"key_code": 9, "control_down": True, "shift_down": True}, -1),
            ("ctrl pagedown forward", {"key_code": 367, "control_down": True, "shift_down": False}, 1),
            ("ctrl pageup backward", {"key_code": 366, "control_down": True, "shift_down": False}, -1),
            ("ctrl shift pagedown still forward", {"key_code": 367, "control_down": True, "shift_down": True}, 1),
            ("plain tab ignored", {"key_code": 9, "control_down": False, "shift_down": False}, 0),
            ("plain pagedown ignored", {"key_code": 367, "control_down": False, "shift_down": False}, 0),
        ]

        for label, kwargs, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(is_document_cycle_shortcut(**kwargs), expected)

    def test_section_navigation_shortcut_direction(self) -> None:
        cases = [
            ("forward", {"key_code": 345, "shift_down": False}, 1),
            ("backward", {"key_code": 345, "shift_down": True}, -1),
            ("other key", {"key_code": 13, "shift_down": False}, 0),
        ]

        for label, kwargs, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(is_section_navigation_shortcut(**kwargs), expected)

    def test_font_size_wheel_shortcut_step(self) -> None:
        cases = [
            ("ctrl wheel up", {"wheel_rotation": 120, "control_down": True}, 1),
            ("ctrl wheel down", {"wheel_rotation": -120, "control_down": True}, -1),
            ("wheel without ctrl", {"wheel_rotation": 120, "control_down": False}, 0),
            ("zero rotation", {"wheel_rotation": 0, "control_down": True}, 0),
        ]

        for label, kwargs, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(get_font_size_step_from_wheel(**kwargs), expected)


if __name__ == "__main__":
    unittest.main()
