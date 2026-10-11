r"""Item 116 (F-12 D8, D9): the Dual View HTML export of a document without conversion data.

Usage: python safe_run.py item116.py <exe> <work folder>
An empty workspace: the app creates the default document `new`. File > Export > Dual View
HTML; reads the file type list of the save dialog; saves to <d>\out\new.html. Prints the
type list, the box and whether the file holds the zh_TW or the English sentence.
Before F-12 (N-f11c): `HTML files (*.html)` and the English sentence.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, D, G, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
app, w, shown = H.start(d)
print(f"116 start: shown {shown} docs {D.docs(w)} {H.F9.editors(w)}")
G.menu(w, "#0->#6->#2", wait=0.5)
dialog = X.wait_window(app, w, H.F9.EXPORT_DIALOG)
for combo in [c for c in dialog.wrapper_object().descendants() if c.class_name() == "ComboBox"]:
	try:
		print("116 combo:", repr(combo.window_text()), combo.item_texts())
	except Exception as error:
		print("116 combo unreadable:", type(error).__name__)
G.path_dialog(app, w, H.F9.EXPORT_DIALOG, os.path.join(out, "new.html"))
print("116 box:", H.masked(d, H.F9.box(app, d, timeout=30)))
data = A.read(os.path.join(out, "new.html"))
html = data.decode("utf-8") if data else ""
print("116 file:", len(html), "chars; zh_TW sentence", "此文件沒有可顯示的轉換資料。" in html, "; English sentence", "No conversion data" in html)
H.finish(app, w, d)
