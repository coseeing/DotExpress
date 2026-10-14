r"""Manual item 145 (NVDA): prepare a folder for the user.

Usage: python manual145.py <exe> <folder>   (for example D:\dxtest\N-f14\DotExpress.exe D:\dxtest\manual145-f14)
The folder gets a copy of the exe and workspace\ with a pending document 中文 (Chinese text
with a few English words), config.json = "{" and a folder config.json.bak (the case of item
142), and an empty out\ folder. The app is not started: the user starts <folder>\DotExpress.exe
with NVDA on, converts 中文 (Ctrl+Enter), opens Translation > Dual View, exports File > Export >
Dual View HTML into out\ and opens that file in the browser, then changes the width in
Settings and presses Apply to hear the box of item 142. Nothing here touches the clipboard.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f14gui as H  # noqa: E402
from f14gui import A, F9, H12  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
F9.pending(d, "中文", "這是中文點字的雙視檢視測試，含有 English words 與數字 123。\n第二行中文。")
H12.config(d, b"{")
os.makedirs(os.path.join(d, "config.json.bak"))
os.makedirs(os.path.join(d, "out"))
print(f"manual 145 folder ready: {d} files {A.files(d)}")
