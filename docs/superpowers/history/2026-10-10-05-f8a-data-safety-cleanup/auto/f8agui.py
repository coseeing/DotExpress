"""Shared helpers for the F-8a GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py, dicts.py and lock.py of the 2026-10-09-03 Windows verification,
f5gui.py of F-5 and f7gui.py of F-7, unchanged. Every item builds its own work folder
before the start: packages are written with zipfile, config.json as raw bytes. Startup
can show the invalid-workspace-files dialog before the main window; ``start`` answers it
with Keep. Message boxes are task dialogs, read and answered through UIA (f7gui).
Nothing here touches the clipboard.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F7 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-04-f7-dialog-buttons-surrogates-close", "auto"))
sys.path.insert(0, F7)
import f7gui as G  # noqa: E402  (puts F-5's and 2026-10-09-03's auto folders on sys.path)
from f7gui import D, F, X, dx  # noqa: E402

LOCKSHARE = os.path.join(HERE, "lockshare.py")
INVALID_FILES = "無效的工作區文件"
KEEP_INVALID = "保留無效檔案"
OVERWRITE_PROMPT = "確認另存新檔"
WM_MOUSEWHEEL = 0x020A
MK_CONTROL = 0x0008
WHEEL_DELTA = 120


def prepare(exe, d):
	"""A new, empty work folder ``d`` (with workspace\\) and the exe copied in.

	Only processes whose exe lies under ``d`` are ended first (dx.kill_under).
	"""
	d = os.path.normpath(d)
	if os.path.isdir(d):
		dx.kill_under(d)
		shutil.rmtree(d)
	os.makedirs(os.path.join(d, "workspace"))
	shutil.copy(exe, os.path.join(d, "DotExpress.exe"))
	return d


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "wb") as stream:
		stream.write(data)
	return path


def read(path):
	if not os.path.exists(path):
		return None
	with open(path, "rb") as stream:
		return stream.read()


def package(d, name, text, braille=""):
	"""Write workspace\\<name>.dep as the app writes a package (members <name>.txt and .brl)."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.txt", text)
		archive.writestr(f"{name}.brl", braille)
	return path


def sha(path):
	data = read(path)
	return None if data is None else hashlib.sha256(data).hexdigest()[:16]


def listing(folder):
	return sorted(os.listdir(folder)) if os.path.isdir(folder) else None


def files(d):
	return listing(os.path.join(d, "workspace"))


def processes(d):
	import psutil

	d = os.path.normpath(d).lower()
	return [p for p in psutil.process_iter(["exe", "pid"]) if (p.info["exe"] or "").lower().startswith(d)]


def top_windows(d):
	"""(handle, title) of the visible top-level windows of the processes under ``d``."""
	import win32gui
	import win32process

	pids = {p.pid for p in processes(d)}
	found = []

	def collect(handle, _extra):
		if win32gui.IsWindowVisible(handle) and win32process.GetWindowThreadProcessId(handle)[1] in pids:
			found.append((handle, win32gui.GetWindowText(handle)))

	win32gui.EnumWindows(collect, None)
	return found


def start(d, timeout=40):
	"""Start <d>\\DotExpress.exe; press Keep if the invalid-files dialog opens.

	Returns (app, w, invalid): ``invalid`` is the list of the dialog (None if it did not
	open). If the main window does not appear, returns (None, None, how the start ended).
	"""
	from pywinauto import Application

	target = os.path.join(d, "DotExpress.exe")
	launcher = subprocess.Popen([target], cwd=d)
	started = time.time()
	invalid = None
	while time.time() - started < timeout:
		for handle, title in top_windows(d):
			if title == INVALID_FILES and invalid is None:
				dialog = Application(backend="win32").connect(handle=handle).window(handle=handle)
				listbox = dialog.child_window(class_name="ListBox").wrapper_object()
				invalid = listbox.item_texts()
				X.btn(dialog, KEEP_INVALID).click()
				time.sleep(1)
			elif title.endswith("DotExpress"):
				app, w = dx.attach(d)
				return app, w, invalid
		if launcher.poll() is not None and not processes(d):
			return None, None, f"no main window; exited with code {launcher.returncode}"
		time.sleep(0.5)
	return None, None, f"no main window after {timeout} s: {top_windows(d)}"


