"""F-13 item 5 precondition: a system Yes/No box raised from inside a modal dialog.

Usage: python probe_box.py <variant> <result.json>

Run with the client venv's python (wx 4.2.5). Never imports gui.py. A frame owns a
wx.Dialog ("F13 probe editor") shown with ShowModal, as the dictionary editor is
shown from Dictionary Management. 0.8 s after the dialog opens, a button event is
posted to its OK button; the OK handler raises the box with the dialog as parent and
waits in ShowModal, as DictionaryEntriesDialog._on_ok and _on_cancel do. The box is
built like ui.message_box.message_box (wx.MessageDialog with the given style) plus
SetYesNoLabels with the zh_TW labels of the F-11 boxes. When ShowModal returns, the
answer is written to <result.json> and the program ends.

Variants (the affirmative answer is the one that removes rows / discards changes):
  remove   YES_NO | NO_DEFAULT | ICON_WARNING, Yes = "remove and save", No = "back to editing"
  discard  YES_NO | NO_DEFAULT | ICON_WARNING, Yes = "discard changes", No = "back to editing"
  swapped  YES_NO | YES_DEFAULT | ICON_WARNING, Yes = "back to editing", No = "remove and save"
  system   YES_NO | NO_DEFAULT | ICON_WARNING, system labels (as the existing four Yes/No boxes)
  remove_r as remove, but the access key of "remove and save" is R instead of S
  remove_frame  as remove, but raised from the frame (no modal dialog running)

Added after the first run (see README.md): F4 has the virtual-key code 0x73, the
character code of "s"; remove_r and remove_frame test whether Alt+F4 presses the
button whose access key is S.
"""
import json
import sys

import wx

NL = chr(10)
REMOVE_MESSAGE = NL.join(
	(
		"字典「probe」有些列無法在編輯器中顯示。儲存時會從檔案中移除這些列：",
		"",
		"第 3 列：「抹」的注音「ㄇㄚ」格式不正確",
		"第 4 列：沒有來源文字",
		"",
		"要移除這些列並儲存字典嗎？",
	)
)
DISCARD_MESSAGE = "要放棄對字典「probe」所做的變更嗎？"
REMOVE = "移除並儲存(&S)"
DISCARD = "放棄變更(&D)"
BACK = "返回編輯(&B)"
WARNING_YES_NO = wx.YES_NO | wx.ICON_WARNING

VARIANTS = {
	"remove": (REMOVE_MESSAGE, "移除無法顯示的列", WARNING_YES_NO | wx.NO_DEFAULT, (REMOVE, BACK), wx.ID_YES),
	"discard": (DISCARD_MESSAGE, "尚未儲存的變更", WARNING_YES_NO | wx.NO_DEFAULT, (DISCARD, BACK), wx.ID_YES),
	"swapped": (REMOVE_MESSAGE, "移除無法顯示的列", WARNING_YES_NO | wx.YES_DEFAULT, (BACK, REMOVE), wx.ID_NO),
	"system": (REMOVE_MESSAGE, "移除無法顯示的列", WARNING_YES_NO | wx.NO_DEFAULT, None, wx.ID_YES),
	"remove_r": (REMOVE_MESSAGE, "移除無法顯示的列", WARNING_YES_NO | wx.NO_DEFAULT, ("移除並儲存(&R)", BACK), wx.ID_YES),
}
VARIANTS["remove_frame"] = VARIANTS["remove"]
NAMES = {wx.ID_YES: "ID_YES", wx.ID_NO: "ID_NO", wx.ID_OK: "ID_OK", wx.ID_CANCEL: "ID_CANCEL"}


class Editor(wx.Dialog):
	def __init__(self, parent, variant, result_path):
		super().__init__(parent, title="F13 probe editor")
		self.variant = variant
		self.result_path = result_path
		self.ok = wx.Button(self, wx.ID_OK, "OK")
		cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(self.ok, 0, wx.ALL, 8)
		sizer.Add(cancel, 0, wx.ALL, 8)
		self.SetSizerAndFit(sizer)
		self.ok.Bind(wx.EVT_BUTTON, self.on_ok)
		wx.CallLater(800, self.press_ok)

	def press_ok(self):
		event = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK)
		event.SetEventObject(self.ok)
		wx.PostEvent(self.ok, event)

	def on_ok(self, _event):
		ask(self, self.variant, self.result_path)
		self.EndModal(wx.ID_OK)


def ask(parent, variant, result_path):
	"""Raise the box with ``parent`` as its parent and write the answer to ``result_path``."""
	message, caption, style, labels, affirmative = VARIANTS[variant]
	with wx.MessageDialog(parent, message, caption, style) as box:
		if labels is not None:
			box.SetYesNoLabels(*labels)
		answer = box.ShowModal()
	result = {
		"variant": variant,
		"answer": NAMES.get(answer, str(answer)),
		"affirmative": answer == affirmative,
		"wx": wx.version(),
	}
	with open(result_path, "w", encoding="utf-8") as stream:
		json.dump(result, stream, ensure_ascii=False)


def main():
	variant, result_path = sys.argv[1], sys.argv[2]
	app = wx.App()
	frame = wx.Frame(None, title="F13 probe frame", size=(400, 300))
	frame.Show()

	def run():
		if variant.endswith("_frame"):
			ask(frame, variant, result_path)
		else:
			with Editor(frame, variant, result_path) as editor:
				editor.ShowModal()
		frame.Close()

	wx.CallLater(800, run) if variant.endswith("_frame") else wx.CallAfter(run)
	app.MainLoop()


if __name__ == "__main__":
	main()
