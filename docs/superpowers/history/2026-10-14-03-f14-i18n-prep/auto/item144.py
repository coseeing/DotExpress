r"""Item 144 (F-14 D6, D7, regression): the Dual View page and an ordinary settings save.

Usage: python safe_run.py item144.py <exe> <work folder>
alpha (中文 abc) and beta (beta text) are pending documents; alpha is open; config.json is
intact (it selects no dictionary).
(a) alpha: Translation > Convert; Translation > Dual View; then beta (not converted, opened
    with File > Open):
    Dual View again. Translation > Dual View opens the page in a browser: the run puts a
    stand-in browser first on PATH (f14gui.fake_browser) and reads, for each, the page the
    app wrote to <d>\dual_view: its first lines, lang, cells, and whether it shows the zh_TW
    page without conversion data; and the boxes. The stand-in is always installed, before
    the app starts: the first run's "window" mode, which looked for an in-app Dual View
    window and so let the app start a real browser (auto-results.md), is removed (F-14
    review M-1).
(b) Settings: change the width to 30, OK: the boxes; config.json's width.
Expected the same as before F-14 (N-f12b), apart from the page's lang.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f14gui as H  # noqa: E402
from f14gui import A, D, F9, G, H12  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
F9.pending(d, "alpha", "中文 abc")
F9.pending(d, "beta", "beta text")
H12.select_config(d)
print("144 stand-in browser:", H.masked(d, H.fake_browser(d)))
app, w, shown = H12.start(d)
print(f"144 start: shown {shown} docs {D.docs(w)} {F9.editors(w)}")
H12.convert_menu(w)
print("144a convert:", F9.box(app, d, timeout=60))
read = H.dual_view_page
print("144a dual view of alpha:", read(app, w, d))
D.select(w, "beta")
G.menu(w, "#0->#0", wait=1)  # File > Open (a selection alone does not open the document)
print(f"144a beta: {F9.editors(w)}")
print("144a dual view of beta:", read(app, w, d))
dialog = H12.settings(app, w)
H12.width_control(dialog).set_edit_text("30")
H12.press(dialog, "確定", "OK", wait=2)
print("144b after OK:", H12.boxes(app, d, timeout=4))
config = json.loads(A.read(os.path.join(d, "config.json")).decode("utf-8-sig"))
print("144b config.json width:", config.get("conversion", {}).get("width"))
H.finish(app, w, d)
dual = os.path.join(d, "dual_view")
print("144 dual_view folder after the exit:", os.listdir(dual) if os.path.isdir(dual) else "missing")
