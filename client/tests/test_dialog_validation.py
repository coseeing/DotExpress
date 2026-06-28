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


if __name__ == "__main__":
    unittest.main()
