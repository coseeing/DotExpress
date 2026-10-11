"""Shared helpers for the F-11 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f6gui.py of F-6 (Dictionary Management, file and name dialogs, the
share-none lock lockx.py) and f7gui.py of F-7 (message boxes, which are task dialogs, read
and answered through UIA), and through them f5gui.py and dx.py, docs.py, dicts.py of the
2026-10-09-03 Windows verification. The dictionary editor and the entry dialog are wx
dialogs read through win32. Test dictionaries come from 2026-10-09-03/auto/data or are
built here; every item records the sha256, size and st_mtime_ns of each dictionary file.
No script touches the clipboard: text goes in with set_edit_text, and keys go only to a
window of the app under test while it is in the foreground (``keys``).
"""
import ctypes
import hashlib
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-10-03-f6-unreadable-dictionaries", "auto"))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-10-04-f7-dialog-buttons-surrogates-close", "auto"))
import f6gui as S  # noqa: E402  (puts 2026-10-09-03/auto on sys.path)
import f7gui as G  # noqa: E402  (puts F-5's auto folder on sys.path)
from f7gui import D, F, X, dx  # noqa: E402

DATA = os.path.join(HISTORY, "2026-10-09-03-windows-verification", "auto", "data")
F.KEYS.update({"alt-s": "%s", "alt-b": "%b", "alt-d": "%d"})
MGR = "字典管理"
EDITOR = "自訂字典管理器"
ADD_ENTRY = "新增字典項目"
EDIT_ENTRY = "編輯字典項目"
SETTINGS = "DotExpress 設定"
EM_GETSEL = 0x00B0
GW_OWNER = 4
BOM = b"\xef\xbb\xbf"


RANDOM_TMP = re.compile(r"(\.[\w.]+?\.csv\.)[A-Za-z0-9_]{8,16}(\.tmp)")


def data(name):
	with open(os.path.join(DATA, name), "rb") as stream:
		return stream.read()


def masked(d, value):
	"""``value`` as text, with the work folder as <d> and the random part of a temporary
	file name as <rnd>; a path inside an error message is a repr, so it can be escaped twice."""
	shown = value if isinstance(value, str) else repr(value)
	for form in (d.replace("\\", "\\" * 4), d.replace("\\", "\\" * 2), d):
		shown = shown.replace(form, "<d>")
	return RANDOM_TMP.sub(r"\1<rnd>\2", shown)


def dictionary(d, name=None):
	folder = S.dictionary(d)
	return folder if name is None else os.path.join(folder, f"{name}.csv")


def setup(exe, d, files=None):
	"""A new work folder ``d``: start once (the app creates dictionary\\default.csv), close,
	write ``files`` ({file name: bytes}) into dictionary\\ and start again. Returns (app, w)."""
	app, w = dx.launch(exe, d)
	print("first start, close:", D.close(app, w))
	for name, content in (files or {}).items():
		S.write(os.path.join(dictionary(d), name), content)
	print("dictionary:", files_state(d))
	return dx.launch(exe, d, fresh=False)


def state(path):
	"""(sha256 prefix, size, st_mtime_ns) of a file, or "missing"."""
	if not os.path.exists(path):
		return "missing"
	with open(path, "rb") as stream:
		content = stream.read()
	return (hashlib.sha256(content).hexdigest()[:16], len(content), os.stat(path).st_mtime_ns)


def files_state(d):
	"""{file name: (sha256 prefix, size)} of the dictionary folder (the time is kept apart)."""
	folder = dictionary(d)
	return {name: state(os.path.join(folder, name))[:2] for name in sorted(os.listdir(folder))}


def same(before, path):
	"""Whether the file still has the bytes and the modification time of ``before`` (state())."""
	now = state(path)
	return {"bytes": now[:2] == before[:2], "time": now[2:] == before[2:]}


def text(path):
	"""The file as text, the BOM shown as "<BOM>", so line ends and spaces are visible in a repr."""
	if not os.path.exists(path):
		return "missing"
	with open(path, "rb") as stream:
		content = stream.read()
	prefix = "<BOM>" if content.startswith(BOM) else ""
	return prefix + content[len(BOM) if prefix else 0:].decode("utf-8")


def manager(app, w):
	return X.windows(app, w).get(MGR) or S.open_mgr(app, w)


def close_manager(app, w):
	mgr = X.windows(app, w).get(MGR)
	if mgr is not None:
		X.close_mgr(app, w, mgr)


def count(app, w, name):
	return [row[1] for row in X.mgr_items(manager(app, w))[1] if row[0] == name]


def editor(app, w, name):
	return X.open_editor(app, w, manager(app, w), name)


def windows(app, w):
	return sorted(X.windows(app, w))


def keys(win, sequence, wait=1.0):
	"""Bring ``win`` (a window of the app under test) to the foreground and press ``sequence``."""
	import win32gui
	from pywinauto.keyboard import send_keys

	for _attempt in range(10):
		if win32gui.GetForegroundWindow() == win.handle:
			send_keys(sequence)
			time.sleep(wait)
			return
		win.set_focus()
		time.sleep(0.3)
	raise RuntimeError(f"{win.window_text()!r} is not in the foreground; {sequence!r} was not sent")


