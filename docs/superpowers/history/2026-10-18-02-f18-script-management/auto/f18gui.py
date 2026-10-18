"""Shared helpers for the F-18 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f13gui.py of F-13 (its ``start`` waits until the workspace is loaded,
F-13 D2) and through it f12gui.py, f9gui.py, f8bgui.py, f8agui.py, f7gui.py, f5gui.py and
dx.py, docs.py, dicts.py of the 2026-10-09-03 Windows verification; and f14gui.py of F-14
(the stand-in browser). F-13's safe_run.py runs every item: keys go only to a window of
the app under test while it is in the foreground, and the logs never hold another
program's window or element names. Added here: the readers of F-18's items: the script
folder, the Translation menu, Script Management (its rows, buttons, reason field), the
name prompt, the script editor (its text through WM_GETTEXT and WM_SETTEXT, never the
clipboard), the Settings script choice, and the message boxes with a named button
pressed through UIA (a Yes/No box has no access keys, F-17).
The work folder is shown as <d>. Nothing here touches the clipboard.
"""
import ctypes
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-14-02-f13-behavior-nvda", "auto"))
import f13gui as H13  # noqa: E402
from f13gui import A, D, F, F9, G, H12, X, dx  # noqa: E402

sys.path.insert(0, os.path.join(HISTORY, "2026-10-14-03-f14-i18n-prep", "auto"))
import f14gui as H14  # noqa: E402

MGR = "腳本管理"
ADD = "新增腳本"
RENAME = "重新命名腳本"
IMPORT = "匯入腳本"
EXPORT = "匯出腳本"
SETTINGS = "DotExpress 設定"
NO_PROCESSING = b"def main(input: str) -> str:\n    return input\n"
UPPER = b"def main(text: str) -> str:\n    return text.upper()\n"
BUTTONS = ("新增", "刪除", "重新命名", "編輯", "匯入", "匯出")
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E


def masked(d, value):
	return H12.masked(d, value)


def prepare(exe, d):
	"""A new work folder with workspace\\ and the exe; the stand-in browser first on PATH."""
	d = A.prepare(exe, d)
	H14.fake_browser(d)
	return d


def write(path, data):
	return A.write(path, data)


def script(d, name, data):
	"""script\\<name>.py with ``data`` (bytes)."""
	return A.write(os.path.join(d, "script", f"{name}.py"), data)


def script_files(d):
	"""{name: bytes} of the script folder (missing: None)."""
	folder = os.path.join(d, "script")
	if not os.path.isdir(folder):
		return None
	return {name: A.read(os.path.join(folder, name)) for name in sorted(os.listdir(folder))}


def config(d):
	"""config.json's conversion section (or what it holds instead)."""
	data = A.read(os.path.join(d, "config.json"))
	if data is None:
		return "missing"
	return json.loads(data.decode("utf-8-sig")).get("conversion", {})


def start(d):
	"""F-13's start: (app, w, shown)."""
	return H13.start(d)


def translation_menu(w):
	"""The items of the Translation menu, as the menu bar shows them."""
	return [item.text() for item in w.menu().items()[1].sub_menu().items()]


def open_manager(app, w):
	"""Translation > 腳本管理... (the third item); the modal Script Management dialog."""
	w.set_focus()
	w.menu_select("#1->#2")
	return X.wait_window(app, w, MGR)


def rows(mgr):
	return X.mgr_items(mgr)[1]


def selected_row(mgr):
	listview = X.mgr_items(mgr)[0]
	selected = [index for index in range(listview.item_count()) if listview.get_item(index).is_selected()]
	return selected


def select(mgr, name):
	"""Select the row whose first column is ``name`` (the display name) and focus the list."""
	listview, items = X.mgr_items(mgr)
	for index, row in enumerate(items):
		if row[0] == name:
			listview.get_item(index).select()
			time.sleep(0.6)
			return
	raise KeyError((name, items))


def buttons(mgr):
	"""{label: enabled} of the six action buttons."""
	return {label: X.btn(mgr, label).is_enabled() for label in BUTTONS}


def reason(mgr):
	"""The reason field (label and text) when it is shown, else None."""
	controls = mgr.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit" and c.is_visible()]
	labels = [c.window_text() for c in controls if c.class_name() == "Static" and c.is_visible() and c.window_text()]
	if not edits:
		return None
	return {"labels": labels, "text": edits[0].window_text()}


def press(win, *labels, wait=1.5):
	"""Press a button with BM_CLICK, so that no key is needed."""
	X.btn(win, *labels).click()
	time.sleep(wait)


