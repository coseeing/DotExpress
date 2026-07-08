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
	def __init__(self, *args, **kwargs):
		self.init_args = args
		self.init_kwargs = kwargs


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
import ui.dual_view as dual_view


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

	def test_initial_geometry_matches_parent(self):
		parent = Mock()
		parent.GetPosition.return_value = (120, 80)
		parent.GetSize.return_value = (1024, 768)

		frame = DualViewFrame(
			parent,
			title="Dual View",
			on_closed=Mock(),
		)

		self.assertEqual(frame.init_kwargs["pos"], (120, 80))
		self.assertEqual(frame.init_kwargs["size"], (1024, 768))
		parent.GetPosition.assert_called_once_with()
		parent.GetSize.assert_called_once_with()

	def test_initialization_logs_native_backend(self):
		parent = Mock()
		parent.GetPosition.return_value = (0, 0)
		parent.GetSize.return_value = (800, 600)
		web_view = Mock()
		web_view.GetNativeBackend.return_value = "Edge"

		with patch.object(dual_view.wx.html2.WebView, "New", return_value=web_view), patch.object(
			dual_view.logger, "debug"
		) as log_debug:
			DualViewFrame(
				parent,
				title="Dual View",
				on_closed=Mock(),
			)

		log_debug.assert_called_once_with("Dual view webview backend: %s", "Edge")


if __name__ == "__main__":
	unittest.main()
