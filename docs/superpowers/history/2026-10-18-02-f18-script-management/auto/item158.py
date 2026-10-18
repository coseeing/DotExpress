r"""Item 158 (F-18 regression): Dictionary Management, and the same Braille as before F-18.

Usage: python safe_run.py item158.py <exe> <work folder>
Run on N-f18 and on N-f14b. dictionary\good.csv maps 甲乙 to ⠁⠃ and is selected; alpha is
pending. (a) The conversion of a mixed text (Chinese, English, a number, a dictionary
word, inline math): its Braille is printed with its sha256, to be the same on both builds
(No Processing changes nothing). (b) Dictionary Management: the rows; 新增 `dict2` (the
prompt) and the rows; 重新命名 `dict2` to `dict3`; 刪除 `dict3` answered 是 (UIA); 編輯
`good`: the editor opens over the main window (Dictionary Management closes) and 取消
closes it without a question. (c) The F-12 settings save: the width set to 30, 確定:
config.json's width.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9, X  # noqa: E402

TEXT = "臺灣的點字 Braille 2026 年，甲乙 $x^2+1$ 完成。"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
H.write(os.path.join(d, "dictionary", "good.csv"), "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n".encode("utf-8"))
H.write(os.path.join(d, "config.json"), json.dumps({"conversion": {"selected_dictionary": "good"}}).encode("utf-8"))
app, w, shown = H.start(d)
print(f"158 start: shown {shown} docs {D.docs(w)}")
box, braille = H.convert(app, w, d, TEXT)
print(f"158a convert: box {box}")
print(f"158a braille {braille!r} sha256 {hashlib.sha256(braille.encode('utf-8')).hexdigest()[:16]}")

w.set_focus()
w.menu_select("#1->#3")
mgr = X.wait_window(app, w, "字典管理")
print("158b rows:", H.rows(mgr))
H.press(mgr, "新增", wait=1)
print("158b add prompt shows:", repr(H.name_prompt(app, w, "新增字典", "dict2")))
print("158b rows after add:", H.rows(mgr))
H.select(mgr, "dict2")
H.press(mgr, "重新命名", wait=1)
print("158b rename prompt shows:", repr(H.name_prompt(app, w, "重新命名字典", "dict3")))
print("158b rows after rename:", H.rows(mgr))
H.select(mgr, "dict3")
H.press(mgr, "刪除", wait=1)
print("158b delete:", H.box_press(app, d, "是"))
print("158b rows after delete:", H.rows(mgr))
H.select(mgr, "good")
H.press(mgr, "編輯", wait=1.5)
editor = X.wait_window(app, w, "自訂字典管理器")
print("158b windows with the editor:", H.windows(app, w))
H.press(editor, "取消", "Cancel", wait=1.5)
print("158b windows after 取消:", H.windows(app, w), "boxes", H.H12.boxes(app, d, timeout=2))

dialog = H.settings(app, w)
H.H12.width_control(dialog).set_edit_text("30")
H.press(dialog, "確定", "OK", wait=2)
print("158c boxes:", H.H12.boxes(app, d, timeout=3))
print("158c config.json width:", H.config(d).get("width"))
H.close(app, w, d)
