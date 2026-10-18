r"""Items 149-151 (F-18 D8.1, D9, D5): Add, the editor, invalid code, Cancel.

Usage: python safe_run.py item149.py <exe> <work folder>
alpha is pending. First `ABC` is converted with No Processing (the reference).
149: Script Management > 新增: the name prompt, `upper`; the editor (title, text, UIA name,
focus); its text replaced (WM_SETTEXT) by an upper-casing main; 確定: the windows, the rows,
script\upper.py. Settings: 「upper」 chosen, 確定: config.json. `abc` converted: the same
Braille as `ABC` before.
150: 新增 `bad`; `def main(a, b): return a`; 套用: the box and the focus after it; the files;
取消: the question, answered 放棄變更 (UIA); the windows and the rows.
151: 新增 `typed`; `def main(x: int) -> str:` ...; 套用: the box; 取消: 放棄變更.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
app, w, shown = H.start(d)
print(f"149 start: shown {shown} docs {D.docs(w)}")
box, reference = H.convert(app, w, d, "ABC")
print(f"149 reference ABC: box {box} braille {reference!r}")

mgr = H.open_manager(app, w)
H.press(mgr, "新增", wait=1)
print("149 name prompt shows:", repr(H.name_prompt(app, w, H.ADD, "upper")))
editor = X.wait_window(app, w, "upper")
print("149 editor:", H.editor_state(editor))
H.set_text(H.editor_control(editor), H.UPPER.decode("utf-8"))
H.press(editor, "確定", "OK")
print("149 windows after 確定:", H.windows(app, w))
print("149 rows:", H.rows(mgr), "selected", H.selected_row(mgr), "focus", H.focus())
files = H.script_files(d)
print("149 script folder:", sorted(files), "upper.py is the text typed:", files.get("upper.py") == H.UPPER)
H.press(mgr, "關閉", "Close")
dialog = H.settings(app, w)
H.choose_script(dialog, "upper")
print("149 settings before 確定:", H.translation_panel(dialog))
H.press(dialog, "確定", "OK")
print("149 config.json conversion:", H.config(d))
box, converted = H.convert(app, w, d, "abc")
print(f"149 convert abc with upper: box {box} braille {converted!r}")
print("149 equals the Braille of ABC:", converted == reference)

mgr = H.open_manager(app, w)
H.press(mgr, "新增", wait=1)
H.name_prompt(app, w, H.ADD, "bad")
editor = X.wait_window(app, w, "bad")
H.set_text(H.editor_control(editor), "def main(a, b): return a")
H.press(editor, "套用", "Apply", wait=1)
print("150 apply:", H.box(app, d))
print("150 focus after the box:", H.focus())
print("150 script folder:", sorted(H.script_files(d)))
H.press(editor, "取消", "Cancel", wait=1)
print("150 cancel:", H.box_press(app, d, "放棄變更"))
print("150 windows:", H.windows(app, w))
print("150 rows:", H.rows(mgr))

H.press(mgr, "新增", wait=1)
H.name_prompt(app, w, H.ADD, "typed")
editor = X.wait_window(app, w, "typed")
H.set_text(H.editor_control(editor), "def main(x: int) -> str:\n    return str(x)\n")
H.press(editor, "套用", "Apply", wait=1)
print("151 apply:", H.box(app, d))
H.press(editor, "取消", "Cancel", wait=1)
print("151 cancel:", H.box_press(app, d, "放棄變更"))
print("151 rows:", H.rows(mgr), "script folder:", sorted(H.script_files(d)))
H.press(mgr, "關閉", "Close")
H.close(app, w, d)
