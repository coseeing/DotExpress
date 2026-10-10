"""Shared helpers for the F-6 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and dicts.py of the 2026-10-09-03 Windows verification unchanged.
The dictionary files are built here; their bytes are those of
client/tests/unreadable_dictionary_files.py (big5.csv, big5_late.csv) plus a UTF-8 file
with an unclosed quotation mark (badquote.csv) and readable UTF-8 files (alpha.csv,
acl.csv). Message boxes are read through UIA and their button is pressed through UIA
(``boxes``); Dictionary Management and the entries editor are left open.
"""
import ctypes
import hashlib
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402
import dicts as X  # noqa: E402

LOCKX = os.path.join(HERE, "lockx.py")
MGR = "字典管理"
EDITOR = "自訂字典管理器"
EM_GETSEL = 0x00B0
EM_GETLINECOUNT = 0x00BA
WM_GETTEXTLENGTH = 0x000E

HEADER = "text,braille,type\r\n"
TAIPEI_ROW = "臺北,ㄊㄞˊㄅㄟˇ,Bopomofo\r\n"
ASCII_ROWS = "".join(f"w{index:04d},x,General\r\n" for index in range(1000))
READABLE = (HEADER + "Alpha,⠁,General\r\n").encode("utf-8")
FILES = {
	"big5.csv": (HEADER + TAIPEI_ROW).encode("cp950"),
	"big5_late.csv": (HEADER + ASCII_ROWS).encode("ascii") + TAIPEI_ROW.encode("cp950"),
	# Row 2 opens a quotation mark that is never closed; more than 128 KiB of rows follow,
	# so the field passes the csv module's limit of 131,072 characters.
	"badquote.csv": (HEADER + 'bad,"oops,General\r\n' + "".join(f"q{index:05d},x,General\r\n" for index in range(8000))).encode("utf-8"),
	"alpha.csv": READABLE,
	"acl.csv": READABLE,
}
UTF8_FIXED = (HEADER + TAIPEI_ROW).encode("utf-8")
TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} ")


def digest(data):
	return hashlib.sha256(data).hexdigest()[:16]


def sha(path):
	with open(path, "rb") as stream:
		return digest(stream.read())


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "wb") as stream:
		stream.write(data)


def dictionary(d):
	return os.path.join(d, "dictionary")


def shas(folder):
	return {name: sha(os.path.join(folder, name)) for name in sorted(os.listdir(folder))}


def sources(d):
	"""The test files in <d>\\data (outside the dictionary folder), for Import."""
	folder = os.path.join(d, "data")
	for name, data in FILES.items():
		write(os.path.join(folder, name), data)
	return folder


def start(exe, d, put=()):
	"""Start in a new folder once (the app creates dictionary\\default.csv), close, put the
	named FILES into dictionary\\ and start again. Returns (app, w)."""
	app, w = dx.launch(exe, d)
	print("first start, close:", D.close(app, w))
	for name in put:
		write(os.path.join(dictionary(d), name), FILES[name])
	print("dictionary:", shas(dictionary(d)))
	return dx.launch(exe, d, fresh=False)


def gui_log(d):
	"""The lines of <d>\\log\\gui.log without their time stamps ([] if there is none)."""
	path = os.path.join(d, "log", "gui.log")
	if not os.path.exists(path):
		return []
	with open(path, encoding="utf-8") as stream:
		return [TIMESTAMP.sub("", line) for line in stream.read().splitlines()]


def open_mgr(app, w, timeout=10):
	"""Choose Dictionary Management; return its window, or None if none opens (F-W12)."""
	w.set_focus()
	w.menu_select("#1->#3")
	try:
		return X.wait_window(app, w, MGR, timeout)
	except RuntimeError:
		return None


def rows(mgr):
	"""[[name, count, selected]] of the list."""
	lv, items = X.mgr_items(mgr)
	return [row + (["selected"] if lv.get_item(index).is_selected() else []) for index, row in enumerate(items)]


