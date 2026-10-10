"""Item 47 (F-6): a dictionary held open by another program without sharing.

Usage: python item47.py <exe> <work folder>
lockx.py holds <dictionary>\\alpha.csv (a readable UTF-8 dictionary) with share mode 0;
open Dictionary Management; select alpha; release the lock; 編輯 (re-read): the editor
opens with the row; 取消.
Before F-6 (N-f5b): nothing opens.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
alpha = os.path.join(G.dictionary(d), "alpha.csv")
app, w = G.start(EXE, d, put=("alpha.csv",))
holder = G.lock_none(alpha)
try:
	mgr = G.open_mgr(app, w)
	if mgr is None:
		print("47: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	else:
		print("47 rows:", G.rows(mgr))
		X.mgr_select(mgr, "alpha")
		print("47 alpha reason:", G.reason(mgr))
finally:
	G.unlock(holder)
print("47 unlocked")
if mgr is not None:
	G.click(mgr, "編輯")
	print("47 edit after unlock: boxes:", G.boxes(app, w), "windows:", G.windows(app, w))
	editor = X.windows(app, w).get(G.EDITOR)
	if editor is not None:
		print("47 editor rows:", X.editor_rows(editor))
		X.btn(editor, "取消", "Cancel").click()
		time.sleep(1)
print("47 alpha.csv unchanged:", G.sha(alpha) == G.digest(G.FILES["alpha.csv"]))
print("47 gui.log:", G.gui_log(d))
G.finish(app, w, d)
