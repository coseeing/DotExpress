"""Shared helpers for the F-5 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and lock.py of the 2026-10-09-03 Windows verification unchanged.
wx shows its message boxes as Windows task dialogs. dx.dismiss reads their text, but
its win32 click does not reach the button, so the box stays open (seen in the F-5 dry
run; an open box keeps the process alive after Close). ``dismiss`` presses OK through
UIA instead, and the F-5 close dialog is read and answered through UIA too.
"""
import ctypes
import os
import subprocess
import sys
import time
import zipfile
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402

LOCK = os.path.join(AUTO03, "lock.py")
CLOSE_DIALOG_TITLE = "無法儲存文件"
KEYS = {"enter": "{ENTER}", "esc": "{ESC}", "alt-r": "%r", "alt-w": "%w"}


def workspace(d):
	return os.path.join(d, "workspace")


def files(d):
	return sorted(os.listdir(workspace(d)))


def leftovers(d):
	return [name for name in files(d) if name.endswith(".tmp")]


def attrib(path):
	return subprocess.run(["cmd", "/c", "attrib", path], capture_output=True, text=True).stdout.strip()


def package(path):
	"""(sha256 of the zip members, st_mtime_ns): the members ignore the zip timestamps."""
	return D.content_hash(path), os.stat(path).st_mtime_ns


def member(path, name):
	with zipfile.ZipFile(path) as archive:
		return archive.read(name)


