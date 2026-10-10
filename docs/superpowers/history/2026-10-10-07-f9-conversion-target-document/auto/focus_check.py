"""Fix phase (F-9 review M-6): where the keyboard focus is after a case (b) box.

Usage: python focus_check.py <exe> <work folder> <85|88>
Item 85's flow (alpha long and pending, open; beta short): Ctrl+Enter, Ctrl+Tab to beta at
once, the box, Enter; 88 also holds alpha.dep open with lock.py until the box, so the box is
the save error. The focus is read at each step with GetGUIThreadInfo of the app's UI
thread and mapped to the main window's Edit children (the review's focus_probe.py).
Nothing here touches the clipboard; keys go only to the foreground main window (f9gui.keys).
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f9gui as H  # noqa: E402
from f9gui import A, B, D, F  # noqa: E402

import win32gui  # noqa: E402
import win32process  # noqa: E402


class GUITHREADINFO(ctypes.Structure):
	_fields_ = [
		("cbSize", wt.DWORD),
		("flags", wt.DWORD),
		("hwndActive", wt.HWND),
		("hwndFocus", wt.HWND),
		("hwndCapture", wt.HWND),
		("hwndMenuOwner", wt.HWND),
		("hwndMoveSize", wt.HWND),
		("hwndCaret", wt.HWND),
		("rcCaret", wt.RECT),
	]


def focus(w):
	"""The control with the keyboard focus in the app's UI thread, and whether it is enabled."""
	thread_id = win32process.GetWindowThreadProcessId(w.handle)[0]
	info = GUITHREADINFO()
	info.cbSize = ctypes.sizeof(GUITHREADINFO)
	ctypes.windll.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info))
	handle = info.hwndFocus
	if not handle:
		return "none"
	edits = [control.handle for control in w.children(class_name="Edit")]
	enabled = bool(win32gui.IsWindowEnabled(handle))
	if handle in edits:
		which = ["source editor", "braille result editor"][edits.index(handle)]
		return f"{which} (enabled {enabled})"
	owner = win32gui.GetWindowText(win32gui.GetAncestor(handle, 2))
	return f"{win32gui.GetClassName(handle)} in {owner!r} (enabled {enabled})"


EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
H.pending(d, "alpha", H.long_text())
A.package(d, "beta", "beta body", "⠃")
app, w, shown = B.start(d)
print(f"{item} start: docs {D.docs(w)} {H.editors(w)} focus {focus(w)}")
H.convert(w)
time.sleep(0.3)
print(f"{item} after Ctrl+Enter: focus {focus(w)}")
H.keys(w, "^{TAB}")
print(f"{item} after Ctrl+Tab: {H.editors(w)} focus {focus(w)}")
holder = F.lock(os.path.join(d, "workspace", "alpha.dep"), "r") if item == "88" else None
print(f"{item} box: {H.box(app, d, timeout=90)}")
time.sleep(0.8)
print(f"{item} after the box: {H.editors(w)} focus {focus(w)}")
if holder is not None:
	F.unlock(holder)
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
H.keys(w, "^{TAB}")
print(f"{item} Ctrl+Tab back: {H.editors(w)} focus {focus(w)}")
H.finish(app, w, d)
