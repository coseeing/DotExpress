import sys
import types
import unittest


if "wx" not in sys.modules:
    wx_stub = types.ModuleType("wx")
    wx_stub.Dialog = type("Dialog", (), {})
    wx_stub.Window = type("Window", (), {})
    wx_stub.CommandEvent = type("CommandEvent", (), {})
    sys.modules["wx"] = wx_stub

from dialog import DictionaryNameDialog, DocumentNameDialog


class _TextCtrl:
    def __init__(self) -> None:
        self.value = None
        self.focused = False
        self.selected_all = False

    def SetValue(self, value: str) -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value or ""

    def SetFocus(self) -> None:
        self.focused = True

    def SelectAll(self) -> None:
        self.selected_all = True


class DialogValidationTextTest(unittest.TestCase):
    def test_dictionary_name_validation_mentions_32_characters(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertEqual(
            DictionaryNameDialog._validate_name(dialog, "a" * 33),
            "字典名稱長度需為 1 到 32 個字元。",
        )

    def test_document_name_validation_mentions_32_characters(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        self.assertEqual(
            DocumentNameDialog._validate_name(dialog, "a" * 33),
            "文件名稱長度需為 1 到 32 個字元。",
        )

    def test_dictionary_name_dialog_applies_initial_name(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)
        dialog.name_ctrl = _TextCtrl()

        DictionaryNameDialog._apply_initial_name(dialog, "1.1")

        self.assertEqual(dialog.name_ctrl.value, "1.1")
        self.assertTrue(dialog.name_ctrl.focused)
        self.assertTrue(dialog.name_ctrl.selected_all)

    def test_dictionary_name_validation_accepts_windows_valid_names(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertIsNone(DictionaryNameDialog._validate_name(dialog, "1.1"))

    def test_dictionary_name_validation_rejects_windows_invalid_names(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        for name in ("name.", "name ", "name\t", "CON", "a?b"):
            with self.subTest(name=name):
                self.assertEqual(
                    DictionaryNameDialog._validate_name(dialog, name),
                    "字典名稱不是有效的 Windows 檔名。",
                )

    def test_dictionary_name_validation_keeps_reserved_default_message(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertEqual(
            DictionaryNameDialog._validate_name(dialog, "default"),
            "字典名稱「default」為保留名稱。",
        )

    def test_document_name_validation_accepts_windows_valid_names(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        self.assertIsNone(DocumentNameDialog._validate_name(dialog, "1.1"))

    def test_document_name_validation_rejects_windows_invalid_names(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        for name in ("name.", "name ", "name\t", "CON", "a?b"):
            with self.subTest(name=name):
                self.assertEqual(
                    DocumentNameDialog._validate_name(dialog, name),
                    "文件名稱不是有效的 Windows 檔名。",
                )


if __name__ == "__main__":
    unittest.main()
