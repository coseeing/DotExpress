from collections.abc import Callable

import wx
import wx.html2


class DualViewFrame(wx.Frame):
	def __init__(
		self,
		parent: wx.Window,
		*,
		title: str,
		on_closed: Callable[["DualViewFrame"], None],
	):
		super().__init__(parent, title=title, size=(900, 650))
		self._on_closed = on_closed
		self.web_view = wx.html2.WebView.New(self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.web_view, 1, wx.EXPAND)
		self.SetSizer(sizer)
		self.Bind(wx.EVT_CLOSE, self._handle_close)

	def refresh_html(self, content: str) -> None:
		self.web_view.SetPage(content, "")

	def _handle_close(self, event: wx.CloseEvent) -> None:
		self._on_closed(self)
		self.Destroy()
