import unittest
from unittest.mock import MagicMock, Mock, patch

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
		dialog.FindWindow.side_effect = buttons.get

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
		dialog.FindWindow.return_value = close_button

		previous_gettext = dialog_module._
		dialog_module._ = {"Close": "關閉"}.get
		try:
			dialog_module.localize_standard_buttons(dialog, dialog_module.wx.CLOSE)
		finally:
			dialog_module._ = previous_gettext

		close_button.SetLabel.assert_called_once_with("關閉")

	def test_localizes_buttons_from_standard_button_sizer(self):
		dialog = Mock()
		dialog.FindWindow.return_value = None
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

	def test_localize_ignores_buttons_of_other_windows(self):
		# F-W9: called on a dialog, wx.Window.FindWindowById searches every top-level window
		# and can return another dialog's button (a destroyed name dialog, an open Settings).
		dialog = Mock()
		own = {dialog_module.wx.ID_OK: Mock(), dialog_module.wx.ID_CANCEL: Mock()}
		other = {dialog_module.wx.ID_OK: Mock(), dialog_module.wx.ID_CANCEL: Mock()}
		dialog.FindWindow.side_effect = own.get
		dialog.FindWindowById.side_effect = other.get

		previous_gettext = dialog_module._
		dialog_module._ = {"OK": "確定", "Cancel": "取消"}.get
		try:
			dialog_module.localize_standard_buttons(dialog, dialog_module.wx.OK | dialog_module.wx.CANCEL)
		finally:
			dialog_module._ = previous_gettext

		own[dialog_module.wx.ID_OK].SetLabel.assert_called_once_with("確定")
		own[dialog_module.wx.ID_CANCEL].SetLabel.assert_called_once_with("取消")
		for button in other.values():
			button.SetLabel.assert_not_called()
		dialog.FindWindowById.assert_not_called()

	def test_file_issues_dialog_localizes_its_ok_button(self):
		dialog = object.__new__(dialog_module.FileIssuesDialog)
		button_sizer = Mock()
		dialog.CreateButtonSizer = Mock(return_value=button_sizer)
		dialog.SetMinSize = Mock()
		widgets = MagicMock(OK=dialog_module.wx.OK)

		with (
			patch.object(dialog_module.wx.Dialog, "__init__", lambda *_args, **_kwargs: None),
			patch.object(dialog_module, "wx", widgets),
			patch.object(dialog_module, "finalize_dialog_layout"),
			patch.object(dialog_module, "localize_standard_buttons") as localize,
		):
			dialog_module.FileIssuesDialog.__init__(dialog, None, "Import Issues", "Some files were skipped.", ["a.txt"])

		dialog.CreateButtonSizer.assert_called_once_with(dialog_module.wx.OK)
		localize.assert_called_once_with(dialog, dialog_module.wx.OK, button_sizer)


if __name__ == "__main__":
	unittest.main()