def maybe_window(app, w, title, timeout=5):
	try:
		return X.wait_window(app, w, title, timeout=timeout)
	except RuntimeError:
		return None


def closed(handle, timeout=5):
	"""Whether the window ``handle`` is gone or hidden within ``timeout`` seconds.

	wx hides a dialog when it ends and destroys it later, so hidden counts as closed.
	"""
	import win32gui

	end = time.time() + timeout
	while time.time() < end:
		if not win32gui.IsWindow(handle) or not win32gui.IsWindowVisible(handle):
			return True
		time.sleep(0.2)
	return False


def name_prompt(app, w, menu_path, title, name):
	"""Choose ``menu_path``, type ``name`` in the name dialog ``title`` and press 確定.

	The dialog closes before the app checks the name, so a click that is lost (the
	dialog stays open) is repeated, at most three times. Returns the box shown then
	(None if none) and the name dialog shown again (its buttons and name; it is closed
	with Esc), or None.
	"""
	G.menu(w, menu_path, wait=0.5)
	dialog = X.wait_window(app, w, title)
	handle = dialog.wrapper_object().handle
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	ok = X.btn(dialog, "確定", "OK")
	for _attempt in range(3):
		ok.click()
		if closed(handle):
			break
	box = G.answer_box(app, "enter", timeout=5)
	again = maybe_window(app, w, title, timeout=3)
	shown_again = None
	if again is not None:
		handle = again.wrapper_object().handle
		shown_again = {"buttons": G.buttons(again), "name": G.edit_text(again)}
		G.press_keys(again, "{ESC}")
		closed(handle)
	return box, shown_again


def save_dialog(app, w, title, path):
	"""Fill the Save dialog ``title`` with ``path``; answer the overwrite prompt with Yes.

	Returns whether the overwrite prompt appeared.
	"""
	G.path_dialog(app, w, title, path)
	prompt = maybe_window(app, w, OVERWRITE_PROMPT, timeout=3)
	if prompt is None:
		return False
	G.press_keys(prompt, "%y", wait=1.5)
	return True


def wheel_up_with_ctrl(w):
	"""Ctrl + one wheel notch up over the source editor: the font size grows by one."""
	import win32api

	editor = w.children(class_name="Edit")[0]
	rect = editor.rectangle()
	x, y = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
	editor.send_message(WM_MOUSEWHEEL, (WHEEL_DELTA << 16) | MK_CONTROL, win32api.MAKELONG(x, y))
	time.sleep(1)


def config(d):
	"""config.json: (BOM, CRLF line ends only, parsed JSON or the bytes if it does not parse)."""
	data = read(os.path.join(d, "config.json"))
	if data is None:
		return None
	try:
		parsed = json.loads(data.decode("utf-8-sig"))
	except ValueError:
		parsed = data
	return {
		"bom": data.startswith(b"\xef\xbb\xbf"),
		"crlf": data.count(b"\n") == data.count(b"\r\n"),
		"json": parsed,
	}


def config_log(d):
	"""The messages of log\\config.log without their timestamps."""
	data = read(os.path.join(d, "log", "config.log"))
	if data is None:
		return []
	return [line[24:] for line in data.decode("utf-8").splitlines() if line[:4].isdigit()]


def lock(path, seconds="600", share="rw"):
	"""Hold ``path`` open in another process (lockshare.py) until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCKSHARE, path, seconds, share], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip(), share)
	return process


unlock = F.unlock


def finish(app, w, d):
	print("close:", D.close(app, w))
	dx.kill_under(d)