def reason(mgr):
	"""The reason row: what win32 shows and what UIA reports for it."""
	from pywinauto import Desktop

	descendants = mgr.wrapper_object().descendants()
	edits = [c for c in descendants if c.class_name() == "Edit" and c.is_visible()]
	labels = [c.window_text() for c in descendants if c.class_name() == "Static" and c.is_visible() and c.window_text()]
	uia = Desktop(backend="uia").window(handle=mgr.handle).descendants(control_type="Edit")
	if not edits:
		return {"edit": None, "uia edits": len(uia), "labels": labels}
	handle = edits[0].handle
	start_pos, end_pos = ctypes.c_ulong(), ctypes.c_ulong()
	user32 = ctypes.windll.user32
	user32.SendMessageW(handle, EM_GETSEL, ctypes.byref(start_pos), ctypes.byref(end_pos))
	return {
		"labels": labels,
		"uia name": uia[0].window_text() if uia else None,
		"uia value": uia[0].get_value() if uia else None,
		"sel": (start_pos.value, end_pos.value),
		"length": user32.SendMessageW(handle, WM_GETTEXTLENGTH, 0, 0),
		"lines": user32.SendMessageW(handle, EM_GETLINECOUNT, 0, 0),
	}


def boxes(app, w, press=("OK", "確定"), keep=(MGR, EDITOR)):
	"""Read every other window of the app and press its first ``press`` button through UIA.

	Returns [(title, texts)]. Windows titled in ``keep`` and file dialogs are left open.
	"""
	from pywinauto import Desktop

	out = []
	for title, win in X.windows(app, w).items():
		if title in keep:
			continue
		texts = dx.dialog_text(win)
		if "檔案名稱:" in texts:
			out.append((title, "<file dialog left open>"))
			continue
		out.append((title, [t for t in texts if t not in ("MainInstructionIcon", "關閉", title)]))
		buttons = [
			button
			for button in Desktop(backend="uia").window(handle=win.handle).descendants(control_type="Button")
			if button.window_text() in press
		]
		if buttons:
			buttons[0].invoke()
			time.sleep(0.8)
	return out


def click(mgr, label, wait=1.5):
	X.btn(mgr, label).click()
	time.sleep(wait)


def windows(app, w):
	return sorted(X.windows(app, w))


def focus_after(mgr, keys):
	"""Press ``keys`` in the dialog and return (control type, name) of the focused element."""
	from pywinauto.keyboard import send_keys
	from pywinauto.uia_defines import IUIA
	from pywinauto.uia_element_info import UIAElementInfo

	mgr.set_focus()
	send_keys(keys)
	time.sleep(0.6)
	info = UIAElementInfo(IUIA().iuia.GetFocusedElement())
	return info.control_type, info.name


def focus_list(mgr):
	lv = X.mgr_items(mgr)[0]
	mgr.set_focus()
	lv.set_focus()
	time.sleep(0.4)


def file_dialog(app, w, title, path):
	"""Fill the file dialog ``title`` with ``path`` and press its Open or Save button.

	That is the first visible button other than Cancel (the Save dialog has hidden
	buttons before it).
	"""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit", found_index=0).wrapper_object().set_edit_text(path)
	buttons = [
		c
		for c in dialog.wrapper_object().descendants()
		if c.class_name() == "Button" and c.is_visible() and c.window_text() not in ("取消", "Cancel")
	]
	buttons[0].click()
	time.sleep(2)


def name_dialog(app, w, title, name):
	"""Type ``name`` into the name dialog ``title``, press OK and return the boxes it showed."""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	X.btn(dialog, "確定", "OK").click()
	time.sleep(1.5)
	return boxes(app, w)


def import_as(app, w, mgr, path, name):
	click(mgr, "匯入", wait=0.5)
	file_dialog(app, w, "匯入字典", path)
	return name_dialog(app, w, "新增字典", name)


def export_to(app, w, mgr, path):
	click(mgr, "匯出", wait=0.5)
	file_dialog(app, w, "匯出字典", path)
	return boxes(app, w)


def lock_none(path):
	"""Hold ``path`` open without sharing in another process (lockx.py) until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCKX, path, "600"], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip())
	return process


def unlock(process):
	subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
	time.sleep(1)


def finish(app, w, d):
	"""Close Dictionary Management if open, close the app, end anything left under ``d``."""
	mgr = X.windows(app, w).get(MGR)
	if mgr is not None:
		X.close_mgr(app, w, mgr)
	print("close:", D.close(app, w))
	dx.kill_under(d)
