r"""Items 154-155 (F-18 D8.3, D8.4, D8.6, D4): Rename and Delete of the active script; Export of No Processing.

Usage: python safe_run.py item154.py <exe> <work folder>
script\upper.py upper-cases; config.json selects it; no-processing.py is altered on disk
(it upper-cases too). alpha is pending.
154: Settings shows 「upper」; `abc` is converted (upper case). Script Management: rename
`upper` to `Upper2` (the prompt's title and name); the rows; config.json; Settings shows
「Upper2」. Delete `Upper2`: the question, answered 是 (UIA); the rows and the selection;
config.json; Settings shows 「不處理」; `abc` converted again (No Processing: as `abc`,
not as `ABC`).
155: Export 「不處理」: the file dialog's default name, a path under <d>\export; the file
holds the documented text, not the altered one; no-processing.py keeps the altered bytes.
Since the review fixes (N-f18c): 重新命名 and 刪除 are pressed with the keyboard focus on
them, and the focus and the buttons are logged after each (review I-1: back in the list).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import A, D, F9, G, X  # noqa: E402

ALTERED = b"def main(text):\n    return text.upper()\n"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
H.script(d, "upper", H.UPPER)
H.script(d, "no-processing", ALTERED)
H.write(os.path.join(d, "config.json"), json.dumps({"conversion": {"selected_script": "upper"}}).encode("utf-8"))
app, w, shown = H.start(d)
print(f"154 start: shown {shown} docs {D.docs(w)}")
dialog = H.settings(app, w)
print("154 settings at the start:", H.translation_panel(dialog)["choices"][2])
H.press(dialog, "取消", "Cancel")
box, before = H.convert(app, w, d, "abc")
print(f"154 convert abc with upper: box {box} braille {before!r}")
box, reference_upper = H.convert(app, w, d, "ABC")
print("154 equals the Braille of ABC:", before == reference_upper)

mgr = H.open_manager(app, w)
H.select(mgr, "upper")
H.press_focused(mgr, "重新命名", wait=1)
print("154 rename prompt shows:", repr(H.name_prompt(app, w, H.RENAME, "Upper2")))
print("154 rows after the rename:", H.rows(mgr), "selected", H.selected_row(mgr))
print("154 focus after the rename:", H.focus())
print("154 config.json conversion:", H.config(d))
H.press(mgr, "關閉", "Close")
dialog = H.settings(app, w)
print("154 settings after the rename:", H.translation_panel(dialog)["choices"][2])
H.press(dialog, "取消", "Cancel")

mgr = H.open_manager(app, w)
H.select(mgr, "Upper2")
H.press_focused(mgr, "刪除", wait=1)
print("154 delete:", H.box_press(app, d, "是"))
print("154 rows after the delete:", H.rows(mgr), "selected", H.selected_row(mgr))
print("154 focus after the delete:", H.focus(), "buttons", H.buttons(mgr))
print("154 config.json conversion:", H.config(d))
print("154 script folder:", sorted(H.script_files(d)))
H.press(mgr, "關閉", "Close")
dialog = H.settings(app, w)
print("154 settings after the delete:", H.translation_panel(dialog)["choices"][2])
H.press(dialog, "取消", "Cancel")
box, after = H.convert(app, w, d, "abc")
print(f"154 convert abc with No Processing: box {box} braille {after!r}")
print("154 differs from the Braille of ABC:", after != reference_upper)

mgr = H.open_manager(app, w)
H.select(mgr, "不處理")
H.press(mgr, "匯出", wait=1.5)
export = X.wait_window(app, w, H.EXPORT)
print("155 export dialog file name:", repr(export.child_window(class_name="Edit", found_index=0).wrapper_object().window_text()))
os.makedirs(os.path.join(d, "export"), exist_ok=True)
H.file_dialog(app, w, H.EXPORT, os.path.join(d, "export", "no-processing.py"))
print("155 boxes:", H.H12.boxes(app, d, timeout=2))
print("155 exported file is the documented text:", A.read(os.path.join(d, "export", "no-processing.py")) == H.NO_PROCESSING)
print("155 no-processing.py keeps the altered bytes:", H.script_files(d).get("no-processing.py") == ALTERED)
H.press(mgr, "關閉", "Close")
H.close(app, w, d)