def button(win, *labels):
	return X.btn(win, *labels)


def press_button(win, *labels, wait=1.5):
	"""Focus a win32 button of an app dialog, then press it (BM_CLICK): the focus stays on
	the button, as after a click with the mouse."""
	target = button(win, *labels)
	target.set_focus()
	time.sleep(0.3)
	target.click()
	time.sleep(wait)


def focused():
	"""(control type, name) of the element that has the keyboard focus (UIA)."""
	from pywinauto.uia_defines import IUIA
	from pywinauto.uia_element_info import UIAElementInfo

	info = UIAElementInfo(IUIA().iuia.GetFocusedElement())
	return info.control_type, info.name


def open_boxes(app):
	"""The open message boxes of ``app`` as UIA wrappers: the task dialogs of
	ui.message_box.message_box and the generic dialogs of confirm_box (F-11), which are
	#32770 windows that hold no edit field or list."""
	from pywinauto import Desktop

	found = []
	for dialog in dx.dialogs(app):
		if dialog.window_text() in (MGR, EDITOR, ADD_ENTRY, EDIT_ENTRY):
			continue
		classes = {c.class_name() for c in dialog.wrapper_object().descendants()}
		if G.is_task_dialog(dialog) or not classes & {"Edit", "SysListView32", "ComboBox"}:
			found.append(Desktop(backend="uia").window(handle=dialog.handle))
	return found


def describe(found):
	"""What a screen reader gets from a box: f5gui.describe for a task dialog (title, main
	instruction, content, buttons, focus); for a generic dialog its title, its lines of
	text (one Text element each), buttons and focus. Plus the title of its owner window."""
	import win32gui

	if any(c.class_name() == "DirectUIHWND" for c in found.wrapper_object().children()):
		described = F.describe(found)
	else:
		found.set_focus()
		time.sleep(0.5)
		buttons = [
			b.window_text() for b in found.descendants(control_type="Button") if b.element_info.parent.control_type != "TitleBar"
		]
		described = {
			"title": found.window_text(),
			"text": [t.window_text() for t in found.descendants(control_type="Text")],
			"buttons": buttons,
			"focus": focused()[1],
		}
	owner = win32gui.GetWindow(found.handle, GW_OWNER)
	described["owner"] = win32gui.GetWindowText(owner) if owner else None
	return described


def box(app, timeout=5):
	"""(description, UIA wrapper) of the next message box, or (None, None) if none opens
	within ``timeout`` seconds."""
	end = time.time() + timeout
	while time.time() < end:
		found = open_boxes(app)
		if found:
			return describe(found[0]), found[0]
		time.sleep(0.3)
	return None, None


def answer(found, key):
	"""Press ``key`` (a key of f5gui.KEYS, or f5gui.CLOSE_BOX) in the box; f5gui.answer
	presses again if the key was lost. How often is left out of the logs."""
	F.answer(found, key)
	time.sleep(0.5)


def next_box(app, key, timeout=5):
	"""The next box, answered with ``key``; None if no box opens."""
	described, found = box(app, timeout)
	if found is not None:
		answer(found, key)
	return described


def entry_dialog(app, w, title, timeout=10):
	return X.wait_window(app, w, title, timeout)


def entry_fields(dialog):
	"""(source text, braille, type) as the entry dialog shows them."""
	controls = dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	combo = [c for c in controls if c.class_name() == "ComboBox"][0]
	return edits[0].window_text(), edits[1].window_text(), combo.selected_text()


def fill_entry(dialog, source, braille, type_label=None):
	controls = dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	edits[0].set_edit_text(source)
	edits[1].set_edit_text(braille)
	if type_label is not None:
		[c for c in controls if c.class_name() == "ComboBox"][0].select(type_label)


def source_selection(dialog):
	"""(start, end) of the selection in the entry dialog's source text field (EM_GETSEL)."""
	edit = [c for c in dialog.wrapper_object().descendants() if c.class_name() == "Edit"][0]
	start, end = ctypes.c_ulong(), ctypes.c_ulong()
	ctypes.windll.user32.SendMessageW(edit.handle, EM_GETSEL, ctypes.byref(start), ctypes.byref(end))
	return start.value, end.value


def select_row(ed, index):
	"""Select row ``index`` of the editor's list and put the focus in the list."""
	rows = [c for c in ed.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	rows.get_item(index).select()
	rows.set_focus()
	time.sleep(0.5)


def convert(app, w, word):
	"""Convert ``word`` in the open document: the Braille Result text without its trailing
	blank cells (U+2800), and the boxes shown."""
	close_manager(app, w)
	D.set_input(w, word)
	output, shown = X.convert(app, w)
	return output.rstrip(chr(0x2800)), shown


def set_dictionary(app, w, name):
	close_manager(app, w)
	X.set_dictionary(app, w, name)


def config_dictionary(d):
	"""conversion.selected_dictionary in config.json."""
	import json

	path = os.path.join(d, "config.json")
	with open(path, encoding="utf-8") as stream:
		return json.load(stream).get("conversion", {}).get("selected_dictionary")


def finish(app, w, d):
	S.finish(app, w, d)
