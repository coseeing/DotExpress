"""Items 42-45 (F-6): Dictionary Management with a Big5 dictionary.

Usage: python item42.py <exe> <work folder>
42: start once, close, put big5.csv into dictionary\\, start, open Dictionary Management:
    the rows, no reason row, gui.log, big5.csv unchanged.
43: select big5 (the reason row appears), then default (it is gone).
45: Tab order: big5 selected, from the list Tab (the reason field) and Shift+Tab (the
    list); default selected, from the list Tab (新增).
44: big5 selected, 編輯: the error box, the dialog stays open, a second log line. Then
    big5.csv is rewritten as UTF-8 and 編輯 opens the editor with the row; 取消; reopened,
    the count is 1.
Before F-6 (N-f5b): nothing opens at 42; the script stops there.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
big5 = os.path.join(G.dictionary(d), "big5.csv")
app, w = G.start(EXE, d, put=("big5.csv",))
mgr = G.open_mgr(app, w)
if mgr is None:
	print("42: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	print("42: gui.log:", G.gui_log(d))
	G.finish(app, w, d)
	sys.exit(0)
print("42 rows:", G.rows(mgr))
print("42 reason:", G.reason(mgr))
print("42 gui.log:", G.gui_log(d))
print("42 big5.csv unchanged:", G.sha(big5) == G.digest(G.FILES["big5.csv"]), "files:", G.shas(G.dictionary(d)))

X.mgr_select(mgr, "big5")
print("43 big5 rows:", G.rows(mgr))
print("43 big5 reason:", G.reason(mgr))
X.mgr_select(mgr, "default")
print("43 default reason:", G.reason(mgr))

X.mgr_select(mgr, "big5")
G.focus_list(mgr)
print("45 big5, Tab:", G.focus_after(mgr, "{TAB}"))
print("45 big5, Shift+Tab:", G.focus_after(mgr, "+{TAB}"))
X.mgr_select(mgr, "default")
G.focus_list(mgr)
print("45 default, Tab:", G.focus_after(mgr, "{TAB}"))

X.mgr_select(mgr, "big5")
G.click(mgr, "編輯")
print("44 edit:", G.boxes(app, w))
print("44 windows:", G.windows(app, w), "rows:", G.rows(mgr))
print("44 gui.log:", G.gui_log(d))
G.write(big5, G.UTF8_FIXED)
G.click(mgr, "編輯")
editor = X.wait_window(app, w, G.EDITOR)
print("44 fixed, edit: windows:", G.windows(app, w), "editor rows:", X.editor_rows(editor))
X.btn(editor, "取消", "Cancel").click()
time.sleep(1)
print("44 cancel: windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
mgr = G.open_mgr(app, w)
print("44 reopened rows:", G.rows(mgr), "reason:", G.reason(mgr))
print("44 gui.log lines:", len(G.gui_log(d)))
G.finish(app, w, d)
