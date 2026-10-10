"""Shared helpers for the F-7 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py, dicts.py and lock.py of the 2026-10-09-03 Windows verification
and f5gui.py of F-5, unchanged. wx shows its message boxes as Windows task dialogs:
``boxes`` reads each one through UIA (title, main instruction, content, buttons, focus)
and ``answer_box`` presses a key in it (f5gui.answer, which presses again if the key was
lost). The app's own dialogs (name dialogs, the dictionary editor, Settings, Text
Processing) are plain win32 dialogs, read by ``buttons``.

The session-end items send WM_QUERYENDSESSION or WM_ENDSESSION to the main window of
the DotExpress process under test only, from a driver thread (SendMessageTimeoutW).
Nothing here asks Windows to log off or shut down.
"""
import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
F5 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-01-f5-save-failure-handling", "auto"))
sys.path.insert(0, F5)
import f5gui as F  # noqa: E402  (puts 2026-10-09-03/auto on sys.path)
from f5gui import D, dx  # noqa: E402
import dicts as X  # noqa: E402

F.KEYS.update({"alt-y": "%y", "alt-n": "%n"})
CLOSE_DIALOG = F.CLOSE_DIALOG_TITLE
TEXT_PROCESSING = "文字處理"
SETTINGS_PREFIX = "DotExpress 設定"
MGR = "字典管理"
EDITOR = "自訂字典管理器"
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
ENDSESSION_LOGOFF = 0x80000000
SMTO_NORMAL = 0x0000

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SendMessageTimeoutW.argtypes = (
	wintypes.HWND,
	wintypes.UINT,
	wintypes.WPARAM,
	wintypes.LPARAM,
	wintypes.UINT,
	wintypes.UINT,
	ctypes.POINTER(ctypes.c_size_t),
)
user32.SendMessageTimeoutW.restype = ctypes.c_size_t


def is_task_dialog(win):
	return any(c.class_name() == "DirectUIHWND" for c in win.wrapper_object().children())


def task_dialogs(app):
	"""The open message boxes (task dialogs) of ``app``, as UIA wrappers."""
	from pywinauto import Desktop

	return [Desktop(backend="uia").window(handle=box.handle) for box in dx.dialogs(app) if is_task_dialog(box)]


def wait_box(app, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		found = task_dialogs(app)
		if found:
			return found[0]
		time.sleep(0.3)
	return None


def answer_box(app, key, timeout=10):
	"""Read the next message box, press ``key`` (a key of f5gui.KEYS) and return what it showed.

	The result is the description of f5gui.describe plus ``presses``, or None if no box
	opened within ``timeout`` seconds.
	"""
	box = wait_box(app, timeout)
	if box is None:
		return None
	described = F.describe(box)
	described["presses"] = F.answer(box, key)
	return described


def buttons(win):
	"""The visible win32 buttons of a wx dialog, in tab order."""
	return [c.window_text() for c in win.wrapper_object().descendants() if c.class_name() == "Button" and c.is_visible()]


def edit_text(win):
	return win.child_window(class_name="Edit", found_index=0).wrapper_object().window_text()


def windows(app, w):
	return sorted(X.windows(app, w))


def window_titled(app, w, prefix, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		for title, win in X.windows(app, w).items():
			if title.startswith(prefix):
				return win
		time.sleep(0.3)
	raise RuntimeError(f"no window {prefix}: {windows(app, w)}")


def menu(w, path, wait=1.5):
	w.set_focus()
	w.menu_select(path)
	time.sleep(wait)


def path_dialog(app, w, title, path):
	"""Fill the file or folder dialog ``title`` with ``path`` and press its Save, Open or
	Select Folder button: the first visible button other than Cancel."""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit", found_index=0).wrapper_object().set_edit_text(path)
	pressable = [
		c
		for c in dialog.wrapper_object().descendants()
		if c.class_name() == "Button" and c.is_visible() and c.window_text() not in ("取消", "Cancel")
	]
	pressable[0].click()
	time.sleep(2)


def press_keys(win, keys, wait=1.0):
	from pywinauto.keyboard import send_keys

	win.set_focus()
	send_keys(keys)
	time.sleep(wait)


def count_titled(app, title):
	return len([h for h in app.windows(visible_only=True) if h.window_text() == title])


class SessionMessage(threading.Thread):
	"""Send WM_QUERYENDSESSION or WM_ENDSESSION to ``hwnd`` from a driver thread.

	``returned_after`` is the time from the start of the call to its return in seconds,
	``ok`` the return value of SendMessageTimeoutW (0: timed out or failed) and
	``result`` the window's answer (WM_QUERYENDSESSION: 1 may end, 0 may not).
	"""

	def __init__(self, hwnd, message, wparam=0, lparam=ENDSESSION_LOGOFF, timeout_ms=10000):
		super().__init__(daemon=True)
		self.args = (hwnd, message, wparam, lparam, SMTO_NORMAL, timeout_ms)
		self.ok = None
		self.result = None
		self.returned_after = None

	def run(self):
		result = ctypes.c_size_t(0)
		start = time.time()
		self.ok = user32.SendMessageTimeoutW(*self.args, ctypes.byref(result))
		self.returned_after = round(time.time() - start, 1)
		self.result = result.value

	def state(self):
		if self.returned_after is None:
			return "not returned"
		return {"ok": self.ok, "result": self.result, "after_s": self.returned_after}


def watch_close_dialogs(app, seconds=3.0, step=0.25):
	"""The largest number of open close dialogs seen during ``seconds``."""
	most = 0
	end = time.time() + seconds
	while time.time() < end:
		most = max(most, count_titled(app, CLOSE_DIALOG))
		time.sleep(step)
	return most


def answer_close_dialogs(app, key="esc", sender=None):
	"""Press ``key`` in the topmost open close dialog (the innermost one), one dialog at a
	time, until none is left. Returns one entry per dialog: the dialogs open before the key,
	how often it was pressed, and the state of ``sender`` after it."""
	from pywinauto import Desktop

	steps = []
	end = time.time() + 40
	while time.time() < end:
		# Top-level windows come in z-order, topmost first.
		open_now = [h.handle for h in app.windows(visible_only=True) if h.window_text() == CLOSE_DIALOG]
		if not open_now:
			break
		dialog = Desktop(backend="uia").window(handle=open_now[0])
		presses = F.answer(dialog, key)
		time.sleep(0.5)
		steps.append({"open": len(open_now), "presses": presses, "call": sender.state() if sender else None})
	return steps


def exit_code(pid, timeout=10):
	"""The exit code of process ``pid`` once it has ended, or None if it is still running."""
	import psutil

	try:
		process = psutil.Process(pid)
	except psutil.NoSuchProcess:
		return "gone"
	try:
		return process.wait(timeout)
	except psutil.TimeoutExpired:
		return None


def gui_log(d):
	path = os.path.join(d, "log", "gui.log")
	if not os.path.exists(path):
		return []
	with open(path, encoding="utf-8") as stream:
		return stream.read().splitlines()
