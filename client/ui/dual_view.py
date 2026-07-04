from collections.abc import Callable
import ctypes
from ctypes import wintypes
import sys

import wx
import wx.html2


def _raise_windows_without_activating(window: wx.Window) -> bool:
	try:
		user32 = ctypes.WinDLL("user32", use_last_error=True)
	except (AttributeError, OSError):
		return False

	set_window_pos = user32.SetWindowPos
	set_window_pos.argtypes = (
		wintypes.HWND,
		wintypes.HWND,
		ctypes.c_int,
		ctypes.c_int,
		ctypes.c_int,
		ctypes.c_int,
		wintypes.UINT,
	)
	set_window_pos.restype = wintypes.BOOL
	flags = 0x0001 | 0x0002 | 0x0010  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
	return bool(set_window_pos(window.GetHandle(), 0, 0, 0, 0, 0, flags))


class DualViewFrame(wx.Frame):
	def __init__(
		self,
		parent: wx.Window,
		*,
		title: str,
		on_closed: Callable[["DualViewFrame"], None],
	):
		super().__init__(
			parent,
			title=title,
			pos=parent.GetPosition(),
			size=parent.GetSize(),
		)
		self._on_closed = on_closed
		self.web_view = wx.html2.WebView.New(self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.web_view, 1, wx.EXPAND)
		self.SetSizer(sizer)
		self.Bind(wx.EVT_CLOSE, self._handle_close)

	def refresh_html(self, content: str) -> None:
		self.web_view.SetPage(content, "")

	def raise_without_activating(self) -> None:
		if sys.platform == "win32" and _raise_windows_without_activating(self):
			return
		focused_window = wx.Window.FindFocus()
		self.Raise()
		if focused_window is not None:
			wx.CallAfter(focused_window.SetFocus)

	def _handle_close(self, event: wx.CloseEvent) -> None:
		self._on_closed(self)
		self.Destroy()
