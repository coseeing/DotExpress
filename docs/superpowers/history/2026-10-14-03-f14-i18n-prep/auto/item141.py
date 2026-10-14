r"""Item 141 (F-14 D6): the lang of exported Dual View HTML files.

Usage: python safe_run.py item141.py <exe> <work folder>
alpha (中文 abc) and beta (beta text) are pending documents; alpha is open.
(a) Translation > Convert; File > Export > Dual View HTML into <d>\out_a\alpha.html.
(c) beta: Convert; File > Export All > Dual View HTML into <d>\out_c (two converted documents).
(b) In <d>\b, an empty workspace: the app creates the default document `new` (no conversion
    data); File > Export > Dual View HTML into <d>\b\out_b\new.html.
Prints each box and, for each file, its first two lines, its lang, its cells and whether it
shows the zh_TW page without conversion data.
Before F-14 (N-f12b): <html lang="en">.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f14gui as H  # noqa: E402
from f14gui import A, D, F9, G, H12  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
F9.pending(d, "alpha", "中文 abc")
F9.pending(d, "beta", "beta text")
out_a = os.path.join(d, "out_a")
out_c = os.path.join(d, "out_c")
os.makedirs(out_a)
os.makedirs(out_c)
app, w, shown = H12.start(d)
print(f"141 start: shown {shown} docs {D.docs(w)} {F9.editors(w)}")
H12.convert_menu(w)
print("141a convert:", F9.box(app, d, timeout=60))
G.menu(w, "#0->#6->#2", wait=0.5)
F9.export_path(app, w, F9.EXPORT_DIALOG, os.path.join(out_a, "alpha.html"))
print("141a export:", F9.box(app, d, timeout=30))
print("141a alpha.html:", H.html_file(os.path.join(out_a, "alpha.html")))
D.select(w, "beta")
H12.convert_menu(w)
print("141c convert beta:", F9.box(app, d, timeout=60))
G.menu(w, "#0->#7->#2", wait=0.5)
F9.export_path(app, w, F9.EXPORT_ALL_DIALOG, out_c)
print("141c export all:", F9.box(app, d, timeout=30))
for name in sorted(os.listdir(out_c)):
	print(f"141c {name}:", H.html_file(os.path.join(out_c, name)))
H.finish(app, w, d)

d_b = A.prepare(EXE, os.path.join(d, "b"))
out_b = os.path.join(d_b, "out_b")
os.makedirs(out_b)
app, w, shown = H12.start(d_b)
print(f"141b start: shown {shown} docs {D.docs(w)} {F9.editors(w)}")
G.menu(w, "#0->#6->#2", wait=0.5)
F9.export_path(app, w, F9.EXPORT_DIALOG, os.path.join(out_b, "new.html"))
print("141b export:", F9.box(app, d_b, timeout=30))
print("141b new.html:", H.html_file(os.path.join(out_b, "new.html")))
H.finish(app, w, d_b)
