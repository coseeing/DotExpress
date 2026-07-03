RETURN_KEY_CODE = 13
NUMPAD_RETURN_KEY_CODE = 370
S_KEY_CODE = 83
O_KEY_CODE = 79
TAB_KEY_CODE = 9
PAGEUP_KEY_CODE = 366
PAGEDOWN_KEY_CODE = 367
F2_KEY_CODE = 341
F6_KEY_CODE = 345
DELETE_KEY_CODE = 127


def is_convert_shortcut(key_code: int, control_down: bool) -> bool:
    return control_down and key_code in {RETURN_KEY_CODE, NUMPAD_RETURN_KEY_CODE}


def is_brl_export_shortcut(key_code: int, control_down: bool) -> bool:
    return control_down and key_code == S_KEY_CODE


def is_document_import_txt_shortcut(key_code: int, control_down: bool) -> bool:
    return control_down and key_code == O_KEY_CODE


def is_document_cycle_shortcut(key_code: int, control_down: bool, shift_down: bool) -> int:
    if not control_down:
        return 0
    if key_code == TAB_KEY_CODE:
        return -1 if shift_down else 1
    if key_code == PAGEDOWN_KEY_CODE:
        return 1
    if key_code == PAGEUP_KEY_CODE:
        return -1
    return 0


def is_document_rename_shortcut(key_code: int) -> bool:
    return key_code == F2_KEY_CODE


def is_document_delete_shortcut(key_code: int) -> bool:
    return key_code == DELETE_KEY_CODE


def is_section_navigation_shortcut(key_code: int, shift_down: bool) -> int:
    if key_code != F6_KEY_CODE:
        return 0
    return -1 if shift_down else 1


def get_font_size_step_from_wheel(wheel_rotation: int, control_down: bool) -> int:
    if not control_down or wheel_rotation == 0:
        return 0
    return 1 if wheel_rotation > 0 else -1
