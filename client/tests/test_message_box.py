"""Tests of ``ui.message_box`` (F-7, F-W9) against a minimal fake ``wx``.

The fake has wx's own values for the styles, the results and the ids; its
``MessageDialog`` is replaced in each test by a recorder that answers from a queue.
The labels are the real zh_TW catalog, through ``i18n``.
"""

import importlib
import types
import unittest
from unittest.mock import patch

from i18n import _
from tests import wx_stub


def _fake_wx() -> types.ModuleType:
    wx = types.ModuleType("wx")
    wx.Window = type("Window", (), {})
    wx.MessageDialog = type("MessageDialog", (), {})
    wx.YES = 0x2
    wx.OK = 0x4
    wx.NO = 0x8
    wx.YES_NO = wx.YES | wx.NO
    wx.CANCEL = 0x10
    wx.NO_DEFAULT = 0x80
    wx.ICON_WARNING = 0x100
    wx.ICON_ERROR = 0x200
    wx.ICON_INFORMATION = 0x800
    wx.ID_OK = 5100
    wx.ID_CANCEL = 5101
    wx.ID_YES = 5103
    wx.ID_NO = 5104
    return wx


_SCOPE = wx_stub.StubScope({"wx": _fake_wx()}, isolate=("ui.message_box",))
with _SCOPE.loading():
    message_box_module = importlib.import_module("ui.message_box")

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

message_box = message_box_module.message_box
wx = message_box_module.wx
CONFIRM_STYLE = 0x2 | 0x8 | 0x80 | 0x100  # YES_NO | NO_DEFAULT | ICON_WARNING


class MessageBoxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list = []
        self.answers: list = []
        self.label_result = True
        patcher = patch.object(wx, "MessageDialog", self._dialog_class())
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dialog_class(self, name="MessageDialog"):
        test = self

        class RecordingMessageDialog:
            def __init__(self, *args):
                test.calls.append((name, *args))

            def __enter__(self):
                test.calls.append(("enter",))
                return self

            def __exit__(self, *_exc):
                test.calls.append(("exit",))
                return False

            def SetOKLabel(self, ok):
                test.calls.append(("SetOKLabel", ok))
                return test.label_result

            def SetOKCancelLabels(self, ok, cancel):
                test.calls.append(("SetOKCancelLabels", ok, cancel))
                return test.label_result

            def SetYesNoLabels(self, yes, no):
                test.calls.append(("SetYesNoLabels", yes, no))
                return test.label_result

            def ShowModal(self):
                test.calls.append(("ShowModal",))
                return test.answers.pop(0)

        return RecordingMessageDialog

    def test_ok_box_sets_the_translated_ok_label(self) -> None:
        parent = object()
        self.answers = [wx.ID_OK]

        result = message_box("message", "caption", wx.OK | wx.ICON_ERROR, parent=parent)

        self.assertEqual(
            self.calls,
            [
                ("MessageDialog", parent, "message", "caption", wx.OK | wx.ICON_ERROR),
                ("enter",),
                ("SetOKLabel", "確定"),
                ("ShowModal",),
                ("exit",),
            ],
        )
        self.assertEqual(_("OK"), "確定")
        self.assertEqual(result, wx.OK)

    def test_ok_cancel_box_sets_both_labels(self) -> None:
        self.answers = [wx.ID_CANCEL]

        result = message_box("message", "caption", wx.OK | wx.CANCEL | wx.ICON_WARNING)

        self.assertEqual(self.calls[2], ("SetOKCancelLabels", "確定", "取消"))
        self.assertEqual([call[0] for call in self.calls], ["MessageDialog", "enter", "SetOKCancelLabels", "ShowModal", "exit"])
        self.assertEqual(result, wx.CANCEL)

    def test_yes_no_box_keeps_the_system_labels(self) -> None:
        for style in (wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, wx.YES_NO | wx.ICON_WARNING):
            for answer, expected in ((wx.ID_YES, wx.YES), (wx.ID_NO, wx.NO)):
                with self.subTest(style=style, answer=answer):
                    self.calls.clear()
                    self.answers = [answer]

                    result = message_box("question", "caption", style, parent=None)

                    self.assertEqual(
                        self.calls,
                        [("MessageDialog", None, "question", "caption", style), ("enter",), ("ShowModal",), ("exit",)],
                    )
                    self.assertEqual(result, expected)

    def test_unexpected_result_maps_to_cancel(self) -> None:
        for answer in (wx.ID_CANCEL, 12345):
            with self.subTest(answer=answer):
                self.answers = [answer]

                self.assertEqual(message_box("message", "caption", wx.OK | wx.ICON_INFORMATION), wx.CANCEL)

    def test_parent_can_be_omitted_or_positional(self) -> None:
        frame = object()
        self.answers = [wx.ID_OK, wx.ID_OK]

        message_box("first", "caption", wx.OK | wx.ICON_ERROR)
        message_box("second", "caption", wx.OK | wx.ICON_ERROR, frame)

        self.assertEqual(
            [call for call in self.calls if call[0] == "MessageDialog"],
            [
                ("MessageDialog", None, "first", "caption", wx.OK | wx.ICON_ERROR),
                ("MessageDialog", frame, "second", "caption", wx.OK | wx.ICON_ERROR),
            ],
        )

    def test_confirm_box_is_a_system_yes_no_warning_whose_no_button_is_the_default(self) -> None:
        # F-15: the system Yes/No box with the caller's labels, No (the one that keeps the
        # user's work) the default, so Enter answers it. Esc, Alt+F4 and the close button
        # do nothing in it, and without access keys no Alt+key presses a button.
        parent = object()
        self.answers = [wx.ID_YES, wx.ID_NO]

        first = message_box_module.confirm_box("message", "caption", "Discard", "Back", parent=parent)
        second = message_box_module.confirm_box("message", "caption", "Discard", "Back")

        self.assertEqual((first, second), (True, False))
        self.assertEqual(
            self.calls[:5],
            [
                ("MessageDialog", parent, "message", "caption", CONFIRM_STYLE),
                ("enter",),
                ("SetYesNoLabels", "Discard", "Back"),
                ("ShowModal",),
                ("exit",),
            ],
        )
        self.assertEqual(self.calls[5], ("MessageDialog", None, "message", "caption", CONFIRM_STYLE))

    def test_confirm_box_any_other_answer_is_no(self) -> None:
        for answer in (wx.ID_OK, wx.ID_CANCEL, 12345):
            with self.subTest(answer=answer):
                self.answers = [answer]

                self.assertIs(message_box_module.confirm_box("message", "caption", "Discard", "Back"), False)

    def test_confirm_box_drops_access_keys_from_its_labels(self) -> None:
        # F-15: in the system Yes/No box Alt+<key> presses the button whose access key has
        # the key's code (Alt+F4 is "s"), so no label may bring one back.
        cases = [
            (("Remove and &Save", "&Back to Editing"), ("Remove and Save", "Back to Editing")),
            (("移除並儲存(&S)", "返回編輯(&B)"), ("移除並儲存", "返回編輯")),
            (("放棄變更(&D)", "&&Back"), ("放棄變更", "Back")),
        ]
        for labels, expected in cases:
            with self.subTest(labels=labels):
                self.calls.clear()
                self.answers = [wx.ID_NO]

                message_box_module.confirm_box("message", "caption", *labels)

                self.assertEqual(self.calls[2], ("SetYesNoLabels", *expected))

    def test_a_label_the_platform_refuses_still_shows_the_box(self) -> None:
        self.label_result = False
        self.answers = [wx.ID_OK]

        result = message_box("message", "caption", wx.OK | wx.ICON_INFORMATION)

        self.assertEqual([call[0] for call in self.calls], ["MessageDialog", "enter", "SetOKLabel", "ShowModal", "exit"])
        self.assertEqual(result, wx.OK)


if __name__ == "__main__":
    unittest.main()
