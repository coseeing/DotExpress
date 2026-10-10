"""Items 48 and 49 (F-6): Import refuses a file that cannot be read; a CSV over the field limit.

Usage: python item48.py <exe> <work folder>
The sources are written to <work folder>\\data. badquote.csv is also put into the
dictionary folder before the second start.
48: import data\\big5.csv as b1 and data\\big5_late.csv as b2.
49: select badquote (the reason row); import data\\badquote.csv as bq2.
Before F-6 (N-f5b): nothing opens (badquote.csv is in the dictionary folder).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = G.start(EXE, d, put=("badquote.csv",))
data = G.sources(d)
before = G.shas(data)
mgr = G.open_mgr(app, w)
if mgr is None:
	print("48: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	G.finish(app, w, d)
	sys.exit(0)
print("48 rows:", G.rows(mgr))
print("48 import big5.csv as b1:", G.import_as(app, w, mgr, os.path.join(data, "big5.csv"), "b1"))
print("48 import big5_late.csv as b2:", G.import_as(app, w, mgr, os.path.join(data, "big5_late.csv"), "b2"))
print("48 rows after:", G.rows(mgr), "windows:", G.windows(app, w))
print("48 dictionary files:", sorted(os.listdir(G.dictionary(d))))

X.mgr_select(mgr, "badquote")
print("49 badquote reason:", G.reason(mgr))
print("49 import badquote.csv as bq2:", G.import_as(app, w, mgr, os.path.join(data, "badquote.csv"), "bq2"))
print("49 rows after:", G.rows(mgr))
print("49 dictionary files:", sorted(os.listdir(G.dictionary(d))))
print("48-49 sources unchanged:", G.shas(data) == before)
print("48-49 gui.log:", G.gui_log(d))
G.finish(app, w, d)
