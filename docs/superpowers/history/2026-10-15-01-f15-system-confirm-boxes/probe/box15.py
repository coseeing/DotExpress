"""F-15 probe: the F-11 boxes as system Yes/No boxes with labels WITHOUT access keys."""
import os
import sys
# The committed F-13 probe this one wraps, relative to this folder.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "2026-10-14-02-f13-behavior-nvda", "probe"))
import wx
import probe_box as p

p.VARIANTS["remove_nokey"] = (p.REMOVE_MESSAGE, "移除無法顯示的列", p.WARNING_YES_NO | wx.NO_DEFAULT, ("移除並儲存", "返回編輯"), wx.ID_YES)
p.VARIANTS["discard_nokey"] = (p.DISCARD_MESSAGE, "尚未儲存的變更", p.WARNING_YES_NO | wx.NO_DEFAULT, ("放棄變更", "返回編輯"), wx.ID_YES)
if __name__ == "__main__":
	p.main()
