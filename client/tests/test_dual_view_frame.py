import types
import unittest
from unittest.mock import Mock, patch

import sys

wx = sys.modules.get("wx", types.ModuleType("wx"))


class _Widget:
	def __init__(self, *args, **kwargs):
		pass

	def __getattr__(self, _name):
		def _method(*args, **kwargs):
			return None

		return _method


class Window(_Widget):
	pass


class Frame(Window):
	pass


class BoxSizer(_Widget):
	pass


wx.Window = Window
wx.Frame = Frame
wx.BoxSizer = BoxSizer
wx.__path__ = []
wx.VERTICAL = 1
wx.EXPAND = 2
wx.EVT_CLOSE = object()
wx.CallAfter = lambda callback: callback()
wx.__getattr__ = lambda name: type(name, (), {})

wx_html2 = types.ModuleType("wx.html2")
wx_html2.WebView = type(
	"WebView",
	(),
	{"New": staticmethod(lambda parent: Mock())},
)
wx.html2 = wx_html2
sys.modules["wx"] = wx
sys.modules["wx.html2"] = wx_html2

from ui.dual_view import DualViewFrame


class DualViewFrameTest(unittest.TestCase):
	def test_refresh_loads_complete_html(self):
		frame = DualViewFrame.__new__(DualViewFrame)
		frame.web_view = Mock()

		frame.refresh_html("<html>alignment</html>")

		frame.web_view.SetPage.assert_called_once_with("<html>alignment</html>", "")

	def test_close_notifies_owner_and_destroys(self):
		owner = Mock()
		event = Mock()
		frame = DualViewFrame.__new__(DualViewFrame)
		frame._on_closed = owner
		frame.Destroy = Mock()

		frame._handle_close(event)

		owner.assert_called_once_with(frame)
		frame.Destroy.assert_called_once_with()
		event.Skip.assert_not_called()

	def test_raise_without_activating_uses_windows_no_activate_path(self):
		frame = DualViewFrame.__new__(DualViewFrame)
		frame.Raise = Mock()

		with (
			patch("ui.dual_view.sys.platform", "win32"),
			patch("ui.dual_view._raise_windows_without_activating", return_value=True) as raise_windows,
		):
			frame.raise_without_activating()

		raise_windows.assert_called_once_with(frame)
		frame.Raise.assert_not_called()

	def test_raise_without_activating_restores_focus_on_other_platforms(self):
		frame = DualViewFrame.__new__(DualViewFrame)
		frame.Raise = Mock()
		focused_window = Mock()

		with (
			patch("ui.dual_view.sys.platform", "linux"),
			patch.object(wx.Window, "FindFocus", return_value=focused_window, create=True),
		):
			frame.raise_without_activating()

		frame.Raise.assert_called_once_with()
		focused_window.SetFocus.assert_called_once_with()


if __name__ == "__main__":
	unittest.main()