def name_prompt(app, w, title, name, timeout=10):
	"""The name dialog ``title``: its name field, then ``name`` typed in (WM_SETTEXT) and 確定."""
	dialog = X.wait_window(app, w, title, timeout)
	edit = dialog.child_window(class_name="Edit").wrapper_object()
	shown = edit.window_text()
	edit.set_edit_text(name)
	press(dialog, "確定", "OK")
	return shown


def maybe_window(app, w, title, timeout=5):
	return A.maybe_window(app, w, title, timeout=timeout)


def editor_control(editor):
	return [c for c in editor.wrapper_object().descendants() if c.class_name().upper().startswith("RICHEDIT")][0]


def get_text(control):
	length = ctypes.windll.user32.SendMessageW(control.handle, WM_GETTEXTLENGTH, 0, 0)
	buffer = ctypes.create_unicode_buffer(length + 1)
	ctypes.windll.user32.SendMessageW(control.handle, WM_GETTEXT, length + 1, buffer)
	return buffer.value


def set_text(control, text):
	"""Replace the editor's text with WM_SETTEXT (wx sends EVT_TEXT), never the clipboard."""
	ctypes.windll.user32.SendMessageW(control.handle, WM_SETTEXT, 0, ctypes.c_wchar_p(text))
	time.sleep(0.5)


def editor_state(editor):
	"""The editor's title, text, UIA name and the focused element."""
	from pywinauto import Desktop

	control = editor_control(editor)
	element = Desktop(backend="uia").window(handle=control.handle)
	return {
		"title": editor.window_text(),
		"text": get_text(control),
		"uia name": element.element_info.name,
		"uia type": element.element_info.control_type,
		"focus": focus(),
	}


def focus():
	"""(control type, name) of the UIA focused element; masked when the app is not in the foreground."""
	if not H13.foreground_is_app():
		return "<another program>"
	return H13.uia_focus()


def box(app, d, timeout=10, key="enter"):
	"""The next message box (masked), answered with ``key``; None if none opens."""
	return H12.box(app, d, timeout=timeout, key=key)


def box_press(app, d, label, timeout=10):
	"""The next message box (masked), answered by invoking its button ``label`` through UIA."""
	import win32gui

	found = G.wait_box(app, timeout)
	if found is None:
		return None
	owner = win32gui.GetWindow(found.handle, 4)
	described = F.describe(found)
	described["owner"] = win32gui.GetWindowText(owner) if owner else None
	# Before F-17 a Yes/No box labels its buttons with an access key, as 「是(&Y)」.
	button = [b for b in found.descendants(control_type="Button") if b.window_text().split("(")[0] == label][0]
	button.invoke()
	time.sleep(1)
	return masked(d, described)


def settings(app, w):
	"""Translation > 設定 (the fifth item): the settings dialog (modeless)."""
	w.set_focus()
	w.menu_select("#1->#4")
	time.sleep(1.5)
	return G.window_titled(app, w, SETTINGS)


def translation_panel(dialog):
	"""The Translation panel's labels and its three choices (items, selection)."""
	controls = dialog.wrapper_object().descendants()
	labels = [c.window_text() for c in controls if c.class_name() == "Static" and c.is_visible() and c.window_text()]
	combos = [c for c in controls if c.class_name() == "ComboBox" and c.is_visible()]
	return {
		"labels": labels,
		"choices": [(combo.item_texts(), combo.selected_text()) for combo in combos],
	}


def choose_script(dialog, display_name):
	"""Select ``display_name`` in the script choice (the third ComboBox of the Translation panel)."""
	combos = [c for c in dialog.wrapper_object().descendants() if c.class_name() == "ComboBox" and c.is_visible()]
	combos[2].select(display_name)
	time.sleep(0.5)


def convert(app, w, d, text):
	"""Put ``text`` in the open document, Translation > Convert; (the box, the Braille Result)."""
	H12.set_source(w, text)
	H12.convert_menu(w)
	shown = F9.box(app, d, timeout=60)
	return shown, H12.braille_text(w)


def file_dialog(app, w, title, path):
	"""Fill the file dialog ``title`` with ``path`` (WM_SETTEXT) and press its Open or Save button."""
	G.path_dialog(app, w, title, path)


def windows(app, w):
	return sorted(X.windows(app, w))


def close(app, w, d):
	"""Close the app (answering what it shows) and end anything under <d>."""
	H12.close_app(app, w, d)
