"""Item 114 (F-12 D6): settings that cannot be saved.

Usage: python safe_run.py item114.py <exe> <work folder> <a|b>
a: config.json is held open without sharing by lockshare.py after the start (held from
   before the start, the app does not start: it reports that it cannot write its data
   folder). Settings: change the conversion width, OK; then Ctrl + one wheel notch in the
   source editor.
b: config.json holds "{" and config.json.bak is a folder. Settings: change the width, Apply,
   then OK.
Prints each box (title, main instruction, content, owner), the editor's font height before
and after the wheel, and config.json's bytes.
Before F-12 (N-f11c): no box.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, G  # noqa: E402

EXE, d, case = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = H.prepare(EXE, d)
cfg = os.path.join(d, "config.json")
holder = None
if case == "a":
	H.config(d, b'{"conversion": {}}')
else:
	H.config(d, b"{")
	os.makedirs(cfg + ".bak")
app, w, shown = H.start(d)
# The app writes its client id a moment after the window is up; read config.json after that.
time.sleep(2)
before = A.read(cfg)
if case == "a":
	holder = H.lock(cfg, "none")
print(f"114{case} start: shown {shown}")
height = H.editor_font_height(w)
dialog = H.settings(app, w)
print(f"114{case} settings buttons: {G.buttons(dialog)}")
H.width_control(dialog).set_edit_text("30")
time.sleep(0.5)
if case == "a":
	H.press(dialog, "確定", "OK", wait=2)
	print("114a after OK:", H.boxes(app, d, timeout=6))
	A.wheel_up_with_ctrl(w)
	print("114a after Ctrl+wheel:", H.boxes(app, d, timeout=4))
	print(f"114a font height {height} -> {H.editor_font_height(w)}")
	H.unlock(holder)
	print("114a config.json bytes unchanged:", A.read(cfg) == before)
else:
	H.press(dialog, "套用", "Apply", wait=2)
	print("114b after Apply:", H.boxes(app, d, timeout=6))
	again = G.window_titled(app, w, H.SETTINGS)
	H.press(again, "確定", "OK", wait=2)
	print("114b after OK:", H.boxes(app, d, timeout=4))
	print("114b config.json:", A.read(cfg), "bak is a folder:", os.path.isdir(cfg + ".bak"))
H.finish(app, w, d)
