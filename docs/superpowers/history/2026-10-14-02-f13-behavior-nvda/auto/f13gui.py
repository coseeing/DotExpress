"""Shared helpers for the F-13 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f12gui.py of F-12 and through it f9gui.py, f8bgui.py, f8agui.py,
f7gui.py, f5gui.py and dx.py, docs.py, dicts.py of the 2026-10-09-03 Windows verification.

Since F-13 (D2) the main window appears before the workspace is loaded and before the
startup boxes. The earlier start helpers (f8agui.start, f8bgui.start, dx.launch) return as
soon as a window titled "...DotExpress" is visible, which is too early on the new build.
``start`` waits for the main window, answers the invalid-files dialog (Keep) and every
message box (Enter), whether a main window exists yet or not, and records for each of them
whether the main window was visible, whether the box is owned by it, and the main window's
title at that moment. It returns once the main window is visible and enabled, no box of
the process has been open for 1 s, and its title is not the bare "DotExpress".
``start_a``, ``start_b`` and ``launch`` give the results of the old helpers, so that the
scripts of earlier items run unchanged (safe_run.py puts them in place of the old ones).
Work folders are built by script; keys go only to a window of the app under test while it
is in the foreground (safe_run.py). The work folder is shown as <d>. Nothing here touches
the clipboard.
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-11-02-f12-localization-cleanup", "auto"))
import f12gui as H12  # noqa: E402  (puts the F-9, F-8b, F-8a, F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f12gui import A, B, D, F, F9, G, X, dx  # noqa: E402

GW_OWNER = 4
MAIN_CLASS = "wxWindowNR"
OLD_START_A = A.start
OLD_START_B = B.start
OLD_LAUNCH = dx.launch
# The work folder of the item; safe_run.py sets it. Keys go only to windows of processes under it.
FOLDER = None


def foreground_is_app():
	"""Whether the foreground window belongs to a process whose exe lies under FOLDER."""
	import psutil
	import win32gui
	import win32process

	handle = win32gui.GetForegroundWindow()
	if not handle or FOLDER is None:
		return False
	pid = win32process.GetWindowThreadProcessId(handle)[1]
	try:
		exe = psutil.Process(pid).exe()
	except psutil.Error:
		return False
	return os.path.normcase(exe).startswith(FOLDER + os.sep)


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


def masked(d, value):
	return H12.masked(d, value)


def windows_of(d):
	"""(handle, title, class, visible, enabled) of every top-level window of the processes under ``d``."""
	import win32gui
	import win32process

	pids = {p.pid for p in A.processes(d)}
	found = []

	def collect(handle, _extra):
		if win32process.GetWindowThreadProcessId(handle)[1] in pids:
			found.append(
				(
					handle,
					win32gui.GetWindowText(handle),
					win32gui.GetClassName(handle),
					bool(win32gui.IsWindowVisible(handle)),
					bool(win32gui.IsWindowEnabled(handle)),
				)
			)

	win32gui.EnumWindows(collect, None)
	return found


def is_main_title(title):
	return title == "DotExpress" or title.endswith(" - DotExpress")


def main_handle(found):
	for handle, title, class_name, _visible, _enabled in found:
		if class_name == MAIN_CLASS and is_main_title(title):
			return handle
	return None


def _placement(handle, main):
	import win32gui

	owner = win32gui.GetWindow(handle, GW_OWNER)
	return {
		"main_visible": bool(win32gui.IsWindowVisible(main)) if main else None,
		"owner_is_main": main is not None and owner == main,
		"main_title": win32gui.GetWindowText(main) if main else None,
		"owner_visible": bool(win32gui.IsWindowVisible(owner)) if owner else None,
	}


def _answer(handle, title):
	"""Read and answer one startup window: the invalid-files dialog (Keep) or a message box (Enter)."""
	from pywinauto import Application, Desktop

	win = Application(backend="win32").connect(handle=handle).window(handle=handle)
	if title == A.INVALID_FILES:
		entry = {"invalid": win.child_window(class_name="ListBox").wrapper_object().item_texts()}
		X.btn(win, A.KEEP_INVALID).click()
		time.sleep(1)
		return entry
	if G.is_task_dialog(win):
		box = Desktop(backend="uia").window(handle=handle)
		entry = F.describe(box)
		entry["presses"] = F.answer(box, "enter")
		return entry
	return {"other window": title}


def start(d, timeout=60):
	"""Start <d>\\DotExpress.exe; answer what startup shows; (app, w, shown).

	``shown`` lists, in order, a dict per window answered: {"invalid": [...]} or the
	f5gui.describe dict of a message box (plus "presses"), each with main_visible,
	owner_is_main and main_title. If the main window is not ready in time, returns
	(None, None, shown + [how the start ended]).
	"""
	from pywinauto import Application

	launcher = subprocess.Popen([os.path.join(d, "DotExpress.exe")], cwd=d)
	started = time.time()
	shown = []
	handled = set()
	quiet_since = time.time()
	while time.time() - started < timeout:
		found = windows_of(d)
		main = main_handle(found)
		pending = [(h, t) for h, t, _c, visible, _e in found if visible and h != main and h not in handled]
		if pending:
			handle, title = pending[0]
			placement = _placement(handle, main)
			entry = _answer(handle, title)
			entry.update(placement)
			shown.append(entry)
			handled.add(handle)
			quiet_since = time.time()
			continue
		if any(visible for h, _t, _c, visible, _e in found if h != main):
			quiet_since = time.time()
		if main is not None:
			state = next(f for f in found if f[0] == main)
			if state[3] and state[4] and time.time() - quiet_since >= 1 and state[1] != "DotExpress":
				app = Application(backend="win32").connect(handle=main)
				return app, app.window(handle=main), shown
		if launcher.poll() is not None and not A.processes(d):
			return None, None, shown + [f"no main window; exited with code {launcher.returncode}"]
		time.sleep(0.3)
	return None, None, shown + [f"main window not ready after {timeout} s: {[f[1:] for f in windows_of(d)]}"]


def placements(shown):
	"""Where each startup window of ``shown`` appeared, as one short line."""
	out = []
	for entry in shown:
		if not isinstance(entry, dict):
			out.append(entry)
			continue
		name = "invalid-files dialog" if "invalid" in entry else entry.get("title") or entry.get("other window")
		out.append((name, entry.get("main_visible"), entry.get("owner_is_main"), entry.get("main_title"), entry.get("owner_visible")))
	return out


def _old_entry(entry):
	if not isinstance(entry, dict):
		return entry
	if "invalid" in entry:
		return ("invalid", entry["invalid"])
	return {key: value for key, value in entry.items() if key not in ("main_visible", "owner_is_main", "main_title", "owner_visible")}


def start_b(d, timeout=60):
	"""f8bgui.start's result from ``start``: ``shown`` as f8bgui gave it. The placement of
	each window is printed on a line of its own, "f13 start: [(window, main_visible,
	owner_is_main, main_title, owner_visible), ...]"."""
	app, w, shown = start(d, timeout)
	print(f"f13 start: {placements(shown)}")
	return app, w, [_old_entry(entry) for entry in shown]


