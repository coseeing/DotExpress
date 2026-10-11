r"""Item 118 (F-12 regression): what must not change.

Usage: python safe_run.py item118.py <exe> <work folder>
config.json selects `good` (a UTF-8 dictionary with 甲乙). alpha is a pending document.
(a) Translation > Convert: the box 轉換完成。
(b) File > Add `alpha` while alpha is listed: 文件「alpha」已存在。 and the name dialog again.
(c) Settings, change the width, OK: no box; config.json holds the new width.
(d) After a restart with alpha long (pending): Ctrl+Enter, Ctrl+Tab to beta: the box
    轉換完成。結果已儲存到文件「alpha」。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, D, G  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
H.dictionary(d, "good", "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n".encode("utf-8"))
H.select_config(d, "good")
H.F9.pending(d, "alpha", "甲乙")
A.package(d, "beta", "beta body", "⠃")
app, w, shown = H.start(d)
print(f"118 start: shown {shown} docs {D.docs(w)} {H.F9.editors(w)}")
H.convert_menu(w)
print("118a convert:", H.F9.box(app, d, timeout=30))
print(f"118a braille: {H.braille_text(w)!r}")
box, again = A.name_prompt(app, w, "#0->#3", "新增文件", "alpha")
print("118b add alpha: box", H.masked(d, box), "name dialog again", again)
dialog = H.settings(app, w)
H.width_control(dialog).set_edit_text("30")
H.press(dialog, "確定", "OK", wait=2)
print("118c after OK:", H.boxes(app, d, timeout=4))
print("118c config.json width:", json.loads(A.read(os.path.join(d, "config.json")).decode("utf-8-sig")).get("conversion", {}).get("width"))
H.close_app(app, w, d)

H.F9.pending(d, "alpha", H.F9.long_text())
app, w, shown = H.start(d)
print(f"118d start: shown {shown} docs {D.docs(w)} {H.F9.editors(w)}")
H.F9.convert(w)
H.F9.keys(w, "^{TAB}")
print("118d box:", H.masked(d, H.F9.box(app, d, timeout=120)))
print("118d more boxes:", H.boxes(app, d, timeout=3))
print(f"118d {H.F9.editors(w)} alpha {H.F9.package(d, 'alpha')}")
H.finish(app, w, d)
