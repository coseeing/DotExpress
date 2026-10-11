r"""Items 109 and 110 (F-12 D1): the Export All summary.

Usage: python safe_run.py item109.py <exe> <work folder> <109|110>
Three converted documents (alpha, beta, gamma). File > Export All > BRL into <d>\out.
110: <d>\out\beta.brl exists and is held open without sharing by F-8a's lockshare.py;
the overwrite question is answered with Yes (Alt+Y). Prints the boxes (caption, text) and
the files of the folder.
Before F-12 (N-f11c): the English summary.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, D, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
BRAILLE = {"alpha": "⠁⠃", "beta": "⠃⠑", "gamma": "⠛⠁"}
d = H.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
for name, braille in BRAILLE.items():
	A.package(d, name, name + " text", braille)
holder = None
if item == "110":
	beta = H.write(os.path.join(out, "beta.brl"), b"OLD BETA EXPORT")
	holder = H.lock(beta, "none")
app, w, shown = H.start(d)
print(f"{item} start: shown {shown} docs {D.docs(w)}")
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, H.EXPORT_ALL_DIALOG, out)
if item == "110":
	print("110 overwrite question:", H.box(app, d, timeout=10, key="alt-y"))
print(f"{item} summary:", H.box(app, d, timeout=30))
print(f"{item} more boxes:", H.boxes(app, d, timeout=2))
if holder is not None:
	H.unlock(holder)
for name in sorted(os.listdir(out)):
	print(f"{item} out\\{name}: {A.read(os.path.join(out, name))!r}")
H.finish(app, w, d)