def start_a(d, timeout=60):
	"""f8agui.start's result from ``start``: (app, w, the invalid-files list or None)."""
	app, w, shown = start(d, timeout)
	print(f"f13 start: {placements(shown)}")
	if app is None:
		return None, None, shown
	invalid = next((entry["invalid"] for entry in shown if isinstance(entry, dict) and "invalid" in entry), None)
	return app, w, invalid


def launch(exe, d, fresh=True):
	"""dx.launch's result from ``start``: (app, w), the exe copied into ``d`` as dx.launch does."""
	import shutil

	d = os.path.normpath(d)
	if fresh and os.path.isdir(d):
		dx.kill_under(d)
		shutil.rmtree(d)
	os.makedirs(d, exist_ok=True)
	target = os.path.join(d, "DotExpress.exe")
	if not os.path.exists(target):
		shutil.copy(exe, target)
	app, w, shown = start(d)
	if shown:
		print(f"f13 start: {placements(shown)}")
	if app is None:
		raise RuntimeError(f"main window not found: {shown}")
	return app, w


def install():
	"""Put ``start_a``, ``start_b`` and ``launch`` in place of the old start helpers."""
	A.start = start_a
	B.start = start_b
	dx.launch = launch


def focus(w):
	"""The control with the keyboard focus in the app's UI thread (GetGUIThreadInfo), and whether it is enabled."""
	import win32gui
	import win32process

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


def uia_focus():
	"""(control type, name) of the UIA focused element; "<another program>" if the app is not in the foreground."""
	from pywinauto.uia_defines import IUIA
	from pywinauto.uia_element_info import UIAElementInfo

	if not foreground_is_app():
		return "<another program>"
	info = UIAElementInfo(IUIA().iuia.GetFocusedElement())
	return info.control_type, info.name


def state(w):
	"""The list, the title, the editors (shortened) and the focus of the main window."""
	return f"docs {D.docs(w)} {F9.editors(w)} focus {focus(w)} uia {uia_focus()}"


def exit_code(handle, timeout):
	"""The exit code of the process behind ``handle`` (f9gui.process_handle) once it has ended
	within ``timeout`` s, or None if it still runs."""
	import win32event
	import win32process

	if win32event.WaitForSingleObject(handle, int(timeout * 1000)) != win32event.WAIT_OBJECT_0:
		return None
	code = win32process.GetExitCodeProcess(handle)
	return code - (1 << 32) if code >= 1 << 31 else code


def finish(app, w, d):
	print("close:", masked(d, D.close(app, w)))
	dx.kill_under(d)
