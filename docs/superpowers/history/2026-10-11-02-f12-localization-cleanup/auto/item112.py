r"""Item 112 (F-12 D4): a dictionary that cannot be read.

Usage: python safe_run.py item112.py <exe> <work folder>
Each case starts the app with config.json selecting one dictionary, types 甲乙 and runs
Translation > Convert:
  big5dict (a Big5 CSV), caps (header Text,Braille,Type), empty (0 bytes), locked (a good
  UTF-8 dictionary held open without sharing by lockshare.py from after the start).
Then, with big5dict selected, two pending documents (p1, p2): File > Export All > BRL into
<d>\out. Prints each box (title, main instruction, content) and the braille editor.
Before F-12 (N-f11c): the raw Python messages.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, D, G  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
HEAD = "text,braille,type\r\n"
ROW = "甲乙,⠁⠃,Braille\r\n"
d = H.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
H.dictionary(d, "big5dict", (HEAD + "甲乙,甲乙,Braille\r\n").encode("cp950"))
H.dictionary(d, "caps", ("Text,Braille,Type\r\n" + ROW).encode("utf-8"))
H.dictionary(d, "empty", b"")
H.dictionary(d, "locked", (HEAD + ROW).encode("utf-8"))

app = w = None
for case in ("big5dict", "caps", "empty", "locked"):
	H.select_config(d, case)
	app, w, shown = H.start(d)
	print(f"112 {case} start: shown {shown}")
	holder = H.lock(os.path.join(d, "dictionary", "locked.csv"), "none") if case == "locked" else None
	H.set_source(w, "甲乙")
	H.convert_menu(w)
	print(f"112 {case} convert:", H.box(app, d, timeout=30))
	print(f"112 {case} braille: {H.braille_text(w)!r}")
	if holder is not None:
		H.unlock(holder)
	H.close_app(app, w, d)

for name in ("p1", "p2"):
	H.F9.pending(d, name, name + " text")
for name in ("new.dep",):
	path = os.path.join(d, "workspace", name)
	if os.path.exists(path):
		os.remove(path)
H.select_config(d, "big5dict")
app, w, shown = H.start(d)
print(f"112 export all start: shown {shown} docs {D.docs(w)}")
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, H.EXPORT_ALL_DIALOG, out)
print("112 export all summary:", H.box(app, d, timeout=60))
print("112 more boxes:", H.boxes(app, d, timeout=2))
print("112 out:", A.listing(out))
H.finish(app, w, d)
