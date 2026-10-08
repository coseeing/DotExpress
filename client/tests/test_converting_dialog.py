import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch, sentinel

from tests import wx_stub

# The module that defines ConvertingDialog, loaded against stub wx.
_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view"),
)
with _SCOPE.loading():
    defining_module = importlib.import_module("gui")

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

FAKE_WX = SimpleNamespace(
    DEFAULT_DIALOG_STYLE=0b0111,
    CLOSE_BOX=0b0010,
    STAY_ON_TOP=0b1000,
    VERTICAL=0b0100,
    ALL=0b0001_0000,
    ALIGN_CENTER_HORIZONTAL=0b0010_0000,
    EVT_CLOSE=sentinel.EVT_CLOSE,
)


class ConvertingDialogTest(unittest.TestCase):
    def build(self, parent):
        """Run the real ``ConvertingDialog.__init__`` with recording wx calls; return the records."""
        dialog_class = defining_module.ConvertingDialog
        wx_namespace = SimpleNamespace(
            **vars(FAKE_WX),
            StaticText=Mock(return_value=sentinel.message),
            BoxSizer=Mock(return_value=Mock(name="sizer")),
        )
        dialog_init = Mock(return_value=None)
        dialog = object.__new__(dialog_class)
        dialog.Bind = Mock()
        with (
            patch.object(defining_module.wx.Dialog, "__init__", dialog_init),
            patch.object(defining_module, "wx", wx_namespace),
            patch.object(defining_module, "finalize_dialog_layout") as finalize,
        ):
            dialog_class.__init__(dialog, parent)
        return dialog, dialog_init, wx_namespace, finalize

    def test_builds_a_closeless_stay_on_top_info_dialog_with_the_converting_label(self) -> None:
        dialog, dialog_init, wx_namespace, finalize = self.build(sentinel.parent)

        dialog_init.assert_called_once_with(sentinel.parent, title="資訊", style=0b1101)
        wx_namespace.StaticText.assert_called_once_with(dialog, label="轉換中")
        wx_namespace.BoxSizer.assert_called_once_with(0b0100)
        sizer = wx_namespace.BoxSizer.return_value
        sizer.Add.assert_called_once_with(sentinel.message, 0, 0b0011_0000, 20)
        finalize.assert_called_once_with(dialog, sizer)
        dialog.Bind.assert_called_once_with(sentinel.EVT_CLOSE, dialog._on_close)

    def test_close_is_vetoed_when_it_can_be(self) -> None:
        dialog = object.__new__(defining_module.ConvertingDialog)
        event = Mock()
        event.CanVeto.return_value = True

        dialog._on_close(event)

        event.Veto.assert_called_once_with()

    def test_close_is_not_vetoed_when_it_cannot_be(self) -> None:
        dialog = object.__new__(defining_module.ConvertingDialog)
        event = Mock()
        event.CanVeto.return_value = False

        dialog._on_close(event)

        event.Veto.assert_not_called()
        self.assertEqual(event.mock_calls, [call.CanVeto()])


if __name__ == "__main__":
    unittest.main()
