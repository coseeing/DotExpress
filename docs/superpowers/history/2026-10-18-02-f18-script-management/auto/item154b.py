r"""Item 154b (F-18 review I-1, M-5, M-6): Delete of the last and the first user script, of a
script already removed outside the app, and No Processing when no-processing.py is a folder.

Usage: python safe_run.py item154b.py <exe> <work folder>
script\ holds alpha.py, gone.py and zeta.py (valid), and no-processing.py is a folder (M-5);
config.json selects `gone`. Script Management: the rows (M-5: 「不處理」 first).
1. Select `zeta` (the last row), 刪除 with the keyboard focus on it, 是: the rows, the
   selection, the focus and the buttons (I-1).
2. Delete gone.py outside the app; select `gone`, 刪除, 是: any box (M-6: none; before, a
   「無法刪除腳本：[Errno 2] …」 box), the rows, config.json (the active script was `gone`).
3. Select `alpha` (the first user script), 刪除, 是: 「不處理」 is selected, 刪除 is disabled,
   and the focus (I-1: in the list on 「不處理」, not on the disabled button).
Settings shows 「不處理」 first and selected. Nothing reads or writes the clipboard.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9  # noqa: E402


def listing(d):
	"""The script folder's names, a folder with a trailing "/" (A.read cannot read one)."""
	folder = os.path.join(d, "script")
	return sorted(name + ("/" if os.path.isdir(os.path.join(folder, name)) else "") for name in os.listdir(folder))


EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
for name in ("alpha", "gone", "zeta"):
	H.script(d, name, H.UPPER)
os.makedirs(os.path.join(d, "script", "no-processing.py"))
H.write(os.path.join(d, "config.json"), json.dumps({"conversion": {"selected_script": "gone"}}).encode("utf-8"))
app, w, shown = H.start(d)
print(f"154b start: shown {shown} docs {D.docs(w)}")
print("154b script folder:", listing(d))

mgr = H.open_manager(app, w)
print("154b rows:", H.rows(mgr), "selected", H.selected_row(mgr))

H.select(mgr, "zeta")
print("154b selected after selecting zeta:", H.selected_row(mgr), "focus", H.focus())
H.press_focused(mgr, "刪除", wait=1)
print("154b delete zeta (last row):", H.box_press(app, d, "是"))
print("154b after zeta: rows", H.rows(mgr), "selected", H.selected_row(mgr), "focus", H.focus(), "buttons", H.buttons(mgr))

os.remove(os.path.join(d, "script", "gone.py"))
H.select(mgr, "gone")
print("154b selected after selecting gone:", H.selected_row(mgr), "focus", H.focus())
H.press_focused(mgr, "刪除", wait=1)
print("154b delete gone (removed outside the app):", H.box_press(app, d, "是"))
print("154b any box after it:", H.box(app, d, timeout=3))
print("154b after gone: rows", H.rows(mgr), "selected", H.selected_row(mgr), "focus", H.focus(), "buttons", H.buttons(mgr))
print("154b config.json conversion:", H.config(d))

H.select(mgr, "alpha")
print("154b selected after selecting alpha:", H.selected_row(mgr), "focus", H.focus())
H.press_focused(mgr, "刪除", wait=1)
print("154b delete alpha (first user script):", H.box_press(app, d, "是"))
print("154b after alpha: rows", H.rows(mgr), "selected", H.selected_row(mgr), "focus", H.focus(), "buttons", H.buttons(mgr))
print("154b script folder:", listing(d))
H.press(mgr, "關閉", "Close")

dialog = H.settings(app, w)
print("154b settings:", H.translation_panel(dialog)["choices"][2])
H.press(dialog, "取消", "Cancel")
H.close(app, w, d)
