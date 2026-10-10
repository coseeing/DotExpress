"""Items 76-78 (F-8 D8): BRL and HTML exports.

Usage: python item76.py <exe> <work folder> <76|77|78>
76: alpha (two braille lines): File > Export > BRL to out\\alpha.brl, then HTML to
    out\\alpha.html: the boxes, each file's sha256 and CRLF count, the folder.
77: Export BRL over out\\old.brl while lockshare.py holds it open (share rw, as an editor
    does), overwrite Yes: the box; old.brl's bytes; the folder.
78: alpha and beta: File > Export All > BRL into out\\, where beta.brl is held open (share
    rw), overwrite Yes: the summary; alpha.brl, beta.brl; the folder.
Before F-8 (N-f7): 76 is the reference (the same bytes); 77 and 78 write under the holder.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
BRAILLE = {"alpha": "⠁⠃\n⠉⠙", "beta": "⠃⠑\n⠞⠁"}
d = A.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
A.package(d, "alpha", "ab\ncd", BRAILLE["alpha"])
if item == "78":
	A.package(d, "beta", "be\nta", BRAILLE["beta"])
app, w, invalid = A.start(d)
print(f"{item} start: invalid {invalid} docs {D.docs(w)}")


def shown(box):
	"""The box with the work folder as <d> and a temporary file's random part as <random>."""
	if box is None:
		return None
	content = box["content"].replace(repr(d)[1:-1], "<d>")
	box["content"] = re.sub(r"(\.\w+\.brl\.)[0-9a-f]{16}(\.tmp)", r"\1<random>\2", content)
	return box


def describe(name):
	path = os.path.join(out, name)
	data = A.read(path)
	if data is None:
		return f"{name}: missing"
	crlf, lf = data.count(b"\r\n"), data.count(b"\n")
	return f"{name}: {data!r}" if len(data) < 20 else f"{name}: sha {A.sha(path)} crlf {crlf} lf {lf}"


if item == "76":
	D.select(w, "alpha")
	for key, menu_path, name in (("brl", "#0->#6->#1", "alpha.brl"), ("html", "#0->#6->#2", "alpha.html")):
		G.menu(w, menu_path, wait=0.5)
		A.save_dialog(app, w, "匯出文件", os.path.join(out, name))
		print(f"76 export {key}:", shown(G.answer_box(app, "enter")))
		print("76", describe(name))
elif item == "77":
	old = A.write(os.path.join(out, "old.brl"), b"OLD GOOD EXPORT")
	holder = A.lock(old, share="rw")
	D.select(w, "alpha")
	G.menu(w, "#0->#6->#1", wait=0.5)
	print("77 overwrite prompt:", A.save_dialog(app, w, "匯出文件", old))
	print("77 export brl:", shown(G.answer_box(app, "enter")))
	A.unlock(holder)
	print("77", describe("old.brl"))
elif item == "78":
	beta = A.write(os.path.join(out, "beta.brl"), b"OLD BETA EXPORT")
	holder = A.lock(beta, share="rw")
	G.menu(w, "#0->#7->#1", wait=0.5)
	G.path_dialog(app, w, "匯出全部文件", out)
	print("78 overwrite question:", shown(G.answer_box(app, "alt-y")))
	print("78 summary:", shown(G.answer_box(app, "enter")))
	A.unlock(holder)
	print("78", describe("alpha.brl"))
	print("78", describe("beta.brl"))
print(f"{item} out: {A.listing(out)}")
A.finish(app, w, d)