def lock(path, share):
	"""Hold ``path`` open in another process (lock.py, share "r" or "rw") until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCK, path, "600", share], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip(), share)
	return process


def unlock(process):
	subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
	time.sleep(1)


def dismiss(app, buttons=("OK", "確定")):
	"""Read every message box of ``app`` and press its OK button through UIA.

	Returns [(caption, texts)] like dx.dismiss. A file dialog and the F-5 close dialog
	are left open.
	"""
	from pywinauto import Desktop

	out = []
	for box in dx.dialogs(app):
		if box.window_text() == CLOSE_DIALOG_TITLE:
			continue
		texts = dx.dialog_text(box)
		if "檔案名稱:" in texts:
			out.append((box.window_text(), "<file dialog left open>"))
			continue
		out.append((box.window_text(), [t for t in texts if t not in ("MainInstructionIcon", "關閉")]))
		pressable = [
			button
			for button in Desktop(backend="uia").window(handle=box.handle).descendants(control_type="Button")
			if button.window_text() in buttons
		]
		if pressable:
			pressable[0].invoke()
			time.sleep(0.8)
	return out


def switch(app, w, back=False):
	"""Ctrl+Tab (Ctrl+Shift+Tab if ``back``); return the message boxes it showed (closed) and the title."""
	from pywinauto.keyboard import send_keys

	w.set_focus()
	send_keys("^+{TAB}" if back else "^{TAB}")
	time.sleep(1.5)
	return dismiss(app), w.window_text()


def open_document(app, w, name):
	"""Select ``name``, choose File > Open (#0->#0) and return the message boxes it showed."""
	D.select(w, name)
	w.set_focus()
	w.menu_select("#0->#0")
	time.sleep(1.2)
	return dismiss(app)


def setup_alpha_beta(exe, d):
	"""A new work folder with alpha ("alpha body") and beta ("beta body"), closed and restarted.

	After the restart alpha is open and unchanged since it was loaded.
	"""
	app, w = dx.launch(exe, d)
	print("add alpha:", D.add(app, w, "alpha"))
	D.set_input(w, "alpha body")
	print("add beta:", D.add(app, w, "beta"))
	D.set_input(w, "beta body")
	print("close:", D.close(app, w))
	app, w = dx.launch(exe, d, fresh=False)
	print("docs:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)), "files:", files(d))
	return app, w


def paste_text_with_lone_surrogate(w, units=(0x41, 0xD83D, 0x42)):
	"""Replace the input text by pasting raw UTF-16 code units (a lone surrogate by default)."""
	user32 = ctypes.WinDLL("user32", use_last_error=True)
	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	user32.OpenClipboard.argtypes = (wintypes.HWND,)
	user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
	user32.SetClipboardData.restype = wintypes.HANDLE
	kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
	kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
	kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
	kernel32.GlobalLock.restype = ctypes.c_void_p
	kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
	data = b"".join(unit.to_bytes(2, "little") for unit in units) + b"\x00\x00"
	handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
	pointer = kernel32.GlobalLock(handle)
	ctypes.memmove(pointer, data, len(data))
	kernel32.GlobalUnlock(handle)
	if not user32.OpenClipboard(None):
		raise ctypes.WinError(ctypes.get_last_error())
	try:
		user32.EmptyClipboard()
		if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
			raise ctypes.WinError(ctypes.get_last_error())
	finally:
		user32.CloseClipboard()
	edit = w.children(class_name="Edit")[0]
	edit.set_edit_text("")
	edit.send_message(0x0302, 0, 0)  # WM_PASTE
	time.sleep(0.5)


def close_dialog(w, timeout=15):
	"""The F-5 close dialog (UIA wrapper), a child of the main window in the UIA tree."""
	from pywinauto import Desktop

	end = time.time() + timeout
	while time.time() < end:
		dialog = Desktop(backend="uia").window(handle=w.handle).child_window(title=CLOSE_DIALOG_TITLE, control_type="Window")
		if dialog.exists(timeout=0):
			return dialog
		time.sleep(0.3)
	return None


def describe(dialog):
	"""What a screen reader gets: title, main instruction, content, buttons, focus."""
	from pywinauto.uia_defines import IUIA

	dialog.set_focus()
	time.sleep(0.5)

	def text(automation_id):
		found = dialog.child_window(auto_id=automation_id, control_type="Text")
		return found.window_text() if found.exists(timeout=0) else None

	buttons = [
		button.window_text()
		for button in dialog.descendants(control_type="Button")
		if button.element_info.parent.control_type != "TitleBar"
	]
	focused = IUIA().iuia.GetFocusedElement()
	return {
		"title": dialog.window_text(),
		"main": text("MainInstruction"),
		"content": text("ContentText"),
		"buttons": buttons,
		"focus": focused.CurrentName,
	}


def answer(dialog, key):
	"""Bring the dialog to the foreground and press ``key`` (a key of KEYS).

	A key pressed while the window takes the focus is sometimes lost: if the same dialog
	is still open 5 s later, the key is pressed again (at most three times). Returns how
	many times it was pressed. A dialog shown again after a failed retry is a new window.
	"""
	import win32gui
	from pywinauto.keyboard import send_keys

	handle = dialog.handle
	for presses in (1, 2, 3):
		for _attempt in range(10):
			if win32gui.GetForegroundWindow() == handle:
				break
			dialog.set_focus()
			time.sleep(0.5)
		time.sleep(0.5)
		send_keys(KEYS[key])
		end = time.time() + 5
		while time.time() < end:
			if not win32gui.IsWindow(handle):
				time.sleep(1)
				return presses
			time.sleep(0.2)
	return presses


def wait_exit(app, timeout=15):
	end = time.time() + timeout
	while time.time() < end:
		if not app.is_process_running():
			return True
		time.sleep(0.5)
	return False


def close_and_answer(app, w, answers, between=None):
	"""Post WM_CLOSE and answer each close dialog in turn with a key of KEYS.

	``between`` maps an answer's index to a function called before that answer (for
	example releasing a lock). Returns (dialogs, outcome): the description of each dialog
	answered, and "exited", "running" or a message about an unexpected window.
	"""
	import win32con

	w.post_message(win32con.WM_CLOSE)
	time.sleep(1)
	dialogs = []
	for index, key in enumerate(answers):
		dialog = close_dialog(w)
		if dialog is None:
			return dialogs, "exited" if wait_exit(app, 5) else f"no dialog for answer {index}: {dismiss(app)}"
		dialogs.append(describe(dialog))
		if between and index in between:
			between[index]()
		dialogs[-1]["presses"] = answer(dialog, key)
	if wait_exit(app, 5):
		return dialogs, "exited"
	if close_dialog(w, timeout=1) is not None:
		return dialogs, "dialog still open"
	other = dismiss(app)
	return dialogs, f"running {other}" if other else "running"
