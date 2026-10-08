import unittest
from unittest.mock import Mock

from tests import wx_stub


dialog_module, _DIALOG_SCOPE = wx_stub.load_display_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate


class FinalizeDialogLayoutTest(unittest.TestCase):
	def test_fits_and_centers_on_parent(self):
		owner = object()
		dialog = Mock()
		dialog.GetParent.return_value = owner
		sizer = object()

		dialog_module.finalize_dialog_layout(dialog, sizer)

		dialog.SetSizerAndFit.assert_called_once_with(sizer)
		dialog.CentreOnParent.assert_called_once_with()
		dialog.Centre.assert_not_called()

	def test_fits_and_centers_on_screen_without_parent(self):
		dialog = Mock()
		dialog.GetParent.return_value = None
		sizer = object()

		dialog_module.finalize_dialog_layout(dialog, sizer)

		dialog.SetSizerAndFit.assert_called_once_with(sizer)
		dialog.Centre.assert_called_once_with()
		dialog.CentreOnParent.assert_not_called()

	def test_localizes_standard_dialog_buttons(self):
		dialog = Mock()
		buttons = {
			dialog_module.wx.ID_OK: Mock(),
			dialog_module.wx.ID_CANCEL: Mock(),
		}
		dialog.FindWindowById.side_effect = buttons.get

		translations = {"OK": "確定", "Cancel": "取消", "Apply": "套用"}
		previous_gettext = dialog_module._
		dialog_module._ = translations.get
		try:
			dialog_module.localize_standard_buttons(dialog, dialog_module.wx.OK | dialog_module.wx.CANCEL)
		finally:
			dialog_module._ = previous_gettext

		buttons[dialog_module.wx.ID_OK].SetLabel.assert_called_once_with("確定")
		buttons[dialog_module.wx.ID_CANCEL].SetLabel.assert_called_once_with("取消")

	def test_localizes_close_button(self):
		dialog = Mock()
		close_button = Mock()
		dialog.FindWindowById.return_value = close_button

		previous_gettext = dialog_module._
		dialog_module._ = {"Close": "關閉"}.get
		try:
			dialog_module.localize_standard_buttons(dialog, dialog_module.wx.CLOSE)
		finally:
			dialog_module._ = previous_gettext

		close_button.SetLabel.assert_called_once_with("關閉")

	def test_localizes_buttons_from_standard_button_sizer(self):
		dialog = Mock()
		dialog.FindWindowById.return_value = None
		button_sizer = Mock()
		button_sizer.GetAffirmativeButton.return_value = Mock()
		button_sizer.GetCancelButton.return_value = Mock()

		previous_gettext = dialog_module._
		dialog_module._ = {"OK": "確定", "Cancel": "取消"}.get
		try:
			dialog_module.localize_standard_buttons(
				dialog,
				dialog_module.wx.OK | dialog_module.wx.CANCEL,
				button_sizer,
			)
		finally:
			dialog_module._ = previous_gettext

		button_sizer.GetAffirmativeButton.return_value.SetLabel.assert_called_once_with("確定")
		button_sizer.GetCancelButton.return_value.SetLabel.assert_called_once_with("取消")


if __name__ == "__main__":
	unittest.main()
