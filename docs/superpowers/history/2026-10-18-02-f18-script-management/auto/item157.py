r"""Item 157 (F-18 D10, O8, D3): the selected script is deleted outside the app.

Usage: python safe_run.py item157.py <exe> <work folder>
script\upper.py is selected in config.json; alpha is pending. Convert `abc` (upper case);
remove script\upper.py; convert again: the text-processing box. Restart: Settings shows
「不處理」 (the saved name is not listed); config.json keeps `upper` until a save.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
path = H.script(d, "upper", H.UPPER)
H.write(os.path.join(d, "config.json"), json.dumps({"conversion": {"selected_script": "upper"}}).encode("utf-8"))
app, w, shown = H.start(d)
print(f"157 start: shown {shown} docs {D.docs(w)}")
box, first = H.convert(app, w, d, "abc")
print(f"157 convert with upper: box {box} braille {first!r}")
os.remove(path)
print("157 script folder after the removal:", sorted(H.script_files(d)))
box, second = H.convert(app, w, d, "abc")
print(f"157 convert after the removal: box {box} braille {second!r}")
H.close(app, w, d)
app, w, shown = H.start(d)
print(f"157 restart: shown {shown} docs {D.docs(w)}")
dialog = H.settings(app, w)
print("157 settings after the restart:", H.translation_panel(dialog)["choices"][2])
H.press(dialog, "取消", "Cancel")
print("157 config.json conversion:", H.config(d))
H.close(app, w, d)
