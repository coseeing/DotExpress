"""Items 50 and 51 (F-6): Rename, Export, Delete and conversion with an unreadable dictionary.

Usage: python item50.py <exe> <work folder>
50: big5.csv in the dictionary folder: rename big5 to big5x; export big5x to
    <work folder>\\out.csv; delete big5x (confirm with 是).
51: big5.csv written again; Settings: dictionary big5; input 臺北; convert.
Before F-6 (N-f5b): nothing opens at 50.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import D, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
out = os.path.join(d, "out.csv")
app, w = G.start(EXE, d, put=("big5.csv",))
mgr = G.open_mgr(app, w)
if mgr is None:
	print("50: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	G.finish(app, w, d)
	sys.exit(0)
X.mgr_select(mgr, "big5")
G.click(mgr, "重新命名", wait=0.5)
print("50 rename big5 -> big5x:", G.name_dialog(app, w, "重新命名字典", "big5x"))
print("50 rows:", G.rows(mgr), "reason:", G.reason(mgr))
print("50 export big5x:", G.export_to(app, w, mgr, out))
print("50 out.csv equals the source:", G.sha(out) == G.digest(G.FILES["big5.csv"]))
G.click(mgr, "刪除")
print("50 delete big5x:", G.boxes(app, w, press=("是(Y)", "是(&Y)", "Yes")))
print("50 rows:", G.rows(mgr), "boxes:", G.boxes(app, w))
print("50 dictionary files:", sorted(os.listdir(G.dictionary(d))))
X.close_mgr(app, w, mgr)

G.write(os.path.join(G.dictionary(d), "big5.csv"), G.FILES["big5.csv"])
X.set_dictionary(app, w, "big5")
D.set_input(w, "臺北")
print("51 convert:", X.convert(app, w))
X.set_dictionary(app, w, "default")
print("50-51 gui.log:", G.gui_log(d))
G.finish(app, w, d)
